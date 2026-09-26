"""Accounting engine: postings for each voucher category."""
from datetime import date
from decimal import Decimal

from app.accounting.gst import gstin_checksum_char, gstin_error, normalise_state
from app.accounting.models import Side, VoucherKind
from app.accounting.services import VoucherAssembler
from app.accounting.validation import VoucherValidator
from app.excel.template_spec import spec_for
from app.excel.validator import ParsedRow
from tests.conftest import TODAY, NoHistory


def rows(*dicts, start=2):
    return [ParsedRow(start + i, {k: (Decimal(str(v)) if isinstance(v, (int, float)) else v) for k, v in d.items()})
            for i, d in enumerate(dicts)]


def assemble(kind, parsed, config, masters):
    vouchers, issues = VoucherAssembler(spec_for(kind), config, masters).assemble(parsed)
    issues += VoucherValidator(config, masters, NoHistory(), today=TODAY).validate(vouchers)
    return vouchers, issues


def errors(issues):
    return [i for i in issues if i.severity == "error"]


def book(v):
    """{ledger: (side, amount)} including inventory allocations."""
    out = {p.ledger: (p.side, p.amount) for p in v.postings}
    for i in v.inventory:
        out[i.ledger] = (i.side, i.amount)
    return out


SALE = dict(voucher_date=date(2026, 9, 25), invoice_number="INV-1", customer_ledger="abc traders",
            place_of_supply="Maharashtra", sales_ledger="Sales @ 18%", taxable_value=100000,
            cgst_rate=9, cgst_amount=9000, sgst_rate=9, sgst_amount=9000, invoice_total=118000)


def test_sales_intra_state(config, masters):
    [v], issues = assemble(VoucherKind.SALES, rows(SALE), config, masters)
    assert not errors(issues)
    b = book(v)
    assert b["ABC Traders"] == (Side.DR, Decimal("118000.00"))  # canonical Tally name resolved
    assert b["Sales @ 18%"] == (Side.CR, Decimal("100000.00"))
    assert b["Output CGST"] == (Side.CR, Decimal("9000.00"))
    assert b["Output SGST"] == (Side.CR, Decimal("9000.00"))
    assert v.is_balanced


def test_sales_rejects_igst_on_intra_state(config, masters):
    bad = {**SALE, "cgst_rate": None, "cgst_amount": None, "sgst_rate": None, "sgst_amount": None,
           "igst_rate": 18, "igst_amount": 18000}
    _, issues = assemble(VoucherKind.SALES, rows(bad), config, masters)
    assert any(i.code == "gst.intra" for i in errors(issues))


def test_sales_wrong_tax_amount_and_total(config, masters):
    bad = {**SALE, "cgst_amount": 8000, "invoice_total": 117000}
    _, issues = assemble(VoucherKind.SALES, rows(bad), config, masters)
    codes = {i.code for i in errors(issues)}
    assert "gst.amount" in codes


def test_sales_round_off_and_multi_line(config, masters):
    r = rows(
        {**SALE, "taxable_value": 100.40, "cgst_amount": None, "sgst_amount": None, "round_off": -0.48,
         "invoice_total": 118},
    )
    [v], issues = assemble(VoucherKind.SALES, r, config, masters)
    assert not errors(issues), issues
    b = book(v)
    assert b["Output CGST"][1] == Decimal("9.04")
    assert b["Round Off"] == (Side.DR, Decimal("0.48"))
    assert b["ABC Traders"] == (Side.DR, Decimal("118.00"))


def test_sales_stock_item_becomes_inventory(config, masters):
    line = {**SALE, "item_description": "office chair", "quantity": 2, "unit": "nos", "rate": 50000,
            "taxable_value": 100000}
    [v], issues = assemble(VoucherKind.SALES, rows(line), config, masters)
    assert not errors(issues), issues
    assert v.inventory[0].stock_item == "Office Chair"
    assert v.inventory[0].unit == "Nos"
    assert v.is_balanced


def test_purchase_itc_ineligible_goes_to_expense(config, masters):
    p = dict(voucher_date=date(2026, 9, 22), supplier_ledger="Metro Office Supplies", invoice_number="M-1",
             invoice_date=date(2026, 9, 22), supplier_state="Maharashtra", place_of_supply="Maharashtra",
             purchase_ledger="Office Expenses", taxable_value=1000, cgst_rate=9, cgst_amount=90, sgst_rate=9,
             sgst_amount=90, invoice_total=1180, itc_eligibility="Ineligible")
    [v], issues = assemble(VoucherKind.PURCHASE, rows(p), config, masters)
    assert not errors(issues), issues
    b = book(v)
    assert b["Office Expenses"] == (Side.DR, Decimal("1180.00"))
    assert "Input CGST" not in b
    assert b["Metro Office Supplies"] == (Side.CR, Decimal("1180.00"))


