from datetime import datetime

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from .. import log_activity
from ..access import login_required, manager_required, visible_clients
from ..models import Client, FirmSetting, User, WhatsAppMessage, WhatsAppTemplate, db
from ..services import duedates, mailer, pictures
from ..services import whatsapp as wa

bp = Blueprint("whatsapp", __name__, url_prefix="/whatsapp")


def _firm() -> str:
    return FirmSetting.get("firm_name", "our office")


def _own(q):
    """Managers and above see everyone's messages; employees see only their own."""
    return q if g.user.is_manager_or_above else q.filter(WhatsAppMessage.created_by_id == g.user.id)


@bp.route("/")
@login_required
def index():
    clients = visible_clients(g.user).filter(Client.status != "inactive").order_by(Client.name).all()
    staff = User.query.filter_by(is_active_user=True).order_by(User.name).all() if g.user.is_manager_or_above else []
    return render_template("whatsapp/compose.html", clients=clients, staff=staff, templates=WhatsAppTemplate.query.order_by(WhatsAppTemplate.name).all(),
                           placeholders=wa.PLACEHOLDERS, firm=_firm(), tpl=request.args.get("tpl", type=int),
                           due_options=(duedates.options() or wa.due_date_options()), work_types=wa.WORK_TYPES, mail_ready=mailer.is_configured())


