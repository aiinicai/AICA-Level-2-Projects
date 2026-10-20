"""Colour palette and fonts. Tuples are (light-mode, dark-mode) colours."""

import sys

NAVY = "#0B1F3A"
NAVY_2 = "#16305A"
PURPLE = "#4B2E83"
PURPLE_HOVER = "#5E3BA0"
GOLD = "#C9A227"
GOLD_HOVER = "#B08D1E"
WHITE = "#FFFFFF"
DANGER = "#B3261E"
DANGER_HOVER = "#8F1E18"
SUCCESS = "#1E7B4F"
WARNING = ("#9A6700", "#F2C14E")

# Navy buttons need a lighter shade in dark mode to stay visible on dark cards.
BTN_NAVY = (NAVY, "#2B3F6B")
BTN_NAVY_HOVER = (NAVY_2, "#36508A")

BG = ("#EEF0F7", "#0D1322")
CARD = ("#FFFFFF", "#161F36")
CARD_BORDER = ("#D9DCEA", "#26314F")
TEXT = ("#1B1F2A", "#E8EAF2")
MUTED = ("#5B6275", "#9AA3B8")
ENTRY_BG = ("#F7F8FC", "#0F1729")

# Colours for the rich-text results view (plain tk.Text needs explicit values).
TEXTVIEW = {
    "Light": {"bg": "#FFFFFF", "fg": "#1B1F2A", "h1": NAVY, "h2": NAVY, "h3": PURPLE, "quote": "#4A4F5E",
              "court": "#1E7B3A", "ai": "#C62828", "uncertain": "#9A6700", "select": "#D8CCF0", "muted": "#6B7285"},
    "Dark": {"bg": "#111A2E", "fg": "#E8EAF2", "h1": GOLD, "h2": "#F0D27A", "h3": "#B9A2F0", "quote": "#B8BFD0",
             "court": "#6FD3A0", "ai": "#FF8A80", "uncertain": "#F2C14E", "select": "#3B2E63", "muted": "#9AA3B8"},
}

if sys.platform.startswith("win"):
    FONT_FAMILY = "Segoe UI"
elif sys.platform == "darwin":
    FONT_FAMILY = "Helvetica Neue"
else:
    FONT_FAMILY = "DejaVu Sans"
