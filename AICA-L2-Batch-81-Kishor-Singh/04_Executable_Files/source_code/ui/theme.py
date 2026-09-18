"""Light/dark/system theme stylesheets for a clean, professional office look."""
from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from models.enums import ThemeMode

_LIGHT_QSS = """
QWidget { background-color: #f5f6f8; color: #1c1f26; font-size: 13px; }
QMainWindow, QDialog { background-color: #f5f6f8; }
#Sidebar { background-color: #1f2b3d; }
#Sidebar QListWidget { background-color: #1f2b3d; border: none; color: #dbe4f0; font-size: 13px; }
#Sidebar QListWidget::item { padding: 10px 16px; }
#Sidebar QListWidget::item:selected { background-color: #2f6fed; color: white; border-radius: 4px; }
#Sidebar QListWidget::item:hover:!selected { background-color: #29374d; }
#AppTitle { color: white; font-size: 15px; font-weight: 600; padding: 16px; }
QTableWidget, QTableView { background-color: white; alternate-background-color: #f0f2f5; gridline-color: #e0e3e8; border: 1px solid #dde1e7; }
QHeaderView::section { background-color: #eef1f5; padding: 6px; border: none; border-bottom: 1px solid #dde1e7; font-weight: 600; }
QPushButton { background-color: #2f6fed; color: white; border: none; border-radius: 5px; padding: 7px 16px; font-weight: 600; }
QPushButton:hover { background-color: #255bcc; }
QPushButton:disabled { background-color: #b7c3d6; color: #eef1f5; }
QPushButton#SecondaryButton { background-color: #e5e9f0; color: #1c1f26; }
QPushButton#SecondaryButton:hover { background-color: #d6dce6; }
QPushButton#DangerButton { background-color: #d64545; }
QPushButton#DangerButton:hover { background-color: #b83a3a; }
QGroupBox { border: 1px solid #dde1e7; border-radius: 6px; margin-top: 10px; padding-top: 12px; font-weight: 600; background-color: white; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QTabWidget::pane { border: 1px solid #dde1e7; background: white; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit { background-color: white; border: 1px solid #ccd2db; border-radius: 4px; padding: 4px 6px; }
QProgressBar { border: 1px solid #ccd2db; border-radius: 4px; text-align: center; background: white; }
QProgressBar::chunk { background-color: #2f6fed; border-radius: 4px; }
#PreviewCanvas { background-color: #2b2f36; }
#DashboardCard { background-color: white; border: 1px solid #dde1e7; border-radius: 8px; }
#DashboardCard QLabel[cardTitle="true"] { font-size: 14px; font-weight: 700; }
"""

_DARK_QSS = """
QWidget { background-color: #1e2126; color: #e6e8eb; font-size: 13px; }
QMainWindow, QDialog { background-color: #1e2126; }
#Sidebar { background-color: #14171b; }
#Sidebar QListWidget { background-color: #14171b; border: none; color: #c7ccd4; font-size: 13px; }
#Sidebar QListWidget::item { padding: 10px 16px; }
#Sidebar QListWidget::item:selected { background-color: #3576f5; color: white; border-radius: 4px; }
#Sidebar QListWidget::item:hover:!selected { background-color: #22262d; }
#AppTitle { color: white; font-size: 15px; font-weight: 600; padding: 16px; }
QTableWidget, QTableView { background-color: #24272e; alternate-background-color: #2a2e36; gridline-color: #363b44; border: 1px solid #363b44; }
QHeaderView::section { background-color: #2a2e36; padding: 6px; border: none; border-bottom: 1px solid #363b44; font-weight: 600; color: #e6e8eb; }
QPushButton { background-color: #3576f5; color: white; border: none; border-radius: 5px; padding: 7px 16px; font-weight: 600; }
QPushButton:hover { background-color: #285ecb; }
QPushButton:disabled { background-color: #3a3f47; color: #7b8290; }
QPushButton#SecondaryButton { background-color: #2c2f36; color: #e6e8eb; }
QPushButton#SecondaryButton:hover { background-color: #383c45; }
QPushButton#DangerButton { background-color: #b83a3a; }
QPushButton#DangerButton:hover { background-color: #9a2f2f; }
QGroupBox { border: 1px solid #363b44; border-radius: 6px; margin-top: 10px; padding-top: 12px; font-weight: 600; background-color: #24272e; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QTabWidget::pane { border: 1px solid #363b44; background: #24272e; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit { background-color: #24272e; border: 1px solid #3a3f47; border-radius: 4px; padding: 4px 6px; color: #e6e8eb; }
QProgressBar { border: 1px solid #3a3f47; border-radius: 4px; text-align: center; background: #24272e; }
QProgressBar::chunk { background-color: #3576f5; border-radius: 4px; }
#PreviewCanvas { background-color: #111318; }
#DashboardCard { background-color: #24272e; border: 1px solid #363b44; border-radius: 8px; }
#DashboardCard QLabel[cardTitle="true"] { font-size: 14px; font-weight: 700; }
"""


def _system_prefers_dark() -> bool:
    app = QApplication.instance()
    if app is None:
        return False
    palette = app.palette()
    window_color = palette.color(QPalette.ColorRole.Window)
    return window_color.lightness() < 128


def apply_theme(app: QApplication, mode: str) -> None:
    """Apply the requested theme (System/Light/Dark) to the whole application."""
    if mode == ThemeMode.DARK.value:
        use_dark = True
    elif mode == ThemeMode.LIGHT.value:
        use_dark = False
    else:
        use_dark = _system_prefers_dark()
    app.setStyleSheet(_DARK_QSS if use_dark else _LIGHT_QSS)
