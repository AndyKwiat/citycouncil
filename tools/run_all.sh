#!/bin/bash
# Summarize councils' missing meetings one council at a time (so only one Whisper job ever runs), then publish
# (search index + deploy, site build + deploy). If a batch reports a real usage/rate limit, its script exits 3 and
# this stops at once without publishing.
#   tools/run_all.sh "kitchener 8 40" "guelph 2 30"      (city, batches, batch size)
cd "$(dirname "$0")/.." || exit 1
run=state/logs/run_all-$(date +%Y%m%d-%H%M%S)
mkdir -p "$run"

for spec in "$@"; do
  set -- $spec
  echo "$(date +%T) starting $1"
  STOP_ON_LIMIT=1 tools/summarize_batches.sh "$1" "$2" "$3" > "$run/$1.out" 2>&1
  code=$?
  if [ $code -eq 3 ]; then
    echo "$(date +%T) $1 hit a usage limit; stopping without publishing (see $run/$1.out)"
    rm -rf data/*/raw/*/tmp*/ 2>/dev/null; find data -name "*.tmp" -delete 2>/dev/null
    exit 2
  fi
  echo "$(date +%T) finished $1 (exit $code)"
done

echo "$(date +%T) publishing"
.venv/bin/python -m unittest discover tests > "$run/tests.log" 2>&1 || { echo "tests failed; not publishing"; exit 1; }
.venv/bin/python pipeline.py search-index > "$run/search-index.log" 2>&1 &&
.venv/bin/python pipeline.py search-deploy > "$run/search-deploy.log" 2>&1 &&
.venv/bin/python pipeline.py build > "$run/build.log" 2>&1 &&
.venv/bin/python pipeline.py deploy > "$run/deploy.log" 2>&1 || { echo "publish step failed; see $run"; exit 1; }
echo "$(date +%T) published"
