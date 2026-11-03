"""Report generation: Word audit reports, PowerPoint board packs, Excel exports."""
import os
from collections import Counter, defaultdict
from datetime import datetime

import db
import library
import services

NAVY = "1F3A5F"
ACCENT = "2E75B6"
LIGHT = "EAF1F8"
RATING_COLORS = {"Critical": "7B1E1E", "High": "C0392B", "Medium": "E67E22", "Low": "2E8B57",
                 "Satisfactory": "2E8B57", "Needs Improvement": "E6A23C",
                 "Needs Significant Improvement": "E67E22", "Unsatisfactory": "C0392B"}

RATING_DEFINITIONS = [
    ("Critical", "A fundamental control failure or fraud exposing the organisation to severe financial loss, "
                 "regulatory sanction or reputational damage. Immediate action by senior management is required."),
    ("High", "A significant weakness that could materially affect the achievement of process objectives. "
             "Action required within 30-60 days."),
    ("Medium", "A weakness that could impact process objectives if not addressed. Action required within 90 days."),
    ("Low", "Opportunity to improve efficiency or strengthen controls. Action within 180 days."),
]
OVERALL_DEFINITIONS = [
    ("Satisfactory", "Controls are adequately designed and operating effectively; only low-rated observations."),
    ("Needs Improvement", "Generally adequate controls with some medium-rated weaknesses requiring attention."),
    ("Needs Significant Improvement", "One or more high-rated weaknesses; key risks are not adequately mitigated."),
    ("Unsatisfactory", "Critical weaknesses or multiple high-rated findings; the control environment is not reliable."),
]


def _out(name):
    os.makedirs(db.EXPORT_DIR, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return os.path.join(db.EXPORT_DIR, safe)


def _fmt_date(s):
    if not s:
        return "-"
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return s


def _process_name(code):
    p = library.get_process(code)
    return p["name"] if p else (code or "-")


# =========================================================== WORD
def _docx_helpers():
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    def shade(cell, hex_color):
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tc_pr.append(shd)

    def cell_text(cell, text, bold=False, color=None, size=9, align=None):
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run("" if text is None else str(text))
        run.bold = bold
        run.font.size = Pt(size)
        if color:
            run.font.color.rgb = RGBColor.from_string(color)
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return cell

    def table(doc, headers, rows, widths=None):
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]
            cell_text(c, h, bold=True, color="FFFFFF")
            shade(c, NAVY)
        for r in rows:
            cells = t.add_row().cells
            for i, v in enumerate(r):
                cell_text(cells[i], v)
                if headers[i] in ("Rating", "Overall Rating") and v in RATING_COLORS:
                    cell_text(cells[i], v, bold=True, color="FFFFFF")
                    shade(cells[i], RATING_COLORS[v])
        if widths:
            from docx.shared import Cm
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        doc.add_paragraph()
        return t

    return shade, cell_text, table


def _new_doc(company):
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2)
        s.top_margin = s.bottom_margin = Cm(2)
        fp = s.footer.paragraphs[0]
        fp.text = f"{company['name']}  |  Internal Audit  |  Strictly Confidential"
        fp.runs[0].font.size = Pt(8)
        fp.runs[0].font.color.rgb = RGBColor.from_string("7F8C8D")
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10)
    for lvl, size in ((1, 16), (2, 13), (3, 11)):
        h = doc.styles[f"Heading {lvl}"]
        h.font.name = "Calibri"
        h.font.size = Pt(size)
        h.font.color.rgb = RGBColor.from_string(NAVY)
    return doc


def _cover(doc, company, title, subtitle_lines, rating=None):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor
    shade, cell_text, _ = _docx_helpers()
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run(company["name"].upper())
    r.bold = True
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor.from_string(ACCENT)
    p = doc.add_paragraph()
    r = p.add_run(title)
    r.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = RGBColor.from_string(NAVY)
    for line in subtitle_lines:
        p = doc.add_paragraph()
        r = p.add_run(line)
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor.from_string("34495E")
    if rating:
        doc.add_paragraph()
        t = doc.add_table(rows=1, cols=2)
        cell_text(t.rows[0].cells[0], "OVERALL RATING", bold=True, color="FFFFFF", size=11)
        shade(t.rows[0].cells[0], NAVY)
        cell_text(t.rows[0].cells[1], rating, bold=True, color="FFFFFF", size=11, align="center")
        shade(t.rows[0].cells[1], RATING_COLORS.get(rating, ACCENT))
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run("This report is confidential and intended solely for the use of management and the "
                  "Audit Committee. It should not be distributed to third parties without the prior "
                  "consent of the Head of Internal Audit.")
    r.italic = True
    r.font.size = Pt(8)
    doc.add_page_break()


