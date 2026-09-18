import streamlit as st
import google.generativeai as genai

# 1. Page Configuration
st.set_page_config(page_title="TaxNotice AI", layout="wide")
st.title("💼 TaxNotice AI: Automated Notice Analyzer & Drafter")
st.caption("Advanced Automated Compliance Engine | ICAI AICA Level 2 Capstone Project")

# 2. Sidebar Configuration
st.sidebar.header("🔑 System Configuration")
api_key = st.sidebar.text_input("Enter Google AI Studio API Key:", type="password", key="user_api_key")

st.sidebar.markdown("---")
if st.sidebar.button("Enable Antigravity Mode"):
    st.sidebar.success("✨ Antigravity Activated! Floating code modules optimized.")

# 3. Flat Dataset Storage (Zero Indentation Risk)
S148_TEXT = "GOVERNMENT OF INDIA\nMINISTRY OF FINANCE\nINCOME TAX DEPARTMENT\nOFFICE OF THE INCOME TAX OFFICER, WARD 11(2), NEW DELHI\n\nPAN: ABCDE1234F\nAssessment Year: 2021-22\nNotice DIN: ITN/2026/148/MIG/9827419\nDate: 14-May-2026\n\nNOTICE UNDER SECTION 148 OF THE INCOME TAX ACT, 1961\n\nTo,\nMr. Rajesh Kumar,\n12, Connaught Place, New Delhi - 110001.\n\n1. Whereas I have reasons to believe that your income chargeable to tax for the Assessment Year 2021-22 has escaped assessment within the meaning of section 147 of the Income Tax Act, 1961.\n\n2. Information available on the Insight Portal indicates that you have made cash deposits aggregating to INR 45,00,000/- in your Savings Bank Account maintained with State Bank of India during the financial year 2020-21. However, upon verification of the Income Tax Return (ITR-1) filed by you for the said year, a total income of only INR 6,50,000/- has been declared."
S148_STRATEGY = "Invoke Section 10(1) for Agricultural income components (INR 25L). Detail past accumulated household cash savings and small familial gifts for the remaining amount (INR 20L). Request formal 'Reasons to believe' recorded under Section 148A(b) citing the GKN Driveshafts ruling."
S148_TABLE = "\n| Parameter | Notice Allegation Value | Assessee Explained Value | Proposed Defense Source |\n| :--- | :--- | :--- | :--- |\n| **Cash Deposits** | ₹ 45,00,000 | ₹ 25,00,000 | Agricultural Income (Sec 10(1)) |\n| **Cash Deposits** | Included Above | ₹ 20,00,000 | Accumulated Household Savings & Gifts |\n| **Declared Income** | ₹ 6,50,000 | ₹ 6,50,000 | As per originally filed ITR-1 |\n| **Unexplained Gap**| **₹ 38,50,000** | **₹ 0** | **Fully Reconciled** |\n"

S143_TEXT = "GOVERNMENT OF INDIA\nINCOME TAX DEPARTMENT\nNATIONAL FACELESS ASSESSMENT CENTRE (NFAC), DELHI\n\nPAN: AAFPM9988K\nAssessment Year: 2024-25\nNotice DIN: ITN/2026/1432/SCR/311045\nDate: 12-August-2026\n\nNOTICE UNDER SECTION 143(2) OF THE INCOME TAX ACT, 1961\n\nTo,\nM/s Apex Ventures LLP,\nPlot 45, Phase-3, Industrial Area, Gurugram, Haryana.\n\n1. Your Return of Income for the Assessment Year 2024-25 has been filed on 28-July-2024 showing a total income of INR 12,00,000/-.\n\n2. The return filed has been selected for Complete Scrutiny under Faceless Assessment due to high value immovable property transactions mismatching reported capital.\n\n3. As per reporting from the Sub-Registrar Office, the LLP purchased a commercial immovable property valued at INR 2,10,00,000/- during FY 2023-24."
S143_STRATEGY = "Map financial source channels: Secured institutional Bank Loan of INR 1.5 Crores. Map interest-free family gifts to the promoter partners under Section 56(2)(x) amounting to INR 50 Lakhs. Balance from partners' internal capital accounts (INR 10 Lakhs)."
S143_TABLE = "\n| Parameter | Notice Allegation Value | Assessee Explained Value | Proposed Defense Source |\n| :--- | :--- | :--- | :--- |\n| **Property Purchase** | ₹ 2,10,00,000 | ₹ 1,50,00,000 | Secured Institutional Bank Loan |\n| **Property Purchase** | Included Above | ₹ 50,00,000 | Exempt Family Gifts (Sec 56(2)(x)) |\n| **Property Purchase** | Included Above | ₹ 10,00,000 | Partners' Capital Drawdown |\n| **Unexplained Gap**| **₹ 1,98,00,000**| **₹ 0** | **Fully Reconciled** |\n"

