#!/usr/bin/env bash
# Run the official PaddleOCR-VL pipeline over a full benchmark, resiliently.
# paddlex flakily deadlocks its inference worker on large batches; small batches
# succeed. So run the (resumable) runner in cycles: each cycle processes what it
# can, a hang is killed by the per-cycle timeout, GPU orphans are cleaned, and
# the next cycle resumes from where it left off. Stop when done or stalled.
#
# Usage: bench/paddle_supervisor.sh <omnidocbench|olmocr_bench> <out_dir> <total>
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
KIND="$1"; OUT="$2"; TOTAL="$3"
PY="$REPO/bench/paddle_env/bin/python"
RUNNER="$REPO/bench/paddleocr_vl_run.py"
CYCLE_TIMEOUT=900   # hard cap per cycle
NOPROG_KILL=50     # kill a hung cycle fast
MAX_STALL=500

count_done() {
  if [ "$KIND" = "omnidocbench" ]; then
    ls "$OUT/pred/"*.md 2>/dev/null | wc -l
  else
    find "$OUT/bench_data/model_paddleocr_official" -name '*_pg1_repeat1.md' 2>/dev/null | wc -l
  fi
}
clean_gpu() {
  for pid in $(nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader 2>/dev/null | grep -i paddle_env | cut -d, -f1); do
    kill -9 "$pid" 2>/dev/null
  done
  for pid in $(ps -eo pid,args | grep 'paddleocr_vl_run.py' | grep -v grep | awk '{print $1}'); do
    kill -9 "$pid" 2>/dev/null
  done
  sleep 2
}

stall=0
cycle=0
while true; do
  before=$(count_done)
  if [ "$before" -ge "$TOTAL" ]; then echo "ALL DONE: $before/$TOTAL"; break; fi
  cycle=$((cycle+1))
  echo "[cycle $cycle] done=$before/$TOTAL  (running…)"
  "$PY" "$RUNNER" "$KIND" "$OUT" > "$OUT/.cycle.log" 2>&1 &
  cpid=$!
  # watchdog: kill the cycle if it produces no new output for NOPROG_KILL sec
  last_prog=$(count_done); last_t=$SECONDS; started=$SECONDS
  while kill -0 "$cpid" 2>/dev/null; do
    sleep 15
    now=$(count_done)
    if [ "$now" -gt "$last_prog" ]; then last_prog=$now; last_t=$SECONDS; fi
    if [ $((SECONDS-last_t)) -ge "$NOPROG_KILL" ] || [ $((SECONDS-started)) -ge "$CYCLE_TIMEOUT" ]; then
      kill -9 "$cpid" 2>/dev/null; break
    fi
  done
  wait "$cpid" 2>/dev/null; rc=$?
  clean_gpu
  after=$(count_done)
  echo "[cycle $cycle] done=$after/$TOTAL (rc=$rc, +$((after-before)))"
  if grep -q "DONE" "$OUT/.cycle.log" 2>/dev/null && [ "$after" -ge "$TOTAL" ]; then
    echo "ALL DONE: $after/$TOTAL"; break
  fi
  if [ "$after" -le "$before" ]; then
    stall=$((stall+1))
    echo "[cycle $cycle] no progress (stall $stall/$MAX_STALL)"
    if [ "$stall" -ge "$MAX_STALL" ]; then echo "GIVING UP at $after/$TOTAL after $stall stalls"; break; fi
  else
    stall=0
  fi
done
echo "SUPERVISOR EXIT: $(count_done)/$TOTAL"
