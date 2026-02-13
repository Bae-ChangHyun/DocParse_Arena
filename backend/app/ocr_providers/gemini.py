import time
from collections.abc import AsyncGenerator
from google import genai
from google.genai import types
from app.ocr_providers.base import OcrProvider, DEFAULT_OCR_PROMPT
from app.models.schemas import OcrResult
from app.utils.error_sanitizer import sanitize_error


class GeminiOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "gemini-2.0-flash", api_key: str = "", base_url: str = "", extra_config: dict | None = None):
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        self.client = genai.Client(**kwargs)
        self.model_id = model_id
        self.extra_config = extra_config or {}

    def _build_contents(self, image_data: bytes, mime_type: str) -> list:
        return [
            types.Part.from_bytes(data=image_data, mime_type=mime_type),
            "Convert this document to markdown.",
        ]

    async def process_image(self, image_data: bytes, mime_type: str, prompt: str = "") -> OcrResult:
        system_prompt = prompt or DEFAULT_OCR_PROMPT
        start = time.time()
        try:
            config_kwargs = {"system_instruction": system_prompt}
            config_kwargs.update(self.extra_config)
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                config=types.GenerateContentConfig(**config_kwargs),
                contents=self._build_contents(image_data, mime_type),
            )
            latency = int((time.time() - start) * 1000)
            text = response.text or ""
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=sanitize_error(e))

    async def process_image_stream(
        self, image_data: bytes, mime_type: str, prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        system_prompt = prompt or DEFAULT_OCR_PROMPT
        config_kwargs = {"system_instruction": system_prompt}
        config_kwargs.update(self.extra_config)
        async for chunk in self.client.aio.models.generate_content_stream(
            model=self.model_id,
            config=types.GenerateContentConfig(**config_kwargs),
            contents=self._build_contents(image_data, mime_type),
        ):
            if chunk.text:
                yield chunk.text
