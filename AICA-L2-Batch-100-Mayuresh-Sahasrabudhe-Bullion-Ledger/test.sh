#!/bin/zsh
# Bullion Ledger - Test Runner
export PATH="/Users/sahamay/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:/Users/sahamay/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback:$PATH"
cd "$(dirname "$0")"
pnpm test
