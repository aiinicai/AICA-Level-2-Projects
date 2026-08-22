"""Raw -> canonical financial statement normalization — Module 1.

Takes the flat FinancialStatementRaw records produced by loaders.py and
pivots them into one FinancialStatement per period, with unit
consistency enforced. This is the single place unit conversion happens;
analysis/*.py modules only ever consume FinancialStatement, never raw
records, so a unit bug here cannot silently propagate per-metric.
"""

from __future__ import annotations

import logging

from app.core.enums import UnitOfMeasure
from app.core.models import FinancialStatement, FinancialStatementRaw, SourceMetadata

logger = logging.getLogger(__name__)


# Conversion factors to the canonical unit (INR crore).
_TO_CRORE: dict[UnitOfMeasure, float] = {
    UnitOfMeasure.INR_CRORE: 1.0,
    UnitOfMeasure.INR_LAKH: 0.01,
    UnitOfMeasure.INR_MILLION: 0.1,
    UnitOfMeasure.INR_BILLION: 100.0,
    UnitOfMeasure.INR_ABSOLUTE: 1e-7,
}

# Maps a raw line_item label -> the FinancialStatement field it fills.
# Fields not in this map (ratios, per-share figures the source already
# derived, etc.) are intentionally left unmapped rather than guessed.
_FIELD_MAP: dict[str, str] = {
    "Sales": "sales",
    "Raw Material Cost": "raw_material_cost",
    "Employee Cost": "employee_cost",
    "Other Income": "other_income",
    "Depreciation": "depreciation",
    "Interest": "interest",
    "Profit before tax": "profit_before_tax",
    "Tax": "tax",
    "Net profit": "net_profit",
    "Dividend Amount": "dividend_amount",
    "Equity Share Capital": "equity_share_capital",
    "Reserves": "reserves",
    "Borrowings": "borrowings",
    "Other Liabilities": "other_liabilities",
    "Total Liabilities": "total_liabilities",
    "Net Block": "net_block",
    "Capital Work in Progress": "capital_work_in_progress",
    "Investments": "investments",
    "Other Assets": "other_assets",
    "Total Assets": "total_assets",
    "Receivables": "receivables",
    "Inventory": "inventory",
    "Cash & Bank": "cash_and_bank",
    "No. of Equity Shares": "num_equity_shares",
    "Face value": "face_value",
    "Cash from Operating Activity": "cash_from_operations",
    "Cash from Investing Activity": "cash_from_investing",
    "Cash from Financing Activity": "cash_from_financing",
    "Net Cash Flow": "net_cash_flow",
    "Price": "price",
}

# Fields that are monetary (crore-scale) and therefore need the unit
# conversion applied. Share counts, face value, and per-share figures
# are NOT monetary in this sense and are passed through unconverted.
_MONETARY_FIELDS = {
    "sales", "raw_material_cost", "employee_cost", "other_income",
    "depreciation", "interest", "profit_before_tax", "tax", "net_profit",
    "dividend_amount", "equity_share_capital", "reserves", "borrowings",
    "other_liabilities", "total_liabilities", "net_block",
    "capital_work_in_progress", "investments", "other_assets",
    "total_assets", "receivables", "inventory", "cash_and_bank",
    "cash_from_operations", "cash_from_investing", "cash_from_financing",
    "net_cash_flow",
}


def build_canonical_statements(
    raw_records: list[FinancialStatementRaw],
    *,
    statement_types: tuple[str, ...] = (
        "profit_and_loss", "balance_sheet", "cash_flow", "market_price",
    ),
) -> list[FinancialStatement]:
    """Pivot raw line items into one FinancialStatement per period.

    Args:
        raw_records: Output of a loaders.py function.
        statement_types: Which statement_type values to include. Defaults
            to the three annual statements; pass ("quarterly",) instead
            for quarterly analysis.

    Returns:
        One FinancialStatement per distinct period found, sorted by
        period_end_date ascending. Every field not present in the source
        data is left as None (never fabricated or zero-filled).
    """
    by_period: dict[str, list[FinancialStatementRaw]] = {}
    for rec in raw_records:
        if rec.statement_type not in statement_types:
            continue
        by_period.setdefault(rec.period, []).append(rec)

    statements: list[FinancialStatement] = []
    for period, recs in by_period.items():
        company = recs[0].company
        period_end_date = recs[0].period_end_date
        source_unit = recs[0].source.unit
        conversion_factor = _TO_CRORE.get(source_unit)

        if conversion_factor is None:
            logger.warning(
                "No conversion factor known for unit %s (period %s); "
                "monetary fields for this period will be left as None "
                "rather than guessed.",
                source_unit,
                period,
            )

        field_values: dict[str, float | None] = {}
        notes: list[str] = []

        for rec in recs:
            field_name = _FIELD_MAP.get(rec.line_item)
            if field_name is None:
                continue  # unmapped label (e.g. "Change in Inventory") — not in canonical schema yet
            if rec.value is None:
                field_values[field_name] = None
                continue
            if field_name in _MONETARY_FIELDS and conversion_factor is not None:
                field_values[field_name] = rec.value * conversion_factor
            else:
                field_values[field_name] = rec.value

        # operating_profit is not a direct Screener "Data Sheet" row for
        # annual P&L (it's derivable: Sales - Raw Material - Employee -
        # other opex); leave unset here rather than approximate it from a
        # partial expense breakdown — fundamentals.py will compute it
        # explicitly with full input visibility instead (Module 2).
        if source_unit != UnitOfMeasure.INR_CRORE:
            notes.append(
                f"Source unit assumed as {source_unit.value}; converted to INR crore "
                f"using factor {conversion_factor}. Verify against original filing if in doubt."
            )

        statements.append(
            FinancialStatement(
                company=company,
                period=period,
                period_end_date=period_end_date,
                unit=UnitOfMeasure.INR_CRORE,
                source=SourceMetadata(
                    company=company,
                    source=recs[0].source.source,
                    source_type=recs[0].source.source_type,
                    source_date=period_end_date,
                    reporting_period=period,
                    unit=UnitOfMeasure.INR_CRORE,
                    confidence=recs[0].source.confidence,
                ),
                data_quality_notes=notes,
                **field_values,
            )
        )

    statements.sort(key=lambda s: s.period_end_date or s.period)
    logger.info("Built %d canonical financial statements", len(statements))
    return statements
