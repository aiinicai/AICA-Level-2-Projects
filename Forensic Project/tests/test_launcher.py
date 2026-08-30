"""
Regression tests for the launcher.

Two separate defects stopped the application from starting on a machine where
the engine itself ran perfectly:

  1. The launcher rejected Python 3.14 by version number. The dependencies
     imported fine on 3.14 and a full analysis completed on it.
  2. Streamlit's first-run prompt asks for an email on standard input. In a
     double-clicked window that reads as a hang, and the window closes.

Both are cheap to reintroduce, so both are pinned here, along with the batch
file properties that make failures visible rather than silent.
"""
import importlib.util
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCH_PY = os.path.join(ROOT, "scripts", "launch.py")
RUN_BAT = os.path.join(ROOT, "run_app.bat")
RUN_DESKTOP_BAT = os.path.join(ROOT, "run_desktop.bat")


@pytest.fixture(scope="module")
def launcher():
    spec = importlib.util.spec_from_file_location("rfe_launch", LAUNCH_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------- capability
def test_interpreter_is_judged_by_capability_not_version(launcher):
    """No comparison against sys.version_info may gate the launch."""
    source = open(LAUNCH_PY, encoding="utf-8").read()
    gates = re.findall(r"sys\.version_info\s*[<>=]", source)
    assert not gates, f"launch.py must not gate on the version number: {gates}"


def test_current_interpreter_is_accepted_when_dependencies_are_present(launcher):
    assert launcher.can_import_all(sys.executable) is True


def test_absent_interpreter_is_rejected_without_raising(launcher):
    assert launcher.can_import_all(os.path.join(ROOT, "no", "such", "python")) is False


def test_missing_packages_names_exactly_what_is_absent(launcher, monkeypatch):
    monkeypatch.setattr(launcher, "NEEDED", ["os", "json", "not_a_real_module_xyz"])
    assert launcher.missing_packages(sys.executable) == ["not_a_real_module_xyz"]


def test_every_module_the_app_imports_is_declared(launcher):
    """NEEDED must not drift from what app.py actually imports."""
    app_source = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    for module, marker in [
        ("streamlit", "import streamlit"),
        ("pandas", "import pandas"),
        ("numpy", "import numpy"),
        ("plotly", "import plotly"),
    ]:
        if marker in app_source:
            assert module in launcher.NEEDED, f"{module} is imported but not checked"


# ------------------------------------------------------- first-run prompt
def test_streamlit_first_run_prompt_is_suppressed(launcher, monkeypatch, tmp_path):
    """A fresh profile must get a credentials file, or Streamlit blocks on stdin."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(home) if p == "~" else p)

    assert launcher.ensure_streamlit_credentials() is True
    written = home / ".streamlit" / "credentials.toml"
    assert written.exists(), "no credentials file written — Streamlit would prompt"
    assert "email" in written.read_text()

    # Idempotent: an existing file is never overwritten.
    written.write_text('[general]\nemail = "someone@example.com"\n')
    assert launcher.ensure_streamlit_credentials() is True
    assert "someone@example.com" in written.read_text()


def test_launch_command_disables_usage_stats_and_pins_the_port():
    source = open(LAUNCH_PY, encoding="utf-8").read()
    assert "--browser.gatherUsageStats" in source
    assert "--server.port" in source


# ----------------------------------------------------------- batch files
@pytest.mark.parametrize("path", [RUN_BAT, RUN_DESKTOP_BAT])
def test_batch_files_use_crlf_line_endings(path):
    """cmd.exe mishandles GOTO and labels in LF-only batch files."""
    raw = open(path, "rb").read()
    assert b"\r\n" in raw, f"{os.path.basename(path)} has no CRLF line endings"
    lone_lf = re.findall(rb"(?<!\r)\n", raw)
    assert not lone_lf, f"{os.path.basename(path)} mixes LF and CRLF endings"


@pytest.mark.parametrize("path", [RUN_BAT, RUN_DESKTOP_BAT])
def test_batch_files_pause_before_closing(path):
    """The window must never vanish before the user can read the error."""
    text = open(path, encoding="utf-8").read().lower()
    assert "pause" in text, f"{os.path.basename(path)} can close without pausing"


def test_run_app_bat_delegates_rather_than_branching():
    """
    Conditional logic in batch is where this kept going wrong. run_app.bat may
    only locate an interpreter and hand over to launch.py.
    """
    text = open(RUN_BAT, encoding="utf-8").read()
    assert "scripts\\launch.py" in text
    assert "pip install" not in text.lower(), "installation logic belongs in launch.py"
    assert "streamlit run" not in text.lower(), "launch logic belongs in launch.py"


def test_batch_files_reference_files_that_exist():
    for path in (RUN_BAT, RUN_DESKTOP_BAT):
        text = open(path, encoding="utf-8").read()
        for referenced in re.findall(r'"(scripts\\[a-z_]+\.py)"', text):
            full = os.path.join(ROOT, referenced.replace("\\", os.sep))
            assert os.path.exists(full), f"{path} references missing {referenced}"


# --------------------------------------------------------- starting the app
def test_a_busy_port_falls_back_instead_of_failing(launcher):
    """A Streamlit left running from an earlier attempt must not block a launch."""
    import socket

    test_port = launcher.find_free_port(8550)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
        held.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        held.bind(("127.0.0.1", test_port))
        held.listen(1)
        assert launcher.find_free_port(test_port) != test_port

    # Once released, the preferred port is used again.
    assert launcher.find_free_port(test_port) == test_port


def test_launcher_opens_the_browser_itself(launcher):
    """
    Streamlit's own auto-open does not always fire. When it does not, the user
    is left looking at a console log with no window, which reads as a crash —
    which is exactly what happened. The launcher must open it explicitly.
    """
    source = open(LAUNCH_PY, encoding="utf-8").read()
    assert "webbrowser.open" in source
    assert callable(launcher.open_browser_when_ready)


def test_browser_opener_gives_up_quietly_when_nothing_answers(launcher):
    """It must never hang the launch or raise if the server never comes up."""
    import time

    started = time.time()
    launcher.open_browser_when_ready("http://127.0.0.1:9/", timeout=2)
    assert time.time() - started < 15


def test_console_tells_the_user_the_log_is_not_an_error():
    """
    The server's normal startup log was mistaken for a crash. The banner must
    say plainly that this window is the server and that what follows is normal.
    """
    source = open(LAUNCH_PY, encoding="utf-8").read()
    assert "THE APP IS STARTING" in source
    assert "KEEP THIS WINDOW OPEN" in source
    assert "not an error" in source


def test_streamlit_runs_headless_so_the_launcher_controls_the_browser():
    source = open(LAUNCH_PY, encoding="utf-8").read()
    block = source[source.index("command = ["):source.index("threading.Thread")]
    assert '"--server.headless", "true"' in block
