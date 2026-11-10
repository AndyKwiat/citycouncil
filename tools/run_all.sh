#!/bin/bash
# Summarize every council's missing meetings at once, then publish (search index + deploy, site build + deploy).
# If the claude CLI reports a usage/token limit, everything is stopped (no waiting) and nothing is published.
#   tools/run_all.sh
cd "$(dirname "$0")/.." || exit 1
mkdir -p state/logs
run=state/logs/run_all-$(date +%Y%m%d-%H%M%S)
mkdir -p "$run"
LIMIT='usage limit|limit reached|hit your limit|out of (extra )?usage|credit balance|weekly limit|session limit'

stop_all() {
  echo "$(date +%T) stopping everything: $1"
  pkill -TERM -f "tools/summarize_batches.sh" ; pkill -TERM -f "pipeline.py process"
  pkill -TERM -f "claude -p --model" ; pkill -TERM -f "ffmpeg.*-hide_banner -loglevel error"
  sleep 5
  rm -rf data/*/raw/*/tmp*/ 2>/dev/null
  find data -name "*.tmp" -delete 2>/dev/null
  exit 2
}

pids=()
for spec in "guelph 3 30" "waterloo 2 40" "centre-wellington 3 40" "region-of-waterloo 6 40" "kitchener 8 40"; do
  set -- $spec
  STOP_ON_LIMIT=1 tools/summarize_batches.sh "$1" "$2" "$3" > "$run/$1.out" 2>&1 &
  pids+=($!)
  echo "$(date +%T) started $1 (pid $!)"
done

start=$(date +%s)
while :; do
  alive=0
  for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && alive=1; done
  # Only logs written by this run count.
  new_logs=$(find state/logs -maxdepth 1 -name "*-summaries-*.log" -newermt "@$start" 2>/dev/null)
  if [ -n "$new_logs" ]; then
    if grep -qiE "$LIMIT" $new_logs "$run"/*.out 2>/dev/null; then stop_all "usage limit reported"; fi
    fails=$(cat $new_logs | grep -c "claude failed")
    [ "$fails" -ge 5 ] && stop_all "$fails summary calls failed"
  fi
  [ $alive -eq 0 ] && break
  sleep 60
done
echo "$(date +%T) all batches finished"
grep -qiE "$LIMIT" "$run"/*.out && stop_all "usage limit reported"

echo "$(date +%T) publishing"
.venv/bin/python -m unittest discover tests > "$run/tests.log" 2>&1 || { echo "tests failed; not publishing"; exit 1; }
.venv/bin/python pipeline.py search-index > "$run/search-index.log" 2>&1 &&
.venv/bin/python pipeline.py search-deploy > "$run/search-deploy.log" 2>&1 &&
.venv/bin/python pipeline.py build > "$run/build.log" 2>&1 &&
.venv/bin/python pipeline.py deploy > "$run/deploy.log" 2>&1 || { echo "publish step failed; see $run"; exit 1; }
echo "$(date +%T) published"