def test_purchase_eligible_and_inter_state(config, masters):
    p = dict(voucher_date=date(2026, 9, 22), supplier_ledger="Sharma Suppliers", invoice_number="S-9",
             invoice_date=date(2026, 9, 20), supplier_state="Gujarat", place_of_supply="Maharashtra",
             purchase_ledger="Purchase @ 18%", taxable_value=1000, igst_rate=18, igst_amount=180, invoice_total=1180)
    [v], issues = assemble(VoucherKind.PURCHASE, rows(p), config, masters)
    assert not errors(issues), issues
    b = book(v)
    assert b["Purchase @ 18%"] == (Side.DR, Decimal("1000.00"))
    assert b["Input IGST"] == (Side.DR, Decimal("180.00"))
    assert b["Sharma Suppliers"] == (Side.CR, Decimal("1180.00"))
    assert v.reference == "S-9"


def test_journal_balanced(config, masters):
    r = rows(dict(voucher_date=date(2026, 9, 30), reference_number="JV-1", ledger="Salary", debit=500),
             dict(voucher_date=date(2026, 9, 30), reference_number="JV-1", ledger="Salary Payable", credit=500))
    [v], issues = assemble(VoucherKind.JOURNAL, r, config, masters)
    assert not errors(issues)
    assert v.total_debit == v.total_credit == Decimal("500.00")


def test_journal_unbalanced_is_blocked(config, masters):
    r = rows(dict(voucher_date=date(2026, 9, 30), reference_number="JV-1", ledger="Salary", debit=500),
             dict(voucher_date=date(2026, 9, 30), reference_number="JV-1", ledger="Salary Payable", credit=400))
    _, issues = assemble(VoucherKind.JOURNAL, r, config, masters)
    assert any(i.code == "balance" for i in errors(issues))


def test_journal_row_with_both_sides(config, masters):
    r = rows(dict(voucher_date=date(2026, 9, 30), reference_number="JV-1", ledger="Salary", debit=5, credit=5))
    _, issues = assemble(VoucherKind.JOURNAL, r, config, masters)
    assert any(i.code == "jv.both" for i in errors(issues))


def test_bank_receipt(config, masters):
    r = rows(dict(voucher_date=date(2026, 9, 27), bank_ledger="HDFC Bank", party_ledger="ABC Traders",
                  amount=1000, instrument_number="UTR1", reference_number="INV-1"))
    [v], issues = assemble(VoucherKind.RECEIPT, r, config, masters)
    assert not errors(issues)
    b = book(v)
    assert b["HDFC Bank"] == (Side.DR, Decimal("1000.00"))
    assert b["ABC Traders"] == (Side.CR, Decimal("1000.00"))
    party = next(p for p in v.postings if p.is_party)
    assert party.bill_type == "Agst Ref" and party.bill_name == "INV-1"


def test_bank_payment(config, masters):
    r = rows(dict(voucher_date=date(2026, 9, 27), bank_ledger="ICICI Bank", party_ledger="Rent", amount=2500))
    [v], issues = assemble(VoucherKind.PAYMENT, r, config, masters)
    assert not errors(issues)
    b = book(v)
    assert b["Rent"] == (Side.DR, Decimal("2500.00"))
    assert b["ICICI Bank"] == (Side.CR, Decimal("2500.00"))


def test_unknown_ledger_reported_with_row_and_column(config, masters):
    r = rows(dict(voucher_date=date(2026, 9, 27), bank_ledger="HDFC Bank", party_ledger="Nobody & Co", amount=10),
             start=7)
    _, issues = assemble(VoucherKind.RECEIPT, r, config, masters)
    e = next(i for i in errors(issues) if i.code == "master.ledger")
    assert e.row == 7 and e.column == "Party Ledger"
    assert 'Ledger "Nobody & Co" does not exist in Tally master data.' in e.message


def test_date_outside_financial_year(config, masters):
    r = rows(dict(voucher_date=date(2026, 3, 31), bank_ledger="HDFC Bank", party_ledger="ABC Traders", amount=10))
    _, issues = assemble(VoucherKind.RECEIPT, r, config, masters)
    assert any(i.code == "date.fy" for i in errors(issues))


def test_duplicate_against_history(config, masters):
    [v], _ = VoucherAssembler(spec_for(VoucherKind.SALES), config, masters).assemble(rows(SALE))
    history = NoHistory(exact={f"2026-27|{v.exact_key()}": {"posted_at": "2026-09-25T10:00:00", "voucher_label": "INV-1"}})
    issues = VoucherValidator(config, masters, history, today=TODAY).validate([v])
    assert any(i.code == "dup.history" for i in errors(issues))


def test_masters_required_outside_demo(config):
    from app.tally.masters import CachedMasters
    live = config.model_copy(update={"demo_mode": False})
    empty = CachedMasters.from_records({})
    _, issues = assemble(VoucherKind.SALES, rows(SALE), live, empty)
    assert any(i.code == "master.nosync" for i in errors(issues))


def test_gstin_and_states():
    good = "27AAPFA1234B1Z" + gstin_checksum_char("27AAPFA1234B1Z")
    assert gstin_error(good) is None
    wrong_check = good[:-1] + ("A" if good[-1] != "A" else "B")
    assert "checksum" in gstin_error(wrong_check)
    assert gstin_error("27AAPFA1234") is not None
    assert normalise_state("27") == "Maharashtra"
    assert normalise_state("24-Gujarat") == "Gujarat"
    assert normalise_state("Atlantis") is None
