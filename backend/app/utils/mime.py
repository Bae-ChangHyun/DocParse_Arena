MIME_MAP: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
}

ALLOWED_EXTENSIONS: set[str] = set(MIME_MAP.keys())


def extension_to_mime(ext: str, default: str = "application/octet-stream") -> str:
    return MIME_MAP.get(ext.lower(), default)
