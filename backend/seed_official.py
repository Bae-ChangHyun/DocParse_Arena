"""Seed official benchmark datasets as ground-truth Collections.

Scans the datasets downloaded by ``bench/download_datasets.py`` under
``settings.benchmarks_dir`` and registers each as a Collection (``kind`` =
``omnidocbench`` / ``olmocr_bench``) with one CollectionDocument per page/PDF,
carrying the ground-truth mapping key in ``gt_ref``.

Idempotent: re-running refreshes documents for an existing official collection
without duplicating it.

Run from the backend dir:
    uv run python seed_official.py               # both, if present
    uv run python seed_official.py --only omnidocbench
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from loguru import logger
from sqlalchemy import delete, select

from app.config import get_settings
from app.models.database import (
    Collection,
    CollectionDocument,
    async_session,
    init_db,
)

OFFICIAL_NAMES = {
    "omnidocbench": "OmniDocBench (official)",
    "olmocr_bench": "olmOCR-Bench (official)",
}


def _find_omnidocbench_gt(root: str) -> str | None:
    """Locate the OmniDocBench ground-truth JSON (a list of page entries)."""
    candidates = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".json") and "OmniDocBench" in f:
                candidates.append(os.path.join(dirpath, f))
    # Prefer the top-level annotation (shortest path, contains "page_info")
    candidates.sort(key=len)
    for path in candidates:
        try:
            data = json.load(open(path))
        except Exception:
            continue
        if isinstance(data, list) and data and isinstance(data[0], dict) and "page_info" in data[0]:
            return path
    return None


def _scan_omnidocbench(root: str) -> list[dict]:
    """Return [{stored_path, gt_ref, original_name, mime_type, size}] for each page image."""
    gt_path = _find_omnidocbench_gt(root)
    if gt_path is None:
        logger.warning(f"OmniDocBench GT JSON not found under {root}")
        return []
    data = json.load(open(gt_path))

    # Build an index of available image files by basename
    image_index: dict[str, str] = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                image_index.setdefault(f, os.path.join(dirpath, f))

    benchmarks_dir = get_settings().benchmarks_dir
    docs = []
    for entry in data:
        img_key = entry.get("page_info", {}).get("image_path")
        if not img_key:
            continue
        abs_img = image_index.get(os.path.basename(img_key))
        if abs_img is None or not os.path.isfile(abs_img):
            continue
        stored_rel = os.path.relpath(abs_img, benchmarks_dir)
        ext = os.path.splitext(abs_img)[1].lower()
        docs.append({
            "stored_path": stored_rel,
            "gt_ref": img_key,
            "original_name": os.path.basename(img_key),
            "mime_type": "image/png" if ext == ".png" else "image/jpeg",
            "size": os.path.getsize(abs_img),
        })
    return docs


def _scan_olmocr(root: str) -> list[dict]:
    """Return document rows for each PDF under an olmOCR-bench pdfs/ folder."""
    pdfs_dirs = []
    for dirpath, dirs, _files in os.walk(root):
        if os.path.basename(dirpath) == "pdfs":
            pdfs_dirs.append(dirpath)
    if not pdfs_dirs:
        logger.warning(f"olmOCR-bench pdfs/ folder not found under {root}")
        return []

    benchmarks_dir = get_settings().benchmarks_dir
    docs = []
    for pdfs_dir in pdfs_dirs:
        for dirpath, _dirs, files in os.walk(pdfs_dir):
            for f in files:
                if not f.lower().endswith(".pdf"):
                    continue
                abs_pdf = os.path.join(dirpath, f)
                gt_ref = os.path.relpath(abs_pdf, pdfs_dir)  # bench references this
                stored_rel = os.path.relpath(abs_pdf, benchmarks_dir)
                docs.append({
                    "stored_path": stored_rel,
                    "gt_ref": gt_ref,
                    "original_name": gt_ref,
                    "mime_type": "application/pdf",
                    "size": os.path.getsize(abs_pdf),
                })
    return docs


SCANNERS = {"omnidocbench": _scan_omnidocbench, "olmocr_bench": _scan_olmocr}


async def seed_kind(kind: str) -> None:
    settings = get_settings()
    root = os.path.join(settings.benchmarks_dir, kind)
    if not os.path.isdir(root):
        logger.warning(f"[{kind}] dataset dir not found: {root} — run download_datasets.py first")
        return

    docs = SCANNERS[kind](root)
    if not docs:
        logger.warning(f"[{kind}] no documents discovered under {root}")
        return

    async with async_session() as db:
        result = await db.execute(select(Collection).where(Collection.kind == kind))
        collection = result.scalar_one_or_none()
        if collection is None:
            collection = Collection(name=OFFICIAL_NAMES[kind], kind=kind,
                                    description=f"Official {kind} dataset")
            db.add(collection)
            await db.flush()
        else:
            # Refresh: drop existing documents, re-add
            await db.execute(
                delete(CollectionDocument).where(
                    CollectionDocument.collection_id == collection.id
                )
            )

        for d in docs:
            db.add(CollectionDocument(collection_id=collection.id, **d))
        await db.commit()
    logger.success(f"[{kind}] seeded {len(docs)} documents")


async def main(only: str | None) -> None:
    await init_db()
    kinds = [only] if only else list(SCANNERS.keys())
    for kind in kinds:
        await seed_kind(kind)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=list(SCANNERS.keys()))
    args = ap.parse_args()
    asyncio.run(main(args.only))
