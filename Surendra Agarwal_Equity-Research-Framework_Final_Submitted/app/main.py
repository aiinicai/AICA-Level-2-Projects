"""Streamlit entrypoint. Run with: streamlit run app/main.py

Also supports `python -m app.main` as a convenience: when NOT already
running under the Streamlit script runner, this re-execs itself via
`streamlit run` so both invocation styles work identically.

IMPORTANT: Streamlit executes this file with __name__ == "__main__"
whether launched via `streamlit run` or re-exec'd from `python -m
app.main` below - so there must be exactly ONE call to the dashboard
here, not one at module level and another inside main(). An earlier
version of this file called it twice, which crashed Streamlit with a
duplicate-widget-ID error (caught by the AppTest smoke test in
tests/unit/test_dashboard.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

# When Streamlit runs this file directly (`streamlit run app/main.py`),
# it only adds THIS FILE'S OWN DIRECTORY (app/) to sys.path — not the
# project root above it. Since every import in this codebase is
# absolute (e.g. `from app.ui.dashboard import run`), Python needs the
# project root (the parent of app/) on sys.path, not app/ itself, or
# `import app` fails with "No module named 'app'" — a real error a
# user hit running `streamlit run app\main.py` from a fresh terminal,
# which the in-process AppTest-based test suite never caught (AppTest
# runs inside the same Python process as pytest, which already had the
# project root on sys.path from how the test itself was invoked).
# Inserting the project root here, before any `app.*` import is
# attempted, fixes this for every invocation style.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _running_under_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except ImportError:
        return False


def main() -> None:
    if _running_under_streamlit():
        from app.ui.dashboard import run
        run()
    else:
        # Launched as `python -m app.main` outside the Streamlit runtime -
        # re-exec via `streamlit run` so the script actually gets a
        # Streamlit context this time.
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__], check=True)


if __name__ == "__main__":
    main()
