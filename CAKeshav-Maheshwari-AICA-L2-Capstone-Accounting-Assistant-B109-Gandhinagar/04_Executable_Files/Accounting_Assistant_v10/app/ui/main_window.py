"""Main window: top bar (company, read invoices, status) + sidebar (Workbench, Journals, GSTR-2B, Memory, Setup)."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QSpinBox,
                             QStackedWidget, QStatusBar, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout,
                             QWidget)
from sqlalchemy import select

from ..config import delete_secret, get_secret, set_secret
from ..db.models import Company
from ..db.session import is_reachable
from ..db.sync import sync
from ..engine import masters as masters_mod, rules, tds as tds_mod
from ..tally.client import TallyClient
from ..tally.sync_masters import sync_company
from .common import LedgerCombo, card, run_bg, set_pill
from .inbox import CompanyPicker
from .journals_page import JournalsPage
from .bank_page import BankPage
from .other_pages import ReconPage, RulesPage
from .workbench import Workbench
from .entry_page import EntryPage
from .home_page import HomePage
from .reports_page import ReportsPage
from .compliance_page import ClosePage, CompliancePage, SearchPage
from .redflags_page import RedFlagsPage
from . import theme
from .state import AppState

class CompaniesPage(QWidget):
    synced = pyqtSignal()
    def __init__(self, app_state):
        super().__init__(objectName="page")
        self.st = app_state
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        root.addWidget(QLabel("Companies", objectName="h1"))
        root.addWidget(QLabel("Connect to TallyPrime, pick the companies you handle and pull their "
                              "masters and vouchers for the period you choose.", objectName="muted"))

        conn, cl = card("TallyPrime connection")
        row = QHBoxLayout()
        self.host = QLineEdit(self.st.settings.default_tally_host)
        self.port = QSpinBox(maximum=65535, value=self.st.settings.default_tally_port)
        self.btn_connect = QPushButton("Connect", objectName="primary")
        self.btn_connect.clicked.connect(self.connect_tally)
        self.conn_pill = QLabel("Not connected", objectName="pillWarn")
        for w, stretch in ((QLabel("Host"), 0), (self.host, 2), (QLabel("Port"), 0), (self.port, 0),
                           (self.btn_connect, 0), (self.conn_pill, 0)):
            row.addWidget(w, stretch)
        cl.addLayout(row)
        root.addWidget(conn)

        lst, ll = card("Companies open in Tally")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Company", "GSTIN", "State", "Last sync"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        ll.addWidget(self.table)
        act = QHBoxLayout()
        self.progress = QProgressBar(maximum=0, visible=False)
        self.progress_lbl = QLabel("", objectName="muted")
        self.btn_sync = QPushButton("Sync selected", objectName="primary", enabled=False)
        self.btn_sync.clicked.connect(self.sync_selected)
        self.btn_wizard = QPushButton("Setup wizard…")
        self.btn_wizard.clicked.connect(lambda: self.st.window.open_wizard())
        act.addWidget(self.btn_wizard)
        self.btn_settings = QPushButton("Company settings…")
        self.btn_settings.clicked.connect(self.company_settings)
        from .common import PeriodPicker
        self.sync_period = PeriodPicker("sync", "Vouchers for")
        self.sync_period.setToolTip("Voucher history pulled from Tally (used for learning, duplicates and matching)")
        act.addWidget(self.sync_period)
        act.addWidget(self.progress_lbl, 1)
        act.addWidget(self.progress, 1)
        act.addWidget(self.btn_settings)
        act.addWidget(self.btn_sync)
        ll.addLayout(act)
        root.addWidget(lst, 1)

        stats, sl = card("Last sync result")
        self.stats_grid = QGridLayout()
        sl.addLayout(self.stats_grid)
        root.addWidget(stats)
        self.companies: list[dict] = []

    def client(self) -> TallyClient:
        return TallyClient(self.host.text().strip(), self.port.value(), self.st.settings.tally_timeout_s)

    def connect_tally(self):
        self.btn_connect.setEnabled(False)
        self.conn_pill.setText("Connecting…")
        c = self.client()
        run_bg(self, lambda _p: c.companies(), self._got_companies, self._fail)

    def _got_companies(self, comps):
        self.btn_connect.setEnabled(True)
        self.companies = comps
        self.conn_pill.setObjectName("pillOk")
        self.conn_pill.setText(f"Connected · {len(comps)} open")
        self.conn_pill.setStyle(self.conn_pill.style())
        self.table.setRowCount(len(comps))
        for r, c in enumerate(comps):
            for col, v in enumerate((c["name"], c["gstin"], c["state"], "—")):
                self.table.setItem(r, col, QTableWidgetItem(v))
        self.btn_sync.setEnabled(bool(comps))
        self.st.window.set_tally_state(True)

    def _fail(self, msg):
        self.btn_connect.setEnabled(True)
        self.btn_sync.setEnabled(bool(self.companies))
        self.progress.setVisible(False)
        self.conn_pill.setObjectName("pillBad")
        self.conn_pill.setText("Error")
        self.conn_pill.setStyle(self.conn_pill.style())
        QMessageBox.warning(self, "TallyPrime", msg)

    def sync_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "Sync", "Select one or more companies first.")
            return
        picked = [(r, self.companies[r]) for r in rows]
        client, months = self.client(), self.st.settings.voucher_history_months
        per = self.sync_period.period()
        self.btn_sync.setEnabled(False)
        self.progress.setVisible(True)

        def job(progress):
            out = []
            session = self.st.Local()
            for r, info in picked:
                progress(f"{info['name']}: starting")
                rep = sync_company(session, client, info, months,
                                   progress=lambda m, n=info["name"]: progress(f"{n}: {m}"),
                                   default_style=self.st.settings.default_voucher_style,
                                   start=per.start, end=per.end)
                comp = session.get(Company, rep.company_id)
                rep.warm_rules = rules.warm_start(session, comp, masters_mod.load(session, comp.id))
                out.append((r, info, rep))
            session.close()
            return out

        run_bg(self, job, self._synced, self._fail, self.progress_lbl.setText)

    def _synced(self, results):
        self.progress.setVisible(False)
        self.btn_sync.setEnabled(True)
        self.progress_lbl.setText("Sync complete")
        while self.stats_grid.count():
            item = self.stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        tot, by_type, by_month, notes, period, first_last = {}, {}, {}, [], ("", ""), ("", "")
        for r, info, rep in results:
            self.table.setItem(r, 1, QTableWidgetItem(rep.gstin or "not found"))
            self.table.setItem(r, 3, QTableWidgetItem("just now"))
            if rep.skipped:
                notes.append(f"{info['name']}: {rep.skipped} voucher(s) had unreadable characters in Tally's reply "
                             "and were skipped (raw reply kept in the diagnostics folder).")
            if rep.gstin_note:
                notes.append(f"{info['name']}: {rep.gstin_note}")
            for k, v in {**rep.counts, "vouchers": rep.vouchers}.items():
                tot[k] = tot.get(k, 0) + v
            for k, v in rep.vouchers_by_type.items():
                by_type[k] = by_type.get(k, 0) + v
            for k, v in rep.vouchers_by_month.items():
                by_month[k] = by_month.get(k, 0) + v
            period, first_last = rep.period, rep.first_last
            if rep.orphaned_rules:
                QMessageBox.warning(self, info["name"], "These mapped ledgers no longer exist in Tally and "
                                    "their rules were paused for re-mapping:\n\n" + "\n".join(rep.orphaned_rules))
        fmt = lambda d: f"{d[6:8]}-{d[4:6]}-{d[:4]}" if len(d) == 8 else d
        labels = [("ledger", "Ledgers"), ("stock_item", "Stock items"), ("group", "Groups"),
                  ("voucher_type", "Voucher types"), ("godown", "Godowns"),
                  ("vouchers", f"Vouchers {fmt(period[0])} to {fmt(period[1])}")]
        for i, (k, lbl) in enumerate(labels):
            box = QVBoxLayout()
            w = QWidget()
            w.setLayout(box)
            box.addWidget(QLabel(f"{tot.get(k, 0):,}", objectName="stat"))
            box.addWidget(QLabel(lbl, objectName="muted"))
            self.stats_grid.addWidget(w, 0, i)
        if by_type:
            breakdown = "   ·   ".join(f"{k}: {v:,}" for k, v in by_type.items())
            lbl = QLabel("By voucher type (excludes cancelled and optional) - " + breakdown,
                         objectName="muted", wordWrap=True)
            self.stats_grid.addWidget(lbl, 1, 0, 1, len(labels))
        if by_month:
            mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            months = "   ·   ".join(f"{mon[int(k[4:]) - 1]}-{k[2:4]}: {v:,}" for k, v in by_month.items())
            lbl2 = QLabel(f"By month (first {fmt(first_last[0])}, last {fmt(first_last[1])}) - {months}",
                          objectName="muted", wordWrap=True)
            self.stats_grid.addWidget(lbl2, 2, 0, 1, len(labels))
        warm = sum(getattr(rep, "warm_rules", 0) for _, _, rep in results)
        if warm:
            notes.append(f"{warm} vendor-to-ledger rule(s) learned from Tally history (shown amber until approved).")
        if notes:
            QMessageBox.information(self, "Sync", "\n".join(notes))
        if results:
            self.st.session.expire_all()
            self.st.set_company(results[0][2].company_id)
            self.synced.emit()
        self.st.window.try_db_sync(silent=True)

    def company_settings(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        comp = None
        if rows and self.companies:
            guid = self.companies[rows[0]]["guid"]
            comp = self.st.session.scalar(select(Company).where(Company.tally_guid == guid))
        comp = comp or self.st.company()
        if not comp:
            QMessageBox.information(self, "Company settings", "Sync the company first.")
            return
        CompanySettingsDialog(self.st, comp, self).exec()


class CompanySettingsDialog(QDialog):
    def __init__(self, st, comp: Company, parent=None):
        super().__init__(parent)
        self.st, self.comp = st, comp
        self.setWindowTitle(f"Settings - {comp.name}")
        self.resize(680, 640)
        cfg = comp.settings or {}
        m = st.masters(comp)
        ledgers = sorted(m.ledgers)
        outer = QVBoxLayout(self)
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea(widgetResizable=True)
        inner = QWidget()
        form = QFormLayout(inner)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        self.folder = QLineEdit(cfg.get("folder", ""))
        b = QPushButton("Browse…")
        b.clicked.connect(self._browse)
        fr = QHBoxLayout()
        fr.addWidget(self.folder, 1)
        fr.addWidget(b)
        form.addRow("Invoice folder", fr)
        self.style = QComboBox()
        for key, label in (("purchase_accounting", "Purchase - accounting invoice (ledgers)"),
                           ("purchase_item", "Purchase - item invoice (stock items)"),
                           ("journal", "Journal")):
            self.style.addItem(label, key)
        self.style.setCurrentIndex(max(0, self.style.findData(comp.voucher_style)))
        form.addRow("Voucher style", self.style)
        self.vtype = QComboBox()
        self.vtype.setEditable(True)
        self.vtype.addItems([""] + sorted(m.voucher_types))
        self.vtype.setCurrentText(cfg.get("voucher_type_name", ""))
        form.addRow("Voucher type name (optional)", self.vtype)
        self.pending = QCheckBox("Book GST to an 'ITC pending 2B' ledger until matched")
        self.pending.setChecked(bool(comp.itc_pending_2b))
        form.addRow("", self.pending)
        self.narr = QLineEdit(cfg.get("narration_template", rules.DEFAULT_NARRATION))
        form.addRow("Narration template", self.narr)
        form.addRow("", QLabel("Placeholders: {kind} {supplier} {inv_no} {inv_date} {gstin}", objectName="muted"))
        self.round = LedgerCombo(ledgers, cfg.get("round_off_ledger", ""))
        form.addRow("Round-off ledger", self.round)
        self.purchase = LedgerCombo(ledgers, cfg.get("purchase_ledger", ""))
        form.addRow("Purchase ledger (item mode)", self.purchase)
        self.tcs = LedgerCombo(ledgers, cfg.get("tcs_ledger", ""))
        form.addRow("TCS receivable ledger", self.tcs)
        self.tds_ledgers = {}
        for code in tds_mod.DEFAULT_SECTIONS:
            cb = LedgerCombo(ledgers, cfg.get("tds_ledgers", {}).get(code, ""))
            self.tds_ledgers[code] = cb
            form.addRow(f"TDS ledger {code}", cb)
        # period lock
        from PyQt6.QtCore import QDate
        from PyQt6.QtWidgets import QDateEdit, QListWidget, QListWidgetItem
        lu = cfg.get("lock_until", "")
        self.chk_lock = QCheckBox("Lock books up to")
        self.chk_lock.setChecked(bool(lu))
        self.lock_date = QDateEdit(calendarPopup=True)
        self.lock_date.setDisplayFormat("dd-MM-yyyy")
        if lu:
            self.lock_date.setDate(QDate(int(lu[:4]), int(lu[4:6]), int(lu[6:8])))
        else:
            self.lock_date.setDate(QDate.currentDate().addMonths(-1))
        lr = QHBoxLayout()
        lr.addWidget(self.chk_lock)
        lr.addWidget(self.lock_date)
        lr.addStretch(1)
        form.addRow("Period lock", lr)
        form.addRow("", QLabel("e.g. after GST returns are filed. Posting into a locked period asks for a reason, "
                               "which is kept in the audit log.", objectName="muted", wordWrap=True))
        # credit cards kept outside Bank OD
        self.cards = QListWidget()
        self.cards.setMaximumHeight(150)
        picked = set(cfg.get("card_ledgers", []))
        pool = m.names_under("Current Liabilities", "Loans (Liability)", "Secured Loans", "Unsecured Loans",
                             "Sundry Creditors")
        pool = sorted(pool, key=lambda n: (n not in picked, not any(w in n.lower() for w in ("card", "amex", "visa",
                                                                                              "credit")), n))
        for n in pool[:400]:
            it = QListWidgetItem(n)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if n in picked else Qt.CheckState.Unchecked)
            self.cards.addItem(it)
        form.addRow("Treat as bank / card", self.cards)
        form.addRow("", QLabel("Credit cards are treated as Bank OD / CC. Tick card ledgers kept under another group "
                               "so they can be used on the bank side of Payment, Receipt and Contra.",
                               objectName="muted", wordWrap=True))
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)
        outer.addWidget(btns)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Invoice folder", self.folder.text())
        if d:
            self.folder.setText(d)

    def save(self):
        c = self.comp
        cfg = dict(c.settings or {})
        cfg.update({"folder": self.folder.text().strip(), "voucher_type_name": self.vtype.currentText().strip(),
                    "narration_template": self.narr.text().strip() or rules.DEFAULT_NARRATION,
                    "round_off_ledger": self.round.currentText().strip(),
                    "purchase_ledger": self.purchase.currentText().strip(),
                    "tcs_ledger": self.tcs.currentText().strip(),
                    "tds_ledgers": {k: cb.currentText().strip() for k, cb in self.tds_ledgers.items()
                                    if cb.currentText().strip()},
                    "lock_until": self.lock_date.date().toString("yyyyMMdd") if self.chk_lock.isChecked() else "",
                    "card_ledgers": [self.cards.item(i).text() for i in range(self.cards.count())
                                     if self.cards.item(i).checkState() == Qt.CheckState.Checked]})
        from ..db.models import AuditLog
        if cfg.get("lock_until") != (c.settings or {}).get("lock_until"):
            self.st.session.add(AuditLog(company_id=c.id, action="period_lock", entity="companies", entity_id=c.id,
                                         before={"lock_until": (c.settings or {}).get("lock_until", "")},
                                         after={"lock_until": cfg.get("lock_until", "")},
                                         updated_by=self.st.actor))
        c.settings = cfg
        c.voucher_style = self.style.currentData()
        c.itc_pending_2b = self.pending.isChecked()
        self.st.session.commit()
        if self.st.window:
            self.st.window._company_changed()
        self.accept()


class SettingsPage(QWidget):
    def __init__(self, app_state):
        super().__init__(objectName="page")
        self.st = app_state
        s = self.st.settings
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        root.addWidget(QLabel("Settings", objectName="h1"))
        c, cl = card("Office database (LAN)")
        form = QFormLayout()
        self.url = QLineEdit(s.remote_db_url, placeholderText="postgresql+pg8000://acct@192.168.1.10/acct")
        self.pwd = QLineEdit(echoMode=QLineEdit.EchoMode.Password,
                             placeholderText="stored in Windows Credential Manager")
        form.addRow("Connection URL", self.url)
        form.addRow("Password", self.pwd)
        cl.addLayout(form)
        cl.addWidget(QLabel("Leave blank to work on this PC only. When the LAN server is unreachable the app keeps "
                            "working locally and syncs on reconnect.", objectName="muted", wordWrap=True))
        root.addWidget(c)

        g, gl = card("Gemini (reads every invoice; local reading is the offline backup and cross-check)")
        gf = QFormLayout()
        self.use_gemini = QCheckBox("Use Gemini as a fallback")
        self.use_gemini.setChecked(s.use_gemini)
        self.key = QLineEdit(echoMode=QLineEdit.EchoMode.Password,
                             placeholderText="saved" if get_secret("gemini_api_key") else "paste API key")
        self.model = QLineEdit(s.gemini_model)
        self.model.setPlaceholderText("gemini-3.5-flash-lite (cheapest) · auto-lite · auto")
        self.threshold = QDoubleSpinBox(minimum=0.3, maximum=0.99, singleStep=0.05, value=s.gemini_threshold)
        self.unredacted = QCheckBox("Allow sending a page image when nothing could be redacted (not recommended)")
        self.unredacted.setChecked(s.allow_unredacted_image)
        gf.addRow("", self.use_gemini)
        key_row = QHBoxLayout()
        key_row.addWidget(self.key, 1)
        self.btn_del_key = QPushButton("Remove saved key")
        self.btn_del_key.setToolTip("Delete the Gemini key from Windows Credential Manager on this PC")
        self.btn_del_key.setEnabled(bool(get_secret("gemini_api_key")))
        self.btn_del_key.clicked.connect(self.remove_key)
        key_row.addWidget(self.btn_del_key)
        gf.addRow("API key (paid tier)", key_row)
        gf.addRow("Model", self.model)
        gf.addRow("", self.unredacted)
        gl.addLayout(gf)
        gl.addWidget(QLabel("PAN, Aadhaar, bank account, IFSC and UPI IDs are masked before upload; every upload is "
                            "logged in %APPDATA%\\AccountingAssistant\\gemini_uploads.log.", objectName="muted",
                            wordWrap=True))
        root.addWidget(g)

        e, ecl = card("Default entry type")
        ef = QFormLayout()
        self.def_style = QComboBox()
        for label, key in (("Journal", "journal"), ("Purchase", "purchase_accounting"),
                           ("Purchase (stock items)", "purchase_item")):
            self.def_style.addItem(label, key)
        self.def_style.setCurrentIndex(max(0, self.def_style.findData(s.default_voucher_style)))
        ef.addRow("Book invoices as", self.def_style)
        ecl.addLayout(ef)
        ecl.addWidget(QLabel("Used for newly synced companies. Each company can override it in Company settings, and "
                             "each supplier remembers what you last booked it as.", objectName="muted",
                             wordWrap=True))
        b_all = QPushButton("Apply to all existing companies")
        b_all.clicked.connect(self.apply_style_all)
        ecl.addWidget(b_all, alignment=Qt.AlignmentFlag.AlignLeft)
        root.addWidget(e)
        ap, apl = card("Appearance")
        self.theme_combo = QComboBox()
        for key, label in theme.THEMES:
            self.theme_combo.addItem(theme.swatch(key), label, key)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(theme.resolve(s.theme))))
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        tr = QHBoxLayout()
        tr.addWidget(QLabel("Theme"))
        tr.addWidget(self.theme_combo)
        tr.addStretch(1)
        apl.addLayout(tr)
        apl.addWidget(QLabel("Dark is easier on the eyes for long sessions. Some screens finish switching after a "
                             "restart.", objectName="muted", wordWrap=True))
        root.addWidget(ap)
        save = QPushButton("Save", objectName="primary")
        save.clicked.connect(self.save)
        root.addWidget(save, alignment=Qt.AlignmentFlag.AlignRight)
        root.addStretch(1)

    def _theme_changed(self, *_):
        from PyQt6.QtWidgets import QApplication
        from . import theme
        name = self.theme_combo.currentData()
        if self.st.window is not None:
            self.st.window.set_theme(name)
        else:
            QApplication.instance().setStyleSheet(theme.apply(name))
            self.st.settings.theme = name
            self.st.settings.save()

    def apply_style_all(self):
        style = self.def_style.currentData()
        n = 0
        for c in self.st.companies():
            c.voucher_style = style
            n += 1
        self.st.settings.default_voucher_style = style
        self.st.settings.save()
        self.st.session.commit()
        QMessageBox.information(self, "Default entry type", f"{n} compan{'y' if n == 1 else 'ies'} set to "
                                f"{self.def_style.currentText()}. Suppliers you've already booked differently keep "
                                "their own choice.")
        if self.st.window:
            self.st.window.workbench.refresh()

    def remove_key(self):
        if QMessageBox.question(self, "Remove Gemini key",
                                "Delete the saved Gemini API key from this PC? Invoices will then be read locally "
                                "only, until a key is added again.") != QMessageBox.StandardButton.Yes:
            return
        delete_secret("gemini_api_key")
        self.st.settings.use_gemini = False
        self.use_gemini.setChecked(False)
        self.st.settings.save()
        self.key.clear()
        self.key.setPlaceholderText("paste API key")
        self.btn_del_key.setEnabled(False)
        self.st.reset_remote()
        self.st.window.refresh_status()
        QMessageBox.information(self, "Remove Gemini key", "Gemini key removed from this PC.")

    def save(self):
        s = self.st.settings
        s.default_voucher_style = self.def_style.currentData()
        s.remote_db_url = self.url.text().strip()
        if self.pwd.text():
            set_secret("remote_db_password", self.pwd.text())
            self.pwd.clear()
        if self.key.text().strip():
            set_secret("gemini_api_key", self.key.text().strip())
            self.key.clear()
            self.key.setPlaceholderText("saved")
            self.btn_del_key.setEnabled(True)
        s.use_gemini = self.use_gemini.isChecked()
        s.gemini_model = self.model.text().strip() or "gemini-3.5-flash-lite"
        s.gemini_threshold = self.threshold.value()
        s.allow_unredacted_image = self.unredacted.isChecked()
        s.save()
        self.st.reset_remote()
        self.st.window.refresh_status()
        QMessageBox.information(self, "Settings", "Saved.")


class SetupPage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        from PyQt6.QtWidgets import QScrollArea
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 14, 20, 14)
        tabs = QTabWidget()
        self.companies = CompaniesPage(st)
        tabs.addTab(self.companies, "Companies && Tally")
        sc = QScrollArea(widgetResizable=True)
        sc.setWidget(SettingsPage(st))
        tabs.addTab(sc, "App settings")
        lay.addWidget(tabs)


class StatusDot(QLabel):
    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self._compact = False
        self._state, self._tip = "unknown", ""
        self.set("unknown", "")

    def compact(self, on: bool):
        if on != self._compact:
            self._compact = on
            self.set(self._state, self._tip)

    def set(self, state: str, tip: str):
        from . import theme as _th
        self._state, self._tip = state, tip
        colour = {"ok": "#22C55E", "bad": "#F04438", "warn": "#F79009"}.get(state, "#98A2B3")
        txt = f"<span style='color:{colour}; font-size:13px'>●</span>"
        if not self._compact:
            txt += f" <span style='color:{_th.INK}'>{self.label}</span>"
        self.setObjectName("statuspill" if not self._compact else "")
        self.setMaximumHeight(28)
        self.setText(txt)
        self.setToolTip(f"{self.label}: {tip}" if tip else self.label)


class MainWindow(QMainWindow):
    NAV = [("Home", "Money position, what's due, what's waiting"),
           ("Office", "All companies on one screen: waiting, due, needs attention"),
           ("Workbench", "Invoices to read, check and post"),
           ("New entry", "Payment, Receipt, Contra, Sales, Purchase, Journal, Debit / Credit Note"),
           ("Bank", "Import bank statements and post entries"),
           ("Reports", "Trial Balance, P&L, Balance Sheet and Schedule III live from Tally"),
           ("Compliance", "TDS tracker, GST control panel, AP / AR ageing"),
           ("Close", "Month-end close checklist"),
           ("Red flags", "Suspicious-transaction indicators, party risk, related parties"),
           ("Journals", "Recurring entries, templates, salary"),
           ("Claims", "Employee reimbursements and petty cash in bulk"),
           ("Exports", "Foreign-currency invoices, realisation, FIRC / e-BRC, forex revaluation"),
           ("GSTR-2B", "Match invoices with 2B"), ("Memory", "Learned ledger rules and supplier settings"),
           ("Setup", "Companies, Tally connection, Gemini, office DB")]

    def __init__(self, st: AppState):
        super().__init__()
        self.st = st
        st.window = self
        self.setWindowTitle("Accounting Assistant")
        self.setWindowIcon(theme.app_icon())
        self.setMinimumSize(980, 600)
        if st.companies():
            st.company_id = st.companies()[0].id

        shell = QWidget(objectName="shell")
        v = QVBoxLayout(shell)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ---- top bar: brand · company · actions · status
        top = QWidget(objectName="topbar")
        top.setFixedHeight(58)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(16, 8, 16, 8)
        tl.setSpacing(10)
        self.page_title = QLabel("", objectName="pagetitle")
        tl.addWidget(self.page_title)
        tl.addSpacing(12)
        self.picker = CompanyPicker(st)
        self.picker.setMinimumWidth(220)
        self.picker.setMaximumWidth(340)
        self.picker.setStyleSheet("QComboBox { font-weight: 600; }")
        tl.addWidget(self.picker)
        self.folder_lbl = QPushButton("", objectName="folder")
        self.folder_lbl.setMaximumWidth(300)
        self.folder_lbl.setMinimumWidth(0)
        self.folder_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folder_lbl.clicked.connect(self.choose_folder)
        tl.addWidget(self.folder_lbl, 1)
        tl.addStretch(1)
        self.progress_lbl = QLabel("", objectName="muted")
        self.progress = QProgressBar(maximum=0)
        self.progress.setFixedWidth(120)
        self.progress.setVisible(False)
        tl.addWidget(self.progress_lbl)
        tl.addWidget(self.progress)
        self.btn_sync_tally = QPushButton("Sync Tally")
        self.btn_sync_tally.setToolTip("Pull the latest ledgers, items and vouchers of this company from Tally")
        self.btn_reread = QPushButton("Re-read")
        self.btn_reread.setToolTip("Read the selected invoice again (e.g. after adding the Gemini key)")
        self.btn_read = QPushButton("Read new invoices", objectName="primary")
        self.btn_read.setMinimumHeight(34)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search all companies  Ctrl+F")
        self.search_box.setMaximumWidth(240)
        self.search_box.setMinimumWidth(120)
        self.search_box.returnPressed.connect(lambda: self.open_search(self.search_box.text()))
        tl.addWidget(self.search_box)
        tl.addWidget(self.btn_sync_tally)
        self.btn_check = QPushButton("Check company")
        self.btn_check.setToolTip("Compare the app with live Tally: day book, TB, P&L, Balance Sheet, Schedule III, "
                                  "bank balances, voucher numbering (read-only)")
        self.btn_check.clicked.connect(self.open_health)
        tl.addWidget(self.btn_check)
        tl.addWidget(self.btn_reread)
        tl.addWidget(self.btn_read)
        tl.addSpacing(6)
        self.theme_btn = self._theme_button()
        tl.addWidget(self.theme_btn)
        tl.addSpacing(4)
        self.dot_tally, self.dot_gemini, self.dot_db = StatusDot("Tally"), StatusDot("Gemini"), StatusDot("Office DB")
        for d in (self.dot_tally, self.dot_gemini, self.dot_db):
            tl.addWidget(d)
        v.addWidget(top)

        body = QWidget()
        h = QHBoxLayout(body)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        side = QWidget(objectName="sidebar")
        side.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        side.setFixedWidth(196)
        self.side = side
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 12, 0, 12)
        sv.setSpacing(1)
        logo = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(theme.app_icon().pixmap(34, 34))
        ic.setStyleSheet("padding-left: 14px;")
        logo.addWidget(ic)
        bl = QVBoxLayout()
        bl.setSpacing(0)
        bl.addWidget(QLabel("Accounting", objectName="sidebrand"))
        sub = QLabel("Assistant for Tally", objectName="sidesub")
        bl.addWidget(sub)
        logo.addLayout(bl, 1)
        sv.addLayout(logo)
        sv.addSpacing(10)
        self.stack = QStackedWidget()
        self.workbench = Workbench(st)
        self.setup = SetupPage(st)
        self.bank = BankPage(st)
        self.home = HomePage(st)
        self.search_page = SearchPage(st)
        from .claims_page import ClaimsPage
        from .exports_page import ExportsPage
        from .office_page import OfficePage
        self.office = OfficePage(st)
        self.entry_page = EntryPage(st)
        pages = [self.home, self.office, self.workbench, self.entry_page, self.bank, ReportsPage(st),
                 CompliancePage(st), ClosePage(st), RedFlagsPage(st), JournalsPage(st), ClaimsPage(st),
                 ExportsPage(st), ReconPage(st), RulesPage(st), self.setup, self.search_page]
        self.nav_buttons = []
        group = QButtonGroup(self)
        self._nav_group = group
        from PyQt6.QtWidgets import QFrame, QScrollArea
        nav_scroll = QScrollArea(widgetResizable=True)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        nav_host = QWidget(objectName="navhost")
        nv = QVBoxLayout(nav_host)
        nv.setContentsMargins(0, 0, 0, 0)
        nv.setSpacing(1)
        for i, ((name, tip), page) in enumerate(zip(self.NAV, pages)):
            self.stack.addWidget(page)
            if name in theme.NAV_SECTIONS:
                nv.addWidget(QLabel(theme.NAV_SECTIONS[name], objectName="navsec"))
            b = QPushButton(f" {theme.ICONS.get(name, '•')}   {name}", objectName="nav", checkable=True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, idx=i: self.go(idx))
            group.addButton(b)
            nv.addWidget(b)
            self.nav_buttons.append(b)
        nv.addStretch(1)
        hint = QLabel("Keys ⓘ", objectName="navsec")
        hint.setToolTip("Ctrl+A accept & post · Alt+C new ledger · Alt+↑/↓ next invoice · F4-F9, Alt+F5/F6 entry "
                        "types · Ctrl+F search · Tab moves; Tab past the last line adds one while Dr ≠ Cr")
        nv.addWidget(hint)
        nav_scroll.setWidget(nav_host)
        sv.addWidget(nav_scroll, 1)
        for page in pages[len(self.NAV):]:
            self.stack.addWidget(page)               # e.g. Search: opened from the top bar, no sidebar entry
        h.addWidget(side)
        h.addWidget(self.stack, 1)
        v.addWidget(body, 1)
        self.setCentralWidget(shell)
        self.setStatusBar(QStatusBar())

        self.btn_read.clicked.connect(self.read_new)
        self.btn_reread.clicked.connect(self.reread)
        self.btn_sync_tally.clicked.connect(self.sync_tally)
        st.on_company_change(self._company_changed)
        self.setup.companies.synced.connect(self._after_sync)

        first_run = not st.companies()
        self.go(len(self.NAV) - 1 if first_run else 0)
        from PyQt6.QtGui import QKeySequence, QShortcut
        for k, base in (("F5", "Payment"), ("F6", "Receipt"), ("F4", "Contra"), ("F8", "Sales"), ("F9", "Purchase"),
                        ("F7", "Journal"), ("Alt+F5", "Debit Note"), ("Alt+F6", "Credit Note")):
            QShortcut(QKeySequence(k), self, activated=lambda b=base: self.new_entry(b))
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: (self.search_box.setFocus(),
                                                                   self.search_box.selectAll()))
        self._company_changed()
        self.refresh_status()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(45000)
        if first_run:
            from PyQt6.QtCore import QTimer as _T
            _T.singleShot(400, self.open_wizard)

    def open_wizard(self):
        from .setup_wizard import SetupWizard
        SetupWizard(self.st, self).exec()

    # ---- window sizing
    def show_fitted(self):
        """Open at a size that fits the screen (taskbar excluded); maximise on laptop-size screens."""
        from PyQt6.QtGui import QGuiApplication
        scr = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        if scr.width() < 1500 or scr.height() < 860:
            self.showMaximized()
        else:
            w, h = min(1440, int(scr.width() * 0.92)), min(900, int(scr.height() * 0.92))
            self.resize(w, h)
            self.move(scr.x() + (scr.width() - w) // 2, scr.y() + (scr.height() - h) // 2)
            self.show()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w = self.width()
        narrow = w < 1520            # short button labels, compact status dots
        tight = w < 1320             # folder and page title hidden (the sidebar shows the page)
        self.folder_lbl.setVisible(not tight)          # folder stays reachable from the Workbench
        self.page_title.setVisible(not tight)          # the sidebar already shows the open page
        if hasattr(self, "theme_btn"):
            self.theme_btn.setText("◐" if narrow else "◐  Theme")
        self.btn_check.setText("Check" if narrow else "Check company")
        wide = w >= 1700
        self.folder_lbl.setMaximumWidth(300 if wide else 170)
        self.picker.setMaximumWidth(340 if wide else 250)
        self.folder_lbl.setMinimumWidth(120)
        self.progress_lbl.setMaximumWidth(260 if wide else 0)
        self.search_box.setMaximumWidth(240 if wide else 130 if tight else 150)
        for d in (self.dot_tally, self.dot_gemini, self.dot_db):
            d.compact(narrow)
        self.btn_read.setText("Read new" if narrow else "Read new invoices")
        self.btn_sync_tally.setText("Sync" if narrow else "Sync Tally")

    # ---- navigation
    WORKBENCH = 1

    def go(self, idx: int):
        self.nav_buttons[idx].setChecked(True)
        self.stack.setCurrentIndex(idx)
        self._accent(self.NAV[idx][0], self.stack.widget(idx))
        if self.NAV[idx][0] == "Workbench":
            self.workbench.refresh()

    def _accent(self, name: str, page):
        """Each module wears its own colour: a bar beside the page title, and the title in the top bar."""
        acc = theme.MODULE.get(name, theme.ACCENT)
        h1 = page.findChild(QLabel, "h1")
        if h1 is not None:
            h1.setStyleSheet(f"QLabel#h1 {{ color: {acc}; }}")
        self.page_title.setText(f"{theme.ICONS.get(name, '')}  {name}")
        self.page_title.setStyleSheet(f"color: {acc};")

    def open_health(self):
        from .health_dialog import HealthDialog
        if not self.st.company():
            return
        dlg = HealthDialog(self.st, self)
        dlg.show()
        dlg.run()
        dlg.exec()

    def open_search(self, text: str = ""):
        self.stack.setCurrentWidget(self.search_page)
        self._accent("Search", self.search_page)
        self._nav_group.setExclusive(False)
        for b in self.nav_buttons:
            b.setChecked(False)
        self._nav_group.setExclusive(True)
        self.search_page.start(text)

    def new_entry(self, base: str):
        """Tally keys from anywhere: F5 Payment, F6 Receipt, F4 Contra, F7 Journal, F8 Sales, F9 Purchase..."""
        self.go_page("New entry")
        self.entry_page.set_type(base)

    def go_page(self, name: str):
        names = [n for n, _ in self.NAV]
        key = {"Entry": "New entry"}.get(name, name)
        if key in names:
            self.go(names.index(key))

    def _company_changed(self):
        c = self.st.company()
        folder = (c.settings or {}).get("folder", "") if c else ""
        short = folder if len(folder) <= 34 else "…" + folder[-33:]
        self.folder_lbl.setText(("📁 " + short) if folder else "📁 Choose invoice folder…")
        self.folder_lbl.setToolTip((folder + "\n\n" if folder else "") + "Click to choose the invoice folder of this "
                                                                         "company")
        self.btn_read.setEnabled(bool(c))
        self.refresh_status()

    def choose_folder(self):
        c = self.st.company()
        if not c:
            self.toast("Pick or sync a company first")
            return
        cur = (c.settings or {}).get("folder", "")
        d = QFileDialog.getExistingDirectory(self, f"Invoice folder - {c.name}", cur)
        if not d:
            return
        c.settings = {**(c.settings or {}), "folder": d}
        self.st.session.commit()
        self._company_changed()
        self.toast(f"✓ Invoice folder for {c.name}: {d}")

    def _after_sync(self):
        self.picker.reload()
        self._company_changed()
        self.workbench.refresh()

    # ---- progress / toast
    def progress_start(self, text: str):
        self.progress.setVisible(True)
        self.progress_lbl.setText(text)
        self.btn_read.setEnabled(False)

    def progress_text(self, text: str):
        self.progress_lbl.setText(text)

    def progress_done(self, text: str = ""):
        self.progress.setVisible(False)
        self.progress_lbl.setText(text)
        self.btn_read.setEnabled(True)

    def toast(self, msg: str, ms: int = 6000):
        self.statusBar().showMessage(msg, ms)

    # ---- actions
    def read_new(self):
        self.go_page("Workbench")
        self.progress_start("Looking for new invoices…")

        def done(n):
            self.progress_done("" if n is None else (f"{n} new invoice(s) read" if n else "No new invoices"))
            if n:
                self.workbench.queue.set_filter("all")
        self.workbench.read_new(self.progress_text, done)

    def sync_tally(self):
        c = self.st.company()
        if not c:
            self.go(len(self.NAV) - 1)
            return
        cid, guid, client = c.id, c.tally_guid, self.st.client(c)
        months, style = self.st.settings.voucher_history_months, self.st.settings.default_voucher_style
        per = self.setup.companies.sync_period.period()
        self.progress_start(f"Syncing {c.name} from Tally…")
        self.btn_sync_tally.setEnabled(False)

        def job(progress):
            info = next((x for x in client.companies() if x["guid"] == guid), None)
            if info is None:
                raise RuntimeError("This company isn't open in TallyPrime. Open it in Tally and try again.")
            s = self.st.Local()
            try:
                rep = sync_company(s, client, info, months, progress=progress, default_style=style,
                               start=per.start, end=per.end)
                comp = s.get(Company, cid)
                rep.warm_rules = rules.warm_start(s, comp, masters_mod.load(s, comp.id))
                return rep
            finally:
                s.close()

        def done(rep):
            self.btn_sync_tally.setEnabled(True)
            f, t = rep.period
            span = f" ({f[6:8]}-{f[4:6]}-{f[:4]} to {t[6:8]}-{t[4:6]}-{t[:4]})" if f and t else ""
            self.progress_done(f"Synced: {rep.counts.get('ledger', 0)} ledgers, {rep.vouchers} vouchers{span}"
                               + (f" · {rep.skipped} skipped" if rep.skipped else "") + " · all screens refreshed")
            self.set_tally_state(True)
            self.st.session.expire_all()
            self.st.changed(cid)
            self.workbench.refresh()
            if self.stack.currentWidget() is self.home:
                self.home.load()
            self.bank._ctx_dirty = True
            self.bank.load_banks()
            if rep.orphaned_rules:
                QMessageBox.warning(self, "Sync", "These mapped ledgers no longer exist in Tally; their rules were "
                                    "paused:\n\n" + "\n".join(rep.orphaned_rules))

        def fail(msg):
            self.btn_sync_tally.setEnabled(True)
            self.progress_done("")
            QMessageBox.warning(self, "Sync Tally", msg)

        run_bg(self, job, done, fail, self.progress_text)

    def reread(self):
        if not self.workbench.entry.row:
            self.toast("Select an invoice first")
            return
        self.go_page("Workbench")
        self.progress_start("Re-reading…")
        self.workbench.reread_current(self.progress_text, lambda n: self.progress_done("Re-read done" if n else ""))

    def set_tally_state(self, ok: bool):
        self.dot_tally.set("ok" if ok else "bad", "TallyPrime reachable" if ok else "TallyPrime not reachable")

    def _theme_button(self):
        from PyQt6.QtGui import QAction, QActionGroup
        from PyQt6.QtWidgets import QMenu, QToolButton
        b = QToolButton(objectName="themebtn")
        b.setText("◐  Theme")
        b.setToolTip("Colour theme")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(b)
        grp = QActionGroup(menu)
        for key, label in theme.THEMES:
            a = QAction(theme.swatch(key), label, menu, checkable=True)
            a.setChecked(theme.NAME == key)
            a.triggered.connect(lambda _=False, k=key: self.set_theme(k))
            grp.addAction(a)
            menu.addAction(a)
        b.setMenu(menu)
        return b

    def set_theme(self, key: str):
        """Switch the colour theme live and remember it."""
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(theme.apply(key))
        self.st.settings.theme = theme.NAME
        self.st.settings.save()
        for d in (self.dot_tally, self.dot_gemini, self.dot_db):
            d.set(d._state, d._tip)
        try:
            self.go(self.stack.currentIndex())
        except Exception:
            pass
        for w in self.findChildren(QWidget):
            w.update()
        self.toast(f"Theme: {theme.LABEL}  (a few screens finish switching after a restart)")

    def refresh_status(self):
        key = get_secret("gemini_api_key")
        self.dot_gemini.set("ok" if key and self.st.settings.use_gemini else "warn",
                            "Gemini key saved" if key else "No Gemini key: invoices are read locally only")
        c = self.st.company()
        client = self.st.client(c)

        def job(_p):
            ok = client.ping()
            db = None
            if self.st.settings.remote_db_url:
                eng, Remote = self.st.remote()
                if is_reachable(eng):
                    local = self.st.Local()
                    try:
                        db = sync(local, Remote(), self.st.actor)
                    finally:
                        local.close()
                else:
                    db = False
            return ok, db

        def done(res):
            ok, db = res
            self.set_tally_state(ok)
            if db is None:
                self.dot_db.set("unknown", "Office DB not configured: working on this PC only")
            elif db is False:
                self.dot_db.set("warn", "Office DB unreachable: working locally, will sync on reconnect")
            else:
                self.dot_db.set("ok", f"Office DB synced (↑{db.pushed} ↓{db.pulled})")

        run_bg(self, job, done, lambda m: self.dot_db.set("bad", m))

    def try_db_sync(self, silent=True):
        self.refresh_status()
