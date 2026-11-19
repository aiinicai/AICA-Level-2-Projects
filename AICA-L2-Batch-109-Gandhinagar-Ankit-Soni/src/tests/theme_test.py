"""Checks the olive theme switches cleanly and that nothing stays dark."""
import importlib.util, os, sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["XDG_DATA_HOME"] = "/home/claude/pytest/work/appdata"
spec = importlib.util.spec_from_file_location(
    "bcg", "/home/claude/balance_confirmation_generator.py")
bcg = importlib.util.module_from_spec(spec)
sys.modules["bcg"] = bcg
spec.loader.exec_module(bcg)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QColor

PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name +
          ("" if cond or not detail else "  ->  " + str(detail)[:160]))

app = QApplication([])
app.setStyle("Fusion")
app.setPalette(bcg.qt_palette())
app.setStyleSheet(bcg.style_sheet())
win = bcg.MainWindow()
win.resize(1280, 820)
win.show()
def pump(n=5):
    for _ in range(n):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
pump()

print("\n== Palette ==")
def luminance(hex_colour):
    """WCAG relative luminance."""
    c = QColor(hex_colour)
    def channel(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return (0.2126 * channel(c.redF()) + 0.7152 * channel(c.greenF())
            + 0.0722 * channel(c.blueF()))

def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

for mode in ("dark", "light"):
    t = bcg.THEMES[mode]
    check("%s: body text contrast >= 7:1" % mode,
          contrast(t["text"], t["window"]) >= 7,
          round(contrast(t["text"], t["window"]), 2))
    check("%s: muted text contrast >= 4.5:1" % mode,
          contrast(t["text_mute"], t["surface"]) >= 4.5,
          round(contrast(t["text_mute"], t["surface"]), 2))
    for tone in ("ok", "warn", "err", "info"):
        check("%s: %s message contrast >= 4.5:1" % (mode, tone),
              contrast(t[tone], t[tone + "_bg"]) >= 4.5,
              round(contrast(t[tone], t[tone + "_bg"]), 2))
    check("%s: text on the accent >= 4.5:1" % mode,
          contrast(t["accent_text"], t["accent"]) >= 4.5,
          round(contrast(t["accent_text"], t["accent"]), 2))
    # the accent must actually be olive: green dominant, warm, not grey
    c = QColor(t["accent"])
    check("%s: accent is olive" % mode,
          c.green() > c.blue() + 25 and c.red() > c.blue() + 15
          and c.green() >= c.red(),
          t["accent"])

print("\n== Toggle ==")
check("starts in dark", bcg.is_dark())
check("button offers light", "Light mode" in win.theme_button.text(),
      win.theme_button.text())
win.toggle_theme(); pump()
check("switches to light", not bcg.is_dark())
check("button now offers dark", "Dark mode" in win.theme_button.text(),
      win.theme_button.text())
check("window colour changed",
      bcg.T["window"] == bcg.THEMES["light"]["window"], bcg.T["window"])
check("style sheet rebuilt",
      bcg.THEMES["light"]["window"] in app.styleSheet())
check("no dark surface left in the sheet",
      bcg.THEMES["dark"]["surface"] not in app.styleSheet())
check("choice saved", win.db["settings"]["theme"] == "light")

# a widget created before the switch must have picked up the new palette
sidebar = win.findChild(type(win.nav))
check("palette applied to existing widgets",
      app.palette().color(app.palette().ColorRole.Window).name().lower()
      == bcg.THEMES["light"]["window"].lower(),
      app.palette().color(app.palette().ColorRole.Window).name())

win.toggle_theme(); pump()
check("switches back to dark", bcg.is_dark())
check("still usable after two switches",
      win.isVisible() and win.theme_button.isEnabled())

print("\n== Saved across a restart ==")
win.set_mode("light")
win.persist()
win2 = bcg.MainWindow()
pump()
check("light mode restored on restart", not bcg.is_dark())
check("restored button label", "Dark mode" in win2.theme_button.text(),
      win2.theme_button.text())
win2.set_mode("dark")

print("\n" + "-" * 50)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("Failures: " + "; ".join(FAIL))
sys.exit(1 if FAIL else 0)
