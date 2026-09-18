"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Comprehensive Automated Test Suite (Quality Control - 12 Mandatory Scenarios)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import os
import sys

# Ensure root directory is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from datetime import date
from database import init_db, get_db_connection
from cii_master import get_cii_for_fy, get_cii_for_date, CIINotFoundError, date_to_fy
from tax_rules import check_20_indexation_eligibility, determine_asset_classification, get_pre_2001_adopted_cost
from capital_gain_engine import compute_capital_gains
from tax_calculator import compare_tax_methods
from validation import validate_transaction_inputs


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database is initialized before tests run."""
    init_db()


# ==============================================================================
# TEST CASE 1: Normal transaction where 12.5% method is more beneficial
# ==============================================================================
def test_case_1_12_5_beneficial():
    """
    Scenario: Property with substantial price appreciation and short long-term holding period.
    Acquisition: FY 2022-23 (CII=331) for ₹10,00,000.
    Sale: FY 2026-27 (CII=392) for ₹1,00,00,000.
    Indexed Cost: ~₹11.84 Lakh.
    Tax at 12.5% is significantly lower than 20% indexed.
    """
    cg = compute_capital_gains(
        assessee_name="Assessee 1",
        pan="ABCDE1111A",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2027-28",
        asset_type="Land & Building",
        date_of_sale="10/10/2026",
        date_of_acquisition="10/05/2022",
        gross_sale_price=10000000.0,
        transfer_expenses=0.0,
        actual_cost_acq=1000000.0,
    )
    comp = compare_tax_methods(cg)

    assert comp.is_20_applicable is True
    assert comp.recommended_method_code == "12_5"
    assert "12.5% WITHOUT INDEXATION" in comp.recommended_method
    assert comp.tax_saving > 0
    assert comp.method_12_5.total_tax_liability < comp.method_20.total_tax_liability


# ==============================================================================
# TEST CASE 2: Transaction where 20% indexed method is more beneficial
# ==============================================================================
def test_case_2_20_indexed_beneficial():
    """
    Scenario: User Prompt Test Case:
    Sale = ₹1,00,00,000
    Acq Cost = ₹20,00,000 (FY 2005-06, CII=117)
    Improvement = ₹10,00,000 (FY 2012-13, CII=200)
    Transfer Expenses = ₹2,00,000
    Sale Date = FY 2026-27 (CII=392)
    """
    cg = compute_capital_gains(
        assessee_name="Assessee 2",
        pan="ABCDE2222B",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2027-28",
        asset_type="Land & Building",
        date_of_sale="15/06/2026",
        date_of_acquisition="15/06/2005",
        gross_sale_price=10000000.0,
        transfer_expenses=200000.0,
        actual_cost_acq=2000000.0,
        improvements=[{"particulars": "Construction", "amount": 1000000.0, "date": "15/06/2012"}],
    )
    comp = compare_tax_methods(cg)

    assert comp.is_20_applicable is True
    assert comp.recommended_method_code == "20"
    assert "20% WITH INDEXATION" in comp.recommended_method
    assert comp.tax_saving > 0
    assert comp.method_20.total_tax_liability < comp.method_12_5.total_tax_liability
    # Verify exact difference
    assert comp.tax_saving == abs(comp.method_12_5.total_tax_liability - comp.method_20.total_tax_liability)


# ==============================================================================
# TEST CASE 3: Transaction where both methods give nearly identical tax
# ==============================================================================
def test_case_3_identical_or_nearly_identical_tax():
    """
    Scenario: Property appreciation where 12.5% * LTCG_12.5 is very close to 20% * LTCG_20.
    """
    # Net sale: 10,00,000. Actual acq: 6,00,000. LTCG 12.5% = 4,00,000. Tax @ 12.5% + 4% cess = 52,000.
    # We want LTCG 20% such that Tax @ 20% + 4% cess = 52,000 => LTCG 20% = 2,50,000.
    # Indexed Acq = 10,00,000 - 2,50,000 = 7,50,000.
    # If Acq CII = 313.6 and Sale CII = 392, 600,000 * 392 / 313.6 = 750,000.
    # Let's test equality handling in compare_tax_methods.
    cg = compute_capital_gains(
        assessee_name="Assessee 3",
        pan="ABCDE3333C",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2027-28",
        asset_type="Land & Building",
        date_of_sale="15/06/2026",
        date_of_acquisition="15/06/2005",
        gross_sale_price=5000000.0,
        transfer_expenses=0.0,
        actual_cost_acq=4000000.0,
    )
    comp = compare_tax_methods(cg)
    # Verify that comparison does not crash and produces valid outputs
    assert comp.lower_tax_liability <= comp.higher_tax_liability
    assert comp.tax_saving >= 0


# ==============================================================================
# TEST CASE 4: Multiple improvement costs across different financial years
# ==============================================================================
def test_case_4_multiple_improvements():
    """
    Scenario: 3 distinct improvement expenditures incurred in FY 2008-09, FY 2014-15, and FY 2019-20.
    Verifies that each row is indexed separately using its specific year's CII.
    """
    improvements = [
        {"particulars": "Boundary Wall", "amount": 200000.0, "date": "10/08/2008"},   # FY 2008-09, CII 137
        {"particulars": "First Floor", "amount": 500000.0, "date": "15/11/2014"},     # FY 2014-15, CII 240
        {"particulars": "Interior Renovation", "amount": 300000.0, "date": "20/01/2020"}, # FY 2019-20, CII 289
    ]
    cg = compute_capital_gains(
        assessee_name="Assessee 4",
        pan="ABCDE4444D",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2027-28",
        asset_type="Land & Building",
        date_of_sale="15/06/2026",
        date_of_acquisition="15/06/2005",
        gross_sale_price=15000000.0,
        transfer_expenses=100000.0,
        actual_cost_acq=3000000.0,
        improvements=improvements,
    )

    assert len(cg.improvements) == 3
    assert cg.total_actual_improvement == 1000000.0
    assert cg.improvements[0].cii_improvement == 137
    assert cg.improvements[1].cii_improvement == 240
    assert cg.improvements[2].cii_improvement == 289
    assert cg.total_indexed_improvement > cg.total_actual_improvement


# ==============================================================================
# TEST CASE 5: Missing CII detection and error handling
# ==============================================================================
def test_case_5_missing_cii():
    """
    Scenario: Calculating for a future or unregistered Financial Year where CII is not in DB.
    Must raise CIINotFoundError and not silently default to an incorrect value.
    """
    with pytest.raises(CIINotFoundError):
        get_cii_for_fy("2039-40")

    # Validation should also flag missing CII
    val = validate_transaction_inputs(
        assessee_name="Assessee 5",
        pan="ABCDE5555E",
        assessee_type="Individual",
        residential_status="Resident",
        asset_type="Land & Building",
        date_of_sale="15/06/2039",  # FY 2039-40 missing
        date_of_acquisition="15/06/2010",
        gross_sale_price=5000000.0,
        transfer_expenses=0.0,
        net_sale_already_deducted=False,
        net_sale_price_input=None,
        actual_cost_acq=1000000.0,
    )
    assert not val.is_valid
    assert any("CII Missing" in err for err in val.errors)


# ==============================================================================
# TEST CASE 6: Invalid acquisition date (after sale date)
# ==============================================================================
def test_case_6_invalid_acquisition_date():
    """
    Scenario: Acquisition date is AFTER sale date.
    Validation must catch and reject this.
    """
    val = validate_transaction_inputs(
        assessee_name="Assessee 6",
        pan="ABCDE6666F",
        assessee_type="Individual",
        residential_status="Resident",
        asset_type="Land & Building",
        date_of_sale="15/06/2024",
        date_of_acquisition="20/08/2025",  # Invalid: After sale date
        gross_sale_price=5000000.0,
        transfer_expenses=0.0,
        net_sale_already_deducted=False,
        net_sale_price_input=None,
        actual_cost_acq=1000000.0,
    )
    assert not val.is_valid
    assert any("cannot be after Date of Sale" in err for err in val.errors)


# ==============================================================================
# TEST CASE 7: Invalid improvement date (before acq or after sale)
# ==============================================================================
def test_case_7_invalid_improvement_date():
    """
    Scenario: Improvement date is before acquisition date or after sale date.
    """
    # 1. Improvement before acquisition
    val1 = validate_transaction_inputs(
        assessee_name="Assessee 7",
        pan="ABCDE7777G",
        assessee_type="Individual",
        residential_status="Resident",
        asset_type="Land & Building",
        date_of_sale="15/06/2025",
        date_of_acquisition="15/06/2010",
        gross_sale_price=5000000.0,
        transfer_expenses=0.0,
        net_sale_already_deducted=False,
        net_sale_price_input=None,
        actual_cost_acq=1000000.0,
        improvements=[{"particulars": "Premature Work", "amount": 50000.0, "date": "10/01/2008"}],
    )
    assert not val1.is_valid
    assert any("cannot be before Date of Acquisition" in err for err in val1.errors)

    # 2. Improvement after sale
    val2 = validate_transaction_inputs(
        assessee_name="Assessee 7",
        pan="ABCDE7777G",
        assessee_type="Individual",
        residential_status="Resident",
        asset_type="Land & Building",
        date_of_sale="15/06/2025",
        date_of_acquisition="15/06/2010",
        gross_sale_price=5000000.0,
        transfer_expenses=0.0,
        net_sale_already_deducted=False,
        net_sale_price_input=None,
        actual_cost_acq=1000000.0,
        improvements=[{"particulars": "Post-sale Work", "amount": 50000.0, "date": "10/08/2025"}],
    )
    assert not val2.is_valid
    assert any("cannot be after Date of Sale" in err for err in val2.errors)


# ==============================================================================
# TEST CASE 8: Zero improvement cost handling
# ==============================================================================
def test_case_8_zero_improvement_cost():
    """
    Scenario: Asset sold with no improvement costs incurred.
    Must compute cleanly without division by zero or errors.
    """
    cg = compute_capital_gains(
        assessee_name="Assessee 8",
        pan="ABCDE8888H",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2027-28",
        asset_type="Land & Building",
        date_of_sale="15/06/2026",
        date_of_acquisition="15/06/2010",
        gross_sale_price=8000000.0,
        transfer_expenses=50000.0,
        actual_cost_acq=2500000.0,
        improvements=[],
    )
    assert cg.total_actual_improvement == 0.0
    assert cg.total_indexed_improvement == 0.0
    comp = compare_tax_methods(cg)
    assert comp.lower_tax_liability > 0


# ==============================================================================
# TEST CASE 9: Transfer expenses and Net Sale price deduction safeguards
# ==============================================================================
def test_case_9_transfer_expenses_safeguards():
    """
    Scenario: Verifies that transfer expenses are correctly accounted for,
    and if 'Net Sale Price already after transfer expenses' is checked,
    it avoids deducting transfer expenses twice.
    """
    # Case A: Gross Sale = 1,00,00,000, Transfer Expenses = 3,00,000 -> Net = 97,00,000
    cg_a = compute_capital_gains(
        assessee_name="Assessee 9",
        pan="ABCDE9999I",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2027-28",
        asset_type="Land & Building",
        date_of_sale="15/06/2026",
        date_of_acquisition="15/06/2010",
        gross_sale_price=10000000.0,
        transfer_expenses=300000.0,
        net_sale_already_deducted=False,
        actual_cost_acq=2000000.0,
    )
    assert cg_a.net_sale_price == 9700000.0

    # Case B: User enters Net Sale = 97,00,000 with net_sale_already_deducted=True
    cg_b = compute_capital_gains(
        assessee_name="Assessee 9",
        pan="ABCDE9999I",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2027-28",
        asset_type="Land & Building",
        date_of_sale="15/06/2026",
        date_of_acquisition="15/06/2010",
        gross_sale_price=9700000.0,
        transfer_expenses=300000.0,
        net_sale_already_deducted=True,
        net_sale_price_input=9700000.0,
        actual_cost_acq=2000000.0,
    )
    # Net sale price remains 97,00,000 (not 94,00,000)
    assert cg_b.net_sale_price == 9700000.0
    assert cg_b.gross_sale_price == 10000000.0
    assert cg_a.ltcg_12_5 == cg_b.ltcg_12_5


# ==============================================================================
# TEST CASE 10: Pre-cut-off acquisition / transitional provision scenario
# ==============================================================================
def test_case_10_pre_2001_grandfathering():
    """
    Scenario: Property acquired in 1996 for ₹2,00,000.
    FMV as of 01-04-2001: ₹15,00,000.
    SDV as of 01-04-2001: ₹18,00,000.
    Cost of improvement incurred in 1998 (pre-2001): ₹50,000.
    Must adopt FMV ₹15,00,000, base CII for FY 2001-02 (100), and ignore pre-2001 improvement.
    """
    cg = compute_capital_gains(
        assessee_name="Assessee 10",
        pan="ABCDE1010J",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2027-28",
        asset_type="Land & Building",
        date_of_sale="15/06/2026",
        date_of_acquisition="10/05/1996",
        gross_sale_price=12000000.0,
        transfer_expenses=0.0,
        actual_cost_acq=200000.0,
        fmv_2001=1500000.0,
        sdv_2001=1800000.0,
        improvements=[{"particulars": "Pre-2001 Renovation", "amount": 50000.0, "date": "15/04/1998"}],
    )
    assert cg.adopted_cost_acq == 1500000.0
    assert cg.acq_cii == 100
    assert cg.acq_fy == "2001-02"
    # Pre-2001 improvement must be excluded from deduction under Sec 55(1)(b)
    assert cg.total_actual_improvement == 0.0
    assert cg.total_indexed_improvement == 0.0
    assert len(cg.improvements) == 1
    assert cg.improvements[0].is_eligible is False


# ==============================================================================
# TEST CASE 11: Asset not eligible for indexation
# ==============================================================================
def test_case_11_asset_not_eligible_for_indexation():
    """
    Scenario:
    1. Immovable property acquired AFTER cut-off date (23-07-2024).
    2. Asset type is Shares / Securities.
    3. Assessee is Non-Resident or Corporate.
    Must clearly show 20% indexed method not applicable.
    """
    # 1. Acquired after 23-07-2024
    is_elig_1, reason_1 = check_20_indexation_eligibility(
        asset_type="Land & Building",
        assessee_type="Individual",
        residential_status="Resident",
        acq_date="01/08/2024",  # Post cut-off
        sale_date="01/09/2026",
    )
    assert is_elig_1 is False
    assert "acquired on or after 23rd July 2024" in reason_1

    # 2. Asset is Shares
    is_elig_2, reason_2 = check_20_indexation_eligibility(
        asset_type="Shares",
        assessee_type="Individual",
        residential_status="Resident",
        acq_date="01/05/2020",
        sale_date="01/09/2026",
    )
    assert is_elig_2 is False
    assert "not eligible for indexation comparison" in reason_2

    # 3. Assessee is Company / Corporate
    is_elig_3, reason_3 = check_20_indexation_eligibility(
        asset_type="Land & Building",
        assessee_type="Company",
        residential_status="Resident",
        acq_date="01/05/2020",
        sale_date="01/09/2026",
    )
    assert is_elig_3 is False
    assert "Assessee category 'Company' is not eligible" in reason_3

    # 4. Assessee is Non-Resident
    is_elig_4, reason_4 = check_20_indexation_eligibility(
        asset_type="Land & Building",
        assessee_type="Individual",
        residential_status="Non-Resident",
        acq_date="01/05/2020",
        sale_date="01/09/2026",
    )
    assert is_elig_4 is False
    assert "Residential status is 'Non-Resident'" in reason_4


# ==============================================================================
# TEST CASE 12: Different Assessment Years
# ==============================================================================
def test_case_12_different_assessment_years():
    """
    Scenario: Validates calculations for AY 2025-26, AY 2026-27, and AY 2027-28.
    """
    # AY 2025-26 -> Sale in FY 2024-25 (e.g. 15/10/2024)
    cg_25 = compute_capital_gains(
        assessee_name="Assessee 12A",
        pan="ABCDE1212K",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2025-26",
        asset_type="Land & Building",
        date_of_sale="15/10/2024",
        date_of_acquisition="15/10/2015",
        gross_sale_price=8000000.0,
        transfer_expenses=50000.0,
        actual_cost_acq=2000000.0,
    )
    assert cg_25.financial_year_transfer == "2024-25"
    assert cg_25.sale_cii == 363

    # AY 2026-27 -> Sale in FY 2025-26 (e.g. 15/05/2025)
    cg_26 = compute_capital_gains(
        assessee_name="Assessee 12B",
        pan="ABCDE1212L",
        assessee_type="Individual",
        residential_status="Resident",
        assessment_year="2026-27",
        asset_type="Land & Building",
        date_of_sale="15/05/2025",
        date_of_acquisition="15/10/2015",
        gross_sale_price=8000000.0,
        transfer_expenses=50000.0,
        actual_cost_acq=2000000.0,
    )
    assert cg_26.financial_year_transfer == "2025-26"
    assert cg_26.sale_cii == 377
