import asyncio
import random
import re
import time
from collections.abc import AsyncGenerator
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
from app.services.pdf_service import pdf_to_images_async
from app.services.postprocessors import apply_postprocessor, strip_code_fences

PROVIDER_MAP = {
    "claude": ClaudeOcrProvider,
    "openai": OpenAIOcrProvider,
    "gemini": GeminiOcrProvider,
    "mistral": MistralOcrProvider,
    "ollama": OllamaOcrProvider,
    "custom": CustomOcrProvider,
}


async def _resolve_credentials(db: AsyncSession, model: OcrModel) -> tuple[str, str, str]:
    """Returns (api_key, base_url, provider_type)."""
    api_key = model.api_key or ""
    base_url = model.base_url or ""
    provider_type = model.provider  # fallback: use model.provider as type
    result = await db.execute(
        select(ProviderSetting).where(ProviderSetting.id == model.provider)
    )
    ps = result.scalar_one_or_none()
    if ps:
        provider_type = ps.provider_type or model.provider
        if not api_key:
            api_key = ps.api_key or ""
        if not base_url:
            base_url = ps.base_url or ""
    return api_key.strip(), base_url.strip(), provider_type


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


# Config keys used internally, must NOT be passed to provider APIs
_INTERNAL_CONFIG_KEYS = {"postprocessor"}


def get_provider(provider_name: str, model_id: str, api_key: str = "", base_url: str = "", extra_config: dict | None = None) -> OcrProvider:
    provider_cls = PROVIDER_MAP.get(provider_name)
    if not provider_cls:
        raise ValueError(f"Unknown provider: {provider_name}")
    # Strip internal keys that providers don't understand
    if extra_config:
        extra_config = {k: v for k, v in extra_config.items() if k not in _INTERNAL_CONFIG_KEYS}
    return provider_cls(model_id=model_id, api_key=api_key, base_url=base_url, extra_config=extra_config)


async def select_random_models(db: AsyncSession, count: int = 2) -> list[OcrModel]:
    result = await db.execute(select(OcrModel).where(OcrModel.is_active == True))
    models = list(result.scalars().all())
    if len(models) < count:
        raise ValueError(f"Not enough active models. Need {count}, have {len(models)}")

    # Weighted selection: models with fewer battles get higher weight
    max_battles = max((m.total_battles for m in models), default=0)
    weights = [max_battles - m.total_battles + 1 for m in models]

    # Pick first model weighted
    first = random.choices(models, weights=weights, k=1)[0]

    # Pick second model from remaining (also weighted)
    remaining = [m for m in models if m.id != first.id]
    remaining_weights = [max_battles - m.total_battles + 1 for m in remaining]
    second = random.choices(remaining, weights=remaining_weights, k=1)[0]

    return [first, second]


async def run_ocr(
    model: OcrModel,
    image_data: bytes,
    mime_type: str,
    db: AsyncSession | None = None,
    prompt_override: str | None = None,
    temperature_override: float | None = None,
) -> OcrResult:
    api_key = model.api_key or ""
    base_url = model.base_url or ""
    provider_type = model.provider
    prompt = ""

    if db:
        api_key, base_url, provider_type = await _resolve_credentials(db, model)
        prompt = await _resolve_prompt(db, model)

    if prompt_override is not None:
        prompt = prompt_override

    extra_config = dict(model.config) if isinstance(model.config, dict) else {}
    if temperature_override is not None:
        extra_config["temperature"] = temperature_override

    provider = get_provider(provider_type, model.model_id, api_key, base_url, extra_config)

    # Resolve postprocessor from model config
    postprocessor_name = extra_config.get("postprocessor", "")

    # Handle PDF: split into pages, OCR each, merge
    if mime_type == "application/pdf":
        result = await _run_ocr_pdf(provider, image_data, prompt)
    else:
        result = await provider.process_image(image_data, mime_type, prompt)

    # Global post-processing: strip code fences (```markdown ... ```)
    if result.text and not result.error:
        cleaned = strip_code_fences(result.text)
        # Model-specific post-processing
        if postprocessor_name:
            cleaned = apply_postprocessor(postprocessor_name, cleaned)
        result = OcrResult(
            text=cleaned,
            latency_ms=result.latency_ms,
            error=result.error,
        )

    return result


