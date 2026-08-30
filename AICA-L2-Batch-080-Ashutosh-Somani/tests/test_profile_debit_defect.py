import pytest
from decimal import Decimal
import datetime
from pathlib import Path
from app.services.transaction_normalizer import TransactionNormalizer
from app.extractors.coordinate_extractor import CoordinateExtractor
from app.services.validation_service import ValidationService
from app.models.profile import BankProfile
from app.models.extraction_result import ExtractionResult, RawPage, RawWord

@pytest.fixture
def normalizer():
    return TransactionNormalizer()

def test_debit_credit_normalization_cases(normalizer):
    # Case A: debit = 50.00, credit = None
    table_a = {
        "cells": [
            ["transaction_date", "narration", "debit", "credit", "balance"],
            ["01/01/2023", "ATM Withdrawal", "50.00", "", "950.00"]
        ],
        "page_number": 1
    }
    txns, _ = normalizer.normalize([table_a])
    assert len(txns) == 1
    assert txns[0].debit == Decimal("50.00")
    assert txns[0].credit is None
    assert txns[0].transaction_type == 'Debit'

    # Case B: debit = 706.82, credit = None
    table_b = {
        "cells": [
            ["transaction_date", "narration", "debit", "credit", "balance"],
            ["02/01/2023", "Online Shopping", "706.82", "", "243.18"]
        ],
        "page_number": 1
    }
    txns, _ = normalizer.normalize([table_b])
    assert len(txns) == 1
    assert txns[0].debit == Decimal("706.82")
    assert txns[0].credit is None
    assert txns[0].transaction_type == 'Debit'

    # Case C: debit = None, credit = 1000.00
    table_c = {
        "cells": [
            ["transaction_date", "narration", "debit", "credit", "balance"],
            ["03/01/2023", "Salary Credit", "", "1000.00", "1243.18"]
        ],
        "page_number": 1
    }
    txns, _ = normalizer.normalize([table_c])
    assert len(txns) == 1
    assert txns[0].debit is None
    assert txns[0].credit == Decimal("1000.00")
    assert txns[0].transaction_type == 'Credit'

    # Case D: debit = 0.00, credit = None
    table_d = {
        "cells": [
            ["transaction_date", "narration", "debit", "credit", "balance"],
            ["04/01/2023", "Zero Debit", "0.00", "", "1243.18"]
        ],
        "page_number": 1
    }
    txns, _ = normalizer.normalize([table_d])
    assert len(txns) == 1
    assert txns[0].debit == Decimal("0.00")
    assert txns[0].credit is None
    assert txns[0].transaction_type == 'Debit'

    # Case E: debit = None, credit = 0.00
    table_e = {
        "cells": [
            ["transaction_date", "narration", "debit", "credit", "balance"],
            ["05/01/2023", "Zero Credit", "", "0.00", "1243.18"]
        ],
        "page_number": 1
    }
    txns, _ = normalizer.normalize([table_e])
    assert len(txns) == 1
    assert txns[0].debit is None
    assert txns[0].credit == Decimal("0.00")
    assert txns[0].transaction_type == 'Credit'


