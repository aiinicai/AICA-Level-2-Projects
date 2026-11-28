"""Main window: sidebar navigation, company/FY switcher, page stack."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from ipt import __version__
from ipt.config import APP_NAME
from ipt.ui.pages.audit import AuditPage
from ipt.ui.pages.companies import CompaniesPage
from ipt.ui.pages.dashboard import DashboardPage
from ipt.ui.pages.invoice_processing import InvoiceProcessingPage
from ipt.ui.pages.processed_invoices import ProcessedInvoicesPage
from ipt.ui.pages.suppliers import SuppliersPage
from ipt.ui.pages.imports import ImportsPage
from ipt.ui.pages.mapping import MappingPage
from ipt.ui.pages.tally_integration import TallyIntegrationPage
from ipt.ui.pages.vouchers import VouchersPage
from ipt.ui.pages.placeholder import PlaceholderPage
from ipt.ui.pages.users import UsersPage
from ipt.ui.pages.exceptions import ExceptionsPage
from ipt.ui.pages.gstr2b import Gstr2bPage
from ipt.ui.pages.itc import ItcPage
from ipt.ui.pages.purchase_register import PurchaseRegisterPage
from ipt.ui.pages.recon import ReconPage
from ipt.ui.pages.reports import ExportCentrePage, MisReportsPage
from ipt.ui.pages.settings import SettingsPage
from ipt.ui.services import Services

# (section, name, phase, description) for modules not yet built.
PLANNED: list[tuple[str, str, int, str]] = []


class MainWindow(QMainWindow):
    logout_requested = Signal()

    def __init__(self, services: Services):
        super().__init__()
        self.s = services
        self.setWindowTitle(f"{APP_NAME}  v{__version__}")
        self.resize(1280, 800)
        self._pages: list = []

        root = QWidget(); outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        outer.addWidget(self._top_bar())
        body = QHBoxLayout(); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)
        self.nav = QListWidget(); self.nav.setObjectName("Sidebar"); self.nav.setFixedWidth(230)
        self.stack = QStackedWidget()
        body.addWidget(self.nav); body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)
        self.setCentralWidget(root)

        self.dashboard = DashboardPage(services)
        self.companies_page = CompaniesPage(services)
        self.companies_page.companies_changed.connect(self._reload_switchers)
        self._add_section("Home")
        self._add_page("Dashboard", self.dashboard)
        self._add_section("Processing")
        self._add_page("Invoice Processing", InvoiceProcessingPage(services))
        self._add_page("Processed Invoices", ProcessedInvoicesPage(services))
        self._add_page("Supplier Masters", SuppliersPage(services))
        self._add_section("Tally")
        self._add_page("Tally Integration", TallyIntegrationPage(services))
        self._add_page("Master Mapping", MappingPage(services))
        self._add_page("Purchase Vouchers", VouchersPage(services))
        self._add_page("XML Import", ImportsPage(services))
        self._add_section("GST")
        self._add_page("GSTR-2B Upload", Gstr2bPage(services))
        self._add_page("Purchase Register", PurchaseRegisterPage(services))
        self._add_page("GST Reconciliation", ReconPage(services))
        self._add_page("ITC Analysis", ItcPage(services))
        self._add_page("Exception Management", ExceptionsPage(services))
        self._add_section("Reports")
        self._add_page("MIS Reports", MisReportsPage(services))
        self._add_page("Export Centre", ExportCentrePage(services))
        current = "Reports"
        for section, name, phase, desc in PLANNED:
            if section != current:
                self._add_section(section); current = section
            self._add_page(name, PlaceholderPage(services, name, phase, desc))
        self._add_section("Admin")
        self._add_page("Company Settings", self.companies_page)
        self._add_page("Users", UsersPage(services))
        self._add_page("Audit Trail", AuditPage(services))
        self._add_page("Settings & Backup", SettingsPage(services))
        self.nav.currentRowChanged.connect(self._on_nav)

        self.statusBar().showMessage(f"Data folder: {services.data_root}")
        # answers written by Claude Code are picked up while IPT runs
        self._claude_timer = QTimer(self)
        self._claude_timer.timeout.connect(self.check_claude_answers)
        self._claude_timer.start(20000)
        self._reload_switchers()
        self.nav.setCurrentRow(1)

    # ---------- layout ----------
    def _top_bar(self) -> QWidget:
        bar = QFrame(); bar.setObjectName("TopBar")
        lay = QHBoxLayout(bar); lay.setContentsMargins(16, 8, 16, 8)
        brand = QLabel("IPT"); brand.setStyleSheet("font-size:14pt; font-weight:700; color:#2563eb;")
        lay.addWidget(brand); lay.addSpacing(20)
        lay.addWidget(QLabel("Company"))
        self.company_combo = QComboBox(); self.company_combo.setMinimumWidth(260)
        lay.addWidget(self.company_combo)
        lay.addWidget(QLabel("Financial year"))
        self.fy_combo = QComboBox(); self.fy_combo.setMinimumWidth(110)
        lay.addWidget(self.fy_combo)
        lay.addStretch(1)
        u = self.s.ctx.user
        self.user_label = QLabel(f"{u.full_name or u.username}  ({u.role})" if u else "")
        lay.addWidget(self.user_label)
        btn = QPushButton("Log out"); btn.clicked.connect(self.logout_requested.emit)
        lay.addWidget(btn)
        self.company_combo.currentIndexChanged.connect(self._on_company)
        self.fy_combo.currentIndexChanged.connect(self._on_fy)
        return bar

    def _add_section(self, text: str):
        item = QListWidgetItem(text.upper())
        item.setFlags(Qt.NoItemFlags)
        self.nav.addItem(item)
        self._pages.append(None)

    def _add_page(self, name: str, page):
        self.nav.addItem(QListWidgetItem(name))
        self.stack.addWidget(page)
        self._pages.append(page)

    # ---------- behaviour ----------
    def check_claude_answers(self) -> None:
        from ipt.services import claude_assist
        if not claude_assist.answered(self.s.data_root):
            return
        try:
            r = claude_assist.import_answers(self.s)
        except Exception as e:  # noqa: BLE001 - never break the window over a background check
            self.statusBar().showMessage(f"Could not read Claude Code answers: {e}")
            return
        if r.invoices:
            self.statusBar().showMessage(f"Claude Code checked {r.invoices} bill(s): {r.filled} value(s) filled "
                                         f"after IPT's checks – review and approve them in Processed Invoices.")
            page = self.stack.currentWidget()
            if hasattr(page, "refresh"):
                page.refresh()

    def _on_nav(self, row: int):
        page = self._pages[row] if 0 <= row < len(self._pages) else None
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self._safe_refresh(page)

    def _safe_refresh(self, page) -> None:
        """A page that fails to load shows the error; IPT itself keeps running."""
        try:
            page.refresh()
        except Exception as e:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).exception("Page %s could not be loaded", type(page).__name__)
            self.statusBar().showMessage(f"This page could not be loaded: {e} (details in logs\\ipt.log)")

    def _reload_switchers(self):
        keep = self.s.ctx.company_id or int(self.s.settings.get("last_company_id", "0") or 0)
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        for c in self.s.companies.list_companies(include_inactive=False):
            self.company_combo.addItem(c.name, c.id)
        idx = self.company_combo.findData(keep)
        self.company_combo.setCurrentIndex(idx if idx >= 0 else (0 if self.company_combo.count() else -1))
        self.company_combo.blockSignals(False)
        self._on_company()

    def _on_company(self, *_):
        cid = self.company_combo.currentData()
        self.s.ctx.company_id = cid
        if cid:
            self.s.settings.set("last_company_id", str(cid))
        keep = int(self.s.settings.get(f"last_fy_id_{cid}", "0") or 0) if cid else 0
        self.fy_combo.blockSignals(True)
        self.fy_combo.clear()
        for fy in (self.s.companies.list_fys(cid) if cid else []):
            self.fy_combo.addItem(fy.label + (" (locked)" if fy.is_locked else ""), fy.id)
        idx = self.fy_combo.findData(keep)
        self.fy_combo.setCurrentIndex(idx if idx >= 0 else (0 if self.fy_combo.count() else -1))
        self.fy_combo.blockSignals(False)
        self._on_fy()

    def _on_fy(self, *_):
        fid = self.fy_combo.currentData()
        self.s.ctx.fy_id = fid
        if fid and self.s.ctx.company_id:
            self.s.settings.set(f"last_fy_id_{self.s.ctx.company_id}", str(fid))
        page = self.stack.currentWidget()
        if page is not None and hasattr(page, "refresh"):
            self._safe_refresh(page)
