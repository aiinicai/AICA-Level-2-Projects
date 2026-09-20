"""
Word gap report generator.

A readiness report issued by the assessor on a client, with management
responses. build_report receives the score from its caller and computes nothing:
the report presents a result, it never decides one.

Report structure (the cover is unnumbered; the sections after it are numbered):
    Cover
    1. Scope, basis and limitations
    2. Role determination
    3. Readiness summary with rule-wise breakdown
    4. Claims not supported by evidence (controls gated for want of evidence),
       written only when a claim is struck
    5. Detailed observations - Observation / Impact / Further Actions / Management Response

The numbers run on without a gap: when no claim is struck, detailed observations
are section 4.

A control whose citation_status in rules/*.yaml is pending carries the marker
CITATION_PENDING on its observation and in the unevidenced-claims table.

python-docx rather than docx-js, because the product ships as a single Windows
executable and cannot carry a Node runtime.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

# Severity drives the order findings are presented in.
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

BAND_COLOUR = {
    "Critical": RGBColor(0xB3, 0x1B, 0x1B),
    "Developing": RGBColor(0xB5, 0x6A, 0x00),
    "Substantial": RGBColor(0x1F, 0x5C, 0x2E),
    "Mature": RGBColor(0x1F, 0x5C, 0x2E),
}

# Printed against every control whose citation has not yet been checked against the
# gazette text. It is driven only by citation_status in the rule files, never by a
# control id.
CITATION_PENDING = "Citation pending verification"

_COMMENCEMENT = (
    "The DPDP Rules, 2025 were notified on 13 November 2025 with phased "
    "commencement. Certain provisions, including the consent manager framework, "
    "commence after the date of this report. Observations on those provisions are "
    "forward-looking and are marked as such."
)

# Report wording. It never names the forbidden assurance word, not even to
# disclaim it: a readiness review cannot make that assertion.
REPORT_TEXT = {
    "client": {
        "title": "DPDP Readiness Assessment",
        "issued_line": "Readiness report issued by {by}",
        "by_label": "Assessed by",
        "scope_lead": (
            "We have assessed the entity against {n} controls derived from the "
            "Digital Personal Data Protection Act, 2023 and the Digital Personal Data "
            "Protection Rules, 2025. Controls that cannot apply to the entity on the facts "
            "stated have been excluded from both the score and this report."
        ),
        "limitations": [
            "This report records observations against the criteria stated in the control "
            "catalogue, on the evidence made available to us. It is not an audit, a "
            "certification, or an assurance engagement, and no opinion is expressed.",

            "Assurance terms are deliberately not used. A control assessed as Present means "
            "supporting evidence was produced and examined on a test-check basis; it does "
            "not confirm that the control operated effectively throughout the period.",

            "Controls carrying a weight of 4 or 5 have been scored at nil where no supporting "
            "evidence was produced, irrespective of the status asserted by management. "
            "Self-declaration alone has not been accepted as evidence.",

            "This report does not constitute legal advice. Determinations on the "
            "applicability of statutory provisions, and on the entity's role under the Act, "
            "should be confirmed with legal counsel before being relied upon.",

            _COMMENCEMENT,
        ],
        "role_intro": (
            "The obligations that apply turn on whether the entity acts as a Data Fiduciary "
            "or a Data Processor for the engagement assessed. The role is determined by who "
            "decides the purpose and means of processing, and may differ between engagements "
            "of the same entity."
        ),
        "gated_lead": (
            "Management asserted that the following {n} controls were in place. "
            "No supporting evidence was produced, and each has therefore been scored at nil. "
            "This section is presented separately because the position may improve once "
            "the underlying records are made available."
        ),
        "findings_intro": (
            "Findings are presented in order of severity. Each records the observation, its "
            "impact, the further action recommended, and the response received from management."
        ),
        "response_label": "Management Response",
        "response_missing": "Response awaited.",
        "owner_label": "Owner",
        "footer": "DPDP Readiness Assessment - {name} - Observations only, not an assurance report",
        "filename_prefix": "DPDP_Readiness_",
        # Controls in scope with no answer score nil. The catalogue can grow under
        # an existing file, so the scope says how many rather than let a score
        # move unexplained between reports.
        "unassessed_one": "1 control is not yet assessed; it scores nil until assessed.",
        "unassessed_many": "{n} controls are not yet assessed; they score nil until assessed.",
    },
}



# --------------------------------------------------------------------------
# Low-level formatting helpers
# --------------------------------------------------------------------------

def _shade(cell, hex_colour: str) -> None:
    """Apply background shading to a table cell."""
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), hex_colour)
    cell._tc.get_or_add_tcPr().append(el)


def _cell_text(cell, text: str, *, bold=False, size=9.5, colour=None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if colour:
        run.font.color.rgb = colour


def _footer(doc: Document, text: str) -> None:
    for section in doc.sections:
        p = section.footer.paragraphs[0]
        p.text = text
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)


# --------------------------------------------------------------------------
# Report sections
# --------------------------------------------------------------------------

def _cover(doc: Document, client, result: dict, text: dict) -> None:
    for _ in range(4):
        doc.add_paragraph()

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(text["title"])
    run.bold = True
    run.font.size = Pt(26)

    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = s.add_run("Digital Personal Data Protection Act, 2023\nDPDP Rules, 2025")
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    doc.add_paragraph()
    n = doc.add_paragraph()
    n.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = n.add_run(client.name)
    run.bold = True
    run.font.size = Pt(16)

    e = doc.add_paragraph()
    e.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = e.add_run(f"{client.entity_type}  |  Assessed as Data {client.role.title()}")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    i = doc.add_paragraph()
    i.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = i.add_run(text["issued_line"].format(by=client.assessed_by or "the assessor",
                                                name=client.name))
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    doc.add_paragraph()
    b = doc.add_paragraph()
    b.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = b.add_run(f"Readiness score  {result['score']}  -  {result['band']}")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = BAND_COLOUR.get(result["band"], RGBColor(0, 0, 0))

    for _ in range(6):
        doc.add_paragraph()

    d = doc.add_paragraph()
    d.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = d.add_run(
        f"Assessment date: {client.assessment_date}\n"
        f"{text['by_label']}: {client.assessed_by or 'Not stated'}\n"
        f"Report generated: {date.today().isoformat()}"
    )
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    doc.add_page_break()


def _scope(doc: Document, controls: list, responses: dict, result: dict, text: dict) -> None:
    doc.add_heading("1. Scope, basis and limitations", level=1)

    doc.add_paragraph(text["scope_lead"].format(n=len(controls)))
    unassessed = sum(1 for c in controls if not (responses.get(c.id) or {}).get("status"))
    if unassessed:
        doc.add_paragraph(text["unassessed_one"] if unassessed == 1
                          else text["unassessed_many"].format(n=unassessed))

    doc.add_heading("Basis of scoring", level=2)
    doc.add_paragraph(
        "Each control is assessed as Present, Partial or Absent, and carries a weight "
        "from 1 to 5 reflecting the consequence of its absence. The readiness score is "
        "the weighted proportion of controls satisfied, expressed out of 100."
    )
    if any(c.citation_status == "pending" for c in controls):
        doc.add_paragraph(
            f'Controls marked "{CITATION_PENDING}" cite a provision of the Act or the Rules '
            "that has not yet been checked against the gazette text. They are assessed and "
            "scored in the same way as every other control."
        )

    doc.add_heading("Limitations", level=2)
    for item in text["limitations"]:
        doc.add_paragraph(item, style="List Bullet")


def _role_section(doc: Document, client, text: dict) -> None:
    doc.add_heading("2. Role determination", level=1)
    doc.add_paragraph(text["role_intro"])
    p = doc.add_paragraph()
    p.add_run("Determination: ").bold = True
    p.add_run(f"Data {client.role.title()}")

    if client.role_reasoning:
        doc.add_paragraph(client.role_reasoning)


def _summary(doc: Document, controls: list, responses: dict, result: dict) -> None:
    doc.add_heading("3. Readiness summary", level=1)

    p = doc.add_paragraph()
    p.add_run("Score: ").bold = True
    run = p.add_run(f"{result['score']} out of 100  ({result['band']})")
    run.bold = True
    run.font.color.rgb = BAND_COLOUR.get(result["band"], RGBColor(0, 0, 0))
    doc.add_paragraph(
        f"Weighted marks earned {result['earned']} of {result['available']} available, "
        f"across {result['controls_assessed']} applicable controls."
    )

    # Rule-wise breakdown
    doc.add_heading("Rule-wise position", level=2)
    rules = {}
    for c in controls:
        r = rules.setdefault(c.rule_id, {"title": c.rule_title, "P": 0, "Pa": 0, "A": 0})
        status = responses.get(c.id, {}).get("status", "Absent")
        r[{"Present": "P", "Partial": "Pa", "Absent": "A"}[status]] += 1

    widths = [Inches(0.7), Inches(3.0), Inches(0.8), Inches(0.8), Inches(0.8)]
    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for cell, text, w in zip(table.rows[0].cells,
                             ["Rule", "Area", "Present", "Partial", "Absent"], widths):
        _cell_text(cell, text, bold=True)
        _shade(cell, "E8E8E8")
        cell.width = w

    for rid in sorted(rules, key=lambda r: int(r[1:])):
        r = rules[rid]
        row = table.add_row().cells
        for cell, text, w in zip(row, [rid, r["title"], str(r["P"]), str(r["Pa"]), str(r["A"])], widths):
            _cell_text(cell, text)
            cell.width = w


def _gated(doc: Document, controls: list, result: dict, text: dict) -> bool:
    """Controls claimed as satisfied but scored at nil for want of evidence.

    Returns whether the section was written, so the sections after it are
    numbered without a gap.
    """
    gated = result.get("gated_for_no_evidence") or []
    if not gated:
        return False

    doc.add_heading("4. Claims not supported by evidence", level=1)
    doc.add_paragraph(text["gated_lead"].format(n=len(gated)))

    by_id = {c.id: c for c in controls}
    widths = [Inches(0.9), Inches(3.4), Inches(2.0)]
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, text, w in zip(table.rows[0].cells,
                             ["Control", "Title", "Evidence sought"], widths):
        _cell_text(cell, text, bold=True)
        _shade(cell, "E8E8E8")
        cell.width = w

    for cid in sorted(gated):
        c = by_id.get(cid)
        if not c:
            continue
        title = (f"{c.title} (citation pending verification)"
                 if c.citation_status == "pending" else c.title)
        row = table.add_row().cells
        for cell, text, w in zip(row, [c.id, title, "; ".join(c.evidence_required)], widths):
            _cell_text(cell, text)
            cell.width = w
    return True


def _findings(doc: Document, controls: list, responses: dict, ai_text: dict, text: dict,
              *, number: int) -> None:
    doc.add_heading(f"{number}. Detailed observations", level=1)
    doc.add_paragraph(text["findings_intro"])

    open_controls = [
        c for c in controls
        if responses.get(c.id, {}).get("status", "Absent") in ("Absent", "Partial")
    ]
    open_controls.sort(key=lambda c: (SEVERITY_ORDER.get(c.severity_if_absent, 9), c.id))

    if not open_controls:
        doc.add_paragraph("No controls were assessed as Absent or Partial.")
        return

    for n, c in enumerate(open_controls, start=1):
        resp = responses.get(c.id, {})
        prose = ai_text.get(c.id) or {
            "observation": c.observation, "impact": c.impact, "action": c.action,
        }

        doc.add_heading(f"{number}.{n}  {c.id} - {c.title}", level=2)

        meta = doc.add_paragraph()
        ref_line = (
            f"{c.rule_ref}   |   Status: {resp.get('status', 'Absent')}   |   "
            f"Severity: {c.severity_if_absent.title()}   |   Weight: {c.weight}"
        )
        if c.citation_status == "pending":
            ref_line += f"   |   {CITATION_PENDING}"
        run = meta.add_run(ref_line)
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

        widths = [Inches(1.5), Inches(4.9)]
        table = doc.add_table(rows=0, cols=2)
        table.style = "Table Grid"

        # The assessor's note is working material and is never printed.
        mgmt = resp.get("mgmt_response") or text["response_missing"]
        owner = resp.get("mgmt_owner")
        target = resp.get("mgmt_target_date")
        if owner or target:
            mgmt += (f"\n\n{text['owner_label']}: {owner or 'Not assigned'}   |   "
                     f"Target date: {target or 'Not set'}")

        for label, body in [
            ("Observation", prose["observation"]),
            ("Impact", prose["impact"]),
            ("Further Actions", prose["action"]),
            (text["response_label"], mgmt),
        ]:
            row = table.add_row().cells
            _cell_text(row[0], label, bold=True)
            _shade(row[0], "F2F2F2")
            row[0].width = widths[0]
            _cell_text(row[1], body)
            row[1].width = widths[1]

        doc.add_paragraph()


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def build_report(project, controls: list, responses: dict, result: dict,
                 ai_text: dict | None = None, out_path: str | Path | None = None) -> Path:
    """Generate the Word gap report and return its path."""
    client = project.get_client()
    ai_text = ai_text or {}
    # result was scored by the caller and is used as given.
    text = REPORT_TEXT["client"]

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    style.paragraph_format.space_after = Pt(6)

    for section in doc.sections:
        section.left_margin = section.right_margin = Inches(0.9)

    _cover(doc, client, result, text)
    _scope(doc, controls, responses, result, text)
    _role_section(doc, client, text)
    _summary(doc, controls, responses, result)
    claims_written = _gated(doc, controls, result, text)
    # The claims section is optional; the sections after it take the next free number.
    obs = 5 if claims_written else 4
    _findings(doc, controls, responses, ai_text, text, number=obs)

    _footer(doc, text["footer"].format(name=client.name))

    out = Path(out_path) if out_path else project.output_dir / report_filename(client)
    doc.save(out)
    return out


# Characters Windows refuses in a file name, including ':' (which NTFS reads as
# an alternate data stream, hiding the document), control characters and
# whitespace. Device names such as CON or LPT1 are refused whatever follows them.
_UNSAFE_IN_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f\s]+')
_RESERVED_DEVICE = re.compile(r"^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[0-9¹²³]|LPT[0-9¹²³])(\..*)?$", re.IGNORECASE)
_NAME_MAX = 150


def safe_name_part(name: str) -> str:
    """A client name made safe to use inside a Windows file name.

    Entity names routinely carry characters Windows forbids: "M/s Sharma & Co"
    would otherwise be read as a folder, and "ABC: Unit 2" would write the report
    into an alternate data stream where nobody can find it. Every run of unsafe
    characters or whitespace becomes one underscore, so a plain name such as
    "Meridian Textiles Private Limited" keeps its familiar form. Letters in any
    script are kept.
    """
    part = _UNSAFE_IN_NAME.sub("_", name).strip("_. ")[:_NAME_MAX].rstrip("_. ")
    if not part:
        return "Report"
    if _RESERVED_DEVICE.fullmatch(part):
        part = f"_{part}"
    return part


def report_filename(client) -> str:
    """The one file name a client's report is saved under and downloaded from."""
    text = REPORT_TEXT["client"]
    return f"{text['filename_prefix']}{safe_name_part(client.name)}.docx"
