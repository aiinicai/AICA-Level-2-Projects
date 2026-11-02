"""Financial Reporting Review Assistant - Web Application.

A professional, browser-based web application for Chartered Accountants and FRRB experts.
Reviews draft and published financial statements, identifies potential non-compliances,
and generates audit-grade Excel reports with yellow cell highlighting.
"""

import gc
import html
import importlib
import os
import sys
import streamlit as st
import pandas as pd


def _refresh_core_modules() -> None:
    """Re-imports core modules whose source changed since they were loaded.

    Streamlit re-executes app.py after a redeploy but keeps already-imported modules in memory,
    so without this an updated core/*.py would not take effect until the app is rebooted.
    """
    order = ["core.knowledge_base", "core.fs_model", "core.review_engine", "core.ai_reviewer",
             "core.excel_generator", "core.fs_marker", "core.pdf_extractor", "core.applicability", "core.frrb_library"]
    for name in order:
        mod = sys.modules.get(name)
        path = getattr(mod, "__file__", None)
        if mod is None or not path or not os.path.exists(path):
            continue
        mtime = os.path.getmtime(path)
        if getattr(mod, "_source_mtime", None) != mtime:
            mod = importlib.reload(mod)
            mod._source_mtime = mtime


_refresh_core_modules()

from core.applicability import ApplicabilityEngine
from core.frrb_library import FRRBLibrary
from core.pdf_extractor import PDFExtractor
from core.excel_generator import ExcelReportGenerator
from core.fs_marker import DraftFSMarker
from core.fs_model import FSModel
from core.review_engine import ReviewEngine, NATURES
from core.ai_reviewer import AIReviewer


