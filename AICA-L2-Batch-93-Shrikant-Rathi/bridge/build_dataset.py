"""
Assemble the LookThrough dataset from real market data (cached raw fetches)
and the dummy family template, then embed it into the offline app.

    python lookthrough_bridge.py refresh     (fetch + build)
    python lookthrough_bridge.py build       (build from cache only, no network)
"""
import csv
from datetime import date

import ledger
import sources as S
from common import (APP_OUT, APP_SRC, CACHE, LIVE, VERSION, config, fy_label, is_equity_isin, isin_check_digit_ok, load_json, log,
                    month_ends, now_iso, save_json, valuation_date)

# Order matters: the first sector whose keyword appears wins. Healthcare is checked before IT, and IT has no
# bare "technology", because AMC industry labels such as "Pharmaceuticals & Biotechnology" contain that word.
SECTOR_KEYWORDS = [
    ("Financial Services", ["bank", "finance", "insurance", "capital market", "nbfc", "financial", "asset management", "broking", "housing finance", "exchange"]),
    ("Healthcare", ["pharma", "healthcare", "hospital", "diagnostic", "drug", "medical", "biotech"]),
    ("Information Technology", ["software", "it -", "it-", "information technology", "computers", "it services", "it enabled"]),
    ("Automobile", ["auto", "tyre", "vehicle", "tractor"]),
    ("FMCG", ["fmcg", "food", "beverage", "personal product", "household", "tobacco", "consumer non durable", "agricultural food"]),
    ("Oil, Gas & Energy", ["oil", "gas", "petroleum", "refiner", "energy"]),
    ("Power", ["power", "electric util"]),
    ("Metals & Mining", ["metal", "steel", "mining", "aluminium", "ferrous", "coal", "minerals"]),
    ("Construction Materials", ["cement", "construction material"]),
    ("Capital Goods", ["capital goods", "industrial", "engineering", "electrical equipment", "aerospace", "defence", "construction", "cables", "machinery", "plastic"]),
    ("Telecommunication", ["telecom"]),
    ("Chemicals", ["chemical", "fertili", "agrochem", "pesticide", "paints" ]),
    ("Consumer Durables", ["consumer durable", "durables", "jewel", "electronics"]),
    ("Realty", ["realty", "real estate"]),
    ("Consumer Services", ["retail", "consumer services", "leisure", "hotel", "e-commerce", "internet", "media", "entertainment", "textile", "apparel"]),
    ("Services", ["transport", "logistic", "port", "airline", "shipping", "services"]),
]
# What each Yahoo ticker actually tracks. indices.json lists fallbacks per benchmark, so the series is labelled
# from the ticker that returned data, never from the benchmark it stands in for.
TICKER_INDEX_NAME = {"^NSEI": "Nifty 50", "^CRSLDX": "Nifty 500", "^NSEMDCP50": "Nifty Midcap 50",
                     "NIFTY_MIDCAP_100.NS": "Nifty Midcap 100", "^CNXSC": "Nifty Smallcap 100",
                     "NIFTY_SMLCAP_100.NS": "Nifty Smallcap 100", "^NSEBANK": "Nifty Bank"}

YAHOO_SECTOR = {"Financial Services": "Financial Services", "Technology": "Information Technology", "Healthcare": "Healthcare",
                "Consumer Cyclical": "Consumer Services", "Consumer Defensive": "FMCG", "Energy": "Oil, Gas & Energy", "Utilities": "Power",
                "Basic Materials": "Metals & Mining", "Industrials": "Capital Goods", "Communication Services": "Telecommunication", "Real Estate": "Realty"}


def sector_from_text(t):
    t = (t or "").lower()
    for sec, kws in SECTOR_KEYWORDS:
        if any(k in t for k in kws):
            return sec
    return "Others"


