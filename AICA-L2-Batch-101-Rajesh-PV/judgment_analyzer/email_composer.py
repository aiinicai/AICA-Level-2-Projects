"""Compose client-ready emails from an analysis.

* Removes internal markers before anything reaches a client: page references
  such as "(p. 3)" / "(pp. 3, 6, 7)" and the labels "[Court Finding]" /
  "[AI Observation]".
* Detects points that must be resolved by the reviewer first ("[Uncertain]").
* Builds one personalised email (subject, HTML and plain text) per recipient.
"""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field

from .exporter import markdown_to_plain, parse_blocks, split_inline, strip_inline
from .prompts import REPORT_SECTIONS
from .response_parser import MISSING_TEXT, ParsedReport

# Sections offered for client emails: (section number, default selected?)
EMAIL_SECTION_CHOICES: tuple[tuple[int, bool], ...] = (
    (1, True),    # Case Details
    (2, True),    # Executive Summary
    (8, False),   # Final Decision or Order
    (12, True),   # Practical Implications
    (13, False),  # Key Insights
)

# Sections offered for the internal (employee / litigation team) version.
INTERNAL_SECTION_CHOICES: tuple[tuple[int, bool], ...] = (
    (1, True),    # Case Details
    (2, True),    # Executive Summary
    (4, True),    # Issues
    (7, False),   # Court's Analysis and Reasoning
    (8, True),    # Final Decision or Order
    (9, True),    # Ratio Decidendi
    (12, False),  # Practical Implications
    (13, True),   # Key Insights
    (14, False),  # Points for Consideration
)

INTERNAL_DISCLAIMER = (
    "Internal research note for the firm's team only - not for circulation outside the firm. The summary was "
    "prepared with AI assistance and reviewed before release. Paragraph references point to the original "
    "judgment; read the relevant paragraphs (copy in the precedent register) before relying on any point."
)

DEFAULT_INTERNAL_INTRO = ("Please find below the summary of a judgment added to our precedent register. Paragraph "
                          "references are to the original judgment, which is available in the register.")

CLIENT_DISCLAIMER = (
    "This update summarises a published judgment for general information only. It does not constitute "
    "legal, tax or professional advice on your specific circumstances. Please contact us before acting on it."
)

DEFAULT_INTRO = ("We would like to bring to your attention a recent judgment that may be relevant to you. "
                 "A brief summary is set out below.")

# --------------------------------------------------------------- cleaning ---
_PAGE_WORD = r"(?:pp?\.?|pages?|pgs?\.?)"
_PAGE_NUMS = r"\d+[a-z]?(?:\s*(?:-|–|—|to|,|and|&)\s*\d+[a-z]?)*"
# "(p. 3)", "(pp. 3, 6, 7)", "(pages 3-5)", "[p. 12]", "(see p. 4)", "(p. 3; p. 9)"
_PAGE_REF_RE = re.compile(
    rf"\s*[\(\[]\s*(?:see\s+|at\s+)?{_PAGE_WORD}\s*{_PAGE_NUMS}"
    rf"(?:\s*[;,]\s*(?:{_PAGE_WORD}\s*)?{_PAGE_NUMS})*\s*[\)\]]",
    re.IGNORECASE,
)
_LABEL_RE = re.compile(r"[\[\{\(]\s*(?:Court Findings?|AI Observations?|AI Generated)\s*[\]\}\)]\s*:?\s*",
                       re.IGNORECASE)
_MARKER_RE = re.compile(r"\[(?:Para|Page) \d+(?:, part \d+/\d+)?\]\s*")
_UNCERTAIN_RE = re.compile(r"[\[\{]\s*Uncertain\s*[\]\}]", re.IGNORECASE)
_NOT_STATED_RE = re.compile(r"not stated in the judgment", re.IGNORECASE)


# "(para 12; p. 5)" / "(paras 3-4, pp. 2-3)" -> "(para 12)" / "(paras 3-4)"
_PARA_WITH_PAGE_RE = re.compile(rf"(\(\s*paras?\.?\s*[^()]*?)\s*[;,]\s*{_PAGE_WORD}\s*{_PAGE_NUMS}\s*\)", re.IGNORECASE)


