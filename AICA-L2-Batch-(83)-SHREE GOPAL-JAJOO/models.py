"""
models.py
---------
Core data structures shared across the LC Analyser application.
"""

from dataclasses import dataclass, field
from typing import Optional, List


# The four verdict options shown as radio buttons against every clause/point.
VERDICT_OPTIONS = [
    "Correct / In Order",
    "Requires Amendment",
    "Needs Clarification",
    "Informational / Not Applicable",
]

DEFAULT_VERDICT = VERDICT_OPTIONS[0]

# The four main analysis sections requested by the user, in display order.
SECTION_MAIN_SUMMARY = "Main Summary"
SECTION_GOODS = "Goods / Services Covered"
SECTION_DOCUMENTS = "Documents Required"
SECTION_CHARGES = "Charges & Other Conditions"

SECTION_ORDER = [
    SECTION_MAIN_SUMMARY,
    SECTION_GOODS,
    SECTION_DOCUMENTS,
    SECTION_CHARGES,
]

# The eight sub-heads under "Documents Required", in display order.
SUB_LR_BL = "LR / BL Conditions"
SUB_COO = "Certificate of Origin Conditions"
SUB_INVOICE_PACKING = "Invoicing & Packing List"
SUB_BOE = "Bill of Exchange"
SUB_CERT_INSPECTION = "Certifications & Inspections"
SUB_INSURANCE = "Insurance Details"
SUB_INTIMATION = "Intimation / Communication Requirements"
SUB_OTHER = "Other LC Conditions"

SUBSECTION_ORDER = [
    SUB_LR_BL,
    SUB_COO,
    SUB_INVOICE_PACKING,
    SUB_BOE,
    SUB_CERT_INSPECTION,
    SUB_INSURANCE,
    SUB_INTIMATION,
    SUB_OTHER,
]


@dataclass
class ClausePoint:
    """
    One row of the clause-wise summary table.

    sl_no           : running serial number across the whole document
    point_no        : the field tag / paragraph number as it appears in the LC
                       (e.g. "20", "45A", "Para 7")
    header          : short human-readable heading for the point
    summary         : plain-English summary of what the point says
    raw_text        : the original clause text, shown in the right-hand pane
    section         : one of SECTION_* constants
    subsection      : one of the SUB_* constants (only used within
                       SECTION_DOCUMENTS), else None
    suggested_verdict : verdict proposed by the rule engine
    analysis_note   : rule engine's explanation for the suggested verdict
    user_verdict    : verdict chosen by the user in the GUI (defaults to the
                       suggested verdict until the user changes it)
    user_remarks    : free-text remarks typed by the user in the GUI
    """

    sl_no: int
    point_no: str
    header: str
    summary: str
    raw_text: str
    section: str
    subsection: Optional[str] = None
    suggested_verdict: str = DEFAULT_VERDICT
    analysis_note: str = ""
    user_verdict: Optional[str] = None
    user_remarks: str = ""

    def effective_verdict(self) -> str:
        return self.user_verdict if self.user_verdict else self.suggested_verdict


@dataclass
class DocumentClassification:
    """Result of the step-3 gating check (is it an LC / does it carry a DC No.)."""

    is_lc: bool
    dc_number: Optional[str]
    reason: str = ""


@dataclass
class AnalysisResult:
    """Full output of the analysis pipeline, ready to hand to the GUI/exporter."""

    lc_type: str                      # "Draft LC" or "Issued / Transmitted LC"
    dc_number: Optional[str]
    source_filename: str
    full_text: str
    clauses: List[ClausePoint] = field(default_factory=list)

    def by_section(self, section: str) -> List[ClausePoint]:
        return [c for c in self.clauses if c.section == section]

    def by_subsection(self, subsection: str) -> List[ClausePoint]:
        return [c for c in self.clauses if c.subsection == subsection]
