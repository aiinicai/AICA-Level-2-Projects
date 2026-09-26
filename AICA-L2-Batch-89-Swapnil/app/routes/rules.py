from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, select

from .. import audit
from ..auth import actor
from ..models import Obligation, RuleVerification, db
from ..permissions import require
from ..services import rulepack

bp = Blueprint("rules", __name__, url_prefix="/rules")


@bp.route("/")
@require("view")
def index():
    rp = rulepack()
    counts = dict(db.session.execute(select(Obligation.rule_code, func.count(Obligation.id)).where(
        Obligation.superseded_at.is_(None)).group_by(Obligation.rule_code)).all())
    domain = request.args.get("q", "").strip().upper()
    rules = [r for r in rp.rules if not domain or domain in r.code or domain in r.form.upper()]
    return render_template("rules.html", rules=rules, rp=rp, counts=counts, q=domain, r=None)


@bp.route("/<code>")
@require("view")
def show(code: str):
    from ..models import RegulatoryUpdate
    rp = rulepack()
    r = rp.by_code.get(code) or abort(404)
    history = db.session.execute(select(RuleVerification).where(RuleVerification.rule_code == code).order_by(
        RuleVerification.id.desc())).scalars().all()
    updates = [u for u in db.session.execute(select(RegulatoryUpdate).order_by(RegulatoryUpdate.issued_on.desc())).scalars()
               if any(l.get("code") == code for l in (u.linked_rules or []))]
    return render_template("rules.html", r=r, rp=rp, history=history, updates=updates)


# ======================================================== versions & diff
def _current_snapshot():
    from ..exports import snapshot
    return snapshot(current_app.extensions["rulepack"])


@bp.route("/versions")
@require("view")
def versions():
    from ..exports import diff_snapshots
    from ..models import RuleVersion
    rp = current_app.extensions["rulepack"]
    rows = db.session.execute(select(RuleVersion).order_by(RuleVersion.id.desc())).scalars().all()
    latest = rows[0] if rows else None
    a, b = request.args.get("a"), request.args.get("b")
    diff = None
    if a and b:
        def snap(v):
            if v == "current":
                return _current_snapshot()
            row = db.session.execute(select(RuleVersion).where(RuleVersion.version == v)).scalar() or abort(404)
            return row.snapshot
        diff = diff_snapshots(snap(a), snap(b))
    elif latest:
        a, b = latest.version, "current"
        diff = diff_snapshots(latest.snapshot, _current_snapshot())
    unpublished = latest is None or latest.content_hash != rp.content_hash
    return render_template("rules.html", mode="versions", rows=rows, rp=rp, diff=diff, a=a, b=b,
                           unpublished=unpublished, r=None)


@bp.route("/publish", methods=["POST"])
@require("edit_rulepack")
def publish():
    from ..models import RuleVersion
    rp = current_app.extensions["rulepack"]
    existing = db.session.execute(select(RuleVersion).where(RuleVersion.version == rp.version)).scalar()
    if existing and existing.content_hash == rp.content_hash:
        flash(f"Version {rp.version} is already published with this content.", "info")
        return redirect(url_for("rules.versions"))
    if existing:
        flash(f"Version {rp.version} was already published with different content. Change the VERSION file "
              "(e.g. 2026.09.25-2) before publishing again — published versions are never overwritten.", "danger")
        return redirect(url_for("rules.versions")), 303
    snap = _current_snapshot()
    db.session.add(RuleVersion(version=rp.version, content_hash=rp.content_hash, snapshot=snap,
                               published_by_id=current_user.id))
    audit.record(db.session, actor(), "RULEPACK_PUBLISHED", "rule_version", rp.version,
                 after={"content_hash": rp.content_hash, "rules": len(rp.rules)})
    db.session.commit()
    flash(f"Rule pack {rp.version} published ({rp.content_hash[:12]}).", "success")
    return redirect(url_for("rules.versions"))


# ============================================================== in-app edit
EDITABLE_FILES = ["VERSION", "companies_onetime.yaml", "companies_annual.yaml", "companies_event.yaml", "llp.yaml",
                  "directors.yaml", "fees.yaml", "schemes.yaml"]


