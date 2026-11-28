"""Business rules. Views stay thin; everything that must be correct lives here."""
import json
from datetime import date, datetime
from decimal import Decimal
from difflib import SequenceMatcher

from sqlalchemy.exc import IntegrityError

from . import gst
from .extensions import db
from .models import (ADMIN, APPROVER, CANCELLED, DRAFT, FINAL, MNRC, MRC, AuditLog, Challan, ChallanLine,
                     Counter, Plant, Receipt, SeriesConfig, Vendor, now)

PURPOSES = {
    "Job work": [MRC],
    "Rework": [MRC],
    "Calibration": [MRC],
    "Returnable packing": [MRC],
    "Return of customer material": [MNRC],
    "Return of sister-entity asset": [MNRC],
    "Other": [MRC, MNRC],
}
TRANSPORT_MODES = ["Road", "Rail", "Air", "Ship", "Courier", "By hand"]
UOMS = ["NOS", "KGS", "MTR", "SET", "PCS", "LTR", "BOX", "PAIR", "UNT"]


def purposes_for(ctype):
    return [p for p, t in PURPOSES.items() if ctype in t]


# --------------------------------------------------------------------------- audit
def audit(user, entity, entity_id, ref, action, details=""):
    db.session.add(AuditLog(username=getattr(user, "username", user) or "system", entity=entity,
                            entity_id=entity_id, ref=ref, action=action, details=details))


# --------------------------------------------------------------------------- numbering
def next_counter(key):
    """Atomically increment and return the counter. Must run inside the caller's transaction:
    the UPDATE takes the write lock (SQLite) / row lock (PostgreSQL) until commit, which is what makes
    simultaneous saves safe and keeps the series gap-free on rollback."""
    if not db.session.get(Counter, key):
        try:
            with db.session.begin_nested():
                db.session.add(Counter(key=key, last_no=0))
        except IntegrityError:
            pass            # another user created it first
    db.session.flush()
    db.session.execute(db.update(Counter).where(Counter.key == key).values(last_no=Counter.last_no + 1))
    row = db.session.get(Counter, key)
    db.session.refresh(row)
    return row.last_no


def format_number(cfg, fy, seq):
    fy_txt = gst.fy_short(fy) if cfg.fy_style == "short" else fy
    sep = cfg.separator
    return f"{cfg.prefix}{sep}{fy_txt}{sep}{seq:0{cfg.pad}d}"


def check_series_config(prefix, fy_style, separator, pad):
    errs = []
    if not prefix or not prefix.replace("-", "").isalnum():
        errs.append("Prefix must be letters/digits only.")
    if separator not in ("/", "-"):
        errs.append("Separator must be / or -.")
    if not 3 <= pad <= 6:
        errs.append("Sequence width must be between 3 and 6.")
    if not errs:
        sample = f"{prefix}{separator}{'2026-27' if fy_style == 'long' else '26-27'}{separator}{'9' * pad}"
        if len(sample) > 16:
            errs.append(f"Format would produce numbers of {len(sample)} characters ({sample}); "
                        "GST allows at most 16. Use the short FY style, a shorter prefix or narrower width.")
    return errs


def finalize(ch, user):
    """Assign the number and lock in snapshots. Caller commits (number + data commit together)."""
    if ch.status != DRAFT:
        raise ValueError("Only a draft can be finalised.")
    check_vendor_rule(ch.ctype, ch.vendor, user)
    cfg = db.session.get(SeriesConfig, ch.ctype)
    ch.fy = gst.fy_of(ch.challan_date)
    seq = next_counter(f"{ch.ctype}|{ch.fy}")
    if seq >= 10 ** cfg.pad:
        raise ValueError("Numbering series is exhausted for this year; ask Admin to widen the sequence.")
    ch.seq_no = seq
    ch.number = format_number(cfg, ch.fy, seq)
    ch.status = FINAL
    ch.finalized_by, ch.finalized_at = user.username, now()
    if ch.is_returnable:
        ch.return_status = "Open"
        ch.corrective_status = ch.corrective_status or "Open"
    take_snapshots(ch)
    audit(user, "challan", ch.id, ch.number, "FINALISE", "Number assigned")


