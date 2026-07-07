"""Benchmark collections & batch runs.

A collection is a reusable set of uploaded documents. A batch run executes a
collection against selected models (N documents × M models) so new parsing
models can be compared side-by-side as they are released. Admin-protected,
mirroring the settings/admin surface.
"""

import asyncio
import os
import sys
import uuid

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.config import get_settings
from app.models.database import (
    BatchRun,
    BatchRunItem,
    Collection,
    CollectionDocument,
    OcrModel,
    get_db,
)
from app.models.schemas import (
    BatchRunCreate,
    BatchRunDetail,
    BatchRunItemOut,
    BatchRunOut,
    CollectionCreate,
    CollectionDocumentOut,
    CollectionOut,
    OfficialBenchmarkOut,
)
from app.services.benchmark_service import run_batch

# Official benchmarks that can be seeded as ground-truth collections.
OFFICIAL_BENCHMARKS = {
    "omnidocbench": "OmniDocBench (official)",
    "olmocr_bench": "olmOCR-Bench (official)",
}
from app.utils.file_validation import validate_file_content
from app.utils.mime import ALLOWED_EXTENSIONS, extension_to_mime
from app.utils.path_security import resolve_path_within

router = APIRouter(
    prefix="/api/benchmark",
    tags=["benchmark"],
    dependencies=[Depends(require_admin)],
)


async def _completed_count(db: AsyncSession, run_id: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(BatchRunItem)
        .where(
            BatchRunItem.batch_run_id == run_id,
            BatchRunItem.status.in_(["done", "error"]),
        )
    )
    return int(result.scalar_one())


# ── Collections ──────────────────────────────────────────────
@router.post("/collections", response_model=CollectionOut)
async def create_collection(body: CollectionCreate, db: AsyncSession = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    collection = Collection(name=name, description=body.description.strip())
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return CollectionOut.model_validate(collection)


@router.get("/collections", response_model=list[CollectionOut])
async def list_collections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Collection).order_by(Collection.created_at.desc()))
    collections = list(result.scalars().all())

    out: list[CollectionOut] = []
    for c in collections:
        count_result = await db.execute(
            select(func.count())
            .select_from(CollectionDocument)
            .where(CollectionDocument.collection_id == c.id)
        )
        item = CollectionOut.model_validate(c)
        item.document_count = int(count_result.scalar_one())
        out.append(item)
    return out


@router.get("/collections/{collection_id}/documents", response_model=list[CollectionDocumentOut])
async def list_collection_documents(collection_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CollectionDocument)
        .where(CollectionDocument.collection_id == collection_id)
        .order_by(CollectionDocument.created_at)
    )
    return [CollectionDocumentOut.model_validate(d) for d in result.scalars().all()]


