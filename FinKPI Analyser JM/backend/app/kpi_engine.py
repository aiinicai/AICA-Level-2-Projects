import math
from typing import Dict, List, Any, Optional, Tuple
from .config import config
from .financial_engine import FinancialEngine

def safe_div(num: float, den: float, default: float = 0.0) -> float:
    if den == 0.0 or den is None or math.isnan(den):
        return default
    try:
        res = num / den
        return round(res, 4) if not math.isnan(res) else default
    except Exception:
        return default

def calc_delta(curr: float, prior: float) -> Tuple[float, float]:
    delta = round(curr - prior, 4)
    pct = safe_div(delta, abs(prior)) * 100.0 if prior != 0.0 else 0.0
    return delta, round(pct, 2)

def get_rag_status(kpi_key: str, val: float, delta: float = 0.0) -> str:
    bm = config.BENCHMARKS.get(kpi_key)
    higher_better = {
        "gross_profit_margin", "net_profit_margin", "operating_margin", "ebitda_margin",
        "roa", "roe", "roce", "current_ratio", "quick_ratio", "cash_ratio",
        "nwc_ratio", "operating_cf_ratio", "interest_coverage", "debt_service_coverage",
        "asset_turnover", "fixed_asset_turnover", "inventory_turnover", "receivables_turnover", "payables_turnover",
        "revenue_growth", "gross_profit_growth", "ebitda_growth", "ebit_growth", "net_income_growth", "eps", "book_value_per_share"
    }
    lower_better = {
        "cost_to_income_ratio", "cogs_ratio", "debt_to_equity", "debt_to_assets",
        "net_debt_to_ebitda", "dso", "dio", "ccc"
    }

    if kpi_key in higher_better:
        if bm is not None and val < bm * 0.8:
            return "RED"
        if val >= (bm if bm is not None else 0) and delta < 0:
            return "AMBER"
        if bm is not None and val < bm:
            return "AMBER"
        return "GREEN"

    elif kpi_key in lower_better:
        if bm is not None and val > bm * 1.2:
            return "RED"
        if val <= (bm if bm is not None else 999999) and delta > 0:
            return "AMBER"
        if bm is not None and val > bm:
            return "AMBER"
        return "GREEN"

    if delta < 0:
        return "AMBER"
    return "GREEN"

