from __future__ import annotations

import json
from pathlib import Path

from scripts.release_evidence import bind_file, markdown_report, new_evidence, set_gate, validate

ROOT = Path(__file__).parents[1]


def test_new_evidence_is_not_auto_complete():
    evidence = new_evidence(application_version="test")
    assert evidence["gates"]
    assert all(gate["status"] == "BLOCKED" for gate in evidence["gates"].values())
    assert any("clean" in gate_id for gate_id in evidence["gates"])


def test_complete_validation_requires_every_gate_pass(tmp_path: Path):
    evidence_path = tmp_path / "evidence.json"
    evidence = new_evidence(application_version="test")
    issues = validate(evidence, evidence_file=evidence_path, require_complete=True)
    assert any("Gate not PASS" in issue for issue in issues)


def test_bound_file_hash_tampering_is_detected(tmp_path: Path):
    evidence_path = tmp_path / "evidence.json"
    artifact = tmp_path / "pytest.log"
    artifact.write_text("passed", encoding="utf-8")
    evidence = new_evidence(application_version="test")
    set_gate(evidence, "windows_pinned_pytest", "PASS", "test")
    bind_file(evidence, "windows_pinned_pytest", artifact, base=tmp_path)
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    assert validate(evidence, evidence_file=evidence_path) == []
    artifact.write_text("tampered", encoding="utf-8")
    assert any("SHA-256 mismatch" in issue for issue in validate(evidence, evidence_file=evidence_path))


def test_markdown_report_includes_gate_status():
    evidence = new_evidence(application_version="test")
    set_gate(evidence, "pyinstaller_build", "PASS", "built")
    report = markdown_report(evidence)
    assert "pyinstaller_build" in report
    assert "**PASS**" in report


def test_windows_harness_does_not_auto_pass_bootstrap_or_clean_machine():
    script = (ROOT / "scripts" / "run_windows_release_gate.ps1").read_text(encoding="utf-8")
    assert "bootstrap_online PASS" not in script
    assert "bootstrap_wheelhouse PASS" not in script
    assert "clean_install PASS" not in script
    assert "clean_trial_activation PASS" not in script
    assert "release_evidence.py" in script
    assert "pytest" in script
    assert "build_windows.ps1" in script
    assert "build_installer.ps1" in script


def test_clean_acceptance_is_powershell_only_and_offline_posture_is_preserved():
    clean = (ROOT / "scripts" / "clean_windows_acceptance.ps1").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "WINDOWS_RELEASE_ACCEPTANCE.md").read_text(encoding="utf-8")
    architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    lowered = clean.lower()
    assert "python.exe" not in lowered
    assert "-m pytest" not in lowered
    assert "release_evidence.py" not in lowered
    assert "ConvertFrom-Json" in clean
    assert "SYNTHETIC TEST DATA ONLY" in clean
    combined = (docs + "\n" + architecture).lower()
    assert "no legal/database web downloader" in combined or "no automatic" in combined
    assert "local" in combined
