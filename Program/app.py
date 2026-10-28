"""
Ind AS 116 Lease Accounting Tool - Streamlit Application
Comprehensive, fully offline desktop application for lease contract OCR,
NLP extraction, Ind AS 116 decision analysis, financial schedules, journal vouchers, and audit reporting.
"""
from datetime import datetime, date
import os
from pathlib import Path
import re
import sys
import pandas as pd
import streamlit as st

# Add current directory to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from modules.config import (
    DEFAULT_CURRENCY, DEFAULT_CURRENCY_SYMBOL, DEFAULT_DISCOUNT_RATE,
    DEFAULT_GUIDANCE_DIR, LOW_VALUE_THRESHOLD_INR, STATUTORY_DISCLAIMER
)
from modules.pdf_processor import PDFProcessor
from modules.extractor import LeaseExtractor, ExtractedField
from modules.ind_as_116_engine import IndAS116Engine, IndAS116Assessment
from modules.financial_engine import FinancialEngine, FinancialSummary
from modules.journal_entries import JournalEntryEngine
from modules.quality_checks import QualityControlEngine
from modules.guidance_rag import GuidanceSearchEngine
from modules.reporting_engine import ReportEngine

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Ind AS 116 Lease Accounting Tool",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1F497D;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #595959;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #F8F9FA;
        border-left: 5px solid #1F497D;
        border-radius: 5px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .badge-review {
        background-color: #FFF3CD;
        color: #856404;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.82rem;
    }
    .badge-verified {
        background-color: #D4EDDA;
        color: #155724;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.82rem;
    }
    .disclaimer-box {
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        border-radius: 6px;
        padding: 12px;
        font-size: 0.85rem;
        color: #6C757D;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# SESSION STATE INITIALIZATION
# =========================================================================

if "pdf_results" not in st.session_state:
    st.session_state.pdf_results = None
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = {}
if "assessment" not in st.session_state:
    st.session_state.assessment = None
if "schedule_df" not in st.session_state:
    st.session_state.schedule_df = None
if "fin_summary" not in st.session_state:
    st.session_state.fin_summary = None
if "journal_entries" not in st.session_state:
    st.session_state.journal_entries = []
if "guidance_engine" not in st.session_state:
    st.session_state.guidance_engine = None
if "custom_tesseract_path" not in st.session_state:
    st.session_state.custom_tesseract_path = ""

# =========================================================================
# SIDEBAR: SYSTEM DIAGNOSTICS & GLOBAL SETTINGS
# =========================================================================

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/contract.png", width=64)
    st.markdown("### **Ind AS 116 Controller**")
    st.caption("Offline Technical Accounting & Audit Automation")
    
    st.divider()
    
    # 1. System Health / Offline Engines
    st.markdown("##### 🔌 **System Diagnostics**")
    
    # Tesseract OCR Check
    pdf_proc = PDFProcessor(custom_tesseract_cmd=st.session_state.custom_tesseract_path or None)
    tess_ok = pdf_proc.is_tesseract_available()
    if tess_ok:
        st.success("✅ Tesseract OCR: Active", icon="🔍")
    else:
        st.warning("⚠️ Tesseract OCR: Not Detected", icon="⚠️")
        with st.expander("Configure Tesseract Path"):
            custom_p = st.text_input(
                "Path to tesseract.exe",
                value=st.session_state.custom_tesseract_path,
                placeholder=r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )
            if custom_p != st.session_state.custom_tesseract_path:
                st.session_state.custom_tesseract_path = custom_p
                st.rerun()

    # Ollama Local LLM Check
    extractor = LeaseExtractor()
    ollama_ok = extractor.is_ollama_available()
    if ollama_ok:
        models = extractor.get_ollama_models()
        st.success(f"✅ Local Ollama LLM: Connected ({len(models)} models)")
        selected_llm = st.selectbox("LLM Model", options=models, index=0 if models else None)
    else:
        st.info("ℹ️ Local Heuristic NLP Engine: Active\n(100% Offline Rule Engine)")
        selected_llm = None

    st.divider()

    # 2. Guidance Folder Settings
    st.markdown("##### 📚 **Technical Guidance Library**")
    guidance_path = st.text_input("Guidance Folder", value=str(DEFAULT_GUIDANCE_DIR))
    
    if st.session_state.guidance_engine is None or st.button("Index Guidance Notes"):
        if os.path.isdir(guidance_path):
            with st.spinner("Indexing Ind AS 116 technical materials..."):
                engine = GuidanceSearchEngine(guidance_path)
                chunks_count = engine.build_index()
                st.session_state.guidance_engine = engine
                st.success(f"Indexed {chunks_count} technical paragraphs from {guidance_path}!")
        else:
            st.error(f"Directory not found: {guidance_path}")

    st.divider()

    # 3. Global Accounting Parameters
    st.markdown("##### ⚙️ **Accounting Policy Defaults**")
    currency = st.selectbox("Functional Currency", ["INR (₹)", "USD ($)", "EUR (€)", "GBP (£)"], index=0)
    curr_symbol = currency.split("(")[1].replace(")", "").strip()
    
    compounding_convention = st.radio(
        "Discount Compounding Method",
        ["Nominal (r / n) [ICAI Standard]", "Effective Compound ((1+r)^(1/n) - 1)"],
        index=0
    )
    comp_method = "nominal" if "Nominal" in compounding_convention else "effective"

    low_val_threshold = st.number_input("Low-Value Asset Cap (₹)", value=LOW_VALUE_THRESHOLD_INR, step=50000.0)

# =========================================================================
# MAIN APP HEADER
# =========================================================================

st.markdown('<div class="main-title">Ind AS 116 Lease Accounting Tool</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Automated PDF Contract Ingestion, Local OCR, NLP Term Extraction, '
    'Amortisation Scheduling, and Audit Deliverables (100% Offline)</div>',
    unsafe_allow_html=True
)

# Multi-Tab Workflow
tab_upload, tab_extract, tab_indas, tab_schedule, tab_je, tab_disclosures, tab_rag, tab_export = st.tabs([
    "1. Ingestion & OCR",
    "2. Extracted Terms",
    "3. Ind AS 116 Assessment",
    "4. Amortisation Schedule",
    "5. Journal Entries",
    "6. Disclosures & Checklist",
    "7. Technical Guidance (RAG)",
    "8. Export Reports"
])

# =========================================================================
# TAB 1: PDF INGESTION & OCR
# =========================================================================

with tab_upload:
    st.subheader("Upload Lease Agreement PDF")
    
    col_up1, col_up2 = st.columns([2, 1])
    
    with col_up1:
        uploaded_file = st.file_uploader(
            "Upload scanned or text-based lease contract (PDF)",
            type=["pdf"],
            help="All files remain completely on your local computer."
        )
        
        pdf_password = st.text_input(
            "PDF Password (if password-protected)",
            type="password",
            help="Leave blank if contract is unencrypted."
        )
        
        force_ocr = st.checkbox("Force full OCR on all pages (recommended for low-quality or hybrid scans)", value=False)
        
        btn_process = st.button("🚀 Process Agreement PDF", type="primary", use_container_width=True)

    with col_up2:
        st.markdown("##### 📄 **Built-in Test Contracts**")
        st.caption("Don't have a PDF ready? Load a pre-configured sample contract:")
        sample_choice = st.selectbox(
            "Select Sample Lease Scenario",
            [
                "Commercial Office Lease (5 Years, 5% Escalation)",
                "Retail Showroom Lease (3 Years, Advance Rent)",
                "Short-Term Equipment Lease (10 Months, Exempt)"
            ]
        )
        if st.button("Load Selected Sample Contract"):
            # Load sample synthetic agreement
            if "Office" in sample_choice:
                sample_pages = {
                    1: (
                        "COMMERCIAL LEASE AGREEMENT\n"
                        "This Lease Agreement is made this 1st day of April 2024 between Horizon Realty Pvt Ltd "
                        "(hereinafter called the Lessor) and Apex Tech Solutions India Ltd (hereinafter called the Lessee).\n"
                        "Demised Premises: Unit No. 402, 4th Floor, Tech Park One, Whitefield, Bangalore.\n"
                        "Term of Lease: The lease shall be for a duration of 60 months commencing from 01-04-2024.\n"
                        "Possession Date: Possession handed over on 01-04-2024."
                    ),
                    2: (
                        "RENTAL AND PAYMENT TERMS\n"
                        "Monthly Rent: The Lessee agrees to pay a monthly rent of Rs. 150,000/- (Rupees One Lakh Fifty Thousand only), "
                        "payable in advance on or before the 7th day of each calendar month.\n"
                        "Rent-Free Period: A fit-out rent free period of 2 months shall apply from commencement.\n"
                        "Escalation Clause: The monthly rent shall escalate by 5% every 12 months.\n"
                        "Security Deposit: Rs. 600,000/- interest-free refundable deposit paid on signing."
                    ),
                    3: (
                        "MAINTENANCE AND OTHER TERMS\n"
                        "Common Area Maintenance (CAM): Rs. 25,000/- per month payable to the facility management agency.\n"
                        "Initial Direct Costs: Lessee has incurred brokerage fees of Rs. 50,000/- and stamp duty of Rs. 25,000/-.\n"
                        "Restoration Obligation: Lessee shall restore premises to original bare shell condition on expiry (estimated cost Rs. 100,000/-).\n"
                        "Option to Renew: Lessee holds an option to extend the lease for a further period of 24 months subject to prevailing market rent.\n"
                        "Discount Rate: Entity Incremental Borrowing Rate (IBR) is 8.50% per annum."
                    )
                }
            elif "Retail" in sample_choice:
                sample_pages = {
                    1: (
                        "RETAIL LEASE DEED\n"
                        "This Retail Lease Deed is entered into on 01-07-2024 by and between City Centre Malls Ltd (Lessor) "
                        "and Trend Fashion Retail Pvt Ltd (Lessee).\n"
                        "Leased Premises: Retail Shop G-12, Ground Floor, Grand Mall, MG Road, Mumbai.\n"
                        "Duration of Lease: Period of lease shall be 36 months w.e.f. 01-07-2024.\n"
                        "Monthly License Fee: Rs. 200,000/- payable in advance on 1st day of each month."
                    ),
                    2: (
                        "TERMS & CONDITIONS\n"
                        "Escalation: Rent shall increase by 10% after 24 months.\n"
                        "CAM Charges: Rs. 40,000/- per month towards central HVAC and maintenance.\n"
                        "Security Deposit: Refundable deposit of Rs. 1,200,000/-.\n"
                        "Purchase Option: Lessee has no option to purchase the demised property."
                    )
                }
            else:
                sample_pages = {
                    1: (
                        "EQUIPMENT LEASE AGREEMENT\n"
                        "This Equipment Lease is made on 01-01-2025 between Alpha Equipment Leasing Ltd (Lessor) "
                        "and Precision Engineering Pvt Ltd (Lessee).\n"
                        "Asset: High Precision CNC Milling Machine Serial #CNC-9982.\n"
                        "Duration: The lease duration shall be 10 months commencing from 01-01-2025.\n"
                        "Monthly Lease Rent: Rs. 45,000/- payable in arrears at the end of each month.\n"
                        "Purchase Option: No option to purchase the machinery."
                    )
                }

            st.session_state.pdf_results = {
                "success": True,
                "pages": sample_pages,
                "full_text": "\n\n".join([f"--- Page {p} ---\n{t}" for p, t in sample_pages.items()]),
                "page_count": len(sample_pages),
                "is_scanned": False,
                "page_types": {p: "text" for p in sample_pages},
                "ocr_applied": False,
                "warnings": ["Synthetic test lease loaded into memory."],
                "error": None
            }
            # Auto-run extraction
            ext = LeaseExtractor()
            st.session_state.extracted_data = ext.extract_all_fields(sample_pages)
            st.success(f"Sample contract '{sample_choice}' loaded successfully! Proceed to Tab 2.")

    # Execute PDF Processing
    if btn_process:
        if uploaded_file is None:
            st.warning("Please upload a PDF file or load a sample contract first.")
        else:
            with st.spinner("Analyzing document structure, detecting scans, and running local OCR..."):
                pdf_bytes = uploaded_file.read()
                proc = PDFProcessor(custom_tesseract_cmd=st.session_state.custom_tesseract_path or None)
                results = proc.process_pdf(
                    pdf_input=pdf_bytes,
                    password=pdf_password if pdf_password.strip() else None,
                    force_ocr=force_ocr
                )
                if results["success"]:
                    st.session_state.pdf_results = results
                    st.success(
                        f"PDF Processed: {results['page_count']} pages | "
                        f"{'Scanned Document' if results['is_scanned'] else 'Text-based Document'} | "
                        f"OCR Applied: {'Yes' if results['ocr_applied'] else 'No'}"
                    )
                    # Automatically extract fields
                    ext = LeaseExtractor()
                    st.session_state.extracted_data = ext.extract_all_fields(
                        results["pages"],
                        use_llm=ollama_ok,
                        selected_model=selected_llm
                    )
                else:
                    st.error(f"Processing Failed: {results['error']}")

    # Display Document Inspection if loaded
    if st.session_state.pdf_results and st.session_state.pdf_results["success"]:
        st.divider()
        st.markdown("#### 🔍 **Document Diagnostic Overview**")
        res = st.session_state.pdf_results
        
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_c1.metric("Total Pages", res["page_count"])
        m_c2.metric("Format", "Scanned Image" if res["is_scanned"] else "Searchable Digital")
        m_c3.metric("OCR Triggered", "Yes (Tesseract)" if res["ocr_applied"] else "No (Direct Text)")
        m_c4.metric("Document Warnings", len(res["warnings"]))

        if res["warnings"]:
            for w in res["warnings"]:
                st.warning(w)

        with st.expander("📄 View Extracted Document Pages"):
            selected_page = st.selectbox("Select Page", options=list(res["pages"].keys()))
            st.text_area(f"Page {selected_page} Content", value=res["pages"].get(selected_page, ""), height=240)

# =========================================================================
# TAB 2: EXTRACTED INFORMATION & REVIEW
# =========================================================================

with tab_extract:
    st.subheader("Extracted Agreement Terms & Traceability")
    st.caption("Review extracted terms with page numbers, confidence levels, and edit any values before running accounting calculations.")

    if not st.session_state.extracted_data:
        st.info("No agreement loaded yet. Please upload a PDF in Tab 1 or click 'Load Selected Sample Contract'.")
    else:
        fields = st.session_state.extracted_data

        # Category 1: Parties & Asset
        with st.expander("1. Parties & Demised Premises", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                lessor_val = st.text_input("Lessor / Landlord Name", value=str(fields.get("lessor_name", {}).value or ""))
                fields["lessor_name"].value = lessor_val
                st.caption(f"Source: Page {fields.get('lessor_name', {}).source_page} | Confidence: {fields.get('lessor_name', {}).confidence:.0%}")
            with c2:
                lessee_val = st.text_input("Lessee / Tenant Name", value=str(fields.get("lessee_name", {}).value or ""))
                fields["lessee_name"].value = lessee_val
                st.caption(f"Source: Page {fields.get('lessee_name', {}).source_page} | Confidence: {fields.get('lessee_name', {}).confidence:.0%}")
            
            asset_val = st.text_input("Demised Premises / Asset Description", value=str(fields.get("asset_description", {}).value or ""))
            fields["asset_description"].value = asset_val
            st.caption(f"Source: Page {fields.get('asset_description', {}).source_page} | Snippet: {fields.get('asset_description', {}).source_snippet[:100]}")

        # Category 2: Dates & Lease Term
        with st.expander("2. Dates & Lease Duration", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                comm_val = st.text_input("Commencement Date (YYYY-MM-DD)", value=str(fields.get("commencement_date", {}).value or "2024-04-01"))
                fields["commencement_date"].value = comm_val
                st.caption(f"Source: Page {fields.get('commencement_date', {}).source_page}")
            with c2:
                poss_val = st.text_input("Possession / Handover Date", value=str(fields.get("possession_date", {}).value or comm_val))
                fields["possession_date"].value = poss_val
            with c3:
                term_val = st.number_input("Lease Term (Months)", value=int(fields.get("lease_term_months", {}).value or 60), min_value=1, step=1)
                fields["lease_term_months"].value = term_val
                st.caption(f"Source: Page {fields.get('lease_term_months', {}).source_page}")

        # Category 3: Rental Payments, Frequency & Escalations
        with st.expander("3. Rental Payments, Frequency & Escalations", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                rent_val = st.number_input(f"Fixed Rent per Period ({curr_symbol})", value=float(fields.get("fixed_rental_amount", {}).value or 100000.0), step=5000.0)
                fields["fixed_rental_amount"].value = rent_val
                st.caption(f"Source: Page {fields.get('fixed_rental_amount', {}).source_page}")
            with c2:
                freq_val = st.selectbox("Payment Frequency", ["Monthly", "Quarterly", "Half-Yearly", "Annual"], index=["Monthly", "Quarterly", "Half-Yearly", "Annual"].index(fields.get("payment_frequency", {}).value or "Monthly"))
                fields["payment_frequency"].value = freq_val
            with c3:
                timing_val = st.selectbox("Payment Timing", ["In Advance", "In Arrears"], index=0 if fields.get("payment_timing", {}).value == "In Advance" else 1)
                fields["payment_timing"].value = timing_val
            with c4:
                rf_val = st.number_input("Rent-Free Months", value=int(fields.get("rent_free_period_months", {}).value or 0), min_value=0, step=1)
                fields["rent_free_period_months"].value = rf_val

            c_esc1, c_esc2, c_esc3 = st.columns(3)
            with c_esc1:
                esc_clause = st.checkbox("Escalation Clause Present?", value=bool(fields.get("escalation_clause", {}).value))
                fields["escalation_clause"].value = esc_clause
            with c_esc2:
                esc_pct = st.number_input("Escalation %", value=float(fields.get("escalation_pct", {}).value or 5.0), step=0.5)
                fields["escalation_pct"].value = esc_pct
            with c_esc3:
                esc_freq = st.number_input("Escalation Interval (Months)", value=int(fields.get("escalation_frequency_months", {}).value or 12), step=6)
                fields["escalation_frequency_months"].value = esc_freq

        # Category 4: Financial Adjustments (Incentives, Deposits, Restoration)
        with st.expander("4. Deposits, Incentives & ROU Adjustments", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                sec_val = st.number_input(f"Security Deposit ({curr_symbol})", value=float(fields.get("security_deposit", {}).value or 0.0), step=10000.0)
                fields["security_deposit"].value = sec_val
            with c2:
                inc_val = st.number_input(f"Lease Incentive ({curr_symbol})", value=float(fields.get("lease_incentive", {}).value or 0.0), step=10000.0)
                fields["lease_incentive"].value = inc_val
            with c3:
                idc_val = st.number_input(f"Initial Direct Costs ({curr_symbol})", value=float(fields.get("initial_direct_costs", {}).value or 0.0), step=5000.0)
                fields["initial_direct_costs"].value = idc_val
            with c4:
                rest_val = st.number_input(f"Restoration Provision ({curr_symbol})", value=float(fields.get("restoration_obligation", {}).value or 0.0), step=10000.0)
                fields["restoration_obligation"].value = rest_val

        # Category 5: Options (Renewal, Termination, Purchase)
        with st.expander("5. Renewal, Termination & Purchase Options", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                ren_val = st.text_input("Renewal Option Clause", value=str(fields.get("renewal_option", {}).value or ""))
                fields["renewal_option"].value = ren_val
                ren_cert = st.checkbox("Renewal Reasonably Certain to be Exercised?", value=bool(fields.get("renewal_certain", {}).value))
                fields["renewal_certain"].value = ren_cert
            with c2:
                term_opt_val = st.text_input("Termination Option Clause", value=str(fields.get("termination_option", {}).value or ""))
                fields["termination_option"].value = term_opt_val
            
            c_pur1, c_pur2, c_pur3 = st.columns(3)
            with c_pur1:
                pur_val = st.checkbox("Purchase Option Available?", value=bool(fields.get("purchase_option", {}).value))
                fields["purchase_option"].value = pur_val
            with c_pur2:
                pur_price = st.number_input(f"Purchase Strike Price ({curr_symbol})", value=float(fields.get("purchase_option_price", {}).value or 0.0), step=50000.0)
                fields["purchase_option_price"].value = pur_price
            with c_pur3:
                pur_cert = st.checkbox("Purchase Reasonably Certain?", value=bool(fields.get("purchase_certain", {}).value))
                fields["purchase_certain"].value = pur_cert

        # Category 6: Non-Lease Components & Discount Rate
        with st.expander("6. Non-Lease Components (CAM) & Discount Rate", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                cam_val = st.number_input(f"Non-Lease CAM Charges per Period ({curr_symbol})", value=float(fields.get("non_lease_components", {}).value or 0.0), step=5000.0)
                fields["non_lease_components"].value = cam_val
            with c2:
                disc_val = st.number_input("Incremental Borrowing Rate / Discount Rate (% p.a.)", value=float(fields.get("discount_rate", {}).value or DEFAULT_DISCOUNT_RATE), step=0.25)
                fields["discount_rate"].value = disc_val
                st.caption("Based on entity borrowing rate for comparable maturity and security.")

        if st.button("💾 Confirm Extracted Data & Proceed to Assessment", type="primary"):
            st.session_state.extracted_data = fields
            st.success("Extracted agreement terms validated! Moving to Tab 3.")

# =========================================================================
# TAB 3: IND AS 116 ASSESSMENT
# =========================================================================

with tab_indas:
    st.subheader("Ind AS 116 Technical Assessment & Exemption Analysis")

    if not st.session_state.extracted_data:
        st.warning("Please upload a contract or load sample data in Tab 1 first.")
    else:
        ext_data = st.session_state.extracted_data

        col_assess_left, col_assess_right = st.columns([1, 1])

        with col_assess_left:
            st.markdown("##### 🏛️ **Entity Elections & Accounting Choices**")
            
            asset_class_choice = st.selectbox(
                "Underlying Asset Class",
                ["Real Estate (Office/Retail/Land)", "Vehicles", "IT Hardware & Laptops", "Office Furniture", "Plant & Machinery"],
                index=0
            )

            elect_st = st.checkbox(
                "Elect Short-Term Lease Exemption (Ind AS 116.5a)",
                value=True,
                help="Applies to leases with lease term <= 12 months and no purchase option."
            )

            elect_lv = st.checkbox(
                "Elect Low-Value Asset Exemption (Ind AS 116.5b)",
                value=True,
                help="Applies to low-value assets like personal computers, small furniture (not real estate or cars)."
            )

            elect_pe = st.checkbox(
                "Elect Practical Expedient to Combine Lease & Non-Lease Components (Ind AS 116.15)",
                value=False,
                help="If elected, CAM and service maintenance are bundled with lease payments and capitalized in ROU asset."
            )

            btn_run_eval = st.button("⚖️ Run Ind AS 116 Decision Tree", type="primary", use_container_width=True)

        # Execute Engine Assessment
        engine = IndAS116Engine(low_value_threshold=low_val_threshold)
        assessment = engine.evaluate_contract(
            extracted_data={k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in ext_data.items()},
            elect_short_term_exemption=elect_st,
            elect_low_value_exemption=elect_lv,
            elect_practical_expedient=elect_pe,
            asset_class="Real Estate" if "Real Estate" in asset_class_choice else ("Vehicles" if "Vehicles" in asset_class_choice else "IT Hardware")
        )
        st.session_state.assessment = assessment

        with col_assess_right:
            st.markdown("##### 📋 **Accounting Conclusion Banner**")
            if assessment.accounting_classification == "ROU_AND_LIABILITY":
                st.success("### **ON-BALANCE SHEET LEASE**\nRecognize Right-of-Use Asset & Lease Liability", icon="🏛️")
            elif assessment.accounting_classification == "SHORT_TERM_EXEMPT":
                st.info("### **SHORT-TERM EXEMPT LEASE**\nStraight-line Rental Expense in P&L (Ind AS 116.5a)", icon="⏱️")
            else:
                st.info("### **LOW-VALUE ASSET EXEMPT LEASE**\nStraight-line Rental Expense in P&L (Ind AS 116.5b)", icon="💡")

            st.write(f"**Technical Rationale:**\n{assessment.classification_rationale}")

        st.divider()

        # Step by step validation cards
        st.markdown("#### **Ind AS 116 Step-by-Step Decision Criteria**")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.metric("1. Identified Asset", "YES" if assessment.identified_asset else "NO")
            st.caption("Explicitly specified premises")
        with s2:
            st.metric("2. Control & Benefits", "YES" if assessment.economic_benefits else "NO")
            st.caption("Substantially all economic utility")
        with s3:
            st.metric("3. Effective Term", f"{assessment.effective_lease_term_months} M")
            st.caption(f"Includes {assessment.renewal_included_months}M renewal")
        with s4:
            st.metric("4. Component Split", "Combined" if assessment.practical_expedient_elected else "Separated")
            st.caption(f"Lease: {curr_symbol}{assessment.lease_component_amount:,.0f} | CAM: {curr_symbol}{assessment.non_lease_component_amount:,.0f}")

# =========================================================================
# TAB 4: AMORTISATION & FINANCIAL SCHEDULE
# =========================================================================

with tab_schedule:
    st.subheader("Financial Amortisation & Depreciation Schedule")

    if not st.session_state.extracted_data or not st.session_state.assessment:
        st.warning("Please complete agreement extraction and assessment first.")
    else:
        fields = st.session_state.extracted_data
        ass = st.session_state.assessment

        # Trigger Calculation
        fin_engine = FinancialEngine(currency=currency)
        comm_d = str(fields.get("commencement_date", {}).value or "2024-04-01")
        term_m = ass.effective_lease_term_months
        rent_p = ass.lease_component_amount
        disc_r = float(fields.get("discount_rate", {}).value or DEFAULT_DISCOUNT_RATE)
        freq = str(fields.get("payment_frequency", {}).value or "Monthly")
        timing = str(fields.get("payment_timing", {}).value or "In Advance")
        rf_m = int(fields.get("rent_free_period_months", {}).value or 0)
        esc_pct = float(fields.get("escalation_pct", {}).value or 0.0) if bool(fields.get("escalation_clause", {}).value) else 0.0
        esc_interval = int(fields.get("escalation_frequency_months", {}).value or 12)

        sched_df, summary = fin_engine.generate_schedule(
            commencement_date_str=comm_d,
            term_months=term_m,
            base_rent_per_period=rent_p,
            annual_discount_rate=disc_r,
            frequency=freq,
            payment_timing=timing,
            rent_free_months=rf_m,
            escalation_pct=esc_pct,
            escalation_interval_months=esc_interval,
            initial_direct_costs=ass.initial_direct_costs,
            lease_incentives=ass.lease_incentives,
            restoration_obligation=ass.restoration_provision,
            purchase_option_price=ass.purchase_option_included,
            residual_value_guarantee=ass.residual_value_guarantee,
            compounding_method=comp_method
        )
        st.session_state.schedule_df = sched_df
        st.session_state.fin_summary = summary

        # Summary Metric Cards
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Initial Lease Liability", f"{curr_symbol} {summary.initial_liability:,.2f}")
        m2.metric("Initial ROU Asset", f"{curr_symbol} {summary.initial_rou_asset:,.2f}")
        m3.metric("Total Payments", f"{curr_symbol} {summary.total_lease_payments:,.2f}")
        m4.metric("Total Interest (P&L)", f"{curr_symbol} {summary.total_interest_expense:,.2f}")
        m5.metric("Total Depreciation", f"{curr_symbol} {summary.total_depreciation_expense:,.2f}")

        st.divider()

        # Visual Trajectory Chart
        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            st.markdown("##### 📈 **Balance Sheet Carrying Amounts Over Time**")
            chart_df = sched_df[["period_idx", "closing_liability", "closing_rou_asset"]].copy()
            chart_df = chart_df.set_index("period_idx")
            chart_df.columns = ["Lease Liability", "ROU Asset"]
            st.line_chart(chart_df, color=["#C00000", "#1F497D"])

        with col_ch2:
            st.markdown("##### 📊 **Periodic P&L Expense vs Cash Outflow**")
            pl_chart_df = sched_df[["period_idx", "total_pl_charge", "gross_payment"]].copy()
            pl_chart_df = pl_chart_df.set_index("period_idx")
            pl_chart_df.columns = ["Total P&L Charge (Interest + Depr)", "Gross Cash Payment"]
            st.area_chart(pl_chart_df, color=["#ED7D31", "#41719C"])

        st.divider()

        # Amortisation Schedule Table
        st.markdown("##### 📑 **Detailed Period Amortisation Schedule**")
        disp_df = sched_df[[
            "period_idx", "payment_date", "opening_liability", "gross_payment",
            "interest_expense", "principal_repayment", "closing_liability",
            "current_liability_portion", "non_current_liability_portion",
            "opening_rou_asset", "depreciation_expense", "closing_rou_asset"
        ]].copy()
        
        disp_df.columns = [
            "Period", "Payment Date", "Op. Liability", "Payment",
            "Interest", "Principal", "Cl. Liability",
            "Current Portion", "Non-Current Portion",
            "Op. ROU", "Depreciation", "Cl. ROU"
        ]
        st.dataframe(disp_df.style.format({
            "Op. Liability": f"{curr_symbol} {{:,.2f}}",
            "Payment": f"{curr_symbol} {{:,.2f}}",
            "Interest": f"{curr_symbol} {{:,.2f}}",
            "Principal": f"{curr_symbol} {{:,.2f}}",
            "Cl. Liability": f"{curr_symbol} {{:,.2f}}",
            "Current Portion": f"{curr_symbol} {{:,.2f}}",
            "Non-Current Portion": f"{curr_symbol} {{:,.2f}}",
            "Op. ROU": f"{curr_symbol} {{:,.2f}}",
            "Depreciation": f"{curr_symbol} {{:,.2f}}",
            "Cl. ROU": f"{curr_symbol} {{:,.2f}}"
        }), height=380, use_container_width=True)

# =========================================================================
# TAB 5: JOURNAL ENTRIES
# =========================================================================

with tab_je:
    st.subheader("Period-wise Accounting Journal Vouchers")

    if st.session_state.assessment is None:
        st.warning("Please complete assessment in Tab 3 first.")
    else:
        je_engine = JournalEntryEngine(currency=currency)
        comm_d = str(st.session_state.extracted_data.get("commencement_date", {}).value or "2024-04-01")
        asset_name = str(st.session_state.extracted_data.get("asset_description", {}).value or "Demised Asset")

        entries = je_engine.generate_all_entries(
            assessment=st.session_state.assessment,
            summary=st.session_state.fin_summary,
            schedule_df=st.session_state.schedule_df,
            commencement_date=comm_d,
            asset_description=asset_name
        )
        st.session_state.journal_entries = entries
        je_df = je_engine.to_dataframe(entries)

        # Verification metrics
        tot_dr = je_df["debit_amount"].sum()
        tot_cr = je_df["credit_amount"].sum()
        balanced = abs(tot_dr - tot_cr) < 0.05

        c_v1, c_v2, c_v3 = st.columns(3)
        c_v1.metric("Total Debits", f"{curr_symbol} {tot_dr:,.2f}")
        c_v2.metric("Total Credits", f"{curr_symbol} {tot_cr:,.2f}")
        if balanced:
            c_v3.success("✅ Vouchers Perfectly Balanced (Dr = Cr)")
        else:
            c_v3.error(f"❌ Imbalance: {curr_symbol} {abs(tot_dr - tot_cr):,.2f}")

        st.divider()

        # Filter Entries
        f_period = st.selectbox("Filter by Period / Event", ["All Vouchers", "Commencement Entry", "Lease Payments", "Depreciation", "Lease Expiry"])
        if f_period == "Commencement Entry":
            filtered_df = je_df[je_df["period"] == "Commencement"]
        elif f_period == "Lease Payments":
            filtered_df = je_df[je_df["account_head"].str.contains("Bank|Liability|Interest", case=False) & (je_df["period"] != "Commencement")]
        elif f_period == "Depreciation":
            filtered_df = je_df[je_df["account_head"].str.contains("Depreciation", case=False)]
        elif f_period == "Lease Expiry":
            filtered_df = je_df[je_df["period"] == "Lease Expiry"]
        else:
            filtered_df = je_df

        st.dataframe(filtered_df[[
            "entry_id", "date", "period", "account_head", "account_category", "debit_amount", "credit_amount", "narration"
        ]].style.format({
            "debit_amount": lambda x: f"{curr_symbol} {x:,.2f}" if x > 0 else "-",
            "credit_amount": lambda x: f"{curr_symbol} {x:,.2f}" if x > 0 else "-"
        }), height=400, use_container_width=True)

# =========================================================================
# TAB 6: DISCLOSURES & REVIEWER CHECKLIST
# =========================================================================

with tab_disclosures:
    st.subheader("Ind AS 116 Statutory Disclosures & Auditor Review Checklist")

    if not st.session_state.extracted_data:
        st.info("No agreement loaded yet. Please upload a contract in Tab 1 or click 'Load Selected Sample Contract'.")
    else:
        if st.session_state.fin_summary is not None and st.session_state.schedule_df is not None:
            sm = st.session_state.fin_summary
            df_sch = st.session_state.schedule_df
            ass = st.session_state.assessment

            st.markdown("##### 📊 **Maturity Analysis of Undiscounted Lease Payments (Ind AS 116.58)**")
            # Build maturity buckets
            p_yr = 12 if sm.payment_frequency == "Monthly" else (4 if sm.payment_frequency == "Quarterly" else 1)
            tot_rows = len(df_sch)
            
            y1_pmts = df_sch.iloc[0: min(tot_rows, p_yr)]["gross_payment"].sum()
            y2_pmts = df_sch.iloc[p_yr: min(tot_rows, 2 * p_yr)]["gross_payment"].sum() if tot_rows > p_yr else 0.0
            y3_pmts = df_sch.iloc[2 * p_yr: min(tot_rows, 3 * p_yr)]["gross_payment"].sum() if tot_rows > 2 * p_yr else 0.0
            y4_pmts = df_sch.iloc[3 * p_yr: min(tot_rows, 4 * p_yr)]["gross_payment"].sum() if tot_rows > 3 * p_yr else 0.0
            y5_pmts = df_sch.iloc[4 * p_yr: min(tot_rows, 5 * p_yr)]["gross_payment"].sum() if tot_rows > 4 * p_yr else 0.0
            later_pmts = df_sch.iloc[5 * p_yr:]["gross_payment"].sum() if tot_rows > 5 * p_yr else 0.0
            total_undisc = df_sch["gross_payment"].sum()
            pv_liability = sm.initial_liability

            mat_df = pd.DataFrame([
                {"Maturity Bucket": "Not later than 1 year (Year 1)", "Undiscounted Cash Flow": y1_pmts},
                {"Maturity Bucket": "Between 1 and 2 years (Year 2)", "Undiscounted Cash Flow": y2_pmts},
                {"Maturity Bucket": "Between 2 and 3 years (Year 3)", "Undiscounted Cash Flow": y3_pmts},
                {"Maturity Bucket": "Between 3 and 4 years (Year 4)", "Undiscounted Cash Flow": y4_pmts},
                {"Maturity Bucket": "Between 4 and 5 years (Year 5)", "Undiscounted Cash Flow": y5_pmts},
                {"Maturity Bucket": "Later than 5 years", "Undiscounted Cash Flow": later_pmts},
                {"Maturity Bucket": "Total Undiscounted Lease Commitments", "Undiscounted Cash Flow": total_undisc},
                {"Maturity Bucket": "Less: Future Finance Charges (Discount)", "Undiscounted Cash Flow": total_undisc - pv_liability},
                {"Maturity Bucket": "Present Value of Lease Liabilities Recognized", "Undiscounted Cash Flow": pv_liability}
            ])
            st.table(mat_df.style.format({"Undiscounted Cash Flow": f"{curr_symbol} {{:,.2f}}"}))

            st.divider()

            # Balance Sheet Presentation Split
            st.markdown("##### 🏛️ **Balance Sheet Presentation (Current vs Non-Current Split)**")
            first_p = df_sch.iloc[0]
            c_split1, c_split2, c_split3 = st.columns(3)
            c_split1.metric("Current Lease Liability (Due <= 12M)", f"{curr_symbol} {first_p['current_liability_portion']:,.2f}")
            c_split2.metric("Non-Current Lease Liability (> 12M)", f"{curr_symbol} {first_p['non_current_liability_portion']:,.2f}")
            c_split3.metric("Total Closing Liability", f"{curr_symbol} {first_p['closing_liability']:,.2f}")

            st.divider()

        # Reviewer Quality Checks & Checklist
        st.markdown("##### 🔍 **Audit Review Points & Chartered Accountant Sign-Off Checklist**")
        qc = QualityControlEngine()
        val_res = qc.run_checks(st.session_state.extracted_data, st.session_state.assessment)

        if val_res.errors:
            for err in val_res.errors:
                st.error(f"❌ {err}")
        if val_res.warnings:
            for wrn in val_res.warnings:
                st.warning(f"⚠️ {wrn}")
        if val_res.review_points:
            for pt in val_res.review_points:
                st.info(f"💡 {pt}")

        checklist_items = qc.get_reviewer_checklist()
        st.markdown("###### **Formal Sign-off Questions:**")
        for chk in checklist_items:
            c_chk1, c_chk2 = st.columns([4, 1])
            c_chk1.write(f"**[{chk['id']}] {chk['category']}**: {chk['question']} *(Ref: {chk['reference']})*")
            c_chk2.checkbox("Sign Off", value=True, key=f"sign_{chk['id']}")

    st.markdown("---")
    st.markdown(f'<div class="disclaimer-box"><b>STATUTORY DISCLAIMER:</b><br>{STATUTORY_DISCLAIMER}</div>', unsafe_allow_html=True)

# =========================================================================
# TAB 7: GUIDANCE LIBRARY (OFFLINE RAG SEARCH)
# =========================================================================

with tab_rag:
    st.subheader("Technical Guidance Library & Offline Search (RAG)")
    st.caption("Search across ICAI Guidance Notes, PwC Manuals, and KPMG Technical Documents stored in your local folder.")

    rag_engine = st.session_state.guidance_engine
    if rag_engine is None or not rag_engine.is_indexed:
        st.info("Guidance documents are not yet indexed. Click below to index the guidance library.")
        if st.button("Index Guidance Library Now"):
            with st.spinner("Indexing technical documents..."):
                engine = GuidanceSearchEngine(guidance_path)
                cnt = engine.build_index()
                st.session_state.guidance_engine = engine
                st.success(f"Indexed {cnt} paragraphs from {guidance_path}!")
                st.rerun()
    else:
        st.write(f"📚 **Indexed Knowledge Base:** {len(rag_engine.chunks)} searchable paragraphs from `{guidance_path}`.")

        search_query = st.text_input(
            "Enter Accounting Inquiry or Keyword",
            value="practical expedient non-lease components",
            placeholder="e.g. low-value exemption, incremental borrowing rate, rent free period, lease modification"
        )
        
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            if st.button("🔍 Search: Low-Value Exemption"):
                search_query = "low value asset exemption criteria"
        with col_q2:
            if st.button("🔍 Search: Practical Expedient"):
                search_query = "practical expedient combine lease non lease"
        with col_q3:
            if st.button("🔍 Search: Incremental Borrowing Rate"):
                search_query = "incremental borrowing rate definition"

        if search_query:
            results = rag_engine.search(search_query, top_k=5)
            if results:
                st.markdown(f"##### **Search Results for:** *'{search_query}'*")
                for i, r in enumerate(results, 1):
                    with st.expander(f"Result {i}: {r.doc_name} ({r.page_or_section}) - Match Score: {r.relevance_score}%", expanded=(i == 1)):
                        st.markdown(f"**Document:** `{r.doc_name}` | **Location:** `{r.page_or_section}`")
                        st.write(r.snippet)
            else:
                st.info("No matching passages found for this query.")

# =========================================================================
# TAB 8: EXPORT REPORTS
# =========================================================================

with tab_export:
    st.subheader("Generate Audit Reports & Excel Workbooks")
    st.caption("Generate client-ready Excel and Word deliverables with 1 click.")

    if st.session_state.extracted_data and st.session_state.assessment and st.session_state.schedule_df is not None:
        rep_engine = ReportEngine(currency_symbol=curr_symbol)
        
        # Prepare review points for export
        qc = QualityControlEngine()
        val_res = qc.run_checks(st.session_state.extracted_data, st.session_state.assessment)
        export_points = val_res.review_points + val_res.warnings

        c_exp1, c_exp2 = st.columns(2)

        with c_exp1:
            st.markdown("#### 📊 **Excel Accounting Schedule**")
            st.write(
                "Complete audit model with 9 dedicated worksheets:\n"
                "- 1. Input Summary\n"
                "- 2. Extracted Agreement Data (with Page Traceability)\n"
                "- 3. Ind AS 116 Analysis\n"
                "- 4. Lease Liability Schedule\n"
                "- 5. ROU Asset Schedule\n"
                "- 6. Journal Entries\n"
                "- 7. Financial Statement Presentation\n"
                "- 8. Disclosures\n"
                "- 9. Audit Review Points"
            )
            with st.spinner("Generating Excel Workbook..."):
                excel_bytes = rep_engine.generate_excel_workbook(
                    extracted_data={k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in st.session_state.extracted_data.items()},
                    assessment=st.session_state.assessment,
                    summary=st.session_state.fin_summary,
                    schedule_df=st.session_state.schedule_df,
                    journal_entries=st.session_state.journal_entries,
                    review_points=export_points
                )
            
            st.download_button(
                label="📥 Download Lease_Accounting_Schedule.xlsx",
                data=excel_bytes,
                file_name="Lease_Accounting_Schedule.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

        with c_exp2:
            st.markdown("#### 📝 **Word Accounting Memo**")
            st.write(
                "Executive audit memorandum in Word format:\n"
                "- Executive Summary\n"
                "- Contract Terms & Page Traceability Table\n"
                "- Technical Ind AS 116 Classification\n"
                "- Period Amortisation & Journal Vouchers\n"
                "- Balance Sheet, P&L & Cash Flow Presentation\n"
                "- Disclosure Checklist\n"
                "- Sign-off Block for Chartered Accountant"
            )
            with st.spinner("Generating Word Memo..."):
                word_bytes = rep_engine.generate_word_document(
                    extracted_data={k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in st.session_state.extracted_data.items()},
                    assessment=st.session_state.assessment,
                    summary=st.session_state.fin_summary,
                    schedule_df=st.session_state.schedule_df,
                    journal_entries=st.session_state.journal_entries,
                    review_points=export_points
                )
            
            st.download_button(
                label="📥 Download Lease_Summary.docx",
                data=word_bytes,
                file_name="Lease_Summary.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True
            )
    else:
        st.warning("Please upload a contract and generate schedules in the previous tabs to enable report downloads.")
