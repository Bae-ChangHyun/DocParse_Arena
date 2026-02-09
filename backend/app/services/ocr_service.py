import asyncio
import random
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import OcrModel, ProviderSetting, PromptSetting
from app.models.schemas import OcrResult
from app.ocr_providers.base import OcrProvider
from app.ocr_providers.claude import ClaudeOcrProvider
from app.ocr_providers.openai_gpt import OpenAIOcrProvider
from app.ocr_providers.gemini import GeminiOcrProvider
from app.ocr_providers.mistral import MistralOcrProvider
from app.ocr_providers.ollama import OllamaOcrProvider
from app.ocr_providers.custom import CustomOcrProvider
from app.services.pdf_service import pdf_to_images

PROVIDER_MAP = {
    "claude": ClaudeOcrProvider,
    "openai": OpenAIOcrProvider,
    "gemini": GeminiOcrProvider,
    "mistral": MistralOcrProvider,
    "ollama": OllamaOcrProvider,
    "custom": CustomOcrProvider,
}


async def _resolve_credentials(db: AsyncSession, model: OcrModel) -> tuple[str, str]:
    api_key = model.api_key or ""
    base_url = model.base_url or ""
    if not api_key or not base_url:
        result = await db.execute(
            select(ProviderSetting).where(ProviderSetting.id == model.provider)
        )
        ps = result.scalar_one_or_none()
        if ps:
            if not api_key:
                api_key = ps.api_key or ""
            if not base_url:
                base_url = ps.base_url or ""
    return api_key, base_url


async def _resolve_prompt(db: AsyncSession, model: OcrModel) -> str:
    """Resolve prompt: model-specific > default > empty (provider will use its own)."""
    # 1. Model-specific prompt
    result = await db.execute(
        select(PromptSetting).where(PromptSetting.model_id == model.id)
    )
    prompt = result.scalar_one_or_none()
    if prompt:
        return prompt.prompt_text

    # 2. Default prompt
    result = await db.execute(
        select(PromptSetting).where(PromptSetting.is_default == True)
    )
    prompt = result.scalar_one_or_none()
    if prompt:
        return prompt.prompt_text

    return ""


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
    prompt = ""

    if db:
        api_key, base_url = await _resolve_credentials(db, model)
        prompt = await _resolve_prompt(db, model)

    provider = get_provider(model.provider, model.model_id, api_key, base_url)

    # Handle PDF: split into pages, OCR each, merge
    if mime_type == "application/pdf":
        return await _run_ocr_pdf(provider, image_data, prompt)

    return await provider.process_image(image_data, mime_type, prompt)


async def _run_ocr_pdf(provider: OcrProvider, pdf_data: bytes, prompt: str) -> OcrResult:
    """Split PDF into page images, OCR each page in parallel, merge results."""
    start = time.time()
    try:
        pages = pdf_to_images(pdf_data)
    except Exception as e:
        return OcrResult(text="", latency_ms=0, error=f"PDF conversion failed: {e}")

    if not pages:
        return OcrResult(text="", latency_ms=0, error="PDF has no pages")

    tasks = [provider.process_image(img_bytes, img_mime, prompt) for img_bytes, img_mime in pages]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged_parts = []
    errors = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"Page {idx + 1}: {result}")
        elif result.error:
            errors.append(f"Page {idx + 1}: {result.error}")
        else:
            header = f"\n\n---\n\n<!-- Page {idx + 1} -->\n\n" if idx > 0 else ""
            text = result.text.lstrip("```markdown").rstrip("```").strip()
            merged_parts.append(header + text)

    total_latency = int((time.time() - start) * 1000)
    merged_text = "".join(merged_parts)
    error_msg = "; ".join(errors) if errors else None

    return OcrResult(text=merged_text, latency_ms=total_latency, error=error_msg)
