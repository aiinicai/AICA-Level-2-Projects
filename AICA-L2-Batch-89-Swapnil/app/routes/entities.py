from __future__ import annotations

from collections import OrderedDict
from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from markupsafe import escape
from sqlalchemy import delete, func, or_, select

from engine.types import COMPANY_TYPES

from .. import audit
from ..auth import actor, decrypt, encrypt, mask_pan, today
from ..models import (AnnualFacts, AuditLog, ClassificationDecision, Entity, EntityPerson, Event, Filing,
                      Notification, Obligation, PeriodFlag, Person, User, db)
from ..permissions import can_see_entity, deny, has, require
from ..services import (FACT_FIELDS, classifications, health, sync_entity, validate_din, validate_entity,
                        visible_entities_query)

bp = Blueprint("entities", __name__)

ENTITY_TYPES = ["PRIVATE", "OPC", "PUBLIC_UNLISTED", "PUBLIC_LISTED", "SECTION8", "NIDHI", "PRODUCER", "LLP"]
FLAG_FIELDS = ["is_holding", "is_subsidiary", "subsidiary_of_public", "nbfc", "hfc", "banking", "excluded_sector",
               "government", "special_act", "listed_subsidiary", "startup", "single_director",
               "ro_furnished_at_incorporation", "llp_elect_longer_first_fy", "ccfs_excluded", "has_share_capital"]
# Typed event forms (brief §7 "Record event"): label, group, fields (name, label, kind[, options]).
DIN_FIELDS = [("din", "DIN", "din"), ("person_name", "Name (if DIN is new here)", "text"),
              ("din_allotment_date", "DIN allotted on (if new)", "date")]
DESIGNATIONS = ["Director", "Additional Director", "Independent Director", "Nominee Director", "Whole-time Director",
                "Managing Director"]
