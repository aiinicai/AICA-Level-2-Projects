"""First-run setup wizard: Tally connection -> companies -> first Sync -> invoice folder, bank, Gemini key ->
Check company. Also available later from Setup > Companies & Tally."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWizard, QWizardPage)

from .common import run_bg


class _Conn(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self.wiz = wiz
        self.setTitle("1. Connect to TallyPrime")
        self.setSubTitle("Open TallyPrime with your companies loaded. In Tally: F1 Help > Settings > Connectivity > "
                         "Client/Server configuration > TallyPrime acts as Server/Both, port 9000.")
        v = QVBoxLayout(self)
        r = QHBoxLayout()
        self.host = QLineEdit(wiz.st.settings.default_tally_host)
        self.port = QSpinBox(maximum=65535, value=wiz.st.settings.default_tally_port)
        b = QPushButton("Test connection", objectName="primary")
        b.clicked.connect(self.test)
        for w in (QLabel("Computer running Tally"), self.host, QLabel("Port"), self.port, b):
            r.addWidget(w)
        v.addLayout(r)
        self.msg = QLabel("", wordWrap=True)
        v.addWidget(self.msg)
        v.addStretch(1)
        self.ok = False

    def test(self):
        from ..tally.client import TallyClient
        self.msg.setText("Connecting…")
        c = TallyClient(self.host.text().strip() or "localhost", self.port.value(), self.wiz.st.settings.tally_timeout_s)

        def done(comps):
            self.wiz.companies = comps
            self.ok = bool(comps)
            self.msg.setText(f"✓ Connected. Companies open: {', '.join(x['name'] for x in comps) or 'none'}"
                             if comps else "Connected, but no company is open in Tally. Open one (F3) and test again.")
            s = self.wiz.st.settings
            s.default_tally_host, s.default_tally_port = self.host.text().strip() or "localhost", self.port.value()
            s.save()
            self.completeChanged.emit()

        def fail(m):
            self.ok = False
            self.msg.setText(f"✗ {m}")
            self.completeChanged.emit()
        run_bg(self, lambda _p: c.companies(), done, fail)

    def isComplete(self):
        return self.ok


class _Companies(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self.wiz = wiz
        self.setTitle("2. Pick companies and Sync")
        self.setSubTitle("Tick the companies you handle. Sync reads their ledgers, groups and this financial year's "
                         "vouchers from Tally (nothing is changed in Tally).")
        v = QVBoxLayout(self)
        self.list = QListWidget()
        v.addWidget(self.list, 1)
        r = QHBoxLayout()
        self.btn = QPushButton("Sync ticked companies", objectName="primary")
        self.btn.clicked.connect(self.sync)
        self.bar = QProgressBar(maximum=0, visible=False)
        self.lbl = QLabel("", objectName="muted", wordWrap=True)
        r.addWidget(self.btn)
        r.addWidget(self.bar, 1)
        v.addLayout(r)
        v.addWidget(self.lbl)
        self.done_ok = False

    def initializePage(self):
        self.list.clear()
        for c in self.wiz.companies:
            it = QListWidgetItem(f"{c['name']}   {c.get('gstin') or ''}")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            it.setData(Qt.ItemDataRole.UserRole, c)
            self.list.addItem(it)

    def sync(self):
        from ..db.models import Company
        from ..engine import masters as masters_mod, rules
        from ..tally.client import TallyClient
        from ..tally.sync_masters import sync_company
        picked = [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())
                  if self.list.item(i).checkState() == Qt.CheckState.Checked]
        if not picked:
            return
        st = self.wiz.st
        client = TallyClient(st.settings.default_tally_host, st.settings.default_tally_port, st.settings.tally_timeout_s)
        self.btn.setEnabled(False)
        self.bar.setVisible(True)

        def job(progress):
            s = st.Local()
            ids = []
            try:
                for info in picked:
                    rep = sync_company(s, client, info, st.settings.voucher_history_months,
                                       progress=lambda m, n=info["name"]: progress(f"{n}: {m}"),
                                       default_style=st.settings.default_voucher_style)
                    comp = s.get(Company, rep.company_id)
                    rules.warm_start(s, comp, masters_mod.load(s, comp.id))
                    ids.append(rep.company_id)
            finally:
                s.close()
            return ids

        def done(ids):
            self.bar.setVisible(False)
            self.btn.setEnabled(True)
            st.session.expire_all()
            self.wiz.synced_ids = ids
            if ids:
                st.set_company(ids[0])
            self.lbl.setText(f"✓ {len(ids)} compan{'y' if len(ids) == 1 else 'ies'} synced.")
            self.done_ok = True
            self.completeChanged.emit()

        def fail(m):
            self.bar.setVisible(False)
            self.btn.setEnabled(True)
            self.lbl.setText(f"✗ {m}")
        run_bg(self, job, done, fail, self.lbl.setText)

    def isComplete(self):
        return self.done_ok


class _Details(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self.wiz = wiz
        self.setTitle("3. Invoice folder, bank and Gemini")
        self.setSubTitle("For each company: where its purchase / expense invoices arrive, and its main bank. "
                         "Gemini (optional) helps read invoices; it is never used for bank statements.")
        self.v = QVBoxLayout(self)
        self.rows = []

    def initializePage(self):
        from ..db.models import Company
        from ..engine import entry, masters as masters_mod
        while self.v.count():
            it = self.v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                while it.layout().count():
                    w = it.layout().takeAt(0).widget()
                    if w:
                        w.deleteLater()
        st = self.wiz.st
        self.rows = []
        for cid in self.wiz.synced_ids:
            c = st.session.get(Company, cid)
            m = masters_mod.load(st.session, cid)
            self.v.addWidget(QLabel(f"<b>{c.name}</b>"))
            r = QHBoxLayout()
            folder = QLineEdit((c.settings or {}).get("folder", ""))
            folder.setPlaceholderText("Invoice folder")
            pick = QPushButton("Choose…")
            pick.clicked.connect(lambda _=False, f=folder: f.setText(
                QFileDialog.getExistingDirectory(self, "Invoice folder", f.text()) or f.text()))
            bankc = QComboBox()
            bankc.addItems([b for b in entry.cash_bank_ledgers(m, c) if m.ledgers.get(b, {}).get("_primary") !=
                            "Cash-in-Hand"])
            last = (c.settings or {}).get("last_bank", "")
            if last:
                bankc.setCurrentText(last)
            for w, k in ((folder, 3), (pick, 0), (QLabel("Main bank"), 0), (bankc, 2)):
                r.addWidget(w, k)
            self.v.addLayout(r)
            self.rows.append((cid, folder, bankc))
        g = QHBoxLayout()
        from ..config import get_secret
        self.key = QLineEdit(get_secret("gemini_api_key") or "")
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Gemini API key (optional)")
        g.addWidget(QLabel("Gemini key"))
        g.addWidget(self.key, 1)
        self.v.addLayout(g)
        self.v.addStretch(1)

    def validatePage(self):
        from ..config import set_secret
        from ..db.models import Company
        st = self.wiz.st
        for cid, folder, bankc in self.rows:
            c = st.session.get(Company, cid)
            cfg = dict(c.settings or {})
            if folder.text().strip():
                cfg["folder"] = folder.text().strip()
            if bankc.currentText():
                cfg["last_bank"] = bankc.currentText()
            c.settings = cfg
        st.session.commit()
        if self.key.text().strip():
            try:
                set_secret("gemini_api_key", self.key.text().strip())
            except Exception:
                pass
        return True


class _Finish(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self.wiz = wiz
        self.setTitle("4. Check against Tally")
        self.setSubTitle("Last step: the app compares its figures with Tally's own (Trial Balance, Balance Sheet, "
                         "day book, numbering). Anything flagged can be fixed before you start.")
        v = QVBoxLayout(self)
        self.run = QCheckBox("Run 'Check company' for the first company when I click Finish")
        self.run.setChecked(True)
        v.addWidget(self.run)
        v.addWidget(QLabel("Every day: Read new invoices (Workbench), import the bank statement (Bank), Sync after "
                           "entering in Tally directly, and see all companies on the Office page.", wordWrap=True,
                           objectName="muted"))
        v.addStretch(1)


class SetupWizard(QWizard):
    def __init__(self, st, parent=None):
        super().__init__(parent)
        self.st = st
        self.companies, self.synced_ids = [], []
        self.setWindowTitle("Set up Accounting Assistant")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(760, 520)
        for p in (_Conn(self), _Companies(self), _Details(self)):
            self.addPage(p)
        self.finish = _Finish(self)
        self.addPage(self.finish)

    def accept(self):
        super().accept()
        win = self.st.window
        if win is not None:
            win.refresh_status()
            win._company_changed()
            win.go_page("Office" if len(self.synced_ids) > 1 else "Home")
            if self.finish.run.isChecked() and self.synced_ids:
                self.st.set_company(self.synced_ids[0])
                win.open_health()
