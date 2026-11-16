"""
AI Financial Health & Risk Analyzer for Netcrafty.
Combines deterministic heuristic diagnostics with Google Gemini Generative AI
to pinpoint exactly which figures require management attention and intervention.
"""

from __future__ import annotations
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from engine import NetcraftyModel, CHANNELS, CHANNEL_NAMES

# Default supported models (Google Gemini 3.8 is the latest active standard)
SUPPORTED_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.8-pro",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

CONFIG_FILE = "api_config.json"


def save_api_config(config: Dict[str, Any]):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def load_api_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # Auto-upgrade deprecated gemini-2.5-flash to gemini-3.8-flash
                if cfg.get("model") == "gemini-2.5-flash":
                    cfg["model"] = "gemini-3.8-flash"
                return cfg
        except Exception:
            pass
    # Environment variable fallback
    return {
        "api_key": os.environ.get("GEMINI_API_KEY", ""),
        "model": "gemini-3.8-flash",
        "persona": "Aggressive D2C Growth CFO & Profitability Auditor"
    }


def test_gemini_connection(api_key: str, model_name: str = "gemini-3.8-flash") -> Tuple[bool, str]:
    """Test connection to Gemini API using google-genai, with intelligent auto-fallback."""
    if not api_key or not api_key.strip():
        return False, "API Key is empty. Please enter a valid Google Gemini API key."
    try:
        from google import genai
        client = genai.Client(api_key=api_key.strip())
        
        # Try requested model
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Respond with only the single word: OK"
            )
            if response and response.text:
                return True, f"Connection Successful! Verified with model: {model_name}"
        except Exception as e_model:
            err_str = str(e_model)
            # If model is deprecated or 404, attempt auto-fallback to gemini-3.8-flash
            if ("404" in err_str or "not available" in err_str.lower()) and model_name != "gemini-3.8-flash":
                fallback_resp = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents="Respond with only the single word: OK"
                )
                if fallback_resp and fallback_resp.text:
                    return True, f"Connection Successful! Switched to active model: gemini-3.8-flash (Model '{model_name}' was deprecated)"
            raise e_model

        return False, "Received empty response from Gemini API."
    except Exception as e:
        return False, f"API Connection Error: {str(e)}"


