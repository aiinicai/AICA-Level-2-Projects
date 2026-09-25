"""Primary source-mode desktop launcher for IBC Expert.

The bootstrap progress layer intentionally imports only stdlib-dependent project code before
third-party modules are loaded.
"""
from pathlib import Path

from app.core.bootstrap_ui import run_bootstrap_progress


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    run_bootstrap_progress(root)
    from app.desktop import run_desktop

    run_desktop()
