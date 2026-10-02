"""Director view, fee calculator, board-meeting planner and the onboarding wizard."""
from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy import select

import engine
from engine.dates import company_first_fy_end, due_date, llp_election_available, llp_first_fy_end, standard_fy_end
from engine.generator import entity_fys, horizon_end
from engine.types import EntityIn, FactsIn, PersonIn

from .. import audit
from ..auth import actor, decrypt, encrypt, mask_pan, today
from ..models import AnnualFacts, Entity, EntityPerson, Event, Obligation, Person, db
from ..permissions import can_see_entity, deny, has, require
from ..services import (classifications, health, rulepack, sync_entity, sync_person, validate_din, validate_entity,
                        visible_entities_query)
from .entities import ENTITY_TYPES, to_date, to_money

people = Blueprint("people", __name__)
tools = Blueprint("tools", __name__, url_prefix="/tools")
wizard = Blueprint("wizard", __name__)


# ================================================================ directors
def visible_person_ids():
    ents = visible_entities_query(current_user).with_only_columns(Entity.id)
    return select(EntityPerson.person_id).where(EntityPerson.entity_id.in_(ents))


def get_person(person_id: int) -> Person:
    p = db.session.get(Person, person_id) or abort(404)
    if not has(current_user, "view_all") and not any(can_see_entity(current_user, l.entity) for l in p.links):
        deny("view_all", "This person is not a director of an entity assigned to you.", object_type="person",
             object_id=person_id)
    return p


def next_kyc(p: Person) -> Obligation | None:
    return db.session.execute(select(Obligation).where(
        Obligation.person_id == p.id, Obligation.rule_code.like("DIR3KYC%"), Obligation.superseded_at.is_(None),
        Obligation.status.not_in(["FILED", "ROC_APPROVED", "NOT_APPLICABLE", "WAIVED"])).order_by(
        Obligation.due_date)).scalars().first()


@people.route("/directors")
@require("view")
def index():
    q = select(Person).where(Person.id.in_(visible_person_ids())).order_by(Person.name)
    term = (request.args.get("q") or "").strip()
    if term:
        q = q.where(Person.name.ilike(f"%{term}%") | Person.din.like(f"%{term}%"))
    persons = db.session.execute(q).scalars().all()
    return render_template("directors.html", persons=persons, next_kyc=next_kyc, term=term, person=None)


@people.route("/directors/<int:person_id>")
@require("view")
def show(person_id: int):
    p = get_person(person_id)
    obls = db.session.execute(select(Obligation).where(Obligation.person_id == p.id).order_by(Obligation.due_date)).scalars().all()
    changes = db.session.execute(select(Event).where(Event.person_id == p.id).order_by(Event.event_date.desc())).scalars().all()
    computed = engine.kyc_due(p.din_allotment_date)
    t = today()
    return render_template("directors.html", person=p, obls=obls, changes=changes, computed=computed,
                           masked_pan=mask_pan(decrypt(p.pan_enc)), health=lambda o: health(o, t),
                           legacy=p.din_allotment_date <= date(2025, 3, 31))


@people.route("/directors/<int:person_id>/edit", methods=["POST"])
@require("edit_entity")
def edit(person_id: int):
    p = get_person(person_id)
    before = {"email": p.email, "mobile": p.mobile, "dsc_expiry": p.dsc_expiry, "din_status": p.din_status}
    p.email = request.form.get("email") or None
    p.mobile = request.form.get("mobile") or None
    p.dsc_expiry = to_date(request.form.get("dsc_expiry"))
    if request.form.get("din_status") in ("APPROVED", "DEACTIVATED"):
        p.din_status = request.form["din_status"]
    audit.record(db.session, actor(), "PERSON_UPDATED", "person", p.id, before=before,
                 after={"email": p.email, "mobile": p.mobile, "dsc_expiry": p.dsc_expiry, "din_status": p.din_status})
    db.session.commit()
    flash("Saved.", "success")
    return redirect(url_for("people.show", person_id=p.id))


