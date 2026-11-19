"""Link posted vouchers back to the original invoice document."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Invoice, Posting


def find_document(session: Session, company_id: str, masterid: str = "", reference: str = "",
                  date: str = "") -> str:
    """Path of the source document of a voucher, or '' if the app didn't post it / the file is gone.
    1) the Posting row that created this voucher (Tally voucher id)  2) same supplier invoice number."""
    if masterid:
        p = session.scalar(select(Posting).where(Posting.company_id == company_id, Posting.ok.is_(True),
                                                 Posting.tally_master_id == str(masterid),
                                                 Posting.invoice_id.is_not(None)))
        if p:
            inv = session.get(Invoice, p.invoice_id)
            if inv and Path(inv.file_path).exists():
                return inv.file_path
    if reference:
        for inv in session.scalars(select(Invoice).where(Invoice.company_id == company_id,
                                                         Invoice.status == "posted")):
            ex = inv.extraction or {}
            if str(ex.get("invoice_no", "")).strip().lower() == reference.strip().lower() and \
                    (not date or not ex.get("invoice_date") or abs(int(ex["invoice_date"][:6]) - int(date[:6])) <= 1):
                if Path(inv.file_path).exists():
                    return inv.file_path
    return ""
