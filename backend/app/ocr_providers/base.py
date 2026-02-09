from abc import ABC, abstractmethod
from app.models.schemas import OcrResult


DEFAULT_OCR_PROMPT = """You are a document OCR assistant. Convert the given document image into well-formatted markdown text.
Rules:
- Preserve the document structure (headings, lists, tables, etc.)
- Use proper markdown syntax
- For tables, use markdown table format
- Preserve any special formatting (bold, italic, etc.)
- For mathematical formulas, use LaTeX notation with $...$ for inline and $$...$$ for display
- Output only the converted markdown content, no explanations"""


class OcrProvider(ABC):
    @abstractmethod
    async def process_image(self, image_data: bytes, mime_type: str, prompt: str = "") -> OcrResult:
        """Process an image and return OCR result as markdown text."""
        pass
