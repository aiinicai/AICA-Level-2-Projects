from typing import Dict, List, Optional, Any
import re


ANALYSIS_ENGINE_VERSION = "1.4"


# =========================================================
# BASIC HELPERS
# =========================================================

def safe_divide(
    numerator: Optional[float],
    denominator: Optional[float],
) -> Optional[float]:

    if (
        numerator is None
        or denominator is None
        or denominator == 0
    ):
        return None

    return numerator / denominator


def round_value(
    value: Optional[float],
    digits: int = 2,
) -> Optional[float]:

    if value is None:
        return None

    try:
        return round(float(value), digits)
    except Exception:
        return None


def percentage(
    numerator: Optional[float],
    denominator: Optional[float],
) -> Optional[float]:

    value = safe_divide(
        numerator,
        denominator
    )

    if value is None:
        return None

    return round_value(
        value * 100
    )


def growth_rate(
    current: Optional[float],
    previous: Optional[float],
) -> Optional[float]:

    if (
        current is None
        or previous is None
        or previous == 0
    ):
        return None

    return round_value(
        (
            (
                current
                - previous
            )
            / abs(previous)
        )
        * 100
    )


def cagr(
    start_value: Optional[float],
    end_value: Optional[float],
    years: int,
) -> Optional[float]:

    if (
        start_value is None
        or end_value is None
        or start_value <= 0
        or end_value <= 0
        or years <= 0
    ):
        return None

    try:

        return round_value(
            (
                (
                    end_value
                    / start_value
                )
                ** (1 / years)
                - 1
            )
            * 100
        )

    except Exception:
        return None


def sum_available(
    *values
) -> Optional[float]:

    available = [
        value
        for value in values
        if value is not None
    ]

    if not available:
        return None

    return sum(available)


def clean_number(
    value: Any
) -> Optional[float]:

    if value is None:
        return None

    if isinstance(
        value,
        (int, float)
    ):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    negative = (
        text.startswith("(")
        and text.endswith(")")
    )

    text = (
        text
        .replace(",", "")
        .replace("(", "")
        .replace(")", "")
        .replace("%", "")
    )

    try:

        number = float(text)

        if negative:
            number = -number

        return number

    except Exception:
        return None