@bp.route("/compose", methods=["POST"])
@login_required
def compose():
    f = request.form
    audience = f.get("audience", "client")
    body = f.get("body", "").strip()
    if not body:
        flash("Write the message first.", "danger")
        return redirect(url_for("whatsapp.index"))
    channel = "email" if f.get("channel") == "email" else "whatsapp"
    subject = f.get("subject", "").strip()
    if channel == "email":
        if not mailer.is_configured():
            flash("Email is not set up yet. Fill in the email (SMTP) details in Settings first.", "danger")
            return redirect(url_for("whatsapp.index"))
        if not subject:
            flash("Give the email a subject.", "danger")
            return redirect(url_for("whatsapp.index"))
    # picture: one uploaded for this send, otherwise the chosen template's picture
    image = None
    upload = request.files.get("image")
    if upload and upload.filename:
        try:
            image = pictures.save(upload.read())
        except pictures.PictureError as e:
            flash(str(e), "danger")
            return redirect(url_for("whatsapp.index"))
    elif f.get("use_template_image") == "1":
        tpl = db.session.get(WhatsAppTemplate, f.get("template_id", type=int) or 0)
        image = tpl.image if tpl and pictures.path(tpl.image) else None
    pic = pictures.attachment(image)
    made = skipped = failed = 0
    last_error = ""
    send_at = None
    if channel == "email" and f.get("send_at"):
        try:
            send_at = datetime.strptime(f["send_at"], "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("The date and time to send at is not valid.", "danger")
            return redirect(url_for("whatsapp.index"))
        if send_at <= datetime.now():
            send_at = None  # a past time means send now

    def deliver(aud, person_name, mobile, email, text, values, many, **ids):
        nonlocal made, skipped, failed, last_error
        if channel == "email":
            if not email or "@" not in email:
                skipped += 1
                return
            if send_at:
                wa.schedule_email(aud, email, person_name, wa.render(subject, **values), text, g.user.id, send_at, image=image, **ids)
                made += 1
                return
            ok, msg = mailer.send_mail(email, wa.render(subject, **values), text, [pic] if pic else None)
            wa.log_email(aud, email, person_name, wa.render(subject, **values), text, g.user.id, ok, "bulk" if many else "manual", image=image, **ids)
            if ok:
                made += 1
            else:
                failed += 1
                last_error = msg
        elif wa.queue(aud, mobile, person_name, text, g.user.id, "bulk" if many else "manual", image=image, **ids):
            made += 1
        else:
            skipped += 1

    if audience == "staff":
        if not g.user.is_manager_or_above:
            abort(403)
        ids = [int(x) for x in f.getlist("staff_ids") if x.isdigit()]
        for u in User.query.filter(User.id.in_(ids), User.is_active_user.is_(True)):
            values = {"staff_name": u.name, "firm_name": _firm()}
            deliver("staff", u.name, u.phone, u.email, wa.render(body, **values), values, len(ids) > 1, staff_id=u.id)
    else:
        ids = [int(x) for x in f.getlist("client_ids") if x.isdigit()]
        allowed = {c.id: c for c in visible_clients(g.user).filter(Client.id.in_(ids)).all()}  # ignores ids the user may not see
        for cid in ids:
            c = allowed.get(cid)
            if c is None:
                continue
            values = {"client_name": c.name, "contact_person": c.contact_person or c.name, "firm_name": _firm(), "staff_name": g.user.name, "due_date": f.get("due_date", ""),
                      "period": f.get("period", ""), "amount": f.get("amount", ""), "invoice_number": f.get("invoice_number", ""),
                      "work_type": f.get("work_type", "").strip()}
            deliver("client", c.name, c.mobile, c.email, wa.render(body, **values), values, len(ids) > 1, client_id=c.id)
    if not (made or skipped or failed):
        flash("Choose at least one recipient.", "danger")
        return redirect(url_for("whatsapp.index"))
    if channel == "email":
        log_activity("whatsapp", f"Emailed {made} recipient(s) ({failed} failed, {skipped} without an email address)")
        db.session.commit()
        text = f"{made} email(s) scheduled for {send_at:%d %b %Y, %I:%M %p}. Keep Office Manager running on the host PC at that time." if send_at else f"{made} email(s) sent."
        if skipped:
            text += f" {skipped} skipped because they have no email address."
        if failed:
            text += f" {failed} failed: {last_error}"
        flash(text, "success" if made and not failed else "warning")
        return redirect(url_for("whatsapp.history"))
    log_activity("whatsapp", f"Prepared {made} WhatsApp message(s) ({skipped} skipped, no valid number)")
    db.session.commit()
    flash(f"{made} message(s) ready to send." + (f" {skipped} skipped because they have no valid mobile number." if skipped else ""), "success" if made else "warning")
    return redirect(url_for("whatsapp.queue") if made else url_for("whatsapp.index"))


@bp.route("/queue")
@login_required
def queue():
    msgs = _own(WhatsAppMessage.query.filter_by(status="queued")).order_by(WhatsAppMessage.id).limit(300).all()
    return render_template("whatsapp/queue.html", rows=[(m, wa.links(m.phone, m.body)) for m in msgs])


@bp.route("/<int:mid>/opened", methods=["POST"])
@login_required
def opened(mid):
    m = _get(mid)
    m.status, m.opened_at = "opened", datetime.utcnow()
    db.session.commit()
    return jsonify(ok=True)


@bp.route("/<int:mid>/skip", methods=["POST"])
@login_required
def skip(mid):
    _get(mid).status = "skipped"
    db.session.commit()
    return redirect(url_for("whatsapp.queue"))


def _get(mid: int) -> WhatsAppMessage:
    m = db.get_or_404(WhatsAppMessage, mid)
    if not g.user.is_manager_or_above and m.created_by_id != g.user.id:
        abort(403)
    return m


@bp.route("/<int:mid>/cancel", methods=["POST"])
@login_required
def cancel(mid):
    m = _get(mid)
    if m.status == "scheduled":
        m.status = "skipped"
        db.session.commit()
        flash("The scheduled email was cancelled.", "success")
    return redirect(url_for("whatsapp.history"))


@bp.route("/history")
@login_required
def history():
    page = max(1, request.args.get("page", 1, type=int))
    p = _own(WhatsAppMessage.query.filter(WhatsAppMessage.status != "queued")).order_by(WhatsAppMessage.id.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template("whatsapp/history.html", pagination=p)


@bp.route("/reminders", methods=["GET", "POST"])
@login_required
def reminders():
    days = max(0, min(60, request.values.get("days", 7, type=int)))
    clients = visible_clients(g.user).filter(Client.status != "inactive").all()
    pending = wa.pending_items([c.id for c in clients], days)
    by_id = {c.id: c for c in clients}
    queued = {m.client_id for m in WhatsAppMessage.query.filter_by(status="queued", source="reminder")}
    rows = []
    for cid, lines in pending.items():
        c = by_id[cid]
        rows.append({"client": c, "lines": lines, "phone": wa.normalize_phone(c.mobile), "already": cid in queued})
    rows.sort(key=lambda r: r["client"].name.lower())
    if request.method == "POST":
        chosen = {int(x) for x in request.form.getlist("client_ids") if x.isdigit()}
        made = 0
        for r in rows:
            c = r["client"]
            if c.id in chosen and r["phone"] and not r["already"]:
                if wa.queue("client", c.mobile, c.name, wa.reminder_text(c.name, r["lines"], _firm()), g.user.id, "reminder", client_id=c.id):
                    made += 1
        log_activity("whatsapp", f"Prepared {made} reminder message(s)")
        db.session.commit()
        flash(f"{made} reminder(s) ready to send." if made else "Nothing new to prepare.", "success" if made else "warning")
        return redirect(url_for("whatsapp.queue") if made else url_for("whatsapp.reminders", days=days))
    return render_template("whatsapp/reminders.html", rows=rows, days=days)


def _template_picture(tpl) -> bool:
    """Apply an uploaded / removed picture to a template. False (with a message) if the upload was not a usable picture."""
    upload = request.files.get("image")
    if upload and upload.filename:
        try:
            tpl.image = pictures.save(upload.read())
        except pictures.PictureError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return False
    elif request.form.get("remove_image") == "1":
        tpl.image = None
    return True


@bp.route("/picture/<name>")
@login_required
def picture(name):
    from flask import send_file

    p = pictures.path(name)
    if p is None:
        abort(404)
    return send_file(p, mimetype="image/png" if p.suffix == ".png" else "image/jpeg", max_age=3600)


@bp.route("/templates", methods=["GET", "POST"])
@manager_required
def templates():
    if request.method == "POST":
        name, body = request.form.get("name", "").strip(), request.form.get("body", "").strip()
        tid = request.form.get("id", type=int)
        existing = db.session.get(WhatsAppTemplate, tid) if tid else None
        if not name or not body:
            flash("Give the template a name and some text.", "danger")
        elif existing is not None:
            clash = WhatsAppTemplate.query.filter(WhatsAppTemplate.name == name, WhatsAppTemplate.id != tid).first()
            if clash:
                flash("Another template already has that name.", "danger")
            else:
                existing.name, existing.body = name[:80], body
                existing.category = request.form.get("category", existing.category)[:20]
                if not _template_picture(existing):
                    return redirect(url_for("whatsapp.templates", edit=existing.id))
                log_activity("whatsapp", f"Edited message template {name}")
                db.session.commit()
                flash("Template updated.", "success")
        elif WhatsAppTemplate.query.filter_by(name=name).first():
            flash("A template with that name already exists.", "danger")
        else:
            fresh = WhatsAppTemplate(name=name[:80], body=body, category=request.form.get("category", "general")[:20])
            db.session.add(fresh)
            _template_picture(fresh)
            log_activity("whatsapp", f"Added message template {name}")
            db.session.commit()
            flash("Template saved.", "success")
        return redirect(url_for("whatsapp.templates"))
    edit = db.session.get(WhatsAppTemplate, request.args.get("edit", type=int) or 0)
    return render_template("whatsapp/templates.html", rows=WhatsAppTemplate.query.order_by(WhatsAppTemplate.name).all(), placeholders=wa.PLACEHOLDERS, edit=edit)


@bp.route("/templates/<int:tid>/delete", methods=["POST"])
@manager_required
def delete_template(tid):
    t = db.get_or_404(WhatsAppTemplate, tid)
    db.session.delete(t)
    db.session.commit()
    flash("Template deleted.", "success")
    return redirect(url_for("whatsapp.templates"))


@bp.route("/automation", methods=["GET", "POST"])
@manager_required
def automation():
    from ..services import automation as auto

    if request.method == "POST":
        for event in auto.EVENTS:
            for channel in ("whatsapp", "email"):
                FirmSetting.put(f"auto_{event}_{channel}", "1" if request.form.get(f"{event}_{channel}") == "1" else "0")
        try:
            FirmSetting.put("auto_due_days", str(max(0, min(30, int(request.form.get("auto_due_days") or 3)))))
        except ValueError:
            pass
        log_activity("whatsapp", "Updated automatic (event-based) messages")
        db.session.commit()
        flash("Automatic messages saved.", "success")
        return redirect(url_for("whatsapp.automation"))
    rows = []
    for key, (label, tpl_name, who) in auto.EVENTS.items():
        tpl = WhatsAppTemplate.query.filter_by(name=tpl_name).first()
        rows.append({"key": key, "label": label, "who": who, "tpl": tpl, "whatsapp": auto.is_on(key, "whatsapp"), "email": auto.is_on(key, "email")})
    return render_template("whatsapp/automation.html", rows=rows, due_days=auto.due_days(), mail_ready=mailer.is_configured())
