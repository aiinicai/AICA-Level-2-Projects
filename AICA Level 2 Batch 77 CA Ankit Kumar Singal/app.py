"""
app.py — GST Notice Tracker  |  Streamlit multi-page application
Run: streamlit run app.py
"""

import io
from datetime import datetime, date

import pandas as pd
import streamlit as st

from database import (
    init_db, get_all_notices, get_existing_keys,
    bulk_insert, bulk_upsert, update_notice_fields, delete_notice,
    replace_all_records,
)
from excel_handler import (
    generate_template, validate_excel, validate_excel_for_update,
    validate_excel_for_replace, export_to_excel,
    COLUMN_MAP,
)
from utils import (
    calc_days_remaining, calc_urgency,
    URGENCY_COLORS, URGENCY_BG,
    format_date, parse_date, validate_gstin,
)

# ─────────────────────────────────────────────────────────────────────────────
# Page config & CSS
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="GST Notice Tracker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject global CSS
st.markdown("""
<style>
/* ── Google Font ─────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── App background ──────────────────────────────────────────────────── */
.stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); min-height: 100vh; }

/* ── Sidebar ─────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.05) !important;
    border-right: 1px solid rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
}
section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }

/* ── KPI cards ───────────────────────────────────────────────────────── */
.kpi-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 14px;
    padding: 18px 20px;
    text-align: center;
    backdrop-filter: blur(6px);
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.35); }
.kpi-number { font-size: 2.2rem; font-weight: 700; line-height: 1; }
.kpi-label  { font-size: 0.78rem; color: #aaa; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.05em; }

/* ── Section headings ────────────────────────────────────────────────── */
.section-header {
    font-size: 1.4rem; font-weight: 700; color: #fff;
    border-left: 4px solid #6c63ff;
    padding-left: 12px; margin-bottom: 16px;
}

/* ── Urgency badges ──────────────────────────────────────────────────── */
.badge {
    display: inline-block; border-radius: 6px;
    padding: 2px 10px; font-size: 0.75rem; font-weight: 600;
}
.badge-green  { background: rgba(39,174,96,0.2);  color: #27ae60; }
.badge-amber  { background: rgba(230,126,34,0.2); color: #e67e22; }
.badge-red    { background: rgba(231,76,60,0.2);  color: #e74c3c; }
.badge-overdue{ background: rgba(142,68,173,0.2); color: #8e44ad; }

/* ── Info banner ─────────────────────────────────────────────────────── */
.info-banner {
    background: rgba(108,99,255,0.15);
    border: 1px solid rgba(108,99,255,0.4);
    border-radius: 10px; padding: 14px 18px;
    color: #ccc; font-size: 0.88rem;
    margin-bottom: 16px;
}

/* ── Preview table ───────────────────────────────────────────────────── */
.preview-valid   { color: #27ae60; font-weight: 600; }
.preview-invalid { color: #e74c3c; font-weight: 600; }
.preview-dup     { color: #e67e22; font-weight: 600; }

/* ── Streamlit overrides ─────────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px; font-weight: 600;
    transition: all 0.2s;
}
.stButton > button:hover { transform: translateY(-1px); }
div[data-testid="metric-container"] {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px; padding: 14px;
}
div[data-testid="metric-container"] label { color: #aaa !important; font-size: 0.8rem; }
div[data-testid="metric-container"] div[data-testid="metric-value"] { color: #fff !important; }

/* White text for input labels and widgets */
label, .stSelectbox label, .stTextInput label, .stTextArea label,
.stDateInput label, .stMultiSelect label { color: #ddd !important; }

/* DataFrame / table */
.stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Initialise DB
# ─────────────────────────────────────────────────────────────────────────────

init_db()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar navigation
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 20px 0 10px 0;">
        <div style="font-size:2.4rem;">📋</div>
        <div style="font-size:1.1rem; font-weight:700; color:#fff; margin-top:6px;">
            GST Notice Tracker
        </div>
        <div style="font-size:0.75rem; color:#888; margin-top:2px;">
            Excel-First Workflow
        </div>
    </div>
    <hr style="border-color:rgba(255,255,255,0.1); margin:10px 0 20px 0;">
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["🏠 Dashboard", "📥 Excel Import", "📊 Notice Register",
         "✏️ Add / Edit Notice", "📤 Export"],
        label_visibility="collapsed",
    )
    st.markdown("<hr style='border-color:rgba(255,255,255,0.1);margin:20px 0 10px 0'>",
                unsafe_allow_html=True)
    st.caption(f"Today: **{date.today().strftime('%d-%m-%Y')}**")

    # Quick template download in sidebar
    st.markdown("### 📄 Template")
    st.download_button(
        "⬇️ Download Import Template",
        data=generate_template(),
        file_name="GST_Notice_Import_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="sidebar_template",
    )

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def load_enriched_df() -> pd.DataFrame:
    """Load all notices and add computed columns: days_remaining, urgency."""
    df = get_all_notices()
    if df.empty:
        return df
    df["days_remaining"] = df["due_date"].apply(calc_days_remaining)
    df["urgency"]        = df["due_date"].apply(calc_urgency)
    return df


def urgency_badge(u: str) -> str:
    css = {
        "GREEN":   "badge-green",
        "AMBER":   "badge-amber",
        "RED":     "badge-red",
        "OVERDUE": "badge-overdue",
    }.get(u, "")
    return f'<span class="badge {css}">{u}</span>' if u else ""


def kpi_card(label: str, value, color: str = "#6c63ff") -> str:
    return f"""
    <div class="kpi-card">
        <div class="kpi-number" style="color:{color};">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>"""


def section_header(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Dashboard
# ─────────────────────────────────────────────────────────────────────────────

if page == "🏠 Dashboard":
    st.markdown("""
    <div style="padding:10px 0 24px 0;">
        <h1 style="color:#fff;font-size:2rem;font-weight:700;margin:0;">
            📋 GST Notice Tracker
        </h1>
        <p style="color:#aaa;margin-top:6px;font-size:0.95rem;">
            Real-time dashboard · Urgency auto-updates daily · Excel-first workflow
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_enriched_df()

    if df.empty:
        st.markdown("""
        <div class="info-banner">
            🚀 <strong>No notices yet.</strong>  Go to <em>Excel Import</em> to upload your first batch,
            or use <em>Add / Edit Notice</em> to enter records manually.
        </div>
        """, unsafe_allow_html=True)
    else:
        today = date.today()

        total       = len(df)
        open_n      = len(df[~df["response_status"].str.strip().str.lower().isin(["filed", "completed"])])
        completed   = len(df[df["response_status"].str.strip().str.lower().isin(["filed", "completed"])])
        green_n     = len(df[df["urgency"] == "GREEN"])
        amber_n     = len(df[df["urgency"] == "AMBER"])
        red_n       = len(df[df["urgency"] == "RED"])
        overdue_n   = len(df[df["urgency"] == "OVERDUE"])
        awaiting    = len(df[df["client_data_status"].str.strip().str.lower() == "awaiting client data"])
        partial     = len(df[df["client_data_status"].str.strip().str.lower() == "partially received"])
        received    = len(df[df["client_data_status"].str.strip().str.lower() == "data received"])
        filed       = len(df[df["response_status"].str.strip().str.lower() == "filed"])

        # Row 1 – Core counts
        section_header("Overview")
        cols = st.columns(5)
        cards = [
            ("Total Notices",    total,     "#6c63ff"),
            ("Open",             open_n,    "#3498db"),
            ("Completed",        completed, "#27ae60"),
            ("Overdue",          overdue_n, "#8e44ad"),
        ]
        for col, (lbl, val, clr) in zip(cols, cards):
            col.markdown(kpi_card(lbl, val, clr), unsafe_allow_html=True)

        # Row 2 – Urgency
        section_header("Urgency Breakdown")
        u_cols = st.columns(4)
        u_cards = [
            ("GREEN  (>10 days)", green_n,   "#27ae60"),
            ("AMBER  (6-10 days)", amber_n,  "#e67e22"),
            ("RED    (0-5 days)",  red_n,    "#e74c3c"),
            ("OVERDUE",            overdue_n,"#8e44ad"),
        ]
        for col, (lbl, val, clr) in zip(u_cols, u_cards):
            col.markdown(kpi_card(lbl, val, clr), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Row 3 – Client data + response
        section_header("Client Data & Response Status")
        s_cols = st.columns(4)
        s_cards = [
            ("Awaiting Client Data",  awaiting, "#e74c3c"),
            ("Partially Received",    partial,  "#e67e22"),
            ("Data Received",         received, "#27ae60"),
            ("Responses Filed",       filed,    "#3498db"),
        ]
        for col, (lbl, val, clr) in zip(s_cols, s_cards):
            col.markdown(kpi_card(lbl, val, clr), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Recent critical notices
        section_header("🔴 Notices Needing Immediate Attention")
        urgent = df[df["urgency"].isin(["RED", "OVERDUE"])].copy()
        if urgent.empty:
            st.success("No notices in RED or OVERDUE status right now. ✅")
        else:
            urgent_display = urgent[[
                "client_name", "gstin", "notice_number", "notice_section",
                "due_date", "days_remaining", "urgency",
                "client_data_status", "response_status", "assigned_team_member",
            ]].rename(columns={
                "client_name":        "Client",
                "gstin":              "GSTIN",
                "notice_number":      "Notice No.",
                "notice_section":     "Section",
                "due_date":           "Due Date",
                "days_remaining":     "Days Left",
                "urgency":            "Urgency",
                "client_data_status": "Client Data Status",
                "response_status":    "Response Status",
                "assigned_team_member": "Assigned To",
            })
            st.dataframe(
                urgent_display,
                use_container_width=True,
                hide_index=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Excel Import
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📥 Excel Import":
    section_header("📥 Excel Import / Bulk Upload")

    st.markdown("""
    <div class="info-banner">
        <strong>Workflow:</strong>
        Upload Excel → Validate & Preview → Confirm → Import → Dashboard updates automatically.<br>
        <strong>Template columns:</strong> Client Name · GSTIN · Notice/Reference Number · Due Date
        (required) + 14 optional fields.
    </div>
    """, unsafe_allow_html=True)

    # Template download
    col_t1, col_t2 = st.columns([2, 5])
    with col_t1:
        st.download_button(
            "⬇️ Download Excel Template",
            data=generate_template(),
            file_name="GST_Notice_Import_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="import_template",
        )

    st.markdown("---")

    # Import mode
    import_mode = st.radio(
        "Import Mode",
        [
            "🔄 Update Existing & Add New Records (match on GSTIN + Notice No. - Recommended)",
            "➕ Add New Records Only (skip duplicates)",
            "💥 Replace All Existing Data (wipe database & import new file)",
        ],
        horizontal=True,
    )
    is_update_mode = import_mode.startswith("🔄")
    is_replace_mode = import_mode.startswith("💥")

    st.markdown("#### Upload Excel File (.xlsx)")
    uploaded_file = st.file_uploader(
        "Choose file", type=["xlsx"], label_visibility="collapsed"
    )

    if uploaded_file:
        with st.spinner("Reading & validating Excel file…"):
            try:
                df_raw = pd.read_excel(uploaded_file, engine="openpyxl")
            except Exception as e:
                st.error(f"❌ Could not read Excel file: {e}")
                st.stop()

        existing_keys = get_existing_keys()

        if is_replace_mode:
            result = validate_excel_for_replace(df_raw)
        elif is_update_mode:
            result = validate_excel_for_update(df_raw, existing_keys)
        else:
            result = validate_excel(df_raw, existing_keys)

        if result.get("column_error"):
            st.error(f"❌ Column mismatch: {result['column_error']}")
            st.info("Please download the template and ensure column headers match exactly.")
            st.stop()

        summary = result["summary"]
        valid_records  = result["valid_records"]
        invalid_rows   = result["invalid_rows"]
        dup_rows       = result["duplicate_rows"]

        # ── Summary banner ─────────────────────────────────────────────
        st.markdown("### 📊 Validation Summary")
        if is_update_mode:
            s_cols = st.columns(5)
            s_cols[0].metric("Total Rows", summary["total"])
            s_cols[1].metric("🆕 Add New", summary.get("will_insert", 0))
            s_cols[2].metric("🔄 Update Existing", summary.get("will_update", 0))
            s_cols[3].metric("✅ Completed/Filed", summary.get("completed_count", 0) + summary.get("filed_count", 0))
            s_cols[4].metric("❌ Invalid / Duplicate", summary["invalid"] + summary["duplicates"])
        else:
            s_cols = st.columns(4)
            s_cols[0].metric("Total Rows", summary["total"])
            s_cols[1].metric("✅ Valid",    summary["valid"],      delta=None)
            s_cols[2].metric("❌ Invalid",  summary["invalid"],    delta=None)
            s_cols[3].metric("⚠️ Duplicates", summary["duplicates"], delta=None)

        if is_replace_mode:
            st.warning(
                "⚠️ **Replace mode active**: Confirming import will **permanently wipe all existing records** "
                "in the database and replace them with the valid records from this Excel file."
            )
        elif is_update_mode:
            st.info(
                f"📌 **Update & Add New Mode Active**: **{summary.get('will_insert', 0)}** new records will be "
                f"**added**, and **{summary.get('will_update', 0)}** existing records will be **updated**. "
                f"Existing DB fields will be **maintained** if Excel cells are left blank."
            )

        st.markdown("---")

        # ── Previews ───────────────────────────────────────────────────
        if is_update_mode:
            tab_new, tab_upd = st.tabs([
                f"🆕 New Records to Add ({len(result.get('insert_records', []))})",
                f"🔄 Existing Records to Update ({len(result.get('update_records', []))})"
            ])
            with tab_new:
                if result.get("insert_records"):
                    new_df = pd.DataFrame(result["insert_records"])[[
                        "client_name", "gstin", "notice_number",
                        "notice_section", "act_type", "due_date",
                        "client_data_status", "response_status", "assigned_team_member",
                    ]].rename(columns={
                        "client_name":        "Client",
                        "gstin":              "GSTIN",
                        "notice_number":      "Notice No.",
                        "notice_section":     "Section",
                        "act_type":           "Act",
                        "due_date":           "Due Date",
                        "client_data_status": "Client Data Status",
                        "response_status":    "Response Status",
                        "assigned_team_member": "Assigned To",
                    })
                    st.dataframe(new_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("No new records to insert in this file.")

            with tab_upd:
                if result.get("update_records"):
                    upd_df = pd.DataFrame(result["update_records"])[[
                        "client_name", "gstin", "notice_number",
                        "notice_section", "act_type", "due_date",
                        "client_data_status", "response_status", "assigned_team_member",
                    ]].rename(columns={
                        "client_name":        "Client",
                        "gstin":              "GSTIN",
                        "notice_number":      "Notice No.",
                        "notice_section":     "Section",
                        "act_type":           "Act",
                        "due_date":           "Due Date",
                        "client_data_status": "Client Data Status",
                        "response_status":    "Response Status",
                        "assigned_team_member": "Assigned To",
                    })
                    st.dataframe(upd_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("No existing records match for updating in this file.")
        else:
            if valid_records:
                with st.expander(f"✅ Valid Records ({len(valid_records)}) — click to preview", expanded=True):
                    preview_df = pd.DataFrame(valid_records)[[
                        "client_name", "gstin", "notice_number",
                        "notice_section", "act_type", "due_date",
                        "client_data_status", "response_status", "assigned_team_member",
                    ]].rename(columns={
                        "client_name":        "Client",
                        "gstin":              "GSTIN",
                        "notice_number":      "Notice No.",
                        "notice_section":     "Section",
                        "act_type":           "Act",
                        "due_date":           "Due Date",
                        "client_data_status": "Client Data Status",
                        "response_status":    "Response Status",
                        "assigned_team_member": "Assigned To",
                    })
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)

        # ── Duplicate records ──────────────────────────────────────────
        if dup_rows:
            dup_label = (
                f"⚠️ Duplicate Records within File ({len(dup_rows)}) — will be SKIPPED"
                if is_replace_mode or is_update_mode
                else f"⚠️ Duplicate Records ({len(dup_rows)}) — will be SKIPPED"
            )
            with st.expander(dup_label, expanded=False):
                for item in dup_rows:
                    st.warning(f"Row {item.get('row', 'N/A')}: {item['data'].get('client_name','')} / "
                               f"{item['data'].get('notice_number','')}  — {'; '.join(item['errors'])}")

        # ── Invalid records ────────────────────────────────────────────
        if invalid_rows:
            with st.expander(f"❌ Invalid Records ({len(invalid_rows)}) — will be REJECTED", expanded=False):
                for item in invalid_rows:
                    st.error(
                        f"**Row {item['row']}** | {item['data'].get('client_name','')} / "
                        f"{item['data'].get('notice_number','')} | Errors: {'; '.join(item['errors'])}"
                    )

        # ── Confirm & Import ───────────────────────────────────────────
        st.markdown("---")
        if not valid_records and not (is_update_mode and (result.get("update_records") or result.get("insert_records"))):
            st.warning("⚠️ No valid records to import.")
        else:
            if is_replace_mode:
                st.error("🚨 **Caution**: This action cannot be undone. All current data in the database will be erased.")
                confirm_wipe = st.checkbox(
                    "I understand that all existing records will be permanently deleted and replaced.",
                    key="confirm_wipe",
                )
                if st.button(
                    f"💥 Confirm & Replace All Data ({len(valid_records)} record(s))",
                    type="primary",
                    disabled=not confirm_wipe,
                    key="confirm_replace_btn",
                ):
                    with st.spinner("Wiping existing database records & importing new file…"):
                        count = replace_all_records(valid_records)
                        st.success(f"🎉 Existing data replaced! **{count}** record(s) imported.")
                        st.balloons()
                        st.info("💡 Go to the **Dashboard** or **Notice Register** to see your updated data.")
            elif is_update_mode:
                total_to_import = len(valid_records)
                if st.button(
                    f"✅ Confirm: Add {summary.get('will_insert',0)} + Update {summary.get('will_update',0)} record(s)",
                    type="primary",
                    key="confirm_update_btn",
                ):
                    with st.spinner("Importing & updating data…"):
                        all_records = result.get("insert_records", []) + result.get("update_records", [])
                        inserted, updated = bulk_upsert(all_records)
                        st.success(
                            f"🎉 Import complete! **{inserted}** new record(s) added, "
                            f"**{updated}** existing record(s) updated while maintaining all complete statuses."
                        )
                        st.balloons()
                        st.info("💡 Go to the **Dashboard** or **Notice Register** to see your data.")
            else:
                total_to_import = len(valid_records)
                if st.button(
                    f"✅ Confirm Import of {total_to_import} record(s)",
                    type="primary",
                    key="confirm_add_btn",
                ):
                    with st.spinner("Importing…"):
                        count = bulk_insert(valid_records)
                        skipped = len(dup_rows)
                        st.success(
                            f"🎉 Import complete! **{count}** record(s) imported. "
                            f"**{skipped}** duplicate(s) skipped."
                        )
                        st.balloons()
                        st.info("💡 Go to the **Dashboard** or **Notice Register** to see your data.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Notice Register
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📊 Notice Register":
    section_header("📊 Notice Register")

    df = load_enriched_df()

    if df.empty:
        st.markdown("""
        <div class="info-banner">
            No notices found. Import data via <strong>Excel Import</strong> or
            add records manually via <strong>Add / Edit Notice</strong>.
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # ── Filters ───────────────────────────────────────────────────────
    with st.expander("🔍 Filter", expanded=True):
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        with fc1:
            f_urgency = st.multiselect(
                "Urgency", ["GREEN", "AMBER", "RED", "OVERDUE"],
                default=[], key="filter_urgency"
            )
        with fc2:
            f_response = st.multiselect(
                "Response Status",
                sorted(df["response_status"].dropna().unique().tolist()),
                default=[], key="filter_response"
            )
        with fc3:
            f_client_data = st.multiselect(
                "Client Data Status",
                sorted(df["client_data_status"].dropna().unique().tolist()),
                default=[], key="filter_client_data"
            )
        with fc4:
            f_assignee = st.multiselect(
                "Assigned To",
                sorted(df["assigned_team_member"].dropna().unique().tolist()),
                default=[], key="filter_assignee"
            )
        with fc5:
            f_act = st.multiselect(
                "Act Type",
                sorted(df["act_type"].dropna().unique().tolist()),
                default=[], key="filter_act"
            )
        search_term = st.text_input("🔎 Search (Client / GSTIN / Notice No.)", key="register_search")

    # Apply filters
    filtered = df.copy()
    if f_urgency:
        filtered = filtered[filtered["urgency"].isin(f_urgency)]
    if f_response:
        filtered = filtered[filtered["response_status"].isin(f_response)]
    if f_client_data:
        filtered = filtered[filtered["client_data_status"].isin(f_client_data)]
    if f_assignee:
        filtered = filtered[filtered["assigned_team_member"].isin(f_assignee)]
    if f_act:
        filtered = filtered[filtered["act_type"].isin(f_act)]
    if search_term:
        s = search_term.lower()
        filtered = filtered[
            filtered["client_name"].str.lower().str.contains(s, na=False)
            | filtered["gstin"].str.lower().str.contains(s, na=False)
            | filtered["notice_number"].str.lower().str.contains(s, na=False)
        ]

    st.markdown(f"**{len(filtered)}** of **{len(df)}** notices shown")

    # ── Register table ─────────────────────────────────────────────────
    if not filtered.empty:
        display = filtered[[
            "id", "client_name", "gstin", "notice_number", "notice_section",
            "act_type", "notice_issue_date", "due_date", "days_remaining",
            "urgency", "client_data_status", "response_status",
            "assigned_team_member", "remarks",
        ]].rename(columns={
            "id":                   "ID",
            "client_name":          "Client",
            "gstin":                "GSTIN",
            "notice_number":        "Notice No.",
            "notice_section":       "Section",
            "act_type":             "Act",
            "notice_issue_date":    "Issue Date",
            "due_date":             "Due Date",
            "days_remaining":       "Days Left",
            "urgency":              "Urgency",
            "client_data_status":   "Client Data Status",
            "response_status":      "Response Status",
            "assigned_team_member": "Assigned To",
            "remarks":              "Remarks",
        })

        # Colour-coded urgency via Styler
        def colour_urgency(val):
            colours = {
                "GREEN":   "background-color:#1a4731;color:#27ae60;font-weight:600",
                "AMBER":   "background-color:#4a3100;color:#e67e22;font-weight:600",
                "RED":     "background-color:#4a0f0f;color:#e74c3c;font-weight:600",
                "OVERDUE": "background-color:#2d0a4a;color:#8e44ad;font-weight:600",
            }
            return colours.get(str(val), "")

        styled = display.style.applymap(colour_urgency, subset=["Urgency"])
        st.dataframe(styled, use_container_width=True, hide_index=True, height=480)

    # ── Quick-edit panel ───────────────────────────────────────────────
    st.markdown("---")
    section_header("✏️ Quick Update a Notice")
    if not filtered.empty:
        notice_options = {
            f"[{row['ID']}] {row['client_name']} / {row['notice_number']}": row["id"]
            for _, row in filtered.iterrows()
        }
        selected_label = st.selectbox("Select notice to update", list(notice_options.keys()))
        selected_id = notice_options[selected_label]
        row_data = filtered[filtered["id"] == selected_id].iloc[0]

        qe1, qe2, qe3, qe4 = st.columns(4)
        with qe1:
            new_client_data = st.selectbox(
                "Client Data Status",
                ["Pending", "Awaiting Client Data", "Partially Received",
                 "Data Received", "Not Applicable"],
                index=["Pending", "Awaiting Client Data", "Partially Received",
                       "Data Received", "Not Applicable"].index(
                    row_data["client_data_status"]
                    if row_data["client_data_status"] in
                       ["Pending", "Awaiting Client Data", "Partially Received",
                        "Data Received", "Not Applicable"]
                    else "Pending"
                ),
                key="qe_client_data",
            )
        with qe2:
            new_resp = st.selectbox(
                "Response Status",
                ["Pending", "In Progress", "Filed", "Completed", "Not Applicable"],
                index=["Pending", "In Progress", "Filed", "Completed", "Not Applicable"].index(
                    row_data["response_status"]
                    if row_data["response_status"] in
                       ["Pending", "In Progress", "Filed", "Completed", "Not Applicable"]
                    else "Pending"
                ),
                key="qe_response",
            )
        with qe3:
            new_assignee = st.text_input(
                "Assigned To", value=row_data["assigned_team_member"], key="qe_assignee"
            )
        with qe4:
            new_remarks = st.text_area(
                "Remarks", value=row_data["remarks"], height=80, key="qe_remarks"
            )

        if st.button("💾 Save Changes", type="primary", key="qe_save"):
            ok = update_notice_fields(selected_id, {
                "client_data_status":   new_client_data,
                "response_status":      new_resp,
                "assigned_team_member": new_assignee,
                "remarks":              new_remarks,
            })
            if ok:
                st.success("✅ Record updated successfully!")
                st.rerun()
            else:
                st.error("❌ Update failed — record not found.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Add / Edit Notice
# ─────────────────────────────────────────────────────────────────────────────

elif page == "✏️ Add / Edit Notice":
    section_header("✏️ Add / Edit a Notice")

    tab_add, tab_edit, tab_delete = st.tabs(["➕ Add New", "🖊️ Edit Existing", "🗑️ Delete"])

    # ── ADD tab ──────────────────────────────────────────────────────
    with tab_add:
        st.markdown("Fill in the fields below to add a single GST notice record.")

        with st.form("add_form", clear_on_submit=True):
            a1, a2 = st.columns(2)
            with a1:
                f_client    = st.text_input("Client Name *")
                f_gstin     = st.text_input("GSTIN *", placeholder="e.g. 27AABCU9603R1ZX")
                f_notice_no = st.text_input("Notice / Reference Number *")
                f_issue_dt  = st.text_input("Notice Issue Date (DD-MM-YYYY)")
                f_section   = st.text_input("Notice Issued Under Section")
                f_act       = st.selectbox("Act Type", ["", "CGST", "SGST", "IGST",
                                                         "CGST/SGST", "CGST/IGST", "SGST/IGST"])
                f_officer   = st.text_input("Issuing Officer")
                f_off_desig = st.text_input("Officer Designation")
                f_type      = st.text_input("Notice Type / Subject")
            with a2:
                f_due_dt    = st.text_input("Due Date * (DD-MM-YYYY)")
                f_cd_status = st.selectbox("Client Data Collection Status",
                                           ["Pending", "Awaiting Client Data",
                                            "Partially Received", "Data Received",
                                            "Not Applicable"])
                f_data_req  = st.text_area("Data Requested", height=70)
                f_dt_dreq   = st.text_input("Date Data Requested (DD-MM-YYYY)")
                f_dt_drecv  = st.text_input("Date Data Received (DD-MM-YYYY)")
                f_assignee  = st.text_input("Assigned Team Member")
                f_resp_dt   = st.text_input("Response Filing Date (DD-MM-YYYY)")
                f_resp_st   = st.selectbox("Response Status",
                                           ["Pending", "In Progress", "Filed",
                                            "Completed", "Not Applicable"])
                f_remarks   = st.text_area("Remarks", height=70)

            submitted = st.form_submit_button("➕ Add Notice", type="primary")

        if submitted:
            errors = []
            if not f_client.strip():   errors.append("Client Name is required")
            if not f_gstin.strip():    errors.append("GSTIN is required")
            elif not validate_gstin(f_gstin.strip()): errors.append("Invalid GSTIN format")
            if not f_notice_no.strip(): errors.append("Notice Number is required")
            if not f_due_dt.strip():   errors.append("Due Date is required")
            else:
                parsed_due = parse_date(f_due_dt.strip())
                if parsed_due is None:
                    errors.append("Due Date format invalid (use DD-MM-YYYY)")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                def safe_date(s):
                    dt = parse_date(s.strip()) if s.strip() else None
                    return format_date(dt) if dt else ""

                record = {
                    "client_name":            f_client.strip(),
                    "gstin":                  f_gstin.strip().upper(),
                    "notice_number":          f_notice_no.strip(),
                    "notice_issue_date":      safe_date(f_issue_dt),
                    "notice_section":         f_section.strip(),
                    "act_type":               f_act,
                    "issuing_officer":        f_officer.strip(),
                    "officer_designation":    f_off_desig.strip(),
                    "due_date":               safe_date(f_due_dt),
                    "notice_type":            f_type.strip(),
                    "client_data_status":     f_cd_status,
                    "data_requested":         f_data_req.strip(),
                    "date_data_requested":    safe_date(f_dt_dreq),
                    "date_data_received":     safe_date(f_dt_drecv),
                    "assigned_team_member":   f_assignee.strip(),
                    "response_filing_date":   safe_date(f_resp_dt),
                    "response_status":        f_resp_st,
                    "remarks":                f_remarks.strip(),
                }
                bulk_insert([record])
                st.success(f"✅ Notice '{f_notice_no}' added successfully!")
                st.rerun()

    # ── EDIT tab ─────────────────────────────────────────────────────
    with tab_edit:
        df_all = load_enriched_df()
        if df_all.empty:
            st.info("No notices in database yet.")
        else:
            options = {
                f"[{r['id']}] {r['client_name']} / {r['notice_number']}": r["id"]
                for _, r in df_all.iterrows()
            }
            sel_label = st.selectbox("Select notice to edit", list(options.keys()), key="edit_sel")
            sel_id    = options[sel_label]
            row       = df_all[df_all["id"] == sel_id].iloc[0]

            with st.form("edit_form"):
                e1, e2 = st.columns(2)
                with e1:
                    ef_client   = st.text_input("Client Name", value=row["client_name"])
                    ef_gstin    = st.text_input("GSTIN", value=row["gstin"])
                    ef_notice_no= st.text_input("Notice / Reference Number", value=row["notice_number"])
                    ef_issue_dt = st.text_input("Notice Issue Date", value=row["notice_issue_date"])
                    ef_section  = st.text_input("Section", value=row["notice_section"])
                    ef_act      = st.selectbox("Act Type",
                                               ["", "CGST", "SGST", "IGST", "CGST/SGST", "CGST/IGST", "SGST/IGST"],
                                               index=["", "CGST", "SGST", "IGST", "CGST/SGST", "CGST/IGST", "SGST/IGST"].index(
                                                   row["act_type"] if row["act_type"] in
                                                   ["", "CGST", "SGST", "IGST", "CGST/SGST", "CGST/IGST", "SGST/IGST"]
                                                   else ""))
                    ef_officer  = st.text_input("Issuing Officer", value=row["issuing_officer"])
                    ef_off_desig= st.text_input("Officer Designation", value=row["officer_designation"])
                    ef_type     = st.text_input("Notice Type", value=row["notice_type"])
                with e2:
                    ef_due_dt   = st.text_input("Due Date", value=row["due_date"])
                    ef_cd_status= st.selectbox("Client Data Status",
                                               ["Pending", "Awaiting Client Data",
                                                "Partially Received", "Data Received", "Not Applicable"],
                                               index=["Pending", "Awaiting Client Data",
                                                      "Partially Received", "Data Received", "Not Applicable"].index(
                                                   row["client_data_status"]
                                                   if row["client_data_status"] in
                                                   ["Pending", "Awaiting Client Data", "Partially Received",
                                                    "Data Received", "Not Applicable"]
                                                   else "Pending"))
                    ef_data_req = st.text_area("Data Requested", value=row["data_requested"], height=70)
                    ef_dt_dreq  = st.text_input("Date Data Requested", value=row["date_data_requested"])
                    ef_dt_drecv = st.text_input("Date Data Received", value=row["date_data_received"])
                    ef_assignee = st.text_input("Assigned Team Member", value=row["assigned_team_member"])
                    ef_resp_dt  = st.text_input("Response Filing Date", value=row["response_filing_date"])
                    ef_resp_st  = st.selectbox("Response Status",
                                               ["Pending", "In Progress", "Filed", "Completed", "Not Applicable"],
                                               index=["Pending", "In Progress", "Filed", "Completed", "Not Applicable"].index(
                                                   row["response_status"]
                                                   if row["response_status"] in
                                                   ["Pending", "In Progress", "Filed", "Completed", "Not Applicable"]
                                                   else "Pending"))
                    ef_remarks  = st.text_area("Remarks", value=row["remarks"], height=70)

                save_edit = st.form_submit_button("💾 Save Changes", type="primary")

            if save_edit:
                def safe_d(s): 
                    dt = parse_date(s.strip()) if s.strip() else None
                    return format_date(dt) if dt else ""

                update_notice_fields(sel_id, {
                    "client_name":            ef_client.strip(),
                    "gstin":                  ef_gstin.strip().upper(),
                    "notice_number":          ef_notice_no.strip(),
                    "notice_issue_date":      safe_d(ef_issue_dt),
                    "notice_section":         ef_section.strip(),
                    "act_type":               ef_act,
                    "issuing_officer":        ef_officer.strip(),
                    "officer_designation":    ef_off_desig.strip(),
                    "due_date":               safe_d(ef_due_dt),
                    "notice_type":            ef_type.strip(),
                    "client_data_status":     ef_cd_status,
                    "data_requested":         ef_data_req.strip(),
                    "date_data_requested":    safe_d(ef_dt_dreq),
                    "date_data_received":     safe_d(ef_dt_drecv),
                    "assigned_team_member":   ef_assignee.strip(),
                    "response_filing_date":   safe_d(ef_resp_dt),
                    "response_status":        ef_resp_st,
                    "remarks":                ef_remarks.strip(),
                })
                st.success("✅ Record updated successfully!")
                st.rerun()

    # ── DELETE tab ───────────────────────────────────────────────────
    with tab_delete:
        df_all = load_enriched_df()
        if df_all.empty:
            st.info("No notices to delete.")
        else:
            options_d = {
                f"[{r['id']}] {r['client_name']} / {r['notice_number']}": r["id"]
                for _, r in df_all.iterrows()
            }
            del_label = st.selectbox("Select notice to delete", list(options_d.keys()), key="del_sel")
            del_id    = options_d[del_label]
            row_d     = df_all[df_all["id"] == del_id].iloc[0]

            st.warning(
                f"You are about to **permanently delete**: "
                f"**{row_d['client_name']}** / {row_d['notice_number']} (GSTIN: {row_d['gstin']})"
            )
            if st.button("🗑️ Confirm Delete", type="primary", key="confirm_delete"):
                delete_notice(del_id)
                st.success("Record deleted.")
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Export
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📤 Export":
    section_header("📤 Export Notice Register to Excel")

    df = load_enriched_df()

    if df.empty:
        st.info("No data to export. Import notices first.")
        st.stop()

    st.markdown("""
    <div class="info-banner">
        The exported Excel file uses the same column headers as the import template,
        so you can make updates and upload it again using <strong>Update Existing Records</strong> mode.
    </div>
    """, unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────────
    with st.expander("🔍 Filter export (optional)", expanded=False):
        ex_urgency  = st.multiselect("Urgency",
                                     ["GREEN", "AMBER", "RED", "OVERDUE"],
                                     key="export_urgency")
        ex_response = st.multiselect("Response Status",
                                     sorted(df["response_status"].dropna().unique().tolist()),
                                     key="export_response")
        ex_assignee = st.multiselect("Assigned To",
                                     sorted(df["assigned_team_member"].dropna().unique().tolist()),
                                     key="export_assignee")

    export_df = df.copy()
    if ex_urgency:  export_df = export_df[export_df["urgency"].isin(ex_urgency)]
    if ex_response: export_df = export_df[export_df["response_status"].isin(ex_response)]
    if ex_assignee: export_df = export_df[export_df["assigned_team_member"].isin(ex_assignee)]

    st.markdown(f"**{len(export_df)}** notice(s) will be exported.")

    if len(export_df) > 0:
        xlsx_bytes = export_to_excel(export_df)
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            f"⬇️ Download Excel ({len(export_df)} records)",
            data=xlsx_bytes,
            file_name=f"GST_Notice_Register_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

        # Preview
        preview_cols = [
            "client_name", "gstin", "notice_number", "notice_section",
            "act_type", "due_date", "days_remaining", "urgency",
            "client_data_status", "response_status", "assigned_team_member",
        ]
        st.dataframe(export_df[preview_cols].rename(columns={
            "client_name":          "Client",
            "gstin":                "GSTIN",
            "notice_number":        "Notice No.",
            "notice_section":       "Section",
            "act_type":             "Act",
            "due_date":             "Due Date",
            "days_remaining":       "Days Left",
            "urgency":              "Urgency",
            "client_data_status":   "Client Data Status",
            "response_status":      "Response Status",
            "assigned_team_member": "Assigned To",
        }), use_container_width=True, hide_index=True)
