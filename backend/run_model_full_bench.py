"""Run any registered model over the FULL official benchmarks.

Usage:  PYTHONPATH=$PWD ./.venv/bin/python run_model_full_bench.py <model_id> [kind ...]
        (default kinds: omnidocbench olmocr_bench)
"""
import asyncio
import json as _json
import sys

from sqlalchemy import select, func
from app.models.database import (
    BatchRun, BatchRunItem, Collection, CollectionDocument, async_session, init_db,
)
from app.services.benchmark_service import run_batch

MODEL_ID = sys.argv[1]
KINDS = sys.argv[2:] or ["omnidocbench", "olmocr_bench"]


async def make_run(kind: str) -> str:
    async with async_session() as db:
        coll = (await db.execute(select(Collection).where(Collection.kind == kind))).scalar_one()
        docs = list((await db.execute(
            select(CollectionDocument).where(CollectionDocument.collection_id == coll.id)
        )).scalars().all())
        run = BatchRun(collection_id=coll.id, model_ids=[MODEL_ID], status="pending",
                       total=len(docs), benchmark_kind=kind)
        db.add(run)
        await db.flush()
        for d in docs:
            db.add(BatchRunItem(batch_run_id=run.id, document_id=d.id,
                                model_id=MODEL_ID, status="pending"))
        await db.commit()
        print(f"[{kind}] {MODEL_ID}: run {run.id} over {len(docs)} docs", flush=True)
        return run.id


async def main():
    await init_db()
    for kind in KINDS:
        run_id = await make_run(kind)
        print(f"[{kind}] running (OCR + scoring)…", flush=True)
        await run_batch(run_id)
        async with async_session() as db:
            run = await db.get(BatchRun, run_id)
            errs = (await db.execute(select(func.count()).select_from(BatchRunItem).where(
                BatchRunItem.batch_run_id == run_id, BatchRunItem.status == "error"))).scalar_one()
            print(f"[{kind}] DONE err={errs} SCORES={_json.dumps(run.summary_scores, ensure_ascii=False)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
