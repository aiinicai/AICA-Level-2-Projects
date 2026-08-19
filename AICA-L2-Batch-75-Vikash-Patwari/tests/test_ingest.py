"""Strict ingestion cases. Runs with pytest OR standalone.

    python tests/test_ingest.py
"""

import os
import sys
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clock45.engine import PaymentLine, PurchaseLine  # noqa: E402
from clock45.ingest import (  # noqa: E402
    IngestError,
    ManualEntryGrid,
    detect_columns,
    import_excel_or_csv,
    import_tally_xml,
    load_client_mapping,
    parse_indian_amount,
    parse_indian_date,
    suggest_mapping,
)


SAMPLES = Path(__file__).resolve().parent.parent / "samples"
results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name, got, want))
    assert ok, f"{name}: got {got!r}, want {want!r}"


def valid_purchase_mapping():
    return {
        "invoice_number": "Bill No",
        "invoice_date": "Bill Date",
        "vendor_name": "Supplier Name",
        "vendor_pan_or_gstin": "GSTIN",
        "amount": "Invoice Amount",
        "grn_date": "GRN Date",
        "agreement_credit_days": "Credit Days",
    }


def standard_purchase_mapping():
    return {
        "invoice_number": "Invoice No",
        "invoice_date": "Invoice Date",
        "vendor_name": "Vendor Name",
        "vendor_pan_or_gstin": "GSTIN",
        "amount": "Amount",
    }


def test_01_indian_values():
    check("01 DD/MM/YY date", parse_indian_date("01/04/25"), date(2025, 4, 1))
    check("01 named month date", parse_indian_date("01-Apr-2025"), date(2025, 4, 1))
    check("01 Indian amount Cr", parse_indian_amount("Rs. 1,25,000.50 Cr"), Decimal("125000.50"))
    check("01 parenthesised amount", parse_indian_amount("(₹ 2,500)"), Decimal("2500.00"))


def test_02_detect_and_import_valid_csv():
    path = SAMPLES / "purchases_valid.csv"
    detected = detect_columns(path)
    check("02 column suggestion", detected.suggested_mapping["invoice_number"], "Bill No")
    imported = import_excel_or_csv(path, valid_purchase_mapping())
    check("02 exact engine type", type(imported.purchases[0]), PurchaseLine)
    check("02 lines read", imported.control_totals.lines_read, 3)
    check("02 total read", imported.control_totals.total_value_read, Decimal("250000.50"))
    check("02 total accounted", imported.control_totals.total_value_accounted_for, Decimal("250000.50"))
    check("02 totals tie", imported.control_totals.ties, True)
    check("02 optional GRN", imported.purchases[0].grn_date, date(2025, 4, 2))
    check("02 optional credit", imported.purchases[1].agreement_days, 30)


def test_03_import_valid_excel():
    imported = import_excel_or_csv(SAMPLES / "purchases_valid.xlsx", valid_purchase_mapping())
    check("03 Excel lines", len(imported.purchases), 3)
    check("03 Excel total", imported.control_totals.total_value_accounted_for, Decimal("250000.50"))


def test_04_payment_csv():
    mapping = {
        "invoice_number": "Invoice No",
        "payment_date": "Payment Date",
        "amount": "Amount",
    }
    imported = import_excel_or_csv(
        SAMPLES / "payments_valid.csv", mapping, record_type="payment"
    )
    check("04 exact payment type", type(imported.payments[0]), PaymentLine)
    check("04 payment total", imported.control_totals.total_value_read, Decimal("200000.50"))


def test_05_wrong_declared_total_refused():
    try:
        import_excel_or_csv(SAMPLES / "purchases_wrong_total.csv", standard_purchase_mapping())
    except IngestError as exc:
        check("05 wrong total refuses", exc.control_totals.ties, False)
        check("05 detail total retained", exc.control_totals.total_value_read, Decimal("200000.00"))
        check("05 declared total shown", exc.control_totals.declared_total, Decimal("210000.00"))
    else:
        raise AssertionError("wrong control total was silently accepted")


def test_06_malformed_rows_listed_and_refused():
    try:
        import_excel_or_csv(SAMPLES / "purchases_malformed.csv", standard_purchase_mapping())
    except IngestError as exc:
        check("06 malformed refuses", exc.control_totals.ties, False)
        check("06 every bad row shown", [p.row_number for p in exc.row_problems], [2, 3])
        joined = " | ".join(reason for problem in exc.row_problems for reason in problem.reasons)
        check("06 reasons are specific", "recognised date" in joined and "valid number" in joined, True)
    else:
        raise AssertionError("malformed rows were silently dropped")


def test_07_mapping_remembered_only_in_chosen_folder():
    with tempfile.TemporaryDirectory() as chosen:
        imported = import_excel_or_csv(
            SAMPLES / "purchases_valid.csv",
            valid_purchase_mapping(),
            client_id="client-001",
            mapping_folder=chosen,
        )
        remembered = load_client_mapping(chosen, "client-001")
        check("07 remembered mapping", remembered, valid_purchase_mapping())
        check("07 mapping did not affect import", imported.control_totals.ties, True)


def test_08_tally_purchase_payment_and_confirmation():
    imported = import_tally_xml(SAMPLES / "tally_sample.xml")
    check("08 Tally purchases", len(imported.purchases), 2)
    check("08 Tally payments", len(imported.payments), 1)
    check("08 Tally total", imported.control_totals.total_value_read, Decimal("280000.00"))
    check("08 bill allocation", imported.payments[0].invoice_id, "TP-001")
    narration_flags = [f for f in imported.confirmations if f.field == "vendor_name"]
    check("08 narration confirmation", narration_flags[0].value, "Verma Components")


