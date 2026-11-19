

# ===========================================================================
# SECTION 6 - LOCAL DATABASE
# ---------------------------------------------------------------------------
# A plain JSON file in the user's application-data folder.  Clients hold
# financial years; each year carries its own audit type and period basis;
# every generation run is recorded against the year.
# ===========================================================================

def app_data_dir():
    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(root, "BalanceConfirmationGenerator")
    elif sys.platform == "darwin":
        folder = os.path.expanduser(
            "~/Library/Application Support/BalanceConfirmationGenerator")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser(
            "~/.local/share")
        folder = os.path.join(root, "BalanceConfirmationGenerator")
    os.makedirs(folder, exist_ok=True)
    return folder


DB_PATH = os.path.join(app_data_dir(), "database.json")
DB_VERSION = 3


def new_id():
    return uuid.uuid4().hex[:12]


def blank_db():
    return {
        "version": DB_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "clients": [],
        "runs": [],
        "replies": [],
        "audit_status": [],      # follow-up records, one for a request
        "settings": {
            "firm_name": "Ankit Soni and Associates",
            "firm_designation": "Statutory Auditor",
            "partner_name": "",
            "last_audit_type": "Statutory Audit",
            "letterhead_note": True,
            "letter_date": "",
            "theme": "dark",
            "auditors": [],
            "default_currency": "INR",
            "variance_tolerance": 1.0,
            "reminder_days": [15, 30, 45],
            # the always-on Gmail bridge: the web-app URL published by the
            # Apps Script, and when it was last read
            "letterhead_space_cm": 0.0,
            "bridge_feed_url": "",
            "bridge_last_sync": "",
            "bridge_sync_on_start": True,
            "last_client_id": None,
            "last_fy_id": None,
            "output_folder": "",
            "mail": {
                "provider": "Gmail / Google Workspace",
                "host": "smtp.gmail.com",
                "port": 587,
                "security": "starttls",
                "username": "",
                "sender": "",
                "sender_name": "",
                "remember_password": False,
                "subject": DEFAULT_SUBJECT,
                "body": DEFAULT_BODY,
                "cc_team": True,
                "reply_to_team": True,
                "delay_ms": 1500,
                "attach_mode": "pdf",
            },
        },
    }


def normalise_db(data):
    """Accept any earlier shape and bring it up to the current version."""
    db = blank_db()
    if isinstance(data, dict):
        db["clients"] = data.get("clients") or []
        db["runs"] = data.get("runs") or []
        db["replies"] = data.get("replies") or []
        db["audit_status"] = data.get("audit_status") or []
        settings = data.get("settings") or {}
        mail = dict(db["settings"]["mail"])
        mail.update(settings.get("mail") or {})
        db["settings"].update(settings)
        db["settings"]["mail"] = mail
    db["settings"].setdefault("auditors", [])

    for client in db["clients"]:
        client.setdefault("id", new_id())
        # the letter is signed by the client's own officer
        client.setdefault("signatory_name", "")
        client.setdefault("signatory_designation", "Director / CFO")
        client.setdefault("created_at", datetime.now().isoformat(
            timespec="seconds"))
        client.setdefault("financial_years", client.pop("financialYears", []))
        for year in client["financial_years"]:
            year.setdefault("id", new_id())
            year.setdefault("year", "")
            year.setdefault("year_end", year.pop("yearEnd", ""))
            # v1 -> v2: audit type and period basis did not exist
            year.setdefault("audit_type", "Statutory Audit")
            year.setdefault("audit_type_other", "")
            if year.get("basis") != "period":
                year["basis"] = "year"
            year.setdefault("period_start", "")
            year.setdefault("period_end", "")
    # v1 -> v2: refresh the stock sentence that hard-coded "statutory audit"
    legacy = ("We are conducting the statutory audit of {client} for the year "
              "ended {date}.")
    body = db["settings"]["mail"].get("body") or ""
    if legacy in body:
        db["settings"]["mail"]["body"] = body.replace(
            legacy, "We are conducting the {audittype} of {client} {period}.")
    # the covering e-mail now says the attached letter is the client's own
    legacy_body = ("Please find attached our balance confirmation request in "
                   "respect of the {category} balance")
    if legacy_body in (db["settings"]["mail"].get("body") or ""):
        db["settings"]["mail"]["body"] = DEFAULT_BODY
        db["settings"]["mail"]["subject"] = DEFAULT_SUBJECT
    # the stock subject now carries the reference code; a subject the
    # auditor wrote themselves is left exactly as it is
    if db["settings"]["mail"].get("subject") == LEGACY_SUBJECT:
        db["settings"]["mail"]["subject"] = DEFAULT_SUBJECT
    db["version"] = DB_VERSION
    return db