def engagement_report(engagement_id):
    eng = db.one("SELECT * FROM engagements WHERE id = ?", (engagement_id,))
    company = db.one("SELECT * FROM companies WHERE id = ?", (eng["company_id"],))
    entity = db.one("SELECT * FROM entities WHERE id = ?", (eng["entity_id"],)) if eng["entity_id"] else None
    findings = db.query("SELECT * FROM findings WHERE engagement_id = ? ORDER BY "
                        "CASE rating WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, ref",
                        (engagement_id,))
    procs = db.query("SELECT * FROM procedures WHERE engagement_id = ? ORDER BY sort, id", (engagement_id,))
    rating = eng.get("overall_rating") or services.engagement_rating(findings)
    shade, cell_text, table = _docx_helpers()

    doc = _new_doc(company)
    _cover(doc, company, "Internal Audit Report", [
        eng["title"],
        f"Report Ref: {eng.get('ref') or '-'}   |   Entity: {entity['name'] if entity else company['name']}",
        f"Audit Period: {_fmt_date(eng.get('period_from'))} to {_fmt_date(eng.get('period_to'))}",
        f"Report Date: {_fmt_date(eng.get('report_date') or db.today())}",
    ], rating)

    doc.add_heading("Distribution", 1)
    table(doc, ["Role", "Name"], [
        ["Audit Committee Chair", company.get("audit_committee_chair") or "-"],
        ["Head of Internal Audit", company.get("head_of_audit") or "-"],
        ["Auditee / Process Owner", eng.get("auditee_contact") or "-"],
        ["Engagement Lead", eng.get("lead_auditor") or "-"],
        ["Reviewer", eng.get("reviewer") or "-"],
    ], [6, 10])

    counts = Counter(f["rating"] for f in findings)
    doc.add_heading("1. Executive Summary", 1)
    summary = eng.get("executive_summary") or (
        f"Internal Audit performed a review of {eng['title']} for "
        f"{entity['name'] if entity else company['name']} covering the period "
        f"{_fmt_date(eng.get('period_from'))} to {_fmt_date(eng.get('period_to'))}. "
        f"We tested {len(procs)} controls, of which "
        f"{sum(1 for p in procs if p['oe_result'] == 'Effective')} were operating effectively and "
        f"{sum(1 for p in procs if p['oe_result'] in ('Ineffective', 'Partially Effective'))} were found "
        f"ineffective or partially effective. A total of {len(findings)} observations were raised. "
        f"Based on the work performed, the overall control environment is rated '{rating}'.")
    doc.add_paragraph(summary)
    table(doc, ["Critical", "High", "Medium", "Low", "Total"],
          [[counts.get("Critical", 0), counts.get("High", 0), counts.get("Medium", 0),
            counts.get("Low", 0), len(findings)]])

    doc.add_heading("2. Background, Objectives and Scope", 1)
    doc.add_heading("Objectives", 2)
    doc.add_paragraph(eng.get("objective") or "-")
    doc.add_heading("Scope", 2)
    doc.add_paragraph(eng.get("scope") or "-")
    codes = services.load_json(eng.get("process_codes"))
    if codes:
        doc.add_paragraph("Processes covered:")
        for c in codes:
            doc.add_paragraph(_process_name(c), style="List Bullet")
    if eng.get("out_of_scope"):
        doc.add_heading("Out of Scope", 2)
        doc.add_paragraph(eng["out_of_scope"])
    doc.add_heading("Approach", 2)
    doc.add_paragraph(eng.get("methodology") or (
        "The audit was conducted in conformance with the IIA Global Internal Audit Standards. Our approach "
        "included walkthroughs to understand processes and evaluate control design, tests of operating "
        "effectiveness on a sample basis, data analytics on full transaction populations where possible, "
        "and discussions with process owners."))

    doc.add_heading("3. Summary of Findings", 1)
    if findings:
        table(doc, ["Ref", "Finding", "Rating", "Owner", "Target Date", "Status"],
              [[f["ref"], f["title"], f["rating"], f.get("owner") or "-",
                _fmt_date(f.get("revised_due_date") or f.get("due_date")), f["status"]] for f in findings],
              [1.6, 7, 2, 2.6, 2.3, 2])
    else:
        doc.add_paragraph("No reportable findings were identified.")

    doc.add_heading("4. Detailed Findings", 1)
    for f in findings:
        doc.add_heading(f"{f['ref']}  {f['title']}", 2)
        t = doc.add_table(rows=0, cols=2)
        t.style = "Table Grid"
        rows = [("Risk Rating", f["rating"]), ("Process", _process_name(f.get("process_code"))),
                ("Condition (What we found)", f.get("condition")), ("Criteria (What should be)", f.get("criteria")),
                ("Root Cause", f.get("cause")), ("Effect / Risk", f.get("effect")),
                ("Recommendation", f.get("recommendation")),
                ("Management Response", f.get("mgmt_response")), ("Agreed Action Plan", f.get("action_plan")),
                ("Action Owner", f.get("owner")),
                ("Target Date", _fmt_date(f.get("revised_due_date") or f.get("due_date")))]
        if f.get("financial_impact"):
            rows.insert(2, ("Financial Impact", f"{company.get('base_currency') or ''} {f['financial_impact']:,.2f}"))
        for label, val in rows:
            cells = t.add_row().cells
            cell_text(cells[0], label, bold=True)
            shade(cells[0], LIGHT)
            if label == "Risk Rating":
                cell_text(cells[1], val, bold=True, color="FFFFFF")
                shade(cells[1], RATING_COLORS.get(val, ACCENT))
            else:
                cell_text(cells[1], val or "-")
        from docx.shared import Cm
        for row in t.rows:
            row.cells[0].width = Cm(4.5)
            row.cells[1].width = Cm(12.5)
        doc.add_paragraph()

    doc.add_heading("5. Summary of Work Performed", 1)
    by_proc = defaultdict(lambda: Counter())
    for p in procs:
        by_proc[p["process_code"]]["total"] += 1
        by_proc[p["process_code"]][p["oe_result"] or "Not Tested"] += 1
    table(doc, ["Process", "Controls", "Effective", "Partially Effective", "Ineffective", "Not Tested / N/A"],
          [[_process_name(c), v["total"], v["Effective"], v["Partially Effective"], v["Ineffective"],
            v["Not Tested"] + v["Not Applicable"]] for c, v in by_proc.items()])

    doc.add_page_break()
    doc.add_heading("Appendix A - Rating Definitions", 1)
    table(doc, ["Rating", "Definition"], RATING_DEFINITIONS, [3, 14])
    table(doc, ["Overall Rating", "Definition"], OVERALL_DEFINITIONS, [4.5, 12.5])
    doc.add_heading("Appendix B - Controls Tested", 1)
    table(doc, ["Control ID", "Control", "Design", "Operating", "WP Ref"],
          [[p["control_id"], p["control"], p["design_result"], p["oe_result"], p.get("wp_ref") or "-"]
           for p in procs], [2.2, 9.3, 2, 2, 1.5])

    path = _out(f"Audit_Report_{eng.get('ref') or eng['id']}.docx")
    doc.save(path)
    return path


