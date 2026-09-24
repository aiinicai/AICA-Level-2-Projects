#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 MF X-RAY V1.0 -- Modern Financial Application Backend Server
 ICAI AI Level 2 Capstone Project
================================================================================
"""
import os
import sys
import json
from datetime import datetime, date, timedelta
from io import BytesIO
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file

import MF_XRay_V1 as core
import amfi_service

app = Flask(__name__, template_folder="templates")

# File storage for persistence
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(DATA_DIR, "user_portfolio.json")
FUNDS_FILE = os.path.join(DATA_DIR, "user_funds.json")
SNAPSHOTS_FILE = os.path.join(DATA_DIR, "user_snapshots.json")

# In-memory working state
current_portfolio = core.Portfolio()
snapshots = {}
risk_free_rate = 6.0


def load_persistent_data():
    global current_portfolio, snapshots
    # Load custom funds if saved
    if os.path.exists(FUNDS_FILE):
        try:
            with open(FUNDS_FILE, "r", encoding="utf-8") as f:
                saved_funds = json.load(f)
            for fname, fdata in saved_funds.items():
                core.FUND_META[fname] = fdata["meta"]
                # Convert string date if present
                if "portfolio_date" in core.FUND_META[fname] and isinstance(core.FUND_META[fname]["portfolio_date"], str):
                    try:
                        core.FUND_META[fname]["portfolio_date"] = datetime.strptime(core.FUND_META[fname]["portfolio_date"], "%Y-%m-%d").date()
                    except ValueError:
                        core.FUND_META[fname]["portfolio_date"] = date.today()
                core.FUND_HOLDINGS[fname] = fdata["holdings"]
                core.FUNDS[fname] = core.Fund(fname, core.FUND_META[fname], core.FUND_HOLDINGS[fname])
                for c, s in fdata.get("sectors", {}).items():
                    core.COMPANY_SECTOR_MAP[c] = s
        except Exception as e:
            print("Error loading custom funds:", e)

    # Load portfolio
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                entries_data = json.load(f)
            current_portfolio = core.Portfolio.from_dict_list(entries_data)
        except Exception as e:
            print("Error loading user portfolio:", e)
            current_portfolio = core.Portfolio()
    else:
        # Start clean / empty by default (user's explicit preference)
        current_portfolio = core.Portfolio()

    # Load snapshots
    if os.path.exists(SNAPSHOTS_FILE):
        try:
            with open(SNAPSHOTS_FILE, "r", encoding="utf-8") as f:
                snap_data = json.load(f)
            for label, item in snap_data.items():
                p = core.Portfolio.from_dict_list(item["entries"])
                m = core.compute_all_metrics(p, risk_free_rate)
                snapshots[label] = {
                    "portfolio": p,
                    "metrics": m,
                    "saved_on": datetime.strptime(item["saved_on"], "%Y-%m-%d %H:%M:%S")
                }
        except Exception as e:
            print("Error loading snapshots:", e)


def save_persistent_data():
    try:
        # Save portfolio
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(current_portfolio.to_dict_list(), f, indent=2)

        # Save funds that might have been added or edited
        funds_export = {}
        for fname, fund in core.FUNDS.items():
            meta_copy = dict(core.FUND_META.get(fname, {}))
            if "portfolio_date" in meta_copy and isinstance(meta_copy["portfolio_date"], (date, datetime)):
                meta_copy["portfolio_date"] = meta_copy["portfolio_date"].strftime("%Y-%m-%d")
            sectors = {c: core.COMPANY_SECTOR_MAP.get(c, "Others") for c in fund.holdings}
            funds_export[fname] = {
                "meta": meta_copy,
                "holdings": fund.holdings,
                "sectors": sectors
            }
        with open(FUNDS_FILE, "w", encoding="utf-8") as f:
            json.dump(funds_export, f, indent=2)

        # Save snapshots
        snaps_export = {}
        for label, item in snapshots.items():
            snaps_export[label] = {
                "entries": item["portfolio"].to_dict_list(),
                "saved_on": item["saved_on"].strftime("%Y-%m-%d %H:%M:%S")
            }
        with open(SNAPSHOTS_FILE, "w", encoding="utf-8") as f:
            json.dump(snaps_export, f, indent=2)
    except Exception as e:
        print("Error saving persistent data:", e)


load_persistent_data()


# -----------------------------------------------------------------------------
# Web Routes
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify({
        "app_name": core.APP_NAME,
        "app_version": core.APP_VERSION,
        "app_full_title": core.APP_FULL_TITLE,
        "app_subtitle": core.APP_SUBTITLE,
        "total_funds_available": len(core.FUNDS),
        "portfolio_entries_count": len(current_portfolio.entries),
        "total_investment": current_portfolio.total_investment(),
        "is_empty": current_portfolio.is_empty(),
        "risk_free_rate": risk_free_rate,
        "disclaimer_short": core.DISCLAIMER_SHORT,
        "disclaimer_full": core.DISCLAIMER_FULL,
        "demo_label": core.DEMO_DATA_LABEL
    })


@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    global risk_free_rate
    rf = request.args.get("risk_free_rate", default=risk_free_rate, type=float)
    risk_free_rate = rf
    metrics = core.compute_all_metrics(current_portfolio, rf)
    
    # Format metrics for JSON transfer
    alloc_list = metrics["allocation_df"].to_dict(orient="records") if not metrics["allocation_df"].empty else []
    exp_list = metrics["exposure_df"].drop(columns=["_contributors"], errors="ignore").to_dict(orient="records") if not metrics["exposure_df"].empty else []
    sec_list = metrics["sector_df"].to_dict(orient="records") if not metrics["sector_df"].empty else []
    risk_list = metrics["risk_df"].to_dict(orient="records") if metrics.get("risk_df") is not None and not metrics["risk_df"].empty else []
    
    # Overlap matrix to dict
    overlap_matrix_dict = {}
    if not metrics["overlap_matrix"].empty:
        overlap_matrix_dict = {
            "columns": metrics["overlap_matrix"].columns.tolist(),
            "index": metrics["overlap_matrix"].index.tolist(),
            "data": metrics["overlap_matrix"].values.tolist()
        }
    
    # AI narrative and alerts
    ai_narrative = core.generate_ai_narrative(metrics)
    
    return jsonify({
        "has_portfolio": metrics["has_portfolio"],
        "total_investment": metrics["total_investment"],
        "total_funds": len(current_portfolio.fund_names()),
        "weighted_equity_pct": metrics["weighted_equity_pct"],
        "weighted_debt_pct": metrics["weighted_debt_pct"],
        "weighted_cash_pct": metrics["weighted_cash_pct"],
        "weighted_expense_ratio": metrics["weighted_expense_ratio"],
        "allocation": alloc_list,
        "effective_exposure": exp_list,
        "sector_exposure": sec_list,
        "overlap_matrix": overlap_matrix_dict,
        "overlap_pairs": [{"fund_a": p[0], "fund_b": p[1], "overlap_pct": p[2]} for p in metrics["overlap_pairs"]],
        "concentration": metrics["concentration"],
        "fund_concentration": metrics["fund_concentration"],
        "risk_table": risk_list,
        "portfolio_risk": metrics["risk"],
        "health_score": metrics["health"],
        "risk_bucket": core.health_score_risk_bucket(metrics["health"]["total"]),
        "alerts": metrics["alerts"],
        "ai_narrative": ai_narrative,
        "thresholds": core.THRESHOLDS
    })


@app.route("/api/funds", methods=["GET", "POST"])
def manage_funds():
    if request.method == "GET":
        funds_list = []
        for name, f in core.FUNDS.items():
            top_holdings = [{"company": c, "sector": core.COMPANY_SECTOR_MAP.get(c, "Others"), "weight": w} for c, w in f.top_holdings(100)]
            sectors = sorted(f.sector_allocation().items(), key=lambda kv: kv[1], reverse=True)
            funds_list.append({
                "name": f.name,
                "category": f.category,
                "nav": f.nav,
                "aum_cr": f.aum_cr,
                "expense_ratio_pct": f.expense_ratio_pct,
                "return_1y_pct": f.return_1y_pct,
                "cagr_3y_pct": f.cagr_3y_pct,
                "cagr_5y_pct": f.cagr_5y_pct,
                "risk_level": f.risk_level,
                "equity_pct": f.equity_pct,
                "debt_pct": f.debt_pct,
                "cash_pct": f.cash_pct,
                "benchmark": f.benchmark,
                "portfolio_date": f.portfolio_date.strftime("%Y-%m-%d") if hasattr(f, "portfolio_date") and f.portfolio_date else "",
                "holdings_count": len(f.holdings),
                "top_holdings": top_holdings,
                "sector_allocation": [{"sector": s, "weight": w} for s, w in sectors]
            })
        return jsonify({"funds": funds_list})

    elif request.method == "POST":
        data = request.json or {}
        name = str(data.get("name", "")).strip()
        if not name:
            return jsonify({"error": "Fund name is required"}), 400
        
        meta = {
            "category": str(data.get("category", "Equity - Multi Cap Fund")),
            "nav": float(data.get("nav", 10.0)),
            "aum_cr": float(data.get("aum_cr", 1000.0)),
            "expense_ratio_pct": float(data.get("expense_ratio_pct", 1.5)),
            "return_1y_pct": float(data.get("return_1y_pct", 12.0)),
            "cagr_3y_pct": float(data.get("cagr_3y_pct", 14.0)),
            "cagr_5y_pct": float(data.get("cagr_5y_pct", 12.0)),
            "risk_level": str(data.get("risk_level", "Moderate")),
            "equity_pct": float(data.get("equity_pct", 95.0)),
            "debt_pct": float(data.get("debt_pct", 3.0)),
            "cash_pct": float(data.get("cash_pct", 2.0)),
            "benchmark": str(data.get("benchmark", "Nifty 500 TRI")),
            "portfolio_date": date.today()
        }
        
        holdings_input = data.get("holdings", [])
        holdings_dict = {}
        for h in holdings_input:
            comp = str(h.get("company", "")).strip()
            if comp:
                weight = float(h.get("weight", 0.0))
                holdings_dict[comp] = weight
                sec = str(h.get("sector", "Others")).strip()
                core.COMPANY_SECTOR_MAP[comp] = sec or "Others"
        
        core.FUND_META[name] = meta
        core.FUND_HOLDINGS[name] = holdings_dict
        core.FUNDS[name] = core.Fund(name, meta, holdings_dict)
        save_persistent_data()
        return jsonify({"success": True, "message": f"Fund '{name}' saved successfully with {len(holdings_dict)} holdings."})


@app.route("/api/funds/<fund_name>", methods=["DELETE"])
def delete_fund(fund_name):
    if fund_name in core.FUNDS:
        del core.FUNDS[fund_name]
        core.FUND_META.pop(fund_name, None)
        core.FUND_HOLDINGS.pop(fund_name, None)
        current_portfolio.remove_fund(fund_name)
        save_persistent_data()
        return jsonify({"success": True, "message": f"Fund '{fund_name}' deleted."})
    return jsonify({"error": "Fund not found"}), 404


@app.route("/api/portfolio", methods=["GET", "POST", "DELETE"])
def manage_portfolio():
    global current_portfolio
    if request.method == "GET":
        entries = []
        for e in current_portfolio.entries:
            entries.append({
                "fund_name": e.fund_name,
                "amount": e.amount,
                "method": e.method,
                "inv_date": e.inv_date.strftime("%Y-%m-%d") if e.inv_date else ""
            })
        return jsonify({
            "entries": entries,
            "total_investment": current_portfolio.total_investment(),
            "count": len(entries)
        })

    elif request.method == "POST":
        data = request.json or {}
        fund_name = str(data.get("fund_name", "")).strip()
        if not fund_name:
            return jsonify({"error": "Fund Scheme Name is required"}), 400
        
        # If fund is not yet registered in core.FUNDS, auto-register from AMFI or default profile
        if fund_name not in core.FUNDS:
            scheme = amfi_service.get_scheme_by_code_or_name(fund_name)
            if scheme:
                meta, holdings, sectors = amfi_service.get_scheme_xray_profile(scheme)
                actual_name = scheme["name"]
                core.FUND_META[actual_name] = meta
                core.FUND_HOLDINGS[actual_name] = holdings
                core.FUNDS[actual_name] = core.Fund(actual_name, meta, holdings)
                for comp, sec in sectors.items():
                    core.COMPANY_SECTOR_MAP[comp] = sec
                fund_name = actual_name
            else:
                meta = {
                    "category": str(data.get("category", "Equity Scheme - Multi Cap Fund")),
                    "nav": float(data.get("nav", 50.0)),
                    "aum_cr": float(data.get("aum_cr", 5000.0)),
                    "expense_ratio_pct": float(data.get("expense_ratio_pct", 1.25)),
                    "return_1y_pct": 16.0, "cagr_3y_pct": 18.5, "cagr_5y_pct": 15.0,
                    "risk_level": "Very High", "equity_pct": 95.0, "debt_pct": 2.0, "cash_pct": 3.0,
                    "benchmark": "Nifty 500 TRI", "portfolio_date": date.today()
                }
                holdings = {
                    "HDFC Bank": 8.5, "ICICI Bank": 7.2, "Reliance Industries": 6.8, "Infosys": 6.0,
                    "Tata Consultancy Services": 4.5, "ITC Ltd": 4.2, "Larsen & Toubro": 3.9
                }
                core.FUND_META[fund_name] = meta
                core.FUND_HOLDINGS[fund_name] = holdings
                core.FUNDS[fund_name] = core.Fund(fund_name, meta, holdings)
        try:
            amount = float(str(data.get("amount", 0)).replace(",", ""))
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
        except ValueError:
            return jsonify({"error": "Please enter a valid positive investment amount."}), 400
        
        method = str(data.get("method", "Lump Sum"))
        date_str = str(data.get("inv_date", ""))
        inv_date = date.today()
        if date_str:
            try:
                inv_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                try:
                    inv_date = datetime.strptime(date_str, "%d-%m-%Y").date()
                except ValueError:
                    inv_date = date.today()

        # Update if fund already in portfolio, else add
        existing = [e for e in current_portfolio.entries if e.fund_name == fund_name]
        if existing:
            existing[0].amount = amount
            existing[0].method = method
            existing[0].inv_date = inv_date
            msg = f"Updated '{fund_name}' investment to ₹{amount:,.0f}."
        else:
            current_portfolio.add(fund_name, amount, method, inv_date)
            msg = f"Added '{fund_name}' (₹{amount:,.0f}) to portfolio."

        save_persistent_data()
        return jsonify({"success": True, "message": msg, "fund_name": fund_name})


@app.route("/api/portfolio/<fund_name>", methods=["DELETE"])
def remove_portfolio_fund(fund_name):
    global current_portfolio
    current_portfolio.remove_fund(fund_name)
    save_persistent_data()
    return jsonify({"success": True, "message": f"Removed '{fund_name}' from portfolio."})


# -----------------------------------------------------------------------------
# AMFI Universal Schemes Endpoints
# -----------------------------------------------------------------------------
@app.route("/api/amfi/fund_houses", methods=["GET"])
def get_amfi_fund_houses():
    houses = amfi_service.get_all_fund_houses()
    return jsonify({"fund_houses": houses, "total": len(houses)})


@app.route("/api/amfi/schemes", methods=["GET"])
def search_amfi_schemes():
    amc = request.args.get("amc", default="", type=str)
    query = request.args.get("query", default="", type=str) or request.args.get("q", default="", type=str)
    category = request.args.get("category", default="", type=str)
    limit = request.args.get("limit", default=80, type=int)
    schemes = amfi_service.search_schemes(amc=amc, query=query, category=category, limit=min(limit, 300))
    return jsonify({"schemes": schemes, "count": len(schemes)})


@app.route("/api/amfi/scheme/<path:identifier>", methods=["GET"])
def get_amfi_scheme(identifier):
    scheme = amfi_service.get_scheme_by_code_or_name(identifier)
    if scheme:
        return jsonify({"scheme": scheme})
    return jsonify({"error": "Scheme not found in AMFI database"}), 404


@app.route("/api/portfolio/clear", methods=["POST"])
def clear_portfolio():
    global current_portfolio
    current_portfolio.clear()
    save_persistent_data()
    return jsonify({"success": True, "message": "Portfolio cleared successfully."})


@app.route("/api/portfolio/demo", methods=["POST"])
def load_demo():
    global current_portfolio
    current_portfolio = core.demo_portfolio()
    save_persistent_data()
    return jsonify({"success": True, "message": "Sample demo portfolio loaded (4 funds, ₹9,00,000)."})


@app.route("/api/whatif", methods=["POST"])
def run_whatif():
    data = request.json or {}
    fund_to_remove = str(data.get("fund_name", "")).strip()
    if not fund_to_remove:
        return jsonify({"error": "Please select a fund to simulate removing."}), 400
    
    held_funds = current_portfolio.fund_names()
    if fund_to_remove not in held_funds:
        return jsonify({
            "error": f"'{fund_to_remove}' is not present in your current portfolio. Please select one of your held funds: {', '.join(held_funds)}"
        }), 400
    
    sim = core.simulate_remove_fund(current_portfolio, fund_to_remove, risk_free_rate)
    b = sim["before"]
    a = sim["after"]
    
    b_row = core.whatif_summary_row("Before", b)
    a_row = core.whatif_summary_row(f"After removing {fund_to_remove}", a)
    
    diff_df = core.MFXRayApp._exposure_diff(b["exposure_df"], a["exposure_df"]) if a["has_portfolio"] else pd.DataFrame()
    diff_list = diff_df.head(15).to_dict(orient="records") if not diff_df.empty else []
    
    return jsonify({
        "removed_fund": fund_to_remove,
        "before": b_row,
        "after": a_row,
        "exposure_diff": diff_list
    })


@app.route("/api/sip", methods=["POST"])
def run_sip():
    data = request.json or {}
    fund_name = str(data.get("fund_name", "")).strip()
    try:
        amount = float(data.get("amount", 10000))
        instalments = int(data.get("instalments", 24))
        start_date = str(data.get("start_date", (date.today().replace(day=1) - timedelta(days=730)).strftime("%d-%m-%Y")))
        
        result = core.simulate_sip(fund_name, amount, start_date, instalments)
        # Format schedule dates for JSON
        sched = []
        for row in result["schedule"]:
            r = dict(row)
            if hasattr(r["Date"], "strftime"):
                r["Date"] = r["Date"].strftime("%d-%b-%Y")
            sched.append(r)
        result["schedule"] = sched
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def call_external_llm(prompt, provider="gemini", api_key=None, model=None):
    if not api_key:
        return None
    try:
        import urllib.request
        import json
        import ssl
        ctx = ssl._create_unverified_context()
        
        if provider == "gemini":
            model_name = model or "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        elif provider == "openai":
            model_name = model or "gpt-4o-mini"
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a professional SEBI Registered Investment Advisor (RIA) and Chartered Accountant specializing in mutual fund portfolio intelligence, stock overlap reduction, and asset allocation."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "")
    except Exception as e:
        print(f"External LLM call failed: {e}")
        return None
    return None


def generate_comprehensive_ai_optimization(metrics, portfolio, provider=None, api_key=None, model=None):
    if not metrics.get("has_portfolio"):
        return {
            "summary": "No active portfolio to analyze. Add mutual funds to your portfolio first.",
            "report_markdown": "### 📊 No Active Portfolio Found\n\nPlease add mutual funds to your portfolio first to enable deep AI portfolio optimization.",
            "source": "rule_based"
        }

    total_corpus = metrics["total_investment"]
    funds = portfolio.entries
    fund_names = portfolio.fund_names()
    overlap_pairs = metrics.get("overlap_pairs", [])
    high_overlap = [p for p in overlap_pairs if p[2] >= 40.0]
    top_stocks = metrics.get("exposure_df", pd.DataFrame())
    top_sectors = metrics.get("sector_df", pd.DataFrame())
    health = metrics.get("health", {})
    health_score = health.get("total", 50)
    risk_bucket = core.health_score_risk_bucket(health_score)

    top_stock_name = top_stocks.iloc[0]["Company"] if not top_stocks.empty else "N/A"
    top_stock_pct = top_stocks.iloc[0]["Effective Exposure %"] if not top_stocks.empty else 0.0
    top_sector_name = top_sectors.iloc[0]["Sector"] if not top_sectors.empty else "N/A"
    top_sector_pct = top_sectors.iloc[0]["Effective Exposure %"] if not top_sectors.empty else 0.0

    # Format structured context
    holdings_summary = []
    for e in funds:
        holdings_summary.append(f"- {e.fund_name}: ₹{e.amount:,.0f} ({e.amount/total_corpus*100:.1f}%) via {e.method}")

    top_stocks_list = []
    if not top_stocks.empty:
        for _, r in top_stocks.head(6).iterrows():
            top_stocks_list.append(f"- {r['Company']} ({r['Sector']}): {r['Effective Exposure %']:.2f}% (₹{r['Exposure Amount']:,.0f}) held in {r['Number of Funds']} funds")

    overlap_list = []
    for p in overlap_pairs:
        overlap_list.append(f"- {p[0]} <-> {p[1]}: {p[2]:.1f}% overlap")

    prompt_context = f"""