def clean_for_client(text: str) -> str:
    """Remove page references and internal labels (paragraph references are kept); tidy the spacing."""
    text = _MARKER_RE.sub("", text or "")
    text = _PARA_WITH_PAGE_RE.sub(r"\1)", text)
    text = _PAGE_REF_RE.sub("", text)
    text = _LABEL_RE.sub("", text)
    text = re.sub(r"(?<![\w*])(\*\*|__)\s*\1(?![\w*])", "", text)  # bold markers left empty, e.g. "**[Court Finding]**"
    text = re.sub(r"[ \t]+([.,;:])", r"\1", text)       # "word ." -> "word."
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"(?m)^([ \t]*[-*+•][ \t]*|\d+\.[ \t]*)\s*$\n?", "", text)  # bullets left empty
    text = re.sub(r"(?m)[ \t]+$", "", text)
    return text.strip()


@dataclass
class ReviewItem:
    line_no: int
    text: str
    blocking: bool  # True = must be fixed before approval


def find_review_items(text: str) -> list[ReviewItem]:
    """Lines the reviewer must look at. '[Uncertain]' blocks approval; 'Not stated' is a warning."""
    items = []
    for i, line in enumerate((text or "").splitlines(), 1):
        if _UNCERTAIN_RE.search(line):
            items.append(ReviewItem(i, line.strip(), True))
        elif _NOT_STATED_RE.search(line) or MISSING_TEXT.strip("_") in line:
            items.append(ReviewItem(i, line.strip(), False))
    return items


def _case_detail(report: ParsedReport, label_pattern: str) -> str:
    """Value of a 'Label: value' line in Case Details, cleaned for clients ('' if not stated)."""
    for line in report.sections.get(1, "").splitlines():
        plain = "".join(r[0] for r in split_inline(line)).strip(" -*•\t")
        m = re.match(rf"(?i){label_pattern}[^:]*:\s*(.+)", plain)
        if m:
            value = clean_for_client(m.group(1)).strip().rstrip(".")
            if value and not _NOT_STATED_RE.search(value) and not _UNCERTAIN_RE.search(value):
                return value
    return ""


def extract_case_title(report: ParsedReport) -> str:
    """Pull the case title from the Case Details section, if present."""
    return _case_detail(report, r"case title")


_REPORTER_RE = re.compile(r"[\[(]\d{4}[\])]")  # "[2026] 190 taxmann.com 964", "(2024) 5 SCC 1"


def extract_citation(report: ParsedReport) -> str:
    """Prefer a law-report citation (e.g. '[2026] 190 taxmann.com 964 (Bangalore - Trib.)')
    over the case/appeal number; fall back to the full value."""
    value = _case_detail(report, r"citation")
    if not value:
        return ""
    parts = [p.strip() for p in re.split(r";|\s+/\s+", value) if p.strip()]
    reported = [p for p in parts if _REPORTER_RE.search(p)]
    return reported[0] if reported else value


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def format_judgment_date(text: str) -> str:
    """Convert common date styles to DD-MM-YYYY; return '' if no clear date is found."""
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", (text or "").lower()).replace(",", " ")
    m = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b", t)  # 21-09-2026 / 21.09.2026
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.search(r"\b(\d{1,2})\s+([a-z]{3,9})\s+(\d{4})\b", t)  # 21 September 2026
        if m and m.group(2)[:3] in _MONTHS:
            d, mo, y = int(m.group(1)), _MONTHS[m.group(2)[:3]], int(m.group(3))
        else:
            m = re.search(r"\b([a-z]{3,9})\s+(\d{1,2})\s+(\d{4})\b", t)  # September 21, 2026
            if not (m and m.group(1)[:3] in _MONTHS):
                return ""
            d, mo, y = int(m.group(2)), _MONTHS[m.group(1)[:3]], int(m.group(3))
    if not (1 <= d <= 31 and 1 <= mo <= 12):
        return ""
    return f"{d:02d}-{mo:02d}-{y}"


