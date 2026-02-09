import random
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import OcrModel, ProviderSetting
from app.models.schemas import OcrResult
from app.ocr_providers.base import OcrProvider
from app.ocr_providers.claude import ClaudeOcrProvider
from app.ocr_providers.openai_gpt import OpenAIOcrProvider
from app.ocr_providers.gemini import GeminiOcrProvider
from app.ocr_providers.mistral import MistralOcrProvider
from app.ocr_providers.ollama import OllamaOcrProvider
from app.ocr_providers.custom import CustomOcrProvider

PROVIDER_MAP = {
    "claude": ClaudeOcrProvider,
    "openai": OpenAIOcrProvider,
    "gemini": GeminiOcrProvider,
    "mistral": MistralOcrProvider,
    "ollama": OllamaOcrProvider,
    "custom": CustomOcrProvider,
}


async def _resolve_credentials(db: AsyncSession, model: OcrModel) -> tuple[str, str]:
    """Resolve api_key and base_url: model-level overrides provider-level."""
    api_key = model.api_key or ""
    base_url = model.base_url or ""

    if not api_key or not base_url:
        result = await db.execute(
            select(ProviderSetting).where(ProviderSetting.id == model.provider)
        )
        provider_setting = result.scalar_one_or_none()
        if provider_setting:
            if not api_key:
                api_key = provider_setting.api_key or ""
            if not base_url:
                base_url = provider_setting.base_url or ""

    return api_key, base_url


def get_provider(provider_name: str, model_id: str, api_key: str = "", base_url: str = "") -> OcrProvider:
    provider_cls = PROVIDER_MAP.get(provider_name)
    if not provider_cls:
        raise ValueError(f"Unknown provider: {provider_name}")
    return provider_cls(model_id=model_id, api_key=api_key, base_url=base_url)


async def select_random_models(db: AsyncSession, count: int = 2) -> list[OcrModel]:
    result = await db.execute(select(OcrModel).where(OcrModel.is_active == True))
    models = list(result.scalars().all())
    if len(models) < count:
        raise ValueError(f"Not enough active models. Need {count}, have {len(models)}")
    return random.sample(models, count)


async def run_ocr(model: OcrModel, image_data: bytes, mime_type: str, db: AsyncSession | None = None) -> OcrResult:
    api_key = model.api_key or ""
    base_url = model.base_url or ""

    if db and (not api_key or not base_url):
        api_key, base_url = await _resolve_credentials(db, model)

    provider = get_provider(model.provider, model.model_id, api_key, base_url)
    return await provider.process_image(image_data, mime_type)
