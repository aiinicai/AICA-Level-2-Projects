"""
Workforce consolidation & budget variance engine – AICA Level 2 capstone.

Reads the five country workforce files (as saved by the n8n intake workflow), validates them,
consolidates internal + external resources in INR and produces:
  * Consolidated_Workforce_<period>.xlsx  – walk, cost, mix, budget variance, detail, validation log
  * dashboard_data_<period>.json          – the same numbers for the CFO dashboard

Usage (from the folder containing this script):
    python consolidate.py --period Nov-2026 --input ./inbox --budget ./Workforce_Budget_FY26.xlsx \
                          --assumptions ./Workforce_Assumptions_and_Control_Totals.xlsx --output ./output

Requires: pandas, openpyxl   (pip install pandas openpyxl)
"""
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

COUNTRIES = ["India", "UK", "US", "France", "China"]
LOCAL_CCY = {"India": "INR", "UK": "GBP", "US": "USD", "France": "EUR", "China": "CNY"}
SHEETS = {"int_prev": "Internal_Previous month", "int_cur": "Internal_Current month",
          "ext_prev": "External_Previous month", "ext_cur": "External_Current month"}
INT_COLS = ["Employee Code", "Employee name", "Hire date", "Hire type", "Project name", "Exit date", "Exit type",
            "Grade", "Location", "Salary currency", "Fixed Salary", "Bonus", "CTC", "Function"]
EXT_COLS = ["Consultant code", "Consultant name", "Contract Start", "Contract end", "Engagement type", "Project name",
            "End reason", "Location", "Bill Currency", "Bill Frequency", "Bill Rate"]
GRADES = ["G1", "G2", "G3", "G4", "G5", "G6"]
EXT_LEAVER = ["Contract completed"]
EXT_TERMINATION = ["Early termination", "Converted to employee"]


# ----------------------------------------------------------------------------- helpers
class Log:
    def __init__(self):
        self.rows = []

    def add(self, country, check, severity, detail):
        self.rows.append(dict(Country=country, Check=check, Severity=severity, Detail=detail))
        print(f"  [{severity:5}] {country:7} {check}: {detail}")

    @property
    def errors(self):
        return [r for r in self.rows if r["Severity"] == "ERROR"]


def month_bounds(period):
    start = datetime.strptime(period, "%b-%Y")
    end = (pd.Timestamp(start) + pd.offsets.MonthEnd(0)).to_pydatetime()
    prev_end = pd.Timestamp(start) - pd.Timedelta(days=1)
    return pd.Timestamp(start), pd.Timestamp(end), prev_end, prev_end.strftime("%b-%Y")


def find_file(folder, country, period):
    """Prefer the n8n name Workforce_<Country>_<Mon-YYYY>.xlsx; fall back to Workforce_<Country>.xlsx.
    If several match, take the most recently modified (latest resubmission)."""
    pats = [f"Workforce_{country}_{period}*.xlsx", f"Workforce_{country}.xlsx"]
    for p in pats:
        hits = sorted(folder.glob(p), key=lambda f: f.stat().st_mtime, reverse=True)
        hits = [h for h in hits if re.fullmatch(rf"Workforce_{country}(_{period})?( \(\d+\))?\.xlsx", h.name)]
        if hits:
            return hits[0]
    return None


def read_sheet(path, sheet, cols):
    df = pd.read_excel(path, sheet_name=sheet, header=1)
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in cols if c not in df.columns]
    return df.dropna(how="all"), missing


def load_fx(path, period, prev_period):
    fx = pd.read_excel(path, sheet_name="FX_Rates", header=1)
    fx = fx.set_index("Currency")
    col = f"{period} → INR"
    if col not in fx.columns:
        sys.exit(f"FX rate column '{col}' not found in {path.name} (FX_Rates sheet). Add the month's rates first.")
    units = pd.read_excel(path, sheet_name="Assumptions", header=0).set_index("Item")["Value"]
    bill_units = {"Hourly": float(units["Hours per month (Hourly billing)"]),
                  "Daily": float(units["Days per month (Daily billing)"]),
                  "Monthly": float(units["Units per month (Monthly billing)"])}
    return fx[col].astype(float).to_dict(), bill_units


