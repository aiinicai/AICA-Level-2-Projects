"""
reports.py - Exports produced by the Task Tracker.

  tasks_csv()            : every task as a CSV file that opens in Excel
  needs_attention_pdf()  : a printable "Needs Attention" report - starred
                           tasks, overdue tasks and tasks due within 2 days,
                           grouped section-wise
"""

import csv
import io
from datetime import date
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

import cycles

NAVY, OCHRE = (31, 56, 100), (191, 144, 0)
INK, MUTED, LINE, HEAD_FILL = (20, 32, 58), (122, 132, 152), (220, 225, 234), (242, 244, 248)
WINDOWS_FONTS = Path("C:/Windows/Fonts")


def _by_order(task):
    return (task.get("order") or 0, task.get("title") or "")


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------
def tasks_csv(sections, tasks, today=None):
    today = today or date.today()
    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(["Section", "Particulars", "Due", "Repeats", "With", "Label",
                     "Remarks", "Status", "Steps"])
    for section in sections:
        for task in sorted((t for t in tasks if t.get("section") == section["id"]), key=_by_order):
            status = cycles.pill_text(task, cycles.info(task, today), today) or "Open"
            steps = "; ".join(("[x] " if s["done"] else "[ ] ") + s["text"]
                              for s in task.get("subtasks", []))
            writer.writerow([section["name"], task.get("title", ""),
                             cycles.due_text(task, today), task.get("frequency") or "One-time",
                             task.get("owner") or "", task.get("tag") or "",
                             task.get("remarks") or "", status, steps])
    # The BOM makes Excel read the file as UTF-8 (needed for symbols such as the rupee sign)
    return "\ufeff" + out.getvalue()


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------
def attention_tasks(tasks, today):
    """Open tasks that need attention, each paired with a rank:
    0 = starred, 1 = overdue, 2 = due within the next 2 days."""
    picked = []
    for task in tasks:
        i = cycles.info(task, today)
        if i["done"] or i["checked"]:
            continue
        if task.get("starred"):
            rank = 0
        elif i["state"] == "overdue":
            rank = 1
        elif i["days"] is not None and 0 <= i["days"] <= 2 and not i["free"]:
            rank = 2
        else:
            continue
        picked.append((rank, i["c"]["deadline"] or date.max, _by_order(task), task))
    return sorted(picked, key=lambda item: item[:3])


class ReportPDF(FPDF):
    def __init__(self, footer_text):
        super().__init__(unit="mm", format="A4")
        self.footer_text = footer_text
        self.face = "helvetica"
        regular, bold = WINDOWS_FONTS / "arial.ttf", WINDOWS_FONTS / "arialbd.ttf"
        if regular.exists() and bold.exists():          # Unicode font when available
            self.add_font("arial", "", str(regular))
            self.add_font("arial", "B", str(bold))
            self.face = "arial"
        self.set_margins(16, 14, 16)
        self.set_auto_page_break(True, margin=16)

    def clean(self, text):
        """The built-in Helvetica font supports only Latin-1 characters."""
        text = str(text or "")
        if self.face == "helvetica":
            text = text.replace("–", "-").replace("·", "-").replace("—", "-")
            text = text.encode("latin-1", "replace").decode("latin-1")
        return text

    def footer(self):
        self.set_y(-12)
        self.set_font(self.face, "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, self.clean(self.footer_text))
        self.set_x(16)
        self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="R")


def needs_attention_pdf(sections, tasks, today=None):
    today = today or date.today()
    date_text = f"{today:%A}, {cycles.fmt(today, today, with_year=True)}"
    pdf = ReportPDF(f"Task Tracker  ·  Needs Attention  ·  {cycles.fmt(today, today, True)}")
    pdf.add_page()

    pdf.set_font(pdf.face, "B", 18)
    pdf.set_text_color(*INK)
    pdf.cell(0, 9, "Needs Attention", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(pdf.face, "", 9.5)
    pdf.set_text_color(*MUTED)
    subtitle = f"{date_text}   ·   {cycles.fy_label(cycles.fy_start(today))}   ·   Task Tracker"
    pdf.cell(0, 6, pdf.clean(subtitle), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.6)
    pdf.line(16, pdf.get_y() + 1.5, 194, pdf.get_y() + 1.5)
    pdf.ln(7)

    picked = attention_tasks(tasks, today)
    pdf.set_draw_color(*LINE)
    pdf.set_line_width(0.2)
    pdf.set_text_color(*INK)

    for section in sections:
        items = [task for *_, task in picked if task.get("section") == section["id"]]
        if not items:
            continue
        ochre = section.get("color") == "ochre"
        band = FontFace(emphasis="BOLD", size_pt=11, fill_color=OCHRE if ochre else NAVY,
                        color=(28, 22, 6) if ochre else (255, 255, 255))
        column_head = FontFace(emphasis="BOLD", size_pt=8, fill_color=HEAD_FILL, color=(74, 85, 108))

        pdf.set_font(pdf.face, "", 9.5)
        with pdf.table(col_widths=(92, 30, 56), num_heading_rows=2, line_height=5.2,
                       padding=(1.6, 3), text_align="LEFT", v_align="TOP",
                       headings_style=FontFace()) as table:
            table.row().cell(pdf.clean(f"{section['name']}   ·   {len(items)}"),
                             colspan=3, style=band)
            head = table.row()
            for title in ("Particulars", "With", "Remarks"):
                head.cell(title, style=column_head)
            for task in items:
                row = table.row()
                for value in (task.get("title"), task.get("owner"), task.get("remarks")):
                    row.cell(pdf.clean(value))
        pdf.ln(8)

    if not picked:
        pdf.set_font(pdf.face, "", 11)
        pdf.cell(0, 8, pdf.clean("All clear — nothing starred, overdue or due in the next 2 days."))

    return bytes(pdf.output())
