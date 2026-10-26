import io
import os
import re
import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
import streamlit as st
import pdfplumber
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from google import genai
from google.genai import types

# ---------------------------------------------------------
# Page Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="TaxLitigator AI | AICA Capstone Project",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Database Operations (SQLite Local Store)
# ---------------------------------------------------------
DB_FILE = "taxlitigator_registry.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS analyzed_notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            assessee_name TEXT,
            pan_gstin TEXT,
            act_type TEXT,
            assessment_period TEXT,
            sections TEXT,
            din_ref TEXT,
            notice_date TEXT,
            compliance_deadline TEXT,
            total_alleged_demand REAL,
            monetary_tier TEXT,
            risk_level TEXT,
            has_jurisdiction_defect INTEGER,
            raw_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_case_to_db(assessee_name: str, pan_gstin: str, analysis: 'NoticeAnalysisResult', category_info: dict, has_defect: bool):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    total_amt = sum(t.alleged_amount_inr for t in analysis.transactions)
    c.execute("""
        INSERT INTO analyzed_notices (
            timestamp, assessee_name, pan_gstin, act_type, assessment_period,
            sections, din_ref, notice_date, compliance_deadline,
            total_alleged_demand, monetary_tier, risk_level, has_jurisdiction_defect, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        assessee_name,
        pan_gstin,
        analysis.act_type,
        analysis.assessment_year_or_period,
        ", ".join(analysis.sections_invoked),
        analysis.din_or or "N/A",
        analysis.notice_date or "N/A",
        analysis.compliance_due_date or "N/A",
        total_amt,
        category_info.get("tier", "N/A"),
        category_info.get("risk_level", "MODERATE"),
        1 if has_defect else 0,
        analysis.model_dump_json()
    ))
    conn.commit()
    conn.close()

def fetch_all_cases() -> pd.DataFrame:
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM analyzed_notices ORDER BY id DESC", conn)
    conn.close()
    return df

init_db()

# ---------------------------------------------------------
# Pydantic Schemas for Strict Data Contracts
# ---------------------------------------------------------
class ImpugnedTransaction(BaseModel):
    transaction_type: str = Field(description="Nature of transaction (e.g., ITC Mismatch, Cash Deposit, Bogus Purchase)")
    alleged_amount_inr: float = Field(description="Quantum involved in INR. 0 if unquantified.")
    brief_allegation: str = Field(description="Summary of the assessing officer's allegation")

class LegalGround(BaseModel):
    category: str = Field(description="e.g., Jurisdictional Defect, Natural Justice, Merits, Limitation")
    legal_basis: str = Field(description="Section, Rule, Circular, or Landmark Case Law cited")
    substantive_argument: str = Field(description="Formal legal rebuttal paragraph for the reply")

class NoticeAnalysisResult(BaseModel):
    act_type: str = Field(description="'Income Tax Act, 1961' or 'CGST/SGST Act, 2017'")
    issuing_authority: str = Field(description="Designation of issuing officer or Faceless Center")
    din_or: Optional[str] = Field(None, description="DIN / GST Notice Reference Number")
    notice_date: Optional[str] = Field(None, description="Date of notice (DD/MM/YYYY)")
    assessment_year_or_period: str = Field(description="e.g., AY 2017-18 or FY 2018-19")
    sections_invoked: List[str] = Field(description="Sections cited, e.g., ['Section 148A(b)', 'Section 73']")
    compliance_due_date: Optional[str] = Field(None, description="Statutory reply deadline")
    transactions: List[ImpugnedTransaction] = Field(description="List of additions or allegations")
    preliminary_objections: List[LegalGround] = Field(description="Grounds on procedure, limitation, and merits")

# ---------------------------------------------------------
# Statutory Categorisation & Deterministic Engine
# ---------------------------------------------------------
def categorize_monetary_demand(act_type: str, total_demand: float) -> Dict[str, Any]:
    if "Income Tax" in act_type:
        reopen_tier = "Tier 1: < ₹50 Lakhs (3-Year Bar)" if total_demand < 5000000 else "Tier 2: >= ₹50 Lakhs (10-Year Extended Window)"
        reopen_note = "Barred beyond 3 years from end of AY under Sec 149(1)(a)." if total_demand < 5000000 else "Sec 149(1)(b) applies subject to asset evidence."
        
        # CBDT Circular No. 09/2024 Thresholds
        if total_demand < 6000000:
            dept_status = "Protected from ITAT Appeal (CBDT 09/2024: < ₹60 Lakhs)"
        elif total_demand < 20000000:
            dept_status = "Subject to ITAT, Protected from High Court (< ₹2 Crore)"
        elif total_demand < 50000000:
            dept_status = "Subject to ITAT & High Court, Protected from Supreme Court (< ₹5 Crore)"
        else:
            dept_status = "High-Stakes: Full Judicial Hierarchy Open (>= ₹5 Crore)"

        return {
            "tier": reopen_tier,
            "reopen_note": reopen_note,
            "appeal_status": dept_status,
            "risk_level": "CRITICAL" if total_demand >= 5000000 else "MODERATE"
        }
    else:
        # GST Adjudication Competency under Circular No. 31/05/2018-GST
        if total_demand <= 1000000:
            officer = "Superintendent of Central Tax"
            risk = "LOW"
        elif total_demand <= 10000000:
            officer = "Deputy / Assistant Commissioner"
            risk = "MEDIUM"
        else:
            officer = "Additional / Joint Commissioner"
            risk = "HIGH STAKES"

        pre_deposit = total_demand * 0.10
        return {
            "tier": f"GST Demand Tier: ₹{total_demand:,.2f}",
            "reopen_note": f"Adjudication Jurisdiction: {officer}",
            "appeal_status": f"Mandatory 10% Pre-Deposit for Sec 107 Appeal: ₹{pre_deposit:,.2f}",
            "risk_level": risk
        }

def check_statutory_limitation(act_type: str, sections: List[str], ay: str, notice_ref: Optional[str], amount: float) -> Tuple[List[str], bool]:
    flags = []
    has_defect = False
    
    if "Income Tax" in act_type:
        if any("148" in s for s in sections) and amount < 5000000:
            flags.append("⚠️ **Section 149(1)(a) Limitation Defect**: Escaped income is < ₹50 Lakhs. Notice is barred by limitation if issued beyond 3 years from the end of the relevant AY.")
            has_defect = True
        if not notice_ref or not re.search(r"\b\d{4}/\d{4,}\b", notice_ref):
            flags.append("⚖️ **DIN Defect (CBDT Circular 19/2019)**: Valid DIN missing; communication is non-est and void ab initio.")
            has_defect = True
            
    if "GST" in act_type and any("74" in s for s in sections):
        flags.append("🚨 **Section 74 Invoked**: Rebut wilful misstatement to downgrade to Section 73 (limiting maximum penalty to 10%).")
        
    return flags, has_defect

# ---------------------------------------------------------
# Formal Legal Word Document (.docx) Generator
# ---------------------------------------------------------
def generate_docx_submission(analysis: NoticeAnalysisResult, assessee_name: str, pan_gstin: str, extra_notes: str = "") -> io.BytesIO:
    doc = Document()
    for s in doc.sections:
        s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1)

    p_date = doc.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_date.add_run(f"Date: {datetime.now().strftime('%d-%m-%Y')}").font.size = Pt(10)

    p_to = doc.add_paragraph()
    p_to.add_run(f"To,\nThe {analysis.issuing_authority},\nTax Department.\nRef/DIN: {analysis.din_or or 'N/A'}").font.size = Pt(10.5)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(12)
    p_sub.paragraph_format.space_after = Pt(12)
    r_sub = p_sub.add_run(
        f"SUBJECT: PRELIMINARY WRITTEN SUBMISSIONS AND OBJECTIONS TO NOTICE ISSUED UNDER "
        f"{', '.join(analysis.sections_invoked)} FOR {analysis.assessment_year_or_period}\n"
        f"ASSESSEE: {assessee_name.upper()} | IDENTIFIER: {pan_gstin}"
    )
    r_sub.font.bold = True

    p_body = doc.add_paragraph()
    p_body.add_run(
        f"May it please your honour,\n\n"
        f"The Assessee, {assessee_name}, respectfully submits this point-wise preliminary objection to the captioned notice. "
        f"The Assessee denies each allegation and proposed addition as bad in law and contrary to the record."
    )

    doc.add_heading("I. JURISDICTIONAL AND STATUTORY DEFECTS", level=2)
    for idx, obj in enumerate(analysis.preliminary_objections, start=1):
        p = doc.add_paragraph()
        r1 = p.add_run(f"{idx}. {obj.category} (Reliance: {obj.legal_basis})\n")
        r1.bold = True
        p.add_run(obj.substantive_argument)

    doc.add_heading("II. DISPUTED QUANTUM REBUTTAL STATEMENT", level=2)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Light Shading Accent 1'
    table.rows[0].cells[0].text = 'Item of Dispute'
    table.rows[0].cells[1].text = 'Alleged Quantum (INR)'
    table.rows[0].cells[2].text = 'Assessee Rebuttal Summary'

    for tx in analysis.transactions:
        row = table.add_row().cells
        row[0].text = tx.transaction_type
        row[1].text = f"₹ {tx.alleged_amount_inr:,.2f}"
        row[2].text = tx.brief_allegation

    if extra_notes:
        doc.add_heading("III. ADDITIONAL GROUNDS & PRECEDENTS ON RECORD", level=2)
        doc.add_paragraph(extra_notes)

    doc.add_heading("IV. PRAYER FOR RELIEF", level=2)
    doc.add_paragraph(
        "In view of the statutory limits and judicial precedents cited herein, it is respectfully prayed that:\n"
        "1. The impugned notice and proceedings initiated thereunder be dropped and quashed as void ab initio;\n"
        "2. No penalty or interest under the relevant provisions be levied;\n"
        "3. An opportunity of personal hearing via Video Conferencing be afforded before passing any adverse order."
    )
    doc.add_paragraph(f"\n\nYours Faithfully,\nFor {assessee_name}\n\nAuthorised Representative / Chartered Accountant")

    stream = io.BytesIO()
    doc.save(stream)
    stream.seek(0)
    return stream

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/scales.png", width=56)
    st.title("TaxLitigator AI")
    st.caption("AICA Capstone Project | CA Legal Suite")
    st.markdown("---")
    
    default_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input("Gemini API Key", value=default_key, type="password")
    
    st.subheader("Assessee Master")
    client_name = st.text_input("Name", value="Sunrise Agro Processors Ltd")
    client_id = st.text_input("PAN / GSTIN", value="32AAECS4567F1Z1")
    
    st.markdown("---")
    st.caption("Architecture: Gemini Flash + Pydantic + SQLite + Deterministic Rule Engine")

# ---------------------------------------------------------
# Navigation Tabs
# ---------------------------------------------------------
tab_dash, tab_analyzer, tab_gst = st.tabs([
    "📈 Practice Litigation Registry", 
    "📄 Notice Analyzer & Drafter", 
    "📊 GST ITC Mismatch Calculator"
])

# ---------------------------------------------------------
# TAB 1: EXECUTIVE LITIGATION REGISTRY
# ---------------------------------------------------------
with tab_dash:
    st.subheader("🏛️ Practice Registry: Analyzed Notices & Scrutiny Tracking")
    
    df_cases = fetch_all_cases()
    
    if df_cases.empty:
        st.info("No cases analyzed yet. Analyze a notice in the 'Notice Analyzer' tab to populate this registry.")
    else:
        total_cases = len(df_cases)
        total_exposure = df_cases["total_alleged_demand"].sum()
        total_defects = df_cases["has_jurisdiction_defect"].sum()
        critical_cases = len(df_cases[df_cases["risk_level"].isin(["CRITICAL", "HIGH STAKES"])])

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Matters Tracked", total_cases)
        kpi2.metric("Portfolio Tax Exposure", f"₹ {total_exposure:,.2f}")
        kpi3.metric("Limitation/DIN Defects", total_defects, delta=f"{total_defects} Fatal Defects", delta_color="normal")
        kpi4.metric("High-Stakes Matters", critical_cases, delta="Scrutiny Alert", delta_color="inverse")

        st.markdown("---")
        
        c_filter1, c_filter2 = st.columns([2, 1])
        with c_filter1:
            search_query = st.text_input("🔍 Search by Assessee Name, PAN, or Ref No.")
        with c_filter2:
            act_filter = st.selectbox("Filter by Statute", ["All Acts"] + list(df_cases["act_type"].unique()))

        filtered_df = df_cases.copy()
        if search_query:
            filtered_df = filtered_df[
                filtered_df["assessee_name"].str.contains(search_query, case=False, na=False) |
                filtered_df["pan_gstin"].str.contains(search_query, case=False, na=False) |
                filtered_df["din_ref"].str.contains(search_query, case=False, na=False)
            ]
        if act_filter != "All Acts":
            filtered_df = filtered_df[filtered_df["act_type"] == act_filter]

        display_cols = [
            "id", "timestamp", "assessee_name", "pan_gstin", "act_type", 
            "assessment_period", "total_alleged_demand", "compliance_deadline", "risk_level"
        ]
        
        st.dataframe(
            filtered_df[display_cols].rename(columns={
                "id": "Case #",
                "timestamp": "Analysis Date",
                "assessee_name": "Assessee",
                "pan_gstin": "PAN / GSTIN",
                "act_type": "Act",
                "assessment_period": "Period/AY",
                "total_alleged_demand": "Disputed Demand (₹)",
                "compliance_deadline": "Due Date",
                "risk_level": "Risk Tier"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.subheader("📂 Instant Dossier & Reply Retrieval")
        selected_case_id = st.selectbox("Select Case # to view grounds or download submission:", df_cases["id"].tolist())
        
        if selected_case_id:
            row = df_cases[df_cases["id"] == selected_case_id].iloc[0]
            case_data = NoticeAnalysisResult.model_validate_json(row["raw_json"])
            
            d_col1, d_col2 = st.columns([2, 1])
            with d_col1:
                st.markdown(f"**Assessee:** {row['assessee_name']} ({row['pan_gstin']}) | **Period:** {row['assessment_period']}")
                st.markdown(f"**Sections Cited:** `{row['sections']}` | **DIN / Ref:** `{row['din_ref']}`")
                st.markdown(f"**Monetary Classification:** {row['monetary_tier']}")
                
                with st.expander("Review Stored Grounds of Defense", expanded=False):
                    for g in case_data.preliminary_objections:
                        st.markdown(f"• **{g.category}** ({g.legal_basis}): {g.substantive_argument}")

            with d_col2:
                re_doc = generate_docx_submission(case_data, row['assessee_name'], row['pan_gstin'])
                st.download_button(
                    label=f"📄 Download Legal Reply for Case #{selected_case_id}",
                    data=re_doc,
                    file_name=f"Reply_Case_{selected_case_id}_{row['assessee_name'][:8]}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

# ---------------------------------------------------------
# TAB 2: NOTICE ANALYZER
# ---------------------------------------------------------
with tab_analyzer:
    col_in, col_out = st.columns([1, 1])
    
    with col_in:
        st.subheader("1. Notice Ingestion")
        src = st.radio("Choose Input:", ["Sample Income Tax SCN (Sec 148A)", "Sample GST SCN (DRC-01)", "Upload Notice PDF"])
        
        raw_text = ""
        if src == "Sample Income Tax SCN (Sec 148A)":
            raw_text = (
                "INCOME TAX DEPARTMENT - WARD 1(1), ERNAKULAM\n"
                "DIN: ITBA/AST/F/148A/2024-25/1049281728\n"
                "Date: 15-03-2024\n"
                "To: Sunrise Agro Processors Ltd (PAN: AAECS4567F)\n"
                "NOTICE UNDER SECTION 148A(b) FOR AY 2017-18\n"
                "Information indicates income escaping assessment. Assessee made cash deposits of Rs. 34,50,000/- "
                "in Federal Bank and unexplained vendor balances of Rs. 8,00,000/-. Total: Rs. 42,50,000/-. "
                "Show cause why notice under Section 148 should not be issued by 26-03-2024."
            )
        elif src == "Sample GST SCN (DRC-01)":
            raw_text = (
                "FORM GST DRC-01 - CENTRAL TAX, RANGE II, KOCHI\n"
                "Ref No: ZD320324001928K\n"
                "Date: 04-03-2024\n"
                "To: Sunrise Agro Processors Ltd (GSTIN: 32AAECS4567F1Z1)\n"
                "SHOW CAUSE NOTICE UNDER SECTION 74(1) FOR FY 2018-19\n"
                "Scrutiny reveals excess ITC availment in GSTR-3B over GSTR-2A by Rs. 22,00,000/-. "
                "Deliberate suppression of facts with intent to evade tax. "
                "Tax proposed: Rs. 22,00,000/-, Penalty under Sec 74: Rs. 22,00,000/-. Due date: 03-04-2024."
            )
        else:
            up_doc = st.file_uploader("Upload PDF Notice", type=["pdf"])
            if up_doc:
                raw_text = "\n".join([p.extract_text() or "" for p in pdfplumber.open(up_doc).pages])

        st.text_area("Notice Text", raw_text, height=220)
        btn_analyze = st.button("🚀 Analyze Notice & Log to Dashboard", type="primary")

    with col_out:
        st.subheader("2. AI Analysis & Procedural Guardrails")
        if btn_analyze:
            if not api_key_input:
                st.error("Please enter a Gemini API Key in the sidebar or set GEMINI_API_KEY environment variable.")
            elif not raw_text.strip():
                st.warning("Please provide notice text.")
            else:
                with st.spinner("Analyzing notice and checking limitation rules..."):
                    try:
                        client = genai.Client(api_key=api_key_input)
                        prompt = (
                            "You are a Senior Indian Chartered Accountant & Tax Counsel. "
                            "Parse the notice text. Extract Act, dates, sections, DIN, authority, "
                            "and transactions. Formulate robust preliminary legal objections "
                            "(jurisdiction, limitation, natural justice, and substantive merits)."
                        )

                        # Sequential failover across active models to guarantee uptime
                        candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.8-flash"]
                        response = None
                        last_error = None

                        for model_name in candidate_models:
                            try:
                                response = client.models.generate_content(
                                    model=model_name,
                                    contents=f"{prompt}\n\nNotice Content:\n{raw_text}",
                                    config=types.GenerateContentConfig(
                                        response_mime_type="application/json",
                                        response_schema=NoticeAnalysisResult,
                                        temperature=0.1
                                    )
                                )
                                if response and response.text:
                                    break
                            except Exception as model_err:
                                last_error = model_err
                                continue

                        if not response or not response.text:
                            raise Exception(f"All candidate endpoints failed. Last error: {last_error}")

                        parsed = NoticeAnalysisResult.model_validate_json(response.text)
                        
                        tot_demand = sum(t.alleged_amount_inr for t in parsed.transactions)
                        cat_info = categorize_monetary_demand(parsed.act_type, tot_demand)
                        flags, defect_found = check_statutory_limitation(
                            parsed.act_type, parsed.sections_invoked, parsed.assessment_year_or_period,
                            parsed.din_or, tot_demand
                        )
                        
                        save_case_to_db(client_name, client_id, parsed, cat_info, defect_found)
                        st.session_state["live_res"] = (parsed, cat_info, flags)
                        st.success("✅ Analysis completed and case logged to Practice Registry Dashboard!")
                    except Exception as ex:
                        st.error(f"Analysis failed: {ex}")

        if "live_res" in st.session_state:
            parsed, cat_info, flags = st.session_state["live_res"]
            
            st.info(f"**Classification:** {cat_info['tier']} | **Risk:** {cat_info['risk_level']}")
            st.warning(f"**Appeal Ceiling:** {cat_info['appeal_status']}")
            
            for f in flags:
                st.markdown(f)

            with st.expander("Generated Preliminary Objections", expanded=True):
                for obj in parsed.preliminary_objections:
                    st.markdown(f"**{obj.category}** ({obj.legal_basis}):\n{obj.substantive_argument}\n")

            doc_file = generate_docx_submission(parsed, client_name, client_id)
            st.download_button(
                "📥 Download Ready Legal Submission (.docx)",
                data=doc_file,
                file_name=f"Reply_{client_name[:6]}_{parsed.assessment_year_or_period}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

# ---------------------------------------------------------
# TAB 3: GST ITC MISMATCH
# ---------------------------------------------------------
with tab_gst:
    st.subheader("📊 DRC-01C / Section 73 & 74 ITC Mismatch Defense")
    g1, g2 = st.columns(2)
    with g1:
        itc_3b = st.number_input("ITC Availed in GSTR-3B (₹)", value=2500000.0, step=25000.0)
        itc_2b = st.number_input("ITC Reflected in GSTR-2B (₹)", value=1850000.0, step=25000.0)
        mismatch = itc_3b - itc_2b
        st.metric("Disputed Difference", f"₹ {mismatch:,.2f}", delta="-Excess Claim" if mismatch > 0 else "0", delta_color="inverse")
    with g2:
        st.markdown("**Statutory Defenses Available:**")
        st.markdown("• *Suncraft Energy* (Calcutta HC) - Department must first proceed against supplier.")
        st.markdown("• *Bharti Airtel* (Supreme Court) - GSTR-2A/2B is a facilitative tool, not conclusive.")
        st.markdown("• *Section 73 vs 74* - In absence of mens rea, 100% fraud penalty is illegal.")