def extract_judgment_date(report: ParsedReport) -> str:
    return format_judgment_date(_case_detail(report, r"date of (?:judgment|order|decision)"))


def strip_page_refs(text: str) -> str:
    """Remove page references only (keep [Court Finding] / [AI Observation] labels for the reviewer)."""
    text = _MARKER_RE.sub("", text or "")
    text = _PARA_WITH_PAGE_RE.sub(r"\1)", text)
    text = _PAGE_REF_RE.sub("", text)
    return re.sub(r"[ \t]+([.,;:])", r"\1", text).strip()


def build_client_body(report: ParsedReport, section_numbers: list[int]) -> str:
    """Markdown body (selected sections) for the reviewer to edit. Page references are removed; the
    [Court Finding] / [AI Observation] labels stay visible in the editor so the reviewer can tell court
    findings from AI commentary - they are removed automatically from what is sent."""
    parts = []
    for number in section_numbers:
        title = REPORT_SECTIONS[number - 1].title
        parts.append(f"## {title}\n\n{strip_page_refs(report.section_body(number))}")
    return "\n\n".join(parts).strip()


def build_internal_body(report: ParsedReport, section_numbers: list[int], register_ref: str = "") -> str:
    """Markdown body for the litigation team: the register reference first, then the selected sections
    (paragraph references kept, page references removed)."""
    parts = [f"**Precedent register reference:** {register_ref}"] if register_ref else []
    for number in section_numbers:
        title = REPORT_SECTIONS[number - 1].title
        parts.append(f"## {title}\n\n{strip_page_refs(report.section_body(number))}")
    return "\n\n".join(parts).strip()


def default_subject(case_title: str, citation: str = "", judgment_date: str = "") -> str:
    """e.g. 'Judgment update: A v. B - [2026] 190 taxmann.com 964 (Bangalore - Trib.)[21-09-2026]'."""
    subject = f"Judgment update: {case_title}" if case_title else "Judgment update"
    if citation and citation not in subject:
        subject += f" - {citation}"
    if judgment_date:
        subject += f"[{judgment_date}]" if citation else f" [{judgment_date}]"
    return subject


# ------------------------------------------------------------ data types ---
@dataclass
class SenderProfile:
    name: str = ""
    designation: str = ""
    firm: str = ""
    email: str = ""
    phone: str = ""

    def validate(self) -> list[str]:
        from .recipients import is_valid_email

        problems = []
        if not self.name.strip():
            problems.append("Enter your name.")
        if not is_valid_email(self.email):
            problems.append("Enter a valid sender email address.")
        for label, value in (("Name", self.name), ("Designation", self.designation), ("Firm", self.firm),
                             ("Phone", self.phone)):
            if len(value) > 120:
                problems.append(f"{label} is too long.")
        return problems

    def signature_lines(self) -> list[str]:
        return [x for x in (self.name, self.designation, self.firm, self.phone, self.email) if x.strip()]


@dataclass
class EmailMessage:
    to_name: str
    to_email: str
    subject: str
    html: str
    text: str


@dataclass
class EmailContent:
    """Reviewed content shared by all recipients; only the greeting is personalised."""
    subject: str
    intro: str
    body_markdown: str
    sender: SenderProfile
    disclaimer: str = ""  # optional closing note; empty = none
    extra: dict = field(default_factory=dict)

    def fingerprint(self) -> str:
        """Hash of exactly what was approved (stored in the audit log)."""
        raw = "\x1f".join([self.subject, self.intro, self.body_markdown, self.disclaimer,
                           *self.sender.signature_lines()])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------- rendering ---
def _inline_html(text: str) -> str:
    out = []
    for content, bold, italic in split_inline(text):
        piece = html.escape(content)
        if italic:
            piece = f"<i>{piece}</i>"
        if bold:
            piece = f"<b>{piece}</b>"
        out.append(piece)
    return "".join(out)


