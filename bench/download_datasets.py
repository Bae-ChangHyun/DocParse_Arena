#!/usr/bin/env python3
"""Download the official OCR benchmark datasets locally.

Datasets land under ``backend/data/benchmarks/`` (gitignored) so the FastAPI
backend can read documents + ground truth with its existing path logic.

  - OmniDocBench : HF dataset ``opendatalab/OmniDocBench``
      -> backend/data/benchmarks/omnidocbench/
      (1651 PDF-page images + OmniDocBench.json ground truth)
  - olmOCR-Bench : HF dataset ``allenai/olmOCR-bench``
      -> backend/data/benchmarks/olmocr_bench/
      (bench_data/: pdfs + *.jsonl unit tests)

Requires the HuggingFace CLI (``hf``), already installed on this machine.

Usage:
    python bench/download_datasets.py                 # both, full
    python bench/download_datasets.py --only omnidocbench
    python bench/download_datasets.py --only olmocr_bench
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO_ROOT / "backend" / "data" / "benchmarks"

DATASETS = {
    "omnidocbench": {
        "repo_id": "opendatalab/OmniDocBench",
        "dest": DATA_ROOT / "omnidocbench",
    },
    "olmocr_bench": {
        "repo_id": "allenai/olmOCR-bench",
        "dest": DATA_ROOT / "olmocr_bench",
    },
}


def download(key: str) -> None:
    spec = DATASETS[key]
    dest = spec["dest"]
    dest.mkdir(parents=True, exist_ok=True)
    print(f"→ Downloading {spec['repo_id']} into {dest}")
    # The modern `hf download` resumes automatically (no --resume-download flag).
    cmd = [
        "hf", "download",
        "--repo-type", "dataset",
        spec["repo_id"],
        "--local-dir", str(dest),
    ]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"✗ Download failed for {spec['repo_id']}", file=sys.stderr)
        sys.exit(result.returncode)
    print(f"✓ {spec['repo_id']} ready at {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=list(DATASETS.keys()),
        help="Download only one dataset (default: both).",
    )
    args = parser.parse_args()

    keys = [args.only] if args.only else list(DATASETS.keys())
    for key in keys:
        download(key)


if __name__ == "__main__":
    main()
