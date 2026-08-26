"""
Unit & Back-Tests for Advanced Forensic Tests Engine (RSF, Duplicates, Smurfing, Round Numbers).
"""

import pytest
from backend.app.engine.forensic_tests import ForensicAnalysisEngine


def test_relative_size_factor_rsf():
    """
    Tests RSF outlier detection:
    Vendor A has baseline payments of ₹50,000 and one anomalous spike of ₹5,00,000 (RSF = 10.0).
    Vendor B has regular payments of ₹10,000, ₹12,000, ₹11,000 (RSF ≈ 1.09).
    """
    records = [
        {"vendor": "Vendor_A", "amount": 50000},
        {"vendor": "Vendor_A", "amount": 50000},
        {"vendor": "Vendor_A", "amount": 500000}, # Outlier invoice!
        {"vendor": "Vendor_B", "amount": 10000},
        {"vendor": "Vendor_B", "amount": 12000},
        {"vendor": "Vendor_B", "amount": 11000},
    ]

    res = ForensicAnalysisEngine.compute_relative_size_factor(records, "amount", "vendor")
    assert res["available"] is True
    assert res["outlier_vendor_count"] >= 1

    vendor_a_meta = next(v for v in res["high_risk_vendors"] if v["vendor_name"] == "Vendor_A")
    assert vendor_a_meta["rsf_value"] == 10.0
    assert vendor_a_meta["is_outlier"] is True
    assert vendor_a_meta["risk_level"] == "CRITICAL"


def test_duplicate_invoicing_detection():
    """Tests exact duplicate and fuzzy duplicate payment detection."""
    records = [
        {"vendor": "ABC Corp", "amount": 75000, "invoice_no": "INV-001", "date": "2026-03-15"},
        {"vendor": "ABC Corp", "amount": 75000, "invoice_no": "INV-001", "date": "2026-03-15"}, # Exact duplicate
        {"vendor": "XYZ Ltd", "amount": 25000, "invoice_no": "INV-101", "date": "2026-03-10"},
        {"vendor": "XYZ Ltd", "amount": 25000, "invoice_no": "INV-109", "date": "2026-03-25"}, # Fuzzy (same vendor & amount, diff invoice/date)
    ]

    res = ForensicAnalysisEngine.compute_duplicates(records, "amount", "vendor", "invoice_no", "date")
    assert res["exact_duplicate_clusters"] == 1
    assert res["exact_duplicated_rows"] == 2
    assert len(res["fuzzy_duplicates"]) >= 1


def test_split_transaction_smurfing():
    """Tests detection of transactions clustered just below statutory PAN ₹50k limit."""
    records = [
        {"vendor": "Supplier_1", "amount": 49500, "date": "2026-03-01"}, # Smurfed under 50k
        {"vendor": "Supplier_1", "amount": 49800, "date": "2026-03-02"}, # Smurfed under 50k
        {"vendor": "Supplier_2", "amount": 15000, "date": "2026-03-01"},
        {"vendor": "Supplier_3", "amount": 195000, "date": "2026-03-05"}, # Smurfed under 2 Lakh cash limit
    ]

    res = ForensicAnalysisEngine.compute_split_transactions(
        records, "amount", "vendor", "date", [50000.0, 200000.0]
    )
    assert res["total_split_anomalies"] == 3


def test_round_number_anomaly():
    """Tests identification of rounded figures (multiples of 1k, 10k, 50k, 1L)."""
    records = [
        {"amount": 100000},
        {"amount": 50000},
        {"amount": 25000},
        {"amount": 10000},
        {"amount": 14258.75}, # Unrounded
    ]

    res = ForensicAnalysisEngine.compute_round_numbers(records, "amount")
    assert res["total_round_transactions"] == 4
    assert res["breakdown"]["multiples_of_1Lakh"] == 1
    assert res["breakdown"]["multiples_of_50k"] == 1
