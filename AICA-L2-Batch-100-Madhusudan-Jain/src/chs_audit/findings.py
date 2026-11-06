"""A single structure for every audit observation produced by any module."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2, "Info": 3}


@dataclass
class Finding:
    module: str          # e.g. "Member Ledger", "GST", "Expenses", "Compliance", "Tax"
    area: str            # short label
    severity: str        # High / Medium / Low / Info
    observation: str     # what was found (facts and figures)
    reference: str       # bye-law / section / circular
    recommendation: str  # what the committee should do
    amount: float = 0.0  # financial exposure where quantifiable
    evidence: str = ""   # pointer to supporting schedule / rows
    id: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def number_findings(findings: list[Finding]) -> list[Finding]:
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.module))
    for i, f in enumerate(findings, start=1):
        f.id = f"OBS-{i:02d}"
    return findings


def inr(x: float) -> str:
    """Indian-style grouping with Rs prefix: 12,34,567."""
    neg = x < 0
    s = str(int(round(abs(float(x)))))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if neg else "") + "Rs " + s