# Page configuration
st.set_page_config(
    page_title="Financial Reporting Review Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Chartered Accountant Executive UI
st.markdown("""
<style>
    .main-title {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #0B2F4C;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.1rem;
    }
    .sub-title {
        color: #5A6B7C;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #E2E8F0;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-num {
        font-size: 1.9rem;
        font-weight: bold;
        margin-bottom: 4px;
    }
    .metric-label {
        color: #64748B;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-high {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-med {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-low {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .correction-box {
        background-color: #FFFDE7;
        border-left: 4px solid #F59E0B;
        padding: 12px 16px;
        border-radius: 4px;
        margin-top: 8px;
        margin-bottom: 8px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "extracted_doc" not in st.session_state:
    st.session_state.extracted_doc = None
if "audit_results" not in st.session_state:
    st.session_state.audit_results = None
if "current_filename" not in st.session_state:
    st.session_state.current_filename = None


# -----------------------------------------------------------------------------
# SIDEBAR: Company Profile & Applicability Assessment
# -----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/scales--v1.png", width=64)
st.sidebar.markdown("### 🏢 Entity Applicability Profile")
st.sidebar.caption("Mandatory statutory configuration per Companies Act, 2013")

company_type = st.sidebar.selectbox(
    "Company Type",
    ["Public Company", "Private Company"],
    index=0
)

# Under Section 2(68) of Companies Act, 2013, a Private Company cannot be listed on equity exchanges.
if company_type == "Private Company":
    listing_status = "Unlisted"
    st.sidebar.selectbox(
        "Listing Status",
        ["Unlisted"],
        index=0,
        disabled=True,
        help="A Private Company cannot be listed per Section 2(68) of the Companies Act, 2013."
    )
else:
    listing_status = st.sidebar.selectbox(
        "Listing Status",
        ["Listed", "Unlisted"],
        index=0,
        help="Under Companies (Ind AS) Rules 2015, all listed companies must prepare financial statements under Ind AS."
    )

framework = st.sidebar.selectbox(
    "Financial Reporting Framework",
    ["Indian Accounting Standards (Ind AS)", "Accounting Standards (AS)"],
    index=0
)

schedule_iii_division = st.sidebar.selectbox(
    "Schedule III Division",
    ["Division II", "Division I", "Division III"],
    index=0,
    help="Division I: AS | Division II: Ind AS Non-NBFC | Division III: Ind AS NBFC"
)

financial_year = st.sidebar.selectbox(
    "Financial Year under Review",
    ["FY 2025-26", "FY 2024-25", "FY 2023-24", "FY 2022-23", "FY 2021-22"],
    index=0
)

statement_type = st.sidebar.selectbox(
    "Statement Type",
    ["Standalone", "Consolidated"],
    index=0
)

with st.sidebar.expander("Additional Threshold Parameters (Optional)", expanded=False):
    is_nbfc = st.checkbox("Non-Banking Financial Company (NBFC)", value=False)
    net_worth_input = st.number_input(
        "Net Worth (in ₹ Crores, if unlisted)",
        min_value=0.0,
        value=350.0 if listing_status == "Unlisted" else 0.0,
        step=50.0,
        help="Net Worth ≥ ₹250 Crores mandates Ind AS for unlisted companies."
    )
    net_worth_val = net_worth_input if net_worth_input > 0 else None

# Run Applicability Validation
profile_validation = ApplicabilityEngine.validate_profile(
    company_type=company_type,
    listing_status=listing_status,
    framework=framework,
    schedule_iii_division=schedule_iii_division,
    financial_year=financial_year,
    statement_type=statement_type,
    is_nbfc=is_nbfc,
    net_worth_crores=net_worth_val
)

# Render Applicability Status in Sidebar
if profile_validation["is_valid"]:
    st.sidebar.success(f"✓ Profile Status: {profile_validation['status']}")
else:
    st.sidebar.error(f"⚠️ Profile Status: {profile_validation['status']}")
    for err in profile_validation["errors"]:
        st.sidebar.warning(f"• {err}")

if profile_validation["clarifications_needed"]:
    for clar in profile_validation["clarifications_needed"]:
        st.sidebar.info(f"ℹ️ {clar}")

# AI API Key Configuration in Sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 AI Model Configuration")
gemini_key_input = st.sidebar.text_input(
    "Google Gemini API Key (Optional)",
    type="password",
    value=os.environ.get("GEMINI_API_KEY", ""),
    help="Optional. If omitted, the application seamlessly runs on its built-in Offline CA Expert Analytical Engine without external API dependencies."
)
if gemini_key_input:
    st.sidebar.success("⚡ Live Gemini AI Model Active")
else:
    st.sidebar.info("🔒 Offline CA Expert Heuristics Active (Free, private & offline)")


# -----------------------------------------------------------------------------
# MAIN APP HEADER & REVIEW MODE SELECTION
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">Financial Reporting Review Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">AI-Augmented Financial Statement & Annual Report Compliance Review | Built for Chartered Accountants & FRRB Experts</div>', unsafe_allow_html=True)

# Prominent Review Mode Selection
st.markdown("### 1. Select Review Mode")
mode_cols = st.columns([1, 1])

with mode_cols[0]:
    mode_a_selected = st.button(
        "📋 Option A: Financial Statements Review Before Finalisation",
        use_container_width=True,
        type="primary" if st.session_state.get("review_mode", "Option A") == "Option A" else "secondary"
    )
    if mode_a_selected:
        st.session_state.review_mode = "Option A"

with mode_cols[1]:
    mode_b_selected = st.button(
        "🔍 Option B: Annual Report Review & Red-Flag Identification",
        use_container_width=True,
        type="primary" if st.session_state.get("review_mode", "Option A") == "Option B" else "secondary"
    )
    if mode_b_selected:
        st.session_state.review_mode = "Option B"

review_mode = st.session_state.get("review_mode", "Option A")

if review_mode == "Option A":
    st.info(
        "**Option A Active:** Designed for draft, unfinalised financial statements. "
        "The objective is to identify errors, missing disclosures, arithmetic imbalances, and generate an "
        "**Excel Issue Log (Worksheet 1)** and **Corrected Draft Financial Statements with Yellow Cell Highlighting (Worksheet 2)**."
    )
else:
    st.info(
        "**Option B Active:** Designed for published or finalised annual reports. "
        "The objective is to identify reporting deficiencies, CARO 2020 remarks, auditor modifications, and generate a "
        "**Structured Findings Register with Risk Ratings (Worksheet 1)** and **Executive Summary Analytics (Worksheet 2)**."
    )


# -----------------------------------------------------------------------------
# DOCUMENT INGESTION (EXCEL)
# -----------------------------------------------------------------------------
st.markdown("### 2. Document Ingestion (Excel)")

st.markdown("#### 📁 Output Required")
output_choice = st.radio(
    "Select Output",
    [
        "Financial Reporting Review Points Sheet",
        "Draft Financial Statements (Yellow Highlights)",
    ],
    index=0 if st.session_state.get("output_choice") != "Draft Financial Statements (Yellow Highlights)" else 1,
    help="Option 1: Financial Reporting Review Points Sheet | Option 2: Draft Financial Statements – incorporate the relevant disclosures into the draft financial statements and highlight all additions or modifications in yellow."
)
st.session_state.output_choice = output_choice

if output_choice == "Financial Reporting Review Points Sheet":
    st.caption("📋 **Financial Reporting Review Points Sheet:** Identifies reporting non-compliances, Schedule III gaps, CARO red flags, and auditor remarks.")
else:
    st.caption("📝 **Draft Financial Statements (Yellow Highlights):** Your own draft financial statements are returned in the same format – relevant disclosures are incorporated and every addition or modification is highlighted in yellow.")

st.markdown("---")
st.markdown("#### 📤 Upload Financial Statements (Excel)")
uploaded_file = st.file_uploader(
    "Upload Draft Financial Statements or Published Annual Report (Excel Workbook)",
    type=["xlsx", "xls", "xlsm", "pdf"],
    help="Upload Excel (.xlsx, .xls) financial statement workbook."
)

if uploaded_file is not None:
    if st.session_state.current_filename != uploaded_file.name:
        file_bytes = uploaded_file.read()
        st.session_state.extracted_doc = PDFExtractor.extract_from_bytes(file_bytes, filename=uploaded_file.name)
        st.session_state.source_bytes = file_bytes
        st.session_state.current_filename = uploaded_file.name
        st.session_state.audit_results = None
        st.success(f"✓ Uploaded and parsed: {uploaded_file.name}")


# -----------------------------------------------------------------------------
# DOCUMENT DIAGNOSTICS & SECTION MAPPING
# -----------------------------------------------------------------------------
doc = st.session_state.extracted_doc

if doc:
    if not doc["success"]:
        st.error(f"❌ Document Error: {doc.get('error')}")
    else:
        with st.expander("📄 Document Diagnostics & Section Detection", expanded=False):
            is_excel = doc["filename"].lower().endswith((".xlsx", ".xls", ".xlsm"))
            diag_cols = st.columns(4)
            diag_cols[0].metric("File Name", doc["filename"])
            diag_cols[1].metric("Total Sheets / Pages", doc["total_pages"])
            diag_cols[2].metric("Selectable Chars / Sheet" if is_excel else "Selectable Chars / Page", f"{doc['avg_chars_per_page']}")
            diag_cols[3].metric("Document Format", "Excel Workbook (.xlsx)" if is_excel else "Financial Document")

            st.markdown("**Detected Financial Statements & Structural Sections:**")
            sec_info = []
            for sec_name, sec_data in doc["sections"].items():
                sec_info.append({
                    "Section Name": sec_name.replace("_", " ").title(),
                    "Detected": "✓ Yes" if sec_data["detected"] else "— Not Found",
                    "Start Sheet / Page": f"Sheet {sec_data['start_page']}" if is_excel and sec_data['start_page'] else (f"Page {sec_data['start_page']}" if sec_data['start_page'] else "—"),
                    "Total Spanned": len(sec_data["pages"]) if sec_data["pages"] else 0
                })
            st.table(pd.DataFrame(sec_info))



# -----------------------------------------------------------------------------
# ENTITY PROFILE DETECTED FROM THE FINANCIAL STATEMENTS
# -----------------------------------------------------------------------------
fs_model = None
if doc and doc.get("success") and st.session_state.get("source_bytes"):
    if st.session_state.get("fs_model_for") != st.session_state.current_filename:
        st.session_state.fs_model = FSModel.from_bytes(st.session_state.source_bytes, st.session_state.current_filename, doc.get("pages"))
        st.session_state.fs_model_for = st.session_state.current_filename
    fs_model = st.session_state.fs_model

sidebar_profile = {
    "company_type": company_type,
    "listing_status": listing_status,
    "listed": listing_status == "Listed",
    "framework": framework,
    "schedule_iii_division": schedule_iii_division,
    "financial_year": financial_year,
    "statement_type": statement_type,
}
effective_profile = dict(sidebar_profile)

if fs_model is not None:
    detected = fs_model.profile
    with st.expander("🔎 Entity profile detected from the financial statements", expanded=True):
        rows, mismatches = [], []
        for key, label in [("company_type", "Company type"), ("framework", "Framework"), ("schedule_iii_division", "Schedule III division"),
                           ("financial_year", "Financial year")]:
            d = detected.get(key)
            s = sidebar_profile.get(key)
            rows.append({"Attribute": label, "Detected from statements": d or "—", "Sidebar selection": s})
            if d and s and d != s:
                mismatches.append(label)
        listed_d = detected.get("listed")
        rows.append({"Attribute": "Listed", "Detected from statements": ("Yes" if listed_d else "No") if listed_d is not None else "—",
                     "Sidebar selection": listing_status})
        if listed_d is not None and listed_d != (listing_status == "Listed"):
            mismatches.append("Listing status")
        rows.append({"Attribute": "CIN", "Detected from statements": detected.get("cin", "—"), "Sidebar selection": "—"})
        rows.append({"Attribute": "Amounts", "Detected from statements": detected.get("unit", "—"), "Sidebar selection": "—"})
        if "small_company" in detected:
            rows.append({"Attribute": "Small company (Sec 2(85)) / SMC", "Detected from statements":
                         f"{'Yes' if detected['small_company'] else 'No'} / {'Yes' if detected.get('smc') else 'No'}", "Sidebar selection": "—"})
        st.table(pd.DataFrame(rows))
        use_detected = st.checkbox("Use the profile detected from the financial statements (recommended)", value=True,
                                   help="Applicability of every check is decided on this profile.")
        if mismatches:
            st.warning(f"The sidebar selection differs from the statements for: {', '.join(mismatches)}. "
                       + ("The detected profile will be used." if use_detected else "The sidebar profile will be used."))
    if use_detected:
        for key in ("company_type", "framework", "schedule_iii_division", "financial_year"):
            if detected.get(key):
                effective_profile[key] = detected[key]
        if detected.get("listed") is not None:
            effective_profile["listed"] = detected["listed"]
            effective_profile["listing_status"] = "Listed" if detected["listed"] else "Unlisted"
    for key in ("cin", "unit", "small_company", "smc", "one_person_company", "turnover_rs", "paid_up_capital_rs"):
        if key in detected:
            effective_profile[key] = detected[key]


# -----------------------------------------------------------------------------
# EXECUTION: RUN FRRB REVIEW
# -----------------------------------------------------------------------------
st.markdown("### 3. Review Execution")

run_audit_col, info_col = st.columns([1, 2])

with run_audit_col:
    run_btn = st.button("🚀 Run FRRB Compliance Review", type="primary", use_container_width=True, disabled=(fs_model is None))

with info_col:
    if doc and doc.get("success"):
        st.markdown(f"**Active Document:** `{doc['filename']}` ({doc['total_pages']} sheets/sections)")
    else:
        st.caption("Upload the financial statements above to enable review.")

if run_btn and fs_model is not None:
    with st.spinner("Establishing applicability and verifying the financial statements..."):
        engine_out = ReviewEngine(fs_model, effective_profile).run()
        findings = engine_out["findings"]
        ai_note, rejected = "Evidence-based review engine (no AI)", []
        if gemini_key_input:
            try:
                ai_findings, rejected = AIReviewer.review(fs_model, effective_profile, findings, engine_out["checks"], gemini_key_input)
                findings = findings + ai_findings
                ai_note = f"Review engine + Gemini ({len(ai_findings)} AI observation(s) accepted, {len(rejected)} rejected by evidence validation)"
            except Exception as exc:
                ai_note = f"Review engine only - Gemini call failed: {str(exc)[:120]}"
        order = {n: i for i, n in enumerate(NATURES)}
        findings.sort(key=lambda f: (order.get(f.get("nature"), 9), {"High": 0, "Medium": 1, "Low": 2}.get(f.get("significance"), 3)))
        for i, f in enumerate(findings, start=1):
            f["issue_id"] = f"OBS-{i:02d}"

        st.session_state.audit_results = {
            "review_mode": review_mode,
            "profile": effective_profile,
            "total_issues": len(findings),
            "high_risk_count": sum(1 for x in findings if x.get("significance") == "High"),
            "med_risk_count": sum(1 for x in findings if x.get("significance") == "Medium"),
            "low_risk_count": sum(1 for x in findings if x.get("significance") == "Low"),
            "categories_breakdown": {n: sum(1 for x in findings if x.get("nature") == n) for n in NATURES},
            "issues": findings,
            "checks": engine_out["checks"],
            "rejected_ai": rejected,
            "ai_source": ai_note,
        }


# -----------------------------------------------------------------------------
# 4. AUDIT RESULTS & OUTPUT PRESENTATION
# -----------------------------------------------------------------------------
results = st.session_state.audit_results

if results:
    st.markdown("---")
    st.markdown("### 4. Review Output & Analytical Results")

    # Default output view follows the user's "Output Required" selection
    default_opt_idx = 0 if st.session_state.get("output_choice") == "Draft Financial Statements (Yellow Highlights)" else 1

    output_mode = st.radio(
        "Select Report Output View",
        [
            "Draft Financial Statements (Yellow Highlights)",
            "Financial Reporting Review Points Sheet",
        ],
        index=default_opt_idx,
        horizontal=True,
        help="Switch between your draft financial statements with yellow highlighted disclosures and the Financial Reporting Review Points Sheet."
    )

    # =========================================================================
    # VIEW A: DRAFT FINANCIAL STATEMENTS (YELLOW HIGHLIGHTS) - ENTITY'S OWN FORMAT
    # =========================================================================
    if output_mode == "Draft Financial Statements (Yellow Highlights)":
        st.markdown(f"""
        <div style="background-color: #FEF9C3; border-left: 5px solid #EAB308; padding: 14px 18px; border-radius: 6px; margin-bottom: 18px;">
            <b style="color: #854D0E; font-size: 1.05rem;">📝 Draft Financial Statements – your format retained</b><br/>
            <span style="color: #713F12; font-size: 0.9rem;">
            The uploaded workbook is returned in exactly the same format (sheets, layout, fonts, number formats and formulas).
            Line items affected by a review point are <b>highlighted in yellow</b> with a cell comment giving the issue ID and reference,
            and the required disclosures under <b>Schedule III ({schedule_iii_division})</b> and the applicable standards are inserted into the
            existing Notes in yellow. Amounts not available in the draft are left as <b>[___]</b> for management to complete.
            </span>
        </div>
        """, unsafe_allow_html=True)

        source_bytes = st.session_state.get("source_bytes")
        current_name = st.session_state.get("current_filename") or ""
        if not source_bytes or not DraftFSMarker.is_supported(current_name):
            st.warning("Draft Financial Statements output needs the draft statements uploaded as an Excel workbook (.xlsx / .xlsm) so that its format can be retained. Please upload the Excel draft, or use the Review Points Sheet view.")
        else:
            # built once per review and kept with the results (rebuilding on every rerun exhausted the hosted app's memory)
            if "_marked" not in results:
                marked, changes = DraftFSMarker.mark(source_bytes, current_name, results["issues"])
                results["_marked"] = (marked, changes, DraftFSMarker.preview(marked, source_bytes))
                gc.collect()
            marked_bytes, fs_changes, preview = results["_marked"]
            base_name = os.path.splitext(current_name)[0]
            ext = os.path.splitext(current_name)[1].lower()

            fs_col1, fs_col2 = st.columns([2, 1])
            with fs_col1:
                inserted = sum(1 for c in fs_changes if c["type"] == "Disclosure inserted")
                highlighted = sum(1 for c in fs_changes if c["type"] == "Existing line highlighted")
                st.write(f"**{highlighted}** existing line items highlighted and **{inserted}** disclosure lines incorporated. "
                         "A 'Yellow Changes Index' sheet is added at the end of the workbook as the audit trail.")
            with fs_col2:
                st.download_button(
                    label="⬇️ Download Draft Financial Statements",
                    data=marked_bytes,
                    file_name=f"{base_name}_Reviewed_Yellow{ext}",
                    mime="application/vnd.ms-excel.sheet.macroEnabled.12" if ext == ".xlsm" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )

            st.markdown("---")
            sheet_tabs = st.tabs([f"📄 {name}" for name in preview] + ["📋 Yellow Changes Index"])

            for tab, (sheet_name, data) in zip(sheet_tabs, preview.items()):
                with tab:
                    grid, yellow = data["grid"], data["yellow"]
                    if not grid:
                        st.caption("Empty sheet")
                        continue
                    width = max(len(r) for r in grid)
                    grid = [list(r) + [""] * (width - len(r)) for r in grid]
                    yellow = [list(r) + [False] * (width - len(r)) for r in yellow]
                    sheet_df = pd.DataFrame(grid, columns=[chr(65 + i) if i < 26 else f"C{i+1}" for i in range(width)])
                    sheet_df.index = range(1, len(sheet_df) + 1)
                    sheet_df = sheet_df.astype(str).replace({"None": ""})
                    styles = pd.DataFrame(
                        [["background-color: #FFFF00; color: #000000; font-weight: 600" if f else "" for f in r] for r in yellow],
                        index=sheet_df.index, columns=sheet_df.columns
                    )
                    st.dataframe(sheet_df.style.apply(lambda _: styles, axis=None), use_container_width=True, height=min(640, 38 + 35 * len(sheet_df)))

            with sheet_tabs[-1]:
                st.caption("Every yellow change, linked to its review point and reference.")
                st.dataframe(pd.DataFrame(fs_changes), use_container_width=True)

    # =========================================================================
    # VIEW B: FINANCIAL REPORTING REVIEW POINTS SHEET (FRRB TECHNICAL REVIEW FORMAT)
    # =========================================================================
    else:
        prof = results["profile"]
        st.markdown(f"""
        <div style="background-color: #F0FDF4; border-left: 5px solid #16A34A; padding: 14px 18px; border-radius: 6px; margin-bottom: 18px;">
            <b style="color: #166534; font-size: 1.05rem;">📋 Financial Reporting Review Points Sheet</b><br/>
            <span style="color: #14532D; font-size: 0.9rem;">
            Only evidence-based observations are reported. Applicability of every check was first established from the financial statements
            ({html.escape(str(prof.get('framework')))}, {html.escape(str(prof.get('schedule_iii_division')))}, {html.escape(str(prof.get('financial_year')))});
            checks that do not apply are listed under <b>Checks &amp; applicability</b>, not reported as observations.
            Source: {html.escape(results.get('ai_source', ''))}.
            </span>
        </div>
        """, unsafe_allow_html=True)

        nature_colors = {"Non-compliance": "#DC2626", "Inconsistency": "#C2410C", "Disclosure gap": "#D97706",
                         "Potential concern": "#2563EB", "Requires verification": "#64748B"}
        kpi_cols = st.columns(len(NATURES) + 1)
        with kpi_cols[0]:
            st.markdown(f"""<div class="metric-card"><div class="metric-num" style="color:#0B2F4C;">{results['total_issues']}</div>
            <div class="metric-label">Observations</div></div>""", unsafe_allow_html=True)
        for col, n in zip(kpi_cols[1:], NATURES):
            with col:
                st.markdown(f"""<div class="metric-card"><div class="metric-num" style="color:{nature_colors[n]};">{results['categories_breakdown'].get(n, 0)}</div>
                <div class="metric-label">{n}</div></div>""", unsafe_allow_html=True)
        st.markdown("<br/>", unsafe_allow_html=True)

        if "_tr_xlsx" not in results:
            results["_tr_xlsx"] = ExcelReportGenerator.generate_tr_workbook(
                results["issues"], results.get("checks", []), prof,
                entity_name=os.path.splitext(st.session_state.get("current_filename") or "")[0])
        rp_col1, rp_col2 = st.columns([2, 1])
        with rp_col1:
            st.write("**Downloadable Review Points Sheet** in the FRRB Technical Review layout (Title, Sub Title, View of the Reviewer, "
                     "Matter contained in the financial statements, Exact technical requirement), with the applicability log and detected profile.")
        with rp_col2:
            st.download_button(
                label="⬇️ Download Review Points Sheet (.xlsx)",
                data=results["_tr_xlsx"],
                file_name=f"Financial_Reporting_Review_Points_{str(prof.get('financial_year', financial_year)).replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

        st.markdown("---")
        tab_findings, tab_checks, tab_library = st.tabs([
            "📋 Observations",
            "✅ Checks & applicability",
            "📚 Technical Reference Library"
        ])

        with tab_findings:
            f1, f3 = st.columns([1, 2])
            with f1:
                nature_filter = st.selectbox("Nature", ["All"] + NATURES)
            with f3:
                search_query = st.text_input("Search (e.g. ratio, related party, cash flow)", "")

            shown = results["issues"]
            if nature_filter != "All":
                shown = [i for i in shown if i.get("nature") == nature_filter]
            if search_query.strip():
                q = search_query.strip().lower()
                shown = [i for i in shown if q in (i.get("view", "") + i.get("sub_title", "") + i.get("title", "") + i.get("matter", "")).lower()]

            if not shown:
                if results["total_issues"] == 0:
                    st.success("No substantiated observations. See 'Checks & applicability' for the procedures performed.")
                else:
                    st.info("No observations match the filters.")

            for issue in shown:
                color = nature_colors.get(issue.get("nature"), "#64748B")
                evidence_html = "".join(f"<li>{html.escape(str(e.get('text', '')))}</li>" for e in issue.get("evidence", [])[:8])
                req_html = "".join(
                    f"<div style='margin-top:4px;'><b>{html.escape(p['ref'])}:</b> {html.escape(p['text'][:700])}{'…' if len(p['text']) > 700 else ''}</div>"
                    for p in issue.get("source_requirements", [])
                ) or html.escape(issue.get("statutory_ref", ""))
                st.markdown(f"""
                <div style="border: 1px solid #CBD5E1; border-left: 5px solid {color}; border-radius: 8px; padding: 16px; margin-bottom: 14px; background-color: #FFFFFF; color: #0F172A;">
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
                        <span style="font-weight:700; color:#1F4E79; font-size:1.02rem;">{issue.get('issue_id')} — {html.escape(issue.get('title', ''))} | {html.escape(issue.get('sub_title', ''))}</span>
                        <span><span style="background:{color};color:#FFFFFF;padding:3px 10px;border-radius:10px;font-size:0.78rem;font-weight:600;">{html.escape(issue.get('nature', ''))}</span>
                        <span style="background:#F1F5F9;color:#334155;padding:3px 8px;border-radius:10px;font-size:0.75rem;margin-left:6px;">{html.escape(issue.get('significance', ''))} significance</span></span>
                    </div>
                    <div style="margin-top:10px; font-size:0.93rem;"><b>View of the Reviewer:</b><br/>{html.escape(issue.get('view', ''))}</div>
                    <div style="background-color:#F1F5F9; color:#0F172A; padding:8px 12px; border-radius:4px; font-size:0.88rem; margin-top:10px;">
                        <b>Matter contained in the financial statements:</b><br/>{html.escape(issue.get('matter', ''))}
                        <ul style="margin:6px 0 0 18px; padding:0;">{evidence_html}</ul>
                    </div>
                    <div style="background-color:#EEF2FF; color:#1E1B4B; padding:8px 12px; border-radius:4px; font-size:0.85rem; margin-top:8px;">
                        <b>Exact technical requirement(s):</b>{req_html}
                    </div>
                    <div class="correction-box" style="color:#422006;"><b>Suggested correction:</b><br/>{html.escape(issue.get('suggested_correction', ''))}</div>
                    <div style="font-size:0.78rem; color:#64748B;">Basis: {html.escape(issue.get('basis', ''))}</div>
                </div>
                """, unsafe_allow_html=True)

            if results.get("rejected_ai"):
                with st.expander(f"AI suggestions rejected by evidence validation ({len(results['rejected_ai'])})"):
                    for r in results["rejected_ai"]:
                        st.caption(f"• {r}")

        with tab_checks:
            st.markdown("#### Procedures performed and applicability")
            st.caption("Each check first establishes, from the company's own figures, whether the item exists. "
                       "'Not applicable' checks are not reported as observations.")
            checks_df = pd.DataFrame(results.get("checks", []))
            if not checks_df.empty:
                st.dataframe(checks_df, use_container_width=True, height=min(700, 40 + 35 * len(checks_df)))
            st.markdown("#### Entity profile used")
            st.json({k: v for k, v in prof.items() if k not in ("turnover_rs", "paid_up_capital_rs")})

        with tab_library:
            st.markdown("#### ICAI FRRB Precedent & Technical Standards Library")
            st.caption("Principles compiled from ICAI's Study on Compliance of Financial Reporting Requirements")
            precedents = FRRBLibrary.get_precedents_by_framework(prof.get("framework", framework))
            for p in precedents:
                with st.expander(f"{p['id']}: {p['topic']} ({p['framework']})", expanded=False):
                    st.markdown(f"**Category:** {p['category']}")
                    st.markdown(f"**Standard Citation:** `{p['standard_ref']}` | **Statutory Reference:** `{p['statutory_ref']}`")
                    st.markdown(f"**Technical Principle:**\n> {p['principle']}")
                    st.markdown(f"**Common FRRB Deficiency:**\n{p['common_deficiency']}")
                    st.markdown(f"**Recommended Correction:**\n{p['suggested_correction']}")
