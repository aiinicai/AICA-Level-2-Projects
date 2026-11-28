"""Tally integration service: connection status and master sync for the active company."""
from __future__ import annotations

from ipt.core.timefmt import fmt

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.db.base import Database
from ipt.db.models import Company, TallyMaster
from ipt.services import audit_service
from ipt.services.tally.client import TallyClient, TallyError
from ipt.services.tally.masters import SPECS, fetch_masters, primary_group_of


@dataclass
class TallyStatus:
    reachable: bool
    product: str = ""
    open_companies: list[str] | None = None
    company_open: bool = False
    message: str = ""


class TallyService:
    def __init__(self, db: Database, ctx: AppContext, client_factory=TallyClient):
        self.db = db
        self.ctx = ctx
        self.client_factory = client_factory

    def _company(self) -> Company:
        if not self.ctx.company_id:
            raise TallyError("Select a company first")
        with self.db.session() as s:
            c = s.get(Company, self.ctx.company_id)
        if not c.tally_company_name:
            raise TallyError("Enter the 'Tally company name' for this company in Company Settings first")
        return c

    def client(self, company: Company | None = None) -> TallyClient:
        c = company or self._company()
        return self.client_factory(c.tally_host or "localhost", c.tally_port or 9000)

    def status(self) -> TallyStatus:
        if not self.ctx.company_id:
            return TallyStatus(False, message="Select a company first")
        with self.db.session() as s:
            c = s.get(Company, self.ctx.company_id)
        cl = self.client_factory(c.tally_host or "localhost", c.tally_port or 9000)
        try:
            product = cl.ping()
            names = [x["name"] for x in cl.companies()]
        except TallyError as e:
            return TallyStatus(False, message=str(e))
        is_open = bool(c.tally_company_name) and c.tally_company_name in names
        if not c.tally_company_name:
            msg = "Connected. Set the 'Tally company name' in Company Settings."
        elif is_open:
            msg = f"Connected. '{c.tally_company_name}' is open in Tally."
        else:
            msg = f"Connected, but '{c.tally_company_name}' is not open in Tally. Open it (exact same name)."
        return TallyStatus(True, product, names, is_open, msg)

    def sync_masters(self, types: list[str] | None = None, progress=None) -> dict[str, int]:
        """Replace IPT's copy of the selected master types. Tally itself is only read."""
        perms.require(self.ctx.user.role if self.ctx.user else None, "mapping.edit")
        c = self._company()
        cl = self.client(c)
        names = [x["name"] for x in cl.companies()]
        if c.tally_company_name not in names:
            raise TallyError(f"'{c.tally_company_name}' is not open in Tally. Open it and try again.")
        types = types or list(SPECS)
        if "ledger" in types and "group" not in types:
            types = ["group"] + types
        fetched: dict[str, list[dict]] = {}
        for n, t in enumerate(types):
            if progress:
                progress(n, len(types), f"Reading {t.replace('_', ' ')}s from Tally")
            fetched[t] = fetch_masters(cl, c.tally_company_name, t)
        groups = {g["name"]: g["parent"] for g in fetched.get("group", [])} or self._stored_groups(c.id)
        now = datetime.now()
        counts = {}
        with self.db.session() as s:
            for t, rows in fetched.items():
                s.execute(delete(TallyMaster).where(TallyMaster.company_id == c.id, TallyMaster.master_type == t))
                seen = set()
                for r in rows:
                    if r["name"] in seen:
                        continue
                    seen.add(r["name"])
                    s.add(TallyMaster(company_id=c.id, master_type=t, name=r["name"], parent=r["parent"],
                                      primary_group=primary_group_of(r["parent"], groups) if t in ("ledger", "group")
                                      else "", guid=r["guid"], gstin=r["gstin"], hsn=r["hsn"],
                                      gst_rate=r["gst_rate"], base_unit=r["base_unit"], synced_at=now))
                counts[t] = len(seen)
            audit_service.record(s, self.ctx.user, "tally.sync_masters", "company", c.id, after=counts,
                                 company_id=c.id)
        return counts

    def create_master(self, kind: str, name: str, *, gstin: str = "", unit: str = "", hsn: str = "",
                      gst_rate=None) -> str:
        """Create a supplier ledger ('ledger') or stock item ('stock_item') in Tally - only after the user
        confirmed. Refused if a master of that name exists; afterwards the masters are read back from Tally
        and the new one must be there, otherwise an error is raised."""
        from ipt.services.tally.create_masters import ledger_xml, stock_item_xml
        perms.require(self.ctx.user.role if self.ctx.user else None, "tally.import")
        name = " ".join((name or "").split())
        if not name:
            raise TallyError("Enter a name")
        c = self._company()
        cl = self.client(c)
        if c.tally_company_name not in [x["name"] for x in cl.companies()]:
            raise TallyError(f"'{c.tally_company_name}' is not open in Tally")
        existing = {m.name.lower() for m in self.masters(kind)}
        if name.lower() in existing:
            raise TallyError(f"Tally already has a {kind.replace('_', ' ')} named '{name}' – choose it instead")
        if kind == "ledger":
            xml = ledger_xml(c.tally_company_name, name, gstin.strip().upper())
        elif kind == "stock_item":
            units = {m.name.lower(): m.name for m in self.masters("unit")}
            if not unit or unit.lower() not in units:
                raise TallyError(f"Unit '{unit}' is not in Tally. Use one of: " + ", ".join(sorted(units.values()))
                                 if units else "No units are synced from Tally – click Sync masters first")
            xml = stock_item_xml(c.tally_company_name, name, units[unit.lower()], hsn.strip(), gst_rate)
        else:
            raise TallyError(f"Cannot create a {kind}")
        res = cl.import_xml(xml)
        if not res.ok:
            raise TallyError("Tally did not create it: " + ("; ".join(res.line_errors) or res.raw[:300]))
        self.sync_masters([kind])
        if name.lower() not in {m.name.lower() for m in self.masters(kind)}:
            raise TallyError(f"Tally said OK but '{name}' was not found when reading the masters back")
        with self.db.session() as s:
            audit_service.record(s, self.ctx.user, "tally.create_master", kind, name,
                                 after={"name": name, "gstin": gstin, "unit": unit, "hsn": hsn,
                                        "gst_rate": str(gst_rate) if gst_rate is not None else None},
                                 company_id=c.id)
        return name

    # ------------------------------------------------------------ GST details Tally's GSTR-3B asks for
    def _gst_state(self, cl, company: str) -> tuple[list[dict], list[dict]]:
        """Read party ledgers (GSTIN, state) and units (UQC) straight from Tally."""
        from ipt.core.gstin import validate_gstin
        from ipt.services.tally.client import first_text
        from ipt.services.tally.create_masters import uqc_for
        led = cl.collection("IPTGstLedgers", "Ledger",
                            "NAME, PARENT, PARTYGSTIN, LEDGSTREGDETAILS.LIST, LEDMAILINGDETAILS.LIST, LEDSTATENAME",
                            company=company)
        ledgers = []
        for el in led.iter("LEDGER"):
            name = (el.get("NAME") or first_text(el, "NAME")).strip()
            g = first_text(el, "LEDGSTREGDETAILS.LIST/GSTIN", "PARTYGSTIN").upper()
            if not name or not validate_gstin(g).valid:
                continue
            import xml.etree.ElementTree as ET
            state = first_text(el, "LEDMAILINGDETAILS.LIST/STATE")
            reg_state = first_text(el, "LEDGSTREGDETAILS.LIST/STATE")
            ledgers.append({"name": name, "gstin": g, "state": state, "reg_state": reg_state,
                            "needs_fix": not state or not reg_state,
                            "address": first_text(el, "LEDMAILINGDETAILS.LIST/ADDRESS.LIST/ADDRESS"),
                            # the ledger's own detail rows, sent back unchanged except the empty state
                            "mailing": [ET.tostring(x, encoding="unicode") for x in el.findall("LEDMAILINGDETAILS.LIST")],
                            "gstreg": [ET.tostring(x, encoding="unicode") for x in el.findall("LEDGSTREGDETAILS.LIST")]})
        un = cl.collection("IPTGstUnits", "Unit", "NAME, GSTREPUOM", company=company)
        units = []
        for el in un.iter("UNIT"):
            name = (el.get("NAME") or first_text(el, "NAME")).strip()
            cur = first_text(el, "GSTREPUOM").replace("\x04", "").strip()
            uqc = uqc_for(name)
            if name:
                units.append({"name": name, "uqc": cur, "suggested": uqc,
                              "needs_fix": bool(uqc) and (not cur or "Not Applicable" in cur)})
        return ledgers, units

    def gst_fix_preview(self) -> dict:
        """What 'Fix GST details in Tally' would change (nothing is written)."""
        perms.require(self.ctx.user.role if self.ctx.user else None, "tally.import")
        c = self._company()
        cl = self.client(c)
        if c.tally_company_name not in [x["name"] for x in cl.companies()]:
            raise TallyError(f"'{c.tally_company_name}' is not open in Tally")
        ledgers, units = self._gst_state(cl, c.tally_company_name)
        no_uqc = [u["name"] for u in units if not u["suggested"] and (not u["uqc"] or "Not Applicable" in u["uqc"])]
        return {"company": c.tally_company_name, "ledgers": [x for x in ledgers if x["needs_fix"]],
                "units": [u for u in units if u["needs_fix"]], "units_unknown": no_uqc}

    def gst_fix_apply(self, progress=None) -> dict:
        """Write the missing party state / GST details and unit UQCs to Tally (after the user confirmed), then read
        them back: only what Tally now shows counts as fixed."""
        from ipt.core.states import state_name
        from ipt.services.tally.create_masters import ledger_gst_alter_xml, unit_uqc_alter_xml
        plan = self.gst_fix_preview()
        c = self._company()
        cl = self.client(c)
        errors, checked_address = [], False
        todo = [("ledger", x) for x in plan["ledgers"]] + [("unit", u) for u in plan["units"]]
        for n, (kind, x) in enumerate(todo, 1):
            if progress:
                progress(f"Updating {kind} {n} of {len(todo)}: {x['name']}")
            xml = ledger_gst_alter_xml(c.tally_company_name, x["name"], x["gstin"], x.get("mailing"),
                                       x.get("gstreg")) if kind == "ledger" else \
                unit_uqc_alter_xml(c.tally_company_name, x["name"], x["suggested"])
            res = cl.import_xml(xml)
            if not res.ok:
                errors.append(f"{x['name']}: " + ("; ".join(res.line_errors) or res.raw[:200]))
            elif kind == "ledger" and x.get("address") and not checked_address:
                # first ledger that had an address: make sure Tally kept it before touching any other ledger
                checked_address = True
                now = {y["name"]: y for y in self._gst_state(cl, c.tally_company_name)[0]}
                if not now.get(x["name"], {}).get("address"):
                    errors.append(f"STOPPED: after updating '{x['name']}' its address was no longer in Tally – no "
                                  "other ledger was changed. Re-enter that address in Tally (Alt+F1 shows it in "
                                  "the last backup) and report this.")
                    break
        ledgers, units = self._gst_state(cl, c.tally_company_name)
        led_now = {x["name"]: x for x in ledgers}
        unit_now = {u["name"]: u for u in units}
        fixed_l = [x["name"] for x in plan["ledgers"] if not led_now.get(x["name"], {"needs_fix": True})["needs_fix"]]
        fixed_u = [u["name"] for u in plan["units"] if not unit_now.get(u["name"], {"needs_fix": True})["needs_fix"]]
        still = [x["name"] for x in plan["ledgers"] if x["name"] not in fixed_l] + \
            [u["name"] for u in plan["units"] if u["name"] not in fixed_u]
        result = {"ledgers_fixed": fixed_l, "units_fixed": fixed_u, "not_fixed": still, "errors": errors,
                  "states": {x: state_name(led_now[x]["gstin"][:2]) for x in fixed_l}}
        with self.db.session() as s:
            audit_service.record(s, self.ctx.user, "tally.fix_gst_details", "company", c.id, after=result,
                                 company_id=c.id)
        return result

    def _stored_groups(self, company_id: int) -> dict[str, str]:
        with self.db.session() as s:
            return {g.name: g.parent for g in s.scalars(select(TallyMaster).where(
                TallyMaster.company_id == company_id, TallyMaster.master_type == "group"))}

    def masters(self, master_type: str, under_primary: str | None = None) -> list[TallyMaster]:
        if not self.ctx.company_id:
            return []
        with self.db.session() as s:
            q = select(TallyMaster).where(TallyMaster.company_id == self.ctx.company_id,
                                          TallyMaster.master_type == master_type).order_by(TallyMaster.name)
            if under_primary:
                q = q.where(TallyMaster.primary_group == under_primary)
            return list(s.scalars(q))

    def last_sync(self) -> datetime | None:
        rows = self.masters("ledger")
        return max((r.synced_at for r in rows), default=None)


