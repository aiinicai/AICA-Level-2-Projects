"""
Compliance Tracker Dashboard  -  ICAI AICA Level 2 Capstone Project
Run with:  streamlit run dashboard.py   (or double-click Run_Dashboard.bat)

Reads the "Task Instances" data - live from a shared Google Sheet once
SHEET_CSV_URL is set below (recommended, so every user's data entry shows
up here), or from the local Compliance_Master.xlsx file as a fallback -
and shows a Due-this-month / Completed / Overdue view, filterable by
department.

SETUP FOR LIVE MULTI-USER DATA:
1. Import/keep Compliance_Master.xlsx as a Google Sheet (Google Sheets ->
   File -> Import -> Upload, "Insert new sheet(s)").
2. Share -> add each real user as an Editor (this controls who can key in
   Amount Paid / Payment Date / Task Complete). Keep this restricted.
3. File -> Share -> Publish to web -> select just the "Task Instances"
   sheet -> CSV -> Publish. This gives a public READ-ONLY link, separate
   from the edit permissions above.
4. Paste that link into SHEET_CSV_URL below. The dashboard (and anyone
   you send it to) will then always show the latest shared data, with no
   login needed to view it.
5. Optional but recommended: add a "Trial Balance" tab to the same Sheet
   (columns: Period (mmm-yyyy), GL Code, GL Name, TB Balance), repeat step
   3-4 for that tab, and paste its link into TB_SHEET_CSV_URL below. The
   Variance Report in the sidebar then compares against it automatically -
   no manual upload needed each month.

DEMO NOTE 1: this build uses a simple View toggle (User / HOD) instead of
real login, to keep the capstone demo/recording simple. On a live
deployment this would be replaced with email-based login so each person
only ever sees their own department automatically (see project PPT).

DEMO NOTE 2: running this with "streamlit run dashboard.py" only serves
the app on your own machine (localhost) - other users cannot open it. A
live deployment would host this on Streamlit Community Cloud (or a
similar host) so it runs continuously at a public URL that every
department and the HOD can open from their own browser (see project PPT).
"""

import datetime as dt
import io
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

MASTER_FILE = "Compliance_Master.xlsx"
USER_EMAIL = "riteshgarodia@yahoo.com"
HOD_EMAIL = "garodia1.ritesh@gmail.com"

# ---- Live data source (Google Sheet) -----------------------------------
# Paste the "Publish to web" CSV link for the "Task Instances" tab here.
# File -> Share -> Publish to web -> choose the "Task Instances" sheet ->
# CSV -> Publish -> copy the link below. This is a public READ-ONLY export
# link, separate from who has *edit* access (that stays controlled by the
# normal Share button, restricted to specific invited Editors).
# Leave it as "" to keep using the local Compliance_Master.xlsx file instead
# (e.g. while you're still setting the Google Sheet up).
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSM7hSr2kJKeu8Ocd1wPSAY7UpGldiTzoOT_u3fLl69ejpbkwfqC2aXkPguepJeaBxPmQ6l0EUhO1a1/pub?gid=1644749680&single=true&output=csv"

# Same idea for the "Trial Balance" tab (same Google Sheet or a separate one),
# so the Variance Report pulls the trial balance automatically instead of a
# manual file upload. Publish just that tab to web as CSV the same way, and
# paste its link here. Required columns: Period (mmm-yyyy), GL Code, GL Name,
# TB Balance (a "TB Balance (Dr)" column, as in the master workbook's Trial
# Balance sheet, is also accepted and renamed automatically).
# Leave as "" to fall back to the "Trial Balance" sheet in Compliance_Master.xlsx.
TB_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSM7hSr2kJKeu8Ocd1wPSAY7UpGldiTzoOT_u3fLl69ejpbkwfqC2aXkPguepJeaBxPmQ6l0EUhO1a1/pub?gid=89901483&single=true&output=csv"

# ---- Brand palette (matches the Excel tracker / PDF report / slide deck) ----
NAVY = "#14213D"
ACCENT = "#1F4E78"
ACCENT_LIGHT = "#EAF1F8"
GOOD = "#2E7D32"
GOOD_BG = "#E2F0E4"
WARN = "#B26A00"
WARN_BG = "#FDF3E3"
CRIT = "#C0392B"
CRIT_BG = "#FBE7E5"
INK_MUTED = "#4A5568"
SURFACE = "#FBFBF8"
BORDER = "#DCE3E8"

