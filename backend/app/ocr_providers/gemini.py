import time
from google import genai
from google.genai import types
from app.ocr_providers.base import OcrProvider, DEFAULT_OCR_PROMPT
from app.models.schemas import OcrResult


class GeminiOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "gemini-2.0-flash", api_key: str = "", base_url: str = "", extra_config: dict | None = None):
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        self.client = genai.Client(**kwargs)
        self.model_id = model_id
        self.extra_config = extra_config or {}

    async def process_image(self, image_data: bytes, mime_type: str, prompt: str = "") -> OcrResult:
        system_prompt = prompt or DEFAULT_OCR_PROMPT
        start = time.time()
        try:
            config_kwargs = {"system_instruction": system_prompt}
            config_kwargs.update(self.extra_config)
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                config=types.GenerateContentConfig(**config_kwargs),
                contents=[
                    types.Part.from_bytes(data=image_data, mime_type=mime_type),
                    "Convert this document to markdown.",
                ],
            )
            latency = int((time.time() - start) * 1000)
            text = response.text or ""
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=str(e))
