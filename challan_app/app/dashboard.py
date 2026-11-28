from collections import Counter, OrderedDict
from datetime import date

from flask import Blueprint, render_template, request

from . import gst, services as sv
from .models import CANCELLED, FINAL, Challan, Plant, Vendor

bp = Blueprint("dashboard", __name__)


def _months(d1, d2):
    y, m = d1.year, d1.month
    while (y, m) <= (d2.year, d2.month):
        yield (y, m)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


@bp.route("/")
def index():
    a = request.args
    today = date.today()
    fy_start, _ = gst.fy_range(gst.fy_of(today))
    d1, d2 = sv._date(a.get("from")) or fy_start, sv._date(a.get("to")) or today
    q = Challan.query.filter(Challan.status.in_([FINAL, CANCELLED]), Challan.challan_date >= d1, Challan.challan_date <= d2)
    if a.get("ctype") in ("MRC", "MNRC"):
        q = q.filter(Challan.ctype == a["ctype"])
    if a.get("plant", "").isdigit():
        q = q.filter(Challan.plant_id == int(a["plant"]))
    rows = q.all()
    live = [c for c in rows if c.status == FINAL]

    trend = OrderedDict(((y, m), {"MRC": 0, "MNRC": 0}) for y, m in _months(d1, d2))
    for c in live:
        trend[(c.challan_date.year, c.challan_date.month)][c.ctype] += 1
    peak = max([sum(v.values()) for v in trend.values()] + [1])
    bars = [{"label": date(y, m, 1).strftime("%b %y"), "mrc": v["MRC"], "mnrc": v["MNRC"], "total": v["MRC"] + v["MNRC"],
             "h_mrc": v["MRC"] / peak * 100, "h_mnrc": v["MNRC"] / peak * 100} for (y, m), v in trend.items()]

    purpose = Counter(c.purpose for c in live).most_common()
    mrc = [c for c in live if c.ctype == "MRC"]
    by_vendor = Counter(c.vendor_id for c in live).most_common(10)
    vend = {v.id: v for v in Vendor.query.filter(Vendor.id.in_([i for i, _ in by_vendor] or [0]))}
    top_vendors = [(vend[i], n, sum(1 for c in live if c.vendor_id == i and c.ctype == "MRC")) for i, n in by_vendor]
    mrc_vendor_ids = Counter(c.vendor_id for c in mrc)
    not_in_erp = [(v, mrc_vendor_ids[v.id]) for v in Vendor.query.filter(Vendor.active.is_(True), Vendor.erp_code.is_(None))
                  .order_by(Vendor.name).all()]
    not_in_erp.sort(key=lambda t: -t[1])

    open_ret = Challan.query.filter(Challan.ctype == "MRC", Challan.status == FINAL, Challan.return_status != "Closed").all()
    pending_ewb = Challan.query.filter_by(status=FINAL, ewb_status="Pending").count()

    return render_template(
        "dashboard.html", a=a, d1=d1, d2=d2, plants=Plant.query.order_by(Plant.code).all(), bars=bars,
        n_total=len(live), n_mrc=len(mrc), n_mnrc=len(live) - len(mrc), n_cancelled=len(rows) - len(live),
        purpose=purpose, pmax=max([n for _, n in purpose] + [1]), top_vendors=top_vendors,
        not_in_erp=not_in_erp[:10], n_not_in_erp=len(not_in_erp), pending_ewb=pending_ewb, open_ret=len(open_ret))
