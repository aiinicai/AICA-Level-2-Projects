from __future__ import annotations

from pathlib import Path

import pytest

from app.core.bootstrap import verify_wheelhouse_integrity
from scripts.verify_wheelhouse import verify_manifest, verify_wheelhouse, write_manifest


def _wheelhouse(tmp_path: Path) -> Path:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "example_pkg-1.0-py3-none-any.whl").write_bytes(b"wheel-one")
    (wheelhouse / "second_pkg-2.0-py3-none-any.whl").write_bytes(b"wheel-two")
    return wheelhouse


def test_wheelhouse_manifest_round_trip_and_bootstrap_integrity(tmp_path: Path):
    wheelhouse = _wheelhouse(tmp_path)
    write_manifest(wheelhouse)
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("# test-only placeholder\n", encoding="utf-8")
    assert verify_manifest(wheelhouse) == []
    assert verify_wheelhouse(wheelhouse, requirements, resolve=False) == []
    verify_wheelhouse_integrity(wheelhouse)


def test_wheelhouse_tamper_is_detected(tmp_path: Path):
    wheelhouse = _wheelhouse(tmp_path)
    write_manifest(wheelhouse)
    (wheelhouse / "example_pkg-1.0-py3-none-any.whl").write_bytes(b"tampered")
    assert any("SHA-256 mismatch" in issue for issue in verify_manifest(wheelhouse))
    with pytest.raises(RuntimeError, match="integrity check failed"):
        verify_wheelhouse_integrity(wheelhouse)


def test_wheelhouse_requires_exact_manifest_membership(tmp_path: Path):
    wheelhouse = _wheelhouse(tmp_path)
    write_manifest(wheelhouse)
    (wheelhouse / "extra_pkg-1.0-py3-none-any.whl").write_bytes(b"extra")
    with pytest.raises(RuntimeError, match="contents do not match"):
        verify_wheelhouse_integrity(wheelhouse)


def test_installer_definition_wraps_verified_onedir_only():
    root = Path(__file__).parents[1]
    iss = (root / "packaging" / "installer" / "IBCExpert.iss").read_text(encoding="utf-8")
    script = (root / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")
    assert 'Source: "{#SourceDir}\\*"' in iss
    assert "recursesubdirs" in iss
    assert "verify_customer_package.py" in script
    assert "dist\\IBCExpert" in script
    assert "owner_private_key" not in iss
    assert "owner_tools" not in iss


def test_windows_build_verifies_wheelhouse_before_offline_install():
    root = Path(__file__).parents[1]
    script = (root / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")
    assert "verify_wheelhouse.py" in script
    assert "--no-index" in script
    assert "--find-links" in script
    assert "BuildInstaller" in script


def test_prepare_wheelhouse_refuses_source_distributions_and_verifies_offline():
    root = Path(__file__).parents[1]
    script = (root / "scripts" / "prepare_wheelhouse.ps1").read_text(encoding="utf-8")
    assert "--only-binary=:all:" in script
    assert "verify_wheelhouse.py" in script
    assert "SHA256SUMS.txt" in (root / "packaging" / "OFFLINE_WHEELHOUSE.md").read_text(encoding="utf-8")
