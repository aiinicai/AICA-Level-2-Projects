from repositories import depreciation_repository as dep_repo
from repositories import asset_repository, settings_repository, disposal_repository
from calculations.bulk_depreciation import run_bulk_depreciation, calculate_block_depreciation
from utils.date_utils import financial_year_bounds, parse_date, days_between
from utils.validation import ValidationError, require
from utils.formatting import to_decimal

HALF_YEAR_THRESHOLD_DAYS = 180


def load_eligible_assets(conn, financial_year, category_id=None, department=None, location=None,
                          asset_ids=None):
    rows = asset_repository.list_assets(conn, status="ACTIVE", category_id=category_id)
    eligible = []
    for row in rows:
        if department and row["department"] != department:
            continue
        if location and row["location"] != location:
            continue
        if asset_ids and row["asset_id"] not in asset_ids:
            continue
        if row["is_depreciable"] != 1:
            continue
        eligible.append(dict(row))
    return eligible


def _asset_with_opening_ca(conn, asset_row):
    asset = dict(asset_row)
    history = dep_repo.get_history_for_asset(conn, asset["asset_id"])
    posted = [h for h in history if h["run_status"] == "POSTED"]
    if posted:
        latest = posted[-1]
        asset["opening_carrying_amount"] = latest["closing_carrying_amount"]
        asset["opening_accum_dep"] = to_decimal(asset["original_cost"]) - to_decimal(latest["closing_carrying_amount"])
    else:
        asset["opening_carrying_amount"] = asset["opening_wdv"]
        asset["opening_accum_dep"] = asset.get("opening_accum_dep") or 0
    return asset


def validate_depreciation_run(conn, assets, financial_year):
    valid, exceptions = [], []
    for asset in assets:
        dup = dep_repo.existing_posted_run_for_asset(conn, asset["asset_id"], financial_year)
        if dup:
            exceptions.append({"asset_id": asset["asset_id"],
                                "reason": f"Companies Act depreciation already posted for {financial_year}."})
        else:
            valid.append(asset)
    return valid, exceptions


def calculate_depreciation_run(conn, assets, period_start, period_end, basis, financial_year):
    start, end = financial_year_bounds(financial_year)
    year_days = (end - start).days + 1
    prepared = [_asset_with_opening_ca(conn, a) for a in assets]
    asset_results = run_bulk_depreciation(prepared, period_start, period_end, basis, year_days)
    block_results = _calculate_block_results(conn, prepared, asset_results, period_start, period_end,
                                              financial_year)
    return {"asset_results": asset_results, "block_results": block_results}


def _calculate_block_results(conn, assets, asset_results, period_start, period_end, financial_year):
    deferred_tax_rate = settings_repository.get_current_deferred_tax_rate(conn)
    p_start = parse_date(period_start)
    p_end = parse_date(period_end)

    closing_ca_by_asset = {r["asset_id"]: to_decimal(r["closing_carrying_amount"])
                           for r in asset_results if r["status"] == "OK"}

    blocks = {}
    for asset in assets:
        block_id = asset.get("income_tax_block_id")
        if not block_id:
            continue
        blocks.setdefault(block_id, {"assets": [], "additions_full": to_decimal(0),
                                      "additions_half": to_decimal(0), "closing_ca_total": to_decimal(0),
                                      "disposals": to_decimal(0)})
        b = blocks[block_id]
        b["assets"].append(asset["asset_id"])
        b["closing_ca_total"] += closing_ca_by_asset.get(asset["asset_id"], to_decimal(0))

        put_to_use = parse_date(asset["date_put_to_use"])
        if p_start <= put_to_use <= p_end:
            days_used = days_between(put_to_use, p_end)
            if days_used >= HALF_YEAR_THRESHOLD_DAYS:
                b["additions_full"] += to_decimal(asset["original_cost"])
            else:
                b["additions_half"] += to_decimal(asset["original_cost"])

    disposals = disposal_repository.get_disposals_in_period(conn, period_start, period_end)
    for d in disposals:
        block_id = d["income_tax_block_id"]
        if not block_id:
            continue
        blocks.setdefault(block_id, {"assets": [], "additions_full": to_decimal(0),
                                      "additions_half": to_decimal(0), "closing_ca_total": to_decimal(0),
                                      "disposals": to_decimal(0)})
        blocks[block_id]["disposals"] += to_decimal(d["sale_consideration"])

    block_results = []
    for block_id, agg in blocks.items():
        block_row = conn.execute("SELECT * FROM tax_blocks WHERE block_id=?", (block_id,)).fetchone()
        if block_row is None:
            continue
        rate = _applicable_block_rate(conn, block_id, p_end)
        latest = dep_repo.get_latest_posted_block_record(conn, block_id)
        opening_wdv = latest["closing_wdv"] if latest else _initial_block_opening(conn, block_id)

        block = {"block_id": block_id, "block_code": block_row["block_code"], "rate": rate,
                 "opening_wdv": opening_wdv}
        result = calculate_block_depreciation(
            block, agg["additions_full"], agg["additions_half"], agg["disposals"],
            deferred_tax_rate, agg["closing_ca_total"])
        result["asset_ids"] = agg["assets"]
        block_results.append(result)
    return block_results


