"""Qt stylesheet for InstaCMA (navy / white professional theme)."""

NAVY = "#1F3864"
NAVY_DARK = "#152847"
ACCENT = "#C55A11"
PASS = "#C6EFCE"
FAIL = "#FFC7CE"
AMBER = "#FFEB9C"
STATUS_COLOURS = {"PASS": PASS, "FAIL": FAIL, "AMBER": AMBER, "OK": PASS, "WARN": AMBER, "ERROR": FAIL}

STYLESHEET = """
QMainWindow, QWidget { background: #F5F7FA; font-family: 'Segoe UI', Arial; font-size: 10pt; color: #222; }
QListWidget#Sidebar { background: %(navy)s; color: white; border: none; font-size: 10.5pt; padding-top: 8px; }
QListWidget#Sidebar::item { padding: 10px 14px; border-left: 4px solid transparent; }
QListWidget#Sidebar::item:selected { background: %(navy_dark)s; border-left: 4px solid %(accent)s; color: white; }
QListWidget#Sidebar::item:hover { background: #2B4A7E; }
QLabel#AppTitle { background: %(navy)s; color: white; font-size: 16pt; font-weight: bold; padding: 14px 14px 2px 14px; }
QLabel#AppCredit { background: %(navy)s; color: #C9D3E6; font-size: 8pt; padding: 0px 14px 12px 14px; }
QLabel#PageTitle { font-size: 16pt; font-weight: bold; color: %(navy)s; padding: 4px 0 2px 0; }
QLabel#PageSub { color: #595959; padding-bottom: 8px; }
QFrame#Card { background: white; border: 1px solid #DDE3EC; border-radius: 8px; }
QLabel#CardTitle { color: #595959; font-size: 9pt; background: transparent; }
QLabel#CardValue { color: %(navy)s; font-size: 17pt; font-weight: bold; background: transparent; }
QLabel#CardSub { color: #7F7F7F; font-size: 8.5pt; background: transparent; }
QPushButton { background: %(navy)s; color: white; border: none; border-radius: 5px; padding: 7px 16px; }
QPushButton:hover { background: #2B4A7E; }
QPushButton:disabled { background: #A6A6A6; }
QPushButton#Secondary { background: white; color: %(navy)s; border: 1px solid %(navy)s; }
QPushButton#Accent { background: %(accent)s; }
QGroupBox { background: white; border: 1px solid #DDE3EC; border-radius: 6px; margin-top: 14px; padding: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: %(navy)s; font-weight: bold; }
QTableWidget, QTableView { background: white; gridline-color: #E7E6E6; border: 1px solid #DDE3EC;
    selection-background-color: #DDEBF7; selection-color: #000; }
QHeaderView::section { background: %(navy)s; color: white; padding: 4px; border: none; font-weight: bold; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QPlainTextEdit, QTextEdit {
    background: white; border: 1px solid #BFBFBF; border-radius: 4px; padding: 3px; }
QStatusBar { background: white; color: #404040; }
QTabWidget::pane { border: 1px solid #DDE3EC; background: white; }
QTabBar::tab { background: #E7ECF3; padding: 6px 14px; }
QTabBar::tab:selected { background: white; color: %(navy)s; font-weight: bold; }
""" % {"navy": NAVY, "navy_dark": NAVY_DARK, "accent": ACCENT}
