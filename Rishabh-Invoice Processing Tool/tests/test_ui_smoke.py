"""Opens the main window offscreen and exercises navigation + switching."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402

from ipt.services.company_service import CompanyInput  # noqa: E402
from ipt.ui.main_window import MainWindow  # noqa: E402
from ipt.ui.services import Services  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_main_window_switching(qapp, db, admin, tmp_path):
    s = Services.build(db, tmp_path / "data")
    s.ctx.user = admin
    a = s.companies.create_company(CompanyInput(name="Alpha", state_code="08"), admin)
    b = s.companies.create_company(CompanyInput(name="Beta", state_code="27"), admin)
    s.companies.create_fy(a.id, 2025, admin)
    s.companies.create_fy(b.id, 2026, admin)
    w = MainWindow(s)
    assert w.company_combo.count() == 2
    for row in range(w.nav.count()):
        w.nav.setCurrentRow(row)          # every page must open without error
    w.company_combo.setCurrentIndex(w.company_combo.findData(b.id))
    assert s.ctx.company_id == b.id
    assert w.fy_combo.currentText() == "2026-27"
    w.company_combo.setCurrentIndex(w.company_combo.findData(a.id))
    assert w.fy_combo.currentText() == "2025-26"
    w.close()


def test_phase2_pages_and_review_dialog(qapp, services, tmp_path):
    from ipt.services.extraction.pipeline import ExtractionPipeline
    from ipt.ui.invoice_review import InvoiceReviewDialog
    from ipt.ui.main_window import MainWindow
    from tests.pdfgen import gst, make_invoice
    pdf = make_invoice(tmp_path / "x.pdf", supplier_gstin=gst("08BBBCS2222B1Z"), buyer_gstin=services.company_gstin,
                       items=[("Cement", "2523", "1", "100.00", "100.00", "18%", "118.00")],
                       totals=[("Taxable Value", "100.00"), ("Grand Total", "999.00")])
    doc = services.documents.add_files([pdf]).added[0]
    iid = ExtractionPipeline(services).run(doc.id).invoice_id
    w = MainWindow(services)
    for row in range(w.nav.count()):
        w.nav.setCurrentRow(row)
    dlg = InvoiceReviewDialog(services, [iid], 0)
    assert dlg.inputs["invoice_total"].styleSheet().endswith("#fee2e2")   # wrong total shown red
    assert dlg.items.rowCount() == 1
    # click-to-fill: field focused, then the 'Grand Total' value clicked on the page
    import pymupdf
    with pymupdf.open(pdf) as d:
        page = d[0]
        hit = next(w for w in page.get_text("words") if w[4] == "999.00")
        fx, fy = (hit[0] + hit[2]) / 2 / page.rect.width, (hit[1] + hit[3]) / 2 / page.rect.height
    dlg._target = "invoice_total"
    dlg._pick_value(0, fx, fy, False)
    assert dlg.inputs["invoice_total"].text() == "999.00" and dlg.dirty
    dlg.inputs["invoice_total"].setText("100.00")
    dlg._mark_dirty()
    assert dlg._save()
    assert str(services.invoices.get(iid).invoice_total) == "100.00"
    dlg.dirty = False
    dlg.close()
    w.close()


def test_extraction_job_reports_progress(qapp, services, tmp_path):
    from ipt.ui.pages.invoice_processing import ExtractionJob
    from tests.pdfgen import gst, make_invoice
    pdf = make_invoice(tmp_path / "i.pdf", supplier_gstin=gst("08BBBCS2222B1Z"), buyer_gstin=services.company_gstin,
                       items=[("Cement bags", "2523", "10", "350.00", "3500.00", "18%", "4130.00")],
                       totals=[("Taxable Value", "3500.00"), ("CGST", "315.00"), ("SGST", "315.00"),
                               ("Grand Total", "4130.00")])
    doc = services.documents.add_files([pdf]).added[0]
    job = ExtractionJob(services, [doc.id], "auto")
    seen, started, finished = [], [], []
    job.signals.progress.connect(lambda d, t, m: seen.append(m))
    job.signals.file_started.connect(started.append)
    job.signals.finished.connect(lambda ok, failed, c: finished.append((ok, failed)))
    job.run()
    assert started == [doc.id] and finished == [(1, 0)]
    assert any("Reading page 1 of 1" in m for m in seen)


def test_phase4_pages_with_data(qapp, services, tmp_path):
    from ipt.ui.main_window import MainWindow
    from ipt.ui.pages.purchase_register import PrImportDialog
    from tests.test_recon_services import PR_ROWS, _2b, _pr_excel
    _2b(services, tmp_path)
    dlg = PrImportDialog(services, _pr_excel(tmp_path, PR_ROWS[:2]))
    assert dlg.header.value() == 3 and dlg.mapping()["supplier_invoice_no"] == [4]
    dlg._accept()
    assert dlg.result_upload.rows_ok == 2
    services.recon.run("tally_2b")
    w = MainWindow(services)
    names = [w.nav.item(i).text().strip() for i in range(w.nav.count())]
    for page in ("GSTR-2B Upload", "Purchase Register", "GST Reconciliation", "ITC Analysis", "Exception Management"):
        w.nav.setCurrentRow(names.index(page))
        w.stack.currentWidget().refresh()
    recon = w.stack.widget(names.index("GST Reconciliation")) if False else None
    for i in range(w.stack.count()):
        p = w.stack.widget(i)
        if p.__class__.__name__ == "ReconPage":
            recon = p
    assert recon.table.rowCount() == 3
    recon.table.selectRow(0)
    recon._show_detail()
    assert "GSTR-2B" in recon.detail.toHtml()
    recon._set_filter("NOT_IN_BOOKS")
    assert recon.table.rowCount() == 1
    w.close()


def test_phase5_pages_with_data(qapp, services, tmp_path):
    from ipt.ui.main_window import MainWindow
    from tests.test_reports import _load
    _load(services, tmp_path)
    w = MainWindow(services)
    pages = {w.stack.widget(i).__class__.__name__: w.stack.widget(i) for i in range(w.stack.count())}
    dash = pages["DashboardPage"]
    dash.refresh()
    assert dash.v["docs"].text() == "2" and dash.v["taxable"].text().startswith("30,000")
    mis = pages["MisReportsPage"]
    mis.refresh()
    for i in range(mis.report.count()):
        mis.report.setCurrentIndex(i)          # every report renders
    mis.report.setCurrentIndex(0)
    assert mis.table.rowCount() == 2           # one supplier + total row
    pages["ExportCentrePage"].refresh()
    w.close()


def test_tick_boxes_select_all_and_validated(qapp, services, tmp_path):
    from PySide6.QtCore import Qt
    from ipt.services.extraction.pipeline import ExtractionPipeline
    from ipt.ui.helpers import checked_ids
    from ipt.ui.pages.processed_invoices import ProcessedInvoicesPage
    from ipt.ui.pages.vouchers import VouchersPage
    from tests.pdfgen import gst, make_invoice
    for n in (1, 2):
        pdf = make_invoice(tmp_path / f"t{n}.pdf", supplier_gstin=gst("08BBBCS2222B1Z"),
                           buyer_gstin=services.company_gstin, inv_no=f"T-{n}",
                           items=[("Cement", "2523", "1", "100.00", "100.00", "18%", "118.00")],
                           totals=[("Taxable Value", "100.00"), ("CGST", "9.00"), ("SGST", "9.00"),
                                   ("Grand Total", "118.00")])
        ExtractionPipeline(services).run(services.documents.add_files([pdf]).added[0].id)
    page = ProcessedInvoicesPage(services)
    page.refresh()
    assert page.table.rowCount() == 2 and checked_ids(page.table) == []
    page._toggle_all()
    assert len(checked_ids(page.table)) == 2 and page.btn_all.text() == "Deselect all"
    page._toggle_all()
    assert checked_ids(page.table) == []
    page.table.item(1, 0).setCheckState(Qt.Checked)
    assert page._ids() == [page.table.item(1, 0).data(Qt.UserRole)]
    vp = VouchersPage(services)
    vp.refresh()
    vp._toggle_all()
    assert len(checked_ids(vp.list)) == vp.list.rowCount()


def test_processing_extracts_only_ticked_new_files_and_archives_old(qapp, services, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt
    from ipt.services.extraction.pipeline import ExtractionPipeline
    from ipt.ui.helpers import checked_ids
    from ipt.ui.pages.invoice_processing import InvoiceProcessingPage
    from tests.pdfgen import gst, make_invoice

    def bill(n):
        return make_invoice(tmp_path / f"p{n}.pdf", supplier_gstin=gst("08BBBCS2222B1Z"),
                            buyer_gstin=services.company_gstin, inv_no=f"P-{n}",
                            items=[("Cement", "2523", "1", "100.00", "100.00", "18%", "118.00")],
                            totals=[("Taxable Value", "100.00"), ("CGST", "9.00"), ("SGST", "9.00"),
                                    ("Grand Total", "118.00")])
    old = services.documents.add_files([bill(1)]).added[0]
    inv = ExtractionPipeline(services).run(old.id).invoice_id
    services.invoices.delete(inv)                         # old file goes back to the queue
    page = InvoiceProcessingPage(services)
    page.refresh()
    assert checked_ids(page.table) == []                  # nothing ticked by itself
    page._add([bill(2)])
    new_id = max(page._ids)
    assert checked_ids(page.table) == [new_id]            # the new file comes ticked
    started = []
    monkeypatch.setattr(page, "_run", lambda ids: started.append(ids))
    page._start_ticked()
    assert started == [[new_id]]                          # the old queued file is not read again
    # archive: a file with an invoice is hidden, not deleted
    inv2 = ExtractionPipeline(services).run(new_id).invoice_id
    removed, archived = services.documents.remove([new_id])
    assert (removed, archived) == (0, 1) and services.invoices.get(inv2) is not None
    page.refresh()
    assert new_id not in page._ids
    page.show_archived.setChecked(True)
    assert new_id in page._ids


def test_gstr3b_working_dialog(qapp, services, tmp_path):
    from ipt.ui.pages.itc import Gstr3bDialog
    from tests.gstr2b_samples import make_2b_excel
    from tests.pdfgen import gst
    dlg = Gstr3bDialog(services)                  # nothing loaded yet: says so, export off
    assert not dlg.btn_export.isEnabled() and "No GSTR-2B" in dlg.warn.text()
    g = gst("08AAACS1111A1Z")
    p = make_2b_excel(tmp_path / "2b.xlsx", [(g, "Shree", "S-1", "05-10-2025", 1050, "08-Rajasthan", "No", 1000, 0,
                                              25, 25, 0, "Yes")], period_month="October", fy="2025-26",
                      gstin=services.company_gstin)
    services.gstr2b.upload(p)
    dlg = Gstr3bDialog(services)
    assert dlg.btn_export.isEnabled() and dlg.lines.rowCount() == 11
    assert dlg.lines.item(4, 0).text() == "4(A)(5)" and "25" in dlg.lines.item(4, 3).text()
    assert "purchase register" in dlg.warn.text()


def test_reset_dialog(qapp, services, monkeypatch):
    from ipt.ui.pages import settings as page
    from ipt.ui.pages.settings import ResetDialog
    shown = []
    monkeypatch.setattr(page, "error", lambda _w, msg: shown.append(msg))   # no modal box in tests
    dlg = ResetDialog(services)
    assert set(dlg.groups()) == {"invoices", "gstr2b", "purchases", "recon"}     # setup off by default
    dlg.name.setText("wrong")
    dlg._go()                                       # mismatch: nothing starts
    assert dlg.result_ is None and dlg.btn_go.isEnabled() and "does not match" in shown[0]


def test_approve_ticked_including_bills_that_need_review(qapp, services, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from ipt.services.extraction.pipeline import ExtractionPipeline
    from ipt.ui.pages import processed_invoices as mod
    from tests.pdfgen import gst, make_invoice
    ids = []
    for n, total in ((1, "118.00"), (2, "999.00")):            # the second has a total error -> needs review
        pdf = make_invoice(tmp_path / f"a{n}.pdf", supplier_gstin=gst("08BBBCS2222B1Z"),
                           buyer_gstin=services.company_gstin, inv_no=f"A-{n}",
                           items=[("Cement", "2523", "1", "100.00", "100.00", "18%", "118.00")],
                           totals=[("Taxable Value", "100.00"), ("CGST", "9.00"), ("SGST", "9.00"),
                                   ("Grand Total", total)])
        ids.append(ExtractionPipeline(services).run(services.documents.add_files([pdf]).added[0].id).invoice_id)
    assert services.invoices.get(ids[1]).status == "needs_review"
    page = mod.ProcessedInvoicesPage(services)
    page.refresh()
    monkeypatch.setattr(page, "_ids", lambda selected_only=True: list(ids))
    clicked = {}

    def fake_exec(box):                                         # the user clicks 'Approve all 2'
        clicked["b"] = next(b for b in box.buttons() if b.text().startswith("Approve all"))
        return 0
    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda box: clicked["b"])
    monkeypatch.setattr(mod.QInputDialog, "getText", lambda *a, **k: ("Checked against the bill", True))
    monkeypatch.setattr(mod, "info", lambda *a: None)
    monkeypatch.setattr(mod, "error", lambda _w, m: (_ for _ in ()).throw(AssertionError(m)))
    page._approve()
    assert [services.invoices.get(i).status for i in ids] == ["approved", "approved"]
    assert "Checked against the bill" in services.invoices.get(ids[1]).remarks


def test_mouse_wheel_does_not_change_an_unclicked_dropdown(qapp):
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication, QComboBox, QWidget
    from ipt.ui.helpers import install_wheel_guard
    install_wheel_guard(qapp)
    w = QWidget()
    cb = QComboBox(w)
    cb.addItems(["tax_invoice", "credit_note", "other"])
    w.show()

    def wheel():
        ev = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120), Qt.NoButton, Qt.NoModifier,
                         Qt.NoScrollPhase, False)
        QApplication.sendEvent(cb, ev)
    wheel()
    assert cb.currentText() == "tax_invoice"           # not clicked: the wheel scrolls the page instead
    cb.setFocus()
    qapp.processEvents()
    if cb.hasFocus():                                  # offscreen platforms may refuse focus
        wheel()
        assert cb.currentText() == "credit_note"
    w.close()


def test_review_shows_tally_mapping_problems_before_import(qapp, services, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from ipt.ui.invoice_review import InvoiceReviewDialog
    from ipt.services.extraction.pipeline import ExtractionPipeline
    from tests.pdfgen import gst, make_invoice
    pdf = make_invoice(tmp_path / "t.pdf", supplier_gstin=gst("08BBBCS2222B1Z"), buyer_gstin=services.company_gstin,
                       items=[("Cement", "2523", "1", "100.00", "100.00", "18%", "118.00")],
                       totals=[("Taxable Value", "100.00"), ("Grand Total", "118.00")])
    iid = ExtractionPipeline(services).run(services.documents.add_files([pdf]).added[0].id).invoice_id
    c = services.companies.get_company(services.ctx.company_id)
    monkeypatch.setattr(services.companies, "get_company", lambda _i: SimpleNamespace(**{**c.__dict__,
                                                                                       "tally_company_name": "X"}))
    monkeypatch.setattr(services.tally, "masters", lambda *_a, **_k: [object()])
    monkeypatch.setattr(services.vouchers, "build", lambda *_a, **_k: SimpleNamespace(blockers=[
        "Invoice is not approved yet (approve it in Processed Invoices)",
        "Not mapped – Supplier → party ledger: ABC (08...)"]))
    dlg = InvoiceReviewDialog(services, [iid], 0)
    lst = dlg._validation_tab()                       # keep a reference: Qt deletes an unowned widget
    texts = [lst.item(i).text() for i in range(lst.count())]
    assert any("Tally import: Not mapped – Supplier" in x for x in texts)
    assert not any("not approved" in x for x in texts)
