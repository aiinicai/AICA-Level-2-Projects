"""Third, separate method. tests/excel_check.xlsx values every fund and share with plain Excel formulas.
This test fills its As-on date for all 12 dates, lets LibreOffice calculate it, and compares the Excel total
with the Python engine. (The dashboard itself is tied to the Python engine by test_dashboard_numbers.py.)
Needs LibreOffice (soffice). On a laptop with Excel, open tests/excel_check.xlsx, type a date and compare by eye.
"""
import csv
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import make_excel_check as M  # noqa: E402
from app import portfolio as P  # noqa: E402


def main():
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    db = P.load(ROOT / "db_dummy")
    ons = sorted({r["date"] for r in P.read(ROOT / "db_dummy" / "prices.csv")})
    tmp = Path(tempfile.mkdtemp())
    worst = 0
    for o in ons:
        f = tmp / f"c_{o}.xlsx"
        M.main(out=f, asof=o)
        subprocess.run([exe, "--headless", "--convert-to", "csv", "--outdir", str(tmp), str(f)], capture_output=True, timeout=180)
        xl = int(list(csv.reader(open(tmp / f"c_{o}.csv")))[4][1].replace(",", ""))
        py = round(sum(x["value"] for x in P.lines(db, date.fromisoformat(o)) if x["cls"] in ("Mutual funds", "Equity shares")))
        worst = max(worst, abs(xl - py))
        assert abs(xl - py) <= 1, (o, xl, py)
    print(f"  Excel formulas = Python engine on {len(ons)} dates, largest difference INR {worst}")
    print("ALL PASS")


if __name__ == "__main__":
    main()
