

# ===========================================================================
# SECTION 5C - REPORTS
# ---------------------------------------------------------------------------
# Each report is built once as a plain table (title, columns, rows, totals)
# and then rendered three ways: on screen, into a formatted workbook, and
# into a PDF.  Building the data once is what keeps the three in agreement.
#
# Column spec: (heading, key, kind) where kind is
#   "text" | "money" | "number" | "date" | "pct" | "status"
#   "link"   - text on paper; on screen a link that opens the related record
#   "action" - on screen only (a Review link); left out of the exports
# ===========================================================================

REPORT_REGISTER = "register"
REPORT_RECEIVED = "received"
REPORT_PENDING = "pending"
REPORT_COMPARISON = "comparison"
REPORT_VARIANCE = "variance"
REPORT_EXCEPTIONS = "exceptions"
REPORT_AUDIT = "audit"

REPORT_TITLES = [
    (REPORT_REGISTER, "Confirmation register",
     "Every party the request was sent to"),
    (REPORT_RECEIVED, "Confirmations received",
     "Replies matched, with the amount confirmed"),
    (REPORT_PENDING, "Pending confirmations",
     "Sent but not yet answered, with ageing"),
    (REPORT_COMPARISON, "Requested vs confirmed",
     "Our books beside the party's reply"),
    (REPORT_VARIANCE, "Consolidated variance report",
     "Differences by category, with coverage"),
    (REPORT_EXCEPTIONS, "Exception queue",
     "Nothing here is counted until you decide it - click Review on a "
     "reply"),
    (REPORT_AUDIT, "Audit status",
     "Follow-up on every mismatch and every reply under review"),
]


def _pct(value):
    return None if value is None else round(value, 2)


