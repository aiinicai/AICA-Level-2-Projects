"""Script to verify 1-year forward-looking calendar and capture theme screenshots."""
import os
import sys
from datetime import date
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

# Configure Windows font directory for crisp rendering
os.environ['QT_QPA_FONTDIR'] = r'C:\Windows\Fonts'
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication
from app.database.store import Database
from app.services.bootstrap import initialize
from app.database.events import EventRepository
from app.services.demo import load_demo
from app.ui.theme import get_style, DARK_STYLE, LIGHT_STYLE
from app.ui.window import MainWindow

out_dir = Path("screenshots_verification")
out_dir.mkdir(exist_ok=True)

test_db_path = Path("test_verify.db")
if test_db_path.exists():
    test_db_path.unlink()

db = Database(str(test_db_path))
initialize(db)

# Load demo with anchor date Nov 13, 2026
anchor = date(2026, 11, 13)
result = load_demo(db, anchor)
print(f"Loaded demo events: {result.inserted} inserted, {result.updated} updated")

repo = EventRepository(db)
all_events, total = repo.search("", {}, limit=10000)
print(f"Total events in database: {total}")

# Breakdown by month
from collections import defaultdict
months = defaultdict(int)
for e in all_events:
    time_str = e.get("scheduled_at") or e.get("published_at") or e.get("effective_at") or e.get("deadline_at") or e.get("record_date") or e.get("ex_date")
    if time_str:
        ym = time_str[:7]
        months[ym] += 1

print("\n--- Event Distribution Across 1-Year Horizon ---")
for ym in sorted(months.keys()):
    print(f"  {ym}: {months[ym]} events")

app = QApplication.instance() or QApplication([sys.argv[0], "-platform", "offscreen"])

# 1. Dark Theme Screenshot
app.setStyleSheet(DARK_STYLE)
window = MainWindow(db, background=False)
window.apply_theme("Dark Navy")
window.resize(1600, 940)
window.show()

# Dashboard view
window.navigation.setCurrentRow(0)
QApplication.processEvents()
window.grab().save(str(out_dir / "01_dark_dashboard.png"))

# Month Calendar view (Nov 2026)
window.navigation.setCurrentRow(1)
window.view.setCurrentText("Month")
QApplication.processEvents()
window.grab().save(str(out_dir / "02_dark_month_nov2026.png"))

# Shift forward 2 months to Jan 2027 (Q3 FY27 earnings season!)
window.shift_date(1)
window.shift_date(1)
QApplication.processEvents()
window.grab().save(str(out_dir / "03_dark_month_jan2027.png"))

# Shift to Feb 2027 (Union Budget + RBI MPC)
window.shift_date(1)
QApplication.processEvents()
window.grab().save(str(out_dir / "04_dark_month_feb2027.png"))

# 2. Light Theme Screenshot
window.apply_theme("Clean Light")
QApplication.processEvents()
window.grab().save(str(out_dir / "05_light_month_feb2027.png"))

# Switch back to Dashboard in Light theme
window.navigation.setCurrentRow(0)
window.view.setCurrentText("Agenda")
QApplication.processEvents()
window.grab().save(str(out_dir / "06_light_dashboard.png"))

# Corporate view in Light theme
window.navigation.setCurrentRow(3)
QApplication.processEvents()
window.grab().save(str(out_dir / "07_light_corporate.png"))

# Regulatory view in Light theme
window.navigation.setCurrentRow(4)
QApplication.processEvents()
window.grab().save(str(out_dir / "08_light_regulatory.png"))

print("\nAll screenshots captured successfully in screenshots_verification/")
window.close()
if test_db_path.exists():
    test_db_path.unlink()
