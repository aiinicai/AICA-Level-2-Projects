"""Excel upload: validate everything first, show an error report, commit only when the file is clean."""
import io
import json
import re
from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal

from flask import (Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for)
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from . import gst, services as sv
from .auth import approver_required
from .extensions import db
from .models import (CANCELLED, FINAL, Challan, ChallanLine, Counter, Plant, Receipt, SeriesConfig, UploadBatch, Vendor, now)

bp = Blueprint("uploads", __name__, url_prefix="/upload")

VENDOR_COLS = [("Vendor Name*", "name"), ("Address*", "address"), ("State* (name or code)", "state"), ("PIN Code*", "pin"),
               ("GSTIN", "gstin"), ("Contact Person", "contact_person"), ("Phone", "phone"), ("Email", "email"),
               ("ERP Vendor Code", "erp_code")]
CHALLAN_COLS = [("Challan Type* (MRC/MNRC)", "ctype"), ("Challan No*", "number"), ("Challan Date*", "date"),
                ("Plant Code*", "plant"), ("Vendor No or GSTIN*", "vendor"), ("Place of Supply (state, blank=vendor state)", "pos"),
                ("Purpose*", "purpose"), ("Purpose Detail", "purpose_text"), ("Reason*", "reason"),
                ("Corrective Action", "corrective_action"), ("Corrective Owner", "corrective_owner"),
                ("Corrective Target Date", "corrective_target_date"), ("Expected Return Date", "expected_return_date"),
                ("Goods Category (INPUTS/CAPITAL)", "goods_category"), ("Transport Mode", "transport_mode"),
                ("Vehicle No", "vehicle_no"), ("Transporter Name", "transporter_name"), ("Transporter ID", "transporter_id"),
                ("Ref Doc No", "ref_doc_no"), ("Ref Doc Date", "ref_doc_date"), ("E-way Bill No", "ewb_no"),
                ("E-way Bill Date", "ewb_date"), ("E-way Valid Upto", "ewb_valid_upto"), ("Status (FINAL/CANCELLED)", "status"),
                ("Cancel Reason", "cancel_reason"), ("Line No*", "line_no"), ("Part No*", "part_no"),
                ("Description*", "description"), ("HSN*", "hsn"), ("Qty*", "qty"), ("UoM*", "uom"), ("Rate*", "rate"),
                ("GST Rate %*", "tax_rate"), ("Cess Rate %", "cess_rate"), ("Qty Already Received", "qty_received")]
REQ_V = {"name", "address", "state", "pin"}
REQ_C = {"ctype", "number", "date", "plant", "vendor", "purpose", "reason", "part_no", "description", "hsn", "qty", "uom", "rate", "tax_rate"}


def _key(h):
    return re.sub(r"[^a-z0-9]", "", str(h or "").split("(")[0].lower())


