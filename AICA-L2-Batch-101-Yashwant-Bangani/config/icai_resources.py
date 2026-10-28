"""Static ICAI resources, legal text, syllabus grid and branding assets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

FAIR_USE_NOTICE: Final[str] = (
    "Educational fair-use companion. All Study Materials, Past Examination Papers, "
    "Suggested Answers, and Revision Test Papers (RTPs) referenced herein are the "
    "intellectual property and copyright of The Institute of Chartered Accountants of "
    "India (ICAI). This tool provides independent faculty commentary, pedagogical notes, "
    "and deep-links directly to official ICAI portals. Not officially affiliated with, "
    "endorsed by, or sponsored by ICAI."
)

CITATION_METADATA: Final[dict[str, str]] = {
    "source_document": "ICAI CA Intermediate Study Material / RTP / Suggested Answers",
    "paper": "Paper 6: Financial Management and Strategic Management",
    "canonical_url": "https://www.icai.org",
    "copyright_holder": "The Institute of Chartered Accountants of India (ICAI)",
    "license_nature": "Educational Fair Dealing (Section 52, Indian Copyright Act, 1957)",
}

ALLOWED_HOSTS: Final[tuple[str, ...]] = ("www.icai.org", "resource.cdn.icai.org")


@dataclass(frozen=True)
class HubTile:
    title: str
    subtitle: str
    url: str


HUB_TILES: Final[tuple[HubTile, ...]] = (
    HubTile("RTP Directory", "Revision Test Papers",
            "https://www.icai.org/post/rtp-intermediate-course"),
    HubTile("Past Question Papers", "Intermediate Course",
            "https://www.icai.org/post/question-papers-intermediate-course"),
    HubTile("Suggested Answers", "Latest diet answers",
            "https://www.icai.org/post/sugg-ans-inter-may2026"),
    HubTile("BOS Weightage Notification", "Official chapter weightage (PDF)",
            "https://resource.cdn.icai.org/76830bos61899-inter.pdf"),
)


def is_canonical_icai_url(url: str) -> bool:
    """Guard: only official ICAI hosts may be deep-linked."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.netloc in ALLOWED_HOSTS


# ----------------------------------------------------------------------------
# Syllabus: 100 marks normalised (6A = 50, 6B = 50)
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Module:
    module_id: str
    name: str
    part: str            # "6A" or "6B"
    weightage_label: str  # shown on the PDF badge / UI
    avg_marks: float


@dataclass(frozen=True)
class Chapter:
    chapter_id: str
    name: str
    module_id: str
    marks: float  # indicative faculty allocation inside the module (editable)


MODULES: Final[tuple[Module, ...]] = (
    Module("M1", "Module 1: Scope, Financing & Ratios", "6A", "5% - 8%", 7.0),
    Module("M2", "Module 2: Cost of Capital & Leverages", "6A", "8% - 12%", 10.0),
    Module("M3", "Module 3: Capital Budgeting Decisions", "6A", "12% - 15%", 14.0),
    Module("M4", "Module 4: Dividend Decisions", "6A", "4% - 6%", 5.0),
    Module("M5", "Module 5: Management of Working Capital", "6A", "12% - 16%", 14.0),
    Module("SM", "Paper 6B: Strategic Management", "6B", "50%", 50.0),
)

# Chapter-level split is an indicative teaching allocation that sums to each module
# average. It is NOT an ICAI-published chapter weightage; edit freely.
CHAPTERS: Final[tuple[Chapter, ...]] = (
    Chapter("M1a", "Scope and Objectives of Financial Management", "M1", 1.5),
    Chapter("M1b", "Types of Financing", "M1", 2.5),
    Chapter("M1c", "Ratio Analysis", "M1", 3.0),
    Chapter("M2a", "Cost of Capital", "M2", 4.0),
    Chapter("M2b", "Capital Structure Decisions", "M2", 3.0),
    Chapter("M2c", "Leverages", "M2", 3.0),
    Chapter("M3a", "Investment Decisions (Capital Budgeting)", "M3", 14.0),
    Chapter("M4a", "Dividend Decisions", "M4", 5.0),
    Chapter("M5a", "Working Capital Management", "M5", 7.0),
    Chapter("M5b", "Cash Management", "M5", 3.5),
    Chapter("M5c", "Receivables Management", "M5", 3.5),
    Chapter("SMa", "Introduction to Strategic Management", "SM", 8.0),
    Chapter("SMb", "Strategic Analysis (External and Internal Environment)", "SM", 16.0),
    Chapter("SMc", "Strategic Choices", "SM", 14.0),
    Chapter("SMd", "Strategy Implementation and Evaluation", "SM", 12.0),
)

TOTAL_MARKS: Final[float] = 100.0


def _validate() -> None:
    assert abs(sum(m.avg_marks for m in MODULES) - TOTAL_MARKS) < 1e-9, "Modules must sum to 100"
    assert abs(sum(m.avg_marks for m in MODULES if m.part == "6A") - 50.0) < 1e-9
    assert abs(sum(c.marks for c in CHAPTERS) - TOTAL_MARKS) < 1e-9, "Chapters must sum to 100"
    for m in MODULES:
        assert abs(sum(c.marks for c in CHAPTERS if c.module_id == m.module_id) - m.avg_marks) < 1e-9, m.module_id


_validate()


def module_by_id(module_id: str) -> Module:
    return next(m for m in MODULES if m.module_id == module_id)


# ----------------------------------------------------------------------------
# Inline SVG emblem (stylised original artwork, see README note on trademarks)
# ----------------------------------------------------------------------------
def emblem_svg(size: int = 72) -> str:
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 120 120" role="img" aria-label="CA India emblem">
  <circle cx="60" cy="60" r="56" fill="#FFFFFF" stroke="#0F172A" stroke-width="3"/>
  <circle cx="60" cy="60" r="48" fill="none" stroke="#0284C7" stroke-width="1.5"/>
  <path d="M16 62 A44 44 0 0 1 104 62" fill="none" stroke="#FF9933" stroke-width="7" stroke-linecap="round"/>
  <path d="M24 64 A36 36 0 0 1 96 64" fill="none" stroke="#FFFFFF" stroke-width="5"/>
  <path d="M16 62 A44 44 0 0 0 104 62" fill="none" stroke="#138808" stroke-width="7" stroke-linecap="round"/>
  <text x="60" y="70" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif"
        font-weight="700" font-size="34" fill="#0F172A">CA</text>
  <text x="60" y="92" text-anchor="middle" font-family="Arial, sans-serif"
        font-weight="700" font-size="9" letter-spacing="4" fill="#0F172A">INDIA</text>
</svg>
""".strip()
