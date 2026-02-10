import os
import random
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".tiff", ".bmp"}


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
    settings = get_settings()
    filepath = os.path.join(settings.sample_docs_dir, filename)

    if not os.path.abspath(filepath).startswith(os.path.abspath(settings.sample_docs_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
    }
    media_type = mime_map.get(ext, "application/octet-stream")
    return FileResponse(filepath, media_type=media_type)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    settings = get_settings()
    os.makedirs(settings.sample_docs_dir, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.sample_docs_dir, safe_name)

    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    return {
        "filename": safe_name,
        "original_name": file.filename,
        "path": f"/api/documents/file/{safe_name}",
        "size": len(content),
    }
