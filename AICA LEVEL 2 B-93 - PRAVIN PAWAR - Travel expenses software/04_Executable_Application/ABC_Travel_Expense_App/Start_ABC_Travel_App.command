#!/usr/bin/env bash
# ABC Travel & Expense - start on macOS / Linux.   Usage: ./start_mac_linux.sh  [--demo]
cd "$(dirname "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is not installed. Install Node.js 22 LTS or newer from https://nodejs.org (macOS: brew install node)"; exit 1
fi
node launch.js "$@"