@people.route("/directors/<int:person_id>/detail-change", methods=["POST"])
@require("record_event")
def detail_change(person_id: int):
    p = get_person(person_id)
    d = to_date(request.form.get("event_date"))
    what = request.form.get("changed") or "mobile"
    if d is None or d > today():
        flash("Enter the date of the change (not in the future).", "danger")
        return redirect(url_for("people.show", person_id=p.id)), 303
    ev = Event(person_id=p.id, type="DIRECTOR_DETAIL_CHANGE", event_date=d, attrs={"changed": what},
               reference=request.form.get("reference") or None, created_by_id=current_user.id)
    db.session.add(ev)
    db.session.flush()
    audit.record(db.session, actor(), "EVENT_RECORDED", "event", ev.id, after={"type": ev.type, "din": p.din, "date": d,
                                                                                 "changed": what})
    st = sync_person(p, today(), actor())
    db.session.commit()
    flash(f"Change recorded: {st['inserted']} DIR-3 KYC Web obligation(s) created (does not reset the 3-year cycle).",
          "success")
    return redirect(url_for("people.show", person_id=p.id))


@people.route("/directors/<int:person_id>/kyc-override", methods=["POST"])
@require("decide")
def kyc_override(person_id: int):
    p = get_person(person_id)
    d = to_date(request.form.get("first_due"))
    reason = (request.form.get("reason") or "").strip()
    if len(reason) < 20:
        flash("Give the reason for overriding the KYC cycle (at least 20 characters).", "danger")
        return redirect(url_for("people.show", person_id=p.id)), 303
    if d is not None and (d.month, d.day) != (6, 30):
        flash("A DIR-3 KYC cycle always ends on 30 June.", "danger")
        return redirect(url_for("people.show", person_id=p.id)), 303
    before = p.kyc_override_first_due
    p.kyc_override_first_due = d
    audit.record(db.session, actor(), "KYC_CYCLE_OVERRIDDEN", "person", p.id, before={"first_due": before},
                 after={"first_due": d, "reason": reason})
    sync_person(p, today(), actor())
    db.session.commit()
    flash("KYC cycle updated." if d else "Override removed — the computed cycle applies.", "success")
    return redirect(url_for("people.show", person_id=p.id))


# ============================================================ fee calculator
@tools.route("/fees")
@require("view")
def fees():
    rp = rulepack()
    fee_rules = [r for r in rp.rules if r.fee_regime != "NONE"]
    ents = db.session.execute(visible_entities_query(current_user).order_by(Entity.name)).scalars().all()
    a = request.args
    result, err, ein = None, None, None
    code = a.get("rule") or "AOC4"
    due, filed = to_date(a.get("due")), to_date(a.get("filed"))
    if a.get("entity_id"):
        e = db.session.get(Entity, int(a["entity_id"]))
        if e is None or not can_see_entity(current_user, e):
            abort(404)
        from ..services import entity_in
        ein = entity_in(e)
    elif a.get("etype"):
        ein = EntityIn(0, "Ad-hoc", a["etype"] if a["etype"] in ENTITY_TYPES else "PRIVATE", date(2000, 1, 1),
                       has_share_capital=a.get("share_capital", "on") == "on" and a["etype"] != "LLP",
                       nominal_capital=to_money(a.get("nominal")) or 0.0, llp_contribution=to_money(a.get("contribution")) or 0.0)
    if ein and due and filed and code in rp.by_code:
        small = {"yes": True, "no": False}.get(a.get("small"))
        prior = int(a.get("prior") or 0) if (a.get("prior") or "0").isdigit() else 0
        result = engine.compute_fee(code, ein, due, filed, prior, rp, period_key=a.get("period") or None,
                                    charge_amount=to_money(a.get("charge_amount")), is_small=small)
    elif a:
        err = "Choose a form, an entity (or type and capital), the due date and the filing date."
    if request.headers.get("HX-Request"):
        from flask import get_template_attribute
        return get_template_attribute("_macros.html", "fee_result")(result, err)
    return render_template("tools.html", mode="fees", fee_rules=fee_rules, ents=ents, a=a, code=code, result=result,
                           err=err, ein=ein)


