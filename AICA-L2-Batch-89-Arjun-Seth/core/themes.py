# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Appearance: dashboard layouts, light/dark themes and the colour tokens of each combination.

Pure Python (no UI framework, no database). A user picks a LAYOUT (classic / modern / pro) and a THEME
(light / dark); ``palette(layout, theme)`` returns the colours for that combination. Every combination is
checked for readable contrast (``contrast_ratio``), so no text ends up unreadable on its background.
"""
THEMES = {"light": "Light", "dark": "Dark"}
DEFAULT_THEME = "light"

LAYOUTS = {
    "classic": {
        "label": "Classic",
        "description": "Navy sidebar, white cards and coloured KPI accents - the familiar analytics look.",
        "nav": "sidebar",
    },
    "modern": {
        "label": "Modern",
        "description": "Top navigation bar, gradient greeting banner, soft glass cards and ring gauges.",
        "nav": "top",
    },
    "pro": {
        "label": "Pro",
        "description": "Compact control room with glowing accents, ring gauges and a Quick Actions ribbon along the bottom.",
        "nav": "sidebar",
    },
}
DEFAULT_LAYOUT = "classic"


# --------------------------------------------------------------------------- #
# colour maths
# --------------------------------------------------------------------------- #
def _rgb(color: str) -> tuple:
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def luminance(color: str) -> float:
    """Relative luminance (WCAG 2)."""
    channels = []
    for value in _rgb(color):
        v = value / 255.0
        channels.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG contrast ratio between two hex colours: 1 (identical) to 21 (black on white)."""
    a, b = luminance(foreground), luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


