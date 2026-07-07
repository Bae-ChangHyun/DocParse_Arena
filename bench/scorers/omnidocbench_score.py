#!/usr/bin/env python3
"""OmniDocBench scorer → normalized JSON (host-side, stdlib only).

Runs the OFFICIAL OmniDocBench end2end evaluation via its Docker image
(``ghcr.io/zeng-weijun/omnidocbench-eval:repro-ubuntu2204``) against one model's
prediction folder, then parses the consolidated ``metric_result.json`` into a
normalized summary on stdout.

Prediction folder: one markdown file per page, named to match the ground-truth
image key (``<image_name>.md``). Ground truth is the OmniDocBench JSON.

Usage:
    python omnidocbench_score.py --gt <OmniDocBench.json> --pred <pred_dir> \
        --out <result_dir> [--no-cdm] [--workers 8]

Normalized output (edit-distance metrics: LOWER is better; CDM/TEDS: HIGHER):
    {
      "benchmark": "omnidocbench",
      "metrics": {
        "text_edit": 0.335, "formula_edit": 0.236, "formula_cdm": 0.882,
        "table_teds": 0.796, "table_edit": 0.190, "reading_order_edit": 0.224
      },
      "overall_edit": 0.246,     # mean of the 4 edit distances (official headline, lower=better)
      "result_dir": "..."
    }
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

# Run the container as the host user so result files aren't left root-owned.
_HOST_USER = f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else None

IMAGE = "ghcr.io/zeng-weijun/omnidocbench-eval:repro-ubuntu2204"


def _build_config(with_cdm: bool, workers: int) -> str:
    formula_metrics = "[Edit_dist, CDM]" if with_cdm else "[Edit_dist]"
    return f"""end2end_eval:
  metrics:
    text_block:
      metric: [Edit_dist]
    display_formula:
      metric: {formula_metrics}
      cdm_workers: {workers}
    table:
      metric: [TEDS, Edit_dist]
      teds_workers: {workers}
    reading_order:
      metric: [Edit_dist]
  dataset:
    dataset_name: end2end_dataset
    ground_truth:
      data_path: /data/gt.json
    prediction:
      data_path: /data/pred
    match_method: quick_match
    match_workers: {workers}
    quick_match_truncated_timeout_sec: 300
    match_timeout_sec: 420
    timeout_fallback_max_chunk_span: 10
    timeout_fallback_order_penalty: 0.10
"""


def _all(section: dict, *path):
    cur = section
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _parse(result_dir: str) -> dict:
    # Locate the consolidated metric_result.json (name is prefixed by match method)
    hit = None
    for f in os.listdir(result_dir):
        if f.endswith("_metric_result.json"):
            hit = os.path.join(result_dir, f)
            break
    if hit is None:
        raise FileNotFoundError(f"No *_metric_result.json in {result_dir}")
    d = json.load(open(hit))

    metrics = {
        "text_edit": _all(d, "text_block", "all", "Edit_dist", "ALL_page_avg"),
        "formula_edit": _all(d, "display_formula", "all", "Edit_dist", "ALL_page_avg"),
        "formula_cdm": _all(d, "display_formula", "all", "CDM", "all"),
        "table_teds": _all(d, "table", "all", "TEDS", "all"),
        "table_edit": _all(d, "table", "all", "Edit_dist", "ALL_page_avg"),
        "reading_order_edit": _all(d, "reading_order", "all", "Edit_dist", "ALL_page_avg"),
    }
    edits = [metrics["text_edit"], metrics["formula_edit"],
             metrics["table_edit"], metrics["reading_order_edit"]]
    edits = [e for e in edits if isinstance(e, (int, float))]
    overall_edit = sum(edits) / len(edits) if edits else None

    return {"benchmark": "omnidocbench", "metrics": metrics,
            "overall_edit": overall_edit, "result_dir": result_dir}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", required=True, help="OmniDocBench ground-truth JSON")
    ap.add_argument("--pred", required=True, help="Prediction markdown folder")
    ap.add_argument("--out", required=True, help="Host dir to write result JSONs")
    ap.add_argument("--no-cdm", action="store_true", help="Skip slow CDM formula metric")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=3600)
    args = ap.parse_args()

    gt = os.path.abspath(args.gt)
    pred = os.path.abspath(args.pred)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = os.path.join(tmp, "config.yaml")
        with open(cfg_path, "w") as f:
            f.write(_build_config(not args.no_cdm, args.workers))

        cmd = ["docker", "run", "--rm"]
        if _HOST_USER:
            cmd += ["--user", _HOST_USER]
        cmd += [
            "-v", f"{gt}:/data/gt.json:ro",
            "-v", f"{pred}:/data/pred:ro",
            "-v", f"{out}:/workspace/result",
            "-v", f"{cfg_path}:/data/config.yaml:ro",
            IMAGE, "--config", "/data/config.yaml",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
        if proc.returncode != 0:
            sys.stderr.write(proc.stdout[-3000:] + "\n" + proc.stderr[-3000:] + "\n")
            print(f"Error: OmniDocBench eval failed (exit {proc.returncode})", file=sys.stderr)
            sys.exit(proc.returncode)

    print(json.dumps(_parse(out), ensure_ascii=False))


if __name__ == "__main__":
    main()
