"""One-command startup. Build Prompt v2 §1.

    python run.py

Binds to 127.0.0.1 by default — the firm's LAN, never the public internet.
"""

from __future__ import annotations

import sys

import uvicorn

from app.config import get_settings


def main() -> int:
    settings = get_settings()
    settings.ensure_directories()

    default_key = "change-me-before-first-run"
    if settings.env != "development" and settings.secret_key == default_key:
        print("Refusing to start: AUDITCRAFT_SECRET_KEY is still the default.", file=sys.stderr)
        return 1

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.env == "development",
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
