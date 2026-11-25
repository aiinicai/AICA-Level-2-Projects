import io
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import xlsxwriter
from sqlalchemy import func, select, text

from app.advisory.matching import score
from app.advisory.overlaps import find_overlaps
from app.importers import exceptions as X
from app.importers.parsing import CellError, parse_date
from app.importers.pipeline import current_batches, import_file, open_exceptions
from app.importers.readers import UploadRejected, check_upload
from app.models import (AuditLog, BankAccount, BatchStatus, Category, CategoryAlias, ImportBatch, LineItem,
                        Override, OverrideAction, SourceType)

ROOT = Path(__file__).resolve().parents[1]
DAY1 = ROOT / "synthetic_data" / "day1_2026-11-24"
DAY2 = ROOT / "synthetic_data" / "day2_2026-11-25"
MB = 10 * 1024 * 1024


def imp(db, source, path: Path, **kw):
    rep = import_file(db, source, path.name, path.read_bytes(), **kw)
    db.commit()
    return rep


def xlsx_bytes(headers, rows, title_rows=()):
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("Data")
    r = 0
    for t in title_rows:
        ws.write(r, 0, t); r += 1
    ws.write_row(r, 0, headers)
    for row in rows:
        r += 1
        for c, v in enumerate(row):
            if isinstance(v, date):
                ws.write_datetime(r, c, v)
            elif v is not None:
                ws.write(r, c, v)
    wb.close()
    return buf.getvalue()


@pytest.fixture
def cats(db):
    rep = imp(db, "category_list", DAY1 / "category_list.xlsx")
    assert rep.status == "accepted", rep.issues
    return rep


PDC_H = ["Voucher No", "Vendor", "Cheque No", "Cheque Date", "Amount"]


# ---------------------------------------------------------------- upload safety
def _with_extra(content: bytes, name: str, data: bytes = b"x", ct_patch: str | None = None) -> bytes:
    src = zipfile.ZipFile(io.BytesIO(content))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for i in src.infolist():
            d = src.read(i.filename)
            if ct_patch and i.filename == "[Content_Types].xml":
                d = d.replace(b"</Types>", ct_patch.encode() + b"</Types>")
            z.writestr(i, d)
        if name:
            z.writestr(name, data)
    return out.getvalue()