def test_profile_preview_integration(client, app):
    # 1. Upload PDF
    pdf_path = Path('samples/synthetic_defect_test.pdf')
    with open(pdf_path, 'rb') as f:
        resp = client.post('/upload', data={'file': f})
    assert resp.status_code == 200
    job_id = resp.json['job_id']
    
    # 2. Extract
    resp = client.post(f'/jobs/{job_id}/extract')
    assert resp.status_code == 302

    # 3. Request Profile Preview with one Debit and one Credit transaction
    column_definitions = [
        {"canonical_name": "transaction_date", "x0": 10, "x1": 80},
        {"canonical_name": "narration", "x0": 160, "x1": 440},
        {"canonical_name": "debit", "x0": 510, "x1": 600},
        {"canonical_name": "credit", "x0": 620, "x1": 700},
        {"canonical_name": "balance", "x0": 730, "x1": 800}
    ]
    resp = client.post('/profiles/api/preview', json={
        "job_id": job_id,
        "profile_data": {
            "profile_name": "Synthetic Baroda",
            "bank_name": "Bank of Synthetic Baroda",
            "expected_header_signatures": ["Bank of Synthetic Baroda"],
            "column_definitions": column_definitions,
            "table_bbox": {"x0": 0, "top": 0, "x1": 1000, "bottom": 1000}
        }
    })
    assert resp.status_code == 200
    txns = resp.json['transactions']
    
    # Verify we extracted 3 transactions
    # Row 1 (Opening Balance): debit = None, credit = None
    # Row 2 (ATM Withdrawal): debit = 200.00, credit = None, type = Debit
    # Row 3 (Salary Credit): debit = None, credit = 2500.50, type = Credit
    assert len(txns) == 3
    
    assert txns[0]['debit'] is None
    assert txns[0]['credit'] is None
    
    assert txns[1]['debit'] == '200.00'
    assert txns[1]['credit'] is None
    assert txns[1]['transaction_type'] == 'Debit'
    
    assert txns[2]['debit'] is None
    assert txns[2]['credit'] == '2500.50'
    assert txns[2]['transaction_type'] == 'Credit'


