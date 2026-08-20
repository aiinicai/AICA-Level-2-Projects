from __future__ import annotations

import hashlib
import pandas as pd
import streamlit as st
import altair as alt

from analyzer import StatementError, apply_transaction_changes, calculate_metrics, parse_statement, remap_name_selection, rename_counterparties, summarize_names
from exporter import build_excel


@st.cache_data(max_entries=20, show_spinner=False)
def make_excel_report(data: pd.DataFrame, source_name: str, warnings: list[str]) -> bytes:
    """Build a reusable Excel report for the exact current transaction state."""
    return build_excel(data, source_name, warnings)


st.set_page_config(page_title="Bank statement analyzer", page_icon=":material/account_balance:", layout="wide")
st.title(":material/account_balance: Bank statement analyzer")
st.caption("Version 1.6.1 - compatible live Excel name summary")
st.caption("Upload a bank statement, review intelligent counterparty extraction, explore cash flow, and export an audit-ready Excel workbook.")

st.session_state.setdefault("parsed_key", None)
st.session_state.setdefault("transactions", None)
st.session_state.setdefault("warnings", [])
st.session_state.setdefault("name_edit_revision", 0)
st.session_state.setdefault("counterparty_filter_default", None)
st.session_state.setdefault("pending_counterparty_selection", None)
st.session_state.setdefault("name_change_message", None)
st.session_state.setdefault("transaction_change_message", None)
st.session_state.setdefault("last_transaction_update", None)

with st.container(border=True):
    uploaded = st.file_uploader("Bank statement", type=["pdf", "xlsx", "xls", "xlsm"], help="Text-based PDFs and Excel bank statements up to 200 MB are supported.")
    st.caption("Your statement is processed locally in this app. Password-protected and scanned/image-only PDFs must first be unlocked or OCR-converted.")

if uploaded is None:
    st.info("Upload a PDF or Excel bank statement to begin.", icon=":material/upload_file:")
    with st.expander("What the analysis includes"):
        st.markdown("Opening and closing balances, deposits, withdrawals, net movement, date and channel trends, counterparty-wise summaries, editable transaction review, reconciliation checks, and multi-sheet Excel export.")
    st.stop()

content = uploaded.getvalue()
file_key = hashlib.sha256(content).hexdigest()
if st.session_state.parsed_key != file_key:
    try:
        with st.status("Reading and interpreting statement…", expanded=True) as status:
            parsed = parse_statement(content, uploaded.name)
            st.write(f"Detected {len(parsed.transactions):,} transactions from {parsed.source_type}.")
            st.session_state.transactions = parsed.transactions
            st.session_state.warnings = parsed.warnings
            st.session_state.parsed_key = file_key
            st.session_state.name_edit_revision = 0
            st.session_state.counterparty_filter_default = None
            st.session_state.pending_counterparty_selection = None
            st.session_state.name_change_message = None
            st.session_state.transaction_change_message = None
            st.session_state.last_transaction_update = None
            status.update(label="Statement analysis ready", state="complete", expanded=False)
    except StatementError as exc:
        st.error(str(exc), icon=":material/error:")
        st.stop()
    except Exception as exc:
        st.error(f"Unexpected parsing error: {exc}", icon=":material/error:")
        st.stop()

base = st.session_state.transactions.copy()
with st.sidebar:
    st.header("Filters")
    min_date, max_date = base["Date"].min().date(), base["Date"].max().date()
    selected_dates = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    channels = st.multiselect("Channels", sorted(base["Channel"].unique()), default=sorted(base["Channel"].unique()))
    available_names = sorted(base["Counterparty"].dropna().astype(str).unique(), key=str.casefold)
    pending_names = st.session_state.pending_counterparty_selection
    saved_names = st.session_state.counterparty_filter_default
    if pending_names is not None:
        default_names = [name for name in pending_names if name in available_names]
        st.session_state.counterparty_filter_default = default_names
        st.session_state.pending_counterparty_selection = None
    elif saved_names is None:
        default_names = available_names
    else:
        default_names = [name for name in saved_names if name in available_names]
    selected_names = st.multiselect(
        "Counterparties for summary",
        available_names,
        default=default_names,
        key=f"counterparty_filter_{file_key}_{st.session_state.name_edit_revision}",
        help="Select one or more names. The dashboard, name summary and filtered Excel export will use only these counterparties.",
    )
    st.session_state.counterparty_filter_default = selected_names
    search = st.text_input("Search narration or name", placeholder="e.g. ABC Traders")
    st.caption(f"Source: {uploaded.name}")

if len(selected_dates) == 2:
    start, end = pd.Timestamp(selected_dates[0]), pd.Timestamp(selected_dates[1])