EVENT_SPECS: OrderedDict[str, dict] = OrderedDict([
    ("DIRECTOR_APPOINTED", {"label": "Director appointed", "group": "Directors & KMP",
                            "fields": DIN_FIELDS + [("designation", "Designation", "select", DESIGNATIONS),
                                                    ("dsc_expiry", "DSC expiry", "date")]}),
    ("DIRECTOR_RESIGNED", {"label": "Director resigned", "group": "Directors & KMP", "fields": [("din", "DIN", "din")]}),
    ("DIRECTOR_CESSATION", {"label": "Director ceased (death, disqualification, removal)", "group": "Directors & KMP",
                            "fields": [("din", "DIN", "din"), ("reason", "Reason", "text")]}),
    ("DESIGNATION_CHANGE", {"label": "Change in designation", "group": "Directors & KMP",
                            "fields": [("din", "DIN", "din"), ("designation", "New designation", "select", DESIGNATIONS)]}),
    ("MD_WTD_APPOINTED", {"label": "MD / WTD / Manager appointed", "group": "Directors & KMP",
                          "fields": [("din", "DIN", "din"), ("designation", "Appointed as", "select",
                                                             ["Managing Director", "Whole-time Director", "Manager"])]}),
    ("KMP_APPOINTED", {"label": "KMP appointed (CS / CFO / CEO)", "group": "Directors & KMP",
                       "fields": [("kmp_name", "Name", "text"), ("kmp_role", "Role", "select", ["Company Secretary", "CFO", "CEO"])]}),
    ("KMP_CESSATION", {"label": "KMP ceased", "group": "Directors & KMP",
                       "fields": [("kmp_name", "Name", "text"), ("kmp_role", "Role", "select", ["Company Secretary", "CFO", "CEO"])]}),
    ("ALLOTMENT", {"label": "Allotment of shares / securities", "group": "Capital",
                   "fields": [("kind", "Kind", "select", ["PRIVATE_PLACEMENT", "RIGHTS", "BONUS", "ESOP", "PREFERENTIAL_OTHER"]),
                              ("shares", "Number of shares", "text"), ("amount", "Amount ₹", "money")]}),
    ("AUTH_CAPITAL_INCREASE", {"label": "Increase in authorised capital", "group": "Capital",
                               "fields": [("new_authorised", "New authorised capital ₹", "money")]}),
    ("BUYBACK_COMPLETED", {"label": "Buy-back completed", "group": "Capital", "fields": [("amount", "Amount ₹", "money")]}),
    ("SPECIAL_RESOLUTION", {"label": "Special resolution passed", "group": "Resolutions", "fields": [("subject", "Subject", "text")]}),
    ("BOARD_RESOLUTION_117", {"label": "Board resolution needing MGT-14", "group": "Resolutions",
                              "fields": [("subject", "Subject", "text")]}),
    ("BOARD_MEETING", {"label": "Board meeting held", "group": "Resolutions", "fields": [("agenda", "Main business", "text")]}),
    ("RO_SHIFT_SAME_CITY", {"label": "Registered office shifted within the city", "group": "Registered office",
                            "fields": [("new_address", "New address", "text")]}),
    ("CHARGE_CREATED", {"label": "Charge created", "group": "Charges",
                        "fields": [("amount", "Amount secured ₹", "money"), ("charge_holder", "Charge holder", "text")]}),
    ("CHARGE_MODIFIED", {"label": "Charge modified", "group": "Charges",
                         "fields": [("amount", "Amount secured ₹", "money"), ("charge_holder", "Charge holder", "text")]}),
    ("CHARGE_SATISFIED", {"label": "Charge satisfied", "group": "Charges", "fields": [("charge_holder", "Charge holder", "text")]}),
    ("FIRST_AUDITOR_APPOINTED", {"label": "First auditor appointed", "group": "Auditors", "fields": [("auditor", "Auditor firm", "text")]}),
    ("AUDITOR_RESIGNED", {"label": "Auditor resigned", "group": "Auditors", "fields": [("auditor", "Auditor firm", "text")]}),
    ("AUDITOR_CASUAL_VACANCY", {"label": "Casual vacancy in office of auditor", "group": "Auditors",
                                "fields": [("cause", "Cause", "select", ["RESIGNATION", "OTHER"])]}),
    ("AUDITOR_APPOINTED_CASUAL", {"label": "Auditor appointed in a casual vacancy", "group": "Auditors",
                                  "fields": [("auditor", "Auditor firm", "text")]}),
    ("BEN1_RECEIVED", {"label": "BEN-1 declaration received from SBO", "group": "Declarations",
                       "fields": [("declarant", "Declarant", "text")]}),
    ("MGT4_5_RECEIVED", {"label": "MGT-4 / MGT-5 declaration received", "group": "Declarations",
                         "fields": [("declarant", "Declarant", "text")]}),
    ("DORMANT_RESOLUTION", {"label": "Resolution to apply for dormant status", "group": "Status", "fields": []}),
    ("LLP_AGREEMENT_CHANGED", {"label": "LLP agreement changed", "group": "LLP", "llp": True,
                               "fields": [("subject", "Nature of change", "text")]}),
    ("PARTNER_CHANGE", {"label": "Partner / designated partner admitted or ceased", "group": "LLP", "llp": True,
                        "fields": DIN_FIELDS + [("change", "Change", "select", ["ADMISSION", "CESSATION", "CHANGE_IN_DESIGNATION"])]}),
    ("LLP_RO_CHANGE", {"label": "LLP registered office changed", "group": "LLP", "llp": True,
                       "fields": [("new_address", "New address", "text")]}),
    ("LLP_BEN1_RECEIVED", {"label": "LLP BEN-1 declaration received", "group": "LLP", "llp": True,
                           "fields": [("declarant", "Declarant", "text")]}),
    ("LLP_BENEFICIAL_DECL_RECEIVED", {"label": "Form 4B / 4C declaration received", "group": "LLP", "llp": True,
                                      "fields": [("declarant", "Declarant", "text")]}),
])
EVENT_TYPES = OrderedDict((k, v["label"]) for k, v in EVENT_SPECS.items())
LLP_EVENTS = {k for k, v in EVENT_SPECS.items() if v.get("llp")}
LINK_EVENTS = {"DIRECTOR_APPOINTED": "link", "PARTNER_CHANGE": "llp", "DIRECTOR_RESIGNED": "cease",
               "DIRECTOR_CESSATION": "cease", "DESIGNATION_CHANGE": "designate", "MD_WTD_APPOINTED": "designate"}


def events_for(entity_type: str) -> OrderedDict:
    return OrderedDict((k, v) for k, v in EVENT_SPECS.items() if bool(v.get("llp")) == (entity_type == "LLP"))


# --------------------------------------------------------------- parsing
def to_date(v: str | None) -> date | None:
    try:
        return date.fromisoformat(v) if v else None
    except ValueError:
        return None


def to_money(v: str | None) -> float | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace(",", "").replace("₹", "").strip())
    except ValueError:
        return None


def to_tri(v: str | None) -> bool | None:
    return {"yes": True, "no": False}.get((v or "").lower())


def get_entity(entity_id: int) -> Entity:
    e = db.session.get(Entity, entity_id)
    if e is None:
        abort(404)
    if not can_see_entity(current_user, e):
        deny("view_all", "This entity is not assigned to you.", object_type="entity", object_id=entity_id,
             entity_id=entity_id)
    return e


def entity_snapshot(e: Entity) -> dict:
    d = {c.name: getattr(e, c.key) for c in Entity.__table__.columns if c.key != "pan_enc"}
    d["pan"] = "(encrypted)" if e.pan_enc else None
    return d


