import base64
import time
import anthropic
from app.ocr_providers.base import OcrProvider, OCR_SYSTEM_PROMPT
from app.models.schemas import OcrResult
from app.config import get_settings


class ClaudeOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "claude-sonnet-4-20250514"):
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model_id = model_id

    async def process_image(self, image_data: bytes, mime_type: str) -> OcrResult:
        start = time.time()
        try:
            b64_image = base64.b64encode(image_data).decode("utf-8")
            response = await self.client.messages.create(
                model=self.model_id,
                max_tokens=4096,
                system=OCR_SYSTEM_PROMPT,
                messages=[
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
                ],
            )
            latency = int((time.time() - start) * 1000)
            text = response.content[0].text
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=str(e))