You are an expert SEBI RIA / Chartered Accountant mutual fund portfolio optimizer.
Analyze this investor's actual portfolio data and deliver a comprehensive diagnostic and restructuring plan:

Portfolio Summary:
- Total Corpus: ₹{total_corpus:,.0f}
- Number of Funds: {len(fund_names)}
- Health Score: {health_score}/100 ({risk_bucket})
- Weighted Expense Ratio: {metrics.get('weighted_expense_ratio', 0):.2f}%
- Asset Allocation: Equity {metrics.get('weighted_equity_pct', 0):.1f}%, Debt {metrics.get('weighted_debt_pct', 0):.1f}%, Cash {metrics.get('weighted_cash_pct', 0):.1f}%

Funds in Portfolio:
{chr(10).join(holdings_summary)}

Pairwise Overlap Between Schemes:
{chr(10).join(overlap_list) if overlap_list else "None detected"}

Top Underlying Look-Through Stock Exposures:
{chr(10).join(top_stocks_list)}

Top Sector Exposure:
- {top_sector_name}: {top_sector_pct:.1f}% of total portfolio

Provide your response in structured markdown:
1. Executive Portfolio Observation & Health Diagnosis (critical flaws, category duplication, banking concentration).
2. Specific Action Plan — Exactly What to Change (which funds to retain, exit, or switch, and which complementary asset classes to add).
3. Recommended Target Allocation Model Table (Category, Target %, Target ₹, Specific Benefit).
4. Quantified Maximum Benefits (Health Score rise, overlap drop, fee reduction, drawdown cushion).
"""

    if api_key:
        llm_response = call_external_llm(prompt_context, provider=provider, api_key=api_key, model=model)
        if llm_response:
            return {
                "source": f"llm_{provider}",
                "report_markdown": llm_response,
                "health_score": health_score,
                "risk_bucket": risk_bucket,
                "total_corpus": total_corpus
            }

    # Built-in deterministic CA-Grade Optimization Engine
    obs = []
    recs = []

    if len(fund_names) >= 2:
        all_flexi = all("flexi" in f.lower() for f in fund_names)
        if all_flexi:
            obs.append(f"**Severe Style Redundancy**: All {len(fund_names)} funds in your portfolio belong to the exact same category (*Flexi Cap*). While you hold multiple schemes, you are executing the exact same investment mandate repeatedly.")
        
    if high_overlap:
        pair_strs = [f"**{p[0]}** and **{p[1]}** ({p[2]:.1f}% overlap)" for p in high_overlap]
        obs.append(f"**High Stock Duplication**: Massive overlapping positions between {', '.join(pair_strs)}. You are paying multiple AMC expense ratios for essentially identical underlying stock baskets.")

    if top_sector_pct >= 25.0:
        obs.append(f"**Heavy Sector Concentration in {top_sector_name} ({top_sector_pct:.1f}%)**: More than a quarter of your entire net worth is tied to {top_sector_name}, exposing your corpus to sharp drawdowns if financial and credit markets face cyclical stress.")

    if top_stock_pct >= 8.0:
        obs.append(f"**Individual Stock Exposure Spike**: Combined look-through exposure in **{top_stock_name} ({top_stock_pct:.2f}%)** exceeds the recommended 8.0% prudential diversification limit.")

    # Generate Actionable Recommendations
    if high_overlap:
        p = high_overlap[0]
        recs.append(f"**Action 1 (Eliminate Duplication)**: Consolidate duplicate Flexi Cap schemes. Keep **Parag Parikh Flexi Cap Fund** (due to its distinct global equity allocation and deep value strategy) and redeem/switch **{p[1]}** (which has {p[2]:.1f}% duplicate overlap) to remove fee drag.")
        recs.append(f"**Action 2 (Capture Growth via Mid/Small Caps)**: Reallocate the redeemed capital into a specialized **Mid Cap** or **Small Cap Fund** (e.g. *Nippon India Small Cap* or *Motilal Oswal Midcap*). This unleashes real compounding potential rather than duplicate large-cap banking stocks.")
    else:
        recs.append(f"**Action 1 (Market Cap Diversification)**: Diversify across market caps by allocating 25-30% into quality Mid-Cap / Small-Cap schemes.")

    recs.append(f"**Action 3 (Downside Cushion)**: Allocate 15-20% into a **Balanced Advantage / Dynamic Asset Allocation Fund** (e.g. *ICICI Prudential Balanced Advantage Fund*). This automatically trims equity risk during high market valuations and cushions against drawdowns.")
    recs.append(f"**Action 4 (Sector Rebalancing)**: Ensure Financial Services exposure is brought down from {top_sector_pct:.1f}% to under 22% by increasing exposure to Industrials, Healthcare, and Technology.")

    report_md = f"""### 📊 AI Portfolio Diagnostic & Optimization Report

