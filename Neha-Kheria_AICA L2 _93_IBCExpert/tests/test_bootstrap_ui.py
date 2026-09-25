from pathlib import Path

from app.core.bootstrap_ui import dependencies_missing, run_bootstrap_progress


def test_bootstrap_progress_returns_without_gui_when_nothing_missing(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    assert dependencies_missing(tmp_path) is False
    run_bootstrap_progress(tmp_path)
