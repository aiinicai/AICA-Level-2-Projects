# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Reports: the OUTPUT side of LeaseIQ Pro.

Leases (Add lease, Bulk Upload) are the inputs; Approvals and the Audit Log are the workflow; this page produces the
finished disclosure report for Ind AS 116 or ASC 842 - portfolio summary, lease register, maturity analysis, lease
liability and right-of-use asset movements, lease costs, the consolidated technical memo and reconciliation checks -
as a PDF, a Word document and an Excel workbook.
"""
from datetime import date, datetime

import streamlit as st

from auth_ui import require_login, show_flash
from core import dashboard as dash
from core.formatting import NUMBER_FORMATS, currency_label, format_money
from core.report_docx import build_report_docx, report_docx_name
from core.report_pdf import build_report_pdf, report_pdf_name
from core.report_xlsx import build_report_excel, report_excel_name
from core.reports import FRAMEWORK_TITLES, FRAMEWORKS, build_disclosure_report, report_file_stem
from core.workflow import get_dashboard_leases, get_report_inputs
from db.database import get_session

st.set_page_config(page_title="LeaseIQ Pro - Reports", page_icon="📑", layout="wide")
user = require_login()

STATUS_CHOICES = {
    "Approved and active leases only": ("Approved", "Active"),
    "All calculated leases (pending review, approved, active)": dash.INCLUDE_VALIDATED,
}
FRAMEWORK_KEYS = {"Ind AS 116": "IND_AS_116", "ASC 842": "ASC_842"}

st.title("Reports")
st.caption(
    "The finished output: a full lease disclosure report and the consolidated technical memo, as PDF, Word and Excel. "
    "The lease inputs are on the Leases pages; approvals and the audit log are under Workflow."
)
show_flash()

with get_session() as session:
    leases = get_dashboard_leases(session, user["user_id"])
calculated = [lease for lease in leases if lease["has_results"]]
if not calculated:
    st.info("There are no calculated leases yet. Add a lease (upload, bulk upload or manual entry) and it will be available here.")
    st.stop()

# ------------------------------- the choices -------------------------------- #
first, second, third = st.columns(3)
framework_label = first.radio("Framework", list(FRAMEWORK_KEYS), horizontal=True, key="rep_framework")
framework = FRAMEWORK_KEYS[framework_label]
options = dash.currency_options(calculated)
codes = [code for code, _ in options]
counts = dict(options)
default_index = codes.index(dash.default_currency(options, user.get("default_currency", "INR")))
currency = second.selectbox(
    "Currency",
    codes,
    index=default_index,
    format_func=lambda code: "{}  ({} lease{})".format(currency_label(code), counts[code], "" if counts[code] == 1 else "s"),
    key="rep_currency",
    help="Amounts are never added across currencies: produce one report per currency.",
)
as_at = third.date_input(
    "Reporting date (as at)", value=date.today(), key="rep_as_at",
    help="Balances are month-end balances of the month you pick; movements cover the 12 months ending then.",
)
scope_label = st.radio("Leases in scope", list(STATUS_CHOICES), horizontal=True, key="rep_scope")
statuses = STATUS_CHOICES[scope_label]
in_scope = [l for l in calculated if (l["currency"] or "INR") == currency and l["status"] in statuses]
labels = {l["case_id"]: "{} - {} / {}".format(l["lease_ref"], l["lessor"] or "-", l["lessee"] or "-") for l in in_scope}
chosen = st.multiselect("Leases included", list(labels), default=list(labels), format_func=labels.get, placeholder="Choose leases")
include_memo = st.checkbox("Include the consolidated technical memo", value=True, key="rep_memo")
st.caption(
    "Number format: {} (change it on the Settings page). The memo uses each lease's latest saved memo, or is generated from "
    "its calculation results when none has been saved.".format(NUMBER_FORMATS.get(user.get("number_format", "indian")))
)
if not in_scope:
    st.warning("No {} leases in {} match this scope yet. Choose the other scope, or another currency.".format(framework_label, currency))

# -------------------------------- generating -------------------------------- #
if st.button("Generate reports", key="rep_generate", type="primary", disabled=not chosen):
    with st.spinner("Building the report..."):
        with get_session() as session:
            inputs = get_report_inputs(session, user["user_id"], framework, currency, statuses, chosen, include_memo)
        report = build_disclosure_report(
            inputs, framework, as_at, currency, user.get("number_format", "indian"), scope_label, user["name"], datetime.now(), include_memo
        )
        st.session_state["report_bundle"] = {
            "pdf": build_report_pdf(report),
            "docx": build_report_docx(report),
            "xlsx": build_report_excel(report),
            "names": (report_pdf_name(report), report_docx_name(report), report_excel_name(report)),
            "title": report["title"],
            "as_at_label": report["as_at_label"],
            "currency": currency,
            "style": user.get("number_format", "indian"),
            "leases": report["leases_included"],
            "not_commenced": report["not_commenced"],
            "liability": report["liability_at"],
            "checks": (report["checks_passed"], len(report["checks"])),
            "memo": report["memo"],
            "sections": [section["title"] for section in report["sections"]],
        }

bundle = st.session_state.get("report_bundle")
if bundle:
    st.divider()
    st.subheader("{} - as at {}".format(bundle["title"], bundle["as_at_label"]))
    passed, total = bundle["checks"]
    metrics = st.columns(4)
    metrics[0].metric("Leases included", bundle["leases"])
    metrics[1].metric("Lease liability at the date", format_money(bundle["liability"], bundle["currency"], bundle["style"]))
    metrics[2].metric("Reconciliation checks", "{} of {} passed".format(passed, total))
    metrics[3].metric("Memos", "{} saved, {} generated".format(bundle["memo"]["saved"], bundle["memo"]["generated"]))
    if passed != total:
        st.error("Some reconciliation checks did not pass. Open the report's 'Reconciliation checks' section before relying on it.")
    if bundle["not_commenced"]:
        st.info("{} lease{} had not commenced by this date and {} left out.".format(bundle["not_commenced"], "" if bundle["not_commenced"] == 1 else "s", "is" if bundle["not_commenced"] == 1 else "are"))
    pdf_name, docx_name, xlsx_name = bundle["names"]
    pdf_column, word_column, excel_column = st.columns(3)
    pdf_column.download_button("Download PDF", bundle["pdf"], pdf_name, "application/pdf", key="rep_dl_pdf", icon=":material/picture_as_pdf:")
    word_column.download_button(
        "Download Word", bundle["docx"], docx_name,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="rep_dl_docx", icon=":material/description:",
    )
    excel_column.download_button(
        "Download Excel", bundle["xlsx"], xlsx_name,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="rep_dl_xlsx", icon=":material/table_view:",
    )
    with st.expander("What is in the report"):
        for title in bundle["sections"]:
            st.markdown("- {}".format(title))
