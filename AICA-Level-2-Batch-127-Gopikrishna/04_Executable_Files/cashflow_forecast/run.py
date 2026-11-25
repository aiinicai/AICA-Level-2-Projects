"""Start the server:  .venv\\Scripts\\python.exe run.py   (or double-click start_app.bat)

Listens on 127.0.0.1 by default. To serve the intranet, set CFF_HOST and the two
CFF_SSL_* variables; the app refuses a non-loopback address without HTTPS.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_PY = HERE / ".venv" / "Scripts" / "python.exe"

try:
    import uvicorn

    from app.core.config import get_settings
except ModuleNotFoundError as exc:          # started with the system Python (e.g. IDLE / F5), not the venv
    sys.exit(
        f"\nMissing package: {exc.name}\n\n"
        "This Python does not have the app's libraries. They are installed in the project's\n"
        "virtual environment. Start the app in one of these ways instead:\n\n"
        f"  1. Double-click  {HERE / 'start_app.bat'}\n"
        f"  2. In PowerShell:  & \"{VENV_PY}\" \"{HERE / 'run.py'}\"\n\n"
        "(Running run.py from IDLE uses the system Python, which does not see the virtual environment.)\n")


def main() -> None:
    s = get_settings()
    s.check_network_safety()
    kwargs = {}
    if s.https_enabled:
        kwargs = {"ssl_certfile": str(s.ssl_certfile), "ssl_keyfile": str(s.ssl_keyfile)}
    scheme = "https" if s.https_enabled else "http"
    print(f"Cash Flow Forecast on {scheme}://{s.host}:{s.port}  (database: {s.database_path})")
    print("Press Ctrl+C to stop.")
    uvicorn.run("app.main:app", host=s.host, port=s.port, proxy_headers=False, **kwargs)


if __name__ == "__main__":
    main()
