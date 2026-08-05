import os

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import OcrModel, PromptSetting, ProviderSetting, get_db
from app.models.schemas import OcrModelOut, PlaygroundResponse
from app.ocr_providers.base import DEFAULT_OCR_PROMPT
from app.services.ocr_service import resolve_prompts, run_ocr
from app.utils.file_validation import validate_file_content
from app.utils.mime import ALLOWED_EXTENSIONS, extension_to_mime
from app.utils.path_security import resolve_path_within

router = APIRouter(prefix="/api/playground", tags=["playground"])


@router.get("/models", response_model=list[OcrModelOut])
async def list_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OcrModel)
        .outerjoin(ProviderSetting, ProviderSetting.id == OcrModel.provider)
        .where(
            OcrModel.is_active,
            or_(ProviderSetting.id.is_(None), ProviderSetting.is_enabled.is_(True)),
        )
        .order_by(OcrModel.elo.desc())
    )
    return [OcrModelOut.model_validate(m) for m in result.scalars().all()]


@router.get("/prompt/{model_id}")
async def get_resolved_prompt(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OcrModel).where(OcrModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    system_prompt, user_prompt = await resolve_prompts(db, model)

    # Determine source from where the prompt actually came (so an intentionally
    # empty system prompt on a model-specific row still reads as "model", not
    # "builtin" — important for models like PaddleOCR-VL that use only a user prompt).
    ms_result = await db.execute(
        select(PromptSetting).where(PromptSetting.model_id == model_id)
    )
    if ms_result.scalar_one_or_none():
        source = "model"
    else:
        default_result = await db.execute(
            select(PromptSetting).where(PromptSetting.is_default)
        )
        source = "default" if default_result.scalar_one_or_none() else "builtin"

    return {
        "prompt": system_prompt,
        "user_prompt": user_prompt,
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
        filepath = resolve_path_within(settings.sample_docs_dir, document_name)
        if filepath is None:
            raise HTTPException(status_code=400, detail="Invalid document name")
        if not filepath.is_file():
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
