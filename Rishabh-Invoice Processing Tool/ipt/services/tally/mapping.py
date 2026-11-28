"""Master mapping: which Tally ledger / stock item / godown each part of an invoice goes to.

Suggestions come from (in order) a remembered rule, an exact GSTIN match, then
name similarity. Nothing is used for a voucher until the user approves it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from sqlalchemy import select

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.db.base import Database
from ipt.db.models import Invoice, MappingRule, TallyMaster
from ipt.services import audit_service

ENTITY_LABELS = {"party": "Supplier → party ledger", "stock_item": "Item → stock item",
                 "purchase_ledger": "Purchase ledger", "tax_ledger": "GST ledger", "round_off": "Round-off ledger",
                 "godown": "Godown", "charge_ledger": "Freight / other charges ledger",
                 "voucher_type": "Voucher type",
                 "debit_ledger": "Book this supplier to a ledger (no items)"}
# a supplier with an approved 'debit_ledger' is booked ledger-wise: Accounting Invoice, that ledger is debited
# with the taxable value and no stock items are needed (e.g. electrical repairs -> Repair & Maintenance)
NOTE_TYPES = ("credit_note", "debit_note")
EXPENSE_GROUPS = ("Indirect Expenses", "Direct Expenses", "Purchase Accounts", "Fixed Assets")


@dataclass
class Candidate:
    name: str
    score: int
    reason: str


@dataclass
class MappingLine:
    entity: str
    source_key: str
    source_label: str
    approved: str | None = None
    candidates: list[Candidate] = field(default_factory=list)

    @property
    def best(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None


def norm_desc(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _sim(a: str, b: str) -> int:
    a, b = norm_desc(a), norm_desc(b)
    if not a or not b:
        return 0
    ratio = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    overlap = len(ta & tb) / max(1, min(len(ta), len(tb)))
    return int(round(max(ratio, overlap * 0.95) * 100))


def is_intra(inv: Invoice) -> bool | None:
    sup = (inv.supplier_gstin or "")[:2] or inv.supplier_state_code
    if not sup or not inv.place_of_supply:
        return None
    return sup == inv.place_of_supply


class MappingService:
    def __init__(self, db: Database, ctx: AppContext):
        self.db, self.ctx = db, ctx

    # ------------------------------------------------------------------ data
    def _masters(self, s, mtype: str, primary: str | None = None) -> list[TallyMaster]:
        q = select(TallyMaster).where(TallyMaster.company_id == self.ctx.company_id, TallyMaster.master_type == mtype)
        if primary:
            q = q.where(TallyMaster.primary_group == primary)
        return list(s.scalars(q))

    def _rule(self, s, entity: str, key: str) -> MappingRule | None:
        return s.scalar(select(MappingRule).where(MappingRule.company_id == self.ctx.company_id,
                                                  MappingRule.entity == entity, MappingRule.source_key == key))

    def master_names(self, entity: str) -> list[str]:
        mtype, primary = {"party": ("ledger", None), "stock_item": ("stock_item", None),
                          "purchase_ledger": ("ledger", None), "tax_ledger": ("ledger", "Duties & Taxes"),
                          "round_off": ("ledger", None), "godown": ("godown", None),
                          "charge_ledger": ("ledger", None), "voucher_type": ("voucher_type", None),
                          "debit_ledger": ("ledger", None)}[entity]
        with self.db.session() as s:
            return sorted(m.name for m in self._masters(s, mtype, primary))

    # ------------------------------------------------------------------ suggestions
    def lines_for(self, invoice_id: int, mode: str = "inventory") -> list[MappingLine]:
        with self.db.session() as s:
            inv = s.get(Invoice, invoice_id)
            if inv is None or inv.company_id != self.ctx.company_id:
                return []
            items = list(inv.items)
            ledgers = self._masters(s, "ledger")
            out: list[MappingLine] = []

            def add(entity, key, label, cands):
                rule = self._rule(s, entity, key)
                cands.sort(key=lambda c: -c.score)
                if rule:
                    cands = [Candidate(rule.tally_name, 100, "Remembered mapping")] + \
                            [c for c in cands if c.name != rule.tally_name]
                out.append(MappingLine(entity, key, label, rule.tally_name if rule else None, cands[:8]))

            # party ledger
            g = inv.supplier_gstin or ""
            cands = [Candidate(l.name, 100, "Same GSTIN in Tally") for l in ledgers if g and l.gstin == g]
            if not cands:
                cands = [Candidate(l.name, sc, f"Name {sc}% similar") for l in ledgers
                         if l.primary_group == "Sundry Creditors" and (sc := _sim(inv.supplier_name or "", l.name)) >= 55]
            pkey = g or norm_desc(inv.supplier_name)
            add("party", pkey, f"{inv.supplier_name or '?'} ({g or 'no GSTIN'})", cands)

            # optional: book this supplier to one ledger, without items
            ledger_wise = self._rule(s, "debit_ledger", pkey)
            dcands = [Candidate(l.name, 60, l.primary_group or "Ledger") for l in ledgers
                      if l.primary_group in EXPENSE_GROUPS]
            add("debit_ledger", pkey, f"{inv.supplier_name or '?'} – leave empty to book item-wise", dcands)
            if ledger_wise or inv.doc_type in NOTE_TYPES:
                mode = "accounting"           # booked to a ledger / a value note: never item-wise
            elif mode == "auto":
                mode = "inventory"

            # purchase ledger by supply type (+ rate when the user wants separate ledgers per rate)
            intra = is_intra(inv)
            key = "intra" if intra else ("inter" if intra is False else "unknown")
            word = r"within|local|intra" if intra else r"inter(?!nal)|igst|outside"
            avoid = r"inter(?!nal)|igst|import|urd|unregistered" if intra else r"within|local|intra|import|urd"
            cands = []
            for l in ledgers:
                if l.primary_group != "Purchase Accounts":
                    continue
                sc = 90 if re.search(word, l.name, re.I) else 50
                sc -= 35 if re.search(avoid, l.name, re.I) else 0
                cands.append(Candidate(l.name, sc, "Name matches supply type" if sc >= 90 else "Purchase ledger"))
            if not ledger_wise:
                add("purchase_ledger", key, "Purchase – " + {"intra": "within state (CGST+SGST)",
                                                             "inter": "inter-state (IGST)"}.get(key,
                                                                                                "supply type unknown"),
                    cands)

            # stock items (inventory mode)
            if mode == "inventory":
                stock = self._masters(s, "stock_item")
                for it in items:
                    k = norm_desc(it.description)
                    if not k:
                        continue
                    cands = []
                    for m in stock:
                        sc = _sim(it.description, m.name)
                        reasons = [f"name {sc}%"]
                        if it.hsn_sac and m.hsn and (it.hsn_sac.startswith(m.hsn) or m.hsn.startswith(it.hsn_sac[:4])):
                            sc += 25
                            reasons.append("HSN matches")
                        if it.gst_rate is not None and m.gst_rate is not None and it.gst_rate == m.gst_rate:
                            sc += 10
                            reasons.append("GST rate matches")
                        if sc >= 45:
                            cands.append(Candidate(m.name, min(sc, 99), ", ".join(reasons)))
                    add("stock_item", k, f"{it.description} (HSN {it.hsn_sac or '-'}, {it.gst_rate or '-'}%)", cands)
                godowns = self._masters(s, "godown")
                add("godown", "default", "Godown for all items",
                    [Candidate(gd.name, 95 if len(godowns) == 1 else 60, "Only godown" if len(godowns) == 1
                               else "Godown") for gd in godowns])

            # GST ledgers actually needed by this invoice
            heads = [h for h, v in (("CGST", inv.cgst), ("SGST", inv.sgst), ("IGST", inv.igst), ("CESS", inv.cess))
                     if v]
            for h in heads:
                pat = {"SGST": r"SGST|UTGST"}.get(h, h)
                cands = []
                for l in ledgers:
                    if l.primary_group != "Duties & Taxes" or not re.search(pat, l.name, re.I):
                        continue
                    sc = 60 + (30 if re.search(r"input|itc", l.name, re.I) else 0) - \
                        (40 if re.search(r"output|payable|not eligible|reversed|to be claimed|import", l.name, re.I)
                         else 0)
                    cands.append(Candidate(l.name, sc, "Input tax ledger" if sc >= 90 else "GST ledger"))
                add("tax_ledger", h, f"{h} amount", cands)
            # charges
            for kind in ("freight", "packing", "other_charges"):
                if getattr(inv, kind):
                    cands = [Candidate(l.name, sc, f"name {sc}%") for l in ledgers
                             if l.primary_group in ("Indirect Expenses", "Direct Expenses", "Purchase Accounts")
                             and (sc := _sim(kind.replace("_", " "), l.name)) >= 40]
                    add("charge_ledger", kind, kind.replace("_", " ").capitalize(), cands)
            # round off (always offered; used only when there is a difference)
            add("round_off", "default", "Round off",
                [Candidate(l.name, 95, "Round-off ledger") for l in ledgers if re.search(r"round", l.name, re.I)])
            vts = self._masters(s, "voucher_type")
            if inv.doc_type == "credit_note":
                # a supplier's credit note reduces the purchase: a Debit Note (purchase return) voucher in Tally
                add("voucher_type", "credit_note", "Voucher type for supplier credit notes (Debit Note)",
                    [Candidate(v.name, 100 if v.name == "Debit Note" else 70, "Debit Note voucher type")
                     for v in vts if v.parent == "Debit Note" or v.name == "Debit Note"])
            elif inv.doc_type == "debit_note":
                # a supplier's debit note adds to the purchase: booked like a purchase, against the original bill
                add("voucher_type", "debit_note", "Voucher type for supplier debit notes",
                    [Candidate(v.name, 100 if v.name == "Purchase" else 70, "Purchase voucher type")
                     for v in vts if v.parent == "Purchase" or v.name == "Purchase"])
            else:
                add("voucher_type", "purchase", "Voucher type for purchases",
                    [Candidate(v.name, 100 if v.name == "Purchase" else 70, "Purchase voucher type")
                     for v in vts if v.parent == "Purchase" or v.name == "Purchase"])
            return out

    # ------------------------------------------------------------------ approve
    def approve(self, entity: str, source_key: str, tally_name: str) -> None:
        perms.require(self.ctx.user.role if self.ctx.user else None, "mapping.edit")
        if not tally_name.strip():
            raise ValueError("Choose a Tally master")
        if tally_name not in self.master_names(entity):
            raise ValueError(f"'{tally_name}' does not exist in Tally (sync masters first, or create it in Tally)")
        with self.db.session() as s:
            rule = self._rule(s, entity, source_key)
            before = {"tally_name": rule.tally_name} if rule else None
            if rule is None:
                rule = MappingRule(company_id=self.ctx.company_id, entity=entity, source_key=source_key,
                                   tally_name=tally_name, approved_by=self.ctx.user.username)
                s.add(rule)
            else:
                rule.tally_name, rule.approved_by = tally_name, self.ctx.user.username
            rule.times_used = (rule.times_used or 0) + 1
            s.flush()
            audit_service.record(s, self.ctx.user, "mapping.approve", "mapping_rule", rule.id, before,
                                 {"entity": entity, "source": source_key, "tally_name": tally_name},
                                 company_id=self.ctx.company_id)

    def rules(self) -> list[MappingRule]:
        with self.db.session() as s:
            return list(s.scalars(select(MappingRule).where(MappingRule.company_id == self.ctx.company_id)
                                  .order_by(MappingRule.entity, MappingRule.source_key)))

    def delete_rule(self, rule_id: int) -> None:
        perms.require(self.ctx.user.role if self.ctx.user else None, "mapping.edit")
        with self.db.session() as s:
            r = s.get(MappingRule, rule_id)
            if r and r.company_id == self.ctx.company_id:
                audit_service.record(s, self.ctx.user, "mapping.delete", "mapping_rule", r.id,
                                     before={"entity": r.entity, "source": r.source_key, "tally_name": r.tally_name},
                                     company_id=self.ctx.company_id)
                s.delete(r)

    def effective_mode(self, invoice_id: int, mode: str) -> str:
        """Suppliers booked to a ledger always use Accounting Invoice; otherwise 'auto' means Item Invoice."""
        with self.db.session() as s:
            inv = s.get(Invoice, invoice_id)
            if inv is not None and inv.doc_type in NOTE_TYPES:
                return "accounting"          # credit / debit notes are imported as value notes
            key = (inv.supplier_gstin or norm_desc(inv.supplier_name)) if inv else ""
            if key and self._rule(s, "debit_ledger", key):
                return "accounting"
        return "inventory" if mode == "auto" else mode

    def resolved(self, invoice_id: int, mode: str) -> tuple[dict, list[str]]:
        """Approved mapping for an invoice, plus the list of what is still missing."""
        lines = self.lines_for(invoice_id, mode)
        mapping: dict = {"stock_item": {}, "tax_ledger": {}, "charge_ledger": {}}
        missing = []
        for ln in lines:
            if ln.entity in ("stock_item", "tax_ledger", "charge_ledger"):
                if ln.approved:
                    mapping[ln.entity][ln.source_key] = ln.approved
                else:
                    missing.append(f"{ENTITY_LABELS[ln.entity]}: {ln.source_label}")
            elif ln.entity == "round_off":
                mapping["round_off"] = ln.approved
            elif ln.entity == "debit_ledger":
                if ln.approved:                      # supplier booked ledger-wise: this ledger takes the taxable
                    mapping["purchase_ledger"] = ln.approved
                    mapping["ledger_wise"] = True
            else:
                mapping[ln.entity] = ln.approved
                if not ln.approved:
                    missing.append(f"{ENTITY_LABELS[ln.entity]}: {ln.source_label}")
        return mapping, missing
