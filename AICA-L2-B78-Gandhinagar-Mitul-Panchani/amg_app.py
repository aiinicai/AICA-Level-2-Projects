"""Portable Windows entry point for the AI Memory Governance web demo."""

from __future__ import annotations

import socket
import sys
import threading
import webbrowser
from pathlib import Path


def _application_root() -> Path:
    """Resolve PyInstaller's extraction root or this source checkout."""

    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root)
    return Path(__file__).resolve().parent


if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(_application_root() / "src"))


def _free_local_port(start: int = 8000, attempts: int = 200) -> int:
    """Find a localhost port so a second copy does not crash on startup."""

    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            try:
                candidate.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(
        f"No free localhost port was found between {start} and {start + attempts - 1}."
    )


def _print_banner(url: str) -> None:
    border = "=" * 68
    print(border)
    print("AI Memory Governance & Audit Layer")
    print(f"Open in your browser: {url}")
    print("Offline mode - no API keys needed (optional recipient keys enable live mode)")
    print("Close this window or press Ctrl+C to stop")
    print(border, flush=True)


def _pause_after_failure() -> None:
    try:
        input("Press Enter to close...")
    except (EOFError, KeyboardInterrupt):
        pass


def main() -> int:
    try:
        import uvicorn

        from amg.web.app import app

        port = _free_local_port()
        url = f"http://127.0.0.1:{port}"
        _print_banner(url)
        browser_timer = threading.Timer(1.0, webbrowser.open, args=(url,))
        browser_timer.daemon = True
        browser_timer.start()
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
        )
        return 0
    except KeyboardInterrupt:
        print("\nAI Memory Governance stopped.")
        return 0
    except SystemExit as exc:
        print("\nAI Memory Governance could not start.")
        print(f"Reason: the local web server stopped during startup (code {exc.code}).")
        print("No data was sent anywhere by this startup failure.")
        _pause_after_failure()
        return 1
    except Exception as exc:
        print("\nAI Memory Governance could not start.")
        print(f"Reason: {exc}")
        print("No data was sent anywhere by this startup failure.")
        _pause_after_failure()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
