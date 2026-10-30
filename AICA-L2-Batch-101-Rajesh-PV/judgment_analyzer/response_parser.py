"""Parse Gemini's Markdown report into the 14 canonical sections.

The parser is tolerant of common formatting drift (different heading levels,
bold headings, missing numbers, slightly different titles) and always returns
every section - missing ones are explicitly labelled rather than silently
dropped.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from .prompts import DISCLAIMER_TEXT, DISCLAIMER_TITLE, REPORT_SECTIONS, SectionDef

MISSING_TEXT = "_Not provided in the AI response. Refer to the original judgment._"

# GUI tab name -> section numbers shown in that tab.
TAB_GROUPS: dict[str, tuple[int, ...]] = {
    "Summary": (1, 2, 3, 8),
    "Legal Analysis": (4, 5, 6, 7, 9, 10, 11, 12),
    "Key Insights": (13,),
    "Points for Consideration": (14,),
}

_HEADING_RE = re.compile(
    r"^\s*(?P<hashes>#{1,6})\s*(?P<body>.+?)\s*#*\s*$"  # markdown heading
    r"|^\s*\*\*(?P<bold>.+?)\*\*\s*:?\s*$"  # a line that is entirely bold
)
_NUMBER_RE = re.compile(r"^(?:section\s+)?(?P<num>\d{1,2})\s*[.):\-]?\s*(?P<title>.*)$", re.IGNORECASE)


def _norm(text: str) -> str:
    text = text.lower().replace("&", "and").replace("’", "'")
    text = re.sub(r"[*_`]", "", text)
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return " ".join(text.split())


def _title_matches(candidate: str, section: SectionDef, loose: bool = True) -> bool:
    """Exact/fuzzy title match. ``loose`` also accepts prefix matches (used when a number is present)."""
    cand = _norm(candidate)
    if not cand:
        return False
    names = [_norm(section.title), *(_norm(a) for a in section.aliases)]
    for name in names:
        if cand == name:
            return True
        if loose and (cand.startswith(name) or (name.startswith(cand) and len(cand) >= 5)):
            return True
    return max(difflib.SequenceMatcher(None, cand, n).ratio() for n in names) >= 0.82


def _match_heading(line: str) -> tuple[int | None, int]:
    """Return (section_number | 0 for disclaimer | None, heading_level)."""
    m = _HEADING_RE.match(line)
    if not m:
        return None, 0
    is_bold_line = not m.group("hashes")
    level = len(m.group("hashes")) if m.group("hashes") else 2
    body = (m.group("body") or m.group("bold") or "").strip().strip("*").strip()

    if _norm(body).startswith(_norm(DISCLAIMER_TITLE)) and level <= 3:
        return 0, level

    num_match = _NUMBER_RE.match(body)
    if num_match:
        number = int(num_match.group("num"))
        title = num_match.group("title")
        if 1 <= number <= len(REPORT_SECTIONS):
            section = REPORT_SECTIONS[number - 1]
            if not title.strip() or _title_matches(title, section):
                return number, level
            # Number present but title differs: trust the title if it names another section.
            for s in REPORT_SECTIONS:
                if _title_matches(title, s):
                    return s.number, level
            # Numbered markdown heading with an unfamiliar title: trust the number
            # for top-level headings only. Numbered bold lines (e.g. a list of
            # issues) are content, not section headings.
            return (number, level) if level <= 2 and not is_bold_line else (None, level)

    # Un-numbered headings start a section only if they are real Markdown
    # headings (not bold lines inside a section) and closely match a title.
    if level <= 2 and not is_bold_line:
        for s in REPORT_SECTIONS:
            if _title_matches(body, s, loose=False):
                return s.number, level
    return None, level


@dataclass
class ParsedReport:
    sections: dict[int, str] = field(default_factory=dict)
    disclaimer: str = DISCLAIMER_TEXT
    preamble: str = ""
    raw: str = ""
    unstructured: bool = False  # True when no expected heading was found at all

    @property
    def missing_sections(self) -> list[int]:
        return [s.number for s in REPORT_SECTIONS if not self.sections.get(s.number, "").strip()]

    def section_body(self, number: int) -> str:
        body = self.sections.get(number, "").strip()
        return body or MISSING_TEXT

    def section_markdown(self, number: int, display_number: int | None = None) -> str:
        """Heading + body. ``display_number`` overrides the printed heading number
        (used to renumber sections from 1 within each tab); the body is unchanged."""
        section = REPORT_SECTIONS[number - 1]
        shown = section.number if display_number is None else display_number
        return f"## {shown}. {section.title}\n\n{self.section_body(number)}"

    def tab_markdown(self, tab: str) -> str:
        if tab not in TAB_GROUPS:
            raise KeyError(tab)
        # Each tab numbers its own section headings from 1; the Full Report keeps 1-14.
        parts = [self.section_markdown(n, i) for i, n in enumerate(TAB_GROUPS[tab], start=1)]
        if tab == "Points for Consideration":
            parts.append(f"## {DISCLAIMER_TITLE}\n\n{self.disclaimer}")
        return "\n\n".join(parts)

    def to_markdown(self) -> str:
        parts = [self.section_markdown(s.number) for s in REPORT_SECTIONS]
        parts.append(f"## {DISCLAIMER_TITLE}\n\n{self.disclaimer}")
        return "\n\n".join(parts)

    def ordered_sections(self) -> list[tuple[str, str]]:
        """[(heading, markdown body)] in canonical order, including the disclaimer."""
        out = [(f"{s.number}. {s.title}", self.section_body(s.number)) for s in REPORT_SECTIONS]
        out.append((DISCLAIMER_TITLE, self.disclaimer))
        return out


def parse_report(markdown: str) -> ParsedReport:
    report = ParsedReport(raw=markdown or "")
    if not markdown or not markdown.strip():
        return report

    text = markdown.strip()
    # Strip a wrapping ```markdown fence if the model added one.
    fence = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)

    current: int | None = None  # None = preamble, 0 = disclaimer
    buffers: dict[int | None, list[str]] = {None: []}
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        number = None
        if not in_code:
            number, _level = _match_heading(line)
        if number is not None:
            current = number
            buffers.setdefault(current, [])
            if buffers[current]:  # duplicate heading - keep content together
                buffers[current].append("")
            continue
        buffers.setdefault(current, []).append(line)

    report.preamble = "\n".join(buffers.pop(None, [])).strip()
    disclaimer = "\n".join(buffers.pop(0, [])).strip()
    if disclaimer:
        report.disclaimer = disclaimer
    for number, lines in buffers.items():
        if isinstance(number, int) and number > 0:
            report.sections[number] = "\n".join(lines).strip()

    # If nothing matched at all, keep the response visible rather than losing it.
    if not report.sections and report.preamble:
        report.unstructured = True
        report.sections[2] = (
            "_The AI response did not follow the expected headings; the full response is shown below._\n\n"
            + report.preamble
        )
        report.preamble = ""

    # Remove instruction text the model sometimes echoes into labels,
    # e.g. "Parties involved (identify each party's role):".
    if 1 in report.sections:
        report.sections[1] = re.sub(r"(?i)(parties involved)\s*\((?:identify|give|show)[^)]*\)", r"\1",
                                    report.sections[1])

    # The app always guarantees the educational-use disclaimer is present.
    if "not legal advice" not in report.disclaimer.lower():
        report.disclaimer = f"{report.disclaimer}\n\n{DISCLAIMER_TEXT}".strip()
    return report


EDITED_NOTE = "Content was edited by the user after AI generation."


def apply_edit(report: ParsedReport, tab: str, edited_markdown: str) -> list[int]:
    """Write the user's edited text for one results tab back into ``report``.

    ``tab`` is "Full Report" or a key of TAB_GROUPS. Sections are recognised by their
    "## n. Title" headings (the number may differ, the title decides). A section whose
    heading the user removed becomes empty. Raises ValueError if no headings are found,
    so a slip of the keyboard cannot wipe the report. Returns the changed section numbers.
    """
    numbers = list(range(1, len(REPORT_SECTIONS) + 1)) if tab == "Full Report" else list(TAB_GROUPS[tab])
    if not re.search(r"(?m)^\s*#{1,6}\s*\S", edited_markdown or ""):
        raise ValueError("No section headings were found. Keep the '## ' heading lines (e.g. '## 1. Case "
                         "Details') so the app knows which section each part belongs to.")
    parsed = parse_report(edited_markdown)
    found = [] if parsed.unstructured else [n for n in numbers if n in parsed.sections]
    if not found:
        raise ValueError("None of this tab's section headings were recognised. Keep the original '## ' "
                         "heading lines and edit only the text below them.")
    if parsed.preamble.strip():
        raise ValueError("There is text above the first heading. Move it under a section heading.")
    stray = [n for n in parsed.sections if n not in numbers]
    if stray:
        names = ", ".join(REPORT_SECTIONS[n - 1].title for n in stray)
        raise ValueError(f"This tab contains headings that belong to other tabs ({names}). "
                         "Edit those sections in their own tab or in Full Report.")
    changed = []
    for n in numbers:
        new_body = parsed.sections.get(n, "").strip()
        if new_body == MISSING_TEXT:  # the on-screen placeholder for an empty section
            new_body = ""
        if new_body != report.sections.get(n, "").strip():
            report.sections[n] = new_body
            changed.append(n)
    if tab in ("Full Report", "Points for Consideration") and re.search(
            rf"(?im)^\s*#{{1,6}}\s*{DISCLAIMER_TITLE}", edited_markdown):
        report.disclaimer = parsed.disclaimer  # parse_report guarantees the 'not legal advice' wording
    return changed
