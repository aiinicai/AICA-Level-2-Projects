"""Tally Integration: connection test, open companies, master sync (read-only) and master browser."""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout)

from ipt.core.permissions import has_permission
from ipt.services.tally.client import TallyError
from ipt.services.tally.masters import SPECS
from ipt.ui.helpers import error, fill_table, make_table, muted, title
from ipt.ui.pages.base import BasePage

LABELS = {"group": "Groups", "ledger": "Ledgers", "stock_item": "Stock items", "unit": "Units",
          "godown": "Godowns", "voucher_type": "Voucher types", "cost_centre": "Cost centres"}


class _Sig(QObject):
    done = Signal(object, str)   # result, error message
    progress = Signal(str)


class _Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn, self.sig = fn, _Sig()

    def run(self):
        try:
            self.sig.done.emit(self.fn(self.sig.progress.emit), "")
        except TallyError as e:
            self.sig.done.emit(None, str(e))
        except Exception as e:  # noqa: BLE001 - shown to the user
            self.sig.done.emit(None, f"{e.__class__.__name__}: {e}")


class TallyIntegrationPage(BasePage):
    title_text = "Tally Integration"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Tally Integration"))
        self.layout_.addWidget(muted("IPT talks to TallyPrime on this computer (XML over HTTP). Syncing only READS "
                                     "masters from Tally; nothing is changed in Tally here."))
        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        self.lbl_target = QLabel()
        self.lbl_status = QLabel("Not checked yet")
        self.lbl_status.setWordWrap(True)
        bar = QHBoxLayout()
        self.btn_test = QPushButton("Test connection")
        self.btn_test.setObjectName("Primary")
        bar.addWidget(self.btn_test)
        bar.addStretch(1)
        cl.addWidget(self.lbl_target)
        cl.addWidget(self.lbl_status)
        cl.addLayout(bar)
        cl.addWidget(muted("If Tally is not reachable: in TallyPrime press F1 > Settings > Connectivity > "
                           "Client/Server configuration, set 'TallyPrime acts as' = Both and port = 9000, and "
                           "keep the company open."))
        self.layout_.addWidget(card)

        sync = QHBoxLayout()
        sync.addWidget(QLabel("Sync from Tally:"))
        self.checks = {}
        for t in SPECS:
            cb = QCheckBox(LABELS[t])
            cb.setChecked(True)
            self.checks[t] = cb
            sync.addWidget(cb)
        self.btn_sync = QPushButton("Sync masters")
        sync.addWidget(self.btn_sync)
        self.btn_gst = QPushButton("Create GST ledgers...")
        sync.addWidget(self.btn_gst)
        self.btn_fixgst = QPushButton("Fix GST details in Tally...")
        self.btn_fixgst.setToolTip("Fills the party state / GST registration in supplier ledgers and the GST UQC in "
                                   "units (GSTR-3B 'Uncertain transactions'). Shows the list first; writes only "
                                   "after you confirm.")
        sync.addWidget(self.btn_fixgst)
        sync.addStretch(1)
        self.layout_.addLayout(sync)
        self.lbl_sync = muted("")
        self.layout_.addWidget(self.lbl_sync)

        self.tabs = QTabWidget()
        self.tables = {}
        for t in SPECS:
            cols = ["Name", "Under", "Primary group", "GSTIN"] if t in ("ledger", "group") else \
                ["Name", "Under", "Base unit", "HSN", "GST %"] if t == "stock_item" else ["Name", "Under"]
            tb = make_table(cols)
            self.tables[t] = tb
            self.tabs.addTab(tb, LABELS[t])
        self.layout_.addWidget(self.tabs, 1)
        self.btn_test.clicked.connect(self._test)
        self.btn_sync.clicked.connect(self._sync)
        self.btn_gst.clicked.connect(self._create_gst)
        self.btn_fixgst.clicked.connect(self._fix_gst)
        self.tabs.currentChanged.connect(lambda _: self._load_tab())

    def refresh(self):
        c = self.s.companies.get_company(self.s.ctx.company_id) if self.s.ctx.company_id else None
        if c is None:
            self.lbl_target.setText("No company selected")
        else:
            self.lbl_target.setText(f"IPT company: {c.name}   →   Tally company: "
                                    f"{c.tally_company_name or '(not set – Company Settings > Edit)'}   at "
                                    f"{c.tally_host}:{c.tally_port}")
        role = self.s.ctx.user.role if self.s.ctx.user else None
        self.btn_sync.setEnabled(has_permission(role, "mapping.edit") and bool(c and c.tally_company_name))
        self.btn_gst.setEnabled(self.btn_sync.isEnabled())
        self.btn_fixgst.setEnabled(has_permission(role, "tally.import") and bool(c and c.tally_company_name))
        last = self.s.tally.last_sync()
        self.lbl_sync.setText(f"Last sync: {last:%d-%m-%Y %H:%M}" if last else "Masters not synced yet.")
        self._load_tab()

    def _load_tab(self):
        t = list(SPECS)[self.tabs.currentIndex()]
        rows = self.s.tally.masters(t)
        if t in ("ledger", "group"):
            data = [[r.name, r.parent, r.primary_group, r.gstin] for r in rows]
        elif t == "stock_item":
            data = [[r.name, r.parent, r.base_unit, r.hsn, "" if r.gst_rate is None else f"{r.gst_rate.normalize()}"]
                    for r in rows]
        else:
            data = [[r.name, r.parent] for r in rows]
        fill_table(self.tables[t], data)
        self.tabs.setTabText(self.tabs.currentIndex(), f"{LABELS[t]} ({len(rows)})")

    def _run(self, fn, on_done):
        job = _Job(fn)
        job.sig.progress.connect(self.lbl_sync.setText)
        job.sig.done.connect(on_done)
        self._job = job
        QThreadPool.globalInstance().start(job)

    def _test(self):
        self.btn_test.setEnabled(False)
        self.lbl_status.setText("Checking...")

        def done(st, err):
            self.btn_test.setEnabled(True)
            if err:
                self.lbl_status.setText(f"⛔ {err}")
                return
            icon = "✅" if st.reachable and st.company_open else ("⚠" if st.reachable else "⛔")
            extra = f"\nProduct: {st.product}\nOpen companies: {', '.join(st.open_companies or [])}" \
                if st.reachable else ""
            self.lbl_status.setText(f"{icon} {st.message}{extra}")
        self._run(lambda _p: self.s.tally.status(), done)

    def _sync(self):
        types = [t for t, cb in self.checks.items() if cb.isChecked()]
        if not types:
            error(self, "Select at least one master type")
            return
        self.btn_sync.setEnabled(False)
        self.lbl_sync.setText("Reading masters from Tally...")

        def done(counts, err):
            self.btn_sync.setEnabled(True)
            if err:
                error(self, err)
                self.lbl_sync.setText("Sync failed.")
                return
            self.lbl_sync.setText("Synced: " + ", ".join(f"{LABELS[k]} {v}" for k, v in counts.items()))
            self._load_tab()
        self._run(lambda p: self.s.tally.sync_masters(types, lambda n, t, m: p(m)), done)

    def _create_gst(self):
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        existing = {m.name.lower() for m in self.s.tally.masters("ledger")}
        heads = [h for h in ("CGST", "SGST", "IGST")]
        head, ok = QInputDialog.getItem(self, "Create GST ledger in Tally", "Tax head", heads, 0, False)
        if not ok:
            return
        name, ok = QInputDialog.getText(self, "Create GST ledger in Tally", "Ledger name", text=f"Input {head}")
        if not ok or not name.strip():
            return
        if name.strip().lower() in existing:
            error(self, f"'{name}' already exists in Tally")
            return
        c = self.s.companies.get_company(self.s.ctx.company_id)
        if QMessageBox.question(self, "Please confirm", f"Create ledger '{name}' (Duties & Taxes, GST, {head}) in "
                                f"Tally company '{c.tally_company_name}'?") != QMessageBox.Yes:
            return
        try:
            self.s.imports.create_gst_ledger(head, name.strip())
            self.lbl_sync.setText(f"Created '{name}' in Tally and refreshed ledgers.")
            self._load_tab()
        except TallyError as e:
            error(self, str(e))

    def _fix_gst(self):
        from PySide6.QtWidgets import QMessageBox
        self.btn_fixgst.setEnabled(False)
        self.lbl_sync.setText("Reading ledgers and units from Tally...")

        def previewed(plan, err):
            self.btn_fixgst.setEnabled(True)
            if err:
                self.lbl_sync.setText("")
                error(self, err)
                return
            led, units = plan["ledgers"], plan["units"]
            if not led and not units:
                self.lbl_sync.setText("GST details in Tally look complete – nothing to fix.")
                msg = "Every supplier ledger with a GSTIN has its state and GST registration, and every unit IPT " \
                      "knows has its UQC."
                if plan["units_unknown"]:
                    msg += "\n\nUnits with no UQC that IPT cannot map (set them in Tally): " + \
                        ", ".join(plan["units_unknown"])
                QMessageBox.information(self, "Fix GST details", msg)
                return
            lines = [f"Ledger '{x['name']}': state {x['gstin'][:2]} / GST registration (GSTIN {x['gstin']})"
                     for x in led] + [f"Unit '{u['name']}': UQC {u['suggested']}" for u in units]
            box = QMessageBox(self)
            box.setWindowTitle("Fix GST details in Tally")
            box.setIcon(QMessageBox.Question)
            box.setText(f"Update {len(led)} ledger(s) and {len(units)} unit(s) in Tally company "
                        f"'{plan['company']}'?")
            box.setInformativeText("Only the party state / GST registration and the unit's UQC are added; names, "
                                   "balances and vouchers are not touched. Tally is read again afterwards.")
            box.setDetailedText("\n".join(lines) + ("\n\nNo UQC known for: " + ", ".join(plan["units_unknown"])
                                                    if plan["units_unknown"] else ""))
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            if box.exec() != QMessageBox.Yes:
                self.lbl_sync.setText("")
                return
            self.btn_fixgst.setEnabled(False)
            self._run(lambda p: self.s.tally.gst_fix_apply(p), applied)

        def applied(res, err):
            self.btn_fixgst.setEnabled(True)
            if err:
                self.lbl_sync.setText("")
                error(self, err)
                return
            self.lbl_sync.setText(f"Fixed in Tally: {len(res['ledgers_fixed'])} ledger(s), "
                                  f"{len(res['units_fixed'])} unit(s).")
            msg = (f"Tally now shows the GST details for {len(res['ledgers_fixed'])} ledger(s) and the UQC for "
                   f"{len(res['units_fixed'])} unit(s).")
            if res["not_fixed"]:
                msg += "\n\nNot fixed (please check in Tally): " + ", ".join(res["not_fixed"])
            if res["errors"]:
                msg += "\n\nTally said: " + "; ".join(res["errors"][:5])
            msg += ("\n\nVouchers already in Tally keep the details they were saved with: open GSTR-3B → "
                    "Uncertain Transactions in Tally to accept them, or delete and import them again from IPT.")
            from PySide6.QtWidgets import QMessageBox as MB
            MB.information(self, "Fix GST details", msg)

        self._run(lambda _p: self.s.tally.gst_fix_preview(), previewed)