else:
    start = end = pd.Timestamp(selected_dates[0])
mask = base["Date"].between(start, end) & base["Channel"].isin(channels) & base["Counterparty"].isin(selected_names)
if search:
    mask &= base["Narration"].str.contains(search, case=False, na=False) | base["Counterparty"].str.contains(search, case=False, na=False)
filtered = base.loc[mask].copy()

for warning in st.session_state.warnings:
    st.warning(warning, icon=":material/warning:")

metrics = calculate_metrics(filtered) if len(filtered) else {k: None for k in ["Opening Balance", "Closing Balance", "Total Deposits", "Total Withdrawals", "Net Movement", "Transactions", "Reconciliation Variance"]}
currency = lambda x: "—" if x is None or pd.isna(x) else f"{x:,.2f}"
with st.container(horizontal=True):
    st.metric("Opening balance", currency(metrics["Opening Balance"]), border=True)
    st.metric("Closing balance", currency(metrics["Closing Balance"]), border=True)
    st.metric("Total deposits", currency(metrics["Total Deposits"]), border=True)
    st.metric("Total withdrawals", currency(metrics["Total Withdrawals"]), border=True)
    st.metric("Net movement", currency(metrics["Net Movement"]), border=True)

overview_tab, names_tab, transactions_tab, quality_tab = st.tabs(["Overview", "Name summary", "Transactions", "Quality checks"])
with overview_tab:
    if filtered.empty:
        st.info("No transactions match the selected filters.")
    else:
        monthly = filtered.assign(Month=filtered["Date"].dt.to_period("M").dt.to_timestamp()).groupby("Month", as_index=False)[["Deposit", "Withdrawal"]].sum()
        flow = monthly.melt("Month", var_name="Flow", value_name="Amount")
        chart = alt.Chart(flow).mark_bar().encode(x=alt.X("Month:T", title="Month"), y=alt.Y("Amount:Q", title="Amount"), color=alt.Color("Flow:N", scale=alt.Scale(domain=["Deposit", "Withdrawal"], range=["#0F766E", "#D97706"])), tooltip=["Month:T", "Flow:N", alt.Tooltip("Amount:Q", format=",.2f")]).properties(height=330)
        left, right = st.columns(2)
        with left.container(border=True):
            st.subheader("Monthly cash flow")
            st.altair_chart(chart)
        with right.container(border=True):
            st.subheader("Running balance")
            balance_data = filtered.dropna(subset=["Balance"]).sort_values("Date")
            st.line_chart(balance_data, x="Date", y="Balance", color="#17324D")
        with st.container(border=True):
            st.subheader("Largest transactions")
            largest = filtered.assign(Amount=filtered[["Deposit", "Withdrawal"]].max(axis=1)).nlargest(10, "Amount")
            st.dataframe(largest[["Date", "Counterparty", "Channel", "Deposit", "Withdrawal", "Narration"]], hide_index=True, column_config={"Date": st.column_config.DateColumn(format="DD-MMM-YYYY"), "Deposit": st.column_config.NumberColumn(format="localized"), "Withdrawal": st.column_config.NumberColumn(format="localized")})

