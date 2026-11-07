"""Royal themes, stylesheet generator and the built-in SVG icon set."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

THEMES = {
    "Royal Night": dict(dark=True, bg="#0A0F24", bg2="#0E1530", surface="#131C3E", surface2="#1A2552", border="#27346B",
                        text="#EAEEFF", muted="#8F9CCB", primary="#6D5DF6", primary2="#9B6BFF", gold="#F6C453",
                        paper="#FBFCFF", paper_text="#14193A", ok="#34D399", sel="#26336E"),
    "Royal Ivory": dict(dark=False, bg="#F3F5FC", bg2="#E9EDFA", surface="#FFFFFF", surface2="#F0F3FF", border="#D5DBF2",
                        text="#10173A", muted="#5E6A9A", primary="#4338CA", primary2="#7C3AED", gold="#B7791F",
                        paper="#FFFFFF", paper_text="#14193A", ok="#059669", sel="#DDE3FF"),
    "Classic": dict(dark=False, bg="#EEF0F3", bg2="#E3E6EA", surface="#FFFFFF", surface2="#F6F7F9", border="#C5CBD3",
                    text="#1B2433", muted="#586272", primary="#1F3A5F", primary2="#1F3A5F", gold="#1F3A5F",
                    paper="#FFFFFF", paper_text="#1B2433", ok="#1F7A4D", sel="#DCE6F2"),
    "Imperial Ruby": dict(dark=True, bg="#160A12", bg2="#1E0E19", surface="#291322", surface2="#37192D", border="#5A2A47",
                          text="#FBEFF5", muted="#C79AB3", primary="#D6336C", primary2="#F0642A", gold="#F6C453",
                          paper="#FFFBFD", paper_text="#2A1020", ok="#34D399", sel="#4A2038"),
}
SEV = {"Critical": "#FF5C7A", "Major": "#FFA24C", "Minor": "#F2CF55", "Info": "#62B4FF"}
SEV_SOFT = {"Critical": "#FF5C7A", "Major": "#FFA24C", "Minor": "#F2CF55", "Info": "#62B4FF"}

FONT_STACK = '"Segoe UI Variable Text","Segoe UI","Inter","SF Pro Text","Helvetica Neue",Arial,sans-serif'
MONO_STACK = '"Cascadia Mono","Consolas","DejaVu Sans Mono",monospace'

_P = {
    "crown": "M3 18l2-11 5 5 2-8 2 8 5-5 2 11z M3 21h18",
    "home": "M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
    "dash": "M4 20V10 M10 20V4 M16 20v-7 M22 20H2",
    "list": "M8 6h13 M8 12h13 M8 18h13 M3 6h.01 M3 12h.01 M3 18h.01",
    "pen": "M12 20h9 M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z",
    "align": "M9 17H7a5 5 0 0 1 0-10h2 M15 7h2a5 5 0 0 1 0 10h-2 M8 12h8",
    "report": "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z M14 3v5h5 M9 13h6 M9 17h6",
    "settings": "M4 21v-7 M4 10V3 M12 21v-9 M12 8V3 M20 21v-5 M20 12V3 M1 14h6 M9 8h6 M17 16h6",
    "folder": "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
    "scan": "M3 7V5a2 2 0 0 1 2-2h2 M17 3h2a2 2 0 0 1 2 2v2 M21 17v2a2 2 0 0 1-2 2h-2 M7 21H5a2 2 0 0 1-2-2v-2 M7 12h10",
    "play": "M7 4l13 8-13 8z",
    "stop": "M6 6h12v12H6z",
    "rotl": "M2.5 2v6h6 M2.66 15.57a10 10 0 1 0 .57-8.38",
    "rotr": "M21.5 2v6h-6 M21.34 15.57a10 10 0 1 1-.57-8.38",
    "rot180": "M4 12a8 8 0 0 1 14-5.3 M20 4v4h-4 M20 12a8 8 0 0 1-14 5.3 M4 20v-4h4",
    "zin": "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z M21 21l-4.3-4.3 M11 8v6 M8 11h6",
    "zout": "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z M21 21l-4.3-4.3 M8 11h6",
    "fit": "M8 3H5a2 2 0 0 0-2 2v3 M21 8V5a2 2 0 0 0-2-2h-3 M3 16v3a2 2 0 0 0 2 2h3 M16 21h3a2 2 0 0 0 2-2v-3",
    "merge": "M6 3v6a6 6 0 0 0 6 6h6 M18 15l-3-3 M18 15l-3 3 M6 21v-6",
    "split": "M16 3h5v5 M8 3H3v5 M12 22v-8.3a4 4 0 0 0-1.2-2.8L3 3 M15 9l6-6",
    "eyeoff": "M3 3l18 18 M10.6 10.6a2 2 0 0 0 2.8 2.8 M9.9 5.1A10 10 0 0 1 12 5c5 0 9 4 10 7a13 13 0 0 1-2.2 3.2 M6.6 6.6A13 13 0 0 0 2 12c1 3 5 7 10 7a9.7 9.7 0 0 0 4-.9",
    "link": "M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7 M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7",
    "unlink": "M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7 M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7 M3 3l18 18",
    "save": "M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z M17 21v-8H7v8 M7 3v5h8",
    "upload": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M17 8l-5-5-5 5 M12 3v12",
    "download": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M7 10l5 5 5-5 M12 15V3",
    "sun": "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z M12 1v2 M12 21v2 M4.2 4.2l1.4 1.4 M18.4 18.4l1.4 1.4 M1 12h2 M21 12h2 M4.2 19.8l1.4-1.4 M18.4 5.6l1.4-1.4",
    "moon": "M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z",
    "search": "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z M21 21l-4.3-4.3",
    "check": "M20 6L9 17l-5-5",
    "cmd": "M18 3a3 3 0 0 0-3 3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V6a3 3 0 1 0-3 3h12a3 3 0 1 0 0-6z",
    "chev": "M6 9l6 6 6-6",
    "up": "M18 15l-6-6-6 6",
    "menu": "M3 6h18 M3 12h18 M3 18h18",
    "table": "M3 3h18v18H3z M3 9h18 M3 15h18 M9 3v18",
    "copy": "M9 9h11v11H9z M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1",
    "done": "M22 11.1V12a10 10 0 1 1-5.9-9.1 M22 4L12 14l-3-3",
    "alert": "M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z M12 9v4 M12 17h.01",
    "doc": "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z M14 3v5h5",
    "bolt": "M13 2L3 14h8l-1 8 10-12h-8z",
    "trash": "M3 6h18 M8 6V4h8v2 M6 6l1 14h10l1-14",
    "x": "M18 6L6 18 M6 6l12 12",
    "star": "M12 2l3 7 7 .6-5.3 4.7 1.6 7.2L12 17.8 5.7 21.5l1.6-7.2L2 9.6 9 9z",
}
_cache = {}


def icon(name, color="#FFFFFF", size=20, width=1.9):
    key = (name, color, size, width)
    if key in _cache:
        return _cache[key]
    d = _P.get(name, _P["doc"])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{width}" '
           f'stroke-linecap="round" stroke-linejoin="round"><path d="{d}"/></svg>')
    r = QSvgRenderer(QByteArray(svg.encode()))
    ratio = 2
    pm = QPixmap(size * ratio, size * ratio); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); r.render(p); p.end()
    pm.setDevicePixelRatio(ratio)
    ic = QIcon(pm); _cache[key] = ic
    return ic


def qss(p, scale=1.0):
    fs = int(round(13 * scale))
    return f"""
