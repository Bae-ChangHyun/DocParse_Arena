import asyncio
import json
import os
import uuid
import aiofiles
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.models.database import get_db, async_session, OcrModel, Battle
from app.models.schemas import BattleStartResponse, VoteRequest, VoteResponse, OcrModelOut
from app.services.ocr_service import select_random_models, run_ocr
from app.services.elo_service import calculate_elo_change
from app.config import get_settings

router = APIRouter(prefix="/api/battle", tags=["battle"])


@router.post("/start", response_model=BattleStartResponse)
async def start_battle(
    file: UploadFile = File(None),
    document_name: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()

    if file:
        ext = os.path.splitext(file.filename or "")[1].lower()
        safe_name = f"{uuid.uuid4().hex}{ext}"
        os.makedirs(settings.sample_docs_dir, exist_ok=True)
        filepath = os.path.join(settings.sample_docs_dir, safe_name)
        async with aiofiles.open(filepath, "wb") as f:
            content = await file.read()
            await f.write(content)
        doc_path = safe_name
    elif document_name:
        filepath = os.path.join(settings.sample_docs_dir, document_name)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Document not found")
        doc_path = document_name
    else:
        raise HTTPException(status_code=400, detail="Provide a file or document_name")

    models = await select_random_models(db, 2)

    battle = Battle(
        id=str(uuid.uuid4()),
        document_path=doc_path,
        model_a_id=models[0].id,
        model_b_id=models[1].id,
    )
    db.add(battle)
    await db.commit()

    return BattleStartResponse(
        battle_id=battle.id,
        document_url=f"/api/documents/file/{doc_path}",
        model_a_label="Model A",
        model_b_label="Model B",
    )


@router.get("/{battle_id}/stream")
async def stream_battle(battle_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Battle).where(Battle.id == battle_id))
    battle = result.scalar_one_or_none()
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    if battle.model_a_result and battle.model_b_result:
        async def cached_stream():
            yield {
                "event": "model_a_result",
                "data": json.dumps({
                    "text": battle.model_a_result,
                    "latency_ms": battle.model_a_latency_ms,
                }),
            }
            yield {
                "event": "model_b_result",
                "data": json.dumps({
                    "text": battle.model_b_result,
                    "latency_ms": battle.model_b_latency_ms,
                }),
            }
            yield {"event": "done", "data": "{}"}
        return EventSourceResponse(cached_stream())

    model_a_res = await db.execute(select(OcrModel).where(OcrModel.id == battle.model_a_id))
    model_a = model_a_res.scalar_one()
    model_b_res = await db.execute(select(OcrModel).where(OcrModel.id == battle.model_b_id))
    model_b = model_b_res.scalar_one()

    settings = get_settings()
    filepath = os.path.join(settings.sample_docs_dir, battle.document_path)

    async with aiofiles.open(filepath, "rb") as f:
        image_data = await f.read()

    ext = os.path.splitext(battle.document_path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
    }
    mime_type = mime_map.get(ext, "image/png")

    async def event_stream():
        tasks = {
            "a": asyncio.create_task(run_ocr(model_a, image_data, mime_type, db)),
            "b": asyncio.create_task(run_ocr(model_b, image_data, mime_type, db)),
        }

        for key, label in [("a", "model_a_result"), ("b", "model_b_result")]:
            try:
                result = await tasks[key]
                yield {
                    "event": label,
                    "data": json.dumps({
                        "text": result.text,
                        "latency_ms": result.latency_ms,
                        "error": result.error,
                    }),
                }
            except Exception as e:
                yield {
                    "event": label,
                    "data": json.dumps({"text": "", "latency_ms": 0, "error": str(e)}),
                }

        result_a = tasks["a"].result() if tasks["a"].done() else None
        result_b = tasks["b"].result() if tasks["b"].done() else None

        async with async_session() as update_db:
            update_result = await update_db.execute(select(Battle).where(Battle.id == battle_id))
            battle_to_update = update_result.scalar_one()
            if result_a:
                battle_to_update.model_a_result = result_a.text
                battle_to_update.model_a_latency_ms = result_a.latency_ms
            if result_b:
                battle_to_update.model_b_result = result_b.text
                battle_to_update.model_b_latency_ms = result_b.latency_ms
            await update_db.commit()

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_stream())


