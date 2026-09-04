"""
Unit Tests for Multi-Format Universal Data Ingestion Engine.
"""

import io
import json
import pytest
import pandas as pd
from backend.app.engine.data_loader import UniversalDataLoader


def test_csv_ingestion_and_column_detection():
    """Tests CSV parsing and automatic column mapping."""
    csv_content = (
        "Transaction_Date,Vendor_Name,Invoice_No,Gross_Amount,Narration\n"
        "2026-03-01,ABC Supplies,INV-1001,45200.00,Office Equipment\n"
        "2026-03-02,XYZ Logistics,INV-1002,125000.50,Freight Charges\n"
    ).encode('utf-8')

    res = UniversalDataLoader.load_from_bytes(csv_content, "financial_ledger.csv")
    assert res.success is True
    assert res.row_count == 2
    assert res.column_mapping.get("amount") == "Gross_Amount"
    assert res.column_mapping.get("vendor") == "Vendor_Name"
    assert res.column_mapping.get("invoice_no") == "Invoice_No"
    assert res.column_mapping.get("date") == "Transaction_Date"
    assert len(res.dataset_hash) == 64


def test_excel_ingestion():
    """Tests Excel spreadsheet parsing with openpyxl."""
    df = pd.DataFrame({
        "Posting Date": ["2026-01-10", "2026-01-11"],
        "Party": ["Tech Solutions", "Apex Corp"],
        "Payment Amount": [95000, 180000]
    })
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    excel_bytes = buffer.getvalue()

    res = UniversalDataLoader.load_from_bytes(excel_bytes, "bank_statement.xlsx")
    assert res.success is True
    assert res.row_count == 2
    assert res.column_mapping.get("amount") == "Payment Amount"
    assert res.column_mapping.get("vendor") == "Party"


def test_json_ingestion():
    """Tests JSON array ingestion."""
    records = [
        {"trans_id": "TXN01", "vendor": "Supplier A", "amount": 55000},
        {"trans_id": "TXN02", "vendor": "Supplier B", "amount": 88000}
    ]
    json_bytes = json.dumps(records).encode('utf-8')

    res = UniversalDataLoader.load_from_bytes(json_bytes, "records.json")
    assert res.success is True
    assert res.row_count == 2
    assert res.column_mapping.get("amount") == "amount"


def test_unsupported_format_diagnostics():
    """Tests that unknown format returns polite diagnostic with actionable suggestions."""
    dummy_bytes = b"Some random binary"
    res = UniversalDataLoader.load_from_bytes(dummy_bytes, "unknown_file.xyz")
    assert res.success is False
    assert "Unsupported file format" in res.error_message
    assert res.recommendation is not None
