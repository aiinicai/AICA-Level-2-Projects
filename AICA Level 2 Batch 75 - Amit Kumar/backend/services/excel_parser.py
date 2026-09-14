import os
import pandas as pd
from sqlalchemy.orm import Session
from models import (
    TrialBalanceLine, ARAgeing, APAgeing, CWIPAgeing,
    RelatedParty, Borrowing, Contingency
)
from services.mapping_engine import suggest_mapping_for_line

def parse_trial_balance(file_path: str, client_id: int, db: Session):
    df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path)
    db.query(TrialBalanceLine).filter(TrialBalanceLine.client_id == client_id).delete()
    
    lines = []
    for _, row in df.iterrows():
        ledger_name = str(row.get('Ledger Name', '')).strip()
        if not ledger_name or ledger_name == 'nan':
            continue
        
        orig_group = str(row.get('Original Group', ''))
        cy_amt = float(row.get('Current Year Amount', 0.0) or 0.0)
        py_amt = float(row.get('Previous Year Amount', 0.0) or 0.0)
        
        mapped = suggest_mapping_for_line(ledger_name, orig_group, db)
        
        tb_line = TrialBalanceLine(
            client_id=client_id,
            ledger_code=str(row.get('Ledger Code', '')),
            ledger_name=ledger_name,
            original_group=orig_group,
            cy_amount=cy_amt,
            py_amount=py_amt,
            suggested_classification=mapped['final_classification'],
            final_classification=mapped['final_classification'],
            financial_statement=mapped['financial_statement'],
            note_number=mapped['note_number'],
            current_non_current=mapped['current_non_current'],
            user_override=False
        )
        db.add(tb_line)
        lines.append(tb_line)
    
    db.commit()
    return lines


def parse_ar_ageing(file_path: str, client_id: int, db: Session):
    df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path)
    db.query(ARAgeing).filter(ARAgeing.client_id == client_id).delete()
    
    records = []
    for _, row in df.iterrows():
        name = str(row.get('Customer Name', '')).strip()
        if not name or name == 'nan': continue
        
        rec = ARAgeing(
            client_id=client_id,
            customer_name=name,
            l6m=float(row.get('< 6 Months', 0.0) or 0.0),
            m6_1y=float(row.get('6M - 1Y', 0.0) or 0.0),
            y1_2y=float(row.get('1Y - 2Y', 0.0) or 0.0),
            y2_3y=float(row.get('2Y - 3Y', 0.0) or 0.0),
            mor_3y=float(row.get('> 3Y', 0.0) or 0.0),
            total=float(row.get('Total Amount', 0.0) or 0.0),
            category=str(row.get('Classification Category', 'Undisputed Considered Good')),
            disputed=str(row.get('Disputed Status', 'No')),
            py_total=float(row.get('Previous Year Total', 0.0) or 0.0)
        )
        db.add(rec)
        records.append(rec)
    db.commit()
    return records


def parse_ap_ageing(file_path: str, client_id: int, db: Session):
    df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path)
    db.query(APAgeing).filter(APAgeing.client_id == client_id).delete()
    
    records = []
    for _, row in df.iterrows():
        name = str(row.get('Vendor Name', '')).strip()
        if not name or name == 'nan': continue
        
        rec = APAgeing(
            client_id=client_id,
            vendor_name=name,
            msme=str(row.get('MSME Status', 'No')),
            l1y=float(row.get('< 1 Year', 0.0) or 0.0),
            y1_2y=float(row.get('1Y - 2Y', 0.0) or 0.0),
            y2_3y=float(row.get('2Y - 3Y', 0.0) or 0.0),
            mor_3y=float(row.get('> 3Y', 0.0) or 0.0),
            outstanding_amount=float(row.get('Total Outstanding', 0.0) or 0.0),
            category=str(row.get('Classification Category', 'Undisputed Dues')),
            disputed=str(row.get('Disputed Status', 'No')),
            py_outstanding_amount=float(row.get('Previous Year Total', 0.0) or 0.0)
        )
        db.add(rec)
        records.append(rec)
    db.commit()
    return records


