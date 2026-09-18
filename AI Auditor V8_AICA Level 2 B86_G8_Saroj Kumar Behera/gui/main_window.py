"""
AI Auditor V8 - Main Application Window
Coordinates sidebar navigation, stacked page routing, model lifecycle, and status bar.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame, QStatusBar, QButtonGroup
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont

from config.constants import APP_NAME, APP_VERSION, APP_SUBTITLE
from gui.theme import APP_STYLESHEET
from gui.pages import (
    DashboardPage, UploadPage, ReviewPage, RatioPage, TrendPage,
    VariancePage, RiskPage, AuditVerificationPage, ExportPage,
    SettingsPage, HelpPage
)
from core.models import FinancialModel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model: FinancialModel = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(f"{APP_NAME} - {APP_SUBTITLE} (v{APP_VERSION})")
        self.resize(1280, 820)
        self.setMinimumSize(1000, 680)
        self.setStyleSheet(APP_STYLESHEET)

        # Central Layout: Sidebar + Stacked Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_hbox = QHBoxLayout(central_widget)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)

        # 1. Sidebar Navigation
        sidebar = self._create_sidebar()
        main_hbox.addWidget(sidebar)

        # 2. Stacked Pages
        self.stack = QStackedWidget()
        main_hbox.addWidget(self.stack, 1)

        # Initialize Pages
        self.page_dashboard = DashboardPage()
        self.page_upload = UploadPage()
        self.page_review = ReviewPage()
        self.page_ratio = RatioPage()
        self.page_trend = TrendPage()
        self.page_variance = VariancePage()
        self.page_risk = RiskPage()
        self.page_audit = AuditVerificationPage()
        self.page_export = ExportPage()
        self.page_settings = SettingsPage()
        self.page_help = HelpPage()

        # Add to stack
        self.pages_map = {
            "dashboard": (self.page_dashboard, self.btn_nav_dashboard),
            "upload": (self.page_upload, self.btn_nav_upload),
            "review": (self.page_review, self.btn_nav_review),
            "ratio": (self.page_ratio, self.btn_nav_ratio),
            "trend": (self.page_trend, self.btn_nav_trend),
            "variance": (self.page_variance, self.btn_nav_variance),
            "risk": (self.page_risk, self.btn_nav_risk),
            "audit": (self.page_audit, self.btn_nav_audit),
            "export": (self.page_export, self.btn_nav_export),
            "settings": (self.page_settings, self.btn_nav_settings),
            "help": (self.page_help, self.btn_nav_help),
        }

        for key, (page_widget, _) in self.pages_map.items():
            self.stack.addWidget(page_widget)

        # Connect internal signals
        self.page_dashboard.navigate_requested.connect(self.navigate_to)
        self.page_upload.model_loaded.connect(self._on_model_loaded)
        self.page_review.data_recalculated.connect(self._on_model_updated)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_status_entity = QLabel("No Financial Statement Loaded")
        self.lbl_status_entity.setStyleSheet("color: #475569; font-weight: 500; padding: 2px 8px;")
        self.status_bar.addWidget(self.lbl_status_entity)
        self.status_bar.showMessage("Ready | Offline Mode Active", 5000)

        # Default start page
        self.navigate_to("upload")

    def _create_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("SidebarWidget")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 12, 8, 16)
        layout.setSpacing(4)

        # App Brand
        lbl_title = QLabel("AI Auditor V8")
        lbl_title.setObjectName("SidebarTitle")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Financial & Audit System")
        lbl_sub.setObjectName("SidebarSubtitle")
        layout.addWidget(lbl_sub)

        # Navigation Button Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nav_dashboard = self._add_nav_btn("📊 Dashboard", "dashboard", layout)
        self.btn_nav_upload = self._add_nav_btn("📁 Upload Financials", "upload", layout)
        self.btn_nav_review = self._add_nav_btn("📝 Data Review & Mapping", "review", layout)
        self.btn_nav_ratio = self._add_nav_btn("📈 Financial Ratios", "ratio", layout)
        self.btn_nav_trend = self._add_nav_btn("📉 Trend Analysis", "trend", layout)
        self.btn_nav_variance = self._add_nav_btn("🔍 Significant Variations", "variance", layout)
        self.btn_nav_risk = self._add_nav_btn("⚠️ Potential Risk Areas", "risk", layout)
        self.btn_nav_audit = self._add_nav_btn("📋 Audit Verification", "audit", layout)
        self.btn_nav_export = self._add_nav_btn("📤 Export Reports", "export", layout)

        layout.addStretch()

        # Bottom Utilities
        self.btn_nav_settings = self._add_nav_btn("⚙️ Settings", "settings", layout)
        self.btn_nav_help = self._add_nav_btn("❓ User Manual", "help", layout)

        return sidebar

    def _add_nav_btn(self, text: str, page_key: str, layout: QVBoxLayout) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "nav-btn")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.navigate_to(page_key))
        self.nav_group.addButton(btn)
        layout.addWidget(btn)
        return btn

    def navigate_to(self, page_key: str):
        if page_key in self.pages_map:
            page_widget, btn = self.pages_map[page_key]
            btn.setChecked(True)
            self.stack.setCurrentWidget(page_widget)

    def _on_model_loaded(self, model: FinancialModel):
        self.model = model
        self._sync_model_across_pages()
        self.lbl_status_entity.setText(f"Active Company: {model.company_info.name} | Period: {model.company_info.financial_year_current}")
        self.status_bar.showMessage(f"Loaded {model.company_info.name} successfully!", 6000)
        self.navigate_to("dashboard")

    def _on_model_updated(self, model: FinancialModel):
        self.model = model
        self._sync_model_across_pages()
        self.status_bar.showMessage("Recalculated all ratios, variances and audit requirements!", 5000)

    def _sync_model_across_pages(self):
        if not self.model:
            return
        self.page_dashboard.load_model(self.model)
        self.page_review.load_model(self.model)
        self.page_ratio.load_model(self.model)
        self.page_trend.load_model(self.model)
        self.page_variance.load_model(self.model)
        self.page_risk.load_model(self.model)
        self.page_audit.load_model(self.model)
        self.page_export.load_model(self.model)