def issuer_equity_index(by_isin):
    """{issuer prefix: NSE symbol} for Indian equity shares on NSE's list. An Indian ISIN is IN + E + 4-character issuer
    code + 2-digit security type (01 = equity shares) + 2-digit serial + check digit, so INE419M01027 and INE419M01035
    are the same issuer's equity share before and after an ISIN change (e.g. a split). Issuers with more than one
    listed equity line are left out: ambiguous, so never guessed."""
    idx = {}
    for isin, sym in by_isin.items():
        if len(isin) == 12 and isin.startswith("INE") and isin[7:9] == "01":
            idx.setdefault(isin[:7], set()).add(sym)
    return {k: next(iter(v)) for k, v in idx.items() if len(v) == 1}


def cap_class(mcap_cr, pol):
    if mcap_cr is None:
        return "Unclassified"
    return "Large" if mcap_cr >= pol["large_cap_min_cr"] else "Mid" if mcap_cr >= pol["mid_cap_min_cr"] else "Small"


def build(fetch=True, progress=lambda m: None):
    t0 = now_iso()
    uni, schemes_cfg, idx_cfg, fam, pol = config("universe"), config("schemes"), config("indices"), config("family"), config("policy")
    schemes_cfg = [{**x, "source": "config"} for x in schemes_cfg] + [{**x, "source": "user"} for x in ledger.load()["schemes"]]  # user-added schemes (data/user)
    extra = load_json(CACHE.parent / "config" / "user_universe.json", []) or []
    known = {u["symbol"] for u in uni}
    uni = uni + [u for u in extra if u["symbol"] not in known]  # legacy: companies fetched before they were kept in data/user
    user_cos = ledger.load()["companies"]  # listed companies added in the app (data/user)
    user_syms = {c["symbol"] for c in user_cos}
    known = {u["symbol"] for u in uni}
    uni = uni + [{"symbol": c["symbol"], "name": c["name"], "sector": c["sector"], "industry": c.get("industry", "")} for c in user_cos if c["symbol"] not in known]
    # An offline rebuild (after an entry, or on a fresh clone) keeps the valuation date of the data it already has:
    # without fetching there are no newer prices. Only a refresh moves to the latest completed month-end.
    cur = None if fetch else load_json(LIVE / "dataset.json")
    as_on = date.fromisoformat(cur["meta"]["as_on"]) if cur and (cur.get("meta") or {}).get("as_on") else valuation_date()
    dates = month_ends(as_on, 37)
    D = [d.isoformat() for d in dates]
    warnings = []

    progress("NSE equity list")
    by_sym, by_isin = S.nse_equity_list(refresh=False)
    if not by_sym:
        warnings.append("NSE equity list unavailable: ISINs of the research universe could not be confirmed.")

    # ---------- schemes and NAV history
    progress("AMFI scheme codes")
    navall = S.amfi_navall() if fetch else S.amfi_navall()
    schemes, nav_rows = [], []
    for s in schemes_cfg:
        codes = {"direct": s.get("amfi_code_direct"), "regular": s.get("amfi_code_regular")}
        names = {}
        if navall and not (codes["direct"] and codes["regular"]):
            r = S.resolve_scheme(s, navall)
            for plan in ("direct", "regular"):
                if not codes[plan] and r.get(plan):
                    codes[plan], names[plan] = r[plan]["code"], r[plan]["name"]
        series = {}
        for plan in ("direct", "regular"):
            if not codes[plan]:
                continue
            progress(f"NAV history {s['name']} ({plan})")
            raw = S.mf_nav_history(codes[plan])
            m = S.nav_monthly(raw, dates)
            if raw and not names.get(plan):
                names[plan] = raw.get("meta", {}).get("scheme_name")
            if sum(v is not None for v in m) >= 13:
                series[plan.capitalize()] = m
        if "Direct" not in series:
            warnings.append(f"{s['name']}: no Direct-plan NAV history found (AMFI code {codes['direct']}); scheme skipped.")
            continue
        for plan, vals in series.items():
            for d, v in zip(D, vals):
                if v is not None:
                    nav_rows.append({"date": d, "scheme_id": s["scheme_id"], "plan": plan, "nav": v})
        schemes.append({"scheme_id": s["scheme_id"], "name": s["name"], "amc": s["amc"], "category": s["category"], "benchmark": s["benchmark"],
                        "amfi_code": codes["direct"], "amfi_code_regular": codes["regular"], "amfi_name": names.get("direct"), "amfi_name_regular": names.get("regular"),
                        "ter_direct": s.get("ter_direct"), "ter_regular": s.get("ter_regular"), "aum_cr": s.get("aum_cr"),
                        "has_regular": "Regular" in series, "source": s["source"], "inception": None, "fund_manager": None, "exit_load": s.get("exit_load"), "riskometer": None,
                        # Growth-option ISINs from AMFI, so a CAS row can be matched exactly (an IDCW option has another ISIN)
                        "isin_direct": next((r["isin_growth"] for r in navall or [] if r["code"] == codes["direct"] and r.get("isin_growth")), None),
                        "isin_regular": next((r["isin_growth"] for r in navall or [] if r["code"] == codes["regular"] and r.get("isin_growth")), None)})
    sids = {s["scheme_id"] for s in schemes}

    # ---------- AMC portfolios (applied by the user)
    applied = load_json(CACHE / "portfolios_applied.json", []) or []
    issuer_idx, remapped = issuer_equity_index(by_isin), {}  # ISIN changes (old ISIN in an earlier month's file)
    port_rows, scheme_mix, sec_seen = [], {}, {}
    for p in applied:
        if p.get("scheme_id") not in sids or not p.get("portfolio_date") or p["portfolio_date"] > D[-1]:
            continue
        eq = sum(h["weight"] for h in p["holdings"] if h["class"] in ("equity", "foreign_equity"))
        oth = sum(h["weight"] for h in p["holdings"] if h["class"] == "debt_other")
        scheme_mix[(p["scheme_id"], p["portfolio_date"])] = (eq, oth)
        agg = {}
        for h in p["holdings"]:
            if h["class"] not in ("equity", "foreign_equity"):
                continue
            code = by_isin.get(h["isin"])
            if not code and h["isin"].startswith("INE") and h["isin"][7:9] == "01" and h["isin"][:7] in issuer_idx:
                # an old ISIN of a listed company (e.g. before a split): the same issuer's current equity share
                code = issuer_idx[h["isin"][:7]]
                remapped.setdefault(h["isin"], f"{h['isin']} ({h['name']}) read as {code}: the same issuer's equity share under its current ISIN")
            code = code or h["isin"]
            agg.setdefault(code, {"w": 0.0, "isin": h["isin"]})["w"] += h["weight"]
            sec_seen.setdefault(code, {"isin": h["isin"], "name": h["name"], "industry": h["industry"], "foreign": h["class"] == "foreign_equity"})
        for code, a in agg.items():
            port_rows.append({"portfolio_date": p["portfolio_date"], "scheme_id": p["scheme_id"], "code": code, "isin": a["isin"], "weight_pct": round(a["w"], 4)})
    port_dates = sorted({r["portfolio_date"] for r in port_rows})
    if not port_rows:
        warnings.append("No AMC portfolio files applied yet: look-through, overlap and fund-manager activity need them.")
    for s in schemes:
        ds = sorted(d for (sid, d) in scheme_mix if sid == s["scheme_id"])
        if ds:
            eq, oth = scheme_mix[(s["scheme_id"], ds[-1])]
            s.update(equity_pct=round(eq, 2), debt_pct=round(oth, 2), cash_pct=round(max(0.0, 100 - eq - oth), 2), portfolio_date=ds[-1])
        else:
            s.update(equity_pct=None, debt_pct=None, cash_pct=None, portfolio_date=None)
            warnings.append(f"{s['name']}: no portfolio file applied.")
    # AMCs publish a month's portfolio within about 10 days of month-end: until then the latest file is a month older than
    # the prices. Look-through still uses it (the latest disclosure is the best available), but it is said, never hidden.
    behind = [s for s in schemes if s["portfolio_date"] and s["portfolio_date"][:7] < D[-1][:7]]
    if behind:
        warnings.append(f"Fund holdings older than the prices: {len(behind)} of {len(schemes)} schemes are looked through on an earlier "
                        f"month's disclosure ({', '.join(sorted({s['portfolio_date'] for s in behind}))}) while prices and NAVs are at {D[-1]}. "
                        "Add the new AMC files when they are published.")

    for msg in remapped.values():
        warnings.append(f"ISIN change: {msg}.")
    # ---------- securities to price
    codes = [u["symbol"] for u in uni]
    for code, v in sec_seen.items():
        if code not in codes and not v["foreign"] and not code.startswith(("INE", "IN9")) and code in by_sym:
            codes.append(code)
    fam_codes = {e[1] for e in fam["eq"]}
    missing_fam = fam_codes - set(codes)
    codes += sorted(missing_fam)
    tickers = [S.yahoo_ticker(c) for c in codes]
    idx_tickers = sorted({t for v in idx_cfg.values() for t in v["yahoo"]})
    progress(f"Prices for {len(tickers)} stocks and {len(idx_tickers)} indices")
    start = date(dates[0].year, dates[0].month, 1).replace(day=1)
    px_cache = S.yahoo_prices(tickers + idx_tickers, start=start, end=date.today()) if fetch else S.price_cache()

    def monthly(tk):
        pts = (px_cache or {}).get(tk, {}).get("points") or []
        return S.monthly_from_daily([(date.fromisoformat(d), v) for d, v in pts], dates)

    progress("Market capitalisation")
    mc = S.yahoo_market_caps(tickers) if fetch else load_json(CACHE / "yahoo_mcap.json", {})

    # ---------- research universe fundamentals (fetched in parallel, then read from cache)
    fin_rows, cos, price_rows = [], [], []
    uni_map = {u["symbol"]: u for u in uni}
    if fetch:
        from concurrent.futures import ThreadPoolExecutor
        done = [0]

        def pre(c):
            try:
                S.yahoo_company(c)
            except Exception as e:  # noqa: BLE001
                log.warning("%s financials: %s", c, e)
            done[0] += 1
            progress(f"Financials {done[0]}/{len(uni_map)}")

        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(pre, list(uni_map)))
    for i, code in enumerate(codes):
        tk = S.yahoo_ticker(code)
        m = monthly(tk)
        if sum(v is not None for v in m) < 13:
            if code in uni_map or code in fam_codes:
                warnings.append(f"{code}: price history unavailable from Yahoo ({tk}).")
            continue
        # forward-fill short gaps (suspensions) so month-end valuations exist
        last = None
        for j in range(len(m)):
            if m[j] is None and last is not None:
                m[j] = last
            last = m[j] if m[j] is not None else last
        for d, v in zip(D, m):
            if v is not None:
                price_rows.append({"date": d, "code": code, "close": round(v, 2)})
        u = uni_map.get(code)
        info, years, divs = {}, [], {}
        if u:
            co = S.company_cache(tk)
            if co:
                info, years = co.get("info") or {}, co.get("years") or []
                divs = co.get("dividends_by_fy") or {}
                if not years:
                    warnings.append(f"{code}: Yahoo returned no financial statements; the company is priced but not scored.")
            else:
                warnings.append(f"{code}: financial statements unavailable.")
        mcv = (mc or {}).get(tk) or {}
        shares = info.get("sharesOutstanding") or mcv.get("shares")
        price = m[-1]
        mcap_cr = shares * price / 1e7 if shares and price else (mcv.get("market_cap") / 1e7 if mcv.get("market_cap") else None)
        # Statements must be in rupees. Yahoo's financialCurrency is not reliable on its own (HCLTECH says USD but
        # reports INR), so a non-INR flag is acted on only when the scale confirms it: revenue implausibly small
        # against market capitalisation (price-to-sales above 50). Such statements are excluded, never mis-stated.
        cur = (info.get("financialCurrency") or "INR").upper()
        fin_excluded = None  # why statements were left out (the app explains it instead of offering a fetch that cannot help)
        if years and cur != "INR" and mcap_cr:
            rev = next((y["revenue"] for y in reversed(years) if y.get("revenue")), None)
            if rev and mcap_cr / (rev / 1e7) > 50:
                warnings.append(f"{code}: statements are reported in {cur}, not INR; financial ratios excluded rather than mis-stated.")
                years, fin_excluded = [], cur
        seen = sec_seen.get(code, {})
        sector = (u or {}).get("sector") or YAHOO_SECTOR.get(info.get("sector") or "") or sector_from_text(seen.get("industry"))
        isin = (by_sym.get(code) or {}).get("isin") or seen.get("isin") or ""
        name = (u or {}).get("name") or info.get("longName") or (by_sym.get(code) or {}).get("name") or seen.get("name") or code
        cos.append({"code": code, "isin": isin, "name": name, "sector": sector, "industry": (u or {}).get("industry") or info.get("industry") or seen.get("industry") or "",
                    "cap": cap_class(mcap_cr, pol), "is_financial": sector == "Financial Services", "price": round(price, 2) if price else None,
                    "shares_cr": round(shares / 1e7, 4) if shares else None, "mcap_cr": round(mcap_cr, 0) if mcap_cr else None,
                    "promoter_pct": round(info["heldPercentInsiders"] * 100, 2) if info.get("heldPercentInsiders") is not None else None,
                    "institutions_pct": round(info["heldPercentInstitutions"] * 100, 2) if info.get("heldPercentInstitutions") is not None else None,
                    "pledge_pct": None, "fii_pct": None, "dii_pct": None, "in_universe": bool(u), "yahoo": tk, "has_fin": bool(years), "fin_excluded": fin_excluded,
                    "source": "Yahoo Finance (yfinance)",
                    "origin": "user" if code in user_syms else "universe" if u else "family" if code in fam_codes else "fund"})
        for y in years:
            sh = y.get("shares") or shares
            cr = lambda v: None if v is None else round(v / 1e7, 2)  # noqa: E731
            fin_rows.append({"code": code, "fy": y["fy"], "period_end": y["period_end"], "revenue": cr(y["revenue"]), "ebitda": cr(y["ebitda"]),
                             "depreciation": cr(y["depreciation"]), "interest": cr(y["interest"]), "pbt": cr(y["pbt"]), "tax": cr(y["tax"]), "pat": cr(y["pat"]),
                             "total_assets": cr(y["total_assets"]), "net_worth": cr(y["net_worth"]), "total_debt": cr(y["total_debt"]), "cash_eq": cr(y["cash_eq"]),
                             "current_assets": cr(y["current_assets"]), "current_liabilities": cr(y["current_liabilities"]), "cfo": cr(y["cfo"]),
                             "capex": None if y["capex"] is None else round(abs(y["capex"]) / 1e7, 2), "dividend_ps": round(divs.get(y["fy"], 0.0), 2) if u else None,
                             "shares_cr": round(sh / 1e7, 4) if sh else None, "gnpa_pct": None, "nnpa_pct": None, "car_pct": None, "nim_pct": None})
    apply_official_financials(fin_rows, cos, warnings)
    have = {c["code"] for c in cos}
    for code, v in sec_seen.items():  # held but not priceable (foreign stocks, unlisted, BSE-only)
        if code not in have:
            cos.append({"code": code, "isin": v["isin"], "name": v["name"] or code, "sector": "Foreign equity" if v["foreign"] else sector_from_text(v["industry"]),
                        "industry": v["industry"], "cap": "Foreign" if v["foreign"] else "Unclassified", "is_financial": False, "price": None, "shares_cr": None,
                        "mcap_cr": None, "promoter_pct": None, "institutions_pct": None, "pledge_pct": None, "fii_pct": None, "dii_pct": None,
                        "in_universe": False, "yahoo": None, "has_fin": False, "source": "AMC portfolio file", "origin": "fund"})

    # ---------- indices
    idx_rows = []
    for k, v in idx_cfg.items():
        for i, tk in enumerate(v["yahoo"]):
            m = monthly(tk)
            if sum(x is not None for x in m) >= 30:
                actual = TICKER_INDEX_NAME.get(tk, v["name"])  # name the series after the index it really holds
                if i > 0 or actual != v["name"]:
                    warnings.append(f"Benchmark {v['name']}: {actual} ({tk}) used in its place; funds benchmarked to it are compared with a different index.")
                for d, x in zip(D, m):
                    if x is not None:
                        idx_rows.append({"date": d, "index_code": k, "index_name": actual + " (price index)", "level": round(x, 2), "source": tk})
                break
        else:
            warnings.append(f"Index {v['name']}: no Yahoo data for {v['yahoo']}.")
    n50 = [r for r in idx_rows if r["index_code"] == "NIFTY50"]
    if n50:
        debt_m = 1.072 ** (1 / 12) - 1
        lv = [1000.0]
        for a, b in zip(n50, n50[1:]):
            lv.append(lv[-1] * (1 + 0.65 * (b["level"] / a["level"] - 1) + 0.35 * debt_m))
        idx_rows += [{"date": r["date"], "index_code": "HYBRID", "index_name": "65% Nifty 50 + 35% debt at 7.2% (composite)", "level": round(x, 4), "source": "composite"} for r, x in zip(n50, lv)]
    idx_have = {r["index_code"] for r in idx_rows}
    for s in schemes:
        if s["benchmark"] not in idx_have:
            s["benchmark"] = "NIFTY500" if "NIFTY500" in idx_have else "NIFTY50"
        s["benchmark_name"] = next((r["index_name"] for r in idx_rows if r["index_code"] == s["benchmark"]), s["benchmark"])

    # benchmark weights for active-weight analysis: the Nifty 50 index fund's own disclosed holdings
    const = []
    s03 = sorted({r["portfolio_date"] for r in port_rows if r["scheme_id"] == "S03"})
    if s03:
        rows = [r for r in port_rows if r["scheme_id"] == "S03" and r["portfolio_date"] == s03[-1]]
        tot = sum(r["weight_pct"] for r in rows)
        const = [{"index_code": "BENCH", "code": r["code"], "weight_pct": round(r["weight_pct"] / tot * 100, 4)} for r in rows]
    else:
        large = [c for c in cos if c["in_universe"] and c["mcap_cr"] and c["cap"] == "Large"]
        tot = sum(c["mcap_cr"] for c in large) or 1
        const = [{"index_code": "BENCH", "code": c["code"], "weight_pct": round(c["mcap_cr"] / tot * 100, 4)} for c in large]
        warnings.append("Benchmark sector weights approximated from market caps of the large-cap universe (Nifty 50 index-fund portfolio not applied).")

    # ---------- dummy family transactions at real prices / NAVs
    progress("Family transactions")
    navs = {}
    for r in nav_rows:
        navs.setdefault((r["scheme_id"], r["plan"]), {})[r["date"]] = r["nav"]
    pxs = {}
    for r in price_rows:
        pxs.setdefault(r["code"], {})[r["date"]] = r["close"]
    txns = []

    def add(member, kind, inst, plan, t, typ, amount=None, qty=None):
        d = D[t]
        px = navs.get((inst, plan), {}).get(d) if kind == "MF" else pxs.get(inst, {}).get(d)
        if px is None:
            return False
        if kind == "MF":
            units = round(amount / px, 3) if qty is None else qty
        else:
            units = int(round(amount / px)) if qty is None else int(qty)
        if units <= 0:
            return False
        txns.append({"txn_id": "", "date": d, "member_id": member, "asset_type": kind, "instrument": inst, "plan": plan, "txn_type": typ,
                     "units": units, "price": px, "amount": round(units * px, 2)})
        return True

    led = ledger.load()
    demo_on = led["settings"]["include_demo_family"]
    if not demo_on:
        fam = {**fam, "mf": [], "eq": [], "sells": []}
    skipped = set()
    for mbr, sid, plan, lumps, sip in fam["mf"]:
        if sid not in sids or (plan == "Regular" and not any(s["scheme_id"] == sid and s["has_regular"] for s in schemes)):
            skipped.add(f"{sid}/{plan}")
            continue
        for t, amt in lumps:
            add(mbr, "MF", sid, plan, t, "Purchase", amt)
        if sip:
            for t in range(sip[0], len(D)):
                add(mbr, "MF", sid, plan, t, "SIP", sip[1])
    for mbr, code, lots in fam["eq"]:
        for t, amt in lots:
            if not add(mbr, "EQ", code, "", t, "Buy", amt):
                skipped.add(code)
    for mbr, kind, inst, plan, t, frac in fam["sells"]:
        held = sum(x["units"] * (-1 if x["txn_type"] == "Sell" else 1) for x in txns
                   if x["member_id"] == mbr and x["instrument"] == inst and x["plan"] == plan and x["date"] <= D[t])
        q = round(held * frac, 3) if kind == "MF" else int(held * frac)
        if q > 0:
            add(mbr, kind, inst, plan, t, "Sell", qty=q)
    if skipped:
        warnings.append(f"Family positions skipped for lack of data: {', '.join(sorted(skipped))}")
    txns.sort(key=lambda x: (x["date"], x["member_id"], x["instrument"]))
    for i, x in enumerate(txns):
        x["txn_id"] = f"T{i + 1:05d}"
        x["source"] = "demo"
    # ---------- entities and transactions entered in the app (data/user/ledger.json); ids are stable (U#####)
    members = [{**m, "source": "demo"} for m in fam["members"]] if demo_on else []
    members += [{k: m[k] for k in ("member_id", "name", "type", "relationship")} | {"source": "user"} for m in led["members"]]
    known = {m["member_id"] for m in members}
    for t in led["transactions"]:
        priced = (navs.get((t["instrument"], t["plan"]), {}) if t["asset_type"] == "MF" else pxs.get(t["instrument"], {})).get(D[-1])
        if t["member_id"] not in known or priced is None:
            warnings.append(f"Entered transaction {t['txn_id']} left out: its entity or its price on {D[-1]} is missing.")
            continue
        txns.append({k: t[k] for k in ("txn_id", "date", "member_id", "asset_type", "instrument", "plan", "txn_type", "units", "price", "amount")}
                    | {"source": "user"} | ({"note": t["note"]} if t.get("note") else {}))
    txns.sort(key=lambda x: (x["date"], x["member_id"], x["instrument"], x["txn_id"]))

    dataset = {
        "meta": {"as_on": D[-1], "dates": D, "portfolio_dates": port_dates, "currency": "INR", "version": VERSION, "mode": "live",
                 "built_at": now_iso(), "started_at": t0,
                 "sources": {"prices": "Yahoo Finance via yfinance (split-adjusted closes, month-end)", "financials": "Yahoo Finance annual statements via yfinance",
                             "navs": "AMFI scheme codes (NAVAll.txt); NAV history from api.mfapi.in", "portfolios": "AMC monthly portfolio disclosures (files supplied by user)",
                             "isin": "NSE equity list (EQUITY_L.csv)", "family": "Dummy family and transactions (fictitious), priced at real NAVs and prices"},
                 "warnings": warnings, "note": "Real market data; the family, its entities and transactions are fictitious."},
        "policy": pol, "members": members, "members_demo": config("family")["members"], "companies": cos, "financials": fin_rows,
        "prices": price_rows, "indices": idx_rows, "index_constituents": const, "schemes": schemes, "scheme_portfolios": port_rows,
        "nav_history": nav_rows, "transactions": txns,
    }
    write_outputs(dataset)
    log.info("Dataset built: %d companies (%d with financials), %d schemes, %d portfolio rows, %d transactions, %d warnings",
             len(cos), len({r['code'] for r in fin_rows}), len(schemes), len(port_rows), len(txns), len(warnings))
    for w in warnings:
        log.warning(w)
    return dataset


