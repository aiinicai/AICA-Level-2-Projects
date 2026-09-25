"""PyWebView desktop shell and dynamic loopback Uvicorn server.

The browser-facing service is never bound to an external interface. A listening socket is
reserved by the process first, then handed directly to Uvicorn so there is no free-port race.
"""
from __future__ import annotations

import logging
import socket
import threading
import time
import http.client
from dataclasses import dataclass
from pathlib import Path

from app.core.config import AppConfig


class DesktopLaunchError(RuntimeError):
    """Raised when the local desktop shell cannot start safely."""


def reserve_loopback_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        return sock
    except Exception:
        sock.close()
        raise


@dataclass
class LocalServer:
    data_root: Path | str | None = None
    startup_timeout: float = 12.0

    def __post_init__(self) -> None:
        self.socket = reserve_loopback_socket()
        self.port = int(self.socket.getsockname()[1])
        self.url = f"http://127.0.0.1:{self.port}"
        self.server = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        import uvicorn
        from app.web.application import create_app

        cfg = AppConfig(host="127.0.0.1", port=self.port)
        application = create_app(data_root=self.data_root, config=cfg)
        uv_config = uvicorn.Config(
            application,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
            access_log=False,
            server_header=False,
            date_header=False,
        )
        self.server = uvicorn.Server(uv_config)
        self.thread = threading.Thread(
            target=self.server.run,
            kwargs={"sockets": [self.socket]},
            name="IBCExpertLocalServer",
            daemon=True,
        )
        self.thread.start()
        deadline = time.monotonic() + self.startup_timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=0.4)
                connection.request("GET", "/health")
                response = connection.getresponse()
                response.read()
                connection.close()
                if response.status == 200:
                    return
            except OSError as exc:
                last_error = exc
                time.sleep(0.08)
        self.stop()
        raise DesktopLaunchError(f"IBC Expert local service did not start correctly: {last_error}")

    def stop(self) -> None:
        if self.server is not None:
            self.server.should_exit = True
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        try:
            self.socket.close()
        except OSError as exc:
            logging.getLogger("ibc_expert.desktop").debug("Loopback socket already closed: %s", exc)


def run_desktop(*, data_root: Path | str | None = None) -> None:
    try:
        import webview
    except ImportError as exc:
        raise DesktopLaunchError(
            "PyWebView is not installed. Run the IBC Expert bootstrap/dependency setup first."
        ) from exc

    server = LocalServer(data_root=data_root)
    server.start()
    try:
        window = webview.create_window(
            "IBC Expert",
            server.url,
            width=1380,
            height=880,
            min_size=(980, 650),
            resizable=True,
            confirm_close=False,
            text_select=True,
        )
        try:
            window.events.closed += server.stop
        except Exception as exc:
            # The finally block remains authoritative even if a backend does not expose events.
            logging.getLogger("ibc_expert.desktop").debug("Window close event hook unavailable: %s", exc)
        webview.start(debug=False, private_mode=True)
    finally:
        server.stop()