# ----------------------------------------------------------------------------- validation
def validate(country, d, period, m_start, m_end, prev_end, log):
    ip, ic, xp, xc = d["int_prev"], d["int_cur"], d["ext_prev"], d["ext_cur"]
    for name, df, code in [("Internal current", ic, "Employee Code"), ("External current", xc, "Consultant code")]:
        dups = df[df[code].duplicated()][code].tolist()
        if dups:
            log.add(country, f"{name}: duplicate codes", "ERROR", ", ".join(map(str, dups[:10])))
    bad_loc = ic[ic["Location"] != country]
    if len(bad_loc):
        log.add(country, "Location differs from file country", "WARN",
                f"{len(bad_loc)} employee(s): {', '.join(bad_loc['Employee Code'].astype(str).head(5))} – check for transfers")
    bad_ccy = ic[ic["Salary currency"] != ic["Location"].map(LOCAL_CCY)]
    if len(bad_ccy):
        log.add(country, "Salary currency not local", "WARN", f"{len(bad_ccy)} employee(s)")
    for col, allowed, df, lbl in [("Grade", GRADES, ic, "Grade"), ("Hire type", ["Regular", "Project"], ic, "Hire type"),
                                  ("Engagement type", ["Regular", "Project"], xc, "Engagement type"),
                                  ("Bill Frequency", ["Hourly", "Daily", "Monthly"], xc, "Bill frequency")]:
        bad = df[~df[col].isin(allowed)]
        if len(bad):
            log.add(country, f"Invalid {lbl}", "ERROR", f"{len(bad)} row(s) e.g. {bad[col].astype(str).unique()[:3].tolist()}")
    exits = ic[ic["Exit date"].notna()]
    bad = exits[~exits["Exit type"].isin(["Resignation", "Termination"])]
    if len(bad):
        log.add(country, "Exit date without valid Exit type", "ERROR", f"{len(bad)} row(s)")
    ended = xc[(xc["Contract end"] >= m_start) & (xc["Contract end"] <= m_end)]
    bad = ended[~ended["End reason"].isin(EXT_LEAVER + EXT_TERMINATION)]
    if len(bad):
        log.add(country, "Contract ended in month without End reason", "ERROR", f"{len(bad)} row(s)")
    if (ic["Hire date"] > ic["Exit date"]).any():
        log.add(country, "Hire date after exit date", "ERROR", f"{int((ic['Hire date'] > ic['Exit date']).sum())} row(s)")
    if (xc["Contract Start"] > xc["Contract end"]).any():
        log.add(country, "Contract start after end", "ERROR", f"{int((xc['Contract Start'] > xc['Contract end']).sum())} row(s)")
    future = ic[ic["Hire date"] > m_end]
    if len(future):
        log.add(country, "Hire date after period end", "WARN", f"{len(future)} row(s)")
    blank = ic["CTC"].isna()
    if blank.any():
        log.add(country, "CTC blank", "INFO", f"{int(blank.sum())} row(s) – computed as Fixed + Bonus")
    ctc_gap = ~blank & ((ic["Fixed Salary"].fillna(0) + ic["Bonus"].fillna(0) - ic["CTC"]).abs() > 1)
    if ctc_gap.any():
        log.add(country, "CTC ≠ Fixed + Bonus", "WARN", f"{int(ctc_gap.sum())} row(s) – CTC recomputed")
    if (ic["Fixed Salary"].fillna(0) <= 0).any() or (xc["Bill Rate"].fillna(0) <= 0).any():
        log.add(country, "Missing / zero salary or bill rate", "ERROR", "check pay columns")
    # roll-forward: everyone active at previous month-end must appear in the current file
    for name, p, c, code, end in [("Internal", ip, ic, "Employee Code", "Exit date"),
                                  ("External", xp, xc, "Consultant code", "Contract end")]:
        open_codes = set(p.loc[p[end].isna() | (p[end] > prev_end), code])
        missing = open_codes - set(c[code])
        if missing:
            log.add(country, f"{name}: opening population missing from current month", "ERROR",
                    f"{len(missing)} code(s) e.g. {sorted(missing)[:5]}")


