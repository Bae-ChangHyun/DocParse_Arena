"""Convert PDF files to a list of page images using pypdfium2."""
import asyncio

import pypdfium2 as pdfium

from app.services.image_utils import downscale_pil_to_png


def pdf_to_images(
    pdf_data: bytes,
    dpi: float = 216.0,
    max_pages: int = 50,
    image_setting: dict | None = None,
) -> list[tuple[bytes, str]]:
    """Convert PDF bytes to a list of (png_bytes, mime_type) per page.

    Pages are rendered at the given DPI, then optionally downscaled per
    ``image_setting`` (see image_utils.normalize_image_setting).
    """
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
        png_bytes = downscale_pil_to_png(pil_image, image_setting)
        pages.append((png_bytes, "image/png"))
    pdf.close()
    return pages


async def pdf_to_images_async(
    pdf_data: bytes,
    dpi: float = 216.0,
    max_pages: int = 50,
    image_setting: dict | None = None,
) -> list[tuple[bytes, str]]:
    """Async wrapper — offloads CPU-heavy PDF rendering to a thread."""
    return await asyncio.to_thread(pdf_to_images, pdf_data, dpi, max_pages, image_setting)
