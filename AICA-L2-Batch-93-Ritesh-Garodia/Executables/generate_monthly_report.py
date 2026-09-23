"""
Month-end Compliance PDF Report Generator - ICAI AICA Level 2 Capstone Project

Reads Compliance_Master.xlsx ("Task Instances" sheet) and produces a PDF
report of every compliance item due in the given month: tax/compliance name,
due date, actual payment date, amount, and status - grouped by department.

Usage:
    python generate_monthly_report.py                 # current month
    python generate_monthly_report.py 2026-09          # a specific month (YYYY-MM)
"""

import sys
import datetime as dt
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

MASTER_FILE = "Compliance_Master.xlsx"


def parse_month_arg():
    if len(sys.argv) > 1:
        year, month = (int(x) for x in sys.argv[1].split("-"))
        return year, month
    today = dt.date.today()
    return today.year, today.month


def load_month_data(year, month):
    df = pd.read_excel(MASTER_FILE, sheet_name="Task Instances", engine="openpyxl")
    df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")
    df["Payment Date"] = pd.to_datetime(df["Payment Date"], errors="coerce")
    df["Task Complete (Y/N)"] = df["Task Complete (Y/N)"].fillna("N").astype(str).str.upper()
    month_df = df[(df["Due Date"].dt.year == year) & (df["Due Date"].dt.month == month)].copy()

    def status(row):
        if row["Task Complete (Y/N)"] == "Y":
            return "Completed"
        if row["Due Date"] < pd.Timestamp(dt.date.today()):
            return "Overdue"
        return "Pending"

    month_df["Status"] = month_df.apply(status, axis=1)
    return month_df.sort_values(["Department", "Due Date"])


def fmt_date(d):
    return d.strftime("%d-%b-%Y") if pd.notna(d) else "-"


def fmt_amount(a):
    if pd.isna(a) or a == "":
        return "-"
    return f"{float(a):,.0f}"


def build_pdf(month_df, year, month, out_path):
    doc = SimpleDocTemplate(
        out_path, pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=18, spaceAfter=4)
    sub_style = ParagraphStyle("SubX", parent=styles["Normal"], fontSize=10, textColor=colors.grey)
    dept_style = ParagraphStyle("DeptX", parent=styles["Heading2"], fontSize=13,
                                 textColor=colors.HexColor("#1F4E78"), spaceBefore=14, spaceAfter=6)

    month_name = dt.date(year, month, 1).strftime("%B %Y")
    story = [
        Paragraph("Tax &amp; Labour-Code Compliance Report", title_style),
        Paragraph(f"Month: {month_name}  |  Generated on {dt.date.today().strftime('%d-%b-%Y')}", sub_style),
        Spacer(1, 10),
    ]

    total_due = 0.0
    total_paid = 0.0

    if month_df.empty:
        story.append(Paragraph("No compliance items due in this month.", styles["Normal"]))
    else:
        header = ["Compliance", "Periodicity", "Due Date", "Amount Due",
                  "Amount Paid", "Payment Date", "Status"]
        for dept, dept_df in month_df.groupby("Department"):
            story.append(Paragraph(dept, dept_style))
            data = [header]
            for _, row in dept_df.iterrows():
                data.append([
                    row["Compliance Name"],
                    row["Periodicity"],
                    fmt_date(row["Due Date"]),
                    fmt_amount(row["Amount Due"]),
                    fmt_amount(row["Amount Paid"]),
                    fmt_date(row["Payment Date"]),
                    row["Status"],
                ])
                total_due += float(row["Amount Due"]) if pd.notna(row["Amount Due"]) and row["Amount Due"] != "" else 0
                total_paid += float(row["Amount Paid"]) if pd.notna(row["Amount Paid"]) and row["Amount Paid"] != "" else 0

            col_widths = [70 * mm, 24 * mm, 24 * mm, 24 * mm, 24 * mm, 26 * mm, 24 * mm]
            table = Table(data, colWidths=col_widths, repeatRows=1)
            status_col = 6
            style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6FB")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (3, 1), (5, -1), "RIGHT"),
            ]
            for r_idx in range(1, len(data)):
                status_val = data[r_idx][status_col]
                color = colors.HexColor("#2E7D32") if status_val == "Completed" else (
                    colors.HexColor("#C62828") if status_val == "Overdue" else colors.HexColor("#B26A00"))
                style_cmds.append(("TEXTCOLOR", (status_col, r_idx), (status_col, r_idx), color))
                style_cmds.append(("FONTNAME", (status_col, r_idx), (status_col, r_idx), "Helvetica-Bold"))
            table.setStyle(TableStyle(style_cmds))
            story.append(table)
            story.append(Spacer(1, 6))

        story.append(Spacer(1, 10))
        summary_style = ParagraphStyle("SummaryX", parent=styles["Normal"], fontSize=10.5)
        story.append(Paragraph(
            f"<b>Total Amount Due:</b> {total_due:,.0f}  &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Total Amount Paid:</b> {total_paid:,.0f}  &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Variance:</b> {total_due - total_paid:,.0f}",
            summary_style,
        ))

    doc.build(story)


def main():
    year, month = parse_month_arg()
    month_df = load_month_data(year, month)
    out_path = f"Compliance_Report_{year}-{month:02d}.pdf"
    build_pdf(month_df, year, month, out_path)
    print(f"Saved {out_path} ({len(month_df)} items)")


if __name__ == "__main__":
    main()