# ---------------------------------------------------------------- list
@bp.route("/entities")
@require("view")
def index():
    q = visible_entities_query(current_user)
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term.lower()}%"
        q = q.where(or_(func.lower(Entity.name).like(like), func.lower(Entity.cin).like(like)))
    a = request.args
    if a.get("type"):
        q = q.where(Entity.entity_type == a["type"])
    if a.get("rm", "").isdigit():
        q = q.where(Entity.rm_id == int(a["rm"]))
    if a.get("roc"):
        q = q.where(Entity.roc == a["roc"])
    ents = db.session.execute(q.order_by(Entity.name)).scalars().all()
    t = today()
    summary = {}
    for e in ents:
        obls = db.session.execute(select(Obligation).where(Obligation.entity_id == e.id,
                                                           Obligation.superseded_at.is_(None))).scalars()
        hs = [health(o, t) for o in obls]
        summary[e.id] = {"overdue": hs.count("overdue"), "due30": hs.count("due7") + hs.count("due30"),
                         "decisions": 0}
    if a.get("health") == "overdue":
        ents = [e for e in ents if summary[e.id]["overdue"]]
    elif a.get("health") == "due30":
        ents = [e for e in ents if summary[e.id]["due30"]]
    elif a.get("health") == "clear":
        ents = [e for e in ents if not summary[e.id]["overdue"] and not summary[e.id]["due30"]]
    rocs = sorted({r for (r,) in db.session.execute(select(Entity.roc).distinct()) if r})
    rms = db.session.execute(select(User).where(User.id.in_(select(Entity.rm_id)))).scalars().all()
    return render_template("entities.html", entities=ents, summary=summary, types=ENTITY_TYPES, term=term, a=a,
                           rocs=rocs, rms=rms)


# ------------------------------------------------------------ create/edit
def _form_to_dict(form) -> dict:
    d = {"name": (form.get("name") or "").strip(), "entity_type": form.get("entity_type"),
         "cin": (form.get("cin") or "").strip().upper() or None, "pan": (form.get("pan") or "").strip().upper(),
         "incorporation_date": to_date(form.get("incorporation_date")),
         "engagement_start": to_date(form.get("engagement_start")),
         "roc": form.get("roc") or None, "registered_office": form.get("registered_office") or None,
         "email": form.get("email") or None, "status": form.get("status") or "ACTIVE",
         "nominal_capital": to_money(form.get("nominal_capital")) or 0.0,
         "paid_up_capital": to_money(form.get("paid_up_capital")) or 0.0,
         "llp_contribution": to_money(form.get("llp_contribution")) or 0.0,
         "rm_id": int(form["rm_id"]) if form.get("rm_id") else None,
         "preparer_id": int(form["preparer_id"]) if form.get("preparer_id") else None}
    for f in FLAG_FIELDS:
        d[f] = form.get(f) == "on"
    if d["entity_type"] == "LLP":
        d["has_share_capital"] = False
    return d


def _staff():
    return db.session.execute(select(User).where(User.is_active_flag.is_(True)).order_by(User.full_name)).scalars().all()


@bp.route("/entities/new", methods=["GET", "POST"])
@require("edit_entity")
def create():
    if request.method == "POST":
        d = _form_to_dict(request.form)
        if d["entity_type"] not in ENTITY_TYPES:
            d["entity_type"] = "PRIVATE"
        errors, warnings = validate_entity(d, today())
        if d["cin"] and db.session.execute(select(Entity.id).where(Entity.cin == d["cin"])).first():
            errors.append("An entity with this CIN/LLPIN already exists.")
        if errors:
            for m in errors:
                flash(m, "danger")
            return render_template("entity_form.html", d=d, types=ENTITY_TYPES, staff=_staff(), new=True), 422
        pan = d.pop("pan")
        if d["preparer_id"] is None and not has(current_user, "view_all"):
            d["preparer_id"] = current_user.id          # otherwise the creator could not see it
        e = Entity(**d, pan_enc=encrypt(pan) if pan else None)
        db.session.add(e)
        db.session.flush()
        audit.record(db.session, actor(), "ENTITY_CREATED", "entity", e.id, e.id, after=entity_snapshot(e))
        stats = sync_entity(e, today(), actor())
        db.session.commit()
        for m in warnings:
            flash(m, "warning")
        flash(f"{e.name} added: {stats['inserted']} obligations generated.", "success")
        return redirect(url_for("entities.show", entity_id=e.id))
    return render_template("entity_form.html", d={"entity_type": "PRIVATE", "has_share_capital": True,
                                                  "ro_furnished_at_incorporation": True, "status": "ACTIVE"},
                           types=ENTITY_TYPES, staff=_staff(), new=True)


