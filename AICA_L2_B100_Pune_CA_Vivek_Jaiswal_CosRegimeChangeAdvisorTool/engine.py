"""
engine.py - Tax engine and optimiser for RegimeWise.

For each company it evaluates six options over the projection years:
    "Stay normal", "Switch in Y1", ..., "Switch in Y5"
and picks the one with the lowest present value (PV) of tax.

Normal regime, each year:
    set off brought-forward loss / unabsorbed depreciation against income
    deduct inter-corporate dividends (capped at the amount distributed onward)
    tax = higher of normal tax and MAT on book profit
    MAT credit is earned when MAT is higher, and used when normal tax is higher
Concessional regime under Section 200 (old 115BAA), from the switch year onward (irreversible):
    22% + 10% surcharge + cess; no MAT; MAT credit lapses;
    losses entered as "loss_not_allowed_concessional" are dropped at the switch

ALL RATES ARE INPUTS IN `RATES`. Verify them against the Income-tax Act, 2025 and
the current Finance Act before use. Simplifications are listed in the README.
"""
import pandas as pd

RATES = {
    "normal_rate_small": 0.25,        # turnover up to the limit below
    "normal_rate_large": 0.30,
    "small_turnover_limit": 400e7,    # Rs 400 crore
    "surcharge_slabs": [(1e7, 0.0), (10e7, 0.07), (float("inf"), 0.12)],  # income up to 1 cr, 10 cr, above
    "concessional_rate": 0.22,
    "concessional_surcharge": 0.10,
    "mat_rate": 0.15,
    "cess": 0.04,
}

COMPANY_COLS = ["entity", "bf_business_loss", "unabsorbed_depreciation", "mat_credit_bf",
                "loss_not_allowed_concessional"]
PROJECTION_COLS = ["entity", "year", "turnover", "income_before_setoff", "book_profit",
                   "dividend_received", "dividend_distributed"]


def _surcharge(amount: float) -> float:
    for limit, rate in RATES["surcharge_slabs"]:
        if amount <= limit:
            return rate
    return 0.0


def simulate(company: dict, years: pd.DataFrame, switch_year: int | None) -> pd.DataFrame:
    """Year-by-year tax for one company. switch_year = 1-based year of switching, or None to stay normal."""
    cess = 1 + RATES["cess"]
    loss_pool = company["bf_business_loss"] + company["unabsorbed_depreciation"]
    mat_credit = company["mat_credit_bf"]
    rows = []
    for i, y in enumerate(years.itertuples(index=False), start=1):
        concessional = switch_year is not None and i >= switch_year
        note = ""
        if concessional and i == switch_year:
            lapsed = mat_credit
            blocked = min(company["loss_not_allowed_concessional"], loss_pool)
            loss_pool -= blocked
            mat_credit = 0.0
            parts = ["Opts for Section 200 (old 115BAA)"]
            if lapsed:
                parts.append(f"MAT credit Rs {lapsed:,.0f} lapses")
            if blocked:
                parts.append(f"losses Rs {blocked:,.0f} blocked")
            note = "; ".join(parts)

        income = y.income_before_setoff
        if income < 0:                       # a loss year adds to the pool
            loss_pool += -income
            setoff, gti = 0.0, 0.0
        else:
            setoff = min(loss_pool, income)
            loss_pool -= setoff
            gti = income - setoff
        div_ded = min(y.dividend_received, y.dividend_distributed, gti)
        ti = gti - div_ded

        if concessional:
            tax = ti * RATES["concessional_rate"] * (1 + RATES["concessional_surcharge"]) * cess
            mat = credit_used = credit_earned = 0.0
        else:
            rate = RATES["normal_rate_small"] if y.turnover <= RATES["small_turnover_limit"] else RATES["normal_rate_large"]
            normal = ti * rate * (1 + _surcharge(ti)) * cess
            bp = max(y.book_profit, 0)
            mat = bp * RATES["mat_rate"] * (1 + _surcharge(bp)) * cess
            if normal >= mat:
                credit_used = min(mat_credit, normal - mat)
                credit_earned = 0.0
                tax = normal - credit_used
            else:
                credit_used, credit_earned, tax = 0.0, mat - normal, mat
            mat_credit += credit_earned - credit_used

        rows.append({"Year": y.year, "Regime": "Section 200 (old 115BAA)" if concessional else "Normal",
                     "Total income": round(ti), "Tax": round(tax),
                     "MAT credit c/f": round(mat_credit), "Loss c/f": round(loss_pool), "Note": note})
    return pd.DataFrame(rows)


