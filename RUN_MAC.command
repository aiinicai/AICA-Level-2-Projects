#!/bin/bash
cd "$(dirname "$0")"
echo "Checking / installing required packages (first run takes a few minutes)..."
python3 -m pip install -r requirements.txt --upgrade --quiet --disable-pip-version-check
echo
python3 portfolio_analyzer.py "$@"