def write_outputs(dataset):
    save_json(LIVE / "dataset.json", dataset)
    for k, v in dataset.items():
        if isinstance(v, list) and v:
            cols = list(dict.fromkeys(c for r in v for c in r))
            with open(LIVE / f"{k}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerows(v)
    build_app(dataset)


JS_ORDER = ["core.js", "engine.js", "charts.js", "components.js", "views_portfolio.js", "views_funds.js", "views_risk.js",
            "views_research.js", "views_controls.js", "views_entry.js", "bridge_client.js", "app.js"]


OFFICIAL_FIELDS = ("pbt", "tax", "pat", "net_worth", "total_assets", "total_debt")


def apply_official_financials(fin_rows, cos, warnings):
    """Replace Yahoo values with a company's own audited figures where Yahoo is known to be wrong (data/config/
    official_financials.json). Only the fields supplied are replaced; every replaced row records which fields came from
    which filing, and the company records the basis and reason, so the app can show the source beside the figures."""
    off = config("official_financials") or {}
    for code, spec in off.items():
        if code.startswith("_"):
            continue
        rows = {r["fy"]: r for r in fin_rows if r["code"] == code}
        done = []
        for fy, y in (spec.get("years") or {}).items():
            r = rows.get(fy)
            if not r:
                continue
            vals = {"pbt": y.get("pbt"), "tax": y.get("tax"), "pat": y.get("pat"), "total_assets": y.get("total_assets"), "total_debt": y.get("total_debt"),
                    "net_worth": round(y["capital"] + y["reserves_and_surplus"], 2) if y.get("capital") is not None and y.get("reserves_and_surplus") is not None else None}
            changed = []
            for k in OFFICIAL_FIELDS:
                if vals[k] is not None:
                    r[k] = vals[k]
                    changed.append(k)
            if changed:
                r["official_fields"], r["official_source"] = changed, y.get("url") or spec.get("source")
                done.append(fy)
        c = next((c for c in cos if c["code"] == code), None)
        if c and done:
            c["fin_official"] = {"basis": spec.get("basis"), "source": spec.get("source"), "reason": spec.get("reason"), "years": done,
                                 "fields": sorted({f for r in rows.values() for f in r.get("official_fields", [])})}
            names = {"pbt": "profit before tax", "tax": "tax", "pat": "profit after tax", "net_worth": "net worth", "total_assets": "total assets", "total_debt": "borrowings"}
            got = [names[f] for f in OFFICIAL_FIELDS if f in c["fin_official"]["fields"]]
            warnings.append(f"{code}: {', '.join(done)} " + (", ".join(got[:-1]) + " and " + got[-1] if len(got) > 1 else got[0])
                            + f" taken from the company's audited filing, not Yahoo Finance ({spec.get('basis', 'official')}).")


def build_app(dataset, artifact_out=None):
    import json
    js = "\n".join((APP_SRC / f).read_text(encoding="utf-8") for f in JS_ORDER)
    js = js.replace("/*__DATA__*/null", json.dumps(dataset, separators=(",", ":")).replace("</", "<\\/"), 1)
    body = (APP_SRC / "shell.html").read_text(encoding="utf-8")
    # The [hidden] rule goes in at the stylesheet's own marker, never at "the first <style>": the shell's
    # unsupported-browser script also contains that text, and patching it there broke the page.
    css = "[hidden]{display:none!important}\n" + (APP_SRC / "styles.css").read_text(encoding="utf-8")
    body = body.replace("/*__CSS__*/", css, 1).replace("/*__JS__*/", js, 1)
    if artifact_out:
        artifact_out.write_text(body, encoding="utf-8")
    head, rest = body.split('<div class="app">', 1)
    html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + head
            + '</head>\n<body>\n<div class="app">' + rest + "\n</body>\n</html>\n")
    APP_OUT.parent.mkdir(parents=True, exist_ok=True)
    APP_OUT.write_text(html, encoding="utf-8")
    import shutil
    shutil.copytree(APP_SRC / "pwa", APP_OUT.parent / "pwa", dirs_exist_ok=True)  # served by the bridge; see PWA_FILES there
    log.info("App rebuilt: %s (%d KB)", APP_OUT, len(html.encode()) // 1024)


def build_empty():
    """Ship-state app: no market data yet; the app shows how to start the bridge."""
    pol, fam = config("policy"), config("family")
    ds = {"meta": {"mode": "empty", "as_on": None, "dates": [], "portfolio_dates": [], "version": VERSION, "built_at": None, "sources": {}, "warnings": []},
          "policy": pol, "members": fam["members"], "companies": [], "financials": [], "prices": [], "indices": [], "index_constituents": [],
          "schemes": [], "scheme_portfolios": [], "nav_history": [], "transactions": []}
    build_app(ds)
    return ds
