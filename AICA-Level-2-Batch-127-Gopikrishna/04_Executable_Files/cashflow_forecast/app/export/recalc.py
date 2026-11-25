"""Formula check: recalculate an exported workbook in headless LibreOffice and compare with the app.

LibreOffice runs locally with its own private profile (instance/lo_profile), set to always
recalculate Excel files on load and never to check for updates, so nothing leaves the PC.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openpyxl import load_workbook

TOLERANCE = Decimal("0.0005")          # half of the smallest OMR unit (3 decimals)

_PROFILE_XCU = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="ODFRecalcMode" oor:op="fuse"><value>0</value></prop></item>
<item oor:path="/org.openoffice.Office.Jobs/Jobs/org.openoffice.Office.Jobs:Job['UpdateCheck']/Arguments"><prop oor:name="AutoCheckEnabled" oor:op="fuse"><value>false</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="FirstRun" oor:op="fuse"><value>false</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="CollectUsageInformation" oor:op="fuse"><value>false</value></prop></item>
</oor:items>
"""


class RecalcUnavailable(RuntimeError):
    """LibreOffice is not installed / not found."""


class RecalcError(RuntimeError):
    """LibreOffice ran but did not produce a recalculated file."""


def find_soffice(configured: Path | None = None) -> Path | None:
    if configured:
        return configured if configured.exists() else None
    candidates = []
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                 r"C:\Program Files", r"C:\Program Files (x86)"):
        if base:
            candidates += [Path(base) / "LibreOffice" / "program" / "soffice.com",
                           Path(base) / "LibreOffice" / "program" / "soffice.exe"]
    candidates += [Path("/usr/bin/soffice"), Path("/usr/lib/libreoffice/program/soffice"),
                   Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")]
    for c in candidates:
        if c.exists():
            return c
    for name in ("soffice.com", "soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def recalculate(src: Path, outdir: Path, *, soffice: Path | None, profile_dir: Path, timeout: int = 180) -> Path:
    """Open ``src`` in LibreOffice (recalculating every formula) and save a copy in ``outdir``."""
    if soffice is None:
        raise RecalcUnavailable("LibreOffice is not installed on the app server, so the formula check cannot "
                                "run and the export is blocked. Ask the Admin to install LibreOffice "
                                "(or set CFF_SOFFICE_PATH).")
    outdir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "user").mkdir(parents=True, exist_ok=True)
    (profile_dir / "user" / "registrymodifications.xcu").write_text(_PROFILE_XCU, encoding="utf-8")
    cmd = [str(soffice), "--headless", "--invisible", "--norestore", "--nologo", "--nodefault", "--nolockcheck",
           f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
           "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", str(outdir), str(src)]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise RecalcError(f"LibreOffice did not finish within {timeout} seconds.")
    except OSError as exc:
        raise RecalcUnavailable(f"LibreOffice could not be started: {exc}")
    out = outdir / src.name
    if not out.exists():
        msg = (proc.stderr or proc.stdout or "").strip()[-400:]
        raise RecalcError(f"LibreOffice did not produce a recalculated file (exit {proc.returncode}). {msg}")
    return out


def _as_decimal(v) -> Decimal | None:
    if v is None:
        return Decimal(0)
    if isinstance(v, bool):
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def compare(path: Path, expected: dict[tuple[str, str], object], tolerance: Decimal = TOLERANCE,
            label_sheet: str = "Forecast", label_col: str = "A", header_row: int = 5) -> list[dict]:
    """Every cell where the recalculated workbook differs from what the app calculated."""
    wb = load_workbook(path, data_only=True, read_only=False)
    diffs = []
    for (sheet, cell), exp in expected.items():
        if sheet not in wb.sheetnames:
            diffs.append({"sheet": sheet, "cell": cell, "item": "sheet missing", "app": str(exp), "excel": None})
            continue
        ws = wb[sheet]
        got = ws[cell].value
        if isinstance(exp, str):
            ok = got is not None and str(got) == exp
        else:
            g = _as_decimal(got)
            ok = g is not None and abs(g - Decimal(exp)) <= tolerance
        if not ok:
            item = ""
            if sheet == label_sheet:
                row = "".join(ch for ch in cell if ch.isdigit())
                col = "".join(ch for ch in cell if ch.isalpha())
                item = f"{ws[f'{label_col}{row}'].value} / {ws[f'{col}{header_row}'].value}"
            diffs.append({"sheet": sheet, "cell": cell, "item": item, "app": str(exp),
                          "excel": None if got is None else str(got)})
    wb.close()
    return diffs