def template_book(kind):
    cols = VENDOR_COLS if kind == "vendors" else CHALLAN_COLS
    wb = Workbook()
    ws = wb.active
    ws.title = "Vendors" if kind == "vendors" else "Challans"
    ws.append([c for c, _ in cols])
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDE6F0" if "*" not in str(cell.value) else "FCE8B2")
    for i in range(1, len(cols) + 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = 22
    ws.freeze_panes = "A2"
    ins = wb.create_sheet("Instructions")
    notes = (["VENDOR MASTER UPLOAD", "Columns marked * are mandatory. Delete nothing in row 1; add your data from row 2.",
              "GSTIN (if given) must be 15 characters, valid, and its first 2 digits must match the state.",
              "Vendors whose GSTIN or very similar name already exist are reported (GSTIN duplicates are errors, similar names are warnings).",
              "A vendor number (MV-0001...) is generated automatically. ERP Vendor Code may be left blank."]
             if kind == "vendors" else
             ["HISTORICAL CHALLAN UPLOAD - one row per LINE ITEM. Header columns are repeated on each line of the same Challan No.",
              "Challan numbers are kept exactly as given (max 16 characters, unique). The numbering series continues after the highest uploaded number for each type and financial year.",
              "Vendor must already exist (upload the vendor master first). Use Vendor No (MV-0001) or the vendor's GSTIN.",
              "Plant Code must exist under Admin > Plants. Dates: DD-MM-YYYY or YYYY-MM-DD (or real Excel dates).",
              "Purpose must be one of: " + ", ".join(sv.PURPOSES),
              "Status is FINAL unless the challan was cancelled (then CANCELLED + Cancel Reason).",
              "E-way Bill No blank = shows in the Pending E-way Bill list.",
              "MRC: Expected Return Date and Goods Category are needed to track overdue/statutory limits. Missing corrective action is accepted for history and treated as 'Done - migrated'.",
              "Qty Already Received (MRC) creates a single 'MIGRATED' receipt so balances are right."])
    for n in notes:
        ins.append([n])
    ins.column_dimensions["A"].width = 150
    if kind == "challans":
        ex = wb.create_sheet("Example")
        ex.append([c for c, _ in cols])
        ex.append(["MRC", "MRC/25-26/0001", "15-06-2025", "PNQ1", "MV-0001", "", "Calibration", "", "Calibrator not in ERP",
                   "Create vendor in ERP", "Purchase", "30-06-2025", "15-07-2025", "CAPITAL", "Road", "MH12AB1234", "", "",
                   "", "", "", "", "", "FINAL", "", 1, "CMM-PRB-01", "CMM probe", "9031", 1, "NOS", 45000, 18, 0, 0])
    return wb


def _sheet_rows(fileobj, kind):
    wb = load_workbook(fileobj, data_only=True, read_only=True)
    ws = wb["Vendors" if kind == "vendors" else "Challans"] if ("Vendors" if kind == "vendors" else "Challans") in wb.sheetnames else wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    head = next(it, None)
    if not head:
        raise ValueError("The sheet is empty.")
    cols = VENDOR_COLS if kind == "vendors" else CHALLAN_COLS
    want = {_key(label): field for label, field in cols}
    idx = {want[_key(h)]: i for i, h in enumerate(head) if _key(h) in want}
    req = REQ_V if kind == "vendors" else REQ_C
    missing = [f for f in req if f not in idx]
    if missing:
        raise ValueError("Missing column(s): " + ", ".join(missing) + ". Please download a fresh template.")
    rows = []
    for n, r in enumerate(it, start=2):
        vals = {}
        for f, i in idx.items():
            v = r[i] if i < len(r) else None
            if isinstance(v, datetime):
                v = v.date().isoformat()
            elif isinstance(v, date):
                v = v.isoformat()
            elif isinstance(v, float) and v.is_integer():
                v = str(int(v))
            vals[f] = "" if v is None else str(v).strip()
        if any(vals.values()):
            vals["_row"] = n
            rows.append(vals)
    return rows


def _pd(s):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s[:10] if fmt == "%Y-%m-%d" else s, fmt).date()
        except ValueError:
            continue
    return None


# ------------------------------------------------------------------ validation
def validate_vendors(rows):
    errs, warns, seen_g, seen_n = [], [], {}, {}
    clean = []
    for r in rows:
        n = r["_row"]
        st = gst.state_code_from_text(r["state"])
        c, e = sv.clean_vendor({**r, "state_code": st or ""})
        if r["state"] and not st:
            e.append(f"State '{r['state']}' not recognised.")
        if r.get("erp_code") and len(r["erp_code"]) > 30:
            e.append("ERP code too long.")
        c["erp_code"] = (r.get("erp_code") or "").upper() or None
        clash, similar = sv.find_vendor_duplicates(c["name"], c["gstin"])
        if clash:
            e.append(f"GSTIN already in master as {clash.vendor_no} ({clash.name}).")
        for v in similar:
            warns.append((n, f"Similar to existing vendor {v.vendor_no} - {v.name}; it will still be added."))
        if c["gstin"]:
            if c["gstin"] in seen_g:
                e.append(f"GSTIN repeated in this file (row {seen_g[c['gstin']]}).")
            seen_g[c["gstin"]] = n
        nn = gst.normalize_name(c["name"])
        if nn in seen_n and not c["gstin"]:
            e.append(f"Same name as row {seen_n[nn]} and no GSTIN to tell them apart.")
        seen_n.setdefault(nn, n)
        errs += [(n, x) for x in e]
        clean.append(c)
    return errs, warns, clean


