"""SPEC 12B — Upload Plan.

The validation report is the point of this module. A plan that silently
half-imports is worse than one that is rejected, so every row is either
accepted or rejected with a reason, and four cross-checks run over the whole
file before anything is saved.
"""
from __future__ import annotations

import io
import json
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from app.models import BurnCategory, Plan, PlanLine, Setting
from app.services.common import Ctx, fmt_inr, month_start

TEMPLATE_COLUMNS = ["Month", "Customer Collections", "Other Inflow"] + \
    [f"Outflow — {c}" for c in BurnCategory.ALL] + ["Closing Cash"]

MONTH_FORMATS = ("%b-%y", "%b-%Y", "%B-%y", "%B %Y", "%Y-%m", "%Y-%m-%d",
                 "%d-%m-%Y", "%m/%Y", "%b %y")


def build_template() -> bytes:
    """A workbook with the right columns, twelve pre-filled month labels and a
    notes sheet — so the CFO's team fills in a shape the tool can read."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Plan"

    header_fill = PatternFill("solid", fgColor="1E2761")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    for i, col in enumerate(TEMPLATE_COLUMNS, start=1):
        c = ws.cell(row=1, column=i, value=col)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", wrap_text=True, vertical="center")
        ws.column_dimensions[c.column_letter].width = 22 if i > 1 else 14
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "B2"

    start = month_start(date.today())
    for r in range(12):
        m = start + relativedelta(months=r)
        ws.cell(row=2 + r, column=1, value=m.strftime("%b-%y"))
        for c in range(2, len(TEMPLATE_COLUMNS) + 1):
            ws.cell(row=2 + r, column=c).number_format = '#,##0'

    notes = wb.create_sheet("How to fill this in")
    lines = [
        ("Cash Runway — plan upload template", True),
        ("", False),
        ("One row per month. Amounts in rupees, not lakhs or crores.", False),
        ("Enter outflows as positive numbers — the tool knows they are outflows.", False),
        ("", False),
        ("Month", True),
        ("Any of: Apr-26, April 2026, 2026-04. Months must be consecutive with no gaps.", False),
        ("", False),
        ("Closing Cash", True),
        ("Optional. If you fill it in, the tool checks that", False),
        ("  opening + inflows − outflows = closing  for every month,", False),
        ("and rejects the file if it does not tie. If you leave it blank it is derived.", False),
        ("", False),
        ("Categories", True),
        ("Use the nine columns as they are. Extra columns are ignored and reported;", False),
        ("missing columns are treated as nil and reported.", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        c = notes.cell(row=i, column=1, value=text)
        if bold:
            c.font = Font(bold=True)
    notes.column_dimensions["A"].width = 90

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _parse_month(raw) -> date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return month_start(raw.date())
    if isinstance(raw, date):
        return month_start(raw)
    s = str(raw).strip()
    for fmt in MONTH_FORMATS:
        try:
            return month_start(datetime.strptime(s, fmt).date())
        except ValueError:
            continue
    return None


def _number(raw) -> float | None:
    if raw is None or raw == "":
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).replace(",", "").replace("₹", "").strip()
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


def read_workbook(content: bytes, filename: str) -> tuple[list[str], list[list]]:
    """Returns (header, rows). Accepts .xlsx and .csv."""
    if filename.lower().endswith(".csv"):
        import csv
        text = content.decode("utf-8-sig", errors="replace")
        reader = list(csv.reader(io.StringIO(text)))
        if not reader:
            return [], []
        return [h.strip() for h in reader[0]], reader[1:]

    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(content), data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    return header, [list(r) for r in rows[1:]]


def auto_map(header: list[str]) -> dict[str, int]:
    """Best-guess column mapping. The UI lets a human override every one."""
    mapping: dict[str, int] = {}
    norm = {h.strip().lower(): i for i, h in enumerate(header) if h}

    def find(*needles: str) -> int | None:
        for key, idx in norm.items():
            if all(n in key for n in needles):
                return idx
        return None

    for target, needles in [
        ("month", ("month",)),
        ("inflow_collections", ("collection",)),
        ("inflow_other", ("other", "inflow")),
        ("closing", ("closing",)),
    ]:
        idx = find(*needles)
        if idx is not None:
            mapping[target] = idx
    if "month" not in mapping and header:
        mapping["month"] = 0

    for cat in BurnCategory.ALL:
        idx = find(cat.split()[0].lower())
        if idx is not None and idx not in mapping.values():
            mapping[f"outflow::{cat}"] = idx
    return mapping


def validate(ctx: Ctx, header: list[str], rows: list[list],
             mapping: dict[str, int], opening_cash: float | None) -> dict:
    """The validation report: rows accepted, rows rejected with reason, totals
    check, period continuity, opening cash tie-in."""
    accepted: list[dict] = []
    rejected: list[dict] = []
    month_idx = mapping.get("month", 0)

    for n, raw in enumerate(rows, start=2):
        if raw is None or all(v in (None, "") for v in raw):
            continue
        m = _parse_month(raw[month_idx] if month_idx < len(raw) else None)
        if m is None:
            rejected.append({"row": n, "reason": "Month could not be read",
                             "value": str(raw[month_idx] if month_idx < len(raw) else "")})
            continue

        parsed = {"month": m, "inflow": {}, "outflow": {}, "closing": None}
        bad = None
        for key, idx in mapping.items():
            if key == "month" or idx >= len(raw):
                continue
            v = _number(raw[idx])
            if v is None:
                bad = f"'{header[idx] if idx < len(header) else idx}' is not a number"
                break
            if key.startswith("outflow::"):
                parsed["outflow"][key.split("::", 1)[1]] = abs(v)
            elif key == "inflow_collections":
                parsed["inflow"]["Customer Collections"] = v
            elif key == "inflow_other":
                parsed["inflow"]["Other Inflow"] = v
            elif key == "closing":
                parsed["closing"] = v
        if bad:
            rejected.append({"row": n, "reason": bad, "value": ""})
            continue
        accepted.append(parsed)

    accepted.sort(key=lambda r: r["month"])

    # --- period continuity ---------------------------------------------
    continuity = {"ok": True, "gaps": [], "duplicates": []}
    seen = set()
    for i, r in enumerate(accepted):
        if r["month"] in seen:
            continuity["duplicates"].append(r["month"].strftime("%b-%y"))
            continuity["ok"] = False
        seen.add(r["month"])
        if i:
            expected = accepted[i - 1]["month"] + relativedelta(months=1)
            if r["month"] != expected and r["month"] not in seen or r["month"] > expected:
                if r["month"] != expected:
                    continuity["gaps"].append(
                        f"{accepted[i-1]['month']:%b-%y} → {r['month']:%b-%y}")
                    continuity["ok"] = False

    # --- totals + opening cash tie-in -----------------------------------
    from app.services.cash import position
    opening = opening_cash if opening_cash is not None else position(ctx)["available"]
    running = opening
    totals = {"ok": True, "mismatches": []}
    for r in accepted:
        inflow = sum(r["inflow"].values())
        outflow = sum(r["outflow"].values())
        running += inflow - outflow
        r["derived_closing"] = round(running, 2)
        if r["closing"] is not None and abs(r["closing"] - running) > 1:
            totals["ok"] = False
            totals["mismatches"].append({
                "month": r["month"].strftime("%b-%y"),
                "stated_closing": round(r["closing"], 2),
                "derived_closing": round(running, 2),
                "difference": round(r["closing"] - running, 2),
            })
            running = r["closing"]      # trust the file, but flag it

    unknown_cols = [h for i, h in enumerate(header)
                    if h and i not in mapping.values()]
    missing_cats = [c for c in BurnCategory.ALL if f"outflow::{c}" not in mapping]

    return {
        "accepted": len(accepted),
        "rejected": rejected,
        "rows": [{
            "month": r["month"].isoformat(),
            "label": r["month"].strftime("%b-%y"),
            "inflow": round(sum(r["inflow"].values()), 2),
            "outflow": round(sum(r["outflow"].values()), 2),
            "net": round(sum(r["inflow"].values()) - sum(r["outflow"].values()), 2),
            "stated_closing": round(r["closing"], 2) if r["closing"] is not None else None,
            "derived_closing": r["derived_closing"],
            "by_category": {k: round(v, 2) for k, v in r["outflow"].items()},
        } for r in accepted],
        "continuity": continuity,
        "totals_check": totals,
        "opening_cash": round(opening, 2),
        "opening_cash_source": ("supplied with the upload" if opening_cash is not None
                                else "current available cash from the bank position"),
        "unknown_columns": unknown_cols,
        "missing_categories": missing_cats,
        "period_from": accepted[0]["month"].isoformat() if accepted else None,
        "period_to": accepted[-1]["month"].isoformat() if accepted else None,
        "can_save": bool(accepted) and continuity["ok"],
        "summary": _summary(accepted, rejected, continuity, totals),
        "_parsed": accepted,
    }


def _summary(accepted, rejected, continuity, totals) -> str:
    bits = [f"{len(accepted)} row(s) accepted"]
    if rejected:
        bits.append(f"{len(rejected)} rejected")
    if not continuity["ok"]:
        bits.append("period continuity failed")
    if not totals["ok"]:
        bits.append(f"{len(totals['mismatches'])} closing-cash mismatch(es)")
    if len(bits) == 1:
        return bits[0] + ". The file is clean."
    return ", ".join(bits) + "."


def diff_against_active(ctx: Ctx, parsed: list[dict]) -> dict:
    """Preview with a diff against the active plan (SPEC 12B)."""
    from app.services.variance import active_plan, _plan_monthly

    current = active_plan(ctx)
    old = _plan_monthly(ctx, current)
    rows = []
    for r in parsed:
        m = r["month"]
        o = old.get(m, {})
        new_in = sum(r["inflow"].values())
        new_out = sum(r["outflow"].values())
        rows.append({
            "month": m.isoformat(), "label": m.strftime("%b-%y"),
            "old_inflow": round(o.get("inflow", 0.0), 2) if o else None,
            "new_inflow": round(new_in, 2),
            "inflow_delta": round(new_in - o.get("inflow", 0.0), 2) if o else None,
            "old_outflow": round(o.get("outflow", 0.0), 2) if o else None,
            "new_outflow": round(new_out, 2),
            "outflow_delta": round(new_out - o.get("outflow", 0.0), 2) if o else None,
            "old_closing": round(o.get("closing", 0.0), 2) if o else None,
            "new_closing": r["derived_closing"],
        })
    return {
        "compared_to": ({"id": current.id, "name": current.name, "version": current.version}
                        if current else None),
        "rows": rows,
        "note": ("Compared against the currently active plan." if current
                 else "No active plan to compare against — this will be the first."),
    }


def save_plan(ctx: Ctx, parsed: list[dict], name: str, version: str, note: str | None,
              opening_cash: float, filename: str | None, user_name: str,
              make_active: bool = True) -> Plan:
    from app.services.variance import active_plan

    prior = active_plan(ctx)
    plan = Plan(entity_id=ctx.entity.id, name=name, version=version, note=note,
                uploaded_by=user_name, is_active=make_active, is_locked=False,
                board_approved=False,
                period_from=parsed[0]["month"], period_to=parsed[-1]["month"],
                opening_cash=opening_cash, source_filename=filename,
                supersedes_id=prior.id if prior else None,
                source="upload", created_by=user_name)
    if make_active and prior:
        prior.is_active = False
    ctx.db.add(plan)
    ctx.db.flush()

    for r in parsed:
        for cat, amt in r["inflow"].items():
            ctx.db.add(PlanLine(plan_id=plan.id, month=r["month"], line_type="inflow",
                                category=cat, amount=amt))
        for cat, amt in r["outflow"].items():
            ctx.db.add(PlanLine(plan_id=plan.id, month=r["month"], line_type="outflow",
                                category=cat, amount=amt))
        ctx.db.add(PlanLine(plan_id=plan.id, month=r["month"], line_type="closing",
                            category="Closing Cash",
                            amount=r["closing"] if r["closing"] is not None
                            else r["derived_closing"]))
    ctx.db.flush()
    return plan


# --- saveable column-mapping profiles --------------------------------------
PROFILE_KEY = "plan_mapping_profiles"


def list_profiles(ctx: Ctx) -> dict:
    row = (ctx.db.query(Setting)
           .filter(Setting.entity_id == ctx.entity.id, Setting.key == PROFILE_KEY).first())
    return json.loads(row.value) if row else {}


def save_profile(ctx: Ctx, name: str, mapping: dict, user_name: str) -> dict:
    row = (ctx.db.query(Setting)
           .filter(Setting.entity_id == ctx.entity.id, Setting.key == PROFILE_KEY).first())
    profiles = json.loads(row.value) if row else {}
    profiles[name] = mapping
    if row:
        row.value = json.dumps(profiles)
        row.updated_by = user_name
    else:
        ctx.db.add(Setting(entity_id=ctx.entity.id, key=PROFILE_KEY,
                           value=json.dumps(profiles), value_type="json",
                           label="Saved column-mapping profiles for plan uploads",
                           updated_by=user_name))
    ctx.db.flush()
    return profiles
