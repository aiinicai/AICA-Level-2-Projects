"""
Shared style constants for the desktop GUI.

Visual language mirrors the AI Studio-generated React UI: dark sidebar,
neutral slate background, data-dense tables, minimal decoration — a
professional audit-tool look rather than a consumer app.
"""

FONT_FAMILY = "Segoe UI, Arial, sans-serif"
FONT_FAMILY_MONO = "Consolas, 'Courier New', monospace"

COLOR_BG_MAIN = "#0f172a"
COLOR_BG_PANEL = "#1e293b"
COLOR_BG_PANEL_ALT = "#273449"
COLOR_SIDEBAR_BG = "#0b1220"
COLOR_BORDER = "#334155"
COLOR_TEXT_PRIMARY = "#e2e8f0"
COLOR_TEXT_SECONDARY = "#94a3b8"
COLOR_TEXT_MUTED = "#64748b"
COLOR_ACCENT = "#3b82f6"
COLOR_ACCENT_HOVER = "#2563eb"
COLOR_SUCCESS = "#22c55e"
COLOR_SUCCESS_BG = "#052e16"
COLOR_WARNING = "#f59e0b"
COLOR_WARNING_BG = "#451a03"
COLOR_ERROR = "#ef4444"
COLOR_ERROR_BG = "#450a0a"
COLOR_DISABLED = "#475569"

THEMES = {
    "Dark": {
        "bg_main": "#0f172a",
        "bg_panel": "#1e293b",
        "bg_panel_alt": "#273449",
        "sidebar_bg": "#0b1220",
        "border": "#334155",
        "text_primary": "#e2e8f0",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "disabled": "#475569",
    },
    "Light": {
        "bg_main": "#f8fafc",
        "bg_panel": "#ffffff",
        "bg_panel_alt": "#f1f5f9",
        "sidebar_bg": "#e2e8f0",
        "border": "#cbd5e1",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "text_muted": "#94a3b8",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "disabled": "#cbd5e1",
    },
    "Navy Blue": {
        "bg_main": "#0a192f",
        "bg_panel": "#112240",
        "bg_panel_alt": "#1d2d50",
        "sidebar_bg": "#020c1b",
        "border": "#233554",
        "text_primary": "#e6f1ff",
        "text_secondary": "#8892b0",
        "text_muted": "#495670",
        "accent": "#64ffda",
        "accent_hover": "#4cd9b0",
        "disabled": "#233554",
    },
    "Sundowner": {
        "bg_main": "#1a1a24",
        "bg_panel": "#242434",
        "bg_panel_alt": "#2e2e42",
        "sidebar_bg": "#12121a",
        "border": "#3d3d56",
        "text_primary": "#eaeaea",
        "text_secondary": "#a0a0b8",
        "text_muted": "#6c6c84",
        "accent": "#ff6b6b",
        "accent_hover": "#ee5253",
        "disabled": "#3d3d56",
    },
}


