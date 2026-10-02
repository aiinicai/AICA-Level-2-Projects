"""
LookThrough MCP server: the family-office portfolio engine as read-only tools for Claude.

Every number a tool returns comes from verify/recompute.py, the independent pandas engine that
is reconciled value-for-value against the browser app (verify/reconcile_app.js). The server adds
no financial arithmetic of its own beyond comparing those figures with the investment policy.

Controls
  * Read-only: no tool writes data, places orders or reaches the network.
  * Evidence ledger: every number returned in this session is recorded; verify_note() checks that
    each figure in a drafted note traces to one of them (deterministic, not model-judged).
  * Audit log: logs/mcp_audit.jsonl gets one line per call (time, tool, arguments, result hash).

Run:   python mcp_server/lookthrough_mcp.py          (stdio transport, for Claude Desktop)
"""
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
_LIVE = ROOT / "data" / "live" / "dataset.json"  # a fresh clone has none: the committed 31-Aug-2026 snapshot is used
os.environ.setdefault("LOOKTHROUGH_DATASET", str(_LIVE if _LIVE.exists() else ROOT / "data" / "snapshot" / "dataset.json"))
sys.path.insert(0, str(ROOT / "verify"))

import recompute as E  # noqa: E402  - the reconciled reference engine; computes on import
from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402


class BadInput(ToolError, ValueError):
    """Anticipated input error: its message reaches the client (plain exceptions are withheld as crashes)."""

AUDIT = ROOT / "logs" / "mcp_audit.jsonl"
RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
CR, LAKH = 1e7, 1e5
AS_ON = E.AS_ON
BASIS = ("Real Indian market data (NSE/Yahoo prices, AMFI NAVs, AMC portfolio disclosures); the family, its entities "
         "and transactions are fictitious. Figures from the LookThrough reference engine, reconciled against the app.")
DISCLAIMER = "Decision support for an investment committee. Not investment advice and not a recommendation."

# ------------------------------------------------------------------ evidence ledger
LEDGER: list[dict] = []  # every number emitted this session: {"tool", "path", "value", "unit", "labels"}

# Words that say nothing about WHICH figure a field holds; they are left out of the labels a note must match.
_GENERIC = {"pct", "cr", "lakh", "the", "of", "and", "data", "amount", "number", "figure", "ratio", "ratios", "rs",
            "inr", "per", "cent", "with", "for", "from", "that", "this", "are", "was", "were", "has", "have", "its", "into", "not",
            "all", "one", "two", "three", "limit", "latest", "month"}
# Short field names and the words a note uses for them (explicit and small, so a match stays explainable).
_ALIASES = {"xirr": {"xirr", "return", "returns"}, "1y": {"year", "yearly", "annual"}, "cagr3": {"three", "cagr", "growth"},
            "hhi": {"hhi", "herfindahl", "concentration"}, "pe": {"p/e", "earnings"}, "pb": {"p/b", "book"}, "roe": {"roe", "equity"},
            "roa": {"roa", "assets"}, "pat": {"pat", "profit", "profits"}, "cfo": {"cfo", "cash", "operations"},
            "via": {"through", "funds", "fund", "via"}, "top10": {"top", "ten", "top-10"}, "companies": {"companies", "stocks", "names"},
            "change": {"change", "fall", "loss", "reduce", "gain", "rise"}, "move": {"move", "fall", "rise", "drop", "market"},
            "correlation": {"correlation", "correlated"}, "overlap": {"overlap", "overlapping"}, "stress": {"stress", "scenario", "fall"},
            "value": {"value", "worth", "valued"}}


def _tokens(text: str, aliases: bool = True) -> set[str]:
    out = set()
    raw = re.findall(r"[a-z0-9/\-]+", str(text).lower().replace("_", " "))
    for w in raw + [p for w in raw if "-" in w for p in w.split("-")]:  # "single-stock" also as "single", "stock"
        w = w.strip("-/")
        if len(w) >= 2 and not w.isdigit() and w not in _GENERIC:
            if len(w) > 5 and w.endswith("ly"):
                w = w[:-2]  # "directly" -> "direct"
            out.add(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)  # plural -> singular
            if aliases:
                out |= _ALIASES.get(w, set())
    return out


_COUNT_LEAVES = {"companies", "common_stocks", "holdings_count", "breaches", "warnings", "not_computable", "holders", "adding", "reducing", "fills"}
_RATIO_LEAVES = {"beta", "hhi", "return_correlation", "pe", "pb", "effective_number_of_stocks", "portfolio_beta", "correlation"}


def _unit(path: str) -> str:
    """Unit of a returned figure, from its field path: cr, lakh, pct, rs (per-unit price/NAV), ratio, count or any."""
    segs = [x for x in re.split(r"[.\[\]]+", path.lower()) if x and not x.isdigit()]
    leaf = segs[-1] if segs else ""
    if leaf.endswith("_cr") or leaf == "cr" or any(x.endswith("_cr") for x in segs[:-1]):
        return "cr"
    if leaf.endswith("_lakh") or any(x.endswith("_lakh") for x in segs[:-1]):
        return "lakh"
    if "pct" in leaf or any(x.endswith("_pct") for x in segs[:-1]):
        return "pct"
    if leaf in ("price", "nav", "rate", "net_rate"):
        return "rs"
    if leaf in _RATIO_LEAVES or leaf.endswith("beta"):
        return "ratio"
    if leaf in _COUNT_LEAVES or leaf.endswith("_count"):
        return "count"
    return "any"


