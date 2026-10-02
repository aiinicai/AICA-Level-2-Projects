from __future__ import annotations

from collections import Counter
from datetime import timedelta

from flask import Blueprint, render_template
from flask_login import current_user
from sqlalchemy import select

from ..auth import today
from ..models import Entity, EntityPerson, Obligation, Person, db
from ..permissions import require
from ..services import fee_for, health, rulepack, visible_entities_query, visible_obligations_query

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@require("view")
def index():
    t = today()
    obls = db.session.execute(visible_obligations_query(current_user).order_by(Obligation.due_date)).scalars().all()
    open_ = [o for o in obls if health(o, t) != "closed"]
    bands = Counter(health(o, t) for o in obls)
    overdue = [o for o in open_ if health(o, t) == "overdue"]
    exposure = [(o, fee_for(o, t) if o.fee_regime != "NONE" else None) for o in overdue[:40]]
    upcoming = [o for o in open_ if 0 <= (o.due_date - t).days <= 30]
    review = [o for o in open_ if o.status == "READY_FOR_REVIEW" and o.ready_by_id != current_user.id]
    mine = [o for o in open_ if o.assignee_id == current_user.id][:15]
    entity_ids = visible_entities_query(current_user).with_only_columns(Entity.id)
    dsc = db.session.execute(
        select(Person).join(EntityPerson, EntityPerson.person_id == Person.id).where(
            EntityPerson.entity_id.in_(entity_ids), EntityPerson.ceased_on.is_(None),
            Person.dsc_expiry.is_not(None), Person.dsc_expiry <= t + timedelta(days=30)).distinct()
    ).scalars().all()
    rp = rulepack()
    return render_template(
        "dashboard.html", bands=bands, exposure=exposure, n_overdue=len(overdue), upcoming=upcoming[:25],
        review=review, mine=mine, dsc=dsc, unverified=sum(1 for r in rp.rules if not r.verified),
        stale=sum(1 for o in open_ if o.facts_stale), decisions=[o for o in open_ if o.needs_decision])