async def _run_ocr_pdf(provider: OcrProvider, pdf_data: bytes, prompt: str) -> OcrResult:
    """Split PDF into page images, OCR each page in parallel, merge results."""
    start = time.time()
    try:
        pages = await pdf_to_images_async(pdf_data)
    except Exception as e:
        return OcrResult(text="", latency_ms=0, error=f"PDF conversion failed: {e}")

    if not pages:
        return OcrResult(text="", latency_ms=0, error="PDF has no pages")

    # Process first page alone to fail fast on auth/config errors
    first_result = await provider.process_image(pages[0][0], pages[0][1], prompt)
    if first_result.error:
        latency = int((time.time() - start) * 1000)
        return OcrResult(text="", latency_ms=latency, error=first_result.error)

    # First page succeeded — process remaining pages in parallel
    if len(pages) > 1:
        remaining_tasks = [provider.process_image(img_bytes, img_mime, prompt) for img_bytes, img_mime in pages[1:]]
        remaining_results = await asyncio.gather(*remaining_tasks, return_exceptions=True)
        results = [first_result, *remaining_results]
    else:
        results = [first_result]

    merged_parts = []
    errors = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"Page {idx + 1}: {result}")
        elif result.error:
            errors.append(f"Page {idx + 1}: {result.error}")
        else:
            header = f"\n\n---\n\n<!-- Page {idx + 1} -->\n\n" if idx > 0 else ""
            text = strip_code_fences(result.text).strip()
            merged_parts.append(header + text)

    total_latency = int((time.time() - start) * 1000)
    merged_text = "".join(merged_parts)
    error_msg = "; ".join(errors) if errors else None

    return OcrResult(text=merged_text, latency_ms=total_latency, error=error_msg)


def get_postprocessor_name(model: OcrModel) -> str:
    """Return the postprocessor name from model config, or empty string."""
    extra_config = dict(model.config) if isinstance(model.config, dict) else {}
    return extra_config.get("postprocessor", "")


async def _strip_stream_fences(
    chunks: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
    """Strip opening/closing code fences from a token stream in real time.

    - Head: buffers initial tokens; if first line is ```markdown/```/etc, skips it.
    - Tail: holds back last few chars; if stream ends with ```, strips it.
    """
    head = ""
    head_resolved = False
    fence_opened = False
    pending = ""

    async for chunk in chunks:
        if not head_resolved:
            head += chunk
            if "\n" in head:
                nl = head.index("\n")
                first_line = head[:nl].strip()
                if re.match(r"^```\w*$", first_line):
                    fence_opened = True
                    pending = head[nl + 1:]
                else:
                    pending = head
                head_resolved = True
            elif len(head) > 20:
                # No newline in first 20 chars — not a fence
                head_resolved = True
                pending = head
            continue

        # Stream through with a small tail buffer for closing fence detection
        pending += chunk
        if len(pending) > 6:
            yield pending[:-6]
            pending = pending[-6:]

    # Flush
    if not head_resolved:
        pending = head

    if fence_opened and pending.rstrip().endswith("```"):
        cleaned = pending.rstrip()[:-3]
        if cleaned:
            yield cleaned
    elif pending:
        yield pending


async def run_ocr_stream(
    model: OcrModel,
    image_data: bytes,
    mime_type: str,
    db: AsyncSession | None = None,
    prompt_override: str | None = None,
    temperature_override: float | None = None,
) -> AsyncGenerator[str, None]:
    """Yield text chunks as the provider streams tokens.

    Streams for all inputs including PDFs (page-by-page sequential).
    Code fences are stripped in real-time per page/image.
    Model-specific postprocessors are NOT applied here — callers handle that
    separately via replace events after full collection.
    """
    api_key = model.api_key or ""
    base_url = model.base_url or ""
    provider_type = model.provider
    prompt = ""

    if db:
        api_key, base_url, provider_type = await _resolve_credentials(db, model)
        prompt = await _resolve_prompt(db, model)

    if prompt_override is not None:
        prompt = prompt_override

    extra_config = dict(model.config) if isinstance(model.config, dict) else {}
    if temperature_override is not None:
        extra_config["temperature"] = temperature_override

    provider = get_provider(provider_type, model.model_id, api_key, base_url, extra_config)

    if mime_type == "application/pdf":
        pages = await pdf_to_images_async(pdf_data=image_data)
        if not pages:
            raise RuntimeError("PDF has no pages")
        for page_idx, (page_bytes, page_mime) in enumerate(pages):
            if page_idx > 0:
                yield f"\n\n---\n\n<!-- Page {page_idx + 1} -->\n\n"
            raw = provider.process_image_stream(page_bytes, page_mime, prompt)
            async for chunk in _strip_stream_fences(raw):
                yield chunk
    else:
        raw = provider.process_image_stream(image_data, mime_type, prompt)
        async for chunk in _strip_stream_fences(raw):
            yield chunk
