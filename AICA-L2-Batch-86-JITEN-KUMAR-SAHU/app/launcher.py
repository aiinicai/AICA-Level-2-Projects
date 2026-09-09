"""
=============================================================
  ClientLedger India — Desktop Launcher
=============================================================
This is the entry point PyInstaller builds into the installed
app (both Windows .exe and macOS .app). It:

  1. Starts the existing Flask + Playwright server (gst_rpa.py)
     in a background thread, exactly as before.
  2. Opens a native desktop window (via pywebview) pointed at
     that local server, so the accountant gets a real app window
     instead of "please open your browser to localhost:8765".

Running `python gst_rpa.py` directly (the old way) still works
unchanged for anyone who prefers the browser-tab workflow.
=============================================================
"""

import sys
import os
import threading
import time

# Force UTF-8 console output, with a crash-proof fallback if that isn't
# fully honoured by this environment — see the matching (and more
# detailed) comment in gst_rpa.py for why this two-layer approach
# matters on Windows.
class _SafeStream:
    def __init__(self, stream):
        self._stream = stream
        self._encoding = getattr(stream, "encoding", None) or "utf-8"

    def write(self, s):
        try:
            return self._stream.write(s)
        except UnicodeEncodeError:
            safe = s.encode(self._encoding, errors="replace").decode(self._encoding, errors="replace")
            return self._stream.write(safe)
        except Exception:
            return 0

    def flush(self):
        try:
            self._stream.flush()
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self._stream, name)


for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is None:
        continue
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        setattr(sys, _stream_name, _SafeStream(_stream))
    except Exception:
        pass


def _app_dir():
    """Directory bundled data files (templates, pw-browsers) live in — the
    PyInstaller onedir/_internal folder when frozen (sys._MEIPASS is the
    officially documented, version-agnostic way to find it), or this
    file's own folder when run from source."""
    return getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))


_APP_DIR = _app_dir()

# Make sure we can import gst_rpa.py, config.py, dbstore.py regardless
# of the working directory PyInstaller launches from.
sys.path.insert(0, _APP_DIR)

# ── Chromium bundled with the app ───────────────────────────────────
# The build scripts install Chromium with PLAYWRIGHT_BROWSERS_PATH=0,
# which puts it inside the playwright package itself, at
# playwright/driver/package/.local-browsers/... — PyInstaller bundles
# that whole folder (see the *.spec files), and Playwright's own
# driver already looks there by default, so no env var override is
# needed at runtime; this just has to exist in the same place it was
# installed to.

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


def _start_server():
    import gst_rpa  # noqa: F401 — importing runs module-level setup (config, dbstore.init)
    # gst_rpa.app is the Flask app object; run it here instead of relying on
    # gst_rpa's own `if __name__ == "__main__"` block (which also tries to
    # auto-open a browser tab — we don't want that in the desktop build).
    gst_rpa.app.run(host=HOST, port=PORT, debug=False, threaded=True, use_reloader=False)


def main():
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    # Give Flask a moment to bind before pointing a window at it.
    time.sleep(1.2)

    try:
        import webview
    except ImportError:
        # pywebview not installed (e.g. running from source without the
        # desktop extra) — fall back to the plain browser-tab workflow.
        import webbrowser
        webbrowser.open(URL)
        print(f"pywebview not installed — opened {URL} in your default browser instead.")
        print("Install the desktop window with:  pip install pywebview")
        while True:
            time.sleep(3600)
        return

    webview.create_window("ClientLedger India", URL, width=1360, height=860, min_size=(1000, 640))
    # debug=True enables right-click -> Inspect (real browser DevTools) —
    # extremely useful for tracking down issues like a generic "Failed
    # to fetch" error (blocked by CORS, connection refused, blocked by
    # local security software, etc. all look identical from JS's
    # perspective, but very different in DevTools' Network/Console
    # tabs). BUT on this app's WebView2 backend, debug=True doesn't just
    # make Inspect available — it auto-opens a DevTools window on every
    # single launch, which is exactly what you don't want for normal
    # day-to-day use. So this is opt-in only, via an environment
    # variable, rather than always on: set CLIENTLEDGER_DEBUG=1 before
    # launching the app if you need to diagnose a network/fetch issue.
    _debug = os.environ.get("CLIENTLEDGER_DEBUG") == "1"
    webview.start(debug=_debug)


if __name__ == "__main__":
    main()
