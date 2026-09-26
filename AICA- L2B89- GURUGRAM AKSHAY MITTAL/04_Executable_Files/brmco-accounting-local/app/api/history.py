"""/api/history and /api/audit — import history and audit log."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from app.container import Container, get_container
from app.services.errors import NotFound

router = APIRouter(tags=["history"])


@router.get("/history", summary="Search import history")
def search(q: str = "", kind: str = "", status: str = "", date_from: str = "", date_to: str = "",
           c: Container = Depends(get_container)) -> dict:
    rows = c.history.search(q=q, kind=kind, status=status, date_from=date_from, date_to=date_to)
    for r in rows:
        r.pop("error_details", None)
    return {"items": rows}


@router.get("/history/{history_id}", summary="One import with per-voucher results")
def detail(history_id: int, c: Container = Depends(get_container)) -> dict:
    row = c.history.get(history_id)
    if not row:
        raise NotFound("History entry not found.")
    row["results"] = json.loads(row.pop("error_details") or "[]")
    return row


@router.get("/audit", summary="Audit log")
def audit(q: str = "", action: str = "", c: Container = Depends(get_container)) -> dict:
    return {"items": c.audit_repo.search(q=q, action=action)}
