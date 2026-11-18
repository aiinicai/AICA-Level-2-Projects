"""Visual system (v8): deep-navy sidebar with icons, white work surfaces, an accent colour per module, status
colours used only for meaning. Light (default) and dark variants; apply(name) switches every colour constant used
by the pages, then returns the Qt stylesheet."""
from __future__ import annotations

# module accents (sidebar marker, page title bar, tiles): set per theme by apply()
MODULE: dict = {}
ICONS = {
    "Home": "⌂", "Office": "▣", "Claims": "✚", "Exports": "$", "Workbench": "▤", "New entry": "✎", "Bank": "₹", "Reports": "▦", "Compliance": "⚖",
    "Close": "✓", "Red flags": "⚑", "Journals": "⟳", "GSTR-2B": "⇄", "Memory": "◈", "Setup": "⚙",
}
# sidebar sections (by the first page of each)
NAV_SECTIONS = {"Home": "WORK", "Reports": "OUTCOMES", "Journals": "ACTION", "Memory": "SYSTEM"}

_MOD_DARK = {"Home": "#8B7CFF", "Office": "#38BDF8", "Claims": "#F472B6", "Exports": "#4ADE80", "Workbench": "#60A5FA",
             "New entry": "#22D3EE", "Bank": "#2DD4BF", "Reports": "#A78BFA", "Compliance": "#FBBF24",
             "Close": "#34D399", "Red flags": "#FB7185", "Journals": "#C084FC", "GSTR-2B": "#FB923C",
             "Memory": "#94A3B8", "Setup": "#94A3B8", "Search": "#8B7CFF"}
_MOD_LIGHT = {"Home": "#4F46E5", "Office": "#0284C7", "Claims": "#DB2777", "Exports": "#16A34A", "Workbench": "#2563EB",
              "New entry": "#0891B2", "Bank": "#0D9488", "Reports": "#7C3AED", "Compliance": "#D97706",
              "Close": "#059669", "Red flags": "#DC2626", "Journals": "#9333EA", "GSTR-2B": "#EA580C",
              "Memory": "#475569", "Setup": "#64748B", "Search": "#4F46E5"}

# Every value read by QColor() elsewhere stays a plain hex colour; translucent values (GLASS, TOPBAR, ...) are used
# only inside the stylesheet. TILES = the three Home tiles (gradient start, end, sparkline).
_DARK_STATUS = dict(OK_FG="#34D399", OK_BG="#0E2B24", WARN_FG="#FBBF24", WARN_BG="#2D2210", ERR_FG="#F87171",
                    ERR_BG="#2E1418", INFO_FG="#A5B4FC", INFO_BG="#1B2050")