# ======================================================== board planner
def board_plan(e: Entity, regime: str, meetings: list[date], t: date) -> dict:
    """Checks for s.173: REGULAR (≥4/yr, gap ≤120 days) or RELAXED (one in each half of the
    calendar year, gap ≥90 days). Returns findings and the next latest/earliest date."""
    out = {"regime": regime, "warnings": [], "next_by": None, "next_not_before": None, "rows": []}
    first_by = e.incorporation_date + timedelta(days=30)
    prev = None
    for m in meetings:
        gap = (m - prev).days if prev else None
        ok = True
        if gap is not None and regime == "REGULAR" and gap > 120:
            ok = False
            out["warnings"].append(f"{gap} days between {prev:%d-%m-%Y} and {m:%d-%m-%Y} — more than 120 (s.173(1)).")
        if gap is not None and regime == "RELAXED" and gap < 90:
            ok = False
            out["warnings"].append(f"Only {gap} days between {prev:%d-%m-%Y} and {m:%d-%m-%Y} — at least 90 needed (s.173(5)).")
        out["rows"].append((m, gap, ok))
        prev = m
    if not meetings:
        out["next_by"] = first_by
        out["warnings"].append(f"No Board meeting recorded. The first meeting was due by {first_by:%d-%m-%Y} (s.173(1)).")
        return out
    last = meetings[-1]
    if regime == "REGULAR":
        out["next_by"] = last + timedelta(days=120)
        fy_start = date(standard_fy_end(t).year - 1, 4, 1)
        held = [m for m in meetings if m >= fy_start]
        out["summary"] = f"{len(held)} meeting(s) so far in the FY starting {fy_start:%d-%m-%Y}; at least 4 are needed."
    elif regime == "RELAXED":
        half_start = date(t.year, 1, 1) if t.month <= 6 else date(t.year, 7, 1)
        half_end = date(t.year, 6, 30) if t.month <= 6 else date(t.year, 12, 31)
        held = [m for m in meetings if half_start <= m <= half_end]
        out["next_not_before"] = last + timedelta(days=90)
        out["next_by"] = half_end if not held else (date(t.year, 12, 31) if t.month <= 6 else date(t.year + 1, 6, 30))
        out["summary"] = (f"{'A meeting has' if held else 'No meeting has'} been held in the current half-year "
                          f"({half_start:%d-%m-%Y} to {half_end:%d-%m-%Y}).")
    if out["next_by"] and out["next_by"] < t:
        out["warnings"].append(f"The next meeting was due by {out['next_by']:%d-%m-%Y} — overdue.")
    elif out["next_by"] and (out["next_by"] - t).days <= 30:
        out["warnings"].append(f"The next meeting must be held by {out['next_by']:%d-%m-%Y} "
                               f"({(out['next_by'] - t).days} days).")
    return out


@tools.route("/board")
@require("view")
def board():
    ents = [e for e in db.session.execute(visible_entities_query(current_user).where(Entity.entity_type != "LLP")
                                          .order_by(Entity.name)).scalars()]
    e = None
    if request.args.get("entity_id"):
        e = db.session.get(Entity, int(request.args["entity_id"]))
        if e is None or not can_see_entity(current_user, e) or e.entity_type == "LLP":
            abort(404)
    elif ents:
        e = ents[0]
    plan, regime_cls = None, None
    if e is not None:
        t = today()
        _, _, panel = classifications(e, None, t)
        regime_cls = next(c for c in panel if c.name == "board_meeting_regime")
        meetings = sorted(db.session.execute(select(Event.event_date).where(
            Event.entity_id == e.id, Event.type == "BOARD_MEETING")).scalars().all())
        plan = board_plan(e, regime_cls.result, meetings, t) if regime_cls.result != "NA" else None
    return render_template("tools.html", mode="board", ents=ents, e=e, plan=plan, regime=regime_cls)


# ============================================================ onboarding wizard
STEPS = ["Entity", "Financial year", "Directors", "Annual facts", "Preview"]


def _wiz() -> dict:
    return session.setdefault("wiz", {})


def _entity_from_wiz(w: dict) -> EntityIn:
    d = w["entity"]
    return EntityIn("new", d["name"], d["entity_type"], date.fromisoformat(d["incorporation_date"]),
                    has_share_capital=d["has_share_capital"], nominal_capital=d["nominal_capital"],
                    paid_up_capital=d["paid_up_capital"], llp_contribution=d["llp_contribution"],
                    single_director=d["single_director"], startup=d["startup"], is_holding=d["is_holding"],
                    is_subsidiary=d["is_subsidiary"], subsidiary_of_public=d["subsidiary_of_public"],
                    engagement_start=date.fromisoformat(d["engagement_start"]) if d.get("engagement_start") else None,
                    llp_elect_longer_first_fy=w.get("elect_longer", False))


def _facts_from_wiz(w: dict) -> dict[str, FactsIn]:
    out = {}
    for key, f in (w.get("facts") or {}).items():
        out[key] = FactsIn(key, **{k: (date.fromisoformat(v) if k == "agm_date" and v else v) for k, v in f.items()})
    return out