def validate_challans(rows):
    errs, warns = [], []
    groups = OrderedDict()
    for r in rows:
        groups.setdefault(r["number"].strip().upper(), []).append(r)
    existing = {n for (n,) in db.session.query(Challan.number).filter(Challan.number.isnot(None))}
    plants = {p.code: p for p in Plant.query.all()}
    today = date.today()
    parsed = []
    for number, grp in groups.items():
        first = grp[0]
        rn = first["_row"]
        E = lambda m, row=rn: errs.append((row, f"{number}: {m}"))
        ctype = first["ctype"].upper()
        if ctype not in ("MRC", "MNRC"):
            E("Challan Type must be MRC or MNRC.")
        if not number or len(number) > 16:
            E("Challan number is missing or longer than 16 characters.")
        if number in existing:
            E("Challan number already exists in the system.")
        m = re.search(r"(\d+)$", number)
        if not m:
            E("Challan number must end with the running sequence digits.")
        cdate = _pd(first["date"])
        if not cdate or cdate > today:
            E("Challan date is invalid or in the future.")
        plant = plants.get(first["plant"].upper())
        if not plant:
            E(f"Plant code '{first['plant']}' not found.")
        key = first["vendor"].strip()
        vendor = (Vendor.query.filter_by(vendor_no=key.upper()).first() or Vendor.query.filter_by(gstin=gst.norm_gstin(key)).first())
        if not vendor:
            E(f"Vendor '{key}' not found in the vendor master (upload vendors first).")
        for r in grp[1:]:
            for f in ("ctype", "date", "vendor", "plant"):
                if r[f].upper() != first[f].upper():
                    E(f"{f} differs between lines of the same challan.", r["_row"])
        pos = gst.state_code_from_text(first.get("pos")) or (vendor.state_code if vendor else None)
        purpose = next((p for p in sv.PURPOSES if p.lower() == first["purpose"].strip().lower()), None)
        if not purpose:
            E(f"Purpose '{first['purpose']}' is not one of: {', '.join(sv.PURPOSES)}.")
        if not first["reason"]:
            E("Reason is required.")
        status = (first.get("status") or "FINAL").upper()
        if status not in ("FINAL", "CANCELLED"):
            E("Status must be FINAL or CANCELLED.")
        if status == "CANCELLED" and len(first.get("cancel_reason", "")) < 5:
            E("Cancel Reason is required for cancelled challans.")
        dates = {}
        for f in ("corrective_target_date", "expected_return_date", "ref_doc_date", "ewb_date", "ewb_valid_upto"):
            if first.get(f):
                dates[f] = _pd(first[f])
                if not dates[f]:
                    E(f"{f.replace('_', ' ')} is not a valid date.")
        if ctype == "MRC":
            if not dates.get("expected_return_date"):
                warns.append((rn, f"{number}: no expected return date - it cannot appear in the overdue report."))
            if first.get("goods_category", "").upper() not in ("INPUTS", "CAPITAL"):
                warns.append((rn, f"{number}: goods category missing - treated as INPUTS (1 year limit)."))
            if not first.get("corrective_action"):
                warns.append((rn, f"{number}: no corrective action - recorded as 'Done (migrated)'."))
        if first.get("ewb_no"):
            if not gst.EWB_RE.match(first["ewb_no"]):
                E("E-way bill number must be 12 digits.")
            if not (dates.get("ewb_date") and dates.get("ewb_valid_upto")):
                E("E-way bill date and valid-upto date are needed with the e-way bill number.")
        else:
            warns.append((rn, f"{number}: no e-way bill number - will show in the Pending E-way Bill list."))
        veh = gst.norm_vehicle(first.get("vehicle_no"))
        if veh and not gst.VEHICLE_RE.match(veh):
            E("Vehicle number format is invalid.")
        lines = []
        for r in grp:
            L = lambda msg, row=r["_row"]: errs.append((row, f"{number}: {msg}"))
            qty, rate = gst.D(r["qty"]), gst.D(r["rate"], None)
            tax, cess = gst.D(r["tax_rate"], None), gst.D(r.get("cess_rate"), Decimal(0))
            if not r["part_no"] or not r["description"] or not r["uom"]:
                L("part no, description and UoM are mandatory.")
            if not gst.valid_hsn(r["hsn"]):
                L(f"HSN '{r['hsn']}' must be 4, 6 or 8 digits.")
            if qty is None or qty <= 0:
                L("Qty must be a number greater than zero.")
            if rate is None or rate < 0:
                L("Rate must be a number >= 0.")
            if tax is None or not 0 <= tax <= 100:
                L("GST rate must be between 0 and 100.")
            rec = gst.D(r.get("qty_received"), Decimal(0))
            if rec is None or rec < 0 or (qty and rec > qty):
                L("Qty Already Received is invalid or exceeds Qty.")
            lines.append({"part_no": r["part_no"], "description": r["description"], "hsn": r["hsn"], "qty": str(qty),
                          "uom": r["uom"].upper(), "rate": str(rate), "tax_rate": str(tax), "cess_rate": str(cess),
                          "qty_received": str(rec if ctype == "MRC" else 0)})
        parsed.append({"number": number, "ctype": ctype, "date": cdate.isoformat() if cdate else None, "plant": plant.code if plant else None,
                       "vendor_id": vendor.id if vendor else None, "pos": pos, "purpose": purpose, "status": status,
                       "seq": int(m.group(1)) if m else None, "h": first, "dates": {k: v.isoformat() for k, v in dates.items() if v},
                       "lines": lines})
    return errs, warns, parsed