def plan_document(company_id, plan_id):
    company = db.one("SELECT * FROM companies WHERE id = ?", (company_id,))
    plan = db.one("SELECT * FROM plans WHERE id = ?", (plan_id,))
    engs = db.query("SELECT e.*, en.name AS entity_name FROM engagements e LEFT JOIN entities en ON en.id = e.entity_id "
                    "WHERE e.plan_id = ? ORDER BY e.quarter, e.ref", (plan_id,))
    uni = db.query("SELECT u.*, en.name AS entity_name FROM universe u LEFT JOIN entities en ON en.id = u.entity_id "
                   "WHERE u.company_id = ? ORDER BY u.risk_score DESC", (company_id,))
    _, _, table = _docx_helpers()
    doc = _new_doc(company)
    _cover(doc, company, "Risk-Based Internal Audit Plan", [
        plan.get("title") or f"Annual Audit Plan {plan.get('year')}",
        f"Status: {plan.get('status')}   |   Approved by: {plan.get('approved_by') or 'Pending'}",
        f"Prepared: {_fmt_date(db.today())}"])
    doc.add_heading("1. Introduction", 1)
    doc.add_paragraph(
        "This plan has been developed using a risk-based approach in line with the IIA Global Internal Audit "
        "Standards. The audit universe was assessed on financial significance, fraud risk, regulatory exposure, "
        "process complexity, degree of change and the strength of the control environment. Higher-risk "
        "auditable units are prioritised for coverage during the year.")
    budget = sum(e.get("budget_hours") or 0 for e in engs)
    doc.add_heading("2. Plan Summary", 1)
    table(doc, ["Metric", "Value"], [
        ["Planned engagements", len(engs)], ["Budgeted hours", f"{budget:,.0f}"],
        ["Available hours", f"{plan.get('available_hours') or 0:,.0f}"],
        ["Auditable units in universe", len(uni)],
        ["High-risk units", sum(1 for u in uni if u["risk_level"] == "High")]], [8, 8])
    doc.add_heading("3. Planned Engagements", 1)
    table(doc, ["Ref", "Engagement", "Entity", "Quarter", "Type", "Hours"],
          [[e.get("ref"), e["title"], e.get("entity_name") or "-", e.get("quarter") or "-",
            e.get("audit_type"), f"{e.get('budget_hours') or 0:,.0f}"] for e in engs],
          [1.8, 6.5, 3.5, 1.7, 2, 1.5])
    doc.add_heading("4. Audit Universe & Risk Assessment (Top 40)", 1)
    table(doc, ["Process", "Entity", "Score", "Level", "Frequency"],
          [[u["process_name"], u.get("entity_name") or "-", u["risk_score"], u["risk_level"],
            u.get("audit_frequency") or "-"] for u in uni[:40]], [6.5, 4, 1.6, 1.8, 3])
    if plan.get("notes"):
        doc.add_heading("5. Notes", 1)
        doc.add_paragraph(plan["notes"])
    path = _out(f"Audit_Plan_{plan.get('year')}_{company['short_code'] or company['id']}.docx")
    doc.save(path)
    return path