def build_report(kind, rows, exceptions, context=None):
    """Return {key, title, subtitle, columns, rows, totals, note}."""
    context = context or {}
    title = dict((k, (t, s)) for k, t, s in REPORT_TITLES)[kind]

    if kind == REPORT_REGISTER:
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Currency", "currency", "text"),
                   ("Amount as per books", "books_amount", "money"),
                   ("Email", "email", "text"),
                   ("Reference", "reference", "text"),
                   ("Date sent", "sent_at", "date"),
                   ("Delivery", "delivery", "text"),
                   ("Reply from", "reply_from", "text"),
                   ("Reply received", "received_at", "date"),
                   ("Matched on", "match_basis", "text"),
                   ("Amount confirmed", "confirmed_amount", "money"),
                   ("Outcome", "status", "status"),
                   ("Audit status", "audit_state", "link")]
        data = list(rows)
        totals = {"books_amount": sum(abs(r["books_amount"]) for r in data
                                      if r["books_amount"] is not None)}

    elif kind == REPORT_RECEIVED:
        data = [r for r in rows if r["status"] in (STATUS_AGREED,
                                                   STATUS_VARIANCE)]
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Date received", "received_at", "date"),
                   ("Reply from", "reply_from", "text"),
                   ("Amount confirmed", "confirmed_amount", "money"),
                   ("Matched on", "match_basis", "text"),
                   ("Match confidence", "match_confidence", "pct_unit"),
                   ("Read from", "extract_source", "text"),
                   ("Read confidence", "extract_confidence", "pct_unit"),
                   ("Party's stance", "stance", "text"),
                   ("Outcome", "status", "status")]
        totals = {"confirmed_amount": sum(abs(r["confirmed_amount"])
                                          for r in data
                                          if r["confirmed_amount"] is not None)}

    elif kind == REPORT_PENDING:
        data = [r for r in rows if r["status"] in (STATUS_PENDING,
                                                   STATUS_RETURNED)]
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Amount as per books", "books_amount", "money"),
                   ("Email", "email", "text"),
                   ("Date sent", "sent_at", "date"),
                   ("Days outstanding", "age_days", "number"),
                   ("Reminder due", "reminder_label", "text"),
                   ("Status", "status", "status")]
        stages = context.get("reminders", DEFAULT_REMINDERS)
        for row in data:
            stage = row.get("reminder_stage", 0)
            row["reminder_label"] = ("%d of %d (%d days)"
                                     % (stage, len(stages),
                                        sorted(stages)[stage - 1])) \
                if stage else "not yet"
        totals = {"books_amount": sum(abs(r["books_amount"]) for r in data
                                      if r["books_amount"] is not None)}

    elif kind == REPORT_COMPARISON:
        data = [r for r in rows if r["status"] != STATUS_NOT_SENT]
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Currency", "currency", "text"),
                   ("As per client's books", "books_amount", "money"),
                   ("Confirmed by party", "confirmed_amount", "money"),
                   ("Variance (confirmed less books)", "variance", "money"),
                   ("Variance %", "variance_pct", "pct"),
                   ("Status", "status", "status"),
                   ("Audit status", "audit_state", "link"),
                   ("Confirmed by (reply from)", "reply_from", "text"),
                   ("Reply received", "received_at", "date"),
                   ("Remark", "note", "text")]
        totals = {
            "books_amount": sum(abs(r["books_amount"]) for r in data
                                if r["books_amount"] is not None),
            "confirmed_amount": sum(abs(r["confirmed_amount"]) for r in data
                                    if r["confirmed_amount"] is not None),
            "variance": sum(r["variance"] for r in data
                            if r["variance"] is not None),
        }

    elif kind == REPORT_VARIANCE:
        columns = [("Category", "category", "text"),
                   ("Parties", "parties", "number"),
                   ("Value requested", "requested_value", "money"),
                   ("Books value of replies counted", "confirmed_value",
                    "money"),
                   ("Coverage %", "coverage_pct", "pct"),
                   ("Amount confirmed by parties", "amount_confirmed",
                    "money"),
                   ("Matched", "agreed", "number"),
                   ("Mismatch", "variance", "number"),
                   ("Pending", "pending", "number"),
                   ("Returned", "returned", "number"),
                   ("Needs Review", "review", "number"),
                   ("Net difference", "net_variance", "money"),
                   ("Gross difference", "gross_variance", "money")]
        data = summarise_by_category(rows)
        overall = summarise(rows)
        totals = {"parties": sum(d["parties"] for d in data),
                  "requested_value": overall["requested_value"],
                  "confirmed_value": overall["confirmed_value"],
                  "amount_confirmed": overall["amount_confirmed"],
                  "coverage_pct": _pct(overall["coverage_pct"]),
                  "agreed": overall["agreed"],
                  "variance": overall["variance"],
                  "pending": overall["pending"],
                  "returned": overall["returned"],
                  "review": overall["review"],
                  "net_variance": overall["net_variance"],
                  "gross_variance": overall["gross_variance"]}

    elif kind == REPORT_EXCEPTIONS:
        columns = [("Action", "review", "action"),
                   ("Reason", "reason", "text"),
                   ("From", "from_email", "text"),
                   ("Received", "received_at", "date"),
                   ("Amount read", "amount", "money"),
                   ("Suggested party", "suggested_party", "text"),
                   ("Evidence points to", "candidates", "text"),
                   ("Subject", "subject", "text"),
                   ("Name on the reply", "from_name", "text"),
                   ("Confidence", "confidence", "pct_unit")]
        data = list(exceptions)
        totals = {}

    elif kind == REPORT_AUDIT:
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Reference", "reference", "text"),
                   ("As per client's books", "books_amount", "money"),
                   ("Confirmed by party", "confirmed_amount", "money"),
                   ("Variance", "variance", "money"),
                   ("Confirmation status", "confirmation_status", "status"),
                   ("Follow-up", "state", "link"),
                   ("Nature of difference", "nature", "text"),
                   ("Notes", "notes", "text"),
                   ("Owner", "owner", "text"),
                   ("Reply from", "reply_from", "text"),
                   ("Reply received", "reply_received_at", "date"),
                   ("Opened", "created_at", "date"),
                   ("Last updated", "updated_at", "date")]
        # the record shows the position as it stands NOW, not as it stood
        # when the record was opened
        current = {r.get("document_id"): r for r in rows}
        data = []
        for record in context.get("audit_records") or []:
            if record.get("document_id") not in current:
                continue
            entry = dict(record)
            entry.update(audit_snapshot(current[record["document_id"]]))
            entry["state_link"] = "Open record: %s" % entry.get("state", "")
            data.append(entry)
        data.sort(key=lambda e: (e.get("state") not in AUDIT_OPEN_STATES,
                                 str(e.get("party_name", "")).lower()))
        totals = {"variance": sum(e["variance"] for e in data
                                  if e.get("variance") is not None)}

    else:
        raise ValueError("Unknown report: %s" % kind)

    return {"key": kind, "title": title[0], "subtitle": title[1],
            "columns": columns, "rows": data, "totals": totals,
            "note": context.get("note", "")}


