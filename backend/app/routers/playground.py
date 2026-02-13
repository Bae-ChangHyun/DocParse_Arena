import os
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, OcrModel
from app.models.schemas import PlaygroundResponse, OcrModelOut
from app.services.ocr_service import run_ocr, resolve_prompt
from app.ocr_providers.base import DEFAULT_OCR_PROMPT
from app.config import get_settings
from app.utils.mime import extension_to_mime, ALLOWED_EXTENSIONS
from app.utils.file_validation import validate_file_content

router = APIRouter(prefix="/api/playground", tags=["playground"])


@router.get("/models", response_model=list[OcrModelOut])
async def list_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OcrModel).where(OcrModel.is_active == True).order_by(OcrModel.elo.desc())
    )
    return [OcrModelOut.model_validate(m) for m in result.scalars().all()]


@router.get("/prompt/{model_id}")
async def get_resolved_prompt(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OcrModel).where(OcrModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    prompt = await resolve_prompt(db, model)

    if prompt:
        # Determine source
        from app.models.database import PromptSetting
        ms_result = await db.execute(
            select(PromptSetting).where(PromptSetting.model_id == model_id)
        )
        source = "model" if ms_result.scalar_one_or_none() else "default"
    else:
        prompt = DEFAULT_OCR_PROMPT
        source = "builtin"

    return {
        "prompt": prompt,
        "source": source,
        "default_prompt": DEFAULT_OCR_PROMPT,
    }


@router.post("/ocr", response_model=PlaygroundResponse)
async def playground_ocr(
    model_id: str = Form(...),
    file: UploadFile = File(None),
    document_name: str = Form(None),
    prompt: str = Form(None),
    temperature: float = Form(None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OcrModel).where(OcrModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    settings = get_settings()

    if file:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        image_data = await file.read()
        if len(image_data) > settings.max_upload_size:
            raise HTTPException(status_code=413, detail="File too large")
        if not validate_file_content(image_data, ext):
            raise HTTPException(status_code=400, detail="File content does not match its extension")
    elif document_name:
        filepath = os.path.join(settings.sample_docs_dir, document_name)
        if not os.path.realpath(filepath).startswith(os.path.realpath(settings.sample_docs_dir)):
            raise HTTPException(status_code=400, detail="Invalid document name")
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Document not found")
        async with aiofiles.open(filepath, "rb") as f:
            image_data = await f.read()
        ext = os.path.splitext(document_name)[1].lower()
    else:
        raise HTTPException(status_code=400, detail="Provide a file or document_name")

    mime_type = extension_to_mime(ext, default="image/png")

    ocr_result = await run_ocr(
        model, image_data, mime_type, db,
        prompt_override=prompt,
        temperature_override=temperature,
    )
    if ocr_result.error:
        raise HTTPException(status_code=500, detail=ocr_result.error)

    return PlaygroundResponse(
        model_id=model.id,
        model_name=model.display_name,
        result=ocr_result.text,
        latency_ms=ocr_result.latency_ms,
    )