def markdown_to_email_html(markdown: str) -> str:
    """Email-safe HTML (inline styles only) for the small Markdown subset we use."""
    out: list[str] = []
    list_tag = None

    def close_list():
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    for b in parse_blocks(markdown):
        if b.kind in ("bullet", "numbered"):
            tag = "ul" if b.kind == "bullet" else "ol"
            if list_tag != tag:
                close_list()
                out.append(f'<{tag} style="margin:4px 0 10px 22px;padding:0;">')
                list_tag = tag
            out.append(f'<li style="margin:3px 0;text-align:justify;">{_inline_html(b.text)}</li>')
            continue
        close_list()
        if b.kind == "heading":
            size = 16 if b.level <= 2 else 14
            color = "#0B1F3A" if b.level <= 2 else "#4B2E83"
            out.append(f'<p style="font-size:{size}px;font-weight:bold;color:{color};margin:18px 0 6px 0;">'
                       f"{html.escape(strip_inline(b.text))}</p>")
        elif b.kind == "quote":
            out.append(f'<p style="margin:6px 0 6px 16px;color:#444;font-style:italic;text-align:justify;">'
                       f'{_inline_html(b.text)}</p>')
        elif b.kind == "paragraph":
            out.append(f'<p style="margin:6px 0;text-align:justify;">{_inline_html(b.text)}</p>')
    close_list()
    return "\n".join(out)


def _greeting(name: str, salutation: str = "") -> str:
    who = " ".join(x for x in (salutation.strip(), name.strip()) if x) or "Sir/Madam"
    return f"Dear {who},"


BLANK_GREETING = "Dear <<Recipient name>>,"   # for drafts created without a recipient


def render_email(content: EmailContent, to_name: str, to_email: str, salutation: str = "",
                 subject_prefix: str = "", greeting: str | None = None) -> EmailMessage:
    """Final email. Internal labels ([Court Finding], [AI Observation], [AI Generated]), page references
    and Markdown symbols never reach the recipient."""
    greeting = greeting or _greeting(to_name, salutation)
    body = clean_for_client(content.body_markdown)
    intro = clean_for_client(content.intro)
    sig = content.sender.signature_lines()
    subject = f"{subject_prefix}{content.subject}".strip()
    font = "font-family:Calibri,Arial,sans-serif;font-size:14px;color:#1B1F2A;line-height:1.45;"
    sig_html = "<br>".join(html.escape(s) for s in sig)
    note_html = (f'<p style="margin:22px 0 0 0;font-size:11px;color:#6B7285;text-align:justify;">'
                 f'{html.escape(content.disclaimer)}</p>\n' if content.disclaimer.strip() else "")
    body_html = f"""<div style="{font}">
<p style="margin:0 0 10px 0;">{html.escape(greeting)}</p>
<p style="margin:0 0 10px 0;text-align:justify;">{html.escape(intro).replace(chr(10), '<br>')}</p>
{markdown_to_email_html(body)}
<p style="margin:18px 0 4px 0;">Kind regards,</p>
<p style="margin:0;">{sig_html}</p>
{note_html}</div>"""
    text = "\n".join([
        greeting, "", intro, "", markdown_to_plain(body).strip(), "",
        "Kind regards,", *sig, *(["", content.disclaimer] if content.disclaimer.strip() else []),
    ])
    return EmailMessage(to_name, to_email, subject, body_html, text)


# ------------------------------------------------------------ persistence ---
def _profile_path():
    from .config import user_config_dir

    return user_config_dir() / "sender_profile.json"


def load_sender_profile() -> SenderProfile:
    import json

    try:
        data = json.loads(_profile_path().read_text(encoding="utf-8"))
        return SenderProfile(**{k: str(v) for k, v in data.items() if k in SenderProfile.__dataclass_fields__})
    except (OSError, ValueError, TypeError):
        return SenderProfile()


def save_sender_profile(profile: SenderProfile) -> None:
    import json
    from dataclasses import asdict

    _profile_path().write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")
