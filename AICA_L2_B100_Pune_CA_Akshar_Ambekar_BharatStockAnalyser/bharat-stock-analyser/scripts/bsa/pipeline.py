"""End-to-end orchestration: resolve, fetch, analyse, chart, write JSON, HTML and PDF."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from . import (__version__, charts, data, exchange, fundamentals, indicators, narrative, peers, report, scoring,
               valuation)
from .fmt import (clean, fmt_cr, fmt_num, fmt_pct, fmt_rs, fmt_x, median, num, pct_from_fraction)

DEFAULT_OUTDIR = os.environ.get("BSA_OUTPUT_DIR") or str(Path.home() / "Documents" / "Bharat-Stock-Reports")


def _peer_row(symbol: str, inf: dict, ret_1y: float | None) -> dict:
    return {
        "symbol": symbol.replace(".NS", "").replace(".BO", ""),
        "name": inf.get("longName") or inf.get("shortName") or symbol,
        "market_cap": num(inf.get("marketCap")),
        "price": num(inf.get("currentPrice")) or num(inf.get("regularMarketPrice")),
        "pe": num(inf.get("trailingPE")),
        "pb": num(inf.get("priceToBook")),
        "roe": pct_from_fraction(inf.get("returnOnEquity")),
        "op_margin": pct_from_fraction(inf.get("operatingMargins")),
        "div_yield": num(inf.get("dividendYield")),
        "return_1y": ret_1y,
    }


def consistency_checks(info: dict, fund: dict) -> list[str]:
    """Cross-check statement-derived figures against the source's own summary fields."""
    out = []
    last = fund["annual"][-1] if fund["annual"] else {}
    bv_src, bv_calc = num(info.get("bookValue")), last.get("bvps_adj")
    if bv_src and bv_calc and abs(bv_calc / bv_src - 1) > 0.15:
        out.append(f"Source inconsistency: balance-sheet equity implies book value of {fmt_rs(bv_calc)} per share, "
                   f"but the source reports {fmt_rs(bv_src)}. Statement-based ratios (ROE, P/B history) may be "
                   "affected; check the latest annual report.")
    roe_src, roe_calc = pct_from_fraction(info.get("returnOnEquity")), last.get("roe")
    if roe_src is not None and roe_calc is not None and abs(roe_src - roe_calc) > 3:
        out.append(f"ROE check: calculated {last['label']} ROE is {fmt_pct(roe_calc)} (average equity) while the "
                   f"source reports {fmt_pct(roe_src)} (trailing). Treat ROE-based scores with care.")
    return out


CRITICAL_DOWNLOADS = {
    "Company profile": "the company profile download failed, so analyst consensus, market data and sector are "
                       "missing.",
    "Annual income statement": "the annual income statement download failed.",
    "Quarterly results": "the quarterly results download failed.",
}


def _latest_period(fund: dict) -> date | None:
    ends = [pd.Timestamp(x["date"]).date() for x in (fund["quarters"][-1:] + fund["annual"][-1:])]
    return max(ends) if ends else None


def exchange_reasons(exch, fund: dict) -> list[str]:
    """Provisional reasons from the exchange record: results filed or considered but not in the data."""
    latest = _latest_period(fund)
    if exch is None or latest is None:
        return []
    out = []
    newest = exch.filings[0] if exch.filings else None
    if newest and date.fromisoformat(newest["period_end"]) > latest + pd.Timedelta(days=20):
        out.append(f"{newest['label']} results were filed with {exch.source or 'the exchange'} on {newest['filed']} "
                   "but are not in the model data.")
    last = exch.meetings.get("last")
    if last and not last.get("rescheduled"):
        qe = date.fromisoformat(last["quarter_end"])
        filed_through = date.fromisoformat(newest["period_end"]) if newest else None
        if qe > latest + pd.Timedelta(days=20) and (filed_through is None or filed_through < qe):
            out.append(f"The results board meeting on {last['date']} covered {last['quarter']}, which is not in the "
                       "model data.")
    return out