@bp.route("/entities/<int:entity_id>/edit", methods=["GET", "POST"])
@require("edit_entity")
def edit(entity_id: int):
    e = get_entity(entity_id)
    if request.method == "POST":
        d = _form_to_dict(request.form)
        d["entity_type"] = d["entity_type"] if d["entity_type"] in ENTITY_TYPES else e.entity_type
        errors, warnings = validate_entity(d, today())
        if d["cin"] and db.session.execute(select(Entity.id).where(Entity.cin == d["cin"], Entity.id != e.id)).first():
            errors.append("Another entity already has this CIN/LLPIN.")
        if errors:
            for m in errors:
                flash(m, "danger")
            return render_template("entity_form.html", d=d, types=ENTITY_TYPES, staff=_staff(), e=e), 422
        before = entity_snapshot(e)
        pan = d.pop("pan")
        for k, v in d.items():
            setattr(e, k, v)
        if pan:
            e.pan_enc = encrypt(pan)
        audit.record(db.session, actor(), "ENTITY_UPDATED", "entity", e.id, e.id, before=before, after=entity_snapshot(e))
        sync_entity(e, today(), actor())
        db.session.commit()
        for m in warnings:
            flash(m, "warning")
        flash("Saved and obligations recomputed.", "success")
        return redirect(url_for("entities.show", entity_id=e.id))
    d = {c.key: getattr(e, c.key) for c in Entity.__table__.columns}
    d["pan"] = ""
    return render_template("entity_form.html", d=d, types=ENTITY_TYPES, staff=_staff(), e=e)


# ------------------------------------------------------------------ show
@bp.route("/entities/<int:entity_id>")
@require("view")
def show(entity_id: int):
    e = get_entity(entity_id)
    t = today()
    fy, fys, panel = classifications(e, request.args.get("fy"), t)
    obls = db.session.execute(select(Obligation).where(Obligation.entity_id == e.id).order_by(
        Obligation.due_date)).scalars().all()
    links = db.session.execute(select(EntityPerson).where(EntityPerson.entity_id == e.id)).scalars().all()
    person_ids = [l.person_id for l in links if l.ceased_on is None]
    din_obls = db.session.execute(select(Obligation).where(Obligation.person_id.in_(person_ids),
                                                           Obligation.superseded_at.is_(None)).order_by(
        Obligation.due_date)).scalars().all() if person_ids else []
    grouped: OrderedDict[str, list] = OrderedDict()
    show_all = request.args.get("all") == "1"
    for o in obls:
        if not show_all and (o.superseded_at or (o.pre_engagement and health(o, t) == "closed")):
            continue
        grouped.setdefault(o.period_key if o.period_key.startswith(("FY", "H")) else
                           ("One-time" if o.period_key == "ONCE" else "Events"), []).append(o)
    order = sorted(grouped, key=lambda k: (k in ("One-time", "Events"), k[3:] if k.startswith("H") else k[2:], k))
    events = db.session.execute(select(Event).where(Event.entity_id == e.id).order_by(Event.event_date.desc())).scalars().all()
    facts = {f.fy_key: f for f in db.session.execute(select(AnnualFacts).where(AnnualFacts.entity_id == e.id)).scalars()}
    flags = db.session.execute(select(PeriodFlag).where(PeriodFlag.entity_id == e.id)).scalars().all()
    decisions = db.session.execute(select(ClassificationDecision).where(
        ClassificationDecision.entity_id == e.id)).scalars().all()
    trail = []
    if has(current_user, "read_audit"):
        trail = db.session.execute(select(AuditLog).where(AuditLog.entity_id == e.id).order_by(
            AuditLog.id.desc()).limit(40)).scalars().all()
    pending_decisions = sorted({o.needs_decision for o in obls if o.needs_decision and o.superseded_at is None})
    from ..models import Document
    docs = db.session.execute(select(Document).where(Document.entity_id == e.id).order_by(Document.id.desc())).scalars().all()
    counts = {"open": sum(1 for o in obls if not o.superseded_at and health(o, t) != "closed"),
              "overdue": sum(1 for o in obls if not o.superseded_at and health(o, t) == "overdue")}
    return render_template("entity.html", e=e, fy=fy, fys=fys, panel=panel, grouped=[(k, grouped[k]) for k in order],
                           docs=docs, counts=counts,
                           din_obls=din_obls, links=links, events=events, facts=facts, flags=flags,
                           decisions=decisions, pending_decisions=pending_decisions, trail=trail,
                           event_types=EVENT_TYPES, llp_events=LLP_EVENTS, fact_fields=FACT_FIELDS,
                           masked_pan=mask_pan(decrypt(e.pan_enc)), show_all=show_all,
                           health=lambda o: health(o, t))