def letter_date(db):
    """The date printed at the top of the letter; today unless overridden."""
    saved = db["settings"].get("letter_date")
    return saved if (saved and to_date(saved)) else date.today().isoformat()


def load_db():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as handle:
                return normalise_db(json.load(handle)), None
        except Exception as exc:
            return blank_db(), str(exc)
    return blank_db(), None


def save_db(db):
    """Write through a temporary file so a crash cannot truncate the data."""
    try:
        temp = DB_PATH + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(db, handle, indent=2, ensure_ascii=False)
        os.replace(temp, DB_PATH)
        return True, None
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------- financial year helpers
def fy_as_at(year):
    """The date every letter confirms balances as on."""
    if not year:
        return ""
    return (year.get("period_end") or "") if year.get("basis") == "period" \
        else (year.get("year_end") or "")


def fy_basis_label(year):
    return "Period end" if (year and year.get("basis") == "period") \
        else "Year end"


def fy_audit_type(year):
    return (year or {}).get("audit_type") or "Statutory Audit"


def fy_audit_ok(year):
    if not year:
        return False
    if fy_audit_type(year) != "Other":
        return True
    return bool(str(year.get("audit_type_other") or "").strip())


def fy_span_text(year):
    return period_label(year.get("basis"), fy_as_at(year),
                        year.get("period_start")) if year else ""


# ===========================================================================
# SECTION 7 - APPEARANCE
# ---------------------------------------------------------------------------
# One olive-green identity in two modes.  Every colour used anywhere in the
# interface is a key in T, so switching mode re-reads the same keys and the
# whole window repaints - there are no colours hard-coded further down.
# ===========================================================================

THEMES = {
    "dark": {
        "name": "dark",
        "window":    "#14170F",   # deepest olive-charcoal
        "surface":   "#1C2014",   # cards and panels
        "raised":    "#252A19",   # inputs, buttons, table rows
        "raised2":   "#2E3420",   # hover
        "line":      "#39402A",
        "line_soft": "#49512F",
        "text":      "#E7EADA",
        "text_soft": "#B3B99F",
        "text_mute": "#959C7E",
        # depth: every raised surface runs light-to-dark, is lit along its
        # top edge and shaded along its bottom one, and casts a shadow
        "card_hi": "#262B1A", "card_lo": "#1A1E12",
        "bevel_hi": "#4B5334", "bevel_lo": "#090B06",
        "btn_hi": "#353C24", "btn_lo": "#20251A",
        "btn_hover_hi": "#3F472B", "btn_hover_lo": "#272D1C",
        "accent_top": "#9BB158", "accent_bot": "#7F9142",
        "accent_edge": "#46521F",
        "well": "#12150D", "well_edge": "#070804",
        "shadow_rgba": (0, 0, 0, 165),
        "accent":      "#7F9142",   # olive
        "accent_hi":   "#93A851",   # olive, lighter
        "accent_deep": "#56642C",
        "accent_text": "#14170F",   # deep ink on olive: 5.2:1
        "on_accent_soft": "#C7D79A",
        "panel_tint": "#20250F",    # selected navigation row
        "ok":    "#8FBF5F", "ok_bg":   "#1E2A12", "ok_line":   "#4C6B28",
        "warn":  "#D9B356", "warn_bg": "#2E2812", "warn_line": "#6E5C22",
        "err":   "#D98A6E", "err_bg":  "#2E1A14", "err_line":  "#70392A",
        "info":  "#8FB3C9", "info_bg": "#15222A", "info_line": "#2F4F60",
        "paper":      "#FBFAF4",   # the letter preview is always paper-white
        "paper_ink":  "#1C1A17",
        "paper_line": "#C9C6B4",
        "shadow": "rgba(0,0,0,.45)",
    },
    "light": {
        "name": "light",
        "window":    "#F4F4EC",
        "surface":   "#FFFFFF",
        "raised":    "#FBFBF5",
        "raised2":   "#F0F1E4",
        "line":      "#DCDCCB",
        "line_soft": "#C7C8B2",
        "text":      "#23281A",
        "text_soft": "#5A6049",
        "text_mute": "#626950",
        "card_hi": "#FFFFFF", "card_lo": "#F0F1E6",
        "bevel_hi": "#FFFFFF", "bevel_lo": "#B4B79C",
        "btn_hi": "#FFFFFF", "btn_lo": "#E4E6D3",
        "btn_hover_hi": "#FFFFFF", "btn_hover_lo": "#D9DCC4",
        "accent_top": "#687D37", "accent_bot": "#4F6027",
        "accent_edge": "#2F3B15",
        "well": "#FFFFFF", "well_edge": "#A9AC90",
        "shadow_rgba": (70, 76, 44, 80),
        "accent":      "#5F7232",
        "accent_hi":   "#71873C",
        "accent_deep": "#44531F",
        "accent_text": "#FFFFFF",
        "on_accent_soft": "#3C4A1C",
        "panel_tint": "#E8EDD6",
        "ok":    "#3F6B1F", "ok_bg":   "#EBF3DF", "ok_line":   "#A9C285",
        "warn":  "#7E610F", "warn_bg": "#FAF1D9", "warn_line": "#D9BE78",
        "err":   "#9B3F28", "err_bg":  "#FAE7E1", "err_line":  "#D9A694",
        "info":  "#2F5A74", "info_bg": "#E6F0F6", "info_line": "#9DC0D4",
        "paper":      "#FFFFFF",
        "paper_ink":  "#1C1A17",
        "paper_line": "#D8D6C8",
        "shadow": "rgba(60,64,40,.16)",
    },
}