def data_checks(raw, fund: dict, today: date, exch=None) -> tuple[list[str], list[str], dict]:
    """Provisional reasons, extra warnings and the results freshness record.

    When the exchange layer answered, a quarter that is past its period end but not yet due is
    confirmed as not published (no web search needed), and results that were filed or
    considered at a board meeting but are missing from the data make the rating provisional.
    """
    reasons, warns = [], []
    from_filings = any(q.get("source", "").startswith("NSE") for q in fund["quarters"])
    for label, text in CRITICAL_DOWNLOADS.items():
        if label in raw.failed and not (label == "Quarterly results" and from_filings):
            reasons.append(text[0].upper() + text[1:])
    fresh = fundamentals.freshness(fund["quarters"], today, fund["annual"])
    ex_reasons = exchange_reasons(exch, fund)
    reasons += ex_reasons
    checked = bool(exch is not None and exch.checked)
    nxt = (exch.meetings.get("next") if checked else None) or {}
    fresh["exchange"] = {
        "checked": checked,
        "source": exch.source if exch is not None else None,
        "latest_filed": ({k: exch.filings[0][k] for k in ("label", "filed", "nature")} if checked and exch.filings
                         else None),
        "last_results_meeting": exch.meetings.get("last") if checked else None,
        "next_results_meeting": nxt or None,
    }
    confirmed = checked and not ex_reasons
    for x in fresh["missing"]:
        if x["overdue"]:
            reasons.append(f"{x['quarter']} results were due by {x['due_by']} but are not in the data"
                           f"{' and not filed with the exchange' if confirmed else ''}.")
        elif confirmed:
            when = f"; the results board meeting is scheduled for {nxt['date']}" if nxt.get("date") else ""
            warns.append(f"Exchange check: {x['quarter']} results are not yet published (legal deadline "
                         f"{x['due_by']}){when}.")
        else:
            warns.append(f"Freshness check: {x['quarter']} (period ended {x['period_end']}) results may already be "
                         f"published; the legal deadline is {x['due_by']}. The data stops at {fresh['latest_quarter']}.")
    if confirmed and not fresh["overdue"]:
        fresh["check_required"] = False
        fresh["confirmed_by_exchange"] = True
    qc = fund["quarter_changes"]
    if qc.get("missing"):
        warns.append(f"The source has no data for {', '.join(qc['missing'])}. Quarterly comparisons are matched by "
                     "date; trailing EPS uses the latest full year when four consecutive quarters are not available.")
    for q in fund["quarters"][-2:]:
        if q.get("one_off"):
            kind = "gain" if q["one_off"] > 0 else "charge"
            warns.append(f"{q['label']} includes an estimated one-off {kind} of Rs {fmt_cr(abs(q['one_off']))} cr "
                         f"before tax ({q['one_off_source']}); profit excluding it is Rs {fmt_cr(q.get('pat_norm'))} cr "
                         f"against Rs {fmt_cr(q.get('pat'))} cr reported.")
    return reasons, warns, fresh