@pytest.mark.parametrize("name,content,msg", [
    ("a.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1rest", "not accepted"),
    ("a.xlsm", b"PK\x03\x04", "not accepted"),
    ("a.exe", b"MZ", "not accepted"),
    ("a.xlsx", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1rest", "old binary"),
    ("a.xlsx", b"just text", "not an Excel"),
    ("a.xlsx", b"PK\x03\x04garbage", "damaged"),
    ("a.csv", b"PK\x03\x04abc", "Rename it to .xlsx"),
    ("a.csv", b"a,b\x00,c", "binary"),
    ("a.csv", b"", "empty"),
])
def test_upload_rejections(name, content, msg):
    with pytest.raises(UploadRejected, match=msg):
        check_upload(name, content, MB)


def test_size_limit():
    with pytest.raises(UploadRejected, match="limit"):
        check_upload("a.csv", b"x" * 2000, 1000)


def test_macros_refused():
    good = xlsx_bytes(PDC_H, [])
    check_upload("ok.xlsx", good, MB)
    with pytest.raises(UploadRejected, match="macros"):
        check_upload("m.xlsx", _with_extra(good, "xl/vbaProject.bin"), MB)
    with pytest.raises(UploadRejected, match="macro"):
        ct = '<Override PartName="/xl/x.bin" ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/>'
        check_upload("m.xlsx", _with_extra(good, "", ct_patch=ct), MB)


def test_rejected_upload_is_still_logged_with_hash(db, cats):
    rep = import_file(db, "vendor_pdc", "evil.xlsx", _with_extra(xlsx_bytes(PDC_H, []), "xl/vbaProject.bin"))
    db.commit()
    b = db.get(ImportBatch, rep.batch_id)
    assert b.status == BatchStatus.REJECTED and len(b.sha256) == 64 and b.stored_filename == ""
    assert db.scalar(select(AuditLog).where(AuditLog.action == "import.rejected")) is not None


# ---------------------------------------------------------------- parsing
def test_day_first_dates():
    assert parse_date("05/12/2026") == date(2026, 12, 5)
    assert parse_date("5-Dec-2026") == date(2026, 12, 5)
    assert parse_date(46361) == date(2026, 12, 5)        # Excel serial
    with pytest.raises(CellError):
        parse_date("31/31/2026")


def test_fuzzy_scorer_ignores_short_alias_noise():
    assert score("Marketing campaign", "Rent") < 70
    assert score("Visa Renewal Fees", "Visa fees") >= 90


# ---------------------------------------------------------------- ERP exports
def test_erp_export_with_title_rows_total_row_and_aliases(db, cats):
    rep = imp(db, "collections", DAY1 / "erp_receivables.xlsx", as_of=date(2026, 11, 24))
    assert rep.status == "accepted" and rep.header_row == 4 and rep.records == 60
    assert rep.columns["Doc No"] == "invoice_no" and rep.columns["Outstanding (OMR)"] == "amount"
    assert any(i.message == "Total row skipped." for i in rep.issues)
    li = db.scalar(select(LineItem).where(LineItem.source_key == "INV-26-1406"))
    assert li.risk_flag_imported is True and li.category_id is not None
    assert li.raw["Doc No"] == "INV-26-1406"             # stored exactly as imported


def test_duplicate_rows(db, cats):
    same = [["PV-1", "V1", "001", date(2026, 12, 5), 100.0]] * 2
    rep = import_file(db, "vendor_pdc", "p.xlsx", xlsx_bytes(PDC_H, same))
    assert rep.status == "accepted" and rep.records == 1 and "duplicate" in rep.warnings[0].message
    diff = [["PV-1", "V1", "001", date(2026, 12, 5), 100.0], ["PV-1", "V1", "001", date(2026, 12, 6), 100.0]]
    rep = import_file(db, "vendor_pdc", "p.xlsx", xlsx_bytes(PDC_H, diff))
    assert rep.status == "rejected" and "different details" in rep.errors[0].message


def test_any_row_error_rejects_file_and_keeps_current_data(db, cats):
    ok = imp(db, "vendor_pdc", DAY1 / "erp_pdc_register.xlsx")
    bad = xlsx_bytes(PDC_H, [["PV-1", "V1", "001", "31/31/2026", 100.0], ["PV-2", "V2", "002", "05/12/2026", -5]])
    rep = import_file(db, "vendor_pdc", "bad.xlsx", bad)
    db.commit()
    assert rep.status == "rejected" and len(rep.errors) == 2
    assert {e.row for e in rep.errors} == {2, 3} and rep.errors[0].column == "Cheque Date"
    assert [b.id for b in current_batches(db, "vendor_pdc")] == [ok.batch_id]
    assert db.scalar(select(func.count()).select_from(LineItem).where(LineItem.batch_id == rep.batch_id)) == 0


def test_missing_required_column(db, cats):
    rep = import_file(db, "vendor_pdc", "p.xlsx", xlsx_bytes(["Voucher No", "Vendor", "Amount"], [["a", "b", 1]]))
    assert rep.status == "rejected" and "Cheque No" in rep.errors[0].message


def test_forecast_import_needs_category_list(db):
    rep = import_file(db, "vendor_pdc", "p.xlsx", xlsx_bytes(PDC_H, [["PV-1", "V", "1", date(2026, 12, 1), 1.0]]))
    assert rep.status == "rejected" and "category list first" in rep.errors[0].message


def test_csv_semicolon_and_text_dates(db, cats):
    content = "Supplier;Bill No;Payment Date;Allocated Amount\nVendor X;B-1;05/12/2026;1.234,5\n".encode()
    rep = import_file(db, "allocation", "plan.csv", content)
    # '1.234,5' is not a valid amount in this app (comma = thousands): rejected with a clear message
    assert rep.status == "rejected" and rep.errors[0].column == "Amount"
    content = "Supplier;Bill No;Payment Date;Allocated Amount\nVendor X;B-1;05/12/2026;1234.5\n".encode()
    rep = import_file(db, "allocation", "plan.csv", content)
    li = db.scalar(select(LineItem).where(LineItem.batch_id == rep.batch_id))
    assert rep.status == "accepted" and li.planned_date == date(2026, 12, 5) and li.amount == Decimal("1234.500")


# ---------------------------------------------------------------- categories and exceptions
def test_category_list_sets_defaults_and_aliases(db, cats):
    assert db.scalar(select(func.count()).select_from(Category)) == 12
    assert db.scalar(select(CategoryAlias).where(CategoryAlias.alias_normalised == "wps")).category.name == "Payroll"
    bad = xlsx_bytes(["Category", "Inflow/Outflow", "Summary Group", "Display Order", "Default Treatment",
                      "Default For Source"], [["X", "Outflow", "G", 1, "Fixed", "collections"]])
    rep = import_file(db, "category_list", "c.xlsx", bad)
    assert rep.status == "rejected" and "needs an inflow" in rep.errors[0].message


def test_new_header_category_appears_after_mapping(db, cats):
    """Acceptance: a new category in an Excel header is usable after mapping (and remembered)."""
    rep = imp(db, "other", DAY1 / "other_recurring_wide.xlsx")
    assert rep.status == "exceptions"
    e = rep.exceptions[0]
    assert e["text"] == "Visa Renewal Fees" and e["suggestion"] == "Visa & labour fees"
    assert current_batches(db, "other") == []            # not current while an exception is open
    became_current = X.map_to_category(db, e["id"], db.scalar(select(Category.id).where(
        Category.name == "Visa & labour fees")))
    db.commit()
    assert became_current and [b.id for b in current_batches(db, "other")] == [rep.batch_id]
    li = db.scalar(select(LineItem).where(LineItem.category_text == "Visa Renewal Fees",
                                          LineItem.batch_id == rep.batch_id))
    assert db.get(Category, li.category_id).name == "Visa & labour fees" and li.direction.value == "outflow"
    rep2 = imp(db, "other", DAY2 / "other_recurring_wide.xlsx")   # remembered: no question next time
    assert rep2.status == "accepted" and rep2.exceptions == []


def test_add_new_category_from_exception(db, cats):
    rep = imp(db, "other", DAY1 / "other_recurring_long.xlsx")
    e = rep.exceptions[0]
    assert e["text"] == "Marketing campaign" and e["suggestion"] is None
    X.add_new_category(db, e["id"], direction="outflow", summary_group="Overheads")
    db.commit()
    cat = db.scalar(select(Category).where(Category.name == "Marketing campaign"))
    assert cat is not None and cat.display_order > 0
    assert db.scalar(select(LineItem).where(LineItem.category_text == "Marketing campaign")).category_id == cat.id
    assert open_exceptions(db) == []


def test_ignore_exception_leaves_rows_out(db, cats):
    rep = imp(db, "other", DAY1 / "other_recurring_long.xlsx")
    X.ignore(db, rep.exceptions[0]["id"])
    db.commit()
    li = db.scalar(select(LineItem).where(LineItem.category_text == "Marketing campaign"))
    assert li.category_id is None and current_batches(db, "other")


def test_mapping_direction_conflict_refused(db, cats):
    content = xlsx_bytes(PDC_H + ["Category"], [["PV-1", "V", "1", date(2026, 12, 1), 10.0, "Mystery"]])
    rep = import_file(db, "vendor_pdc", "p.xlsx", content)
    inflow = db.scalar(select(Category.id).where(Category.name == "Other inflows"))
    with pytest.raises(X.ResolveError, match="inflow category"):
        X.map_to_category(db, rep.exceptions[0]["id"], inflow)


# ---------------------------------------------------------------- re-upload
def test_reupload_keeps_overrides(db, cats):
    """Acceptance: re-uploading keeps all overrides (keys are voucher + cheque)."""
    imp(db, "vendor_pdc", DAY1 / "erp_pdc_register.xlsx")
    later = db.scalars(select(LineItem).where(LineItem.source_type == SourceType.VENDOR_PDC,
                                              LineItem.planned_date > date(2026, 12, 1))).first()
    db.add(Override(source_type=SourceType.VENDOR_PDC, source_key=later.source_key, action=OverrideAction.HOLD,
                    new_date=date(2026, 12, 20), reason="test"))
    db.commit()
    for path in (DAY1 / "erp_pdc_register.xlsx", DAY2 / "erp_pdc_register.xlsx"):  # same file, then next day
        imp(db, "vendor_pdc", path)
        cur = current_batches(db, "vendor_pdc")[0]
        hit = db.execute(select(LineItem.source_key).join(
            Override, (Override.source_type == LineItem.source_type) & (Override.source_key == LineItem.source_key))
            .where(LineItem.batch_id == cur.id, Override.is_active)).scalars().all()
        assert hit == [later.source_key]
    assert len(current_batches(db, "vendor_pdc")) == 1


# ---------------------------------------------------------------- reference data
def test_bank_balances_rules(db):
    rep = imp(db, "bank_balances", DAY1 / "bank_balances.csv")
    assert rep.status == "accepted" and rep.records == 4
    usd = db.scalar(select(BankAccount).where(BankAccount.currency == "USD"))
    assert usd.balances[0].fx_rate_to_base == Decimal("0.384")
    no_rate = "Bank,Account,Currency,As-of Date,Balance\nBank E,USD 2,USD,24/11/2026,10\n".encode()
    assert "manual rate" in import_file(db, "bank_balances", "b.csv", no_rate).errors[0].message
    fourth = "Bank,Account,Currency,As-of Date,Balance\nBank E,Current 9,OMR,24/11/2026,10\n".encode()
    rep = import_file(db, "bank_balances", "b.csv", fourth)
    assert rep.status == "rejected" and "limit is 3" in rep.errors[0].message


# ---------------------------------------------------------------- advisory checks
def test_overlap_and_bill_discount_findings(db, cats):
    for src, f in [("collections", "erp_receivables.xlsx"), ("vendor_pdc", "erp_pdc_register.xlsx"),
                   ("allocation", "erp_payment_plan.csv"), ("bill_discount", "bank_bd_lc.xlsx")]:
        assert imp(db, src, DAY1 / f).status == "accepted"
    rules = {f.rule: f for f in find_overlaps(db)}
    assert "pdc_vs_allocation" in rules and "PINV-OVERLAP-1" in rules["pdc_vs_allocation"].message
    bd = rules["bill_discounted_invoice"]
    db.add(Override(source_type=SourceType.COLLECTIONS, source_key=bd.keys[0][1],
                    action=OverrideAction.BILL_DISCOUNTED))
    db.commit()
    assert "bill_discounted_invoice" not in {f.rule for f in find_overlaps(db)}


# ---------------------------------------------------------------- migration
def test_v1_database_is_upgraded_in_place(tmp_path):
    from app.db import make_engine
    from app.services.init_db import SCHEMA_VERSION, init_db
    eng = make_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with eng.begin() as c:
        c.exec_driver_sql("CREATE TABLE app_setting (key VARCHAR(64) PRIMARY KEY, value JSON NOT NULL, "
                          "updated_at DATETIME, updated_by_id INTEGER)")
        c.exec_driver_sql("INSERT INTO app_setting VALUES ('schema_version', '1', NULL, NULL)")
        c.exec_driver_sql("CREATE TABLE import_batch (id INTEGER PRIMARY KEY, source_type VARCHAR(24) NOT NULL, "
                          "original_filename VARCHAR(255) NOT NULL, stored_filename VARCHAR(255) NOT NULL, "
                          "sha256 VARCHAR(64) NOT NULL, size_bytes INTEGER NOT NULL, as_of_date DATE, "
                          "status VARCHAR(24), row_count INTEGER, error_count INTEGER, validation_report JSON, "
                          "uploaded_by_id INTEGER, uploaded_at DATETIME NOT NULL)")
        c.exec_driver_sql("INSERT INTO import_batch (id, source_type, original_filename, stored_filename, sha256, "
                          "size_bytes, uploaded_at) VALUES (1, 'vendor_pdc', 'a', 'a', 'x', 1, '2026-11-01')")
    init_db(eng)
    with eng.connect() as c:
        cols = {r[1] for r in c.exec_driver_sql("PRAGMA table_info('import_batch')")}
        assert "slot" in cols
        assert c.execute(text("SELECT slot FROM import_batch")).scalar() == "vendor_pdc"
        assert int(c.execute(text("SELECT value FROM app_setting WHERE key='schema_version'")).scalar()) == SCHEMA_VERSION
