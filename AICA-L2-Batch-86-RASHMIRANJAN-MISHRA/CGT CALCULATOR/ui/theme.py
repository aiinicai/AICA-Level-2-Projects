"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
UI Theme & Professional Stylesheet (PyQt6)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

PRIMARY_COLOR = "#1E40AF"     # Royal Blue
DARK_BLUE = "#1E3A8A"         # Deep Navy
ACCENT_BLUE = "#3B82F6"       # Vivid Blue
BG_MAIN = "#F8FAFC"           # Slate Light
BG_CARD = "#FFFFFF"           # Clean White
TEXT_MAIN = "#0F172A"         # Slate Dark
TEXT_MUTED = "#64748B"        # Slate Muted
BORDER_COLOR = "#E2E8F0"      # Light Border
SUCCESS_COLOR = "#059669"     # Emerald Green
SUCCESS_BG = "#ECFDF5"        # Soft Mint
WARNING_COLOR = "#D97706"     # Amber
WARNING_BG = "#FFFBEB"        # Soft Amber
DANGER_COLOR = "#DC2626"      # Ruby Red
DANGER_BG = "#FEF2F2"         # Soft Red

APP_STYLESHEET = """
QMainWindow, QWidget#centralWidget {
    background-color: #F1F5F9;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
    color: #0F172A;
}

/* Sidebar Navigation */
QFrame#sidebar {
    background-color: #1E3A8A;
    border-right: 1px solid #1E293B;
}

QLabel#sidebarTitle {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 12px 8px 4px 8px;
}

QLabel#sidebarSubtitle {
    color: #93C5FD;
    font-size: 11px;
    padding: 0px 8px 12px 8px;
}

QPushButton.sidebarBtn {
    background-color: transparent;
    color: #E2E8F0;
    text-align: left;
    padding: 10px 14px;
    font-size: 12.5px;
    font-weight: 500;
    border: none;
    border-radius: 6px;
    margin: 2px 8px;
}

QPushButton.sidebarBtn:hover {
    background-color: #1E40AF;
    color: #FFFFFF;
}

QPushButton.sidebarBtn:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: bold;
}

/* Cards & Content Containers */
QFrame.contentCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px;
}

QFrame.highlightCard {
    background-color: #ECFDF5;
    border: 2px solid #059669;
    border-radius: 8px;
    padding: 14px;
}

QLabel.cardHeading {
    color: #1E3A8A;
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 6px;
}

/* Form Controls */
QLabel {
    color: #1E293B;
    font-size: 12px;
}

QLabel.fieldLabel {
    color: #334155;
    font-size: 11.5px;
    font-weight: 600;
}

QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 12px;
    color: #0F172A;
    min-height: 20px;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1.5px solid #2563EB;
    background-color: #F8FAFC;
}

QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #CBD5E1;
}

/* Buttons */
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-radius: 5px;
    padding: 7px 16px;
    min-height: 22px;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton.secondaryBtn {
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
}

QPushButton.secondaryBtn:hover {
    background-color: #F8FAFC;
    border-color: #94A3B8;
}

QPushButton.successBtn {
    background-color: #059669;
    color: #FFFFFF;
}

QPushButton.successBtn:hover {
    background-color: #047857;
}

QPushButton.dangerBtn {
    background-color: #DC2626;
    color: #FFFFFF;
}

QPushButton.dangerBtn:hover {
    background-color: #B91C1C;
}

QPushButton.accentBtn {
    background-color: #D97706;
    color: #FFFFFF;
}

/* Tables */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    gridline-color: #F1F5F9;
    font-size: 11.5px;
    color: #0F172A;
    selection-background-color: #EFF6FF;
    selection-color: #1E40AF;
}

QHeaderView::section {
    background-color: #1E3A8A;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 11.5px;
    border: 1px solid #1E293B;
    padding: 6px 8px;
}

QTableWidget::item {
    padding: 5px 8px;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #F1F5F9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

/* TabWidget */
QTabWidget::pane {
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background-color: #E2E8F0;
    color: #475569;
    border: 1px solid #CBD5E1;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #1E3A8A;
    border-bottom: 2px solid #2563EB;
}

QCheckBox {
    font-size: 11.5px;
    color: #1E293B;
    spacing: 6px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1.5px solid #CBD5E1;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #2563EB;
}
"""
