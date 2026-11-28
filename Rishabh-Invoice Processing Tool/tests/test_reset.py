"""Reset company data: backup first, typed name required, only the chosen groups, other companies untouched."""
import pytest

from ipt.db.models import (Document, Gstr2bRecord, Invoice, MappingRule, PurchaseRegisterRecord, ReconRun,
                           Supplier, TallyImport)
from ipt.services.extraction.pipeline import ExtractionPipeline
from ipt.services.reset_service import ResetError
from tests.pdfgen import gst, make_invoice


def _count(s, model, cid):
    with s.db.session() as ss:
        return ss.query(model).filter(model.company_id == cid).count()


def _fill(services, tmp_path):
    from tests.gstr2b_samples import make_2b_excel
    from tests.test_recon_services import B2B, PR_ROWS, _pr_excel
    from ipt.services.recon.purchase_register import guess_mapping, read_rows
    pdf = make_invoice(tmp_path / "x.pdf", supplier_gstin=gst("08BBBCS2222B1Z"), buyer_gstin=services.company_gstin,
                       items=[("Cement", "2523", "1", "100.00", "100.00", "18%", "118.00")],
                       totals=[("Taxable Value", "100.00"), ("Grand Total", "118.00")])
    doc = services.documents.add_files([pdf]).added[0]
    iid = ExtractionPipeline(services).run(doc.id).invoice_id
    services.gstr2b.upload(make_2b_excel(tmp_path / "2b.xlsx", B2B, period_month="October", fy="2025-26",
                                         gstin=services.company_gstin))
    pr = _pr_excel(tmp_path, [PR_ROWS[0]])
    _, rows = read_rows(pr)
    services.purchases.import_excel(pr, None, 3, guess_mapping(rows[2]))
    services.recon.run("tally_2b")
    with services.db.session() as ss:
        ss.add(MappingRule(company_id=services.ctx.company_id, entity="party", source_key="X", tally_name="Y"))
    return iid, services.documents.absolute_path(services.documents.get(doc.id))


def test_reset_deletes_chosen_data_after_a_backup(services, tmp_path):
    cid = services.ctx.company_id
    iid, stored = _fill(services, tmp_path)
    assert stored.exists() and _count(services, Invoice, cid) == 1
    with pytest.raises(ResetError, match="does not match"):
        services.resets.reset(cid, ["invoices"], "wrong name")
    assert _count(services, Invoice, cid) == 1                       # nothing deleted
    summary = services.resets.summary(cid)
    assert summary["invoices"] == 2 and summary["gstr2b"] > 0 and summary["purchases"] == 1
    r = services.resets.reset(cid, ["invoices", "gstr2b", "purchases", "recon"], "abc enterprises")
    assert r.backup_file.startswith("IPT_backup_") and "before-reset" in r.backup_file
    for model in (Invoice, Document, Gstr2bRecord, PurchaseRegisterRecord, ReconRun, TallyImport):
        assert _count(services, model, cid) == 0, model
    assert not stored.exists() and r.files_removed >= 1
    assert _count(services, MappingRule, cid) == 1                   # setup kept unless asked for
    assert services.companies.get_company(cid) is not None
    with services.db.session() as ss:
        from ipt.db.models import AuditLog
        assert ss.query(AuditLog).filter_by(action="company.reset").count() == 1
    r = services.resets.reset(cid, ["setup"], "ABC Enterprises")
    assert _count(services, MappingRule, cid) == 0 and _count(services, Supplier, cid) == 0


def test_reset_needs_admin_and_a_choice(services, tmp_path):
    from ipt.core.permissions import PermissionDenied
    cid = services.ctx.company_id
    with pytest.raises(ResetError):
        services.resets.reset(cid, [], "ABC Enterprises")
    services.ctx.user.role = "accountant"
    with pytest.raises(PermissionDenied):
        services.resets.reset(cid, ["invoices"], "ABC Enterprises")
