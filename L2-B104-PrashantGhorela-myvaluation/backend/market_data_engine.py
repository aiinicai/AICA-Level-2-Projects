from typing import Dict, List, Optional, Any
from datetime import datetime
import re
import urllib.request


# =========================================================
# MARKET DATA SUGGESTION ENGINE
# =========================================================
#
# Design:
# - Suggestions only. The Registered Valuer remains responsible
#   for review and approval.
# - No AI is used in the calculations.
# - Risk-free rate tries a public historical web source first,
#   then uses a clearly disclosed fallback for the sample date.
# - ERP / beta reference data is based on Damodaran datasets.
# - Cost of debt and capital weights are derived from the
#   assignment's extracted financial statements where possible.
# =========================================================


def _round(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def _fetch_text(url: str, timeout: int = 8) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/152 Safari/537.36"
            )
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="ignore",
        )


def _risk_free_from_countryeconomy(
    valuation_date: str
) -> Optional[Dict[str, Any]]:

    try:
        target = datetime.strptime(
            valuation_date,
            "%Y-%m-%d",
        )

        month_url = (
            "https://countryeconomy.com/bonds/india"
            f"?dr={target.strftime('%Y-%m')}"
        )

        html = _fetch_text(month_url)

        # Locate all mm/dd/yyyy + yield pairs in the historical table.
        matches = re.findall(
            r"(\d{2}/\d{2}/\d{4}).{0,500}?([0-9]+\.[0-9]+)%",
            html,
            flags=re.I | re.S,
        )

        observations = []

        for date_text, yield_text in matches:
            try:
                date_value = datetime.strptime(
                    date_text,
                    "%m/%d/%Y",
                )

                observations.append(
                    (
                        date_value,
                        float(yield_text),
                    )
                )
            except Exception:
                continue

        if not observations:
            return None

        # Use same date where available; otherwise nearest prior
        # trading date. If none is prior, use nearest date.
        prior = [
            item
            for item in observations
            if item[0] <= target
        ]

        if prior:
            chosen = max(
                prior,
                key=lambda item: item[0],
            )
        else:
            chosen = min(
                observations,
                key=lambda item: abs(
                    (item[0] - target).days
                ),
            )

        return {
            "value": _round(chosen[1], 3),
            "date": chosen[0].strftime(
                "%Y-%m-%d"
            ),
            "source": (
                "India 10-Year Government Bond historical yield "
                "- countryeconomy.com"
            ),
            "url": month_url,
            "basis": (
                "10-year India Government Bond yield on the valuation "
                "date or nearest prior available trading date."
            ),
        }

    except Exception:
        return None


def _risk_free_fallback(
    valuation_date: str
) -> Optional[Dict[str, Any]]:

    # Curated fallback currently included for the sample assignment.
    # This is intentionally explicit rather than silently fabricated.
    fallback = {
        "2026-06-01": {
            "value": 7.02,
            "date": "2026-06-01",
            "source": (
                "Bank of Baroda Economic Weekly Wrap / Bloomberg "
                "India 10Y Government Bond yield"
            ),
            "url": (
                "https://bankofbaroda.bank.in/banking-mantra/"
                "economic-scenario/articles/weekly-wrap-01-june-2026"
            ),
            "basis": (
                "India 10-year Government Bond yield reported at "
                "7.02% for 01-Jun-2026."
            ),
        }
    }

    return fallback.get(
        valuation_date
    )


def _suggest_risk_free_rate(
    valuation_date: str
) -> Dict[str, Any]:

    live = _risk_free_from_countryeconomy(
        valuation_date
    )

    if live:
        live["retrieval_mode"] = "WEB"
        return live

    fallback = _risk_free_fallback(
        valuation_date
    )

    if fallback:
        result = dict(fallback)
        result["retrieval_mode"] = (
            "CURATED_FALLBACK"
        )
        return result

    return {
        "value": None,
        "date": valuation_date,
        "source": "",
        "url": "",
        "basis": (
            "Automatic historical risk-free rate was not available. "
            "Valuer input required."
        ),
        "retrieval_mode": "NOT_AVAILABLE",
    }


def _infer_industry(
    assignment: Dict[str, Any]
) -> str:

    searchable = " ".join([
        str(
            assignment.get(
                "company_name",
                ""
            )
        ),
        str(
            assignment.get(
                "transaction_details",
                ""
            )
        ),
    ]).lower()

    if any(
        token in searchable
        for token in [
            "furniture",
            "furnishing",
            "furnishings",
            "wooden furniture",
        ]
    ):
        return "Furn/Home Furnishings"

    return ""


