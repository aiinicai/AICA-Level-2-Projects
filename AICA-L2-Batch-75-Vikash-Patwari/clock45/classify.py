"""
clock45.classify
================
The four coverage gates. This module is the product's differentiator.

A payable falls within the disallowance ONLY if all four gates pass. Anything
that fails a gate goes onto the Exclusion Register with the reason and the
evidence — that register is what proves to a partner that you know the law,
because producing a defensible NON-disallowance list is the hard part.

Gate 2 (trader exclusion) is the one most tools get wrong in both directions.
Ministry of MSME Office Memoranda dated 2 July 2021 and 1 September 2021:
retail and wholesale trades may register on Udyam, but their benefits are
restricted to Priority Sector Lending, and the delayed-payment provisions of
the MSMED Act are expressly excluded. Udyam registration for traders was
granted under NIC codes 45, 46 and 47.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

# NIC 2-digit divisions covering wholesale and retail trade.
TRADER_NIC_DIVISIONS = {"45", "46", "47"}

MICRO, SMALL, MEDIUM = "MICRO", "SMALL", "MEDIUM"
COVERED_CLASSES = {MICRO, SMALL}

# Evidence strength. Never let these render identically in the UI.
SRC_CERTIFICATE = "UDYAM_CERTIFICATE"   # strong  - certificate on file, hashed
SRC_DECLARATION = "VENDOR_DECLARATION"  # medium  - vendor's written word
SRC_CLIENT_FLAG = "CLIENT_ERP_FLAG"     # weak    - a hint, not evidence
SRC_ASSUMED = "ASSUMED"                 # none    - must block sign-off

EVIDENCE_RANK = {
    SRC_CERTIFICATE: 3, SRC_DECLARATION: 2, SRC_CLIENT_FLAG: 1, SRC_ASSUMED: 0
}

GATE_CLASS = "GATE_1_ENTERPRISE_CLASS"
GATE_ACTIVITY = "GATE_2_ACTIVITY_TRADER"
GATE_REGISTRATION = "GATE_3_UDYAM_REGISTRATION"
GATE_TIMING = "GATE_4_REGISTERED_BEFORE_SUPPLY"


@dataclass
class UdyamRecord:
    vendor_id: str
    udyam_no: Optional[str] = None
    enterprise_class: Optional[str] = None      # MICRO / SMALL / MEDIUM
    nic_code: Optional[str] = None              # e.g. "46109"
    activity_label: Optional[str] = None
    registration_date: Optional[date] = None
    source: str = SRC_ASSUMED
    evidence_file_hash: Optional[str] = None
    confirmed_by: Optional[str] = None
    confirmed_on: Optional[date] = None

    @property
    def nic_division(self) -> Optional[str]:
        return self.nic_code[:2] if self.nic_code and len(self.nic_code) >= 2 else None

    @property
    def is_trader(self) -> bool:
        return self.nic_division in TRADER_NIC_DIVISIONS


@dataclass
class Coverage:
    covered: bool
    gate_failed: Optional[str]
    reason: str
    evidence_strength: int
    needs_human_confirmation: bool


def assess_coverage(rec: UdyamRecord, supply_date: date) -> Coverage:
    """
    Run the four gates in order and stop at the first failure.
    Order matters: it produces the most useful reason text for the register.
    """
    strength = EVIDENCE_RANK.get(rec.source, 0)
    needs_confirm = strength < EVIDENCE_RANK[SRC_DECLARATION]

    # Gate 3 first in practice: without registration there is no "supplier".
    if not rec.udyam_no:
        return Coverage(
            False, GATE_REGISTRATION,
            "No Udyam registration on record. The MSMED definition of "
            "'supplier' requires a memorandum filed under s.8(1), so the "
            "provision cannot apply.",
            strength, True,
        )

    if rec.enterprise_class not in COVERED_CLASSES:
        return Coverage(
            False, GATE_CLASS,
            f"Classified as {rec.enterprise_class or 'UNKNOWN'}. Only MICRO and "
            f"SMALL enterprises are covered; MEDIUM enterprises are outside the "
            f"provision.",
            strength, needs_confirm,
        )

    if rec.is_trader:
        return Coverage(
            False, GATE_ACTIVITY,
            f"Udyam activity is wholesale/retail trade (NIC {rec.nic_code}"
            f"{', ' + rec.activity_label if rec.activity_label else ''}). "
            f"Per Ministry of MSME OMs dated 02.07.2021 and 01.09.2021, trader "
            f"benefits are restricted to Priority Sector Lending and the "
            f"delayed-payment provisions are excluded. Not a 'supplier' for "
            f"s.15 purposes.",
            strength, needs_confirm,
        )

    if rec.registration_date and rec.registration_date > supply_date:
        return Coverage(
            False, GATE_TIMING,
            f"Udyam registered {rec.registration_date.isoformat()}, after the "
            f"supply on {supply_date.isoformat()}. The supplier was not a "
            f"registered MSE at the time of supply.",
            strength, needs_confirm,
        )

    return Coverage(
        True, None,
        f"{rec.enterprise_class} enterprise, NIC {rec.nic_code} "
        f"(manufacturing/services), registered {rec.registration_date}. "
        f"Within scope.",
        strength, needs_confirm,
    )


def exclusion_summary(coverages: list[Coverage]) -> dict[str, int]:
    """Counts by gate, for the Exclusion Register header."""
    out: dict[str, int] = {}
    for c in coverages:
        if not c.covered and c.gate_failed:
            out[c.gate_failed] = out.get(c.gate_failed, 0) + 1
    return out