def run(query: str, outdir: str | None = None, assumptions: dict | None = None, make_pdf: bool = True,
        today: date | None = None) -> dict:
    res = data.resolve(query)
    raw = data.fetch(res["symbol"], res["exchange"])
    info = raw.info
    base = res["symbol"].split(".")[0]
    warnings = list(raw.warnings)
    today = today or datetime.now(data.IST).date()

    cmp = num(info.get("currentPrice")) or num(info.get("regularMarketPrice")) or float(raw.ohlc["Close"].iloc[-1])
    financial = fundamentals.is_financial(info, raw.income)

    # Exchange filings: quarters filed with NSE replace or extend Yahoo's quarterly data.
    exch = exchange.fetch(res["symbol"], today)
    warnings += exch.warnings
    usable = [q for q in exch.quarters if financial or not q["is_bank"]]
    if usable:
        warnings += exchange.cross_check(raw.q_income, usable, raw.fx_to_inr)
        raw.q_income, raw.q_sources = exchange.merge_quarters(raw.q_income, usable, raw.fx_to_inr)

    fund = fundamentals.build(raw, financial)
    tech = indicators.technical_summary(raw.ohlc, raw.bench if not raw.bench.empty else None)

    warnings += consistency_checks(info, fund)
    reasons, more_warnings, fresh = data_checks(raw, fund, today, exch)
    warnings += more_warnings

    group = peers.group_for(base, info.get("industry"))
    peer_bases = peers.peers_for(base, group)
    peer_raw = data.fetch_peers(peer_bases)
    if peer_bases and not peer_raw:
        warnings.append(f"Peer data download failed for all {len(peer_bases)} peers; peer multiples are missing.")
    elif peer_bases and len(peer_raw) < len(peer_bases):
        warnings.append(f"Peer data was returned for {len(peer_raw)} of {len(peer_bases)} peers.")
    peer_rows = [_peer_row(r["symbol"], r, r.get("return_1y")) for r in peer_raw]
    peer_medians = {
        "pe": median(r["pe"] for r in peer_rows if r["pe"] and 0 < r["pe"] < 150),
        "pb": median(r["pb"] for r in peer_rows if r["pb"] and 0 < r["pb"] < 40),
        "roe": median(r["roe"] for r in peer_rows),
        "return_1y": median(r["return_1y"] for r in peer_rows),
    }
    if not group:
        warnings.append("No curated peer group for this stock; peer comparison and peer multiples are skipped.")
    subject_row = _peer_row(res["symbol"], info, tech["returns"].get("1y"))
    subject_row["is_subject"] = True
    if subject_row["roe"] is None and fund["annual"]:
        subject_row["roe"] = fund["annual"][-1].get("roe")

    sector = peers.sector_index_for(group)
    sector_series = data.fetch_sector_index(sector[0]) if sector else None

    val = valuation.value(cmp, info, fund, tech, peer_medians, assumptions)
    sc = scoring.scorecard(fund, val, tech)
    rating_inputs = {"upside": val.get("upside"), "composite": sc.get("composite"),
                     "methods_used": val["methods_used"], "dispersion": val.get("dispersion"),
                     "provisional_reasons": reasons, "conflicts": val.get("excluded_conflicts", [])}
    rt = scoring.rating(**rating_inputs)

    if exch.shareholding:
        holdings = dict(exch.shareholding)
    else:
        ins = pct_from_fraction(info.get("heldPercentInsiders"))
        inst = pct_from_fraction(info.get("heldPercentInstitutions"))
        holdings = {"source": "Yahoo Finance", "insiders": ins, "institutions": inst,
                    "public_other": (100 - ins - inst) if ins is not None and inst is not None else None}

    meta = {
        "query": query,
        "symbol": res["symbol"],
        "nse_symbol": base,
        "bse_code": exch.bse_code,
        "exchange": res["exchange"],
        "matched_by": res["matched_by"],
        "name": info.get("longName") or info.get("shortName") or base,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "peer_group": group,
        "sector_index": sector[1] if sector else None,
        "website": info.get("website"),
        "business": info.get("longBusinessSummary"),
        "employees": info.get("fullTimeEmployees"),
        "fetched_at": raw.fetched_at,
        "price_date": raw.ohlc.index[-1].strftime("%d-%b-%Y"),
        "report_date": datetime.now(data.IST).strftime("%d %B %Y"),
        "generator": f"Bharat Stock Analyser v{__version__}",
        "is_financial": financial,
    }
    price = {
        "cmp": cmp,
        "prev_close": num(info.get("previousClose")),
        "day_change": (cmp / num(info["previousClose"]) - 1) * 100 if num(info.get("previousClose")) else None,
        "high_52w": tech.get("high_52w"),
        "low_52w": tech.get("low_52w"),
        "market_cap": val["multiples"]["market_cap"],
        "shares": fund["shares"],
        "value_3m_avg": tech.get("value_3m_avg"),
        "nifty": num(raw.bench.iloc[-1]) if not raw.bench.empty else None,
        "sensex": raw.sensex_last,
        "face_value": None,
    }
    story = narrative.build(meta, price, fund, val, tech, sc, rt, {"rows": peer_rows, "medians": peer_medians},
                            holdings)

    stem = f"{base.replace('&', 'and')}_{datetime.now(data.IST).strftime('%Y%m%d')}"
    out = Path(outdir or DEFAULT_OUTDIR).expanduser()
    chart_dir = out / f"{stem}_charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    close = raw.ohlc["Close"].dropna()
    adj = raw.ohlc["Adj Close"].dropna() if "Adj Close" in raw.ohlc else close
    chart_paths = {}

    def make(name, fn, *args):
        try:
            chart_paths[name] = fn(*args, str(chart_dir / f"{name}.png"))
        except Exception as exc:  # a chart failure must not stop the report
            warnings.append(f"Chart '{name}' could not be drawn ({type(exc).__name__}: {exc}).")

    make("price", charts.price_chart, raw.ohlc, indicators.sma(close, 50), indicators.sma(close, 200))
    rel = [(base, adj), ("Nifty 50", raw.bench)]
    if sector_series is not None and not sector_series.empty:
        rel.append((sector[1], sector_series))
    make("relative", charts.relative_chart, rel)
    if fund["annual"]:
        make("annual", lambda a, p: charts.annual_bars(a, p, financial), fund["annual"])
        make("ratios", lambda a, p: charts.ratio_lines(a, p, financial), fund["annual"])
        cur = val["multiples"]["pb"] if financial else val["multiples"]["pe"]
        make("multiples", lambda a, p: charts.multiple_history(a, cur, p, financial), fund["annual"])
    if fund["quarters"]:
        make("quarterly", lambda q, p: charts.quarterly_bars(q, p, financial), fund["quarters"])
    make("valuation", charts.football_field, val, tech)
    make("scorecard", charts.scorecard_bars, sc["pillars"], sc.get("composite"))
    make("momentum", charts.momentum_chart, close, indicators.rsi(close), indicators.macd(close))

    tech_out = {k: v for k, v in tech.items()}
    analysis = clean({
        "meta": meta,
        "price": price,
        "holdings": holdings,
        "technical": tech_out,
        "fundamentals": fund,
        "peers": {"group": group, "rows": [subject_row] + peer_rows, "medians": peer_medians},
        "valuation": val,
        "scorecard": sc,
        "rating": rt,
        "rating_inputs": rating_inputs,
        "data_quality": {"failed_downloads": raw.failed, "freshness": fresh},
        "exchange": {
            "enabled": exchange.enabled(),
            "source": exch.source or None,
            "bse_code": exch.bse_code,
            "filings": [{k: f[k] for k in ("label", "nature", "filed", "revised")} for f in exch.filings[:8]],
            "quarters_used": [q["label"] for q in usable],
            "meetings": exch.meetings,
            "links": exch.links,
            "failed": exch.failed,
        },
        "narrative": story,
        "news": raw.news,
        "warnings": warnings,
        "charts": {k: os.path.relpath(v, out) for k, v in chart_paths.items()},
        "commentary": None,
        "files": {},
    })
    analysis["files"] = {"json": str(out / f"{stem}_analysis.json")}
    write_outputs(analysis, out, stem, make_pdf)
    return analysis