PALETTES = {
    "midnight": dict(_DARK_STATUS, LABEL="Midnight Neon", DARK=True,
                     INK="#E8ECF8", MUTED="#9AA3C7", LINE="#2A3256", BG="#070B1A", BG2="#16103A",
                     SURFACE="#11162E", SUBTLE="#151B36", HOVER="#1C2447", HEADER="#141A35", SELECT="#2A2366",
                     GLASS="rgba(20, 26, 56, 0.72)", TOPBAR="rgba(9, 13, 32, 0.92)", INPUT="#0E1330",
                     ACCENT="#7C5CFF", ACCENT2="#4F8BFF", ACCENT_HOVER="#957BFF", ACCENT_SOFT="#241E52",
                     PRIMARY_FG="#FFFFFF", GLOW="#7C5CFF",
                     NAV_BG="#080C1E", NAV_BG2="#0F0B2A", NAV_FG="#A3ACD1", NAV_HOVER="#161D3D",
                     NAV_ACTIVE="#251D57", NAV_TEXT_ON="#FFFFFF",
                     TILES=[("#2563EB", "#1E2A78", "#7DD3FC"), ("#0EA5A4", "#0B3B4A", "#5EEAD4"),
                            ("#8B3CF7", "#3B1675", "#F0ABFC")]),
    "aurora": dict(_DARK_STATUS, LABEL="Aurora Teal", DARK=True,
                   INK="#E6F4F1", MUTED="#8FB3AE", LINE="#1F3D40", BG="#03141A", BG2="#062B2B",
                   SURFACE="#0A2026", SUBTLE="#0D262C", HOVER="#123238", HEADER="#0C252B", SELECT="#134E4A",
                   GLASS="rgba(10, 36, 42, 0.74)", TOPBAR="rgba(3, 20, 26, 0.92)", INPUT="#071B21",
                   ACCENT="#14B8A6", ACCENT2="#22D3EE", ACCENT_HOVER="#2DD4BF", ACCENT_SOFT="#0F3B3A",
                   PRIMARY_FG="#04201E", GLOW="#14B8A6",
                   NAV_BG="#021015", NAV_BG2="#042226", NAV_FG="#94BDB7", NAV_HOVER="#0B2A2F",
                   NAV_ACTIVE="#0F3D3C", NAV_TEXT_ON="#FFFFFF",
                   TILES=[("#0891B2", "#0C3A4A", "#67E8F9"), ("#059669", "#063A2E", "#6EE7B7"),
                          ("#4F46E5", "#1E1B5A", "#A5B4FC")]),
    "royal": dict(_DARK_STATUS, LABEL="Royal Navy & Gold", DARK=True,
                  INK="#F1F2F6", MUTED="#A9B0C8", LINE="#2B3560", BG="#0A1128", BG2="#1B1640",
                  SURFACE="#111A38", SUBTLE="#141E40", HOVER="#1B2650", HEADER="#141D3E", SELECT="#3A3218",
                  GLASS="rgba(19, 28, 62, 0.74)", TOPBAR="rgba(10, 16, 40, 0.92)", INPUT="#0D1531",
                  ACCENT="#D4AF37", ACCENT2="#F5D77A", ACCENT_HOVER="#E3C25A", ACCENT_SOFT="#3A3218",
                  PRIMARY_FG="#1A1405", GLOW="#D4AF37",
                  NAV_BG="#070D22", NAV_BG2="#120E2C", NAV_FG="#AEB5CF", NAV_HOVER="#16204A",
                  NAV_ACTIVE="#2A2614", NAV_TEXT_ON="#FFF7DD",
                  TILES=[("#1D4ED8", "#172554", "#93C5FD"), ("#B45309", "#3B2408", "#FCD34D"),
                         ("#7E22CE", "#2E1065", "#D8B4FE")]),
    "graphite": dict(_DARK_STATUS, LABEL="Graphite", DARK=True,
                     INK="#ECEEF2", MUTED="#9CA3AF", LINE="#2E3238", BG="#0F1013", BG2="#1B1D23",
                     SURFACE="#17191E", SUBTLE="#1B1E24", HOVER="#23262E", HEADER="#1B1E24", SELECT="#1E3A5F",
                     GLASS="rgba(26, 28, 34, 0.80)", TOPBAR="rgba(15, 16, 19, 0.94)", INPUT="#121418",
                     ACCENT="#3B82F6", ACCENT2="#06B6D4", ACCENT_HOVER="#60A5FA", ACCENT_SOFT="#16253F",
                     PRIMARY_FG="#FFFFFF", GLOW="#3B82F6",
                     NAV_BG="#0B0C0F", NAV_BG2="#121318", NAV_FG="#A1A7B3", NAV_HOVER="#1B1D23",
                     NAV_ACTIVE="#1E2A40", NAV_TEXT_ON="#FFFFFF",
                     TILES=[("#2563EB", "#1E293B", "#93C5FD"), ("#0D9488", "#1F2937", "#5EEAD4"),
                            ("#64748B", "#1E293B", "#CBD5E1")]),
    "pearl": dict(LABEL="Pearl (light)", DARK=False,
                  INK="#0F172A", MUTED="#64748B", LINE="#E2E8F0", BG="#EEF1F8", BG2="#F6F3FF",
                  SURFACE="#FFFFFF", SUBTLE="#F8FAFC", HOVER="#F1F5F9", HEADER="#F8FAFC", SELECT="#E0E7FF",
                  GLASS="rgba(255, 255, 255, 0.88)", TOPBAR="rgba(255, 255, 255, 0.94)", INPUT="#FFFFFF",
                  ACCENT="#4F46E5", ACCENT2="#7C3AED", ACCENT_HOVER="#4338CA", ACCENT_SOFT="#EEF2FF",
                  PRIMARY_FG="#FFFFFF", GLOW="#6366F1",
                  NAV_BG="#0F172A", NAV_BG2="#1E1B4B", NAV_FG="#B6C0DC", NAV_HOVER="#1E2A4A",
                  NAV_ACTIVE="#2E2A7A", NAV_TEXT_ON="#FFFFFF",
                  OK_FG="#067647", OK_BG="#ECFDF3", WARN_FG="#B54708", WARN_BG="#FFFAEB", ERR_FG="#B42318",
                  ERR_BG="#FEF3F2", INFO_FG="#3538CD", INFO_BG="#EEF4FF",
                  TILES=[("#3B82F6", "#4338CA", "#DBEAFE"), ("#14B8A6", "#0E7490", "#CCFBF1"),
                         ("#A855F7", "#6D28D9", "#F5D0FE")]),
}
ALIASES = {"light": "pearl", "dark": "midnight"}
DEFAULT = "midnight"
THEMES = [(k, v["LABEL"]) for k, v in PALETTES.items()]