# ------------------------------------------------------------------ commit
def commit_vendors(clean, user):
    n = 0
    for c in clean:
        v = sv.create_vendor(c, user)
        if c.get("erp_code"):
            sv.set_erp_code(v, c["erp_code"], user)
        n += 1
    return n


def _bump_counter(key, value):
    if not db.session.get(Counter, key):
        db.session.add(Counter(key=key, last_no=0))
        db.session.flush()
    row = db.session.get(Counter, key)
    if row.last_no < value:
        row.last_no = value


def commit_challans(parsed, user):
    top = {}
    for p in sorted(parsed, key=lambda x: (x["ctype"], x["seq"])):
        h, d = p["h"], p["dates"]
        cdate = date.fromisoformat(p["date"])
        plant = Plant.query.filter_by(code=p["plant"]).one()
        ch = Challan(ctype=p["ctype"], status=p["status"], number=p["number"], fy=gst.fy_of(cdate), seq_no=p["seq"],
                     challan_date=cdate, plant_id=plant.id, vendor_id=p["vendor_id"], place_of_supply=p["pos"],
                     interstate=plant.state_code != p["pos"], purpose=p["purpose"], purpose_text=h.get("purpose_text") or None,
                     reason=h["reason"], transport_mode=h.get("transport_mode") or None,
                     vehicle_no=gst.norm_vehicle(h.get("vehicle_no")) or None, transporter_name=h.get("transporter_name") or None,
                     transporter_id=gst.norm_gstin(h.get("transporter_id")) or None, ref_doc_no=h.get("ref_doc_no") or None,
                     ref_doc_date=date.fromisoformat(d["ref_doc_date"]) if d.get("ref_doc_date") else None,
                     is_historical=True, created_by=user.username, finalized_by=user.username, finalized_at=now())
        if p["ctype"] == "MRC":
            ch.expected_return_date = date.fromisoformat(d["expected_return_date"]) if d.get("expected_return_date") else None
            ch.goods_category = h.get("goods_category", "").upper() if h.get("goods_category", "").upper() in ("INPUTS", "CAPITAL") else "INPUTS"
            ch.corrective_action = h.get("corrective_action") or None
            ch.corrective_owner = h.get("corrective_owner") or None
            ch.corrective_target_date = date.fromisoformat(d["corrective_target_date"]) if d.get("corrective_target_date") else None
            if ch.corrective_action:
                ch.corrective_status = "Open"
            else:
                ch.corrective_status, ch.corrective_remarks, ch.corrective_done_date = "Done", "Migrated - no corrective action recorded", cdate
        if h.get("ewb_no"):
            ch.ewb_no, ch.ewb_status = h["ewb_no"], "Updated"
            ch.ewb_date, ch.ewb_valid_upto = date.fromisoformat(d["ewb_date"]), date.fromisoformat(d["ewb_valid_upto"])
        if p["status"] == CANCELLED:
            ch.cancel_reason, ch.cancelled_by, ch.cancelled_at = h["cancel_reason"], user.username, now()
        db.session.add(ch)
        for i, l in enumerate(p["lines"], 1):
            ch.lines.append(ChallanLine(line_no=i, part_no=l["part_no"], description=l["description"], hsn=l["hsn"],
                                        qty=Decimal(l["qty"]), uom=l["uom"], rate=Decimal(l["rate"]),
                                        tax_rate=Decimal(l["tax_rate"]), cess_rate=Decimal(l["cess_rate"]),
                                        qty_received=Decimal(l["qty_received"])))
        db.session.flush()
        sv.recompute(ch)
        sv.take_snapshots(ch)
        for ln in ch.lines:
            if ln.qty_received and ln.qty_received > 0:
                db.session.add(Receipt(challan_id=ch.id, line_id=ln.id, received_date=date.today(), qty=ln.qty_received,
                                       doc_ref="MIGRATED", remarks="Balance carried from historical upload", created_by=user.username))
        sv.refresh_return_status(ch)
        sv.audit(user, "challan", ch.id, ch.number, "IMPORT", "Historical challan uploaded from Excel")
        k = f"{p['ctype']}|{ch.fy}"
        top[k] = max(top.get(k, 0), p["seq"])
    for k, v in top.items():
        _bump_counter(k, v)           # numbering carries on after the highest uploaded number
    return len(parsed)


