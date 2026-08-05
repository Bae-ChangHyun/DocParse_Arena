import time
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types

from app.models.schemas import OcrResult
from app.ocr_providers.base import DEFAULT_OCR_USER_PROMPT, OcrProvider
from app.utils.error_sanitizer import sanitize_error


class GeminiOcrProvider(OcrProvider):
    def __init__(
        self,
        model_id: str = "gemini-2.0-flash",
        api_key: str = "",
        base_url: str = "",
        extra_config: dict | None = None,
    ):
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        self.client = genai.Client(**kwargs)
        self.model_id = model_id
        self.extra_config = extra_config or {}

    def _build_contents(self, image_data: bytes, mime_type: str, user_prompt: str) -> list:
        return [
            types.Part.from_bytes(data=image_data, mime_type=mime_type),
            user_prompt or DEFAULT_OCR_USER_PROMPT,
        ]

    async def process_image(
        self, image_data: bytes, mime_type: str, prompt: str = "", user_prompt: str = ""
    ) -> OcrResult:
        start = time.time()
        try:
            config_kwargs = dict(self.extra_config)
            if prompt:
                config_kwargs["system_instruction"] = prompt
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                config=types.GenerateContentConfig(**config_kwargs),
                contents=self._build_contents(image_data, mime_type, user_prompt),
            )
            latency = int((time.time() - start) * 1000)
            text = response.text or ""
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=sanitize_error(e))

    async def process_image_stream(
        self, image_data: bytes, mime_type: str, prompt: str = "", user_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        config_kwargs = dict(self.extra_config)
        if prompt:
            config_kwargs["system_instruction"] = prompt
        async for chunk in self.client.aio.models.generate_content_stream(
            model=self.model_id,
            config=types.GenerateContentConfig(**config_kwargs),
            contents=self._build_contents(image_data, mime_type, user_prompt),
        ):
            if chunk.text:
                yield chunk.text
