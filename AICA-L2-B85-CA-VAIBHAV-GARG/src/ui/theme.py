"""Modern corporate stylesheet and design system tokens for the desktop application."""

PRIMARY_NAVY = "#0A2540"
PRIMARY_BLUE = "#0066CC"
SECONDARY_BLUE = "#1E88E5"
BG_LIGHT = "#F8FAFC"
SURFACE_WHITE = "#FFFFFF"
BORDER_COLOR = "#E2E8F0"
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#475569"
TEXT_MUTED = "#94A3B8"
ACCENT_FLAG_BG = "#FEF2F2"
ACCENT_FLAG_TEXT = "#DC2626"
ACCENT_PASS_BG = "#F0FDF4"
ACCENT_PASS_TEXT = "#16A34A"

APP_STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
    color: #0F172A;
    background-color: #F8FAFC;
    font-size: 13px;
}

/* Main Window & Menus */
QMainWindow {
    background-color: #F8FAFC;
}

QMenuBar {
    background-color: #FFFFFF;
    color: #0F172A;
    border-bottom: 1px solid #E2E8F0;
    padding: 4px 8px;
    font-weight: 500;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #EFF6FF;
    color: #0066CC;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
    color: #0F172A;
}

QMenu::item:selected {
    background-color: #EFF6FF;
    color: #0066CC;
}

QMenu::separator {
    height: 1px;
    background-color: #E2E8F0;
    margin: 4px 6px;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    background-color: #FFFFFF;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #F1F5F9;
    color: #475569;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #E2E8F0;
    border-bottom: none;
    font-weight: 600;
    font-size: 13px;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #0066CC;
    border-top: 2px solid #0066CC;
    border-bottom: 1px solid #FFFFFF;
}

QTabBar::tab:hover:!selected {
    background-color: #E2E8F0;
    color: #0F172A;
}

/* Buttons */
QPushButton {
    background-color: #0066CC;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #0052A3;
}

QPushButton:pressed {
    background-color: #003D7A;
}

QPushButton:disabled {
    background-color: #CBD5E1;
    color: #94A3B8;
}

QPushButton.secondary {
    background-color: #FFFFFF;
    color: #475569;
    border: 1px solid #CBD5E1;
}

QPushButton.secondary:hover {
    background-color: #F8FAFC;
    color: #0F172A;
    border-color: #94A3B8;
}

QPushButton.danger {
    background-color: #EF4444;
    color: white;
}

QPushButton.danger:hover {
    background-color: #DC2626;
}

/* Tables */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    gridline-color: #F1F5F9;
    selection-background-color: #EFF6FF;
    selection-color: #0F172A;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #0A2540;
    color: #FFFFFF;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #1E3A5F;
    font-weight: 600;
    font-size: 12px;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #F1F5F9;
}

/* Inputs */
QLineEdit, QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px 12px;
    color: #0F172A;
    selection-background-color: #0066CC;
}

QLineEdit:focus, QTextEdit:focus {
    border: 2px solid #0066CC;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #F1F5F9;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
