# Modern Professional Stylesheet for Smart Billing Manager
# Palette: Deep Navy (#1A365D), Soft Red Accent (#B91C1C), Clean Slate White/Gray

MAIN_STYLESHEET = """
QMainWindow {
    background-color: #F1F5F9;
}

/* Labels and General Text */
QLabel {
    font-family: "Segoe UI", Arial, sans-serif;
    color: #334155;
    font-size: 13px;
}

QLabel#titleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #1A365D;
}

QLabel#subTotalLabel, QLabel#taxLabel, QLabel#grandTotalLabel, QLabel#roundOffLabel {
    font-weight: bold;
    font-size: 14px;
}

QLabel#grandTotalValue {
    font-size: 18px;
    font-weight: bold;
    color: #1A365D;
}

/* GroupBoxes / Sections */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    font-size: 13px;
    color: #1A365D;
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    background-color: #FFFFFF;
}

/* Input Fields (LineEdit, ComboBox, DateEdit, DoubleSpinBox) */
QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QTextEdit {
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 6px 10px;
    background-color: #FFFFFF;
    color: #1E293B;
    font-size: 13px;
    selection-background-color: #1A365D;
    selection-color: #FFFFFF;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QTextEdit:focus {
    border: 1.5px solid #1A365D;
    background-color: #F8FAFC;
}


/* Buttons */
QPushButton {
    font-family: "Segoe UI", Arial, sans-serif;
    font-weight: 600;
    font-size: 13px;
    padding: 8px 16px;
    border-radius: 5px;
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
    color: #334155;
}

QPushButton:hover {
    background-color: #F8FAFC;
    border-color: #94A3B8;
}

QPushButton:pressed {
    background-color: #E2E8F0;
}

/* Primary / Action Buttons (Save, Export) */
QPushButton#btnPrimary, QPushButton[primary="true"] {
    background-color: #1A365D;
    color: #FFFFFF;
    border: 1px solid #1A365D;
}

QPushButton#btnPrimary:hover, QPushButton[primary="true"]:hover {
    background-color: #2A4D7C;
    border-color: #2A4D7C;
}

QPushButton#btnPrimary:pressed, QPushButton[primary="true"]:pressed {
    background-color: #0F233F;
}

/* Danger / Delete Buttons */
QPushButton#btnDanger, QPushButton[danger="true"] {
    background-color: #FFFFFF;
    color: #B91C1C;
    border: 1px solid #FCA5A5;
}

QPushButton#btnDanger:hover, QPushButton[danger="true"]:hover {
    background-color: #FEF2F2;
    border-color: #B91C1C;
}

QPushButton#btnDanger:pressed, QPushButton[danger="true"]:pressed {
    background-color: #FEE2E2;
}

/* Success Buttons */
QPushButton#btnSuccess, QPushButton[success="true"] {
    background-color: #10B981;
    color: #FFFFFF;
    border: 1px solid #10B981;
}

QPushButton#btnSuccess:hover, QPushButton[success="true"]:hover {
    background-color: #059669;
    border-color: #059669;
}

QPushButton#btnSuccess:pressed, QPushButton[success="true"]:pressed {
    background-color: #047857;
}

/* Table Widget styling */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    gridline-color: #E2E8F0;
    border-radius: 6px;
    font-size: 13px;
    color: #334155;
}

QTableWidget::item {
    padding: 5px;
}

QTableWidget::item:selected {
    background-color: #E2E8F0;
    color: #1E293B;
}

QHeaderView::section {
    background-color: #1A365D;
    color: #FFFFFF;
    font-weight: bold;
    padding: 6px;
    border: 1px solid #E2E8F0;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #F1F5F9;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #CBD5E1;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94A3B8;
}

/* List View (for recent invoices) */
QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 5px;
}

QListWidget::item {
    border-bottom: 1px solid #F1F5F9;
    padding: 8px 10px;
    border-radius: 4px;
}

QListWidget::item:hover {
    background-color: #F8FAFC;
}

QListWidget::item:selected {
    background-color: #1A365D;
    color: #FFFFFF;
}

/* Tooltips */
QToolTip {
    background-color: #1E293B;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 5px;
}
"""
