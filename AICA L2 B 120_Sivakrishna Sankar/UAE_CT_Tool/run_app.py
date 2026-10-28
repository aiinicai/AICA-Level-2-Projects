"""Launcher: checks the Python version and required packages, offers to install what is missing, then starts the GUI.
Run:  python run_app.py          (or double-click run_app.bat on Windows after running setup_windows.bat once)"""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED = {"PySide6": "PySide6", "openpyxl": "openpyxl", "pandas": "pandas", "docx": "python-docx", "pdfplumber": "pdfplumber", "pypdfium2": "pypdfium2",
            "reportlab": "reportlab", "pytesseract": "pytesseract", "PIL": "pillow", "xlrd": "xlrd"}
OPTIONAL = {"pytesseract", "xlrd", "reportlab"}


def check():
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required (found %s.%s). Install it from python.org and run this again." % sys.version_info[:2])
        return False
    missing = [pip for mod, pip in REQUIRED.items() if importlib.util.find_spec(mod) is None]
    hard = [m for m in missing if m not in {REQUIRED[o] for o in OPTIONAL}]
    if missing:
        print("Missing packages:", ", ".join(missing))
        ans = input("Install them now with pip? [Y/n] ").strip().lower() if sys.stdin.isatty() else "y"
        if ans in ("", "y", "yes"):
            code = subprocess.call([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])
            if code != 0:
                print("pip install failed. Fix the error above (or install the packages manually) and try again.")
                return False
        elif hard:
            return False
    return True


def selftest() -> int:
    try:
        import json
        import tempfile
        from ct_tool.resources import resource_path
        from ct_tool.models import CONFIG_DIR
        from ct_tool.extract import parse_tb
        from ct_tool.fx import default_settings
        from ct_tool.pipeline import run_analysis
        from ct_tool.project import Project
        from ct_tool.service import export_all

        # 1. Load ct_tool/config/*.json
        cfg_files = list(CONFIG_DIR.glob("*.json"))
        if not cfg_files:
            raise RuntimeError(f"No config JSON files found in {CONFIG_DIR}")
        for cfg in cfg_files:
            with open(cfg, "r", encoding="utf-8") as f:
                json.load(f)

        # 2. Sample data paths
        tb_path = resource_path("sample_data", "marjan", "Marjan_Gulf_Trading_TB_31Dec2025.xlsx")
        answers_path = resource_path("sample_data", "marjan", "Marjan_answers.json")

        if not tb_path.exists():
            raise FileNotFoundError(f"TB sample file not found: {tb_path}")
        if not answers_path.exists():
            raise FileNotFoundError(f"Answers sample file not found: {answers_path}")

        # 3. Parse TB with currency AED and load answers
        p = Project(name="Selftest Marjan")
        p.tb = parse_tb(str(tb_path), currency="AED")
        p.fx = default_settings("AED", "", "")
        p.fx_confirmed = True
        with open(answers_path, "r", encoding="utf-8") as f:
            p.answers = json.load(f)

        # 4. Run analysis
        an = run_analysis(p)

        # 5. Check tax payable with nothing confirmed is 235350.00
        payable = an.comp.payable
        expected_tax = 235350.00
        if round(abs(payable - expected_tax), 2) > 0.01:
            raise AssertionError(f"Expected tax payable {expected_tax:.2f}, got {payable:.2f}")

        # 6. Export all outputs to a temp folder and verify Excel, Word and project files exist
        with tempfile.TemporaryDirectory() as temp_dir:
            res = export_all(an, temp_dir)
            client_file = Path(res.get("client", ""))
            review_file = Path(res.get("review", ""))
            report_file = Path(res.get("report", ""))
            proj_file = Path(res.get("project", ""))

            if not (client_file.exists() and client_file.stat().st_size > 0):
                raise FileNotFoundError(f"Excel computation workbook missing: {client_file}")
            if not (review_file.exists() and review_file.stat().st_size > 0):
                raise FileNotFoundError(f"Excel review workbook missing: {review_file}")
            if not (report_file.exists() and report_file.stat().st_size > 0):
                raise FileNotFoundError(f"Word report missing: {report_file}")
            if not (proj_file.exists() and proj_file.stat().st_size > 0):
                raise FileNotFoundError(f"Project file missing: {proj_file}")

        print("SELFTEST OK")
        return 0
    except Exception as e:
        print(f"SELFTEST ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    if "--selftest" in sys.argv:
        if sys.platform == "win32":
            import ctypes
            try:
                ctypes.windll.kernel32.AttachConsole(-1)
            except Exception:
                pass
            if sys.stdout is None:
                try:
                    sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
                except Exception:
                    pass
            if sys.stderr is None:
                try:
                    sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
                except Exception:
                    pass
        sys.exit(selftest())

    if not getattr(sys, "frozen", False):
        if not check():
            input("Press Enter to close...") if sys.stdin.isatty() else None
            sys.exit(1)

    from ct_tool.gui.main_window import main
    sys.exit(main())