* {{ font-family: {FONT_STACK}; font-size: {fs}px; color: {p['text']}; }}
QMainWindow, QDialog {{ background: {p['bg']}; }}
QWidget#root {{ background: {p['bg']}; }}
QWidget#page {{ background: transparent; }}
QToolTip {{ background: {p['surface2']}; color: {p['text']}; border: 1px solid {p['border']}; padding: 6px 8px; border-radius: 8px; }}

QFrame#sidebar {{ background: {p['bg2']}; border-right: 1px solid {p['border']}; }}
QFrame#topbar {{ background: transparent; border-bottom: 1px solid {p['border']}; }}
QFrame#card {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 16px; }}
QFrame#cardflat {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 12px; }}
QFrame#drop {{ background: {p['surface']}; border: 1.5px dashed {p['border']}; border-radius: 18px; }}
QFrame#drop[hover="true"] {{ border: 1.5px dashed {p['gold']}; background: {p['surface2']}; }}
QFrame#drop[filled="true"] {{ border: 1.5px solid {p['primary']}; }}
QFrame#hero {{ border-radius: 20px; border: 1px solid {p['border']};
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {p['surface2']}, stop:1 {p['surface']}); }}

QLabel {{ background: transparent; }}
QLabel[role="brand"] {{ font-size: {int(18*scale)}px; font-weight: 800; letter-spacing: 0.4px; }}
QLabel[role="title"] {{ font-size: {int(24*scale)}px; font-weight: 800; }}
QLabel[role="h2"] {{ font-size: {int(15*scale)}px; font-weight: 700; }}
QLabel[role="muted"] {{ color: {p['muted']}; }}
QLabel[role="small"] {{ color: {p['muted']}; font-size: {int(11.5*scale)}px; }}
QLabel[role="kpi"] {{ font-size: {int(34*scale)}px; font-weight: 800; }}
QLabel[role="gold"] {{ color: {p['gold']}; font-weight: 700; }}
QLabel[role="pill"] {{ border-radius: 10px; padding: 2px 10px; font-weight: 700; font-size: {int(11.5*scale)}px; }}

