"""Create a ledger in Tally from the app and make it usable immediately (local cache + vendor link)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import AuditLog, Company, MasterCache, Vendor, utcnow
from ..tally.client import TallyClient


def create_ledger(session: Session, client: TallyClient, company: Company, name: str, parent: str, *,
                  gstin: str = "", pan: str = "", state: str = "", bill_wise: bool = False,
                  vendor_key: str = "", actor: str = "") -> None:
    name = name.strip()
    if not name or not parent:
        raise ValueError("Ledger name and group are required")
    exists = session.scalar(select(MasterCache).where(MasterCache.company_id == company.id,
                                                      MasterCache.kind == "ledger", MasterCache.name == name))
    if exists:
        raise ValueError(f"A ledger named '{name}' already exists in Tally")
    client.create_ledger(company.name, name=name, parent=parent, gstin=gstin, pan=pan or (gstin[2:12] if gstin else ""),
                         state=state, bill_wise=bill_wise)
    data = {"PARENT": parent, "PARTYGSTIN": gstin, "_gstin": gstin, "ISBILLWISEON": "Yes" if bill_wise else "No"}
    session.add(MasterCache(company_id=company.id, kind="ledger", name=name, parent=parent, data=data,
                            synced_at=utcnow()))
    if vendor_key:
        v = session.scalar(select(Vendor).where(Vendor.company_id == company.id, Vendor.vendor_key == vendor_key))
        if v is None:
            v = Vendor(company_id=company.id, vendor_key=vendor_key, gstin=gstin, pan=pan, names=[name])
            session.add(v)
        v.party_ledger = name
    session.add(AuditLog(company_id=company.id, action="ledger_created", entity="ledger", entity_id="",
                         after={"name": name, "parent": parent, "gstin": gstin}, updated_by=actor))
    session.commit()