class VoucherService:
    """Builds purchase vouchers for approved invoices (no Tally connection needed)."""

    def __init__(self, db: Database, ctx: AppContext, mapping, data_root=None):
        self.db, self.ctx, self.mapping, self.data_root = db, ctx, mapping, data_root

    def readiness(self, invoice_id: int, status: str = "") -> str:
        """One short text for the invoice list: what Tally import still needs ('' when the company is not linked
        to Tally or its masters are not synced)."""
        if status == "imported":
            return "In Tally"
        if status == "rejected":
            return ""
        try:
            built = self.build(invoice_id, "auto")
        except Exception:  # noqa: BLE001 - the list must always load
            return ""
        blockers = [x for x in built.blockers if "not approved" not in x]
        if not blockers:
            return "Ready" if status == "approved" else "Ready after approval"
        party = any(x.startswith("Not mapped – Supplier") for x in blockers)
        items = sum(x.startswith("Not mapped – Item") or "no Tally stock item" in x for x in blockers)
        other = [x for x in blockers if x.startswith("Not mapped") and not x.startswith(("Not mapped – Supplier",
                                                                                          "Not mapped – Item"))]
        parts = (["party"] if party else []) + ([f"{items} item(s)"] if items else []) + \
            ([f"{len(other)} ledger(s)"] if other else [])
        if parts:
            return "Map: " + ", ".join(parts)
        return "Fix: " + blockers[0][:60]

    def build(self, invoice_id: int, mode: str = "inventory"):
        from sqlalchemy.orm import selectinload

        from ipt.db.models import FinancialYear, Invoice
        from ipt.services.tally.voucher import build_purchase
        mode = self.mapping.effective_mode(invoice_id, mode)
        mapping, missing = self.mapping.resolved(invoice_id, mode)
        with self.db.session() as s:
            inv = s.scalar(select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.items)))
            if inv is None or inv.company_id != self.ctx.company_id:
                raise TallyError("Invoice not found")
            company = s.get(Company, inv.company_id)
            fy = s.get(FinancialYear, inv.fy_id)
            units = {m.name: m.base_unit for m in s.scalars(select(TallyMaster).where(
                TallyMaster.company_id == company.id, TallyMaster.master_type == "stock_item"))}
            if not company.tally_company_name:
                missing = missing + ["Tally company name (Company Settings)"]
            against = self._original_bill_in_tally(s, inv) if inv.doc_type in ("credit_note", "debit_note") else None
            built = build_purchase(inv, company, mapping, missing, mode, units, against=against)
            if fy.is_locked:
                built.blockers.append(f"FY {fy.label} is locked")
                built.xml = ""
            return built

    @staticmethod
    def _original_bill_in_tally(s, inv) -> str | None:
        """The bill name of the original invoice of a credit / debit note, if that invoice is known to be in
        Tally (imported by IPT, or in the purchase register fetched from Tally). The note is then booked
        'Agst Ref' to it; otherwise as a 'New Ref' of its own (never against a bill that may not exist)."""
        from ipt.core.textnorm import normalize_invoice_no
        from ipt.db.models import Invoice, PurchaseRegisterRecord, PurchaseRegisterUpload
        ref = (inv.original_invoice_ref or "").strip()
        if not ref or not inv.supplier_gstin:
            return None
        norm = normalize_invoice_no(ref)
        for o in s.scalars(select(Invoice).where(Invoice.company_id == inv.company_id,
                                                 Invoice.supplier_gstin == inv.supplier_gstin,
                                                 Invoice.status == "imported")):
            if normalize_invoice_no(o.invoice_no or "") == norm:
                return o.invoice_no
        cur = select(PurchaseRegisterUpload.id).where(PurchaseRegisterUpload.company_id == inv.company_id,
                                                      PurchaseRegisterUpload.is_current.is_(True))
        r = s.scalar(select(PurchaseRegisterRecord).where(PurchaseRegisterRecord.upload_id.in_(cur),
                                                          PurchaseRegisterRecord.supplier_gstin == inv.supplier_gstin,
                                                          PurchaseRegisterRecord.invoice_no_normalized == norm,
                                                          PurchaseRegisterRecord.doc_type == "INV"))
        return r.supplier_invoice_no if r else None

    def save_xml(self, invoice_id: int, mode: str, target) -> None:
        built = self.build(invoice_id, mode)
        if not built.ok:
            raise TallyError("Voucher cannot be generated: " + "; ".join(built.blockers))
        from pathlib import Path
        Path(target).write_text(built.xml, encoding="utf-8")
        with self.db.session() as s:
            audit_service.record(s, self.ctx.user, "tally.xml_generated", "invoice", invoice_id,
                                 after={"file": str(target), "mode": mode}, company_id=self.ctx.company_id)


