# Official OCR Benchmarks (local runner)

Runs **OmniDocBench** (CVPR 2025) and **olmOCR-Bench** (AllenAI) locally with their
*official* scoring toolkits, and exposes a normalized JSON interface the FastAPI
backend calls to score model outputs. Heavy dependencies (TeX Live, CDM, chromium)
are isolated in a Docker image / dedicated venv — they never touch the web process.

## Layout

```
bench/
  download_datasets.py      # fetch full datasets from HuggingFace
  vendor/olmocr/            # shallow clone of allenai/olmocr (scoring code)
  vendor/OmniDocBench/      # shallow clone of opendatalab/OmniDocBench (configs/demo)
  olmocr_env/               # uv venv: olmocr[bench] + numpy + playwright chromium
  scorers/
    olmocr_score.py         # olmOCR-bench → normalized JSON (run inside olmocr_env)
    omnidocbench_score.py   # OmniDocBench → normalized JSON (host, drives Docker)
```

Datasets land under `backend/data/benchmarks/` (gitignored).

## One-time setup

### OmniDocBench (Docker, ~18 GB image — bundles TeX Live 2025 for CDM)
```bash
docker pull ghcr.io/zeng-weijun/omnidocbench-eval:repro-ubuntu2204
```

### olmOCR-Bench (dedicated venv, no torch)
```bash
cd bench
uv venv --python 3.12 olmocr_env
source olmocr_env/bin/activate
uv pip install -e "./vendor/olmocr[bench]" numpy
playwright install chromium        # needed for math (KaTeX) + table tests
```

### Datasets (full sets)
```bash
python bench/download_datasets.py                 # both
# → backend/data/benchmarks/{omnidocbench,olmocr_bench}/
```

## Scoring (normalized JSON)

### OmniDocBench (one model's prediction folder)
Predictions = one markdown file per page, named `<gt_image_name>.md`.
```bash
python bench/scorers/omnidocbench_score.py \
  --gt  backend/data/benchmarks/omnidocbench/OmniDocBench.json \
  --pred <pred_dir> --out <result_dir> [--no-cdm] [--workers 8]
```
Output: `{text_edit, formula_edit, formula_cdm, table_teds, table_edit,
reading_order_edit, overall_edit}`. Edit-distance metrics are **lower = better**;
CDM/TEDS are **higher = better**.

### olmOCR-Bench (one or more candidate subdirs)
Candidate dir = one per model, files `{pdf_basename}_pg{page}_repeat{n}.md`.
```bash
source bench/olmocr_env/bin/activate
python bench/scorers/olmocr_score.py --dir <bench_data> [--candidate NAME]
```
Output: per-candidate `{overall, n_tests, by_type, by_jsonl}` (pass-rate, higher = better).

## Verified (Phase 0 smoke)

Both scorers were validated on the toolkits' bundled demo/sample data:
- olmOCR sample `olmocr_pipeline` → **0.943** overall pass-rate.
- OmniDocBench demo → text_edit 0.336, formula_cdm 0.883, table_teds 0.797, overall_edit 0.247.
CDM (formula) rendering via TeX Live works inside the container; no GPU required.
