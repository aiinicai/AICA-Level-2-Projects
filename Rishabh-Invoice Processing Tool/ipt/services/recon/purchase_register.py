"""Purchase register ("books") for reconciliation: from Tally directly, or from an Excel export.

From Tally: purchase / debit note / credit note vouchers are read month by month from the Day Book
(read-only). Each ledger line is classified with the synced Tally masters: Purchase Accounts -> taxable
value, Duties & Taxes ledgers named IGST / CGST / SGST / UTGST / Cess -> that tax head, the party ledger
-> invoice total. The supplier's invoice number is the voucher's Reference (Supplier Invoice No.), else
the voucher number.

From Excel: the user picks the sheet and header row and maps columns (several columns may add up into
one amount, e.g. two purchase ledgers). The mapping can be saved as a template. Rows that cannot be read
are rejected with the reason and can be exported.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.core.gstin import validate_gstin
from ipt.core.textnorm import normalize_invoice_no, parse_date
from ipt.db.base import Database
from ipt.db.models import (Company, FinancialYear, PrTemplate, PurchaseRegisterRecord, PurchaseRegisterReject,
                           PurchaseRegisterUpload, TallyMaster)
from ipt.services import audit_service, storage_service
from ipt.services.document_service import sha256_of
from ipt.services.tally.client import TallyError, esc

# fields a column can be mapped to; amount fields may take several columns (added together)
PR_FIELDS = {
    "voucher_date": "Voucher date", "voucher_no": "Voucher no.", "voucher_type": "Voucher type",
    "party_name": "Party (supplier) name", "supplier_gstin": "Supplier GSTIN",
    "supplier_invoice_no": "Supplier invoice no.", "supplier_invoice_date": "Supplier invoice date",
    "purchase_ledger": "Purchase ledger", "taxable_value": "Taxable value", "igst": "IGST", "cgst": "CGST",
    "sgst": "SGST / UTGST", "cess": "Cess", "invoice_total": "Invoice total", "narration": "Narration",
}
AMOUNT_FIELDS = ("taxable_value", "igst", "cgst", "sgst", "cess", "invoice_total")
GUESS_RULES = [
    ("supplier_invoice_date", r"supplier\s*inv(oice)?\.?\s*date|bill\s*date|ref(erence)?\.?\s*date"),
    ("supplier_invoice_no", r"supplier\s*inv(oice)?\.?\s*no|bill\s*no|ref(erence)?\.?\s*no|^reference$"),
    ("voucher_date", r"^(voucher\s*)?date$"),
    ("voucher_no", r"voucher\s*no|vch\.?\s*no"),
    ("voucher_type", r"voucher\s*type|vch\.?\s*type"),
    ("supplier_gstin", r"gstin|gst\s*no"),
    ("party_name", r"^particulars$|party|supplier\s*name|ledger\s*name"),
    ("taxable_value", r"taxable|^purchase|purchase\s*(a/c|account|@|within|inter|local)"),
    ("igst", r"igst|integrated\s*tax"),
    ("cgst", r"cgst|central\s*tax"),
    ("sgst", r"sgst|utgst|state\s*(/\s*ut\s*)?tax"),
    ("cess", r"\bcess\b"),
    ("invoice_total", r"gross\s*total|invoice\s*(value|amount|total)|^total$|^value$"),
    ("narration", r"narration"),
]


class PurchaseRegisterError(Exception):
    pass


# ----------------------------------------------------------------------------- helpers
def _money(v) -> Decimal | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v)).quantize(Decimal("0.01"))
    s = str(v).strip()
    neg = s.endswith("Dr") or s.endswith("Cr") or s.startswith("(")
    s = re.sub(r"[₹,\s()]|Dr|Cr", "", s)
    if s in ("", "-"):
        return None
    try:
        d = Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation as e:
        raise ValueError(f"'{v}' is not an amount") from e
    return d if not neg else abs(d)


def _date(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    if re.fullmatch(r"\d{8}", s):
        return date(int(s[:4]), int(s[4:6]), int(s[6:]))
    return parse_date(s)


def guess_mapping(headers: list[str]) -> dict[str, list[int]]:
    """A first suggestion for the column mapping; the user always confirms it."""
    out: dict[str, list[int]] = {}
    used: set[int] = set()
    for fld, pattern in GUESS_RULES:
        for c, h in enumerate(headers):
            if c in used or not h:
                continue
            if re.search(pattern, str(h).strip(), re.I):
                if fld in AMOUNT_FIELDS:
                    out.setdefault(fld, []).append(c)
                    used.add(c)
                elif fld not in out:
                    out[fld] = [c]
                    used.add(c)
                    break
    return out


def read_rows(path: Path, sheet: str | None = None, limit: int | None = None) -> tuple[list[str], list[list]]:
    """(sheet names, rows of the chosen sheet). .xlsx / .xlsm / .csv"""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        import csv
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = [r for _, r in zip(range(limit or 10 ** 9), csv.reader(f))]
        return ["CSV"], rows
    from openpyxl import load_workbook
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001
        raise PurchaseRegisterError(f"Could not open the file: {e}") from e
    try:
        names = wb.sheetnames
        ws = wb[sheet] if sheet in names else wb[names[0]]
        rows = []
        for i, r in enumerate(ws.iter_rows(values_only=True)):
            if limit and i >= limit:
                break
            rows.append(list(r))
        return names, rows
    finally:
        wb.close()


def guess_header_row(rows: list[list]) -> int:
    """1-based row number that looks most like a header (most text cells matching known names)."""
    best, best_row = -1, 1
    for i, r in enumerate(rows[:30]):
        score = sum(1 for v in r if isinstance(v, str) and any(re.search(p, v, re.I) for _, p in GUESS_RULES))
        if score > best:
            best, best_row = score, i + 1
    return best_row


# ----------------------------------------------------------------------------- Tally Day Book
def day_book_range_xml(company: str, start: date, end: date) -> str:
    f, t = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    return ("<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC>"
            "<REPORTNAME>Day Book</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
            f"<SVCURRENTCOMPANY>{esc(company)}</SVCURRENTCOMPANY>"
            f'<SVFROMDATE TYPE="Date">{f}</SVFROMDATE><SVTODATE TYPE="Date">{t}</SVTODATE>'
            f'<SVCURRENTDATE TYPE="Date">{t}</SVCURRENTDATE>'
            "</STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>")


_LOAD_LOCK = __import__("threading").Lock()


def _tag(xml: str, t: str) -> str:
    m = re.search(fr"<{t}(?:\s[^>]*)?>(.*?)</{t}>", xml, re.S)
    return _unesc(m.group(1).strip()) if m else ""


def _unesc(s: str) -> str:
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")


@dataclass
class TallyMasters:
    primary: dict[str, str] = field(default_factory=dict)     # ledger -> primary group
    gstin: dict[str, str] = field(default_factory=dict)       # ledger -> GSTIN
    vch_base: dict[str, str] = field(default_factory=dict)    # voucher type -> base (parent chain)


def _base_type(name: str, m: TallyMasters) -> str:
    seen, cur = set(), name
    while cur in m.vch_base and cur not in seen and m.vch_base[cur] and m.vch_base[cur] != cur:
        seen.add(cur)
        cur = m.vch_base[cur]
    return cur


NOT_TAXABLE_GROUPS = {"Sundry Creditors", "Sundry Debtors", "Bank Accounts", "Bank OD A/c", "Cash-in-Hand",
                      "Loans (Liability)", "Current Liabilities", "Provisions"}
# voucher types that never carry input tax credit of a purchase
SKIP_BASES = {"Sales", "Receipt", "Contra", "Sales Order", "Purchase Order", "Delivery Note", "Receipt Note",
              "Rejections In", "Rejections Out", "Stock Journal", "Physical Stock", "Memorandum", "Job Work In Order",
              "Job Work Out Order", "Material In", "Material Out", "Attendance", "Payroll"}
PARTY_GROUPS = {"Sundry Creditors", "Sundry Debtors"}


def _tax_head(name: str) -> str | None:
    return ("igst" if re.search(r"IGST|integrated", name, re.I) else
            "cgst" if re.search(r"CGST|central", name, re.I) else
            "sgst" if re.search(r"SGST|UTGST|state", name, re.I) else
            "cess" if re.search(r"cess", name, re.I) else None)


def parse_day_book(raw: str, masters: TallyMasters, start: date, end: date) -> list[dict]:
    """Purchase-side rows of a Day Book XML: every voucher - Purchase, Journal, Payment, Debit Note... - in which
    an input GST ledger (IGST/CGST/SGST/Cess under Duties & Taxes) is on the input-credit side. Vouchers without
    such a tax line are left out. Tally XML: a debit is a negative AMOUNT.

    Input side = debit for invoices (Purchase, Journal, Payment ...) and credit for a Debit Note (purchase
    return). RCM journals (Input CGST Dr / CGST RCM payable Cr) count only the input lines and are marked."""
    out = []
    for v in re.findall(r"<VOUCHER[ >].*?</VOUCHER>", raw, re.S):
        if _tag(v, "ISCANCELLED") == "Yes" or _tag(v, "ISDELETED") == "Yes" or _tag(v, "ISOPTIONAL") == "Yes":
            continue
        vtype = _tag(v, "VOUCHERTYPENAME")
        base = _base_type(vtype, masters)
        if base in SKIP_BASES:
            continue
        party = _tag(v, "PARTYLEDGERNAME")
        if base == "Credit Note" and masters.primary.get(party) != "Sundry Creditors":
            continue                       # a sales-side credit note
        d = _date(_tag(v, "DATE"))
        if d is None or not (start <= d <= end):
            continue
        doc_type = {"Debit Note": "CRN", "Credit Note": "DBN"}.get(base, "INV")
        # input side: debit (negative) for invoices / supplier debit notes, credit (positive) for purchase returns
        input_sign = 1 if doc_type == "CRN" else -1

        lines = re.findall(r"<(?:ALL)?LEDGERENTRIES\.LIST>(.*?)</(?:ALL)?LEDGERENTRIES\.LIST>", v, re.S)
        for inv in re.findall(r"<(?:ALL)?INVENTORYENTRIES\.LIST>(.*?)</(?:ALL)?INVENTORYENTRIES\.LIST>", v, re.S):
            lines += re.findall(r"<ACCOUNTINGALLOCATIONS\.LIST>(.*?)</ACCOUNTINGALLOCATIONS\.LIST>", inv, re.S)
        entries = []
        for ln in lines:
            name = _tag(ln, "LEDGERNAME")
            try:
                amt = Decimal(_tag(ln, "AMOUNT") or "0")
            except InvalidOperation:
                continue
            if name and amt:
                entries.append((name, amt, masters.primary.get(name, "")))

        buckets = {k: Decimal("0") for k in ("taxable_value", "igst", "cgst", "sgst", "cess")}
        seen = {k: False for k in buckets}
        rcm = False
        for name, amt, group in entries:
            head = _tax_head(name) if group == "Duties & Taxes" else None
            if head is None:
                continue
            if (amt > 0) == (input_sign > 0) and not re.search(r"output|payable|liabilit", name, re.I):
                buckets[head] += abs(amt)
                seen[head] = True
            else:
                rcm = rcm or bool(re.search(r"rcm|reverse|payable", name, re.I))
            if re.search(r"rcm|reverse", name, re.I):
                rcm = True
        if not any(seen[h] for h in ("igst", "cgst", "sgst", "cess")):
            continue                       # no input GST in this voucher: not part of the ITC register

        # party: the voucher's party, else the supplier ledger on the other side
        if not party or masters.primary.get(party) not in PARTY_GROUPS:
            cands = [n for n, a, g in entries if g in PARTY_GROUPS and (a > 0) != (input_sign > 0)]
            party = cands[0] if cands else party
        party_amt = sum((a for n, a, g in entries if n == party), Decimal("0")) if party else None
        purchase_ledgers: list[str] = []
        for name, amt, group in entries:
            if name == party or group == "Duties & Taxes" or group in NOT_TAXABLE_GROUPS:
                continue
            if re.search(r"round", name, re.I) or (amt > 0) != (input_sign > 0):
                continue                   # round off, and lines on the other side (not the supply)
            # Purchase Accounts, expenses or fixed assets: the taxable value of the supply
            buckets["taxable_value"] += abs(amt)
            seen["taxable_value"] = True
            if name not in purchase_ledgers:
                purchase_ledgers.append(name)
        tax = sum(buckets[h] for h in ("igst", "cgst", "sgst", "cess"))
        if party_amt:
            total = abs(party_amt)
        else:
            total = buckets["taxable_value"] + tax
        ref = _tag(v, "REFERENCE")
        inv_no = ref or _tag(v, "VOUCHERNUMBER")
        narr = _tag(v, "NARRATION")
        out.append({
            "voucher_no": _tag(v, "VOUCHERNUMBER"), "voucher_date": d, "voucher_type": vtype, "doc_type": doc_type,
            "party_name": party, "supplier_gstin": (_tag(v, "PARTYGSTIN") or masters.gstin.get(party, "")).upper(),
            "supplier_invoice_no": inv_no, "invoice_no_normalized": normalize_invoice_no(inv_no) or "",
            "supplier_invoice_date": _date(_tag(v, "REFERENCEDATE")) or d,
            "purchase_ledger": ", ".join(purchase_ledgers),
            **{k: (buckets[k].quantize(Decimal("0.01")) if seen[k] else None) for k in buckets},
            "invoice_total": total.quantize(Decimal("0.01")),
            "narration": ("[RCM] " if rcm else "") + narr, "tally_master_id": _tag(v, "MASTERID"),
        })
    return out


def months(start: date, end: date):
    cur = date(start.year, start.month, 1)
    while cur <= end:
        nxt = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)
        yield max(cur, start), min(nxt - timedelta(days=1), end)
        cur = nxt


# ----------------------------------------------------------------------------- service
class PurchaseRegisterService:
    def __init__(self, db: Database, data_root: Path, ctx: AppContext, tally=None):
        self.db, self.data_root, self.ctx, self.tally = db, data_root, ctx, tally

    def _scope(self, s) -> tuple[Company, FinancialYear]:
        if not self.ctx.company_id or not self.ctx.fy_id:
            raise PurchaseRegisterError("Select a company and financial year first")
        company, fy = s.get(Company, self.ctx.company_id), s.get(FinancialYear, self.ctx.fy_id)
        if company is None or fy is None or fy.company_id != company.id:
            raise PurchaseRegisterError("The selected company / financial year is not valid")
        return company, fy

    def _require(self):
        perms.require(self.ctx.user.role if self.ctx.user else None, "gst.upload")

    # ---------------------------------------------------------------- save
    def _save(self, s, company, fy, source: str, rows: list[dict], rejects: list[tuple[int, str, dict]],
              file_name: str = "", digest: str = "", start: date | None = None, end: date | None = None):
        dates = [r["voucher_date"] or r["supplier_invoice_date"] for r in rows if
                 r.get("voucher_date") or r.get("supplier_invoice_date")]
        start = start or (min(dates) if dates else None)
        end = end or (max(dates) if dates else None)
        # a new register replaces current ones whose period overlaps (kept as history)
        replaced = []
        for old in s.scalars(select(PurchaseRegisterUpload).where(
                PurchaseRegisterUpload.company_id == company.id, PurchaseRegisterUpload.fy_id == fy.id,
                PurchaseRegisterUpload.is_current.is_(True))):
            broken = old.period_from and old.period_to and old.period_from > old.period_to   # empty, bad dates
            if broken or start is None or old.period_from is None or not (old.period_to < start or
                                                                          old.period_from > end):
                old.is_current = False
                replaced.append(old.id)
        up = PurchaseRegisterUpload(company_id=company.id, fy_id=fy.id, source=source, file_name=file_name,
                                    file_sha256=digest, period_from=start, period_to=end, rows_ok=len(rows),
                                    rows_rejected=len(rejects),
                                    uploaded_by=self.ctx.user.username if self.ctx.user else "")
        s.add(up)
        s.flush()
        for n, r in enumerate(rows, 1):
            r.setdefault("row_no", n)
            s.add(PurchaseRegisterRecord(upload_id=up.id, company_id=company.id, fy_id=fy.id, **r))
        for row_no, reason, raw in rejects:
            s.add(PurchaseRegisterReject(upload_id=up.id, row_no=row_no, reason=reason,
                                         raw_json=json.dumps(raw, default=str)))
        audit_service.record(s, self.ctx.user, "purchase_register.load", "purchase_register_upload", up.id,
                             before={"replaced": replaced} if replaced else None,
                             after={"source": source, "file": file_name, "rows": len(rows), "rejected": len(rejects),
                                    "from": str(start), "to": str(end)}, company_id=company.id)
        s.flush()
        return up

    # ---------------------------------------------------------------- Tally
    def masters(self, s, company_id: int) -> TallyMasters:
        m = TallyMasters()
        for t in s.scalars(select(TallyMaster).where(TallyMaster.company_id == company_id)):
            if t.master_type == "ledger":
                m.primary[t.name] = t.primary_group
                if t.gstin:
                    m.gstin[t.name] = t.gstin
            elif t.master_type == "voucher_type":
                m.vch_base[t.name] = t.parent or t.name
        return m

    def fetch_from_tally(self, start: date, end: date, progress=None) -> PurchaseRegisterUpload:
        """Read purchase vouchers from Tally (read-only) for the period and store them as the register.
        Only one load runs at a time: two at once would both stay 'current' and every voucher would show twice."""
        if not _LOAD_LOCK.acquire(blocking=False):
            raise PurchaseRegisterError("A purchase register is already being loaded – wait for it to finish")
        try:
            return self._fetch_from_tally(start, end, progress)
        finally:
            _LOAD_LOCK.release()

    def _fetch_from_tally(self, start: date, end: date, progress=None) -> PurchaseRegisterUpload:
        self._require()
        if start > end:
            raise PurchaseRegisterError(f"'From' {start:%d-%m-%Y} is after 'To' {end:%d-%m-%Y}")
        if self.tally is None:
            raise PurchaseRegisterError("Tally connection is not available")
        with self.db.session() as s:
            company, fy = self._scope(s)
            if not company.tally_company_name:
                raise PurchaseRegisterError("Set the Tally company name in Company settings first")
            start, end = max(start, fy.start_date), min(end, fy.end_date)
            masters = self.masters(s, company.id)
            if not masters.primary:
                raise PurchaseRegisterError("Sync the Tally masters first (Tally Integration page) so ledgers "
                                            "can be classified")
            tally_name = company.tally_company_name
        client = self.tally.client(company)
        if tally_name not in [c["name"] for c in client.companies()]:
            raise TallyError(f"'{tally_name}' is not open in Tally")
        rows: list[dict] = []
        # Tested on TallyPrime with 439 vouchers in a month: the Day Book export returns only the
        # SVCURRENTDATE day and ignores SVFROMDATE/SVTODATE. So it is read one day at a time (fast: one small
        # request per day) - the only way that is known to return every voucher.
        day = start
        while day <= end:
            if progress and (day == start or day.day == 1):
                progress(f"Reading {day:%b %Y} from Tally ({len(rows)} vouchers so far)")
            raw = client.post(day_book_range_xml(tally_name, day, day))
            if "<LINEERROR>" in raw or "<ENVELOPE" not in raw:
                raise TallyError(f"Tally did not return the Day Book for {day:%d-%m-%Y}: " + raw[:200])
            rows += parse_day_book(raw, masters, day, day)
            day += timedelta(days=1)
        seen, unique = set(), []
        for r in rows:          # the same voucher could come back in two month requests
            key = r["tally_master_id"] or (r["voucher_type"], r["voucher_no"], r["voucher_date"])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        with self.db.session() as s:
            company, fy = self._scope(s)
            return self._save(s, company, fy, "tally", unique, [], file_name=f"Tally: {tally_name}",
                              start=start, end=end)

    # ---------------------------------------------------------------- Excel
    def import_excel(self, path: Path, sheet: str | None, header_row: int, mapping: dict[str, list[int]],
                     template_name: str = "") -> PurchaseRegisterUpload:
        self._require()
        path = Path(path)
        if not any(f in mapping for f in ("supplier_invoice_no", "voucher_no")):
            raise PurchaseRegisterError("Map the supplier invoice no. (or voucher no.) column")
        if not any(f in mapping for f in ("supplier_invoice_date", "voucher_date")):
            raise PurchaseRegisterError("Map a date column")
        if not any(f in mapping for f in ("taxable_value", "invoice_total")):
            raise PurchaseRegisterError("Map the taxable value or invoice total column")
        _, rows = read_rows(path, sheet)
        header = rows[header_row - 1] if 0 < header_row <= len(rows) else []
        good, rejects = [], []
        for i, row in enumerate(rows[header_row:], start=header_row + 1):
            if not any(v not in (None, "") for v in row):
                continue
            raw = {str(header[c] if c < len(header) else c): row[c] for c in range(len(row)) if row[c] not in (None, "")}

            def cell(c):
                return row[c] if c < len(row) else None

            first = " ".join(str(v) for v in row if v not in (None, "")).strip().lower()
            if first.startswith(("total", "grand total", "opening", "closing")):
                continue
            try:
                rec: dict = {}
                for fld, cols in mapping.items():
                    if fld in AMOUNT_FIELDS:
                        vals = [_money(cell(c)) for c in cols]
                        vals = [v for v in vals if v is not None]
                        rec[fld] = abs(sum(vals, Decimal("0.00"))) if vals else None
                    elif fld in ("voucher_date", "supplier_invoice_date"):
                        rec[fld] = _date(cell(cols[0]))
                        if cell(cols[0]) not in (None, "") and rec[fld] is None:
                            raise ValueError(f"'{cell(cols[0])}' is not a date")
                    else:
                        v = cell(cols[0])
                        rec[fld] = "" if v is None else str(v).strip()
            except ValueError as e:
                rejects.append((i, str(e), raw))
                continue
            inv_no = rec.get("supplier_invoice_no") or rec.get("voucher_no") or ""
            if not inv_no:
                rejects.append((i, "No invoice / voucher number", raw))
                continue
            if not (rec.get("supplier_invoice_date") or rec.get("voucher_date")):
                rejects.append((i, "No date", raw))
                continue
            g = (rec.get("supplier_gstin") or "").upper().replace(" ", "")
            if g and not validate_gstin(g).valid:
                rejects.append((i, f"GSTIN {g} is not valid ({validate_gstin(g).message})", raw))
                continue
            vt = (rec.get("voucher_type") or "").lower()
            rec.update(supplier_gstin=g, supplier_invoice_no=inv_no,
                       invoice_no_normalized=normalize_invoice_no(inv_no) or "",
                       supplier_invoice_date=rec.get("supplier_invoice_date") or rec.get("voucher_date"),
                       doc_type="CRN" if "debit" in vt else "DBN" if "credit" in vt else "INV", row_no=i)
            good.append(rec)
        with self.db.session() as s:
            company, fy = self._scope(s)
            folder = storage_service.ensure_fy_folders(self.data_root, company.folder_name, fy.label) / "Purchase_Register"
            import shutil
            target = folder / f"{datetime.now():%Y%m%d_%H%M%S}_{path.name}"
            shutil.copy2(path, target)
            if template_name:
                self._save_template(s, company.id, template_name, sheet or "", header_row, mapping)
            return self._save(s, company, fy, "excel", good, rejects, file_name=path.name, digest=sha256_of(path))

    def _save_template(self, s, company_id: int, name: str, sheet: str, header_row: int, mapping: dict):
        t = s.scalar(select(PrTemplate).where(PrTemplate.company_id == company_id, PrTemplate.name == name))
        if t is None:
            t = PrTemplate(company_id=company_id, name=name)
            s.add(t)
        t.sheet, t.header_row, t.mapping_json = sheet, header_row, json.dumps(mapping)

    def templates(self) -> list[PrTemplate]:
        with self.db.session() as s:
            return list(s.scalars(select(PrTemplate).where(PrTemplate.company_id == self.ctx.company_id)
                                  .order_by(PrTemplate.name)))

    # ---------------------------------------------------------------- read
    def uploads(self, include_history: bool = False) -> list[PurchaseRegisterUpload]:
        if not self.ctx.company_id or not self.ctx.fy_id:
            return []
        with self.db.session() as s:
            q = select(PurchaseRegisterUpload).where(PurchaseRegisterUpload.company_id == self.ctx.company_id,
                                                     PurchaseRegisterUpload.fy_id == self.ctx.fy_id)
            if not include_history:
                q = q.where(PurchaseRegisterUpload.is_current.is_(True))
            return list(s.scalars(q.order_by(PurchaseRegisterUpload.id.desc())))

    def records(self, upload_id: int | None = None) -> list[PurchaseRegisterRecord]:
        if not self.ctx.company_id or not self.ctx.fy_id:
            return []
        with self.db.session() as s:
            q = select(PurchaseRegisterRecord).where(PurchaseRegisterRecord.company_id == self.ctx.company_id,
                                                     PurchaseRegisterRecord.fy_id == self.ctx.fy_id)
            if upload_id:
                q = q.where(PurchaseRegisterRecord.upload_id == upload_id)
            else:
                cur = select(PurchaseRegisterUpload.id).where(
                    PurchaseRegisterUpload.company_id == self.ctx.company_id,
                    PurchaseRegisterUpload.fy_id == self.ctx.fy_id, PurchaseRegisterUpload.is_current.is_(True))
                q = q.where(PurchaseRegisterRecord.upload_id.in_(cur))
            return list(s.scalars(q.order_by(PurchaseRegisterRecord.supplier_invoice_date, PurchaseRegisterRecord.id)))

    def rejects(self, upload_id: int) -> list[PurchaseRegisterReject]:
        with self.db.session() as s:
            up = s.get(PurchaseRegisterUpload, upload_id)
            if up is None or up.company_id != self.ctx.company_id:
                return []
            return list(s.scalars(select(PurchaseRegisterReject).where(PurchaseRegisterReject.upload_id == upload_id)
                                  .order_by(PurchaseRegisterReject.row_no)))

    def export_rejects(self, upload_id: int, target: Path) -> Path:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Rejected rows"
        ws.append(["Row", "Reason", "Data"])
        for r in self.rejects(upload_id):
            ws.append([r.row_no, r.reason, r.raw_json])
        wb.save(target)
        return target
