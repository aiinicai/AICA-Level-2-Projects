"""Source Check: verify the AI report against the judgment text, without AI.

Every checkable item in the report - quotations, law-report citations and case
numbers, section references, dates, amounts, paragraph and page references -
is looked up in the text extracted from the PDF. Each item is marked:

* FOUND      - present in the judgment (exact, after normalising spacing/case/quotes)
* CLOSE      - a quotation whose wording mostly matches but is not identical
* NOT_FOUND  - not present in the judgment; the reviewer must check it

This is deterministic Python, so it gives the same answer every time and can be
explained line by line. It cannot judge whether a summary is *fair*; that remains
the reviewer's job. It catches the most dangerous failure: invented or altered
quotes, citations, sections, dates and figures.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .prompts import REPORT_SECTIONS
from .response_parser import ParsedReport

FOUND, CLOSE, NOT_FOUND = "Found", "Close match", "Not found"
KINDS = ("Quotation", "Citation", "Section", "Date", "Amount", "Paragraph ref", "Page ref")

# --------------------------------------------------------------- normalising ---
_QUOTES = str.maketrans({"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "`": "'", "–": "-", "—": "-",
                         " ": " "})
_MARKERS = re.compile(r"\[(?:Page \d+(?:, part \d+/\d+)?|Para \d+)\]\s*")


def normalise(text: str) -> str:
    """Lower-case, unify quotes/dashes, re-join words hyphenated across lines, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text or "").translate(_QUOTES)
    text = _MARKERS.sub("", text)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return " ".join(text.lower().split())


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalise(text))


def _compact(text: str) -> str:
    """Letters and digits only: '[2026] 190 taxmann.com 964' -> '2026190taxmanncom964'."""
    return re.sub(r"[^a-z0-9]", "", normalise(text))


# ---------------------------------------------------------------- patterns ---
_QUOTE_RE = re.compile(r"[\"“]([^\"“”]{20,600})[\"”]")
_CITATION_RES = [
    re.compile(r"\[\d{4}\]\s*\d+\s*taxmann\.com\s*\d+", re.I),
    re.compile(r"[\[(]\d{4}[\])]\s*\d+\s*(?:SCC|ITR|ITD|TTJ|SOT|Taxman|CTR|DTR|ITR\(T\)|SCR|AIR|GSTL|STC)\b\s*\(?[A-Za-z. ]{0,20}\)?\s*\d+",
               re.I),
    re.compile(r"\b\d{1,4}\s+(?:ITR|ITD|TTJ|SOT|Taxman|CTR)\s+\d{1,4}\b"),
    re.compile(r"\b(?:I\.?T\.?A\.?|W\.?P\.?(?:\s*\(C\))?|C\.?A\.?|S\.?L\.?P\.?(?:\s*\(C\))?|Civil Appeal|Writ Petition|"
               r"C\.?O\.?|S\.?A\.?|Tax Case(?:\s*\(Appeal\))?|T\.?C\.?A\.?|ITTA)\s*No[s]?\.?\s*\d+"
               r"(?:\s*/\s*[A-Za-z]{2,8}\.?)?(?:\s*/\s*\d{2,4})?(?:\s+of\s+\d{4})?",
               re.I),
]
_SECTION_RE = re.compile(
    r"\b(?:sections?|secs?\.?|u/s\.?|s\.)\s*(\d{1,3}[A-Z]{0,4}(?:\s*\(\s*[0-9A-Za-z]{1,6}\s*\))*)"
    r"((?:\s*(?:,|and|&|r\.?\s*w\.?|read with)\s*\d{1,3}[A-Z]{0,4}(?:\s*\(\s*[0-9A-Za-z]{1,6}\s*\))*)*)",
    re.I)
_SECTION_TOKEN = re.compile(r"\d{1,3}[A-Z]{0,4}(?:\s*\(\s*[0-9A-Za-z]{1,6}\s*\))*", re.I)
_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
                                       "nov", "dec"], 1)}
_DATE_NUM = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
_DATE_DMY = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
_DATE_MDY = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
_AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)(?:\s*/-)?(?:\s*(crores?|lakhs?|lacs?|cr\.?))?", re.I)
_PARA_REF = re.compile(r"\bparas?\.?\s*(\d{1,3}(?:\s*(?:-|–|to|,|and|&)\s*\d{1,3})*)", re.I)
_PAGE_REF = re.compile(r"[\(\[;,]\s*(?:see\s+)?pp?\.\s*(\d{1,4}(?:\s*(?:-|–|to|,|and|&)\s*\d{1,4})*)", re.I)
_RANGE_SPLIT = re.compile(r"\s*(?:,|and|&)\s*")


