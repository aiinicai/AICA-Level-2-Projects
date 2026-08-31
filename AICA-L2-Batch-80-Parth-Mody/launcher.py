"""Entry point for the packaged Personal Finance & Debt Impact Calculator.

Streamlit is normally started by its own CLI, which does not exist inside a
frozen build. This drives Streamlit's bootstrap in-process instead, picks a free
port so a second copy cannot collide with the first, and opens the browser.

Run with --selftest to exercise the engine, the audit and the Excel export
inside the bundle and exit — proof that every dependency really came along.
"""
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_FILE = "Finance.py"
TITLE = "Personal Finance & Debt Impact Calculator"

# Streamlit reads most settings from the environment at import time, so these
# must be set before anything imports streamlit.
os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")
os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")
os.environ.setdefault("STREAMLIT_LOGGER_LEVEL", "warning")


def base_dir() -> Path:
    """Where the bundled data lives: the PyInstaller app dir when frozen."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def config_home() -> Path:
    """A writable home for Streamlit's config, so a roaming or locked-down
    profile cannot stop the app starting."""
    root = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    home = root / "FinancePlanner"
    home.mkdir(parents=True, exist_ok=True)
    return home


def free_port(preferred: int = 8501) -> int:
    """First port that will actually bind, so two open copies do not clash."""
    for port in [preferred, *range(8502, 8600)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def open_browser_when_ready(port: int, timeout: float = 120.0) -> None:
    """Poll the port and open the browser once the server answers, rather than
    guessing a fixed delay — a cold first start can be slow."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                webbrowser.open(f"http://localhost:{port}")
                return
        time.sleep(0.4)


def selftest() -> int:
    """Exercise the real engine inside the frozen bundle and report."""
    print(f"{TITLE} — self test\n")
    sys.path.insert(0, str(base_dir()))
    failures = 0
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "finance_engine", str(base_dir() / APP_FILE))
        eng = importlib.util.module_from_spec(spec)
        sys.modules["finance_engine"] = eng
        spec.loader.exec_module(eng)
        print(f"  [ok] loaded {APP_FILE} (v{eng.VER})")
    except Exception as exc:                                    # noqa: BLE001
        print(f"  [FAIL] could not load {APP_FILE}: {exc!r}")
        return 1

    scen = dict(return_shift=0.0, expense_shift=0.0, rate_bps=0.0,
                market_shock=0.0, income_loss_pct=0.0, income_loss_months=0)
    try:
        profile = eng.demo()
        profile["_tax"] = eng.TaxConfig.from_dict(profile["tax"])
        sim = eng.simulate(profile, dict(scen))
        sim.audit = eng.audit(sim, profile)
        passed = int((sim.audit["Result"] == "PASS").sum())
        total = len(sim.audit)
        print(f"  [ok] projection ran: {len(sim.monthly)} months, "
              f"{len(sim.loans)} loans")
        print(f"  {'[ok]' if passed == total else '[FAIL]'} audit: "
              f"{passed}/{total} identity tests passed")
        failures += passed != total
    except Exception as exc:                                    # noqa: BLE001
        print(f"  [FAIL] engine: {exc!r}")
        return 1

    for label, fn in (
        ("Excel report (xlsxwriter)",
         lambda: eng.report_bytes(profile, sim, eng.optimise(sim, profile),
                                  eng.advice(sim, profile,
                                             eng.optimise(sim, profile)),
                                  eng.levers(sim, profile), sim.audit)),
        ("Excel input template", lambda: eng.template_bytes(profile)),
        ("JSON profile", lambda: eng.to_json(profile).encode()),
    ):
        try:
            size = len(fn())
            print(f"  [ok] {label}: {size / 1024:.0f} KB")
        except Exception as exc:                                # noqa: BLE001
            print(f"  [FAIL] {label}: {exc!r}")
            failures += 1

    for mod in ("pandas", "numpy", "plotly.graph_objects", "xlsxwriter",
                "openpyxl", "streamlit", "pyarrow"):
        try:
            __import__(mod)
            print(f"  [ok] import {mod}")
        except Exception as exc:                                # noqa: BLE001
            print(f"  [FAIL] import {mod}: {exc!r}")
            failures += 1

    print("\n  RESULT:", "ALL CHECKS PASSED" if not failures
          else f"{failures} CHECK(S) FAILED")
    return 1 if failures else 0


def main() -> None:
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())

    app_path = base_dir() / APP_FILE
    if not app_path.exists():
        raise SystemExit(f"[error] {APP_FILE} is missing from {base_dir()}")

    home = config_home()
    os.environ.setdefault("STREAMLIT_HOME", str(home))
    os.environ.setdefault("HOME", str(home))

    port = free_port()

    from streamlit import config as st_config
    from streamlit.web import bootstrap

    options = {
        "server.port": port,
        "server.address": "127.0.0.1",     # local only; nothing is exposed
        "server.headless": True,           # we open the browser ourselves
        "server.fileWatcherType": "none",  # nothing to watch in a frozen build
        "browser.gatherUsageStats": False,
        "global.developmentMode": False,
    }
    for key, value in options.items():
        st_config.set_option(key, value)

    print(f"\n  {TITLE}")
    print(f"  Opening http://localhost:{port} in your browser.")
    print("  Keep this window open while you use the app. Close it to quit.\n")

    threading.Thread(target=open_browser_when_ready, args=(port,),
                     daemon=True).start()
    bootstrap.run(str(app_path), False, [], options)


if __name__ == "__main__":
    main()
