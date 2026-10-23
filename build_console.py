"""
build_console.py  -  regenerate the single-file console build (gst_console.py).

Merges the modules (portal_config, reports, compliance, issues, ewaybill,
dashboard, portal) into one file, sandwiched between a fixed import header and
the bespoke console application. The header and the console-application tail are
lifted verbatim from the existing gst_console.py, so this stays in sync with any
hand-written console code.

Run:  python build_console.py
Writes: ../gst_console.py   (one directory up, next to the other deliverables)
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "gst_console.py"

ORDER = ["portal_config", "reports", "compliance", "issues", "ewaybill", "dashboard", "portal"]
BANNERS = {
    "portal_config": "PORTAL CONFIG",
    "reports": "REPORTS",
    "compliance": "COMPLIANCE",
    "issues": "ISSUES & RISK",
    "ewaybill": "E-WAY BILL",
    "dashboard": "HTML DASHBOARD",
    "portal": "PORTAL WORKER",
}

# top-level imports that the consolidated header already provides, or that refer to
# sibling modules now living in the same namespace -> stripped during merge.
_STRIP_TOP = re.compile(
    r"^(from __future__ import|"
    r"import (compliance|reports|issues|ewaybill|dashboard|portal_config)\b|"
    r"import (json|re|html|sys|os|queue|time|traceback|zipfile|base64|io|threading)\b|"
    r"from (datetime|pathlib|portal_config|reports|playwright)\b|"
    r"import pandas as pd)"
)


def strip_imports(src: str) -> str:
    """Remove only COLUMN-0 imports covered by the header / siblings. Indented imports
    inside functions (openpyxl, math) are kept."""
    out, skip_paren = [], False
    for line in src.splitlines():
        if skip_paren:                       # inside a multi-line  from X import ( ... )
            if ")" in line:
                skip_paren = False
            continue
        if line[:1] not in (" ", "\t") and _STRIP_TOP.match(line):
            if "(" in line and ")" not in line:   # multi-line  from X import ( ... )
                skip_paren = True
            continue
        out.append(line)
    return "\n".join(out).strip("\n")


def slice_existing(path: Path):
    """Pull the fixed header (everything before the first section banner) and the tail
    (from the module-alias line to EOF) out of the current gst_console.py."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    head_end = next(i for i, l in enumerate(lines) if l.startswith("#  PORTAL CONFIG")) - 1
    # banner is 3 lines: ===, "#  PORTAL CONFIG", === ; step back over the opening ===
    while head_end > 0 and lines[head_end].startswith("# ===="):
        head_end -= 1
    tail_start = next(i for i, l in enumerate(lines)
                      if l.startswith("# module aliases") or "sys.modules[__name__]" in l)
    header = "\n".join(lines[:head_end + 1]).rstrip() + "\n"
    tail = "\n".join(lines[tail_start:]).rstrip() + "\n"
    return header, tail


def banner(title: str) -> str:
    bar = "# " + "=" * 85
    return f"\n\n{bar}\n#  {title}\n{bar}\n"


def main():
    header, tail = slice_existing(OUT)
    parts = [header]
    for mod in ORDER:
        body = strip_imports((HERE / f"{mod}.py").read_text(encoding="utf-8"))
        parts.append(banner(BANNERS[mod]))
        parts.append(body + "\n")
    parts.append("\n" + tail)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.read_text(encoding='utf-8').count(chr(10))} lines)")


if __name__ == "__main__":
    main()
