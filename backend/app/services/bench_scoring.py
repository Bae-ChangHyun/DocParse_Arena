"""Score a batch run against an official benchmark's ground truth.

Exports each model's predictions into the folder layout the official scorer
expects, then invokes the vendored scorer wrappers (``bench/scorers/*.py``) as
subprocesses and returns normalized per-model scores. Heavy dependencies live in
the OmniDocBench Docker image / the ``bench/olmocr_env`` venv — never here.
"""

from __future__ import annotations

import asyncio
import glob
import json
import os
import re
import shutil

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import BatchRunItem, CollectionDocument, OcrModel

# Splits merged multi-page markdown produced by _run_ocr_pdf back into pages.
_PAGE_SPLIT = re.compile(r"\n\n---\n\n<!-- Page \d+ -->\n\n")


def _pages(result_text: str) -> list[str]:
    """Recover per-page markdown from a merged OCR result (order preserved)."""
    if not result_text:
        return [""]
    return _PAGE_SPLIT.split(result_text)


def _find_omnidocbench_gt(root: str) -> str | None:
    candidates = sorted(
        (p for p in glob.glob(os.path.join(root, "**", "*.json"), recursive=True)
         if "OmniDocBench" in os.path.basename(p)),
        key=len,
    )
    for path in candidates:
        try:
            data = json.load(open(path))
        except Exception:
            continue
        if isinstance(data, list) and data and isinstance(data[0], dict) and "page_info" in data[0]:
            return path
    return None


async def _load(db: AsyncSession, run_id: str):
    """Return (done_items, docs_by_id, models_by_id) for a run."""
    items_result = await db.execute(
        select(BatchRunItem).where(
            BatchRunItem.batch_run_id == run_id,
            BatchRunItem.status == "done",
        )
    )
    items = list(items_result.scalars().all())

    doc_ids = {i.document_id for i in items}
    model_ids = {i.model_id for i in items}
    docs_by_id: dict[str, CollectionDocument] = {}
    models_by_id: dict[str, OcrModel] = {}
    for did in doc_ids:
        doc = await db.get(CollectionDocument, did)
        if doc is not None:
            docs_by_id[did] = doc
    for mid in model_ids:
        m = await db.get(OcrModel, mid)
        if m is not None:
            models_by_id[mid] = m
    return items, docs_by_id, models_by_id


def _work_dir(run_id: str) -> str:
    settings = get_settings()
    d = os.path.join(settings.benchmarks_dir, "_runs", run_id)
    os.makedirs(d, exist_ok=True)
    return os.path.abspath(d)


# ── OmniDocBench ─────────────────────────────────────────────
def _export_omnidocbench(items, docs_by_id, models_by_id, work_dir: str) -> dict[str, str]:
    """Write <work>/pred_<model>/<image_key_no_ext>.md. Returns {model_id: pred_dir}."""
    pred_dirs: dict[str, str] = {}
    by_model: dict[str, list] = {}
    for it in items:
        by_model.setdefault(it.model_id, []).append(it)

    for model_id, model_items in by_model.items():
        pred_dir = os.path.join(work_dir, f"pred_{model_id}")
        os.makedirs(pred_dir, exist_ok=True)
        for it in model_items:
            doc = docs_by_id.get(it.document_id)
            if doc is None or not doc.gt_ref:
                continue
            fname = os.path.splitext(doc.gt_ref)[0] + ".md"
            out_path = os.path.join(pred_dir, fname)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w") as f:
                f.write(it.result_text or "")
        pred_dirs[model_id] = pred_dir
    return pred_dirs


async def _score_omnidocbench(items, docs_by_id, models_by_id, work_dir: str) -> dict[str, dict]:
    settings = get_settings()
    gt_json = _find_omnidocbench_gt(os.path.join(settings.benchmarks_dir, "omnidocbench"))
    if gt_json is None:
        raise FileNotFoundError("OmniDocBench ground-truth JSON not found")

    scorer = os.path.join(settings.bench_root, "scorers", "omnidocbench_score.py")
    pred_dirs = _export_omnidocbench(items, docs_by_id, models_by_id, work_dir)

    scores: dict[str, dict] = {}
    for model_id, pred_dir in pred_dirs.items():
        out_dir = os.path.join(work_dir, f"result_{model_id}")
        cmd = [
            "python3", scorer,
            "--gt", gt_json,
            "--pred", pred_dir,
            "--out", out_dir,
            "--workers", str(settings.omnidocbench_workers),
        ]
        if not settings.omnidocbench_enable_cdm:
            cmd.append("--no-cdm")
        result = await _run(cmd)
        scores[model_id] = result
    return scores


