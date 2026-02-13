import asyncio
import json
import os
import time as _time_module
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.models.database import get_db, async_session, OcrModel, Battle
from app.models.schemas import BattleStartResponse, VoteRequest, VoteResponse, OcrModelOut
from app.services.ocr_service import select_random_models, run_ocr, run_ocr_stream, get_postprocessor_name
from app.services.postprocessors import apply_postprocessor
from app.services.elo_service import calculate_elo_change
from app.config import get_settings
from app.utils.mime import extension_to_mime, ALLOWED_EXTENSIONS
from app.utils.file_validation import validate_file_content
from app.utils.error_sanitizer import sanitize_error

router = APIRouter(prefix="/api/battle", tags=["battle"])

# ── In-memory file cache (no disk writes for uploads) ────────
_battle_file_cache: dict[str, tuple[bytes, str, float]] = {}  # battle_id -> (data, mime, created_at)
_CACHE_TTL = 1800  # 30 minutes
_MAX_CACHE_ENTRIES = 50
_MAX_CACHE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB total limit


def _cleanup_stale_cache() -> None:
    now = _time_module.time()
    expired = [k for k, (_, _, ts) in _battle_file_cache.items() if now - ts > _CACHE_TTL]
    for k in expired:
        del _battle_file_cache[k]
    # Evict oldest entries if over entry limit
    while len(_battle_file_cache) > _MAX_CACHE_ENTRIES:
        oldest_key = min(_battle_file_cache, key=lambda k: _battle_file_cache[k][2])
        del _battle_file_cache[oldest_key]
    # Evict oldest entries if over size limit
    total_size = sum(len(data) for data, _, _ in _battle_file_cache.values())
    while total_size > _MAX_CACHE_SIZE_BYTES and _battle_file_cache:
        oldest_key = min(_battle_file_cache, key=lambda k: _battle_file_cache[k][2])
        total_size -= len(_battle_file_cache[oldest_key][0])
        del _battle_file_cache[oldest_key]


@router.post("/start", response_model=BattleStartResponse)
async def start_battle(
    file: UploadFile = File(None),
    document_name: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    _cleanup_stale_cache()

    if file:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        content = await file.read()
        if len(content) > settings.max_upload_size:
            raise HTTPException(status_code=413, detail="File too large (max 50 MB)")
        if not validate_file_content(content, ext):
            raise HTTPException(status_code=400, detail="File content does not match its extension")
        mime_type = extension_to_mime(ext, default="image/png")
        doc_path = file.filename or f"upload{ext}"
    elif document_name:
        filepath = os.path.join(settings.sample_docs_dir, document_name)
        if not os.path.realpath(filepath).startswith(os.path.realpath(settings.sample_docs_dir)):
            raise HTTPException(status_code=400, detail="Invalid document name")
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Document not found")
        with open(filepath, "rb") as f:
            content = f.read()
        ext = os.path.splitext(document_name)[1].lower()
        mime_type = extension_to_mime(ext, default="image/png")
        doc_path = document_name
    else:
        raise HTTPException(status_code=400, detail="Provide a file or document_name")

    models = await select_random_models(db, 2)

    battle_id = str(uuid.uuid4())

    # Store file in memory cache (not on disk)
    _battle_file_cache[battle_id] = (content, mime_type, _time_module.time())

    battle = Battle(
        id=battle_id,
        document_path=doc_path,
        model_a_id=models[0].id,
        model_b_id=models[1].id,
    )
    db.add(battle)
    await db.commit()

    return BattleStartResponse(
        battle_id=battle.id,
        document_url="",
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

    # Read from in-memory cache first, fallback to disk for sample docs
    cache_entry = _battle_file_cache.get(battle_id)
    if cache_entry:
        image_data, mime_type = cache_entry[0], cache_entry[1]
    else:
        settings = get_settings()
        filepath = os.path.join(settings.sample_docs_dir, battle.document_path)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Document no longer available")
        with open(filepath, "rb") as f:
            image_data = f.read()
        ext = os.path.splitext(battle.document_path)[1].lower()
        mime_type = extension_to_mime(ext, default="image/png")

    async def event_stream():
        queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        results: dict[str, dict] = {}

        async def _stream_model(key: str, model: OcrModel):
            token_event = f"model_{key}_token"
            done_event = f"model_{key}_done"
            replace_event = f"model_{key}_replace"
            start = _time_module.time()
            collected: list[str] = []
            try:
                async for chunk in run_ocr_stream(model, image_data, mime_type, db):
                    collected.append(chunk)
                    try:
                        await queue.put((token_event, json.dumps({"token": chunk})))
                    except asyncio.CancelledError:
                        return
                latency = int((_time_module.time() - start) * 1000)
                full_text = "".join(collected)

                pp_name = get_postprocessor_name(model)
                if pp_name and full_text:
                    processed_text = apply_postprocessor(pp_name, full_text)
                    results[key] = {"text": processed_text, "latency_ms": latency, "error": None}
                    try:
                        await queue.put((replace_event, json.dumps({"text": processed_text})))
                    except asyncio.CancelledError:
                        return
                else:
                    results[key] = {"text": full_text, "latency_ms": latency, "error": None}

                try:
                    await queue.put((done_event, json.dumps({"latency_ms": latency})))
                except asyncio.CancelledError:
                    return
            except asyncio.CancelledError:
                return
            except Exception as e:
                latency = int((_time_module.time() - start) * 1000)
                results[key] = {"text": "", "latency_ms": latency, "error": sanitize_error(e)}
                try:
                    await queue.put((done_event, json.dumps({"latency_ms": latency, "error": sanitize_error(e)})))
                except asyncio.CancelledError:
                    return

        task_a = asyncio.create_task(_stream_model("a", model_a))
        task_b = asyncio.create_task(_stream_model("b", model_b))

        done_count = 0
        _stream_timeout = get_settings().stream_timeout_seconds
        while done_count < 2:
            try:
                event_name, event_data = await asyncio.wait_for(
                    queue.get(), timeout=_stream_timeout
                )
            except asyncio.TimeoutError:
                task_a.cancel()
                task_b.cancel()
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Stream timed out"}),
                }
                return
            yield {"event": event_name, "data": event_data}
            if event_name.endswith("_done"):
                done_count += 1

        await asyncio.gather(task_a, task_b, return_exceptions=True)

        # Free cached file data
        _battle_file_cache.pop(battle_id, None)

        # Save results to DB (latency always; OCR text only if configured)
        settings = get_settings()
        async with async_session() as update_db:
            update_result = await update_db.execute(select(Battle).where(Battle.id == battle_id))
            battle_to_update = update_result.scalar_one()
            for key in ("a", "b"):
                r = results.get(key)
                if r:
                    setattr(battle_to_update, f"model_{key}_latency_ms", r["latency_ms"])
                    if settings.store_ocr_results:
                        setattr(battle_to_update, f"model_{key}_result", r["text"])
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

    vote_result = await db.execute(
        update(Battle)
        .where(Battle.id == battle_id, Battle.winner.is_(None))
        .values(winner=vote.winner, voted_at=datetime.now(timezone.utc))
    )
    if vote_result.rowcount == 0:
        raise HTTPException(status_code=400, detail="Already voted")

    model_a_res = await db.execute(select(OcrModel).where(OcrModel.id == battle.model_a_id))
    model_a = model_a_res.scalar_one()
    model_b_res = await db.execute(select(OcrModel).where(OcrModel.id == battle.model_b_id))
    model_b = model_b_res.scalar_one()

    change_a, change_b = calculate_elo_change(model_a.elo, model_b.elo, vote.winner)

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
        "document_name": battle.document_path,
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
