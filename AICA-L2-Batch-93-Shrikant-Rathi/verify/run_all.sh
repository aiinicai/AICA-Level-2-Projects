#!/usr/bin/env bash
# Full verification: reference engine vs app on a dataset, functional tests, smoke test.
# Usage: verify/run_all.sh <dataset.json> <LookThrough.html>
set -e
cd "$(dirname "$0")"
DS=${1:-../data/live/dataset.json}; APP=${2:-../app/LookThrough.html}
export NODE_PATH=${NODE_PATH:-$(npm root -g)}
python3 recompute.py "$DS"
node reconcile_app.js "$APP"
node functional.js "$APP"
node smoke.js "$APP"
