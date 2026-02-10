import uuid
import httpx
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, OcrModel, ProviderSetting, PromptSetting, Battle
from app.models.schemas import (
    OcrModelAdmin,
    OcrModelCreate,
    OcrModelUpdate,
    ProviderSettingOut,
    ProviderSettingCreate,
    ProviderSettingUpdate,
    PromptSettingOut,
    PromptSettingCreate,
    PromptSettingUpdate,
    AdminLoginRequest,
)
from app.config import get_settings
from app.auth import require_admin, create_token
from app.vlm_registry import list_registry, match_registry

# Public router: no auth required
public_router = APIRouter(prefix="/api/admin", tags=["admin"])

# Protected router: requires admin auth
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

@public_router.get("/auth-status")
async def auth_status():
    settings = get_settings()
    return {"auth_required": bool(settings.admin_password)}


@public_router.post("/login")
async def admin_login(data: AdminLoginRequest):
    settings = get_settings()
    if not settings.admin_password:
        return {"token": ""}
    if data.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_token()
    return {"token": token}


BUILTIN_PROVIDERS = [
    {"id": "claude", "display_name": "Anthropic Claude", "provider_type": "claude"},
    {"id": "openai", "display_name": "OpenAI", "provider_type": "openai"},
    {"id": "gemini", "display_name": "Google Gemini", "provider_type": "gemini"},
    {"id": "mistral", "display_name": "Mistral AI", "provider_type": "mistral"},
    {"id": "ollama", "display_name": "Ollama (Local)", "provider_type": "ollama"},
]

BUILTIN_IDS = {p["id"] for p in BUILTIN_PROVIDERS}

# Provider types that require base_url connectivity
URL_BASED_TYPES = {"ollama", "custom"}
# Provider types that require api_key
KEY_BASED_TYPES = {"claude", "openai", "gemini", "mistral"}


# ── Provider Settings ──────────────────────────────────────────

@router.get("/providers", response_model=list[ProviderSettingOut])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProviderSetting))
    existing = {p.id: p for p in result.scalars().all()}

    # Ensure all built-in providers exist in DB
    for bp in BUILTIN_PROVIDERS:
        if bp["id"] not in existing:
            ps = ProviderSetting(
                id=bp["id"],
                display_name=bp["display_name"],
                provider_type=bp["provider_type"],
            )
            db.add(ps)
            existing[bp["id"]] = ps
    await db.commit()

    providers = []
    # Built-in first (in order)
    for bp in BUILTIN_PROVIDERS:
        p = existing[bp["id"]]
        await db.refresh(p)
        providers.append(ProviderSettingOut.model_validate(p))
    # Then custom providers
    for pid, p in existing.items():
        if pid not in BUILTIN_IDS:
            await db.refresh(p)
            providers.append(ProviderSettingOut.model_validate(p))
    return providers


