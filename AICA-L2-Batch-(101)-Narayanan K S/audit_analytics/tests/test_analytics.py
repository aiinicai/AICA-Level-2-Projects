"""
test_analytics.py
Unit tests for Audit Analytics & Journal Entry Testing Tool.
Covers materiality validation, data ingestion & reconciliation,
the 10 SA 240 / SA 330 JE tests, Benford analysis, sampling, Excel WP and PDF Memo.
"""

from datetime import datetime, time
import io
from pathlib import Path
import sys

# Ensure audit_analytics module directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl
import pandas as pd
import pytest

from analytics import (
    generate_audit_sample,
    perform_benford_analysis,
    run_journal_entry_tests,
    validate_materiality,
)
from ingestion import (
    CANONICAL_COLUMNS,
    generate_synthetic_audit_dataset,
    parse_numeric,
    process_and_standardize_data,
    suggest_column_mappings,
)
from memo import generate_pdf_conclusion_memo
from workpapers import build_excel_workpaper


def test_materiality_validation_valid():
    res = validate_materiality(om=10000000.0, pm=7000000.0, ctt=350000.0)
    assert res["is_valid"] is True
    assert len(res["errors"]) == 0
    assert len(res["warnings"]) == 0


def test_materiality_validation_invalid_hierarchy():
    # PM >= OM
    res1 = validate_materiality(om=5000000.0, pm=6000000.0, ctt=100000.0)
    assert res1["is_valid"] is False
    assert any("less than Overall Materiality" in e for e in res1["errors"])

    # CTT >= PM
    res2 = validate_materiality(om=10000000.0, pm=5000000.0, ctt=5500000.0)
    assert res2["is_valid"] is False
    assert any("less than Performance Materiality" in e for e in res2["errors"])


def test_numeric_parsing():
    raw_series = pd.Series([
        "₹ 1,50,000.00", "5,00,000", "(25,000.00)", "  10000 Cr ", " 20000 Dr ", "N/A", None
    ])
    parsed = parse_numeric(raw_series)
    assert parsed.iloc[0] == 150000.0
    assert parsed.iloc[1] == 500000.0
    assert parsed.iloc[2] == -25000.0
    assert parsed.iloc[3] == 10000.0
    assert parsed.iloc[4] == 20000.0
    # "N/A" is unparseable text so it returns NaN without silently zeroing
    assert pd.isna(parsed.iloc[5])
    # None or blank becomes 0.0
    assert parsed.iloc[6] == 0.0


def test_column_mapping_suggestion():
    sample_cols = [
        "Voucher Date", "Doc No", "Particulars", "Debit Amount", "Credit Amount",
        "Narration", "Entered By", "Voucher Type"
    ]
    mapping = suggest_column_mappings(sample_cols)
    assert mapping["voucher_date"] == "Voucher Date"
    assert mapping["voucher_number"] == "Doc No"
    assert mapping["account_name"] == "Particulars"
    assert mapping["debit"] == "Debit Amount"
    assert mapping["credit"] == "Credit Amount"
    assert mapping["narration"] == "Narration"
    assert mapping["created_by"] == "Entered By"


def test_synthetic_data_generation_and_reconciliation():
    syn_df = generate_synthetic_audit_dataset(fy_year=2023, num_entries=50)
    assert len(syn_df) > 0
    assert "Voucher Number" in syn_df.columns
    assert "Debit" in syn_df.columns
    assert "Credit" in syn_df.columns

    mapping = {k: CANONICAL_COLUMNS[k] for k in CANONICAL_COLUMNS}
    std_df, diag = process_and_standardize_data(
        syn_df, mapping, fy_start=datetime(2023, 4, 1), fy_end=datetime(2024, 3, 31)
    )

    assert diag["total_rows"] == len(syn_df)
    assert diag["is_balanced"] is True
    assert abs(diag["difference"]) < 0.01
    assert std_df["source_row_index"].iloc[0] == 2


def test_journal_entry_red_flag_tests():
    syn_df = generate_synthetic_audit_dataset(fy_year=2023, num_entries=100)
    mapping = {k: CANONICAL_COLUMNS[k] for k in CANONICAL_COLUMNS}
    std_df, _ = process_and_standardize_data(syn_df, mapping)

    enriched_df, flags_df = run_journal_entry_tests(
        std_df,
        pm=5000000.0,
        start_business_hour=time(9, 0),
        end_business_hour=time(19, 0),
        round_multiples=[100000.0, 500000.0],
        auth_thresholds=[500000.0, 1000000.0]
    )

    assert len(flags_df) > 0
    assert "TEST_01" in flags_df["test_id"].values  # Sunday
    assert "TEST_03" in flags_df["test_id"].values  # Backdated
    assert "TEST_04" in flags_df["test_id"].values  # Round values
    assert "TEST_07" in flags_df["test_id"].values  # Keywords
    assert "TEST_08" in flags_df["test_id"].values  # Exceeding PM
    assert "TEST_09" in flags_df["test_id"].values  # Sensitive account
    assert "TEST_10" in flags_df["test_id"].values  # Admin/SoD anomaly

    assert "High" in flags_df["risk_level"].values
    assert "Medium" in flags_df["risk_level"].values
    assert "Low" in flags_df["risk_level"].values

    # Enriched df checks
    assert enriched_df["is_flagged"].sum() > 0