@router.post("/{battle_id}/vote", response_model=VoteResponse)
async def vote_battle(battle_id: str, vote: VoteRequest, db: AsyncSession = Depends(get_db)):
    if vote.winner not in ("a", "b", "tie"):
        raise HTTPException(status_code=400, detail="winner must be 'a', 'b', or 'tie'")

    result = await db.execute(select(Battle).where(Battle.id == battle_id))
    battle = result.scalar_one_or_none()
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")
    if battle.winner:
        raise HTTPException(status_code=400, detail="Already voted")

    # Atomically mark battle as voted (prevents double-vote race condition)
    vote_result = await db.execute(
        update(Battle)
        .where(Battle.id == battle_id, Battle.winner.is_(None))
        .values(winner=vote.winner, voted_at=datetime.utcnow())
    )
    if vote_result.rowcount == 0:
        raise HTTPException(status_code=400, detail="Already voted")

    model_a_res = await db.execute(select(OcrModel).where(OcrModel.id == battle.model_a_id))
    model_a = model_a_res.scalar_one()
    model_b_res = await db.execute(select(OcrModel).where(OcrModel.id == battle.model_b_id))
    model_b = model_b_res.scalar_one()

    change_a, change_b = calculate_elo_change(model_a.elo, model_b.elo, vote.winner)

    # Atomic SQL updates to prevent lost updates under concurrency
    update_a = {
        "elo": OcrModel.elo + change_a,
        "total_battles": OcrModel.total_battles + 1,
    }
    update_b = {
        "elo": OcrModel.elo + change_b,
        "total_battles": OcrModel.total_battles + 1,
    }

    if vote.winner == "a":
        update_a["wins"] = OcrModel.wins + 1
        update_b["losses"] = OcrModel.losses + 1
    elif vote.winner == "b":
        update_b["wins"] = OcrModel.wins + 1
        update_a["losses"] = OcrModel.losses + 1

    if battle.model_a_latency_ms:
        update_a["avg_latency_ms"] = (
            OcrModel.avg_latency_ms * OcrModel.total_battles + battle.model_a_latency_ms
        ) / (OcrModel.total_battles + 1)
    if battle.model_b_latency_ms:
        update_b["avg_latency_ms"] = (
            OcrModel.avg_latency_ms * OcrModel.total_battles + battle.model_b_latency_ms
        ) / (OcrModel.total_battles + 1)

    await db.execute(update(OcrModel).where(OcrModel.id == battle.model_a_id).values(**update_a))
    await db.execute(update(OcrModel).where(OcrModel.id == battle.model_b_id).values(**update_b))

    await db.commit()

    # Refresh for response
    await db.refresh(model_a)
    await db.refresh(model_b)

    return VoteResponse(
        battle_id=battle_id,
        winner=vote.winner,
        model_a=OcrModelOut.model_validate(model_a),
        model_b=OcrModelOut.model_validate(model_b),
        model_a_elo_change=change_a,
        model_b_elo_change=change_b,
    )


@router.get("/{battle_id}")
async def get_battle(battle_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Battle).where(Battle.id == battle_id))
    battle = result.scalar_one_or_none()
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    data = {
        "id": battle.id,
        "document_url": f"/api/documents/file/{battle.document_path}",
        "model_a_result": battle.model_a_result,
        "model_b_result": battle.model_b_result,
        "model_a_latency_ms": battle.model_a_latency_ms,
        "model_b_latency_ms": battle.model_b_latency_ms,
        "winner": battle.winner,
        "created_at": battle.created_at.isoformat() if battle.created_at else None,
    }

    if battle.winner:
        model_a_res = await db.execute(select(OcrModel).where(OcrModel.id == battle.model_a_id))
        model_b_res = await db.execute(select(OcrModel).where(OcrModel.id == battle.model_b_id))
        data["model_a"] = OcrModelOut.model_validate(model_a_res.scalar_one()).model_dump()
        data["model_b"] = OcrModelOut.model_validate(model_b_res.scalar_one()).model_dump()

    return data
