import pytest
from app.exporters.excel_exporter import ExcelExporter
import openpyxl
from decimal import Decimal
from datetime import date

def test_excel_exporter(tmp_path):
    exporter = ExcelExporter()
    payload = {
        'transactions': [
            {
                "transaction_date": date(2023, 1, 1),
                "narration": "=SUM(A1)",  # Formula injection
                "debit": Decimal("10.00"),
                "credit": None,  # Blank vs Zero
                "balance": Decimal("9999999999999999.99") # 18 significant digits
            }
        ],
        'summary': {
            "account_holder": "+ATTACK", # Formula injection
            "total_debits": Decimal("10.00"),
            "difference": Decimal("9999999999999999.99")
        },
        'exceptions': [],
        'audit': [
            {"action": "FIELD_EDIT", "before_value": "10", "after_value": "10.00"}
        ]
    }
    
    filepath = tmp_path / "test_export.xlsx"
    exporter.export(filepath, payload)
    
    # Reload workbook and assert
    wb = openpyxl.load_workbook(filepath)
    assert wb.sheetnames == ["Transactions", "Summary", "Exceptions", "Audit Trail"]
    
    ws_tx = wb["Transactions"]
    assert ws_tx["C2"].value == "'=SUM(A1)"  # Sanitized!
    assert ws_tx["F2"].value == 10.00
    assert ws_tx["G2"].value is None
    assert ws_tx["H2"].value == "PRECISION WARNING: 9999999999999999.99"
    
    ws_sum = wb["Summary"]
    assert ws_sum["B7"].value == "'+ATTACK"
    assert ws_sum["B13"].value == 10.00
    assert ws_sum["B17"].value == "PRECISION WARNING: 9999999999999999.99"
