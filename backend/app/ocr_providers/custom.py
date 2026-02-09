import base64
import time
from openai import AsyncOpenAI
from app.ocr_providers.base import OcrProvider, OCR_SYSTEM_PROMPT
from app.models.schemas import OcrResult


class CustomOcrProvider(OcrProvider):
    """OpenAI-compatible custom endpoint (vLLM, LiteLLM, LocalAI, etc.)."""

    def __init__(self, model_id: str, api_key: str = "", base_url: str = ""):
        if not base_url:
            raise ValueError("Custom provider requires base_url")
        self.client = AsyncOpenAI(
            api_key=api_key or "no-key",
            base_url=base_url,
        )
        self.model_id = model_id

    async def process_image(self, image_data: bytes, mime_type: str) -> OcrResult:
        start = time.time()
        try:
            b64_image = base64.b64encode(image_data).decode("utf-8")
            response = await self.client.chat.completions.create(
                model=self.model_id,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": OCR_SYSTEM_PROMPT},
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
                                "text": "Convert this document to markdown.",
                            },
                        ],
                    },
                ],
            )
            latency = int((time.time() - start) * 1000)
            text = response.choices[0].message.content or ""
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=str(e))