# ------------------------------------------------------------------ views
@bp.route("/")
def index():
    batches = UploadBatch.query.order_by(UploadBatch.id.desc()).limit(10).all()
    return render_template("uploads/index.html", batches=batches)


@bp.route("/template/<kind>")
def template(kind):
    if kind not in ("vendors", "challans"):
        abort(404)
    buf = io.BytesIO()
    template_book(kind).save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"template_{kind}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.route("/<kind>", methods=["POST"])
@approver_required
def upload(kind):
    if kind not in ("vendors", "challans"):
        abort(404)
    if kind == "challans" and not g.user.is_admin:
        abort(403)
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".xlsx"):
        flash("Choose an .xlsx file (use the downloadable template).", "error")
        return redirect(url_for("uploads.index"))
    try:
        rows = _sheet_rows(f.stream, kind)
    except Exception as e:                 # noqa - any unreadable file is reported to the user
        flash(f"Could not read the file: {e}", "error")
        return redirect(url_for("uploads.index"))
    if not rows:
        flash("The file has no data rows.", "error")
        return redirect(url_for("uploads.index"))
    errs, warns, _ = (validate_vendors if kind == "vendors" else validate_challans)(rows)
    b = UploadBatch(kind=kind, filename=f.filename[:200], payload=json.dumps(rows), errors=json.dumps(errs),
                    warnings=json.dumps(warns), created_by=g.user.username)
    db.session.add(b)
    db.session.commit()
    return redirect(url_for("uploads.batch", bid=b.id))


@bp.route("/batch/<int:bid>")
def batch(bid):
    b = db.get_or_404(UploadBatch, bid)
    return render_template("uploads/batch.html", b=b, errors=json.loads(b.errors), warnings=json.loads(b.warnings),
                           n=len(json.loads(b.payload)))


@bp.route("/batch/<int:bid>/errors.xlsx")
def error_report(bid):
    b = db.get_or_404(UploadBatch, bid)
    wb = Workbook()
    ws = wb.active
    ws.title = "Validation report"
    ws.append(["Excel row", "Severity", "Message"])
    for row, m in json.loads(b.errors):
        ws.append([row, "ERROR", m])
    for row, m in json.loads(b.warnings):
        ws.append([row, "Warning", m])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.column_dimensions["C"].width = 120
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"upload_{bid}_validation.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.route("/batch/<int:bid>/commit", methods=["POST"])
@approver_required
def commit(bid):
    b = db.get_or_404(UploadBatch, bid)
    if b.status != "PENDING":
        flash("This upload was already processed.", "error")
        return redirect(url_for("uploads.batch", bid=bid))
    rows = json.loads(b.payload)
    errs, _, data = (validate_vendors if b.kind == "vendors" else validate_challans)(rows)   # re-check: data may have changed
    if errs:
        b.errors = json.dumps(errs)
        db.session.commit()
        flash("The data changed since validation and now has errors. Nothing was imported.", "error")
        return redirect(url_for("uploads.batch", bid=bid))
    try:
        n = (commit_vendors if b.kind == "vendors" else commit_challans)(data, g.user)
        b.status = "COMMITTED"
        sv.audit(g.user, "upload", b.id, b.filename, "COMMIT", f"{b.kind}: {n} record(s)")
        db.session.commit()
        flash(f"Imported {n} {b.kind[:-1]}(s) successfully.", "ok")
    except Exception as e:                  # noqa - all-or-nothing
        db.session.rollback()
        flash(f"Import failed and was rolled back: {e}", "error")
    return redirect(url_for("uploads.batch", bid=bid))


@bp.route("/batch/<int:bid>/discard", methods=["POST"])
def discard(bid):
    b = db.get_or_404(UploadBatch, bid)
    if b.status == "PENDING":
        b.status = "DISCARDED"
        db.session.commit()
    return redirect(url_for("uploads.index"))

