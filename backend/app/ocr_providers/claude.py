import base64
import time
import anthropic
from app.ocr_providers.base import OcrProvider, DEFAULT_OCR_PROMPT
from app.models.schemas import OcrResult


class ClaudeOcrProvider(OcrProvider):
    def __init__(self, model_id: str = "claude-sonnet-4-20250514", api_key: str = "", base_url: str = ""):
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = anthropic.AsyncAnthropic(**kwargs)
        self.model_id = model_id

    async def process_image(self, image_data: bytes, mime_type: str, prompt: str = "") -> OcrResult:
        system_prompt = prompt or DEFAULT_OCR_PROMPT
        start = time.time()
        try:
            b64_image = base64.b64encode(image_data).decode("utf-8")
            response = await self.client.messages.create(
                model=self.model_id,
                max_tokens=4096,
                system=system_prompt,
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