#### 1. Key Observations & Vulnerabilities
{"".join([chr(10) + "- " + o for o in obs])}

---

#### 2. Strategic Action Plan (Where & How to Change)
{"".join([chr(10) + "- " + r for r in recs])}

---

#### 3. Recommended Target Allocation Model (for ₹{total_corpus:,.0f} Corpus)

| Portfolio Component | Recommended Scheme Strategy | Current % | Target % | Target Amount (₹) | Key Strategic Benefit |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Core Multi-Cap / Flexi** | Parag Parikh Flexi Cap Fund | {100.0/len(fund_names)*len(fund_names):.0f}% | **45%** | ₹{total_corpus*0.45:,.0f} | Retains core bluechip + global tech diversification |
| **Alpha / Mid-Cap Growth** | Quality Mid Cap / Small Cap Scheme | 0% | **30%** | ₹{total_corpus*0.30:,.0f} | Unlocks high compounding in Indian manufacturing & midcaps |
| **Downside Buffer (Hybrid)**| Balanced Advantage / Dynamic Asset | 0% | **15%** | ₹{total_corpus*0.15:,.0f} | Automatic debt-equity rebalancing during market corrections |
| **Liquid / Emergency Debt** | Overnight / Arbitrage / Liquid Scheme | 0% | **10%** | ₹{total_corpus*0.10:,.0f} | Zero market volatility; ready dry powder for market dips |

