from pathlib import Path

import app.core.bootstrap as bootstrap


def test_python314_release_pins_are_present():
    root = Path(__file__).resolve().parents[1]
    text = (root / "requirements.txt").read_text(encoding="utf-8")
    required = {
        "fastapi==0.140.2",
        "pywebview==6.2.1",
        "cryptography==50.0.1",
        "argon2-cffi==25.1.0",
        "Pillow==12.2.0",
        "PyMuPDF==1.28.2",
        "reportlab==5.0.1",
        "pytest==9.1.1",
        "pytest-cov==7.1.0",
        "pyinstaller==6.22.3",
    }
    assert required.issubset(set(text.splitlines()))


def test_windows_release_scripts_enforce_python314():
    root = Path(__file__).resolve().parents[1]
    for name in ("run_windows_release_gate.ps1", "build_windows.ps1"):
        text = (root / "scripts" / name).read_text(encoding="utf-8")
        assert "validate_python_target.py" in text
    wheel = (root / "scripts" / "prepare_wheelhouse.ps1").read_text(encoding="utf-8")
    assert '$Parts[0] -ne "3.14"' in wheel


def test_bootstrap_detects_wrong_installed_pin(tmp_path, monkeypatch):
    req = tmp_path / "requirements.txt"
    req.write_text("example-package==2.0.0\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(bootstrap.importlib.metadata, "version", lambda name: "1.0.0")
    missing = bootstrap.missing_dependencies(req)
    assert len(missing) == 1
    assert missing[0].requirement == "example-package==2.0.0"


def test_bootstrap_accepts_exact_installed_pin(tmp_path, monkeypatch):
    req = tmp_path / "requirements.txt"
    req.write_text("example-package==2.0.0\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(bootstrap.importlib.metadata, "version", lambda name: "2.0.0")
    assert bootstrap.missing_dependencies(req) == []
