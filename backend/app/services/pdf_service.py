"""Convert PDF files to a list of page images using PyMuPDF (fitz)."""
import io
import asyncio
import fitz  # PyMuPDF


def pdf_to_images(pdf_data: bytes, dpi: float = 216.0, max_pages: int = 50) -> list[tuple[bytes, str]]:
    """Convert PDF bytes to a list of (png_bytes, mime_type) per page."""
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    if doc.page_count > max_pages:
        doc.close()
        raise ValueError(f"PDF has {doc.page_count} pages (max {max_pages})")
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pages = []
    for page in doc:
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        png_bytes = pixmap.tobytes("png")
        pages.append((png_bytes, "image/png"))
    doc.close()
    return pages


async def pdf_to_images_async(pdf_data: bytes, dpi: float = 216.0, max_pages: int = 50) -> list[tuple[bytes, str]]:
    """Async wrapper — offloads CPU-heavy PDF rendering to a thread."""
    return await asyncio.to_thread(pdf_to_images, pdf_data, dpi, max_pages)
