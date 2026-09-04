"""
Query Builder Module — Screen 4 backend. Schema-free.

Filters operate on whatever column names actually exist in the compiled
DataFrame — there is no predefined field list. The GUI populates its
field dropdown directly from df.columns at runtime.
"""

from dataclasses import dataclass

import pandas as pd

VALID_OPERATORS = {
    "equals", "not_equals", "greater_than", "less_than", "between",
    "contains", "starts_with", "in",
    "date_equals", "date_before", "date_after", "date_between",
}

DATE_KEYWORDS = {"date", "dt", "time", "month", "release", "billed_on", "created"}


@dataclass
class FilterRow:
    field: str
    operator: str
    value: str
    secondary_value: str | None = None


def detect_column_type(series: pd.Series, col_name: str = "") -> str:
    """
    Returns 'date', 'numeric', or 'text' based on series dtype, column name, and content.
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # Check if column name suggests a date
    col_lower = str(col_name).lower()
    if any(kw in col_lower for kw in DATE_KEYWORDS):
        # Test if sample values can be parsed as dates
        non_nulls = series.dropna().head(20)
        if not non_nulls.empty:
            try:
                parsed = pd.to_datetime(non_nulls, errors="coerce")
                if parsed.notna().sum() > len(non_nulls) * 0.5:
                    return "date"
            except Exception:
                pass

    return "text"


def get_operators_for_type(col_type: str) -> list[tuple[str, str]]:
    """Returns (key, user_friendly_label) list based on column type."""
    if col_type == "date":
        return [
            ("date_equals", "on date"),
            ("date_before", "before date"),
            ("date_after", "after date"),
            ("date_between", "between dates"),
            ("in", "in selected dates/values"),
            ("not_equals", "not equals"),
        ]
    elif col_type == "numeric":
        return [
            ("equals", "equals (=)"),
            ("not_equals", "not equals (≠)"),
            ("greater_than", "greater than (>)"),
            ("less_than", "less than (<)"),
            ("between", "between"),
            ("in", "in list / selected"),
        ]
    else:
        return [
            ("equals", "equals"),
            ("not_equals", "not equals"),
            ("contains", "contains"),
            ("starts_with", "starts with"),
            ("in", "in selected list"),
        ]


def _apply_single_filter(df: pd.DataFrame, f: FilterRow) -> pd.Series:
    if f.field not in df.columns:
        raise ValueError(f"Unknown column: {f.field}")
    if f.operator not in VALID_OPERATORS:
        raise ValueError(f"Unknown operator: {f.operator}")
    if f.value is None or str(f.value).strip() == "":
        return pd.Series(True, index=df.index)

    col = df[f.field]
    col_type = detect_column_type(col, f.field)

    # Date handling
    if f.operator.startswith("date_") or (col_type == "date" and f.operator in ("equals", "greater_than", "less_than", "between")):
        dt_col = pd.to_datetime(col, errors="coerce")
        try:
            val_dt = pd.to_datetime(f.value, errors="coerce")
        except Exception:
            val_dt = pd.NaT

        if f.operator in ("date_equals", "equals"):
            if pd.notna(val_dt):
                return dt_col.dt.date == val_dt.date()
            return col.astype(str).str.lower() == str(f.value).lower()

        if f.operator in ("date_before", "less_than"):
            return dt_col < val_dt

        if f.operator in ("date_after", "greater_than"):
            return dt_col > val_dt

        if f.operator in ("date_between", "between"):
            sec_dt = pd.to_datetime(f.secondary_value, errors="coerce") if f.secondary_value else val_dt
            return (dt_col >= val_dt) & (dt_col <= sec_dt)

    if f.operator == "equals":
        if col_type == "numeric":
            try:
                return col == float(f.value)
            except ValueError:
                pass
        return col.astype(str).str.lower() == str(f.value).lower()

    if f.operator == "not_equals":
        if col_type == "numeric":
            try:
                return col != float(f.value)
            except ValueError:
                pass
        return col.astype(str).str.lower() != str(f.value).lower()

    if f.operator == "greater_than":
        return pd.to_numeric(col, errors="coerce") > float(f.value)

    if f.operator == "less_than":
        return pd.to_numeric(col, errors="coerce") < float(f.value)

    if f.operator == "between":
        lo = float(f.value)
        hi = float(f.secondary_value) if f.secondary_value not in (None, "") else lo
        numeric_col = pd.to_numeric(col, errors="coerce")
        return (numeric_col >= lo) & (numeric_col <= hi)

    if f.operator == "contains":
        return col.astype(str).str.lower().str.contains(str(f.value).lower(), na=False)

    if f.operator == "starts_with":
        return col.astype(str).str.lower().str.startswith(str(f.value).lower(), na=False)

    if f.operator == "in":
        allowed = [s.strip().lower() for s in str(f.value).split(",") if s.strip()]
        return col.astype(str).str.lower().isin(allowed)

    raise ValueError(f"Unhandled operator: {f.operator}")  # pragma: no cover


def evaluate_filters(df: pd.DataFrame, filters: list[FilterRow]) -> pd.DataFrame:
    """Apply all filter rows with AND logic and return the filtered subset."""
    if df.empty or not filters:
        return df.copy()

    mask = pd.Series(True, index=df.index)
    for f in filters:
        mask &= _apply_single_filter(df, f)

    return df[mask].copy()