def test_full_pipeline_with_coordinate_profile(app):
    # 1. Create a synthetic ExtractionResult with raw words
    raw_words = [
        # Headers
        RawWord(text="Date", x0=15, x1=50, top=10, bottom=20, page_number=1),
        RawWord(text="Narration", x0=165, x1=220, top=10, bottom=20, page_number=1),
        RawWord(text="Debit", x0=518, x1=550, top=10, bottom=20, page_number=1),
        RawWord(text="Credit", x0=631, x1=660, top=10, bottom=20, page_number=1),
        RawWord(text="Balance", x0=738, x1=770, top=10, bottom=20, page_number=1),
        
        # Row 1: 01/01/2023 | Opening Balance | | | 1000.00
        RawWord(text="01/01/2023", x0=15, x1=70, top=30, bottom=40, page_number=1),
        RawWord(text="Opening", x0=165, x1=200, top=30, bottom=40, page_number=1),
        RawWord(text="Balance", x0=205, x1=240, top=30, bottom=40, page_number=1),
        RawWord(text="1000.00", x0=738, x1=775, top=30, bottom=40, page_number=1),
        
        # Row 2: 02/01/2023 | ATM Withdrawal | 50.00 | | 950.00
        RawWord(text="02/01/2023", x0=15, x1=70, top=50, bottom=60, page_number=1),
        RawWord(text="ATM", x0=165, x1=185, top=50, bottom=60, page_number=1),
        RawWord(text="Withdrawal", x0=190, x1=240, top=50, bottom=60, page_number=1),
        RawWord(text="50.00", x0=518, x1=545, top=50, bottom=60, page_number=1),
        RawWord(text="950.00", x0=738, x1=770, top=50, bottom=60, page_number=1),
        
        # Row 3: 05/01/2023 | Salary Credit | | 1000.00 | 1950.00
        RawWord(text="05/01/2023", x0=15, x1=70, top=70, bottom=80, page_number=1),
        RawWord(text="Salary", x0=165, x1=195, top=70, bottom=80, page_number=1),
        RawWord(text="Credit", x0=200, x1=230, top=70, bottom=80, page_number=1),
        RawWord(text="1000.00", x0=631, x1=665, top=70, bottom=80, page_number=1),
        RawWord(text="1950.00", x0=738, x1=775, top=70, bottom=80, page_number=1)
    ]
    
    page = RawPage(
        page_number=1,
        width=800,
        height=600,
        raw_text="Date Narration Debit Credit Balance 01/01/2023 Opening Balance 1000.00 02/01/2023 ATM Withdrawal 50.00 950.00 05/01/2023 Salary Credit 1000.00 1950.00",
        word_count=len(raw_words),
        character_count=100,
        words=raw_words,
        table_candidates=[]
    )
    
    er = ExtractionResult(
        job_id="test_pipeline_job",
        extractor_used="coordinate_extractor",
        extractor_version="1.0.0",
        status="success",
        page_count=1,
        pages_processed=1,
        total_words=len(raw_words),
        total_characters=100,
        text_layer_status="usable_digital",
        pages=[page],
        table_candidate_count=0
    )
    
    # 2. Build Profile
    from app.models.profile import ColumnDefinition, TableRegion
    prof = BankProfile(
        profile_id="test_pipeline_profile",
        profile_name="Pipeline Baroda",
        bank_name="Pipeline Bank",
        page_width=800.0,
        page_height=600.0,
        expected_header_signatures=["Pipeline Bank"]
    )
    prof.column_definitions = [
        ColumnDefinition(canonical_name="transaction_date", x0=10.0, x1=80.0),
        ColumnDefinition(canonical_name="narration", x0=160.0, x1=250.0),
        ColumnDefinition(canonical_name="debit", x0=510.0, x1=600.0),
        ColumnDefinition(canonical_name="credit", x0=620.0, x1=700.0),
        ColumnDefinition(canonical_name="balance", x0=730.0, x1=800.0)
    ]
    prof.table_bbox = TableRegion(x0=0.0, top=0.0, x1=800.0, bottom=600.0)
    
    # 3. Coordinate Extractor
    extractor = CoordinateExtractor(prof)
    er = extractor.extract(er)
    
    table_candidates = [tc.to_dict() if hasattr(tc, 'to_dict') else __import__('dataclasses').asdict(tc) for tc in er.pages[0].table_candidates]
    
    # 4. Normalizer
    normalizer = TransactionNormalizer()
    transactions, warnings = normalizer.normalize(table_candidates)
    
    assert len(transactions) == 3
    
    # Row 1 (Opening Balance)
    assert transactions[0].debit is None
    assert transactions[0].credit is None
    assert transactions[0].balance == Decimal("1000.00")
    
    # Row 2 (ATM Withdrawal)
    assert transactions[1].debit == Decimal("50.00")
    assert transactions[1].credit is None
    assert transactions[1].transaction_type == 'Debit'
    assert transactions[1].balance == Decimal("950.00")
    
    # Row 3 (Salary Credit)
    assert transactions[2].debit is None
    assert transactions[2].credit == Decimal("1000.00")
    assert transactions[2].transaction_type == 'Credit'
    assert transactions[2].balance == Decimal("1950.00")
    
    # 5. Validation Service
    val_service = ValidationService(app.config['APP_CONFIG'])
    norm_data = {
        "metadata": {
            "statement_start_date": "2023-01-01",
            "statement_end_date": "2023-01-05"
        },
        "transactions": [t.to_dict() for t in transactions]
    }
    
    val_summary, tx_results, all_exceptions = val_service._perform_validation(norm_data)
    
    # Verify validations
    assert val_summary.transaction_count == 3
    assert val_summary.total_debits == Decimal("50.00")
    assert val_summary.total_credits == Decimal("1000.00")
    assert val_summary.balance_mismatch_count == 0


