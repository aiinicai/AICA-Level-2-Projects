"""The ratios Schedule III (Division I) asks every company to disclose, with the 25% change test.

Definitions follow the ICAI guidance on Schedule III. Where a ratio needs the previous year's
profit and loss, which is not loaded, the previous-year value is None and no variance test is made;
the report says so rather than guessing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model import Model

VARIANCE_LIMIT = 0.25


@dataclass
class Ratio:
    id: str
    name: str
    formula: str
    unit: str                      # "x" or "%"
    cur: float | None
    prev: float | None
    components: dict = field(default_factory=dict)   # label -> (current, previous) in rupees
    note: str = ""
    explanation: str = ""
    explanation_source: str = ""   # "AI draft" | "Required from management" | ""

    @property
    def variance(self) -> float | None:
        if self.cur is None or self.prev is None or self.prev == 0:
            return None
        return (self.cur - self.prev) / abs(self.prev)

    @property
    def flagged(self) -> bool:
        v = self.variance
        return v is not None and abs(v) > VARIANCE_LIMIT


def _div(a, b):
    return None if b in (0, None) or a is None else a / b


def _avg(c, p):
    return (c + p) / 2


def compute_ratios(m: Model) -> list[Ratio]:
    cur, prev, pl = m.figures["cur"], m.figures["prev"], m.figures["pl"]
    debt = lambda f: f["ltb"] + f["stb"]  # noqa: E731
    wc = lambda f: f["ca"] - f["cl"]      # noqa: E731
    out: list[Ratio] = []

    out.append(Ratio("current_ratio", "Current ratio", "Current assets / current liabilities", "x",
                     _div(cur["ca"], cur["cl"]), _div(prev["ca"], prev["cl"]),
                     {"Current assets": (cur["ca"], prev["ca"]), "Current liabilities": (cur["cl"], prev["cl"])}))
    out.append(Ratio("debt_equity", "Debt-equity ratio", "Total borrowings / shareholders' equity", "x",
                     _div(debt(cur), cur["equity"]), _div(debt(prev), prev["equity"]),
                     {"Total borrowings": (debt(cur), debt(prev)), "Shareholders' equity": (cur["equity"], prev["equity"])},
                     "Current maturities of long-term debt cannot be separated in Tally, so borrowings may be understated."))
    service = pl["fin"] + pl["lt_repaid"]
    earnings = pl["pbt"] + pl["dep"] + pl["fin"]       # ICAI Annexure B: net profit BEFORE tax + non-cash charges + interest
    out.append(Ratio("dscr", "Debt service coverage ratio",
                     "(Profit before tax + depreciation + finance costs) / (finance costs + principal repaid)", "x",
                     _div(earnings, service), None,
                     {"Earnings available for debt service": (earnings, None),
                      "Debt service (interest + principal repaid)": (service, None)}))
    out.append(Ratio("roe", "Return on equity", "Profit after tax / average shareholders' equity", "%",
                     _div(pl["pat"], _avg(cur["equity"], prev["equity"])), None,
                     {"Profit after tax": (pl["pat"], None),
                      "Average shareholders' equity": (_avg(cur["equity"], prev["equity"]), None)}))
    out.append(Ratio("inventory_turnover", "Inventory turnover ratio",
                     "Cost of goods sold / average inventory", "x",
                     _div(pl["cogs"], _avg(cur["inv"], prev["inv"])), None,
                     {"Cost of goods sold (materials consumed + changes in stock)": (pl["cogs"], None),
                      "Average inventory": (_avg(cur["inv"], prev["inv"]), None)},
                     "Direct manufacturing expenses (job work, power, wages) are excluded from cost of goods sold."))
    out.append(Ratio("tr_turnover", "Trade receivables turnover ratio",
                     "Net credit sales / average trade receivables", "x",
                     _div(pl["revenue"], _avg(cur["tr"], prev["tr"])), None,
                     {"Net credit sales (all revenue assumed on credit)": (pl["revenue"], None),
                      "Average trade receivables": (_avg(cur["tr"], prev["tr"]), None)},
                     "All revenue is assumed to be on credit; cash sales are not separable in Tally."))
    out.append(Ratio("tp_turnover", "Trade payables turnover ratio",
                     "Net credit purchases / average trade payables", "x",
                     _div(pl["purchases"], _avg(cur["tp"], prev["tp"])), None,
                     {"Net credit purchases": (pl["purchases"], None),
                      "Average trade payables": (_avg(cur["tp"], prev["tp"]), None)}))
    out.append(Ratio("net_capital_turnover", "Net capital turnover ratio", "Net sales / average working capital", "x",
                     _div(pl["revenue"], _avg(wc(cur), wc(prev))), None,
                     {"Net sales": (pl["revenue"], None),
                      "Average working capital (current assets - current liabilities)": (_avg(wc(cur), wc(prev)), None)}))
    out.append(Ratio("net_profit", "Net profit ratio", "Profit after tax / net sales", "%",
                     _div(pl["pat"], pl["revenue"]), None,
                     {"Profit after tax": (pl["pat"], None), "Net sales": (pl["revenue"], None)}))
    ebit = pl["pbt"] + pl["fin"]
    ce = lambda f: f["equity"] - f["intang"] + debt(f) + f["dtl"]  # noqa: E731
    out.append(Ratio("roce", "Return on capital employed",
                     "EBIT / (tangible net worth + total debt + deferred tax liability)", "%",
                     _div(ebit, ce(cur)), None,
                     {"EBIT (profit before tax + finance costs)": (ebit, None),
                      "Capital employed": (ce(cur), ce(prev))}))
    inv_cur, inv_prev = cur["investments"], prev["investments"]
    out.append(Ratio("roi", "Return on investment", "Income from investments / average investments", "%",
                     None, None, {"Investments": (inv_cur, inv_prev)},
                     "Not applicable: the company holds no investments (a bank deposit is shown as a bank balance)."
                     if not (inv_cur or inv_prev) else "Income from investments is not separately identified in Tally."))
    return out


def fmt_value(r: Ratio, v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"{v * 100:.2f}%" if r.unit == "%" else f"{v:.2f}x"


def fmt_variance(v: float | None) -> str:
    if v is None:
        return "n/a"
    s = f"{abs(v) * 100:.1f}%"
    return f"({s})" if v < 0 else s
