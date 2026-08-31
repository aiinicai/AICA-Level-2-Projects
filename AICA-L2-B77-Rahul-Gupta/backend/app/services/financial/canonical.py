"""Canonical financial schema and label → metric mapping."""
from __future__ import annotations

import re

PNL_METRICS = [
    "revenue", "other_income", "material_cost", "employee_cost",
    "other_operating_expenses", "ebitda", "depreciation", "ebit",
    "finance_cost", "pbt", "tax", "pat",
]

BS_METRICS = [
    "share_capital", "reserves", "net_worth", "fixed_assets", "investments",
    "inventory", "receivables", "cash", "other_current_assets", "total_assets",
    "long_term_borrowings", "short_term_borrowings", "trade_payables",
    "other_liabilities", "total_liabilities",
]

CF_METRICS = ["cfo", "cfi", "cff", "capex", "opening_cash", "closing_cash"]

ALL_METRICS = PNL_METRICS + BS_METRICS + CF_METRICS

STATEMENT_OF: dict[str, str] = (
    {m: "pnl" for m in PNL_METRICS}
    | {m: "balance_sheet" for m in BS_METRICS}
    | {m: "cash_flow" for m in CF_METRICS}
)

METRIC_LABELS: dict[str, str] = {
    "revenue": "Revenue from Operations",
    "other_income": "Other Income",
    "material_cost": "Cost of Materials Consumed",
    "employee_cost": "Employee Benefit Expenses",
    "other_operating_expenses": "Other Operating Expenses",
    "ebitda": "EBITDA",
    "depreciation": "Depreciation & Amortisation",
    "ebit": "EBIT",
    "finance_cost": "Finance Costs",
    "pbt": "Profit Before Tax",
    "tax": "Tax Expense",
    "pat": "Profit After Tax",
    "share_capital": "Share Capital",
    "reserves": "Reserves & Surplus",
    "net_worth": "Net Worth",
    "fixed_assets": "Fixed Assets (Net Block)",
    "investments": "Investments",
    "inventory": "Inventories",
    "receivables": "Trade Receivables",
    "cash": "Cash & Cash Equivalents",
    "other_current_assets": "Other Current Assets",
    "total_assets": "Total Assets",
    "long_term_borrowings": "Long-term Borrowings",
    "short_term_borrowings": "Short-term Borrowings",
    "trade_payables": "Trade Payables",
    "other_liabilities": "Other Liabilities & Provisions",
    "total_liabilities": "Total Liabilities",
    "cfo": "Cash Flow from Operations",
    "cfi": "Cash Flow from Investing",
    "cff": "Cash Flow from Financing",
    "capex": "Capital Expenditure",
    "opening_cash": "Opening Cash Balance",
    "closing_cash": "Closing Cash Balance",
}

# Schedule III enumerates almost every line ("(a) Share capital", "IX. Profit
# before tax", "(iii) Capital work-in-progress"). Stripping the enumerator first
# is what lets the patterns below use ^ anchors, which is the only way to tell a
# statement line ("Sales") from a note sub-line that merely contains the same
# word ("Sales promotion expenses").
_ENUM_PREFIX = re.compile(
    r"^\s*(?:\((?:[a-z]|[ivxlcdm]{1,6}|\d{1,3})\)|(?:[a-z]|[ivxlcdm]{1,6}|\d{1,3})[.)])\s+",
    re.I)

# The 2021 Schedule III amendment mandates a ratio table in the notes. Its rows
# ("Inventory turnover ratio", "Trade payables turnover ratio") carry small
# numbers and would otherwise be mapped as revenue/inventory/payables figures.
_RATIO_LINE = re.compile(r"\bratio\b")

# A row whose entire label is "TOTAL" (optionally "Total assets"/"Total equity and
# liabilities" written bare). Only consulted on a balance-sheet page.
_BARE_TOTAL = re.compile(r"total(?:\s+(?:assets|equity\s+and\s+liabilities))?")

