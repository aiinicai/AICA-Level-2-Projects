"""
Summary / Pivot Module — Screen 3 backend. Schema-free.

No hard-coded field names (no 'billedAmount', no 'division'). Instead,
this module inspects whatever columns exist in the compiled DataFrame and
classifies each as numeric or categorical/text, so the GUI can offer the
user a dropdown of "group by" and "measure" columns built from whatever
is actually present — including the Source Division column added during
compilation.
"""

import pandas as pd


def classify_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """
    Returns (numeric_columns, categorical_columns) based on the actual
    dtypes pandas inferred during compilation — not any predefined list.
    """
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in df.columns if c not in numeric_cols]
    return numeric_cols, categorical_cols


def group_summary(df: pd.DataFrame, group_by_col: str, measure_cols: list[str] | None = None) -> pd.DataFrame:
    """
    Generic group-by summary: groups by any chosen categorical column and
    aggregates (sum, for now) any chosen numeric columns, plus a row count.
    This replaces the old fixed 'division_summary' / 'tariff_summary'
    functions — the caller picks which column to group by and which
    numeric columns to total.
    """
    if df.empty or group_by_col not in df.columns:
        return pd.DataFrame()

    numeric_cols, _ = classify_columns(df)
    if measure_cols is None:
        measure_cols = numeric_cols
    else:
        measure_cols = [c for c in measure_cols if c in numeric_cols]

    agg_dict = {c: "sum" for c in measure_cols}
    g = df.groupby(group_by_col, dropna=False).agg(**{
        "Row Count": (group_by_col, "count"),
        **{c: (c, "sum") for c in measure_cols},
    }).reset_index()

    return g.sort_values(group_by_col).reset_index(drop=True)


def cross_tab_matrix(df: pd.DataFrame, row_col: str, col_col: str, measure_col: str, agg: str = "sum") -> dict:
    """
    Generic two-dimensional cross-tab (e.g. Division x any other chosen
    categorical column), with a chosen numeric measure column and
    aggregation ('sum' or 'count'). No hard-coded 'division'/'tariffCategory'
    — row_col, col_col, and measure_col are all caller-chosen from whatever
    columns actually exist.
    """
    if df.empty or row_col not in df.columns or col_col not in df.columns or row_col == col_col:
        return {"rows": [], "columns": [], "values": {}, "rowTotals": {}, "colTotals": {}, "grandTotal": 0}

    if agg == "count":
        pivot = pd.pivot_table(df, index=row_col, columns=col_col, values=measure_col,
                                aggfunc="count", fill_value=0)
    else:
        pivot = pd.pivot_table(df, index=row_col, columns=col_col, values=measure_col,
                                aggfunc="sum", fill_value=0)

    rows = list(pivot.index.astype(str))
    columns = list(pivot.columns.astype(str))
    values = {str(r): {str(c): float(pivot.loc[r, c]) for c in pivot.columns} for r in pivot.index}
    row_totals = {str(r): float(pivot.loc[r].sum()) for r in pivot.index}
    col_totals = {str(c): float(pivot[c].sum()) for c in pivot.columns}
    grand_total = float(pivot.values.sum())

    return {
        "rows": rows, "columns": columns, "values": values,
        "rowTotals": row_totals, "colTotals": col_totals, "grandTotal": grand_total,
    }


def overall_totals(df: pd.DataFrame, measure_cols: list[str] | None = None) -> dict:
    """Simple top-line totals for whatever numeric columns are chosen (or all numeric columns)."""
    if df.empty:
        return {"totalRows": 0, "totals": {}}

    numeric_cols, _ = classify_columns(df)
    if measure_cols is None:
        measure_cols = numeric_cols
    else:
        measure_cols = [c for c in measure_cols if c in numeric_cols]

    totals = {c: float(df[c].sum()) for c in measure_cols}
    return {"totalRows": int(len(df)), "totals": totals}
