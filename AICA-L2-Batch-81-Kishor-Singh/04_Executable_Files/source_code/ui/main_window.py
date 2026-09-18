"""Main application window: sidebar navigation, menu bar, global keyboard shortcuts."""
from __future__ import annotations

from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config.app_config import APP_ICON_PATH, APP_NAME
from ui.about_tab import AboutTab
from ui.ai_assistant_tab import AIAssistantTab
from ui.app_context import AppContext
from ui.compare_tab import CompareTab
from ui.convert_tab import ConvertTab
from ui.dashboard import DashboardTab
from ui.logs_tab import LogsTab
from ui.merge_tab import MergeTab
from ui.integrity_tab import IntegrityTab
from ui.ocr_tab import OCRTab
from ui.organizer_tab import OrganizerTab
from ui.pdf_tools_tab import PDFToolsTab
from ui.redact_tab import RedactTab
from ui.settings_tab import SettingsTab
from ui.sign_tab import SignTab
from ui.split_tab import SplitTab
from ui.submission_pack_tab import SubmissionPackTab
from ui.templates_tab import TemplatesTab
from ui.workflow_tab import WorkflowTab

_NAV_ITEMS = [
    "Dashboard",
    "Sign PDF",
    "Word → PDF",
    "Merge PDF",
    "Split PDF",
    "Organize Pages",
    "OCR / Scan",
    "Edit / Redact",
    "Compare",
    "AI Assistant",
    "PDF Tools",
    "Submission Pack",
    "Integrity / QR",
    "Batch Workflow",
    "Templates",
    "Settings",
    "Logs",
    "About",
]


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 820)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        self._build_ui()
        self._build_menu()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        title.setWordWrap(True)
        sidebar_layout.addWidget(title)

        self.nav_list = QListWidget()
        self.nav_list.addItems(_NAV_ITEMS)
        sidebar_layout.addWidget(self.nav_list, 1)
        layout.addWidget(sidebar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.dashboard = DashboardTab(self.ctx)
        self.sign_tab = SignTab(self.ctx)
        self.convert_tab = ConvertTab(self.ctx)
        self.merge_tab = MergeTab(self.ctx)
        self.split_tab = SplitTab(self.ctx)
        self.organizer_tab = OrganizerTab(self.ctx)
        self.ocr_tab = OCRTab(self.ctx)
        self.redact_tab = RedactTab(self.ctx)
        self.compare_tab = CompareTab(self.ctx)
        self.ai_assistant_tab = AIAssistantTab(self.ctx)
        self.pdf_tools_tab = PDFToolsTab(self.ctx)
        self.submission_pack_tab = SubmissionPackTab(self.ctx)
        self.integrity_tab = IntegrityTab(self.ctx)
        self.workflow_tab = WorkflowTab(self.ctx)
        self.templates_tab = TemplatesTab(self.ctx)
        self.settings_tab = SettingsTab(self.ctx)
        self.logs_tab = LogsTab(self.ctx)
        self.about_tab = AboutTab()

        self.tabs_by_name = {
            "Dashboard": self.dashboard,
            "Sign PDF": self.sign_tab,
            "Word → PDF": self.convert_tab,
            "Merge PDF": self.merge_tab,
            "Split PDF": self.split_tab,
            "Organize Pages": self.organizer_tab,
            "OCR / Scan": self.ocr_tab,
            "Edit / Redact": self.redact_tab,
            "Compare": self.compare_tab,
            "AI Assistant": self.ai_assistant_tab,
            "PDF Tools": self.pdf_tools_tab,
            "Submission Pack": self.submission_pack_tab,
            "Integrity / QR": self.integrity_tab,
            "Batch Workflow": self.workflow_tab,
            "Templates": self.templates_tab,
            "Settings": self.settings_tab,
            "Logs": self.logs_tab,
            "About": self.about_tab,
        }
        for name in _NAV_ITEMS:
            self.stack.addWidget(self.tabs_by_name[name])

        self.dashboard.navigate_requested.connect(self.navigate_to)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setCurrentRow(0)

    def _on_nav_changed(self, row: int) -> None:
        self.stack.setCurrentIndex(row)
        name = _NAV_ITEMS[row]
        if name == "Dashboard":
            self.dashboard.refresh()
        elif name == "Templates":
            self.templates_tab.refresh()
        elif name == "Logs":
            self.logs_tab.refresh()
        elif name == "AI Assistant":
            self.ai_assistant_tab._refresh_status()

    def navigate_to(self, tab_name: str) -> None:
        if tab_name in _NAV_ITEMS:
            self.nav_list.setCurrentRow(_NAV_ITEMS.index(tab_name))

    # ----------------------------------------------------------------- menu
    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        act_add_files = QAction("Add Files...", self)
        act_add_files.setShortcut(QKeySequence("Ctrl+O"))
        act_add_files.triggered.connect(lambda: self._delegate("add_files"))
        file_menu.addAction(act_add_files)

        act_add_folder = QAction("Add Folder...", self)
        act_add_folder.setShortcut(QKeySequence("Ctrl+Shift+O"))
        act_add_folder.triggered.connect(lambda: self._delegate("add_folder"))
        file_menu.addAction(act_add_folder)

        file_menu.addSeparator()
        act_process = QAction("Process / Save", self)
        act_process.setShortcut(QKeySequence("Ctrl+S"))
        act_process.triggered.connect(lambda: self._delegate("process"))
        file_menu.addAction(act_process)

        file_menu.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        edit_menu = menu_bar.addMenu("&Edit")
        act_select_all = QAction("Select All", self)
        act_select_all.setShortcut(QKeySequence("Ctrl+A"))
        act_select_all.triggered.connect(lambda: self._delegate("select_all"))
        edit_menu.addAction(act_select_all)

        act_remove = QAction("Remove Selected", self)
        act_remove.setShortcut(QKeySequence("Delete"))
        act_remove.triggered.connect(lambda: self._delegate("remove_selected"))
        edit_menu.addAction(act_remove)

        help_menu = menu_bar.addMenu("&Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(lambda: self.navigate_to("About"))
        help_menu.addAction(act_about)

    def _delegate(self, method_name: str) -> None:
        """Forward a global shortcut/menu action to whichever method the
        currently visible tab implements (tabs that don't support an action
        simply don't define the method, so this is a no-op for them)."""
        current = self.stack.currentWidget()
        method = getattr(current, method_name, None)
        if callable(method):
            method()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.ctx.config.save()
        super().closeEvent(event)
