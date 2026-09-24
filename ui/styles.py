"""
Modern, professional stylesheets and themes for TDS & TCS Certificate PDF Auto-Renamer.
Features crisp typography, subtle elevation, and distinct compliance badges.
"""

APP_STYLESHEET = """
/* Global Window Styling */
QMainWindow {
    background-color: #F8FAFC;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    color: #1E293B;
}

QWidget {
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    color: #1E293B;
}

/* Toolbars */
QToolBar {
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    padding: 6px 12px;
    spacing: 8px;
}

/* Header & Banner */
#HeaderCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #0284C7);
    border-radius: 8px;
    padding: 16px 20px;
    color: #FFFFFF;
}

#HeaderTitle {
    color: #FFFFFF;
    font-size: 20px;
    font-weight: 700;
}

#HeaderSubtitle {
    color: #E0F2FE;
    font-size: 12px;
}

/* Stat Metric Cards */
.MetricCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 10px 14px;
}

.MetricCard:hover {
    border-color: #CBD5E1;
}

.MetricValue {
    font-size: 22px;
    font-weight: 700;
    color: #0F172A;
}

.MetricLabel {
    font-size: 11px;
    color: #64748B;
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* Push Buttons */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    color: #334155;
}

QPushButton:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
}

QPushButton:pressed {
    background-color: #E2E8F0;
}

QPushButton:disabled {
    background-color: #F8FAFC;
    color: #94A3B8;
    border-color: #E2E8F0;
}

/* Primary Action Button */
QPushButton#PrimaryBtn {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    font-weight: 600;
}

QPushButton#PrimaryBtn:hover {
    background-color: #1D4ED8;
}

QPushButton#PrimaryBtn:pressed {
    background-color: #1E40AF;
}

/* Success Action Button */
QPushButton#SuccessBtn {
    background-color: #059669;
    color: #FFFFFF;
    border: 1px solid #047857;
    font-weight: 600;
}

QPushButton#SuccessBtn:hover {
    background-color: #047857;
}

QPushButton#SuccessBtn:pressed {
    background-color: #065F46;
}

/* Danger / Undo Button */
QPushButton#WarningBtn {
    background-color: #D97706;
    color: #FFFFFF;
    border: 1px solid #B45309;
    font-weight: 600;
}

QPushButton#WarningBtn:hover {
    background-color: #B45309;
}

/* Inputs & ComboBoxes */
QLineEdit, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2563EB;
    outline: none;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Table View */
QTableView {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    gridline-color: #F1F5F9;
    selection-background-color: #EFF6FF;
    selection-color: #1E293B;
}

QTableView::item {
    padding: 6px 10px;
}

QTableView::item:selected {
    background-color: #E0E7FF;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #E2E8F0;
    border-right: 1px solid #F1F5F9;
    font-weight: 600;
    font-size: 12px;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #E2E8F0;
    border-radius: 5px;
    text-align: center;
    background-color: #F1F5F9;
    height: 14px;
    font-size: 10px;
}

QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 4px;
}

/* Log Box / TextEdit */
QPlainTextEdit#LogView {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px;
}

/* Status Bar */
QStatusBar {
    background: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    color: #64748B;
    font-size: 12px;
}

QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    margin-top: 18px;
    font-weight: 600;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #334155;
}
"""

# Color badge constants for Table View Delegate
STATUS_COLORS = {
    "Pending": ("#F1F5F9", "#475569"),
    "Analyzing": ("#FEF3C7", "#D97706"),
    "Extracted": ("#DBEAFE", "#1D4ED8"),
    "Preview Ready": ("#E0E7FF", "#4338CA"),
    "Renamed": ("#DCFCE7", "#15803D"),
    "Copied": ("#D1FAE5", "#047857"),
    "Moved": ("#CCFBF1", "#0F766E"),
    "Skipped": ("#FEF3C7", "#B45309"),
    "Error": ("#FEE2E2", "#B91C1C"),
    "Undone": ("#F3E8FF", "#7E22CE"),
}

ACT_COLORS = {
    "Income-tax Act, 1961": ("#EFF6FF", "#1D4ED8"),  # Blue tone
    "Income-tax Act, 2025": ("#FDF4FF", "#A21CAF"),  # Purple/Magenta tone
    "Unknown Act": ("#F1F5F9", "#64748B"),
}
