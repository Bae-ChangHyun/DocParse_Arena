"""Run the OFFICIAL PaddleOCR-VL pipeline (PP-DocLayoutV3 + PaddleOCR-VL) over a
benchmark's docs and write prediction markdown in the layout the scorers expect.

Run inside bench/paddle_env:
    bench/paddle_env/bin/python bench/paddleocr_vl_run.py <kind> <out_dir> [--limit N]

- omnidocbench: writes <out_dir>/pred/<image_stem>.md  (one per GT image)
- olmocr_bench: writes <out_dir>/bench_data/model_paddleocr_official/{base}_pg{n}_repeat1.md
                and symlinks pdfs/ + *.jsonl for the scorer
"""
import argparse
import glob
import multiprocessing as mp
import os
import sys
import warnings

# paddlex forks inference workers; forking after CUDA init deadlocks (flaky —
# small batches sometimes slip through). Force 'spawn' so workers re-init CUDA.
try:
    mp.set_start_method("spawn", force=True)
except RuntimeError:
    pass

warnings.filterwarnings("ignore")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(REPO, "backend", "data", "benchmarks")


def _md_text(res) -> str:
    md = getattr(res, "markdown", None)
    if isinstance(md, dict):
        return md.get("markdown_texts", "") or ""
    return str(md or "")


def run_omnidocbench(pipeline, out_dir: str, limit: int | None):
    root = os.path.join(BENCH, "omnidocbench")
    images = sorted(glob.glob(os.path.join(root, "images", "*.png")) +
                    glob.glob(os.path.join(root, "images", "*.jpg")))
    if limit:
        images = images[:limit]
    pred = os.path.join(out_dir, "pred")
    os.makedirs(pred, exist_ok=True)
    for i, img in enumerate(images, 1):
        stem = os.path.splitext(os.path.basename(img))[0]
        dst = os.path.join(pred, stem + ".md")
        if os.path.exists(dst):  # resume: skip already-written outputs
            continue
        try:
            out = list(pipeline.predict(img))
            text = "\n\n".join(_md_text(r) for r in out)
        except Exception as e:  # noqa: BLE001
            text = ""
            print(f"  [err] {stem}: {e}", flush=True)
        with open(os.path.join(pred, stem + ".md"), "w") as f:
            f.write(text)
        if i % 50 == 0:
            print(f"omnidocbench {i}/{len(images)}", flush=True)
    print(f"omnidocbench DONE {len(images)} -> {pred}", flush=True)


def run_olmocr(pipeline, out_dir: str, limit: int | None):
    src = os.path.join(BENCH, "olmocr_bench", "bench_data")
    pdfs_dir = os.path.join(src, "pdfs")
    pdfs = sorted(glob.glob(os.path.join(pdfs_dir, "**", "*.pdf"), recursive=True))
    if limit:
        pdfs = pdfs[:limit]
    bench_dir = os.path.join(out_dir, "bench_data")
    cand = os.path.join(bench_dir, "model_paddleocr_official")
    os.makedirs(cand, exist_ok=True)
    # symlink pdfs/ + jsonl so the scorer can run against this bench_dir
    link = os.path.join(bench_dir, "pdfs")
    if not os.path.exists(link):
        os.symlink(pdfs_dir, link)
    for jsonl in glob.glob(os.path.join(src, "*.jsonl")):
        d = os.path.join(bench_dir, os.path.basename(jsonl))
        if not os.path.exists(d):
            os.symlink(jsonl, d)

    for i, pdf in enumerate(pdfs, 1):
        base = os.path.splitext(os.path.relpath(pdf, pdfs_dir))[0]  # may contain subdirs
        if os.path.exists(os.path.join(cand, f"{base}_pg1_repeat1.md")):
            continue  # resume: skip already-written
        try:
            out = list(pipeline.predict(pdf))  # one result per page
        except Exception as e:  # noqa: BLE001
            out = []
            print(f"  [err] {base}: {e}", flush=True)
        if not out:
            page_path = os.path.join(cand, f"{base}_pg1_repeat1.md")
            os.makedirs(os.path.dirname(page_path), exist_ok=True)
            open(page_path, "w").close()
        for page_idx, r in enumerate(out, 1):
            page_path = os.path.join(cand, f"{base}_pg{page_idx}_repeat1.md")
            os.makedirs(os.path.dirname(page_path), exist_ok=True)
            with open(page_path, "w") as f:
                f.write(_md_text(r))
        if i % 50 == 0:
            print(f"olmocr {i}/{len(pdfs)}", flush=True)
    print(f"olmocr DONE {len(pdfs)} -> {cand}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["omnidocbench", "olmocr_bench"])
    ap.add_argument("out_dir")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--vllm-url", default=None,
                    help="Route the VL model through this OpenAI-compatible vLLM "
                         "server (avoids the native paddle in-process deadlock).")
    args = ap.parse_args()

    from paddleocr import PaddleOCRVL
    if args.vllm_url:
        # VL generation runs on the vLLM server (stable); only layout runs locally.
        pipeline = PaddleOCRVL(vl_rec_backend="vllm-server", vl_rec_server_url=args.vllm_url)
    else:
        pipeline = PaddleOCRVL()
        # Warmup absorbs the native first-predict deadlock (not needed with vLLM).
        try:
            warm = sorted(glob.glob(os.path.join(BENCH, "omnidocbench", "images", "*.png")))
            if warm:
                list(pipeline.predict(warm[0]))
        except Exception:  # noqa: BLE001
            pass
    print("pipeline ready", flush=True)

    os.makedirs(args.out_dir, exist_ok=True)
    if args.kind == "omnidocbench":
        run_omnidocbench(pipeline, args.out_dir, args.limit)
    else:
        run_olmocr(pipeline, args.out_dir, args.limit)


if __name__ == "__main__":
    main()
