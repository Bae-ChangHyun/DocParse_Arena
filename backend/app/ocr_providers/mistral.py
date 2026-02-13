import base64
import time
from collections.abc import AsyncGenerator
from mistralai import Mistral
from app.ocr_providers.base import OcrProvider, DEFAULT_OCR_PROMPT
from app.models.schemas import OcrResult
from app.utils.error_sanitizer import sanitize_error


class MistralOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "mistral-small-latest", api_key: str = "", base_url: str = "", extra_config: dict | None = None):
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["server_url"] = base_url
        self.client = Mistral(**kwargs)
        self.model_id = model_id
        self.extra_config = extra_config or {}

    def _build_messages(self, b64_image: str, mime_type: str, prompt: str) -> list:
        system_prompt = prompt or DEFAULT_OCR_PROMPT
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": f"data:{mime_type};base64,{b64_image}",
                    },
                    {
                        "type": "text",
                        "text": "Convert this document to markdown.",
                    },
                ],
            },
        ]

    async def process_image(self, image_data: bytes, mime_type: str, prompt: str = "") -> OcrResult:
        start = time.time()
        try:
            b64_image = base64.b64encode(image_data).decode("utf-8")
            api_kwargs = dict(self.extra_config)
            response = await self.client.chat.complete_async(
                model=self.model_id,
                messages=self._build_messages(b64_image, mime_type, prompt),
                **api_kwargs,
            )
            latency = int((time.time() - start) * 1000)
            text = response.choices[0].message.content or ""
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=sanitize_error(e))

    async def process_image_stream(
        self, image_data: bytes, mime_type: str, prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        b64_image = base64.b64encode(image_data).decode("utf-8")
        api_kwargs = dict(self.extra_config)
        response = await self.client.chat.stream_async(
            model=self.model_id,
            messages=self._build_messages(b64_image, mime_type, prompt),
            **api_kwargs,
        )
        async for event in response:
            content = event.data.choices[0].delta.content if event.data.choices else None
            if content:
                yield content
