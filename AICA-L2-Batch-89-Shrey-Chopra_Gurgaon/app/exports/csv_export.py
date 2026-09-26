"""
csv_export.py
--------------
Flat CSV export — for pasting into another workbook, loading into a BI
tool, or archiving in a flat-file audit trail.
"""

from __future__ import annotations

import io
import pandas as pd


def build_csv(run: dict) -> bytes:
    rows = list(run["rows"].values())
    data = []
    for r in rows:
        d = r["data"]
        data.append({
            "entity": d["entity"],
            "category": d["category"],
            "line_item": d["line_item"],
            "prior_amount": d["prior_amount"],
            "current_amount": d["current_amount"],
            "variance_usd": d["variance_usd"],
            "variance_pct": d["variance_pct"],
            "is_material": d["is_material"],
            "severity": d.get("severity", "none"),
            "review_status": r["status"],
            "reviewed_by": r["reviewer"] or "",
            "ai_generated_commentary_reference_only": r["ai_commentary"],
            "controller_final_commentary": r["controller_commentary"],
        })
    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")
