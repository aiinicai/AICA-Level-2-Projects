"""
LexSecure India Pro - Design System & Dynamic Dual-Theme QSS Engine
Supports both Dark Professional Slate/Navy Mode and Light Executive Enterprise Mode
"""

DARK_THEME = {
    "bg_dark": "#0B1120",
    "bg_main": "#0F172A",
    "bg_card": "#1E293B",
    "bg_card_hover": "#26354A",
    "border": "#334155",
    "border_light": "#475569",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    
    # Accents
    "teal_primary": "#0D9488",
    "teal_hover": "#14B8A6",
    "emerald": "#10B981",
    "cyan": "#06B6D4",
    "blue": "#3B82F6",
    
    # Statutory Risk Tiers
    "risk_high": "#EF4444",
    "risk_caution": "#F59E0B",
    "risk_compliant": "#10B981"
}

LIGHT_THEME = {
    "bg_dark": "#F1F5F9",
    "bg_main": "#F8FAFC",
    "bg_card": "#FFFFFF",
    "bg_card_hover": "#F8FAFC",
    "border": "#CBD5E1",
    "border_light": "#E2E8F0",
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#64748B",
    
    # Accents
    "teal_primary": "#0D9488",
    "teal_hover": "#14B8A6",
    "emerald": "#059669",
    "cyan": "#0284C7",
    "blue": "#2563EB",
    
    # Statutory Risk Tiers
    "risk_high": "#DC2626",
    "risk_caution": "#D97706",
    "risk_compliant": "#059669"
}

THEME_COLORS = DARK_THEME

def get_theme_qss(mode: str = "dark") -> str:
    if mode == "light":
        return """
QMainWindow, QWidget {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
    font-size: 13px;
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
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #0D9488;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #F1F5F9;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #CBD5E1;
    min-width: 25px;
    border-radius: 4px;
}

/* Sidebar Navigation */
QFrame#sidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #CBD5E1;
}

QPushButton.nav-btn {
    text-align: left;
    padding: 10px 14px;
    font-size: 12.5px;
    font-weight: 600;
    color: #475569;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    margin: 2px 8px;
}
QPushButton.nav-btn:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}
QPushButton.nav-btn:checked {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0D9488, stop:1 #10B981);
    color: #FFFFFF;
    font-weight: bold;
}

/* Header Top Bar */
QFrame#topbar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #CBD5E1;
    padding: 6px 16px;
}

/* Cards & Panels */
QFrame.card {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    padding: 16px;
}
QFrame.card:hover {
    border: 1px solid #94A3B8;
}

/* Buttons */
QPushButton.btn-primary {
    background-color: #0D9488;
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-primary:hover {
    background-color: #14B8A6;
}

QPushButton.btn-emerald {
    background-color: #059669;
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-emerald:hover {
    background-color: #10B981;
}

QPushButton.btn-danger {
    background-color: #DC2626;
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-danger:hover {
    background-color: #EF4444;
}

QPushButton.btn-outline {
    background-color: transparent;
    color: #0284C7;
    border: 1px solid #0284C7;
    font-weight: 600;
    padding: 7px 14px;
    border-radius: 6px;
}
QPushButton.btn-outline:hover {
    background-color: rgba(2, 132, 199, 0.08);
    color: #0369A1;
}

/* Form Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #0D9488;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #0D9488;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    selection-background-color: #0D9488;
    selection-color: #FFFFFF;
}

/* Tables */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    gridline-color: #E2E8F0;
    color: #0F172A;
    selection-background-color: rgba(13, 148, 136, 0.15);
    selection-color: #0F172A;
}
QHeaderView::section {
    background-color: #F1F5F9;
    color: #0284C7;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #CBD5E1;
    font-weight: bold;
    font-size: 12px;
}

QTabWidget::pane {
    border: 1px solid #CBD5E1;
    background: #FFFFFF;
    border-radius: 8px;
}
QTabBar::tab {
    background: #F1F5F9;
    color: #475569;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #0D9488;
    border-bottom: 2px solid #0D9488;
}
"""
    else:
        # Dark Mode
        return """
QMainWindow, QWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
    font-size: 13px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0B1120;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #334155;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #0D9488;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #0B1120;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #334155;
    min-width: 25px;
    border-radius: 4px;
}

/* Sidebar Navigation */
QFrame#sidebar {
    background-color: #0B1120;
    border-right: 1px solid #1E293B;
}

QPushButton.nav-btn {
    text-align: left;
    padding: 10px 14px;
    font-size: 12.5px;
    font-weight: 600;
    color: #94A3B8;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    margin: 2px 8px;
}
QPushButton.nav-btn:hover {
    background-color: #1E293B;
    color: #F8FAFC;
}
QPushButton.nav-btn:checked {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0D9488, stop:1 #10B981);
    color: #FFFFFF;
    font-weight: bold;
}

/* Header Top Bar */
QFrame#topbar {
    background-color: #0B1120;
    border-bottom: 1px solid #1E293B;
    padding: 6px 16px;
}

/* Cards & Panels */
QFrame.card {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px;
}
QFrame.card:hover {
    border: 1px solid #475569;
}

/* Buttons */
QPushButton.btn-primary {
    background-color: #0D9488;
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-primary:hover {
    background-color: #14B8A6;
}

QPushButton.btn-emerald {
    background-color: #10B981;
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-emerald:hover {
    background-color: #34D399;
}

QPushButton.btn-danger {
    background-color: #EF4444;
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-danger:hover {
    background-color: #F87171;
}

QPushButton.btn-outline {
    background-color: transparent;
    color: #38BDF8;
    border: 1px solid #0284C7;
    font-weight: 600;
    padding: 7px 14px;
    border-radius: 6px;
}
QPushButton.btn-outline:hover {
    background-color: rgba(2, 132, 199, 0.15);
    color: #7DD3FC;
    border: 1px solid #38BDF8;
}

/* Form Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background-color: #0B1120;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #0D9488;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #0D9488;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    selection-background-color: #0D9488;
}

/* Tables */
QTableWidget {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #334155;
    color: #F8FAFC;
    selection-background-color: rgba(13, 148, 136, 0.35);
}
QHeaderView::section {
    background-color: #0B1120;
    color: #38BDF8;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #334155;
    font-weight: bold;
    font-size: 12px;
}

QTabWidget::pane {
    border: 1px solid #334155;
    background: #1E293B;
    border-radius: 8px;
}
QTabBar::tab {
    background: #0B1120;
    color: #94A3B8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background: #1E293B;
    color: #10B981;
    border-bottom: 2px solid #10B981;
}
"""

MAIN_QSS = get_theme_qss("dark")
