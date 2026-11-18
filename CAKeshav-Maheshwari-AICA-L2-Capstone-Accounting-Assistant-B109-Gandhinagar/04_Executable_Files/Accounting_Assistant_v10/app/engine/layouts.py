"""DB side of the supplier layout memory (see extract/layout.py)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import SupplierLayout
from ..extract import layout as layout_mod


def learn(session: Session, company_id: str, vendor_key: str, inv, text: str, offline_ok: bool = False) -> None:
    if not vendor_key or not text.strip():
        return
    found = layout_mod.learn_fields(inv, text)
    if not found:
        return
    row = session.scalar(select(SupplierLayout).where(SupplierLayout.company_id == company_id,
                                                      SupplierLayout.vendor_key == vendor_key))
    if row is None:
        row = SupplierLayout(company_id=company_id, vendor_key=vendor_key, fields={}, samples=0, successes=0)
        session.add(row)
    row.fields = layout_mod.merge(row.fields, found)
    row.samples = (row.samples or 0) + 1
    if offline_ok:
        row.successes = (row.successes or 0) + 1
    session.commit()


def load_all(session: Session, company_id: str) -> dict:
    return {r.vendor_key: r.fields for r in session.scalars(
        select(SupplierLayout).where(SupplierLayout.company_id == company_id)) if r.fields}


def offline_ready(session: Session, company_id: str) -> dict[str, tuple[int, int]]:
    """vendor_key -> (samples, offline successes)."""
    return {r.vendor_key: (r.samples or 0, r.successes or 0) for r in session.scalars(
        select(SupplierLayout).where(SupplierLayout.company_id == company_id))}