def take_snapshots(ch):
    p, v = ch.plant, ch.vendor
    ch.consignor_json = json.dumps({"company": p.company_name, "address": p.address, "pin": p.pin,
                                    "state_code": p.state_code, "gstin": p.gstin, "phone": p.phone,
                                    "email": p.email, "signatory": p.signatory, "code": p.code})
    ch.consignee_json = json.dumps({"vendor_no": v.vendor_no, "name": v.name, "address": v.address,
                                    "pin": v.pin, "state_code": v.state_code, "gstin": v.gstin, "pan": v.pan})


def consignor(ch):
    if ch.consignor_json:
        return json.loads(ch.consignor_json)
    p = ch.plant
    return {"company": p.company_name, "address": p.address, "pin": p.pin, "state_code": p.state_code,
            "gstin": p.gstin, "phone": p.phone, "email": p.email, "signatory": p.signatory, "code": p.code}


def consignee(ch):
    if ch.consignee_json:
        return json.loads(ch.consignee_json)
    v = ch.vendor
    return {"vendor_no": v.vendor_no, "name": v.name, "address": v.address, "pin": v.pin,
            "state_code": v.state_code, "gstin": v.gstin, "pan": v.pan}


# --------------------------------------------------------------------------- vendors
def check_vendor_rule(ctype, vendor, user):
    """Blocking rule: no new returnable manual challan for a vendor that exists in the ERP (Admin exempt)."""
    if ctype == MRC and vendor.erp_code and user.role != ADMIN:
        raise ValueError(f"This vendor is now set up in the ERP (Vendor Code: {vendor.erp_code}). "
                         "Please generate the returnable challan from the ERP system.")


def find_vendor_duplicates(name, gstin, exclude_id=None):
    """Return (gstin_clash_vendor | None, [similar-name vendors])."""
    clash = None
    if gstin:
        clash = Vendor.query.filter(Vendor.gstin == gstin).first()
        if clash and clash.id == exclude_id:
            clash = None
    norm = gst.normalize_name(name)
    similar = []
    for v in Vendor.query.all():
        if v.id == exclude_id or (clash and v.id == clash.id):
            continue
        vn = v.name_norm or gst.normalize_name(v.name)
        if vn == norm or (norm and SequenceMatcher(None, vn, norm).ratio() >= 0.85):
            similar.append(v)
    return clash, similar


def clean_vendor(data, exclude_id=None):
    """Validate vendor fields. Returns (cleaned dict, errors list)."""
    errs, c = [], {}
    c["name"] = (data.get("name") or "").strip()
    c["address"] = (data.get("address") or "").strip()
    c["pin"] = (data.get("pin") or "").strip()
    c["gstin"] = gst.norm_gstin(data.get("gstin")) or None
    c["state_code"] = (data.get("state_code") or "").strip()
    for f in ("contact_person", "phone", "email"):
        c[f] = (data.get(f) or "").strip() or None
    if not c["name"]:
        errs.append("Vendor name is required.")
    if not c["address"]:
        errs.append("Address is required.")
    if not gst.PIN_RE.match(c["pin"]):
        errs.append("PIN code must be 6 digits.")
    if c["gstin"]:
        errs += gst.validate_gstin(c["gstin"])
        if c["gstin"][:2] in gst.STATES:
            c["state_code"] = c["state_code"] or c["gstin"][:2]
    if c["state_code"] not in gst.STATES:
        errs.append("Select a valid state.")
    elif c["gstin"] and c["gstin"][:2] != c["state_code"]:
        errs.append(f"GSTIN's first two digits ({c['gstin'][:2]}) do not match state code {c['state_code']}.")
    if c["email"] and "@" not in c["email"]:
        errs.append("Email looks invalid.")
    c["pan"] = gst.pan_from_gstin(c["gstin"]) if c["gstin"] else None
    return c, errs


def create_vendor(c, user):
    seq = next_counter("VENDOR")
    v = Vendor(vendor_no=f"MV-{seq:04d}", name=c["name"], name_norm=gst.normalize_name(c["name"]),
               address=c["address"], state_code=c["state_code"], pin=c["pin"], gstin=c["gstin"], pan=c["pan"],
               contact_person=c["contact_person"], phone=c["phone"], email=c["email"],
               created_by=user.username)
    db.session.add(v)
    db.session.flush()
    audit(user, "vendor", v.id, v.vendor_no, "CREATE", v.name)
    return v


