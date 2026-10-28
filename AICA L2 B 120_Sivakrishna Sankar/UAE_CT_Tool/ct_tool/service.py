"""High-level operations shared by the CLI and the GUI: export all deliverables, load/prepare projects."""
from __future__ import annotations

import re
from pathlib import Path

from .excel_out import ClientWorkbook
from .pipeline import Analysis, run_analysis
from .project import Project
from .review_xlsx import ReviewWorkbook
from .word_out import build_report
from .resources import resource_path

ROOT = resource_path()
BUNDLED_TEMPLATE = resource_path("templates", "Elitser_Holding_CT_Computation_FY_2025_TEMPLATE.xlsx")
if not BUNDLED_TEMPLATE.exists():
    BUNDLED_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "Elitser_Holding_CT_Computation_FY_2025_TEMPLATE.xlsx"



_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_name(s: str) -> str:
    """A file-name stem that is valid on Windows: letters (including Arabic and other scripts), digits, '.', '-', '_'; no reserved device names."""
    s = re.sub(r"[^\w.-]+", "_", (s or "").strip())
    s = s[:60].strip("._ ") or "Entity"
    return "_" + s if s.upper() in _RESERVED else s


def default_template(p: Project) -> str:
    t = p.settings.template_path
    if t and Path(t).exists():
        return t
    return str(BUNDLED_TEMPLATE)


def export_all(an: Analysis, out_dir: str, which=("client", "review", "report", "project")) -> dict:
    """Write the deliverables into out_dir (created if needed). Source files are never touched. Returns {kind: path}."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = f"{safe_name(an.entity)}_{(an.period_end or 'period')[:4]}"
    res = {}
    p = an.project
    if "client" in which:
        path = out / f"{base}_CT_Computation.xlsx"
        cw = ClientWorkbook(an, default_template(p))
        cw.build(str(path))
        res["client"] = str(path)
        p.log("Export", f"Client computation workbook written: {path.name}")
    if "review" in which:
        path = out / f"{base}_Review_Workbook.xlsx"
        ReviewWorkbook(an).build(str(path))
        res["review"] = str(path)
        p.log("Export", f"Review workbook written: {path.name}")
    if "report" in which:
        path = out / f"{base}_Tax_Risk_Report.docx"
        build_report(an, str(path), p.settings.letterhead_path)
        res["report"] = str(path)
        p.log("Export", f"Word report written: {path.name}")
    if "project" in which:
        path = out / f"{base}.ctproj"
        p.save(str(path))
        res["project"] = str(path)
    return res