def write_outputs(analysis: dict, out: Path, stem: str, make_pdf: bool = True) -> dict:
    html_path = out / f"{stem}_report.html"
    html_path.write_text(report.render(analysis, out), encoding="utf-8")
    analysis["files"]["html"] = str(html_path)
    if make_pdf:
        pdf_path = out / f"{stem}_report.pdf"
        ok, msg = report.to_pdf(html_path, pdf_path)
        if ok:
            analysis["files"]["pdf"] = str(pdf_path)
        else:
            analysis["files"].pop("pdf", None)
            analysis["warnings"].append(f"PDF not produced: {msg}")
    json_path = out / f"{stem}_analysis.json"
    analysis["files"]["json"] = str(json_path)
    json_path.write_text(json.dumps(analysis, indent=1, ensure_ascii=False), encoding="utf-8")
    return analysis["files"]


def commentary_reasons(c: dict) -> list[str]:
    """Provisional reasons raised by Claude's research. They can only make the rating more cautious."""
    out = []
    nr = c.get("newer_results")
    if nr:
        out.append(f"Newer results ({nr['quarter']}, published {nr.get('date') or 'date not stated'}) are not in the "
                   "model data; the figures and target predate them.")
    for x in c.get("data_conflicts", []):
        out.append(f"Data conflict found in research: {x}")
    return out