# ── olmOCR-Bench ─────────────────────────────────────────────
def _export_olmocr(items, docs_by_id, models_by_id, work_dir: str) -> str:
    """Build a bench_data-shaped dir with symlinked pdfs/jsonl + one candidate per model.

    Returns the bench dir to pass to the scorer.
    """
    settings = get_settings()
    src = os.path.join(settings.benchmarks_dir, "olmocr_bench", "bench_data")
    bench_dir = os.path.join(work_dir, "bench_data")
    os.makedirs(bench_dir, exist_ok=True)

    # symlink pdfs/ and each *.jsonl from the real dataset
    pdfs_link = os.path.join(bench_dir, "pdfs")
    if not os.path.exists(pdfs_link):
        os.symlink(os.path.abspath(os.path.join(src, "pdfs")), pdfs_link)
    for jsonl in glob.glob(os.path.join(src, "*.jsonl")):
        dst = os.path.join(bench_dir, os.path.basename(jsonl))
        if not os.path.exists(dst):
            os.symlink(os.path.abspath(jsonl), dst)

    by_model: dict[str, list] = {}
    for it in items:
        by_model.setdefault(it.model_id, []).append(it)

    for model_id, model_items in by_model.items():
        cand_dir = os.path.join(bench_dir, f"model_{model_id}")
        os.makedirs(cand_dir, exist_ok=True)
        for it in model_items:
            doc = docs_by_id.get(it.document_id)
            if doc is None or not doc.gt_ref:
                continue
            base = os.path.splitext(doc.gt_ref)[0]  # may contain subdirs
            for page_idx, page_text in enumerate(_pages(it.result_text or ""), start=1):
                out_path = os.path.join(cand_dir, f"{base}_pg{page_idx}_repeat1.md")
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w") as f:
                    f.write(page_text)
    return bench_dir


async def _score_olmocr(items, docs_by_id, models_by_id, work_dir: str) -> dict[str, dict]:
    settings = get_settings()
    bench_dir = _export_olmocr(items, docs_by_id, models_by_id, work_dir)
    venv_python = os.path.join(settings.bench_root, "olmocr_env", "bin", "python")
    scorer = os.path.join(settings.bench_root, "scorers", "olmocr_score.py")

    cmd = [venv_python, scorer, "--dir", bench_dir, "--force"]
    result = await _run(cmd)
    # result: {"benchmark": "olmocr_bench", "candidates": {"model_<id>": {...}}}
    scores: dict[str, dict] = {}
    for cand_name, cand in (result.get("candidates") or {}).items():
        if cand_name.startswith("model_"):
            scores[cand_name[len("model_"):]] = cand
    return scores


# ── shared subprocess runner ────────────────────────────────
async def _run(cmd: list[str]) -> dict:
    """Run a scorer subprocess and parse its final stdout line as JSON."""
    logger.info(f"bench scorer: {' '.join(cmd[:3])} ...")
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        tail = (stderr or b"").decode(errors="replace")[-2000:]
        raise RuntimeError(f"scorer failed (exit {proc.returncode}): {tail}")
    out = (stdout or b"").decode(errors="replace")
    # The scorer prints its result JSON as one line, but noisy deps (playwright
    # browser cleanup, tqdm) may print AFTER it. Scan from the end for the last
    # line that parses as JSON rather than blindly taking the final line.
    for line in reversed(out.splitlines()):
        line = line.strip()
        if not line or line[0] not in "{[":
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"scorer produced no JSON output; tail:\n{out[-2000:]}")


_SCORERS = {"omnidocbench": _score_omnidocbench, "olmocr_bench": _score_olmocr}


async def score_run(db: AsyncSession, run_id: str, kind: str) -> dict[str, dict]:
    """Score a completed run against ``kind`` and return {model_id: scores}."""
    if kind not in _SCORERS:
        raise ValueError(f"Unknown benchmark kind: {kind}")
    items, docs_by_id, models_by_id = await _load(db, run_id)
    if not items:
        return {}
    work_dir = _work_dir(run_id)
    try:
        return await _SCORERS[kind](items, docs_by_id, models_by_id, work_dir)
    finally:
        # keep raw results for debugging OmniDocBench; drop olmocr symlink tree
        if kind == "olmocr_bench":
            shutil.rmtree(os.path.join(work_dir, "bench_data"), ignore_errors=True)