with names_tab:
    if st.session_state.name_change_message:
        st.success(st.session_state.name_change_message, icon=":material/check_circle:")
        st.session_state.name_change_message = None
    with st.container(border=True):
        st.subheader("Change or merge a name")
        st.caption("Select the existing name, type the corrected name, then click the blue button below.")
        with st.form(f"quick_name_form_{file_key}_{st.session_state.name_edit_revision}"):
            quick_sources = st.multiselect(
                "Existing name(s)",
                sorted(base["Counterparty"].dropna().astype(str).unique(), key=str.casefold),
                help="Select one name to rename, or several name variants to merge.",
            )
            quick_target = st.text_input("Correct/new name", placeholder="e.g. Deepak Singh")
            apply_quick_change = st.form_submit_button(
                "APPLY NAME CHANGE",
                type="primary",
                icon=":material/save:",
                width="stretch",
            )
        if apply_quick_change:
            target = " ".join(quick_target.split()).strip()
            if not quick_sources:
                st.warning("Select at least one existing name.")
            elif not target:
                st.warning("Enter the correct/new name.")
            else:
                quick_mapping = {name: target for name in quick_sources}
                updated = rename_counterparties(base, quick_mapping)
                updated_names = sorted(updated["Counterparty"].dropna().astype(str).unique(), key=str.casefold)
                st.session_state.transactions = updated
                next_selection = remap_name_selection(selected_names, quick_mapping, updated_names)
                if target in updated_names and target not in next_selection:
                    next_selection.append(target)
                st.session_state.pending_counterparty_selection = next_selection
                st.session_state.name_change_message = f"Renamed/merged {len(quick_sources)} name(s) as {target}. The filter and Name Summary have been refreshed."
                st.session_state.name_edit_revision += 1
                st.rerun()
    summary_scope = st.segmented_control(
        "Name summary scope",
        ["All transactions", "Current dashboard filters"],
        default="All transactions",
        key=f"name_summary_scope_{file_key}",
        help="All transactions always shows every saved name. Current dashboard filters follows the sidebar filters.",
    )
    summary_data = base if summary_scope == "All transactions" else filtered
    summary = summarize_names(summary_data) if len(summary_data) else pd.DataFrame()
    st.subheader("Counterparty-wise deposit and withdrawal summary")
    st.caption(f"Summary contains {len(summary):,} counterparties and {len(summary_data):,} transactions from: {summary_scope}.")
    if st.session_state.last_transaction_update:
        st.info(st.session_state.last_transaction_update, icon=":material/sync:")
    st.dataframe(summary, hide_index=True, column_config={"Total_Deposits": st.column_config.NumberColumn("Total deposits", format="localized"), "Total_Withdrawals": st.column_config.NumberColumn("Total withdrawals", format="localized"), "Net_Amount": st.column_config.NumberColumn("Net amount", format="localized"), "Last_Transaction": st.column_config.DateColumn("Last transaction", format="DD-MMM-YYYY")})
    with st.expander("Advanced bulk name editor", icon=":material/edit:"):
        st.markdown("**Bulk editor**")
        st.caption("Edit ‘New name’ and apply. Every transaction with the old name will be updated; using the same new name merges multiple names in the summary.")
        full_summary = summarize_names(base)
        name_editor_source = pd.DataFrame({
            "Current name": full_summary["Counterparty"],
            "New name": full_summary["Counterparty"],
            "Transactions": full_summary["Total_Transactions"],
        })
        renamed = st.data_editor(
            name_editor_source,
            key=f"name_mapping_editor_{file_key}_{st.session_state.name_edit_revision}",
            hide_index=True,
            disabled=["Current name", "Transactions"],
            column_config={
                "Current name": st.column_config.TextColumn(pinned=True),
                "New name": st.column_config.TextColumn(help="Type the corrected or consolidated name."),
                "Transactions": st.column_config.NumberColumn(format="localized"),
            },
        )
        if st.button("Apply summary name changes", type="primary", icon=":material/save:"):
            changes = {
                str(row["Current name"]): str(row["New name"]).strip()
                for _, row in renamed.iterrows()
                if str(row["New name"]).strip() and str(row["Current name"]).strip() != str(row["New name"]).strip()
            }
            if changes:
                updated = rename_counterparties(base, changes)
                updated_names = sorted(updated["Counterparty"].dropna().astype(str).unique(), key=str.casefold)
                st.session_state.transactions = updated
                next_selection = remap_name_selection(selected_names, changes, updated_names)
                for target in changes.values():
                    target = " ".join(str(target).split()).strip()
                    if target in updated_names and target not in next_selection:
                        next_selection.append(target)
                st.session_state.pending_counterparty_selection = next_selection
                st.session_state.name_change_message = f"Applied {len(changes)} name change(s). The filter and Name Summary have been refreshed."
                st.session_state.name_edit_revision += 1
                st.rerun()
            else:
                st.info("No name changes were entered.")

