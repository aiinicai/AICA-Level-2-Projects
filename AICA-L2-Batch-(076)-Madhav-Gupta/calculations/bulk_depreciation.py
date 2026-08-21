from calculations.companies_act import calculate_slm_depreciation, calculate_wdv_depreciation
from calculations.income_tax import calculate_block_income_tax_depreciation
from calculations.deferred_tax import calculate_deferred_tax
from utils.formatting import to_decimal
from utils.date_utils import parse_date


def calculate_asset_companies_act(asset, period_start, period_end, basis, year_days):
    """
    Companies Act depreciation for a SINGLE asset, based on the ACTUAL date the asset
    was put to use (not blindly assuming the full period). If the asset was put to use
    partway through the period, only the actual number of days/months it was in use
    during the period is depreciated.
    """
    errors = []
    method = (asset.get("companies_act_method") or "").upper()
    if method not in ("SLM", "WDV"):
        errors.append("Missing/invalid Companies Act method")
    useful_life = asset.get("useful_life_years")
    if method == "SLM" and (useful_life is None or to_decimal(useful_life) <= 0):
        errors.append("Missing useful life")
    if method == "WDV" and asset.get("companies_act_rate") in (None, ""):
        errors.append("Missing Companies Act WDV rate")
    if asset.get("opening_carrying_amount") is None:
        errors.append("Missing opening carrying amount")
    if not asset.get("date_put_to_use"):
        errors.append("Missing date put to use")

    if errors:
        return {"asset_id": asset.get("asset_id"), "status": "ERROR", "exception": "; ".join(errors)}

    p_start = parse_date(period_start)
    p_end = parse_date(period_end)
    put_to_use = parse_date(asset["date_put_to_use"])
    effective_start = max(put_to_use, p_start)

    if effective_start > p_end:
        opening = to_decimal(asset["opening_carrying_amount"])
        return {
            "asset_id": asset["asset_id"], "asset_name": asset.get("asset_name"),
            "opening_carrying_amount": opening, "companies_act_method": method,
            "companies_act_depreciation": to_decimal(0), "closing_carrying_amount": opening,
            "status": "OK", "exception": "Not yet put to use during this period",
        }

    residual_value = asset.get("residual_value") or 0
    cost = asset.get("original_cost")
    opening_carrying_amount = asset["opening_carrying_amount"]
    opening_accum_dep = asset.get("opening_accum_dep") or 0

    if method == "SLM":
        result = calculate_slm_depreciation(
            cost=cost, residual_value=residual_value, useful_life_years=useful_life,
            period_start=effective_start, period_end=p_end, basis=basis, year_days=year_days,
            opening_accum_dep=opening_accum_dep,
        )
    else:
        result = calculate_wdv_depreciation(
            opening_wdv=opening_carrying_amount, rate=asset.get("companies_act_rate"),
            residual_value=residual_value, period_start=effective_start, period_end=p_end,
            basis=basis, year_days=year_days,
        )

    depreciation = result["period_depreciation"]
    closing = to_decimal(opening_carrying_amount) - to_decimal(depreciation)

    return {
        "asset_id": asset["asset_id"], "asset_name": asset.get("asset_name"),
        "opening_carrying_amount": to_decimal(opening_carrying_amount),
        "companies_act_method": method, "companies_act_depreciation": depreciation,
        "closing_carrying_amount": closing, "effective_start": effective_start,
        "effective_end": p_end, "status": "OK", "exception": None,
    }


def calculate_block_depreciation(block, additions_full, additions_half, disposals, deferred_tax_rate,
                                  closing_carrying_amount_total):
    """
    Income-tax depreciation computed at the BLOCK OF ASSETS level. Individual disposed
    assets never carry their own tax depreciation - the sale consideration only reduces
    the block's WDV. Deferred tax is computed by comparing the AGGREGATE CLOSING
    carrying amount (Companies Act) of assets remaining in the block against the
    block's closing tax WDV.
    """
    rate = block.get("rate", 0)
    opening_wdv = block.get("opening_wdv", 0)

    it_result = calculate_block_income_tax_depreciation(
        opening_wdv=opening_wdv, additions_full_rate=additions_full, additions_half_rate=additions_half,
        disposal_proceeds=disposals, rate=rate,
    )

    dt_result = calculate_deferred_tax(closing_carrying_amount_total, it_result["closing_wdv"], deferred_tax_rate)

    return {
        "block_id": block["block_id"], "block_code": block.get("block_code"),
        "opening_wdv": it_result["opening_wdv"], "additions_full_rate": to_decimal(additions_full),
        "additions_half_rate": to_decimal(additions_half), "disposals": it_result["disposals"],
        "wdv_before_depreciation": it_result["wdv_before_depreciation"], "tax_rate": rate,
        "depreciation": it_result["depreciation"], "closing_wdv": it_result["closing_wdv"],
        "short_term_capital_gain": it_result["short_term_capital_gain"],
        "closing_carrying_amount_total": dt_result["carrying_amount"],
        "temporary_difference": dt_result["temporary_difference"],
        "deferred_tax_rate": deferred_tax_rate, "deferred_tax": dt_result["deferred_tax"],
        "deferred_tax_type": dt_result["deferred_tax_type"], "status": "OK",
    }


def run_bulk_depreciation(assets, period_start, period_end, basis, year_days):
    """
    Phase 1: per-asset Companies Act depreciation only. Block-level Income-tax and
    deferred tax calculations are performed separately (see services/depreciation_service.py)
    once assets have been grouped by their Income-tax Block.
    """
    results = []
    for asset in assets:
        try:
            result = calculate_asset_companies_act(asset, period_start, period_end, basis, year_days)
        except Exception as exc:
            result = {"asset_id": asset.get("asset_id"), "status": "ERROR", "exception": str(exc)}
        results.append(result)
    return results