def test_benford_analysis():
    syn_df = generate_synthetic_audit_dataset(fy_year=2023, num_entries=200)
    mapping = {k: CANONICAL_COLUMNS[k] for k in CANONICAL_COLUMNS}
    std_df, _ = process_and_standardize_data(syn_df, mapping)

    res = perform_benford_analysis(std_df["amount"])
    assert res["sample_size"] > 0
    assert res["degrees_of_freedom"] == 8
    assert len(res["summary_df"]) == 9
    assert res["is_valid_test"] is True
    assert "limitation_note" in res


def test_audit_sampling_engine():
    syn_df = generate_synthetic_audit_dataset(fy_year=2023, num_entries=100)
    mapping = {k: CANONICAL_COLUMNS[k] for k in CANONICAL_COLUMNS}
    std_df, _ = process_and_standardize_data(syn_df, mapping)
    _, flags_df = run_journal_entry_tests(std_df, pm=5000000.0)

    sample_df = generate_audit_sample(
        std_df, flags_df, pm=5000000.0, sample_high_risk=True, random_sample_size=15
    )

    assert len(sample_df) > 0
    # No duplicate source rows
    assert sample_df["source_row_index"].nunique() == len(sample_df)
    # Check strata presence
    strata = set(sample_df["stratum"])
    assert "Stratum 1 (Key Items)" in strata
    assert "Stratum 2 (Risk Anomalies)" in strata
    assert "Stratum 3 (Remaining Population)" in strata


def test_excel_workpaper_generation():
    syn_df = generate_synthetic_audit_dataset(fy_year=2023, num_entries=50)
    mapping = {k: CANONICAL_COLUMNS[k] for k in CANONICAL_COLUMNS}
    std_df, diag = process_and_standardize_data(syn_df, mapping)
    _, flags_df = run_journal_entry_tests(std_df, pm=5000000.0)
    sample_df = generate_audit_sample(std_df, flags_df, pm=5000000.0, random_sample_size=10)
    ben_res = perform_benford_analysis(std_df["amount"])

    eng_info = {
        "company_name": "Test Company Ltd",
        "engagement_name": "Statutory Audit",
        "financial_year": "FY 2023-24",
        "audit_period": "01-Apr-2023 to 31-Mar-2024",
        "prepared_by": "Senior",
        "reviewed_by": "Partner",
        "om": 10000000.0,
        "pm": 5000000.0,
        "ctt": 350000.0
    }

    excel_bytes = build_excel_workpaper(
        engagement_info=eng_info,
        diagnostics=diag,
        flags_df=flags_df,
        sample_df=sample_df,
        benford_result=ben_res
    )

    assert len(excel_bytes) > 0
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    expected_sheets = [
        "Index & Objective",
        "Methodology & Criteria",
        "Testing Summary",
        "Sample Testing Schedule",
        "Benford Analysis"
    ]
    for s in expected_sheets:
        assert s in wb.sheetnames


def test_pdf_conclusion_memo_generation():
    syn_df = generate_synthetic_audit_dataset(fy_year=2023, num_entries=50)
    mapping = {k: CANONICAL_COLUMNS[k] for k in CANONICAL_COLUMNS}
    std_df, diag = process_and_standardize_data(syn_df, mapping)
    _, flags_df = run_journal_entry_tests(std_df, pm=5000000.0)
    sample_df = generate_audit_sample(std_df, flags_df, pm=5000000.0, random_sample_size=10)
    ben_res = perform_benford_analysis(std_df["amount"])

    eng_info = {
        "company_name": "Test Company Ltd",
        "engagement_name": "Statutory Audit",
        "financial_year": "FY 2023-24",
        "audit_period": "01-Apr-2023 to 31-Mar-2024",
        "prepared_by": "Senior",
        "reviewed_by": "Partner",
        "om": 10000000.0,
        "pm": 5000000.0,
        "ctt": 350000.0
    }

    pdf_bytes = generate_pdf_conclusion_memo(
        engagement_info=eng_info,
        diagnostics=diag,
        flags_df=flags_df,
        sample_df=sample_df,
        benford_result=ben_res,
        conclusion_choice="Satisfactory"
    )

    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
