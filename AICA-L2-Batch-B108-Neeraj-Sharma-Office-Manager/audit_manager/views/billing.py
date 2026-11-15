import io
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for

from .. import log_activity, parse_date, to_float
from ..access import can_access_client, manager_required, visible_clients
from ..models import Client, FirmSetting, Invoice, Payment, ServiceItem, db
from ..services import billing as svc
from ..services import mailer

bp = Blueprint("billing", __name__, url_prefix="/billing")


def _invoice(invoice_id: int) -> Invoice:
    inv = db.get_or_404(Invoice, invoice_id)
    if not can_access_client(g.user, inv.client):
        abort(403)
    return inv


@bp.route("/")
@manager_required
def index():
    ids = [c.id for c in visible_clients(g.user).all()]
    q = Invoice.query.filter(Invoice.client_id.in_(ids))
    status, client_id = request.args.get("status", ""), request.args.get("client_id", type=int)
    if status:
        q = q.filter(Invoice.status == status)
    if client_id:
        q = q.filter(Invoice.client_id == client_id)
    base = Invoice.query.filter(Invoice.client_id.in_(ids))
    if client_id:
        base = base.filter(Invoice.client_id == client_id)
    counts = dict(base.with_entities(Invoice.status, db.func.count()).group_by(Invoice.status).all())
    invoices = q.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).limit(300).all()
    totals = {"billed": sum(i.total_amount for i in invoices), "paid": sum(i.paid_amount for i in invoices),
              "due": sum(i.balance for i in invoices)}
    return render_template("billing/index.html", invoices=invoices, status=status, client_id=client_id, totals=totals, counts=counts,
                           clients=visible_clients(g.user).order_by(Client.name).all())


@bp.route("/new", methods=["GET", "POST"])
@manager_required
def new():
    clients = visible_clients(g.user).order_by(Client.name).all()
    if request.method == "POST":
        f = request.form
        client = db.session.get(Client, f.get("client_id", type=int) or 0)
        if not client or not can_access_client(g.user, client):
            flash("Choose a client.", "danger")
        else:
            descs, qtys, rates, sacs = (f.getlist(k) for k in ("description", "quantity", "rate", "sac_code"))
            items = []
            for i, d in enumerate(descs):
                if d.strip():
                    items.append({"description": d.strip(), "quantity": to_float(qtys[i], 1) or 1.0, "rate": to_float(rates[i]),
                                  "sac_code": sacs[i].strip() if i < len(sacs) else ""})
            tax_mode = f.get("tax_mode") if f.get("tax_mode") in svc.TAX_MODES else "cgst_sgst"
            if not items:
                flash("Add at least one service line.", "danger")
            elif any(it["rate"] < 0 for it in items):
                flash("Rates cannot be negative.", "danger")
            else:
                inv_date = parse_date(f.get("invoice_date")) or date.today()
                inv = svc.create_invoice(client.id, inv_date, parse_date(f.get("due_date")), tax_mode, items,
                                         to_float(f.get("discount_amount")), f.get("notes", "").strip(), g.user.id)
                log_activity("billing", f"Created invoice {inv.invoice_number} for {client.name}")
                db.session.commit()
                from ..services import automation

                automation.fire("invoice_created", client=client, user_id=g.user.id,
                                values={"invoice_number": inv.invoice_number, "amount": f"{inv.total_amount:,.2f}",
                                        "due_date": f"{inv.due_date:%d-%b-%Y}" if inv.due_date else "On receipt"},
                                attachments=[(inv.invoice_number.replace("/", "-") + ".pdf", svc.invoice_pdf(inv), "application/pdf")])
                db.session.commit()
                flash(f"Invoice {inv.invoice_number} created.", "success")
                return redirect(url_for("billing.show", invoice_id=inv.id))
    return render_template("billing/new.html", clients=clients, tax_modes=svc.TAX_MODES,
                           preselect=request.args.get("client_id", type=int), today=date.today(),
                           services=[{"name": x.name, "sac": x.sac_code or "", "rate": x.default_rate or 0}
                                     for x in ServiceItem.query.filter_by(active=True).order_by(ServiceItem.name)],
                           rates={"cgst": svc.default_rate("default_cgst_rate", 9), "sgst": svc.default_rate("default_sgst_rate", 9),
                                  "igst": svc.default_rate("default_igst_rate", 18)})


@bp.route("/<int:invoice_id>")
@manager_required
def show(invoice_id):
    return render_template("billing/show.html", inv=_invoice(invoice_id), modes=svc.PAYMENT_MODES, tax_modes=svc.TAX_MODES,
                           mail_ready=mailer.is_configured())


@bp.route("/<int:invoice_id>/payment", methods=["POST"])
@manager_required
def payment(invoice_id):
    inv = _invoice(invoice_id)
    amount = to_float(request.form.get("amount"))
    if amount <= 0:
        flash("Enter an amount greater than zero.", "danger")
    elif amount > inv.balance + 0.005:
        flash(f"That is more than the balance due ({inv.balance:,.2f}).", "danger")
    else:
        mode = request.form.get("mode") if request.form.get("mode") in svc.PAYMENT_MODES else "bank"
        db.session.add(Payment(invoice_id=inv.id, payment_date=parse_date(request.form.get("payment_date")) or date.today(), amount=amount,
                               mode=mode, reference=request.form.get("reference", "").strip() or None,
                               notes=request.form.get("notes", "").strip() or None, recorded_by_id=g.user.id))
        db.session.flush()
        db.session.refresh(inv)
        inv.sync_payments()
        log_activity("billing", f"Recorded payment of {amount:,.2f} on {inv.invoice_number}")
        db.session.commit()
        from ..services import automation

        automation.fire("payment_received", client=inv.client, user_id=g.user.id,
                        values={"invoice_number": inv.invoice_number, "amount": f"{amount:,.2f}"})
        db.session.commit()
        flash("Payment recorded.", "success")
    return redirect(url_for("billing.show", invoice_id=inv.id))


