"""Batch benchmark runner.

Executes a collection of documents against a set of OCR models as an N×M
matrix, reusing the existing ``run_ocr`` engine. Each cell is one
``BatchRunItem``. Runs in the background with bounded concurrency; a single
failed cell does not abort the rest of the run.
"""

import asyncio

import aiofiles
from loguru import logger
from sqlalchemy import select, update

from app.config import get_settings
from app.models.database import (
    BatchRun,
    BatchRunItem,
    Collection,
    CollectionDocument,
    OcrModel,
    async_session,
)
from app.services.bench_scoring import score_run
from app.services.ocr_service import run_ocr
from app.utils.error_sanitizer import sanitize_error
from app.utils.path_security import resolve_path_within


async def _run_item(
    item_id: str, sem: asyncio.Semaphore, base_dir: str, benchmark_kind: str | None
) -> None:
    """Execute a single matrix cell in its own DB session.

    ``base_dir`` is where ``doc.stored_path`` resolves (uploads vs benchmarks).
    ``benchmark_kind`` selects benchmark-scoped prompts when set.
    """
    async with sem:
        async with async_session() as db:
            item = await db.get(BatchRunItem, item_id)
            if item is None:
                return

            item.status = "running"
            await db.commit()

            model = await db.get(OcrModel, item.model_id)
            doc = await db.get(CollectionDocument, item.document_id)

            error: str | None = None
            text: str | None = None
            latency: int | None = None

            try:
                if model is None or doc is None:
                    raise ValueError("Model or document no longer exists")

                filepath = resolve_path_within(base_dir, doc.stored_path)
                if filepath is None or not filepath.is_file():
                    raise FileNotFoundError("Stored document not found")

                async with aiofiles.open(filepath, "rb") as f:
                    data = await f.read()

                result = await run_ocr(model, data, doc.mime_type, db, benchmark=benchmark_kind)
                if result.error:
                    error = sanitize_error(Exception(result.error))
                else:
                    text = result.text
                    latency = result.latency_ms
            except Exception as e:  # noqa: BLE001 — record per-cell failure, keep going
                error = sanitize_error(e)
                logger.warning(f"Batch item {item_id} failed: {e}")

            item.status = "error" if error else "done"
            item.result_text = text
            item.latency_ms = latency
            item.error = error
            await db.commit()


async def _finalize(run_id: str, status: str = "done") -> None:
    async with async_session() as db:
        await db.execute(
            update(BatchRun).where(BatchRun.id == run_id).values(status=status)
        )
        await db.commit()


async def _score_stage(run_id: str, benchmark_kind: str) -> None:
    """Score a finished official-benchmark run and persist per-model scores."""
    await _finalize(run_id, status="scoring")
    try:
        async with async_session() as db:
            scores = await score_run(db, run_id, benchmark_kind)
            await db.execute(
                update(BatchRun).where(BatchRun.id == run_id).values(summary_scores=scores)
            )
            await db.commit()
        logger.info(f"Run {run_id}: scored {len(scores)} models on {benchmark_kind}")
    except Exception as e:  # noqa: BLE001 — scoring failure shouldn't wipe OCR results
        logger.error(f"Run {run_id}: scoring failed: {e}")


async def run_batch(run_id: str) -> None:
    """Background entrypoint: execute all pending items for a batch run."""
    settings = get_settings()
    sem = asyncio.Semaphore(max(1, settings.batch_concurrency))

    async with async_session() as db:
        await db.execute(
            update(BatchRun).where(BatchRun.id == run_id).values(status="running")
        )
        await db.commit()
        run = await db.get(BatchRun, run_id)
        benchmark_kind = run.benchmark_kind if run else None
        collection = await db.get(Collection, run.collection_id) if run else None
        result = await db.execute(
            select(BatchRunItem.id).where(BatchRunItem.batch_run_id == run_id)
        )
        item_ids = [row[0] for row in result.all()]

    # Official collections store files under benchmarks_dir/ (stored_path already
    # includes the <kind>/ prefix); user collections resolve under uploads.
    if collection is not None and collection.kind != "user":
        base_dir = settings.benchmarks_dir
    else:
        base_dir = settings.batch_uploads_dir

    try:
        await asyncio.gather(
            *(_run_item(iid, sem, base_dir, benchmark_kind) for iid in item_ids)
        )
        if benchmark_kind:
            await _score_stage(run_id, benchmark_kind)
    finally:
        # completed count is derived at read time, but stamp terminal status here
        await _finalize(run_id)
