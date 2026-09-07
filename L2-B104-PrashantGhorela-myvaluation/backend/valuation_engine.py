from typing import List, Dict, Optional


def calculate_fcff(
    projections: List[Dict],
    tax_rate: float
):
    """
    Expected projection keys:
    year
    ebit
    depreciation
    capex
    change_working_capital
    """

    if not projections:
        raise ValueError(
            "At least one projection year is required."
        )

    if tax_rate < 0 or tax_rate > 1:
        raise ValueError(
            "Tax rate must be between 0 and 1."
        )

    results = []

    for row in projections:

        ebit = float(
            row.get(
                "ebit",
                0
            )
        )

        depreciation = float(
            row.get(
                "depreciation",
                0
            )
        )

        capex = float(
            row.get(
                "capex",
                0
            )
        )

        change_wc = float(
            row.get(
                "change_working_capital",
                0
            )
        )

        nopat = (
            ebit
            * (1 - tax_rate)
        )

        fcff = (
            nopat
            + depreciation
            - capex
            - change_wc
        )

        results.append({
            "year":
                row.get("year"),

            "ebit":
                round(ebit, 2),

            "nopat":
                round(nopat, 2),

            "depreciation":
                round(
                    depreciation,
                    2
                ),

            "capex":
                round(
                    capex,
                    2
                ),

            "change_working_capital":
                round(
                    change_wc,
                    2
                ),

            "fcff":
                round(
                    fcff,
                    2
                ),
        })

    return results


def calculate_dcf(
    projections: List[Dict],
    tax_rate: float,
    wacc: float,
    terminal_growth: float,
    cash: float,
    debt: float,
    non_operating_assets: float = 0,
):
    """
    Rates should be decimals.

    Example:
    tax_rate = 0.2517
    wacc = 0.12
    terminal_growth = 0.05
    """

    if wacc <= 0:
        raise ValueError(
            "WACC must be greater than zero."
        )

    if terminal_growth < 0:
        raise ValueError(
            "Terminal growth rate cannot be negative."
        )

    if wacc <= terminal_growth:
        raise ValueError(
            "WACC must be greater than terminal growth rate."
        )

    fcff_rows = calculate_fcff(
        projections,
        tax_rate
    )

    pv_fcff_total = 0

    for index, row in enumerate(
        fcff_rows,
        start=1
    ):
        discount_factor = (
            1
            / (
                (1 + wacc)
                ** index
            )
        )

        pv_fcff = (
            row["fcff"]
            * discount_factor
        )

        row[
            "discount_factor"
        ] = round(
            discount_factor,
            6
        )

        row[
            "pv_fcff"
        ] = round(
            pv_fcff,
            2
        )

        pv_fcff_total += (
            pv_fcff
        )

    final_fcff = (
        fcff_rows[-1][
            "fcff"
        ]
    )

    terminal_value = (
        final_fcff
        * (
            1
            + terminal_growth
        )
        / (
            wacc
            - terminal_growth
        )
    )

    terminal_discount_factor = (
        1
        / (
            (1 + wacc)
            ** len(
                fcff_rows
            )
        )
    )

    pv_terminal_value = (
        terminal_value
        * terminal_discount_factor
    )

    enterprise_value = (
        pv_fcff_total
        + pv_terminal_value
    )

    equity_value = (
        enterprise_value
        + cash
        + non_operating_assets
        - debt
    )

    return {
        "fcff":
            fcff_rows,

        "pv_explicit_fcff":
            round(
                pv_fcff_total,
                2
            ),

        "terminal_value":
            round(
                terminal_value,
                2
            ),

        "pv_terminal_value":
            round(
                pv_terminal_value,
                2
            ),

        "enterprise_value":
            round(
                enterprise_value,
                2
            ),

        "cash":
            round(
                cash,
                2
            ),

        "non_operating_assets":
            round(
                non_operating_assets,
                2
            ),

        "debt":
            round(
                debt,
                2
            ),

        "equity_value":
            round(
                equity_value,
                2
            ),
    }