def _expand(spec: str, limit: int = 60) -> list[int]:
    """'12-14, 18' -> [12, 13, 14, 18]"""
    out: list[int] = []
    for part in _RANGE_SPLIT.split(spec.strip()):
        bits = re.split(r"\s*(?:-|–|to)\s*", part)
        nums = [int(b) for b in bits if b.isdigit()]
        if len(nums) == 2 and 0 < nums[1] - nums[0] < limit:
            out.extend(range(nums[0], nums[1] + 1))
        else:
            out.extend(nums)
    return out


def _dates(text: str) -> set[tuple[int, int, int]]:
    found = set()
    for d, m, y in _DATE_NUM.findall(text):
        found.add((int(y), int(m), int(d)))
    for d, mon, y in _DATE_DMY.findall(text):
        if mon[:3].lower() in _MONTHS:
            found.add((int(y), _MONTHS[mon[:3].lower()], int(d)))
    for mon, d, y in _DATE_MDY.findall(text):
        if mon[:3].lower() in _MONTHS:
            found.add((int(y), _MONTHS[mon[:3].lower()], int(d)))
    return {x for x in found if 1 <= x[1] <= 12 and 1 <= x[2] <= 31}


def _section_key(token: str) -> str:
    return re.sub(r"\s+", "", token).lower()


# ------------------------------------------------------------------- types ---
@dataclass
class CheckItem:
    kind: str
    text: str
    status: str
    section: str = ""  # report section title where the item appears
    detail: str = ""


@dataclass
class VerificationReport:
    items: list[CheckItem] = field(default_factory=list)
    para_detected: int = 0
    page_count: int = 0

    def count(self, status: str | None = None, kind: str | None = None) -> int:
        return sum(1 for i in self.items if (status is None or i.status == status) and (kind is None or i.kind == kind))

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def not_found(self) -> list[CheckItem]:
        return [i for i in self.items if i.status == NOT_FOUND]

    @property
    def score(self) -> float | None:
        """Share of checkable items found in the judgment (close matches count half). None if nothing to check."""
        if not self.items:
            return None
        return (self.count(FOUND) + 0.5 * self.count(CLOSE)) / self.total

    def score_text(self) -> str:
        s = self.score
        return "n/a" if s is None else f"{s * 100:.0f}%"

    def summary_line(self) -> str:
        if not self.items:
            return "Source check: no quotations, citations, sections, dates or amounts to check."
        return (f"Source check {self.score_text()}: {self.count(FOUND)} found, {self.count(CLOSE)} close, "
                f"{self.count(NOT_FOUND)} not found in the judgment (of {self.total} items).")

    def to_markdown(self) -> str:
        lines = ["## Source Check", "",
                 "The app looked up every quotation, citation, section, date, amount and paragraph reference in the "
                 "analysis in the text of the judgment (no AI involved).", "",
                 "**What to do:** check each item under 'Not found' against the judgment. If it is wrong, correct "
                 "or delete it with 'Edit this tab'. Items under 'Found' appear in the judgment as written.", "",
                 f"- **Score:** {self.score_text()}  ({self.summary_line().split(': ', 1)[-1]})",
                 f"- **Numbered paragraphs detected in the judgment:** {self.para_detected or 'none'}",
                 f"- **Pages in the judgment:** {self.page_count}", ""]
        lines.append("## Items by type")
        lines.append("")
        for kind in KINDS:
            n = self.count(kind=kind)
            if n:
                lines.append(f"- **{kind}:** {n} checked - {self.count(FOUND, kind)} found, "
                             f"{self.count(CLOSE, kind)} close, {self.count(NOT_FOUND, kind)} not found")
        for status, title, note in (
            (NOT_FOUND, "Not found in the judgment - check before relying on these",
             "[Uncertain] items below were not located in the judgment text. They may be paraphrased, OCR-damaged "
             "or invented. Correct or delete them in the report."),
            (CLOSE, "Close matches - wording differs from the judgment", ""),
            (FOUND, "Found in the judgment", ""),
        ):
            group = [i for i in self.items if i.status == status]
            if not group:
                continue
            lines += ["", f"## {title}", ""]
            if note:
                lines += [note, ""]
            for i in group[:200]:
                where = f" _(in {i.section})_" if i.section else ""
                detail = f" - {i.detail}" if i.detail else ""
                lines.append(f"- **{i.kind}:** {i.text}{where}{detail}")
        return "\n".join(lines)


