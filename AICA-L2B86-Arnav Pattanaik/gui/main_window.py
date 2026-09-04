"""Main application window — sidebar + status bar + stacked screens."""

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import Qt

from gui.app_state import AppState
from gui.sidebar import Sidebar
from gui.status_bar import StatusBar
from gui.screen_compile import ScreenCompileData
from gui.screen_export import ScreenExport
from gui.screen_summaries import ScreenSummaries
from gui.screen_query import ScreenQueryBuilder
from gui.screen_energy_audit import ScreenEnergyAudit
from gui.settings_dialog import SettingsDialog


from core.session_manager import load_session, clear_session


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DISCOM Audit Data Compiler")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 700)

        self.state = AppState()
        self.state.on_change(self._on_state_change)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)

        self.sidebar = Sidebar(self.state)
        self.sidebar.screen_selected.connect(self._navigate)
        self.sidebar.new_audit_requested.connect(self._reset_session)
        self.sidebar.settings_button.clicked.connect(self._open_settings)
        content_row.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        content_row.addWidget(self.stack, 1)

        self.screen_compile = ScreenCompileData(self.state, on_compiled_callback=self._on_compiled)
        self.screen_export = ScreenExport(self.state)
        self.screen_summaries = ScreenSummaries(self.state)
        self.screen_query = ScreenQueryBuilder(self.state)
        self.screen_energy_audit = ScreenEnergyAudit(self.state)

        self.screen_keys = ["compile", "export", "summaries", "query_builder", "energy_audit"]
        for w in (self.screen_compile, self.screen_export, self.screen_summaries, self.screen_query, self.screen_energy_audit):
            self.stack.addWidget(w)

        root_layout.addLayout(content_row, 1)

        self.status_bar_widget = StatusBar(self.state)
        root_layout.addWidget(self.status_bar_widget)

        # Attempt to auto-restore last compiled session on startup
        if load_session(self.state):
            from PyQt6.QtWidgets import QApplication
            from gui.styles import get_theme_stylesheet
            app = QApplication.instance()
            if app and getattr(self.state.settings, "theme_name", None):
                app.setStyleSheet(get_theme_stylesheet(self.state.settings.theme_name))
            self._on_compiled()

    def _navigate(self, key: str):
        idx = self.screen_keys.index(key)
        self.stack.setCurrentIndex(idx)
        self.sidebar.select(key)
        if key == "export":
            self.screen_export.refresh()
        elif key == "summaries":
            self.screen_summaries.refresh()
        elif key == "query_builder":
            self.screen_query.refresh()
        elif key == "energy_audit":
            self.screen_energy_audit.refresh()

    def _on_compiled(self):
        self.sidebar.refresh()
        self.status_bar_widget.refresh()

    def _on_state_change(self):
        self.sidebar.refresh()
        self.status_bar_widget.refresh()

    def _reset_session(self):
        clear_session(self.state)
        self.screen_compile.refresh()
        self._navigate("compile")

    def _open_settings(self):
        dialog = SettingsDialog(self.state, self)
        dialog.exec()
