"""Run DeepSeek-OCR over a benchmark using the OFFICIAL vLLM recipe.

Official recipe (docs.vllm.ai DeepSeek-OCR): serve with the
NGramPerReqLogitsProcessor, and send requests with skip_special_tokens=False +
vllm_xargs {ngram_size:30, window_size:90, whitelist_token_ids:[128821,128822]}.
The grounding prompt yields markdown (tables as HTML). We strip the grounding
label lines (word[[x,y,w,h]]) like the deepseek_clean postprocessor.

Run with backend venv (has pypdfium2 for PDFs):
  backend/.venv/bin/python bench/deepseek_run.py <kind> <out_dir> --vllm-url http://localhost:8001/v1 [--limit N]
"""
from __future__ import annotations

import argparse
import base64
import glob
import io
import json
import os
import re
import sys
import urllib.request

MODEL = "deepseek-ai/DeepSeek-OCR"
PROMPT = "<image>\n<|grounding|>Convert the document to markdown. "
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(REPO, "backend", "data", "benchmarks")

# Faithful port of the official DeepSeek-OCR OmniDocBench post-processing
# (DeepSeek-OCR-vllm/run_dpsk_ocr_eval_batch.py): clean_formula, then strip each
# whole <|ref|>..<|/ref|><|det|>..<|/det|> grounding block (keeping the content
# that follows), drop <center>/</center>, and collapse blank runs. The markers
# survive generation because the recipe sends skip_special_tokens=False.
_REF_DET = re.compile(r"<\|ref\|>.*?<\|/ref\|><\|det\|>.*?<\|/det\|>", re.DOTALL)
_FORMULA = re.compile(r"\\\[(.*?)\\\]")
_QUAD = re.compile(r"\\quad\s*\([^)]*\)")


def _clean_formula(text: str) -> str:
    return _FORMULA.sub(lambda m: r"\[" + _QUAD.sub("", m.group(1)).strip() + r"\]", text)


def clean(text: str) -> str:
    text = _clean_formula(text)
    for full in _REF_DET.findall(text):
        text = text.replace(full, "")
    text = text.replace("<center>", "").replace("</center>", "")
    # official uses greedy .replace chains; loop to fully collapse blank runs
    text = text.replace("<｜end▁of▁sentence｜>", "").replace("<|end▁of▁sentence|>", "")
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def infer(url: str, b64: str, max_tokens: int = 4096) -> str:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": PROMPT}]}],
        "max_tokens": max_tokens, "temperature": 0.0,
        "skip_special_tokens": False,
        "vllm_xargs": {"ngram_size": 30, "window_size": 90,
                       "whitelist_token_ids": [128821, 128822]},
    }
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=600))
    return clean(r["choices"][0]["message"]["content"])


def img_b64(path: str) -> str:
    return base64.b64encode(open(path, "rb").read()).decode()


def pdf_pages_b64(path: str) -> list[str]:
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    out = []
    for i in range(len(pdf)):
        pil = pdf[i].render(scale=200 / 72).to_pil().convert("RGB")
        buf = io.BytesIO(); pil.save(buf, format="PNG")
        out.append(base64.b64encode(buf.getvalue()).decode())
    return out


def run_omnidocbench(url, out_dir, limit):
    idir = os.path.join(BENCH, "omnidocbench", "images")
    imgs = sorted(glob.glob(os.path.join(idir, "*.png")) +
                  glob.glob(os.path.join(idir, "*.jpg")) +
                  glob.glob(os.path.join(idir, "*.jpeg")))
    if limit:
        imgs = imgs[:limit]
    pred = os.path.join(out_dir, "pred"); os.makedirs(pred, exist_ok=True)
    for i, img in enumerate(imgs, 1):
        stem = os.path.splitext(os.path.basename(img))[0]
        dst = os.path.join(pred, stem + ".md")
        if os.path.exists(dst):
            continue
        try:
            text = infer(url, img_b64(img))
        except Exception as e:  # noqa: BLE001
            text = ""; print(f"  [err] {stem}: {e}", flush=True)
        open(dst, "w").write(text)
        if i % 50 == 0:
            print(f"omnidocbench {i}/{len(imgs)}", flush=True)
    print(f"omnidocbench DONE {len(imgs)}", flush=True)


def run_olmocr(url, out_dir, limit):
    src = os.path.join(BENCH, "olmocr_bench", "bench_data")
    pdfs_dir = os.path.join(src, "pdfs")
    pdfs = sorted(glob.glob(os.path.join(pdfs_dir, "**", "*.pdf"), recursive=True))
    if limit:
        pdfs = pdfs[:limit]
    bench_dir = os.path.join(out_dir, "bench_data")
    cand = os.path.join(bench_dir, "model_deepseek_official"); os.makedirs(cand, exist_ok=True)
    link = os.path.join(bench_dir, "pdfs")
    if not os.path.exists(link):
        os.symlink(pdfs_dir, link)
    for j in glob.glob(os.path.join(src, "*.jsonl")):
        d = os.path.join(bench_dir, os.path.basename(j))
        if not os.path.exists(d):
            os.symlink(j, d)
    for i, pdf in enumerate(pdfs, 1):
        base = os.path.splitext(os.path.relpath(pdf, pdfs_dir))[0]
        if os.path.exists(os.path.join(cand, f"{base}_pg1_repeat1.md")):
            continue
        try:
            pages = pdf_pages_b64(pdf)
        except Exception as e:  # noqa: BLE001
            pages = []; print(f"  [err render] {base}: {e}", flush=True)
        if not pages:
            p = os.path.join(cand, f"{base}_pg1_repeat1.md")
            os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").close()
        for pi, b64 in enumerate(pages, 1):
            try:
                text = infer(url, b64)
            except Exception as e:  # noqa: BLE001
                text = ""; print(f"  [err] {base} pg{pi}: {e}", flush=True)
            p = os.path.join(cand, f"{base}_pg{pi}_repeat1.md")
            os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(text)
        if i % 50 == 0:
            print(f"olmocr {i}/{len(pdfs)}", flush=True)
    print(f"olmocr DONE {len(pdfs)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["omnidocbench", "olmocr_bench"])
    ap.add_argument("out_dir")
    ap.add_argument("--vllm-url", required=True)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    (run_omnidocbench if a.kind == "omnidocbench" else run_olmocr)(a.vllm_url, a.out_dir, a.limit)


if __name__ == "__main__":
    main()