def get_theme_stylesheet(theme_name: str = "Dark") -> str:
    palette = THEMES.get(theme_name, THEMES["Dark"])
    # If Navy Blue accent is light, dark text on checked nav button
    btn_checked_text = "#0a192f" if theme_name == "Navy Blue" else "white"

    return f"""
QWidget {{
    background-color: {palette['bg_main']};
    color: {palette['text_primary']};
    font-family: {FONT_FAMILY};
    font-size: 13px;
}}

QMainWindow {{
    background-color: {palette['bg_main']};
}}

/* --- Sidebar --- */
QFrame#sidebar {{
    background-color: {palette['sidebar_bg']};
    border-right: 1px solid {palette['border']};
}}

QPushButton#navButton {{
    background-color: transparent;
    color: {palette['text_secondary']};
    border: none;
    text-align: left;
    padding: 12px 16px;
    font-size: 13px;
    border-radius: 6px;
    margin: 2px 8px;
}}

QPushButton#navButton:hover {{
    background-color: {palette['bg_panel']};
    color: {palette['text_primary']};
}}

QPushButton#navButton:checked {{
    background-color: {palette['accent']};
    color: {btn_checked_text};
    font-weight: 600;
}}

QPushButton#navButtonDisabled {{
    background-color: transparent;
    color: {palette['disabled']};
    border: none;
    text-align: left;
    padding: 12px 16px;
    font-size: 13px;
    border-radius: 6px;
    margin: 2px 8px;
}}

/* --- Status bar --- */
QFrame#statusBar {{
    background-color: {palette['bg_panel']};
    border-top: 1px solid {palette['border']};
}}

QLabel#statusLabel {{
    color: {palette['text_secondary']};
    font-size: 11px;
}}

/* --- Cards / panels --- */
QFrame#card {{
    background-color: {palette['bg_panel']};
    border: 1px solid {palette['border']};
    border-radius: 8px;
}}

QLabel#screenTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {palette['text_primary']};
}}

QLabel#screenSubtitle {{
    font-size: 12px;
    color: {palette['text_secondary']};
}}

QLabel#sectionHeader {{
    font-size: 13px;
    font-weight: 600;
    color: {palette['text_primary']};
    padding-top: 4px;
}}

/* --- Buttons --- */
QPushButton#primaryButton {{
    background-color: {palette['accent']};
    color: {btn_checked_text};
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#primaryButton:hover {{
    background-color: {palette['accent_hover']};
}}

QPushButton#primaryButton:disabled {{
    background-color: {palette['disabled']};
    color: {palette['text_muted']};
}}

QPushButton#secondaryButton {{
    background-color: transparent;
    color: {palette['text_primary']};
    border: 1px solid {palette['border']};
    border-radius: 6px;
    padding: 9px 18px;
    font-size: 13px;
}}

QPushButton#secondaryButton:hover {{
    background-color: {palette['bg_panel_alt']};
}}

/* --- Tables --- */
QTableWidget {{
    background-color: {palette['bg_panel']};
    alternate-background-color: {palette['bg_panel_alt']};
    gridline-color: {palette['border']};
    border: 1px solid {palette['border']};
    border-radius: 6px;
    selection-background-color: {palette['accent']};
    selection-color: {btn_checked_text};
}}

QHeaderView::section {{
    background-color: {palette['sidebar_bg']};
    color: {palette['text_secondary']};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {palette['border']};
    font-weight: 600;
    font-size: 11px;
}}

QTableWidget::item {{
    padding: 4px 8px;
}}

/* --- Inputs --- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {palette['bg_panel_alt']};
    color: {palette['text_primary']};
    border: 1px solid {palette['border']};
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 13px;
}}

QComboBox::drop-down {{
    border: none;
}}

QComboBox QAbstractItemView {{
    background-color: {palette['bg_panel_alt']};
    color: {palette['text_primary']};
    selection-background-color: {palette['accent']};
    selection-color: {btn_checked_text};
}}

/* --- Tabs --- */
QTabWidget::pane {{
    border: 1px solid {palette['border']};
    border-radius: 6px;
    background-color: {palette['bg_panel']};
}}

QTabBar::tab {{
    background-color: transparent;
    color: {palette['text_secondary']};
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:selected {{
    background-color: {palette['bg_panel']};
    color: {palette['text_primary']};
    font-weight: 600;
    border-bottom: 2px solid {palette['accent']};
}}

/* --- Scroll areas --- */
QScrollArea {{
    border: none;
}}

QScrollBar:vertical {{
    background: {palette['bg_main']};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {palette['border']};
    border-radius: 5px;
    min-height: 20px;
}}

/* --- Progress bar --- */
QProgressBar {{
    background-color: {palette['bg_panel_alt']};
    border: 1px solid {palette['border']};
    border-radius: 4px;
    text-align: center;
    color: {palette['text_primary']};
}}
QProgressBar::chunk {{
    background-color: {palette['accent']};
    border-radius: 4px;
}}

/* --- Drop zone --- */
QFrame#dropZone {{
    background-color: {palette['bg_panel_alt']};
    border: 2px dashed {palette['border']};
    border-radius: 8px;
}}

QFrame#dropZone[dragActive="true"] {{
    border: 2px dashed {palette['accent']};
    background-color: {palette['bg_panel']};
}}
"""


APP_STYLESHEET = get_theme_stylesheet("Dark")


def status_pill_style(kind: str) -> str:
    """kind: 'ok' | 'warning' | 'error' | 'pending'"""
    mapping = {
        "ok": (COLOR_SUCCESS, COLOR_SUCCESS_BG),
        "warning": (COLOR_WARNING, COLOR_WARNING_BG),
        "error": (COLOR_ERROR, COLOR_ERROR_BG),
        "pending": (COLOR_TEXT_MUTED, COLOR_BG_PANEL_ALT),
    }
    fg, bg = mapping.get(kind, mapping["pending"])
    return f"color: {fg}; background-color: {bg}; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;"