# ordered patterns — first match wins; keep more specific patterns first
_LABEL_PATTERNS: list[tuple[str, str]] = [
    # ---------------------------- profit & loss ----------------------------
    (r"revenue\s+from\s+operations?|operating\s+revenue"
     r"|^(?:gross\s+|net\s+|total\s+)?sales\b"
     r"(?!\s*(?:tax|promotion|incentive|return|discount|commission|and\s+marketing))"
     r"|\bnet\s+sales\b|^(?:gross\s+|net\s+)?turnover\b|^revenue$", "revenue"),
    (r"other\s+income", "other_income"),
    # COGS = materials consumed + purchases of stock-in-trade + change in stock.
    # "Changes in inventories…" is a Part II *expense*, not the balance-sheet
    # stock, so it must be claimed here before the `inventory` pattern sees it.
    (r"cost\s+of\s+(?:materials?|goods|sales)|material\s+cost|raw\s+material"
     r"|purchases?\s+of\s+(?:stock|traded\s+goods)"
     r"|changes?\s+in\s+inventor(?:y|ies)", "material_cost"),
    (r"employee\s+(?:benefit|cost)|staff\s+cost|salaries|personnel", "employee_cost"),
    (r"other\s+(?:operating\s+)?expenses?|administrative|selling\s+and\s+distribution",
     "other_operating_expenses"),
    (r"\bebitda\b", "ebitda"),
    (r"depreciation|amorti[sz]ation", "depreciation"),
    (r"\bebit\b(?!da)", "ebit"),
    # "Interest on term loans" is an AS-16 finance-cost component. It must be
    # claimed here, or the `term loans?` alternative in long_term_borrowings
    # writes a P&L expense into a balance-sheet debt stock.
    (r"finance\s+costs?|interest\s+expense|borrowing\s+costs?"
     r"|interest\s+on\s+(?:term\s+loans?|working\s+capital|borrowings?|debentures?"
     r"|cash\s+credit|loans?|bank\s+overdraft|deposits?)", "finance_cost"),
    (r"profit\s+before\s+tax|\bpbt\b", "pbt"),
    (r"tax\s+expense|current\s+tax|total\s+tax|^tax$", "tax"),
    (r"profit\s+after\s+tax|\bpat\b|profit\s+for\s+the\s+(?:year|period)|net\s+profit", "pat"),

    # ------------------------ cash flow section totals ---------------------
    # The reported AS-3 / Ind AS 7 totals. The wording between "net cash" and the
    # activity varies wildly ("from", "used in", "generated from", "from /
    # (used in)"), so allow a short gap rather than enumerating variants, but
    # always require the "activities" noun — without it, detail lines such as
    # "Net cash used in purchase of investments" match the section total.
    # The `before` lookahead rejects the pre-total subtotals ("Net cash from
    # operating activities BEFORE extraordinary items"), which sit ABOVE the
    # real total and would win under first-match-wins. "Cash generated from
    # operations", the PRE-TAX subtotal above "Income taxes paid", never matches.
    (r"^(?![^.]*\bbefore\b)(?:net\s+cash\b.{0,40}?operating\s+activit"
     r"|cash\s+flows?\s+(?:from|used\s+in|generated\s+from|to).{0,25}?operating\s+activit)"
     r"|\bcfo\b", "cfo"),
    (r"^(?![^.]*\bbefore\b)(?:net\s+cash\b.{0,40}?invest(?:ing|ment)\s+activit"
     r"|cash\s+flows?\s+(?:from|used\s+in|generated\s+from|to).{0,25}?invest(?:ing|ment)\s+activit)"
     r"|\bcfi\b", "cfi"),
    (r"^(?![^.]*\bbefore\b)(?:net\s+cash\b.{0,40}?financing\s+activit"
     r"|cash\s+flows?\s+(?:from|used\s+in|generated\s+from|to).{0,25}?financing\s+activit)"
     r"|\bcff\b", "cff"),

    # capex must precede fixed_assets: an *acquisition* of PPE is a cash-flow
    # outflow, not the net block. The leading lookahead keeps disposals out.
    (r"\bcapex\b|capital\s+expenditure|^capital\s+advances?"
     r"|^(?!.*\b(?:sale|sold|disposal|disposals|proceeds|maturity|redemption)\b)"
     r".*\b(?:purchase[sd]?|acquisition|acquired|additions?|payments?|expenditure|advances?)\b"
     r".*\b(?:propert(?:y|ies)|plant\s+and\s+equipment|ppe|fixed\s+assets?"
     r"|(?:in)?tangible\s+assets?|capital\s+work.in.progress|cwip|capital\s+goods"
     r"|capital\s+assets?|land\s+and\s+building)\b", "capex"),

    # opening/closing balances must precede the generic "cash" pattern below,
    # which would otherwise swallow "Cash and cash equivalents at the beginning
    # of the year". Both require the word "cash": a bare "Closing balance" is a
    # reserves / gross-block / provisions roll-forward, not the cash bridge.
    (r"^opening\s+(?:balance\s+of\s+)?cash|cash.{0,40}?\bat\s+the\s+beginning"
     r"|cash.{0,40}?\bas\s+at\s+the\s+beginning"
     r"|cash.{0,40}?\b(?:opening\s+balance|beginning\s+of\s+the\s+(?:year|period))",
     "opening_cash"),
    (r"^closing\s+(?:balance\s+of\s+)?cash"
     r"|cash.{0,40}?\bat\s+(?:the\s+)?(?:year|period)?[\s-]*end"
     r"|cash.{0,40}?\bclosing\s+balance", "closing_cash"),

    # ---------------------------- balance sheet ----------------------------
    (r"share\s+capital|equity\s+share", "share_capital"),
    (r"reserves|other\s+equity|surplus", "reserves"),
    # The Division II grand total "Total equity and liabilities" IS total assets
    # by the accounting identity. It must precede net_worth, whose `total equity`
    # alternative would otherwise book the whole balance sheet as shareholders'
    # funds — and it must NOT go to total_liabilities, which excludes equity.
    (r"^total\s+assets|total\s+equity\s*(?:and|&)\s*liabilit", "total_assets"),
    (r"net\s*worth|total\s+equity(?!\s*(?:and|&)\s*liabilit)"
     r"|shareholders?.{0,3}\s*funds?", "net_worth"),
    (r"^(?!.*\b(?:purchase[sd]?|acquisition|acquired|additions?|sale|sold|disposal"
     r"|proceeds|payments?)\b)"
     r".*(?:fixed\s+assets|propert(?:y|ies),?\s*plant|net\s+block"
     r"|\b(?:in)?tangible\s+assets|capital\s+work.in.progress|\bcwip\b)", "fixed_assets"),
    (r"^investments?$|non.current\s+investments?|current\s+investments?", "investments"),
    (r"inventor(?:y|ies)|stock.in.trade", "inventory"),
    (r"trade\s+receivables?|sundry\s+debtors|accounts?\s+receivable", "receivables"),
    # AS-3 / Ind AS 7 exclude "bank balances other than cash and cash
    # equivalents" (margin money, >3-month deposits) from cash.
    (r"^(?!.*\bother\s+than\b)(?!other\s+bank)"
     r".*(?:cash\s+(?:and|&)\s+(?:cash\s+equivalents?|bank)|cash\s+equivalents?"
     r"|cash\s+in\s+hand|balances?\s+with\s+banks?)", "cash"),
    (r"other\s+current\s+assets|short.term\s+loans\s+and\s+advances", "other_current_assets"),
    # `term loans?` is anchored: unanchored it swallowed "Interest on term loans"
    # (a P&L expense) and "Long-term loans and advances" (a non-current ASSET).
    (r"long.term\s+borrowings?|non.current\s+borrowings?|long.term\s+debt"
     r"|\bterm\s+loans?\s+from\b|^(?:secured\s+|unsecured\s+)?term\s+loans?\b",
     "long_term_borrowings"),
    (r"short.term\s+borrowings?|current\s+borrowings?"
     r"|^working\s+capital\s+(?:loan|borrowing|facilit)|^cash\s+credit",
     "short_term_borrowings"),
    # The Schedule III MSME split is the only amount-bearing payables disclosure
    # on most balance sheets; the parent "Trade payables" row is often blank.
    (r"trade\s+payables?|sundry\s+creditors|accounts?\s+payable"
     r"|(?:total\s+outstanding\s+)?dues\s+(?:of|to)\s+(?:micro|creditors)", "trade_payables"),
    # `provisions` is anchored so "Long-term provisions" cannot land in a bucket
    # that compute_period_ratios treats as wholly current.
    (r"other\s+current\s+liabilit|^other\s+liabilit"
     r"|short.term\s+provisions?|current\s+provisions?|^provisions?$", "other_liabilities"),
    (r"^total\s+liabilit", "total_liabilities"),
]