def _register(tool: str, obj: Any, path: str = "", labels: frozenset = frozenset()) -> None:
    """Record every number a tool returns, with its unit and the words that identify it: its field path, the tool,
    and the text fields of the records around it (company, test name, sector...). verify_note binds a figure in a
    note to a record only through these."""
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        if math.isfinite(obj):
            leaf = re.split(r"[.\]]", path)[-1]
            LEDGER.append({"tool": tool, "path": path, "value": float(obj), "unit": _unit(path),
                           "labels": set(labels) | _tokens(re.sub(r"\[\d+\]", " ", path)),
                           # the field's own name words (no aliases) and its record, to tell sibling fields apart
                           "own": _tokens(leaf, aliases=False) - {"cr", "lakh", "pct"}, "own_alias": _tokens(leaf) - {"cr", "lakh", "pct"},
                           "record": path[:len(path) - len(leaf)]})
    elif isinstance(obj, dict):
        here = labels | frozenset(t for v in obj.values() if isinstance(v, str) and len(v) <= 120 for t in _tokens(v))
        for k, v in obj.items():
            _register(tool, v, f"{path}.{k}" if path else str(k), here)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _register(tool, v, f"{path}[{i}]", labels)


def _r(x, nd=2):
    """Round for output; None for missing or non-finite. Missing data is never estimated."""
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


def _emit(tool: str, args: dict, data: dict, caveats: list[str] | None = None) -> dict:
    out = {"tool": tool, "as_on": AS_ON, "basis": BASIS, "data": data, "caveats": (caveats or []) + [DISCLAIMER]}
    if tool != "verify_note":
        _register(tool, data)
    try:
        AUDIT.parent.mkdir(exist_ok=True)
        blob = json.dumps(out, sort_keys=True, default=str)
        with AUDIT.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "tool": tool, "args": args,
                                "result_sha256": hashlib.sha256(blob.encode()).hexdigest()}) + "\n")
    except OSError:
        pass  # an unwritable log must not break the answer; the ledger still works
    return out


# ------------------------------------------------------------------ input validation
def _member(member: str) -> str | None:
    m = (member or "ALL").strip().upper()
    if m == "ALL":
        return None
    if m not in E.MEMBERS:
        raise BadInput(f"Unknown member {member!r}. Use 'ALL' or one of {E.MEMBERS} (see list_entities).")
    return m


def _scheme(sid: str) -> str:
    s = (sid or "").strip().upper()
    if s not in E.SCH:
        raise BadInput(f"Unknown scheme_id {sid!r}. Valid: {sorted(E.SCH)} (see list_entities).")
    return s