---

#### 4. Projected Quantitative Benefits
- **Portfolio Health Score**: Projected to surge from **{health_score}/100** to **86+/100** (upgrading to *Prime Diversified* status).
- **Pairwise Overlap**: Drops from **{high_overlap[0][2] if high_overlap else 21:.1f}%** down to **< 12%** across all scheme pairs.
- **Top Stock Concentration**: Reduces maximum single-stock exposure from **{top_stock_pct:.2f}%** to **< 5.0%**.
- **Net Annual Fee Savings**: Eliminates redundant AMC fees, saving an estimated **0.35% - 0.50%** per year in compounding expense ratios.
"""

    return {
        "source": "rule_based_expert",
        "report_markdown": report_md,
        "health_score": health_score,
        "risk_bucket": risk_bucket,
        "total_corpus": total_corpus
    }


@app.route("/api/ai/optimize", methods=["POST"])
def optimize_portfolio():
    data = request.json or {}
    provider = data.get("provider", "gemini")
    api_key = data.get("api_key", "").strip() or None
    model = data.get("model", "").strip() or None
    metrics = core.compute_all_metrics(current_portfolio, risk_free_rate)
    result = generate_comprehensive_ai_optimization(metrics, current_portfolio, provider=provider, api_key=api_key, model=model)
    return jsonify(result)


@app.route("/api/ai/test_key", methods=["POST"])
def test_ai_key():
    data = request.json or {}
    provider = data.get("provider", "gemini")
    api_key = data.get("api_key", "").strip()
    model = data.get("model", "").strip()
    if not api_key:
        return jsonify({"success": False, "error": "API Key is required"}), 400
    
    test_res = call_external_llm("Reply with exact words: 'API Key Connected Successfully.'", provider=provider, api_key=api_key, model=model)
    if test_res:
        return jsonify({"success": True, "message": "API Key verified and connected successfully!", "response": test_res.strip()})
    return jsonify({"success": False, "error": "Could not connect to AI provider. Please verify your API Key and internet connection."}), 400


@app.route("/api/ask", methods=["POST"])
def ask_question():
    data = request.json or {}
    q = str(data.get("question", "")).strip()
    provider = data.get("provider", "gemini")
    api_key = data.get("api_key", "").strip() or None
    model = data.get("model", "").strip() or None
    
    metrics = core.compute_all_metrics(current_portfolio, risk_free_rate)
    
    if api_key:
        prompt = f"""
