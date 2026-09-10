"""
lc_parser.py
------------
Turns raw LC text into a list of "raw fields" (tag/header + value text),
and provides the step-3 gating checks:
    - is this document an LC at all?
    - for an Issued/Transmitted LC, does it carry a Documentary Credit No.?

Two parsing strategies are used:
  1. SWIFT-style field tags - this is how the overwhelming majority of
     issued/transmitted LCs (MT700/MT710 based) are laid out, even after
     being rendered to PDF/reprinted by the advising/issuing bank. The tag
     is usually printed as "F" + a 2-digit field number + an optional
     1-2 letter suffix, e.g. "F27:", "F40A:", "F31D:", "F46A:" (some
     systems omit the leading "F" and just print "27:", "40A:" etc. - both
     are recognised). The bank's own header text is printed on the SAME
     line as the tag ("F20: Documentary Credit Number"), and the actual
     value is indented on the line(s) below it.
  2. A fallback "numbered paragraph" parser for free-form draft LCs that are
     typed up by an applicant/trade team without SWIFT tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RawField:
    tag: str          # e.g. "20", "45A", or "Para 3" for fallback mode
    header_hint: str  # any header text found next to the tag (may be empty)
    value: str        # the field's body text
    order: int        # position in the document (0-based)


# ---------------------------------------------------------------------------
# LC / field-tag recognition
# ---------------------------------------------------------------------------

# Recognised SWIFT field tags for MT700 (Issue of a Documentary Credit) and
# the handful of MT707/MT710 tags that also show up in amendments/second
# beneficiary advices. Matching is done on the numeric+letter tag only; the
# human-readable header (if the bank printed one) is picked up separately.
_KNOWN_TAGS = {
    "20", "21", "23", "27", "31C", "31D", "32B", "39A", "39B", "39C",
    "40A", "40E", "41A", "41D", "42A", "42C", "42M", "42P",
    "43P", "43T", "44A", "44B", "44C", "44D", "44E", "44F",
    "45A", "45B", "46A", "46B", "47A", "47B", "48", "49",
    "50", "51A", "51D", "52A", "52D", "53A", "53D", "56A", "56D",
    "57A", "57D", "58A", "58D", "59", "71B", "71D", "72", "72Z", "73", "77J", "78",
}

# A generic SWIFT field tag line looks like ":27:", "27:", "27 :", or - the
# very common bank "message reprint" convention - "F27:", "F40A:", "F31D:"
# (an optional leading "F" before the 2-digit + optional letter code),
# possibly followed on the same line by the bank's own printed header, e.g.
#   "F40A: Form of Documentary Credit"
#   ":45A: DESCRIPTION OF GOODS AND/OR SERVICES"
_TAG_LINE_RE = re.compile(
    r"^\s*:?F?(\d{2}[A-Za-z]{0,2})\s*:\s*(.*)$"
)

# Many bank SWIFT-message reprints wrap the actual field data between a
# "Message Text" heading and a "Message Trailer" heading, with unrelated
# envelope/administrative text (sender/receiver, MUR, checksums, PKI
# signature block, etc.) before and after. Slicing to this window before
# tokenising fields keeps that boilerplate out of the first/last field's
# value. If the markers aren't present (e.g. a plain draft LC), the whole
# text is used unchanged.
_MESSAGE_TEXT_MARKER = re.compile(r"(?im)^\s*Message Text\s*$")
_MESSAGE_TRAILER_MARKER = re.compile(r"(?im)^\s*Message Trailer\s*$")


def _slice_message_body(text: str) -> str:
    start = 0
    m1 = _MESSAGE_TEXT_MARKER.search(text)
    if m1:
        start = m1.end()
    end = len(text)
    m2 = _MESSAGE_TRAILER_MARKER.search(text, start)
    if m2:
        end = m2.start()
    return text[start:end]

_LC_KEYWORDS = [
    "documentary credit",
    "letter of credit",
    "irrevocable",
    "revocable",
    "mt700",
    "mt 700",
    "swift",
    "beneficiary",
    "applicant",
    "issuing bank",
    "advising bank",
]

_DC_NUMBER_PATTERNS = [
    re.compile(r"documentary\s+credit\s+number\D{0,10}([A-Za-z0-9/\-]{4,})", re.I),
    re.compile(r"\bl\s*/?\s*c\s*no\.?\D{0,5}([A-Za-z0-9/\-]{4,})", re.I),
    re.compile(r"\bcredit\s+no\.?\D{0,5}([A-Za-z0-9/\-]{4,})", re.I),
    re.compile(r"\bdc\s*no\.?\D{0,5}([A-Za-z0-9/\-]{4,})", re.I),
]


def looks_like_lc(text: str) -> bool:
    """Heuristic check: does this document look like an LC / documentary credit at all?"""
    lower = text.lower()
    hits = sum(1 for kw in _LC_KEYWORDS if kw in lower)
    has_tags = _count_known_tags(text) >= 3
    return has_tags or hits >= 3


def _count_known_tags(text: str) -> int:
    count = 0
    for line in text.split("\n"):
        m = _TAG_LINE_RE.match(line)
        if m and m.group(1).upper() in _KNOWN_TAGS:
            count += 1
    return count


def _looks_like_header_label(s: str) -> bool:
    """True if 's' reads like a printed field description (e.g. 'Documentary
    Credit Number') rather than an actual value - mirrors the heuristic used
    by _extract_swift_fields so the two stay consistent."""
    return bool(s) and len(s) <= 60 and not re.search(r"\d", s) and not s.isupper() and s[0:1].isalpha()


def find_dc_number(text: str) -> Optional[str]:
    """Look for a Documentary Credit Number via field :20: first, then via
    free-text patterns such as 'L/C No', 'Credit No', 'DC No'."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = _TAG_LINE_RE.match(line)
        if m and m.group(1).upper() == "20":
            rest = m.group(2).strip()
            if rest and not _looks_like_header_label(rest):
                return rest
            # 'rest' is empty or just a header label like "Documentary Credit
            # Number" printed on the tag line - the actual value is on one of
            # the following lines, up to the next field tag.
            for j in range(i + 1, min(i + 4, len(lines))):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                if _TAG_LINE_RE.match(candidate):
                    break
                return candidate
    for pattern in _DC_NUMBER_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return None


def classify_document(text: str, declared_type: str) -> "ClassificationResult":
    """
    Implements the step-3 gating logic.

    declared_type: "draft" or "issued"
    """
    from models import DocumentClassification  # local import avoids cycle at module import time

    if not looks_like_lc(text):
        return DocumentClassification(
            is_lc=False,
            dc_number=None,
            reason=(
                "The submitted document does not appear to be a Letter of "
                "Credit / Documentary Credit. Please submit a proper LC copy."
            ),
        )

    dc_number = find_dc_number(text)

    if declared_type == "issued" and not dc_number:
        return DocumentClassification(
            is_lc=False,
            dc_number=None,
            reason=(
                "This document was submitted as an Issued / Transmitted LC "
                "but no Documentary Credit Number (field 20 / 'L/C No.') "
                "could be found. Please submit a proper Issued / Transmitted "
                "LC copy."
            ),
        )

    return DocumentClassification(is_lc=True, dc_number=dc_number, reason="")


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def extract_fields(text: str) -> List[RawField]:
    """
    Try SWIFT-tag based extraction first; if too few tags are recognised,
    fall back to a numbered-paragraph splitter suitable for free-form
    draft LCs.
    """
    body = _slice_message_body(text)
    tagged = _extract_swift_fields(body)
    if len(tagged) >= 3:
        return tagged
    return _extract_numbered_paragraphs(body)


def _extract_swift_fields(text: str) -> List[RawField]:
    """
    Tokenise "Fxx: <header>" / "xx: <header>" tag lines into fields. The
    bank's header text (printed on the tag line itself) is always kept as
    the header; every following line up to the next tag becomes the
    field's value. This matches how bank SWIFT-message reprints are
    consistently laid out (header on the tag line, value indented below -
    even for one-word values like "IRREVOCABLE" or "ALLOWED").
    """
    lines = text.split("\n")
    fields: List[RawField] = []
    current_tag = None
    current_header = ""
    current_value_lines: List[str] = []
    order = 0

    def flush():
        nonlocal current_tag, current_header, current_value_lines, order
        if current_tag is not None:
            value = "\n".join(current_value_lines).strip()
            fields.append(RawField(current_tag, current_header.strip(), value, order))
            order += 1
        current_tag = None
        current_header = ""
        current_value_lines = []

    for line in lines:
        m = _TAG_LINE_RE.match(line)
        if m and m.group(1).upper() in _KNOWN_TAGS:
            flush()
            current_tag = m.group(1).upper()
            current_header = m.group(2).strip()
        else:
            if current_tag is not None:
                current_value_lines.append(line)
    flush()
    return fields


# Matches "1.", "1)", "(1)", "a.", "a)", "A)" style paragraph numbering at
# the start of a line.
_PARA_RE = re.compile(r"^\s*(\(?\d{1,3}\)?[.)]|\(?[a-zA-Z]\)?[.)])\s+(.*)$")


def _extract_numbered_paragraphs(text: str) -> List[RawField]:
    lines = text.split("\n")
    fields: List[RawField] = []
    current_no = None
    current_lines: List[str] = []
    order = 0

    def flush():
        nonlocal current_no, current_lines, order
        if current_no is not None:
            value = "\n".join(current_lines).strip()
            if value:
                fields.append(RawField(f"Para {order + 1}", current_no, value, order))
                order += 1
        current_no = None
        current_lines = []

    for line in lines:
        m = _PARA_RE.match(line)
        if m:
            flush()
            current_no = m.group(1)
            current_lines.append(m.group(2))
        else:
            if current_no is not None:
                current_lines.append(line)
    flush()

    if fields:
        return fields

    # Last-resort fallback: split on blank lines into paragraphs so the
    # user still gets *something* to review rather than an empty summary.
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [
        RawField(f"Para {i + 1}", "", p, i)
        for i, p in enumerate(paras)
    ]


# ---------------------------------------------------------------------------
# Splitting a block of text (e.g. field 46A / 47A) into individual items
# ---------------------------------------------------------------------------

_ITEM_MARKER_RE = re.compile(
    r"(?m)^\s*(?:"
    r"[+*•\-]\s*"           # bullet symbols - space after is optional
    r"|\(?\d{1,2}\)\s*"     # "1)" / "(1)" - space optional (real docs often omit it)
    r"|\(?\d{1,2}\.\s+"     # "1." - space required, else risks matching decimals
    r"|\(?[A-Za-z]\)\s*"    # "A)" / "(A)" - space optional
    r"|\(?[A-Za-z]\.\s+"    # "A." - space required, else risks matching abbreviations like 'e.g.'
    r")"
)


def split_into_items(block_text: str) -> List[str]:
    """
    Split a documents-required / additional-conditions block into
    individual document/condition items using common bank formatting
    conventions: +, -, *, bullet, "1.", "1)", or the very common single
    uppercase-letter lettering ("A)", "B)", ... "N)") banks use for
    documents-required / additional-conditions lists. Falls back to
    newline- or sentence-splitting if no markers are found.
    """
    text = block_text.strip()
    if not text:
        return []

    marker_positions = [m.start() for m in _ITEM_MARKER_RE.finditer(text)]
    if len(marker_positions) >= 2:
        items = []
        for i, pos in enumerate(marker_positions):
            end = marker_positions[i + 1] if i + 1 < len(marker_positions) else len(text)
            chunk = text[pos:end].strip()
            chunk = _ITEM_MARKER_RE.sub("", chunk, count=1).strip()
            if chunk:
                items.append(chunk)
        if items:
            return items

    # No bullet markers: try one-item-per-line (common in simpler LCs)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) >= 2:
        return lines

    # Single blob: try sentence-ish splitting as a last resort.
    sentences = re.split(r"(?<=[.;])\s+(?=[A-Z0-9])", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences if sentences else [text]