with transactions_tab:
    if st.session_state.transaction_change_message:
        st.success(st.session_state.transaction_change_message, icon=":material/check_circle:")
        st.session_state.transaction_change_message = None
    st.subheader("Review and correct transactions")
    st.caption("Show all transactions or filter the list by one counterparty. Edit only the required row; other transactions will not be renamed.")
    transaction_names = sorted(base["Counterparty"].dropna().astype(str).unique(), key=str.casefold)
    transaction_filter = st.selectbox(
        "Show transactions for",
        ["All counterparties", *transaction_names],
        key=f"transaction_counterparty_filter_{file_key}_{st.session_state.name_edit_revision}",
        help="Choose All counterparties for the complete transaction list, or select one name for a name-wise list.",
    )
    if transaction_filter == "All counterparties":
        transaction_view = base
    else:
        transaction_view = base.loc[base["Counterparty"].astype(str).eq(transaction_filter)]
    editable = transaction_view[
        ["Row", "Date", "Narration", "Counterparty", "Channel", "Withdrawal", "Deposit", "Balance", "Reference"]
    ].copy()
    st.caption(f"Showing {len(editable):,} transaction(s) for: {transaction_filter}.")
    edited = st.data_editor(
        editable,
        key=f"transaction_editor_{file_key}_{st.session_state.name_edit_revision}_{transaction_filter}",
        hide_index=True,
        disabled=["Row", "Date", "Narration", "Withdrawal", "Deposit", "Balance", "Reference"],
        column_config={
            "Row": st.column_config.NumberColumn("Row ID", pinned=True),
            "Date": st.column_config.DateColumn(format="DD-MMM-YYYY"),
            "Counterparty": st.column_config.TextColumn("Counterparty (editable)", pinned=True, help="Change the name only on the required transaction row."),
            "Withdrawal": st.column_config.NumberColumn(format="localized"),
            "Deposit": st.column_config.NumberColumn(format="localized"),
            "Balance": st.column_config.NumberColumn(format="localized"),
            "Channel": st.column_config.SelectboxColumn(options=["UPI", "NEFT", "RTGS", "IMPS", "Cheque", "Card/POS", "ATM", "Cash", "Interest", "Charges", "Other"]),
        },
    )
    if st.button("Apply transaction changes", type="primary", icon=":material/save:", width="stretch"):
        try:
            updated, changed_rows, changed_names = apply_transaction_changes(base, edited)
        except StatementError as exc:
            st.warning(str(exc))
        else:
            if not changed_rows:
                st.info("No transaction changes were entered.")
                st.stop()
            updated_names = sorted(updated["Counterparty"].dropna().astype(str).unique(), key=str.casefold)
            st.session_state.transactions = updated
            st.session_state.pending_counterparty_selection = updated_names
            changed_name_text = ", ".join(changed_names)
            st.session_state.last_transaction_update = f"Last update: {len(changed_rows)} transaction(s) changed to {changed_name_text}."
            st.session_state.name_change_message = f"Updated {len(changed_rows)} individual transaction(s). Name Summary now includes: {changed_name_text}."
            st.session_state.transaction_change_message = f"Applied changes to {len(changed_rows)} transaction(s). The Name Summary and Excel analysis are synchronized."
            st.session_state.name_edit_revision += 1
            st.rerun()

    with st.container(border=True):
        st.subheader("Download the current corrected report")
        st.caption("The downloaded Excel report is live and Excel 2010+ compatible: edit the yellow Counterparty column and Name Summary updates automatically.")
        transaction_excel_bytes = make_excel_report(base, uploaded.name, st.session_state.warnings)
        transaction_report_name = f"{uploaded.name.rsplit('.', 1)[0]}_analysis_revision_{st.session_state.name_edit_revision}.xlsx"
        st.download_button(
            "Download live editable Excel report",
            data=transaction_excel_bytes,
            file_name=transaction_report_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            icon=":material/download:",
            width="stretch",
            key=f"transaction_excel_download_{file_key}_{st.session_state.name_edit_revision}",
        )
        st.caption(f"Current app revision: {st.session_state.name_edit_revision}. After download, Excel name changes recalculate inside the workbook—no app re-download is required.")

with quality_tab:
    variance = metrics["Reconciliation Variance"]
    if variance is not None and abs(variance) <= 0.02:
        st.success("Opening balance + deposits - withdrawals matches the closing balance.", icon=":material/check_circle:")
    elif variance is not None:
        st.warning(f"Reconciliation variance: {variance:,.2f}. Review missing rows, duplicated rows, or debit/credit mapping.", icon=":material/warning:")
    else:
        st.info("A reconciliation variance cannot be calculated because running balances are unavailable.")
    unidentified = int((base["Counterparty"] == "Unidentified").sum())
    st.metric("Unidentified counterparties", f"{unidentified:,}", border=True)
    st.dataframe(pd.DataFrame({"Check": ["Transactions parsed", "Rows with balance", "Rows with extracted name", "Reconciliation variance"], "Result": [len(base), int(base["Balance"].notna().sum()), len(base) - unidentified, variance]}), hide_index=True)

export_scope = st.segmented_control(
    "Excel export scope",
    ["All transactions", "Current filters"],
    default="All transactions",
    help="Current filters includes the selected date range, channels, counterparties and search text.",
)
export_data = st.session_state.transactions if export_scope == "All transactions" else filtered
excel_bytes = make_excel_report(export_data, uploaded.name, st.session_state.warnings) if len(export_data) else None
st.download_button(
    "Download live editable Excel analysis",
    data=excel_bytes or b"",
    file_name=f"{uploaded.name.rsplit('.', 1)[0]}_analysis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
    icon=":material/download:",
    disabled=excel_bytes is None,
)
