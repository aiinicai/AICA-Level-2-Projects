"""
Desktop launcher.

Starts the server and opens the browser only once the port is actually
accepting connections. Opening the browser first is a race the browser
usually loses, and the user is shown a connection-refused page while the
server is still coming up two seconds behind it.

    python -m auditlens.launch              # start, and open the browser
    python -m auditlens.launch --no-browser # start only
    python -m auditlens.launch --port 8080  # a particular port
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser

HOST = "127.0.0.1"
DEFAULT_PORT = 8000
PORT_ATTEMPTS = 20


def find_free_port(preferred: int = DEFAULT_PORT, attempts: int = PORT_ATTEMPTS) -> int:
    """The first free port at or after `preferred`.

    Port 8000 is popular; another application holding it should move
    AuditLens along rather than stop it.
    """
    for port in range(preferred, preferred + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((HOST, port))
            except OSError:
                continue
            return port
    raise SystemExit(
        f"Could not find a free port between {preferred} and "
        f"{preferred + attempts - 1}. Close some applications and try again."
    )


def is_listening(port: int, timeout: float = 0.4) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(timeout)
        return probe.connect_ex((HOST, port)) == 0


def open_when_ready(port: int, wait_seconds: float = 90.0) -> None:
    """Poll until the server answers, then open the browser."""
    url = f"http://{HOST}:{port}"
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if is_listening(port):
            print(f"\n  AuditLens is ready at {url}\n", flush=True)
            try:
                webbrowser.open(url)
            except Exception:
                print(f"  Could not open the browser. Go to {url} yourself.", flush=True)
            return
        time.sleep(0.25)
    print(
        f"\n  The server did not start within {wait_seconds:.0f} seconds. "
        f"If it starts shortly, open {url} yourself.\n",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="auditlens-app", description="Start AuditLens and open it in a browser."
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--no-browser", action="store_true",
                        help="Start the server without opening a browser.")
    parser.add_argument("--reload", action="store_true", help="Reload on code changes.")
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError:
        print(
            "AuditLens is not installed in this environment.\n"
            'Run:  pip install -e ".[dev]"',
            file=sys.stderr,
        )
        return 1

    port = find_free_port(args.port) if args.host == HOST else args.port
    if port != args.port:
        print(f"  Port {args.port} is in use; using {port} instead.")

    print("=" * 62)
    print("  AuditLens - statutory audit analytical review")
    print("=" * 62)
    print(f"  Starting at http://{args.host}:{port}")
    print("  The browser will open by itself once the server is ready.")
    print("  Press Ctrl+C, or close this window, to stop it.")
    print("=" * 62)

    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(port,), daemon=True).start()

    try:
        uvicorn.run(
            "auditlens.api:app",
            host=args.host,
            port=port,
            reload=args.reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n  AuditLens stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
