"""
main.py
--------
Application entry point.

Startup sequence:
    1. bootstrap.ensure_dependencies() — detect/install any missing
       third-party packages, with a visible installer log window (skipped
       entirely when running from a frozen .exe, which already bundles
       everything). If packages were freshly installed, the process
       restarts itself cleanly so the new interpreter picks them up.
    2. Minimal audit logging setup (event types/timestamps only — never
       passwords, face images, or key material).
    3. Launch the Tkinter GUI.
"""

from __future__ import annotations

import logging
import os
import sys

import bootstrap
import config


def _setup_logging() -> None:
    config.ensure_dirs()
    logging.basicConfig(
        filename=str(config.AUDIT_LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("folder_lock").info("application started")


def main() -> None:
    try:
        ready = bootstrap.ensure_dependencies()
    except bootstrap._RestartRequired:
        # Freshly installed a C-extension package (e.g. opencv/dlib) — the
        # current interpreter cannot see it without a clean restart.
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return  # unreachable; os.execv replaces this process

    if not ready:
        print(
            "Required dependencies could not be installed. "
            "Folder Lock cannot start. See the installer log for details.",
            file=sys.stderr,
        )
        sys.exit(1)

    _setup_logging()
    import ui

    app = ui.App()
    app.mainloop()


if __name__ == "__main__":
    main()
