"""Faithful reproduction of DeepSeek-OCR's OFFICIAL OmniDocBench / olmOCR eval,
running the repo's own vLLM code (DeepSeek-OCR-vllm/) in the deepseek_env venv
(torch 2.6.0+cu118, vllm 0.8.5+cu118, transformers 4.46.3, V0 engine).

It imports the official modules verbatim (config, deepseek_ocr, process.*) and
copies the exact SamplingParams + post-processing from run_dpsk_ocr_eval_batch.py
(OmniDocBench) and run_dpsk_ocr_pdf.py (PDF → olmOCR). Only the file I/O is
adapted to our data layout (png+jpg per GT image; per-page olmOCR candidates).

Run in the deepseek_env venv:
  bench/deepseek_env/bin/python bench/deepseek_official_run.py <kind> <out_dir> [--limit N] [--chunk 256]
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

# vLLM engine + device MUST be set before importing vllm (matches official scripts).
os.environ["VLLM_USE_V1"] = "0"
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(REPO, "backend", "data", "benchmarks")
VLLM_DIR = os.path.join(REPO, "bench", "vendor", "DeepSeek-OCR",
                        "DeepSeek-OCR-master", "DeepSeek-OCR-vllm")
# Official scripts run from inside DeepSeek-OCR-vllm/ (relative imports).
os.chdir(VLLM_DIR)
sys.path.insert(0, VLLM_DIR)

import torch  # noqa: E402

if torch.version.cuda == "11.8":
    os.environ["TRITON_PTXAS_PATH"] = "/usr/local/cuda-11.8/bin/ptxas"

from PIL import Image  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

from config import MODEL_PATH, PROMPT, CROP_MODE, MAX_CONCURRENCY, NUM_WORKERS, SKIP_REPEAT  # noqa: E402
from deepseek_ocr import DeepseekOCRForCausalLM  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402
from vllm.model_executor.models.registry import ModelRegistry  # noqa: E402
from process.ngram_norepeat import NoRepeatNGramLogitsProcessor  # noqa: E402
from process.image_process import DeepseekOCRProcessor  # noqa: E402

ModelRegistry.register_model("DeepseekOCRForCausalLM", DeepseekOCRForCausalLM)

_PROC = DeepseekOCRProcessor()  # reused across images (deterministic output)


# ── official post-processing (verbatim from the repo scripts) ──────────────
def clean_formula(text):
    def process_formula(match):
        formula = match.group(1)
        formula = re.sub(r"\\quad\s*\([^)]*\)", "", formula)
        return r"\[" + formula.strip() + r"\]"
    return re.sub(r"\\\[(.*?)\\\]", process_formula, text)


def re_match(text):
    pattern = r"(<\|ref\|>(.*?)<\|/ref\|><\|det\|>(.*?)<\|/det\|>)"
    matches = re.findall(pattern, text, re.DOTALL)
    images, others = [], []
    for a_match in matches:
        (images if "<|ref|>image<|/ref|>" in a_match[0] else others).append(a_match[0])
    return images, others


def post_omnidocbench(content: str) -> str:
    """run_dpsk_ocr_eval_batch.py post-processing: removes ALL grounding blocks
    (image ones included — eval_batch does not keep image placeholders)."""
    content = clean_formula(content)
    images, others = re_match(content)
    for blk in images + others:
        content = (content.replace(blk, "")
                   .replace("\n\n\n\n", "\n\n").replace("\n\n\n", "\n\n")
                   .replace("<center>", "").replace("</center>", ""))
    return content


def post_pdf(content: str, jdx: int) -> str | None:
    """run_dpsk_ocr_pdf.py per-page post-processing. Returns None if the page is
    a repetition (no eos) and SKIP_REPEAT is on — exactly the official `continue`."""
    if "<｜end▁of▁sentence｜>" in content:
        content = content.replace("<｜end▁of▁sentence｜>", "")
    elif SKIP_REPEAT:
        return None
    images, others = re_match(content)
    for idx, m in enumerate(images):
        content = content.replace(m, f"![](images/{jdx}_{idx}.jpg)\n")
    for m in others:
        content = (content.replace(m, "")
                   .replace("\\coloneqq", ":=").replace("\\eqqcolon", "=:")
                   .replace("\n\n\n\n", "\n\n").replace("\n\n\n", "\n\n"))
    return content


# 16GB 4080 + dual-4K display (~2.7GB VRAM 상시 점유)에 맞춘 메모리 파라미터.
# gpu_memory_utilization은 전체(16GB) 기준이라 0.9는 초과 커밋 → 0.75로 낮춤.
# enforce_eager=True는 CUDA graph 메모리 절약 — 속도만 영향, 추론 출력은 불변.
_GPU_UTIL = float(os.environ.get("DS_GPU_UTIL", "0.75"))


def build_llm(disable_cache: bool) -> LLM:
    return LLM(
        model=MODEL_PATH,
        hf_overrides={"architectures": ["DeepseekOCRForCausalLM"]},
        block_size=256,
        enforce_eager=True,
        trust_remote_code=True,
        max_model_len=8192,
        swap_space=0,
        max_num_seqs=MAX_CONCURRENCY,
        tensor_parallel_size=1,
        gpu_memory_utilization=_GPU_UTIL,
        disable_mm_preprocessor_cache=disable_cache,
    )


def _preprocess(image):
    return {
        "prompt": PROMPT,
        "multi_modal_data": {
            "image": _PROC.tokenize_with_images(images=[image], bos=True, eos=True, cropping=CROP_MODE)
        },
    }


def _batch_inputs(images):
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as ex:
        return list(ex.map(_preprocess, images))


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# ── OmniDocBench ────────────────────────────────────────────────────────────
def run_omnidocbench(out_dir, limit, chunk):
    idir = os.path.join(BENCH, "omnidocbench", "images")
    imgs = sorted(glob.glob(os.path.join(idir, "*.png")) +
                  glob.glob(os.path.join(idir, "*.jpg")) +
                  glob.glob(os.path.join(idir, "*.jpeg")))
    if limit:
        imgs = imgs[:limit]
    pred = os.path.join(out_dir, "pred")
    os.makedirs(pred, exist_ok=True)
    todo = [p for p in imgs if not os.path.exists(
        os.path.join(pred, os.path.splitext(os.path.basename(p))[0] + ".md"))]
    print(f"omnidocbench: {len(todo)}/{len(imgs)} to do", flush=True)

    llm = build_llm(disable_cache=False)
    sp = SamplingParams(
        temperature=0.0, max_tokens=8192,
        logits_processors=[NoRepeatNGramLogitsProcessor(ngram_size=40, window_size=90,
                                                        whitelist_token_ids={128821, 128822})],
        skip_special_tokens=False,
    )
    done = 0
    for group in _chunks(todo, chunk):
        pil = [Image.open(p).convert("RGB") for p in group]
        outs = llm.generate(_batch_inputs(pil), sampling_params=sp)
        for out, path in zip(outs, group):
            content = post_omnidocbench(out.outputs[0].text)
            stem = os.path.splitext(os.path.basename(path))[0]
            with open(os.path.join(pred, stem + ".md"), "w", encoding="utf-8") as f:
                f.write(content)
        done += len(group)
        print(f"omnidocbench {done}/{len(todo)}", flush=True)
    print(f"omnidocbench DONE {len(imgs)}", flush=True)


# ── olmOCR-Bench (PDF, official pdf recipe) ────────────────────────────────
def run_olmocr(out_dir, limit, chunk):
    import fitz  # PyMuPDF, from requirements
    src = os.path.join(BENCH, "olmocr_bench", "bench_data")
    pdfs_dir = os.path.join(src, "pdfs")
    pdfs = sorted(glob.glob(os.path.join(pdfs_dir, "**", "*.pdf"), recursive=True))
    if limit:
        pdfs = pdfs[:limit]
    bench_dir = os.path.join(out_dir, "bench_data")
    cand = os.path.join(bench_dir, "model_deepseek_official")
    os.makedirs(cand, exist_ok=True)
    if not os.path.exists(os.path.join(bench_dir, "pdfs")):
        os.symlink(pdfs_dir, os.path.join(bench_dir, "pdfs"))
    for j in glob.glob(os.path.join(src, "*.jsonl")):
        d = os.path.join(bench_dir, os.path.basename(j))
        if not os.path.exists(d):
            os.symlink(j, d)

    def render(pdf_path):
        doc = fitz.open(pdf_path)
        mat = fitz.Matrix(144 / 72.0, 144 / 72.0)
        pages = []
        for i in range(doc.page_count):
            pm = doc[i].get_pixmap(matrix=mat, alpha=False)
            import io
            pages.append(Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB"))
        doc.close()
        return pages

    todo = [p for p in pdfs if not os.path.exists(os.path.join(
        cand, os.path.splitext(os.path.relpath(p, pdfs_dir))[0] + "_pg1_repeat1.md"))]
    print(f"olmocr: {len(todo)}/{len(pdfs)} pdfs to do", flush=True)

    llm = build_llm(disable_cache=True)
    sp = SamplingParams(
        temperature=0.0, max_tokens=8192,
        logits_processors=[NoRepeatNGramLogitsProcessor(ngram_size=20, window_size=50,
                                                        whitelist_token_ids={128821, 128822})],
        skip_special_tokens=False, include_stop_str_in_output=True,
    )
    done = 0
    for group in _chunks(todo, chunk):
        # flatten pages across the pdf group, remember (pdf_index, page_index)
        flat, index = [], []
        rendered = {}
        for gi, pdf in enumerate(group):
            pages = render(pdf)
            rendered[gi] = len(pages)
            for pi, img in enumerate(pages):
                flat.append(img); index.append((gi, pi))
        outs = llm.generate(_batch_inputs(flat), sampling_params=sp) if flat else []
        # group outputs back per pdf
        per_pdf = {gi: {} for gi in range(len(group))}
        for (gi, pi), out in zip(index, outs):
            per_pdf[gi][pi] = post_pdf(out.outputs[0].text, pi)
        for gi, pdf in enumerate(group):
            base = os.path.splitext(os.path.relpath(pdf, pdfs_dir))[0]
            npages = rendered.get(gi, 0)
            if npages == 0:
                p = os.path.join(cand, f"{base}_pg1_repeat1.md")
                os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").close()
                continue
            for pi in range(npages):
                content = per_pdf[gi].get(pi)
                p = os.path.join(cand, f"{base}_pg{pi + 1}_repeat1.md")
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content if content is not None else "")
        done += len(group)
        print(f"olmocr {done}/{len(todo)}", flush=True)
    print(f"olmocr DONE {len(pdfs)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["omnidocbench", "olmocr_bench"])
    ap.add_argument("out_dir")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--chunk", type=int, default=256)
    a = ap.parse_args()
    out = a.out_dir if os.path.isabs(a.out_dir) else os.path.join(REPO, a.out_dir)
    os.makedirs(out, exist_ok=True)
    (run_omnidocbench if a.kind == "omnidocbench" else run_olmocr)(out, a.limit, a.chunk)


if __name__ == "__main__":
    main()
