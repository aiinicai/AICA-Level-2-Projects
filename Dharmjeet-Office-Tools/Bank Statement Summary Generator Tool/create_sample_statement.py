"""Sample Bank Statement Generator for Testing & Demonstration.
Generates realistic Indian bank statements (Excel, CSV, Word, and PDF).
"""

import os
import pandas as pd
from datetime import date, timedelta
import random
import openpyxl

def generate_mock_transactions(count: int = 40) -> list:
    """Generate realistic mock Indian bank transactions."""
    start_date = date(2024, 4, 1)
    
    narrations_pool = [
        ("ACH CR - TECH MAHINDRA LTD - SALARY FOR APRIL", 145000.0, 0.0, "Salary", "Tech Mahindra Ltd"),
        ("ACH CR - TECH MAHINDRA LTD - SALARY FOR MAY", 145000.0, 0.0, "Salary", "Tech Mahindra Ltd"),
        ("ACH CR - TECH MAHINDRA LTD - SALARY FOR JUNE", 145000.0, 0.0, "Salary", "Tech Mahindra Ltd"),
        ("UPI/412300000001/Rahul Sharma/rahul@okaxis/Payment", 0.0, 4500.0, "Household/Personal Expense", "Rahul Sharma"),
        ("UPI/412300000002/Swiggy/swiggy@icici/Food order", 0.0, 680.0, "Household/Personal Expense", "Swiggy"),
        ("UPI/412300000003/Blinkit/blinkit@hdfc/Groceries", 0.0, 1420.0, "Household/Personal Expense", "Blinkit"),
        ("UPI/412300000004/Client ABC Consulting/abc@okaxis/Invoice 101", 85000.0, 0.0, "Professional Fees", "Client ABC Consulting"),
        ("UPI/412300000005/Client XYZ Corp/xyz@icici/Consultancy", 120000.0, 0.0, "Professional Fees", "Client XYZ Corp"),
        ("NEFT-HDFC0001234-N123456789-MAHESH METALS-RAW MATERIALS", 0.0, 95000.0, "Purchases", "Mahesh Metals"),
        ("RTGS-ICIC0000001-R987654321-ACME ENTERPRISES", 0.0, 250000.0, "Purchases", "Acme Enterprises"),
        ("ACH-DEBIT/HDFC BANK LTD/HL EMI 00123456", 0.0, 48500.0, "Loan Repayment (EMI/Principal/Interest)", "HDFC Bank Ltd"),
        ("NACH/BAJAJ FINANCE/EMI LOAN", 0.0, 12500.0, "Loan Repayment (EMI/Principal/Interest)", "Bajaj Finance"),
        ("CREDIT CARD PMT - HDFC CARD 4123", 0.0, 34200.0, "Credit Card Payment", "HDFC Card"),
        ("ATM CASH WITHDRAWAL - S1NA001 - NEW DELHI", 0.0, 10000.0, "Cash Withdrawal", "Self / Cash"),
        ("BY CASH DEPOSIT - SELF AT BNA BRANCH", 75000.0, 0.0, "Cash Deposit", "Self / Cash"), # Flagged: > 50k
        ("BY CASH DEPOSIT - SELF", 45000.0, 0.0, "Cash Deposit", "Self / Cash"), # Structuring candidate
        ("BY CASH DEPOSIT - SELF", 48000.0, 0.0, "Cash Deposit", "Self / Cash"), # Structuring candidate
        ("SB INT.PD 01-04-2024 TO 30-06-2024", 8450.0, 0.0, "Interest Income", "Bank Interest Credit"),
        ("DIVIDEND/ACH/TCS LTD/DIV2024", 12000.0, 0.0, "Dividend", "TCS Ltd"),
        ("OLTAS ADVANCE TAX PMT - AY 2025-26", 0.0, 30000.0, "Tax Payment (Advance Tax/Self-Assessment/TDS/GST)", "Income Tax"),
        ("CONSOLIDATED CHARGES + GST", 0.0, 590.0, "Bank Charges", "Bank Charges"),
        ("SMS ALERT CHARGES", 0.0, 25.0, "Bank Charges", "Bank Charges"),
        ("CASH LOAN RECEIVED FROM MR SURESH", 25000.0, 0.0, "Loan Received", "Mr Suresh"), # Flagged: 269SS
        ("RTGS CR - QUICK REVERSAL ENTRY", 500000.0, 0.0, "Business Receipts/Sales", "Fast Capital"), # Flagged: 2-day reversal
        ("RTGS DR - QUICK REVERSAL ENTRY", 0.0, 500000.0, "Purchases", "Fast Capital"), # Flagged: 2-day reversal
    ]

    running_bal = 100000.0
    transactions = []
    curr_date = start_date

    for idx, item in enumerate(narrations_pool):
        desc, cr, dr, nat, party = item
        curr_date += timedelta(days=random.randint(1, 3))
        running_bal = running_bal + cr - dr
        
        transactions.append({
            "Date": curr_date.strftime("%d/%m/%Y"),
            "Narration": desc,
            "Chq/Ref No": f"REF{100000 + idx}",
            "Withdrawal (Dr)": dr if dr > 0 else "",
            "Deposit (Cr)": cr if cr > 0 else "",
            "Balance": running_bal
        })

    return transactions

def create_sample_excel(output_path: str = "sample_hdfc_statement.xlsx"):
    """Create sample HDFC bank statement Excel with metadata header."""
    txns = generate_mock_transactions()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Account Statement"
    
    # Statement Metadata Header
    ws.append(["HDFC BANK LIMITED"])
    ws.append(["Account Statement for Period: 01/04/2024 to 30/06/2024"])
    ws.append(["Account Name: M/s ABC Traders (Prop. Dharmjeet Kumar)"])
    ws.append(["Account Number: 50200012345678"])
    ws.append(["IFSC Code: HDFC0001234 | Branch: Connaught Place, New Delhi"])
    ws.append([]) # Blank row
    
    # Table Header
    headers = ["Date", "Narration", "Chq/Ref No", "Withdrawal (Dr)", "Deposit (Cr)", "Balance"]
    ws.append(headers)
    
    for t in txns:
        ws.append([t["Date"], t["Narration"], t["Chq/Ref No"], t["Withdrawal (Dr)"], t["Deposit (Cr)"], t["Balance"]])
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) if os.path.dirname(output_path) else ".", exist_ok=True)
    wb.save(output_path)
    print(f"[OK] Created sample statement: {output_path}")

if __name__ == "__main__":
    create_sample_excel("sample_hdfc_statement.xlsx")
