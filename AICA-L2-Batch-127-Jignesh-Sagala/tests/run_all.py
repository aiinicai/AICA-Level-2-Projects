"""Runs every test and writes docs/test_result.md. Usage:  py tests/run_all.py"""
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = [
    ("test_cdsl.py", "Fund and demat statement reader (CAS)", None),
    ("test_zcn.py", "Broker contract note reader", None),
    ("test_bank.py", "Bank statement readers (two layouts)", None),
    ("test_zledger.py", "Broker funds ledger reader", None),
    ("test_samples.py", "Made-up sample statements (samples/): locked, holder BusyMe, readers pass, wrong password refused", None),
    ("test_open_position.py", "Opening-cost back-solve (average-cost rule)", None),
    ("test_prices_fetch.py", "Price script: parsers, plan, safe append (offline)", None),
    ("test_dashboard_numbers.py", "Dashboard engine (JavaScript) = Python engine, plus hand cases", "node"),
    ("test_life.py", "Calendar, premiums, SIP and rent (JavaScript) = Python, plus hand cases", "node"),
    ("test_excel_check.py", "Excel formulas (separate method) = dashboard value of funds and shares, 12 dates", "soffice"),
    ("test_dashboard_ui.py", "Dashboard on screen: displayed numbers = Python engine, filters, CSV export, SIP, property, insurance, calendar, DTAA tab, phone width", "playwright"),
]


def have(tool):
    if tool in ("node", "soffice"):
        return shutil.which(tool) is not None or (tool == "soffice" and shutil.which("libreoffice") is not None)
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def main():
    rows, bad = [], 0
    for f, what, need in TESTS:
        if need and not have(need):
            rows.append((f, what, "SKIPPED", f"{need} not installed"))
            continue
        r = subprocess.run([sys.executable, str(ROOT / "tests" / f)], capture_output=True, text=True, cwd=ROOT)
        ok = r.returncode == 0 and "ALL PASS" in r.stdout.upper().replace("ALL PASSED", "ALL PASS")
        last = [x for x in r.stdout.strip().splitlines() if x.strip()][-1:] or [""]
        rows.append((f, what, "PASS" if ok else "FAIL", last[0].strip() if ok else (r.stderr.strip().splitlines() or r.stdout.strip().splitlines() or [""])[-1]))
        bad += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {f}")
    md = [f"# Test result", "", f"Run: {datetime.now():%d %b %Y %H:%M}. Python {platform.python_version()} on {platform.system()}.", "",
          "| Test file | What it checks | Result |", "|---|---|---|"] + [f"| `{f}` | {w} | **{res}**{(' (' + n + ')') if res == 'SKIPPED' else ''} |" for f, w, res, n in rows]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "test_result.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("FAILED" if bad else "ALL TESTS PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