def rerender(json_path: str, commentary: dict | None, make_pdf: bool = True) -> dict:
    """Re-render with commentary. No new download and no number changes; the rating gates are
    re-applied so that newer results or data conflicts found by Claude mark the rating provisional."""
    p = Path(json_path).expanduser().resolve()
    analysis = json.loads(p.read_text(encoding="utf-8"))
    if commentary is not None:
        analysis["commentary"] = validate_commentary(commentary)
    ri = analysis.get("rating_inputs")
    if ri is not None:
        inputs = dict(ri, provisional_reasons=list(ri.get("provisional_reasons", []))
                      + commentary_reasons(analysis.get("commentary") or {}))
        analysis["rating"] = scoring.rating(**inputs)
        analysis["narrative"] = narrative.build(
            analysis["meta"], analysis["price"], analysis["fundamentals"], analysis["valuation"],
            analysis["technical"], analysis["scorecard"], analysis["rating"],
            {"rows": analysis["peers"]["rows"][1:], "medians": analysis["peers"]["medians"]}, analysis["holdings"])
    analysis["warnings"] = [w for w in analysis.get("warnings", []) if not w.startswith("PDF not produced")]
    stem = p.name.replace("_analysis.json", "")
    write_outputs(analysis, p.parent, stem, make_pdf)
    return analysis


COMMENTARY_KEYS = {"headline": str, "summary": str, "highlights": list, "catalysts": list, "risks": list,
                   "business": str, "sources": list, "newer_results": dict, "data_conflicts": list}


def validate_commentary(c: dict) -> dict:
    out = {}
    for k, t in COMMENTARY_KEYS.items():
        v = c.get(k)
        if v is None:
            continue
        if not isinstance(v, t):
            raise ValueError(f"Commentary field '{k}' must be a {t.__name__}.")
        out[k] = v
    for s in out.get("sources", []):
        if not isinstance(s, dict) or "title" not in s:
            raise ValueError("Each source must be an object with 'title' and optional 'url' and 'date'.")
    nr = out.get("newer_results")
    if nr is not None and not nr.get("quarter"):
        raise ValueError("'newer_results' needs at least 'quarter' (for example Q2FY27), plus 'date' and 'source'.")
    if any(not isinstance(x, str) for x in out.get("data_conflicts", [])):
        raise ValueError("'data_conflicts' must be a list of strings.")
    unknown = set(c) - set(COMMENTARY_KEYS)
    if unknown:
        raise ValueError(f"Unknown commentary fields: {', '.join(sorted(unknown))}.")
    return out


