"""
Builds the Schedule III face of the financial statements from a mapped
trial balance, and derives the figures the ratio engine needs.

Sign convention throughout: every amount is held debit-positive
internally, and presented positive on the face of the statements.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .formatting import inr

from .ingest import TrialBalance
from .schedule3 import (
    BALANCE_SHEET_STRUCTURE,
    PROFIT_AND_LOSS_STRUCTURE,
    UNMAPPED,
    Classification,
    classify_account,
    is_balance_sheet_head,
)


@dataclass
class MappedTrialBalance:
    financial_year: str
    df: pd.DataFrame                      # tb columns + head, basis, confidence
    classifications: list[Classification]

    def head_total(self, head: str) -> float:
        """Debit-positive net total of a Schedule III head."""
        rows = self.df[self.df["head"] == head]
        return round(float(rows["debit"].sum() - rows["credit"].sum()), 2)

    def presented(self, head: str) -> float:
        """The figure as it appears on the face of the statements (positive)."""
        return round(abs(self.head_total(head)), 2)

    def group_total(self, heads: list[str]) -> float:
        return round(sum(self.presented(h) for h in heads), 2)


def map_trial_balance(tb: TrialBalance) -> MappedTrialBalance:
    classifications = [
        classify_account(row.account_code, row.account_name)
        for row in tb.df.itertuples(index=False)
    ]
    df = tb.df.copy()
    df["head"] = [c.head for c in classifications]
    df["basis"] = [c.basis for c in classifications]
    df["confidence"] = [c.confidence for c in classifications]
    df["needs_review"] = [c.needs_review for c in classifications]
    return MappedTrialBalance(tb.financial_year, df, classifications)


# --------------------------------------------------------------------------
# Figures used by the ratio engine
# --------------------------------------------------------------------------

CURRENT_ASSET_HEADS = BALANCE_SHEET_STRUCTURE["ASSETS"]["Current assets"]
CURRENT_LIABILITY_HEADS = BALANCE_SHEET_STRUCTURE["EQUITY AND LIABILITIES"]["Current liabilities"]
NON_CURRENT_ASSET_HEADS = BALANCE_SHEET_STRUCTURE["ASSETS"]["Non-current assets"]
NON_CURRENT_LIABILITY_HEADS = BALANCE_SHEET_STRUCTURE["EQUITY AND LIABILITIES"]["Non-current liabilities"]
EQUITY_HEADS = BALANCE_SHEET_STRUCTURE["EQUITY AND LIABILITIES"]["Shareholders' funds"]


@dataclass
class Figures:
    """Everything the eleven ratios draw on, for one financial year."""

    financial_year: str

    # Balance sheet
    current_assets: float = 0.0
    current_liabilities: float = 0.0
    inventories: float = 0.0
    trade_receivables: float = 0.0
    trade_payables: float = 0.0
    shareholders_equity: float = 0.0
    long_term_borrowings: float = 0.0
    short_term_borrowings: float = 0.0
    deferred_tax_liability: float = 0.0
    non_current_investments: float = 0.0
    current_investments: float = 0.0
    total_assets: float = 0.0

    # Statement of profit and loss
    revenue_from_operations: float = 0.0
    other_income: float = 0.0
    cost_of_materials: float = 0.0
    purchases_stock_in_trade: float = 0.0
    changes_in_inventories: float = 0.0
    employee_benefits: float = 0.0
    finance_costs: float = 0.0
    depreciation: float = 0.0
    other_expenses: float = 0.0
    current_tax: float = 0.0
    deferred_tax: float = 0.0

    # Supplied by the client, not derivable from the trial balance
    principal_repayments: float = 0.0
    income_from_investments: float = 0.0
    credit_sales_ratio: float = 1.0      # proportion of revenue that is on credit
    credit_purchase_ratio: float = 1.0

    # ---- derived -------------------------------------------------------
    @property
    def total_debt(self) -> float:
        return round(self.long_term_borrowings + self.short_term_borrowings, 2)

    @property
    def total_income(self) -> float:
        return round(self.revenue_from_operations + self.other_income, 2)

    @property
    def cogs(self) -> float:
        """Cost of goods sold, per Schedule III expense heads."""
        return round(
            self.cost_of_materials
            + self.purchases_stock_in_trade
            + self.changes_in_inventories,
            2,
        )

    @property
    def total_expenses(self) -> float:
        return round(
            self.cogs
            + self.employee_benefits
            + self.finance_costs
            + self.depreciation
            + self.other_expenses,
            2,
        )

    @property
    def profit_before_tax(self) -> float:
        return round(self.total_income - self.total_expenses, 2)

    @property
    def profit_after_tax(self) -> float:
        return round(self.profit_before_tax - self.current_tax - self.deferred_tax, 2)

    @property
    def ebit(self) -> float:
        return round(self.profit_before_tax + self.finance_costs, 2)

    @property
    def earnings_for_debt_service(self) -> float:
        """PAT before depreciation, other non-cash items and interest."""
        return round(self.profit_after_tax + self.depreciation + self.finance_costs, 2)

    @property
    def debt_service(self) -> float:
        return round(self.finance_costs + self.principal_repayments, 2)

    @property
    def working_capital(self) -> float:
        return round(self.current_assets - self.current_liabilities, 2)

    @property
    def capital_employed(self) -> float:
        """Tangible net worth + total debt + deferred tax liability."""
        return round(
            self.shareholders_equity + self.total_debt + self.deferred_tax_liability, 2
        )

    @property
    def net_credit_sales(self) -> float:
        return round(self.revenue_from_operations * self.credit_sales_ratio, 2)

    @property
    def net_credit_purchases(self) -> float:
        base = self.cost_of_materials + self.purchases_stock_in_trade
        return round(base * self.credit_purchase_ratio, 2)

    @property
    def total_investments(self) -> float:
        return round(self.non_current_investments + self.current_investments, 2)


def derive_figures(
    mtb: MappedTrialBalance,
    *,
    principal_repayments: float = 0.0,
    income_from_investments: float | None = None,
    credit_sales_ratio: float = 1.0,
    credit_purchase_ratio: float = 1.0,
) -> Figures:
    p = mtb.presented
    f = Figures(
        financial_year=mtb.financial_year,
        current_assets=mtb.group_total(CURRENT_ASSET_HEADS),
        current_liabilities=mtb.group_total(CURRENT_LIABILITY_HEADS),
        inventories=p("Inventories"),
        trade_receivables=p("Trade receivables"),
        trade_payables=p("Trade payables"),
        shareholders_equity=mtb.group_total(EQUITY_HEADS),
        long_term_borrowings=p("Long-term borrowings"),
        short_term_borrowings=p("Short-term borrowings"),
        deferred_tax_liability=p("Deferred tax liabilities (net)"),
        non_current_investments=p("Non-current investments"),
        current_investments=p("Current investments"),
        revenue_from_operations=p("Revenue from operations"),
        other_income=p("Other income"),
        cost_of_materials=p("Cost of materials consumed"),
        purchases_stock_in_trade=p("Purchases of stock-in-trade"),
        employee_benefits=p("Employee benefits expense"),
        finance_costs=p("Finance costs"),
        depreciation=p("Depreciation and amortisation expense"),
        other_expenses=p("Other expenses"),
        current_tax=p("Current tax"),
        deferred_tax=p("Deferred tax"),
        principal_repayments=principal_repayments,
        credit_sales_ratio=credit_sales_ratio,
        credit_purchase_ratio=credit_purchase_ratio,
    )
    # Changes in inventories keeps its sign: a debit is an increase in cost.
    f.changes_in_inventories = mtb.head_total(
        "Changes in inventories of finished goods, WIP and stock-in-trade"
    )
    f.total_assets = round(
        mtb.group_total(NON_CURRENT_ASSET_HEADS) + f.current_assets, 2
    )
    f.income_from_investments = (
        f.other_income if income_from_investments is None else income_from_investments
    )
    return f


# --------------------------------------------------------------------------
# Face of the financial statements
# --------------------------------------------------------------------------

@dataclass
class StatementLine:
    label: str
    level: int              # 0 = section, 1 = group, 2 = line item
    current: float | None = None
    prior: float | None = None
    is_total: bool = False


@dataclass
class FinancialStatements:
    balance_sheet: list[StatementLine] = field(default_factory=list)
    profit_and_loss: list[StatementLine] = field(default_factory=list)
    balance_sheet_tallies: bool = False
    equity_liabilities_total: float = 0.0
    assets_total: float = 0.0
    profit_for_the_year: float = 0.0
    unmapped_value: float = 0.0
    difference: float = 0.0
    reconciliation: str = ""


def build_statements(
    current: MappedTrialBalance,
    prior: MappedTrialBalance | None = None,
    *,
    profit_for_the_year: float = 0.0,
    prior_profit: float | None = None,
) -> FinancialStatements:
    """Build the face of the balance sheet and the statement of profit and loss.

    The trial balance is pre-closing, so the profit for the year still sits
    in the revenue and expense ledgers.  It is transferred to reserves and
    surplus here, exactly as it would be on closing the books; without that
    transfer the balance sheet cannot tie.
    """
    fs = FinancialStatements(profit_for_the_year=round(profit_for_the_year, 2))

    def pair(head: str) -> tuple[float, float | None]:
        cur = current.presented(head)
        pri = prior.presented(head) if prior else None
        if head == "Reserves and surplus":
            cur = round(cur + profit_for_the_year, 2)
            if pri is not None and prior_profit is not None:
                pri = round(pri + prior_profit, 2)
        return cur, pri

    # ---- Balance sheet ------------------------------------------------
    side_totals: dict[str, float] = {}
    for section, groups in BALANCE_SHEET_STRUCTURE.items():
        fs.balance_sheet.append(StatementLine(section, 0))
        section_total = 0.0
        section_prior: float | None = 0.0 if prior else None
        for group, heads in groups.items():
            # 'Reserves and surplus' must appear whenever there is a profit to
            # carry, even where the client keeps no reserves ledger of its own.
            present = [
                h
                for h in heads
                if current.presented(h) != 0
                or (h == "Reserves and surplus" and profit_for_the_year != 0)
            ]
            if not present:
                continue
            fs.balance_sheet.append(StatementLine(group, 1))
            group_total = 0.0
            group_prior: float | None = 0.0 if prior else None
            for head in present:
                cur, pri = pair(head)
                fs.balance_sheet.append(StatementLine(head, 2, cur, pri))
                group_total += cur
                if group_prior is not None:
                    group_prior += pri or 0.0
            group_total = round(group_total, 2)
            # Totals carry a comparative too; a blank prior-year total column
            # reads as an unfinished statement.
            fs.balance_sheet.append(
                StatementLine(
                    f"Total {group.lower()}", 1, group_total,
                    None if group_prior is None else round(group_prior, 2), True,
                )
            )
            section_total += group_total
            if section_prior is not None and group_prior is not None:
                section_prior += group_prior
        fs.balance_sheet.append(
            StatementLine(
                f"TOTAL - {section}", 0, round(section_total, 2),
                None if section_prior is None else round(section_prior, 2), True,
            )
        )
        side_totals[section] = round(section_total, 2)

    fs.equity_liabilities_total = side_totals.get("EQUITY AND LIABILITIES", 0.0)
    fs.assets_total = side_totals.get("ASSETS", 0.0)

    # A balance sheet that does not tie is reported, never quietly balanced.
    fs.unmapped_value = unmapped_value(current)
    fs.difference = round(fs.assets_total - fs.equity_liabilities_total, 2)
    fs.balance_sheet_tallies = abs(fs.difference) <= 1.00
    if fs.balance_sheet_tallies:
        fs.reconciliation = "The balance sheet tallies."
    elif abs(abs(fs.difference) - fs.unmapped_value) <= 1.00:
        fs.reconciliation = (
            f"The balance sheet is out by Rs {inr(fs.difference)}, which is exactly the "
            f"Rs {inr(fs.unmapped_value)} sitting in ledgers the engine could not classify. "
            "Clear the unmapped queue and the statements will tie."
        )
    else:
        fs.reconciliation = (
            f"The balance sheet is out by Rs {inr(fs.difference)}. "
            f"Rs {inr(fs.unmapped_value)} is unclassified; the remaining "
            f"Rs {inr(abs(fs.difference) - fs.unmapped_value)} needs investigation."
        )

    # ---- Statement of profit and loss ---------------------------------
    for group, heads in PROFIT_AND_LOSS_STRUCTURE.items():
        present = [h for h in heads if current.presented(h) != 0]
        if not present:
            continue
        fs.profit_and_loss.append(StatementLine(group, 1))
        for head in present:
            cur, pri = pair(head)
            fs.profit_and_loss.append(StatementLine(head, 2, cur, pri))

    return fs


def unmapped_value(mtb: MappedTrialBalance) -> float:
    """Absolute rupee value sitting in ledgers the engine could not map."""
    rows = mtb.df[mtb.df["head"] == UNMAPPED]
    return round(float((rows["debit"] - rows["credit"]).abs().sum()), 2)
