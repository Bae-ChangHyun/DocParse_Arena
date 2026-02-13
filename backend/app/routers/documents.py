import os
import random
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.utils.mime import ALLOWED_EXTENSIONS, extension_to_mime
from app.utils.file_validation import validate_file_content

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/random")
async def get_random_document():
    settings = get_settings()
    docs_dir = settings.sample_docs_dir

    if not os.path.exists(docs_dir):
        raise HTTPException(status_code=404, detail="Sample documents directory not found")

    files = [
        f for f in os.listdir(docs_dir)
        if os.path.isfile(os.path.join(docs_dir, f))
        and os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    ]

    if not files:
        raise HTTPException(status_code=404, detail="No sample documents found")

    chosen = random.choice(files)
    return FileResponse(
        os.path.join(docs_dir, chosen),
        filename=chosen,
        headers={"X-Document-Name": chosen},
    )


@router.get("/list")
async def list_documents():
    settings = get_settings()
    docs_dir = settings.sample_docs_dir

    if not os.path.exists(docs_dir):
        return {"documents": []}

    files = [
        {
            "name": f,
            "path": f"/api/documents/file/{f}",
            "extension": os.path.splitext(f)[1].lower(),
        }
        for f in sorted(os.listdir(docs_dir))
        if os.path.isfile(os.path.join(docs_dir, f))
        and os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    ]
    return {"documents": files}


@router.get("/file/{filename}")
async def get_document(filename: str):
    """Serve pre-seeded sample documents only (admin-managed)."""
    settings = get_settings()
    filepath = os.path.join(settings.sample_docs_dir, filename)

    if not os.path.realpath(filepath).startswith(os.path.realpath(settings.sample_docs_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(filename)[1].lower()
    media_type = extension_to_mime(ext)
    return FileResponse(filepath, media_type=media_type)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Validate an uploaded file without storing it on disk.

    Returns metadata only — the file bytes are held in memory
    by the battle endpoint, not persisted.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    settings = get_settings()
    content = await file.read()
    if len(content) > settings.max_upload_size:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    if not validate_file_content(content, ext):
        raise HTTPException(status_code=400, detail="File content does not match its extension")

    return {
        "original_name": file.filename,
        "size": len(content),
        "extension": ext,
    }
