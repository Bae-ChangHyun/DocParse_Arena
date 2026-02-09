"""Convert PDF files to a list of page images using PyMuPDF (fitz)."""
import io
import fitz  # PyMuPDF


def pdf_to_images(pdf_data: bytes, dpi: float = 216.0) -> list[tuple[bytes, str]]:
    """Convert PDF bytes to a list of (png_bytes, mime_type) per page."""
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pages = []
    for page in doc:
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        png_bytes = pixmap.tobytes("png")
        pages.append((png_bytes, "image/png"))
    doc.close()
    return pages
