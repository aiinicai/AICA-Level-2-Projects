"""PDF Tool Suite - one desktop application combining PDF Studio and secure redaction."""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget

from pdf_redaction_tool import RedactionTool
from pdf_studio import PDFStudio


class PDFToolSuite(QMainWindow):
    """Hosts both PDF applications in a single Windows desktop window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF Tool Suite - Convert, Organize & Redact")
        self.resize(1320, 860)
        self.setMinimumSize(960, 680)

        # Keep the original controllers alive; their central widgets become suite tabs.
        self.studio = PDFStudio()
        self.redaction = RedactionTool()
        studio_widget = self.studio.takeCentralWidget()
        redaction_widget = self.redaction.takeCentralWidget()

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.addTab(studio_widget, "  PDF Studio  ")
        tabs.addTab(redaction_widget, "  Secure Redaction  ")
        self.setCentralWidget(tabs)


STYLE = """
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #003F35, stop:.52 #006A4E, stop:1 #0A7A5B);
}
QWidget { font-family: "Segoe UI"; font-size: 10pt; }
QTabWidget::pane { border: 1px solid #3b87ad; border-radius: 12px; background: rgba(5, 28, 68, 235); top: -1px; }
QTabBar::tab {
    background: #124E9B; color: #eaf5ff; padding: 13px 26px; min-width: 145px;
    margin-right: 5px; border-top-left-radius: 10px; border-top-right-radius: 10px; font-weight: 700;
}
QTabBar::tab:hover { background: #1976D2; }
QTabBar::tab:selected { background: #0B63CE; color: white; }
QFrame#card, QFrame#side {
    background: rgba(8, 31, 72, 232); border: 1px solid #3e93b6; border-radius: 16px;
}
QLabel { color: #edfaff; }
QLabel#title { color: white; font: bold 29px "Segoe UI"; letter-spacing: 1px; }
QLabel#subtitle, QLabel#hint { color: #b9e5d4; }
QLabel#section { color: #62e0b1; font-weight: 800; font-size: 11pt; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QTableWidget, QTextEdit {
    background: #0a244f; color: #f4fbff; border: 1px solid #408bb3; border-radius: 8px; padding: 8px;
    selection-background-color: #177d8b; selection-color: white;
}
QLineEdit:focus, QComboBox:focus, QListWidget:focus, QTableWidget:focus { border: 2px solid #55d69c; }
QComboBox::drop-down { border: 0; width: 28px; }
QComboBox QAbstractItemView { background: #0a244f; color: white; selection-background-color: #177d8b; }
QPushButton {
    background: #0f7583; color: white; border: 1px solid #42c9b0; border-radius: 8px; padding: 9px 15px; font-weight: 700;
}
QPushButton:hover { background: #159f8c; border-color: #8bf0c4; }
QPushButton:pressed { background: #0a5968; }
QPushButton#accent { background: #d82345; border-color: #ff7790; }
QPushButton#accent:hover { background: #ef3c59; }
QHeaderView::section { background: #126e88; color: white; border: 0; padding: 8px; font-weight: bold; }
QScrollArea { background: transparent; border: 0; }
QScrollBar:vertical { background: #08234b; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: #2f9b9c; min-height: 24px; border-radius: 6px; }
QTextEdit#status { background: #061936; border: 1px solid #2e8a93; color: #99f1cb; font-family: Consolas; font-size: 9pt; }
QMessageBox { background: #0a244f; } QMessageBox QLabel { color: white; }
"""


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = PDFToolSuite()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
