"""Tamper-evident release-gate evidence for IBC Expert Windows acceptance.

This tool is deliberately stdlib-only so it can be used before third-party dependencies are
installed.  It never marks a gate PASS merely because another gate passed: every PASS is an
explicit recorded assertion and optional evidence files are SHA-256 bound into the record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
STATUSES = {"BLOCKED", "PASS", "FAIL"}

GATE_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("windows_pinned_pytest", "Full monolithic pytest suite exits cleanly with pinned dependencies on Windows"),
    ("pyinstaller_build", "PyInstaller onedir customer package builds successfully on Windows"),
    ("customer_package_verify", "Customer package security verification passes"),
    ("installer_build", "Inno Setup installer builds successfully"),
    ("bootstrap_online", "First-run dependency bootstrap succeeds from the configured package index on disposable Windows source-install test"),
    ("bootstrap_wheelhouse", "First-run dependency bootstrap succeeds from a verified offline wheelhouse on disposable Windows source-install test"),
    ("clean_install", "Installer works on a genuinely clean Windows machine/VM"),
    ("packaged_launch", "Packaged application launches on clean Windows"),
    ("clean_core_workflow", "Synthetic client/document/OCR/search/workflow/form sequence succeeds on clean Windows"),
    ("clean_backup_restore", "Backup/restore sequence succeeds on clean Windows using synthetic data"),
    ("clean_restart_persistence", "Restart preserves synthetic data on clean Windows"),
    ("clean_trial_activation", "Trial expiry, owner activation and post-restart licence persistence succeed on clean Windows"),
)
GATE_IDS = {gate_id for gate_id, _ in GATE_DEFINITIONS}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def new_evidence(*, application_version: str = "unknown") -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "application_version": application_version,
        "created_utc": utc_now(),
        "updated_utc": utc_now(),
        "machine": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "gates": {
            gate_id: {
                "description": description,
                "status": "BLOCKED",
                "note": "Not yet executed/recorded.",
                "updated_utc": utc_now(),
                "evidence_files": [],
            }
            for gate_id, description in GATE_DEFINITIONS
        },
    }


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict[str, Any]) -> None:
    data["updated_utc"] = utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def ensure_gate(data: dict[str, Any], gate_id: str) -> dict[str, Any]:
    if gate_id not in GATE_IDS:
        raise ValueError(f"Unknown gate: {gate_id}")
    gates = data.get("gates")
    if not isinstance(gates, dict) or gate_id not in gates:
        raise ValueError(f"Evidence file does not contain gate: {gate_id}")
    return gates[gate_id]


def set_gate(data: dict[str, Any], gate_id: str, status: str, note: str = "") -> None:
    status = status.upper()
    if status not in STATUSES:
        raise ValueError(f"Status must be one of {sorted(STATUSES)}")
    gate = ensure_gate(data, gate_id)
    gate["status"] = status
    gate["note"] = note.strip() or ("Recorded PASS." if status == "PASS" else "Recorded result.")
    gate["updated_utc"] = utc_now()


def bind_file(data: dict[str, Any], gate_id: str, file_path: Path, *, base: Path | None = None) -> dict[str, Any]:
    gate = ensure_gate(data, gate_id)
    file_path = file_path.expanduser().resolve()
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    root = (base or Path.cwd()).resolve()
    try:
        display = str(file_path.relative_to(root))
    except ValueError:
        display = str(file_path)
    entry = {"path": display, "sha256": sha256_file(file_path), "size": file_path.stat().st_size}
    existing = [item for item in gate.get("evidence_files", []) if item.get("path") != display]
    gate["evidence_files"] = existing + [entry]
    gate["updated_utc"] = utc_now()
    return entry


def _resolve_bound_path(evidence_file: Path, recorded: str) -> Path:
    candidate = Path(recorded)
    if candidate.is_absolute():
        return candidate
    return (evidence_file.parent / candidate).resolve()


def validate(data: dict[str, Any], *, evidence_file: Path | None = None, require_complete: bool = False) -> list[str]:
    issues: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"Unsupported evidence schema version: {data.get('schema_version')!r}")
    gates = data.get("gates")
    if not isinstance(gates, dict):
        return issues + ["Missing gates object."]
    for gate_id, description in GATE_DEFINITIONS:
        gate = gates.get(gate_id)
        if not isinstance(gate, dict):
            issues.append(f"Missing gate: {gate_id}")
            continue
        status = gate.get("status")
        if status not in STATUSES:
            issues.append(f"Invalid status for {gate_id}: {status!r}")
        if gate.get("description") != description:
            issues.append(f"Gate description changed for {gate_id}.")
        if require_complete and status != "PASS":
            issues.append(f"Gate not PASS: {gate_id} ({status})")
        for item in gate.get("evidence_files", []):
            if not isinstance(item, dict) or not all(key in item for key in ("path", "sha256", "size")):
                issues.append(f"Malformed evidence entry for {gate_id}.")
                continue
            if evidence_file is None:
                continue
            bound = _resolve_bound_path(evidence_file, str(item["path"]))
            if not bound.is_file():
                issues.append(f"Missing bound evidence file for {gate_id}: {item['path']}")
                continue
            if bound.stat().st_size != item["size"]:
                issues.append(f"Evidence size mismatch for {gate_id}: {item['path']}")
            if sha256_file(bound) != str(item["sha256"]).lower():
                issues.append(f"Evidence SHA-256 mismatch for {gate_id}: {item['path']}")
    extra = sorted(set(gates) - GATE_IDS)
    if extra:
        issues.append("Unknown gates present: " + ", ".join(extra))
    return issues


def markdown_report(data: dict[str, Any]) -> str:
    lines = [
        "# IBC Expert Windows Release Evidence",
        "",
        f"Application version: `{data.get('application_version', 'unknown')}`  ",
        f"Updated UTC: `{data.get('updated_utc', '')}`",
        "",
        "| Gate | Status | Note |",
        "| --- | --- | --- |",
    ]
    for gate_id, _ in GATE_DEFINITIONS:
        gate = data["gates"][gate_id]
        note = str(gate.get("note", "")).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{gate_id}` | **{gate.get('status')}** | {note} |")
    return "\n".join(lines) + "\n"


def _parse_files(values: Iterable[str]) -> list[Path]:
    return [Path(value) for value in values]


def main() -> int:
    parser = argparse.ArgumentParser(description="IBC Expert Windows release evidence recorder")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("evidence", type=Path)
    p_init.add_argument("--version", default="unknown")

    p_set = sub.add_parser("set")
    p_set.add_argument("evidence", type=Path)
    p_set.add_argument("gate", choices=sorted(GATE_IDS))
    p_set.add_argument("status", choices=sorted(STATUSES))
    p_set.add_argument("--note", default="")
    p_set.add_argument("--file", action="append", default=[])

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("evidence", type=Path)
    p_validate.add_argument("--require-complete", action="store_true")

    p_report = sub.add_parser("report")
    p_report.add_argument("evidence", type=Path)
    p_report.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "init":
        save(args.evidence, new_evidence(application_version=args.version))
        print(f"Created release evidence: {args.evidence}")
        return 0

    data = load(args.evidence)
    if args.command == "set":
        set_gate(data, args.gate, args.status, args.note)
        for item in _parse_files(args.file):
            # Bind relative to evidence directory so the record can travel with the kit.
            bind_file(data, args.gate, item, base=args.evidence.parent)
        save(args.evidence, data)
        print(f"Recorded {args.gate}={args.status}")
        return 0

    if args.command == "validate":
        issues = validate(data, evidence_file=args.evidence, require_complete=args.require_complete)
        if issues:
            print("RELEASE EVIDENCE VALIDATION FAILED")
            for issue in issues:
                print(f" - {issue}")
            return 2
        print("Release evidence validation passed.")
        return 0

    if args.command == "report":
        report = markdown_report(data)
        if args.output:
            args.output.write_text(report, encoding="utf-8")
            print(f"Wrote report: {args.output}")
        else:
            print(report, end="")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
