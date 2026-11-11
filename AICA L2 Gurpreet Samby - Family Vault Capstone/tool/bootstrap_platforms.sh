#!/usr/bin/env bash
#
# Generates the Android, Windows and web platform projects that Flutter needs,
# without touching application code.
#
# Why this exists: the environment that authors this project has no Flutter or
# Android SDK and cannot reach pub.dev, dl.google.com, maven.google.com or
# services.gradle.org, so it cannot run `flutter create`. Rather than
# hand-writing a Gradle and CMake project blind, CI generates them from
# Flutter's own templates on the first run. The generated directories are then
# committed, after which this script is a no-op.
#
# It copies a platform directory only when that directory is absent, so it can
# never overwrite real, committed platform code.
#
# See docs/decisions-and-risks.md, decision D-004.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ORG="com.casamby"
PROJECT_NAME="family_vault"
DESCRIPTION="Family Vault - a secure, offline-first, zero-knowledge password manager."

missing=()
for dir in android windows web; do
  if [ ! -d "$ROOT/$dir" ]; then
    missing+=("$dir")
  fi
done

if [ ${#missing[@]} -eq 0 ]; then
  echo "bootstrap: android, windows and web already present - nothing to do."
  exit 0
fi

echo "bootstrap: generating ${missing[*]}"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

# Generated in a scratch directory, never in place, so application code and
# pubspec.yaml cannot be overwritten by the template.
flutter create \
  --platforms=android,windows,web \
  --org "$ORG" \
  --project-name "$PROJECT_NAME" \
  --description "$DESCRIPTION" \
  --template=app \
  "$SCRATCH/scaffold" >/dev/null

for dir in "${missing[@]}"; do
  cp -R "$SCRATCH/scaffold/$dir" "$ROOT/$dir"
  echo "bootstrap: generated $dir/"
done

echo "bootstrap: done."
