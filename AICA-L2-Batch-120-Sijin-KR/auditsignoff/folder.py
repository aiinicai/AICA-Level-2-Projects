"""Scan an engagement folder and guess each file's role. The reviewer can override any guess in the app."""
from __future__ import annotations
import re
from pathlib import Path

ROLES = ["FS pack", "Engagement fact sheet", "Trial balance", "Trade licence", "MOA / AOA", "Other source document (pre-fill)", "Ignore"]
OFFICE = {".docx", ".doc", ".rtf", ".pdf", ".xlsx", ".xls", ".xlsm", ".csv", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
RULES = [  # (role, filename regex, allowed extensions or None)
    ("Engagement fact sheet", r"fact\s*sheet|engagement[_ -]*(fact|info|sheet)", None),
    ("Trial balance", r"trial[_ -]*balance|\btb\b|tb[_ -]", {".xlsx", ".xls", ".xlsm", ".csv"}),
    ("Trade licence", r"licen[cs]e|trade[_ -]*lic|\btl\b", None),
    ("MOA / AOA", r"\bmoa\b|\baoa\b|memorandum|articles[_ -]*of|partnership[_ -]*agreement|shareholder", None),
    ("Other source document (pre-fill)", r"passport|emirates[_ -]*id|\beid\b|incorporation|certificate|board[_ -]*resolution|\bbr\b|poa|power[_ -]*of", None),
    ("FS pack", r"financial[_ -]*statement|\bfs\b|\bafs\b|audited|draft|audit[_ -]*report|accounts", {".docx", ".doc", ".rtf", ".pdf", ".xlsx", ".xls", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}),
]


def scan_folder(folder, max_files=200):
    f = Path(str(folder).strip().strip('"'))
    if not f.is_dir():
        raise ValueError(f"Folder not found: {f}")
    rows = []
    for p in sorted(f.rglob("*")):
        if p.is_file() and p.suffix.lower() in OFFICE and not p.name.startswith(("~$", ".")) and "out" not in p.relative_to(f).parts[:1]:
            rows.append(p)
        if len(rows) >= max_files:
            break
    out = []
    for p in rows:
        role = "Ignore"
        for r, rx, exts in RULES:
            if re.search(rx, p.stem, re.I) and (exts is None or p.suffix.lower() in exts):
                role = r; break
        out.append({"File": str(p.relative_to(f)), "Role": role, "Size KB": round(p.stat().st_size / 1024, 1), "_path": str(p)})
    # if no FS pack was named, the largest Word/PDF that is unclassified is the likely pack - flagged for confirmation
    if not any(o["Role"] == "FS pack" for o in out):
        cand = [o for o in out if o["Role"] == "Ignore" and Path(o["_path"]).suffix.lower() in (".docx", ".doc", ".pdf")]
        if cand:
            max(cand, key=lambda o: o["Size KB"])["Role"] = "FS pack"
    return out


LIQ_ROLES = ["Liquidation tracker", "Board Resolution", "Statement of Affairs", "Liquidator's report", "Trial balance",
             "CT / VAT registration or FTA letter", "Trade licence / MOA", "Ignore"]
LIQ_RULES = [
    ("Liquidation tracker", r"tracker|liquidation[_ -]*(sheet|input|fact)", {".xlsx", ".xls", ".xlsm", ".yaml", ".yml"}),
    ("Board Resolution", r"board[_ -]*res|(?<![a-z])br(?![a-z])|resolution", None),
    ("Statement of Affairs", r"statement[_ -]*of[_ -]*affairs|(?<![a-z])soa(?![a-z])", None),
    ("Liquidator's report", r"liquidat\w*[_ -]*(audit[_ -]*)?report|final[_ -]*report|liquidator", None),
    ("Trial balance", r"trial[_ -]*balance|(?<![a-z])tb(?![a-z])|tb[_ -]", {".xlsx", ".xls", ".xlsm", ".csv"}),
    ("CT / VAT registration or FTA letter", r"(?<![a-z])ct(?![a-z])|corporate[_ -]*tax|(?<![a-z])vat(?![a-z])|(?<![a-z])trn(?![a-z])|(?<![a-z])fta(?![a-z])|emaratax|dereg", None),
    ("Trade licence / MOA", r"licen[cs]e|(?<![a-z])moa(?![a-z])|(?<![a-z])aoa(?![a-z])|memorandum|articles", None),
]


def scan_liq_folder(folder, max_files=200):
    f = Path(str(folder).strip().strip('"'))
    if not f.is_dir():
        raise ValueError(f"Folder not found: {f}")
    out = []
    for p in sorted(f.rglob("*")):
        if p.is_file() and (p.suffix.lower() in OFFICE or p.suffix.lower() in (".yaml", ".yml")) and not p.name.startswith(("~$", ".")):
            role = "Ignore"
            for r, rx, exts in LIQ_RULES:
                if re.search(rx, p.stem, re.I) and (exts is None or p.suffix.lower() in exts):
                    role = r; break
            out.append({"File": str(p.relative_to(f)), "Role": role, "Size KB": round(p.stat().st_size / 1024, 1), "_path": str(p)})
        if len(out) >= max_files:
            break
    return out
