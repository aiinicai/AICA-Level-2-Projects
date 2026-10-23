"""Audit Support Tool – Stage 2. Runs locally through Streamlit."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis import (flag_variances, group_summary, indian_amount, monthly_trend, party_table,
                      top_ledgers_chart, trend_chart, variance_analysis, voucher_mix_chart,
                      test_round_amounts, test_dates, test_narrations, test_thresholds, test_benford, test_outliers)
from loaders import (DAYBOOK_DEFAULTS, TB_DEFAULTS, combine_uploads, excel_sheets_and_headers,
                     load_saved_mapping, normalise_daybook, normalise_tb, read_excel, save_mapping,
                     validation_checks, validation_exceptions, classify_group)
from sampling import (simple_random_sample, select_key_items, stratified_sample, monetary_unit_sample)
from exports import create_working_paper

st.set_page_config(page_title="Audit Support Tool", page_icon="✅", layout="wide")
st.markdown("""<style>
    .stApp {background: #f6fbfa;} [data-testid='stSidebar'] {background: linear-gradient(180deg,#073b4c,#007f75);}
    [data-testid='stSidebar'] * {color: white;} h1,h2,h3 {color:#075e54;} .stButton>button {background:#008f7a;color:white;border:0;}
</style>""", unsafe_allow_html=True)

if "daybook" not in st.session_state: st.session_state.daybook = None
if "tb_current" not in st.session_state: st.session_state.tb_current = None
if "tb_previous" not in st.session_state: st.session_state.tb_previous = None
if "working_sample" not in st.session_state: st.session_state.working_sample = pd.DataFrame()
if "sample_params" not in st.session_state: st.session_state.sample_params = []
if "exceptions" not in st.session_state: st.session_state.exceptions = pd.DataFrame()

st.sidebar.title("✅ Audit Support")
page = st.sidebar.radio("Navigate", ["Home", "1) Upload & Validate", "2) Comparative Dashboard", "3) Exception Tests", "4) Sampling", "5) Export"])
st.sidebar.caption("Stage 1: Upload, validation, dashboard and reproducible random sampling.")


def map_columns(raw: pd.DataFrame, defaults: dict, prefix: str) -> dict:
    saved = load_saved_mapping().get(prefix, defaults)
    options = [""] + list(raw.columns)
    mapping = {}
    for key, default in defaults.items():
        preferred = saved.get(key, default)
        index = options.index(preferred) if preferred in options else 0
        mapping[key] = st.selectbox(key.replace("_", " ").title(), options, index=index, key=f"{prefix}_{key}")
    return mapping


def uploader(label, key):
    return st.file_uploader(label, type=["xlsx", "xls"], accept_multiple_files=True, key=key)

if page == "Home":
    st.title("Audit Support Tool")
    st.subheader("A local tool for SAP Day Book and Trial Balance audit analysis")
    st.success("Your files stay on your Windows computer. The app has no cloud storage or external upload feature.")
    st.markdown("""**Stage 1 is ready to test:**
1. Upload SAP Day Book and Trial Balance Excel files.
2. Confirm the column mapping once; it is saved in a small file next to the app on your PC.
3. Review plain-language validation checks and use the comparative dashboard.
4. Create a reproducible simple-random sample using a fixed seed.

Use the sidebar to begin with **Upload & Validate**. To try the app without client data, run `py generate_dummy_data.py` in the app folder first.""")

elif page == "1) Upload & Validate":
    st.title("Upload & Validate")
    st.info("Upload only Excel files stored on this computer. You can upload more than one Day Book file if all files use the same layout.")
    fy_label = st.text_input("Financial year / period label", "FY 2025-26")
    c1, c2 = st.columns(2)
    with c1: fy_start = st.date_input("Selected period starts", value=pd.Timestamp("2025-04-01"))
    with c2: fy_end = st.date_input("Selected period ends", value=pd.Timestamp("2026-03-31"))
    db_files = uploader("Day Book file(s)", "db_upload")
    current_files = uploader("Current-period Trial Balance file(s)", "current_tb_upload")
    previous_files = uploader("Previous-period Trial Balance file(s) – optional for comparison", "previous_tb_upload")

    if db_files:
        try:
            sheets, headers = excel_sheets_and_headers(db_files[0])
            dc1, dc2 = st.columns(2)
            with dc1: db_sheet = st.selectbox("Day Book sheet", sheets, key="db_sheet")
            with dc2: db_header = st.selectbox("Day Book header row (Excel row)", headers[db_sheet], format_func=lambda x: str(x + 1), key="db_header")
            raw_db = read_excel(db_files[0], db_sheet, db_header)
            with st.expander("Map Day Book columns (required before processing)", expanded=True):
                st.caption("Your SAP sample is detected as Amount + Debit/Credit indicator. For a simple export, leave Amount blank and map Debit and Credit instead.")
                db_map = map_columns(raw_db, DAYBOOK_DEFAULTS, "daybook")
            if current_files:
                tb_sheets, tb_headers = excel_sheets_and_headers(current_files[0])
                tc1, tc2 = st.columns(2)
                with tc1: tb_sheet = st.selectbox("Current TB sheet", tb_sheets, key="tb_sheet")
                with tc2: tb_header = st.selectbox("Current TB header row (Excel row)", tb_headers[tb_sheet], format_func=lambda x: str(x + 1), key="tb_header")
                raw_tb = read_excel(current_files[0], tb_sheet, tb_header)
                with st.expander("Map Trial Balance columns", expanded=True):
                    tb_map = map_columns(raw_tb, TB_DEFAULTS, "tb")
            else:
                tb_map, tb_sheet, tb_header = TB_DEFAULTS.copy(), "", 0
            if st.button("Process files and run validation", type="primary"):
                if not db_map["date"] or not db_map["ledger"]:
                    st.error("Please map at least Date and Ledger for the Day Book.")
                else:
                    with st.spinner("Reading and checking the files locally..."):
                        st.session_state.daybook = combine_uploads(db_files, normalise_daybook, db_map, db_sheet, db_header)
                        st.session_state.tb_current = combine_uploads(current_files, normalise_tb, tb_map, tb_sheet, tb_header) if current_files else None
                        # Previous TB follows its first detected header automatically. For unusual layout, upload it as current TB once to map it.
                        if previous_files:
                            ps, ph = excel_sheets_and_headers(previous_files[0]); prev_sheet, prev_header = ps[0], ph[ps[0]][0]
                            st.session_state.tb_previous = combine_uploads(previous_files, normalise_tb, tb_map, prev_sheet, prev_header)
                        save_mapping(db_map, tb_map)
                        st.session_state.fy_start, st.session_state.fy_end, st.session_state.fy_label = pd.Timestamp(fy_start), pd.Timestamp(fy_end), fy_label
                    st.success(f"Processed {len(st.session_state.daybook):,} Day Book lines. Mapping saved on this computer.")
        except Exception as error:
            st.error(f"The file could not be processed: {error}. Check the selected sheet, header row and column mapping.")
    if st.session_state.daybook is not None:
        db, tb = st.session_state.daybook, st.session_state.tb_current
        st.subheader("Validation summary")
        checks = validation_checks(db, tb, st.session_state.fy_start, st.session_state.fy_end)
        st.dataframe(checks, use_container_width=True, hide_index=True)
        exceptions = validation_exceptions(db, st.session_state.fy_start, st.session_state.fy_end)
        if not exceptions.empty:
            st.warning(f"{len(exceptions):,} validation exception row(s) found.")
            st.dataframe(exceptions, use_container_width=True, hide_index=True)
        else: st.success("No date or duplicate-line exceptions were found by the Stage 1 checks.")
        with st.expander("Preview standardised Day Book"):
            st.dataframe(db.head(100), use_container_width=True, hide_index=True)

elif page == "2) Comparative Dashboard":
    st.title("Comparative Dashboard")
    if st.session_state.daybook is None:
        st.warning("First go to Upload & Validate and process a Day Book.")
    else:
        db = st.session_state.daybook
        unit = st.radio("Display amounts as", ["₹", "₹ lakh", "₹ crore"], horizontal=True)
        a, b, c = st.columns(3)
        a.metric("Day Book debit", indian_amount(db["Debit"].sum(), unit))
        b.metric("Day Book credit", indian_amount(db["Credit"].sum(), unit))
        c.metric("Journal lines", f"{len(db):,}")
        st.subheader("Transaction activity")
        ledgers = sorted(db["Ledger"].dropna().unique().tolist())
        selected = st.multiselect("Select ledgers for month-wise trend", ledgers, default=ledgers[:min(4, len(ledgers))])
        if selected: st.plotly_chart(trend_chart(monthly_trend(db, selected)), use_container_width=True)
        x, y = st.columns(2)
        with x: st.plotly_chart(top_ledgers_chart(db, st.selectbox("Top ledgers", [10, 20], index=0)), use_container_width=True)
        with y: st.plotly_chart(voucher_mix_chart(db), use_container_width=True)
        st.subheader("Top parties")
        st.dataframe(party_table(db, 20), use_container_width=True, hide_index=True)
        if st.session_state.tb_current is not None:
            st.subheader("Group-level Trial Balance view")
            st.caption("Group is automatically classified from SAP G/L code range: 1 assets, 2 liabilities, 3 equity, 4 income, 5–6 expenses. Editing will be added in the next stage.")
            st.dataframe(group_summary(st.session_state.tb_current), use_container_width=True, hide_index=True)
        if st.session_state.tb_current is not None and st.session_state.tb_previous is not None:
            st.subheader("Current period vs previous period Trial Balance movement")
            st.caption("The uploaded periods are compared as-is; the tool does not annualise a shorter period.")
            p1, p2 = st.columns(2)
            with p1: pct = st.number_input("Variance percentage threshold", value=20.0, min_value=0.0)
            with p2: amt = st.number_input("Variance amount threshold (₹)", value=100000.0, min_value=0.0, step=10000.0)
            variance = flag_variances(variance_analysis(st.session_state.tb_current, st.session_state.tb_previous), pct, amt)
            st.dataframe(variance, use_container_width=True, hide_index=True)
        else:
            st.info("Upload both current and previous-period TB files to see variance analysis.")

elif page == "3) Exception Tests":
    st.title("Exception & Risk Indicators")
    if st.session_state.daybook is None:
        st.warning("First upload and process a Day Book.")
    else:
        db = st.session_state.daybook
        st.info("Select risk tests to run on the Day Book lines. Results are added to a combined exceptions table.")
        
        with st.expander("Configure Test Parameters", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1: 
                round_t = st.multiselect("Round amount multiples", [1000, 10000, 100000], default=[10000, 100000])
                keywords = st.text_input("Narration keywords (comma separated)", "adjustment, reversal, loan, director, personal")
            with c2:
                cash_lim = st.number_input("Cash limit (per transaction)", value=10000)
                audit_lim = st.number_input("Audit threshold (e.g. for 'just-below')", value=200000)
            with c3:
                st.write("Date tests included: weekends and last 5 days of month/quarter.")

        if st.button("Run all selected tests", type="primary"):
            with st.spinner("Running tests..."):
                ex_list = []
                ex_list.append(test_round_amounts(db, round_t))
                ex_list.append(test_dates(db))
                ex_list.append(test_narrations(db, [k.strip() for k in keywords.split(",")]))
                ex_list.append(test_thresholds(db, cash_lim, audit_lim))
                ex_list.append(test_outliers(db))
                
                # Preserve every test label for a Row ID instead of silently keeping
                # only whichever test happened to be concatenated first.
                nonempty = [frame for frame in ex_list if frame is not None and not frame.empty]
                if nonempty:
                    combined = pd.concat(nonempty, ignore_index=True, sort=False)
                    if "Row ID" in combined.columns:
                        exception_labels = (
                            combined.dropna(subset=["Exception"])
                            .groupby("Row ID")["Exception"]
                            .agg(lambda values: "; ".join(
                                dict.fromkeys(str(v) for v in values if str(v).strip())
                            ))
                        )
                        combined = combined.drop_duplicates(subset=["Row ID"]).set_index("Row ID")
                        combined["Exception"] = exception_labels.reindex(combined.index).fillna("")
                        combined = combined.reset_index()
                    combined = combined.sort_values("Amount", ascending=False)
                else:
                    combined = pd.DataFrame()
                st.session_state.exceptions = combined
                st.success(f"Tests complete. Found {len(combined):,} flags.")

        if not st.session_state.exceptions.empty:
            st.subheader("Combined Exception Table")
            st.dataframe(st.session_state.exceptions, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("Statistical Analysis")
            digits, fig = test_benford(db)
            st.plotly_chart(fig, use_container_width=True)

elif page == "4) Sampling":
    st.title("Audit Sample Selection")
    if st.session_state.daybook is None:
        st.warning("First upload and process a Day Book.")
    else:
        db = st.session_state.daybook
        st.write(f"Total lines available: **{len(db):,}** | Total value: **{indian_amount(db['Amount'].sum())}**")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Key Items", "Random", "Stratified", "MUS", "Risk-Based"])
        
        with tab1:
            st.subheader("High Value / Key Items")
            k_amt = st.number_input("Select all items above ₹", value=100000, step=10000)
            if st.button("Select Key Items"):
                s, p, n = select_key_items(db, k_amt)
                st.session_state.working_sample = pd.concat([st.session_state.working_sample, s]).drop_duplicates(subset=["Row ID"])
                st.session_state.sample_params.append(p)
                st.success(n)

        with tab2:
            st.subheader("Simple Random Sampling")
            r_size = st.number_input("Sample size", value=25, key="rs_size")
            r_seed = st.number_input("Seed", value=1234, key="rs_seed")
            if st.button("Select Random Sample"):
                s, p, n = simple_random_sample(db, r_size, r_seed)
                st.session_state.working_sample = pd.concat([st.session_state.working_sample, s]).drop_duplicates(subset=["Row ID"])
                st.session_state.sample_params.append(p)
                st.success(n)

        with tab3:
            st.subheader("Stratified Sampling")
            s_bands = st.text_input("Bands (comma separated)", "10000, 50000, 100000")
            s_n = st.number_input("Items per band", value=5)
            if st.button("Select Stratified Sample"):
                bands = [float(x.strip()) for x in s_bands.split(",")]
                s, p, n = stratified_sample(db, bands, s_n, 1234)
                st.session_state.working_sample = pd.concat([st.session_state.working_sample, s]).drop_duplicates(subset=["Row ID"])
                st.session_state.sample_params.append(p)
                st.success(n)

        with tab4:
            st.subheader("Monetary Unit Sampling (MUS)")
            st.info("MUS focuses on higher-value items. It calculates a sampling interval based on risk.")
            m_tm = st.number_input("Tolerable Misstatement", value=min(500000.0, db["Amount"].sum()*0.05))
            m_conf = st.selectbox("Confidence Level", [0.80, 0.90, 0.95], index=2)
            m_em = st.number_input("Expected Misstatement", value=0.0)
            if st.button("Select MUS Sample"):
                s, p, n = monetary_unit_sample(db, m_tm, m_conf, m_em)
                st.session_state.working_sample = pd.concat([st.session_state.working_sample, s]).drop_duplicates(subset=["Row ID"])
                st.session_state.sample_params.append(p)
                st.success(n)
                
        with tab5:
            st.subheader("Judgmental / Risk-Based")
            if st.session_state.exceptions.empty:
                st.warning("Run tests in 'Exception Tests' page first to select items here.")
            else:
                st.write(f"Available exceptions: {len(st.session_state.exceptions)}")
                if st.button("Select All Exceptions as Sample"):
                    s = st.session_state.exceptions.copy()
                    st.session_state.working_sample = pd.concat([st.session_state.working_sample, s]).drop_duplicates(subset=["Row ID"])
                    st.session_state.sample_params.append({"Method": "Judgmental (Risk-Based)", "Parameters": "All flags from Exception Tests", "Items": len(s), "Value": s["Amount"].sum()})
                    st.success("All flagged items added to working sample.")

        if not st.session_state.working_sample.empty:
            st.divider()
            st.subheader("Working Sample List")
            st.write(f"Total Unique Items: {len(st.session_state.working_sample)} | Total Value: {indian_amount(st.session_state.working_sample['Amount'].sum())}")
            st.dataframe(st.session_state.working_sample, use_container_width=True, hide_index=True)
            if st.button("Clear Working Sample"):
                st.session_state.working_sample = pd.DataFrame()
                st.session_state.sample_params = []
                st.rerun()

else:
    st.title("Export Working Papers")
    if st.session_state.daybook is None:
        st.warning("No data processed yet.")
    else:
        st.subheader("Final Documentation")
        st.markdown("""Download a professional multi-sheet Excel file containing:
- **Audit Summary**: Methods used, population totals, and sample coverage.
- **Selected Samples**: The final list of vouchers to test.
- **Exceptions**: Any flags raised during automated risk tests.
- **Variance**: Current vs previous Trial Balance movement analysis.
""")
        
        # Prepare Variance for export
        var_df = None
        if st.session_state.tb_current is not None and st.session_state.tb_previous is not None:
            var_df = variance_analysis(st.session_state.tb_current, st.session_state.tb_previous)

        excel_data = create_working_paper(
            st.session_state.daybook,
            None, # Summary text is handled by params
            st.session_state.exceptions,
            st.session_state.working_sample,
            var_df,
            st.session_state.sample_params
        )
        
        st.download_button(
            label="📥 Download Working Paper (Excel)",
            data=excel_data,
            file_name=f"Audit_Working_Paper_{st.session_state.get('fy_label', 'FY')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