# ----------------------------------------------------------- annual facts
@bp.route("/entities/<int:entity_id>/facts")
@require("view")
def facts_screen(entity_id: int):
    from ..services import FACT_INFO, fact_fields_for
    e = get_entity(entity_id)
    fy, fys, _ = classifications(e, request.args.get("fy"), today())
    rows = {f.fy_key: f for f in db.session.execute(select(AnnualFacts).where(AnnualFacts.entity_id == e.id)).scalars()}
    stale_counts = dict(db.session.execute(select(Obligation.period_key, func.count(Obligation.id)).where(
        Obligation.entity_id == e.id, Obligation.facts_stale.is_(True), Obligation.superseded_at.is_(None)).group_by(
        Obligation.period_key)).all())
    return render_template("facts.html", e=e, fy=fy, fys=list(reversed(fys)), rows=rows, info=FACT_INFO,
                           fields=fact_fields_for(e.entity_type), stale_counts=stale_counts, current=rows.get(fy.key))


@bp.route("/entities/<int:entity_id>/notes", methods=["POST"])
@require("edit_entity")
def save_notes(entity_id: int):
    e = get_entity(entity_id)
    before = e.notes
    e.notes = (request.form.get("notes") or "").strip()[:5000] or None
    audit.record(db.session, actor(), "NOTES_SAVED", "entity", e.id, e.id, before={"notes": before}, after={"notes": e.notes})
    db.session.commit()
    flash("Notes saved.", "success")
    return redirect(url_for("entities.show", entity_id=e.id))


@bp.route("/entities/<int:entity_id>/documents", methods=["POST"])
@require("edit_entity")
def upload_document(entity_id: int):
    from ..models import Document
    from .obligations import save_upload
    from ..services import ValidationError
    e = get_entity(entity_id)
    try:
        saved = save_upload(request.files.get("file"))
        if saved is None:
            raise ValidationError("Choose a file to upload.")
    except ValidationError as v:
        for m in v.messages:
            flash(m, "danger")
        return redirect(url_for("entities.show", entity_id=e.id)), 303
    stored, original, size = saved
    doc = Document(entity_id=e.id, title=(request.form.get("title") or original)[:200], original_name=original,
                   stored_name=stored, size=size, uploaded_by_id=current_user.id)
    db.session.add(doc)
    db.session.flush()
    audit.record(db.session, actor(), "DOCUMENT_UPLOADED", "document", doc.id, e.id,
                 after={"title": doc.title, "file": original, "size": size})
    db.session.commit()
    flash("Document uploaded.", "success")
    return redirect(url_for("entities.show", entity_id=e.id))


@bp.route("/documents/<int:doc_id>")
@require("view")
def download_document(doc_id: int):
    from pathlib import Path

    from flask import current_app, send_file

    from ..models import Document
    doc = db.session.get(Document, doc_id) or abort(404)
    get_entity(doc.entity_id)
    path = Path(current_app.config["UPLOAD_DIR"]) / doc.stored_name
    if not path.is_file():
        abort(404)
    audit.record(db.session, actor(), "FILE_DOWNLOADED", "document", doc.id, doc.entity_id)
    db.session.commit()
    return send_file(path, download_name=doc.original_name, as_attachment=True)


BOOL_FACTS ={"deposits_outstanding_31mar", "has_subs_assoc_jv", "ind_as", "cost_audit_applicable", "csr_override",
              "auditor_appointed_at_agm"}
DATE_FACTS = {"agm_date", "board_approval_date", "isin_obtained_date"}


@bp.route("/entities/<int:entity_id>/facts", methods=["POST"])
@require("edit_entity")
def save_facts(entity_id: int):
    e = get_entity(entity_id)
    fy_key = request.form.get("fy_key", "")
    valid = {f.key for f in classifications(e, None, today())[1]}
    if fy_key not in valid:
        flash("Choose a financial year of this entity.", "danger")
        return redirect(url_for("entities.show", entity_id=e.id)), 303
    row = db.session.execute(select(AnnualFacts).where(AnnualFacts.entity_id == e.id,
                                                       AnnualFacts.fy_key == fy_key)).scalar()
    before = None
    if row is None:
        row = AnnualFacts(entity_id=e.id, fy_key=fy_key)
        db.session.add(row)
    else:
        before = {f: getattr(row, f) for f in FACT_FIELDS}
    for f in FACT_FIELDS:
        raw = request.form.get(f)
        if f in BOOL_FACTS:
            setattr(row, f, to_tri(raw))
        elif f in DATE_FACTS:
            v = to_date(raw)
            if v and v > today() and f != "board_approval_date":
                flash(f"{f.replace('_', ' ').capitalize()} cannot be in the future.", "danger")
                db.session.rollback()
                return redirect(url_for("entities.facts_screen", entity_id=e.id, fy=fy_key)), 303
            setattr(row, f, v)
        else:
            setattr(row, f, to_money(raw))
    db.session.flush()
    audit.record(db.session, actor(), "FACTS_SAVED", "annual_facts", f"{e.id}:{fy_key}", e.id, before=before,
                 after={f: getattr(row, f) for f in FACT_FIELDS})
    stats = sync_entity(e, today(), actor())
    db.session.commit()
    flash(f"Facts for {fy_key} saved. {stats['updated']} obligations updated, {stats['inserted']} added, "
          f"{stats['superseded']} no longer apply.", "success")
    return redirect(url_for("entities.facts_screen", entity_id=e.id, fy=fy_key))


