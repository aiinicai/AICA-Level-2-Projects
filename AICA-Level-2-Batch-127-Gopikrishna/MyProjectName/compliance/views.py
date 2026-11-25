import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from locations.models import Entity

from .models import BenamiDeclaration, FinancialYear
from .services.reports import build_caro_evidence, build_ind_as16_rollforward, build_schedule_iii


def _get_entity_fy(request):
    entity = Entity.objects.first()
    entity_id = request.GET.get("entity")
    if entity_id:
        entity = get_object_or_404(Entity, pk=entity_id)
    fy = FinancialYear.objects.filter(entity=entity).order_by("-start_date").first()
    fy_id = request.GET.get("fy")
    if fy_id:
        fy = get_object_or_404(FinancialYear, pk=fy_id)
    return entity, fy


@login_required
def home(request):
    entities = Entity.objects.all()
    entity, fy = _get_entity_fy(request)
    fys = FinancialYear.objects.filter(entity=entity) if entity else FinancialYear.objects.none()
    return render(request, "compliance/home.html", {
        "entities": entities, "entity": entity, "fy": fy, "fys": fys,
    })


@login_required
def schedule_iii(request):
    entity, fy = _get_entity_fy(request)
    if not entity or not fy:
        messages.error(request, "Set up an Entity and Financial Year first (Django admin → Compliance).")
        return redirect("compliance:home")
    rows, totals = build_schedule_iii(entity, fy)

    if request.GET.get("format") == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Asset class", "Opening gross block", "Additions", "Disposals (gross)", "Closing gross block",
                    "Opening acc. dep.", "Dep. charge for the year", "Dep. on disposals", "Closing acc. dep.", "Net block"])
        for r in rows:
            w.writerow([r["asset_class"].name, r["opening_gross"], r["additions"], r["disposals_gross"],
                        r["closing_gross"], r["opening_dep"], r["dep_charge"], r["dep_on_disposals"],
                        r["closing_dep"], r["closing_net"]])
        w.writerow(["TOTAL", totals["opening_gross"], totals["additions"], totals["disposals_gross"],
                    totals["closing_gross"], totals["opening_dep"], totals["dep_charge"], totals["dep_on_disposals"],
                    totals["closing_dep"], totals["closing_net"]])
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="schedule_iii_{fy.label}.csv"'
        return resp

    return render(request, "compliance/schedule_iii.html", {"entity": entity, "fy": fy, "rows": rows, "totals": totals})


@login_required
def ind_as_16(request):
    entity, fy = _get_entity_fy(request)
    if not entity or not fy:
        messages.error(request, "Set up an Entity and Financial Year first.")
        return redirect("compliance:home")
    rows, totals = build_ind_as16_rollforward(entity, fy)

    if request.GET.get("format") == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Asset class", "Opening gross block", "Additions", "Disposals", "Revaluation surplus",
                    "Closing gross block", "Opening acc. dep.", "Dep. charge", "Impairment loss", "Closing acc. dep.", "Net block"])
        for r in rows:
            w.writerow([r["asset_class"].name, r["opening_gross"], r["additions"], r["disposals_gross"],
                        r["revaluation_surplus"], r["closing_gross"], r["opening_dep"], r["dep_charge"],
                        r["impairment_loss"], r["closing_dep"], r["closing_net"]])
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="ind_as16_rollforward_{fy.label}.csv"'
        return resp

    return render(request, "compliance/ind_as_16.html", {"entity": entity, "fy": fy, "rows": rows, "totals": totals})


@login_required
def caro_pack(request):
    entity, fy = _get_entity_fy(request)
    if not entity:
        messages.error(request, "Set up an Entity first.")
        return redirect("compliance:home")
    data = build_caro_evidence(entity)
    benami = BenamiDeclaration.objects.filter(entity=entity, financial_year=fy).first() if fy else None
    return render(request, "compliance/caro_pack.html", {"entity": entity, "fy": fy, "data": data, "benami": benami})


@login_required
def verification_papers(request):
    entity, fy = _get_entity_fy(request)
    from verification.models import PhysicalVerificationRecord
    records = PhysicalVerificationRecord.objects.filter(asset__entity=entity).select_related(
        "asset", "verified_by", "cycle"
    ).order_by("-verified_date")

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Cycle", "Asset ID", "Description", "Verified by", "Date", "Condition", "Discrepancy notes", "Resolved"])
    for r in records:
        w.writerow([r.cycle.name, r.asset.asset_id, r.asset.description, r.verified_by, r.verified_date,
                    r.get_condition_display(), r.discrepancy_notes, "Yes" if r.discrepancy_resolved else "No"])
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="physical_verification_working_papers.csv"'
    return resp


@login_required
def xbrl_export(request):
    """
    XBRL-ready export (blueprint §07): a structured CSV carrying the PP&E
    note fields AOC-4's PP&E schedule expects, ready to hand to XBRL
    tagging software. This is a data-readiness export, not a signed XBRL
    instance document — that step still runs through the company's XBRL
    filing tool/agent.
    """
    entity, fy = _get_entity_fy(request)
    if not entity or not fy:
        messages.error(request, "Set up an Entity and Financial Year first.")
        return redirect("compliance:home")
    rows, totals = build_schedule_iii(entity, fy)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["XBRLTag", "AssetClass", "Value"])
    tag_map = [
        ("GrossCarryingAmountAtStartOfPeriod", "opening_gross"),
        ("AdditionsPropertyPlantEquipment", "additions"),
        ("DisposalsPropertyPlantEquipment", "disposals_gross"),
        ("GrossCarryingAmountAtEndOfPeriod", "closing_gross"),
        ("AccumulatedDepreciationAtStartOfPeriod", "opening_dep"),
        ("DepreciationChargeForPeriod", "dep_charge"),
        ("AccumulatedDepreciationAtEndOfPeriod", "closing_dep"),
        ("NetCarryingAmount", "closing_net"),
    ]
    for r in rows:
        for tag, key in tag_map:
            w.writerow([tag, r["asset_class"].name, r[key]])
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="xbrl_ready_ppe_{fy.label}.csv"'
    return resp


@login_required
def benami_declare(request):
    entity, fy = _get_entity_fy(request)
    if request.method == "POST" and entity and fy:
        BenamiDeclaration.objects.update_or_create(
            entity=entity, financial_year=fy,
            defaults={
                "proceedings_exist": request.POST.get("proceedings_exist") == "on",
                "details": request.POST.get("details", ""),
                "declared_by": request.user,
            },
        )
        messages.success(request, "Benami declaration recorded (CARO 3(i)(e)).")
    return redirect("compliance:caro_pack")