def test_09_manual_excel_paste():
    grid = ManualEntryGrid("purchase")
    mapping = grid.paste_from_excel(
        "Invoice No\tInvoice Date\tVendor Name\tGSTIN\tAmount\n"
        "M-001\t01/04/25\tManual Supplier\t27EEEEE0000E1Z5\t1,000 Cr\n"
        "M-002\t02-Apr-2025\tSecond Supplier\t27FFFFF0000F1Z6\t2,000 Dr"
    )
    imported = grid.import_rows(mapping, expected_total="3,000")
    check("09 pasted rows", len(imported.purchases), 2)
    check("09 pasted total", imported.control_totals.total_value_read, Decimal("3000.00"))
    check("09 pasted ties", imported.control_totals.ties, True)


def test_10_rich_vendor_fields_and_mapping_guards():
    grid = ManualEntryGrid("purchase")
    grid.add_row(**{
        "Bill Number": "RICH-001", "Bill Date": "01-04-2025",
        "Supplier Name": "Sample Engineering Works", "Vendor PAN": "ABCDE1234F",
        "Invoice Amount": "1,00,000", "Udyam No": "UDYAM-MH-12-0123456",
        "MSME Type": "Small", "Classification Year": "2025-26",
        "NIC Code": "25999", "Major Activity": "Manufacturing",
        "GRN Date": "02-04-2025", "Payment Terms": "30",
        "Due Date": "01-05-2025", "Outstanding Amount": "25,000",
        "Expense Category": "Repairs", "Remarks": "Confirmed by accounts",
    })
    mapping = suggest_mapping(grid.rows[0].keys())
    imported = grid.import_rows(mapping)
    vendor = next(iter(imported.vendor_data.values()))
    supplement = imported.invoice_supplements["RICH-001"]
    check("10 separate PAN accepted", vendor.pan, "ABCDE1234F")
    check("10 Udyam imported", vendor.udyam_no, "UDYAM-MH-12-0123456")
    check("10 class imported", vendor.enterprise_class, "SMALL")
    check("10 credit terms mapped", imported.purchases[0].agreement_days, 30)
    check("10 due date retained", supplement.agreed_due_date.isoformat(), "2025-05-01")
    check("10 outstanding retained", supplement.outstanding_amount, Decimal("25000.00"))

    duplicate_mapping = dict(mapping)
    duplicate_mapping["remarks"] = duplicate_mapping["amount"]
    try:
        grid.import_rows(duplicate_mapping)
    except IngestError as exc:
        check("10 duplicate mapping refused", "cannot be mapped to two fields" in str(exc), True)
    else:
        raise AssertionError("Duplicate column mapping was accepted")


def test_11_duplicate_invoice_refused():
    grid = ManualEntryGrid("purchase")
    for amount in ("100", "200"):
        grid.add_row(**{
            "Invoice No": "DUP-1", "Invoice Date": "01-04-2025",
            "Vendor": "Duplicate Vendor", "Amount": amount,
        })
    mapping = suggest_mapping(grid.rows[0].keys())
    try:
        grid.import_rows(mapping)
    except IngestError as exc:
        check("11 duplicate invoice refused", len(exc.row_problems), 1)
        check(
            "11 duplicate reason explicit",
            "duplicate invoice" in exc.row_problems[0].reasons[0],
            True,
        )
    else:
        raise AssertionError("Duplicate invoice was accepted")


def test_12_embedded_payment_and_vendor_conflict_controls():
    grid = ManualEntryGrid("purchase")
    grid.add_row(**{
        "Invoice No": "PAID-1", "Invoice Date": "01-04-2025",
        "Vendor": "Controlled Vendor", "PAN": "ABCDE1234F", "Amount": "1,00,000",
        "Actual Payment Date": "20-04-2025", "Outstanding Amount": "25,000",
        "Udyam No": "UDYAM-DL-10-0050117", "MSME Type": "Micro",
    })
    imported = grid.import_rows(suggest_mapping(grid.rows[0].keys()))
    check("12 embedded payment created", len(imported.payments), 1)
    check("12 paid amount derived", imported.payments[0].amount, Decimal("75000.00"))

    grid.add_row(**{
        "Invoice No": "PAID-2", "Invoice Date": "02-04-2025",
        "Vendor": "Controlled Vendor", "PAN": "ABCDE1234F", "Amount": "10,000",
        "Udyam No": "UDYAM-DL-10-0050117", "MSME Type": "Small",
    })
    try:
        grid.import_rows(suggest_mapping(grid.rows[0].keys()))
    except IngestError as exc:
        detail = " | ".join(reason for problem in exc.row_problems for reason in problem.reasons)
        check("12 conflicting class refused", "enterprise class conflicts" in detail, True)
    else:
        raise AssertionError("Conflicting vendor classification was silently accepted")


if __name__ == "__main__":
    functions = [value for key, value in sorted(globals().items()) if key.startswith("test_")]
    failed = 0
    for function in functions:
        try:
            function()
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {function.__name__}: {exc}")
        except Exception as exc:
            failed += 1
            print(f"  ERROR {function.__name__}: {type(exc).__name__}: {exc}")
    for ok, name, got, want in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<34} {got}")
    print(
        f"\n{len(results)} assertions across {len(functions)} cases · "
        f"{'ALL PASSED' if failed == 0 else f'{failed} FAILED'}"
    )
    sys.exit(1 if failed else 0)
