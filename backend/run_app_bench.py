"""Trigger an app benchmark run (same path as the UI's POST /runs) for a model
on an official collection, then wait for run_batch + scoring to finish and print
the summary_scores. Proves the app produces official numbers end-to-end.

  backend/.venv/bin/python backend/run_app_bench.py <collection_kind> <model_id>
"""
import asyncio
import sys

from sqlalchemy import select

from app.models.database import BatchRun, BatchRunItem, Collection, CollectionDocument, OcrModel, async_session
from app.services.benchmark_service import run_batch


async def main():
    kind, model_id = sys.argv[1], sys.argv[2]
    async with async_session() as db:
        coll = (await db.execute(select(Collection).where(Collection.kind == kind))).scalar_one()
        docs = list((await db.execute(
            select(CollectionDocument).where(CollectionDocument.collection_id == coll.id))).scalars().all())
        model = (await db.execute(select(OcrModel).where(OcrModel.id == model_id))).scalar_one()
        run = BatchRun(collection_id=coll.id, model_ids=[model_id], status="pending",
                       total=len(docs), completed=0, benchmark_kind=coll.kind)
        db.add(run)
        await db.flush()
        for doc in docs:
            db.add(BatchRunItem(batch_run_id=run.id, document_id=doc.id, model_id=model_id, status="pending"))
        await db.commit()
        await db.refresh(run)
        run_id = run.id
    print(f"run_id={run_id}  docs={len(docs)}  model={model_id}  kind={kind}", flush=True)

    await run_batch(run_id)

    async with async_session() as db:
        run = await db.get(BatchRun, run_id)
        print("STATUS:", run.status, flush=True)
        print("SUMMARY_SCORES:", run.summary_scores, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