@bp.route("/entities/<int:entity_id>/flags", methods=["POST"])
@require("edit_entity")
def save_flag(entity_id: int):
    e = get_entity(entity_id)
    period, name = request.form.get("period_key", "").strip(), request.form.get("name")
    if name not in ("msme_over_45", "deposits_outstanding") or not period:
        abort(422)
    value = request.form.get("value") == "yes"
    row = db.session.execute(select(PeriodFlag).where(PeriodFlag.entity_id == e.id, PeriodFlag.period_key == period,
                                                      PeriodFlag.name == name)).scalar()
    before = row.value if row else None
    if row is None:
        db.session.add(PeriodFlag(entity_id=e.id, period_key=period, name=name, value=value))
    else:
        row.value = value
    audit.record(db.session, actor(), "FLAG_SAVED", "period_flag", f"{e.id}:{period}:{name}", e.id,
                 before={name: before}, after={name: value})
    sync_entity(e, today(), actor())
    db.session.commit()
    flash("Saved.", "success")
    return redirect(url_for("entities.show", entity_id=e.id))


# ---------------------------------------------------------------- events
def rules_for_event(etype: str) -> list:
    from ..services import rulepack
    return [r for r in rulepack().rules if etype in r.event_types]


@bp.route("/entities/<int:entity_id>/events/new")
@require("record_event")
def new_event(entity_id: int):
    e = get_entity(entity_id)
    specs = events_for(e.entity_type)
    etype = request.args.get("type") or next(iter(specs))
    if etype not in specs:
        abort(404)
    links = db.session.execute(select(EntityPerson).where(EntityPerson.entity_id == e.id,
                                                          EntityPerson.ceased_on.is_(None))).scalars().all()
    creates = rules_for_event(etype)
    if request.headers.get("HX-Request"):          # HTMX: swap only the typed fields
        from flask import get_template_attribute
        return get_template_attribute("_macros.html", "fields_block")(etype, specs[etype], creates, links)
    return render_template("event_form.html", e=e, specs=specs, etype=etype, spec=specs[etype], creates=creates,
                           links=links)


def _person_side_effect(e: Entity, etype: str, d: date, attrs: dict) -> list[str]:
    """Director appointments/cessations keep the entity–person links in step with events."""
    mode = LINK_EVENTS.get(etype)
    if mode is None:
        return []
    din = (attrs.get("din") or "").strip()
    err = validate_din(din)
    if err:
        return [err]
    p = db.session.execute(select(Person).where(Person.din == din)).scalar()
    link = None
    if p is not None:
        link = db.session.execute(select(EntityPerson).where(EntityPerson.entity_id == e.id, EntityPerson.person_id == p.id,
                                                             EntityPerson.ceased_on.is_(None))).scalar()
    admit = mode == "link" or (mode == "llp" and attrs.get("change") == "ADMISSION")
    cease = mode == "cease" or (mode == "llp" and attrs.get("change") == "CESSATION")
    if admit:
        if p is None:
            allot = to_date(attrs.get("din_allotment_date"))
            if not attrs.get("person_name") or allot is None:
                return ["This DIN is new to the firm: enter the person's name and DIN allotment date."]
            p = Person(name=attrs["person_name"], din=din, din_allotment_date=allot,
                       dsc_expiry=to_date(attrs.get("dsc_expiry")))
            db.session.add(p)
            db.session.flush()
            audit.record(db.session, actor(), "PERSON_CREATED", "person", p.id, e.id, after={"name": p.name, "din": din})
        if link is None:
            link = EntityPerson(entity_id=e.id, person_id=p.id, appointed_on=d,
                                designation=attrs.get("designation") or ("Designated Partner" if e.entity_type == "LLP" else "Director"))
            db.session.add(link)
            db.session.flush()
            audit.record(db.session, actor(), "DIRECTOR_LINKED", "entity_person", link.id, e.id,
                         after={"din": din, "designation": link.designation, "appointed_on": d})
    elif link is None:
        return [f"DIN {din} is not a current director / partner of {e.name}."]
    elif cease:
        link.ceased_on = d
        audit.record(db.session, actor(), "DIRECTOR_CEASED", "entity_person", link.id, e.id, after={"din": din, "ceased_on": d})
    elif attrs.get("designation"):
        before = link.designation
        link.designation = attrs["designation"]
        audit.record(db.session, actor(), "DESIGNATION_CHANGED", "entity_person", link.id, e.id,
                     before={"designation": before}, after={"designation": link.designation})
    return []