# Cash-flow *movement* lines. These name the same nouns as balance-sheet metrics
# ("...in cash and cash equivalents", "Proceeds from long-term borrowings") but
# state the change over the year, not the closing balance, so mapping them to a
# balance metric silently substitutes a delta for a stock figure. Applied only
# when the resolved metric is a balance-sheet stock: the same verbs are perfectly
# legitimate on P&L and cash-flow metrics ("Changes in inventories" is COGS).
_FLOW_LINE = re.compile(
    r"^(?:adjustments?\s+for\s+)?\(?(?:net\s+)?(?:increase|decrease)\b"
    r"|^adjustments?\s+for\b"
    r"|^changes?\s+in\b"
    r"|^(?:net\s+)?(?:proceeds|repayments?|repaid|receipts?)\b"
    r"|^(?:proceeds|payments?|receipts?|dividends?|interest)\s+"
    r"(?:from|for|to|towards|paid|received)\b"
    r"|^repayment\b|^redemption\s+of\b|^issue\s+of\b|^buy.?back\s+of\b"
    r"|^availment\s+of\b|^drawdown\s+of\b|^current\s+maturit"
    r"|\b(?:availed|raised|repaid|drawn)(?:\s+during\s+the\s+(?:year|period))?\s*$"
)

_BS_METRIC_SET = frozenset(BS_METRICS)


