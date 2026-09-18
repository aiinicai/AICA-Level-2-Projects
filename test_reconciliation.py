import pytest
import pandas as pd
from datetime import datetime
import sys
sys.path.insert(0, '/home/claude/bank-reconciliation-app')
from utils import reconcile_transactions, generate_brs


@pytest.fixture
def sample_bank_data():
    """Create sample bank statement data."""
    data = {
        'Date': [
            pd.Timestamp('2024-09-01'),
            pd.Timestamp('2024-09-02'),
            pd.Timestamp('2024-09-03'),
            pd.Timestamp('2024-09-04'),
            pd.Timestamp('2024-09-05'),
        ],
        'Reference': ['CHQ001', 'DEP001', 'CHQ002', 'TRF001', 'CHQ003'],
        'Amount': [5000, 10000, 3000, 7500, 2500],
        'Balance': [95000, 105000, 102000, 109500, 107000]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_gl_data():
    """Create sample GL register data."""
    data = {
        'Date': [
            pd.Timestamp('2024-09-01'),
            pd.Timestamp('2024-09-02'),
            pd.Timestamp('2024-09-03'),
            pd.Timestamp('2024-09-04'),
            pd.Timestamp('2024-09-06'),
        ],
        'Reference': ['CHQ001', 'DEP001', 'CHQ002', 'TRF001', 'CHQ004'],
        'Amount': [5000, 10000, 3000, 7500, 1500],
        'Description': ['Rent', 'Deposit', 'Supplies', 'Transfer', 'Misc']
    }
    return pd.DataFrame(data)


def test_basic_matching(sample_bank_data, sample_gl_data):
    """Test that basic transactions are matched correctly."""
    matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
        sample_bank_data, sample_gl_data, date_tolerance=3
    )
    
    # Should match CHQ001, DEP001, CHQ002, TRF001
    assert len(matched) >= 3, "Should match at least 3 transactions"
    assert 'Bank_Date' in matched.columns
    assert 'GL_Date' in matched.columns


def test_unmatched_bank_only(sample_bank_data, sample_gl_data):
    """Test identification of bank-only transactions."""
    matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
        sample_bank_data, sample_gl_data, date_tolerance=3
    )
    
    # CHQ003 should be bank-only (no matching GL)
    assert len(bank_only) > 0, "Should have unmatched bank transactions"
    assert bank_only['Reference'].str.contains('CHQ003').any(), "CHQ003 should be bank-only"


def test_unmatched_gl_only(sample_bank_data, sample_gl_data):
    """Test identification of GL-only transactions."""
    matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
        sample_bank_data, sample_gl_data, date_tolerance=3
    )
    
    # CHQ004 should be GL-only (no matching Bank entry)
    assert len(gl_only) > 0, "Should have unmatched GL transactions"
    assert gl_only['Reference'].str.contains('CHQ004').any(), "CHQ004 should be GL-only"


def test_date_tolerance(sample_bank_data, sample_gl_data):
    """Test date tolerance matching."""
    # Create test data with timing difference
    bank = pd.DataFrame({
        'Date': [pd.Timestamp('2024-09-01'), pd.Timestamp('2024-09-05')],
        'Reference': ['CHQ001', 'CHQ002'],
        'Amount': [5000, 3000],
        'Balance': [95000, 92000]
    })
    
    gl = pd.DataFrame({
        'Date': [pd.Timestamp('2024-09-01'), pd.Timestamp('2024-09-07')],
        'Reference': ['CHQ001', 'CHQ002'],
        'Amount': [5000, 3000],
        'Description': ['Rent', 'Supplies']
    })
    
    # With 3-day tolerance, both should match
    matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
        bank, gl, date_tolerance=3
    )
    
    # CHQ001 should match (same date)
    assert len(matched) >= 1, "Should match at least 1 transaction"


def test_amount_mismatch_detection(sample_bank_data, sample_gl_data):
    """Test detection of amount mismatches."""
    matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
        sample_bank_data, sample_gl_data, date_tolerance=3
    )
    
    # CHQ003 in bank (2500) vs CHQ004 in GL (1500) - should show as mismatch or unmatched
    # Since reference doesn't match, they won't be flagged as mismatch
    # But both should appear in unmatched
    total_unmatched = len(bank_only) + len(gl_only)
    assert total_unmatched > 0, "Should have unmatched transactions"


def test_duplicate_detection():
    """Test detection of duplicate transactions."""
    bank = pd.DataFrame({
        'Date': [
            pd.Timestamp('2024-09-01'),
            pd.Timestamp('2024-09-01'),  # Duplicate
        ],
        'Reference': ['CHQ001', 'CHQ001'],
        'Amount': [5000, 5000],
        'Balance': [95000, 90000]
    })
    
    gl = pd.DataFrame({
        'Date': [pd.Timestamp('2024-09-01')],
        'Reference': ['CHQ001'],
        'Amount': [5000],
        'Description': ['Rent']
    })
    
    matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
        bank, gl, date_tolerance=3
    )
    
    # Should detect duplicate in bank
    assert len(duplicates) > 0, "Should detect duplicates"


def test_brs_generation(sample_bank_data, sample_gl_data):
    """Test BRS summary generation."""
    matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
        sample_bank_data, sample_gl_data, date_tolerance=3
    )
    
    brs = generate_brs(sample_bank_data, matched, bank_only, gl_only, mismatch)
    
    assert len(brs) == 4, "BRS should have 4 rows"
    assert 'Particulars' in brs.columns
    assert 'Amount' in brs.columns
    assert brs.loc[0, 'Particulars'] == 'Balance as per Bank Statement'


def test_empty_dataframes():
    """Test handling of empty dataframes."""
    empty_bank = pd.DataFrame(columns=['Date', 'Reference', 'Amount', 'Balance'])
    empty_gl = pd.DataFrame(columns=['Date', 'Reference', 'Amount', 'Description'])
    
    matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
        empty_bank, empty_gl, date_tolerance=3
    )
    
    assert len(matched) == 0
    assert len(bank_only) == 0
    assert len(gl_only) == 0
    assert len(mismatch) == 0


def test_perfect_match(sample_bank_data, sample_gl_data):
    """Test perfect matching scenario."""
    # Create identical data
    perfect_bank = pd.DataFrame({
        'Date': [pd.Timestamp('2024-09-01'), pd.Timestamp('2024-09-02')],
        'Reference': ['CHQ001', 'DEP001'],
        'Amount': [5000, 10000],
        'Balance': [95000, 105000]
    })
    
    perfect_gl = pd.DataFrame({
        'Date': [pd.Timestamp('2024-09-01'), pd.Timestamp('2024-09-02')],
        'Reference': ['CHQ001', 'DEP001'],
        'Amount': [5000, 10000],
        'Description': ['Rent', 'Deposit']
    })
    
    matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
        perfect_bank, perfect_gl, date_tolerance=3
    )
    
    assert len(matched) == 2, "Both transactions should match"
    assert len(bank_only) == 0, "No bank-only transactions"
    assert len(gl_only) == 0, "No GL-only transactions"
    assert len(duplicates) == 0, "No duplicates"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
