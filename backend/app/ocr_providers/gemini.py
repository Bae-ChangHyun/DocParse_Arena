import time
import google.generativeai as genai
from app.ocr_providers.base import OcrProvider, OCR_SYSTEM_PROMPT
from app.models.schemas import OcrResult
from app.config import get_settings


class GeminiOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "gemini-2.0-flash"):
        settings = get_settings()
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(
            model_name=model_id,
            system_instruction=OCR_SYSTEM_PROMPT,
        )
        self.model_id = model_id

    async def process_image(self, image_data: bytes, mime_type: str) -> OcrResult:
        start = time.time()
        try:
            image_part = {"mime_type": mime_type, "data": image_data}
            response = await self.model.generate_content_async(
                [image_part, "Convert this document to markdown."]
            )
            latency = int((time.time() - start) * 1000)
            text = response.text or ""
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=str(e))