class HeuristicDiagnostic:
    """
    Deterministic rule-based audit that runs instantly without an API key
    to identify numbers and metrics that need immediate attention.
    """
    @staticmethod
    def analyze(model: NetcraftyModel) -> Dict[str, Any]:
        results = model.compute()
        kpi = model.get_kpi_summary()
        
        red_flags = []
        warnings = []
        opportunities = []
        channel_metrics = {c: {} for c in CHANNELS}

        # Inspect Month 1 as primary baseline
        m1 = results[0]["rows"]
        m1_data = model.months[0]
        
        # 1. Total Cumulative Profit / Loss Check
        if kpi["net_profit"] < 0:
            red_flags.append({
                "figure": f"12-Month Net Loss: ₹{abs(kpi['net_profit']):,.0f}",
                "metric": "12-Month Cumulative P&L",
                "severity": "CRITICAL",
                "impact": "High Cash Burn",
                "detail": f"The business operates at a cumulative loss of ₹{abs(kpi['net_profit']):,.0f} across 12 months with no break-even achieved.",
                "recommendation": "Review high shared agency expenses, improve COD delivery rates, or expand prepaid share to reach profitability."
            })
        elif kpi["first_positive_month"] and kpi["first_positive_month"] > 6:
            warnings.append({
                "figure": f"Break-even at Month {kpi['first_positive_month']}",
                "metric": "Break-even Horizon",
                "severity": "WARNING",
                "impact": "Slow Capital Recovery",
                "detail": f"Cumulative profit only turns positive in Month {kpi['first_positive_month']}.",
                "recommendation": "Accelerate marketing efficiency in early months to shorten break-even to under 90 days."
            })

        # 2. Channel-by-Channel Analysis
        for c in CHANNELS:
            name = CHANNEL_NAMES[c]
            ch_data = m1_data.channels[c]
            r = m1[c]
            leads = r["volume"]
            deliv = r["delivered"]
            conf = r["confirmed"]
            rev = r["received"]
            cost = r["costs"]
            profit = r["profit"]

            channel_metrics[c] = {
                "name": name,
                "leads": leads,
                "delivered": deliv,
                "revenue": rev,
                "costs": cost,
                "profit": profit,
                "margin": (profit / rev * 100) if rev > 0 else 0.0,
                "ad_cost_per_lead": ch_data["ad"],
                "delivery_pct": ch_data["delivery"],
                "confirm_pct": ch_data["confirm"]
            }

            if leads > 0:
                # Delivery Rate / RTO Risk
                if ch_data["delivery"] < 60.0:
                    red_flags.append({
                        "figure": f"{ch_data['delivery']:.0f}% Delivery Rate",
                        "metric": f"{name} Delivery %",
                        "severity": "CRITICAL",
                        "impact": f"High RTO & Return Courier Waste ({100 - ch_data['delivery']:.0f}% lost)",
                        "detail": f"In {name}, {100 - ch_data['delivery']:.0f}% of confirmed orders fail to deliver. You are paying ad spend, packaging, and shipping on orders that bring zero revenue.",
                        "recommendation": "Implement automated WhatsApp address verification, OTP verification before dispatch, and offer prepaid discounts."
                    })
                elif ch_data["delivery"] < 75.0:
                    warnings.append({
                        "figure": f"{ch_data['delivery']:.0f}% Delivery Rate",
                        "metric": f"{name} Delivery %",
                        "severity": "WARNING",
                        "impact": "Moderate RTO drag",
                        "detail": f"{name} delivery rate is below the 75% e-commerce benchmark.",
                        "recommendation": "Partner with reliable NDR (Non-Delivery Report) management couriers."
                    })

                # Ad cost efficiency
                ad_spend = r["ads"]
                if rev > 0 and (ad_spend / rev) > 0.40:
                    red_flags.append({
                        "figure": f"Ad Cost is {ad_spend / rev * 100:.1f}% of Revenue",
                        "metric": f"{name} Ad Cost Ratio",
                        "severity": "CRITICAL",
                        "impact": "Ad Burn / Negative Unit Economics",
                        "detail": f"You spend ₹{ad_spend:,.0f} on ads to generate ₹{rev:,.0f} in revenue (Ad to Revenue ratio of {ad_spend / rev * 100:.1f}%).",
                        "recommendation": f"Target reducing Ad per Lead (currently ₹{ch_data['ad']:.0f}) or increase conversion rate."
                    })

                # Confirmation Rate
                if ch_data["confirm"] < 50.0:
                    warnings.append({
                        "figure": f"{ch_data['confirm']:.0f}% Confirmation Rate",
                        "metric": f"{name} Confirmation %",
                        "severity": "WARNING",
                        "impact": "Funnel Leakage",
                        "detail": f"Over {100 - ch_data['confirm']:.0f}% of leads are lost before order confirmation.",
                        "recommendation": "Streamline checkout flow and engage leads via instant WhatsApp follow-up bots within 2 minutes."
                    })

        # 3. Transit Uplift Analysis
        web_uplift = m1_data.channels["wc"]["uplift"]
        if web_uplift >= 25.0:
            warnings.append({
                "figure": f"{web_uplift:.0f}% Transit Uplift",
                "metric": "In-Transit Deferred Revenue & Extra Costs",
                "severity": "WARNING",
                "impact": "Cash Liquidity Delay",
                "detail": f"A {web_uplift:.0f}% uplift delays ₹{sum(m1[c]['deferred'] for c in CHANNELS):,.0f} in Month 1 revenue into Month 2 and adds {web_uplift:.0f}% extra buffer on product & shipping costs.",
                "recommendation": "Negotiate faster courier remittance cycles (e.g. T+1 or T+2 COD settlement) to lower working capital lag."
            })

        # 4. Shared Fixed Costs Overhead Ratio
        total_shared = sum(m1_data.shared.values())
        total_m1_deliv = results[0]["all_delivered"]
        if total_m1_deliv > 0:
            shared_per_order = total_shared / total_m1_deliv
            if shared_per_order > 300.0:
                red_flags.append({
                    "figure": f"₹{shared_per_order:,.0f} Shared Cost Per Delivered Order",
                    "metric": "Fixed Overhead Dilution",
                    "severity": "CRITICAL",
                    "impact": "Heavy Overhead Crushing Margins",
                    "detail": f"Monthly shared expenses (Agency: ₹{m1_data.shared['agency']:,.0f}, Server: ₹{m1_data.shared['server']:,.0f}, Influencer: ₹{m1_data.shared['influencer']:,.0f} = ₹{total_shared:,.0f}) average ₹{shared_per_order:,.0f} per delivered order across {total_m1_deliv:.1f} orders.",
                    "recommendation": "Scale lead volume to dilute fixed overhead, or negotiate agency retainers down until order volume crosses 1,500 orders/month."
                })
        else:
            red_flags.append({
                "figure": f"₹{total_shared:,.0f} Fixed Costs with 0 Delivered Orders",
                "metric": "Zero Volume Overhead",
                "severity": "CRITICAL",
                "impact": "100% Fixed Cost Loss",
                "detail": "Shared expenses are being incurred without any successful deliveries.",
                "recommendation": "Increase lead generation or pause fixed agency retainers."
            })

        # 5. Staffing Efficiency
        web_leads = m1_data.splits["web"]["total"]
        web_cap = m1_data.channels["wc"]["capacity"]
        if web_leads > 0 and (web_leads % web_cap > 0) and (web_leads % web_cap <= web_cap * 0.2):
            rem = web_leads % web_cap
            warnings.append({
                "figure": f"{rem:.0f} leads pushed staffing by 1 full employee",
                "metric": "Website Staffing Ceiling Discontinuity",
                "severity": "WARNING",
                "impact": "Excess Payroll Cost",
                "detail": f"With a handling capacity of {web_cap:.0f} leads/person, {web_leads:.0f} leads requires {results[0]['web_staff']} employees. The last employee is only handling {rem:.0f} leads ({rem/web_cap*100:.0f}% utilization).",
                "recommendation": f"Increase lead volume to fully saturate capacity ({results[0]['web_staff'] * web_cap:.0f} leads) or use partial automation."
            })

        # 6. Prepaid Share Opportunity
        web_prep = m1_data.splits["web"]["prepaid"]
        if web_prep < 20.0 and web_leads > 0:
            opportunities.append({
                "figure": f"{web_prep:.0f}% Website Prepaid Share",
                "metric": "Prepaid Growth Opportunity",
                "impact": "High Margin & 0% RTO Upside",
                "detail": f"Website is currently only {web_prep:.0f}% prepaid. Prepaid orders have a {m1_data.channels['wp']['delivery']:.0f}% delivery rate compared to {m1_data.channels['wc']['delivery']:.0f}% for COD.",
                "action": "Incentivize prepaid with a ₹100 instant discount or free gift; lifting prepaid to 35% will sharply increase delivered orders and cut return logistics."
            })

        # Score computation (0 to 100)
        score = 100
        score -= min(50, len(red_flags) * 18)
        score -= min(30, len(warnings) * 7)
        if kpi["net_profit"] < 0:
            score = min(score, 45)
        score = max(5, min(100, score))

        return {
            "score": score,
            "kpi": kpi,
            "red_flags": red_flags,
            "warnings": warnings,
            "opportunities": opportunities,
            "channel_metrics": channel_metrics
        }