# the live palette; apply_theme() swaps its contents in place so that every
# module-level reference stays valid
T = dict(THEMES["dark"])


def set_theme(name):
    T.clear()
    T.update(THEMES.get(name, THEMES["dark"]))
    return T


def is_dark():
    return T.get("name") == "dark"


def style_sheet():
    """Build the whole style sheet from the active palette."""
    tokens = dict(T)
    tokens["card_grad"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                           "stop:0 %(card_hi)s, stop:1 %(card_lo)s)" % T)
    tokens["btn_grad"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                          "stop:0 %(btn_hi)s, stop:1 %(btn_lo)s)" % T)
    tokens["btn_hover"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                           "stop:0 %(btn_hover_hi)s, stop:1 %(btn_hover_lo)s)"
                           % T)
    tokens["btn_down"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                          "stop:0 %(btn_lo)s, stop:1 %(btn_hi)s)" % T)
    tokens["accent_grad"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                             "stop:0 %(accent_top)s, stop:1 %(accent_bot)s)"
                             % T)
    tokens["accent_down"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                             "stop:0 %(accent_bot)s, stop:1 %(accent_top)s)"
                             % T)
    tokens["side_grad"] = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                           "stop:0 %(card_hi)s, stop:1 %(card_lo)s)" % T)
    return """
/* Only the window paints a background.  Anything not styled here stays
   transparent and shows the surface it sits on, so a label never appears as
   a coloured rectangle on a card. */
QWidget { color: %(text)s; font-size: 13px; }
QMainWindow, QDialog, QScrollArea, #TopBar { background: %(window)s; }

/* ---------- sidebar ---------- */
#Sidebar { background: %(side_grad)s; border-right: 2px solid %(bevel_lo)s; }
#BrandMark { color: %(text)s; font-size: 17px; font-weight: 600; }
#BrandTag  { color: %(text_mute)s; font-size: 10px; letter-spacing: 1.4px; }
#NavList { background: transparent; border: 0; outline: 0; }
#NavList::item { color: %(text_soft)s; padding: 9px 10px; margin: 2px 7px;
                 border: 1px solid transparent; border-radius: 9px; }
#NavList::item:hover { background: %(btn_grad)s; color: %(text)s;
                       border: 1px solid %(line_soft)s;
                       border-bottom: 2px solid %(bevel_lo)s; }
#NavList::item:selected { background: %(accent_grad)s; color: %(accent_text)s;
                          border: 1px solid %(accent_top)s;
                          border-bottom: 3px solid %(accent_edge)s; }
#SideFoot { color: %(text_mute)s; font-size: 11px; }

/* ---------- header ---------- */
#TopBar { border-bottom: 2px solid %(bevel_lo)s; }
#PageTitle { color: %(text)s; font-size: 21px; font-weight: 600; }
#PageSub { color: %(text_mute)s; font-size: 12px; }
QLabel[chip="neutral"], QLabel[chip="green"], QLabel[chip="blue"],
QLabel[chip="warn"], QLabel[chip="brass"] {
    border-radius: 11px; padding: 4px 11px; font-size: 11px;
    background: %(raised)s; border: 1px solid %(line_soft)s;
    color: %(text_soft)s; }
QLabel[chip="green"] { background: %(ok_bg)s; border-color: %(ok_line)s;
                       color: %(ok)s; }
QLabel[chip="blue"]  { background: %(info_bg)s; border-color: %(info_line)s;
                       color: %(info)s; }
QLabel[chip="warn"]  { background: %(warn_bg)s; border-color: %(warn_line)s;
                       color: %(warn)s; }
QLabel[chip="brass"] { background: %(ok_bg)s; border-color: %(accent)s;
                       color: %(ok)s; }

/* ---------- cards ---------- */
/* a card is a slab: lit along the top, shaded underneath, and lifted off the
   page by the drop shadow the helper gives it */
#CardDark, #CardLight { background: %(card_grad)s;
                        border: 1px solid %(line)s;
                        border-top: 1px solid %(bevel_hi)s;
                        border-bottom: 3px solid %(bevel_lo)s;
                        border-radius: 14px; }
#CardHeadDark, #CardHeadLight { color: %(text)s; font-size: 15px;
                                font-weight: 600; }
#HintDark, #HintLight { color: %(text_mute)s; font-size: 11.5px; }
#FieldLabelDark, #FieldLabelLight { color: %(text_mute)s; font-size: 10px;
    letter-spacing: 1.1px; font-weight: 600; }
#Rule, #RuleLight { background: %(line)s; max-height: 1px; border: 0; }

/* ---------- inputs ---------- */
/* fields are wells: sunk into the card, darker along the top lip */
QLineEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
    background: %(well)s; border: 1px solid %(line_soft)s;
    border-top: 2px solid %(well_edge)s;
    border-radius: 8px; padding: 6px 8px; color: %(text)s;
    selection-background-color: %(accent)s;
    selection-color: %(accent_text)s; }
QComboBox, QDateEdit { padding-right: 22px; }
QSpinBox, QDoubleSpinBox { padding-right: 18px; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid %(accent_hi)s;
    border-top: 2px solid %(accent_hi)s; }
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled,
QPlainTextEdit:disabled { color: %(text_mute)s; background: %(raised2)s; }
QComboBox QAbstractItemView { background: %(surface)s; color: %(text)s;
    border: 1px solid %(line_soft)s;
    selection-background-color: %(accent)s;
    selection-color: %(accent_text)s; outline: 0; }

/* ---------- buttons ---------- */
/* a button is a key: it stands 3px proud of the card and travels down
   when pressed */
QPushButton { background: %(btn_grad)s; border: 1px solid %(line_soft)s;
    border-top: 1px solid %(bevel_hi)s;
    border-bottom: 3px solid %(bevel_lo)s;
    border-radius: 9px; padding: 6px 14px; color: %(text)s;
    font-weight: 600; }
QPushButton:hover { background: %(btn_hover)s; border-color: %(accent)s;
    border-top-color: %(bevel_hi)s; border-bottom-color: %(bevel_lo)s; }
QPushButton:pressed { background: %(btn_down)s;
    border-top: 3px solid %(bevel_lo)s;
    border-bottom: 1px solid %(line_soft)s; }
QPushButton:disabled { color: %(text_mute)s; border: 1px solid %(line)s;
    border-bottom: 2px solid %(line)s; background: %(raised2)s; }
QPushButton[kind="primary"] { background: %(accent_grad)s;
    border: 1px solid %(accent_top)s;
    border-bottom: 3px solid %(accent_edge)s; color: %(accent_text)s; }
QPushButton[kind="primary"]:hover { background: %(accent_top)s;
    border-color: %(accent_top)s; border-bottom-color: %(accent_edge)s; }
QPushButton[kind="primary"]:pressed { background: %(accent_down)s;
    border-top: 3px solid %(accent_edge)s;
    border-bottom: 1px solid %(accent_top)s; }
QPushButton[kind="primary"]:disabled { background: %(raised2)s;
    color: %(text_mute)s; border: 1px solid %(line)s;
    border-bottom: 2px solid %(line)s; }
QPushButton[kind="blue"] { background: %(info_bg)s; border-color: %(info_line)s;
    border-bottom: 3px solid %(info_line)s; color: %(info)s; }
QPushButton[kind="blue"]:hover { border-color: %(info)s; }
QPushButton[kind="brass"] { background: %(accent_grad)s;
    border: 1px solid %(accent_top)s;
    border-bottom: 3px solid %(accent_edge)s; color: %(accent_text)s; }
QPushButton[kind="brass"]:hover { background: %(accent_top)s; }
QPushButton[kind="brass"]:pressed { background: %(accent_down)s;
    border-top: 3px solid %(accent_edge)s;
    border-bottom: 1px solid %(accent_top)s; }
QPushButton[kind="danger"] { background: transparent;
    border-color: %(err_line)s; color: %(err)s; }
QPushButton[kind="danger"]:hover { background: %(err_bg)s; }
QPushButton[kind="small"] { padding: 4px 9px; font-size: 12px; }
#ThemeToggle { padding: 5px 13px; font-size: 12px;
               border-radius: 14px; background: %(btn_grad)s;
               border: 1px solid %(line_soft)s;
               border-top: 1px solid %(bevel_hi)s;
               border-bottom: 3px solid %(bevel_lo)s; color: %(text_soft)s; }
#ThemeToggle:hover { border-color: %(accent)s; color: %(text)s; }

/* ---------- tables ---------- */
QTableWidget { background: %(well)s;
    alternate-background-color: %(raised2)s;
    gridline-color: %(line)s; border: 1px solid %(line)s; border-radius: 8px;
    color: %(text)s; selection-background-color: %(panel_tint)s;
    selection-color: %(text)s; }
QTableWidget::item { padding: 5px 6px; }
QHeaderView::section { background: %(btn_grad)s; color: %(text_soft)s;
    border: 0; border-bottom: 2px solid %(bevel_lo)s;
    border-right: 1px solid %(line)s; padding: 7px 6px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.6px; }
QTableCornerButton::section { background: %(raised2)s; border: 0; }

/* ---------- misc ---------- */
QProgressBar { background: %(well)s; border: 1px solid %(line_soft)s;
    border-top: 2px solid %(well_edge)s;
    border-radius: 7px; height: 13px; text-align: center;
    color: %(text_soft)s; font-size: 11px; }
QProgressBar::chunk { background: %(accent_grad)s; border-radius: 5px; }
QCheckBox { spacing: 7px; }
QScrollArea { border: 0; }
QScrollBar:vertical { background: %(surface)s; width: 11px; margin: 0; }
QScrollBar::handle:vertical { background: %(line_soft)s; border-radius: 5px;
                              min-height: 30px; }
QScrollBar::handle:vertical:hover { background: %(accent)s; }
QScrollBar:horizontal { background: %(surface)s; height: 11px; }
QScrollBar::handle:horizontal { background: %(line_soft)s; border-radius: 5px;
                                min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: %(accent)s; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QToolTip { background: %(surface)s; color: %(text)s;
           border: 1px solid %(line_soft)s; padding: 5px; }
#StatCard { background: %(card_grad)s; border: 1px solid %(line)s;
            border-top: 1px solid %(bevel_hi)s;
            border-bottom: 3px solid %(bevel_lo)s; border-radius: 12px; }
#StatKey { color: %(text_mute)s; font-size: 10px; letter-spacing: 1px;
           font-weight: 600; }
#StatValue { color: %(text)s; font-size: 24px; font-weight: 600; }
#StatMeta { color: %(text_mute)s; font-size: 11px; }
#NoticeGreen, #NoticeBlue, #NoticeWarn, #NoticeRed {
    border-radius: 7px; padding: 10px 12px; font-size: 12px; }
#NoticeGreen { background: %(ok_bg)s; border: 1px solid %(ok_line)s;
               color: %(ok)s; }
#NoticeBlue  { background: %(info_bg)s; border: 1px solid %(info_line)s;
               color: %(info)s; }
#NoticeWarn  { background: %(warn_bg)s; border: 1px solid %(warn_line)s;
               color: %(warn)s; }
#NoticeRed   { background: %(err_bg)s; border: 1px solid %(err_line)s;
               color: %(err)s; }
QWidget#Pane { background: transparent; }
""" % tokens