NAME = DEFAULT
# populated by apply()
INK = MUTED = LINE = BG = BG2 = SURFACE = SUBTLE = HOVER = ACCENT = ACCENT2 = ACCENT_HOVER = ACCENT_SOFT = ""
NAV_BG = NAV_BG2 = NAV_FG = NAV_HOVER = NAV_ACTIVE = NAV_TEXT_ON = HEADER = SELECT = GLASS = TOPBAR = INPUT = ""
OK_FG = OK_BG = WARN_FG = WARN_BG = ERR_FG = ERR_BG = INFO_FG = INFO_BG = PRIMARY_FG = GLOW = LABEL = ""
DARK = True
TILES: list = []
STATUS: dict = {}
LIGHT = ""


def resolve(name: str) -> str:
    name = ALIASES.get(name, name)
    return name if name in PALETTES else DEFAULT


def qss(p: dict) -> str:
    return f"""
* {{ font-family: 'Segoe UI Variable Text', 'Segoe UI', 'Inter', sans-serif; font-size: 13px; color: {p['INK']}; }}
QMainWindow {{ background: {p['BG']}; }}
QWidget#shell {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {p['BG']}, stop:0.55 {p['BG']},
                                             stop:1 {p['BG2']}); }}
QWidget#page, QStackedWidget, QWidget#navhost {{ background: transparent; }}
QWidget#topbar {{ background: {p['TOPBAR']}; border-bottom: 1px solid {p['LINE']}; }}
QWidget#sidebar {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {p['NAV_BG']}, stop:1 {p['NAV_BG2']});
                   border-right: 1px solid {p['LINE'] if p['DARK'] else p['NAV_BG']}; }}
QWidget#sidebar QLabel {{ color: {p['NAV_FG']}; background: transparent; }}
QLabel#navsec {{ color: {p['NAV_FG']}; font-size: 10px; font-weight: 700; letter-spacing: 1.4px;
                 padding: 8px 20px 2px 20px; }}
QLabel#pagetitle {{ font-size: 16px; font-weight: 700; padding: 0 4px; }}
QLabel#statuspill {{ background: {p['HOVER']}; border: 1px solid {p['LINE']}; border-radius: 12px; padding: 3px 10px;
                     font-size: 12px; }}
QToolButton#themebtn {{ background: {p['HOVER']}; border: 1px solid {p['LINE']}; border-radius: 15px;
                        padding: 4px 12px; color: {p['INK']}; font-weight: 600; }}
QToolButton#themebtn:hover {{ border-color: {p['ACCENT']}; }}
QToolButton#themebtn::menu-indicator {{ image: none; width: 0; }}
QLabel#heroTitle {{ font-size: 24px; font-weight: 800; }}
QLabel#livepill {{ color: {p['OK_FG']}; background: {p['OK_BG']}; border-radius: 12px; padding: 4px 12px;
                   font-weight: 600; font-size: 12px; }}
QLabel#rowname {{ color: {p['INK']}; }}
QLabel#rowamt {{ font-weight: 700; color: {p['INK']}; }}
QLabel#rowamt[tone="err"] {{ color: {p['ERR_FG']}; }}
QLabel#rowamt[tone="warn"] {{ color: {p['WARN_FG']}; }}
QLabel#rowamt[tone="ok"] {{ color: {p['OK_FG']}; }}
QLabel#bigamt {{ font-size: 18px; font-weight: 800; }}
QLabel#bigamt[tone="warn"] {{ color: {p['WARN_FG']}; }}
QLabel#bigamt[tone="ok"] {{ color: {p['OK_FG']}; }}
QFrame#netrow {{ background: {p['ACCENT_SOFT']}; border: 1px solid {p['ACCENT']}; border-radius: 10px; }}
QFrame#hrow {{ border-radius: 8px; background: transparent; }}
QFrame#hrow:hover {{ background: {p['HOVER']}; }}
QLabel#dot {{ font-size: 13px; }}
QLabel#dot[tone="teal"] {{ color: #2DD4BF; }}
QLabel#dot[tone="amber"] {{ color: #FBBF24; }}
QLabel#dot[tone="pink"] {{ color: #F472B6; }}
QLabel#dot[tone="violet"] {{ color: #A78BFA; }}
QLabel#duechip {{ border-radius: 9px; padding: 1px 8px; font-size: 11px; font-weight: 700; }}
QLabel#duechip[tone="red"] {{ color: {p['ERR_FG']}; background: {p['ERR_BG']}; }}
QLabel#duechip[tone="amber"] {{ color: {p['WARN_FG']}; background: {p['WARN_BG']}; }}
QLabel#duechip[tone="info"] {{ color: {p['INFO_FG']}; background: {p['INFO_BG']}; }}
QLabel#brand {{ font-size: 15px; font-weight: 700; color: {p['INK']}; padding: 0 4px; }}
QLabel#sidebrand {{ font-size: 14px; font-weight: 700; color: #FFFFFF; padding: 4px 14px; }}
QLabel#sidesub {{ font-size: 11px; color: {p['NAV_FG']}; padding: 0 14px 6px 14px; }}
QPushButton#nav {{ text-align: left; padding: 5px 12px; border: 1px solid transparent; border-radius: 10px;
                   margin: 0px 10px; color: {p['NAV_FG']}; font-weight: 500; background: transparent; }}
QPushButton#nav:hover {{ background: {p['NAV_HOVER']}; color: #FFFFFF; border-color: {p['NAV_HOVER']}; }}
QPushButton#nav:checked {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p['NAV_ACTIVE']},
                                                       stop:1 {p['NAV_BG']});
                           color: {p['NAV_TEXT_ON']}; font-weight: 700; border: 1px solid {p['ACCENT']}; }}
QLabel#h1 {{ font-size: 20px; font-weight: 700; }}
QLabel#h2 {{ font-size: 15px; font-weight: 600; }}
QLabel#muted {{ color: {p['MUTED']}; }}
QLabel#big {{ font-size: 22px; font-weight: 700; }}
QLabel#money {{ font-size: 22px; font-weight: 700; color: {p['INK']}; }}
QLabel#section {{ color: {p['MUTED']}; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }}
QFrame#card {{ background: {p['GLASS']}; border: 1px solid {p['LINE']}; border-radius: 14px; }}
QFrame#card[hover="true"] {{ border-color: {p['ACCENT']}; }}
QLabel#cardTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#stat {{ font-size: 24px; font-weight: 700; color: {p['ACCENT']}; }}
QPushButton {{ background: {p['SURFACE']}; border: 1px solid {p['LINE']}; border-radius: 9px; padding: 7px 14px;
               color: {p['INK']}; font-weight: 500; }}
QPushButton:hover {{ background: {p['HOVER']}; border-color: {p['ACCENT']}; }}
QPushButton:pressed {{ background: {p['ACCENT_SOFT']}; }}
QPushButton#primary {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {p['ACCENT']}, stop:1 {p['ACCENT2']});
                       color: {p['PRIMARY_FG']}; border: 1px solid {p['ACCENT_HOVER']}; font-weight: 700; }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {p['ACCENT_HOVER']},
                                                        stop:1 {p['ACCENT2']}); border-color: {p['ACCENT2']}; }}
QPushButton#primary:disabled {{ background: {p['ACCENT_SOFT']}; color: {p['MUTED']}; }}
QPushButton#ghost {{ background: transparent; border: none; color: {p['MUTED']}; padding: 6px 8px; }}
QPushButton#ghost:hover {{ color: {p['INK']}; background: {p['HOVER']}; }}
QPushButton#folder {{ background: transparent; border: 1px dashed {p['LINE']}; color: {p['MUTED']}; text-align: left;
                      padding: 5px 10px; }}
QPushButton#folder:hover {{ border-color: {p['ACCENT']}; color: {p['ACCENT']}; }}
QPushButton#seg {{ border: none; border-radius: 6px; padding: 5px 6px; font-size: 12px; background: transparent;
                   color: {p['MUTED']}; font-weight: 600; }}
QPushButton#seg:checked {{ background: {p['SURFACE']}; color: {p['ACCENT']}; border: 1px solid {p['LINE']}; }}
QWidget#segbar {{ background: {p['HOVER']}; border-radius: 8px; }}
QPushButton:disabled {{ color: {p['MUTED']}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {{ background: {p['INPUT']}; border: 1px solid {p['LINE']};
    border-radius: 9px; padding: 5px 8px; min-height: 20px; color: {p['INK']}; }}
QLineEdit:hover, QComboBox:hover, QDateEdit:hover {{ border-color: {p['ACCENT_SOFT'] if p['DARK'] else '#C7D2FE'}; }}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus {{ border: 1px solid {p['ACCENT']}; }}
QLineEdit[state="warn"] {{ background: {p['WARN_BG']}; border-color: #FEC84B; }}
QLineEdit[state="error"] {{ background: {p['ERR_BG']}; border-color: #FDA29B; }}
QComboBox QAbstractItemView {{ background: {p['SURFACE']}; border: 1px solid {p['LINE']};
    selection-background-color: {p['SELECT']}; selection-color: {p['INK']}; }}
QTableWidget, QTreeWidget, QTableView, QTreeView {{ background: {p['SURFACE']};
    alternate-background-color: {p['SUBTLE']}; border: 1px solid {p['LINE']}; border-radius: 12px;
    gridline-color: {p['LINE']};
    selection-background-color: {p['SELECT']}; selection-color: {p['INK']}; }}
QHeaderView::section {{ background: {p['HEADER']}; border: none; border-bottom: 2px solid {p['LINE']}; padding: 7px;
                        font-weight: 700; color: {p['MUTED']}; font-size: 12px; }}
QListWidget {{ background: {p['SURFACE']}; border: 1px solid {p['LINE']}; border-radius: 10px; padding: 4px;
               outline: none; }}
QListWidget::item {{ padding: 8px 6px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {p['SELECT']}; color: {p['INK']}; }}
QListWidget::item:hover {{ background: {p['HOVER']}; }}
QListWidget#queue {{ background: transparent; border: none; outline: none; }}
QListWidget#queue::item {{ border: none; margin: 0 0 6px 0; }}
QListWidget#queue::item:selected {{ background: transparent; }}
QFrame#qitem {{ background: {p['SURFACE']}; border: 1px solid {p['LINE']}; border-radius: 10px; }}
QFrame#qitem[selected="true"] {{ border: 2px solid {p['ACCENT']}; background: {p['ACCENT_SOFT']}; }}
QLabel#chip {{ border-radius: 9px; padding: 2px 8px; font-size: 11px; font-weight: 600; }}
QFrame#issue {{ border-radius: 8px; }}
QStatusBar {{ background: {p['SURFACE']}; border-top: 1px solid {p['LINE']}; color: {p['MUTED']}; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: transparent; padding: 8px 14px; color: {p['MUTED']}; font-weight: 600; border: none;
               border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {p['INK']}; border-bottom: 3px solid {p['ACCENT']}; }}
QTabBar::tab:hover {{ background: {p['HOVER']}; border-radius: 6px; }}
QTabBar::tab:hover {{ color: {p['INK']}; }}
QProgressBar {{ border: none; background: {p['ACCENT_SOFT']}; border-radius: 3px; max-height: 6px; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p['ACCENT']},
                                                    stop:1 {p['ACCENT2']}); border-radius: 3px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle {{ background: {p['BG']}; }}
QPlainTextEdit {{ background: {p['SURFACE']}; border: 1px solid {p['LINE']}; border-radius: 10px; color: {p['INK']}; }}
QCheckBox {{ spacing: 6px; }}
QLabel#pillOk {{ background: {p['OK_BG']}; color: {p['OK_FG']}; border-radius: 10px; padding: 3px 10px; font-weight: 600; }}
QLabel#pillBad {{ background: {p['ERR_BG']}; color: {p['ERR_FG']}; border-radius: 10px; padding: 3px 10px; font-weight: 600; }}
QLabel#pillWarn {{ background: {p['WARN_BG']}; color: {p['WARN_FG']}; border-radius: 10px; padding: 3px 10px;
                   font-weight: 600; }}
QComboBox[conf="green"] {{ background: {p['SURFACE']}; }}
QComboBox[conf="amber"] {{ background: {p['WARN_BG']}; }}
QComboBox[conf="red"] {{ background: {p['ERR_BG']}; }}
QComboBox[cell="true"] {{ border: none; border-radius: 0; }}
QLabel[tone="ok"] {{ color: {p['OK_FG']}; font-weight: 600; }}
QLabel[tone="warn"] {{ color: {p['WARN_FG']}; }}
QLabel[tone="err"] {{ color: {p['ERR_FG']}; }}
QLabel[tone="info"] {{ color: {p['INFO_FG']}; }}
QLabel[tone="errb"] {{ color: {p['ERR_FG']}; font-weight: 600; }}
QFrame#issue[tone="red"] {{ background: {p['ERR_BG']}; }}
QFrame#issue[tone="amber"] {{ background: {p['WARN_BG']}; }}
QFrame#issue[tone="info"] {{ background: {p['INFO_BG']}; }}
QFrame#issue[tone="green"] {{ background: {p['OK_BG']}; }}
QFrame#issue[tone="subtle"] {{ background: {p['SUBTLE']}; }}
QLabel#chip[tone="green"], QLabel#chip[tone="ready"] {{ color: {p['OK_FG']}; background: {p['OK_BG']}; }}
QLabel#chip[tone="amber"], QLabel#chip[tone="attention"] {{ color: {p['WARN_FG']}; background: {p['WARN_BG']}; }}
QLabel#chip[tone="red"], QLabel#chip[tone="blocked"] {{ color: {p['ERR_FG']}; background: {p['ERR_BG']}; }}
QLabel#chip[tone="posted"], QLabel#chip[tone="exception"] {{ color: {p['MUTED']}; background: {p['HOVER']}; }}
QLabel#chip[tone="info"] {{ color: {p['INFO_FG']}; background: {p['INFO_BG']}; }}
QPushButton#autochip {{ border: none; border-radius: 11px; padding: 3px 10px; font-size: 12px; font-weight: 600; }}
QPushButton#autochip[tone="green"] {{ color: {p['OK_FG']}; background: {p['OK_BG']}; }}
QPushButton#autochip[tone="amber"] {{ color: {p['INFO_FG']}; background: {p['INFO_BG']}; }}
QPushButton#autochip[tone="red"] {{ color: {p['ERR_FG']}; background: {p['ERR_BG']}; }}
QToolTip {{ background: #0B1020; color: white; border: 1px solid {p['ACCENT']}; padding: 6px 8px; border-radius: 8px; }}
QMenu {{ background: {p['SURFACE']}; border: 1px solid {p['LINE']}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 18px 7px 10px; border-radius: 7px; color: {p['INK']}; }}
QMenu::item:selected {{ background: {p['ACCENT_SOFT']}; color: {p['INK']}; }}
QDialog {{ background: {p['BG']}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p['LINE']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{ background: {p['ACCENT']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p['LINE']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
"""