def calculate_dcf_sensitivity(
    projections: List[Dict],
    tax_rate: float,
    base_wacc: float,
    base_terminal_growth: float,
    cash: float,
    debt: float,
    non_operating_assets: float,
    diluted_shares: float,
    wacc_offsets: Optional[List[float]] = None,
    growth_offsets: Optional[List[float]] = None,
) -> Dict:
    """
    Builds a deterministic DCF sensitivity table.

    All rates / offsets are decimals.
    Default WACC offsets: -2%, -1%, 0%, +1%, +2%
    Default growth offsets: -1%, -0.5%, 0%, +0.5%, +1%
    """

    if diluted_shares <= 0:
        raise ValueError(
            "Fully diluted shares must be greater than zero."
        )

    if wacc_offsets is None:
        wacc_offsets = [
            -0.02,
            -0.01,
            0.00,
            0.01,
            0.02,
        ]

    if growth_offsets is None:
        growth_offsets = [
            -0.01,
            -0.005,
            0.00,
            0.005,
            0.01,
        ]

    wacc_values = [
        round(
            base_wacc
            + offset,
            6
        )
        for offset
        in wacc_offsets
    ]

    growth_values = [
        round(
            max(
                base_terminal_growth
                + offset,
                0
            ),
            6
        )
        for offset
        in growth_offsets
    ]

    rows = []

    for growth in growth_values:

        row = {
            "terminal_growth":
                round(
                    growth
                    * 100,
                    2
                ),

            "values":
                [],
        }

        for sensitivity_wacc in wacc_values:

            if (
                sensitivity_wacc
                <= growth
            ):
                row[
                    "values"
                ].append({
                    "wacc":
                        round(
                            sensitivity_wacc
                            * 100,
                            2
                        ),

                    "equity_value":
                        None,

                    "value_per_share":
                        None,

                    "status":
                        "INVALID",
                })

                continue

            result = (
                calculate_dcf(
                    projections=
                        projections,

                    tax_rate=
                        tax_rate,

                    wacc=
                        sensitivity_wacc,

                    terminal_growth=
                        growth,

                    cash=
                        cash,

                    debt=
                        debt,

                    non_operating_assets=
                        non_operating_assets,
                )
            )

            value_per_share = (
                calculate_value_per_share(
                    result[
                        "equity_value"
                    ],
                    diluted_shares
                )
            )

            row[
                "values"
            ].append({
                "wacc":
                    round(
                        sensitivity_wacc
                        * 100,
                        2
                    ),

                "equity_value":
                    result[
                        "equity_value"
                    ],

                "value_per_share":
                    value_per_share,

                "status":
                    "OK",
            })

        rows.append(
            row
        )

    return {
        "base_wacc_percent":
            round(
                base_wacc
                * 100,
                2
            ),

        "base_terminal_growth_percent":
            round(
                base_terminal_growth
                * 100,
                2
            ),

        "wacc_values_percent": [
            round(
                value
                * 100,
                2
            )
            for value
            in wacc_values
        ],

        "terminal_growth_values_percent": [
            round(
                value
                * 100,
                2
            )
            for value
            in growth_values
        ],

        "rows":
            rows,

        "metric":
            "Value Per Share",
    }


def calculate_nav(
    adjusted_assets: float,
    adjusted_liabilities: float
):
    nav = (
        adjusted_assets
        - adjusted_liabilities
    )

    return round(
        nav,
        2
    )


def calculate_weighted_value(
    methods: List[Dict]
):
    """
    Example:

    [
        {
            "method": "DCF",
            "value": 1000,
            "weight": 70
        },
        {
            "method": "NAV",
            "value": 800,
            "weight": 30
        }
    ]
    """

    if not methods:
        raise ValueError(
            "At least one valuation method is required."
        )

    total_weight = sum(
        float(
            item[
                "weight"
            ]
        )
        for item
        in methods
    )

    if (
        round(
            total_weight,
            6
        )
        != 100
    ):
        raise ValueError(
            "Total method weightage must equal 100%."
        )

    rows = []
    weighted_total = 0

    for item in methods:

        value = float(
            item[
                "value"
            ]
        )

        weight = float(
            item[
                "weight"
            ]
        )

        if weight < 0:
            raise ValueError(
                "Method weightage cannot be negative."
            )

        weighted_value = (
            value
            * weight
            / 100
        )

        weighted_total += (
            weighted_value
        )

        rows.append({
            "method":
                item[
                    "method"
                ],

            "value":
                round(
                    value,
                    2
                ),

            "weight":
                round(
                    weight,
                    2
                ),

            "weighted_value":
                round(
                    weighted_value,
                    2
                )
        })

    return {
        "methods":
            rows,

        "concluded_value":
            round(
                weighted_total,
                2
            )
    }


def calculate_value_per_share(
    equity_value: float,
    diluted_shares: float,
    equity_value_unit: str = "lakhs"
):
    """
    Calculates value per share.

    The current myvaluation financial statements and valuation outputs
    are expressed in Rs. lakhs, while diluted_shares is an absolute
    number of shares.

    Therefore:
        Value per Share =
        Equity Value (Rs. lakhs) x 100,000 / Fully Diluted Shares

    Set equity_value_unit="absolute" only if equity_value is already
    expressed in absolute Rs.
    """

    if diluted_shares <= 0:
        raise ValueError(
            "Fully diluted shares must be greater than zero."
        )

    if equity_value_unit == "lakhs":
        equity_value_rupees = (
            float(equity_value)
            * 100000
        )

    elif equity_value_unit == "absolute":
        equity_value_rupees = float(
            equity_value
        )

    else:
        raise ValueError(
            "equity_value_unit must be either 'lakhs' or 'absolute'."
        )

    return round(
        equity_value_rupees
        / float(diluted_shares),
        2
    )