def _applicable_block_rate(conn, block_id, as_of_date):
    row = conn.execute(
        """SELECT default_rate FROM tax_blocks WHERE block_id=? AND active=1
           AND (applicable_from IS NULL OR applicable_from <= ?)
           AND (applicable_to IS NULL OR applicable_to >= ?)""",
        (block_id, as_of_date.isoformat(), as_of_date.isoformat()),
    ).fetchone()
    if row is None:
        row = conn.execute("SELECT default_rate FROM tax_blocks WHERE block_id=?", (block_id,)).fetchone()
    return float(row["default_rate"]) if row else 0.0


def _initial_block_opening(conn, block_id):
    rows = conn.execute(
        "SELECT opening_tax_wdv FROM assets WHERE income_tax_block_id=? AND opening_tax_wdv IS NOT NULL",
        (block_id,),
    ).fetchall()
    return sum((to_decimal(r["opening_tax_wdv"]) for r in rows), to_decimal(0))


def create_depreciation_run(conn, financial_year, period_start, period_end, basis):
    run_id = dep_repo.generate_next_run_id(conn)
    dep_repo.create_run(conn, run_id, financial_year, period_start, period_end, basis)
    return run_id


def post_depreciation_run(conn, run_id, calc_output, financial_year, period_start, period_end):
    asset_results = calc_output["asset_results"]
    block_results = calc_output["block_results"]
    successful_assets = [r for r in asset_results if r["status"] == "OK"]
    if not successful_assets:
        raise ValidationError("No eligible assets were successfully calculated. Run not posted.")

    try:
        for r in successful_assets:
            record = {
                "run_id": run_id, "asset_id": r["asset_id"], "financial_year": financial_year,
                "period_start": period_start, "period_end": period_end,
                "opening_carrying_amount": str(r["opening_carrying_amount"]),
                "companies_act_method": r["companies_act_method"],
                "companies_act_depreciation": str(r["companies_act_depreciation"]),
                "closing_carrying_amount": str(r["closing_carrying_amount"]),
                "status": "POSTED",
            }
            dep_repo.insert_record(conn, record)

        for br in block_results:
            block_record = {
                "run_id": run_id, "block_id": br["block_id"], "financial_year": financial_year,
                "period_start": period_start, "period_end": period_end,
                "opening_wdv": str(br["opening_wdv"]), "additions_full_rate": str(br["additions_full_rate"]),
                "additions_half_rate": str(br["additions_half_rate"]), "disposals": str(br["disposals"]),
                "wdv_before_depreciation": str(br["wdv_before_depreciation"]), "tax_rate": br["tax_rate"],
                "depreciation": str(br["depreciation"]), "closing_wdv": str(br["closing_wdv"]),
                "short_term_capital_gain": str(br["short_term_capital_gain"]),
                "closing_carrying_amount_total": str(br["closing_carrying_amount_total"]),
                "temporary_difference": str(br["temporary_difference"]),
                "deferred_tax_rate": br["deferred_tax_rate"], "deferred_tax": str(br["deferred_tax"]),
                "deferred_tax_type": br["deferred_tax_type"], "status": "POSTED",
            }
            dep_repo.insert_block_record(conn, block_record)

        totals = {
            "total_assets": len(successful_assets),
            "total_ca_dep": str(sum(to_decimal(r["companies_act_depreciation"]) for r in successful_assets)),
            "total_it_dep": str(sum(to_decimal(br["depreciation"]) for br in block_results)),
            "total_deferred_tax": str(sum(to_decimal(br["deferred_tax"]) for br in block_results)),
        }
        dep_repo.update_run_status(conn, run_id, "POSTED", totals)
        settings_repository.log_audit(conn, "Depreciation Run Posted", "depreciation_runs", run_id,
                                       "", f"{len(successful_assets)} assets, {len(block_results)} blocks")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return totals