# =========================================================== POWERPOINT
def board_presentation(company_id, year=None):
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    company = db.one("SELECT * FROM companies WHERE id = ?", (company_id,))
    engs = db.query("SELECT e.*, en.name AS entity_name FROM engagements e LEFT JOIN entities en ON en.id = e.entity_id "
                    "WHERE e.company_id = ? ORDER BY e.planned_start, e.ref", (company_id,))
    if year:
        plan_ids = {p["id"] for p in db.query("SELECT id FROM plans WHERE company_id = ? AND year = ?",
                                              (company_id, year))}
        engs = [e for e in engs if e["plan_id"] in plan_ids or (e.get("planned_start") or "").startswith(str(year))]
    eng_ids = {e["id"] for e in engs}
    findings = db.query("SELECT f.*, en.name AS entity_name, e.title AS eng_title FROM findings f "
                        "LEFT JOIN entities en ON en.id = f.entity_id LEFT JOIN engagements e ON e.id = f.engagement_id "
                        "WHERE f.company_id = ?", (company_id,))
    period_findings = [f for f in findings if not year or f["engagement_id"] in eng_ids]
    uni = db.query("SELECT * FROM universe WHERE company_id = ?", (company_id,))
    hours = {r["engagement_id"]: r["h"] for r in db.query(
        "SELECT engagement_id, SUM(hours) AS h FROM time_entries GROUP BY engagement_id")}

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    navy, accent = RGBColor.from_string(NAVY), RGBColor.from_string(ACCENT)

    def rect(slide, x, y, w, h, color, text=None, size=12, bold=False, font_color="FFFFFF", align=PP_ALIGN.LEFT):
        s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
        s.fill.solid()
        s.fill.fore_color.rgb = RGBColor.from_string(color) if isinstance(color, str) else color
        s.line.fill.background()
        if text is not None:
            tf = s.text_frame
            tf.word_wrap = True
            tf.text = str(text)
            for p in tf.paragraphs:
                p.alignment = align
                for r in p.runs:
                    r.font.size = Pt(size)
                    r.font.bold = bold
                    r.font.color.rgb = RGBColor.from_string(font_color)
        return s

    def text(slide, x, y, w, h, content, size=14, bold=False, color="2C3E50", bullets=False):
        tb = slide.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame
        tf.word_wrap = True
        lines = content if isinstance(content, list) else [content]
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = ("•  " if bullets else "") + str(line)
            p.space_after = Pt(8)
            for r in p.runs:
                r.font.size = Pt(size)
                r.font.bold = bold
                r.font.color.rgb = RGBColor.from_string(color)
        return tb

    def new_slide(title, subtitle=None):
        s = prs.slides.add_slide(blank)
        rect(s, 0, 0, prs.slide_width, Inches(0.95), navy)
        text(s, Inches(0.5), Inches(0.18), Inches(11), Inches(0.6), title, 26, True, "FFFFFF")
        rect(s, 0, Inches(0.95), prs.slide_width, Inches(0.06), accent)
        if subtitle:
            text(s, Inches(0.5), Inches(1.1), Inches(12), Inches(0.4), subtitle, 12, False, "7F8C8D")
        footer = f"{company['name']}  |  Internal Audit  |  Confidential"
        text(s, Inches(0.5), Inches(7.05), Inches(9), Inches(0.3), footer, 9, False, "95A5A6")
        text(s, Inches(12.2), Inches(7.05), Inches(1), Inches(0.3), str(len(prs.slides)), 9, False, "95A5A6")
        return s

    def table(slide, headers, rows, x, y, w, col_w=None, font=10):
        rows = rows or [["No items"] + [""] * (len(headers) - 1)]
        shape = slide.shapes.add_table(len(rows) + 1, len(headers), x, y, w, Inches(0.3) * (len(rows) + 1))
        t = shape.table
        for i, h in enumerate(headers):
            c = t.cell(0, i)
            c.text = h
            c.fill.solid()
            c.fill.fore_color.rgb = navy
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(font)
                    r.font.bold = True
                    r.font.color.rgb = RGBColor.from_string("FFFFFF")
        for ri, row in enumerate(rows, start=1):
            for ci, v in enumerate(row):
                c = t.cell(ri, ci)
                c.text = "" if v is None else str(v)
                c.fill.solid()
                color = RATING_COLORS.get(str(v)) if headers[ci] in ("Rating", "Overall Rating") else None
                c.fill.fore_color.rgb = RGBColor.from_string(color or ("F4F7FB" if ri % 2 else "FFFFFF"))
                for p in c.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(font - 1)
                        r.font.color.rgb = RGBColor.from_string("FFFFFF" if color else "2C3E50")
                        r.font.bold = bool(color)
        if col_w:
            for i, cw in enumerate(col_w):
                t.columns[i].width = Inches(cw)
        return t

    def chart(slide, kind, categories, series, x, y, w, h, colors=None, legend=True, labels=True):
        if not categories or not any(any(v for v in vals) for _, vals in series):
            rect(slide, x, y, w, h, "F4F7FB", "No data available", 12, False, "7F8C8D", PP_ALIGN.CENTER)
            return None
        cd = CategoryChartData()
        cd.categories = categories
        for name, vals in series:
            cd.add_series(name, vals)
        ch = slide.shapes.add_chart(kind, x, y, w, h, cd).chart
        ch.has_legend = legend
        if legend:
            ch.legend.position = XL_LEGEND_POSITION.BOTTOM
            ch.legend.include_in_layout = False
            ch.legend.font.size = Pt(10)
        if labels:
            plot = ch.plots[0]
            plot.has_data_labels = True
            plot.data_labels.font.size = Pt(10)
        if colors:
            if kind in (XL_CHART_TYPE.PIE, XL_CHART_TYPE.DOUGHNUT):
                for i, pt in enumerate(ch.plots[0].series[0].points):
                    pt.format.fill.solid()
                    pt.format.fill.fore_color.rgb = RGBColor.from_string(colors[i % len(colors)])
            else:
                for i, s in enumerate(ch.plots[0].series):
                    s.format.fill.solid()
                    s.format.fill.fore_color.rgb = RGBColor.from_string(colors[i % len(colors)])
        return ch

    # metrics
    status_c = Counter(e["status"] for e in engs)
    completed = status_c.get("Closed", 0) + status_c.get("Reporting", 0)
    completion = round(completed / len(engs) * 100) if engs else 0
    open_f = [f for f in findings if f["status"] not in services.CLOSED_STATUSES]
    overdue = [f for f in open_f if services.is_overdue(f)]
    hi_open = [f for f in open_f if f["rating"] in ("Critical", "High")]
    rating_c = Counter(f["rating"] for f in period_findings)
    label = f"FY {year}" if year else "All periods"

    # 1. title
    s = prs.slides.add_slide(blank)
    rect(s, 0, 0, prs.slide_width, prs.slide_height, navy)
    rect(s, 0, Inches(4.9), prs.slide_width, Inches(0.08), accent)
    text(s, Inches(0.8), Inches(1.8), Inches(11.5), Inches(0.6), company["name"].upper(), 18, True, "9DC3E6")
    text(s, Inches(0.8), Inches(2.4), Inches(11.5), Inches(1.4), "Internal Audit Update to the Board / Audit Committee", 36, True, "FFFFFF")
    text(s, Inches(0.8), Inches(3.9), Inches(11.5), Inches(0.5), f"{label}   |   {datetime.now().strftime('%d %B %Y')}", 16, False, "D6E4F0")
    text(s, Inches(0.8), Inches(5.2), Inches(11.5), Inches(0.5),
         f"Presented by: {company.get('head_of_audit') or 'Head of Internal Audit'}", 14, False, "D6E4F0")

    # 2. agenda
    s = new_slide("Agenda")
    text(s, Inches(0.8), Inches(1.5), Inches(11), Inches(5), [
        "Executive summary & key messages", "Audit plan progress", "Summary of audit findings",
        "Significant (Critical / High) findings", "Management action tracking & overdue actions",
        "Risk heat map - audit universe", "Resource utilisation", "Matters for the Committee's attention"],
        20, False, "2C3E50", bullets=True)

    # 3. executive summary
    s = new_slide("Executive Summary", label)
    tiles = [("Plan completion", f"{completion}%", ACCENT), ("Engagements", f"{len(engs)}", NAVY),
             ("Findings raised", f"{len(period_findings)}", "5D6D7E"),
             ("Open Critical/High", f"{len(hi_open)}", "C0392B"), ("Overdue actions", f"{len(overdue)}", "E67E22")]
    for i, (lbl, val, col) in enumerate(tiles):
        x = Inches(0.5 + i * 2.5)
        rect(s, x, Inches(1.6), Inches(2.3), Inches(1.5), col)
        text(s, x + Inches(0.15), Inches(1.7), Inches(2), Inches(0.8), val, 34, True, "FFFFFF")
        text(s, x + Inches(0.15), Inches(2.55), Inches(2.1), Inches(0.4), lbl, 12, False, "FFFFFF")
    msgs = [f"{completed} of {len(engs)} planned engagements are at reporting stage or closed ({completion}% completion)."]
    if rating_c:
        msgs.append(f"{len(period_findings)} findings raised: " + ", ".join(
            f"{rating_c.get(r, 0)} {r}" for r in services.FINDING_RATINGS) + ".")
    msgs.append(f"{len(open_f)} management actions remain open, of which {len(overdue)} are past their agreed date.")
    unsat = [e for e in engs if e.get("overall_rating") in ("Unsatisfactory", "Needs Significant Improvement")]
    if unsat:
        msgs.append("Engagements rated below expectation: " + "; ".join(e["title"] for e in unsat[:4]) + ".")
    hi_uni = sum(1 for u in uni if u["risk_level"] == "High")
    msgs.append(f"Audit universe: {len(uni)} auditable units, {hi_uni} assessed as high inherent risk.")
    text(s, Inches(0.6), Inches(3.5), Inches(12.2), Inches(3.4), msgs, 16, False, "2C3E50", bullets=True)

    # 4. plan progress
    s = new_slide("Audit Plan Progress", label)
    order = ["Planned", "Planning", "Fieldwork", "Reporting", "Closed", "Cancelled"]
    cats = [o for o in order if status_c.get(o)]
    st_colors = {"Planned": "BDC3C7", "Planning": "85C1E9", "Fieldwork": ACCENT, "Reporting": "F5B041",
                 "Closed": "27AE60", "Cancelled": "7F8C8D"}
    chart(s, XL_CHART_TYPE.DOUGHNUT, cats, [("Engagements", [status_c[c] for c in cats])],
          Inches(0.4), Inches(1.5), Inches(4.4), Inches(5.2), colors=[st_colors[c] for c in cats])
    table(s, ["Ref", "Engagement", "Entity", "Qtr", "Status", "Overall Rating"],
          [[e.get("ref"), e["title"][:45], (e.get("entity_name") or "-")[:22], e.get("quarter") or "-",
            e["status"], e.get("overall_rating") or "-"] for e in engs[:14]],
          Inches(5.0), Inches(1.5), Inches(8), [0.8, 2.9, 1.6, 0.5, 0.9, 1.3], 10)

    # 5. findings overview
    s = new_slide("Summary of Audit Findings", label)
    chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, services.FINDING_RATINGS,
          [("Findings", [rating_c.get(r, 0) for r in services.FINDING_RATINGS])],
          Inches(0.4), Inches(1.5), Inches(6), Inches(5.2), colors=[ACCENT], legend=False)
    proc_c = Counter(_process_name(f.get("process_code")) for f in period_findings).most_common(8)
    chart(s, XL_CHART_TYPE.BAR_CLUSTERED, [p[0][:35] for p in proc_c][::-1],
          [("Findings", [p[1] for p in proc_c][::-1])],
          Inches(6.7), Inches(1.5), Inches(6.3), Inches(5.2), colors=[NAVY], legend=False)

    # 6. significant findings
    s = new_slide("Significant Findings (Critical & High)", "Open and recently raised")
    sig = sorted([f for f in period_findings if f["rating"] in ("Critical", "High")],
                 key=lambda f: (f["rating"] != "Critical", f.get("due_date") or ""))
    table(s, ["Ref", "Finding", "Entity", "Rating", "Owner", "Due", "Status"],
          [[f["ref"], f["title"][:60], (f.get("entity_name") or "-")[:20], f["rating"], (f.get("owner") or "-")[:18],
            _fmt_date(f.get("revised_due_date") or f.get("due_date")), f["status"]] for f in sig[:10]],
          Inches(0.4), Inches(1.5), Inches(12.5), [0.9, 4.6, 1.8, 1.0, 1.6, 1.3, 1.3], 11)

    # 7. action tracking
    s = new_slide("Management Action Tracking")
    st_c = Counter("Overdue" if services.is_overdue(f) else f["status"] for f in findings)
    cats = [c for c in ["Open", "In Progress", "Overdue", "Implemented", "Closed", "Risk Accepted"] if st_c.get(c)]
    act_colors = {"Open": "85C1E9", "In Progress": ACCENT, "Overdue": "C0392B", "Implemented": "27AE60",
                  "Closed": "1E8449", "Risk Accepted": "95A5A6"}
    chart(s, XL_CHART_TYPE.PIE, cats, [("Actions", [st_c[c] for c in cats])],
          Inches(0.4), Inches(1.5), Inches(5.6), Inches(5.2), colors=[act_colors[c] for c in cats])
    buckets = ["Not yet due", "0-30 days", "31-90 days", "91-180 days", ">180 days"]
    age = Counter()
    today = datetime.now().date()
    for f in open_f:
        due = f.get("revised_due_date") or f.get("due_date")
        if not due or due >= db.today():
            age["Not yet due"] += 1
            continue
        d = (today - datetime.strptime(due[:10], "%Y-%m-%d").date()).days
        age["0-30 days" if d <= 30 else "31-90 days" if d <= 90 else "91-180 days" if d <= 180 else ">180 days"] += 1
    chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, buckets, [("Open actions by days overdue", [age[b] for b in buckets])],
          Inches(6.3), Inches(1.5), Inches(6.7), Inches(5.2), colors=["E67E22"], legend=False)

    # 8. overdue actions
    s = new_slide("Overdue Management Actions", f"{len(overdue)} actions past agreed implementation date")
    table(s, ["Ref", "Finding", "Rating", "Owner", "Original Due", "Revised Due", "Status"],
          [[f["ref"], f["title"][:60], f["rating"], (f.get("owner") or "-")[:18], _fmt_date(f.get("due_date")),
            _fmt_date(f.get("revised_due_date")), f["status"]] for f in sorted(overdue, key=lambda f: f.get("due_date") or "")[:12]],
          Inches(0.4), Inches(1.5), Inches(12.5), [0.9, 5.0, 1.0, 1.7, 1.3, 1.3, 1.3], 11)

    # 9. heat map
    s = new_slide("Risk Heat Map - Audit Universe", "Number of auditable units by inherent impact and likelihood")
    grid = Counter((u["impact"], u["likelihood"]) for u in uni)
    cell = Inches(1.05)
    ox, oy = Inches(2.2), Inches(1.6)
    for imp in range(5, 0, -1):
        for lik in range(1, 6):
            score = imp * lik
            col = "C0392B" if score >= 15 else "E67E22" if score >= 8 else "F4D03F" if score >= 4 else "58D68D"
            rect(s, ox + cell * (lik - 1), oy + cell * (5 - imp), cell - Inches(0.04), cell - Inches(0.04), col,
                 grid.get((imp, lik), "") or "", 18, True, "FFFFFF", PP_ALIGN.CENTER)
        text(s, ox - Inches(0.45), oy + cell * (5 - imp) + Inches(0.35), Inches(0.4), Inches(0.4), str(imp), 12, True)
    for lik in range(1, 6):
        text(s, ox + cell * (lik - 1) + Inches(0.42), oy + cell * 5 + Inches(0.02), Inches(0.4), Inches(0.4), str(lik), 12, True)
    text(s, ox, oy + cell * 5 + Inches(0.35), cell * 5, Inches(0.4), "Likelihood →", 12, True, "7F8C8D")
    text(s, Inches(0.4), oy + Inches(2.2), Inches(1.4), Inches(0.5), "Impact ↑", 12, True, "7F8C8D")
    top = sorted(uni, key=lambda u: -u["risk_score"])[:10]
    ents = {e["id"]: e["name"] for e in db.query("SELECT id, name FROM entities WHERE company_id = ?", (company_id,))}
    table(s, ["Top risks", "Entity", "Score"],
          [[u["process_name"][:38], ents.get(u["entity_id"], "-")[:18], u["risk_score"]] for u in top],
          Inches(7.9), Inches(1.6), Inches(5.1), [2.9, 1.5, 0.7], 10)

    # 10. resources
    s = new_slide("Resource Utilisation", "Budgeted vs actual hours by engagement")
    act = [e for e in engs if e.get("budget_hours") or hours.get(e["id"])][:12]
    chart(s, XL_CHART_TYPE.BAR_CLUSTERED, [(e.get("ref") or e["title"])[:25] for e in act][::-1],
          [("Budget", [e.get("budget_hours") or 0 for e in act][::-1]),
           ("Actual", [round(hours.get(e["id"], 0) or 0, 1) for e in act][::-1])],
          Inches(0.6), Inches(1.5), Inches(12.2), Inches(5.3), colors=["AEB6BF", ACCENT])

    # 11. matters for attention
    s = new_slide("Matters for the Committee's Attention")
    asks = []
    if hi_open:
        asks.append(f"Note {len(hi_open)} open Critical/High findings and the agreed remediation timelines.")
    if overdue:
        asks.append(f"Direct management to address {len(overdue)} overdue actions; consider inviting owners of the oldest items.")
    pending = [e for e in engs if e["status"] in ("Planned", "Planning")]
    if pending:
        asks.append(f"{len(pending)} engagements are yet to start fieldwork - confirm priorities and resourcing.")
    asks.append("Approve any changes to the risk-based audit plan arising from emerging risks.")
    asks.append("Confirm Internal Audit's independence and that no scope limitations were encountered.")
    text(s, Inches(0.8), Inches(1.5), Inches(11.8), Inches(5), asks, 18, False, "2C3E50", bullets=True)

    path = _out(f"Board_Presentation_{company['short_code'] or company['id']}_{year or 'all'}.pptx")
    prs.save(path)
    return path