@bp.route("/entities/<int:entity_id>/events", methods=["POST"])
@require("record_event")
def add_event(entity_id: int):
    e = get_entity(entity_id)
    etype, d = request.form.get("type"), to_date(request.form.get("event_date"))
    specs = events_for(e.entity_type)
    problems = []
    if etype not in specs:
        problems.append("Choose an event type that applies to this entity.")
    if d is None:
        problems.append("Enter the event date.")
    elif d < e.incorporation_date:
        problems.append("The event date cannot be before incorporation.")
    elif d > today() + timedelta(days=90):
        problems.append("The event date is more than 90 days ahead. Record events when they happen.")
    attrs: dict = {}
    if not problems:
        for f in specs[etype]["fields"]:
            name, kind = f[0], f[2]
            raw = (request.form.get(name) or "").strip()
            if not raw:
                continue
            attrs[name] = to_money(raw) if kind == "money" else raw
        for legacy in ("kind", "amount", "cause"):          # older generic form
            if legacy not in attrs and request.form.get(legacy):
                attrs[legacy] = to_money(request.form[legacy]) if legacy == "amount" else request.form[legacy]
        problems += _person_side_effect(e, etype, d, attrs)
    if problems:
        db.session.rollback()
        for m in problems:
            flash(m, "danger")
        if request.form.get("from_form"):
            return redirect(url_for("entities.new_event", entity_id=e.id, type=etype)), 303
        return redirect(url_for("entities.show", entity_id=e.id)), 303
    if etype == "AUTH_CAPITAL_INCREASE" and attrs.get("new_authorised"):
        if attrs["new_authorised"] < e.paid_up_capital:
            flash("The new authorised capital is below the paid-up capital.", "danger")
            db.session.rollback()
            return redirect(url_for("entities.new_event", entity_id=e.id, type=etype)), 303
        audit.record(db.session, actor(), "ENTITY_UPDATED", "entity", e.id, e.id,
                     before={"nominal_capital": e.nominal_capital}, after={"nominal_capital": attrs["new_authorised"]})
        e.nominal_capital = attrs["new_authorised"]
    ev = Event(entity_id=e.id, type=etype, event_date=d, reference=request.form.get("reference") or None,
               attrs={k: v for k, v in attrs.items() if k not in ("person_name", "din_allotment_date")},
               created_by_id=current_user.id)
    db.session.add(ev)
    db.session.flush()
    audit.record(db.session, actor(), "EVENT_RECORDED", "event", ev.id, e.id,
                 after={"type": etype, "date": d, "reference": ev.reference, "attrs": ev.attrs})
    stats = sync_entity(e, today(), actor())
    db.session.commit()
    flash(f"{EVENT_TYPES[etype]} recorded: {stats['inserted']} new obligation(s).", "success")
    return redirect(url_for("entities.show", entity_id=e.id))


# ------------------------------------------------------------- directors
@bp.route("/entities/<int:entity_id>/directors", methods=["POST"])
@require("edit_entity")
def add_director(entity_id: int):
    e = get_entity(entity_id)
    din = (request.form.get("din") or "").strip()
    err = validate_din(din)
    if err:
        flash(err, "danger")
        return redirect(url_for("entities.show", entity_id=e.id)), 303
    p = db.session.execute(select(Person).where(Person.din == din)).scalar()
    if p is None:
        allot = to_date(request.form.get("din_allotment_date"))
        name = (request.form.get("name") or "").strip()
        if not name or allot is None:
            flash("For a new DIN enter the person's name and DIN allotment date.", "danger")
            return redirect(url_for("entities.show", entity_id=e.id)), 303
        pan = (request.form.get("pan") or "").strip().upper()
        p = Person(name=name, din=din, din_allotment_date=allot, pan_enc=encrypt(pan) if pan else None,
                   email=request.form.get("email") or None, mobile=request.form.get("mobile") or None,
                   dsc_expiry=to_date(request.form.get("dsc_expiry")))
        db.session.add(p)
        db.session.flush()
        audit.record(db.session, actor(), "PERSON_CREATED", "person", p.id, e.id, after={"name": name, "din": din})
    link = EntityPerson(entity_id=e.id, person_id=p.id, designation=request.form.get("designation") or "Director",
                        appointed_on=to_date(request.form.get("appointed_on")))
    db.session.add(link)
    db.session.flush()
    audit.record(db.session, actor(), "DIRECTOR_LINKED", "entity_person", link.id, e.id,
                 after={"din": din, "designation": link.designation, "appointed_on": link.appointed_on})
    sync_entity(e, today(), actor())
    db.session.commit()
    flash(f"{p.name} linked.", "success")
    return redirect(url_for("entities.show", entity_id=e.id))