@bp.route("/edit/<name>", methods=["GET", "POST"])
@require("edit_rulepack")
def edit(name: str):
    import hashlib
    import shutil
    import tempfile
    from pathlib import Path

    import engine
    from ..auth import today
    from ..services import recompute_all
    if name not in EDITABLE_FILES:
        abort(404)
    folder = Path(current_app.config["RULEPACK_DIR"])
    path = folder / name
    current = path.read_text(encoding="utf-8")
    if request.method == "POST":
        new = request.form.get("content", "").replace("\r\n", "\n")
        if new == current:
            flash("No changes.", "info")
            return redirect(url_for("rules.edit", name=name))
        with tempfile.TemporaryDirectory() as tmp:           # validate the whole pack before touching the real file
            shutil.copytree(folder, Path(tmp) / "rp")
            (Path(tmp) / "rp" / name).write_text(new, encoding="utf-8")
            try:
                new_pack = engine.load(Path(tmp) / "rp")
            except engine.RulePackError as e:
                return render_template("rules.html", mode="edit", name=name, content=new, files=EDITABLE_FILES,
                                       error=str(e), r=None, rp=current_app.extensions["rulepack"]), 422
        from ..exports import diff_snapshots, snapshot
        change = diff_snapshots(_current_snapshot(), snapshot(new_pack))
        path.write_text(new, encoding="utf-8")
        current_app.extensions["rulepack"] = new_pack
        audit.record(db.session, actor(), "RULEPACK_EDITED", "rulepack_file", name,
                     before={"sha256": hashlib.sha256(current.encode()).hexdigest()},
                     after={"sha256": hashlib.sha256(new.encode()).hexdigest(), "version": new_pack.version,
                            "added": change["added"], "removed": change["removed"],
                            "changed": [c for c, _ in change["changed"]], "other": change["other"]})
        db.session.commit()
        stats = recompute_all(today(), actor())
        flash(f"{name} saved and validated. Obligations recomputed: {stats['updated']} changed, {stats['inserted']} new, "
              f"{stats['superseded']} superseded. Publish the version when ready.", "success")
        return redirect(url_for("rules.versions"))
    return render_template("rules.html", mode="edit", name=name, content=current, files=EDITABLE_FILES, r=None,
                           rp=current_app.extensions["rulepack"])


# ===================================================== regulatory updates
@bp.route("/updates", methods=["GET", "POST"])
@require("view")
def updates():
    from ..models import RegulatoryUpdate
    from ..permissions import deny, has
    rp = rulepack()
    if request.method == "POST":
        if not has(current_user, "edit_rulepack"):
            deny("edit_rulepack")
        from .entities import to_date
        number, d = (request.form.get("number") or "").strip(), to_date(request.form.get("issued_on"))
        summary = (request.form.get("summary") or "").strip()
        links = [{"code": c, "relation": request.form.get(f"rel_{c}", "created")} for c in request.form.getlist("codes")
                 if c in rp.by_code]
        url = (request.form.get("url") or "").strip()
        if not number or d is None or len(summary) < 10 or (url and not url.startswith(("https://", "http://"))):
            flash("Enter the notification/circular number, its date, a summary (10+ characters) and a valid URL.", "danger")
            return redirect(url_for("rules.updates")), 303
        u = RegulatoryUpdate(number=number, issued_on=d, url=url or None, summary=summary, linked_rules=links,
                             created_by_id=current_user.id)
        db.session.add(u)
        db.session.flush()
        audit.record(db.session, actor(), "REGULATORY_UPDATE_LOGGED", "regulatory_update", u.id,
                     after={"number": number, "date": d, "links": links})
        db.session.commit()
        flash("Regulatory update logged.", "success")
        return redirect(url_for("rules.updates"))
    rows = db.session.execute(select(RegulatoryUpdate).order_by(RegulatoryUpdate.issued_on.desc())).scalars().all()
    return render_template("rules.html", mode="updates", rows=rows, rp=rp, r=None)


@bp.route("/<code>/verify", methods=["POST"])
@require("verify_rule")
def verify(code: str):
    rp = rulepack()
    r = rp.by_code.get(code) or abort(404)
    note = (request.form.get("note") or "").strip()
    if len(note) < 10:
        flash("Say what you checked (source and section) in at least 10 characters.", "danger")
        return redirect(url_for("rules.show", code=code)), 303
    db.session.add(RuleVerification(rule_code=code, rule_hash=r.content_hash, verified_by_id=current_user.id, note=note))
    audit.record(db.session, actor(), "RULE_VERIFIED", "rule", code,
                 after={"rule_hash": r.content_hash, "version": rp.version, "note": note})
    db.session.commit()
    flash(f"{code} verified by {current_user.full_name}.", "success")
    return redirect(url_for("rules.show", code=code))
