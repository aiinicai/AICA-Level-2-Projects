"""Finstock EventScope ultra-premium TradingView-inspired theme engine.
Provides high-contrast two-way visibility:
  - Dark Navy (Deep Navy #060D1A, Elevated Navy Cards #0D1C33, Pure White #FFFFFF)
  - Clean Light (Crisp Slate #F1F5F9, Pure White Cards #FFFFFF, Deep Navy #0A192F)
"""

DARK_STYLE = """
* { 
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; 
    font-size: 12px; 
    outline: none;
}

QMainWindow, QDialog, QWidget#root { 
    background: #060D1A; 
    color: #FFFFFF; 
}

QWidget { 
    color: #E2E8F0; 
}

QLabel { 
    background: transparent; 
}

QLabel#brand { 
    font-size: 20px; 
    font-weight: 800; 
    letter-spacing: 2px; 
    color: #FFFFFF;
}

QLabel#brandSub { 
    color: #38BDF8; 
    font-size: 9px; 
    font-weight: 700; 
    letter-spacing: 2.5px; 
}

QLabel#pageTitle { 
    font-size: 24px; 
    font-weight: 700; 
    color: #FFFFFF;
}

QLabel#subtitle { 
    color: #94A3B8; 
    font-size: 12px; 
}

QLabel#eyebrow { 
    color: #60A5FA; 
    font-size: 10px; 
    font-weight: 700; 
    letter-spacing: 1.5px; 
}

QLabel#sampleBanner { 
    color: #FBBF24; 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E293B, stop:1 #0F172A); 
    border: 1px solid #334155; 
    padding: 8px 14px; 
    border-radius: 6px; 
    font-weight: 500;
}

QLabel#liveBanner { 
    color: #34D399; 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #064E3B, stop:1 #022C22); 
    border: 1px solid #059669; 
    padding: 7px 14px; 
    border-radius: 6px; 
    font-weight: 600;
    font-size: 11px;
}

QLabel#metricValue { 
    font-size: 26px; 
    font-weight: 800; 
    color: #FFFFFF;
}

QLabel#metricLabel { 
    color: #94A3B8; 
    font-size: 11px; 
    font-weight: 600; 
    letter-spacing: 0.5px;
}

QFrame#sidebar { 
    background: #081224; 
    border-right: 1px solid #14243C; 
}

QFrame#card { 
    background: #0D1C33; 
    border: 1px solid #1E3A63; 
    border-radius: 8px; 
}

QFrame#card:hover {
    border: 1px solid #2563EB;
}

QListWidget { 
    background: #081426; 
    border: 1px solid #142845; 
    border-radius: 6px; 
    color: #FFFFFF; 
    outline: 0;
}

QListWidget::item { 
    padding: 10px 14px; 
    border-radius: 6px; 
    margin: 2px 6px; 
    color: #E2E8F0; 
    font-weight: 500;
    border-bottom: 1px solid #0D1C33;
}

QListWidget::item:selected { 
    background: #1E40AF; 
    color: #FFFFFF; 
    font-weight: 700;
}

QListWidget::item:hover:!selected { 
    background: #0F223D; 
    color: #38BDF8;
}

QListWidget#navigation { 
    background: transparent; 
    border: 0; 
    outline: 0; 
    font-size: 12px; 
}

QListWidget#navigation::item { 
    padding: 11px 14px; 
    border-radius: 6px; 
    margin: 2px 10px; 
    color: #94A3B8; 
    font-weight: 500;
}

QListWidget#navigation::item:selected { 
    background: #122847; 
    color: #FFFFFF; 
    border-left: 3px solid #3B82F6; 
    font-weight: 600;
}

QListWidget#navigation::item:hover:!selected { 
    background: #0F1E36; 
    color: #E2E8F0;
}

QLineEdit, QComboBox, QDateEdit, QSpinBox, QPlainTextEdit { 
    background: #0A172B; 
    border: 1px solid #1C3355; 
    border-radius: 6px; 
    padding: 6px 10px; 
    color: #FFFFFF; 
    selection-background-color: #2563EB; 
    selection-color: #FFFFFF;
    min-height: 20px; 
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus { 
    border: 1px solid #3B82F6; 
    background: #0D1C34;
}

QComboBox::drop-down { 
    border: 0; 
    width: 24px; 
}

QComboBox QAbstractItemView { 
    background: #0D1C33; 
    border: 1px solid #1E3A63;
    border-radius: 6px;
    selection-background-color: #1E40AF; 
    selection-color: #FFFFFF;
    color: #FFFFFF; 
    padding: 4px;
}

QPushButton { 
    background: #0F223D; 
    border: 1px solid #1E3A63; 
    padding: 7px 14px; 
    border-radius: 6px; 
    color: #FFFFFF; 
    font-weight: 500;
}

QPushButton:hover { 
    background: #183359; 
    border-color: #2563EB; 
}

QPushButton:pressed { 
    background: #0C1B30; 
}

QPushButton:disabled { 
    color: #64748B; 
    background: #081426; 
    border-color: #112035;
}

QPushButton#primary { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563EB, stop:1 #1D4ED8); 
    border: 1px solid #3B82F6; 
    color: #FFFFFF; 
    font-weight: 600; 
}

QPushButton#primary:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3B82F6, stop:1 #2563EB); 
    border-color: #60A5FA;
}

QPushButton#themeToggle {
    background: #0F223D;
    border: 1px solid #2563EB;
    color: #38BDF8;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 6px;
}

QPushButton#themeToggle:hover {
    background: #1A365D;
    color: #FFFFFF;
    border-color: #38BDF8;
}

QPushButton#viewPill {
    background: #0B182E;
    border: 1px solid #162B4A;
    border-radius: 6px;
    padding: 6px 14px;
    color: #94A3B8;
    font-weight: 600;
}

QPushButton#viewPill:checked {
    background: #2563EB;
    border: 1px solid #3B82F6;
    color: #FFFFFF;
}

QPushButton#viewPill:hover:!checked {
    background: #132746;
    color: #FFFFFF;
}

QPushButton#quiet { 
    background: transparent; 
    border: 0; 
    color: #94A3B8; 
}

QPushButton#quiet:hover { 
    color: #FFFFFF; 
}

QTableView, QTableWidget { 
    background: #071120; 
    alternate-background-color: #0A172B; 
    gridline-color: #13243B; 
    border: 1px solid #152945; 
    border-radius: 6px; 
    selection-background-color: #173661; 
    selection-color: #FFFFFF; 
    color: #FFFFFF;
    outline: 0; 
}

QTableView::item { 
    padding: 8px 10px; 
    border-bottom: 1px solid #102137; 
    color: #FFFFFF;
}

QTableView::item:selected {
    background-color: #1E40AF;
    color: #FFFFFF;
}

QHeaderView::section { 
    background: #0C1A30; 
    color: #94A3B8; 
    border: 0; 
    border-bottom: 1px solid #1C3355; 
    padding: 9px 10px; 
    font-size: 11px; 
    font-weight: 700; 
    letter-spacing: 0.5px;
}

QTextBrowser { 
    background: #091424; 
    border: 1px solid #152945; 
    border-radius: 6px; 
    padding: 14px; 
    color: #F1F5F9;
}

QTabWidget::pane { 
    border: 1px solid #172D4D; 
    background: #081222; 
    border-radius: 0 0 6px 6px;
}

QTabBar::tab { 
    background: #091526; 
    color: #94A3B8; 
    padding: 7px 12px; 
    border-bottom: 2px solid transparent; 
    font-weight: 600;
    font-size: 11px;
}

QTabBar::tab:selected { 
    color: #FFFFFF; 
    background: #0F223D; 
    border-bottom: 2px solid #3B82F6; 
    font-weight: 700;
}

QTabBar::tab:hover:!selected {
    color: #E2E8F0;
    background: #0C1A30;
}

QTabBar::scroller {
    width: 44px;
    background: #091526;
}

QTabBar QToolButton {
    background: #0F1E36;
    border: 1px solid #1E3A8A;
    border-radius: 4px;
    color: #38BDF8;
    margin: 1px;
    padding: 1px;
    min-width: 18px;
    min-height: 18px;
    font-weight: 800;
}

QTabBar QToolButton:hover {
    background: #1E3A8A;
    border: 1px solid #3B82F6;
    color: #FFFFFF;
}

QSplitter::handle { 
    background: #14243C; 
}

QScrollBar:vertical { 
    background: #060D1A; 
    width: 8px; 
    margin: 0; 
}

QScrollBar::handle:vertical { 
    background: #1E3A63; 
    min-height: 25px; 
    border-radius: 4px; 
}

QScrollBar::handle:vertical:hover { 
    background: #2563EB; 
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { 
    height: 0; 
}

QScrollBar:horizontal { 
    background: #060D1A; 
    height: 8px; 
}

QScrollBar::handle:horizontal { 
    background: #1E3A63; 
    min-width: 25px; 
    border-radius: 4px; 
}

QScrollBar::handle:horizontal:hover { 
    background: #2563EB; 
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { 
    width: 0; 
}

QStatusBar { 
    background: #07101F; 
    color: #94A3B8; 
    border-top: 1px solid #14243C; 
    font-size: 11px;
}

QCheckBox { 
    spacing: 8px; 
    color: #E2E8F0;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #1E3A63;
    background: #0A172B;
}

QCheckBox::indicator:checked {
    background: #2563EB;
    border-color: #3B82F6;
}

QGroupBox { 
    border: 1px solid #1B3252; 
    border-radius: 6px; 
    margin-top: 18px; 
    padding-top: 15px; 
}

QGroupBox::title { 
    subcontrol-origin: margin; 
    padding: 0 6px; 
    color: #94A3B8; 
    font-weight: 600;
}

QToolTip { 
    color: #FFFFFF; 
    background: #0F223D; 
    border: 1px solid #2563EB; 
    padding: 6px 10px; 
    border-radius: 4px;
}

QMenu { 
    background: #0D1C33; 
    border: 1px solid #1E3A63; 
    border-radius: 6px; 
    padding: 4px;
}

QMenu::item { 
    padding: 7px 20px; 
    color: #E2E8F0;
    border-radius: 4px;
}

QMenu::item:selected { 
    background: #1E40AF; 
    color: #FFFFFF;
}

/* TradingView-Style Right Tool Dock */
QFrame#rightDock {
    background: #081224;
    border-left: 1px solid #14243C;
    max-width: 48px;
    min-width: 48px;
}

QPushButton#dockBtn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 4px;
    margin: 4px;
    color: #94A3B8;
    font-size: 16px;
}

QPushButton#dockBtn:hover {
    background: #0F223D;
    color: #38BDF8;
}

QPushButton#dockBtn:checked {
    background: #1E3A8A;
    color: #FFFFFF;
    border-left: 3px solid #38BDF8;
}

/* Slide-out Drawer Panel */
QFrame#rightDrawer {
    background: #0A1528;
    border-left: 1px solid #172D4D;
}

/* Live Signal Beacon & Header Widgets */
QLabel#beaconLive {
    color: #10B981;
    font-weight: 700;
    font-size: 11px;
    background: #064E3B;
    border: 1px solid #059669;
    border-radius: 12px;
    padding: 4px 12px;
}

QLabel#beaconOffline {
    color: #EF4444;
    font-weight: 700;
    font-size: 11px;
    background: #450A0A;
    border: 1px solid #991B1B;
    border-radius: 12px;
    padding: 4px 12px;
}

QLabel#realtimeClock {
    color: #38BDF8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-weight: 700;
    font-size: 12px;
    background: #08162B;
    border: 1px solid #152E52;
    border-radius: 6px;
    padding: 4px 10px;
}

QLabel#syncCountdown {
    color: #94A3B8;
    font-size: 11px;
    font-weight: 600;
    background: #08162B;
    border: 1px solid #142845;
    border-radius: 6px;
    padding: 4px 8px;
}

/* ======================================================== */
/* QCalendarWidget (Popup Date Picker from QDateEdit)      */
/* ======================================================== */
QCalendarWidget {
    background-color: #0A172B;
    border: 1px solid #1E3A63;
    border-radius: 8px;
}

QCalendarWidget QWidget#qt_datetimedit_calendar {
    background-color: #0A172B;
}

QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #0D1C33;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    border-bottom: 1px solid #1E3A63;
    min-height: 38px;
    max-height: 38px;
}

QCalendarWidget QToolButton {
    color: #FFFFFF;
    background-color: #122847;
    border: 1px solid #1E3A63;
    border-radius: 4px;
    margin: 3px 4px;
    padding: 4px 10px;
    font-weight: 700;
    font-size: 12px;
}

QCalendarWidget QToolButton:hover {
    background-color: #1E3A8A;
    border-color: #38BDF8;
    color: #38BDF8;
}

QCalendarWidget QMenu {
    background-color: #0D1C33;
    color: #FFFFFF;
    border: 1px solid #1E3A63;
    border-radius: 6px;
    padding: 4px;
}

QCalendarWidget QSpinBox {
    background-color: #0D1C33;
    color: #FFFFFF;
    border: 1px solid #1E3A63;
    border-radius: 4px;
    padding: 2px 6px;
    font-weight: 700;
}

QCalendarWidget QTableView {
    background-color: #0A172B;
    alternate-background-color: #0A172B;
    color: #FFFFFF;
    border: none;
    outline: none;
    font-size: 12px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QCalendarWidget QHeaderView::section {
    background-color: #0D1C33;
    color: #38BDF8;
    font-weight: 700;
    font-size: 10px;
    border: none;
    border-bottom: 1px solid #1E3A63;
    padding: 3px 0px;
}

QCalendarWidget QAbstractItemView:enabled {
    color: #FFFFFF;
    background-color: #0A172B;
    font-weight: 700;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #475569;
    background-color: #0A172B;
    font-weight: 500;
}

QCalendarWidget QAbstractItemView:hover {
    background-color: #172E50;
    color: #38BDF8;
}

/* ======================================================== */
/* QCompleter & Timezone Searchable Dropdown Popup          */
/* ======================================================== */
QCompleter QAbstractItemView, QListView#completerPopup, QAbstractItemView#completerPopup {
    background-color: #0A172B !important;
    color: #FFFFFF !important;
    border: 1px solid #1E3A63;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #1E40AF !important;
    selection-color: #FFFFFF !important;
    outline: none;
}

QComboBox QLineEdit, QComboBox:editable, QLineEdit#zoneInput {
    background-color: #0A172B !important;
    color: #FFFFFF !important;
    border: 1px solid #1C3355;
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QComboBox QLineEdit:focus, QLineEdit#zoneInput:focus {
    border: 1px solid #38BDF8;
    background-color: #0D1C34 !important;
    color: #FFFFFF !important;
}
"""

