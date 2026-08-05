from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.models.schemas import OcrResult

DEFAULT_OCR_PROMPT = """You are a document OCR assistant.
Convert the given document image into well-formatted markdown text.
Rules:
- Preserve the document structure (headings, lists, tables, etc.)
- Use proper markdown syntax
- For tables, use markdown table format
- Preserve any special formatting (bold, italic, etc.)
- For mathematical formulas, use LaTeX notation with $...$ for inline and $$...$$ for display
- Output only the converted markdown content, no explanations"""

# Default text placed in the user turn alongside the image. Used when a model
# has no model-specific user prompt configured. Models like PaddleOCR-VL expect
# a task tag (e.g. "OCR:") here instead — set it via the per-model user prompt.
DEFAULT_OCR_USER_PROMPT = "Convert this document to markdown."


class OcrProvider(ABC):
    extra_config: dict = {}

    @abstractmethod
    async def process_image(
        self, image_data: bytes, mime_type: str, prompt: str = "", user_prompt: str = ""
    ) -> OcrResult:
        """Process an image and return OCR result as markdown text.

        ``prompt`` is the system prompt (omitted entirely when empty).
        ``user_prompt`` is the text placed in the user turn next to the image
        (falls back to ``DEFAULT_OCR_USER_PROMPT`` when empty).
        """
        pass

    async def process_image_stream(
        self, image_data: bytes, mime_type: str, prompt: str = "", user_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """Stream OCR result token-by-token. Yields text chunks.

        Default implementation falls back to process_image() and yields the
        full result as a single chunk, so providers that don't support
        streaming still work without overriding this method.
        """
        result = await self.process_image(image_data, mime_type, prompt, user_prompt)
        if result.error:
            raise RuntimeError(result.error)
        yield result.text