def set_erp_code(vendor, code, user):
    code = (code or "").strip().upper()
    if not code:
        if not user.is_admin:
            raise ValueError("Only Admin can clear an ERP vendor code.")
        vendor.erp_code = None
    else:
        if len(code) > 30 or not code.replace("-", "").replace("/", "").isalnum():
            raise ValueError("ERP vendor code may contain letters, digits, - and / only.")
        other = Vendor.query.filter(Vendor.erp_code == code, Vendor.id != vendor.id).first()
        if other:
            raise ValueError(f"ERP code {code} is already used by {other.vendor_no} ({other.name}).")
        vendor.erp_code = code
    vendor.erp_code_updated_at, vendor.erp_code_updated_by = now(), user.username
    audit(user, "vendor", vendor.id, vendor.vendor_no, "ERP_CODE", code or "(cleared)")


# --------------------------------------------------------------------------- challan form
def _date(s):
    try:
        return datetime.strptime((s or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_challan_form(form, ctype, user, lines_locked=False):
    """Validate a posted challan form. Returns (header dict, line dicts, errors)."""
    errs, today = [], date.today()
    g = lambda k: (form.get(k) or "").strip()
    h = {k: g(k) or None for k in ("purpose_text", "corrective_action", "corrective_owner", "remarks",
                                    "transporter_name", "ref_doc_no", "transport_mode")}
    h["reason"] = g("reason")
    h["purpose"] = g("purpose")
    h["challan_date"] = _date(g("challan_date"))
    h["ref_doc_date"] = _date(g("ref_doc_date"))
    h["corrective_target_date"] = _date(g("corrective_target_date"))
    h["expected_return_date"] = _date(g("expected_return_date"))
    h["goods_category"] = g("goods_category") or None
    h["vehicle_no"] = gst.norm_vehicle(g("vehicle_no")) or None
    h["transporter_id"] = gst.norm_gstin(g("transporter_id")) or None
    h["plant_id"] = int(g("plant_id")) if g("plant_id").isdigit() else None
    h["vendor_id"] = int(g("vendor_id")) if g("vendor_id").isdigit() else None
    h["place_of_supply"] = g("place_of_supply")

    if not h["challan_date"]:
        errs.append("Challan date is required.")
    elif h["challan_date"] > today:
        errs.append("Challan date cannot be in the future.")
    plant = db.session.get(Plant, h["plant_id"]) if h["plant_id"] else None
    if not plant or not plant.active:
        errs.append("Select the issuing plant.")
    vendor = db.session.get(Vendor, h["vendor_id"]) if h["vendor_id"] else None
    if not vendor or not vendor.active:
        errs.append("Select a vendor / consignee (add a new one if it is not in the master).")
    else:
        try:
            check_vendor_rule(ctype, vendor, user)
        except ValueError as e:
            errs.append(str(e))
        if not h["place_of_supply"]:
            h["place_of_supply"] = vendor.state_code
    if h["place_of_supply"] not in gst.STATES:
        errs.append("Place of supply is required.")
    if h["purpose"] not in purposes_for(ctype):
        errs.append("Select a valid purpose for this challan type.")
    if h["purpose"] == "Other" and not h["purpose_text"]:
        errs.append("Describe the purpose when 'Other' is selected.")
    if not h["reason"]:
        errs.append("Reason is required." if ctype == MRC else "Reason / business justification is required.")
    if ctype == MRC:
        # corrective action / owner / target / expected return are no longer asked on the form (optional)
        if h["expected_return_date"] and h["challan_date"] and h["expected_return_date"] < h["challan_date"]:
            errs.append("Expected return date cannot be before the challan date.")
        if h["goods_category"] not in ("INPUTS", "CAPITAL"):
            errs.append("Select goods category (inputs / capital goods) - it sets the job-work time limit.")
    else:
        for k in ("corrective_action", "corrective_owner", "corrective_target_date", "expected_return_date",
                  "goods_category"):
            h[k] = None
    if h["vehicle_no"] and not gst.VEHICLE_RE.match(h["vehicle_no"]):
        errs.append("Vehicle number format looks invalid (e.g. MH12AB1234).")
    if h["transporter_id"] and gst.validate_gstin(h["transporter_id"]):
        errs.append("Transporter ID must be a valid 15-character GSTIN.")
    if h["ref_doc_date"] and h["ref_doc_date"] > today:
        errs.append("Reference document date cannot be in the future.")
    if h["ref_doc_no"] and not h["ref_doc_date"]:
        errs.append("Enter the reference document date.")

    lines = []
    if not lines_locked:
        n = len(form.getlist("part_no"))
        for i in range(n):
            f = lambda k: (form.getlist(k)[i] if i < len(form.getlist(k)) else "").strip()
            if not any(f(k) for k in ("part_no", "description", "hsn", "qty", "rate")):
                continue
            ln = {"part_no": f("part_no"), "description": f("description"), "hsn": f("hsn"),
                  "uom": f("uom").upper(), "qty": gst.D(f("qty")), "rate": gst.D(f("rate"), Decimal(0)),
                  "tax_rate": gst.D(f("tax_rate"), Decimal(0)), "cess_rate": gst.D(f("cess_rate"), Decimal(0))}
            tag = f"Line {len(lines) + 1}: "
            if not ln["part_no"]:
                errs.append(tag + "part number is required.")
            if not ln["description"]:
                errs.append(tag + "description is required.")
            if not gst.valid_hsn(ln["hsn"]):
                errs.append(tag + "HSN must be 4, 6 or 8 digits.")
            if ln["qty"] is None or ln["qty"] <= 0:
                errs.append(tag + "quantity must be greater than zero.")
            if not ln["uom"]:
                errs.append(tag + "unit of measure is required.")
            if ln["rate"] is None or ln["rate"] < 0:
                errs.append(tag + "rate is invalid.")
            if not (0 <= ln["tax_rate"] <= 100) or not (0 <= ln["cess_rate"] <= 500):
                errs.append(tag + "tax / cess rate is out of range.")
            lines.append(ln)
        if not lines:
            errs.append("Add at least one line item.")
    if plant and h["place_of_supply"] in gst.STATES:
        h["interstate"] = plant.state_code != h["place_of_supply"]
    return h, lines, errs


def apply_challan(ch, h, lines, lines_locked=False):
    """Copy validated data onto the challan and recompute all tax figures."""
    for k, v in h.items():
        setattr(ch, k, v)
    if not lines_locked:
        ch.lines.clear()
        db.session.flush()
        for i, ln in enumerate(lines, 1):
            ch.lines.append(ChallanLine(line_no=i, **ln))
    recompute(ch)


def recompute(ch):
    tot = {k: Decimal(0) for k in ("taxable", "cgst", "sgst", "igst", "cess")}
    for ln in ch.lines:
        r = gst.compute_line(Decimal(ln.qty), Decimal(ln.rate), Decimal(ln.tax_rate), Decimal(ln.cess_rate),
                             ch.interstate)
        ln.taxable_value, ln.cgst, ln.sgst, ln.igst, ln.cess = r["taxable"], r["cgst"], r["sgst"], r["igst"], r["cess"]
        for k in tot:
            tot[k] += r[k]
    ch.taxable_total, ch.cgst_total, ch.sgst_total = tot["taxable"], tot["cgst"], tot["sgst"]
    ch.igst_total, ch.cess_total = tot["igst"], tot["cess"]
    ch.grand_total = sum(tot.values(), Decimal(0))


HEADER_FIELDS = ["challan_date", "plant_id", "vendor_id", "place_of_supply", "purpose", "purpose_text", "reason",
                 "corrective_action", "corrective_owner", "corrective_target_date", "expected_return_date",
                 "goods_category", "transport_mode", "vehicle_no", "transporter_name", "transporter_id",
                 "ref_doc_no", "ref_doc_date", "remarks"]


def header_snapshot(ch):
    d = {k: getattr(ch, k) for k in HEADER_FIELDS}
    d["lines"] = "; ".join(f"{l.part_no} x{l.qty} @{l.rate} tax{l.tax_rate}" for l in ch.lines)
    return d


def diff_text(old, new):
    return "; ".join(f"{k}: {old[k]!s} -> {new[k]!s}" for k in new if old.get(k) != new[k]) or "no change"


def can_edit(ch, user):
    if ch.status == DRAFT:
        return user.is_approver or ch.created_by == user.username
    return ch.status == FINAL and user.is_admin


# --------------------------------------------------------------------------- tracking actions
def update_ewb(ch, form, user):
    if ch.status != FINAL:
        raise ValueError("E-way bill can be recorded only on a finalised, non-cancelled challan.")
    no, d, v = (form.get("ewb_no") or "").strip(), _date(form.get("ewb_date")), _date(form.get("ewb_valid_upto"))
    if not gst.EWB_RE.match(no):
        raise ValueError("E-way bill number must be 12 digits.")
    if not d or d > date.today():
        raise ValueError("Enter a valid e-way bill date (not in the future).")
    if d < ch.challan_date:
        raise ValueError("E-way bill date cannot be before the challan date.")
    if not v or v < d:
        raise ValueError("Valid-upto date must be on or after the e-way bill date.")
    ch.ewb_no, ch.ewb_date, ch.ewb_valid_upto, ch.ewb_status = no, d, v, "Updated"
    ch.updated_by = user.username
    audit(user, "challan", ch.id, ch.number, "EWB_UPDATE", f"{no} dated {d} valid to {v}")


def record_receipt(ch, form, user):
    if ch.status != FINAL or not ch.is_returnable:
        raise ValueError("Receipts apply only to finalised returnable challans.")
    d = _date(form.get("received_date"))
    ref = (form.get("doc_ref") or "").strip()
    if not d or d > date.today() or d < ch.challan_date:
        raise ValueError("Received date must be between the challan date and today.")
    if not ref:
        raise ValueError("Enter our receiving document reference.")
    got = 0
    for ln in ch.lines:
        q = gst.D(form.get(f"qty_{ln.id}"), Decimal(0))
        if q < 0:
            raise ValueError("Quantity cannot be negative.")
        if q == 0:
            continue
        if q > Decimal(ln.qty) - Decimal(ln.qty_received or 0):
            raise ValueError(f"{ln.part_no}: received quantity exceeds the pending quantity.")
        db.session.add(Receipt(challan_id=ch.id, line_id=ln.id, received_date=d, qty=q, doc_ref=ref,
                               remarks=(form.get("remarks") or "").strip() or None, created_by=user.username))
        ln.qty_received = Decimal(ln.qty_received or 0) + q
        got += 1
    if not got:
        raise ValueError("Enter a received quantity for at least one line.")
    refresh_return_status(ch)
    audit(user, "challan", ch.id, ch.number, "RECEIPT", f"{ref} on {d}; status {ch.return_status}")


def refresh_return_status(ch):
    if not ch.is_returnable:
        return
    rec, tot = ch.received_qty, ch.total_qty
    ch.return_status = "Closed" if rec >= tot else ("Partially Received" if rec > 0 else "Open")


def update_corrective(ch, form, user):
    if not ch.is_returnable or ch.status != FINAL:
        raise ValueError("Corrective action applies to finalised returnable challans.")
    status = form.get("corrective_status")
    if status not in ("Open", "Done"):
        raise ValueError("Invalid status.")
    ch.corrective_status = status
    ch.corrective_remarks = (form.get("corrective_remarks") or "").strip() or None
    if status == "Done":
        d = _date(form.get("corrective_done_date")) or date.today()
        if d > date.today():
            raise ValueError("Completion date cannot be in the future.")
        ch.corrective_done_date = d
    else:
        ch.corrective_done_date = None
    new_t = _date(form.get("corrective_target_date"))
    if new_t:
        ch.corrective_target_date = new_t
    audit(user, "challan", ch.id, ch.number, "CORRECTIVE", f"{status}; {ch.corrective_remarks or ''}")


def cancel_challan(ch, reason, user):
    if ch.status != FINAL:
        raise ValueError("Only finalised challans can be cancelled (delete a draft instead).")
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise ValueError("A cancellation reason is mandatory.")
    if ch.received_qty > 0:
        raise ValueError("Goods have already been received against this challan; it cannot be cancelled.")
    ch.status, ch.cancel_reason = CANCELLED, reason
    ch.cancelled_by, ch.cancelled_at = user.username, now()
    audit(user, "challan", ch.id, ch.number, "CANCEL", reason)