QPushButton {{ background: {p['surface2']}; border: 1px solid {p['border']}; border-radius: 10px; padding: 8px 14px; font-weight: 600; }}
QPushButton:hover {{ border-color: {p['primary']}; background: {p['sel']}; }}
QPushButton:pressed {{ background: {p['border']}; }}
QPushButton:disabled {{ color: {p['muted']}; background: {p['surface']}; border-color: {p['border']}; }}
QPushButton[kind="primary"] {{ border: none; color: white; padding: 11px 24px; font-size: {int(14*scale)}px; font-weight: 700;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {p['primary']}, stop:1 {p['primary2']}); }}
QPushButton[kind="primary"]:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {p['primary2']}, stop:1 {p['primary']}); }}
QPushButton[kind="primary"]:disabled {{ background: {p['border']}; color: {p['muted']}; }}
QPushButton[kind="gold"] {{ border: none; color: #2A1B00; background: {p['gold']}; font-weight: 800; }}
QPushButton[kind="ghost"] {{ background: transparent; border: 1px solid transparent; }}
QPushButton[kind="ghost"]:hover {{ background: {p['sel']}; }}
QPushButton[kind="danger"] {{ color: #FF8DA0; border-color: #6B2A3A; }}
QPushButton[kind="chip"] {{ border-radius: 14px; padding: 5px 14px; background: transparent; }}
QPushButton[kind="chip"]:checked {{ background: {p['primary']}; border-color: {p['primary']}; color: white; }}
QPushButton[kind="nav"] {{ text-align: left; background: transparent; border: none; border-radius: 12px; padding: 11px 14px; font-weight: 600; color: {p['muted']}; }}
QPushButton[kind="nav"]:hover {{ background: {p['surface']}; color: {p['text']}; }}
QPushButton[kind="nav"]:checked {{ color: white;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {p['primary']}, stop:1 {p['primary2']}); }}
QToolButton {{ background: {p['surface2']}; border: 1px solid {p['border']}; border-radius: 9px; padding: 6px 10px; font-weight: 600; }}
QToolButton:hover {{ border-color: {p['primary']}; background: {p['sel']}; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}
QToolButton[kind="ghost"] {{ background: transparent; border: 1px solid transparent; }}
QToolButton[kind="ghost"]:hover {{ background: {p['sel']}; }}

QLineEdit, QComboBox, QSpinBox {{ background: {p['surface2']}; border: 1px solid {p['border']}; border-radius: 10px; padding: 8px 12px;
    selection-background-color: {p['primary']}; selection-color: white; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {p['primary']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {p['surface2']}; border: 1px solid {p['border']}; selection-background-color: {p['primary']}; outline: 0; }}

QTextBrowser#paper, QPlainTextEdit#paper, QTextEdit#paper {{ background: {p['paper']}; color: {p['paper_text']}; border: 1px solid {p['border']};
    border-radius: 12px; padding: 10px; selection-background-color: {p['primary']}; selection-color: white; }}
QPlainTextEdit#editor {{ background: {p['surface2']}; border: 1px solid {p['border']}; border-radius: 12px; padding: 8px; font-family: {MONO_STACK}; }}

QTableView, QTableWidget, QListWidget {{ background: {p['surface']}; alternate-background-color: {p['surface']}; border: 1px solid {p['border']}; border-radius: 12px;
    gridline-color: transparent; selection-background-color: {p['sel']}; selection-color: {p['text']}; outline: 0; }}
QTableView::item, QTableWidget::item, QListWidget::item {{ padding: 5px 8px; border: none; }}
QTableView::item:selected, QTableWidget::item:selected, QListWidget::item:selected {{ background: {p['sel']}; color: {p['text']}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{ background: {p['surface2']}; color: {p['muted']}; border: none; border-bottom: 1px solid {p['border']}; padding: 8px 10px; font-weight: 700; }}
QTableCornerButton::section {{ background: {p['surface2']}; border: none; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 5px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: {p['primary']}; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p['border']}; border-radius: 5px; min-width: 36px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QProgressBar {{ background: {p['surface2']}; border: none; border-radius: 6px; height: 12px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ border-radius: 6px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {p['primary']}, stop:1 {p['gold']}); }}

QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 8px; }}
QSplitter::handle:vertical {{ height: 8px; }}
QMenu {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 12px; padding: 6px; }}
QMenu::item {{ padding: 8px 22px 8px 12px; border-radius: 8px; }}
QMenu::item:selected {{ background: {p['primary']}; color: white; }}
QMenu::separator {{ height: 1px; background: {p['border']}; margin: 6px 8px; }}
QCheckBox {{ spacing: 8px; }}
QGraphicsView {{ border: 1px solid {p['border']}; border-radius: 12px; background: {p['bg2']}; }}
QStatusBar {{ background: {p['bg2']}; color: {p['muted']}; }}
"""


def sev_color(name):
    return QColor(SEV.get(name, "#62B4FF"))


_cur = {"p": THEMES["Royal Night"], "name": "Royal Night"}


def pal():
    return _cur["p"]


def set_pal(name):
    _cur["p"] = THEMES[name]; _cur["name"] = name
    return _cur["p"]


CLASSIC_SEV = {"Critical": "#B42318", "Major": "#B54708", "Minor": "#8A6D00", "Info": "#1D5FA8"}


def use_classic():
    """Switch the whole application to the flat navy-on-white look."""
    SEV.update(CLASSIC_SEV); SEV_SOFT.update(CLASSIC_SEV)
    return set_pal("Classic")


def qss_classic(p, scale=1.0):
    """Base stylesheet plus flat, square, single-accent overrides."""
    n = p["primary"]
    return qss(p, scale) + f"""
QFrame#card, QFrame#cardflat, QFrame#hero {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 3px; }}
QFrame#drop {{ background: {p['surface']}; border: 1.5px dashed {p['border']}; border-radius: 4px; }}
QFrame#drop[hover="true"] {{ border-color: {n}; background: {p['sel']}; }}
QFrame#drop[filled="true"] {{ border: 1.5px solid {n}; }}
QFrame#topbar {{ background: {p['surface']}; }}
QFrame#navbar {{ background: {n}; border: none; }}
QFrame#toolbar {{ background: {p['surface']}; border-bottom: 1px solid {p['border']}; }}
QFrame#statusbar {{ background: {p['bg2']}; border-top: 1px solid {p['border']}; }}
QPushButton {{ border-radius: 3px; padding: 6px 12px; background: {p['surface']}; font-weight: 600; }}
QPushButton:hover {{ border-color: {n}; background: {p['sel']}; }}
QPushButton[kind="primary"] {{ background: {n}; border: 1px solid {n}; color: white; border-radius: 3px; padding: 9px 26px; }}
QPushButton[kind="primary"]:hover {{ background: #2A4D7C; }}
QPushButton[kind="gold"] {{ background: {p['sel']}; color: {n}; border: 1px solid {n}; font-weight: 700; }}
QPushButton[kind="gold"]:hover {{ background: #CFDDEE; }}
QPushButton[kind="danger"] {{ color: #B42318; border-color: #B42318; background: {p['surface']}; }}
QPushButton[kind="chip"] {{ border-radius: 3px; padding: 4px 12px; background: {p['surface']}; }}
QPushButton[kind="chip"]:checked {{ background: {n}; border-color: {n}; color: white; }}
QPushButton[kind="tab"] {{ background: transparent; border: none; border-radius: 0; color: #C9D6E8; padding: 0 20px; font-size: {int(14*scale)}px; font-weight: 600; }}
QPushButton[kind="tab"]:hover {{ background: #2C4A74; color: white; }}
QPushButton[kind="tab"]:checked {{ background: {p['bg']}; color: {n}; font-weight: 800; }}
QPushButton[kind="navbtn"] {{ background: transparent; border: 1px solid #5F7AA0; color: white; border-radius: 3px; padding: 5px 12px; }}
QPushButton[kind="navbtn"]:hover {{ background: #2C4A74; }}
QLineEdit, QComboBox, QSpinBox {{ border-radius: 3px; padding: 6px 9px; background: {p['surface']}; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {n}; }}
QTextBrowser#paper, QPlainTextEdit#paper, QTextEdit#paper {{ border-radius: 3px; padding: 8px; background: {p['paper']}; }}
QTableView, QTableWidget, QListWidget {{ border-radius: 3px; background: {p['surface']}; gridline-color: #E6E9ED; }}
QTableView::item:selected {{ background: {p['sel']}; }}
QHeaderView::section {{ background: {p['bg2']}; color: {p['text']}; border-right: 1px solid {p['border']}; border-bottom: 1px solid {p['border']}; font-weight: 700; padding: 6px 8px; }}
QProgressBar {{ border-radius: 3px; background: {p['bg2']}; }}
QProgressBar::chunk {{ border-radius: 3px; background: {n}; }}
QSplitter::handle {{ background: {p['border']}; }}
QSplitter::handle:horizontal {{ width: 5px; }}
QSplitter::handle:vertical {{ height: 5px; }}
QSplitter::handle:hover {{ background: {n}; }}
QGraphicsView {{ border: 1px solid {p['border']}; border-radius: 3px; background: #D5D9DF; }}
QMenu {{ border-radius: 3px; padding: 3px; }} QMenu::item {{ border-radius: 2px; }}
QMenu::item:selected {{ background: {n}; color: white; }}
QToolButton {{ border-radius: 3px; background: {p['surface']}; }}
QLabel[role="title"] {{ font-size: {int(18*scale)}px; }}
QLabel[role="gold"] {{ color: {n}; }}
QLabel#appname {{ color: white; font-size: {int(16*scale)}px; font-weight: 800; letter-spacing: 0.3px; }}
QLabel#navinfo {{ color: #C9D6E8; }}
"""
