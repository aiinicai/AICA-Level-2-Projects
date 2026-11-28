import sqlite3

import pytest

from ipt.db.base import Database
from ipt.services.document_service import DocumentError
from tests.pdfgen import gst, make_invoice

SAMPLE_ITEMS = [("Cement bags", "2523", "10", "350.00", "3,500.00", "18%", "4,130.00")]


def _pdf(tmp_path, name="a.pdf", **kw):
    return make_invoice(tmp_path / name, supplier_gstin=gst("08BBBCS2222B1Z"), buyer_gstin=gst("08AAACA1111A1Z"),
                        items=SAMPLE_ITEMS, totals=[("Taxable Value", "3,500.00")], **kw)


def test_add_copies_and_detects_duplicate(services, tmp_path):
    f = _pdf(tmp_path)
    r1 = services.documents.add_files([f])
    r2 = services.documents.add_files([f])
    assert len(r1.added) == 1 and r1.added[0].pages == 1
    assert r2.added[0].duplicate_of_id == r1.added[0].id
    stored = services.documents.absolute_path(r1.added[0])
    assert stored.is_file() and "FY_2025_26" in str(stored) and "Invoices" in str(stored)
    assert f.is_file()  # original untouched


def test_unsupported_and_folder(services, tmp_path):
    folder = tmp_path / "in"
    folder.mkdir()
    _pdf(folder, "x.pdf")
    (folder / "notes.txt").write_text("hello")
    r = services.documents.add_files([folder])
    assert [d.original_filename for d in r.added] == ["x.pdf"]
    bad = tmp_path / "y.docx"
    bad.write_text("x")
    assert services.documents.add_files([bad]).skipped


def test_locked_fy_blocks_upload(services, tmp_path, admin):
    services.companies.set_fy_locked(services.ctx.fy_id, True, admin)
    with pytest.raises(DocumentError):
        services.documents.add_files([_pdf(tmp_path)])


def test_remove_deletes_stored_copy(services, tmp_path):
    d = services.documents.add_files([_pdf(tmp_path)]).added[0]
    path = services.documents.absolute_path(d)
    assert services.documents.remove([d.id]) == (1, 0)
    assert not path.exists()


def test_company_isolation(services, tmp_path, admin):
    from ipt.services.company_service import CompanyInput
    services.documents.add_files([_pdf(tmp_path)])
    other = services.companies.create_company(CompanyInput(name="Other", state_code="27"), admin)
    fy = services.companies.create_fy(other.id, 2025, admin)
    services.ctx.company_id, services.ctx.fy_id = other.id, fy.id
    assert services.documents.list_documents() == []


def test_v1_database_upgrades_without_data_loss(tmp_path, admin):
    # build a Phase 1 style database: only phase-1 tables, schema version 1
    path = tmp_path / "old.db"
    db = Database.for_file(path)
    db.create_schema()
    from ipt.services.auth_service import AuthService
    AuthService(db).create_user("boss", "password123", "admin")
    con = sqlite3.connect(path)
    for t in ("validation_results", "invoice_items", "invoices", "suppliers", "extraction_results", "documents"):
        con.execute(f"DROP TABLE {t}")
    con.execute("UPDATE schema_version SET version=1")
    con.commit()
    con.close()
    Database.for_file(path).create_schema()
    con = sqlite3.connect(path)
    from ipt.db.migrations import LATEST
    assert con.execute("SELECT version FROM schema_version").fetchone()[0] == LATEST
    assert con.execute("SELECT username FROM users").fetchone()[0] == "boss"
    assert con.execute("SELECT count(*) FROM invoices").fetchone()[0] == 0
    assert list(tmp_path.glob("old.before-migration-*.db"))


def test_migration_v8_makes_other_documents_tax_invoices(services, tmp_path):
    import sqlite3
    from ipt.services.extraction.pipeline import ExtractionPipeline
    from tests.pdfgen import gst, make_invoice
    pdf = make_invoice(tmp_path / "o.pdf", supplier_gstin=gst("08BBBCS2222B1Z"), buyer_gstin=services.company_gstin,
                       items=[("Cement", "2523", "1", "100.00", "100.00", "18%", "118.00")],
                       totals=[("Taxable Value", "100.00"), ("Grand Total", "118.00")])
    iid = ExtractionPipeline(services).run(services.documents.add_files([pdf]).added[0].id).invoice_id
    f = services.db.file_path()
    con = sqlite3.connect(f)
    con.execute("UPDATE invoices SET doc_type='other' WHERE id=?", (iid,))
    con.execute("UPDATE schema_version SET version=7")
    con.commit()
    con.close()
    services.db.create_schema()                          # IPT opened again: v8 runs
    assert services.invoices.get(iid).doc_type == "tax_invoice"