# =========================================================== EXCEL
def _sheet(ws, headers, rows, widths=None):
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    thin = Side(style="thin", color="D5DBDB")
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for r in rows:
        ws.append(["" if v is None else v for v in r])
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.border = Border(top=thin, bottom=thin, left=thin, right=thin)
            if headers[c.column - 1] in ("Rating", "Risk Rating", "Risk Level") and c.value in RATING_COLORS:
                c.fill = PatternFill("solid", fgColor=RATING_COLORS[c.value])
                c.font = Font(color="FFFFFF", bold=True)
    for i, w in enumerate(widths or [], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def findings_excel(company_id):
    from openpyxl import Workbook
    company = db.one("SELECT * FROM companies WHERE id = ?", (company_id,))
    rows = db.query("SELECT f.*, e.ref AS eng_ref, e.title AS eng_title, en.name AS entity_name FROM findings f "
                    "LEFT JOIN engagements e ON e.id = f.engagement_id LEFT JOIN entities en ON en.id = f.entity_id "
                    "WHERE f.company_id = ? ORDER BY f.ref", (company_id,))
    wb = Workbook()
    ws = wb.active
    ws.title = "Findings Tracker"
    _sheet(ws, ["Ref", "Engagement", "Entity", "Process", "Title", "Rating", "Condition", "Criteria", "Cause",
                "Effect", "Recommendation", "Management Response", "Action Plan", "Owner", "Due Date",
                "Revised Due", "Status", "Overdue", "Repeat", "Financial Impact"],
           [[f["ref"], f"{f.get('eng_ref') or ''} {f.get('eng_title') or ''}".strip(), f.get("entity_name"),
             _process_name(f.get("process_code")), f["title"], f["rating"], f.get("condition"), f.get("criteria"),
             f.get("cause"), f.get("effect"), f.get("recommendation"), f.get("mgmt_response"), f.get("action_plan"),
             f.get("owner"), f.get("due_date"), f.get("revised_due_date"), f["status"],
             "Yes" if services.is_overdue(f) else "No", "Yes" if f.get("repeat_finding") else "No",
             f.get("financial_impact")] for f in rows],
           [9, 28, 18, 24, 34, 10, 40, 30, 30, 30, 40, 36, 36, 16, 12, 12, 13, 9, 8, 14])
    fu = wb.create_sheet("Follow-up History")
    hist = db.query("SELECT fu.*, f.ref FROM followups fu JOIN findings f ON f.id = fu.finding_id "
                    "WHERE f.company_id = ? ORDER BY f.ref, fu.update_date", (company_id,))
    _sheet(fu, ["Finding Ref", "Date", "Update", "Status", "Updated By"],
           [[h["ref"], h["update_date"], h["update_text"], h["status"], h["updated_by"]] for h in hist],
           [12, 12, 70, 14, 18])
    path = _out(f"Findings_Tracker_{company['short_code'] or company['id']}.xlsx")
    wb.save(path)
    return path


def racm_excel(engagement_id):
    from openpyxl import Workbook
    eng = db.one("SELECT * FROM engagements WHERE id = ?", (engagement_id,))
    procs = db.query("SELECT * FROM procedures WHERE engagement_id = ? ORDER BY sort, id", (engagement_id,))
    wb = Workbook()
    ws = wb.active
    ws.title = "RACM & Work Program"
    _sheet(ws, ["Process", "Sub-process", "Risk ID", "Risk", "Risk Rating", "Assertion", "Control ID", "Control",
                "Type", "Nature", "Frequency", "Key", "Fraud", "Test Procedures", "Population", "Sample Size",
                "Design", "Operating", "Testing Notes", "Conclusion", "WP Ref", "Status", "Prepared By",
                "Prepared On", "Reviewed By", "Reviewed On"],
           [[_process_name(p["process_code"]), p["subprocess"], p["risk_id"], p["risk"], p["risk_rating"],
             p["assertion"], p["control_id"], p["control"], p["control_type"], p["control_nature"], p["frequency"],
             "Yes" if p["key_control"] else "No", "Yes" if p["fraud_risk"] else "No", p["steps"], p["population"],
             p["sample_size"], p["design_result"], p["oe_result"], p["testing_notes"], p["conclusion"], p["wp_ref"],
             p["status"], p["prepared_by"], p["prepared_on"], p["reviewed_by"], p["reviewed_on"]] for p in procs],
           [22, 20, 13, 40, 10, 14, 13, 40, 11, 13, 12, 6, 6, 60, 10, 9, 12, 12, 40, 30, 9, 12, 14, 12, 14, 12])
    pbc = wb.create_sheet("PBC List")
    items = db.query("SELECT * FROM pbc WHERE engagement_id = ? ORDER BY id", (engagement_id,))
    _sheet(pbc, ["#", "Process", "Item Requested", "Requested From", "Requested On", "Due On", "Status",
                 "Received On", "Remarks"],
           [[i + 1, _process_name(x["process_code"]), x["item"], x["requested_from"], x["requested_on"],
             x["due_on"], x["status"], x["received_on"], x["remarks"]] for i, x in enumerate(items)],
           [5, 24, 60, 18, 12, 12, 16, 12, 30])
    path = _out(f"RACM_{eng.get('ref') or eng['id']}.xlsx")
    wb.save(path)
    return path


def universe_excel(company_id):
    from openpyxl import Workbook
    company = db.one("SELECT * FROM companies WHERE id = ?", (company_id,))
    uni = db.query("SELECT u.*, en.name AS entity_name FROM universe u LEFT JOIN entities en ON en.id = u.entity_id "
                   "WHERE u.company_id = ? ORDER BY u.risk_score DESC", (company_id,))
    wb = Workbook()
    ws = wb.active
    ws.title = "Audit Universe"
    _sheet(ws, ["Entity", "Process", "Industry", "Owner", "Financial", "Fraud", "Regulatory", "Complexity",
                "Change", "Control Env.", "Impact", "Likelihood", "Score", "Risk Level", "Frequency",
                "Last Audit", "Last Rating", "Notes"],
           [[u.get("entity_name"), u["process_name"], u["industry"], u.get("process_owner"), u["f_financial"],
             u["f_fraud"], u["f_regulatory"], u["f_complexity"], u["f_change"], u["f_control_env"], u["impact"],
             u["likelihood"], u["risk_score"], u["risk_level"], u.get("audit_frequency"), u.get("last_audit_date"),
             u.get("last_rating"), u.get("notes")] for u in uni],
           [22, 36, 20, 16, 9, 8, 10, 10, 8, 11, 8, 10, 8, 10, 14, 12, 14, 30])
    ws2 = wb.create_sheet("Engagements")
    engs = db.query("SELECT e.*, en.name AS entity_name, p.year FROM engagements e "
                    "LEFT JOIN entities en ON en.id = e.entity_id LEFT JOIN plans p ON p.id = e.plan_id "
                    "WHERE e.company_id = ? ORDER BY p.year, e.quarter", (company_id,))
    _sheet(ws2, ["Plan Year", "Ref", "Title", "Entity", "Type", "Quarter", "Status", "Lead", "Planned Start",
                 "Planned End", "Budget Hrs", "Overall Rating"],
           [[e.get("year"), e.get("ref"), e["title"], e.get("entity_name"), e.get("audit_type"), e.get("quarter"),
             e["status"], e.get("lead_auditor"), e.get("planned_start"), e.get("planned_end"), e.get("budget_hours"),
             e.get("overall_rating")] for e in engs],
           [10, 10, 36, 20, 12, 9, 12, 16, 12, 12, 10, 24])
    path = _out(f"Audit_Universe_{company['short_code'] or company['id']}.xlsx")
    wb.save(path)
    return path


def analytics_excel(run):
    from openpyxl import Workbook
    import json
    res = json.loads(run["result"])
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    _sheet(ws, ["Metric", "Value"], [["Test", run["test"]], ["File", run["file_name"]], ["Run on", run["run_on"]]] +
           [[k.replace("_", " ").title(), v] for k, v in res.get("summary", {}).items()], [30, 40])
    if res.get("table"):
        t = wb.create_sheet("Distribution")
        keys = list(res["table"][0].keys())
        _sheet(t, [k.replace("_", " ").title() for k in keys], [[r.get(k) for k in keys] for r in res["table"]])
    ex = wb.create_sheet("Exceptions")
    cols = res.get("columns") or []
    _sheet(ex, [("Reason" if c == "_reason" else c) for c in cols],
           [[r.get(c) for c in cols] for r in res.get("exceptions", [])])
    path = _out(f"Analytics_{run['test']}_{run['id']}.xlsx")
    wb.save(path)
    return path