class GeminiAdvisor:
    """
    Connects to Google Gemini API using google-genai SDK to provide deep,
    custom financial analysis and strategic guidance.
    """
    def __init__(self, api_key: str, model_name: str = "gemini-3.8-flash", persona: Optional[str] = None):
        self.api_key = api_key.strip()
        self.model_name = model_name or "gemini-3.8-flash"
        self.persona = persona or "Aggressive D2C Growth CFO & Profitability Auditor"

    def _call_gemini(self, client, contents: str) -> str:
        """Call Gemini with auto-fallback to gemini-3.8-flash if requested model is deprecated."""
        try:
            resp = client.models.generate_content(
                model=self.model_name,
                contents=contents
            )
            return resp.text if resp and resp.text else ""
        except Exception as e:
            err_str = str(e)
            if ("404" in err_str or "not available" in err_str.lower()) and self.model_name != "gemini-3.8-flash":
                self.model_name = "gemini-3.8-flash"
                resp = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=contents
                )
                return resp.text if resp and resp.text else ""
            raise e

    def generate_audit(self, model: NetcraftyModel, heuristic: Dict[str, Any]) -> str:
        """Generate comprehensive AI diagnostic audit report."""
        if not self.api_key:
            return "Please provide a valid Gemini API Key in the 'API Integration' tab to enable Live AI Analysis."

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)

            kpi = heuristic["kpi"]
            m1_data = model.months[0]
            summary_payload = {
                "total_delivered_orders": kpi["total_delivered"],
                "total_revenue_inr": kpi["total_revenue"],
                "total_costs_inr": kpi["total_costs"],
                "net_profit_inr": kpi["net_profit"],
                "profit_margin_pct": kpi["profit_margin"],
                "break_even_month": kpi["first_positive_month"],
                "website_leads_month1": m1_data.splits["web"]["total"],
                "website_prepaid_pct": m1_data.splits["web"]["prepaid"],
                "whatsapp_leads_month1": m1_data.splits["wa"]["total"],
                "whatsapp_prepaid_pct": m1_data.splits["wa"]["prepaid"],
                "channel_metrics": heuristic["channel_metrics"],
                "shared_costs_monthly": m1_data.shared,
                "identified_red_flags": [f["figure"] + ": " + f["impact"] for f in heuristic["red_flags"]],
                "identified_warnings": [w["figure"] + ": " + w["impact"] for w in heuristic["warnings"]]
            }

            prompt = f"""You are an elite {self.persona}.
Analyze the following 12-month advertising product-costing financial dataset for a direct-to-consumer (D2C) multi-channel business:

### FINANCIAL DATA PAYLOAD:
```json
{json.dumps(summary_payload, indent=2)}
```

### INSTRUCTIONS:
Conduct an incisive financial health audit focusing on:
1. **EXECUTIVE HEALTH ASSESSMENT**: Give an overall assessment of viability and burn rate.
2. **FIGURES TO TAKE CARE OF IMMEDIATELY**: List the top 3-5 specific numbers from the inputs/outputs that are actively harming profitability (e.g. specific channel delivery rates, advertisement per lead, shared overhead per order, transit uplift percentages). For EACH figure, explain WHY it is toxic and give an EXACT TARGET NUMBER to achieve.
3. **CHANNEL-BY-CHANNEL PRESCRIPTIONS**: Provide actionable steps for Website COD, Website Prepaid, WhatsApp COD, and WhatsApp Prepaid.
4. **CASH FLOW & TRANSIT UPLIFT STRATEGY**: Provide concrete advice on how to manage in-transit revenue deferral and inventory working capital.
5. **30-60-90 DAY OPTIMIZATION ROADMAP**: Bullet points with clear immediate, medium, and scale-phase milestones.

Format your response in sleek, engaging Markdown with bold accents, tables where helpful, bullet points, and high readability. Be direct, mathematically grounded, and actionable.
"""
            text = self._call_gemini(client, prompt)
            return text if text else "AI produced an empty response."

        except Exception as e:
            return f"Error contacting Gemini AI: {str(e)}\n\nPlease verify your API key and network connection."

    def answer_question(self, question: str, model: NetcraftyModel, chat_history: List[Dict[str, str]]) -> str:
        """Interactive Q&A answering user's follow-up questions about the financial figures."""
        if not self.api_key:
            return "Please provide an API Key in the 'API Integration' tab."

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)

            kpi = model.get_kpi_summary()
            context_summary = f"""Current 12-Month Summary:
- Total Delivered Orders: {kpi['total_delivered']:,.1f}
- Total Revenue: ₹{kpi['total_revenue']:,.2f}
- Total Costs: ₹{kpi['total_costs']:,.2f}
- Net Profit/Loss: ₹{kpi['net_profit']:,.2f} ({kpi['profit_margin']:.1f}% margin)
- Break-even Month: {kpi['first_positive_month'] or 'None within 12 months'}
"""

            conversation_text = ""
            for msg in chat_history[-6:]:
                role = "User" if msg["role"] == "user" else "Advisor"
                conversation_text += f"{role}: {msg['content']}\n"

            prompt = f"""You are a top-tier D2C CFO and Financial Analyst.
Context on the user's Netcrafty 12-month model:
{context_summary}

Recent conversation:
{conversation_text}

User Question: {question}

Provide a concise, practical, mathematically accurate response in Indian Rupees (₹). Explain which figures to adjust, by how much, and why."""

            text = self._call_gemini(client, prompt)
            return text if text else "No response generated."
        except Exception as e:
            return f"Error: {str(e)}"