def _suggest_beta(
    assignment: Dict[str, Any]
) -> Dict[str, Any]:

    industry = _infer_industry(
        assignment
    )

    # Current MVP reference table. Add sectors as the app expands.
    beta_table = {
        "Furn/Home Furnishings": {
            "value": 0.97,
            "data_date": "2026-01-01",
            "source": (
                "Aswath Damodaran - Betas by Sector (Global), "
                "Furn/Home Furnishings"
            ),
            "url": (
                "https://pages.stern.nyu.edu/~adamodar/"
                "New_Home_Page/datafile/BetasGlobal.html"
            ),
            "basis": (
                "Global industry levered beta for Furn/Home Furnishings. "
                "Valuer should assess whether a bottom-up/relevered beta "
                "is more appropriate for the subject company."
            ),
        },
    }

    if industry in beta_table:
        result = dict(
            beta_table[industry]
        )
        result["industry"] = industry
        return result

    return {
        "value": None,
        "industry": "",
        "data_date": "2026-01-01",
        "source": (
            "Aswath Damodaran - Betas by Sector"
        ),
        "url": (
            "https://pages.stern.nyu.edu/~adamodar/"
            "New_Home_Page/datafile/BetasGlobal.html"
        ),
        "basis": (
            "Industry could not be inferred reliably. "
            "Select / enter an appropriate beta after valuer review."
        ),
    }


def _suggest_erp() -> Dict[str, Any]:

    # Current India country ERP reference used by the MVP.
    # This remains a suggestion and is explicitly source-labelled.
    return {
        "value": 7.27,
        "data_date": "2026-01-01",
        "source": (
            "Aswath Damodaran - Country Risk Premiums, India"
        ),
        "url": (
            "https://pages.stern.nyu.edu/adamodar/"
            "New_Home_Page/datafile/CountryERPlist.htm"
        ),
        "basis": (
            "India total equity risk premium reference. "
            "Valuer should use the dataset vintage appropriate "
            "to the valuation date."
        ),
    }


def _financial_cost_of_debt(
    detailed_analysis: Dict[str, Any]
) -> Dict[str, Any]:

    historical = (
        detailed_analysis.get(
            "historical",
            []
        )
        or []
    )

    if not historical:
        return {
            "value": None,
            "source": "",
            "basis": (
                "Historical debt / finance cost data unavailable."
            ),
        }

    latest = historical[-1]
    latest_metrics = latest.get(
        "metrics",
        {}
    )

    finance_cost = latest_metrics.get(
        "finance_cost"
    )

    latest_debt = latest_metrics.get(
        "total_debt"
    )

    previous_debt = None

    if len(historical) >= 2:
        previous_debt = (
            historical[-2]
            .get("metrics", {})
            .get("total_debt")
        )

    if (
        finance_cost is None
        or latest_debt is None
        or latest_debt == 0
    ):
        return {
            "value": None,
            "source": "",
            "basis": (
                "Finance cost / debt data insufficient for "
                "an implied borrowing-rate suggestion."
            ),
        }

    if (
        previous_debt is not None
        and previous_debt >= 0
    ):
        average_debt = (
            float(previous_debt)
            + float(latest_debt)
        ) / 2
    else:
        average_debt = float(
            latest_debt
        )

    if average_debt <= 0:
        return {
            "value": None,
            "source": "",
            "basis": (
                "Average debt is not positive."
            ),
        }

    implied_rate = (
        float(finance_cost)
        / average_debt
        * 100
    )

    return {
        "value": _round(
            implied_rate,
            2
        ),
        "source": (
            "Derived from extracted audited financial statements"
        ),
        "basis": (
            f"Latest finance cost {finance_cost} divided by "
            f"average total debt {round(average_debt, 2)}. "
            "This is an accounting implied rate, not automatically "
            "the marginal borrowing rate; valuer review is required."
        ),
        "period": latest.get(
            "display",
            latest.get(
                "period",
                ""
            ),
        ),
    }


