"""
Tests for Real Amazon GST Ready-to-File Sample Workbook.
Fixture: sample_data/real_gst_report_sample.xlsx

Required assertions:
- B2C Small total taxable = 25,338.22
- HSN taxable total = 25,338.22
- 18% slab = 14,603.35
- 5% slab = 10,734.87
- HSN tax-column gap ≈ 291.94
- Rows 1-3 ignored, control totals recomputed from detail rows
- Merchant GSTIN extracted = 33AAJFI0296H1ZE
"""
import os
from decimal import Decimal
import pytest
from core.parsers import parse_gst_rtf

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data", "real_gst_report_sample.xlsx")


def test_real_gst_fixture_exists():
    assert os.path.exists(FIXTURE_PATH), f"Fixture not found at {FIXTURE_PATH}"


def test_real_gst_report_parsing_and_totals():
    with open(FIXTURE_PATH, "rb") as f:
        file_bytes = f.read()

    sections, report, control_totals = parse_gst_rtf(
        file_bytes=file_bytes,
        file_name="real_gst_report_sample.xlsx",
        filing_month=3,
        filing_year=2026
    )

    # 1. Merchant GSTIN verification
    assert control_totals.get("merchant_gstin") == "33AAJFI0296H1ZE"

    # 2. B2C Small Total Taxable = 25,338.22
    b2cs_taxable = control_totals["b2cs"]["taxable_value"]
    assert b2cs_taxable == Decimal("25338.22")

    # 3. HSN Total Taxable = 25,338.22
    hsn_taxable = control_totals["hsn"]["taxable_value"]
    assert hsn_taxable == Decimal("25338.22")

    # 4. HSN Breakdown by Rate: 18% = 14,603.35; 5% = 10,734.87
    hsn_rows = sections["hsn"]
    hsn_by_rate = {}
    for r in hsn_rows:
        rate = r["rate"]
        hsn_by_rate[rate] = hsn_by_rate.get(rate, Decimal("0.00")) + r["taxable_value"]

    assert hsn_by_rate[Decimal("0.18")] == Decimal("14603.35")
    assert hsn_by_rate[Decimal("0.05")] == Decimal("10734.87")

    # 5. HSN Tax Column Gap ≈ 291.94
    # Expected tax = rate * taxable; compare with igst + cgst + sgst
    expected_statutory_tax = sum((r["taxable_value"] * r["rate"] for r in hsn_rows), Decimal("0.00"))
    actual_tax_cols = sum((r["igst"] + r["cgst"] + r["sgst"] for r in hsn_rows), Decimal("0.00"))
    gap = (expected_statutory_tax - actual_tax_cols).quantize(Decimal("0.01"))

    assert abs(gap - Decimal("291.94")) <= Decimal("0.05")
    assert actual_tax_cols == Decimal("2873.41")
    assert expected_statutory_tax.quantize(Decimal("0.01")) == Decimal("3165.35")

    # 6. Verify internal checks results
    chk_results = {chk["check_name"]: chk for chk in report.internal_checks_results}
    assert chk_results["B2C Small total taxable equals HSN Summary total taxable"]["passed"] is True
    assert chk_results["B2C Small taxable value by rate equals HSN Summary taxable value by rate"]["passed"] is True
    assert chk_results["HSN: Integrated + Central + State/UT tax amounts equal Taxable Value x Rate"]["passed"] is False
    assert "HSN tax amounts lower than rate x taxable" in chk_results["HSN: Integrated + Central + State/UT tax amounts equal Taxable Value x Rate"]["detail"]
