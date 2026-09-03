"""
Schedule III (Division I) classification engine.

Maps a client trial balance to the presentation heads prescribed by
Schedule III to the Companies Act, 2013 (Division I - companies whose
financial statements are prepared in accordance with the Companies
(Accounting Standards) Rules).

The mapping is deterministic and rule-driven.  Where a ledger cannot be
mapped with confidence it is returned as UNMAPPED for the auditor to
resolve -- the engine never guesses a presentation head silently, because
the classification drives the face of the financial statements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

# --------------------------------------------------------------------------
# Schedule III, Division I - presentation structure
# --------------------------------------------------------------------------

BALANCE_SHEET_STRUCTURE: dict[str, dict[str, list[str]]] = {
    "EQUITY AND LIABILITIES": {
        "Shareholders' funds": [
            "Share capital",
            "Reserves and surplus",
            "Money received against share warrants",
        ],
        "Share application money pending allotment": [
            "Share application money pending allotment",
        ],
        "Non-current liabilities": [
            "Long-term borrowings",
            "Deferred tax liabilities (net)",
            "Other long-term liabilities",
            "Long-term provisions",
        ],
        "Current liabilities": [
            "Short-term borrowings",
            "Trade payables",
            "Other current liabilities",
            "Short-term provisions",
        ],
    },
    "ASSETS": {
        "Non-current assets": [
            "Property, plant and equipment",
            "Capital work-in-progress",
            "Intangible assets",
            "Intangible assets under development",
            "Non-current investments",
            "Deferred tax assets (net)",
            "Long-term loans and advances",
            "Other non-current assets",
        ],
        "Current assets": [
            "Current investments",
            "Inventories",
            "Trade receivables",
            "Cash and cash equivalents",
            "Short-term loans and advances",
            "Other current assets",
        ],
    },
}

PROFIT_AND_LOSS_STRUCTURE: dict[str, list[str]] = {
    "Income": [
        "Revenue from operations",
        "Other income",
    ],
    "Expenses": [
        "Cost of materials consumed",
        "Purchases of stock-in-trade",
        "Changes in inventories of finished goods, WIP and stock-in-trade",
        "Employee benefits expense",
        "Finance costs",
        "Depreciation and amortisation expense",
        "Other expenses",
    ],
    "Tax expense": [
        "Current tax",
        "Deferred tax",
    ],
}

# Every valid Schedule III head, flattened.
VALID_HEADS: set[str] = set()
for _group in BALANCE_SHEET_STRUCTURE.values():
    for _heads in _group.values():
        VALID_HEADS.update(_heads)
for _heads in PROFIT_AND_LOSS_STRUCTURE.values():
    VALID_HEADS.update(_heads)

UNMAPPED = "UNMAPPED"

# Heads that sit on the balance sheet (as opposed to the P&L).
BALANCE_SHEET_HEADS: set[str] = set()
for _group in BALANCE_SHEET_STRUCTURE.values():
    for _heads in _group.values():
        BALANCE_SHEET_HEADS.update(_heads)

# Heads whose natural balance is credit (liabilities, equity, income).
CREDIT_NATURE_HEADS: set[str] = set()
for _heads in BALANCE_SHEET_STRUCTURE["EQUITY AND LIABILITIES"].values():
    CREDIT_NATURE_HEADS.update(_heads)
CREDIT_NATURE_HEADS.update(PROFIT_AND_LOSS_STRUCTURE["Income"])


# --------------------------------------------------------------------------
# Account-code driven mapping
# --------------------------------------------------------------------------
# A firm's chart of accounts is the most reliable signal available, so the
# code range is tested first.  Keyword rules are a fallback for ledgers that
# sit outside the firm's numbering convention.

@dataclass(frozen=True)
class CodeRule:
    low: int
    high: int
    head: str


CODE_RULES: tuple[CodeRule, ...] = (
    CodeRule(1000, 1099, "Share capital"),
    CodeRule(1100, 1199, "Reserves and surplus"),
    CodeRule(1200, 1249, "Long-term borrowings"),
    CodeRule(1250, 1269, "Deferred tax liabilities (net)"),
    CodeRule(1270, 1289, "Other long-term liabilities"),
    CodeRule(1290, 1299, "Long-term provisions"),
    CodeRule(1300, 1329, "Short-term borrowings"),
    CodeRule(1330, 1359, "Trade payables"),
    CodeRule(1360, 1389, "Other current liabilities"),
    CodeRule(1390, 1399, "Short-term provisions"),
    CodeRule(2000, 2049, "Property, plant and equipment"),
    CodeRule(2050, 2059, "Capital work-in-progress"),
    CodeRule(2060, 2079, "Intangible assets"),
    CodeRule(2080, 2089, "Intangible assets under development"),
    CodeRule(2090, 2109, "Non-current investments"),
    CodeRule(2110, 2119, "Deferred tax assets (net)"),
    CodeRule(2120, 2139, "Long-term loans and advances"),
    CodeRule(2140, 2159, "Other non-current assets"),
    CodeRule(2200, 2219, "Current investments"),
    CodeRule(2220, 2249, "Inventories"),
    CodeRule(2250, 2279, "Trade receivables"),
    CodeRule(2280, 2299, "Cash and cash equivalents"),
    CodeRule(2300, 2329, "Short-term loans and advances"),
    CodeRule(2330, 2399, "Other current assets"),
    CodeRule(3000, 3099, "Revenue from operations"),
    CodeRule(3100, 3199, "Other income"),
    CodeRule(4000, 4099, "Cost of materials consumed"),
    CodeRule(4100, 4149, "Purchases of stock-in-trade"),
    CodeRule(4150, 4199, "Changes in inventories of finished goods, WIP and stock-in-trade"),
    CodeRule(4200, 4299, "Employee benefits expense"),
    CodeRule(4300, 4349, "Finance costs"),
    CodeRule(4350, 4399, "Depreciation and amortisation expense"),
    CodeRule(4400, 4899, "Other expenses"),
    CodeRule(4900, 4949, "Current tax"),
    CodeRule(4950, 4999, "Deferred tax"),
)

# Ordered most-specific first: the first phrase found wins.
KEYWORD_RULES: tuple[tuple[str, str], ...] = (
    ("equity share capital", "Share capital"),
    ("preference share capital", "Share capital"),
    ("share capital", "Share capital"),
    ("securities premium", "Reserves and surplus"),
    ("retained earnings", "Reserves and surplus"),
    ("general reserve", "Reserves and surplus"),
    ("surplus in statement", "Reserves and surplus"),
    ("capital work-in-progress", "Capital work-in-progress"),
    ("capital work in progress", "Capital work-in-progress"),
    ("deferred tax liab", "Deferred tax liabilities (net)"),
    ("deferred tax asset", "Deferred tax assets (net)"),
    ("deferred tax", "Deferred tax"),
    ("term loan", "Long-term borrowings"),
    ("debenture", "Long-term borrowings"),
    ("cash credit", "Short-term borrowings"),
    ("working capital loan", "Short-term borrowings"),
    ("overdraft", "Short-term borrowings"),
    ("trade payable", "Trade payables"),
    ("sundry creditor", "Trade payables"),
    ("creditors for goods", "Trade payables"),
    ("statutory dues", "Other current liabilities"),
    ("provision for tax", "Short-term provisions"),
    ("provision for gratuity", "Long-term provisions"),
    ("provision for", "Short-term provisions"),
    ("plant and machinery", "Property, plant and equipment"),
    ("furniture", "Property, plant and equipment"),
    ("accumulated depreciation", "Property, plant and equipment"),
    ("building", "Property, plant and equipment"),
    ("freehold land", "Property, plant and equipment"),
    ("vehicle", "Property, plant and equipment"),
    ("computer", "Property, plant and equipment"),
    ("goodwill", "Intangible assets"),
    ("software", "Intangible assets"),
    ("trade receivable", "Trade receivables"),
    ("sundry debtor", "Trade receivables"),
    ("inventor", "Inventories"),
    ("raw material", "Inventories"),
    ("finished goods", "Inventories"),
    ("work-in-progress", "Inventories"),
    ("stores and spares", "Inventories"),
    ("cash in hand", "Cash and cash equivalents"),
    ("bank balance", "Cash and cash equivalents"),
    ("current account", "Cash and cash equivalents"),
    ("fixed deposit", "Cash and cash equivalents"),
    ("capital advance", "Other non-current assets"),
    ("advance to supplier", "Short-term loans and advances"),
    ("prepaid", "Other current assets"),
    ("gst input", "Other current assets"),
    ("sale of product", "Revenue from operations"),
    ("sale of service", "Revenue from operations"),
    ("revenue from", "Revenue from operations"),
    ("interest income", "Other income"),
    ("other income", "Other income"),
    ("cost of materials", "Cost of materials consumed"),
    ("purchase of stock", "Purchases of stock-in-trade"),
    ("changes in inventor", "Changes in inventories of finished goods, WIP and stock-in-trade"),
    ("salaries", "Employee benefits expense"),
    ("wages", "Employee benefits expense"),
    ("staff welfare", "Employee benefits expense"),
    ("contribution to provident", "Employee benefits expense"),
    ("gratuity expense", "Employee benefits expense"),
    ("interest expense", "Finance costs"),
    ("interest on", "Finance costs"),
    ("bank charges", "Finance costs"),
    ("depreciation", "Depreciation and amortisation expense"),
    ("amortisation", "Depreciation and amortisation expense"),
    ("current tax", "Current tax"),
    ("income tax expense", "Current tax"),
    ("power and fuel", "Other expenses"),
    ("rent", "Other expenses"),
    ("legal and professional", "Other expenses"),
    ("payment to auditor", "Other expenses"),
    ("travel", "Other expenses"),
    ("repairs", "Other expenses"),
    ("insurance", "Other expenses"),
    ("csr", "Other expenses"),
    ("miscellaneous expense", "Other expenses"),
)


@dataclass
class Classification:
    """The result of mapping one ledger to Schedule III."""

    account_code: str
    account_name: str
    head: str
    basis: str          # "account_code" | "keyword" | "unmapped"
    confidence: float   # 0.0 - 1.0
    matched_on: str = ""

    @property
    def is_mapped(self) -> bool:
        return self.head != UNMAPPED

    @property
    def needs_review(self) -> bool:
        """Anything below full confidence goes in front of the auditor."""
        return self.confidence < 0.95


def classify_account(account_code: str | int, account_name: str) -> Classification:
    """Map a single ledger to its Schedule III presentation head.

    The account code is authoritative where it falls inside the firm's
    numbering convention.  Otherwise the ledger name is tested against the
    keyword rules, and the result is flagged for auditor review.
    """
    code_str = str(account_code).strip()
    name = (account_name or "").strip()
    name_lower = name.lower()

    # 1. Account code
    try:
        code_int = int(float(code_str))
    except (TypeError, ValueError):
        code_int = None

    if code_int is not None:
        for rule in CODE_RULES:
            if rule.low <= code_int <= rule.high:
                return Classification(
                    account_code=code_str,
                    account_name=name,
                    head=rule.head,
                    basis="account_code",
                    confidence=1.0,
                    matched_on=f"{rule.low}-{rule.high}",
                )

    # 2. Ledger name
    for phrase, head in KEYWORD_RULES:
        if phrase in name_lower:
            return Classification(
                account_code=code_str,
                account_name=name,
                head=head,
                basis="keyword",
                confidence=0.75,
                matched_on=phrase,
            )

    # 3. Unresolved - the auditor decides.
    return Classification(
        account_code=code_str,
        account_name=name,
        head=UNMAPPED,
        basis="unmapped",
        confidence=0.0,
    )


def classify_many(rows: Iterable[tuple[str | int, str]]) -> list[Classification]:
    return [classify_account(code, name) for code, name in rows]


def is_balance_sheet_head(head: str) -> bool:
    return head in BALANCE_SHEET_HEADS


def natural_balance(head: str) -> str:
    """'Cr' for liabilities, equity and income; 'Dr' otherwise."""
    return "Cr" if head in CREDIT_NATURE_HEADS else "Dr"


@dataclass
class MappingSummary:
    total: int = 0
    mapped: int = 0
    by_code: int = 0
    by_keyword: int = 0
    unmapped: list[Classification] = field(default_factory=list)
    review: list[Classification] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        return 0.0 if self.total == 0 else round(self.mapped / self.total, 4)


def summarise(classifications: list[Classification]) -> MappingSummary:
    s = MappingSummary(total=len(classifications))
    for c in classifications:
        if c.is_mapped:
            s.mapped += 1
            if c.basis == "account_code":
                s.by_code += 1
            else:
                s.by_keyword += 1
                s.review.append(c)
        else:
            s.unmapped.append(c)
            s.review.append(c)
    return s
