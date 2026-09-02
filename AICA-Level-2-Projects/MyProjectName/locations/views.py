from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from assets.models import Asset

from .models import Entity, Location


def _node_summary(node):
    ids = node.descendant_ids()
    qs = Asset.objects.filter(location_id__in=ids)
    count = qs.count()
    value = sum((a.net_book_value() for a in qs), start=0)
    return count, value


@login_required
def tree_view(request):
    entities = Entity.objects.prefetch_related("locations")
    roots = Location.objects.filter(parent__isnull=True).select_related("entity")
    rows = []
    for root in roots:
        rows.append(_build_row(root, depth=0))
    return render(request, "locations/tree.html", {"rows": rows, "entities": entities})


def _build_row(node, depth):
    count, value = _node_summary(node)
    row = {"node": node, "depth": depth, "count": count, "value": value}
    children = [_build_row(child, depth + 1) for child in node.children.all().order_by("name")]
    return {"row": row, "children": children}


@login_required
def node_detail(request, pk):
    node = get_object_or_404(Location, pk=pk)
    ids = node.descendant_ids()
    assets = Asset.objects.filter(location_id__in=ids).select_related("asset_class", "custodian")
    children = node.children.all().order_by("name")
    return render(
        request, "locations/node_detail.html",
        {"node": node, "assets": assets, "children": children},
    )


@login_required
def locator(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        results = Asset.objects.filter(
            models_q_search(query)
        ).select_related("location", "asset_class")[:50]
    return render(request, "locations/locator.html", {"query": query, "results": results})


def models_q_search(query):
    from django.db.models import Q
    return (
        Q(asset_id__icontains=query)
        | Q(description__icontains=query)
        | Q(serial_number__icontains=query)
        | Q(location__name__icontains=query)
        | Q(location__code__icontains=query)
    )
