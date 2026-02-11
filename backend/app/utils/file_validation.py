import magic

from app.utils.mime import MIME_MAP

# Reverse map: MIME type -> set of allowed extensions
_MIME_TO_EXTENSIONS: dict[str, set[str]] = {}
for _ext, _mime in MIME_MAP.items():
    _MIME_TO_EXTENSIONS.setdefault(_mime, set()).add(_ext)


def validate_file_content(data: bytes, claimed_extension: str) -> bool:
    """Validate file content matches its claimed extension using magic bytes.

    Returns True if valid, False if the content doesn't match the extension.
    """
    if not data:
        return False

    detected_mime = magic.from_buffer(data[:2048], mime=True)
    expected_mime = MIME_MAP.get(claimed_extension.lower())

    if not expected_mime:
        return False

    # Exact match
    if detected_mime == expected_mime:
        return True

    # Allow JPEG variants (image/jpeg matches .jpg and .jpeg)
    if expected_mime == "image/jpeg" and detected_mime == "image/jpeg":
        return True

    # TIFF can be detected as image/tiff
    if expected_mime == "image/tiff" and detected_mime == "image/tiff":
        return True

    return False