def _company(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    if s in E.COS:
        return s
    hits = [c for c, v in E.COS.items() if s and s.lower() in (v.get("name") or "").lower()]
    if len(hits) == 1:
        return hits[0]
    raise BadInput(f"Unknown company {symbol!r}." + (f" Did you mean one of {hits[:8]}?" if hits else " Use the NSE symbol, e.g. INFY."))


def _name(code: str) -> str:
    return (E.COS.get(code) or {}).get("name") or code


def _holdings(m: str | None):
    return E.H if m is None else E.H[E.H.member_id == m]


def _holdings_basis(m: str | None) -> tuple[dict, list[str]]:
    """Which disclosure each held fund is looked through on. AMCs publish a month's portfolio within about 10 days of
    month-end, so early in a month the latest file can be a month older than the prices. That is stated in the output
    and as a caveat, never left for the reader to infer. Compared by month (some AMCs date the file on the last business day)."""
    held = sorted(set(_holdings(m)[lambda d: d.asset_type == "MF"].instrument))
    dates = {s: (E.PORT_DATES.get(s) or [None])[-1] for s in held}
    known = sorted(d for d in dates.values() if d)
    behind = [s for s in held if dates[s] and dates[s][:7] < AS_ON[:7]]
    basis = {"prices_and_navs_at": AS_ON,
             "fund_holdings_disclosed_on": (known[0] if known[0] == known[-1] else f"{known[0]} to {known[-1]}") if known else None,
             "funds_on_an_earlier_disclosure": [f"{s} {E.SCH[s]['name']} ({dates[s]})" for s in behind]}
    cav = [f"Fund holdings are older than the prices: {len(behind)} of {len(held)} held funds are looked through on an earlier "
           f"month's disclosure ({', '.join(sorted({dates[s] for s in behind}))}) while prices and NAVs are at {AS_ON}. "
           "State this in any note; AMCs publish each month's portfolio within about 10 days of month-end."] if behind else []
    return basis, cav


# ------------------------------------------------------------------ server
mcp = MCPServer(
    name="lookthrough",
    title="LookThrough family-office portfolio engine",
    instructions=(
        "Read-only analytics for a (fictitious) Indian family office's equity and mutual-fund portfolio. "
        "Quote numbers exactly as tools return them and name the tool each came from. Label every statement "
        "FACT (data), CALC (tool calculation), ASSUMPTION (a stated input) or VIEW (your interpretation). "
        "Never give buy/sell recommendations; present screening results and trade-offs for the committee. "
        "Before presenting a finished note, call verify_note with the full text and fix any untraced figure."),
    version="1.0",
)


@mcp.tool(annotations=RO)
def list_entities() -> dict:
    """List the family's entities (member_id), the mutual-fund schemes (scheme_id), the investment-policy
    limits and the valuation date. Call this first to learn the valid identifiers."""
    data = {
        "members": [{"member_id": m["member_id"], "name": m["name"], "type": m["type"], "relationship": m["relationship"]}
                    for m in E.DS["members"]],
        "schemes": [{"scheme_id": s["scheme_id"], "name": s["name"], "category": s.get("category"),
                     "benchmark": s.get("benchmark_name") or s.get("benchmark"),
                     "portfolio_disclosure_loaded": s["scheme_id"] in E.LATEST} for s in E.DS["schemes"]],
        "policy_limits": {k: v for k, v in E.POL.items() if isinstance(v, (int, float)) and k.startswith(("max_", "target_", "band_"))},
        "valuation_date": AS_ON,
    }
    return _emit("list_entities", {}, data)


@mcp.tool(annotations=RO)
def portfolio_summary(member: str = "ALL") -> dict:
    """Value, cost, gain, XIRR and asset split (direct equity vs mutual funds) for the whole family ('ALL')
    or one entity (member_id). Amounts in Rs crore."""
    m = _member(member)
    h = _holdings(m)
    lt, debt, cash, unmapped, mf, eq = E.look_through(m)
    c = E.conc(lt)
    x = E.family_x if m is None else E.member_x.get(m)
    data = {
        "entity": m or "ALL",
        "value_cr": _r(h.value.sum() / CR), "cost_cr": _r(h.cost.sum() / CR),
        "unrealised_gain_cr": _r((h.value.sum() - h.cost.sum()) / CR),
        "xirr_pct": _r(x * 100 if x is not None else None),
        "direct_equity_cr": _r(eq / CR), "mutual_funds_cr": _r(mf / CR),
        "look_through": {"equity_cr": _r(c["equity"] / CR), "debt_in_funds_cr": _r(debt / CR), "cash_in_funds_cr": _r(cash / CR),
                         "not_looked_through_cr": _r(unmapped / CR), "companies": c["n"]},
        "holdings_count": int(len(h)),
    }
    data["holdings_basis"], cav = _holdings_basis(m)
    if unmapped > 0:
        cav.append("Some fund value is not looked through: no AMC portfolio disclosure loaded for those schemes.")
    if x is None:
        cav.append("XIRR not computable for this entity (no solvable cash-flow root).")
    return _emit("portfolio_summary", {"member": member}, data, cav)


@mcp.tool(annotations=RO)
def look_through_exposure(member: str = "ALL", top_n: int = 15) -> dict:
    """Stock-level exposure after looking through mutual funds into their disclosed holdings: direct holding,
    holding via funds, total, and % of look-through equity. Also concentration (HHI, top-10 share) and
    sector weights."""
    m = _member(member)
    top_n = max(1, min(int(top_n), 50))
    lt, *_ = E.look_through(m)
    c = E.conc(lt)
    tot = float(lt.total.sum()) or 1.0
    rows = [{"symbol": code, "company": _name(code), "sector": E.co_field(code, "sector"),
             "direct_cr": _r(r.direct / CR), "via_funds_cr": _r(r.via / CR), "total_cr": _r(r.total / CR),
             "pct_of_equity": _r(r.total / tot * 100)} for code, r in lt.head(top_n).iterrows()]
    sec: dict[str, float] = {}
    for code, v in lt.total.items():
        k = E.co_field(code, "sector")
        sec[k] = sec.get(k, 0.0) + v
    data = {"entity": m or "ALL", "top_exposures": rows,
            "concentration": {"hhi": _r(c["hhi"], 4), "effective_number_of_stocks": _r(c["eff_n"], 1),
                              "top10_pct": _r(c["top10"]), "largest_single_pct": _r(c["top_pct"]), "companies": c["n"]},
            "sector_weights_pct": {k: _r(v / tot * 100) for k, v in sorted(sec.items(), key=lambda kv: -kv[1])}}
    data["holdings_basis"], lag = _holdings_basis(m)
    return _emit("look_through_exposure", {"member": member, "top_n": top_n}, data,
                 lag + ["Fund holdings are as disclosed by each AMC for the latest month loaded; intra-month changes are not visible."])


@mcp.tool(annotations=RO)
def policy_check(member: str = "ALL") -> dict:
    """Compare the portfolio with the investment policy limits (single stock, sector, top-10, HHI, fund
    overlap, portfolio beta, weighted expense ratio). Returns each test with value, limit and status."""
    m = _member(member)
    P = E.POL
    lt, *_ = E.look_through(m)
    c = E.conc(lt)
    tot = float(lt.total.sum()) or 1.0
    tests = []

    def add(test, value, limit, breach, detail="", warning_only=False):
        # A figure that cannot be computed is never reported as compliant. A warning-grade limit (fund overlap: a cost
        # and duplication signal, not a concentration breach) is graded as the app grades it: ABOVE LIMIT, a warning.
        status = "NOT COMPUTABLE" if value is None else ("ABOVE LIMIT" if warning_only else "BREACH") if breach else "within limit"
        tests.append({"test": test, "value": value, "limit": limit, "status": status, "detail": detail})

    for code, r in lt.iterrows():
        pct = r.total / tot * 100
        if pct > P["max_single_stock_pct"]:
            add(f"Single stock: {_name(code)}", _r(pct), P["max_single_stock_pct"], True,
                f"direct {_r(r.direct / CR)} cr + via funds {_r(r.via / CR)} cr")
    if not any(t["test"].startswith("Single stock") for t in tests):
        add("Single stock: largest holding", _r(c["top_pct"]), P["max_single_stock_pct"], False)
    sec: dict[str, float] = {}
    for code, v in lt.total.items():
        sec[E.co_field(code, "sector")] = sec.get(E.co_field(code, "sector"), 0.0) + v
    top_sec = max(sec.items(), key=lambda kv: kv[1]) if sec else ("-", 0.0)
    add(f"Sector: {top_sec[0]}", _r(top_sec[1] / tot * 100), P["max_sector_pct"], top_sec[1] / tot * 100 > P["max_sector_pct"])
    add("Top-10 share of equity", _r(c["top10"]), P["max_top10_pct"], (c["top10"] or 0) > P["max_top10_pct"])
    add("HHI", _r(c["hhi"], 4), P["max_hhi"], (c["hhi"] or 0) > P["max_hhi"])
    beta = E.port_beta(lt)
    add("Portfolio beta (look-through equity)", _r(beta), P["max_portfolio_beta"], beta is not None and beta > P["max_portfolio_beta"],
        "stocks without 12 months of history are taken at beta 1")
    held = sorted(set(_holdings(m)[lambda d: d.asset_type == "MF"].instrument))
    for i, a in enumerate(held):
        for b in held[i + 1:]:
            o = E.overlap.get(f"{a}|{b}") if f"{a}|{b}" in E.overlap else E.overlap.get(f"{b}|{a}")
            if o is not None and o > P["max_pair_overlap_pct"]:
                add(f"Fund overlap: {E.SCH[a]['name']} / {E.SCH[b]['name']}", _r(o), P["max_pair_overlap_pct"], True,
                    "warning: two expense ratios paid for largely the same stocks", warning_only=True)
    mfh = _holdings(m)[lambda d: d.asset_type == "MF"]
    ters = [E.ter(r) for r in mfh.itertuples()]
    wter = None if not len(mfh) or any(t is None for t in ters) else sum(r.value * t for r, t in zip(mfh.itertuples(), ters)) / mfh.value.sum()
    add("Weighted expense ratio", _r(wter), P["max_weighted_ter_pct"], wter is not None and wter > P["max_weighted_ter_pct"],
        "" if wter is not None else "not computable: expense ratio missing for at least one held scheme")
    data = {"entity": m or "ALL", "tests": tests, "breaches": sum(t["status"] == "BREACH" for t in tests),
            "warnings": sum(t["status"] == "ABOVE LIMIT" for t in tests),
            "not_computable": sum(t["status"] == "NOT COMPUTABLE" for t in tests)}
    data["holdings_basis"], lag = _holdings_basis(m)
    return _emit("policy_check", {"member": member}, data,
                 lag + ["Limits come from data/config/policy.json and are set by the family's investment policy, not by regulation."])


@mcp.tool(annotations=RO)
def fund_report(scheme_id: str) -> dict:
    """Returns and risk for one mutual-fund scheme (Direct plan): 1Y and 3Y returns vs benchmark, volatility,
    Sharpe, Sortino, max drawdown, beta, alpha, tracking error, information ratio, capture ratios, rolling
    1Y beat rate, expense ratio, and its largest disclosed holdings."""
    s = _scheme(scheme_id)
    sc, f = E.SCH[s], E.fund.get(s) or {}
    pct = lambda k: _r(f.get(k) * 100) if f.get(k) is not None else None  # noqa: E731
    w = E.LATEST.get(s)
    top = [] if w is None else [{"symbol": code, "company": _name(code), "weight_pct": _r(v)}
                                for code, v in w.sort_values(ascending=False).head(10).items()]
    data = {"scheme_id": s, "name": sc["name"], "category": sc.get("category"), "amc": sc.get("amc"),
            "amfi_code_direct": sc.get("amfi_code"), "benchmark": sc.get("benchmark_name") or sc.get("benchmark"),
            "expense_ratio_direct_pct": _r(sc.get("ter_direct")), "expense_ratio_regular_pct": _r(sc.get("ter_regular")),
            "return_1y_pct": pct("r1y"), "cagr_3y_pct": pct("cagr3"), "benchmark_cagr_3y_pct": pct("bench3"),
            "volatility_pct": pct("vol"), "max_drawdown_pct": pct("mdd"), "sharpe": _r(f.get("sharpe")), "sortino": _r(f.get("sortino")),
            "beta": _r(f.get("beta")), "alpha_pct": pct("alpha"), "tracking_error_pct": pct("te"), "information_ratio": _r(f.get("ir")),
            "up_capture": _r(f.get("up_capture")), "down_capture": _r(f.get("down_capture")), "rolling_1y_beat_rate_pct": pct("roll_beat"),
            "portfolio_date": (E.PORT_DATES.get(s) or [None])[-1], "top_holdings": top,
            "manager_activity_latest_month": E.act.get(s)}
    cav = [f"Risk-free rate {E.POL['risk_free_pct']}% p.a. (policy input). Benchmarks are price indices, not total-return indices, "
           "so fund-vs-benchmark comparisons flatter the fund by roughly the index dividend yield."]
    cav += [w_ for w_ in E.META.get("warnings", []) if w_.startswith("Benchmark")]
    if not sc.get("ter_direct"):
        cav.append("Expense ratio not in the dataset for this scheme.")
    if w is None:
        cav.append("No AMC portfolio disclosure loaded: holdings unavailable.")
    return _emit("fund_report", {"scheme_id": scheme_id}, data, cav)


@mcp.tool(annotations=RO)
def fund_overlap(scheme_a: str, scheme_b: str) -> dict:
    """Portfolio overlap between two schemes (sum over common stocks of the smaller weight), plus the
    largest common holdings and the correlation of their monthly returns."""
    a, b = sorted([_scheme(scheme_a), _scheme(scheme_b)])
    if a == b:
        raise BadInput("Choose two different schemes.")
    o = E.overlap.get(f"{a}|{b}")
    wa, wb = E.LATEST.get(a), E.LATEST.get(b)
    common = []
    if wa is not None and wb is not None:
        idx = wa.index.intersection(wb.index)
        both = sorted(((code, float(min(wa[code], wb[code])), float(wa[code]), float(wb[code])) for code in idx), key=lambda t: -t[1])
        common = [{"symbol": c_, "company": _name(c_), "overlap_weight_pct": _r(m_), f"{a}_weight_pct": _r(x_), f"{b}_weight_pct": _r(y_)}
                  for c_, m_, x_, y_ in both[:10]]
    data = {"scheme_a": {"scheme_id": a, "name": E.SCH[a]["name"]}, "scheme_b": {"scheme_id": b, "name": E.SCH[b]["name"]},
            "overlap_pct": _r(o), "common_stocks": len(common) if wa is None or wb is None else int(len(wa.index.intersection(wb.index))),
            "largest_common_holdings": common, "return_correlation": _r(E.corr.get(f"{a}|{b}"), 3)}
    cav = [] if o is not None else ["Overlap not computable: a portfolio disclosure is missing for at least one scheme."]
    return _emit("fund_overlap", {"scheme_a": scheme_a, "scheme_b": scheme_b}, data, cav)


@mcp.tool(annotations=RO)
def company_report(symbol: str) -> dict:
    """Fundamentals for one listed company (NSE symbol or name): ratios (ROE, ROCE, margins, growth, leverage,
    cash conversion, Piotroski F-score, valuation), up to five years of statements in Rs crore, price
    statistics, and the family's direct + via-fund exposure."""
    code = _company(symbol)
    c = E.COS[code]
    rows = sorted([r for r in E.DS["financials"] if r["code"] == code], key=lambda r: r["fy"])[-5:]
    keep = ("fy", "revenue", "ebitda", "pbt", "pat", "cfo", "capex", "total_debt", "cash_eq", "net_worth", "total_assets")
    lt, *_ = E.look_through(None)
    tot = float(lt.total.sum()) or 1.0
    ex = lt.loc[code] if code in lt.index else None
    data = {"symbol": code, "company": c.get("name"), "isin": c.get("isin"), "sector": c.get("sector"), "industry": c.get("industry"),
            "is_financial": bool(c.get("is_financial")), "price": _r(c.get("price")), "market_cap_cr": _r(c.get("mcap_cr"), 0),
            "return_1y_pct": _r(E.stock_1y.get(code) * 100) if E.stock_1y.get(code) is not None else None,
            "beta": _r(E.stock_beta.get(code)), "promoter_pledge_pct": _r(c.get("pledge_pct")),
            "ratios": {k: _r(v, 2) for k, v in (E.RAT.get(code) or {}).items()},
            "financials_cr": [{k: (r.get(k) if k == "fy" else _r(r.get(k), 0)) for k in keep} for r in rows],
            "family_exposure": None if ex is None else {"direct_cr": _r(ex.direct / CR), "via_funds_cr": _r(ex.via / CR),
                                                         "total_cr": _r(ex.total / CR), "pct_of_equity": _r(ex.total / tot * 100)},
            "fund_manager_activity_latest_month": E.cons.get(code)}
    off = c.get("fin_official")
    if off:  # some lines replaced by the company's own audited figures (data/config/official_financials.json)
        data["audited_fields"] = {"fields": off.get("fields"), "years": off.get("years"), "basis": off.get("basis"), "source": off.get("source")}
        cav = [f"{', '.join(off.get('fields') or [])} for {', '.join(off.get('years') or [])} are the company's own audited figures "
               f"({off.get('basis')}; {off.get('source')}), used because the secondary source was wrong: {off.get('reason')} "
               "The other statement lines are from Yahoo Finance (secondary source)."]
    else:
        cav = ["Statements are consolidated annual figures from Yahoo Finance (secondary source), not yet verified against the "
               "company's annual report; definitions (e.g. total debt incl. leases, equity incl. minority interest) can differ."]
    if c.get("is_financial"):
        cav.append("Lender: ROCE, debt/equity and FCF do not apply; NPA and capital-adequacy data are not in this dataset.")
    if not rows:
        cav.append("No financial statements available for this company.")
    return _emit("company_report", {"symbol": symbol}, data, cav)


@mcp.tool(annotations=RO)
def tax_position(member: str) -> dict:
    """Indicative capital-gains position of one entity for the current tax year: realised and unrealised
    short- and long-term gains on listed equity and equity-oriented funds, tax if everything were sold today,
    and remaining long-term exemption. Amounts in Rs lakh."""
    m = _member(member)
    if m is None:
        raise BadInput("Tax is computed per assessee; pass a member_id, not 'ALL'.")
    t = E.tax[m]
    who = next(x for x in E.DS["members"] if x["member_id"] == m)
    P = E.POL
    data = {"entity": m, "name": who["name"], "assessee_type": who["type"], "tax_year": P["tax_year_label"],
            "realised_short_term_lakh": _r(t["realised_st"] / LAKH), "realised_long_term_lakh": _r(t["realised_lt"] / LAKH),
            "unrealised_short_term_lakh": _r(t["unrealised_st"] / LAKH), "unrealised_long_term_lakh": _r(t["unrealised_lt"] / LAKH),
            "tax_if_all_sold_lakh": _r(t["tax_if_all_sold"] / LAKH), "exemption_headroom_lakh": _r(t["harvest_headroom"] / LAKH),
            "rates": {"short_term_pct": P["stcg_rate_pct"], "long_term_pct": P["ltcg_rate_pct"], "long_term_exemption_lakh": _r(P["ltcg_exemption"] / LAKH),
                      "holding_period_months": P["lt_months"]},
            "provisions": "Income-tax Act, 2025: section 196 (short-term) and section 198 (long-term), formerly sections 111A and 112A "
                          "of the Income-tax Act, 1961 (ICAI Tabular Mapping of Sections, March 2026)."}
    return _emit("tax_position", {"member": member}, data,
                 ["Indicative only: before surcharge, 4% health and education cess and brought-forward losses; short-term losses "
                  "are set off against long-term gains, not the reverse. Confirm rates against the Finance Act in force."])


@mcp.tool(annotations=RO)
def stress_test(market_move_pct: float) -> dict:
    """Estimated change in the family's look-through equity for a market move of market_move_pct (between -60
    and +60), scaling each stock by its beta to the Nifty 500 (beta 1 where history is short)."""
    mv = float(market_move_pct)
    if not -60 <= mv <= 60:
        raise BadInput("market_move_pct must be between -60 and 60.")
    chg = E.stress_market(mv / 100)
    eq = float(E.lt_all.total.sum()) + float(E.unmapped_all)  # funds not looked through are stressed too (beta 1)
    data = {"market_move_pct": mv, "equity_cr": _r(eq / CR), "estimated_change_cr": _r(chg / CR),
            "estimated_change_pct_of_equity": _r(chg / eq * 100) if eq else None, "portfolio_beta": _r(E.port_beta(E.lt_all))}
    return _emit("stress_test", {"market_move_pct": market_move_pct}, data,
                 ["Linear beta scaling: ignores correlation breakdowns, liquidity and the debt and cash inside funds.",
                  "Funds without a portfolio disclosure are assumed fully equity at beta 1."])


@mcp.tool(annotations=RO)
def data_provenance() -> dict:
    """Where the data came from and how complete it is: sources, build time, AMC files loaded (with download
    time and SHA-256), schemes without a portfolio disclosure, and data warnings."""
    man = ROOT / "data" / "amc_portfolios" / "_sources.csv"
    files = []
    if man.exists():
        import csv
        files = [{"file": r["file"], "month": r["month"], "url": r["url"], "downloaded_at": r["downloaded_at"], "sha256": r["sha256"][:16] + "..."}
                 for r in csv.DictReader(man.open(encoding="utf-8"))]
    data = {"valuation_date": AS_ON, "dataset_built_at": E.META.get("built_at"), "sources": E.META.get("sources"),
            "note": E.META.get("note"), "warnings": E.META.get("warnings", []),
            "schemes_without_disclosure": [f"{s} {E.SCH[s]['name']}" for s in sorted(E.SCH) if s not in E.LATEST],
            "amc_files": files}
    return _emit("data_provenance", {}, data)


# ------------------------------------------------------------------ QC gate
NUM = re.compile(r"(?<![\w.])[-−–]?\d[\d,]*(?:\.\d+)?")
SKIP_BEFORE = re.compile(r"(section|sections|sec\.|§|\bfy|tax year|as on|as at|\band|nifty|sensex|bse|s&p|midcap|smallcap|next)\s*$", re.I)  # "sections 196 and 198", "Nifty 500"
TOOLS = ("list_entities", "portfolio_summary", "look_through_exposure", "policy_check", "fund_overlap", "fund_report", "company_report",
         "tax_position", "stress_test", "data_provenance")
UNIT_NAMES = {"cr": "Rs crore", "lakh": "Rs lakh", "pct": "%", "rs": "Rs per unit", "ratio": "a ratio", "count": "a count", "any": "a number", "bare": "a plain number"}


def _note_unit(before: str, after: str) -> str:
    """Unit a note gives a figure, from the words around it."""
    if re.match(r"\s*(cr\b|crore)", after, re.I):
        return "cr"
    if re.match(r"\s*lakh", after, re.I):
        return "lakh"
    if re.match(r"\s*(%|per\s*cent|percent)", after, re.I):
        return "pct"
    if re.match(r"\s*(x\b|×)", after, re.I):
        return "ratio"
    if re.search(r"(rs\.?|₹|inr)\s*$", before, re.I):
        return "rs"
    return "bare"


def _restatements(entry: dict, note_unit: str) -> list[float]:
    """The values a returned figure may appear as, given the unit the note writes it in. Only unit-preserving
    conversions: crore <-> lakh, a fraction or ratio as a percentage. Anything else must be written as returned."""
    v, u = abs(entry["value"]), entry["unit"]
    if note_unit == "cr":
        return {"cr": [v], "lakh": [v / 100], "any": [v]}.get(u, [])
    if note_unit == "lakh":
        return {"lakh": [v], "cr": [v * 100], "any": [v]}.get(u, [])
    if note_unit == "pct":
        return {"pct": [v], "any": [v] + ([v * 100] if v <= 1 else []), "ratio": [v * 100] if v <= 1 else []}.get(u, [])
    if note_unit == "rs":
        return [v] if u in ("rs", "any") else []
    if note_unit == "ratio":
        return [v] if u in ("ratio", "any") else []
    if u == "pct":
        return [v] + ([v / 100] if v < 100 else [])  # a plain number: as returned, or a percentage written as a fraction
    return [v] if u in ("ratio", "count", "any", "rs") else []  # a plain number: as returned


def _clause(note: str, start: int, end: int) -> str:
    """The sentence the figure sits in (a bullet line is cut at sentence ends, not at decimal points)."""
    a = max(note.rfind("\n", 0, start), max((m.end() for m in re.finditer(r"[.;](\s|$)", note[:start])), default=-1) - 1)
    m = re.search(r"[.;](\s|$)|\n", note[end:])
    return note[a + 1:end + (m.start() if m else len(note) - end)]


def _local(note: str, start: int, end: int) -> str:
    """The words right next to a figure: back to the previous comma, colon, bracket or number, forward to the next.
    In "Rs 5.32 cr, or 13.02% of equity" the words "of equity" belong to 13.02, not to 5.32."""
    back = note[:start]
    cut = max([back.rfind(c) for c in ",;:(\n"] + [m.end() for m in NUM.finditer(back)] + [0])
    fwd = re.sub(r"\([^)\n]*\)", " ", note[end:])  # read past a bracketed aside: "Rs 4.62 cr of fund value (UTI, Kotak) is not looked through"
    stops = [i for i in [fwd.find(c) for c in ",;(\n"] if i >= 0] + [m.start() for m in NUM.finditer(fwd)] + \
            [m.start() for m in re.finditer(r"\.(\s|$)", fwd)] + [len(fwd)]
    return back[cut:] + " " + fwd[:min(stops)]


@mcp.tool(annotations=RO)
def verify_note(note: str) -> dict:
    """Quality-control gate. Pass the full text of a drafted note. Every figure is BOUND to one number a tool returned
    in this session: the value must match (within the note's rounding), the unit must match (Rs crore / lakh, %, a
    ratio or count; only crore<->lakh and fraction<->% conversions), the tool cited on that line in parentheses must be
    the one that returned it, and the words of the figure's sentence must name the field (e.g. 'beta', 'HDFC Bank',
    'overlap'). Returns traced figures with their source, UNTRACED figures with the reason (fix or remove them before
    the note is presented) and figures skipped as dates, section numbers or small counts."""
    traced, untraced, skipped = [], [], []
    text = note or ""
    for mt in NUM.finditer(text):
        tok = mt.group(0)
        before, after = text[max(0, mt.start() - 12):mt.start()], text[mt.end():mt.end() + 8]
        ctx = text[max(0, mt.start() - 40):mt.end() + 25].replace("\n", " ")
        raw = tok.replace(",", "").replace("−", "-").replace("–", "-")
        try:
            v = abs(float(raw))
        except ValueError:
            continue
        dec = len(raw.split(".")[1]) if "." in raw else 0
        is_int_small = dec == 0 and v <= 31 and not re.match(r"\s*(%|cr|crore|lakh|x|×)", after, re.I)
        is_year = dec == 0 and 1990 <= v <= 2100
        is_date = bool(re.match(r"[-/]\d", after)) or bool(re.search(r"\d[-/]$", before))
        if SKIP_BEFORE.search(before) or is_int_small or is_year or is_date:
            skipped.append({"figure": tok, "context": ctx})
            continue
        tol = 0.5 * 10 ** (-dec) + 1e-9
        unit = _note_unit(text[max(0, mt.start() - 6):mt.start()], after)
        line = text[text.rfind("\n", 0, mt.start()) + 1:(text.find("\n", mt.end()) + 1 or len(text) + 1) - 1]
        cited = {t for t in TOOLS if re.search(rf"\b{t}\b", line)}
        words = _tokens(re.sub(r"\b(" + "|".join(TOOLS) + r")\b", " ", _clause(text, mt.start(), mt.end())))
        same_value = [e for e in LEDGER if any(abs(abs(x) - v) <= tol for x in (e["value"], e["value"] * 100, e["value"] / 100, e["value"] / CR, e["value"] / LAKH))]
        in_unit = [e for e in LEDGER if any(abs(x - v) <= tol for x in _restatements(e, unit))]
        in_tool = [e for e in in_unit if not cited or e["tool"] in cited]
        bound = sorted(((len(words & e["labels"]), e) for e in in_tool if words & e["labels"]), key=lambda x: -x[0])
        if bound:
            e = bound[0][1]
            # the sentence must not describe a SIBLING field of the same record instead ("total" called "direct")
            near = _tokens(_local(text, mt.start(), mt.end()))
            other = next((x for x in LEDGER if x["tool"] == e["tool"] and x["record"] == e["record"] and x["path"] != e["path"]
                          and x["own"] and (near & x["own"]) and e["own_alias"] and not (near & e["own_alias"])), None)
            if other:
                untraced.append({"figure": tok, "context": ctx, "reason": (
                    f"The value is {e['tool']}:{e['path']}, but the sentence describes {other['path'].split('.')[-1]} "
                    f"({other['value']:g}) of the same record. Use the figure for what the sentence says, or reword it.")})
                continue
            traced.append({"figure": tok, "context": ctx, "source": f"{e['tool']}:{e['path']}", "unit": UNIT_NAMES[unit],
                           "matched_words": sorted(words & e["labels"])[:6]})
            continue
        from_cited = [e for e in same_value if not cited or e["tool"] in cited]
        if not same_value:
            why = "No tool returned this value in this session."
        elif from_cited and not any(e in in_tool for e in from_cited):
            why = (f"The value was returned as {UNIT_NAMES[from_cited[0]['unit']]} ({from_cited[0]['tool']}:{from_cited[0]['path']}), "
                   f"but the note writes it as {UNIT_NAMES[unit]}.")
        elif not in_unit:
            why = (f"The value was returned as {UNIT_NAMES[same_value[0]['unit']]} ({same_value[0]['tool']}:{same_value[0]['path']}), "
                   f"but the note writes it as {UNIT_NAMES[unit]}.")
        elif not in_tool:
            why = (f"Returned by {', '.join(sorted({e['tool'] for e in in_unit}))}, not by the tool cited on this line "
                   f"({', '.join(sorted(cited))}). Cite the tool the figure came from.")
        else:
            e = in_tool[0]
            why = (f"A tool returned this value ({e['tool']}:{e['path']}), but the sentence does not name that figure "
                   f"(expected words like: {', '.join(sorted(e['labels'])[:6])}). It may be a coincidence; state what the figure is.")
        untraced.append({"figure": tok, "context": ctx, "reason": why})
    data = {"passed": not untraced, "figures_checked": len(traced) + len(untraced), "traced": len(traced),
            "untraced": untraced, "skipped": len(skipped), "skipped_examples": skipped[:10],
            "evidence_numbers_in_session": len(LEDGER), "traced_detail": traced[:80]}
    cav = [] if LEDGER else ["No tool has returned data in this session yet, so nothing can be traced. Call the analysis tools first."]
    return _emit("verify_note", {"chars": len(note or "")}, data, cav)


# ------------------------------------------------------------------ prompt
@mcp.prompt(title="Investment-committee note")
def ic_note(question: str, member: str = "ALL") -> str:
    """A structured investment-committee note answering one question about the family portfolio."""
    return f"""Prepare an investment-committee note on: {question}
Entity: {member}

Use the LookThrough tools for every figure (start with list_entities and data_provenance). Structure:
1. Question and scope (entity, valuation date from the tools).
2. Key facts - each line tagged [FACT] or [CALC] with the tool it came from.
3. Analysis - tag interpretations [VIEW] and inputs [ASSUMPTION].
4. Policy position - results of policy_check.
5. Risks and what would change the conclusion.
6. Options for the committee with trade-offs. Do not recommend buying or selling; the committee decides.
7. Data limitations - from the caveats and data_provenance.

Quote figures exactly as returned, with units, and end each line with every tool its figures came from, in
parentheses, e.g. (fund_overlap; policy_check). Then call verify_note with the complete note; if any figure is
untraced, correct or remove it and verify again. Present the note only when verify_note passes, and state that it passed."""


if __name__ == "__main__":
    mcp.run("stdio")
