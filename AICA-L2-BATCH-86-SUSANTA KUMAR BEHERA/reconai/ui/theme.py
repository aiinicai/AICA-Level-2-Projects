"""
Theme manager and QSS stylesheets for ReconAI desktop application.
Features a professional financial aesthetic (Slate/Navy base with corporate blue accents).
"""

DARK_THEME_QSS = """
/* ReconAI Dark Theme */
QMainWindow, QDialog, QWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: "Segoe UI", "Inter", -apple-system, sans-serif;
    font-size: 13px;
}

QTabBar::tab {
    background: #1E293B;
    color: #94A3B8;
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: #2563EB;
    color: #FFFFFF;
}

QTabBar::tab:hover:!selected {
    background: #334155;
    color: #F8FAFC;
}

QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 6px;
    background-color: #1E293B;
    top: -1px;
}

QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #93C5FD;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}

QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #334155;
    color: #64748B;
}

QPushButton#secondaryBtn {
    background-color: #334155;
    color: #F8FAFC;
    border: 1px solid #475569;
}

QPushButton#secondaryBtn:hover {
    background-color: #475569;
}

QPushButton#dangerBtn {
    background-color: #DC2626;
    color: #FFFFFF;
}

QPushButton#dangerBtn:hover {
    background-color: #B91C1C;
}

QPushButton#successBtn {
    background-color: #059669;
    color: #FFFFFF;
}

QPushButton#successBtn:hover {
    background-color: #047857;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 20px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #3B82F6;
    background-color: #0F172A;
}

QTableView {
    background-color: #1E293B;
    color: #F8FAFC;
    gridline-color: #334155;
    border: 1px solid #334155;
    border-radius: 6px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    font-family: "Segoe UI", "Consolas", sans-serif;
    font-size: 12px;
}

QTableView::item {
    padding: 6px;
}

QTableView::item:hover {
    background-color: #334155;
}

QHeaderView::section {
    background-color: #0F172A;
    color: #94A3B8;
    padding: 8px;
    border: none;
    border-right: 1px solid #334155;
    border-bottom: 2px solid #2563EB;
    font-weight: bold;
}

QScrollBar:vertical {
    background: #0F172A;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #475569;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #64748B;
}

QProgressBar {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #F8FAFC;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 5px;
}

QStatusBar {
    background-color: #0F172A;
    color: #94A3B8;
    border-top: 1px solid #334155;
}

QLabel#statValue {
    font-size: 22px;
    font-weight: bold;
    color: #60A5FA;
}

QLabel#statTitle {
    font-size: 11px;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
}

QFrame#cardFrame {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px;
}

QFrame#cardFrame:hover {
    border: 1px solid #3B82F6;
}
"""

LIGHT_THEME_QSS = """
/* ReconAI Light Theme */
QMainWindow, QDialog, QWidget {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: "Segoe UI", "Inter", -apple-system, sans-serif;
    font-size: 13px;
}

QTabBar::tab {
    background: #E2E8F0;
    color: #475569;
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: #2563EB;
    color: #FFFFFF;
}

QTabBar::tab:hover:!selected {
    background: #CBD5E1;
    color: #0F172A;
}

QTabWidget::pane {
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    background-color: #FFFFFF;
    top: -1px;
}

QGroupBox {
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #1E3A8A;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}

QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #E2E8F0;
    color: #94A3B8;
}

QPushButton#secondaryBtn {
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
}

QPushButton#secondaryBtn:hover {
    background-color: #F1F5F9;
}

QPushButton#dangerBtn {
    background-color: #DC2626;
    color: #FFFFFF;
}

QPushButton#dangerBtn:hover {
    background-color: #B91C1C;
}

QPushButton#successBtn {
    background-color: #059669;
    color: #FFFFFF;
}

QPushButton#successBtn:hover {
    background-color: #047857;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 20px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #2563EB;
    background-color: #FFFFFF;
}

QTableView {
    background-color: #FFFFFF;
    color: #0F172A;
    gridline-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    font-family: "Segoe UI", "Consolas", sans-serif;
    font-size: 12px;
}

QTableView::item {
    padding: 6px;
}

QTableView::item:hover {
    background-color: #F1F5F9;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    padding: 8px;
    border: none;
    border-right: 1px solid #CBD5E1;
    border-bottom: 2px solid #2563EB;
    font-weight: bold;
}

QScrollBar:vertical {
    background: #F8FAFC;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QProgressBar {
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    text-align: center;
    color: #0F172A;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 5px;
}

QStatusBar {
    background-color: #FFFFFF;
    color: #64748B;
    border-top: 1px solid #E2E8F0;
}

QLabel#statValue {
    font-size: 22px;
    font-weight: bold;
    color: #1E3A8A;
}

QLabel#statTitle {
    font-size: 11px;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
}

QFrame#cardFrame {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 12px;
}

QFrame#cardFrame:hover {
    border: 1px solid #2563EB;
}
"""


def apply_theme(app, theme_name: str = "dark"):
    """Applies either 'dark' or 'light' QSS theme to the QApplication."""
    if theme_name.lower() == "light":
        app.setStyleSheet(LIGHT_THEME_QSS)
    else:
        app.setStyleSheet(DARK_THEME_QSS)