You are an AI financial advisor analyzing this user's mutual fund portfolio:
- Total Investment: ₹{metrics['total_investment']:,.0f}
- Funds: {', '.join(current_portfolio.fund_names())}
- Health Score: {metrics['health']['total']}/100
- Overlap Pairs: {metrics.get('overlap_pairs', [])}
- Top Stocks: {[(r['Company'], r['Effective Exposure %']) for _, r in metrics.get('exposure_df', pd.DataFrame()).head(5).iterrows()]}

User Question: {q}
Answer concisely, factually, and professionally based strictly on the portfolio numbers.
"""
        llm_answer = call_external_llm(prompt, provider=provider, api_key=api_key, model=model)
        if llm_answer:
            return jsonify({"question": q, "answer": llm_answer, "source": f"llm_{provider}"})

    answer = core.answer_question(q, metrics, snapshots)
    return jsonify({"question": q, "answer": answer, "source": "rule_based"})


@app.route("/api/snapshots", methods=["GET", "POST"])
def manage_snapshots():
    if request.method == "GET":
        snaps = []
        for label, item in snapshots.items():
            m = item["metrics"]
            snaps.append({
                "label": label,
                "saved_on": item["saved_on"].strftime("%d-%b-%Y %H:%M"),
                "total_investment": m["total_investment"],
                "funds_count": len(item["portfolio"].fund_names()),
                "health_score": m["health"]["total"]
            })
        return jsonify({"snapshots": snaps})

    elif request.method == "POST":
        data = request.json or {}
        label = str(data.get("label", "")).strip() or datetime.now().strftime("Snapshot %d-%b-%Y %H:%M")
        if current_portfolio.is_empty():
            return jsonify({"error": "Cannot save snapshot of an empty portfolio."}), 400
        
        m = core.compute_all_metrics(current_portfolio, risk_free_rate)
        # Save deep copy of entries
        p_copy = core.Portfolio.from_dict_list(current_portfolio.to_dict_list())
        snapshots[label] = {
            "portfolio": p_copy,
            "metrics": m,
            "saved_on": datetime.now()
        }
        save_persistent_data()
        return jsonify({"success": True, "message": f"Snapshot '{label}' saved successfully."})


@app.route("/api/snapshots/compare", methods=["POST"])
def compare_snapshots():
    data = request.json or {}
    prev_label = data.get("prev_label")
    curr_label = data.get("curr_label")
    if prev_label not in snapshots or curr_label not in snapshots:
        return jsonify({"error": "Select two valid saved snapshots."}), 400
    
    prev_m = snapshots[prev_label]["metrics"]
    curr_m = snapshots[curr_label]["metrics"]
    
    stock_diff = core.MFXRayApp._exposure_diff(prev_m["exposure_df"], curr_m["exposure_df"]).to_dict(orient="records")
    sector_diff = core.MFXRayApp._sector_diff(prev_m["sector_df"], curr_m["sector_df"]).to_dict(orient="records")
    
    return jsonify({
        "prev_label": prev_label,
        "curr_label": curr_label,
        "stock_diff": stock_diff,
        "sector_diff": sector_diff
    })


@app.route("/api/export/excel", methods=["GET"])
def export_excel():
    if current_portfolio.is_empty():
        return jsonify({"error": "Cannot export an empty portfolio. Add funds first."}), 400
    m = core.compute_all_metrics(current_portfolio, risk_free_rate)
    temp_path = os.path.join(DATA_DIR, "MF_XRay_Portfolio_Analysis.xlsx")
    core.export_to_excel(temp_path, current_portfolio, m)
    return send_file(temp_path, as_attachment=True, download_name="MF_XRay_Portfolio_Analysis.xlsx")


@app.route("/api/export/word", methods=["GET"])
def export_word():
    if current_portfolio.is_empty():
        return jsonify({"error": "Cannot export an empty portfolio. Add funds first."}), 400
    m = core.compute_all_metrics(current_portfolio, risk_free_rate)
    temp_path = os.path.join(DATA_DIR, "MF_XRay_Executive_Report.docx")
    core.export_to_word(temp_path, current_portfolio, m)
    return send_file(temp_path, as_attachment=True, download_name="MF_XRay_Executive_Report.docx")


@app.route("/api/templates/<template_type>", methods=["GET"])
def download_template(template_type):
    if template_type == "fund_master":
        csv_data = (
            "Fund Name,Category,NAV,AUM_Cr,Expense_Ratio_Pct,Return_1Y_Pct,CAGR_3Y_Pct,CAGR_5Y_Pct,Risk_Level,Equity_Pct,Debt_Pct,Cash_Pct,Benchmark,Portfolio_Date\n"
            "Parag Parikh Flexi Cap,Equity - Flexi Cap,68.45,45000,1.45,18.5,21.2,17.8,Very High,88.0,4.0,8.0,Nifty 500 TRI,2026-08-31\n"
            "Mirae Asset Large Cap,Equity - Large Cap,92.10,38000,1.52,14.8,17.1,14.2,High,97.0,1.5,1.5,Nifty 100 TRI,2026-08-31\n"
        )
        filename = "template_fund_master.csv"
    elif template_type == "holdings":
        csv_data = (
            "Fund Name,Company,Sector,Weight_Pct,Portfolio_Date\n"
            "Parag Parikh Flexi Cap,HDFC Bank,Financial Services,8.2,2026-08-31\n"
            "Parag Parikh Flexi Cap,ITC Limited,Consumer Goods,7.5,2026-08-31\n"
            "Parag Parikh Flexi Cap,Bajaj Holdings,Financial Services,6.8,2026-08-31\n"
            "Mirae Asset Large Cap,HDFC Bank,Financial Services,9.4,2026-08-31\n"
            "Mirae Asset Large Cap,Reliance Industries,Energy,8.1,2026-08-31\n"
            "Mirae Asset Large Cap,Infosys,Information Technology,7.3,2026-08-31\n"
        )
        filename = "template_holdings.csv"
    else:
        csv_data = "Date,Fund Name,NAV\n2026-07-31,Parag Parikh Flexi Cap,66.20\n2026-08-31,Parag Parikh Flexi Cap,68.45\n"
        filename = "template_historical_nav.csv"

    bio = BytesIO(csv_data.encode("utf-8"))
    return send_file(bio, as_attachment=True, download_name=filename, mimetype="text/csv")


if __name__ == "__main__":
    port = 5055
    print(f"Starting MF X-Ray Application Server on http://127.0.0.1:{port}...")
    app.run(host="127.0.0.1", port=port, debug=False)
