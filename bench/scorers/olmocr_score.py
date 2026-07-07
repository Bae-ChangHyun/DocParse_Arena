#!/usr/bin/env python3
"""olmOCR-Bench scorer → normalized JSON.

Runs the OFFICIAL olmOCR-bench scoring logic (imports ``evaluate_candidate`` and
``load_tests`` from the vendored ``olmocr.bench.benchmark``) against one or more
candidate folders, and emits a normalized JSON summary on stdout.

Must run inside the ``bench/olmocr_env`` venv (which has olmocr[bench] + numpy +
playwright chromium installed).

Input dir layout (same as the official runner):
    <dir>/pdfs/**/*.pdf
    <dir>/*.jsonl                      (unit tests)
    <dir>/<candidate>/{pdf}_pg{page}_repeat{n}.md   (one subdir per model)

Usage:
    python olmocr_score.py --dir <bench_data> [--candidate NAME] [--sample N] [--force]

Normalized output (higher score = better; pass-rate in 0..1):
    {
      "benchmark": "olmocr_bench",
      "candidates": {
        "<name>": {
          "overall": 0.943,                 # avg of per-JSONL pass rates (official)
          "n_tests": 120,
          "by_type": {"present": 0.80, "table": 0.85, ...},
          "by_jsonl": {"dataset.jsonl": 0.879, ...},
          "errors": [...]
        }
      }
    }
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from pypdf import PdfReader

# Official scoring logic (vendored)
from olmocr.bench.benchmark import evaluate_candidate
from olmocr.bench.tests import BaselineTest, load_tests


def _collect(input_folder: str, force: bool):
    pdf_folder = os.path.join(input_folder, "pdfs")
    if not os.path.isdir(pdf_folder):
        print(f"Error: {pdf_folder} not found", file=sys.stderr)
        sys.exit(1)

    all_pdf_files = glob.glob(os.path.join(pdf_folder, "**/*.pdf"), recursive=True)
    pdf_basenames = [os.path.relpath(p, pdf_folder) for p in all_pdf_files]

    jsonl_files = glob.glob(os.path.join(input_folder, "*.jsonl"))
    all_tests = []
    test_to_jsonl: dict[str, str] = {}
    for jsonl_path in jsonl_files:
        basename = os.path.basename(jsonl_path)
        for test in load_tests(jsonl_path):
            test_to_jsonl[test.id] = basename
            all_tests.append(test)

    # Synthesize baseline tests exactly like the official main()
    for pdf in pdf_basenames:
        if not any(t.type == "baseline" for t in all_tests if t.pdf == pdf):
            bt = BaselineTest(id=f"{pdf}_baseline", pdf=pdf, page=1, type="baseline")
            all_tests.append(bt)
            test_to_jsonl[bt.id] = "baseline"

    # Fail-fast on missing dataset entries unless --force (mirrors official)
    if not force:
        for pdf in pdf_basenames:
            n = len(PdfReader(os.path.join(pdf_folder, pdf)).pages)
            for page in range(1, n + 1):
                if not any(t.pdf == pdf and t.page == page for t in all_tests):
                    print(f"No dataset entry for {pdf} page {page}", file=sys.stderr)
                    sys.exit(1)

    return all_tests, pdf_basenames, test_to_jsonl


def _score_candidate(folder, all_tests, pdf_basenames, test_to_jsonl, force):
    (
        _overall,
        total_tests,
        candidate_errors,
        _failures,
        type_breakdown,
        _all_scores,
        test_results,
    ) = evaluate_candidate(folder, all_tests, pdf_basenames, force)

    # NOTE: evaluate_candidate puts BOTH missing-file errors and per-test
    # execution exceptions into ``candidate_errors``. The official main() does
    # NOT zero the candidate for the latter — it scores the tests that ran and
    # just reports the errors. So compute from ``test_results`` regardless; an
    # empty test_results (genuine missing files) still yields overall 0.
    per_jsonl: dict[str, list[float]] = {}
    for pdf in test_results:
        for page in test_results[pdf]:
            for test, passed, _expl in test_results[pdf][page]:
                jsonl = test_to_jsonl.get(test.id, "unknown")
                per_jsonl.setdefault(jsonl, []).append(1.0 if passed else 0.0)

    by_jsonl = {k: sum(v) / len(v) for k, v in per_jsonl.items() if v}
    overall = sum(by_jsonl.values()) / len(by_jsonl) if by_jsonl else 0.0
    by_type = {t: (sum(v) / len(v) if v else 0.0) for t, v in type_breakdown.items()}

    return {"overall": overall, "n_tests": total_tests,
            "by_type": by_type, "by_jsonl": by_jsonl,
            "errors": candidate_errors[:20]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True, help="bench_data folder")
    ap.add_argument("--candidate", default=None, help="Score only this candidate subdir")
    ap.add_argument("--force", action="store_true", help="Ignore missing files")
    args = ap.parse_args()

    input_folder = args.dir
    all_tests, pdf_basenames, test_to_jsonl = _collect(input_folder, args.force)

    candidate_folders = []
    for entry in sorted(os.listdir(input_folder)):
        full = os.path.join(input_folder, entry)
        if not os.path.isdir(full) or entry == "pdfs":
            continue
        if args.candidate is not None and entry != args.candidate:
            continue
        candidate_folders.append(full)

    candidates = {}
    for folder in candidate_folders:
        name = os.path.basename(folder)
        candidates[name] = _score_candidate(
            folder, all_tests, pdf_basenames, test_to_jsonl, args.force
        )

    print(json.dumps({"benchmark": "olmocr_bench", "candidates": candidates}, ensure_ascii=False))


if __name__ == "__main__":
    main()