# ====================================================================== import (Phase 3C)
import re as _re  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

from ipt.db.models import FinancialYear, Invoice, TallyImport  # noqa: E402
from ipt.services.tally.client import esc  # noqa: E402

GST_HEADS = {"CGST": "CGST", "SGST": "SGST/UTGST", "IGST": "IGST", "CESS": "Cess"}


def _day_book_xml(company: str, day: str) -> str:
    return ("<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC>"
            "<REPORTNAME>Day Book</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
            f"<SVCURRENTCOMPANY>{esc(company)}</SVCURRENTCOMPANY>"
            # Tested on TallyPrime: without TYPE="Date" and SVCURRENTDATE the Day Book ignores the dates
            f'<SVFROMDATE TYPE="Date">{day}</SVFROMDATE><SVTODATE TYPE="Date">{day}</SVTODATE>'
            f'<SVCURRENTDATE TYPE="Date">{day}</SVCURRENTDATE>'
            "</STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>")


def find_vouchers(client, company: str, day: str, party: str, reference: str) -> list[dict]:
    """Vouchers on one date for a party whose reference / number equals the supplier invoice no."""
    raw = client.post(_day_book_xml(company, day))
    if "<LINEERROR>" in raw or "<ENVELOPE" not in raw:
        raise TallyError("Tally did not return the Day Book: " + raw[:200])
    found = []
    for v in _re.findall(r"<VOUCHER[ >].*?</VOUCHER>", raw, _re.S):
        def tag(t):
            m = _re.search(fr"<{t}>(.*?)</{t}>", v, _re.S)
            return (m.group(1) if m else "").strip()
        same_party = tag("PARTYLEDGERNAME").lower() == party.lower()
        same_ref = reference.lower() in (tag("REFERENCE").lower(), tag("VOUCHERNUMBER").lower())
        if same_party and same_ref and tag("ISCANCELLED") != "Yes" and tag("ISDELETED") != "Yes":
            found.append({"voucher_number": tag("VOUCHERNUMBER"), "type": tag("VOUCHERTYPENAME"),
                          "master_id": tag("MASTERID"), "date": tag("DATE")})
    return found


