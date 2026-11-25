"""
Compliance report builders (blueprint §07). These produce the numbers for
the Schedule III PP&E note and the Ind AS 16 para 73(e) roll-forward
directly from posted DepreciationRun snapshots and the asset master —
never from a parallel spreadsheet — so the numbers tie back to what's
actually in the register.

Simplifications worth knowing about before relying on this for an actual
filing (documented here rather than hidden): accumulated depreciation "as
of" a date is read off the closing_wdv of the latest posted
BookDepreciationEntry at or before that date, so a report date that falls
between depreciation runs will look stale until the next run is posted;
component accounting nets up to the parent's asset_class bucket only when
a component's own asset_class is set — a company running strict
component-level Ind AS 16 notes should extend this to bucket by component
rather than by parent asset_class.
"""

from decimal import Decimal

from assets.models import Asset, AssetClass, BookDepreciationEntry
from disposal.models import DisposalRequest


def _accumulated_dep_as_of(asset, as_of_date):
    entry = (
        BookDepreciationEntry.objects.filter(asset=asset, run__period_end__lte=as_of_date)
        .order_by("-run__period_end")
        .first()
    )
    if not entry:
        return Decimal("0")
    return asset.gross_block() - entry.closing_wdv


def build_schedule_iii(entity, fy):
    """Gross block / additions / disposals / accumulated depreciation / net block, by asset class."""
    classes = AssetClass.objects.filter(assets__entity=entity).distinct()
    rows = []
    totals = {k: Decimal("0") for k in ("opening_gross", "additions", "disposals_gross", "closing_gross", "opening_dep", "dep_charge", "dep_on_disposals", "closing_dep", "closing_net")}

    for ac in classes:
        assets = Asset.objects.filter(entity=entity, asset_class=ac)
        opening_gross = Decimal("0")
        additions = Decimal("0")
        disposals_gross = Decimal("0")
        opening_dep = Decimal("0")
        closing_dep = Decimal("0")
        dep_on_disposals = Decimal("0")

        for a in assets:
            gb = a.gross_block()
            if a.put_to_use_date < fy.start_date:
                opening_gross += gb
                opening_dep += _accumulated_dep_as_of(a, fy.start_date - __import__("datetime").timedelta(days=1))
            elif fy.start_date <= a.put_to_use_date <= fy.end_date:
                additions += gb

            disposal = a.disposal_requests.filter(
                status=DisposalRequest.Status.APPROVED,
                requested_disposal_date__gte=fy.start_date, requested_disposal_date__lte=fy.end_date,
            ).first()
            if disposal:
                disposals_gross += gb
                dep_on_disposals += _accumulated_dep_as_of(a, disposal.requested_disposal_date)
            elif a.life_status != Asset.LifeStatus.DISPOSED or a.put_to_use_date > fy.end_date:
                closing_dep += _accumulated_dep_as_of(a, fy.end_date)

        closing_gross = opening_gross + additions - disposals_gross
        dep_charge = closing_dep + dep_on_disposals - opening_dep
        closing_net = closing_gross - closing_dep

        rows.append({
            "asset_class": ac, "opening_gross": opening_gross, "additions": additions,
            "disposals_gross": disposals_gross, "closing_gross": closing_gross,
            "opening_dep": opening_dep, "dep_charge": dep_charge, "dep_on_disposals": dep_on_disposals,
            "closing_dep": closing_dep, "closing_net": closing_net,
        })
        for k in totals:
            totals[k] += rows[-1][k]

    return rows, totals


def build_ind_as16_rollforward(entity, fy):
    """Same base numbers as Schedule III, plus revaluation and impairment movement (Ind AS 16 para 73(e))."""
    rows, totals = build_schedule_iii(entity, fy)
    from assets.models import RevaluationRecord, ImpairmentCheck

    for row in rows:
        ac = row["asset_class"]
        reval = RevaluationRecord.objects.filter(
            asset__entity=entity, asset__asset_class=ac, approved_by__isnull=False,
            valuation_date__gte=fy.start_date, valuation_date__lte=fy.end_date,
        )
        row["revaluation_surplus"] = sum((r.surplus_or_deficit for r in reval), Decimal("0"))
        impair = ImpairmentCheck.objects.filter(
            asset__entity=entity, asset__asset_class=ac,
            check_date__gte=fy.start_date, check_date__lte=fy.end_date,
        )
        row["impairment_loss"] = sum((i.impairment_loss for i in impair), Decimal("0"))
    totals["revaluation_surplus"] = sum((r["revaluation_surplus"] for r in rows), Decimal("0"))
    totals["impairment_loss"] = sum((r["impairment_loss"] for r in rows), Decimal("0"))
    return rows, totals


def build_caro_evidence(entity):
    """Records-completeness %, verification coverage %, title-deed status, revaluation register (CARO 3(i))."""
    from verification.models import VerificationCycle
    assets = Asset.objects.filter(entity=entity)
    total = assets.count()
    complete_fields = assets.exclude(serial_number="").exclude(location__isnull=True).count()
    records_completeness_pct = round(complete_fields / total * 100, 1) if total else 0

    verified = [a for a in assets if a.last_verified_date]
    verification_coverage_pct = round(len(verified) / total * 100, 1) if total else 0

    immovable = assets.filter(is_immovable_property=True)
    title_deed_issues = immovable.exclude(title_deed_in_company_name=True)

    from assets.models import RevaluationRecord
    revaluations = RevaluationRecord.objects.filter(asset__entity=entity, approved_by__isnull=False)

    cycles = VerificationCycle.objects.filter(entity=entity)

    return {
        "total_assets": total,
        "records_completeness_pct": records_completeness_pct,
        "verification_coverage_pct": verification_coverage_pct,
        "immovable_count": immovable.count(),
        "title_deed_issues": title_deed_issues,
        "revaluations": revaluations,
        "cycles": cycles,
    }