def map_label_to_metric(label: str, statement_type: str | None = None) -> str | None:
    """Map a raw statement label to a canonical metric name, or None.

    `statement_type` is the detected type of the page the label came from. It
    gates one direction only: a balance-sheet STOCK metric may never be sourced
    from a cash-flow page, because every borrowings/cash noun on that page names
    a movement. The reverse gate would be wrong — the AS-3 reconciliation block
    legitimately yields pbt, depreciation, finance_cost and capex.
    """
    t = re.sub(r"\s+", " ", label.strip().lower())
    prev = None
    while prev != t:  # "(a) (i) Term loans" carries more than one enumerator
        prev = t
        t = _ENUM_PREFIX.sub("", t, count=1).strip()
    if not t or _RATIO_LINE.search(t):
        return None
    # Schedule III Division I prints the balance-sheet totals as a bare "TOTAL"
    # on both sides, with no noun to match on. Both sides are equal by
    # construction, so on a balance-sheet page that row IS total assets. Without
    # it the BS_EQUATION check has no left-hand side and silently never runs.
    if statement_type == "balance_sheet" and _BARE_TOTAL.fullmatch(t):
        return "total_assets"
    for pattern, metric in _LABEL_PATTERNS:
        if re.search(pattern, t):
            if metric in _BS_METRIC_SET:
                if _FLOW_LINE.search(t):
                    return None
                if statement_type == "cash_flow":
                    return None
            return metric
    return None


# Metrics that Schedule III splits across several lines of the SAME table, so the
# canonical figure is the sum of its components rather than the first line seen.
# Scope matters more than the set: the notes restate every face figure, so the sum
# must be confined to the one page that first yields the metric (see
# pipeline._resolve_items) — summing document-wide doubles every one of these.
ADDITIVE_METRICS: frozenset[str] = frozenset({
    "material_cost",      # materials consumed + purchases of stock + change in stock
    "trade_payables",     # MSME dues + non-MSME dues
    "other_liabilities",  # other current liabilities + short-term provisions
    "fixed_assets",       # tangible + intangible + capital work-in-progress
})

# When the statement prints the parent/total row WITH a value, that row is the
# answer and its components must not be added on top of it. Only metrics whose
# components are a genuine sub-hierarchy need an entry; sibling sums (e.g.
# other_liabilities) have none, because there is no parent row to prefer.
ADDITIVE_PARENT: dict[str, str] = {
    "trade_payables": r"^trade\s+payables?$|^sundry\s+creditors$|^accounts?\s+payable",
    "fixed_assets": r"^fixed\s+assets|^net\s+block",
}


def normalise_metric_sign(metric: str, value: float | None) -> float | None:
    """Sign-normalise metrics that never legitimately reverse.

    Capex is printed as a bracketed outflow "(63.00)" on the cash flow statement
    but seeded and hand-entered as a positive magnitude, so the same figure
    reached analytics with one sign and the DCF with another. Only capex is
    listed: `tax` must stay signed (a deferred-tax credit is genuinely negative
    and PAT_CHECK depends on it), and cfi/cff are directional by definition.
    """
    if value is None:
        return None
    return abs(value) if metric in _MAGNITUDE_METRICS else value


_MAGNITUDE_METRICS: frozenset[str] = frozenset({"capex"})


STATEMENT_KEYWORDS = {
    "balance_sheet": ["balance sheet", "statement of assets and liabilities", "equity and liabilities"],
    "profit_and_loss": ["profit and loss", "profit & loss", "statement of income", "income statement", "revenue from operations"],
    "cash_flow": ["cash flow", "cash-flow", "statement of cash flows"],
    "notes": ["notes to accounts", "notes forming part", "significant accounting policies"],
}


def detect_statement_type(page_text: str) -> tuple[str, int]:
    """Score page text and return (statement_type, score)."""
    t = page_text.lower()
    best, best_score = "other", 0
    for stype, kws in STATEMENT_KEYWORDS.items():
        score = sum(3 for kw in kws if kw in t)
        # secondary signals
        if stype == "profit_and_loss":
            score += sum(1 for kw in ["total revenue", "employee benefit", "finance costs", "tax expense"] if kw in t)
        if stype == "balance_sheet":
            score += sum(1 for kw in ["share capital", "trade receivables", "total assets", "borrowings"] if kw in t)
        if stype == "cash_flow":
            score += sum(1 for kw in ["operating activities", "investing activities", "financing activities"] if kw in t)
        if score > best_score:
            best, best_score = stype, score
    return best, best_score