def test_multiline_row_reconstruction(app):
    # 1. Create a synthetic ExtractionResult with raw words on multiple lines for transactions
    # Row 1 (Multiline Debit Transaction):
    # Line 1: 01/01/2023 | ATM Withdrawal | | | 1000.00 (Balance)
    # Line 2: | | | 50.00 (Debit)
    # Line 3: | | Charges Continuation
    #
    # Row 2 (Multiline Credit Transaction):
    # Line 4: 02/01/2023 | Salary Credit | | | 2500.00 (Balance)
    # Line 5: | | | | 1500.00 (Credit)
    #
    # Row 3 (Adjacent Standard Transaction):
    # Line 6: 03/01/2023 | Fees | 10.00 | | 2490.00 (Balance)
    raw_words = [
        # Headers (y=10)
        RawWord(text="Date", x0=15, x1=50, top=10, bottom=20, page_number=1),
        RawWord(text="Narration", x0=165, x1=220, top=10, bottom=20, page_number=1),
        RawWord(text="Debit", x0=518, x1=550, top=10, bottom=20, page_number=1),
        RawWord(text="Credit", x0=631, x1=660, top=10, bottom=20, page_number=1),
        RawWord(text="Balance", x0=738, x1=770, top=10, bottom=20, page_number=1),
        
        # Transaction 1: Line 1 (y=30)
        RawWord(text="01/01/2023", x0=15, x1=70, top=30, bottom=40, page_number=1),
        RawWord(text="ATM", x0=165, x1=185, top=30, bottom=40, page_number=1),
        RawWord(text="Withdrawal", x0=190, x1=240, top=30, bottom=40, page_number=1),
        RawWord(text="1000.00", x0=738, x1=775, top=30, bottom=40, page_number=1),
        # Transaction 1: Line 2 (y=50) -> has Debit (50.00)
        RawWord(text="50.00", x0=518, x1=545, top=50, bottom=60, page_number=1),
        # Transaction 1: Line 3 (y=70) -> has Narration continuation
        RawWord(text="Charges", x0=165, x1=210, top=70, bottom=80, page_number=1),
        RawWord(text="Continuation", x0=215, x1=280, top=70, bottom=80, page_number=1),
        
        # Transaction 2: Line 4 (y=90)
        RawWord(text="02/01/2023", x0=15, x1=70, top=90, bottom=100, page_number=1),
        RawWord(text="Salary", x0=165, x1=195, top=90, bottom=100, page_number=1),
        RawWord(text="Credit", x0=200, x1=230, top=90, bottom=100, page_number=1),
        RawWord(text="2500.00", x0=738, x1=775, top=90, bottom=100, page_number=1),
        # Transaction 2: Line 5 (y=110) -> has Credit (1500.00)
        RawWord(text="1500.00", x0=631, x1=665, top=110, bottom=120, page_number=1),
        
        # Transaction 3: Line 6 (y=130) -> Adjacent distinct transaction
        RawWord(text="03/01/2023", x0=15, x1=70, top=130, bottom=140, page_number=1),
        RawWord(text="Fees", x0=165, x1=185, top=130, bottom=140, page_number=1),
        RawWord(text="10.00", x0=518, x1=545, top=130, bottom=140, page_number=1),
        RawWord(text="2490.00", x0=738, x1=770, top=130, bottom=140, page_number=1)
    ]
    
    page = RawPage(
        page_number=1,
        width=800,
        height=600,
        raw_text="Synthetic text block",
        word_count=len(raw_words),
        character_count=100,
        words=raw_words,
        table_candidates=[]
    )
    
    er = ExtractionResult(
        job_id="test_multiline_job",
        extractor_used="coordinate_extractor",
        extractor_version="1.0.0",
        status="success",
        page_count=1,
        pages_processed=1,
        total_words=len(raw_words),
        total_characters=100,
        text_layer_status="usable_digital",
        pages=[page],
        table_candidate_count=0
    )
    
    # 2. Build Profile
    from app.models.profile import ColumnDefinition, TableRegion
    prof = BankProfile(
        profile_id="test_multiline_profile",
        profile_name="Multiline Baroda",
        bank_name="Multiline Bank",
        page_width=800.0,
        page_height=600.0,
        expected_header_signatures=["Multiline Bank"]
    )
    prof.column_definitions = [
        ColumnDefinition(canonical_name="transaction_date", x0=10.0, x1=80.0),
        ColumnDefinition(canonical_name="narration", x0=160.0, x1=300.0),
        ColumnDefinition(canonical_name="debit", x0=510.0, x1=600.0),
        ColumnDefinition(canonical_name="credit", x0=620.0, x1=700.0),
        ColumnDefinition(canonical_name="balance", x0=730.0, x1=800.0)
    ]
    prof.table_bbox = TableRegion(x0=0.0, top=0.0, x1=800.0, bottom=600.0)
    
    # 3. Coordinate Extractor
    extractor = CoordinateExtractor(prof)
    er = extractor.extract(er)
    
    table_candidates = [tc.to_dict() if hasattr(tc, 'to_dict') else __import__('dataclasses').asdict(tc) for tc in er.pages[0].table_candidates]
    
    # Verify cells were merged before normalizer
    cells = table_candidates[0]['cells']
    # Row 0 (Header added): ["transaction_date", "narration", "debit", "credit", "balance"]
    # Row 1 (Header from words): ["Date", "Narration", "Debit", "Credit", "Balance"]
    # Row 2 (Logical Tx 1): ["01/01/2023", "ATM Withdrawal Charges Continuation", "50.00", "", "1000.00"]
    # Row 3 (Logical Tx 2): ["02/01/2023", "Salary Credit", "", "1500.00", "2500.00"]
    # Row 4 (Logical Tx 3): ["03/01/2023", "Fees", "10.00", "", "2490.00"]
    assert len(cells) == 5
    
    assert cells[2][0] == "01/01/2023"
    assert cells[2][1] == "ATM Withdrawal Charges Continuation"
    assert cells[2][2] == "50.00"
    assert cells[2][3] == ""
    assert cells[2][4] == "1000.00"
    
    assert cells[3][0] == "02/01/2023"
    assert cells[3][1] == "Salary Credit"
    assert cells[3][2] == ""
    assert cells[3][3] == "1500.00"
    assert cells[3][4] == "2500.00"
    
    assert cells[4][0] == "03/01/2023"
    assert cells[4][1] == "Fees"
    assert cells[4][2] == "10.00"
    assert cells[4][3] == ""
    assert cells[4][4] == "2490.00"
    
    # 4. Normalizer
    normalizer = TransactionNormalizer()
    transactions, warnings = normalizer.normalize(table_candidates)
    
    assert len(transactions) == 3
    
    # Verify exact Decimals and balances
    assert transactions[0].debit == Decimal("50.00")
    assert transactions[0].credit is None
    assert transactions[0].transaction_type == 'Debit'
    assert transactions[0].balance == Decimal("1000.00")
    assert transactions[0].narration == "ATM Withdrawal Charges Continuation"
    
    assert transactions[1].debit is None
    assert transactions[1].credit == Decimal("1500.00")
    assert transactions[1].transaction_type == 'Credit'
    assert transactions[1].balance == Decimal("2500.00")
    assert transactions[1].narration == "Salary Credit"
    
    assert transactions[2].debit == Decimal("10.00")
    assert transactions[2].credit is None
    assert transactions[2].transaction_type == 'Debit'
    assert transactions[2].balance == Decimal("2490.00")
    assert transactions[2].narration == "Fees"
    
    # 5. Validation Service
    val_service = ValidationService(app.config['APP_CONFIG'])
    norm_data = {
        "metadata": {
            "statement_start_date": "2023-01-01",
            "statement_end_date": "2023-01-03"
        },
        "transactions": [t.to_dict() for t in transactions]
    }
    
    val_summary, tx_results, all_exceptions = val_service._perform_validation(norm_data)
    
    # Verify balance reconciliation
    # Opening balance of Tx 1: 1000.00 + 50.00 (debit) = 1050.00 (Wait, running balance: balance = prev_balance - debit + credit)
    # Tx 1: balance = 1000.00. (Since it's Debit 50, prev_balance = 1050.00)
    # Tx 2: balance = 2500.00. (Since it's Credit 1500, prev_balance = 1000.00. Balances perfectly!)
    # Tx 3: balance = 2490.00. (Since it's Debit 10, prev_balance = 2500.00. Balances perfectly!)
    # validated transaction count should be 2 (tx 2 and tx 3 reconciled).
    assert val_summary.transaction_count == 3
    assert val_summary.balance_mismatch_count == 0
    assert val_summary.total_debits == Decimal("60.00")
    assert val_summary.total_credits == Decimal("1500.00")