# ----------------------------------------------------------------------------- calculations
def walk(country, pop, prev, cur, m_start, m_end, prev_end, kind):
    if kind == "int":
        s, e, t, r = "Hire date", "Exit date", "Hire type", "Exit type"
        lv, tm = ["Resignation"], ["Termination"]
    else:
        s, e, t, r = "Contract Start", "Contract end", "Engagement type", "End reason"
        lv, tm = EXT_LEAVER, EXT_TERMINATION
    opening = int((prev[e].isna() | (prev[e] > prev_end)).sum())
    joined = cur[(cur[s] >= m_start) & (cur[s] <= m_end)]
    left = cur[(cur[e] >= m_start) & (cur[e] <= m_end)]
    w = dict(Country=country, Population=pop, Opening=opening,
             Hires=int((joined[t] == "Regular").sum()),
             Leavers=int(left[r].isin(lv).sum()),
             Terminations=int(left[r].isin(tm).sum()),
             **{"Project hires": int((joined[t] == "Project").sum())})
    w["Closing"] = int((cur[e].isna() | (cur[e] > m_end)).sum())
    w["Walk check"] = w["Opening"] + w["Hires"] - w["Leavers"] - w["Terminations"] + w["Project hires"] - w["Closing"]
    return w


def run(args):
    folder, out = Path(args.input), Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    period = args.period
    m_start, m_end, prev_end, prev_period = month_bounds(period)
    fx, bill_units = load_fx(Path(args.assumptions), period, prev_period)
    log = Log()
    print(f"Consolidating {period} (month-end {m_end:%d-%b-%Y}) from {folder}")

    walks, internal, external, sources = [], [], [], []
    for country in COUNTRIES:
        f = find_file(folder, country, period)
        if f is None:
            log.add(country, "File received", "ERROR", "no file found – excluded from consolidation")
            continue
        sources.append(dict(Country=country, File=f.name, Modified=datetime.fromtimestamp(f.stat().st_mtime)))
        d, ok = {}, True
        try:
            for k, sh in SHEETS.items():
                d[k], missing = read_sheet(f, sh, INT_COLS if k.startswith("int") else EXT_COLS)
                if missing:
                    log.add(country, f"Sheet '{sh}' columns", "ERROR", f"missing {missing}")
                    ok = False
        except ValueError as e:
            log.add(country, "Template structure", "ERROR", str(e)); ok = False
        if not ok:
            continue
        for k in ("int_prev", "int_cur"):
            for c in ("Hire date", "Exit date"):
                d[k][c] = pd.to_datetime(d[k][c], errors="coerce")
        for k in ("ext_prev", "ext_cur"):
            for c in ("Contract Start", "Contract end"):
                d[k][c] = pd.to_datetime(d[k][c], errors="coerce")
        n_err = len(log.errors)
        validate(country, d, period, m_start, m_end, prev_end, log)
        if len(log.errors) == n_err:
            log.add(country, "Validation", "OK", f"{f.name}: all checks passed")

        walks.append(walk(country, "Internal", d["int_prev"], d["int_cur"], m_start, m_end, prev_end, "int"))
        walks.append(walk(country, "External", d["ext_prev"], d["ext_cur"], m_start, m_end, prev_end, "ext"))

        ic = d["int_cur"].copy()
        ic["CTC"] = ic["Fixed Salary"].fillna(0) + ic["Bonus"].fillna(0)
        ic["Country"] = country
        ic["Active at month-end"] = ic["Exit date"].isna() | (ic["Exit date"] > m_end)
        ic["FX to INR"] = ic["Salary currency"].map(fx)
        ic["Monthly cost (INR)"] = (ic["CTC"] / 12 * ic["FX to INR"]).round(0)
        internal.append(ic)

        xc = d["ext_cur"].copy()
        xc["Country"] = country
        xc["Active at month-end"] = xc["Contract end"] > m_end
        xc["FX to INR"] = xc["Bill Currency"].map(fx)
        xc["Monthly cost (INR)"] = (xc["Bill Rate"] * xc["Bill Frequency"].map(bill_units) * xc["FX to INR"]).round(0)
        external.append(xc)

    if not internal:
        sys.exit("No valid country files – nothing to consolidate.")
    missing_fx = set(pd.concat(internal)["Salary currency"]).union(pd.concat(external)["Bill Currency"]) - set(fx)
    if missing_fx:
        sys.exit(f"No FX rate for {missing_fx} in {period}.")
    I, X = pd.concat(internal, ignore_index=True), pd.concat(external, ignore_index=True)
    W = pd.DataFrame(walks)
    Ia, Xa = I[I["Active at month-end"]], X[X["Active at month-end"]]

    # ---- cost & headcount by country
    cost = []
    for c in [s["Country"] for s in sources]:
        for pop, df in (("Internal", Ia), ("External", Xa)):
            sub = df[df["Country"] == c]
            cost.append(dict(Country=c, Population=pop, Headcount=len(sub), **{"Monthly cost (INR)": float(sub["Monthly cost (INR)"].sum())}))
    C = pd.DataFrame(cost)
    C["Cost per head (INR)"] = (C["Monthly cost (INR)"] / C["Headcount"].where(C["Headcount"] > 0)).round(0)

    # ---- budget variance
    B = pd.read_excel(args.budget, sheet_name="Budget")
    B = B[B["Month"] == period].rename(columns={"Location": "Country"})
    if B.empty:
        log.add("Group", "Budget", "WARN", f"no budget rows for {period}")
    V = C.merge(B[["Country", "Population", "Budget headcount", "Budget monthly cost (INR)"]], on=["Country", "Population"], how="left")
    V = V.rename(columns={"Headcount": "Actual headcount", "Monthly cost (INR)": "Actual monthly cost (INR)"})
    V["HC variance"] = V["Actual headcount"] - V["Budget headcount"]
    V["HC variance %"] = V["HC variance"] / V["Budget headcount"]
    V["Cost variance (INR)"] = V["Actual monthly cost (INR)"] - V["Budget monthly cost (INR)"]
    V["Cost variance %"] = V["Cost variance (INR)"] / V["Budget monthly cost (INR)"]
    # volume / rate split of cost variance (budget cost per head = budget cost / budget HC)
    bcph = V["Budget monthly cost (INR)"] / V["Budget headcount"]
    acph = V["Actual monthly cost (INR)"] / V["Actual headcount"]
    V["Volume effect (INR)"] = (V["HC variance"] * bcph).round(0)
    V["Rate / mix effect (INR)"] = ((acph - bcph) * V["Actual headcount"]).round(0)

    # ---- mixes (active at month-end)
    grade = Ia.pivot_table(index="Country", columns="Grade", values="Employee Code", aggfunc="count", fill_value=0).reindex(columns=GRADES, fill_value=0)
    grade.loc["Group"] = grade.sum()
    grade_pct = grade.div(grade.sum(axis=1), axis=0)
    loc_mix = C.pivot_table(index="Country", columns="Population", values="Headcount", aggfunc="sum").reindex(columns=["Internal", "External"])
    loc_mix["Total"] = loc_mix.sum(axis=1)
    loc_mix["Share of group"] = loc_mix["Total"] / loc_mix["Total"].sum()
    loc_mix["External %"] = loc_mix["External"] / loc_mix["Total"]
    func = Ia.pivot_table(index="Function", columns="Country", values="Employee Code", aggfunc="count", fill_value=0)
    func["Group"] = func.sum(axis=1)
    # project resources by project x country x population: month-end heads, cost, and joiners in the month
    pi = Ia[Ia["Hire type"] == "Project"].assign(Population="Internal", Joined=lambda z: z["Hire date"].between(m_start, m_end))
    px = Xa[Xa["Engagement type"] == "Project"].assign(Population="External", Joined=lambda z: z["Contract Start"].between(m_start, m_end))
    proj = pd.concat([pi, px]).groupby(["Project name", "Country", "Population"]).agg(
        Headcount=("Country", "size"), **{"Monthly cost (INR)": ("Monthly cost (INR)", "sum"), "Joined in month": ("Joined", "sum")}).reset_index()
    proj["Joined in month"] = proj["Joined in month"].astype(int)

    # ---- KPI summary
    tot = lambda df, col: float(df[col].sum())
    kpi = {
        "period": period, "generated": datetime.now().strftime("%d-%b-%Y %H:%M"),
        "countries_included": [s["Country"] for s in sources],
        "internal_hc": len(Ia), "external_hc": len(Xa), "total_hc": len(Ia) + len(Xa),
        "budget_hc": int(V["Budget headcount"].sum()),
        "internal_cost": tot(Ia, "Monthly cost (INR)"), "external_cost": tot(Xa, "Monthly cost (INR)"),
        "budget_cost": tot(V, "Budget monthly cost (INR)"),
        "opening_hc": int(W["Opening"].sum()), "hires": int(W["Hires"].sum()), "leavers": int(W["Leavers"].sum()),
        "terminations": int(W["Terminations"].sum()), "project_hires": int(W["Project hires"].sum()),
        "validation_errors": len(log.errors),
    }
    kpi["total_cost"] = kpi["internal_cost"] + kpi["external_cost"]
    kpi["hc_var"] = kpi["total_hc"] - kpi["budget_hc"]
    kpi["hc_var_pct"] = kpi["hc_var"] / kpi["budget_hc"] if kpi["budget_hc"] else None
    kpi["cost_var"] = kpi["total_cost"] - kpi["budget_cost"]
    kpi["cost_var_pct"] = kpi["cost_var"] / kpi["budget_cost"] if kpi["budget_cost"] else None
    kpi["external_share"] = kpi["external_hc"] / kpi["total_hc"]
    kpi["cost_per_head"] = kpi["total_cost"] / kpi["total_hc"]
    kpi["budget_cost_per_head"] = kpi["budget_cost"] / kpi["budget_hc"] if kpi["budget_hc"] else None
    Wi = W[W["Population"] == "Internal"]
    kpi["attrition_month_pct"] = int(Wi["Leavers"].sum() + Wi["Terminations"].sum()) / max(1, int(Wi["Opening"].sum()))
    if (W["Walk check"] != 0).any():
        log.add("Group", "Walk reconciliation", "ERROR", "Opening + movements ≠ closing for some lines")
    else:
        log.add("Group", "Walk reconciliation", "OK", "Opening + hires − leavers − terminations + project hires = closing for every line")

    # ---- write Excel
    xlsx = out / f"Consolidated_Workforce_{period}.xlsx"
    write_excel(xlsx, period, kpi, W, C, V, grade, grade_pct, loc_mix, func, proj, I, X, pd.DataFrame(log.rows), pd.DataFrame(sources), fx)
    # ---- write JSON for the dashboard
    js = out / f"dashboard_data_{period}.json"
    payload = dict(kpi=kpi,
                   walk=W.drop(columns="Walk check").to_dict("records"),
                   cost=C.to_dict("records"),
                   variance=V.round(4).to_dict("records"),
                   grade_mix=grade.reset_index().to_dict("records"),
                   location_mix=loc_mix.reset_index().round(4).to_dict("records"),
                   function_mix=func.reset_index().to_dict("records"),
                   projects=proj.to_dict("records"),
                   validation=log.rows, fx=fx)
    js.write_text(json.dumps(payload, indent=1, default=lambda o: None if pd.isna(o) else str(o)))
    # index of every month in the output folder, for the dashboard's month / year filters
    months = sorted({p.stem.replace("dashboard_data_", "") for p in out.glob("dashboard_data_*.json")},
                    key=lambda m: datetime.strptime(m, "%b-%Y"))
    (out / "index.json").write_text(json.dumps({"periods": months, "updated": kpi["generated"]}, indent=1))
    if kpi["hc_var_pct"] is None or kpi["cost_var_pct"] is None:
        print(f"\nTotal HC {kpi['total_hc']:,} | Monthly cost INR {kpi['total_cost']/1e7:,.1f} Cr (no budget for {period})")
    else:
        print(f"\nTotal HC {kpi['total_hc']:,} (budget {kpi['budget_hc']:,}, {kpi['hc_var_pct']:+.1%}) | "
              f"Monthly cost INR {kpi['total_cost']/1e7:,.1f} Cr (budget {kpi['budget_cost']/1e7:,.1f} Cr, {kpi['cost_var_pct']:+.1%})")
    print(f"Validation errors: {len(log.errors)}\nWrote {xlsx}\nWrote {js}")
    return kpi


