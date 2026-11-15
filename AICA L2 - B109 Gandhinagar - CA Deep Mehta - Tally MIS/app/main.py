"""Tally MIS desktop app: starts the local server, opens the window, and wipes all company data when it closes.

  TallyMIS.exe                    normal use (a window opens)
  TallyMIS.exe --no-window        server only, for tests; prints the address
  TallyMIS.exe --port 8765        use a fixed port (default: any free port)
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time

# A windowed (no console) build has no stdout/stderr; make logging safe and keep it free of company data.
for _name in ("stdout", "stderr"):
    if getattr(sys, _name) is None:
        setattr(sys, _name, open(os.devnull, "w"))

import uvicorn  # noqa: E402

from app.api.server import AppState, create_app, resource_path  # noqa: E402

TITLE = "Tally MIS"


def pick_socket(port: int) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    s.bind(("127.0.0.1", port))  # this PC only: no other computer can connect
    s.listen(50)
    return s


class Runtime:
    def __init__(self, port: int = 0, with_window: bool = True):
        self.state = AppState()
        self.sock = pick_socket(port)
        self.port = self.sock.getsockname()[1]
        self.state.allowed_hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        self.state.on_close = self.close
        self.window = None
        self.with_window = with_window
        self.app = create_app(self.state, resource_path("app/static"))
        self.server = uvicorn.Server(uvicorn.Config(self.app, log_level="warning", access_log=False, lifespan="off"))
        self.thread = threading.Thread(target=lambda: self.server.run(sockets=[self.sock]), daemon=True)
        self._closed = threading.Event()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def start(self) -> None:
        self.thread.start()
        for _ in range(100):
            if self.server.started:
                return
            time.sleep(0.05)
        raise RuntimeError("The local server did not start")

    def wipe(self) -> None:
        """Remove all company data from memory (idempotent)."""
        self.state.store.wipe()

    def close(self) -> None:
        """Wipe the data, then close the window / stop the server."""
        self.wipe()
        self._closed.set()
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
        self.server.should_exit = True

    def wait(self) -> None:
        self._closed.wait()


def run_window(rt: Runtime) -> bool:
    """Open the app window. Returns False if no window could be created (then the browser is used instead)."""
    try:
        import webview
    except Exception:
        return False
    storage = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TallyMIS", "webview")  # theme only, never company data
    try:
        os.makedirs(storage, exist_ok=True)
        rt.window = webview.create_window(TITLE, rt.url, width=1400, height=900, min_size=(1000, 640), text_select=True)
        webview.start(private_mode=False, storage_path=storage)
        return True
    except Exception:
        rt.window = None
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=TITLE)
    ap.add_argument("--no-window", action="store_true", help="run the server only (no window)")
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args(argv)
    rt = Runtime(args.port, with_window=not args.no_window)
    rt.start()
    try:
        if args.no_window:
            print(f"Tally MIS is running at {rt.url} (press Ctrl+C to stop)", flush=True)
            rt.wait()
        elif not run_window(rt):
            import webbrowser
            webbrowser.open(rt.url)
            rt.wait()
    except KeyboardInterrupt:
        pass
    finally:
        rt.close()  # closing the window ends here: data is wiped before the process exits
        rt.thread.join(timeout=3)
    return 0


if __name__ == "__main__":
    sys.exit(main())