def qt_palette():
    """Keep the pieces Qt draws itself (calendar pop-ups, menus) in step."""
    palette = QPalette()
    pairs = [
        (QPalette.ColorRole.Window, T["window"]),
        (QPalette.ColorRole.WindowText, T["text"]),
        (QPalette.ColorRole.Base, T["raised"]),
        (QPalette.ColorRole.AlternateBase, T["raised2"]),
        (QPalette.ColorRole.Text, T["text"]),
        (QPalette.ColorRole.Button, T["raised"]),
        (QPalette.ColorRole.ButtonText, T["text"]),
        (QPalette.ColorRole.Highlight, T["accent"]),
        (QPalette.ColorRole.HighlightedText, T["accent_text"]),
        (QPalette.ColorRole.ToolTipBase, T["surface"]),
        (QPalette.ColorRole.ToolTipText, T["text"]),
        (QPalette.ColorRole.PlaceholderText, T["text_mute"]),
    ]
    for role, colour in pairs:
        palette.setColor(role, QColor(colour))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,
                     QColor(T["text_mute"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,
                     QColor(T["text_mute"]))
    return palette


def shadow_colour():
    return QColor(*T["shadow_rgba"])


def elevate(widget, blur=26, drop=7):
    """Lift a surface off the page with a soft shadow beneath it."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, drop)
    effect.setColor(shadow_colour())
    widget.setGraphicsEffect(effect)
    return widget


def apply_theme(app, name):
    """Switch mode and repaint everything that is already on screen."""
    set_theme(name)
    app.setPalette(qt_palette())
    app.setStyleSheet(style_sheet())
    for widget in app.allWidgets():
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        effect = widget.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            effect.setColor(shadow_colour())     # shadows follow the theme
        widget.update()


# ------------------------------------------------------- small UI helpers
class FlowLayout(QLayout):
    """A layout that wraps its items onto the next line when space runs out.
    Used for the status chips so they never get clipped on a small screen."""

    def __init__(self, spacing=7):
        super().__init__()
        self._items = []
        self._space = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._layout(0, 0, width, apply=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._layout(rect.x(), rect.y(), rect.width(), apply=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _layout(self, left, top, width, apply):
        x, y, line_height = left, top, 0
        for item in self._items:
            hint = item.sizeHint()
            if x > left and x + hint.width() > left + width:
                x = left
                y += line_height + self._space
                line_height = 0
            if apply:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x += hint.width() + self._space
            line_height = max(line_height, hint.height())
        return y + line_height - top


def stamp_text(value):
    """An ISO timestamp as '05 Nov 2026, 10:31' for display in a table."""
    text = str(value or "")
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        return text[:19].replace("T", " ")
    return "%d %s %d, %02d:%02d" % (when.day, MONTHS[when.month - 1][:3],
                                    when.year, when.hour, when.minute)


def pane():
    """A see-through container, so grouping widgets never paints a dark box."""
    holder = QWidget()
    holder.setObjectName("Pane")
    return holder


def h_line(light=False):
    line = QFrame()
    line.setObjectName("RuleLight" if light else "Rule")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


def field_label(text, light=False):
    label = QLabel(text.upper())
    label.setObjectName("FieldLabelLight" if light else "FieldLabelDark")
    return label


def notice(kind, text):
    """kind: green | blue | warn | red"""
    label = QLabel(text)
    label.setObjectName("Notice" + kind.capitalize())
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    return label


def button(text, kind=None, small=False, tooltip=None):
    btn = QPushButton(text)
    if kind:
        btn.setProperty("kind", kind)
    if small:
        btn.setProperty("kind", kind or "small")
        btn.setStyleSheet("padding: 2px 9px; font-size: 12px; "
                          "border-bottom-width: 2px; border-radius: 7px;")
        # a stylesheet overrides the style's own metrics, so reserve the width
        # the label actually needs or the caption is clipped inside a table
        btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(text) + 24)
        btn.setFixedHeight(26)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def card(title, hint="", light=False):
    """Returns (frame, body layout, header layout) for a titled panel."""
    frame = QFrame()
    frame.setObjectName("CardLight" if light else "CardDark")
    # a card may grow, but is never squeezed below the height of its contents
    frame.setSizePolicy(QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Minimum)
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(16, 13, 16, 15)
    outer.setSpacing(10)
    header = QHBoxLayout()
    header.setSpacing(10)
    heading = QLabel(title)
    heading.setObjectName("CardHeadLight" if light else "CardHeadDark")
    header.addWidget(heading)
    if hint:
        hint_label = QLabel(hint)
        hint_label.setObjectName("HintLight" if light else "HintDark")
        header.addWidget(hint_label)
    header.addStretch(1)
    outer.addLayout(header)
    body = QVBoxLayout()
    body.setSpacing(10)
    outer.addLayout(body)
    elevate(frame)
    return frame, body, header


def stat_card(key, value, meta="", accent=None):
    frame = QFrame()
    frame.setObjectName("StatCard")
    # the accent stripe is resolved now, not at import, so a theme switch
    # rebuilds these cards in the new palette
    frame.setStyleSheet(
        "#StatCard { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        "stop:0 %s, stop:1 %s); border: 1px solid %s; "
        "border-top: 1px solid %s; border-bottom: 3px solid %s; "
        "border-radius: 12px; border-left: 4px solid %s; }"
        % (T["card_hi"], T["card_lo"], T["line"], T["bevel_hi"],
           T["bevel_lo"], accent or T["accent"]))
    elevate(frame, blur=18, drop=5)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 11, 14, 12)
    layout.setSpacing(1)
    key_label = QLabel(key.upper())
    key_label.setObjectName("StatKey")
    key_label.setWordWrap(True)
    value_label = QLabel(str(value))
    value_label.setObjectName("StatValue")
    layout.addWidget(key_label)
    layout.addWidget(value_label)
    if meta:
        meta_label = QLabel(meta)
        meta_label.setObjectName("StatMeta")
        meta_label.setWordWrap(True)
        layout.addWidget(meta_label)
    frame.setMinimumWidth(152)
    frame.setMinimumHeight(86)
    frame.setSizePolicy(QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Minimum)
    return frame


def table(headers, stretch_column=None):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.verticalHeader().setVisible(False)
    widget.setAlternatingRowColors(True)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.setWordWrap(False)
    # room for the editors and drop-downs that sit inside the rows
    widget.verticalHeader().setDefaultSectionSize(36)
    header = widget.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    if stretch_column is None:
        header.setStretchLastSection(True)
    else:
        # one named column takes up the slack; stretching the last one as
        # well would push a trailing button column off the edge
        header.setStretchLastSection(False)
        header.setSectionResizeMode(stretch_column,
                                    QHeaderView.ResizeMode.Stretch)
    widget.setMinimumHeight(180)
    return widget


def fit_widget_columns(widget, columns):
    """resizeColumnsToContents ignores cell widgets, so size those columns by
    what the embedded buttons actually need."""
    for column in columns:
        needed = 0
        for row in range(widget.rowCount()):
            holder = widget.cellWidget(row, column)
            if holder is not None:
                needed = max(needed, holder.sizeHint().width())
        if needed:
            widget.setColumnWidth(column, needed + 12)


def cell(text, align_right=False, color=None, bold=False):
    value = "" if text is None else str(text)
    item = QTableWidgetItem(value)
    if len(value) > 14:
        item.setToolTip(value)          # the full text, when a column is tight
    if align_right:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                              | Qt.AlignmentFlag.AlignVCenter)
    else:
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft
                              | Qt.AlignmentFlag.AlignVCenter)
    if color:
        item.setForeground(QColor(color))
    if bold:
        font = item.font()
        font.setBold(True)
        item.setFont(font)
    return item