def reverse_depreciation_run(conn, run_id):
    run = dep_repo.get_run(conn, run_id)
    require(run is not None, "Depreciation run not found.")
    require(run["status"] == "POSTED", "Only posted runs can be reversed.")

    reversal_run_id = dep_repo.generate_next_run_id(conn)
    dep_repo.create_run(conn, reversal_run_id, run["financial_year"], run["period_start"],
                         run["period_end"], run["calculation_basis"])
    records = dep_repo.get_records_for_run(conn, run_id)
    block_records = dep_repo.get_block_records_for_run(conn, run_id)
    try:
        for rec in records:
            reversed_record = {
                "run_id": reversal_run_id, "asset_id": rec["asset_id"],
                "financial_year": rec["financial_year"], "period_start": rec["period_start"],
                "period_end": rec["period_end"], "opening_carrying_amount": rec["closing_carrying_amount"],
                "companies_act_method": rec["companies_act_method"],
                "companies_act_depreciation": str(-to_decimal(rec["companies_act_depreciation"])),
                "closing_carrying_amount": rec["opening_carrying_amount"], "status": "REVERSAL",
            }
            dep_repo.insert_record(conn, reversed_record)
        for brec in block_records:
            reversed_block = {
                "run_id": reversal_run_id, "block_id": brec["block_id"],
                "financial_year": brec["financial_year"], "period_start": brec["period_start"],
                "period_end": brec["period_end"], "opening_wdv": brec["closing_wdv"],
                "additions_full_rate": "0", "additions_half_rate": "0", "disposals": "0",
                "wdv_before_depreciation": brec["closing_wdv"], "tax_rate": brec["tax_rate"],
                "depreciation": str(-to_decimal(brec["depreciation"])),
                "closing_wdv": brec["opening_wdv"], "short_term_capital_gain": "0",
                "closing_carrying_amount_total": brec["closing_carrying_amount_total"],
                "temporary_difference": str(-to_decimal(brec["temporary_difference"])),
                "deferred_tax_rate": brec["deferred_tax_rate"],
                "deferred_tax": str(-to_decimal(brec["deferred_tax"])),
                "deferred_tax_type": brec["deferred_tax_type"], "status": "REVERSAL",
            }
            dep_repo.insert_block_record(conn, reversed_block)

        dep_repo.update_run_status(conn, reversal_run_id, "POSTED",
                                    {"total_assets": len(records), "total_ca_dep": 0,
                                     "total_it_dep": 0, "total_deferred_tax": 0})
        dep_repo.update_run_status(conn, run_id, "REVERSED", reversed_run_id=reversal_run_id)
        settings_repository.log_audit(conn, "Depreciation Run Reversed", "depreciation_runs", run_id,
                                       "POSTED", "REVERSED")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return reversal_run_id