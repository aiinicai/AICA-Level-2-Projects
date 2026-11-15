"""Maps an API path + query string to a report (the same URLs the screens call). Used by the API layer and by tests."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

from . import reports as R


def handle(store, url: str) -> tuple[int, object]:
    """GET `url` (e.g. '/api/c/1/pnl?from=2025-04-01') -> (http status, JSON-ready body)."""
    u = urlsplit(url)
    q = {k: v[0] for k, v in parse_qs(u.query).items()}
    m = re.fullmatch(r"/api/c/(\d+)/(.+)", u.path)
    if not m:
        return 404, {"error": "Not found"}
    cid, rest = int(m[1]), m[2]
    try:
        f = R.make_filters(store, cid, q.get("from"), q.get("to"), q.get("compare"), q.get("costCentre"))
        if rest == "dashboard":
            return 200, R.dashboard(f)
        if rest == "kpis":
            return 200, R.kpis_report(f, q["codes"].split(",") if q.get("codes") else None, q.get("trend") == "1")
        if rest == "pnl":
            return 200, R.pnl_report(f, q.get("view", "compare"))
        if rest == "pnl/revenue":
            return 200, R.pnl_revenue(f)
        if rest == "pnl/costs":
            return 200, R.pnl_costs(f)
        if rest == "bs":
            return 200, R.bs_report(f, q.get("asOf"))
        if rest == "bs/analysis":
            return 200, R.bs_analysis(f)
        if rest == "cashflow":
            return 200, R.cashflow_report(f)
        if rest == "products":
            return 200, R.pnl_products(f)
        if rest == "ageing":
            return 200, R.ageing_report(f, q.get("kind", "receivable"), q.get("asOf"), q.get("buckets"))
        if rest == "ledgers":
            return 200, R.ledgers_list(f, q.get("search", ""))
        if m2 := re.fullmatch(r"ledgers/(\d+)", rest):
            return 200, R.ledger_report(f, int(m2[1]), int(q.get("page", 1) or 1))
        if m2 := re.fullmatch(r"vouchers/(\d+)", rest):
            return 200, R.voucher_report(f, int(m2[1]))
    except R.ApiError as e:
        return e.status, {"error": e.message}
    return 404, {"error": "Not found"}
