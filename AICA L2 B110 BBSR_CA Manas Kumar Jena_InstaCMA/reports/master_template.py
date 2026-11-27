"""
Built-in master CMA format.

prepare_master(src, dst) turns a filled CMA workbook in the firm's format
into the clean master that ships inside the app:

  * the bank format sheets (Instructions, FORM-II, FORM-III, FORM-IV, FORM-VI,
    ABF, CHECK, RATIOS, CRA-DATA, ANALYSIS) are kept exactly - layout,
    formulas, colours, conditional formats, print settings;
  * the client-specific link cells (FORM-II / FORM-III rows that read the
    P&L and Balance Sheet) and the year headers are cleared;
  * the working sheets (Profit and Loss, Balance Sheet, Term Loan, CMA Tests,
    DSCR, Projection Basis) are removed - the app rebuilds them per client
    with the same names, positions and Cambria styling.

The "Update master format" button in Settings (admin password) calls this
function, so a new bank format can be loaded offline.
"""
import os
import sys

import openpyxl

FORMAT_SHEETS = ["FORM-II", "FORM-III", "FORM-IV", "FORM-VI", "ABF", "CHECK", "RATIOS", "CRA-DATA", "ANALYSIS"]
WORKING_SHEETS = ["Profit and Loss", "Balance Sheet", "Term Loan", "CMA Tests", "DSCR", "Projection Basis"]
SHEET_ORDER = ["Instructions"] + FORMAT_SHEETS + WORKING_SHEETS
YEAR_COLS = "EFGHIJKLMN"          # 10 columns in the format; the app uses up to 7

# rows of FORM-II / FORM-III that the app writes for every year column
FORM2_LINK_ROWS = [12, 24, 28, 29, 30, 31, 40, 43, 46, 51, 64, 68]
FORM2_FIRST_COL_ONLY = [38]
FORM3_LINK_ROWS = [15, 20, 25, 27, 32, 41, 45, 58, 59, 81, 87, 105, 108, 109, 110, 115, 116, 124, 130]
FORM3_FIRST_COL_ONLY = [50]


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


MASTER_PATH = resource_path("templates", "cma_master.xlsx")


def user_master_path():
    from config.settings import SETTINGS_DIR
    return os.path.join(SETTINGS_DIR, "cma_master.xlsx")


def master_path():
    """A master loaded through Settings > Update master format wins over the built-in one."""
    p = user_master_path()
    return p if os.path.exists(p) else MASTER_PATH


def prepare_master(src, dst=MASTER_PATH):
    wb = openpyxl.load_workbook(src)
    missing = [s for s in FORMAT_SHEETS if s not in wb.sheetnames]
    if missing:
        raise ValueError("The file is not in the CMA format: sheet(s) missing: " + ", ".join(missing))
    for name in WORKING_SHEETS:
        if name in wb.sheetnames:
            del wb[name]
    f2, f3 = wb["FORM-II"], wb["FORM-III"]
    f2["C4"] = None
    for col in YEAR_COLS:
        for r in (8, 9):
            f2["%s%d" % (col, r)] = None
        f2["%s10" % col] = 12
        for r in FORM2_LINK_ROWS:
            f2["%s%d" % (col, r)] = None
        for r in FORM3_LINK_ROWS:
            f3["%s%d" % (col, r)] = None
    for r in FORM2_FIRST_COL_ONLY:
        f2["E%d" % r] = None
    for r in FORM3_FIRST_COL_ONLY:
        f3["E%d" % r] = None
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    wb.save(dst)
    return dst


if __name__ == "__main__":
    print(prepare_master(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else MASTER_PATH))
