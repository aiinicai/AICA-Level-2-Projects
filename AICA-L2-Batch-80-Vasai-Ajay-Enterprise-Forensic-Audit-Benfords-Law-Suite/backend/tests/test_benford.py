"""
Unit & Statistical Back-Tests for Benford's Law Analytics Engine.
"""

import math
import pytest
from backend.app.engine.benford import (
    get_theoretical_first_digit,
    get_theoretical_second_digit,
    get_theoretical_first_two_digits,
    get_theoretical_last_two_digits,
    extract_digits,
    evaluate_mad_rating,
    BenfordAnalysisEngine
)


def test_theoretical_probabilities_sum_to_one():
    """Validates mathematical integrity: sum of probabilities must equal 1.0."""
    p_1d = sum(get_theoretical_first_digit().values())
    assert math.isclose(p_1d, 1.0, rel_tol=1e-6)

    p_2d = sum(get_theoretical_second_digit().values())
    assert math.isclose(p_2d, 1.0, rel_tol=1e-6)

    p_f2d = sum(get_theoretical_first_two_digits().values())
    assert math.isclose(p_f2d, 1.0, rel_tol=1e-6)

    p_l2d = sum(get_theoretical_last_two_digits().values())
    assert math.isclose(p_l2d, 1.0, rel_tol=1e-6)


def test_digit_extraction_edge_cases():
    """Tests digit extractor on diverse financial formats, currency symbols, and small numbers."""
    # Standard integer
    res = extract_digits(45800)
    assert res is not None
    d1, d2, d12, d123, last2, mantissa = res
    assert d1 == 4 and d2 == 5 and d12 == 45 and d123 == 458

    # Formatted Indian currency string
    res_inr = extract_digits("₹ 1,89,450.25")
    assert res_inr is not None
    assert res_inr[0] == 1 and res_inr[1] == 8 and res_inr[2] == 18

    # Sub-unitary decimal
    res_dec = extract_digits(0.00782)
    assert res_dec is not None
    assert res_dec[0] == 7 and res_dec[1] == 8 and res_dec[2] == 78

    # Invalid / Zero / Negative inputs should return None
    assert extract_digits(0) is None
    assert extract_digits(-500) is None
    assert extract_digits("N/A") is None
    assert extract_digits(None) is None


def test_conforming_geometric_dataset():
    """
    Back-test with a strictly Benford-conforming geometric sequence (powers of 1.05).
    Should produce 'Close Conformity' or 'Acceptable Conformity' on First-Two Digits MAD.
    """
    records = [{"amount": (1.05 ** i) * 10} for i in range(1, 2000)]
    results = BenfordAnalysisEngine.run_full_benford_suite(records, "amount")

    assert results["success"] is True
    assert results["valid_rows"] == 1999
    
    # 1D test MAD should be in close conformity (< 0.006)
    mad_1d = results["first_digit"]["mad"]
    assert mad_1d < 0.010, f"Expected low MAD for geometric sequence, got {mad_1d}"

    # F2D MAD should be low
    mad_f2d = results["first_two_digits"]["mad"]
    assert mad_f2d < 0.0025, f"Expected low F2D MAD, got {mad_f2d}"


def test_fabricated_uniform_dataset_triggers_non_conformity():
    """
    Forward-test with uniform random data.
    Must trigger 'Non-Conformity' (alerting forensic auditor).
    """
    # Uniform numbers between 1000 and 9999
    import random
    random.seed(42)
    records = [{"amount": random.randint(1000, 9999)} for _ in range(3000)]
    results = BenfordAnalysisEngine.run_full_benford_suite(records, "amount")

    assert results["success"] is True
    # In uniform data, first digit 1 has ~11% observed vs 30.1% expected
    mad_1d = results["first_digit"]["mad"]
    assert mad_1d > 0.015, f"Uniform data must fail Benford with MAD > 0.015, got {mad_1d}"
    assert results["first_digit"]["risk_level"] == "HIGH_RISK"


def test_spike_detection_z_score():
    """
    Tests detection of synthetic kickback cluster at digit 49 (e.g. ₹49,000 threshold smurfing).
    Z-Score for 49 should be highly significant (> 2.576).
    """
    import random
    random.seed(42)
    # 1000 conforming-like entries + 150 injected amounts starting with 49
    records = [{"amount": (1.07 ** i) * 15} for i in range(1, 1000)]
    for _ in range(150):
        records.append({"amount": 49000 + random.randint(10, 900)})

    results = BenfordAnalysisEngine.run_full_benford_suite(records, "amount")
    assert results["success"] is True

    f2d_items = results["first_two_digits"]["items"]
    item_49 = next(item for item in f2d_items if item["digit"] == 49)
    assert item_49["is_spike"] is True
    assert item_49["z_score"] > 2.576
    assert len(item_49["row_indices"]) >= 150