def _capital_weights(
    detailed_analysis: Dict[str, Any]
) -> Dict[str, Any]:

    provisional = (
        detailed_analysis.get(
            "provisional",
            []
        )
        or []
    )

    valuation_bs = None

    for row in provisional:
        period = str(
            row.get(
                "period",
                ""
            )
        )

        metrics = row.get(
            "metrics",
            {}
        )

        if (
            not period.startswith("FY")
            and not period.startswith(
                "STUB_"
            )
            and metrics.get(
                "total_debt"
            )
            is not None
            and metrics.get(
                "net_worth"
            )
            is not None
        ):
            valuation_bs = row
            break

    if valuation_bs is None:
        historical = (
            detailed_analysis.get(
                "historical",
                []
            )
            or []
        )

        if historical:
            valuation_bs = (
                historical[-1]
            )

    if valuation_bs is None:
        return {
            "equity_weight": 70.0,
            "debt_weight": 30.0,
            "source": (
                "Default provisional capital mix - valuer review required"
            ),
            "basis": (
                "Valuation-date debt and net worth were unavailable."
            ),
        }

    metrics = valuation_bs.get(
        "metrics",
        {}
    )

    debt = metrics.get(
        "total_debt"
    )

    equity = metrics.get(
        "net_worth"
    )

    if (
        debt is None
        or equity is None
        or (
            float(debt)
            + float(equity)
        ) <= 0
    ):
        return {
            "equity_weight": 70.0,
            "debt_weight": 30.0,
            "source": (
                "Default provisional capital mix - valuer review required"
            ),
            "basis": (
                "Valuation-date debt / net worth were insufficient."
            ),
        }

    total = (
        float(debt)
        + float(equity)
    )

    return {
        "equity_weight": _round(
            float(equity)
            / total
            * 100,
            2,
        ),
        "debt_weight": _round(
            float(debt)
            / total
            * 100,
            2,
        ),
        "source": (
            "Derived from valuation-date extracted balance sheet"
        ),
        "basis": (
            f"Net worth {equity} and total debt {debt}; "
            "book-value capital weights are a suggestion only. "
            "Valuer may replace with market-value / target weights."
        ),
        "period": valuation_bs.get(
            "display",
            valuation_bs.get(
                "period",
                ""
            ),
        ),
    }


def suggest_market_data(
    assignment: Dict[str, Any],
    detailed_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    valuation_date = str(
        assignment.get(
            "valuation_date",
            ""
        )
    )

    risk_free = (
        _suggest_risk_free_rate(
            valuation_date
        )
    )

    erp = _suggest_erp()

    beta = _suggest_beta(
        assignment
    )

    debt_cost = (
        _financial_cost_of_debt(
            detailed_analysis
        )
    )

    weights = _capital_weights(
        detailed_analysis
    )

    warnings: List[str] = []

    if risk_free.get(
        "value"
    ) is None:
        warnings.append(
            "Risk-free rate requires valuer input."
        )

    if beta.get(
        "value"
    ) is None:
        warnings.append(
            "Beta requires valuer input because industry could not be inferred."
        )

    if debt_cost.get(
        "value"
    ) is None:
        warnings.append(
            "Pre-tax cost of debt requires valuer input."
        )
    else:
        warnings.append(
            "Suggested pre-tax cost of debt is an accounting implied rate; "
            "replace it with the current marginal borrowing rate when available."
        )

    warnings.append(
        "Capital weights are book-value based suggestions. "
        "Use market-value / target weights where appropriate."
    )

    warnings.append(
        "Company-specific risk premium is defaulted to 0.00%; "
        "this is a valuer judgement input, not an automated market-data fact."
    )

    return {
        "success": True,
        "assignment_id": assignment.get(
            "assignment_id"
        ),
        "valuation_date": valuation_date,
        "company_name": assignment.get(
            "company_name",
            ""
        ),
        "risk_free_rate_percent": risk_free.get(
            "value"
        ),
        "equity_risk_premium_percent": erp.get(
            "value"
        ),
        "beta": beta.get(
            "value"
        ),
        "company_specific_risk_premium_percent": 0.0,
        "pre_tax_cost_of_debt_percent": debt_cost.get(
            "value"
        ),
        "equity_weight_percent": weights.get(
            "equity_weight"
        ),
        "debt_weight_percent": weights.get(
            "debt_weight"
        ),
        "market_data_date": risk_free.get(
            "date",
            valuation_date
        ),
        "industry": beta.get(
            "industry",
            ""
        ),
        "sources": {
            "risk_free_rate": risk_free.get(
                "source",
                ""
            ),
            "risk_free_url": risk_free.get(
                "url",
                ""
            ),
            "equity_risk_premium": erp.get(
                "source",
                ""
            ),
            "erp_url": erp.get(
                "url",
                ""
            ),
            "beta": beta.get(
                "source",
                ""
            ),
            "beta_url": beta.get(
                "url",
                ""
            ),
            "cost_of_debt": debt_cost.get(
                "source",
                ""
            ),
            "capital_weights": weights.get(
                "source",
                ""
            ),
        },
        "basis": {
            "risk_free_rate": risk_free.get(
                "basis",
                ""
            ),
            "equity_risk_premium": erp.get(
                "basis",
                ""
            ),
            "beta": beta.get(
                "basis",
                ""
            ),
            "cost_of_debt": debt_cost.get(
                "basis",
                ""
            ),
            "capital_weights": weights.get(
                "basis",
                ""
            ),
        },
        "warnings": warnings,
        "status": (
            "SUGGESTIONS_READY"
            if (
                risk_free.get("value")
                is not None
                and erp.get("value")
                is not None
                and beta.get("value")
                is not None
                and debt_cost.get("value")
                is not None
            )
            else "PARTIAL_SUGGESTIONS"
        ),
        "approval_required": True,
    }
