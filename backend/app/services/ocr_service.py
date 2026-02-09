import random
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import OcrModel
from app.models.schemas import OcrResult
from app.ocr_providers.base import OcrProvider
from app.ocr_providers.claude import ClaudeOcrProvider
from app.ocr_providers.openai_gpt import OpenAIOcrProvider
from app.ocr_providers.gemini import GeminiOcrProvider
from app.ocr_providers.mistral import MistralOcrProvider
from app.ocr_providers.ollama import OllamaOcrProvider


def get_provider(provider_name: str, model_id: str, config: dict | None = None) -> OcrProvider:
    providers = {
        "claude": ClaudeOcrProvider,
        "openai": OpenAIOcrProvider,
        "gemini": GeminiOcrProvider,
        "mistral": MistralOcrProvider,
        "ollama": OllamaOcrProvider,
    }
    provider_cls = providers.get(provider_name)
    if not provider_cls:
        raise ValueError(f"Unknown provider: {provider_name}")
    return provider_cls(model_id=model_id)


async def select_random_models(db: AsyncSession, count: int = 2) -> list[OcrModel]:
    result = await db.execute(select(OcrModel).where(OcrModel.is_active == True))
    models = list(result.scalars().all())
    if len(models) < count:
        raise ValueError(f"Not enough active models. Need {count}, have {len(models)}")
    return random.sample(models, count)


async def run_ocr(model: OcrModel, image_data: bytes, mime_type: str) -> OcrResult:
    provider = get_provider(model.provider, model.model_id, model.config)
    return await provider.process_image(image_data, mime_type)