class KPIEngine:
    """
    Computes all 40+ Financial KPIs across all 10 periods.
    Provides QoQ, YoY, 8-Quarter sparklines, RAG status, and comparative analysis.
    """

    def __init__(self, records: List[Dict[str, Any]], shares_outstanding: float = 1000000.0, headcount: int = 500):
        self.fe = FinancialEngine(records)
        self.shares = shares_outstanding if shares_outstanding > 0 else 1000000.0
        self.headcount = headcount if headcount > 0 else 500
        
        # Precompute statements for all 10 periods
        self.statements = {}
        for sheet_key, meta in config.SHEET_MAP.items():
            q = meta["quarter"]
            fy = meta["year"]
            p_key = f"{q}{fy.replace('FY20', 'FY')}"
            
            pnl = self.fe.generate_income_statement(q, fy)
            bs = self.fe.generate_balance_sheet(q, fy)
            
            self.statements[p_key] = {
                "pnl": pnl,
                "bs": bs,
                "period_id": meta["period_id"],
                "label": meta["label"],
                "quarter": q,
                "year": fy
            }

    def _get_raw_kpis(self, p_key: str) -> Dict[str, float]:
        st = self.statements.get(p_key)
        if not st:
            return {}

        pnl = st["pnl"]
        bs  = st["bs"]

        rev   = pnl["net_revenue"]
        gp    = pnl["gross_profit"]
        cogs  = pnl["cogs"]["total"]
        opex  = pnl["opex"]["total"]
        ebitda = pnl["ebitda"]
        ebit  = pnl["ebit"]
        ni    = pnl["net_income"]
        int_exp = pnl["interest_expense"]

        ca  = bs["assets"]["current_assets"]["total"]
        cash = bs["assets"]["current_assets"]["cash_and_equivalents"]
        ar   = bs["assets"]["current_assets"]["accounts_receivable"]
        inv  = bs["assets"]["current_assets"]["inventory"]
        nca  = bs["assets"]["non_current_assets"]["total"]
        ppe  = bs["assets"]["non_current_assets"]["property_plant_equipment_net"]
        ta   = bs["assets"]["total_assets"]

        cl   = bs["liabilities"]["current_liabilities"]["total"]
        ap   = bs["liabilities"]["current_liabilities"]["accounts_payable"]
        st_debt = bs["liabilities"]["current_liabilities"]["short_term_debt"]
        ncl  = bs["liabilities"]["non_current_liabilities"]["total"]
        lt_debt = bs["liabilities"]["non_current_liabilities"]["long_term_debt"]
        tl   = bs["liabilities"]["total_liabilities"]

        eq   = bs["equity"]["total_equity"]
        ocf  = ni + pnl["depreciation_amortization"]

        total_debt = st_debt + lt_debt
        net_debt   = total_debt - cash
        nwc        = ca - cl
        cap_emp    = ta - cl if (ta - cl) != 0 else eq

        is_quarter = p_key.startswith("Q")
        days = 91.0 if is_quarter else 365.0
        ann_mult = 4.0 if is_quarter else 1.0

        # Calculations
        gp_margin   = safe_div(gp, rev) * 100.0
        np_margin   = safe_div(ni, rev) * 100.0
        op_margin   = safe_div(ebit, rev) * 100.0
        ebitda_margin = safe_div(ebitda, rev) * 100.0
        roa         = safe_div(ni, ta) * 100.0
        roe         = safe_div(ni, eq) * 100.0
        roce        = safe_div(ebit, cap_emp) * 100.0
        cost_to_inc = safe_div(opex, rev) * 100.0
        cogs_ratio  = safe_div(cogs, rev) * 100.0

        curr_ratio  = safe_div(ca, cl)
        quick_ratio = safe_div(ca - inv, cl)
        cash_ratio  = safe_div(cash, cl)
        nwc_ratio   = safe_div(nwc, rev) * 100.0
        ocf_ratio   = safe_div(ocf, cl)

        dte         = safe_div(total_debt, eq)
        dta         = safe_div(total_debt, ta)
        net_debt_ebitda = safe_div(net_debt, ebitda * ann_mult)
        int_cov     = safe_div(ebit, int_exp, default=99.0) if int_exp > 0 else 99.0
        dscr        = safe_div(ebitda, int_exp + st_debt, default=10.0)
        eq_mult     = safe_div(ta, eq)
        fin_lev     = eq_mult

        asset_turn  = safe_div(rev * ann_mult, ta)
        fa_turn     = safe_div(rev * ann_mult, ppe)
        inv_turn    = safe_div(cogs * ann_mult, inv)
        rec_turn    = safe_div(rev * ann_mult, ar)
        pay_turn    = safe_div(cogs * ann_mult, ap)

        dso         = safe_div(days, rec_turn)
        dio         = safe_div(days, inv_turn)
        dpo         = safe_div(days, pay_turn)
        ccc         = dso + dio - dpo
        rev_per_emp = safe_div(rev, self.headcount)

        paid_in_cap = bs["equity"].get("paid_in_capital", 60000.0)
        share_issue_price = 10.0
        shares_outstanding = safe_div(paid_in_cap, share_issue_price, default=6000.0)
        if shares_outstanding == 0:
            shares_outstanding = 6000.0

        eps         = safe_div(ni, shares_outstanding)
        bvps        = safe_div(eq, shares_outstanding)

        return {
            "gross_profit_margin": round(gp_margin, 2),
            "net_profit_margin": round(np_margin, 2),
            "operating_margin": round(op_margin, 2),
            "ebitda_margin": round(ebitda_margin, 2),
            "roa": round(roa, 2),
            "roe": round(roe, 2),
            "roce": round(roce, 2),
            "cost_to_income_ratio": round(cost_to_inc, 2),
            "cogs_ratio": round(cogs_ratio, 2),

            "current_ratio": round(curr_ratio, 2),
            "quick_ratio": round(quick_ratio, 2),
            "cash_ratio": round(cash_ratio, 2),
            "net_working_capital": round(nwc, 2),
            "nwc_ratio": round(nwc_ratio, 2),
            "operating_cf_ratio": round(ocf_ratio, 2),

            "debt_to_equity": round(dte, 2),
            "debt_to_assets": round(dta, 2),
            "net_debt": round(net_debt, 2),
            "net_debt_to_ebitda": round(net_debt_ebitda, 2),
            "interest_coverage": round(int_cov, 2),
            "debt_service_coverage": round(dscr, 2),
            "equity_multiplier": round(eq_mult, 2),
            "financial_leverage": round(fin_lev, 2),

            "asset_turnover": round(asset_turn, 2),
            "fixed_asset_turnover": round(fa_turn, 2),
            "inventory_turnover": round(inv_turn, 2),
            "receivables_turnover": round(rec_turn, 2),
            "payables_turnover": round(pay_turn, 2),
            "dso": round(dso, 2),
            "dio": round(dio, 2),
            "dpo": round(dpo, 2),
            "ccc": round(ccc, 2),
            "revenue_per_employee": round(rev_per_emp, 2),

            "eps": round(eps, 2),
            "book_value_per_share": round(bvps, 2),
            "diluted_eps": round(eps, 2),

            "_net_revenue": rev,
            "_gross_profit": gp,
            "_ebitda": ebitda,
            "_ebit": ebit,
            "_net_income": ni,
            "_total_assets": ta,
            "_equity": eq,
            "_operating_cf": ocf
        }

    def get_all_kpis_for_period(self, p_key: str) -> Dict[str, Any]:
        raw_curr = self._get_raw_kpis(p_key)
        if not raw_curr:
            return {}

        quarter_order = config.QUARTER_ORDER_8Q
        qoq_prior_key = None
        yoy_prior_key = None

        if p_key in quarter_order:
            idx = quarter_order.index(p_key)
            if idx > 0:
                qoq_prior_key = quarter_order[idx - 1]
            if idx >= 4:
                yoy_prior_key = quarter_order[idx - 4]
        elif p_key == "AnnualFY24":
            yoy_prior_key = "AnnualFY23"
            qoq_prior_key = "AnnualFY23"

        raw_qoq = self._get_raw_kpis(qoq_prior_key) if qoq_prior_key else {}
        raw_yoy = self._get_raw_kpis(yoy_prior_key) if yoy_prior_key else {}

        trend_8q_data = {}
        for q_key in quarter_order:
            q_kpis = self._get_raw_kpis(q_key)
            for k, v in q_kpis.items():
                if not k.startswith("_"):
                    if k not in trend_8q_data:
                        trend_8q_data[k] = []
                    trend_8q_data[k].append(v)

        output = {
            "profitability": {},
            "liquidity": {},
            "solvency": {},
            "efficiency": {},
            "growth": {},
            "valuation": {}
        }

        category_map = {
            "profitability": ["gross_profit_margin", "net_profit_margin", "operating_margin", "ebitda_margin", "roa", "roe", "roce", "cost_to_income_ratio", "cogs_ratio"],
            "liquidity": ["current_ratio", "quick_ratio", "cash_ratio", "net_working_capital", "nwc_ratio", "operating_cf_ratio"],
            "solvency": ["debt_to_equity", "debt_to_assets", "net_debt", "net_debt_to_ebitda", "interest_coverage", "debt_service_coverage", "equity_multiplier", "financial_leverage"],
            "efficiency": ["asset_turnover", "fixed_asset_turnover", "inventory_turnover", "receivables_turnover", "payables_turnover", "dso", "dio", "dpo", "ccc", "revenue_per_employee"],
            "valuation": ["eps", "book_value_per_share", "diluted_eps"]
        }

        for cat, kpi_keys in category_map.items():
            for k in kpi_keys:
                val = raw_curr.get(k, 0.0)
                qoq_val = raw_qoq.get(k, val)
                yoy_val = raw_yoy.get(k, val)

                qoq_delta = round(val - qoq_val, 2)
                qoq_pct = safe_div(qoq_delta, abs(qoq_val)) * 100.0 if qoq_val != 0 else 0.0

                yoy_delta = round(val - yoy_val, 2)
                yoy_pct = safe_div(yoy_delta, abs(yoy_val)) * 100.0 if yoy_val != 0 else 0.0

                bm = config.BENCHMARKS.get(k, 0.0)
                rag = get_rag_status(k, val, qoq_delta)

                is_lower_better = k in ["cost_to_income_ratio", "cogs_ratio", "debt_to_equity", "debt_to_assets", "net_debt_to_ebitda", "dso", "dio", "ccc"]
                trend_dir = "improving" if (qoq_delta < 0 if is_lower_better else qoq_delta > 0) else ("declining" if (qoq_delta > 0 if is_lower_better else qoq_delta < 0) else "stable")
                
                is_target_met = (val <= bm) if is_lower_better else (val >= bm)

                unit = "%" if "margin" in k or "ratio" in k or k in ["roa", "roe", "roce"] else ("days" if k in ["dso", "dio", "dpo", "ccc"] else ("₹" if k in ["net_working_capital", "net_debt", "eps", "book_value_per_share", "revenue_per_employee"] else "x"))

                output[cat][k] = {
                    "value": val,
                    "unit": unit,
                    "qoq_delta": qoq_delta,
                    "qoq_pct": round(qoq_pct, 2),
                    "yoy_delta": yoy_delta,
                    "yoy_pct": round(yoy_pct, 2),
                    "trend_8Q": trend_8q_data.get(k, []),
                    "benchmark": bm,
                    "status": "above_benchmark" if is_target_met else "below_benchmark",
                    "rag_status": rag,
                    "trend_dir": trend_dir
                }

        growth_items = {
            "revenue_growth": ("_net_revenue", "%"),
            "gross_profit_growth": ("_gross_profit", "%"),
            "ebitda_growth": ("_ebitda", "%"),
            "ebit_growth": ("_ebit", "%"),
            "net_income_growth": ("_net_income", "%"),
            "total_assets_growth": ("_total_assets", "%"),
            "equity_growth": ("_equity", "%"),
            "operating_cf_growth": ("_operating_cf", "%")
        }

        for g_kpi, (raw_key, u) in growth_items.items():
            curr_v = raw_curr.get(raw_key, 0.0)
            prior_v = raw_qoq.get(raw_key, curr_v)
            g_pct = safe_div(curr_v - prior_v, abs(prior_v)) * 100.0 if prior_v != 0 else 0.0
            
            yoy_prior_v = raw_yoy.get(raw_key, curr_v)
            yoy_g_pct = safe_div(curr_v - yoy_prior_v, abs(yoy_prior_v)) * 100.0 if yoy_prior_v != 0 else 0.0

            rag = "GREEN" if g_pct >= 5.0 else ("AMBER" if g_pct >= 0.0 else "RED")

            output["growth"][g_kpi] = {
                "value": round(g_pct, 2),
                "unit": "%",
                "qoq_delta": round(g_pct, 2),
                "qoq_pct": round(g_pct, 2),
                "yoy_delta": round(yoy_g_pct, 2),
                "yoy_pct": round(yoy_g_pct, 2),
                "trend_8Q": [],
                "benchmark": 10.0,
                "status": "above_benchmark" if rag == "GREEN" else "below_benchmark",
                "rag_status": rag,
                "trend_dir": "improving" if g_pct >= 0 else "declining"
            }

        return output