def present_value(taxes: pd.Series, discount_pct: float) -> float:
    r = discount_pct / 100
    return float(sum(t / (1 + r) ** i for i, t in enumerate(taxes)))


def options(company: dict, years: pd.DataFrame, discount_pct: float) -> pd.DataFrame:
    """Every option for one company, with total and PV of tax, best first."""
    out = []
    for sw in [None] + list(range(1, len(years) + 1)):
        sched = simulate(company, years, sw)
        out.append({"Option": "Stay normal" if sw is None else f"Switch in Y{sw} ({years['year'].iloc[sw - 1]})",
                    "switch_year": sw,
                    "Total tax": int(sched["Tax"].sum()),
                    "PV of tax": round(present_value(sched["Tax"], discount_pct)),
                    "Unused MAT credit at end": int(sched["MAT credit c/f"].iloc[-1])})
    return pd.DataFrame(out).sort_values("PV of tax").reset_index(drop=True)


def analyse_group(companies: pd.DataFrame, projections: pd.DataFrame, discount_pct: float = 10.0):
    """Best option per company plus the group summary."""
    summary, detail = [], {}
    for c in companies.to_dict("records"):
        years = projections[projections["entity"] == c["entity"]].sort_values("year")
        if years.empty:
            continue
        opts = options(c, years, discount_pct)
        best = opts.iloc[0]
        normal = opts[opts["switch_year"].isna()].iloc[0]
        detail[c["entity"]] = {"options": opts.drop(columns="switch_year"),
                               "schedule": simulate(c, years, None if pd.isna(best["switch_year"]) else int(best["switch_year"]))}
        summary.append({"Entity": c["entity"], "Best option": best["Option"],
                        "PV of tax - best": int(best["PV of tax"]),
                        "PV of tax - stay normal": int(normal["PV of tax"]),
                        "PV saving": int(normal["PV of tax"] - best["PV of tax"]),
                        "Runner-up": opts.iloc[1]["Option"] if len(opts) > 1 else "",
                        "Margin over runner-up": int(opts.iloc[1]["PV of tax"] - best["PV of tax"]) if len(opts) > 1 else 0})
    s = pd.DataFrame(summary)
    return s, detail


def templates(entities=("Co A", "Co B"), first_year: int = 2026, n_years: int = 5):
    """Blank input templates: right columns, one row per company (and per year), amounts left empty."""
    companies = pd.DataFrame({"entity": list(entities)}).reindex(columns=COMPANY_COLS)
    years = [f"{y}-{str(y + 1)[-2:]}" for y in range(first_year, first_year + n_years)]
    projections = (pd.DataFrame([(e, y) for e in entities for y in years], columns=["entity", "year"])
                   .reindex(columns=PROJECTION_COLS))
    return companies, projections


def missing_columns(companies: pd.DataFrame, projections: pd.DataFrame) -> list[str]:
    """Columns the templates require that an uploaded file lacks (they would otherwise be read as zero)."""
    return ([f"companies: {c}" for c in COMPANY_COLS if c not in companies.columns] +
            [f"projections: {c}" for c in PROJECTION_COLS if c not in projections.columns])


def prepare(c: pd.DataFrame, p: pd.DataFrame):
    """Clean raw inputs: trim names, add any missing column as zero, turn amounts into numbers.
    Commas in amounts (e.g. 1,50,000 typed in Excel) are removed first."""
    c, p = c.copy(), p.copy()
    c.columns, p.columns = c.columns.str.strip(), p.columns.str.strip()
    for df, cols in ((c, COMPANY_COLS[1:]), (p, PROJECTION_COLS[2:])):
        if "entity" in df:
            df["entity"] = df["entity"].astype(str).str.strip()
        for col in cols:
            raw = df[col] if col in df else pd.Series(0, index=df.index)
            df[col] = pd.to_numeric(raw.astype(str).str.replace(",", "").str.strip(), errors="coerce").fillna(0)
    if "year" in p:
        p["year"] = p["year"].astype(str).str.strip()
    return c, p


def load(companies_csv, projections_csv):
    return prepare(pd.read_csv(companies_csv), pd.read_csv(projections_csv))


if __name__ == "__main__":
    comp, proj = load("data/companies.csv", "data/projections.csv")
    summary, detail = analyse_group(comp, proj)
    pd.set_option("display.width", 200)
    print(summary.to_string(index=False))
    for name, d in detail.items():
        print(f"\n=== {name} ===")
        print(d["options"].to_string(index=False))
        print(d["schedule"].to_string(index=False))