st.set_page_config(page_title="Compliance Tracker Dashboard", page_icon="📋", layout="wide")

st.markdown(f"""
<style>
    .stApp {{ background-color: {SURFACE}; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    .block-container {{ padding-top: 1.5rem; max-width: 1200px; }}
    html, body, [class*="css"] {{ font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}

    .ct-banner {{
        background: linear-gradient(135deg, {NAVY} 0%, {ACCENT} 100%);
        border-radius: 14px; padding: 28px 32px; margin-bottom: 22px;
        color: #FBFBF8;
    }}
    .ct-banner h1 {{ margin: 0; font-size: 30px; font-weight: 700; color: #FBFBF8; }}
    .ct-banner p {{ margin: 6px 0 0 0; font-size: 14px; color: #BFD8D5; }}

    .ct-kpi {{
        border-radius: 12px; padding: 18px 20px; border: 1px solid {BORDER};
        background: white; text-align: left; height: 100%;
    }}
    .ct-kpi .ct-kpi-label {{ font-size: 12.5px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.5px; color: {INK_MUTED}; margin-bottom: 6px; }}
    .ct-kpi .ct-kpi-value {{ font-size: 34px; font-weight: 700; line-height: 1; }}

    .ct-badge {{ display:inline-block; padding: 3px 12px; border-radius: 999px;
        font-size: 12.5px; font-weight: 700; }}

    .ct-section-title {{ font-size: 17px; font-weight: 700; color: {NAVY};
        margin: 4px 0 10px 0; }}

    section[data-testid="stSidebar"] {{ background-color: {NAVY}; }}
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] hr {{
        color: #FBFBF8 !important; }}
    /* Selectbox / multiselect closed box: white background, dark readable text */
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important; border: 1px solid #3A4A6B; }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] * {{
        color: {NAVY} !important; }}
    /* Multiselect chips */
    section[data-testid="stSidebar"] span[data-baseweb="tag"] {{
        background-color: {ACCENT} !important; color: #FFFFFF !important; }}
    section[data-testid="stSidebar"] span[data-baseweb="tag"] * {{ color: #FFFFFF !important; }}
    /* Dropdown menu popover (renders in a portal, outside the sidebar) */
    ul[data-testid="stSelectboxVirtualDropdown"], div[data-baseweb="popover"] li {{
        color: {NAVY} !important; background-color: #FFFFFF !important; }}

    div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 10px; overflow: hidden; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data(path, sheet_csv_url):
    if sheet_csv_url:
        # Live source: Google Sheet "Publish to web" CSV export.
        df = pd.read_csv(sheet_csv_url)
    else:
        # Fallback: local workbook (used before the Sheet link is configured).
        df = pd.read_excel(path, sheet_name="Task Instances", engine="openpyxl")
    df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")
    df["Payment Date"] = pd.to_datetime(df["Payment Date"], errors="coerce")
    df["Task Complete (Y/N)"] = df["Task Complete (Y/N)"].fillna("N").astype(str).str.upper()
    today = pd.Timestamp(dt.date.today())
    df["Is Completed"] = df["Task Complete (Y/N)"] == "Y"
    df["Is Overdue"] = (~df["Is Completed"]) & (df["Due Date"] < today)
    df["Is Due This Month"] = (
        (~df["Is Completed"])
        & (df["Due Date"].dt.month == today.month)
        & (df["Due Date"].dt.year == today.year)
    )
    return df


def status_of(row):
    if row["Is Completed"]:
        return "Completed"
    if row["Is Overdue"]:
        return "Overdue"
    return "Pending"


def kpi_card(label, value, color, bg):
    st.markdown(f"""
    <div class="ct-kpi" style="border-left: 5px solid {color};">
        <div class="ct-kpi-label">{label}</div>
        <div class="ct-kpi-value" style="color:{color}">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def style_status_table(frame):
    display = frame.copy()
    for col in ("Due Date", "Payment Date"):
        display[col] = display[col].dt.strftime("%d-%b-%Y").fillna("-")
    for col in ("Amount Due", "Amount Paid"):
        display[col] = display[col].apply(lambda v: f"{v:,.0f}" if pd.notna(v) and v != "" else "-")

    def status_style(val):
        if val == "Completed":
            return f"background-color:{GOOD_BG}; color:{GOOD}; font-weight:700; border-radius:6px;"
        if val == "Overdue":
            return f"background-color:{CRIT_BG}; color:{CRIT}; font-weight:700; border-radius:6px;"
        return f"background-color:{WARN_BG}; color:{WARN}; font-weight:700; border-radius:6px;"

    styler = display.style.map(status_style, subset=["Status"])
    styler = styler.set_properties(**{"font-size": "13.5px"})
    return styler


def _fmt_date(d):
    return d.strftime("%d-%b-%Y") if pd.notna(d) else "-"


def _fmt_amount(a):
    if pd.isna(a) or a == "":
        return "-"
    return f"{float(a):,.0f}"


def build_report_pdf(month_df, year, month):
    """Builds the month-end compliance PDF report (same layout as
    generate_monthly_report.py) into an in-memory buffer and returns the bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
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
                    _fmt_date(row["Due Date"]),
                    _fmt_amount(row["Amount Due"]),
                    _fmt_amount(row["Amount Paid"]),
                    _fmt_date(row["Payment Date"]),
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
    buf.seek(0)
    return buf.getvalue()


VARIANCE_FONT_NAME = "Arial"
VARIANCE_HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
VARIANCE_HEADER_FONT = Font(name=VARIANCE_FONT_NAME, bold=True, color="FFFFFF", size=11)
VARIANCE_OK_FILL = PatternFill("solid", fgColor="E2EFDA")
VARIANCE_BAD_FILL = PatternFill("solid", fgColor="FCE4E4")
VARIANCE_THIN = Side(style="thin", color="BFBFBF")
VARIANCE_BORDER = Border(left=VARIANCE_THIN, right=VARIANCE_THIN, top=VARIANCE_THIN, bottom=VARIANCE_THIN)


@st.cache_data(ttl=60)
def load_trial_balance(tb_sheet_csv_url, master_file):
    """Reads the Trial Balance - live from the Google Sheet tab if
    TB_SHEET_CSV_URL is set, otherwise from the local workbook's
    "Trial Balance" sheet - and validates/normalizes its columns."""
    if tb_sheet_csv_url:
        tb = pd.read_csv(tb_sheet_csv_url)
    else:
        tb = pd.read_excel(master_file, sheet_name="Trial Balance", engine="openpyxl")

    # The master workbook's own Trial Balance sheet uses "TB Balance (Dr)";
    # accept that name too and normalize it.
    if "TB Balance" not in tb.columns and "TB Balance (Dr)" in tb.columns:
        tb = tb.rename(columns={"TB Balance (Dr)": "TB Balance"})

    required = {"Period (mmm-yyyy)", "GL Code", "GL Name", "TB Balance"}
    missing = required - set(tb.columns)
    if missing:
        raise ValueError(f"Trial Balance data is missing columns: {', '.join(sorted(missing))}")

    # Drop blank/instruction rows (e.g. the sample workbook's "Example rows..." note).
    tb = tb.dropna(subset=["GL Code", "Period (mmm-yyyy)"]).copy()
    return tb


def build_variance_report_xlsx(task_df, tb):
    """Compares the tracker's actual payments (by GL Code and period) against an
    uploaded Trial Balance and returns the Variance_Report.xlsx as bytes."""
    actual_df = task_df.copy()
    actual_df["Amount Paid"] = pd.to_numeric(actual_df["Amount Paid"], errors="coerce").fillna(0)
    actual_df = actual_df[actual_df["Payment Date"].notna()].copy()
    actual_df["Period (mmm-yyyy)"] = actual_df["Payment Date"].dt.strftime("%b-%Y")
    actual = (
        actual_df.groupby(["Period (mmm-yyyy)", "GL Code"])["Amount Paid"]
        .sum()
        .reset_index()
        .rename(columns={"Amount Paid": "Actual Amount Paid"})
    )

    merged = tb.merge(actual, on=["Period (mmm-yyyy)", "GL Code"], how="left")
    merged["Actual Amount Paid"] = merged["Actual Amount Paid"].fillna(0)
    merged["Variance (TB - Paid)"] = merged["TB Balance"] - merged["Actual Amount Paid"]
    merged["Flag"] = merged["Variance (TB - Paid)"].abs().le(1).map({True: "OK", False: "VARIANCE"})

    wb = Workbook()
    ws = wb.active
    ws.title = "Variance Report"
    headers = ["Period", "GL Code", "GL Name", "Trial Balance Amount",
               "Actual Amount Paid", "Variance (TB - Paid)", "Flag"]
    for i, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.fill = VARIANCE_HEADER_FILL
        cell.font = VARIANCE_HEADER_FONT
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    for r, row in enumerate(merged.itertuples(index=False), start=2):
        values = [row[0], row[1], row[2], row[3], row[4], row[5], row[6]]
        for c, val in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.font = Font(name=VARIANCE_FONT_NAME, size=10)
            cell.border = VARIANCE_BORDER
            if c in (4, 5, 6):
                cell.number_format = "#,##0"
        fill = VARIANCE_OK_FILL if row[6] == "OK" else VARIANCE_BAD_FILL
        for c in range(1, 8):
            ws.cell(row=r, column=c).fill = fill

    n_variance = int((merged["Flag"] == "VARIANCE").sum())
    total_row = len(merged) + 3
    ws.cell(row=total_row, column=1,
            value=f"{n_variance} of {len(merged)} GL lines show a variance"
                  " (difference > 1) between Trial Balance and actual tax paid.").font = \
        Font(name=VARIANCE_FONT_NAME, italic=True, bold=n_variance > 0,
             color="C00000" if n_variance > 0 else "595959")

    widths = [14, 12, 26, 20, 20, 20, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue(), n_variance, len(merged)


st.markdown(f"""
<div class="ct-banner">
    <h1>📋 Tax &amp; Labour-Code Compliance Tracker</h1>
    <p>ICAI AICA Level 2 Capstone Project — live view of due, completed and overdue compliance tasks</p>
</div>
""", unsafe_allow_html=True)

try:
    df = load_data(MASTER_FILE, SHEET_CSV_URL)
except FileNotFoundError:
    st.error(f"Could not find '{MASTER_FILE}'. Place it in the same folder as this script, "
             "or set SHEET_CSV_URL at the top of dashboard.py to read from the shared Google Sheet instead.")
    st.stop()
except Exception as e:
    st.error(f"Could not load data from the Google Sheet link. Check that SHEET_CSV_URL is a valid "
             f"'Publish to web' CSV link for the 'Task Instances' tab.\n\nDetails: {e}")
    st.stop()

departments = sorted(df["Department"].dropna().unique().tolist())

with st.sidebar:
    st.markdown("### 🔐 View")
    view = st.selectbox("Select view", ["User view", "HOD view"], label_visibility="collapsed")
    is_hod = view == "HOD view"
    st.caption(f"Signed in as: **{HOD_EMAIL if is_hod else USER_EMAIL}**")
    st.caption(
        "Demo build uses a view toggle. On live deployment, "
        "email-based login selects this automatically."
    )
    st.markdown("---")
    st.markdown("### 🏢 Department")
    if is_hod:
        dept_filter = st.multiselect("Departments", departments, default=departments, label_visibility="collapsed")
    else:
        dept_filter = [st.selectbox("Department", departments, label_visibility="collapsed")]
    st.markdown("---")
    st.markdown("### 📄 Month-End Report")
    today = dt.date.today()
    month_options = [
        (dt.date(today.year, today.month, 1) - pd.DateOffset(months=i)).strftime("%B %Y")
        for i in range(0, 12)
    ]
    picked_month_label = st.selectbox("Report month", month_options, label_visibility="collapsed")
    picked_dt = dt.datetime.strptime(picked_month_label, "%B %Y")
    report_scope = df[df["Department"].isin(dept_filter)].copy()
    month_df = report_scope[
        (report_scope["Due Date"].dt.year == picked_dt.year)
        & (report_scope["Due Date"].dt.month == picked_dt.month)
    ].copy()
    month_df["Status"] = month_df.apply(status_of, axis=1)
    month_df = month_df.sort_values(["Department", "Due Date"])
    pdf_bytes = build_report_pdf(month_df, picked_dt.year, picked_dt.month)
    st.download_button(
        "⬇️ Download PDF report",
        data=pdf_bytes,
        file_name=f"Compliance_Report_{picked_dt.year}-{picked_dt.month:02d}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
    st.markdown("---")
    st.markdown("### 📊 Variance Report")
    try:
        tb_df = load_trial_balance(TB_SHEET_CSV_URL, MASTER_FILE)
        xlsx_bytes, n_variance, n_total = build_variance_report_xlsx(df, tb_df)
        source_note = "shared Google Sheet" if TB_SHEET_CSV_URL else "local Compliance_Master.xlsx"
        st.caption(f"Trial Balance source: {source_note}.")
        if n_variance == 0:
            st.success(f"No variance: all {n_total} GL lines match.")
        else:
            st.warning(f"{n_variance} of {n_total} GL lines show a variance.")
        st.download_button(
            "⬇️ Download Variance Report",
            data=xlsx_bytes,
            file_name="Variance_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Could not build the Variance Report: {e}")
    st.markdown("---")
    if SHEET_CSV_URL:
        st.caption("Data source: shared Google Sheet → 'Task Instances' (live, all users' updates included). Cached 60s.")
    else:
        st.caption("Data source: local Compliance_Master.xlsx → 'Task Instances' (not yet shared — set SHEET_CSV_URL). Cached 60s.")

view_df = df[df["Department"].isin(dept_filter)].copy()
view_df["Status"] = view_df.apply(status_of, axis=1)

k1, k2, k3, k4 = st.columns(4)
with k1:
    kpi_card("Due this month", int(view_df["Is Due This Month"].sum()), ACCENT, ACCENT_LIGHT)
with k2:
    kpi_card("Completed", int(view_df["Is Completed"].sum()), GOOD, GOOD_BG)
with k3:
    kpi_card("Overdue", int(view_df["Is Overdue"].sum()), CRIT, CRIT_BG)
with k4:
    kpi_card("Total tracked", len(view_df), NAVY, "#F1F1EE")

st.write("")

if is_hod:
    st.markdown('<div class="ct-section-title">By Department</div>', unsafe_allow_html=True)
    dept_summary = (
        view_df.groupby("Department")
        .agg(
            Due_This_Month=("Is Due This Month", "sum"),
            Completed=("Is Completed", "sum"),
            Overdue=("Is Overdue", "sum"),
            Total=("Instance ID", "count"),
        )
        .reset_index()
        .rename(columns={"Due_This_Month": "Due This Month"})
    )
    st.dataframe(
        dept_summary.style.background_gradient(subset=["Overdue"], cmap="Reds")
        .background_gradient(subset=["Completed"], cmap="Greens"),
        use_container_width=True, hide_index=True,
    )
    st.write("")

st.markdown('<div class="ct-section-title">Task Detail</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["📅 Due This Month", "🔴 Overdue", "✅ Completed"])

display_cols = [
    "Compliance Name", "Department", "Periodicity", "Due Date",
    "Assigned User Name", "Amount Due", "Amount Paid", "Payment Date", "Status",
]

with tab1:
    subset = view_df[view_df["Is Due This Month"]][display_cols].sort_values("Due Date")
    st.dataframe(style_status_table(subset), use_container_width=True, hide_index=True)
with tab2:
    subset = view_df[view_df["Is Overdue"]][display_cols].sort_values("Due Date")
    st.dataframe(style_status_table(subset), use_container_width=True, hide_index=True)
with tab3:
    subset = view_df[view_df["Is Completed"]][display_cols].sort_values("Due Date", ascending=False)
    st.dataframe(style_status_table(subset), use_container_width=True, hide_index=True)

st.markdown(
    f"<p style='color:{INK_MUTED}; font-size:12.5px; margin-top:18px;'>"
    "Refreshes automatically (60s cache) when the tracker is updated - by any user in the shared "
    "Google Sheet, or by the n8n workflow."
    "</p>", unsafe_allow_html=True,
)
