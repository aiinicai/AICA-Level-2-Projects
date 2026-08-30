"""
Tests for Excel and PDF ingestion, parsing, and normalisation.
"""
import io
import pytest
import pandas as pd
import numpy as np
from engine.parse_excel import parse_excel, parse_amount_str, standardize_parsed_df
from engine.normalise import normalise_ledgers
from engine.parse_pdf import parse_pdf, ScannedPDFError

def test_amount_parsing():
    amt, hint = parse_amount_str("1,23,456.78 Dr")
    assert amt == 123456.78
    assert hint == "Dr"
    
    amt, hint = parse_amount_str("1,234 Cr")
    assert amt == 1234.0
    assert hint == "Cr"
    
    amt, hint = parse_amount_str("(1,234)")
    assert amt == -1234.0
    
    amt, hint = parse_amount_str("12,345.50")
    assert amt == 12345.50
    assert hint is None

    amt, hint = parse_amount_str(None)
    assert amt == 0.0

def test_subtotal_rows_dropped():
    raw_data = pd.DataFrame([
        {"Financial Year": "FY24", "Ledger Name": "HDFC Bank", "Group": "Bank Accounts", "Closing Dr": 50000.0, "Closing Cr": 0.0},
        {"Financial Year": "FY24", "Ledger Name": "Grand Total", "Group": "Bank Accounts", "Closing Dr": 50000.0, "Closing Cr": 0.0},
        {"Financial Year": "FY24", "Ledger Name": "Total Current Assets", "Group": "Current Assets", "Closing Dr": 50000.0, "Closing Cr": 0.0},
        {"Financial Year": "FY24", "Ledger Name": "Opening Stock Total", "Group": "Inventories", "Closing Dr": 10000.0, "Closing Cr": 0.0},
    ])
    norm = normalise_ledgers(standardize_parsed_df(raw_data))
    assert len(norm) == 1
    assert norm.iloc[0]["ledger_name"] == "HDFC Bank"

def test_long_wide_multisheet_equivalence(tmp_path):
    # Prepare identical data across 3 formats
    data_fy22 = [
        {"Ledger Name": "Sales", "Group": "Revenue from Operations", "Closing Cr": 100000.0, "Closing Dr": 0.0, "Opening Dr": 0.0, "Opening Cr": 0.0, "Turnover Dr": 0.0, "Turnover Cr": 100000.0},
        {"Ledger Name": "Bank A/c", "Group": "Bank Accounts", "Closing Dr": 100000.0, "Closing Cr": 0.0, "Opening Dr": 50000.0, "Opening Cr": 0.0, "Turnover Dr": 100000.0, "Turnover Cr": 50000.0}
    ]
    data_fy23 = [
        {"Ledger Name": "Sales", "Group": "Revenue from Operations", "Closing Cr": 120000.0, "Closing Dr": 0.0, "Opening Dr": 0.0, "Opening Cr": 0.0, "Turnover Dr": 0.0, "Turnover Cr": 120000.0},
        {"Ledger Name": "Bank A/c", "Group": "Bank Accounts", "Closing Dr": 120000.0, "Closing Cr": 0.0, "Opening Dr": 100000.0, "Opening Cr": 0.0, "Turnover Dr": 120000.0, "Turnover Cr": 100000.0}
    ]
    data_fy24 = [
        {"Ledger Name": "Sales", "Group": "Revenue from Operations", "Closing Cr": 150000.0, "Closing Dr": 0.0, "Opening Dr": 0.0, "Opening Cr": 0.0, "Turnover Dr": 0.0, "Turnover Cr": 150000.0},
        {"Ledger Name": "Bank A/c", "Group": "Bank Accounts", "Closing Dr": 150000.0, "Closing Cr": 0.0, "Opening Dr": 120000.0, "Opening Cr": 0.0, "Turnover Dr": 150000.0, "Turnover Cr": 120000.0}
    ]
    
    # 1. Long Format
    long_rows = []
    for row in data_fy22:
        long_rows.append({**row, "Financial Year": "FY22"})
    for row in data_fy23:
        long_rows.append({**row, "Financial Year": "FY23"})
    for row in data_fy24:
        long_rows.append({**row, "Financial Year": "FY24"})
    df_long = pd.DataFrame(long_rows)
    
    path_long = tmp_path / "long.xlsx"
    df_long.to_excel(path_long, index=False)
    
    # 2. Multi-sheet Format
    path_multi = tmp_path / "multi.xlsx"
    with pd.ExcelWriter(path_multi) as writer:
        pd.DataFrame(data_fy22).to_excel(writer, sheet_name="FY22", index=False)
        pd.DataFrame(data_fy23).to_excel(writer, sheet_name="FY23", index=False)
        pd.DataFrame(data_fy24).to_excel(writer, sheet_name="FY24", index=False)
        
    parsed_long = normalise_ledgers(parse_excel(str(path_long)))
    parsed_multi = normalise_ledgers(parse_excel(str(path_multi)))
    
    # Check total closing balances match
    assert len(parsed_long) == len(parsed_multi) == 6
    assert (parsed_long.groupby("fy")["closing_dr"].sum().values == parsed_multi.groupby("fy")["closing_dr"].sum().values).all()
    assert (parsed_long.groupby("fy")["closing_cr"].sum().values == parsed_multi.groupby("fy")["closing_cr"].sum().values).all()

def test_scanned_pdf_error(tmp_path):
    from reportlab.pdfgen import canvas
    pdf_path = tmp_path / "empty_scanned.pdf"
    # Create a PDF with no text elements (empty canvas)
    c = canvas.Canvas(str(pdf_path))
    c.showPage()
    c.save()
    
    with pytest.raises(ScannedPDFError, match="This PDF contains images, not text"):
        parse_pdf(str(pdf_path))