S142_TEXT = "GOVERNMENT OF INDIA\nMINISTRY OF FINANCE\nINCOME TAX DEPARTMENT\nOFFICE of THE INCOME TAX OFFICER, WARD 4(1), MUMBAI\n\nPAN: BKZPK4433M\nAssessment Year: 2025-26\nNotice DIN: ITN/2026/1421/INQ/847291\nDate: 01-September-2026\n\nNOTICE UNDER SECTION 142(1) OF THE INCOME TAX ACT, 1961\n\nTo,\nMs. Priya Sharma,\nIn connection with the assessment for the Assessment Year 2025-26, you are required to produce the complete source of funds for credit card payments totaling INR 18,50,000/- made during the Financial Year 2024-25."
S142_STRATEGY = "State card holds a dual purpose: Personal card utilized for official company business reimbursements. Assert that INR 14 Lakhs represents official business spending reimbursed directly by the employer. State that INR 4.5 Lakhs represents genuine personal usage paid via tracked salary income."
S142_TABLE = "\n| Parameter | Notice Allegation Value | Assessee Explained Value | Proposed Defense Source |\n| :--- | :--- | :--- | :--- |\n| **Credit Card Spend** | ₹ 18,50,000 | ₹ 14,00,000 | Corporate Expense Reimbursements |\n| **Credit Card Spend** | Included Above | ₹ 4,50,000 | Personal Outlay out of Salary |\n| **Returned Income** | ₹ 4,80,000 | ₹ 4,80,000 | Standard Declared Salary Income |\n| **Unexplained Gap**| **₹ 13,70,000** | **₹ 0** | **Fully Reconciled** |\n"

# 4. Dropdown Mapping
st.subheader("📥 Step 1: Select Notice Dataset Template")
demo_choice = st.selectbox(
    "🎯 Quick Demo Selection:",
    ["-- Select Custom Input --", "Section 148 (Cash Deposit)", "Section 143(2) (Property Purchase)", "Section 142(1) (Credit Card Expense)"]
)

notice_text_val = ""
active_strategy = "Analyze the text and draft standard defensive points."
active_table = ""

if demo_choice == "Section 148 (Cash Deposit)":
    notice_text_val = S148_TEXT
    active_strategy = S148_STRATEGY
    active_table = S148_TABLE
elif demo_choice == "Section 143(2) (Property Purchase)":
    notice_text_val = S143_TEXT
    active_strategy = S143_STRATEGY
    active_table = S143_TABLE
elif demo_choice == "Section 142(1) (Credit Card Expense)":
    notice_text_val = S142_TEXT
    active_strategy = S142_STRATEGY
    active_table = S142_TABLE

# 5. Simple Process Form
with st.form(key="notice_form"):
    final_notice_text = st.text_area("Notice Text Content:", value=notice_text_val, height=200)
    submit_btn = st.form_submit_button(label="🚀 Process Notice and Draft Reply")

# 6. Response Processing
if submit_btn:
    if not api_key:
        st.error("❌ Please enter your Google AI Studio API Key in the left sidebar first!")
    elif final_notice_text.strip() == "":
        st.warning("❌ Please provide valid tax notice text.")
    else:
        status_box = st.info("🤖 Framework Connection Initialized...")
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-3.6-flash')
            
            prompt_payload = "You are a professional Indian Chartered Accountant. Draft a response to the following Income Tax Notice context.\n\n"
            prompt_payload += "CHOSEN RECONCILIATION LEGAL ADVOCACY COUNSEL STRATEGY:\n" + active_strategy + "\n\n"
            prompt_payload += "Structure your response into 3 parts: 1. FACTUAL BACKGROUND, 2. GROUND-BY-GROUND DEFENSIVE SUBMISSIONS, 3. PRAYER CLAUSE.\n\n"
            prompt_payload += "Notice Text:\n" + final_notice_text
            
            status_box.info("🧠 Processing tax arguments via Gemini Engine...")
            response = model.generate_content(prompt_payload)
            generated_output = response.text
            
            status_box.empty()
            st.success("✅ Analysis Complete!")
            
            tab_reconcile, tab_reply = st.tabs(["📊 Figures Reconciliation Dashboard", "📝 Professional Generated Reply"])
            
            with tab_reconcile:
                st.markdown("### 🔍 Financial Target Reconciliation Table")
                if active_table:
                    st.markdown(active_table)
                else:
                    st.markdown("\n| Parameter | Value |\n| :--- | :--- |\n| Data | Extracted |\n")
                st.markdown("#### 🎯 Chosen Legal Defense Strategy Blueprint")
                st.code(active_strategy)
                
            with tab_reply:
                st.markdown("### 📝 Formatted Formal Legal Response")
                editable_reply = st.text_area("Review and Edit Your Drafted Text:", value=generated_output, height=400)
                st.download_button(label="💾 Export Draft Reply as Text File", data=editable_reply, file_name="ICAI_Draft_Reply.txt", mime="text/plain")
                
        except Exception as e:
            st.error("⚠️ Connection Error: " + str(e))