def build_all_reports(rows, exceptions, context=None):
    """Every report as it goes on paper: the screen-only action column is
    left out."""
    reports = [build_report(key, rows, exceptions, context)
               for key, _title, _sub in REPORT_TITLES]
    for report in reports:
        report["columns"] = [column for column in report["columns"]
                             if column[2] != "action"]
    return reports


def format_cell(value, kind, currency="INR"):
    """One value as it should read on screen and on paper."""
    if value is None or value == "":
        return ""
    if kind == "money":
        return fmt_amount(value, currency) or ""
    if kind == "pct":
        return "%.2f%%" % float(value)
    if kind == "pct_unit":
        return "%d%%" % round(float(value) * 100)
    if kind == "date":
        return fmt_date_long(value) or str(value)
    if kind == "number":
        return str(int(value)) if float(value) == int(float(value)) \
            else str(value)
    return str(value)


# ------------------------------------------------------------- Excel export
def write_reports_xlsx(path, reports, heading):
    """One sheet per report, frozen headings, totals, and a cover sheet."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    ink = "FF23281A"
    olive = "FF5F7232"
    band = "FFEFF2E4"
    rule = Side(style="thin", color="FFD5D8C4")

    book = Workbook()
    cover = book.active
    cover.title = "Cover"
    cover["A1"] = heading.get("title", "Balance confirmation reports")
    cover["A1"].font = Font(size=16, bold=True, color=ink)
    line = 3
    for label, value in heading.get("facts", []):
        cover.cell(row=line, column=1, value=label).font = Font(bold=True,
                                                                color=ink)
        cover.cell(row=line, column=2, value=value)
        line += 1
    cover.column_dimensions["A"].width = 30
    cover.column_dimensions["B"].width = 60
    cover.sheet_view.showGridLines = False

    for report in reports:
        sheet = book.create_sheet(report["title"][:31])
        sheet.sheet_view.showGridLines = False
        sheet["A1"] = report["title"]
        sheet["A1"].font = Font(size=13, bold=True, color=ink)
        sheet["A2"] = report["subtitle"]
        sheet["A2"].font = Font(size=10, italic=True, color="FF6E755B")

        head_row = 4
        for index, (heading_text, _key, _kind) in enumerate(report["columns"],
                                                            start=1):
            cell_ = sheet.cell(row=head_row, column=index, value=heading_text)
            cell_.font = Font(bold=True, color="FFFFFFFF", size=10)
            cell_.fill = PatternFill("solid", fgColor=olive)
            cell_.alignment = Alignment(vertical="center", wrap_text=True)
            cell_.border = Border(bottom=rule)

        for offset, row in enumerate(report["rows"]):
            excel_row = head_row + 1 + offset
            currency = row.get("currency") or "INR"
            for index, (_heading, key, kind) in enumerate(report["columns"],
                                                          start=1):
                value = row.get(key)
                cell_ = sheet.cell(row=excel_row, column=index)
                if kind in ("money", "number") and isinstance(value,
                                                              (int, float)):
                    cell_.value = value
                    cell_.number_format = ('#,##0.00' if kind == "money"
                                           else '#,##0')
                    cell_.alignment = Alignment(horizontal="right")
                elif kind == "pct" and isinstance(value, (int, float)):
                    cell_.value = value / 100.0
                    cell_.number_format = '0.00%'
                    cell_.alignment = Alignment(horizontal="right")
                elif kind == "pct_unit" and isinstance(value, (int, float)):
                    cell_.value = value
                    cell_.number_format = '0%'
                    cell_.alignment = Alignment(horizontal="right")
                else:
                    cell_.value = format_cell(value, kind, currency)
                    cell_.alignment = Alignment(horizontal="left",
                                                vertical="top")
                cell_.border = Border(bottom=rule)
                if offset % 2 == 1:
                    cell_.fill = PatternFill("solid", fgColor=band)
                if kind == "status" and value in (STATUS_VARIANCE,
                                                  STATUS_REVIEW):
                    cell_.font = Font(bold=True, color="FF9B3F28")
                elif kind == "status" and value == STATUS_AGREED:
                    cell_.font = Font(bold=True, color="FF3F6B1F")

        if report["totals"]:
            total_row = head_row + 1 + len(report["rows"])
            sheet.cell(row=total_row, column=1, value="Total").font = Font(
                bold=True, color=ink)
            for index, (_heading, key, kind) in enumerate(report["columns"],
                                                          start=1):
                if key in report["totals"]:
                    value = report["totals"][key]
                    cell_ = sheet.cell(row=total_row, column=index)
                    if kind == "pct":
                        cell_.value = (value or 0) / 100.0
                        cell_.number_format = '0.00%'
                    else:
                        cell_.value = value
                        cell_.number_format = ('#,##0.00' if kind == "money"
                                               else '#,##0')
                    cell_.font = Font(bold=True, color=ink)
                    cell_.alignment = Alignment(horizontal="right")
                    cell_.border = Border(top=Side(style="thin", color=olive))

        if not report["rows"]:
            sheet.cell(row=head_row + 1, column=1,
                       value="Nothing to report.").font = Font(italic=True,
                                                               color="FF6E755B")

        for index, (heading_text, key, kind) in enumerate(report["columns"],
                                                          start=1):
            widest = len(heading_text)
            for row in report["rows"]:
                widest = max(widest, len(format_cell(row.get(key), kind,
                                                     row.get("currency")
                                                     or "INR")))
            sheet.column_dimensions[get_column_letter(index)].width = \
                min(46, max(11, widest + 3))
        sheet.freeze_panes = sheet.cell(row=head_row + 1, column=1)

    book.save(path)
    return path


# --------------------------------------------------------------- PDF export
def write_reports_pdf(path, reports, heading):
    """Landscape A4, one report per page, same figures as the workbook."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)

    ink = colors.HexColor("#23281A")
    olive = colors.HexColor("#5F7232")
    muted = colors.HexColor("#6E755B")
    band = colors.HexColor("#F2F4EA")
    rule = colors.HexColor("#D5D8C4")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("t", parent=styles["Title"], fontSize=15,
                                 textColor=ink, alignment=TA_LEFT,
                                 spaceAfter=2)
    sub_style = ParagraphStyle("s", parent=styles["Normal"], fontSize=9,
                               textColor=muted, spaceAfter=8)
    fact_style = ParagraphStyle("f", parent=styles["Normal"], fontSize=9,
                                textColor=ink, leading=13)
    cell_style = ParagraphStyle("c", parent=styles["Normal"], fontSize=7.5,
                                textColor=ink, leading=9.5)
    head_style = ParagraphStyle("h", parent=styles["Normal"], fontSize=7.5,
                                textColor=colors.white, leading=9.5,
                                fontName="Helvetica-Bold")

    document = SimpleDocTemplate(
        path, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title=heading.get("title", "Balance confirmation reports"),
        author=heading.get("author", ""))

    story = [Paragraph(heading.get("title", "Balance confirmation reports"),
                       title_style)]
    facts = "<br/>".join("<b>%s</b>&nbsp;&nbsp;%s" % (label, xml_escape(value))
                         for label, value in heading.get("facts", []))
    if facts:
        story.append(Paragraph(facts, fact_style))
    story.append(Spacer(1, 6 * mm))

    for index, report in enumerate(reports):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(xml_escape(report["title"]), title_style))
        story.append(Paragraph(xml_escape(report["subtitle"]), sub_style))

        head = [Paragraph(xml_escape(h), head_style)
                for h, _k, _t in report["columns"]]
        body = []
        for row in report["rows"]:
            currency = row.get("currency") or "INR"
            body.append([Paragraph(xml_escape(format_cell(row.get(key), kind,
                                                          currency)),
                                   cell_style)
                         for _h, key, kind in report["columns"]])
        if not body:
            body = [[Paragraph("<i>Nothing to report.</i>", cell_style)]
                    + [Paragraph("", cell_style)] * (len(head) - 1)]

        if report["totals"]:
            total_cells = []
            for position, (_h, key, kind) in enumerate(report["columns"]):
                if position == 0:
                    total_cells.append(Paragraph("<b>Total</b>", cell_style))
                elif key in report["totals"]:
                    total_cells.append(Paragraph(
                        "<b>%s</b>" % xml_escape(
                            format_cell(report["totals"][key], kind, "INR")),
                        cell_style))
                else:
                    total_cells.append(Paragraph("", cell_style))
            body.append(total_cells)

        table = Table([head] + body, repeatRows=1, hAlign="LEFT")
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), olive),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, rule),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        for position in range(1, len(body) + 1):
            if position % 2 == 0:
                style.append(("BACKGROUND", (0, position), (-1, position), band))
        if report["totals"]:
            last = len(body)
            style.append(("LINEABOVE", (0, last), (-1, last), 0.8, olive))
            style.append(("BACKGROUND", (0, last), (-1, last), colors.white))
        table.setStyle(TableStyle(style))
        story.append(table)

    document.build(story)
    return path
