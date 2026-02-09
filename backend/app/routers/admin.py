import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, OcrModel, ProviderSetting
from app.models.schemas import (
    OcrModelAdmin,
    OcrModelCreate,
    OcrModelUpdate,
    ProviderSettingOut,
    ProviderSettingUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

KNOWN_PROVIDERS = [
    {"id": "claude", "display_name": "Anthropic Claude"},
    {"id": "openai", "display_name": "OpenAI"},
    {"id": "gemini", "display_name": "Google Gemini"},
    {"id": "mistral", "display_name": "Mistral AI"},
    {"id": "ollama", "display_name": "Ollama (Local)"},
    {"id": "custom", "display_name": "Custom (OpenAI-compatible)"},
]


# ── Provider Settings ──────────────────────────────────────────

@router.get("/providers", response_model=list[ProviderSettingOut])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProviderSetting))
    existing = {p.id: p for p in result.scalars().all()}

    # Ensure all known providers exist in DB
    for kp in KNOWN_PROVIDERS:
        if kp["id"] not in existing:
            ps = ProviderSetting(id=kp["id"], display_name=kp["display_name"])
            db.add(ps)
            existing[kp["id"]] = ps
    await db.commit()

    providers = []
    for kp in KNOWN_PROVIDERS:
        p = existing[kp["id"]]
        await db.refresh(p)
        providers.append(ProviderSettingOut.model_validate(p))
    return providers


@router.put("/providers/{provider_id}", response_model=ProviderSettingOut)
async def update_provider(
    provider_id: str,
    data: ProviderSettingUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProviderSetting).where(ProviderSetting.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if data.api_key is not None:
        provider.api_key = data.api_key
    if data.base_url is not None:
        provider.base_url = data.base_url
    if data.is_enabled is not None:
        provider.is_enabled = data.is_enabled

    await db.commit()
    await db.refresh(provider)
    return ProviderSettingOut.model_validate(provider)


# ── Model Management ──────────────────────────────────────────

@router.get("/models", response_model=list[OcrModelAdmin])
async def list_all_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OcrModel).order_by(OcrModel.created_at))
    return [OcrModelAdmin.model_validate(m) for m in result.scalars().all()]


@router.post("/models", response_model=OcrModelAdmin)
async def create_model(data: OcrModelCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(OcrModel).where(OcrModel.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Model '{data.name}' already exists")

    model = OcrModel(
        id=str(uuid.uuid4()),
        name=data.name,
        display_name=data.display_name,
        icon=data.icon,
        provider=data.provider,
        model_id=data.model_id,
        api_key=data.api_key,
        base_url=data.base_url,
        is_active=data.is_active,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return OcrModelAdmin.model_validate(model)


@router.put("/models/{model_id}", response_model=OcrModelAdmin)
async def update_model(
    model_id: str,
    data: OcrModelUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OcrModel).where(OcrModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(model, field, value)

    await db.commit()
    await db.refresh(model)
    return OcrModelAdmin.model_validate(model)


@router.patch("/models/{model_id}/toggle", response_model=OcrModelAdmin)
async def toggle_model(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OcrModel).where(OcrModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.is_active = not model.is_active
    await db.commit()
    await db.refresh(model)
    return OcrModelAdmin.model_validate(model)


@router.delete("/models/{model_id}")
async def delete_model(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OcrModel).where(OcrModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if model.total_battles > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete model with battle history. Deactivate it instead.",
        )

    await db.delete(model)
    await db.commit()
    return {"ok": True}


@router.post("/models/{model_id}/reset-elo", response_model=OcrModelAdmin)
async def reset_model_elo(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OcrModel).where(OcrModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.elo = 1500
    model.wins = 0
    model.losses = 0
    model.total_battles = 0
    model.avg_latency_ms = 0.0
    await db.commit()
    await db.refresh(model)
    return OcrModelAdmin.model_validate(model)
