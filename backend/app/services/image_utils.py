"""Image downscaling utilities (PIL thumbnail / LANCZOS → PNG bytes).

Mirrors the reference design: shrink-only, aspect ratio preserved, never upscale.
The threshold is read from the `image_processing` key in `app_settings`.
"""
import io

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AppSetting

IMAGE_SETTING_KEY = "image_processing"

DEFAULT_IMAGE_SETTING: dict = {
    "enabled": True,
    "max_width": 1024,
    "max_height": 1448,
}


def _coerce_int(value: object, fallback: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return fallback
    return n if n > 0 else fallback


def normalize_image_setting(raw: dict | None) -> dict:
    """Apply defaults + coerce types so callers can rely on the shape."""
    raw = raw or {}
    return {
        "enabled": bool(raw.get("enabled", DEFAULT_IMAGE_SETTING["enabled"])),
        "max_width": _coerce_int(raw.get("max_width"), DEFAULT_IMAGE_SETTING["max_width"]),
        "max_height": _coerce_int(raw.get("max_height"), DEFAULT_IMAGE_SETTING["max_height"]),
    }


async def get_image_setting(db: AsyncSession) -> dict:
    """Read the current image-processing setting from DB, with defaults."""
    result = await db.execute(select(AppSetting).where(AppSetting.key == IMAGE_SETTING_KEY))
    row = result.scalar_one_or_none()
    return normalize_image_setting(row.value if row else None)


def downscale_pil_to_png(image: Image.Image, setting: dict | None) -> bytes:
    """Shrink-only thumbnail using LANCZOS; always returns PNG bytes."""
    cfg = normalize_image_setting(setting)
    if cfg["enabled"]:
        image.thumbnail((cfg["max_width"], cfg["max_height"]), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def downscale_bytes_to_png(image_bytes: bytes, setting: dict | None) -> bytes:
    """Open raw image bytes, downscale if needed, return PNG bytes.

    Returns the original bytes unchanged if PIL cannot decode them
    (lets the provider surface a proper error for the user instead of us crashing).
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.load()
            if img.mode not in ("RGB", "RGBA", "L"):
                img = img.convert("RGB")
            return downscale_pil_to_png(img, setting)
    except Exception:
        return image_bytes
