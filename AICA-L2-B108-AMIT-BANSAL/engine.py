"""
Netcrafty Costing Engine
Faithfully implements the 4-channel, 12-month advertising product costing model
matching the canonical Netcrafty specification.
"""

from __future__ import annotations
import math
from typing import Dict, List, Any, Optional
import pandas as pd

CHANNELS = ["wc", "wp", "ac", "ap"]
CHANNEL_NAMES = {
    "wc": "Website COD",
    "wp": "Website Prepaid",
    "ac": "WhatsApp COD",
    "ap": "WhatsApp Prepaid"
}
CHANNEL_COLORS = {
    "wc": "#4F46E5",  # Royal Indigo
    "wp": "#06B6D4",  # Cyan Blue
    "ac": "#10B981",  # Emerald Green
    "ap": "#F59E0B"   # Amber Gold
}

# Website Prepaid and WhatsApp Prepaid share these assumptions with their COD channel
LINKED_FIELDS = [
    "confirm", "ad", "product", "packing", "postage",
    "salary", "capacity", "uplift"
]

METRICS_CONFIG = [
    ("group", "ORDER FUNNEL"),
    ("volume", "Leads", "number"),
    ("confirmed", "Confirmed orders", "number"),
    ("delivered", "Successfully delivered", "number"),
    ("staff", "Allocated employee count", "number"),
    
    ("group", "DIRECT COSTS"),
    ("ads", "Advertisement cost", "money"),
    ("staffing", "Employee salary", "money"),
    ("product", "Product + transit uplift", "money"),
    ("packing", "Packing cost", "money"),
    ("postage", "Postage + transit uplift", "money"),
    
    ("group", "ALLOCATED FIXED COSTS"),
    ("agency", "Agency expense", "money"),
    ("server", "Server expense", "money"),
    ("influencer", "Influencer expense", "money"),
    ("costs", "TOTAL COST", "money"),
    
    ("group", "REVENUE AND PROFIT"),
    ("gross", "Gross sales on deliveries", "money"),
    ("deferred", "Revenue carried to next month", "money"),
    ("previous", "Prior-month revenue received", "money"),
    ("received", "Revenue this month", "money"),
    ("profit", "NET PROFIT / LOSS", "money"),
    ("cumulative", "CUMULATIVE PROFIT / LOSS", "money")
]


def default_channel_assumptions() -> Dict[str, Dict[str, float]]:
    return {
        "wc": {
            "volume": 50.0, "confirm": 90.0, "delivery": 50.0, "ad": 300.0,
            "product": 200.0, "packing": 30.0, "postage": 75.0, "price": 1400.0,
            "salary": 10000.0, "capacity": 50.0, "uplift": 30.0
        },
        "wp": {
            "volume": 0.0, "confirm": 90.0, "delivery": 90.0, "ad": 300.0,
            "product": 200.0, "packing": 30.0, "postage": 75.0, "price": 1400.0,
            "salary": 10000.0, "capacity": 50.0, "uplift": 30.0
        },
        "ac": {
            "volume": 0.0, "confirm": 30.0, "delivery": 50.0, "ad": 15.0,
            "product": 200.0, "packing": 30.0, "postage": 75.0, "price": 1400.0,
            "salary": 10000.0, "capacity": 100.0, "uplift": 30.0
        },
        "ap": {
            "volume": 0.0, "confirm": 30.0, "delivery": 90.0, "ad": 15.0,
            "product": 200.0, "packing": 30.0, "postage": 75.0, "price": 1400.0,
            "salary": 10000.0, "capacity": 100.0, "uplift": 30.0
        }
    }


def default_splits() -> Dict[str, Dict[str, float]]:
    return {
        "web": {"total": 50.0, "prepaid": 0.0},
        "wa": {"total": 0.0, "prepaid": 0.0}
    }


def default_shared() -> Dict[str, float]:
    return {
        "agency": 150000.0,
        "server": 20000.0,
        "influencer": 40000.0
    }