def parse_cwip_ageing(file_path: str, client_id: int, db: Session):
    df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path)
    db.query(CWIPAgeing).filter(CWIPAgeing.client_id == client_id).delete()
    
    records = []
    for _, row in df.iterrows():
        name = str(row.get('Project Name / Description', '')).strip()
        if not name or name == 'nan': continue
        
        rec = CWIPAgeing(
            client_id=client_id,
            project_name=name,
            l1y=float(row.get('< 1 Year', 0.0) or 0.0),
            y1_2y=float(row.get('1Y - 2Y', 0.0) or 0.0),
            y2_3y=float(row.get('2Y - 3Y', 0.0) or 0.0),
            mor_3y=float(row.get('> 3Y', 0.0) or 0.0),
            closing_cwip=float(row.get('Total CWIP Amount', 0.0) or 0.0),
            status=str(row.get('Project Status', 'In Progress')),
            reason_delay=str(row.get('Reason for Overdue/Cost Overrun', '')),
            py_closing_cwip=float(row.get('Previous Year Total', 0.0) or 0.0)
        )
        db.add(rec)
        records.append(rec)
    db.commit()
    return records


def parse_related_parties(file_path: str, client_id: int, db: Session):
    df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path)
    db.query(RelatedParty).filter(RelatedParty.client_id == client_id).delete()
    
    records = []
    for _, row in df.iterrows():
        name = str(row.get('Related Party Name', '')).strip()
        if not name or name == 'nan': continue
        
        rec = RelatedParty(
            client_id=client_id,
            name=name,
            relationship=str(row.get('Relationship Type', 'KMP')),
            nature_tx=str(row.get('Nature of Transaction', '')),
            opening_bal=float(row.get('Opening Balance', 0.0) or 0.0),
            debit_tx=float(row.get('Debit Transactions', 0.0) or 0.0),
            credit_tx=float(row.get('Credit Transactions', 0.0) or 0.0),
            closing_bal=float(row.get('Closing Balance', 0.0) or 0.0),
            category=str(row.get('Party Category', 'KMP/Relative')),
            terms=str(row.get('Terms and Conditions', '')),
            py_closing_bal=float(row.get('Previous Year Closing', 0.0) or 0.0)
        )
        db.add(rec)
        records.append(rec)
    db.commit()
    return records


def parse_borrowings(file_path: str, client_id: int, db: Session):
    df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path)
    db.query(Borrowing).filter(Borrowing.client_id == client_id).delete()
    
    records = []
    for _, row in df.iterrows():
        lender = str(row.get('Lender / Bank Name', '')).strip()
        if not lender or lender == 'nan': continue
        
        rec = Borrowing(
            client_id=client_id,
            lender_name=lender,
            loan_type=str(row.get('Facility / Loan Type', 'Term Loan')),
            secured_unsecured=str(row.get('Secured / Unsecured', 'Secured')),
            current_non_current=str(row.get('Current / Non-Current Classification', 'Non-current')),
            opening_bal=float(row.get('Opening Balance', 0.0) or 0.0),
            additions=float(row.get('Fresh Drawals / Additions', 0.0) or 0.0),
            repayments=float(row.get('Repayments / Disbursements', 0.0) or 0.0),
            closing_bal=float(row.get('Closing Outstanding', 0.0) or 0.0),
            interest_rate=str(row.get('Interest Rate %', '')),
            security_details=str(row.get('Security Details', '')),
            repayment_terms=str(row.get('Repayment Terms', '')),
            is_default=str(row.get('Default in Repayment', 'No')),
            default_amount=float(row.get('Default Amount', 0.0) or 0.0),
            py_closing_bal=float(row.get('Previous Year Closing', 0.0) or 0.0)
        )
        db.add(rec)
        records.append(rec)
    db.commit()
    return records


def parse_contingencies(file_path: str, client_id: int, db: Session):
    df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path)
    db.query(Contingency).filter(Contingency.client_id == client_id).delete()
    
    records = []
    for _, row in df.iterrows():
        nature = str(row.get('Nature of Contingency', '')).strip()
        if not nature or nature == 'nan': continue
        
        rec = Contingency(
            client_id=client_id,
            nature=nature,
            forum=str(row.get('Forum/Authority', '')),
            cy_amount=float(row.get('Current Year Amount', 0.0) or 0.0),
            py_amount=float(row.get('Previous Year Amount', 0.0) or 0.0),
            assessment=str(row.get('Management Assessment', '')),
            provision_required=str(row.get('Whether Provision Required', 'No')),
            remarks=str(row.get('Remarks', ''))
        )
        db.add(rec)
        records.append(rec)
    db.commit()
    return records