def _persons_from_wiz(w: dict) -> list[PersonIn]:
    return [PersonIn(i, p["name"], p["din"], date.fromisoformat(p["allot"])) for i, p in enumerate(w.get("directors", []))
            if not p.get("existing")]


def latest_fy(ein: EntityIn, t: date):
    fys = entity_fys(ein, horizon_end(t))
    done = [f for f in fys if f.end <= t]
    return (done[-1] if done else fys[0]), (done[-2] if len(done) > 1 else None), fys


@wizard.route("/entities/onboard", methods=["GET", "POST"])
@require("edit_entity")
def onboard():
    w = _wiz()
    step = int(request.values.get("step", 1))
    if request.args.get("restart"):
        session.pop("wiz", None)
        return redirect(url_for("wizard.onboard"))
    if step > 1 and "entity" not in w:
        return redirect(url_for("wizard.onboard"))
    t = today()
    if request.method == "POST":
        f = request.form
        if step == 1:
            d = {"name": (f.get("name") or "").strip(), "entity_type": f.get("entity_type") if f.get("entity_type") in ENTITY_TYPES else "PRIVATE",
                 "cin": (f.get("cin") or "").strip().upper() or None, "pan": (f.get("pan") or "").strip().upper(),
                 "incorporation_date": to_date(f.get("incorporation_date")), "engagement_start": to_date(f.get("engagement_start")),
                 "nominal_capital": to_money(f.get("nominal_capital")) or 0.0, "paid_up_capital": to_money(f.get("paid_up_capital")) or 0.0,
                 "llp_contribution": to_money(f.get("llp_contribution")) or 0.0}
            for flag in ("has_share_capital", "single_director", "startup", "is_holding", "is_subsidiary", "subsidiary_of_public"):
                d[flag] = f.get(flag) == "on"
            if d["entity_type"] == "LLP":
                d["has_share_capital"] = False
            errors, warnings = validate_entity(d, t)
            if d["cin"] and db.session.execute(select(Entity.id).where(Entity.cin == d["cin"])).first():
                errors.append("An entity with this CIN/LLPIN already exists.")
            if errors:
                for m in errors:
                    flash(m, "danger")
                return render_template("wizard.html", step=1, steps=STEPS, d=d, types=ENTITY_TYPES), 422
            for m in warnings:
                flash(m, "warning")
            d["pan_enc"] = encrypt(d.pop("pan")) if d.get("pan") else None     # never keep a plain PAN in the cookie
            for k in ("incorporation_date", "engagement_start"):
                d[k] = d[k].isoformat() if d[k] else None
            w.clear()
            w["entity"] = d
            session.modified = True
            return redirect(url_for("wizard.onboard", step=2))
        if step == 2:
            w["elect_longer"] = f.get("elect_longer") == "on"
            session.modified = True
            return redirect(url_for("wizard.onboard", step=3))
        if step == 3:
            dirs, problems = [], []
            for i in range(6):
                din = (f.get(f"din{i}") or "").strip()
                if not din:
                    continue
                if validate_din(din):
                    problems.append(f"Row {i + 1}: {validate_din(din)}")
                    continue
                existing = db.session.execute(select(Person).where(Person.din == din)).scalar()
                allot = to_date(f.get(f"allot{i}"))
                name = (f.get(f"name{i}") or "").strip()
                if existing is None and (not name or allot is None):
                    problems.append(f"Row {i + 1}: DIN {din} is new — enter the name and DIN allotment date.")
                    continue
                dirs.append({"din": din, "name": existing.name if existing else name,
                             "allot": (existing.din_allotment_date if existing else allot).isoformat(),
                             "designation": f.get(f"desig{i}") or "Director", "existing": existing is not None})
            if problems:
                for m in problems:
                    flash(m, "danger")
                return redirect(url_for("wizard.onboard", step=3)), 303
            w["directors"] = dirs
            session.modified = True
            return redirect(url_for("wizard.onboard", step=4))
        if step == 4:
            ein = _entity_from_wiz(w)
            fy, prev, _ = latest_fy(ein, t)
            facts = {fy.key: {"paid_up_capital": to_money(f.get("paid_up_capital")), "turnover": to_money(f.get("turnover")),
                              "net_worth": to_money(f.get("net_worth")), "net_profit": to_money(f.get("net_profit")),
                              "llp_contribution": to_money(f.get("llp_contribution")),
                              "agm_date": (to_date(f.get("agm_date")).isoformat() if to_date(f.get("agm_date")) else None),
                              "auditor_appointed_at_agm": {"yes": True, "no": False}.get(f.get("auditor_appointed_at_agm"))}}
            if prev is not None and to_money(f.get("prev_turnover")) is not None:
                facts[prev.key] = {"turnover": to_money(f.get("prev_turnover"))}
            w["facts"] = facts
            session.modified = True
            return redirect(url_for("wizard.onboard", step=5))
        if step == 5:
            return _commit(w, t)
    # ---------------- GET
    ctx = {"step": step, "steps": STEPS, "types": ENTITY_TYPES, "d": w.get("entity") or {"entity_type": "PRIVATE",
                                                                                        "has_share_capital": True}}
    if step >= 2:
        ein = _entity_from_wiz(w)
        inc = ein.incorporation_date
        if ein.is_llp:
            ctx["llp_options"] = (llp_first_fy_end(inc, False), llp_first_fy_end(inc, True) if llp_election_available(inc) else None)
        else:
            ctx["first_end"] = company_first_fy_end(inc)
            ctx["first_agm"] = due_date(ctx["first_end"], {"months": 9})
        ctx["elect_longer"] = w.get("elect_longer", False)
        fy, prev, fys = latest_fy(ein, t)
        ctx.update(fy=fy, prev=prev, fys=fys, ein=ein, directors=w.get("directors", []))
    if step == 5:
        specs = engine.generate(ein, _facts_from_wiz(w), [], _persons_from_wiz(w), rulepack(), t)
        ctx["specs"] = specs
        ctx["overdue"] = [s for s in specs if s.due_date < t and not s.pre_engagement]
        by = {}
        for s in specs:
            by.setdefault(s.period_key if s.period_key.startswith(("FY", "H", "KYC")) else "One-time / events", []).append(s)
        ctx["by_period"] = by
    return render_template("wizard.html", **ctx)