class ImportService:
    """Sends approved vouchers to Tally – only after the user confirmed in the UI."""

    def __init__(self, db: Database, ctx: AppContext, vouchers: "VoucherService", tally: TallyService, data_root):
        self.db, self.ctx, self.vouchers, self.tally, self.data_root = db, ctx, vouchers, tally, data_root

    def check_duplicate(self, invoice_id: int) -> list[dict]:
        with self.db.session() as s:
            inv = s.get(Invoice, invoice_id)
            company = s.get(Company, inv.company_id)
        mapping, _ = self.vouchers.mapping.resolved(invoice_id, "accounting")
        if not mapping.get("party") or not inv.invoice_date:
            return []
        return find_vouchers(self.tally.client(company), company.tally_company_name,
                             inv.invoice_date.strftime("%Y%m%d"), mapping["party"], inv.invoice_no or "")

    def register_duplicates(self, invoice_id: int) -> list[dict]:
        """The same bill already in the purchase register fetched from Tally (any voucher type, any date):
        same supplier GSTIN and invoice number, or same GSTIN, date and total."""
        from ipt.core.textnorm import normalize_invoice_no
        from ipt.db.models import PurchaseRegisterRecord, PurchaseRegisterUpload
        with self.db.session() as s:
            inv = s.get(Invoice, invoice_id)
            if inv is None or not inv.supplier_gstin:
                return []
            cur = select(PurchaseRegisterUpload.id).where(PurchaseRegisterUpload.company_id == inv.company_id,
                                                          PurchaseRegisterUpload.fy_id == inv.fy_id,
                                                          PurchaseRegisterUpload.is_current.is_(True))
            recs = list(s.scalars(select(PurchaseRegisterRecord).where(
                PurchaseRegisterRecord.upload_id.in_(cur),
                PurchaseRegisterRecord.supplier_gstin == inv.supplier_gstin)))
            norm = normalize_invoice_no(inv.invoice_no) if inv.invoice_no else ""
            out = []
            for r in recs:
                same_no = bool(norm) and r.invoice_no_normalized == norm
                same_bill = (inv.invoice_date is not None and r.supplier_invoice_date == inv.invoice_date
                             and inv.invoice_total is not None and r.invoice_total is not None
                             and abs(r.invoice_total - inv.invoice_total) <= 1)
                if same_no or same_bill:
                    out.append({"voucher_number": r.voucher_no, "type": r.voucher_type,
                                "date": r.voucher_date.strftime("%Y%m%d") if r.voucher_date else "",
                                "master_id": r.tally_master_id or "", "source": "purchase register"})
            return out

    def all_duplicates(self, invoice_id: int) -> list[dict]:
        """Tally Day Book on the invoice date + the fetched purchase register."""
        found = [dict(d, source="Tally Day Book") for d in self.check_duplicate(invoice_id)]
        seen = {d["voucher_number"] for d in found}
        return found + [d for d in self.register_duplicates(invoice_id) if d["voucher_number"] not in seen]

    def import_many(self, invoice_ids: list[int], mode: str = "auto", progress=None) -> list[dict]:
        """Import several approved invoices one after another. Each is checked and verified on its own; an
        invoice that may already be in Tally is skipped (import it alone, with a reason, if it is not)."""
        perms.require(self.ctx.user.role if self.ctx.user else None, "tally.import")
        results = []
        for n, iid in enumerate(invoice_ids, 1):
            with self.db.session() as s:
                inv = s.get(Invoice, iid)
                label = f"{inv.supplier_name or '?'} – {inv.invoice_no or '?'}" if inv else str(iid)
            if progress:
                progress(f"Importing {n} of {len(invoice_ids)}: {label}")
            try:
                dups = self.all_duplicates(iid)
                if dups:
                    results.append({"invoice_id": iid, "label": label, "status": "skipped",
                                    "message": f"possibly already in Tally ({dups[0]['source']}: voucher "
                                               f"{dups[0]['voucher_number']}) – import it alone if it is not"})
                    continue
                rec = self.import_invoice(iid, mode)
                msg = {"success": f"created and found in Tally (voucher ID {rec.tally_master_id})",
                       "unverified": "Tally said OK but IPT could not find it – check the Day Book",
                       }.get(rec.status, "Tally refused: " + (rec.line_errors or rec.errors and str(rec.errors) or "?"))
                results.append({"invoice_id": iid, "label": label, "status": rec.status, "message": msg})
            except (TallyError, perms.PermissionDenied) as e:
                results.append({"invoice_id": iid, "label": label, "status": "failed", "message": str(e)})
        return results

    def import_invoice(self, invoice_id: int, mode: str = "inventory", duplicate_remark: str = "") -> TallyImport:
        perms.require(self.ctx.user.role if self.ctx.user else None, "tally.import")
        with self.db.session() as s:
            inv = s.get(Invoice, invoice_id)
            company = s.get(Company, inv.company_id)
            fy = s.get(FinancialYear, inv.fy_id)
            already = s.scalar(select(TallyImport).where(TallyImport.invoice_id == invoice_id,
                                                         TallyImport.status == "success"))
        cl = self.tally.client(company)
        open_names = [c["name"] for c in cl.companies()]
        if company.tally_company_name not in open_names:
            raise TallyError(f"'{company.tally_company_name}' is not open in Tally")
        if already:
            # imported before: ask Tally whether that voucher still exists. Only when Tally (with the company
            # open) confirms it is gone - deleted by the user - is the old import marked 'removed'.
            rec = self.recheck(already.id)
            if rec.status == "success":
                raise TallyError(f"This invoice was already imported into Tally on {fmt(already.at)} and the "
                                 f"voucher is still in Tally. Delete it in Tally first to import it again.")
        built = self.vouchers.build(invoice_id, mode)
        if not built.ok:
            raise TallyError("Voucher is not ready: " + "; ".join(built.blockers))
        from ipt.services.tally.voucher import amounts_sum_zero
        if not amounts_sum_zero(built.xml):
            raise TallyError("Safety check failed: voucher amounts do not add up to zero")
        with self.db.session() as s:
            inv = s.get(Invoice, invoice_id)
        dups = self.check_duplicate(invoice_id)
        reg = [] if already else self.register_duplicates(invoice_id)
        if (dups or reg) and not duplicate_remark.strip():
            d = (dups or reg)[0]
            raise TallyError(f"This bill may already be in Tally (voucher {d['voucher_number']} "
                             f"{'on the same date' if dups else 'in the purchase register'}). Not imported.")
        # keep the exact request on disk
        from ipt.services import storage_service
        xml_dir = storage_service.ensure_fy_folders(self.data_root, company.folder_name, fy.label) / "XML"
        req_path = xml_dir / f"invoice_{invoice_id}_{datetime.now():%Y%m%d_%H%M%S}.xml"
        req_path.write_text(built.xml, encoding="utf-8")
        result = cl.import_xml(built.xml)
        verified = False
        found = []
        if result.ok:
            found = find_vouchers(cl, company.tally_company_name, inv.invoice_date.strftime("%Y%m%d"),
                                  self.vouchers.mapping.resolved(invoice_id, mode)[0]["party"], inv.invoice_no)
            verified = len(found) >= 1 + len(dups)
        status = "success" if result.ok and verified else ("unverified" if result.ok else "failed")
        with self.db.session() as s:
            rec = TallyImport(company_id=company.id, fy_id=fy.id, invoice_id=invoice_id,
                              username=self.ctx.user.username, tally_company=company.tally_company_name,
                              request_xml_path=str(_Path(req_path).relative_to(self.data_root)),
                              response_xml=result.raw[:20000], created=result.created, altered=result.altered,
                              errors=result.errors, line_errors="\n".join(result.line_errors),
                              tally_master_id=(found[-1]["master_id"] if found else result.last_vch_id),
                              verified=verified, status=status, remark=duplicate_remark.strip())
            s.add(rec)
            inv2 = s.get(Invoice, invoice_id)
            if status == "success":
                inv2.status = "imported"
            s.flush()
            audit_service.record(s, self.ctx.user, "tally.import", "invoice", invoice_id,
                                 after={"status": status, "created": result.created, "errors": result.errors,
                                        "line_errors": result.line_errors[:3], "mode": mode},
                                 remark=duplicate_remark, company_id=company.id)
            s.expunge(rec)
        return rec

    def release_many(self, invoice_ids: list[int], progress=None) -> list[dict]:
        """Ask Tally about several imported invoices; those whose voucher is gone become 'approved' again."""
        out = []
        for n, iid in enumerate(invoice_ids, 1):
            with self.db.session() as s:
                inv = s.get(Invoice, iid)
                label = f"{inv.supplier_name or '?'} – {inv.invoice_no or '?'}" if inv else str(iid)
            if progress:
                progress(f"Asking Tally {n} of {len(invoice_ids)}: {label}")
            try:
                freed = self.release_if_deleted(iid)
                out.append({"invoice_id": iid, "label": label, "status": "freed" if freed else "in_tally",
                            "message": "not in Tally any more – ready to import again" if freed
                            else "still in Tally – left as imported"})
            except (TallyError, perms.PermissionDenied) as e:
                out.append({"invoice_id": iid, "label": label, "status": "failed", "message": str(e)})
        return out

    def release_if_deleted(self, invoice_id: int) -> bool:
        """For an imported invoice: ask Tally whether its voucher still exists. True when Tally confirms it
        was deleted - the invoice is then 'approved' again and can be imported again."""
        with self.db.session() as s:
            already = s.scalar(select(TallyImport).where(TallyImport.invoice_id == invoice_id,
                                                         TallyImport.status == "success")
                               .order_by(TallyImport.id.desc()))
            inv = s.get(Invoice, invoice_id)
            if already is None:
                if inv is not None and inv.status == "imported":
                    inv.status = "approved"          # no live import record: nothing to protect
                    return True
                return False
            import_id = already.id
        return self.recheck(import_id).status == "removed"

    def recheck(self, import_id: int) -> TallyImport:
        """Look for an 'unverified' voucher in Tally again; mark it success only if it is found."""
        perms.require(self.ctx.user.role if self.ctx.user else None, "tally.import")
        with self.db.session() as s:
            rec = s.get(TallyImport, import_id)
            if rec is None or rec.company_id != self.ctx.company_id:
                raise TallyError("Import record not found")
            inv = s.get(Invoice, rec.invoice_id)
            company = s.get(Company, rec.company_id)
        party = self.vouchers.mapping.resolved(inv.id, "accounting")[0].get("party")
        cl = self.tally.client(company)
        if company.tally_company_name not in [c["name"] for c in cl.companies()]:
            raise TallyError(f"'{company.tally_company_name}' is not open in Tally – open it and re-check")
        found = find_vouchers(cl, company.tally_company_name,
                              inv.invoice_date.strftime("%Y%m%d"), party or "", inv.invoice_no or "")
        with self.db.session() as s:
            rec = s.get(TallyImport, import_id)
            if found and rec.created >= 1:
                rec.verified, rec.status = True, "success"
                rec.tally_master_id = found[-1]["master_id"] or rec.tally_master_id
                s.get(Invoice, inv.id).status = "imported"
            elif not found and rec.status == "success":
                # Tally answered and the voucher is gone (deleted by the user in Tally):
                # free the invoice so a corrected voucher can be imported again.
                rec.status, rec.verified = "removed", False
                inv2 = s.get(Invoice, inv.id)
                if inv2.status == "imported":
                    inv2.status = "approved"
            audit_service.record(s, self.ctx.user, "tally.import_recheck", "invoice", inv.id,
                                 after={"found": len(found), "status": rec.status}, company_id=rec.company_id)
            s.flush()
            s.expunge(rec)
        return rec

    def history(self) -> list[TallyImport]:
        if not self.ctx.company_id:
            return []
        with self.db.session() as s:
            return list(s.scalars(select(TallyImport).where(TallyImport.company_id == self.ctx.company_id)
                                  .order_by(TallyImport.id.desc())))

    def create_gst_ledger(self, head: str, name: str) -> None:
        """Create an input-tax ledger under Duties & Taxes with the right GST duty head (user-confirmed)."""
        perms.require(self.ctx.user.role if self.ctx.user else None, "mapping.edit")
        c = self.tally._company()
        duty = GST_HEADS[head]
        xml = ("<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC>"
               "<REPORTNAME>All Masters</REPORTNAME><STATICVARIABLES>"
               f"<SVCURRENTCOMPANY>{esc(c.tally_company_name)}</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC>"
               '<REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">'
               f'<LEDGER NAME="{esc(name)}" ACTION="Create"><NAME.LIST><NAME>{esc(name)}</NAME></NAME.LIST>'
               "<PARENT>Duties &amp; Taxes</PARENT><TAXTYPE>GST</TAXTYPE>"
               f"<GSTDUTYHEAD>{esc(duty)}</GSTDUTYHEAD><ISBILLWISEON>No</ISBILLWISEON>"
               "<AFFECTSSTOCK>No</AFFECTSSTOCK></LEDGER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")
        res = self.tally.client(c).import_xml(xml)
        with self.db.session() as s:
            audit_service.record(s, self.ctx.user, "tally.create_ledger", "company", c.id,
                                 after={"ledger": name, "head": duty, "created": res.created, "errors": res.errors,
                                        "line_errors": res.line_errors[:3]}, company_id=c.id)
        if not res.ok:
            raise TallyError("Tally did not create the ledger: " + ("; ".join(res.line_errors) or res.raw[:300]))
        self.tally.sync_masters(["ledger"])
