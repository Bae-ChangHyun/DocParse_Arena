import base64
import time
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.models.schemas import OcrResult
from app.ocr_providers.base import DEFAULT_OCR_USER_PROMPT, OcrProvider
from app.ocr_providers.openai_compat import extract_message_text, iter_think_wrapped
from app.utils.error_sanitizer import sanitize_error


class CustomOcrProvider(OcrProvider):
    """OpenAI-compatible custom endpoint (vLLM, LiteLLM, LocalAI, etc.)."""

    def __init__(
        self,
        model_id: str,
        api_key: str = "",
        base_url: str = "",
        extra_config: dict | None = None,
    ):
        if not base_url:
            raise ValueError("Custom provider requires base_url")
        self.client = AsyncOpenAI(
            api_key=api_key or "no-key",
            base_url=base_url,
        )
        self.model_id = model_id
        self.extra_config = extra_config or {}

    def _build_messages(self, b64_image: str, mime_type: str, prompt: str, user_prompt: str) -> list:
        messages = []
        if prompt:
            messages.append({"role": "system", "content": prompt})
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}",
                        },
                    },
                    {
                        "type": "text",
                        "text": user_prompt or DEFAULT_OCR_USER_PROMPT,
                    },
                ],
            }
        )
        return messages

    async def process_image(
        self, image_data: bytes, mime_type: str, prompt: str = "", user_prompt: str = ""
    ) -> OcrResult:
        start = time.time()
        try:
            b64_image = base64.b64encode(image_data).decode("utf-8")
            api_kwargs = dict(self.extra_config)
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=self._build_messages(b64_image, mime_type, prompt, user_prompt),
                **api_kwargs,
            )
            latency = int((time.time() - start) * 1000)
            text = extract_message_text(response.choices[0].message)
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=sanitize_error(e))

    async def process_image_stream(
        self, image_data: bytes, mime_type: str, prompt: str = "", user_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        b64_image = base64.b64encode(image_data).decode("utf-8")
        api_kwargs = dict(self.extra_config)
        stream = await self.client.chat.completions.create(
            model=self.model_id,
            messages=self._build_messages(b64_image, mime_type, prompt, user_prompt),
            stream=True,
            **api_kwargs,
        )
        async for piece in iter_think_wrapped(stream):
            yield piece