def _commit(w: dict, t: date):
    d = dict(w["entity"])
    pan_enc = d.pop("pan_enc", None)
    for k in ("incorporation_date", "engagement_start"):
        d[k] = date.fromisoformat(d[k]) if d.get(k) else None
    if d["cin"] and db.session.execute(select(Entity.id).where(Entity.cin == d["cin"])).first():
        flash("An entity with this CIN/LLPIN was added meanwhile.", "danger")
        return redirect(url_for("wizard.onboard", step=1)), 303
    e = Entity(**d, pan_enc=pan_enc, llp_elect_longer_first_fy=w.get("elect_longer", False),
               preparer_id=None if has(current_user, "view_all") else current_user.id)
    db.session.add(e)
    db.session.flush()
    from .entities import entity_snapshot
    audit.record(db.session, actor(), "ENTITY_CREATED", "entity", e.id, e.id, after={**entity_snapshot(e), "via": "wizard"})
    for p in w.get("directors", []):
        person = db.session.execute(select(Person).where(Person.din == p["din"])).scalar()
        if person is None:
            person = Person(name=p["name"], din=p["din"], din_allotment_date=date.fromisoformat(p["allot"]))
            db.session.add(person)
            db.session.flush()
            audit.record(db.session, actor(), "PERSON_CREATED", "person", person.id, e.id, after={"name": person.name, "din": p["din"]})
        link = EntityPerson(entity_id=e.id, person_id=person.id, designation=p["designation"], appointed_on=d["incorporation_date"])
        db.session.add(link)
        db.session.flush()
        audit.record(db.session, actor(), "DIRECTOR_LINKED", "entity_person", link.id, e.id, after={"din": p["din"]})
    for key, f in (w.get("facts") or {}).items():
        row = AnnualFacts(entity_id=e.id, fy_key=key, **{k: (date.fromisoformat(v) if k == "agm_date" and v else v)
                                                         for k, v in f.items()})
        db.session.add(row)
        db.session.flush()
        audit.record(db.session, actor(), "FACTS_SAVED", "annual_facts", f"{e.id}:{key}", e.id, after=f)
    stats = sync_entity(e, t, actor())
    db.session.commit()
    session.pop("wiz", None)
    flash(f"{e.name} onboarded: {stats['inserted']} obligations generated.", "success")
    return redirect(url_for("entities.show", entity_id=e.id))