@router.post("/collections/{collection_id}/documents", response_model=CollectionDocumentOut)
async def upload_collection_document(
    collection_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    settings = get_settings()
    data = await file.read()
    if len(data) > settings.max_upload_size:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")
    if not validate_file_content(data, ext):
        raise HTTPException(status_code=400, detail="File content does not match its extension")

    # Store under data/collections/<collection_id>/<uuid><ext>
    rel_path = os.path.join(collection_id, f"{uuid.uuid4()}{ext}")
    dest = resolve_path_within(settings.batch_uploads_dir, rel_path)
    if dest is None:
        raise HTTPException(status_code=400, detail="Invalid storage path")
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(dest, "wb") as f:
        await f.write(data)

    doc = CollectionDocument(
        collection_id=collection_id,
        stored_path=rel_path,
        original_name=file.filename or f"upload{ext}",
        mime_type=extension_to_mime(ext, default="image/png"),
        size=len(data),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return CollectionDocumentOut.model_validate(doc)


@router.delete("/collections/{collection_id}/documents/{document_id}")
async def delete_collection_document(
    collection_id: str, document_id: str, db: AsyncSession = Depends(get_db)
):
    doc = await db.get(CollectionDocument, document_id)
    if doc is None or doc.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Document not found")

    settings = get_settings()
    filepath = resolve_path_within(settings.batch_uploads_dir, doc.stored_path)
    if filepath is not None and filepath.is_file():
        filepath.unlink(missing_ok=True)

    await db.delete(doc)
    await db.commit()
    return {"status": "deleted"}


@router.delete("/collections/{collection_id}")
async def delete_collection(collection_id: str, db: AsyncSession = Depends(get_db)):
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Remove stored files
    settings = get_settings()
    coll_dir = resolve_path_within(settings.batch_uploads_dir, collection_id)
    result = await db.execute(
        select(CollectionDocument).where(CollectionDocument.collection_id == collection_id)
    )
    for doc in result.scalars().all():
        await db.delete(doc)
    await db.delete(collection)
    await db.commit()

    if coll_dir is not None and coll_dir.is_dir():
        for child in coll_dir.iterdir():
            child.unlink(missing_ok=True)
        coll_dir.rmdir()
    return {"status": "deleted"}


# ── Batch runs ───────────────────────────────────────────────
@router.post("/runs", response_model=BatchRunOut)
async def create_run(body: BatchRunCreate, db: AsyncSession = Depends(get_db)):
    collection = await db.get(Collection, body.collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    docs_result = await db.execute(
        select(CollectionDocument).where(
            CollectionDocument.collection_id == body.collection_id
        )
    )
    documents = list(docs_result.scalars().all())
    if not documents:
        raise HTTPException(status_code=400, detail="Collection has no documents")

    model_ids = list(dict.fromkeys(body.model_ids))  # dedupe, preserve order
    if not model_ids:
        raise HTTPException(status_code=400, detail="Select at least one model")

    models_result = await db.execute(
        select(OcrModel.id).where(OcrModel.id.in_(model_ids))
    )
    valid_ids = {row[0] for row in models_result.all()}
    missing = [m for m in model_ids if m not in valid_ids]
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown model(s): {', '.join(missing)}")

    # Official collections (kind != "user") are scored against ground truth.
    benchmark_kind = collection.kind if collection.kind != "user" else None

    run = BatchRun(
        collection_id=body.collection_id,
        model_ids=model_ids,
        status="pending",
        total=len(documents) * len(model_ids),
        completed=0,
        benchmark_kind=benchmark_kind,
    )
    db.add(run)
    await db.flush()

    for doc in documents:
        for model_id in model_ids:
            db.add(
                BatchRunItem(
                    batch_run_id=run.id,
                    document_id=doc.id,
                    model_id=model_id,
                    status="pending",
                )
            )
    await db.commit()
    await db.refresh(run)

    # Fire-and-forget background execution
    asyncio.create_task(run_batch(run.id))

    return BatchRunOut.model_validate(run)


@router.get("/runs", response_model=list[BatchRunOut])
async def list_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BatchRun).order_by(BatchRun.created_at.desc()))
    runs = list(result.scalars().all())
    out: list[BatchRunOut] = []
    for run in runs:
        item = BatchRunOut.model_validate(run)
        item.completed = await _completed_count(db, run.id)
        out.append(item)
    return out


@router.get("/runs/{run_id}", response_model=BatchRunDetail)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await db.get(BatchRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    docs_result = await db.execute(
        select(CollectionDocument)
        .where(CollectionDocument.collection_id == run.collection_id)
        .order_by(CollectionDocument.created_at)
    )
    documents = [CollectionDocumentOut.model_validate(d) for d in docs_result.scalars().all()]

    items_result = await db.execute(
        select(BatchRunItem).where(BatchRunItem.batch_run_id == run_id)
    )
    items = [BatchRunItemOut.model_validate(i) for i in items_result.scalars().all()]

    return BatchRunDetail(
        id=run.id,
        collection_id=run.collection_id,
        status=run.status,
        total=run.total,
        completed=await _completed_count(db, run_id),
        created_at=run.created_at,
        benchmark_kind=run.benchmark_kind,
        summary_scores=dict(run.summary_scores or {}),
        documents=documents,
        model_ids=list(run.model_ids or []),
        items=items,
    )


# ── Official benchmarks ──────────────────────────────────────
def _dataset_downloaded(kind: str) -> bool:
    settings = get_settings()
    root = os.path.join(settings.benchmarks_dir, kind)
    if not os.path.isdir(root):
        return False
    # non-empty (any file) counts as present
    for _dir, _dirs, files in os.walk(root):
        if files:
            return True
    return False


async def _prepare_dataset(kind: str) -> None:
    """Background: download the dataset then seed it as an official collection."""
    settings = get_settings()
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    download_script = os.path.join(settings.bench_root, "download_datasets.py")

    async def _sh(cmd: list[str], cwd: str) -> None:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError((out or b"").decode(errors="replace")[-2000:])

    # Use the running server's interpreter (has app deps + hf on PATH),
    # not a bare python3 that lacks sqlalchemy/loguru/app.
    py = sys.executable
    try:
        # 1. download (idempotent, resumable)
        await _sh([py, download_script, "--only", kind], cwd=backend_dir)
        # 2. seed the official collection
        await _sh([py, "seed_official.py", "--only", kind], cwd=backend_dir)
    except Exception as e:  # noqa: BLE001
        from loguru import logger
        logger.error(f"Prepare {kind} failed: {e}")


@router.get("/official", response_model=list[OfficialBenchmarkOut])
async def list_official(db: AsyncSession = Depends(get_db)):
    out: list[OfficialBenchmarkOut] = []
    for kind, name in OFFICIAL_BENCHMARKS.items():
        result = await db.execute(select(Collection).where(Collection.kind == kind))
        collection = result.scalar_one_or_none()
        doc_count = 0
        if collection is not None:
            cnt = await db.execute(
                select(func.count())
                .select_from(CollectionDocument)
                .where(CollectionDocument.collection_id == collection.id)
            )
            doc_count = int(cnt.scalar_one())
        out.append(OfficialBenchmarkOut(
            kind=kind,
            name=name,
            downloaded=_dataset_downloaded(kind),
            document_count=doc_count,
            collection_id=collection.id if collection else None,
        ))
    return out


@router.post("/official/{kind}/prepare")
async def prepare_official(kind: str):
    if kind not in OFFICIAL_BENCHMARKS:
        raise HTTPException(status_code=404, detail="Unknown benchmark")
    asyncio.create_task(_prepare_dataset(kind))
    return {"status": "preparing", "kind": kind}
