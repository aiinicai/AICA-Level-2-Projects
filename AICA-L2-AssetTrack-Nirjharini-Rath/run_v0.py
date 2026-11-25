"""Local-only Windows launcher for AssetTrack v0 (binds 127.0.0.1 and auto-opens browser)."""

from __future__ import annotations

import sys
import threading
import time
import webbrowser

import uvicorn

from app import config
from app.main import app
from seed_v0 import seed_if_empty


def _open_browser_later(url: str, delay: float = 1.4) -> None:
    def _worker() -> None:
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def main() -> None:
    seed_if_empty()
    url = f"http://127.0.0.1:{config.PORT}"
    print("=" * 56)
    print(f"  {config.COMPANY_NAME} — AssetTrack v0")
    print(f"  Local URL : {url}")
    print("  Press Ctrl+C to stop.")
    print("=" * 56)
    _open_browser_later(url)
    try:
        uvicorn.run(app, host="127.0.0.1", port=config.PORT, log_level="info")
    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        if getattr(sys, "frozen", False):
            input("Press Enter to close...")
        raise


if __name__ == "__main__":
    main()
