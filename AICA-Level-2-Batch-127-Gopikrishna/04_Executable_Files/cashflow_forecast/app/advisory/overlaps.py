"""Advisory cross-checks over the CURRENT line items (pandas). They never change data; each finding
suggests an action the user can take on screen (exclude, flag as bill discounted, hold...).

Rules
1. PDC vs payment allocation: same vendor, same amount, dates within WINDOW days -> possibly paid twice.
2. Payment allocation vs bill discount / LC maturities: same amount within WINDOW days -> possible overlap.
3. Bill discount proceeds that name a customer invoice still open in collections and not flagged
   as bill discounted -> it would be counted twice.
4. Same source, different keys, same counterparty + amount + date -> possible duplicate.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.specs import normalise_header
from app.models import BatchStatus, ImportBatch, LineItem, Override, OverrideAction, SourceType

WINDOW = 7


@dataclass
class Finding:
    rule: str
    message: str
    keys: list[tuple[str, str]]      # (source_type, source_key) involved
    amount: str
    suggested_action: str


def current_items_frame(db: Session) -> pd.DataFrame:
    rows = db.execute(
        select(LineItem.source_type, LineItem.source_key, LineItem.counterparty, LineItem.reference,
               LineItem.planned_date, LineItem.amount, LineItem.direction, LineItem.linked_invoice,
               LineItem.bill_discounted_imported, LineItem.note)
        .join(ImportBatch, ImportBatch.id == LineItem.batch_id)
        .where(ImportBatch.status == BatchStatus.ACCEPTED, LineItem.category_id.is_not(None))).all()
    df = pd.DataFrame(rows, columns=["source", "key", "party", "ref", "date", "amount", "direction", "linked",
                                     "bd_flag", "note"])
    if df.empty:
        return df
    df["source"] = df["source"].map(lambda s: s.value)
    df["direction"] = df["direction"].map(lambda d: d.value)
    df["party_n"] = df["party"].map(normalise_header)
    df["date"] = pd.to_datetime(df["date"])
    df["amount_f"] = df["amount"].astype(str)   # exact comparison on the 3-dp text
    return df


def _pairs(a: pd.DataFrame, b: pd.DataFrame, on: list[str]) -> pd.DataFrame:
    if a.empty or b.empty:
        return pd.DataFrame()
    m = a.merge(b, on=on, suffixes=("_a", "_b"))
    if m.empty:
        return m
    return m[(m["date_a"] - m["date_b"]).abs().dt.days <= WINDOW]


def find_overlaps(db: Session) -> list[Finding]:
    df = current_items_frame(db)
    out: list[Finding] = []
    if df.empty:
        return out
    pdc, alloc = df[df.source == "vendor_pdc"], df[df.source == "allocation"]
    bd = df[df.source == "bill_discount"]
    bd_out, bd_in = bd[bd.direction == "outflow"], bd[bd.direction == "inflow"]

    for _, r in _pairs(pdc, alloc, ["party_n", "amount_f"]).iterrows():
        out.append(Finding(
            "pdc_vs_allocation",
            f"{r.party_a}: PDC cheque {r.ref_a} ({r.date_a:%d-%b}) and planned payment {r.ref_b} "
            f"({r.date_b:%d-%b}) are both {r.amount_a:,.3f}. It may be paid twice.",
            [("vendor_pdc", r.key_a), ("allocation", r.key_b)], f"{r.amount_a:.3f}",
            "Exclude the planned payment if the cheque covers it."))

    for _, r in _pairs(alloc, bd_out, ["amount_f"]).iterrows():
        out.append(Finding(
            "allocation_vs_bd",
            f"Planned payment {r.ref_a} to {r.party_a} and bank maturity {r.ref_b} are both {r.amount_a:,.3f} "
            f"within {WINDOW} days.", [("allocation", r.key_a), ("bill_discount", r.key_b)], f"{r.amount_a:.3f}",
            "Check whether the LC / discount already settles this invoice."))

    if not bd_in.empty:
        coll = df[df.source == "collections"]
        flagged = {o.source_key for o in db.scalars(select(Override).where(
            Override.is_active, Override.action == OverrideAction.BILL_DISCOUNTED,
            Override.source_type == SourceType.COLLECTIONS))}
        for _, b in bd_in[bd_in.linked != ""].iterrows():
            hit = coll[coll.ref.str.upper() == b.linked.upper()]
            for _, c in hit.iterrows():
                if c.bd_flag or c.key in flagged:
                    continue
                out.append(Finding(
                    "bill_discounted_invoice",
                    f"Invoice {c.ref} ({c.party}, {c.amount:,.3f}) was financed by {b.ref} but is still in "
                    "collections. It would be counted twice.", [("collections", c.key), ("bill_discount", b.key)],
                    f"{c.amount:.3f}", "Flag the invoice as bill discounted."))

    for src, g in df.groupby("source"):
        d = g[g.duplicated(["party_n", "amount_f", "date"], keep=False)]
        for _, grp in d.groupby(["party_n", "amount_f", "date"]):
            if len(grp) < 2:
                continue
            first = grp.iloc[0]
            out.append(Finding(
                "possible_duplicate",
                f"{len(grp)} {src} rows for {first.party} of {first.amount:,.3f} on {first.date:%d-%b-%Y} "
                f"(refs {', '.join(grp.ref)}).", [(src, k) for k in grp.key], f"{first.amount:.3f}",
                "Check with the ERP; exclude the extra row if it is a duplicate."))
    return out