def apply(name: str = DEFAULT) -> str:
    """Switch every colour constant to the chosen theme; returns the stylesheet."""
    global NAME, STATUS, LIGHT, MODULE
    NAME = resolve(name)
    p = PALETTES[NAME]
    globals().update(p)
    MODULE = dict(_MOD_DARK if p["DARK"] else _MOD_LIGHT)
    STATUS = {"ready": (p["OK_FG"], p["OK_BG"]), "green": (p["OK_FG"], p["OK_BG"]),
              "attention": (p["WARN_FG"], p["WARN_BG"]), "amber": (p["WARN_FG"], p["WARN_BG"]),
              "blocked": (p["ERR_FG"], p["ERR_BG"]), "red": (p["ERR_FG"], p["ERR_BG"]),
              "posted": (p["MUTED"], p["HOVER"]), "exception": (p["MUTED"], p["HOVER"]),
              "info": (p["INFO_FG"], p["INFO_BG"])}
    LIGHT = qss(p)
    try:
        from . import common
        common.CONF_COLOURS.update({"green": p["SURFACE"] if p["DARK"] else "#F6FEF9",
                                    "amber": p["WARN_BG"], "red": p["ERR_BG"]})
    except Exception:
        pass
    return LIGHT


def swatch(name: str, size: int = 18):
    """A round swatch of a theme's accent gradient, for the theme menu."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
    p = PALETTES[resolve(name)]
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.GlobalColor.transparent)
    qp = QPainter(pm)
    qp.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor(p["BG"]))
    g.setColorAt(0.5, QColor(p["ACCENT"]))
    g.setColorAt(1, QColor(p["ACCENT2"]))
    qp.setBrush(g)
    qp.setPen(QPen(QColor(p["LINE"]), 1))
    qp.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    qp.end()
    return QIcon(pm)


def app_icon():
    """The app's own icon, drawn at runtime (no image files to ship): a rounded tile with a rupee mark."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, size, size)
        g.setColorAt(0, QColor("#4F46E5"))
        g.setColorAt(1, QColor("#0D9488"))
        p.setBrush(QBrush(g))
        p.setPen(Qt.PenStyle.NoPen)
        r = size * 0.22
        p.drawRoundedRect(QRectF(0, 0, size, size), r, r)
        p.setPen(QColor("white"))
        f = QFont("Segoe UI", max(6, int(size * 0.55)))
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, -size * 0.02, size, size), Qt.AlignmentFlag.AlignCenter, "₹")
        p.end()
        icon.addPixmap(pm)
    return icon


def save_icon_file(path) -> bool:
    """Write the icon as .ico (for the Desktop shortcut)."""
    try:
        pm = app_icon().pixmap(256, 256)
        return pm.save(str(path), "ICO") or pm.save(str(path).replace(".ico", ".png"), "PNG")
    except Exception:
        return False


apply(DEFAULT)
