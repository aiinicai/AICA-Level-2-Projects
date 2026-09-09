"""
AI Auditor V8 - Modern Desktop GUI Theme & Stylesheet
Corporate Navy and Slate palette with clean typography and responsive layouts.
"""

NAVY_DARK = "#0F172A"
NAVY_PRIMARY = "#1E293B"
BLUE_ACCENT = "#2563EB"
BLUE_HOVER = "#1D4ED8"
TEXT_PRIMARY = "#0F172A"
TEXT_MUTED = "#64748B"
BG_LIGHT = "#F8FAFC"
CARD_BG = "#FFFFFF"
BORDER_COLOR = "#E2E8F0"

SUCCESS_GREEN = "#10B981"
WARNING_YELLOW = "#F59E0B"
DANGER_RED = "#EF4444"

APP_STYLESHEET = """
QMainWindow {
    background-color: #F8FAFC;
}

QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #1E293B;
}

/* Sidebar Navigation */
#SidebarWidget {
    background-color: #0F172A;
    border-right: 1px solid #1E293B;
    min-width: 220px;
    max-width: 220px;
}

#SidebarTitle {
    font-size: 17px;
    font-weight: bold;
    color: #FFFFFF;
    padding: 18px 12px 6px 12px;
}

#SidebarSubtitle {
    font-size: 11px;
    color: #94A3B8;
    padding: 0px 12px 14px 12px;
}

QPushButton.nav-btn {
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 6px;
    color: #CBD5E1;
    font-size: 13px;
    font-weight: 500;
    margin: 2px 8px;
    background-color: transparent;
}

QPushButton.nav-btn:hover {
    background-color: #1E293B;
    color: #FFFFFF;
}

QPushButton.nav-btn:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: bold;
}

/* Cards & Containers */
QFrame.card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px;
}

QFrame.card-highlight {
    background-color: #FFFFFF;
    border-left: 4px solid #2563EB;
    border-top: 1px solid #E2E8F0;
    border-right: 1px solid #E2E8F0;
    border-bottom: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px;
}

/* Headings */
QLabel.page-title {
    font-size: 20px;
    font-weight: bold;
    color: #0F172A;
    padding-bottom: 4px;
}

QLabel.page-subtitle {
    font-size: 12px;
    color: #64748B;
    padding-bottom: 12px;
}

QLabel.section-title {
    font-size: 15px;
    font-weight: bold;
    color: #1E293B;
    padding: 6px 0px;
}

/* Action Buttons */
QPushButton.primary-btn {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}

QPushButton.primary-btn:hover {
    background-color: #1D4ED8;
}

QPushButton.secondary-btn {
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 500;
}

QPushButton.secondary-btn:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
}

QPushButton.success-btn {
    background-color: #10B981;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}

QPushButton.success-btn:hover {
    background-color: #059669;
}

/* Tables */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    gridline-color: #F1F5F9;
    selection-background-color: #EFF6FF;
    selection-color: #1E293B;
    font-size: 12.5px;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    font-weight: bold;
    font-size: 12px;
    padding: 8px 6px;
    border: none;
    border-bottom: 2px solid #CBD5E1;
}

/* Form Controls */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 6px 10px;
    color: #0F172A;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #2563EB;
}

/* Progress Bar */
QProgressBar {
    background-color: #E2E8F0;
    border-radius: 6px;
    text-align: center;
    color: #0F172A;
    font-weight: 600;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 6px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #F1F5F9;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}
"""
