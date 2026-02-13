"""Convert PDF files to a list of page images using pypdfium2."""
import io
import asyncio
import pypdfium2 as pdfium


def pdf_to_images(pdf_data: bytes, dpi: float = 216.0, max_pages: int = 50) -> list[tuple[bytes, str]]:
    """Convert PDF bytes to a list of (png_bytes, mime_type) per page."""
    pdf = pdfium.PdfDocument(pdf_data)
    n_pages = len(pdf)
    if n_pages > max_pages:
        pdf.close()
        raise ValueError(
            f"PDF has {n_pages} pages, exceeding the maximum of {max_pages}. "
            "Please reduce the number of pages."
        )
    scale = dpi / 72.0
    pages = []
    for i in range(n_pages):
        page = pdf[i]
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        pages.append((buf.getvalue(), "image/png"))
    pdf.close()
    return pages


async def pdf_to_images_async(pdf_data: bytes, dpi: float = 216.0, max_pages: int = 50) -> list[tuple[bytes, str]]:
    """Async wrapper — offloads CPU-heavy PDF rendering to a thread."""
    return await asyncio.to_thread(pdf_to_images, pdf_data, dpi, max_pages)
