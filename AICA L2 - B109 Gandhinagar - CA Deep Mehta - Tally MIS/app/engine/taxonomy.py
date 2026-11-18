"""Canonical account classes and ledger classification (ported from taxonomy.ts and classify.ts)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClassDef:
    code: str
    label: str
    statement: str  # 'PL' | 'BS'
    side: str       # asset | liability | equity | income | expense | other
    section: str
    normal: str     # debit | credit
    current: bool | None = None


def _c(code, label, st, side, section, normal, current=None):
    return ClassDef(code, label, st, side, section, normal, current)


CLASSES: list[ClassDef] = [
    _c("revenue_operating", "Revenue from operations", "PL", "income", "revenue", "credit"),
    _c("revenue_contra", "Sales returns, discounts & reductions", "PL", "income", "revenue", "debit"),
    _c("income_other", "Other income", "PL", "income", "other_income", "credit"),
    _c("cogs_purchases", "Purchases (net of returns)", "PL", "expense", "cogs", "debit"),
    _c("cogs_direct", "Direct expenses", "PL", "expense", "cogs", "debit"),
    _c("opex_employee", "Employee costs", "PL", "expense", "opex", "debit"),
    _c("opex_rent", "Rent & lease", "PL", "expense", "opex", "debit"),
    _c("opex_freight", "Freight & distribution", "PL", "expense", "opex", "debit"),
    _c("opex_utilities", "Utilities & communication", "PL", "expense", "opex", "debit"),
    _c("opex_selling", "Selling & marketing", "PL", "expense", "opex", "debit"),
    _c("opex_admin", "Administrative expenses", "PL", "expense", "opex", "debit"),
    _c("opex_other", "Other operating expenses", "PL", "expense", "opex", "debit"),
    _c("depreciation", "Depreciation & amortisation", "PL", "expense", "da", "debit"),
    _c("finance_cost", "Finance costs", "PL", "expense", "finance", "debit"),
    _c("exceptional", "Exceptional items", "PL", "expense", "exceptional", "debit"),
    _c("tax_expense", "Income tax expense", "PL", "expense", "tax", "debit"),
    _c("equity_capital", "Share capital / partners’ capital", "BS", "equity", "equity", "credit"),
    _c("equity_reserves", "Reserves & surplus", "BS", "equity", "equity", "credit"),
    _c("pl_account", "Profit & Loss A/c (accumulated)", "BS", "equity", "equity", "credit"),
    _c("borrowing_long", "Long-term borrowings", "BS", "liability", "noncurrent_liabilities", "credit", False),
    _c("other_noncurrent_liability", "Other non-current liabilities", "BS", "liability", "noncurrent_liabilities", "credit", False),
    _c("borrowing_short", "Short-term borrowings", "BS", "liability", "current_liabilities", "credit", True),
    _c("trade_payable", "Trade payables", "BS", "liability", "current_liabilities", "credit", True),
    _c("tax_balance", "Duties & taxes (net)", "BS", "liability", "current_liabilities", "credit", True),
    _c("provision", "Provisions", "BS", "liability", "current_liabilities", "credit", True),
    _c("other_current_liability", "Other current liabilities", "BS", "liability", "current_liabilities", "credit", True),
    _c("fixed_asset", "Property, plant & equipment", "BS", "asset", "noncurrent_assets", "debit", False),
    _c("investment", "Investments", "BS", "asset", "noncurrent_assets", "debit", False),
    _c("other_noncurrent_asset", "Other non-current assets", "BS", "asset", "noncurrent_assets", "debit", False),
    _c("misc_expense_asset", "Misc. expenditure (not written off)", "BS", "asset", "noncurrent_assets", "debit", False),
    _c("inventory", "Inventories (stock ledgers)", "BS", "asset", "current_assets", "debit", True),
    _c("trade_receivable", "Trade receivables", "BS", "asset", "current_assets", "debit", True),
    _c("cash", "Cash in hand", "BS", "asset", "current_assets", "debit", True),
    _c("bank", "Bank balances", "BS", "asset", "current_assets", "debit", True),
    _c("loans_advances_asset", "Loans & advances (asset)", "BS", "asset", "current_assets", "debit", True),
    _c("deposits_asset", "Deposits (asset)", "BS", "asset", "current_assets", "debit", True),
    _c("other_current_asset", "Other current assets", "BS", "asset", "current_assets", "debit", True),
    _c("suspense", "Suspense / clearing", "BS", "other", "other", "debit"),
    _c("branch_division", "Branch / division balances", "BS", "other", "other", "debit"),
]
CLASS_BY_CODE = {c.code: c for c in CLASSES}
OPEX_CLASSES = [c.code for c in CLASSES if c.section == "opex"]

SECTION_LABELS = {
    "revenue": "Revenue from operations", "other_income": "Other income", "cogs": "Cost of goods sold",
    "opex": "Operating expenses", "da": "Depreciation & amortisation", "finance": "Finance costs",
    "exceptional": "Exceptional items", "tax": "Tax expense", "equity": "Equity",
    "noncurrent_liabilities": "Non-current liabilities", "current_liabilities": "Current liabilities",
    "noncurrent_assets": "Non-current assets", "current_assets": "Current assets", "other": "Other / suspense",
}

# --------------------------------------------------------------------------------------------- classification
RESERVED_MAP: dict[str, tuple[str, float, dict | None, str | None]] = {
    "Sundry Debtors": ("trade_receivable", 0.95, None, None),
    "Sundry Creditors": ("trade_payable", 0.95, None, None),
    "Bank Accounts": ("bank", 0.95, None, None),
    "Bank OD A/c": ("borrowing_short", 0.9, {"interestBearing": True}, None),
    "Bank OCC A/c": ("borrowing_short", 0.9, {"interestBearing": True}, None),
    "Cash-in-Hand": ("cash", 0.95, None, None),
    "Duties & Taxes": ("tax_balance", 0.9, None, None),
    "Provisions": ("provision", 0.85, None, None),
    "Stock-in-Hand": ("inventory", 0.9, None, None),
    "Deposits (Asset)": ("deposits_asset", 0.85, None, None),
    "Loans & Advances (Asset)": ("loans_advances_asset", 0.8, None, None),
    "Secured Loans": ("borrowing_long", 0.7, {"interestBearing": True}, "Tally does not record maturity; review whether any portion is current"),
    "Unsecured Loans": ("borrowing_long", 0.6, {"interestBearing": True}, "May include interest-free loans from related parties"),
    "Loans (Liability)": ("borrowing_long", 0.65, {"interestBearing": True}, None),
    "Reserves & Surplus": ("equity_reserves", 0.9, None, None),
    "Capital Account": ("equity_capital", 0.9, None, None),
    "Fixed Assets": ("fixed_asset", 0.9, None, None),
    "Investments": ("investment", 0.8, None, None),
    "Current Assets": ("other_current_asset", 0.6, None, None),
    "Current Liabilities": ("other_current_liability", 0.6, None, None),
    "Suspense A/c": ("suspense", 0.95, None, None),
    "Misc. Expenses (ASSET)": ("misc_expense_asset", 0.9, None, None),
    "Branch / Divisions": ("branch_division", 0.9, None, None),
    "Sales Accounts": ("revenue_operating", 0.9, None, None),
    "Purchase Accounts": ("cogs_purchases", 0.9, None, None),
    "Direct Expenses": ("cogs_direct", 0.85, None, None),
    "Direct Incomes": ("revenue_operating", 0.55, None, "Direct incomes are often operating, but may be other income"),
    "Indirect Incomes": ("income_other", 0.8, None, None),
    "Indirect Expenses": ("opex_other", 0.5, None, None),
}

# JavaScript's \b, \s and i-flag behave like Python's for these ASCII patterns.
NAME_RULES: list[tuple[re.Pattern, str, float, str]] = [(re.compile(p, re.I), code, conf, fam) for p, code, conf, fam in [
    (r"sales?\s*return|return\s*inward|credit\s*note", "revenue_contra", 0.85, "revenue"),
    (r"discount\s*(allowed|on\s*sales)|trade\s*discount|rebate|sales\s*discount", "revenue_contra", 0.75, "revenue"),
    (r"interest|finance\s*charge|loan\s*processing|bank\s*charge|bill\s*discounting|commitment\s*fee", "finance_cost", 0.75, "expense"),
    (r"depreciation|amorti[sz]ation", "depreciation", 0.9, "expense"),
    (r"income\s*tax|current\s*tax|deferred\s*tax|tax\s*expense|mat\s*credit", "tax_expense", 0.85, "expense"),
    (r"salar|wage|bonus|staff|employee|\bpf\b|provident|\besi\b|gratuity|incentive|stipend|leave\s*encash|welfare", "opex_employee", 0.8, "expense"),
    (r"\brent\b|lease|hire\s*charge", "opex_rent", 0.8, "expense"),
    (r"freight|cartage|transport|courier|carriage|delivery|forwarding|packing", "opex_freight", 0.7, "expense"),
    (r"electric|power|water|telephone|mobile|internet|broadband|utilit", "opex_utilities", 0.75, "expense"),
    (r"advertis|marketing|promotion|commission|brokerage|business\s*promotion|exhibition|discount\s*allowed", "opex_selling", 0.7, "expense"),
    (r"audit|legal|professional|consult|printing|stationery|office|insurance|repair|maintenance|travel|conveyance|rates\s*&?\s*taxes|software|subscription|fees", "opex_admin", 0.65, "expense"),
    (r"loss\s*on\s*sale|impairment|write[\s-]?off|bad\s*debt|exceptional|extraordinary", "exceptional", 0.55, "expense"),
    (r"interest\s*(received|income|on\s*fd)|dividend|rent\s*received|profit\s*on\s*sale|gain|misc(ellaneous)?\s*income", "income_other", 0.8, "income"),
]]
RELATED_PARTY = re.compile(r"director|partner|proprietor|drawings|\bhuf\b|relative|holding\s*co|subsidiary|sister\s*concern", re.I)
_PL_NAME = re.compile(r"^profit\s*&\s*loss\s*a/?c$", re.I)


@dataclass
class Suggestion:
    code: str | None
    confidence: float
    rationale: str
    attrs: dict | None = None


def suggest_for_ledger(name: str, ancestry: list[dict]) -> Suggestion:
    if _PL_NAME.match(name.strip()):
        return Suggestion("pl_account", 0.95, "Tally reserved Profit & Loss A/c ledger")
    reserved = next((g for g in ancestry if g["name"] in RESERVED_MAP), None)
    if reserved:
        code, conf, attrs, note = RESERVED_MAP[reserved["name"]]
        base = Suggestion(code, conf, f'Under Tally group "{reserved["name"]}"{" — " + note if note else ""}', attrs)
    elif ancestry:
        top, g = ancestry[-1], ancestry[0]
        if g["isRevenue"] == 1:
            if g["affectsGP"] == 1:
                code = "cogs_direct" if g["isDebit"] == 1 else "revenue_operating"
            else:
                code = "opex_other" if g["isDebit"] == 1 else "income_other"
            base = Suggestion(code, 0.45, f'Custom group "{g["name"]}" flagged as P&L in Tally (no reserved parent found)')
        else:
            base = Suggestion(None, 0, f'Group "{top["name"]}" is not a recognised Tally group; needs mapping')
    else:
        return Suggestion(None, 0, "Ledger has no group (master missing from import)")

    cls = CLASS_BY_CODE.get(base.code) if base.code else None
    if cls:
        family = "revenue" if cls.section == "revenue" else "income" if cls.side == "income" else "expense" if cls.side == "expense" else None
        if family:
            for rx, code, conf, fam in NAME_RULES:
                if (fam == family or fam == "any") and rx.search(name):
                    if base.code == "cogs_direct" and code in ("opex_employee", "opex_freight", "opex_utilities", "opex_rent"):
                        break
                    if code == base.code:
                        break
                    base = Suggestion(code, min(conf, base.confidence + 0.2),
                                      f'{base.rationale}; ledger name suggests "{CLASS_BY_CODE[code].label}"', base.attrs)
                    break
    if RELATED_PARTY.search(name):
        base.attrs = {**(base.attrs or {}), "relatedParty": True}
        base.rationale += "; name suggests a related party"
    return base


@dataclass
class ChartEntry:
    ledger_id: int
    name: str
    group_name: str | None
    primary_group: str | None
    code: str | None
    attrs: dict
    status: str      # verified | suggested | unclassified
    source: str
    confidence: float
    rationale: str
    opening_paise: int
    is_billwise: bool
    credit_days: int | None
    credit_limit_paise: int | None


@dataclass
class Chart:
    entries: dict[int, ChartEntry] = field(default_factory=dict)
    by_code: dict[str, list[ChartEntry]] = field(default_factory=dict)

    def ledgers_of(self, *codes: str) -> list[int]:
        return [e.ledger_id for c in codes for e in self.by_code.get(c, [])]


def build_chart(store, company_id: int) -> Chart:
    groups = store.rows("SELECT name, parent_name, is_revenue, affects_gross_profit, is_deemed_positive, primary_group "
                        "FROM ledger_groups WHERE company_id = ? ORDER BY id", [company_id])
    gmap = {g["name"]: g for g in groups}
    maps = store.rows("SELECT target_type, target_name, class_code, attrs_json, status, confidence, rationale "
                      "FROM classifications WHERE company_id = ?", [company_id])
    import json
    lmap = {m["target_name"]: m for m in maps if m["target_type"] == "ledger"}
    gm_map = {m["target_name"]: m for m in maps if m["target_type"] == "group"}
    ledgers = store.rows("SELECT id, name, group_name, opening_paise, is_billwise, credit_period_days, credit_limit_paise "
                         "FROM ledgers WHERE company_id = ? ORDER BY name", [company_id])
    chart = Chart()
    for l in ledgers:
        ancestry, cur, seen = [], l["group_name"], set()
        while cur and cur not in seen:
            seen.add(cur)
            g = gmap.get(cur)
            ancestry.append({"name": cur, "isRevenue": g["is_revenue"] if g else None,
                             "affectsGP": g["affects_gross_profit"] if g else None,
                             "isDebit": g["is_deemed_positive"] if g else None})
            cur = g["parent_name"] if g else None
        pg = None
        if l["group_name"]:
            g = gmap.get(l["group_name"])
            pg = (g["primary_group"] if g and g["primary_group"] else None) or l["group_name"]
        common = dict(ledger_id=l["id"], name=l["name"], group_name=l["group_name"], primary_group=pg,
                      opening_paise=l["opening_paise"], is_billwise=bool(l["is_billwise"]),
                      credit_days=l["credit_period_days"], credit_limit_paise=l["credit_limit_paise"])
        lm = lmap.get(l["name"])
        if lm:
            e = ChartEntry(**common, code=lm["class_code"], attrs=json.loads(lm["attrs_json"]),
                           status="verified" if lm["status"] == "verified" else "suggested", source="ledger",
                           confidence=lm["confidence"] if lm["confidence"] is not None else 1,
                           rationale=lm["rationale"] or "Mapped by user")
        else:
            gm = next((gm_map[a["name"]] for a in ancestry if a["name"] in gm_map), None)
            if gm:
                e = ChartEntry(**common, code=gm["class_code"], attrs=json.loads(gm["attrs_json"]),
                               status="verified" if gm["status"] == "verified" else "suggested", source="group",
                               confidence=gm["confidence"] if gm["confidence"] is not None else 1,
                               rationale=f'Group "{gm["target_name"]}" mapped to {gm["class_code"]}')
            else:
                s = suggest_for_ledger(l["name"], ancestry)
                e = ChartEntry(**common, code=s.code, attrs=s.attrs or {}, status="suggested" if s.code else "unclassified",
                               source="auto", confidence=s.confidence, rationale=s.rationale)
        chart.entries[l["id"]] = e
    for e in chart.entries.values():
        if e.code:
            chart.by_code.setdefault(e.code, []).append(e)
    return chart


def is_current(e: ChartEntry) -> bool | None:
    if e.attrs.get("current") is not None:
        return e.attrs["current"]
    return CLASS_BY_CODE[e.code].current if e.code and e.code in CLASS_BY_CODE else None
