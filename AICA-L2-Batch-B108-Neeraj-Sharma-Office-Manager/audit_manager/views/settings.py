import io
import sqlite3
import tempfile
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for

from .. import log_activity
from ..access import admin_required
from .. import config
from ..config import data_dir
from ..models import ActivityLog, FirmSetting, db
from ..services import backup as backup_svc
from ..services import letterhead, mailer

bp = Blueprint("settings", __name__, url_prefix="/settings")

FIRM_FIELDS = ["firm_name", "firm_tagline", "firm_address", "firm_phone", "firm_email", "firm_website", "firm_pan",
               "firm_gstin", "firm_frn", "firm_partner_name", "firm_membership_no"]


@bp.route("/")
@admin_required
def index():
    s = FirmSetting.all()
    page = max(1, request.args.get("page", 1, type=int))
    logs = ActivityLog.query.order_by(ActivityLog.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("settings/index.html", s=s, logo=letterhead.logo_data_uri(), logs=logs, encryptions=mailer.ENCRYPTIONS,
                           mail_has_password=bool(s.get("mail_password")), report_fields=letterhead.REPORT_FIELDS,
                           hidden=letterhead.hidden_fields(), restore_pending=backup_svc.pending_restore(), data_folder=str(data_dir()),
                           backup_when=backup_svc.WHEN, when=backup_svc.when(), move_pending=config.pending_move(), professions=letterhead.PROFESSIONS, designations=letterhead.designations())


@bp.route("/data-folder", methods=["POST"])
@admin_required
def data_folder():
    """Move the live data (database, logo, keys) to another drive. Takes effect at the next start; the old copy is left in place."""
    from flask import g

    if g.user.role != "super_admin":
        flash("Only the Super Admin can move the data folder.", "danger")
    elif request.form.get("cancel") == "1":
        config.cancel_move()
        flash("The waiting move was cancelled.", "success")
    else:
        try:
            target = backup_svc.check_folder(request.form.get("data_folder", ""))
            if target.resolve() == data_dir().resolve():
                flash("The data is already in that folder.", "warning")
            elif (target / "auditmanager.db").exists():
                flash("That folder already holds Office Manager data. Choose an empty folder.", "danger")
            else:
                config.request_move(str(target))
                log_activity("settings", f"Asked to move the data folder to {target}")
                db.session.commit()
                flash(f"Close Office Manager completely and open it again. The data will then be kept in {target}.", "warning")
        except backup_svc.BackupError as e:
            flash(str(e), "danger")
    return redirect(url_for("settings.index") + "#dataFolder")


@bp.route("/designations", methods=["POST"])
@admin_required
def designations():
    lines = [ln.strip()[:80] for ln in request.form.get("designations", "").splitlines() if ln.strip()]
    FirmSetting.put("designations", "\n".join(lines))
    log_activity("settings", "Updated the designation master")
    db.session.commit()
    flash(f"Designation master saved ({len(letterhead.designations())} designations).", "success")
    return redirect(url_for("settings.index") + "#designations")


@bp.route("/office", methods=["POST"])
@admin_required
def office():
    f = request.form
    FirmSetting.put("profession", f.get("profession") if f.get("profession") in letterhead.PROFESSIONS else "ca")
    FirmSetting.put("profession_title", f.get("profession_title", "").strip()[:60])
    folder = f.get("invoice_pdf_folder", "").strip()
    if folder:
        try:
            folder = str(backup_svc.check_folder(folder))
        except backup_svc.BackupError as e:
            flash(str(e), "danger")
            return redirect(url_for("settings.index") + "#office")
    FirmSetting.put("invoice_pdf_folder", folder)
    FirmSetting.put("hourly_billing", "1" if f.get("hourly_billing") == "1" else "0")
    try:
        FirmSetting.put("default_hourly_rate", str(max(0.0, float(f.get("default_hourly_rate") or 0))))
    except ValueError:
        pass
    log_activity("settings", "Updated office type and billing folders")
    db.session.commit()
    flash("Office settings saved.", "success")
    return redirect(url_for("settings.index") + "#office")


@bp.route("/report-header", methods=["POST"])
@admin_required
def report_header():
    shown = set(request.form.getlist("show"))
    for key in letterhead.REPORT_FIELDS:
        FirmSetting.put("lh_hide_" + key, "0" if key in shown else "1")
    log_activity("settings", "Changed which firm details are shown on reports")
    db.session.commit()
    flash("Report header choices saved. They apply to reports on screen, print, PDF, Excel and CSV.", "success")
    return redirect(url_for("settings.index") + "#reportHeader")


@bp.route("/backup/settings", methods=["POST"])
@admin_required
def backup_settings():
    folder = request.form.get("backup_folder", "").strip()
    try:
        keep = max(1, min(365, int(request.form.get("backup_keep") or 14)))
    except ValueError:
        keep = 14
    if folder:
        try:
            folder = str(backup_svc.check_folder(folder))
        except backup_svc.BackupError as e:
            flash(str(e), "danger")
            return redirect(url_for("settings.index") + "#backup")
    FirmSetting.put("backup_folder", folder)
    FirmSetting.put("backup_keep", str(keep))
    choice = request.form.get("backup_when", "off")
    FirmSetting.put("backup_when", choice if choice in backup_svc.WHEN and folder else "off")
    log_activity("settings", "Updated backup settings")
    db.session.commit()
    flash("Backup settings saved.", "success")
    return redirect(url_for("settings.index") + "#backup")


@bp.route("/backup/now", methods=["POST"])
@admin_required
def backup_now():
    try:
        target = backup_svc.to_folder()
        log_activity("settings", f"Saved a backup to {target}")
        db.session.commit()
        flash(f"Backup saved: {target}", "success")
    except backup_svc.BackupError as e:
        flash(f"Backup failed: {e}", "danger")
    return redirect(url_for("settings.index") + "#backup")


@bp.route("/backup/restore", methods=["POST"])
@admin_required
def backup_restore():
    from flask import g

    if g.user.role != "super_admin":
        flash("Only the Super Admin can restore a backup.", "danger")
        return redirect(url_for("settings.index") + "#backup")
    if request.form.get("cancel") == "1":
        backup_svc.cancel_restore()
        flash("The waiting restore was cancelled.", "success")
        return redirect(url_for("settings.index") + "#backup")
    upload = request.files.get("backup_file")
    if not upload or not upload.filename:
        flash("Choose a backup file first.", "danger")
    elif request.form.get("confirm") != "RESTORE":
        flash("Type RESTORE in the box to confirm.", "danger")
    else:
        try:
            backup_svc.stage_restore(upload.read())
            log_activity("settings", "Uploaded a backup to restore at the next start")
            db.session.commit()
            flash("Backup accepted. Close Office Manager completely and open it again to finish the restore. "
                  "Your present data will be kept as a safety copy.", "warning")
        except backup_svc.BackupError as e:
            flash(str(e), "danger")
    return redirect(url_for("settings.index") + "#backup")


@bp.route("/firm", methods=["POST"])
@admin_required
def firm():
    f = request.form
    if not f.get("firm_name", "").strip():
        flash("The firm name is required.", "danger")
        return redirect(url_for("settings.index"))
    for key in FIRM_FIELDS:
        FirmSetting.put(key, f.get(key, "").strip())
    FirmSetting.put("invoice_prefix", f.get("invoice_prefix", "INV").strip() or "INV")
    for key in ("default_cgst_rate", "default_sgst_rate", "default_igst_rate"):
        try:
            FirmSetting.put(key, str(max(0.0, min(50.0, float(f.get(key, 0))))))
        except ValueError:
            flash("Tax rates must be numbers.", "danger")
            db.session.rollback()
            return redirect(url_for("settings.index"))
    upload = request.files.get("firm_logo")
    try:
        if upload and upload.filename:
            letterhead.save_logo(upload.read())
        elif f.get("remove_logo") == "1":
            letterhead.remove_logo()
    except letterhead.LogoError as e:
        db.session.rollback()
        flash(str(e), "danger")
        return redirect(url_for("settings.index"))
    log_activity("settings", "Updated firm profile and billing settings")
    db.session.commit()
    flash("Firm settings saved.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/mail", methods=["POST"])
@admin_required
def mail():
    f = request.form
    enabled = f.get("mail_enabled") == "1"
    host, port = f.get("mail_host", "").strip(), f.get("mail_port", type=int)
    sender = f.get("mail_from_address", "").strip()
    if enabled and not (host and port and "@" in sender):
        flash("To switch email on, fill in the host, port and a From email address.", "danger")
        return redirect(url_for("settings.index"))
    FirmSetting.put("mail_enabled", "1" if enabled else "0")
    FirmSetting.put("mail_host", host)
    FirmSetting.put("mail_port", str(port or ""))
    FirmSetting.put("mail_encryption", f.get("mail_encryption") if f.get("mail_encryption") in mailer.ENCRYPTIONS else "tls")
    FirmSetting.put("mail_username", f.get("mail_username", "").strip())
    FirmSetting.put("mail_from_address", sender)
    FirmSetting.put("mail_from_name", f.get("mail_from_name", "").strip())
    if f.get("clear_password") == "1":
        FirmSetting.put("mail_password", "")
    elif f.get("mail_password"):
        FirmSetting.put("mail_password", mailer.encrypt_password(f["mail_password"]))
    log_activity("settings", "Updated outgoing email (SMTP) settings")
    db.session.commit()
    flash("Email settings saved. Use Send test email to confirm they work." if enabled
          else "Email settings saved, but email is switched off.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/mail/test", methods=["POST"])
@admin_required
def mail_test():
    to = request.form.get("test_to", "").strip()
    if "@" not in to:
        flash("Enter an email address to send the test to.", "danger")
    else:
        ok, msg = mailer.send_mail(to, "Test email from Office Manager",
                                   "This is a test email. Your email settings are working.")
        flash(msg, "success" if ok else "danger")
    return redirect(url_for("settings.index"))


@bp.route("/backup")
@admin_required
def backup():
    """Download a .zip of the database and logo (safe while other staff are using the app)."""
    data = backup_svc.make_zip()
    log_activity("settings", "Downloaded a backup")
    db.session.commit()
    return send_file(io.BytesIO(data), as_attachment=True, mimetype="application/zip", download_name=backup_svc.file_name())