# --------------------------------------------------------------------------- #
# palettes
# --------------------------------------------------------------------------- #
# ``bg_css`` / ``surface_css`` are what the page uses (they may be gradients or translucent glass);
# ``bg`` / ``surface`` are the solid colours they resemble, used for contrast checks and charts.
_PALETTES = {
    ("classic", "light"): {
        "bg": "#F5F7FA", "bg_css": "#F5F7FA", "surface": "#FFFFFF", "surface_css": "#FFFFFF", "surface_alt": "#EEF2F8",
        "text": "#1A2233", "muted": "#566175", "border": "#E1E7F0",
        "accent": "#2F5BEA", "accent_text": "#FFFFFF",
        "sidebar_bg": "#0F1B3D", "sidebar_text": "#E6EBF5", "sidebar_hover": "rgba(255,255,255,0.10)",
        "kpi_blue": "#2F80ED", "kpi_green": "#1E9E5A", "kpi_purple": "#7C4DE8", "kpi_orange": "#D9770E",
        "interest": "#D9770E", "principal": "#2F80ED", "bar": "#2F80ED",
        "hero_css": "none", "hero_text": "#FFFFFF", "shadow": "0 1px 3px rgba(15,27,61,0.08)", "radius": "12px", "glow": False,
    },
    ("classic", "dark"): {
        "bg": "#0B1220", "bg_css": "#0B1220", "surface": "#131C2E", "surface_css": "#131C2E", "surface_alt": "#1A2540",
        "text": "#E8EDF7", "muted": "#A3B0C8", "border": "#25324D",
        "accent": "#5B8CFF", "accent_text": "#08122B",
        "sidebar_bg": "#070D1A", "sidebar_text": "#E6EBF5", "sidebar_hover": "rgba(255,255,255,0.10)",
        "kpi_blue": "#4C9AFF", "kpi_green": "#34C48B", "kpi_purple": "#A78BFA", "kpi_orange": "#F5A25D",
        "interest": "#F5A25D", "principal": "#4C9AFF", "bar": "#4C9AFF",
        "hero_css": "none", "hero_text": "#FFFFFF", "shadow": "0 1px 3px rgba(0,0,0,0.5)", "radius": "12px", "glow": False,
    },
    ("modern", "light"): {
        "bg": "#EDEBFB", "bg_css": "linear-gradient(135deg, #EEE8FF 0%, #E3EEFF 100%)",
        "surface": "#F8F7FF", "surface_css": "rgba(255,255,255,0.78)", "surface_alt": "#E8E6F8",
        "text": "#1F2340", "muted": "#5A5F86", "border": "rgba(255,255,255,0.95)",
        "accent": "#5B48DB", "accent_text": "#FFFFFF",
        "sidebar_bg": "#FFFFFF", "sidebar_text": "#1F2340", "sidebar_hover": "rgba(91,72,219,0.10)",
        "kpi_blue": "#4F6FF0", "kpi_green": "#1E9E75", "kpi_purple": "#8E4FE0", "kpi_orange": "#CC6D0A",
        "interest": "#E5566B", "principal": "#4F6FF0", "bar": "#7A6CF0",
        "hero_css": "linear-gradient(90deg, #7B5CF0 0%, #5B8DF0 100%)", "hero_text": "#FFFFFF",
        "shadow": "0 4px 18px rgba(91,72,219,0.12)", "radius": "18px", "glow": False,
    },
    ("modern", "dark"): {
        "bg": "#141131", "bg_css": "linear-gradient(135deg, #171233 0%, #0F1A3A 100%)",
        "surface": "#1F1C45", "surface_css": "rgba(255,255,255,0.07)", "surface_alt": "#27235A",
        "text": "#EDEBFF", "muted": "#B3AFDD", "border": "rgba(255,255,255,0.14)",
        "accent": "#A79BFF", "accent_text": "#170F45",
        "sidebar_bg": "#171233", "sidebar_text": "#EDEBFF", "sidebar_hover": "rgba(167,155,255,0.16)",
        "kpi_blue": "#7FA2FF", "kpi_green": "#4FD1A5", "kpi_purple": "#C39BFF", "kpi_orange": "#F5B062",
        "interest": "#FF8FA0", "principal": "#7FA2FF", "bar": "#A79BFF",
        "hero_css": "linear-gradient(90deg, #5B3FD0 0%, #2F6BE0 100%)", "hero_text": "#FFFFFF",
        "shadow": "0 4px 18px rgba(0,0,0,0.35)", "radius": "18px", "glow": False,
    },
    ("pro", "light"): {
        "bg": "#F1F5F9", "bg_css": "#F1F5F9", "surface": "#FFFFFF", "surface_css": "#FFFFFF", "surface_alt": "#E8EEF5",
        "text": "#0F172A", "muted": "#526075", "border": "#D5DEE9",
        "accent": "#0B7A6D", "accent_text": "#FFFFFF",
        "sidebar_bg": "#0F172A", "sidebar_text": "#E6EDF3", "sidebar_hover": "rgba(45,226,196,0.14)",
        "kpi_blue": "#2563EB", "kpi_green": "#0B8F7F", "kpi_purple": "#B324C9", "kpi_orange": "#C26A08",
        "interest": "#C26A08", "principal": "#0B8F7F", "bar": "#0B8F7F",
        "hero_css": "none", "hero_text": "#FFFFFF", "shadow": "0 1px 2px rgba(15,23,42,0.08)", "radius": "10px", "glow": False,
    },
    ("pro", "dark"): {
        "bg": "#0A0E14", "bg_css": "#0A0E14", "surface": "#11161F", "surface_css": "#11161F", "surface_alt": "#171D29",
        "text": "#E6EDF3", "muted": "#9AA8BA", "border": "#232E3F",
        "accent": "#2DE2C4", "accent_text": "#04211C",
        "sidebar_bg": "#0B1017", "sidebar_text": "#E6EDF3", "sidebar_hover": "rgba(45,226,196,0.14)",
        "kpi_blue": "#4C8DFF", "kpi_green": "#2DE2C4", "kpi_purple": "#E36BF5", "kpi_orange": "#F5B942",
        "interest": "#F5B942", "principal": "#2DE2C4", "bar": "#2DE2C4",
        "hero_css": "none", "hero_text": "#FFFFFF", "shadow": "0 0 0 1px rgba(45,226,196,0.10)", "radius": "10px", "glow": True,
    },
}


def validate_theme(theme) -> str:
    if theme not in THEMES:
        raise ValueError("theme must be one of {}, got {!r}".format(", ".join(THEMES), theme))
    return theme


def validate_layout(layout) -> str:
    if layout not in LAYOUTS:
        raise ValueError("layout must be one of {}, got {!r}".format(", ".join(LAYOUTS), layout))
    return layout


def palette(layout: str = DEFAULT_LAYOUT, theme: str = DEFAULT_THEME) -> dict:
    """The colour tokens for a layout + theme (an unknown value falls back to the default, never an error)."""
    layout = layout if layout in LAYOUTS else DEFAULT_LAYOUT
    theme = theme if theme in THEMES else DEFAULT_THEME
    return dict(_PALETTES[(layout, theme)], layout=layout, theme=theme, nav=LAYOUTS[layout]["nav"], is_dark=theme == "dark")


def all_combinations() -> list:
    return [(layout, theme) for layout in LAYOUTS for theme in THEMES]
