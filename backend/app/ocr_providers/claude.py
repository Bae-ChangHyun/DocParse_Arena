import base64
import time
from collections.abc import AsyncGenerator
import anthropic
from app.ocr_providers.base import OcrProvider, DEFAULT_OCR_PROMPT
from app.models.schemas import OcrResult
from app.utils.error_sanitizer import sanitize_error


class ClaudeOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "claude-sonnet-4-20250514", api_key: str = "", base_url: str = "", extra_config: dict | None = None):
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = anthropic.AsyncAnthropic(**kwargs)
        self.model_id = model_id
        self.extra_config = extra_config or {}

    def _build_messages(self, b64_image: str, mime_type: str) -> list:
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": b64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Convert this document to markdown.",
                    },
                ],
            }
        ]

    async def process_image(self, image_data: bytes, mime_type: str, prompt: str = "") -> OcrResult:
        system_prompt = prompt or DEFAULT_OCR_PROMPT
        start = time.time()
        try:
            b64_image = base64.b64encode(image_data).decode("utf-8")
            api_kwargs = {"max_tokens": 4096}
            api_kwargs.update(self.extra_config)
            response = await self.client.messages.create(
                model=self.model_id,
                system=system_prompt,
                messages=self._build_messages(b64_image, mime_type),
                **api_kwargs,
            )
            latency = int((time.time() - start) * 1000)
            text = response.content[0].text
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=sanitize_error(e))

    async def process_image_stream(
        self, image_data: bytes, mime_type: str, prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        system_prompt = prompt or DEFAULT_OCR_PROMPT
        b64_image = base64.b64encode(image_data).decode("utf-8")
        api_kwargs = {"max_tokens": 4096}
        api_kwargs.update(self.extra_config)
        async with self.client.messages.stream(
            model=self.model_id,
            system=system_prompt,
            messages=self._build_messages(b64_image, mime_type),
            **api_kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text
