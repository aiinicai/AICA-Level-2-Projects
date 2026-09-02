"""End-to-end integration tests for report generation."""

import os
import pytest
import pandas as pd
from datetime import date
from normalization.date_utils import get_financial_year, get_fy_quarter, get_month_year, get_month_sort_key
from classification.rules_engine import classify_transactions
from reports.excel_report import export_excel_report
from reports.word_report import export_word_report
from reports.pdf_report import export_pdf_report

@pytest.fixture
def sample_statement_df():
    data = [
        {
            "transaction_date": date(2024, 4, 5),
            "value_date": date(2024, 4, 5),
            "description": "ACH CR - INFOSYS - SALARY",
            "reference_no": "ACH123456",
            "debit_amount": 0.0,
            "credit_amount": 150000.0,
            "balance": 150000.0,
            "mode": "ACH",
            "counterparty_name": "Infosys",
            "counterparty_account": "",
            "source_file": "stmt.xlsx",
            "source_bank": "HDFC Bank",
            "account_number": "XXXX9876",
        },
        {
            "transaction_date": date(2024, 4, 10),
            "value_date": date(2024, 4, 10),
            "description": "UPI/412345678901/Landlord Rent/rent@okaxis",
            "reference_no": "412345678901",
            "debit_amount": 35000.0,
            "credit_amount": 0.0,
            "balance": 115000.0,
            "mode": "UPI",
            "counterparty_name": "Landlord Rent",
            "counterparty_account": "rent@okaxis",
            "source_file": "stmt.xlsx",
            "source_bank": "HDFC Bank",
            "account_number": "XXXX9876",
        },
        {
            "transaction_date": date(2024, 5, 2),
            "value_date": date(2024, 5, 2),
            "description": "BY CASH DEPOSIT - SELF",
            "reference_no": "",
            "debit_amount": 0.0,
            "credit_amount": 60000.0,
            "balance": 175000.0,
            "mode": "CASH",
            "counterparty_name": "Self",
            "counterparty_account": "",
            "source_file": "stmt.xlsx",
            "source_bank": "HDFC Bank",
            "account_number": "XXXX9876",
        }
    ]
    df = pd.DataFrame(data)
    df["fy"] = df["transaction_date"].apply(get_financial_year)
    df["fy_quarter"] = df["transaction_date"].apply(get_fy_quarter)
    df["month_year"] = df["transaction_date"].apply(get_month_year)
    df["month_sort_key"] = df["transaction_date"].apply(get_month_sort_key)
    return classify_transactions(df)

def test_generate_excel_report(sample_statement_df, tmp_path):
    out_file = str(tmp_path / "test_report.xlsx")
    export_excel_report(sample_statement_df, out_file, client_name="Test Client")
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000

def test_generate_word_report(sample_statement_df, tmp_path):
    out_file = str(tmp_path / "test_report.docx")
    export_word_report(sample_statement_df, out_file, client_name="Test Client")
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000

def test_generate_pdf_report(sample_statement_df, tmp_path):
    out_file = str(tmp_path / "test_report.pdf")
    export_pdf_report(sample_statement_df, out_file, client_name="Test Client")
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000