# ------------------------------------------------------------------ checks ---
class SourceIndex:
    """Pre-computed views of the judgment text for fast lookups."""

    def __init__(self, source_text: str, para_numbers: set[int] | None = None, page_count: int = 0):
        self.norm = normalise(source_text)
        self.compact = _compact(source_text)
        words = _words(source_text)
        self.words_set = set(words)
        self.shingles = {" ".join(words[i:i + 4]) for i in range(max(0, len(words) - 3))}
        self.dates = _dates(normalise(source_text))
        self.amounts = {re.sub(r"[^\d.]", "", a).rstrip(".") for a, _ in _AMOUNT_RE.findall(source_text)}
        self.numbers = set(re.findall(r"\d[\d,]*\d|\d", source_text))
        self.numbers = {n.replace(",", "") for n in self.numbers}
        self.section_tokens = {_section_key(t) for t in _SECTION_TOKEN.findall(source_text)}
        self.para_numbers = para_numbers or set()
        self.page_count = page_count

    def quote_status(self, quote: str) -> tuple[str, str]:
        q = normalise(quote).strip(" .,;:'\"")
        if q and q in self.norm:
            return FOUND, ""
        words = _words(quote)
        if len(words) < 4:
            return (FOUND, "") if all(w in self.words_set for w in words) else (NOT_FOUND, "")
        sh = [" ".join(words[i:i + 4]) for i in range(len(words) - 3)]
        ratio = sum(1 for s in sh if s in self.shingles) / len(sh)
        if ratio >= 0.95:
            return FOUND, ""
        if ratio >= 0.6:
            return CLOSE, f"{ratio * 100:.0f}% of the wording matches"
        return NOT_FOUND, f"only {ratio * 100:.0f}% of the wording matches"


def _section_titles(report: ParsedReport) -> list[tuple[str, str]]:
    return [(s.title, report.sections.get(s.number, "")) for s in REPORT_SECTIONS]


def verify_report(report: ParsedReport, source_text: str, para_numbers: set[int] | None = None,
                  page_count: int = 0) -> VerificationReport:
    idx = SourceIndex(source_text, para_numbers, page_count)
    result = VerificationReport(para_detected=len(idx.para_numbers), page_count=page_count)
    seen: set[tuple[str, str]] = set()

    def add(kind, text, status, section, detail=""):
        key = (kind, text.lower())
        if key in seen:
            return
        seen.add(key)
        result.items.append(CheckItem(kind, text, status, section, detail))

    for title, body in _section_titles(report):
        if not body.strip():
            continue
        for m in _QUOTE_RE.finditer(body):
            quote = m.group(1).strip()
            if len(quote.split()) < 5:
                continue
            status, detail = idx.quote_status(quote)
            add("Quotation", f"“{quote[:160]}{'…' if len(quote) > 160 else ''}”", status, title, detail)
        for rx in _CITATION_RES:
            for m in rx.finditer(body):
                cite = m.group(0).strip(" ,;")
                c = _compact(cite)
                add("Citation", cite, FOUND if c and c in idx.compact else NOT_FOUND, title)
        for m in _SECTION_RE.finditer(body):
            for token in _SECTION_TOKEN.findall(m.group(1) + (m.group(2) or "")):
                key = _section_key(token)
                base = re.match(r"\d{1,3}[a-z]{0,4}", key).group(0)
                if key in idx.section_tokens:
                    status, detail = FOUND, ""
                elif base in idx.section_tokens:
                    status, detail = CLOSE, f"section {base.upper()} is in the judgment; the sub-clause is not"
                else:
                    status, detail = NOT_FOUND, ""
                add("Section", f"Section {token.strip()}", status, title, detail)
        for d in _dates(normalise(body)):
            label = f"{d[2]:02d}-{d[1]:02d}-{d[0]}"
            add("Date", label, FOUND if d in idx.dates else NOT_FOUND, title)
        for m in _AMOUNT_RE.finditer(body):
            digits = re.sub(r"[^\d.]", "", m.group(1)).rstrip(".")
            if not digits or len(digits.replace(".", "")) < 3:
                continue
            ok = digits in idx.amounts or digits in idx.numbers
            add("Amount", m.group(0).strip(), FOUND if ok else NOT_FOUND, title)
        if idx.para_numbers:
            for m in _PARA_REF.finditer(body):
                for n in _expand(m.group(1)):
                    add("Paragraph ref", f"para {n}", FOUND if n in idx.para_numbers else NOT_FOUND, title,
                        "" if n in idx.para_numbers else "no paragraph with this number was detected")
        if page_count:
            for m in _PAGE_REF.finditer(body):
                for n in _expand(m.group(1), limit=page_count + 1):
                    ok = 1 <= n <= page_count
                    add("Page ref", f"p. {n}", FOUND if ok else NOT_FOUND, title,
                        "" if ok else f"the judgment has only {page_count} pages")
    order = {NOT_FOUND: 0, CLOSE: 1, FOUND: 2}
    result.items.sort(key=lambda i: (order[i.status], KINDS.index(i.kind)))
    return result


def check_value(value: str, source_text: str) -> bool:
    """True if a short value (citation, date, case number) appears in the source text."""
    if not value or not value.strip():
        return False
    v = _compact(value)
    if v and v in _compact(source_text):
        return True
    d = _dates(normalise(value))
    return bool(d) and d <= _dates(normalise(source_text))