class MonthData:
    def __init__(
        self,
        channels: Optional[Dict[str, Dict[str, float]]] = None,
        splits: Optional[Dict[str, Dict[str, float]]] = None,
        shared: Optional[Dict[str, float]] = None
    ):
        self.channels = channels if channels is not None else default_channel_assumptions()
        self.splits = splits if splits is not None else default_splits()
        self.shared = shared if shared is not None else default_shared()

    def sync_prepaid_links(self):
        """Synchronize linked read-only fields from COD to Prepaid for same month."""
        for field in LINKED_FIELDS:
            self.channels["wp"][field] = self.channels["wc"][field]
            self.channels["ap"][field] = self.channels["ac"][field]

    def sync_splits(self):
        """Derive COD and Prepaid lead counts from group totals and prepaid percentages."""
        # Website
        web_total = max(0.0, float(self.splits["web"]["total"]))
        web_prep_pct = max(0.0, min(100.0, float(self.splits["web"]["prepaid"])))
        self.channels["wc"]["volume"] = web_total * (100.0 - web_prep_pct) / 100.0
        self.channels["wp"]["volume"] = web_total * web_prep_pct / 100.0

        # WhatsApp
        wa_total = max(0.0, float(self.splits["wa"]["total"]))
        wa_prep_pct = max(0.0, min(100.0, float(self.splits["wa"]["prepaid"])))
        self.channels["ac"]["volume"] = wa_total * (100.0 - wa_prep_pct) / 100.0
        self.channels["ap"]["volume"] = wa_total * wa_prep_pct / 100.0

    def copy(self) -> MonthData:
        return MonthData(
            channels={c: dict(v) for c, v in self.channels.items()},
            splits={g: dict(v) for g, v in self.splits.items()},
            shared=dict(self.shared)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channels": self.channels,
            "splits": self.splits,
            "shared": self.shared
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MonthData:
        md = cls(
            channels=data.get("channels"),
            splits=data.get("splits"),
            shared=data.get("shared")
        )
        md.sync_prepaid_links()
        md.sync_splits()
        return md


class NetcraftyModel:
    def __init__(self, num_months: int = 12):
        self.months: List[MonthData] = [MonthData() for _ in range(num_months)]
        self.overrides: Dict[str, bool] = {}
        self.sync_all()

    def sync_all(self):
        for m in self.months:
            m.sync_prepaid_links()
            m.sync_splits()

    def add_month(self):
        new_month = self.months[0].copy()
        new_month.sync_prepaid_links()
        new_month.sync_splits()
        self.months.append(new_month)

    def set_value(self, month_idx: int, category: str, field_key: str, value: float, cascade: bool = True):
        """Set a value in a month with automatic Month 1 cascade and override tracking."""
        val = max(0.0, float(value))
        if field_key in ["confirm", "delivery", "uplift", "prepaid"]:
            val = min(100.0, val)

        target_month = self.months[month_idx]
        if category == "shared":
            target_month.shared[field_key] = val
        elif category.startswith("split"):
            group = "web" if "web" in category else "wa"
            target_month.splits[group][field_key] = val
        else:
            target_month.channels[category][field_key] = val

        override_key = f"{month_idx}_{category}_{field_key}"
        if month_idx > 0:
            self.overrides[override_key] = True
        elif cascade:
            # Cascade Month 1 value to all subsequent months that are not overridden
            for j in range(1, len(self.months)):
                sub_ov_key = f"{j}_{category}_{field_key}"
                if not self.overrides.get(sub_ov_key, False):
                    if category == "shared":
                        self.months[j].shared[field_key] = val
                    elif category.startswith("split"):
                        group = "web" if "web" in category else "wa"
                        self.months[j].splits[group][field_key] = val
                    else:
                        self.months[j].channels[category][field_key] = val

        self.sync_all()

    def restore_month1_link(self, month_idx: int, category: str, field_key: str):
        """Restore link to Month 1 for an overridden field."""
        override_key = f"{month_idx}_{category}_{field_key}"
        if override_key in self.overrides:
            del self.overrides[override_key]

        m0 = self.months[0]
        if category == "shared":
            val = m0.shared[field_key]
            self.months[month_idx].shared[field_key] = val
        elif category.startswith("split"):
            group = "web" if "web" in category else "wa"
            val = m0.splits[group][field_key]
            self.months[month_idx].splits[group][field_key] = val
        else:
            val = m0.channels[category][field_key]
            self.months[month_idx].channels[category][field_key] = val

        self.sync_all()

    def cascade_month1_to_all(self):
        """Force apply all Month 1 values across all 12 months, clearing overrides."""
        self.overrides.clear()
        m0 = self.months[0]
        for j in range(1, len(self.months)):
            self.months[j] = m0.copy()
        self.sync_all()

    def compute(self) -> List[Dict[str, Any]]:
        """
        Execute full financial calculation across all months.
        Returns a list of monthly dictionaries with channel breakdowns,
        cost lines, revenues, net profit, and cumulative balance.
        """
        self.sync_all()
        running_profit = 0.0
        previous_deferred = {c: 0.0 for c in CHANNELS}
        results = []

        for i, m in enumerate(self.months):
            leads = {}
            confirmed = {}
            delivered = {}

            for c in CHANNELS:
                ch = m.channels[c]
                leads[c] = ch["volume"]
                confirmed[c] = ch["volume"] * ch["confirm"] / 100.0
                delivered[c] = confirmed[c] * ch["delivery"] / 100.0

            web_leads = leads["wc"] + leads["wp"]
            wa_leads = leads["ac"] + leads["ap"]

            web_capacity = max(1.0, m.channels["wc"]["capacity"])
            wa_capacity = max(1.0, m.channels["ac"]["capacity"])

            web_staff = math.ceil(web_leads / web_capacity) if web_leads > 0 else 0
            wa_staff = math.ceil(wa_leads / wa_capacity) if wa_leads > 0 else 0

            all_delivered = sum(delivered[c] for c in CHANNELS)

            rows = {}
            for c in CHANNELS:
                ch = m.channels[c]
                is_wa = c.startswith("a")
                group_leads = wa_leads if is_wa else web_leads
                group_share = (leads[c] / group_leads) if group_leads > 0 else 0.0

                staff_count = wa_staff if is_wa else web_staff
                staff_salary = m.channels["ac"]["salary"] if is_wa else m.channels["wc"]["salary"]

                staffing_cost = staff_count * staff_salary * group_share
                staff_headcount = staff_count * group_share

                # Shared expenses allocation based on delivered order proportions
                share_of_deliveries = (delivered[c] / all_delivered) if all_delivered > 0 else 0.25

                ads_cost = leads[c] * ch["ad"]
                product_cost = confirmed[c] * ch["product"] * (1.0 + ch["uplift"] / 100.0)
                postage_cost = confirmed[c] * ch["postage"] * (1.0 + ch["uplift"] / 100.0)
                packing_cost = confirmed[c] * ch["packing"]

                agency_cost = m.shared["agency"] * share_of_deliveries
                server_cost = m.shared["server"] * share_of_deliveries
                influencer_cost = m.shared["influencer"] * share_of_deliveries

                total_costs = (
                    staffing_cost + ads_cost + product_cost + postage_cost +
                    packing_cost + agency_cost + server_cost + influencer_cost
                )

                gross_revenue = delivered[c] * ch["price"]
                deferred_revenue = gross_revenue * ch["uplift"] / 100.0
                prev_rev = previous_deferred[c]
                received_revenue = gross_revenue - deferred_revenue + prev_rev
                profit = received_revenue - total_costs

                rows[c] = {
                    "volume": leads[c],
                    "confirmed": confirmed[c],
                    "delivered": delivered[c],
                    "staff": staff_headcount,
                    "staffing": staffing_cost,
                    "ads": ads_cost,
                    "product": product_cost,
                    "postage": postage_cost,
                    "packing": packing_cost,
                    "agency": agency_cost,
                    "server": server_cost,
                    "influencer": influencer_cost,
                    "costs": total_costs,
                    "gross": gross_revenue,
                    "deferred": deferred_revenue,
                    "previous": prev_rev,
                    "received": received_revenue,
                    "profit": profit,
                    "share": share_of_deliveries
                }

            # Update prior-month carried revenue for next month
            previous_deferred = {c: rows[c]["deferred"] for c in CHANNELS}

            month_profit = sum(rows[c]["profit"] for c in CHANNELS)
            month_revenue = sum(rows[c]["received"] for c in CHANNELS)
            month_costs = sum(rows[c]["costs"] for c in CHANNELS)
            running_profit += month_profit

            results.append({
                "month_idx": i,
                "month_label": f"Month {i + 1}",
                "rows": rows,
                "web_staff": web_staff,
                "wa_staff": wa_staff,
                "all_delivered": all_delivered,
                "month_revenue": month_revenue,
                "month_costs": month_costs,
                "month_profit": month_profit,
                "cumulative_profit": running_profit
            })

        return results

    def get_kpi_summary(self) -> Dict[str, Any]:
        """Aggregate high-level metrics across all months."""
        results = self.compute()
        total_delivered = sum(r["all_delivered"] for r in results)
        total_revenue = sum(r["month_revenue"] for r in results)
        total_costs = sum(r["month_costs"] for r in results)
        net_profit = total_revenue - total_costs
        profit_margin = (net_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

        first_positive_idx = None
        for r in results:
            if r["cumulative_profit"] > 0:
                first_positive_idx = r["month_idx"] + 1
                break

        return {
            "total_delivered": total_delivered,
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "net_profit": net_profit,
            "profit_margin": profit_margin,
            "first_positive_month": first_positive_idx,
            "num_months": len(self.months)
        }

    def explain(self, key: str, channel: str, row: Dict[str, float], month_idx: int) -> str:
        """Generate mathematical explanation formula for table view matching HTML dashboard."""
        m = self.months[month_idx]
        ch = m.channels[channel]
        is_wa = channel.startswith("a")
        co = row["confirmed"]

        if key == "volume":
            return "Total source leads × channel allocation %"
        elif key == "confirmed":
            return f"{ch['volume']:,.1f} leads × {ch['confirm']:.1f}%"
        elif key == "delivered":
            return f"{co:,.1f} confirmed × {ch['delivery']:.1f}%"
        elif key == "staff":
            return "WhatsApp staff × share of leads" if is_wa else "Website staff × share of leads"
        elif key == "ads":
            return f"{ch['volume']:,.1f} leads × ₹{ch['ad']:,.0f}"
        elif key == "staffing":
            return "Group staff cost × channel share"
        elif key == "product":
            return f"{co:,.1f} × ₹{ch['product']:,.0f} × (1 + {ch['uplift']:.0f}%)"
        elif key == "packing":
            return f"{co:,.1f} × ₹{ch['packing']:,.0f}"
        elif key == "postage":
            return f"{co:,.1f} × ₹{ch['postage']:,.0f} × (1 + {ch['uplift']:.0f}%)"
        elif key == "agency":
            return f"₹{m.shared['agency']:,.0f} × {row['share']*100:.1f}%"
        elif key == "server":
            return f"₹{m.shared['server']:,.0f} × {row['share']*100:.1f}%"
        elif key == "influencer":
            return f"₹{m.shared['influencer']:,.0f} × {row['share']*100:.1f}%"
        elif key == "costs":
            return "Sum of direct + shared expenses"
        elif key == "gross":
            return f"{row['delivered']:,.1f} deliv × ₹{ch['price']:,.0f}"
        elif key == "deferred":
            return f"₹{row['gross']:,.0f} gross × {ch['uplift']:.0f}%"
        elif key == "previous":
            return "Carried from preceding month"
        elif key == "received":
            return "Gross − deferred + previous"
        elif key == "profit":
            return "Revenue received − total costs"
        elif key == "cumulative":
            return "Previous cumulative + current profit"
        return ""

    def export_dataframe(self) -> pd.DataFrame:
        """Create a comprehensive flattened pandas DataFrame for export."""
        results = self.compute()
        rows_list = []

        for r in results:
            m_idx = r["month_idx"]
            for item in METRICS_CONFIG:
                if item[0] == "group":
                    continue
                k, label, ftype = item
                row_dict = {
                    "Month": m_idx + 1,
                    "Metric": label,
                    "Type": ftype
                }
                total_val = 0.0
                for c in CHANNELS:
                    val = r["rows"][c][k] if k != "cumulative" else 0.0
                    total_val += val
                    row_dict[f"{CHANNEL_NAMES[c]} Calc"] = self.explain(k, c, r["rows"][c], m_idx)
                    row_dict[f"{CHANNEL_NAMES[c]} Value"] = val

                if k == "cumulative":
                    row_dict["Total"] = r["cumulative_profit"]
                elif k == "profit":
                    row_dict["Total"] = r["month_profit"]
                elif k == "received":
                    row_dict["Total"] = r["month_revenue"]
                elif k == "costs":
                    row_dict["Total"] = r["month_costs"]
                else:
                    row_dict["Total"] = total_val

                rows_list.append(row_dict)

        return pd.DataFrame(rows_list)