@router.post("/providers", response_model=ProviderSettingOut)
async def create_provider(data: ProviderSettingCreate, db: AsyncSession = Depends(get_db)):
    """Create a new custom provider."""
    provider = ProviderSetting(
        id=str(uuid.uuid4()),
        display_name=data.display_name,
        provider_type=data.provider_type,
        api_key=data.api_key,
        base_url=data.base_url,
        is_enabled=data.is_enabled,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return ProviderSettingOut.model_validate(provider)


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

    updates = data.model_dump(exclude_none=True)
    # Strip whitespace from key/url fields
    for f in ("api_key", "base_url"):
        if f in updates and isinstance(updates[f], str):
            updates[f] = updates[f].strip()
    # Skip masked api_key (frontend sends back masked value if unchanged)
    if "api_key" in updates and "***" in updates["api_key"]:
        del updates["api_key"]
    for field, value in updates.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return ProviderSettingOut.model_validate(provider)


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    if provider_id in BUILTIN_IDS:
        raise HTTPException(status_code=400, detail="Cannot delete built-in provider")

    result = await db.execute(select(ProviderSetting).where(ProviderSetting.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Check if any models use this provider
    models_result = await db.execute(select(OcrModel).where(OcrModel.provider == provider_id))
    models = models_result.scalars().all()
    if models:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {len(models)} model(s) use this provider. Remove or reassign them first.",
        )

    await db.delete(provider)
    await db.commit()
    return {"ok": True}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    """Test provider connectivity. Auto-deactivates models on failure."""
    result = await db.execute(select(ProviderSetting).where(ProviderSetting.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    ptype = provider.provider_type or provider_id
    ok = False
    message = ""

    if ptype in URL_BASED_TYPES:
        base_url = (provider.base_url or "").strip()
        if not base_url:
            message = "Base URL is not configured"
        else:
            ok, message = await _test_url(base_url, ptype, (provider.api_key or "").strip())
    elif ptype in KEY_BASED_TYPES:
        api_key = (provider.api_key or "").strip()
        if not api_key:
            message = "API key is not configured"
        else:
            ok, message = await _test_api_key(ptype, api_key)
    else:
        ok = True
        message = "No connectivity check required"

    # Auto-deactivate/activate models based on result
    disabled_models = []
    models_result = await db.execute(select(OcrModel).where(OcrModel.provider == provider_id))
    models = list(models_result.scalars().all())
    if not ok and models:
        for m in models:
            if m.is_active:
                m.is_active = False
                disabled_models.append(m.display_name)
        await db.commit()

    return {
        "ok": ok,
        "message": message,
        "disabled_models": disabled_models,
    }


@router.post("/providers/test-all")
async def test_all_providers(db: AsyncSession = Depends(get_db)):
    """Test all enabled providers and auto-deactivate models on failure."""
    result = await db.execute(select(ProviderSetting))
    providers = list(result.scalars().all())

    results = []
    total_disabled = []

    for provider in providers:
        ptype = provider.provider_type or provider.id
        ok = False
        message = ""

        if ptype in URL_BASED_TYPES:
            base_url = (provider.base_url or "").strip()
            if not base_url:
                message = "Base URL is not configured"
            else:
                ok, message = await _test_url(base_url, ptype, (provider.api_key or "").strip())
        elif ptype in KEY_BASED_TYPES:
            api_key = (provider.api_key or "").strip()
            if not api_key:
                message = "API key is not configured"
            else:
                ok, message = await _test_api_key(ptype, api_key)
        else:
            ok = True
            message = "OK"

        # Auto-deactivate models on failure
        disabled = []
        models_result = await db.execute(select(OcrModel).where(OcrModel.provider == provider.id))
        models = list(models_result.scalars().all())
        if not ok and models:
            for m in models:
                if m.is_active:
                    m.is_active = False
                    disabled.append(m.display_name)
                    total_disabled.append(m.display_name)

        results.append({
            "provider_id": provider.id,
            "display_name": provider.display_name,
            "ok": ok,
            "message": message,
            "disabled_models": disabled,
        })

    await db.commit()
    return {"results": results, "total_disabled": total_disabled}


async def _test_api_key(ptype: str, api_key: str) -> tuple[bool, str]:
    """Test API key by making a real API call (list models)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if ptype == "openai":
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            elif ptype == "claude":
                resp = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
            elif ptype == "gemini":
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}&pageSize=1",
                )
            elif ptype == "mistral":
                resp = await client.get(
                    "https://api.mistral.ai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            else:
                return True, "API key is set (no test available)"

            if resp.status_code == 200:
                return True, f"Connected (HTTP {resp.status_code})"
            elif resp.status_code == 401:
                return False, "Invalid API key (HTTP 401)"
            elif resp.status_code == 403:
                return False, "Access denied (HTTP 403)"
            else:
                return False, f"API error (HTTP {resp.status_code})"
    except httpx.TimeoutException:
        return False, "Connection timed out"
    except Exception as e:
        return False, f"Connection failed: {e}"


async def _test_url(base_url: str, ptype: str, api_key: str = "") -> tuple[bool, str]:
    """Test connectivity to a base URL."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if ptype == "ollama":
                resp = await client.get(base_url)
            else:
                # Custom OpenAI-compatible: try /models with auth
                url = base_url.rstrip("/")
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = await client.get(f"{url}/models", headers=headers)
        if resp.status_code < 500:
            return True, f"Connected (HTTP {resp.status_code})"
        return False, f"Server error (HTTP {resp.status_code})"
    except httpx.ConnectError:
        return False, "Connection refused - server not reachable"
    except httpx.TimeoutException:
        return False, "Connection timed out"
    except Exception as e:
        return False, f"Connection failed: {e}"


@router.get("/providers/{provider_id}/models")
async def list_provider_models(provider_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch available models from a provider's API."""
    result = await db.execute(select(ProviderSetting).where(ProviderSetting.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    ptype = provider.provider_type or provider_id
    api_key = (provider.api_key or "").strip()
    base_url = (provider.base_url or "").strip()
    models = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if ptype == "openai":
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = sorted(
                        [m["id"] for m in data.get("data", []) if "gpt" in m["id"].lower()],
                    )
            elif ptype == "gemini":
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = sorted(
                        [m["name"].replace("models/", "") for m in data.get("models", [])
                         if "gemini" in m.get("name", "").lower()],
                    )
            elif ptype == "mistral":
                resp = await client.get(
                    "https://api.mistral.ai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = sorted([m["id"] for m in data.get("data", [])])
            elif ptype == "claude":
                resp = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = sorted([m["id"] for m in data.get("data", [])])
            elif ptype == "ollama":
                url = (base_url or "http://localhost:11434").rstrip("/")
                resp = await client.get(f"{url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = sorted([m["name"] for m in data.get("models", [])])
            elif ptype == "custom":
                url = (base_url or "").rstrip("/")
                if url:
                    headers = {}
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                    resp = await client.get(f"{url}/models", headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        models = sorted([m["id"] for m in data.get("data", [])])
    except Exception as e:
        return {"models": models, "error": str(e)}

    return {"models": models}


# ── Model Management ──────────────────────────────────────────

@router.get("/models")
async def list_all_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OcrModel).order_by(OcrModel.created_at))
    models = result.scalars().all()

    # Build provider config status map
    prov_result = await db.execute(select(ProviderSetting))
    providers = {p.id: p for p in prov_result.scalars().all()}

    items = []
    for m in models:
        data = OcrModelAdmin.model_validate(m).model_dump()
        # Check if provider is properly configured
        ps = providers.get(m.provider)
        if ps:
            ptype = ps.provider_type or m.provider
            if ptype in URL_BASED_TYPES:
                data["provider_ok"] = bool(ps.base_url)
            elif ptype in KEY_BASED_TYPES:
                data["provider_ok"] = bool(ps.api_key or m.api_key)
            else:
                data["provider_ok"] = True
        else:
            data["provider_ok"] = False
        items.append(data)
    return items


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
        config=data.config,
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

    updates = data.model_dump(exclude_none=True)
    # Skip masked api_key (frontend sends back masked value if unchanged)
    if "api_key" in updates and "***" in updates["api_key"]:
        del updates["api_key"]
    for field, value in updates.items():
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


# ── Prompt Settings ──────────────────────────────────────────

@router.get("/prompts", response_model=list[PromptSettingOut])
async def list_prompts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PromptSetting))
    return [PromptSettingOut.model_validate(p) for p in result.scalars().all()]


@router.post("/prompts", response_model=PromptSettingOut)
async def create_prompt(data: PromptSettingCreate, db: AsyncSession = Depends(get_db)):
    # If setting as default, clear existing defaults
    if data.is_default:
        result = await db.execute(select(PromptSetting).where(PromptSetting.is_default == True))
        for p in result.scalars().all():
            p.is_default = False

    # If model_id specified, remove existing prompt for that model
    if data.model_id:
        result = await db.execute(
            select(PromptSetting).where(PromptSetting.model_id == data.model_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            await db.delete(existing)

    prompt = PromptSetting(
        name=data.name,
        prompt_text=data.prompt_text,
        is_default=data.is_default,
        model_id=data.model_id,
    )
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return PromptSettingOut.model_validate(prompt)


@router.put("/prompts/{prompt_id}", response_model=PromptSettingOut)
async def update_prompt(
    prompt_id: str,
    data: PromptSettingUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptSetting).where(PromptSetting.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if data.is_default:
        # Clear other defaults
        result = await db.execute(
            select(PromptSetting).where(PromptSetting.is_default == True, PromptSetting.id != prompt_id)
        )
        for p in result.scalars().all():
            p.is_default = False

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(prompt, field, value)

    await db.commit()
    await db.refresh(prompt)
    return PromptSettingOut.model_validate(prompt)


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PromptSetting).where(PromptSetting.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    await db.delete(prompt)
    await db.commit()
    return {"ok": True}


# ── Dangerous Operations ──────────────────────────────────────────

@router.delete("/reset-battles")
async def reset_battles(db: AsyncSession = Depends(get_db)):
    """Delete all battle records and reset ELO for all models."""
    await db.execute(delete(Battle))

    result = await db.execute(select(OcrModel))
    for model in result.scalars().all():
        model.elo = 1500
        model.wins = 0
        model.losses = 0
        model.total_battles = 0
        model.avg_latency_ms = 0.0

    await db.commit()
    return {"ok": True, "message": "All battles deleted and ELO reset"}


@router.delete("/reset-all")
async def reset_all(db: AsyncSession = Depends(get_db)):
    """Factory reset: delete battles, prompts, and reset ELO."""
    await db.execute(delete(Battle))
    await db.execute(delete(PromptSetting))

    result = await db.execute(select(OcrModel))
    for model in result.scalars().all():
        model.elo = 1500
        model.wins = 0
        model.losses = 0
        model.total_battles = 0
        model.avg_latency_ms = 0.0

    await db.commit()
    return {"ok": True, "message": "Factory reset complete"}


# ── VLM Registry ──────────────────────────────────────────

@router.get("/registry")
async def get_registry():
    """List all known VLM model entries from the registry."""
    return list_registry()


@router.get("/registry/match")
async def get_registry_match(model_id: str):
    """Match a model_id against the VLM registry."""
    result = match_registry(model_id)
    return result