LIGHT_STYLE = """
* { 
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; 
    font-size: 12px; 
    outline: none;
}

QMainWindow, QDialog, QWidget#root { 
    background: #F1F5F9; 
    color: #0A192F; 
}

QWidget { 
    color: #0A192F; 
}

QLabel { 
    background: transparent; 
}

QLabel#brand { 
    font-size: 20px; 
    font-weight: 800; 
    letter-spacing: 2px; 
    color: #0A192F;
}

QLabel#brandSub { 
    color: #0284C7; 
    font-size: 9px; 
    font-weight: 700; 
    letter-spacing: 2.5px; 
}

QLabel#pageTitle { 
    font-size: 24px; 
    font-weight: 700; 
    color: #0A192F;
}

QLabel#subtitle { 
    color: #475569; 
    font-size: 12px; 
}

QLabel#eyebrow { 
    color: #1D4ED8; 
    font-size: 10px; 
    font-weight: 700; 
    letter-spacing: 1.5px; 
}

QLabel#sampleBanner { 
    color: #B45309; 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FEF3C7, stop:1 #FFFBEB); 
    border: 1px solid #FCD34D; 
    padding: 8px 14px; 
    border-radius: 6px; 
    font-weight: 600;
}

QLabel#liveBanner { 
    color: #065F46; 
    background: #D1FAE5; 
    border: 1px solid #6EE7B7; 
    padding: 7px 14px; 
    border-radius: 6px; 
    font-weight: 600;
    font-size: 11px;
}

QLabel#metricValue { 
    font-size: 26px; 
    font-weight: 800; 
    color: #0A192F;
}

QLabel#metricLabel { 
    color: #475569; 
    font-size: 11px; 
    font-weight: 700; 
    letter-spacing: 0.5px;
}

QFrame#sidebar { 
    background: #FFFFFF; 
    border-right: 1px solid #CBD5E1; 
}

QFrame#card { 
    background: #FFFFFF; 
    border: 1px solid #CBD5E1; 
    border-radius: 8px; 
}

QFrame#card:hover {
    border: 1px solid #2563EB;
}

QListWidget { 
    background: #FFFFFF; 
    border: 1px solid #CBD5E1; 
    border-radius: 6px; 
    color: #0A192F; 
    outline: 0;
}

QListWidget::item { 
    padding: 10px 14px; 
    border-radius: 6px; 
    margin: 2px 6px; 
    color: #334155; 
    font-weight: 500;
    border-bottom: 1px solid #F1F5F9;
}

QListWidget::item:selected { 
    background: #DBEAFE; 
    color: #1E40AF; 
    font-weight: 700;
}

QListWidget::item:hover:!selected { 
    background: #EFF6FF; 
    color: #1D4ED8;
}

QListWidget#navigation { 
    background: transparent; 
    border: 0; 
    outline: 0; 
    font-size: 12px; 
}

QListWidget#navigation::item { 
    padding: 11px 14px; 
    border-radius: 6px; 
    margin: 2px 10px; 
    color: #475569; 
    font-weight: 600;
}

QListWidget#navigation::item:selected { 
    background: #EFF6FF; 
    color: #1D4ED8; 
    border-left: 3px solid #1D4ED8; 
    font-weight: 700;
}

QListWidget#navigation::item:hover:!selected { 
    background: #F1F5F9; 
    color: #0A192F;
}

QLineEdit, QComboBox, QDateEdit, QSpinBox, QPlainTextEdit { 
    background: #FFFFFF; 
    border: 1px solid #CBD5E1; 
    border-radius: 6px; 
    padding: 6px 10px; 
    color: #0A192F; 
    selection-background-color: #2563EB; 
    selection-color: #FFFFFF;
    min-height: 20px; 
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus { 
    border: 1px solid #2563EB; 
    background: #FFFFFF;
}

QComboBox::drop-down { 
    border: 0; 
    width: 24px; 
}

QComboBox QAbstractItemView { 
    background: #FFFFFF; 
    border: 1px solid #CBD5E1; 
    border-radius: 6px; 
    selection-background-color: #EFF6FF; 
    selection-color: #1D4ED8; 
    color: #0A192F; 
    padding: 4px;
}

QPushButton { 
    background: #FFFFFF; 
    border: 1px solid #CBD5E1; 
    padding: 7px 14px; 
    border-radius: 6px; 
    color: #0A192F; 
    font-weight: 600;
}

QPushButton:hover { 
    background: #F8FAFC; 
    border-color: #2563EB; 
    color: #1D4ED8;
}

QPushButton:pressed { 
    background: #E2E8F0; 
}

QPushButton:disabled { 
    color: #94A3B8; 
    background: #F1F5F9; 
    border-color: #E2E8F0;
}

QPushButton#primary { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1D4ED8, stop:1 #2563EB); 
    border: 1px solid #1D4ED8; 
    color: #FFFFFF; 
    font-weight: 700; 
}

QPushButton#primary:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563EB, stop:1 #1D4ED8); 
    border-color: #3B82F6;
}

QPushButton#themeToggle {
    background: #FFFFFF;
    border: 1px solid #1D4ED8;
    color: #1D4ED8;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 6px;
}

QPushButton#themeToggle:hover {
    background: #EFF6FF;
    border-color: #2563EB;
}

QPushButton#viewPill {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 14px;
    color: #475569;
    font-weight: 600;
}

QPushButton#viewPill:checked {
    background: #1D4ED8;
    border: 1px solid #1D4ED8;
    color: #FFFFFF;
}

QPushButton#viewPill:hover:!checked {
    background: #F1F5F9;
    color: #0A192F;
}

QPushButton#quiet { 
    background: transparent; 
    border: 0; 
    color: #475569; 
}

QPushButton#quiet:hover { 
    color: #0A192F; 
}

QTableView, QTableWidget { 
    background: #FFFFFF; 
    alternate-background-color: #F8FAFC; 
    gridline-color: #E2E8F0; 
    border: 1px solid #CBD5E1; 
    border-radius: 6px; 
    selection-background-color: #DBEAFE; 
    selection-color: #1E3A8A; 
    color: #0A192F;
    outline: 0; 
}

QTableView::item { 
    padding: 8px 10px; 
    border-bottom: 1px solid #E2E8F0; 
    color: #0A192F;
}

QTableView::item:selected {
    background-color: #DBEAFE;
    color: #1E3A8A;
}

QHeaderView::section { 
    background: #F1F5F9; 
    color: #0A192F; 
    border: 0; 
    border-bottom: 2px solid #CBD5E1; 
    padding: 9px 10px; 
    font-size: 11px; 
    font-weight: 700; 
    letter-spacing: 0.5px;
}

QTextBrowser { 
    background: #FFFFFF; 
    border: 1px solid #CBD5E1; 
    border-radius: 6px; 
    padding: 14px; 
    color: #0A192F;
}

QTabWidget::pane { 
    border: 1px solid #CBD5E1; 
    background: #FFFFFF; 
    border-radius: 0 0 6px 6px;
}

QTabBar::tab { 
    background: #F8FAFC; 
    color: #475569; 
    padding: 7px 12px; 
    border-bottom: 2px solid transparent; 
    font-weight: 600;
    font-size: 11px;
}

QTabBar::tab:selected { 
    color: #1D4ED8; 
    background: #FFFFFF; 
    border-bottom: 2px solid #1D4ED8; 
    font-weight: 700;
}

QTabBar::tab:hover:!selected {
    color: #0A192F;
    background: #F1F5F9;
}

QTabBar::scroller {
    width: 44px;
    background: #FFFFFF;
}

QTabBar QToolButton {
    background: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    color: #1D4ED8;
    margin: 1px;
    padding: 1px;
    min-width: 18px;
    min-height: 18px;
    font-weight: 800;
}

QTabBar QToolButton:hover {
    background: #DBEAFE;
    border: 1px solid #2563EB;
    color: #0A192F;
}

QSplitter::handle { 
    background: #CBD5E1; 
}

QScrollBar:vertical { 
    background: #F1F5F9; 
    width: 8px; 
    margin: 0; 
}

QScrollBar::handle:vertical { 
    background: #CBD5E1; 
    min-height: 25px; 
    border-radius: 4px; 
}

QScrollBar::handle:vertical:hover { 
    background: #94A3B8; 
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { 
    height: 0; 
}

QScrollBar:horizontal { 
    background: #F1F5F9; 
    height: 8px; 
}

QScrollBar::handle:horizontal { 
    background: #CBD5E1; 
    min-width: 25px; 
    border-radius: 4px; 
}

QScrollBar::handle:horizontal:hover { 
    background: #94A3B8; 
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { 
    width: 0; 
}

QStatusBar { 
    background: #FFFFFF; 
    color: #475569; 
    border-top: 1px solid #CBD5E1; 
    font-size: 11px;
}

QCheckBox { 
    spacing: 8px; 
    color: #0A192F;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #CBD5E1;
    background: #FFFFFF;
}

QCheckBox::indicator:checked {
    background: #1D4ED8;
    border-color: #1D4ED8;
}

QGroupBox { 
    border: 1px solid #CBD5E1; 
    border-radius: 6px; 
    margin-top: 18px; 
    padding-top: 15px; 
}

QGroupBox::title { 
    subcontrol-origin: margin; 
    padding: 0 6px; 
    color: #0A192F; 
    font-weight: 700;
}

QToolTip { 
    color: #FFFFFF; 
    background: #0A192F; 
    border: 1px solid #1D4ED8; 
    padding: 6px 10px; 
    border-radius: 4px;
}

QMenu { 
    background: #FFFFFF; 
    border: 1px solid #CBD5E1; 
    border-radius: 6px; 
    padding: 4px;
}

QMenu::item { 
    padding: 7px 20px; 
    color: #0A192F; 
    border-radius: 4px;
}

QMenu::item:selected { 
    background: #EFF6FF; 
    color: #1D4ED8;
}

/* TradingView-Style Right Tool Dock */
QFrame#rightDock {
    background: #F8FAFC;
    border-left: 1px solid #E2E8F0;
    max-width: 48px;
    min-width: 48px;
}

QPushButton#dockBtn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 4px;
    margin: 4px;
    color: #64748B;
    font-size: 16px;
}

QPushButton#dockBtn:hover {
    background: #E2E8F0;
    color: #1D4ED8;
}

QPushButton#dockBtn:checked {
    background: #DBEAFE;
    color: #1E40AF;
    border-left: 3px solid #2563EB;
}

/* Slide-out Drawer Panel */
QFrame#rightDrawer {
    background: #FFFFFF;
    border-left: 1px solid #CBD5E1;
}

/* Live Signal Beacon & Header Widgets */
QLabel#beaconLive {
    color: #065F46;
    font-weight: 700;
    font-size: 11px;
    background: #D1FAE5;
    border: 1px solid #10B981;
    border-radius: 12px;
    padding: 4px 12px;
}

QLabel#beaconOffline {
    color: #991B1B;
    font-weight: 700;
    font-size: 11px;
    background: #FEE2E2;
    border: 1px solid #EF4444;
    border-radius: 12px;
    padding: 4px 12px;
}

QLabel#realtimeClock {
    color: #1D4ED8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-weight: 700;
    font-size: 12px;
    background: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px 10px;
}

QLabel#syncCountdown {
    color: #64748B;
    font-size: 11px;
    font-weight: 600;
    background: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px 8px;
}

/* ======================================================== */
/* QCalendarWidget (Popup Date Picker from QDateEdit)      */
/* ======================================================== */
QCalendarWidget {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
}

QCalendarWidget QWidget#qt_datetimedit_calendar {
    background-color: #FFFFFF;
}

QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #F8FAFC;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    border-bottom: 1px solid #CBD5E1;
    min-height: 38px;
    max-height: 38px;
}

QCalendarWidget QToolButton {
    color: #0A192F;
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    margin: 3px 4px;
    padding: 4px 10px;
    font-weight: 700;
    font-size: 12px;
}

QCalendarWidget QToolButton:hover {
    background-color: #DBEAFE;
    border-color: #2563EB;
    color: #1D4ED8;
}

QCalendarWidget QMenu {
    background-color: #FFFFFF;
    color: #0A192F;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px;
}

QCalendarWidget QSpinBox {
    background-color: #FFFFFF;
    color: #0A192F;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    padding: 2px 6px;
    font-weight: 700;
}

QCalendarWidget QTableView {
    background-color: #FFFFFF;
    color: #0A192F;
    border: none;
    outline: none;
    font-size: 12px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QCalendarWidget QHeaderView::section {
    background-color: #F8FAFC;
    color: #1D4ED8;
    font-weight: 700;
    font-size: 10px;
    border: none;
    border-bottom: 1px solid #CBD5E1;
    padding: 3px 0px;
}

QCalendarWidget QAbstractItemView:enabled {
    color: #0A192F;
    background-color: #FFFFFF;
    font-weight: 700;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #94A3B8;
    background-color: #FFFFFF;
    font-weight: 500;
}

QCalendarWidget QAbstractItemView:hover {
    background-color: #EFF6FF;
    color: #1D4ED8;
}

/* ======================================================== */
/* QCompleter & Timezone Searchable Dropdown Popup          */
/* ======================================================== */
QCompleter QAbstractItemView, QListView#completerPopup, QAbstractItemView#completerPopup {
    background-color: #FFFFFF !important;
    color: #0A192F !important;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #DBEAFE !important;
    selection-color: #1E40AF !important;
    outline: none;
}

QComboBox QLineEdit, QComboBox:editable, QLineEdit#zoneInput {
    background-color: #FFFFFF !important;
    color: #0A192F !important;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QComboBox QLineEdit:focus, QLineEdit#zoneInput:focus {
    border: 1px solid #2563EB;
    background-color: #FFFFFF !important;
    color: #0A192F !important;
}
"""

def is_system_dark() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return val == 0
    except Exception:
        return True

def resolve_theme(theme_name: str) -> str:
    name = str(theme_name).lower()
    if "auto" in name or "system" in name:
        return "Dark Navy" if is_system_dark() else "Clean Light"
    if "light" in name or "white" in name:
        return "Clean Light"
    return "Dark Navy"

STYLE = DARK_STYLE

def get_style(theme_name: str) -> str:
    """Return the Qt QSS stylesheet for the requested theme."""
    resolved = resolve_theme(theme_name)
    if resolved == "Clean Light":
        return LIGHT_STYLE
    return DARK_STYLE
