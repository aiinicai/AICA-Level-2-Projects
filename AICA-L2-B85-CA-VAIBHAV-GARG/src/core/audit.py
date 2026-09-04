"""Audit logger capturing files, hashes, rules, assumptions, and overrides (§11)."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class AuditEntry:
    timestamp: str
    event_type: str  # 'FILE_UPLOAD', 'RULE_APPLIED', 'ASSUMPTION_APPLIED', 'OVERRIDE', 'INTEGRITY_CHECK', 'EXPORT'
    detail: str


class AuditLogger:
    def __init__(self):
        self.entries: List[AuditEntry] = []

    def log(self, event_type: str, detail: str) -> None:
        """Add an audit entry with current timestamp."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.entries.append(AuditEntry(timestamp=ts, event_type=event_type, detail=detail))

    def export_as_text(self, client_name: str, fy_label: str) -> str:
        """Format the entire audit trail into a professional text report for the audit file."""
        lines = [
            "=" * 80,
            f"SCHEDULE III RATIO ANALYSER — AUDIT DOCUMENTATION TRAIL",
            f"Client: {client_name}",
            f"Financial Period: {fy_label}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            "",
            "CHRONOLOGICAL AUDIT LOG:",
            "-" * 80,
        ]
        for e in self.entries:
            lines.append(f"[{e.timestamp}] [{e.event_type:20s}] {e.detail}")
        lines.append("-" * 80)
        lines.append("End of Audit Documentation.")
        return "\n".join(lines)
