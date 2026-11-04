#!/bin/zsh
# Bullion Ledger - Dev Server Launcher
export PATH="/Users/sahamay/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:/Users/sahamay/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback:$PATH"
cd "$(dirname "$0")"
pnpm dev