def generate_sample_templates(sample_dir: str):
    os.makedirs(sample_dir, exist_ok=True)
    
    # 1. Trial Balance Template (100% Balanced CY & PY)
    tb_df = pd.DataFrame([
        {"Ledger Code": "1001", "Ledger Name": "Equity Share Capital", "Original Group": "Capital Account", "Current Year Amount": -100.00, "Previous Year Amount": -100.00},
        {"Ledger Code": "1002", "Ledger Name": "General Reserve", "Original Group": "Reserves & Surplus", "Current Year Amount": -150.00, "Previous Year Amount": -120.00},
        {"Ledger Code": "1003", "Ledger Name": "Retained Earnings P&L", "Original Group": "Reserves & Surplus", "Current Year Amount": -180.00, "Previous Year Amount": -110.00},
        {"Ledger Code": "2001", "Ledger Name": "HDFC Term Loan (Secured)", "Original Group": "Long Term Borrowings", "Current Year Amount": -250.00, "Previous Year Amount": -300.00},
        {"Ledger Code": "2002", "Ledger Name": "ICICI Cash Credit Limit", "Original Group": "Short Term Borrowings", "Current Year Amount": -80.00, "Previous Year Amount": -60.00},
        {"Ledger Code": "2003", "Ledger Name": "Trade Payables - MSME Vendors", "Original Group": "Current Liabilities", "Current Year Amount": -65.00, "Previous Year Amount": -50.00},
        {"Ledger Code": "2004", "Ledger Name": "Trade Payables - Other Vendors", "Original Group": "Current Liabilities", "Current Year Amount": -120.00, "Previous Year Amount": -95.00},
        {"Ledger Code": "2005", "Ledger Name": "Statutory Dues Payable (GST & TDS)", "Original Group": "Current Liabilities", "Current Year Amount": -25.00, "Previous Year Amount": -20.00},
        {"Ledger Code": "2006", "Ledger Name": "Provision for Income Tax", "Original Group": "Provisions", "Current Year Amount": -40.00, "Previous Year Amount": -30.00},
        {"Ledger Code": "3001", "Ledger Name": "Factory Land & Buildings", "Original Group": "Fixed Assets", "Current Year Amount": 450.00, "Previous Year Amount": 450.00},
        {"Ledger Code": "3002", "Ledger Name": "Plant & Machinery", "Original Group": "Fixed Assets", "Current Year Amount": 220.00, "Previous Year Amount": 180.00},
        {"Ledger Code": "3003", "Ledger Name": "Capital Work-in-Progress (Solar Plant)", "Original Group": "Fixed Assets", "Current Year Amount": 45.00, "Previous Year Amount": 15.00},
        {"Ledger Code": "4001", "Ledger Name": "Raw Material Stock", "Original Group": "Current Assets", "Current Year Amount": 85.00, "Previous Year Amount": 70.00},
        {"Ledger Code": "4002", "Ledger Name": "Finished Goods Inventory", "Original Group": "Current Assets", "Current Year Amount": 60.00, "Previous Year Amount": 50.00},
        {"Ledger Code": "4003", "Ledger Name": "Trade Receivables - Domestic", "Original Group": "Current Assets", "Current Year Amount": 175.00, "Previous Year Amount": 140.00},
        {"Ledger Code": "4004", "Ledger Name": "HDFC Bank Current Account", "Original Group": "Bank Accounts", "Current Year Amount": 165.00, "Previous Year Amount": 150.00},
        {"Ledger Code": "4005", "Ledger Name": "Cash in Hand", "Original Group": "Cash Accounts", "Current Year Amount": 10.00, "Previous Year Amount": 5.00},
        {"Ledger Code": "5001", "Ledger Name": "Revenue from Domestic Operations", "Original Group": "Direct Incomes", "Current Year Amount": -850.00, "Previous Year Amount": -700.00},
        {"Ledger Code": "5002", "Ledger Name": "Interest Income on Bank FD", "Original Group": "Indirect Incomes", "Current Year Amount": -15.00, "Previous Year Amount": -10.00},
        {"Ledger Code": "6001", "Ledger Name": "Cost of Raw Material Consumed", "Original Group": "Direct Expenses", "Current Year Amount": 420.00, "Previous Year Amount": 350.00},
        {"Ledger Code": "6002", "Ledger Name": "Salaries & Wages", "Original Group": "Staff Expenses", "Current Year Amount": 140.00, "Previous Year Amount": 120.00},
        {"Ledger Code": "6003", "Ledger Name": "Bank Term Loan Interest", "Original Group": "Financial Charges", "Current Year Amount": 32.00, "Previous Year Amount": 38.00},
        {"Ledger Code": "6004", "Ledger Name": "Depreciation on Machinery", "Original Group": "Depreciation", "Current Year Amount": 28.00, "Previous Year Amount": 25.00},
        {"Ledger Code": "6005", "Ledger Name": "Audit Fees & Legal Charges", "Original Group": "Administrative Expenses", "Current Year Amount": 45.00, "Previous Year Amount": 32.00}
    ])
    tb_df.to_excel(os.path.join(sample_dir, "sample_trial_balance.xlsx"), index=False)

    # 2. AR Ageing Template
    ar_df = pd.DataFrame([
        {"Customer Name": "Precision Engineering Solutions Ltd", "< 6 Months": 85.00, "6M - 1Y": 15.00, "1Y - 2Y": 0.00, "2Y - 3Y": 0.00, "> 3Y": 0.00, "Total Amount": 100.00, "Classification Category": "Undisputed Considered Good", "Disputed Status": "No", "Previous Year Total": 80.00},
        {"Customer Name": "Bharat Auto Components Pvt Ltd", "< 6 Months": 45.00, "6M - 1Y": 10.00, "1Y - 2Y": 5.00, "2Y - 3Y": 0.00, "> 3Y": 0.00, "Total Amount": 60.00, "Classification Category": "Undisputed Considered Good", "Disputed Status": "No", "Previous Year Total": 45.00},
        {"Customer Name": "Apex Heavy Infra Projects", "< 6 Months": 0.00, "6M - 1Y": 5.00, "1Y - 2Y": 10.00, "2Y - 3Y": 0.00, "> 3Y": 0.00, "Total Amount": 15.00, "Classification Category": "Undisputed Considered Doubtful", "Disputed Status": "Yes", "Previous Year Total": 15.00}
    ])
    ar_df.to_excel(os.path.join(sample_dir, "sample_ar_ageing.xlsx"), index=False)

    # 3. AP Ageing Template
    ap_df = pd.DataFrame([
        {"Vendor Name": "Shree Metals & Alloys Pvt Ltd (MSME)", "MSME Status": "Yes", "< 1 Year": 60.00, "1Y - 2Y": 5.00, "2Y - 3Y": 0.00, "> 3Y": 0.00, "Total Outstanding": 65.00, "Classification Category": "Undisputed Dues - MSME", "Disputed Status": "No", "Previous Year Total": 50.00},
        {"Vendor Name": "Global Industrial Suppliers Inc", "MSME Status": "No", "< 1 Year": 110.00, "1Y - 2Y": 10.00, "2Y - 3Y": 0.00, "> 3Y": 0.00, "Total Outstanding": 120.00, "Classification Category": "Undisputed Dues - Others", "Disputed Status": "No", "Previous Year Total": 95.00}
    ])
    ap_df.to_excel(os.path.join(sample_dir, "sample_ap_ageing.xlsx"), index=False)

    # 4. CWIP Ageing Template
    cwip_df = pd.DataFrame([
        {"Project Name / Description": "Rooftop Captive Solar Power Plant (500 KW)", "< 1 Year": 30.00, "1Y - 2Y": 15.00, "2Y - 3Y": 0.00, "> 3Y": 0.00, "Total CWIP Amount": 45.00, "Project Status": "In Progress", "Reason for Overdue/Cost Overrun": "Vendor component delivery delayed", "Previous Year Total": 15.00}
    ])
    cwip_df.to_excel(os.path.join(sample_dir, "sample_cwip_ageing.xlsx"), index=False)

    # 5. Related Party Template
    rpt_df = pd.DataFrame([
        {"Related Party Name": "Rajesh Kumar (Managing Director)", "Relationship Type": "Key Managerial Personnel (KMP)", "Nature of Transaction": "Managerial Remuneration & Director Sitting Fees", "Opening Balance": 0.00, "Debit Transactions": 0.00, "Credit Transactions": 36.00, "Closing Balance": 3.00, "Party Category": "KMP", "Terms and Conditions": "As approved by Nomination & Remuneration Committee", "Previous Year Closing": 2.50}
    ])
    rpt_df.to_excel(os.path.join(sample_dir, "sample_related_party.xlsx"), index=False)

    # 6. Borrowings Template
    bor_df = pd.DataFrame([
        {"Lender / Bank Name": "HDFC Bank Limited", "Facility / Loan Type": "Rupee Term Loan", "Secured / Unsecured": "Secured", "Current / Non-Current Classification": "Non-current", "Opening Balance": 300.00, "Fresh Drawals / Additions": 0.00, "Repayments / Disbursements": 50.00, "Closing Outstanding": 250.00, "Interest Rate %": "8.50% p.a.", "Security Details": "First pari-passu charge on Factory Land & Building at Plot 45, MIDC Pune", "Repayments Terms": "60 monthly installments of Rs 5.00 Lakhs commencing April 2022", "Default in Repayment": "No", "Default Amount": 0.00, "Previous Year Closing": 300.00},
        {"Lender / Bank Name": "ICICI Bank Limited", "Facility / Loan Type": "Working Capital Cash Credit Limit", "Secured / Unsecured": "Secured", "Current / Non-Current Classification": "Current", "Opening Balance": 60.00, "Fresh Drawals / Additions": 20.00, "Repayments / Disbursements": 0.00, "Closing Outstanding": 80.00, "Interest Rate %": "9.10% p.a. floating", "Security Details": "Hypothecation of entire stocks of raw materials, work-in-progress and trade receivables", "Repayments Terms": "Repayable on demand, subject to annual review", "Default in Repayment": "No", "Default Amount": 0.00, "Previous Year Closing": 60.00}
    ])
    bor_df.to_excel(os.path.join(sample_dir, "sample_borrowings.xlsx"), index=False)

    # 7. Contingent Liabilities Template
    cont_df = pd.DataFrame([
        {"Nature of Contingency": "Disputed GST Penalty Assessment", "Forum/Authority": "GST Appellate Authority", "Current Year Amount": 35.00, "Previous Year Amount": 35.00, "Management Assessment": "High probability of favorable decision based on legal counsel opinion", "Whether Provision Required": "No", "Remarks": "Contested matter pending hearing"}
    ])
    cont_df.to_excel(os.path.join(sample_dir, "sample_contingent_liabilities.xlsx"), index=False)