def digest(a: dict) -> str:
    """Compact Markdown summary printed for Claude to read after a run."""
    m, p, v, r, sc, f = a["meta"], a["price"], a["valuation"], a["rating"], a["scorecard"], a["fundamentals"]
    t = a["technical"]
    L = []
    L.append(f"# {m['name']} ({m['exchange']}: {m['nse_symbol']})")
    L.append(f"Sector: {m['sector']} | Industry: {m['industry']} | Peer group: {m['peer_group'] or 'none'}")
    L.append(f"Price date: {m['price_date']} | Data fetched: {m['fetched_at']}")
    L.append("")
    prov = " PROVISIONAL" if r.get("provisional") else ""
    L.append(f"## Rating: {r['rating']}{prov} (conviction {r['conviction']})")
    L.append(f"CMP {fmt_rs(p['cmp'])} | Target {fmt_rs(v.get('target'))} | Upside "
             f"{fmt_pct(v.get('upside'), signed=True)} | Composite score "
             f"{fmt_num(sc.get('composite'), 0)}/100")
    for line in r["trace"]:
        L.append(f"- {line}")
    fresh = (a.get("data_quality") or {}).get("freshness") or {}
    nr = (a.get("commentary") or {}).get("newer_results")
    if nr:
        L.append("")
        L.append(f"## Results freshness: newer results found ({nr['quarter']}, {nr.get('date') or 'date not stated'})")
        L.append("The model data predates them, so the rating is provisional. Re-run the analysis once the data "
                 "source carries that quarter.")
    elif fresh.get("check_required"):
        L.append("")
        L.append("## Results freshness: CHECK REQUIRED")
        L.append(f"The data stops at {fresh['latest_quarter']}. Search the exchange filings for:")
        for x in fresh["missing"]:
            L.append(f"- {x['quarter']} (period ended {x['period_end']}, legal deadline {x['due_by']}"
                     f"{', OVERDUE' if x['overdue'] else ''})")
        L.append("If they are published, set `newer_results` in the commentary. The rating then becomes provisional "
                 "and cannot be BUY.")
    elif fresh.get("confirmed_by_exchange"):
        ex = fresh.get("exchange") or {}
        nxt = ex.get("next_results_meeting") or {}
        L.append("")
        L.append(f"## Results freshness: confirmed with {ex.get('source') or 'the exchange'}")
        lf = ex.get("latest_filed")
        L.append(f"The data runs to {fresh['latest_quarter']}"
                 + (f"; the latest results filed are {lf['label']} ({lf['nature'].lower()}, filed {lf['filed']})"
                    if lf else "")
                 + (f"; the next results board meeting is on {nxt['date']}" if nxt.get("date") else "") + ".")
        if fresh.get("missing"):
            L.append("Not yet published: " + ", ".join(f"{x['quarter']} (deadline {x['due_by']})"
                                                       for x in fresh["missing"]) + ".")
    ex = a.get("exchange") or {}
    h = a.get("holdings") or {}
    if ex.get("source") or h.get("promoter") is not None:
        L.append("")
        L.append(f"## Exchange filings ({ex.get('source') or 'not available'})")
        if ex.get("quarters_used"):
            L.append(f"Quarters taken from NSE results filings: {', '.join(ex['quarters_used'])} (these replace "
                     "the Yahoo figures for the same quarters).")
        for k, lab in (("last", "Last results board meeting"), ("next", "Next results board meeting")):
            mt = (ex.get("meetings") or {}).get(k)
            if mt:
                L.append(f"{lab}: {mt['date']} ({mt.get('quarter') or ''}"
                         f"{', rescheduled to a later date' if mt.get('rescheduled') else ''})")
        if h.get("promoter") is not None:
            tr = h.get("promoter_trend") or []
            trend = (f"; promoter {tr[0]['promoter']:.2f}% on {tr[0]['date']} to {tr[-1]['promoter']:.2f}% on "
                     f"{tr[-1]['date']}") if len(tr) >= 2 else ""
            L.append(f"Shareholding {h.get('as_of')}: promoter {fmt_num(h.get('promoter'), 2)}%, FII "
                     f"{fmt_num(h.get('fii'), 2)}%, DII {fmt_num(h.get('dii'), 2)}% (mutual funds "
                     f"{fmt_num(h.get('mutual_funds'), 2)}%), public and others {fmt_num(h.get('public_other'), 2)}%; "
                     f"promoter shares pledged {fmt_num(h.get('pledged_pct_of_promoter'), 2)}% of promoter holding"
                     f"{trend}")
    L.append("")
    L.append("## Valuation methods")
    L.append("| Method | Value | Weight | Used | Note |")
    L.append("|---|---|---|---|---|")
    for mm in v["methods"]:
        L.append(f"| {mm['name']} | {fmt_rs(mm['value'])} | {fmt_num(mm['weight'], 0)}% | "
                 f"{'yes' if mm['included'] else 'no'} | {mm.get('note') or ''} |")
    fwd = (f"; forward EPS {fmt_rs(v['forward_eps'])} (growth {fmt_pct(v.get('forward_growth'))})"
           if v.get("forward_eps") else "")
    L.append(f"Trailing EPS {fmt_rs(v.get('trailing_eps'))} ({v.get('trailing_basis') or '-'}){fwd}")
    for x in v.get("adjustments", []):
        L.append(f"- Adjustment: {x}")
    for x in v.get("excluded_conflicts", []):
        L.append(f"- Conflict: {x}")
    if v.get("scenarios"):
        L.append("Scenarios: " + "; ".join(f"{s['case']} {fmt_rs(s['value'])} ({fmt_pct(s['upside'], signed=True)}, "
                                           f"{s['multiple_name']} {fmt_x(s['multiple'])})" for s in v["scenarios"]))
    mu = v["multiples"]
    L.append(f"Multiples: P/E {fmt_x(mu.get('pe'))} (own median {fmt_x(f.get('pe_history_median'))}, peers "
             f"{fmt_x(a['peers']['medians'].get('pe'))}) | P/B {fmt_x(mu.get('pb'), 2)} | EV/EBITDA "
             f"{fmt_x(mu.get('ev_ebitda'))} | PEG {fmt_x(mu.get('peg'), 2)} | FCF yield {fmt_pct(mu.get('fcf_yield'))} "
             f"| Div yield {fmt_pct(v.get('dividend_yield'))}")
    coc = v["cost_of_capital"]
    L.append(f"Cost of equity {fmt_pct(coc['cost_of_equity'])}, WACC {fmt_pct(coc['wacc'])}, beta used "
             f"{fmt_num(coc['beta_used'], 2)}")
    L.append("")
    L.append("## Scorecard")
    for pl in sc["pillars"]:
        mets = "; ".join(f"{x['metric']} {x['display']}" for x in pl["metrics"] if x["score"] is not None)
        L.append(f"- {pl['pillar']} ({pl['weight']}%): {fmt_num(pl['score'], 0)} | {mets}")
    L.append("")
    L.append("## Annual financials (Rs crore)")
    ann = f["annual"]
    if ann:
        L.append("| Item | " + " | ".join(x["label"] for x in ann) + " |")
        L.append("|---" * (len(ann) + 1) + "|")
        rows = [("Revenue", "revenue", "cr"), ("EBITDA excl. other income", "ebitda", "cr"),
                ("Other income", "other_income", "cr"), ("One-offs pre-tax (est.)", "one_off", "cr"),
                ("Net profit to owners", "pat", "cr"), ("Net profit excl. one-offs", "pat_norm", "cr"),
                ("EPS excl. one-offs (Rs)", "eps_norm", "rs"), ("ROE %", "roe", "pct"), ("ROCE %", "roce", "pct"),
                ("Net debt/equity", "net_debt_equity", "x"), ("CFO", "cfo", "cr"), ("FCF", "fcf", "cr"),
                ("FY-end P/E", "pe", "x")]
        for lab, k, kind in rows:
            vals = []
            for x in ann:
                val = x.get(k)
                vals.append(fmt_cr(val) if kind == "cr" else fmt_num(val, 1) if kind in ("rs", "pct")
                            else fmt_num(val, 2))
            L.append(f"| {lab} | " + " | ".join(vals) + " |")
    g = f["growth"]
    if g.get("years"):
        L.append(f"CAGR {g['from']} to {g['to']}: revenue {fmt_pct(g.get('revenue'))}, PAT {fmt_pct(g.get('pat'))}, "
                 f"EPS {fmt_pct(g.get('eps'))}")
    qc = f["quarter_changes"]
    if qc.get("latest"):
        L.append(f"Latest quarter {qc['latest']} (QoQ vs {qc.get('prev') or 'n/a'}, YoY vs {qc.get('year_ago') or 'n/a'}): "
                 f"revenue QoQ {fmt_pct(qc['qoq'].get('revenue'))}, YoY {fmt_pct(qc['yoy'].get('revenue'))}; "
                 f"reported PAT YoY {fmt_pct(qc['yoy'].get('pat'))}; PAT excl. one-offs YoY "
                 f"{fmt_pct(qc['yoy'].get('pat_norm'))}")
        L.append("| Quarter | Revenue | EBITDA excl. OI | Other income | One-off pre-tax | PAT | PAT excl. one-offs "
                 "| Source |")
        L.append("|---|---|---|---|---|---|---|---|")
        for q in f["quarters"]:
            L.append(f"| {q['label']} | {fmt_cr(q.get('revenue'))} | {fmt_cr(q.get('ebitda'))} | "
                     f"{fmt_cr(q.get('other_income'))} | {fmt_cr(q.get('one_off'))} | {fmt_cr(q.get('pat'))} | "
                     f"{fmt_cr(q.get('pat_norm'))} | {q.get('source') or 'Yahoo Finance'} |")
    L.append("")
    L.append("## Technicals")
    L.append(f"Returns: 1m {fmt_pct(t['returns'].get('1m'))}, 3m {fmt_pct(t['returns'].get('3m'))}, "
             f"1y {fmt_pct(t['returns'].get('1y'))} | Nifty 1y {fmt_pct(t.get('bench_returns', {}).get('1y'))}")
    for s in t["signals"]:
        L.append(f"- {s['indicator']}: {s['reading']} ({s['signal']})")
    lv = t.get("levels", {})
    L.append(f"Supports: {', '.join(fmt_rs(x) for x in lv.get('supports', [])) or '-'} | Resistances: "
             f"{', '.join(fmt_rs(x) for x in lv.get('resistances', [])) or '-'}")
    L.append("")
    L.append("## Data-backed positives")
    L += [f"- {x}" for x in a["narrative"]["positives"]] or ["- none triggered"]
    L.append("## Data-backed concerns")
    L += [f"- {x}" for x in a["narrative"]["concerns"]] or ["- none triggered"]
    if a["peers"]["rows"]:
        L.append("")
        L.append("## Peers")
        L.append("| Symbol | Mcap Rs cr | P/E | P/B | ROE % | 1y % |")
        L.append("|---|---|---|---|---|---|")
        for pr in a["peers"]["rows"]:
            L.append(f"| {pr['symbol']}{' (subject)' if pr.get('is_subject') else ''} | {fmt_cr(pr['market_cap'])} | "
                     f"{fmt_num(pr['pe'], 1)} | {fmt_num(pr['pb'], 2)} | {fmt_num(pr['roe'], 1)} | "
                     f"{fmt_num(pr['return_1y'], 1)} |")
    if a.get("news"):
        L.append("")
        L.append("## Recent headlines (source feed)")
        L += [f"- {n['date'] or ''} {n['publisher'] or ''}: {n['title']}" for n in a["news"][:6]]
    if a.get("warnings"):
        L.append("")
        L.append("## Data warnings")
        L += [f"- {w}" for w in a["warnings"]]
    L.append("")
    L.append("## Files")
    for k, path in a["files"].items():
        L.append(f"- {k}: {path}")
    return "\n".join(L)
