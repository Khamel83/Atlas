#!/bin/bash
# Atlas Automated Test Script
# Runs all ingestion modes, captures outputs/errors, and summarizes results for LLM troubleshooting.

set -euo pipefail

LOGDIR="test_logs"
SUMMARY="$LOGDIR/summary.txt"
mkdir -p "$LOGDIR"
echo "# Atlas Test Run Summary" > "$SUMMARY"

run_and_log() {
  local desc="$1"
  local cmd="$2"
  local logfile="$LOGDIR/${desc// /_}.log"
  echo -e "\n## $desc" | tee -a "$SUMMARY"
  echo "Running: $cmd" | tee -a "$SUMMARY"
  start_time=$(date +%s)
  (
    eval "$cmd" 2>&1 &
    pid=$!
    interval=0
    while kill -0 $pid 2>/dev/null; do
      sleep 5
      interval=$((interval+5))
      if (( interval % 15 == 0 )); then
        echo "[Heartbeat] $desc still running after $interval seconds..." | tee -a "$SUMMARY"
      fi
    done
    wait $pid
    exit_code=$?
    end_time=$(date +%s)
    elapsed=$((end_time - start_time))
    echo "[Exit code: $exit_code] ($elapsed seconds)" | tee -a "$SUMMARY"
  ) | tee "$logfile" | tee -a "$SUMMARY"
  echo "---" | tee -a "$SUMMARY"
}

# Test all modes
run_and_log "Full Pipeline" "python run.py"
run_and_log "Articles Only" "python run.py --articles"
run_and_log "Podcasts Only" "python run.py --podcasts"
run_and_log "YouTube Only" "python run.py --youtube"

# List outputs
echo -e "\n## Output Directory Structure" | tee -a "$SUMMARY"
find output/ | tee -a "$SUMMARY"

# Show error and retry summary
if grep -q 'Error & Retry Summary' "$LOGDIR/Full_Pipeline.log"; then
  echo -e "\n## Error & Retry Summary (from Full Pipeline)" | tee -a "$SUMMARY"
  awk '/Error & Retry Summary/,/End of Error & Retry Summary/' "$LOGDIR/Full_Pipeline.log" | tee -a "$SUMMARY"
fi

# Show recent errors from logs
echo -e "\n## Recent Errors from Logs" | tee -a "$SUMMARY"
grep -i error output/*/ingest.log | tee -a "$SUMMARY" || echo "No errors found." | tee -a "$SUMMARY"

echo -e "\n## Test Run Complete. See $SUMMARY for details.\n" | tee -a "$SUMMARY"

# Automatically parse the summary for next actions
python3 parse_test_summary.py 