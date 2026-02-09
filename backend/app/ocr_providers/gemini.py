import time
import google.generativeai as genai
from app.ocr_providers.base import OcrProvider, DEFAULT_OCR_PROMPT
from app.models.schemas import OcrResult


class GeminiOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "gemini-2.0-flash", api_key: str = "", base_url: str = ""):
        if api_key:
            genai.configure(api_key=api_key)
        self.model_id = model_id

    async def process_image(self, image_data: bytes, mime_type: str, prompt: str = "") -> OcrResult:
        system_prompt = prompt or DEFAULT_OCR_PROMPT
        start = time.time()
        try:
            model = genai.GenerativeModel(
                model_name=self.model_id,
                system_instruction=system_prompt,
            )
            image_part = {"mime_type": mime_type, "data": image_data}
            response = await model.generate_content_async(
                [image_part, "Convert this document to markdown."]
            )
            latency = int((time.time() - start) * 1000)
            text = response.text or ""
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=str(e))