def normalize_text(
    value: Any
) -> str:

    if value is None:
        return ""

    text = (
        str(value)
        .lower()
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("&", " and ")
    )

    text = re.sub(
        r"[^a-z0-9%()/\-\s]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# NORMALIZED FINANCIAL HELPERS
# =========================================================

def get_field_value(
    period_data: Dict,
    field_name: str,
) -> Optional[float]:

    item = period_data.get(
        field_name
    )

    if not isinstance(
        item,
        dict
    ):
        return None

    return item.get("value")


def get_period_display(
    period_key: str,
    period_data: Dict,
) -> str:

    return (
        period_data
        .get("_period", {})
        .get(
            "display",
            period_key
        )
    )


def period_sort_value(
    period_key: str,
    period_data: Dict,
) -> str:

    return (
        period_data
        .get("_period", {})
        .get(
            "sort_key",
            period_key
        )
    )


def get_statement_period(
    bucket_data: Dict,
    statement: str,
    period_key: str,
) -> Dict:

    return (
        bucket_data
        .get(statement, {})
        .get(period_key, {})
    )


def collect_periods(
    bucket_data: Dict,
) -> List[Dict]:

    periods = {}

    for statement_name in [
        "income_statement",
        "balance_sheet",
        "cash_flow",
    ]:

        statement = bucket_data.get(
            statement_name,
            {}
        )

        for (
            period_key,
            period_data
        ) in statement.items():

            if period_key not in periods:

                periods[
                    period_key
                ] = {
                    "key":
                        period_key,

                    "display":
                        get_period_display(
                            period_key,
                            period_data
                        ),

                    "sort_key":
                        period_sort_value(
                            period_key,
                            period_data
                        ),
                }

    return sorted(
        periods.values(),
        key=lambda item:
            item.get(
                "sort_key",
                ""
            )
    )


# =========================================================
# PROJECTION SCHEDULE EXTRACTION
# =========================================================

def detect_fy_header(
    value: Any
) -> Optional[str]:

    text = normalize_text(value)

    match = re.search(
        r"fy\s*(20\d{2})\s*[-/]\s*(\d{2,4})",
        text,
    )

    if not match:
        return None

    start_year = int(
        match.group(1)
    )

    end_part = match.group(2)

    if len(end_part) == 2:

        end_year = (
            start_year // 100
        ) * 100 + int(
            end_part
        )

    else:
        end_year = int(
            end_part
        )

    return f"FY{end_year}"


def detect_schedule_columns(
    rows: List[Dict]
) -> Dict[int, str]:

    best_columns = {}

    for row in rows[:15]:

        values = row.get(
            "values",
            []
        )

        detected = {}

        for index, value in enumerate(
            values
        ):

            fy = detect_fy_header(
                value
            )

            if fy:
                detected[index] = fy

        if (
            len(detected)
            >
            len(best_columns)
        ):
            best_columns = detected

    return best_columns


def extract_values_from_matching_row(
    row: Dict,
    period_columns: Dict[int, str],
) -> Dict[str, float]:

    values = row.get(
        "values",
        []
    )

    result = {}

    for (
        column_index,
        fy
    ) in period_columns.items():

        if (
            column_index
            >= len(values)
        ):
            continue

        number = clean_number(
            values[
                column_index
            ]
        )

        if number is None:
            continue

        result[fy] = number

    return result


def get_schedule_row_values(
    generic_table: Dict,
    target_labels: List[str],
) -> Dict[str, float]:

    rows = generic_table.get(
        "rows",
        []
    )

    period_columns = (
        detect_schedule_columns(
            rows
        )
    )

    if not period_columns:
        return {}

    normalized_targets = [
        normalize_text(label)
        for label in target_labels
    ]

    # Exact match first.
    for target in normalized_targets:

        for row in rows:

            values = row.get(
                "values",
                []
            )

            for cell in values[:3]:

                label = normalize_text(
                    cell
                )

                if (
                    label
                    and label == target
                ):

                    result = (
                        extract_values_from_matching_row(
                            row,
                            period_columns
                        )
                    )

                    if result:
                        return result

    # Partial fallback.
    for target in normalized_targets:

        for row in rows:

            values = row.get(
                "values",
                []
            )

            for cell in values[:3]:

                label = normalize_text(
                    cell
                )

                if (
                    label
                    and target in label
                ):

                    result = (
                        extract_values_from_matching_row(
                            row,
                            period_columns
                        )
                    )

                    if result:
                        return result

    return {}


def extract_projection_schedule_metrics(
    extraction_result: Dict
) -> Dict[str, Dict]:

    schedule_metrics = {}

    for workbook in extraction_result.get(
        "files",
        []
    ):

        if (
            workbook.get(
                "document_category"
            )
            != "projections"
        ):
            continue

        for table in workbook.get(
            "generic_tables",
            []
        ):

            sheet_type = table.get(
                "sheet_type",
                ""
            )

            sheet_name = normalize_text(
                table.get(
                    "sheet_name",
                    ""
                )
            )

            if (
                sheet_type
                == "fixed_asset_schedule"
                or "fixed asset"
                in sheet_name
            ):

                capex_values = (
                    get_schedule_row_values(
                        table,
                        [
                            "Total cash capital expenditure (PPE and intangibles)",
                            "Total cash capital expenditure",
                            "Capital expenditure during the year",
                        ],
                    )
                )

                for (
                    fy,
                    value
                ) in capex_values.items():

                    schedule_metrics.setdefault(
                        fy,
                        {}
                    )

                    schedule_metrics[
                        fy
                    ][
                        "capex"
                    ] = round_value(
                        value
                    )

                    schedule_metrics[
                        fy
                    ][
                        "capex_source"
                    ] = table.get(
                        "sheet_name"
                    )

                    schedule_metrics[
                        fy
                    ][
                        "capex_basis"
                    ] = (
                        "Total cash capital expenditure "
                        "(PPE and intangibles)"
                    )

            if (
                sheet_type
                == "working_capital_schedule"
                or "working capital"
                in sheet_name
            ):

                wc_values = (
                    get_schedule_row_values(
                        table,
                        [
                            "Increase / (decrease) in net working capital",
                            "Increase in net working capital",
                            "Change in net working capital",
                        ],
                    )
                )

                for (
                    fy,
                    value
                ) in wc_values.items():

                    schedule_metrics.setdefault(
                        fy,
                        {}
                    )

                    schedule_metrics[
                        fy
                    ][
                        "change_working_capital"
                    ] = round_value(
                        value
                    )

                    schedule_metrics[
                        fy
                    ][
                        "working_capital_source"
                    ] = table.get(
                        "sheet_name"
                    )

                    schedule_metrics[
                        fy
                    ][
                        "working_capital_basis"
                    ] = (
                        "Increase / (decrease) "
                        "in net working capital"
                    )

    return schedule_metrics


# =========================================================
# CAPITAL STRUCTURE ENGINE
# =========================================================

def find_capital_structure_workbook(
    extraction_result: Dict
) -> Optional[Dict]:

    for workbook in extraction_result.get(
        "files",
        []
    ):

        if (
            workbook.get(
                "document_category"
            )
            == "capital_structure"
        ):
            return workbook

    return None


def find_generic_table(
    workbook: Dict,
    sheet_names: List[str],
) -> Optional[Dict]:

    normalized_targets = [
        normalize_text(name)
        for name in sheet_names
    ]

    for table in workbook.get(
        "generic_tables",
        []
    ):

        sheet_name = normalize_text(
            table.get(
                "sheet_name",
                ""
            )
        )

        if (
            sheet_name
            in normalized_targets
        ):
            return table

    return None


def find_row_by_label(
    table: Optional[Dict],
    labels: List[str],
) -> Optional[Dict]:

    if not table:
        return None

    normalized_labels = [
        normalize_text(label)
        for label in labels
    ]

    # Exact match first.
    for target in normalized_labels:

        for row in table.get(
            "rows",
            []
        ):

            values = row.get(
                "values",
                []
            )

            if not values:
                continue

            label = normalize_text(
                values[0]
            )

            if label == target:
                return row

    # Partial fallback.
    for target in normalized_labels:

        for row in table.get(
            "rows",
            []
        ):

            values = row.get(
                "values",
                []
            )

            if not values:
                continue

            label = normalize_text(
                values[0]
            )

            if (
                label
                and target in label
            ):
                return row

    return None


def row_number(
    row: Optional[Dict],
    index: int,
) -> Optional[float]:

    if not row:
        return None

    values = row.get(
        "values",
        []
    )

    if index >= len(values):
        return None

    return clean_number(
        values[index]
    )


def parse_instruments_outstanding(
    table: Optional[Dict],
) -> Dict:

    result = {
        "basic_equity_shares":
            None,

        "ccps_outstanding":
            None,

        "ccps_conversion_ratio":
            None,

        "equity_from_ccps":
            None,

        "warrants_outstanding":
            None,

        "equity_from_warrants":
            None,

        "esop_vested":
            None,

        "esop_unvested":
            None,

        "equity_from_esops":
            None,

        "fully_diluted_total":
            None,

        "instruments":
            [],
    }

    if not table:
        return result

    for row in table.get(
        "rows",
        []
    ):

        values = row.get(
            "values",
            []
        )

        if not values:
            continue

        label = normalize_text(
            values[0]
        )

        if not label:
            continue

        if (
            "equity shares"
            in label
            and
            "fully diluted"
            not in label
        ):

            outstanding = (
                clean_number(
                    values[1]
                )
                if len(values) > 1
                else None
            )

            equivalent = (
                clean_number(
                    values[3]
                )
                if len(values) > 3
                else None
            )

            if (
                outstanding is not None
                and equivalent is not None
            ):

                result[
                    "basic_equity_shares"
                ] = outstanding

                result[
                    "instruments"
                ].append({
                    "instrument":
                        str(
                            values[0]
                        ),

                    "outstanding":
                        outstanding,

                    "conversion_ratio":
                        (
                            clean_number(
                                values[2]
                            )
                            if len(values) > 2
                            else None
                        ),

                    "equity_equivalent":
                        equivalent,

                    "exercise_or_conversion_price":
                        (
                            clean_number(
                                values[4]
                            )
                            if len(values) > 4
                            else None
                        ),

                    "terms":
                        (
                            str(values[5])
                            if (
                                len(values) > 5
                                and values[5]
                                is not None
                            )
                            else None
                        ),
                })

        elif "ccps" in label:

            outstanding = (
                clean_number(
                    values[1]
                )
                if len(values) > 1
                else None
            )

            conversion_ratio = (
                clean_number(
                    values[2]
                )
                if len(values) > 2
                else None
            )

            equivalent = (
                clean_number(
                    values[3]
                )
                if len(values) > 3
                else None
            )

            result[
                "ccps_outstanding"
            ] = outstanding

            result[
                "ccps_conversion_ratio"
            ] = conversion_ratio

            result[
                "equity_from_ccps"
            ] = equivalent

            result[
                "instruments"
            ].append({
                "instrument":
                    str(values[0]),

                "outstanding":
                    outstanding,

                "conversion_ratio":
                    conversion_ratio,

                "equity_equivalent":
                    equivalent,

                "exercise_or_conversion_price":
                    (
                        clean_number(
                            values[4]
                        )
                        if len(values) > 4
                        else None
                    ),

                "terms":
                    (
                        str(values[5])
                        if (
                            len(values) > 5
                            and values[5]
                            is not None
                        )
                        else None
                    ),
            })

        elif "warrant" in label:

            outstanding = (
                clean_number(
                    values[1]
                )
                if len(values) > 1
                else None
            )

            equivalent = (
                clean_number(
                    values[3]
                )
                if len(values) > 3
                else None
            )

            result[
                "warrants_outstanding"
            ] = outstanding

            result[
                "equity_from_warrants"
            ] = equivalent

            result[
                "instruments"
            ].append({
                "instrument":
                    str(values[0]),

                "outstanding":
                    outstanding,

                "conversion_ratio":
                    (
                        clean_number(
                            values[2]
                        )
                        if len(values) > 2
                        else None
                    ),

                "equity_equivalent":
                    equivalent,

                "exercise_or_conversion_price":
                    (
                        clean_number(
                            values[4]
                        )
                        if len(values) > 4
                        else None
                    ),

                "terms":
                    (
                        str(values[5])
                        if (
                            len(values) > 5
                            and values[5]
                            is not None
                        )
                        else None
                    ),
            })

        elif (
            "employee stock options"
            in label
        ):

            outstanding = (
                clean_number(
                    values[1]
                )
                if len(values) > 1
                else None
            )

            equivalent = (
                clean_number(
                    values[3]
                )
                if len(values) > 3
                else None
            )

            if "unvested" in label:

                result[
                    "esop_unvested"
                ] = outstanding

            elif "vested" in label:

                result[
                    "esop_vested"
                ] = outstanding

            current_esop = (
                result.get(
                    "equity_from_esops"
                )
                or 0
            )

            result[
                "equity_from_esops"
            ] = (
                current_esop
                +
                (
                    equivalent
                    or 0
                )
            )

            result[
                "instruments"
            ].append({
                "instrument":
                    str(values[0]),

                "outstanding":
                    outstanding,

                "conversion_ratio":
                    (
                        clean_number(
                            values[2]
                        )
                        if len(values) > 2
                        else None
                    ),

                "equity_equivalent":
                    equivalent,

                "exercise_or_conversion_price":
                    (
                        clean_number(
                            values[4]
                        )
                        if len(values) > 4
                        else None
                    ),

                "terms":
                    (
                        str(values[5])
                        if (
                            len(values) > 5
                            and values[5]
                            is not None
                        )
                        else None
                    ),
            })

        elif (
            "total equity shares"
            in label
            and
            "fully diluted"
            in label
        ):

            result[
                "fully_diluted_total"
            ] = (
                clean_number(
                    values[3]
                )
                if len(values) > 3
                else None
            )

    return result


def parse_fully_diluted_table(
    table: Optional[Dict],
) -> Dict:

    result = {
        "basic_equity_shares":
            None,

        "equity_from_ccps":
            None,

        "equity_from_warrants":
            None,

        "equity_from_esops":
            None,

        "fully_diluted_total":
            None,

        "cash_receivable_warrants":
            None,

        "cash_receivable_esops":
            None,

        "total_cash_receivable":
            None,

        "holders":
            [],

        "categories":
            [],
    }

    if not table:
        return result

    total_row = find_row_by_label(
        table,
        ["Total"]
    )

    if total_row:

        result[
            "basic_equity_shares"
        ] = row_number(
            total_row,
            1
        )

        result[
            "equity_from_ccps"
        ] = row_number(
            total_row,
            3
        )

        result[
            "equity_from_warrants"
        ] = row_number(
            total_row,
            4
        )

        result[
            "equity_from_esops"
        ] = row_number(
            total_row,
            5
        )

        result[
            "fully_diluted_total"
        ] = row_number(
            total_row,
            6
        )

    warrant_cash_row = (
        find_row_by_label(
            table,
            [
                "Warrants: 1,50,000 x Rs. 135 balance payable",
                "Warrants",
            ],
        )
    )

    esop_cash_row = (
        find_row_by_label(
            table,
            [
                "ESOPs: 2,50,000 x Rs. 50 exercise price",
                "ESOPs",
            ],
        )
    )

    total_cash_row = (
        find_row_by_label(
            table,
            [
                "Total cash receivable on exercise"
            ],
        )
    )

    result[
        "cash_receivable_warrants"
    ] = row_number(
        warrant_cash_row,
        1
    )

    result[
        "cash_receivable_esops"
    ] = row_number(
        esop_cash_row,
        1
    )

    result[
        "total_cash_receivable"
    ] = row_number(
        total_cash_row,
        1
    )

    for row in table.get(
        "rows",
        []
    ):

        values = row.get(
            "values",
            []
        )

        if len(values) < 8:
            continue

        name = normalize_text(
            values[0]
        )

        if (
            not name
            or name
            in {
                "holder",
                "total",
            }
            or "check" in name
            or "summary" in name
        ):
            continue

        basic = clean_number(
            values[1]
        )

        basic_pct = clean_number(
            values[2]
        )

        ccps = clean_number(
            values[3]
        )

        warrants = clean_number(
            values[4]
        )

        esops = clean_number(
            values[5]
        )

        diluted = clean_number(
            values[6]
        )

        diluted_pct = clean_number(
            values[7]
        )

        if (
            diluted is None
            or diluted_pct is None
        ):
            continue

        result[
            "holders"
        ].append({
            "holder":
                str(
                    values[0]
                ),

            "basic_equity_shares":
                basic or 0,

            "basic_percentage":
                round_value(
                    (
                        basic_pct * 100
                        if (
                            basic_pct
                            is not None
                            and basic_pct <= 1
                        )
                        else basic_pct
                    )
                ),

            "equity_from_ccps":
                ccps or 0,

            "equity_from_warrants":
                warrants or 0,

            "equity_from_esops":
                esops or 0,

            "fully_diluted_shares":
                diluted,

            "fully_diluted_percentage":
                round_value(
                    (
                        diluted_pct
                        * 100
                        if diluted_pct <= 1
                        else diluted_pct
                    )
                ),
        })

    # Summary by category.
    summary_found = False

    for row in table.get(
        "rows",
        []
    ):

        values = row.get(
            "values",
            []
        )

        if not values:
            continue

        label = normalize_text(
            values[0]
        )

        if (
            "summary by category"
            in label
        ):
            summary_found = True
            continue

        if not summary_found:
            continue

        if len(values) < 3:
            continue

        shares = clean_number(
            values[1]
        )

        pct = clean_number(
            values[2]
        )

        if (
            shares is None
            or pct is None
        ):
            continue

        result[
            "categories"
        ].append({
            "category":
                str(
                    values[0]
                ),

            "fully_diluted_shares":
                shares,

            "fully_diluted_percentage":
                round_value(
                    (
                        pct * 100
                        if pct <= 1
                        else pct
                    )
                ),
        })

    return result


def analyze_capital_structure(
    extraction_result: Dict
) -> Dict:

    workbook = (
        find_capital_structure_workbook(
            extraction_result
        )
    )

    if not workbook:

        return {
            "available":
                False,

            "status":
                "NOT_AVAILABLE",

            "message":
                "No capital structure workbook was found.",
        }

    instruments_table = (
        find_generic_table(
            workbook,
            [
                "Instruments Outstanding"
            ],
        )
    )

    diluted_table = (
        find_generic_table(
            workbook,
            [
                "Fully Diluted Table"
            ],
        )
    )

    instruments = (
        parse_instruments_outstanding(
            instruments_table
        )
    )

    diluted = (
        parse_fully_diluted_table(
            diluted_table
        )
    )

    # Prefer fully diluted table as primary
    # because it gives a holder-wise reconciliation.
    basic = (
        diluted.get(
            "basic_equity_shares"
        )
        if diluted.get(
            "basic_equity_shares"
        )
        is not None
        else instruments.get(
            "basic_equity_shares"
        )
    )

    ccps_equity = (
        diluted.get(
            "equity_from_ccps"
        )
        if diluted.get(
            "equity_from_ccps"
        )
        is not None
        else instruments.get(
            "equity_from_ccps"
        )
    )

    warrant_equity = (
        diluted.get(
            "equity_from_warrants"
        )
        if diluted.get(
            "equity_from_warrants"
        )
        is not None
        else instruments.get(
            "equity_from_warrants"
        )
    )

    esop_equity = (
        diluted.get(
            "equity_from_esops"
        )
        if diluted.get(
            "equity_from_esops"
        )
        is not None
        else instruments.get(
            "equity_from_esops"
        )
    )

    fully_diluted = (
        diluted.get(
            "fully_diluted_total"
        )
        if diluted.get(
            "fully_diluted_total"
        )
        is not None
        else instruments.get(
            "fully_diluted_total"
        )
    )

    computed_total = None

    if (
        basic is not None
        and ccps_equity is not None
        and warrant_equity is not None
        and esop_equity is not None
    ):

        computed_total = (
            basic
            +
            ccps_equity
            +
            warrant_equity
            +
            esop_equity
        )

    checks = []

    if (
        fully_diluted is not None
        and computed_total is not None
    ):

        difference = (
            computed_total
            -
            fully_diluted
        )

        checks.append({
            "check":
                (
                    "Basic equity + CCPS conversion + "
                    "warrants + ESOPs = Fully Diluted Shares"
                ),

            "difference":
                round_value(
                    difference
                ),

            "status":
                (
                    "OK"
                    if abs(
                        difference
                    ) < 0.01
                    else "REVIEW"
                ),
        })

    instrument_total = (
        instruments.get(
            "fully_diluted_total"
        )
    )

    diluted_table_total = (
        diluted.get(
            "fully_diluted_total"
        )
    )

    if (
        instrument_total
        is not None
        and diluted_table_total
        is not None
    ):

        difference = (
            instrument_total
            -
            diluted_table_total
        )

        checks.append({
            "check":
                (
                    "Instruments Outstanding total = "
                    "Fully Diluted Table total"
                ),

            "difference":
                round_value(
                    difference
                ),

            "status":
                (
                    "OK"
                    if abs(
                        difference
                    ) < 0.01
                    else "REVIEW"
                ),
        })

    all_checks_ok = (
        bool(checks)
        and all(
            item[
                "status"
            ] == "OK"
            for item in checks
        )
    )

    return {
        "available":
            fully_diluted
            is not None,

        "status":
            (
                "VALIDATED"
                if all_checks_ok
                else (
                    "AVAILABLE"
                    if fully_diluted
                    is not None
                    else "REVIEW"
                )
            ),

        "source_file":
            workbook.get(
                "file_name"
            ),

        "basic_equity_shares":
            round_value(
                basic,
                0
            ),

        "ccps_outstanding":
            round_value(
                instruments.get(
                    "ccps_outstanding"
                ),
                0
            ),

        "ccps_conversion_ratio":
            round_value(
                instruments.get(
                    "ccps_conversion_ratio"
                ),
                4
            ),

        "equity_from_ccps":
            round_value(
                ccps_equity,
                0
            ),

        "warrants_outstanding":
            round_value(
                instruments.get(
                    "warrants_outstanding"
                ),
                0
            ),

        "equity_from_warrants":
            round_value(
                warrant_equity,
                0
            ),

        "esop_vested":
            round_value(
                instruments.get(
                    "esop_vested"
                ),
                0
            ),

        "esop_unvested":
            round_value(
                instruments.get(
                    "esop_unvested"
                ),
                0
            ),

        "equity_from_esops":
            round_value(
                esop_equity,
                0
            ),

        "computed_fully_diluted_shares":
            round_value(
                computed_total,
                0
            ),

        "fully_diluted_shares":
            round_value(
                fully_diluted,
                0
            ),

        "future_cash_receivable_on_exercise":
            round_value(
                diluted.get(
                    "total_cash_receivable"
                )
            ),

        "future_cash_receivable_warrants":
            round_value(
                diluted.get(
                    "cash_receivable_warrants"
                )
            ),

        "future_cash_receivable_esops":
            round_value(
                diluted.get(
                    "cash_receivable_esops"
                )
            ),

        "instruments":
            instruments.get(
                "instruments",
                []
            ),

        "holders":
            diluted.get(
                "holders",
                []
            ),

        "categories":
            diluted.get(
                "categories",
                []
            ),

        "checks":
            checks,

        "valuation_note":
            (
                "Fully diluted shares include conversion of CCPS "
                "and exercise of outstanding warrants and ESOPs. "
                "Future exercise proceeds are disclosed separately "
                "and are not automatically added to valuation-date cash."
            ),
    }


# =========================================================
# FINANCIAL CALCULATIONS
# =========================================================

def calculate_ebit(
    pnl: Dict,
) -> Optional[float]:

    direct = get_field_value(
        pnl,
        "ebit"
    )

    if direct is not None:
        return direct

    ebitda = get_field_value(
        pnl,
        "ebitda"
    )

    depreciation = get_field_value(
        pnl,
        "depreciation_amortisation"
    )

    if (
        ebitda is not None
        and depreciation is not None
    ):

        return (
            ebitda
            - depreciation
        )

    pbt = get_field_value(
        pnl,
        "pbt"
    )

    finance_cost = get_field_value(
        pnl,
        "finance_cost"
    )

    if (
        pbt is not None
        and finance_cost is not None
    ):

        return (
            pbt
            +
            finance_cost
        )

    return None


def calculate_total_debt(
    bs: Dict,
) -> Optional[float]:

    long_term = get_field_value(
        bs,
        "long_term_borrowings"
    )

    short_term = get_field_value(
        bs,
        "short_term_borrowings"
    )

    return sum_available(
        long_term,
        short_term
    )


def calculate_current_assets(
    bs: Dict,
) -> Optional[float]:

    direct = get_field_value(
        bs,
        "current_assets"
    )

    if direct is not None:
        return direct

    return sum_available(
        get_field_value(
            bs,
            "inventory"
        ),
        get_field_value(
            bs,
            "trade_receivables"
        ),
        get_field_value(
            bs,
            "cash_and_equivalents"
        ),
        get_field_value(
            bs,
            "short_term_loans_advances"
        ),
        get_field_value(
            bs,
            "other_current_assets"
        ),
    )


def calculate_current_liabilities(
    bs: Dict,
) -> Optional[float]:

    direct = get_field_value(
        bs,
        "current_liabilities"
    )

    if direct is not None:
        return direct

    return sum_available(
        get_field_value(
            bs,
            "short_term_borrowings"
        ),
        get_field_value(
            bs,
            "trade_payables"
        ),
        get_field_value(
            bs,
            "other_current_liabilities"
        ),
        get_field_value(
            bs,
            "short_term_provisions"
        ),
    )


def calculate_capital_employed(
    bs: Dict,
) -> Optional[float]:

    net_worth = get_field_value(
        bs,
        "net_worth"
    )

    debt = calculate_total_debt(
        bs
    )

    if (
        net_worth is None
        or debt is None
    ):
        return None

    return net_worth + debt


def calculate_period_metrics(
    bucket_data: Dict,
    period_key: str,
) -> Dict:

    pnl = get_statement_period(
        bucket_data,
        "income_statement",
        period_key
    )

    bs = get_statement_period(
        bucket_data,
        "balance_sheet",
        period_key
    )

    cash_flow = get_statement_period(
        bucket_data,
        "cash_flow",
        period_key
    )

    revenue = get_field_value(
        pnl,
        "revenue_from_operations"
    )

    total_income = get_field_value(
        pnl,
        "total_income"
    )

    ebitda = get_field_value(
        pnl,
        "ebitda"
    )

    depreciation = get_field_value(
        pnl,
        "depreciation_amortisation"
    )

    ebit = calculate_ebit(
        pnl
    )

    finance_cost = get_field_value(
        pnl,
        "finance_cost"
    )

    pbt = get_field_value(
        pnl,
        "pbt"
    )

    pat = get_field_value(
        pnl,
        "pat"
    )

    current_assets = (
        calculate_current_assets(
            bs
        )
    )

    current_liabilities = (
        calculate_current_liabilities(
            bs
        )
    )

    inventory = get_field_value(
        bs,
        "inventory"
    )

    receivables = get_field_value(
        bs,
        "trade_receivables"
    )

    payables = get_field_value(
        bs,
        "trade_payables"
    )

    cash = get_field_value(
        bs,
        "cash_and_equivalents"
    )

    net_worth = get_field_value(
        bs,
        "net_worth"
    )

    total_assets = get_field_value(
        bs,
        "total_assets"
    )

    total_debt = (
        calculate_total_debt(
            bs
        )
    )

    capital_employed = (
        calculate_capital_employed(
            bs
        )
    )

    quick_assets = None

    if current_assets is not None:

        quick_assets = (
            current_assets
            -
            (
                inventory
                or 0
            )
        )

    return {
        "revenue":
            round_value(
                revenue
            ),

        "total_income":
            round_value(
                total_income
            ),

        "ebitda":
            round_value(
                ebitda
            ),

        "ebit":
            round_value(
                ebit
            ),

        "pbt":
            round_value(
                pbt
            ),

        "pat":
            round_value(
                pat
            ),

        "depreciation":
            round_value(
                depreciation
            ),

        "finance_cost":
            round_value(
                finance_cost
            ),

        "ebitda_margin":
            percentage(
                ebitda,
                revenue
            ),

        "ebit_margin":
            percentage(
                ebit,
                revenue
            ),

        "pbt_margin":
            percentage(
                pbt,
                revenue
            ),

        "pat_margin":
            percentage(
                pat,
                revenue
            ),

        "current_assets":
            round_value(
                current_assets
            ),

        "current_liabilities":
            round_value(
                current_liabilities
            ),

        "inventory":
            round_value(
                inventory
            ),

        "trade_receivables":
            round_value(
                receivables
            ),

        "trade_payables":
            round_value(
                payables
            ),

        "cash":
            round_value(
                cash
            ),

        "net_worth":
            round_value(
                net_worth
            ),

        "total_assets":
            round_value(
                total_assets
            ),

        "total_debt":
            round_value(
                total_debt
            ),

        "capital_employed":
            round_value(
                capital_employed
            ),

        "current_ratio":
            round_value(
                safe_divide(
                    current_assets,
                    current_liabilities
                )
            ),

        "quick_ratio":
            round_value(
                safe_divide(
                    quick_assets,
                    current_liabilities
                )
            ),

        "debt_equity":
            round_value(
                safe_divide(
                    total_debt,
                    net_worth
                )
            ),

        "interest_coverage":
            round_value(
                safe_divide(
                    ebitda,
                    finance_cost
                )
            ),

        "interest_coverage_ebit":
            round_value(
                safe_divide(
                    ebit,
                    finance_cost
                )
            ),

        "interest_coverage_ebitda":
            round_value(
                safe_divide(
                    ebitda,
                    finance_cost
                )
            ),

        "cash_flow_from_operations":
            round_value(
                get_field_value(
                    cash_flow,
                    "cash_flow_from_operations"
                )
            ),

        "cash_flow_from_investing":
            round_value(
                get_field_value(
                    cash_flow,
                    "cash_flow_from_investing"
                )
            ),

        "cash_flow_from_financing":
            round_value(
                get_field_value(
                    cash_flow,
                    "cash_flow_from_financing"
                )
            ),

        "closing_cash":
            round_value(
                get_field_value(
                    cash_flow,
                    "closing_cash"
                )
            ),

        "capex":
            None,

        "change_working_capital":
            None,
    }


# =========================================================
# COMPARATIVE RATIOS
# =========================================================

def average_value(
    current: Optional[float],
    previous: Optional[float],
) -> Optional[float]:

    if current is None:
        return None

    if previous is None:
        return current

    return (
        current
        +
        previous
    ) / 2


def add_comparative_ratios(
    rows: List[Dict],
    bucket_name: str,
) -> List[Dict]:

    if bucket_name == "provisional":

        for row in rows:

            metrics = row[
                "metrics"
            ]

            metrics["roe"] = None
            metrics["roce"] = None
            metrics[
                "receivable_days"
            ] = None
            metrics[
                "inventory_days"
            ] = None
            metrics[
                "payable_days"
            ] = None

        return rows

    for index, row in enumerate(
        rows
    ):

        metrics = row[
            "metrics"
        ]

        previous = (
            rows[
                index - 1
            ][
                "metrics"
            ]
            if index > 0
            else None
        )

        avg_net_worth = (
            average_value(
                metrics.get(
                    "net_worth"
                ),
                (
                    previous.get(
                        "net_worth"
                    )
                    if previous
                    else None
                )
            )
        )

        avg_capital_employed = (
            average_value(
                metrics.get(
                    "capital_employed"
                ),
                (
                    previous.get(
                        "capital_employed"
                    )
                    if previous
                    else None
                )
            )
        )

        avg_receivables = (
            average_value(
                metrics.get(
                    "trade_receivables"
                ),
                (
                    previous.get(
                        "trade_receivables"
                    )
                    if previous
                    else None
                )
            )
        )

        avg_inventory = (
            average_value(
                metrics.get(
                    "inventory"
                ),
                (
                    previous.get(
                        "inventory"
                    )
                    if previous
                    else None
                )
            )
        )

        avg_payables = (
            average_value(
                metrics.get(
                    "trade_payables"
                ),
                (
                    previous.get(
                        "trade_payables"
                    )
                    if previous
                    else None
                )
            )
        )

        revenue = metrics.get(
            "revenue"
        )

        metrics["roe"] = percentage(
            metrics.get(
                "pat"
            ),
            avg_net_worth
        )

        metrics["roce"] = percentage(
            metrics.get(
                "ebit"
            ),
            avg_capital_employed
        )

        if (
            revenue is not None
            and revenue != 0
        ):

            metrics[
                "receivable_days"
            ] = round_value(
                (
                    avg_receivables
                    / revenue
                    * 365
                )
                if avg_receivables
                is not None
                else None
            )

            metrics[
                "inventory_days"
            ] = round_value(
                (
                    avg_inventory
                    / revenue
                    * 365
                )
                if avg_inventory
                is not None
                else None
            )

            metrics[
                "payable_days"
            ] = round_value(
                (
                    avg_payables
                    / revenue
                    * 365
                )
                if avg_payables
                is not None
                else None
            )

        else:

            metrics[
                "receivable_days"
            ] = None

            metrics[
                "inventory_days"
            ] = None

            metrics[
                "payable_days"
            ] = None

    return rows


def analyze_bucket(
    bucket_data: Dict,
    bucket_name: str,
) -> List[Dict]:

    rows = []

    for period in collect_periods(
        bucket_data
    ):

        rows.append({
            "period":
                period[
                    "key"
                ],

            "display":
                period[
                    "display"
                ],

            "sort_key":
                period[
                    "sort_key"
                ],

            "bucket":
                bucket_name,

            "metrics":
                calculate_period_metrics(
                    bucket_data,
                    period[
                        "key"
                    ]
                ),
        })

    return add_comparative_ratios(
        rows,
        bucket_name
    )


def apply_projection_schedule_metrics(
    projected_rows: List[Dict],
    schedule_metrics: Dict[str, Dict],
) -> List[Dict]:

    for row in projected_rows:

        period = row.get(
            "period"
        )

        schedule = (
            schedule_metrics.get(
                period,
                {}
            )
        )

        metrics = row.get(
            "metrics",
            {}
        )

        metrics[
            "capex"
        ] = schedule.get(
            "capex"
        )

        metrics[
            "change_working_capital"
        ] = schedule.get(
            "change_working_capital"
        )

        metrics[
            "capex_source"
        ] = schedule.get(
            "capex_source"
        )

        metrics[
            "capex_basis"
        ] = schedule.get(
            "capex_basis"
        )

        metrics[
            "working_capital_source"
        ] = schedule.get(
            "working_capital_source"
        )

        metrics[
            "working_capital_basis"
        ] = schedule.get(
            "working_capital_basis"
        )

    return projected_rows


# =========================================================
# GROWTH / CAGR / COMPARISON
# =========================================================

def add_growth_rates(
    rows: List[Dict],
) -> List[Dict]:

    for index, row in enumerate(
        rows
    ):

        metrics = row[
            "metrics"
        ]

        metrics[
            "revenue_growth"
        ] = None

        metrics[
            "ebitda_growth"
        ] = None

        metrics[
            "pat_growth"
        ] = None

        if index == 0:
            continue

        previous = (
            rows[
                index - 1
            ][
                "metrics"
            ]
        )

        metrics[
            "revenue_growth"
        ] = growth_rate(
            metrics.get(
                "revenue"
            ),
            previous.get(
                "revenue"
            )
        )

        metrics[
            "ebitda_growth"
        ] = growth_rate(
            metrics.get(
                "ebitda"
            ),
            previous.get(
                "ebitda"
            )
        )

        metrics[
            "pat_growth"
        ] = growth_rate(
            metrics.get(
                "pat"
            ),
            previous.get(
                "pat"
            )
        )

    return rows


def financial_year_rows(
    rows: List[Dict],
) -> List[Dict]:

    return [
        row
        for row in rows
        if re.match(
            r"^FY20\d{2}$",
            row.get(
                "period",
                ""
            )
        )
    ]


def build_cagr_summary(
    rows: List[Dict],
) -> Dict:

    fy_rows = financial_year_rows(
        rows
    )

    if len(fy_rows) < 2:

        return {
            "revenue_cagr":
                None,

            "ebitda_cagr":
                None,

            "pat_cagr":
                None,
        }

    first = fy_rows[
        0
    ][
        "metrics"
    ]

    last = fy_rows[
        -1
    ][
        "metrics"
    ]

    years = (
        len(fy_rows)
        - 1
    )

    return {
        "revenue_cagr":
            cagr(
                first.get(
                    "revenue"
                ),
                last.get(
                    "revenue"
                ),
                years,
            ),

        "ebitda_cagr":
            cagr(
                first.get(
                    "ebitda"
                ),
                last.get(
                    "ebitda"
                ),
                years,
            ),

        "pat_cagr":
            cagr(
                first.get(
                    "pat"
                ),
                last.get(
                    "pat"
                ),
                years,
            ),
    }


def build_projection_comparison(
    historical_rows: List[Dict],
    projected_rows: List[Dict],
) -> Dict:

    historical_fy = (
        financial_year_rows(
            historical_rows
        )
    )

    projected_fy = (
        financial_year_rows(
            projected_rows
        )
    )

    if (
        not historical_fy
        or not projected_fy
    ):

        return {
            "available":
                False
        }

    latest_historical = (
        historical_fy[-1]
    )

    first_projection = (
        projected_fy[0]
    )

    last_projection = (
        projected_fy[-1]
    )

    hist = (
        latest_historical[
            "metrics"
        ]
    )

    first = (
        first_projection[
            "metrics"
        ]
    )

    last = (
        last_projection[
            "metrics"
        ]
    )

    years = max(
        len(projected_fy)
        - 1,
        1
    )

    return {
        "available":
            True,

        "latest_historical_period":
            latest_historical[
                "display"
            ],

        "first_projected_period":
            first_projection[
                "display"
            ],

        "last_projected_period":
            last_projection[
                "display"
            ],

        "first_year_revenue_growth":
            growth_rate(
                first.get(
                    "revenue"
                ),
                hist.get(
                    "revenue"
                )
            ),

        "first_year_ebitda_growth":
            growth_rate(
                first.get(
                    "ebitda"
                ),
                hist.get(
                    "ebitda"
                )
            ),

        "first_year_pat_growth":
            growth_rate(
                first.get(
                    "pat"
                ),
                hist.get(
                    "pat"
                )
            ),

        "historical_ebitda_margin":
            hist.get(
                "ebitda_margin"
            ),

        "first_projected_ebitda_margin":
            first.get(
                "ebitda_margin"
            ),

        "terminal_projected_ebitda_margin":
            last.get(
                "ebitda_margin"
            ),

        "historical_pat_margin":
            hist.get(
                "pat_margin"
            ),

        "first_projected_pat_margin":
            first.get(
                "pat_margin"
            ),

        "terminal_projected_pat_margin":
            last.get(
                "pat_margin"
            ),

        "projected_revenue_cagr":
            cagr(
                first.get(
                    "revenue"
                ),
                last.get(
                    "revenue"
                ),
                years,
            ),

        "projected_ebitda_cagr":
            cagr(
                first.get(
                    "ebitda"
                ),
                last.get(
                    "ebitda"
                ),
                years,
            ),

        "projected_pat_cagr":
            cagr(
                first.get(
                    "pat"
                ),
                last.get(
                    "pat"
                ),
                years,
            ),
    }


def build_observations(
    historical_rows: List[Dict],
    projected_rows: List[Dict],
    projection_comparison: Dict,
) -> List[Dict]:

    observations = []

    historical_fy = (
        financial_year_rows(
            historical_rows
        )
    )

    if len(
        historical_fy
    ) >= 2:

        latest = (
            historical_fy[
                -1
            ][
                "metrics"
            ]
        )

        revenue_growth = (
            latest.get(
                "revenue_growth"
            )
        )

        if (
            revenue_growth
            is not None
            and revenue_growth > 15
        ):

            observations.append({
                "type":
                    "positive",

                "category":
                    "Revenue",

                "message":
                    (
                        f"Revenue increased by "
                        f"{revenue_growth}% in the latest historical year."
                    ),
            })

    if historical_fy:

        latest = (
            historical_fy[
                -1
            ][
                "metrics"
            ]
        )

        debt_equity = (
            latest.get(
                "debt_equity"
            )
        )

        if (
            debt_equity
            is not None
            and debt_equity < 1
        ):

            observations.append({
                "type":
                    "positive",

                "category":
                    "Leverage",

                "message":
                    (
                        f"Debt-to-equity ratio is "
                        f"{debt_equity}x."
                    ),
            })

    return observations


# =========================================================
# MAIN
# =========================================================

def analyze_normalized_financials(
    extraction_result: Dict,
) -> Dict:

    combined = extraction_result.get(
        "combined_normalized",
        {}
    )

    historical_rows = analyze_bucket(
        combined.get(
            "historical",
            {}
        ),
        "historical",
    )

    provisional_rows = analyze_bucket(
        combined.get(
            "provisional",
            {}
        ),
        "provisional",
    )

    projected_rows = analyze_bucket(
        combined.get(
            "projected",
            {}
        ),
        "projected",
    )

    projection_schedule_metrics = (
        extract_projection_schedule_metrics(
            extraction_result
        )
    )

    projected_rows = (
        apply_projection_schedule_metrics(
            projected_rows,
            projection_schedule_metrics,
        )
    )

    historical_rows = (
        add_growth_rates(
            historical_rows
        )
    )

    projected_rows = (
        add_growth_rates(
            projected_rows
        )
    )

    historical_cagr = (
        build_cagr_summary(
            historical_rows
        )
    )

    projected_cagr = (
        build_cagr_summary(
            projected_rows
        )
    )

    projection_comparison = (
        build_projection_comparison(
            historical_rows,
            projected_rows,
        )
    )

    observations = (
        build_observations(
            historical_rows,
            projected_rows,
            projection_comparison,
        )
    )

    capital_structure = (
        analyze_capital_structure(
            extraction_result
        )
    )

    return {
        "analysis_engine_version":
            ANALYSIS_ENGINE_VERSION,

        "historical":
            historical_rows,

        "provisional":
            provisional_rows,

        "projected":
            projected_rows,

        "projection_schedule_metrics":
            projection_schedule_metrics,

        "capital_structure":
            capital_structure,

        "historical_cagr":
            historical_cagr,

        "projected_cagr":
            projected_cagr,

        "projection_comparison":
            projection_comparison,

        "observations":
            observations,
    }