def get_sample_file_path(sample_dir: str, file_type: str) -> str:
    mapping = {
        "trial_balance": "trial_balance_template.xlsx",
        "ar_ageing": "ar_ageing_template.xlsx",
        "ap_ageing": "ap_ageing_template.xlsx",
        "cwip_ageing": "cwip_ageing_template.xlsx",
        "related_party": "related_party_template.xlsx",
        "borrowings": "borrowings_template.xlsx",
        "contingencies": "contingencies_template.xlsx",
        # Keep old short-codes just in case they are used internally
        "tb": "trial_balance_template.xlsx",
        "ar": "ar_ageing_template.xlsx",
        "ap": "ap_ageing_template.xlsx",
        "cwip": "cwip_ageing_template.xlsx",
        "rpt": "related_party_template.xlsx",
    }
    filename = mapping.get(file_type)
    if filename:
        return os.path.join(sample_dir, filename)
    return ""


def load_sample_dataset(client_id: int, sample_dir: str, db: Session):
    generate_sample_templates(sample_dir)
    parse_trial_balance(os.path.join(sample_dir, "sample_trial_balance.xlsx"), client_id, db)
    parse_ar_ageing(os.path.join(sample_dir, "sample_ar_ageing.xlsx"), client_id, db)
    parse_ap_ageing(os.path.join(sample_dir, "sample_ap_ageing.xlsx"), client_id, db)
    parse_cwip_ageing(os.path.join(sample_dir, "sample_cwip_ageing.xlsx"), client_id, db)
    parse_related_parties(os.path.join(sample_dir, "sample_related_party.xlsx"), client_id, db)
    parse_borrowings(os.path.join(sample_dir, "sample_borrowings.xlsx"), client_id, db)
    parse_contingencies(os.path.join(sample_dir, "sample_contingent_liabilities.xlsx"), client_id, db)


def load_sample_data(client_id: int, db: Session):
    sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_templates")
    load_sample_dataset(client_id, sample_dir, db)
    return {"message": "Sample trial balance and supporting schedules loaded successfully"}