# ----------------------------------------------------------------------------- Excel writer
HF = Font(name="Arial", bold=True, color="FFFFFF", size=10)
HFILL = PatternFill("solid", fgColor="1F3864")
BF, BOLD = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
FMT = {"int": "#,##0;(#,##0);-", "inr": "#,##0;(#,##0);-", "pct": "0.0%;(0.0%);-", "date": "dd-mmm-yyyy"}


def put_df(ws, df, r0, c0=1, fmts=None, total=False):
    fmts = fmts or {}
    for j, col in enumerate(df.columns):
        c = ws.cell(r0, c0 + j, str(col)); c.font, c.fill = HF, HFILL
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    for i, row in enumerate(df.itertuples(index=False), 1):
        for j, v in enumerate(row):
            if isinstance(v, float) and pd.isna(v): v = None
            if isinstance(v, pd.Timestamp): v = v.to_pydatetime()
            c = ws.cell(r0 + i, c0 + j, v); c.font = BF
            col = df.columns[j]
            if col in fmts: c.number_format = FMT[fmts[col]]
            elif isinstance(v, (int, float)): c.number_format = FMT["int"]
    end = r0 + len(df)
    if total:
        end += 1
        ws.cell(end, c0, "Total").font = BOLD
        for j, col in enumerate(df.columns[1:], 1):
            if fmts.get(col) == "pct" or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            L = get_column_letter(c0 + j)
            c = ws.cell(end, c0 + j, f"=SUM({L}{r0+1}:{L}{end-1})"); c.font = BOLD
            c.number_format = FMT[fmts.get(col, "int")]
    return end