@bp.route("/<int:invoice_id>/pdf")
@manager_required
def pdf(invoice_id):
    inv = _invoice(invoice_id)
    name = inv.invoice_number.replace("/", "-") + ".pdf"
    return send_file(io.BytesIO(svc.invoice_pdf(inv)), as_attachment=request.args.get("inline") != "1", download_name=name, mimetype="application/pdf")


@bp.route("/<int:invoice_id>/preview")
@manager_required
def preview(invoice_id):
    """The invoice as it will print, on screen."""
    from ..services import letterhead

    prof = letterhead.profile()
    return render_template("billing/preview.html", inv=_invoice(invoice_id), firm=prof, contact=letterhead.contact_line(prof),
                           ids=letterhead.id_line(prof), signatory=letterhead.signatory_line(prof), tax_modes=svc.TAX_MODES)


@bp.route("/<int:invoice_id>/email", methods=["POST"])
@manager_required
def email(invoice_id):
    inv = _invoice(invoice_id)
    to = request.form.get("to", "").strip() or (inv.client.email or "")
    if "@" not in to:
        flash("The client has no email address. Enter one to send to.", "danger")
        return redirect(url_for("billing.show", invoice_id=inv.id))
    firm = FirmSetting.get("firm_name", "")
    due = f"\nDue date: {inv.due_date:%d %b %Y}" if inv.due_date else ""
    body = (f"Dear {inv.client.name},\n\nGreetings from {firm}.\n\nPlease find attached our invoice. The details are:\n\n"
            f"Invoice No.: *{inv.invoice_number}*\nInvoice date: {inv.invoice_date:%d %b %Y}\nInvoice amount: *Rs. {inv.total_amount:,.2f}*\n"
            f"Balance payable: *Rs. {inv.balance:,.2f}*{due}\n\nKindly arrange the payment at your earliest convenience.\n\n"
            f"Regards,\n{mailer.signature()}")
    ok, msg = mailer.send_mail(to, f"Invoice {inv.invoice_number} from {firm}", body,
                               [(inv.invoice_number.replace("/", "-") + ".pdf", svc.invoice_pdf(inv), "application/pdf")])
    if ok:
        log_activity("billing", f"Emailed invoice {inv.invoice_number} to {to}")
        db.session.commit()
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("billing.show", invoice_id=inv.id))


@bp.route("/<int:invoice_id>/delete", methods=["POST"])
@manager_required
def delete(invoice_id):
    inv = _invoice(invoice_id)
    if inv.payments:
        flash("This invoice has payments recorded, so it cannot be deleted.", "danger")
        return redirect(url_for("billing.show", invoice_id=inv.id))
    log_activity("billing", f"Deleted invoice {inv.invoice_number}")
    db.session.delete(inv)
    db.session.commit()
    flash("Invoice deleted.", "success")
    return redirect(url_for("billing.index"))


@bp.route("/<int:invoice_id>/whatsapp", methods=["POST"])
@manager_required
def whatsapp(invoice_id):
    """Prepare a WhatsApp message with the invoice details. WhatsApp click-to-chat cannot attach files, so the PDF is sent separately."""
    from ..services import whatsapp as wa

    inv = _invoice(invoice_id)
    text = svc.invoice_message(inv, FirmSetting.get("firm_name", "our office"))
    link = request.form.get("link", "").strip()
    if link.lower().startswith(("http://", "https://")):
        text = text.replace("\n\nKindly arrange", f"\n\nYou can view or download the invoice here:\n{link}\n\nKindly arrange")
    saved = svc.save_pdf_copy(inv)
    m = wa.queue("client", inv.client.mobile, inv.client.name, text, g.user.id, "invoice", client_id=inv.client_id)
    if m is None:
        flash("This client has no valid mobile number. Add one on the client page.", "danger")
        return redirect(url_for("billing.show", invoice_id=inv.id))
    log_activity("billing", f"Prepared WhatsApp message for invoice {inv.invoice_number}")
    db.session.commit()
    flash("Message ready. Open the chat and press Send." + (f" The PDF was also saved to {saved}." if saved else
          " To send the PDF too, download it and attach it in WhatsApp, or use Email."), "success")
    return redirect(url_for("whatsapp.queue"))


@bp.route("/services", methods=["GET", "POST"])
@manager_required
def services():
    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        sid = f.get("id", type=int)
        item = db.session.get(ServiceItem, sid) if sid else None
        clash = ServiceItem.query.filter(db.func.lower(ServiceItem.name) == name.lower(), ServiceItem.id != (sid or 0)).first()
        if not name:
            flash("Give the service a name.", "danger")
        elif clash:
            flash("A service with that name already exists.", "danger")
        else:
            if item is None:
                item = ServiceItem()
                db.session.add(item)
            item.name, item.sac_code = name[:160], f.get("sac_code", "").strip()[:12]
            item.default_rate, item.active = max(0.0, to_float(f.get("default_rate"))), f.get("active", "1") == "1"
            log_activity("billing", f"Saved service {name}")
            db.session.commit()
            flash("Service saved.", "success")
        return redirect(url_for("billing.services"))
    return render_template("billing/services.html", rows=ServiceItem.query.order_by(ServiceItem.active.desc(), ServiceItem.name).all())


@bp.route("/services/<int:sid>/delete", methods=["POST"])
@manager_required
def service_delete(sid):
    db.session.delete(db.get_or_404(ServiceItem, sid))
    db.session.commit()
    flash("Service deleted. Invoices already made are not affected.", "success")
    return redirect(url_for("billing.services"))
