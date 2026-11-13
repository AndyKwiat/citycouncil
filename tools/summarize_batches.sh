#!/bin/bash
# Summarize a council's missing meetings in batches, back to back. A batch that hits the claude CLI's usage limit
# waits and is retried. Publishing (index, deploys) is left to the operator.
#   tools/summarize_batches.sh <city> <batches> [batch size]
cd "$(dirname "$0")/.." || exit 1
city=$1; batches=$2; size=${3:-30}
mkdir -p state/logs
source tools/limit_pattern.sh
for n in $(seq 1 "$batches"); do
  for try in 1 2 3 4 5 6; do
    log=state/logs/$city-summaries-$(date +%Y%m%d-%H%M%S).log
    echo "batch $n try $try -> $log"
    .venv/bin/python pipeline.py process --city "$city" --latest "$size" --steps parse,transcribe,summarize > "$log" 2>&1
    grep -E "^Done:|No meetings|no meetings" "$log" | tail -1
    grep -qiE "no meetings to process" "$log" && exit 0
    if grep -qiE "$LIMIT" "$log"; then
      [ -n "$STOP_ON_LIMIT" ] && { echo "usage limit hit; stopping"; exit 3; }
      echo "usage limit hit; waiting 30 minutes"; sleep 1800; continue
    fi
    break
  done
done
