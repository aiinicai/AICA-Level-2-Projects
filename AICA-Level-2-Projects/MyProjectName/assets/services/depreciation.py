"""
Dual depreciation engine (blueprint §01, §05).

Two independent, parallel calculations run over the same Asset master:

* Schedule II (books) — SLM or WDV by asset class, useful life in years,
  residual value capped at 5% of original cost, mid-year addition/deletion
  proration by days in service, component-wise (a component asset simply
  depreciates on its own row, same as any other asset — its parent_asset
  link is what makes it "component accounting" for reporting purposes).

* Income Tax Act — block/WDV basis at rates that differ from Schedule II,
  with the half-year-rate convention for assets used for fewer than 180
  days in the tax year, kept for deferred-tax reconciliation.

Each call to run_schedule_ii() / run_income_tax() creates one frozen
DepreciationRun plus one entry per asset; the unique_together constraint on
(run) x (asset) means a period can be safely re-run only by deleting the
prior run first — entries are never edited in place, only ever superseded,
which is what makes them defensible as a "frozen, re-creatable snapshot"
under audit (blueprint §08).
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from assets.models import (
    Asset,
    AssetClass,
    BookDepreciationEntry,
    DepreciationRun,
    TaxDepreciationEntry,
)

TWO_PLACES = Decimal("0.01")


def _q(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _overlap_days(period_start, period_end, asset_start, asset_end):
    """Days the asset was in service within [period_start, period_end]."""
    start = max(period_start, asset_start)
    end = min(period_end, asset_end) if asset_end else period_end
    if end < start:
        return 0
    return (end - start).days + 1


def _asset_end_date(asset):
    """Last day the asset was in service, for depreciation purposes."""
    disposal = asset.disposal_requests.filter(status="APPROVED").order_by("-approved_at").first()
    if disposal:
        return disposal.requested_disposal_date
    return None


@transaction.atomic
def run_schedule_ii(entity, period_start, period_end, run_by, notes=""):
    """
    Post one Schedule II books depreciation run for `entity` covering
    [period_start, period_end] (inclusive). Returns the DepreciationRun.
    """
    run = DepreciationRun.objects.create(
        entity=entity,
        book=DepreciationRun.Book.SCHEDULE_II,
        period_start=period_start,
        period_end=period_end,
        run_by=run_by,
        notes=notes,
    )
    period_days = (period_end - period_start).days + 1
    assets = Asset.objects.filter(entity=entity, put_to_use_date__lte=period_end).select_related("asset_class")

    entries = []
    for asset in assets:
        asset_end = _asset_end_date(asset)
        days_used = _overlap_days(period_start, period_end, asset.put_to_use_date, asset_end)
        if days_used <= 0:
            continue

        prior_dep = (
            BookDepreciationEntry.objects.filter(asset=asset, run__period_end__lt=period_start)
            .order_by("-run__period_end")
            .first()
        )
        opening_wdv = prior_dep.closing_wdv if prior_dep else asset.gross_block()
        residual = asset.residual_value()

        if opening_wdv <= residual:
            depreciation_amount = Decimal("0")
        elif asset.depreciation_method == AssetClass.Method.SLM:
            depreciable_amount = asset.gross_block() - residual
            annual = depreciable_amount / Decimal(asset.useful_life_years) if asset.useful_life_years else Decimal("0")
            depreciation_amount = annual * Decimal(days_used) / Decimal(365)
        else:  # WDV
            life = Decimal(asset.useful_life_years) if asset.useful_life_years else Decimal("1")
            cost_ratio = (residual / asset.gross_block()) if asset.gross_block() else Decimal("0")
            if cost_ratio > 0:
                # rate = 1 - (residual/cost) ** (1/life), evaluated via logs is overkill here;
                # Schedule II WDV rate tables are conventionally looked up, but we derive it
                # algebraically so any useful-life/residual combination works out of the box.
                rate = Decimal("1") - cost_ratio ** (Decimal("1") / life)
            else:
                rate = Decimal("1") / life
            annual = opening_wdv * rate
            depreciation_amount = annual * Decimal(days_used) / Decimal(period_days if period_days else 365)

        depreciation_amount = _q(min(depreciation_amount, opening_wdv - residual))
        depreciation_amount = max(depreciation_amount, Decimal("0"))
        closing_wdv = _q(opening_wdv - depreciation_amount)

        entries.append(
            BookDepreciationEntry(
                run=run,
                asset=asset,
                opening_wdv=_q(opening_wdv),
                depreciable_amount=_q(asset.gross_block() - residual),
                depreciation_amount=depreciation_amount,
                closing_wdv=closing_wdv,
                days_in_period=period_days,
                days_used=days_used,
                method=asset.depreciation_method,
            )
        )

    BookDepreciationEntry.objects.bulk_create(entries)
    return run


@transaction.atomic
def run_income_tax(entity, period_start, period_end, run_by, notes=""):
    """
    Post one Income Tax Act (block/WDV) depreciation run. Applies the
    half-year-rate convention: an asset first used for fewer than 180 days
    within the tax year gets half its normal WDV rate for that year.
    """
    run = DepreciationRun.objects.create(
        entity=entity,
        book=DepreciationRun.Book.INCOME_TAX,
        period_start=period_start,
        period_end=period_end,
        run_by=run_by,
        notes=notes,
    )
    assets = Asset.objects.filter(
        entity=entity, put_to_use_date__lte=period_end, tax_wdv_rate_pct__isnull=False
    )

    entries = []
    for asset in assets:
        asset_end = _asset_end_date(asset)
        days_used = _overlap_days(period_start, period_end, asset.put_to_use_date, asset_end)
        if days_used <= 0:
            continue

        prior = (
            TaxDepreciationEntry.objects.filter(asset=asset, run__period_end__lt=period_start)
            .order_by("-run__period_end")
            .first()
        )
        opening_wdv = prior.closing_wdv if prior else asset.capitalised_cost
        additions = Decimal("0") if prior else asset.capitalised_cost

        is_first_year = prior is None
        days_in_fy_before_period_end = (period_end - asset.put_to_use_date).days + 1
        is_half_rate = is_first_year and days_in_fy_before_period_end < 180

        rate = asset.tax_wdv_rate_pct / Decimal("100")
        if is_half_rate:
            rate = rate / Decimal("2")

        base = opening_wdv if not is_first_year else additions
        depreciation_amount = _q(base * rate)
        depreciation_amount = max(min(depreciation_amount, base), Decimal("0"))
        closing_wdv = _q((opening_wdv if not is_first_year else additions) - depreciation_amount)

        entries.append(
            TaxDepreciationEntry(
                run=run,
                asset=asset,
                tax_block_code=asset.tax_block_code,
                opening_wdv=_q(opening_wdv if not is_first_year else Decimal("0")),
                additions=_q(additions),
                rate_pct=asset.tax_wdv_rate_pct,
                is_half_rate=is_half_rate,
                depreciation_amount=depreciation_amount,
                closing_wdv=closing_wdv,
                period_end=period_end,
            )
        )

    TaxDepreciationEntry.objects.bulk_create(entries)
    return run