def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[get_column_letter(i)].width = x


def write_excel(path, period, kpi, W, C, V, grade, grade_pct, loc_mix, func, proj, I, X, LOGDF, SRC, fx):
    wb = Workbook()
    ws = wb.active; ws.title = "Summary"
    ws["A1"] = f"Workforce consolidation – {period}"; ws["A1"].font = Font(name="Arial", size=14, bold=True)
    ws["A2"] = f"Generated {kpi['generated']} by consolidate.py | Countries: {', '.join(kpi['countries_included'])} | Validation errors: {kpi['validation_errors']}"
    ws["A2"].font = Font(name="Arial", size=9, italic=True)
    rows = [("Total headcount", kpi["total_hc"], kpi["budget_hc"], "int"),
            ("Internal headcount", kpi["internal_hc"], None, "int"), ("External headcount", kpi["external_hc"], None, "int"),
            ("Monthly cost (INR)", kpi["total_cost"], kpi["budget_cost"], "inr"),
            ("Internal cost (INR)", kpi["internal_cost"], None, "inr"), ("External cost (INR)", kpi["external_cost"], None, "inr"),
            ("Cost per head (INR / month)", kpi["cost_per_head"], kpi["budget_cost_per_head"], "inr"),
            ("External share of headcount", kpi["external_share"], None, "pct"),
            ("Internal exits in month (% of opening)", kpi["attrition_month_pct"], None, "pct")]
    for j, h in enumerate(["Metric", "Actual", "Budget", "Variance", "Variance %"], 1):
        c = ws.cell(4, j, h); c.font, c.fill = HF, HFILL
    for i, (m, a, b, f) in enumerate(rows, 5):
        ws.cell(i, 1, m).font = BF
        ws.cell(i, 2, a).number_format = FMT[f]
        if b is not None:
            ws.cell(i, 3, b).number_format = FMT[f]
            ws.cell(i, 4, f"=B{i}-C{i}").number_format = FMT[f]
            ws.cell(i, 5, f"=IF(C{i}=0,0,D{i}/C{i})").number_format = FMT["pct"]
        for j in range(2, 6): ws.cell(i, j).font = BF
    r = len(rows) + 7
    ws.cell(r, 1, "Source files").font = BOLD
    put_df(ws, SRC, r + 1, fmts={"Modified": "date"})
    widths(ws, [38, 18, 18, 18, 12])

    ws = wb.create_sheet("Workforce_Walk")
    ws["A1"] = f"Workforce walk – {period}: Opening + Hires − Leavers − Terminations + Project hires = Closing"; ws["A1"].font = BOLD
    r = 3
    for pop in ("Internal", "External"):
        ws.cell(r, 1, pop).font = BOLD
        r = put_df(ws, W[W["Population"] == pop].drop(columns=["Population"]), r + 1, total=True) + 2
    widths(ws, [12, 10, 9, 9, 13, 13, 10, 11])

    ws = wb.create_sheet("Cost_by_Country")
    put_df(ws, C, 1, fmts={"Monthly cost (INR)": "inr", "Cost per head (INR)": "inr"})
    widths(ws, [12, 12, 12, 20, 20])

    ws = wb.create_sheet("Budget_Variance")
    ws["A1"] = "Actual vs budget – Variance = Actual − Budget (positive = above budget). Cost split: volume = HC variance × budget cost/head; rate/mix = (actual − budget cost/head) × actual HC."
    ws["A1"].font = Font(name="Arial", size=9, italic=True)
    put_df(ws, V, 3, fmts={"HC variance %": "pct", "Cost variance %": "pct", "Cost per head (INR)": "inr"}, total=True)
    widths(ws, [11, 11, 10, 18, 14, 10, 10, 10, 16, 18, 16, 10, 16, 16])

    ws = wb.create_sheet("Grade_Mix")
    ws["A1"] = "Internal headcount by grade (active at month-end)"; ws["A1"].font = BOLD
    e = put_df(ws, grade.reset_index(), 3)
    ws.cell(e + 2, 1, "Grade mix %").font = BOLD
    put_df(ws, grade_pct.reset_index(), e + 3, fmts={g: "pct" for g in GRADES})
    widths(ws, [12] + [9] * 6)

    ws = wb.create_sheet("Location_Mix")
    put_df(ws, loc_mix.reset_index(), 1, fmts={"Share of group": "pct", "External %": "pct"}, total=False)
    widths(ws, [12, 10, 10, 10, 14, 11])

    ws = wb.create_sheet("Function_Mix")
    put_df(ws, func.reset_index(), 1)
    widths(ws, [14] + [9] * 7)

    ws = wb.create_sheet("Project_Resources")
    put_df(ws, proj, 1, fmts={"Monthly cost (INR)": "inr"}, total=True)
    widths(ws, [40, 12, 11, 18])

    for name, df in (("Detail_Internal", I), ("Detail_External", X)):
        ws = wb.create_sheet(name)
        cols = ["Country"] + [c for c in df.columns if c != "Country"]
        dates = {c: "date" for c in cols if "date" in c.lower() or c in ("Contract Start", "Contract end")}
        put_df(ws, df[cols], 1, fmts={**dates, "Monthly cost (INR)": "inr", "FX to INR": "int"})
        ws.freeze_panes = "C2"; ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(df)+1}"
        widths(ws, [10, 15, 22] + [13] * (len(cols) - 3))

    ws = wb.create_sheet("FX_Used")
    put_df(ws, pd.DataFrame([{"Currency": k, f"{period} → INR": v} for k, v in fx.items()]), 1, fmts={f"{period} → INR": "inr"})
    for i in range(2, len(fx) + 2): ws.cell(i, 2).number_format = "#,##0.00"
    widths(ws, [12, 16])

    ws = wb.create_sheet("Validation_Log")
    put_df(ws, LOGDF, 1)
    widths(ws, [10, 44, 9, 90])
    wb.save(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--period", required=True, help="Reporting month, e.g. Nov-2026")
    ap.add_argument("--input", default="./inbox", help="Folder with Workforce_<Country>_<Mon-YYYY>.xlsx files")
    ap.add_argument("--budget", default="./Workforce_Budget_FY26.xlsx")
    ap.add_argument("--assumptions", default="./Workforce_Assumptions_and_Control_Totals.xlsx")
    ap.add_argument("--output", default="./output")
    run(ap.parse_args())
