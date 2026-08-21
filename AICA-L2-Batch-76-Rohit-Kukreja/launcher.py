"""Entry point for the packaged Windows build.

Double-clicking AuditCraft.exe should end with the application open in a
browser and nothing else asked of the user. That means: find somewhere to put
the data, create the database if this is the first run, pick a port that is
actually free, start the server, and open a browser at it.

Run from source with `python launcher.py` to exercise exactly this path.
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
import time
import webbrowser

HOST = "127.0.0.1"
# The default the source build uses. Tried first so a developer's bookmarks keep
# working, but never insisted on -- port 8000 is one of the most contended on a
# Windows machine and a colleague should not have to know that.
PREFERRED_PORTS = (8000, 8731, 8732, 8733, 0)


def _free_port() -> int:
    """The first preferred port nothing is listening on.

    A port already in use is the commonest reason a local tool appears to start
    and then shows someone else's application, or a blank page. `0` at the end
    of the list asks the operating system for any free port, so this cannot fail
    outright.
    """
    for candidate in PREFERRED_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((HOST, candidate))
            except OSError:
                continue
            return int(probe.getsockname()[1])
    raise RuntimeError("no free port")


def _open_browser_when_ready(url: str, timeout: float = 30.0) -> None:
    """Open the browser once the server answers, not before.

    Opening immediately shows a connection error on a slow machine, and the
    person then reloads a page that was going to work anyway.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.5)
            if probe.connect_ex((HOST, int(url.rsplit(":", 1)[1]))) == 0:
                webbrowser.open(url)
                return
        time.sleep(0.25)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    # Line-buffered, or the banner below -- which carries the address to open --
    # sits in a buffer until the process exits. Python buffers aggressively when
    # stdout is not a terminal, which is what a redirected or piped console is.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    # Imported here, not at module scope: these pull in SQLAlchemy, FastAPI and
    # the clause repository, and a failure while doing so should be reported
    # under the banner below rather than as a bare traceback on a black window.
    from app.bootstrap import first_run
    from app.config import USER_DATA_ROOT

    print("=" * 62)
    print("  AuditCraft")
    print("=" * 62)
    print(f"  Your data:  {USER_DATA_ROOT}")
    print()

    try:
        first_run()
    except Exception as exc:
        print(f"  Could not prepare the database: {exc}")
        print("  The folder above must be writable by your Windows account.")
        input("\n  Press Enter to close.")
        return 1

    port = _free_port()
    url = f"http://{HOST}:{port}"
    print(f"  Open in a browser:  {url}")
    print("  Keep this window open while you work. Close it to stop.")
    print("=" * 62)

    threading.Thread(target=_open_browser_when_ready, args=(url,), daemon=True).start()

    import uvicorn

    from app.main import app

    # The app object, not "app.main:app": the string form re-imports by name,
    # which a frozen build resolves differently. Reload is off for the same
    # reason -- it re-executes the entry point, and in a bundle that starts a
    # second copy of the whole application.
    uvicorn.run(app, host=HOST, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.exit(0)
