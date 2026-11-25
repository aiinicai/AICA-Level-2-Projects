"""Turn a ``Forecast`` into rows and cells for the lot grid template (layout: docs/forecast_layout.md)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.engine.forecast import COVERED, LINE_LABELS, NO_GAP, NOT_SUFFICIENT, Column, Forecast


@dataclass
class ColView:
    label: str
    kind: str            # actual | lot | month | horizon
    status: str          # ACTUAL - locked | CURRENT | FORECAST | ''
    month: str
    col: Column | None = None
    lot: int | None = None
    locked: dict | None = None


@dataclass
class Cell:
    value: object = None
    css: str = ""
    drill: dict | None = None


@dataclass
class GridRow:
    label: str
    kind: str            # section | group | cat | total | line | key | status | memo
    cells: list[Cell] = field(default_factory=list)
    css: str = ""
    hint: str = ""


STATUS_CSS = {NO_GAP: "text-bg-success", COVERED: "text-bg-warning", NOT_SUFFICIENT: "text-bg-danger"}


def build_grid(fc: Forecast) -> dict:
    cols: list[ColView] = []
    for lt in fc.lots:
        if lt.status == "actual":
            cols.append(ColView(lt.label, "actual", "ACTUAL - locked", lt.band,
                                locked=fc.locked.get(lt.start)))
    for c in fc.columns:
        if c.kind == "lot":
            lt = fc.fc_lots[c.lots[0]]
            cols.append(ColView(c.label, "lot", lt.status.upper(), lt.band, c, c.lots[0]))
        else:
            cols.append(ColView(c.label, c.kind, "", c.band, c))

    bands: list[list] = []
    for cv in cols:
        name = cv.month if cv.kind != "horizon" else ""
        if bands and bands[-1][0] == name:
            bands[-1][1] += 1
        else:
            bands.append([name, 1])

    def line_cells(key: str) -> list[Cell]:
        out = []
        for cv in cols:
            if cv.kind == "actual":
                v = (cv.locked or {}).get("lines", {}).get(key)
                out.append(Cell(Decimal(v) if v is not None else None, "locked"))
            else:
                out.append(Cell(fc.line(key, cv.col), "" if cv.kind == "lot" else "subtotal"))
        return out

    def cat_cells(r) -> list[Cell]:
        out = []
        for cv in cols:
            if cv.kind == "actual":
                v = (cv.locked or {}).get("categories", {}).get(r.name)
                out.append(Cell(Decimal(v) if v is not None else None, "locked"))
            elif cv.kind == "lot":
                v = r.values[cv.lot]
                out.append(Cell(v, "", {"lot": cv.lot, "cat": r.category_id} if v else None))
            else:
                out.append(Cell(fc.row(r, cv.col), "subtotal"))
        return out

    rows: list[GridRow] = [GridRow("A. Opening cash", "section"),
                           GridRow(LINE_LABELS["opening"], "line", line_cells("opening"))]
    for title, cats, total in (("B. Cash inflows", fc.inflow_rows, "inflows"),
                               ("C. Cash outflows", fc.outflow_rows, "outflows")):
        rows.append(GridRow(title, "section"))
        groups = {r.group for r in cats}
        last = None
        for r in cats:
            if len(groups) > 1 and r.group != last:
                rows.append(GridRow(r.group, "group"))
                last = r.group
            rows.append(GridRow(r.name, "cat", cat_cells(r)))
        rows.append(GridRow(LINE_LABELS[total], "total", line_cells(total)))
    rows += [
        GridRow("D. " + LINE_LABELS["net"], "total", line_cells("net")),
        GridRow("E. " + LINE_LABELS["closing"], "key", line_cells("closing")),
        GridRow("F. Funding", "section"),
        GridRow(LINE_LABELS["facility"], "line", line_cells("facility")),
        GridRow(LINE_LABELS["fp_before"], "total", line_cells("fp_before")),
        GridRow(LINE_LABELS["gap_before"], "line", line_cells("gap_before"), "gap"),
        GridRow("G. Cheque holds", "section", hint="Rows B-F are as per ERP. Holds are applied here."),
        GridRow(LINE_LABELS["hold_out"], "line", line_cells("hold_out")),
        GridRow(LINE_LABELS["hold_in"], "line", line_cells("hold_in")),
        GridRow(LINE_LABELS["hold_net"], "total", line_cells("hold_net")),
        GridRow(LINE_LABELS["hold_cum"], "line", line_cells("hold_cum")),
        GridRow(LINE_LABELS["closing_after"], "total", line_cells("closing_after")),
        GridRow(LINE_LABELS["fp_after"], "key", line_cells("fp_after"), "fp-after"),
        GridRow(LINE_LABELS["shortfall_after"], "line", line_cells("shortfall_after"), "gap"),
    ]
    status_cells = []
    for cv in cols:
        if cv.kind == "actual":
            st = (cv.locked or {}).get("funding_status")
            status_cells.append(Cell(st or "", STATUS_CSS.get(st, "")))
        else:
            st = fc.status(cv.col)
            status_cells.append(Cell(st, STATUS_CSS[st]))
    rows.append(GridRow("Are the holds sufficient?", "status", status_cells))
    rows.append(GridRow("H. Memo (not in totals)", "section"))
    for key in ("risk_excluded", "deferred_in", "holds_open"):
        rows.append(GridRow(LINE_LABELS[key], "memo", line_cells(key)))
    return {"cols": cols, "bands": bands, "rows": rows}
