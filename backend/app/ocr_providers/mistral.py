import base64
import time
from mistralai import Mistral
from app.ocr_providers.base import OcrProvider, OCR_SYSTEM_PROMPT
from app.models.schemas import OcrResult
from app.config import get_settings


class MistralOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "mistral-small-latest"):
        settings = get_settings()
        self.client = Mistral(api_key=settings.mistral_api_key)
        self.model_id = model_id

    async def process_image(self, image_data: bytes, mime_type: str) -> OcrResult:
        start = time.time()
        try:
            b64_image = base64.b64encode(image_data).decode("utf-8")
            response = await self.client.chat.complete_async(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": OCR_SYSTEM_PROMPT},
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
                ],
            )
            latency = int((time.time() - start) * 1000)
            text = response.choices[0].message.content or ""
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=str(e))
