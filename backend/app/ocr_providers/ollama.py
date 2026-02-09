import base64
import time
import httpx
from app.ocr_providers.base import OcrProvider, DEFAULT_OCR_PROMPT
from app.models.schemas import OcrResult


class OllamaOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "llava", api_key: str = "", base_url: str = "", extra_config: dict | None = None):
        self.base_url = base_url or "http://localhost:11434"
        self.model_id = model_id
        self.extra_config = extra_config or {}

    async def process_image(self, image_data: bytes, mime_type: str, prompt: str = "") -> OcrResult:
        system_prompt = prompt or DEFAULT_OCR_PROMPT
        start = time.time()
        try:
            b64_image = base64.b64encode(image_data).decode("utf-8")
            options = dict(self.extra_config)
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_id,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": "Convert this document to markdown.",
                                "images": [b64_image],
                            },
                        ],
                        "stream": False,
                        "options": options,
                    },
                )
                response.raise_for_status()
                data = response.json()
            latency = int((time.time() - start) * 1000)
            text = data.get("message", {}).get("content", "")
            return OcrResult(text=text, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return OcrResult(text="", latency_ms=latency, error=str(e))
