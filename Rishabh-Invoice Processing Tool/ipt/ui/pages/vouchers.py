"""Purchase Vouchers: build the Tally voucher for an approved invoice, preview Dr/Cr and XML, save XML."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMessageBox,
                               QPlainTextEdit, QPushButton, QSplitter, QTabWidget, QVBoxLayout, QWidget)

from ipt.core.permissions import PermissionDenied, has_permission

from ipt.core.money import format_inr
from ipt.services.tally.client import TallyError
from ipt.ui import worker
from ipt.ui.helpers import (checked_ids, error, fill_table, make_checkable, make_table, muted, selected_id,
                            set_all_checked, title)
from ipt.ui.pages.base import BasePage


class VouchersPage(BasePage):
    title_text = "Purchase Vouchers"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Purchase Vouchers"))
        self.layout_.addWidget(muted("Approved and fully mapped invoices become Tally purchase vouchers in the same "
                                     "format as your existing Tally entries. Preview here; importing into Tally "
                                     "always asks for confirmation."))
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Mode"))
        self.mode = QComboBox()
        self.mode.addItem("Auto (per supplier)", "auto")
        self.mode.addItem("Inventory (item invoice)", "inventory")
        self.mode.addItem("Accounting (ledgers only)", "accounting")
        bar.addWidget(self.mode)
        self.btn_save = QPushButton("Save XML file")
        bar.addWidget(self.btn_save)
        self.btn_import = QPushButton("Import into Tally")
        self.btn_import.setObjectName("Primary")
        bar.addWidget(self.btn_import)
        self.btn_all = QPushButton("Select all")
        bar.addWidget(self.btn_all)
        self.btn_ready = QPushButton("Select all ready")
        bar.addWidget(self.btn_ready)
        self.btn_batch = QPushButton("Import ticked")
        bar.addWidget(self.btn_batch)
        bar.addStretch(1)
        self.progress = muted("")
        bar.addWidget(self.progress)
        self.layout_.addLayout(bar)
        split = QSplitter()
        self.list = make_table(["", "Supplier", "Invoice no", "Date", "Total", "Ready?"])
        split.addWidget(self.list)
        tabs = QTabWidget()
        pv = QWidget()
        pl = QVBoxLayout(pv)
        self.blockers = QLabel()
        self.blockers.setWordWrap(True)
        pl.addWidget(self.blockers)
        self.items = make_table(["Stock item", "Qty", "Rate", "Amount", "Purchase ledger"])
        self.lines = make_table(["Ledger", "Debit", "Credit", ""])
        pl.addWidget(QLabel("Items"))
        pl.addWidget(self.items, 1)
        pl.addWidget(QLabel("Ledger entries"))
        pl.addWidget(self.lines, 1)
        self.totals = QLabel()
        pl.addWidget(self.totals)
        tabs.addTab(pv, "Voucher preview")
        self.xml = QPlainTextEdit()
        self.xml.setReadOnly(True)
        tabs.addTab(self.xml, "XML")
        split.addWidget(tabs)
        split.setSizes([450, 850])
        self.layout_.addWidget(split, 1)
        self.list.itemSelectionChanged.connect(self._preview)
        self.mode.currentIndexChanged.connect(lambda _: self.refresh())
        self.btn_save.clicked.connect(self._save)
        self.btn_import.clicked.connect(self._import)
        self.btn_ready.clicked.connect(self._select_ready)
        self.btn_all.clicked.connect(self._toggle_all)
        self.list.itemChanged.connect(lambda _: self._update_count())
        self.btn_batch.clicked.connect(self._import_batch)

    def refresh(self):
        invs = self.s.invoices.list_invoices("approved") + self.s.invoices.list_invoices("imported")
        self._status = {i.id: i.status for i in invs}
        rows = []
        for i in invs:
            if i.status == "imported":
                state = "Imported"
            else:
                try:
                    state = "Ready" if self.s.vouchers.build(i.id, self.mode.currentData()).ok else "Needs attention"
                except TallyError:
                    state = "Needs attention"
            rows.append(["", i.supplier_name, i.invoice_no,
                         i.invoice_date.strftime("%d-%m-%Y") if i.invoice_date else "",
                         format_inr(i.invoice_total), state])
        self.list.blockSignals(True)
        fill_table(self.list, rows, [i.id for i in invs])
        make_checkable(self.list)
        self.list.blockSignals(False)
        self._update_count()
        self._preview()
        busy = getattr(self, "_importing", False)
        can = has_permission(self.s.ctx.user.role if self.s.ctx.user else None, "tally.import")
        self.btn_batch.setEnabled(can and not busy)
        self.btn_ready.setEnabled(not busy)

    def _selected_ids(self) -> list[int]:
        return checked_ids(self.list)

    def _update_count(self):
        n = len(checked_ids(self.list))
        imp = [i for i in checked_ids(self.list) if getattr(self, "_status", {}).get(i) == "imported"]
        if len(imp) > 1 and not getattr(self, "_importing", False):
            self.btn_import.setText(f"Check Tally / import again ({len(imp)})")
            self.btn_import.setEnabled(has_permission(self.s.ctx.user.role if self.s.ctx.user else None,
                                                      "tally.import"))
        self.btn_batch.setText(f"Import ticked ({n})" if n else "Import ticked")
        self.btn_all.setText("Deselect all" if n and n == self.list.rowCount() else "Select all")

    def _toggle_all(self):
        self.list.blockSignals(True)
        set_all_checked(self.list, self.btn_all.text() == "Select all")
        self.list.blockSignals(False)
        self._update_count()

    def _select_ready(self):
        self.list.blockSignals(True)
        n = set_all_checked(self.list, True, lambda r: self.list.item(r, 5) and self.list.item(r, 5).text() == "Ready")
        self.list.blockSignals(False)
        self._update_count()
        if not n:
            error(self, "No invoice is 'Ready' to import.")

    def _import_batch(self):
        ids = [i for i in self._selected_ids() if getattr(self, "_status", {}).get(i) == "approved"]
        if not ids:
            error(self, "Tick one or more invoices that are 'Ready' (or click 'Select all ready').")
            return
        mode = self.mode.currentData()
        not_ready = [i for i in ids if not self.s.vouchers.build(i, mode).ok]
        if not_ready:
            error(self, f"{len(not_ready)} of the selected invoices are not ready (see 'Ready?'). Fix them or leave "
                        "them out.")
            return
        c = self.s.companies.get_company(self.s.ctx.company_id)
        invs = [self.s.invoices.get(i) for i in ids]
        total = sum((i.invoice_total or 0) for i in invs)
        lines = "\n".join(f"  {i.supplier_name} – {i.invoice_no} – {format_inr(i.invoice_total)}" for i in invs[:15])
        more = f"\n  … and {len(invs) - 15} more" if len(invs) > 15 else ""
        if QMessageBox.question(self, "Import into Tally",
                                f"Create {len(ids)} purchase voucher(s) in Tally company '{c.tally_company_name}'?\n"
                                f"Total {format_inr(total)}\n\n{lines}{more}\n\n"
                                "Each voucher is checked for duplicates first and verified in Tally afterwards; one "
                                "that may already be in Tally is skipped. This writes to your Tally books.",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self._importing = True
        self.btn_batch.setEnabled(False)
        self.btn_import.setEnabled(False)

        def done(results):
            self._importing = False
            self.progress.setText("")
            self.refresh()
            ok = sum(r["status"] == "success" for r in results)
            box = QMessageBox(self)
            box.setWindowTitle("Import result")
            box.setIcon(QMessageBox.Information if ok == len(results) else QMessageBox.Warning)
            box.setText(f"{ok} of {len(results)} voucher(s) created and verified in Tally.")
            box.setDetailedText("\n".join(f"[{r['status'].upper()}] {r['label']}: {r['message']}" for r in results))
            box.exec()

        def failed(msg):
            self._importing = False
            self.progress.setText("")
            self.refresh()
            error(self, msg)

        self._job = worker.start(worker.Job(self.s.imports.import_many, ids, mode, with_progress=True), done, failed,
                                 self.progress.setText)

    def _recheck_many(self, ids: list[int]) -> None:
        """Ask Tally about every ticked imported invoice; those deleted in Tally become ready again."""
        self._importing = True
        self.btn_batch.setEnabled(False)
        self.btn_import.setEnabled(False)

        def done(results):
            self._importing = False
            self.progress.setText("")
            self.refresh()
            freed = sum(r["status"] == "freed" for r in results)
            box = QMessageBox(self)
            box.setWindowTitle("Checked in Tally")
            box.setIcon(QMessageBox.Information)
            box.setText(f"{freed} of {len(results)} invoice(s) are no longer in Tally and are ready to import again."
                        + ("\nClick 'Select all ready' and then 'Import ticked'." if freed else ""))
            box.setDetailedText("\n".join(f"[{r['status'].upper()}] {r['label']}: {r['message']}" for r in results))
            box.exec()

        def failed(msg):
            self._importing = False
            self.progress.setText("")
            self.refresh()
            error(self, msg)

        self._job = worker.start(worker.Job(self.s.imports.release_many, ids, with_progress=True), done, failed,
                                 self.progress.setText)

    def _preview(self):
        self._preview_one()
        self._update_count()      # ticked imported invoices: the button checks them all

    def _preview_one(self):
        iid = selected_id(self.list)
        for t in (self.items, self.lines):
            fill_table(t, [])
        self.xml.setPlainText("")
        self.totals.setText("")
        self.btn_save.setEnabled(False)
        self.btn_import.setEnabled(False)
        if not iid:
            self.blockers.setText("Select an approved invoice.")
            return
        if getattr(self, "_status", {}).get(iid) == "imported":
            self.blockers.setText("✅ Already imported into Tally.\nDeleted that voucher in Tally and want to import "
                                  "it again? Click 'Check Tally / import again' – IPT first asks Tally and frees the "
                                  "invoice only if the voucher is really gone.")
            self.blockers.setStyleSheet("color:#15803d")
            self.btn_import.setText("Check Tally / import again")
            self.btn_import.setEnabled(has_permission(self.s.ctx.user.role if self.s.ctx.user else None,
                                                      "tally.import"))
            return
        self.btn_import.setText("Import into Tally")
        v = self.s.vouchers.build(iid, self.mode.currentData())
        self.blockers.setText("✅ Ready to import" if v.ok else "⛔ " + "\n⛔ ".join(v.blockers))
        self.blockers.setStyleSheet("color:#15803d" if v.ok else "color:#b91c1c")
        fill_table(self.items, [[x["item"], f"{x['qty'].normalize():f} {x['unit']}", format_inr(x["rate"]),
                                 format_inr(x["amount"]), x["ledger"]] for x in v.inventory])
        fill_table(self.lines, [[ln.ledger, format_inr(ln.amount) if ln.amount > 0 else "",
                                 format_inr(-ln.amount) if ln.amount < 0 else "", ln.note] for ln in v.lines])
        self.totals.setText(f"Total debit {format_inr(v.debit)}   Total credit {format_inr(v.credit)}   "
                            + ("(balanced)" if v.debit == v.credit else "(NOT balanced)"))
        self.xml.setPlainText(v.xml.replace("><", ">\n<") if v.xml else "")
        self.btn_save.setEnabled(v.ok)
        self.btn_import.setEnabled(v.ok and has_permission(self.s.ctx.user.role if self.s.ctx.user else None,
                                                           "tally.import"))
        self._built = v

    def _save(self):
        iid = selected_id(self.list)
        if not iid:
            return
        inv = self.s.invoices.get(iid)
        default = str(Path.home() / f"IPT_voucher_{(inv.invoice_no or iid)}.xml".replace("/", "-"))
        path, _ = QFileDialog.getSaveFileName(self, "Save Tally XML", default, "XML (*.xml)")
        if path:
            try:
                self.s.vouchers.save_xml(iid, self.mode.currentData(), Path(path))
                self.totals.setText(self.totals.text() + f"\nSaved {path}")
            except TallyError as e:
                error(self, str(e))

    def _import(self):
        ticked_imported = [i for i in self._selected_ids() if getattr(self, "_status", {}).get(i) == "imported"]
        if len(ticked_imported) > 1:
            self._recheck_many(ticked_imported)
            return
        iid = selected_id(self.list)
        if not iid:
            return
        inv = self.s.invoices.get(iid)
        if inv.status == "imported":
            try:
                freed = self.s.imports.release_if_deleted(iid)
            except (TallyError, PermissionDenied) as e:
                error(self, str(e))
                return
            self.refresh()
            if freed:
                QMessageBox.information(self, "Voucher not in Tally",
                                        "Tally no longer has this voucher, so the invoice is free again. Select it, "
                                        "check the preview and click 'Import into Tally'.")
            else:
                error(self, "Tally still has this voucher. Delete it in Tally first if you want to import it again.")
            return
        c = self.s.companies.get_company(self.s.ctx.company_id)
        v = self._built
        summary = "\n".join(f"  {ln.ledger}: {'Dr' if ln.amount > 0 else 'Cr'} {format_inr(abs(ln.amount))}"
                            for ln in v.lines)
        if QMessageBox.question(self, "Import into Tally",
                                f"Create this purchase voucher in Tally company '{c.tally_company_name}'?\n\n"
                                f"{inv.supplier_name} – {inv.invoice_no} dated {inv.invoice_date:%d-%m-%Y}\n{summary}\n\n"
                                "This writes to your Tally books.",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        remark = ""
        try:
            dups = self.s.imports.all_duplicates(iid)
        except TallyError as e:
            error(self, str(e))
            return
        if dups:
            d = dups[0]
            remark, ok = QInputDialog.getText(self, "Possible duplicate",
                                              f"This bill may already be in Tally: voucher {d['voucher_number']} "
                                              f"({d['type']}, found in the {d['source']}).\nImport anyway? Enter "
                                              "the reason:")
            if not ok or not remark.strip():
                return
        try:
            rec = self.s.imports.import_invoice(iid, self.mode.currentData(), remark)
        except (TallyError, PermissionDenied) as e:
            error(self, str(e))
            return
        if rec.status == "success":
            QMessageBox.information(self, "Imported", f"Tally created the voucher (created {rec.created}) and IPT "
                                    f"found it again in Tally. Voucher ID {rec.tally_master_id}.")
        elif rec.status == "unverified":
            error(self, "Tally reported success but IPT could not find the voucher again. Check Tally's Day Book.")
        else:
            error(self, "Tally did not create the voucher:\n" + _tally_reason(rec))
        self.refresh()


def _tally_reason(rec) -> str:
    """Tally's own line error, or a plain explanation when it only reports an exception count."""
    if rec.line_errors:
        return rec.line_errors
    raw = rec.response_xml or ""
    if "<EXCEPTIONS>" in raw and "<EXCEPTIONS>0</EXCEPTIONS>" not in raw:
        return ("Tally rejected the voucher without saying why (an 'exception'). Usually a master it needs does not "
                "exist in this Tally company – a stock item, ledger, unit or godown – or the Tally company chosen "
                "for this IPT company is not the one that is open. Check the voucher preview and Master Mapping, "
                "then Sync masters.")
    return raw[:500]