# ------------------------------------------------------------- decisions
@bp.route("/entities/<int:entity_id>/decisions", methods=["POST"])
@require("decide")
def decide(entity_id: int):
    e = get_entity(entity_id)
    key, value, reason = request.form.get("key", ""), request.form.get("value", ""), (request.form.get("reason") or "").strip()
    allowed = {"SMALL": ("SMALL", "NOT_SMALL"), "9B_REVERSION": ("CONTINUE", "STOP")}
    kind = key.split(":")[0]
    if kind not in allowed or value not in allowed[kind]:
        abort(422)
    if len(reason) < 20:
        flash("Record the reason for the decision (at least 20 characters).", "danger")
        return redirect(url_for("entities.show", entity_id=e.id)), 303
    row = db.session.execute(select(ClassificationDecision).where(ClassificationDecision.entity_id == e.id,
                                                                  ClassificationDecision.key == key)).scalar()
    before = {"value": row.value, "reason": row.reason} if row else None
    if row is None:
        row = ClassificationDecision(entity_id=e.id, key=key, value=value, reason=reason, decided_by_id=current_user.id)
        db.session.add(row)
    else:
        row.value, row.reason, row.decided_by_id = value, reason, current_user.id
    audit.record(db.session, actor(), "DECISION_RECORDED", "classification_decision", f"{e.id}:{key}", e.id,
                 before=before, after={"value": value, "reason": reason})
    sync_entity(e, today(), actor())
    db.session.commit()
    flash("Decision recorded and obligations recomputed.", "success")
    return redirect(url_for("entities.show", entity_id=e.id))


# ------------------------------------------------------ archive / delete
@bp.route("/entities/<int:entity_id>/archive", methods=["POST"])
@require("archive_entity")
def archive(entity_id: int):
    e = get_entity(entity_id)
    e.archived = True
    audit.record(db.session, actor(), "ENTITY_ARCHIVED", "entity", e.id, e.id, after={"archived": True})
    db.session.commit()
    flash(f"{e.name} archived. Its history is kept.", "success")
    return redirect(url_for("entities.index"))


@bp.route("/entities/<int:entity_id>/delete", methods=["POST"])
@require("delete_entity")
def remove(entity_id: int):
    e = get_entity(entity_id)
    obl_ids = select(Obligation.id).where(Obligation.entity_id == e.id)
    if db.session.execute(select(func.count(Filing.id)).where(Filing.obligation_id.in_(obl_ids))).scalar():
        flash("This entity has recorded filings and cannot be deleted. Archive it instead.", "danger")
        return redirect(url_for("entities.show", entity_id=e.id)), 303
    snap = entity_snapshot(e)
    for model in (Notification,):
        db.session.execute(delete(model).where(model.obligation_id.in_(obl_ids)))
    from ..models import Document
    for model in (Obligation, AnnualFacts, PeriodFlag, ClassificationDecision, EntityPerson, Event, Document):
        db.session.execute(delete(model).where(model.entity_id == e.id))
    db.session.delete(e)
    audit.record(db.session, actor(), "ENTITY_DELETED", "entity", entity_id, entity_id, before=snap)
    db.session.commit()
    flash("Entity deleted. The audit trail keeps a copy of its master data.", "success")
    return redirect(url_for("entities.index"))


# ------------------------------------------------------------ PAN reveal
@bp.route("/entities/<int:entity_id>/pan", methods=["POST"])
@require("reveal_pan")
def reveal_pan(entity_id: int):
    e = get_entity(entity_id)
    audit.record(db.session, actor(), "PAN_REVEALED", "entity", e.id, e.id)
    db.session.commit()
    return f'<span class="font-monospace">{escape(decrypt(e.pan_enc) or "—")}</span>'


@bp.route("/persons/<int:person_id>/pan", methods=["POST"])
@require("reveal_pan")
def reveal_person_pan(person_id: int):
    p = db.session.get(Person, person_id) or abort(404)
    audit.record(db.session, actor(), "PAN_REVEALED", "person", p.id)
    db.session.commit()
    return f'<span class="font-monospace">{escape(decrypt(p.pan_enc) or "—")}</span>'
