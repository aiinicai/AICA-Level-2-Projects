"""Client master data. Build Prompt v2 §5.1 and §5.2.

The SCD Type 2 rule lives here and nowhere else: **never UPDATE a current
profile's business fields.** A change closes the current row and inserts a
new one, so a finalised document keeps printing the master data it was
signed with.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import LOCAL_ACTOR
from app.core.validators import validate_frn, validate_membership_no
from app.models.engagement import Engagement
from app.models.enums import Designation, EngagementStatus, KmpRole
from app.models.issuance import AuditLog, UdinRegister
from app.models.masters import (
    Client,
    ClientProfile,
    Director,
    FieldDefault,
    Firm,
    Kmp,
    Partner,
    User,
)

# Fields that identify a version rather than describe the business. Changing
# one of these is bookkeeping; changing anything else opens a new version.
_VERSIONING_FIELDS = frozenset(
    {
        "profile_id",
        "client_id",
        "valid_from",
        "valid_to",
        "is_current",
        "changed_by",
        "change_reason",
        "changed_at",
    }
)


class ChangeScope(StrEnum):
    """How far a master-data change reaches (§8.3).

    A finalised engagement is never re-pointed under any of these — see
    `_repoint_engagements`.
    """

    MASTER_ONLY = "master_only"
    CURRENT_FY = "current_fy"
    CURRENT_AND_FUTURE = "current_and_future"


class ProfileError(ValueError):
    """Message is safe to show a user."""


@dataclass(frozen=True, slots=True)
class ProfileChange:
    field: str
    before: Any
    after: Any


def current_profile(session: Session, client_id: int) -> ClientProfile:
    profile = session.scalar(
        select(ClientProfile).where(
            ClientProfile.client_id == client_id,
            ClientProfile.is_current.is_(True),
        )
    )
    if profile is None:
        raise ProfileError(f"Client {client_id} has no current profile")
    return profile


def profile_as_on(session: Session, client_id: int, as_on: date) -> ClientProfile:
    """The version in force on a date. What a reprint must read (§18.6)."""
    profile = session.scalar(
        select(ClientProfile)
        .where(
            ClientProfile.client_id == client_id,
            ClientProfile.valid_from <= as_on,
        )
        .order_by(ClientProfile.valid_from.desc())
        .limit(1)
    )
    if profile is None:
        raise ProfileError(f"Client {client_id} has no profile in force on {as_on}")
    if profile.valid_to is not None and profile.valid_to < as_on:
        raise ProfileError(f"Client {client_id} has no profile in force on {as_on}")
    return profile


def _business_fields(profile: ClientProfile) -> dict[str, Any]:
    return {
        column.key: getattr(profile, column.key)
        for column in ClientProfile.__mapper__.column_attrs
        if column.key not in _VERSIONING_FIELDS
    }


def diff_profile(profile: ClientProfile, changes: dict[str, Any]) -> list[ProfileChange]:
    current = _business_fields(profile)
    out: list[ProfileChange] = []
    for field, after in changes.items():
        if field not in current:
            raise ProfileError(f"{field!r} is not a versioned profile field")
        before = current[field]
        if before != after:
            out.append(ProfileChange(field=field, before=before, after=after))
    return out


def _repoint_engagements(
    session: Session,
    client_id: int,
    profile: ClientProfile,
    scope: ChangeScope,
    change_date: date,
) -> list[Engagement]:
    """Point open engagements at the new profile version.

    §8.3 — "never silently alter a finalised engagement". Finalised and
    archived engagements keep the profile they were signed against, which is
    what makes a byte-identical reprint possible (§18.6). They are skipped
    here regardless of the scope chosen, and there is no option that
    overrides that.
    """
    if scope is ChangeScope.MASTER_ONLY:
        return []

    candidates = session.scalars(select(Engagement).where(Engagement.client_id == client_id)).all()

    touched: list[Engagement] = []
    for engagement in candidates:
        if engagement.is_locked:
            continue
        if scope is ChangeScope.CURRENT_FY and not (
            engagement.fy_start <= change_date <= engagement.fy_end
        ):
            continue
        if scope is ChangeScope.CURRENT_AND_FUTURE and engagement.fy_end < change_date:
            continue
        engagement.profile_id = profile.profile_id
        touched.append(engagement)

    return touched


def change_profile(
    session: Session,
    client_id: int,
    changes: dict[str, Any],
    *,
    change_date: date,
    changed_by: str,
    reason: str,
    scope: ChangeScope = ChangeScope.MASTER_ONLY,
) -> ClientProfile:
    """Close the current profile and open a new version.

    The only supported way to change client master data. Returns the new
    current profile; the prior row keeps its values and becomes historical.
    """
    if not reason.strip():
        raise ProfileError("A change reason is required")

    existing = current_profile(session, client_id)

    if change_date <= existing.valid_from:
        raise ProfileError(
            f"Change date {change_date} must fall after the current profile's "
            f"valid_from ({existing.valid_from})"
        )

    diffs = diff_profile(existing, changes)
    if not diffs:
        return existing

    carried = _business_fields(existing)
    carried.update(changes)

    # Close the old row. valid_to and is_current are versioning fields, not
    # business fields — this is the one permitted UPDATE.
    existing.valid_to = change_date - timedelta(days=1)
    existing.is_current = False
    session.flush()

    replacement = ClientProfile(
        client_id=client_id,
        valid_from=change_date,
        valid_to=None,
        is_current=True,
        changed_by=changed_by,
        change_reason=reason,
        **carried,
    )
    session.add(replacement)
    session.flush()

    repointed = _repoint_engagements(session, client_id, replacement, scope, change_date)

    session.add(
        AuditLog(
            entity="client_profile",
            entity_id=str(client_id),
            action="version",
            field=",".join(d.field for d in diffs),
            before_json=json.dumps({d.field: str(d.before) for d in diffs}),
            after_json=json.dumps(
                {
                    **{d.field: str(d.after) for d in diffs},
                    "_scope": scope.value,
                    "_engagements_repointed": [e.fy_code for e in repointed],
                }
            ),
            reason=reason,
            actor=changed_by,
        )
    )
    session.flush()
    return replacement


def change_history(session: Session, client_id: int) -> list[AuditLog]:
    """Audit-log feed for the Change History tab (§8.3)."""
    return list(
        session.scalars(
            select(AuditLog)
            .where(AuditLog.entity == "client_profile", AuditLog.entity_id == str(client_id))
            .order_by(AuditLog.log_id.desc())
        ).all()
    )


def profile_versions(session: Session, client_id: int) -> list[ClientProfile]:
    """The version timeline shown beside the Master Data editor (§8.3)."""
    return list(
        session.scalars(
            select(ClientProfile)
            .where(ClientProfile.client_id == client_id)
            .order_by(ClientProfile.valid_from.desc())
        ).all()
    )


def engagements_for(session: Session, client_id: int) -> list[Engagement]:
    return list(
        session.scalars(
            select(Engagement)
            .where(Engagement.client_id == client_id)
            .order_by(Engagement.fy_end.desc())
        ).all()
    )


OPEN_STATUSES: frozenset[EngagementStatus] = frozenset(
    s for s in EngagementStatus if s not in (EngagementStatus.FINALISED, EngagementStatus.ARCHIVED)
)


# --------------------------------------------------------------------------
# Directors and KMP — computed from effective dates, never typed (§18.8)
# --------------------------------------------------------------------------


def directors_in_office(session: Session, client_id: int, as_on: date) -> list[Director]:
    """Directors holding office on a date."""
    rows = session.scalars(
        select(Director)
        .where(
            Director.client_id == client_id,
            Director.appointment_date <= as_on,
        )
        .order_by(Director.appointment_date, Director.director_id)
    ).all()
    return [d for d in rows if d.cessation_date is None or d.cessation_date >= as_on]


def directors_during_fy(
    session: Session, client_id: int, fy_start: date, fy_end: date
) -> list[Director]:
    """Anyone who held office at any point during the year.

    Drives the Directors' Report changes disclosure, so someone who resigned
    in October must appear even though they are gone by the year end.
    """
    rows = session.scalars(
        select(Director)
        .where(
            Director.client_id == client_id,
            Director.appointment_date <= fy_end,
        )
        .order_by(Director.appointment_date, Director.director_id)
    ).all()
    return [d for d in rows if d.cessation_date is None or d.cessation_date >= fy_start]


def kmp_in_office(session: Session, client_id: int, as_on: date) -> list[Kmp]:
    rows = session.scalars(
        select(Kmp)
        .where(Kmp.client_id == client_id, Kmp.appointment_date <= as_on)
        .order_by(Kmp.appointment_date, Kmp.kmp_id)
    ).all()
    return [k for k in rows if k.cessation_date is None or k.cessation_date >= as_on]


def client_by_code(session: Session, client_code: str) -> Client | None:
    return session.scalar(select(Client).where(Client.client_code == client_code))


# --------------------------------------------------------------------------
# Creating records. Added 17 August 2026: none of this existed, so the
# application could only work with whatever `scripts/seed.py` had inserted —
# no way to onboard a client, and no way to open a financial year except by
# rolling an existing one forward.
# --------------------------------------------------------------------------

_DIRECTOR_REQUIRED = ("name", "din", "designation", "appointment_date")


def create_client(
    session: Session,
    *,
    firm_id: int,
    client_code: str,
    cin: str,
    profile: dict[str, Any],
    pan: str = "",
    date_of_incorp: date | None = None,
    directors: Sequence[dict[str, Any]] = (),
    kmps: Sequence[dict[str, Any]] = (),
    created_by: str = LOCAL_ACTOR,
) -> Client:
    """Create a client, its first profile version, and its officers.

    One transaction. A client with no profile is unusable — every document
    interpolates `company_name` from it — so the two are never created
    separately and a validation failure part-way through leaves nothing
    behind.

    `client_code` and `cin` are unique in the schema; both are checked here so
    the user gets a sentence rather than an IntegrityError.
    """
    code = client_code.strip()
    identifier = cin.strip().upper()
    if not code:
        raise ProfileError("A client code is required")
    if not identifier:
        raise ProfileError("A CIN is required")
    if not str(profile.get("company_name", "")).strip():
        raise ProfileError("A company name is required")

    if session.scalar(select(Client).where(Client.client_code == code)):
        raise ProfileError(f"Client code {code!r} is already in use")
    if session.scalar(select(Client).where(Client.cin == identifier)):
        raise ProfileError(f"CIN {identifier!r} already belongs to another client")

    client = Client(
        firm_id=firm_id,
        client_code=code,
        cin=identifier,
        pan=pan.strip().upper(),
        date_of_incorp=date_of_incorp,
        created_by=created_by,
    )
    session.add(client)
    session.flush()

    # The first profile version opens on the incorporation date where one is
    # known, so a rolled-forward engagement for an earlier year still finds a
    # profile covering it. Without that the SCD-2 lookup returns nothing and
    # the documents interpolate blanks.
    session.add(
        ClientProfile(
            client_id=client.client_id,
            valid_from=date_of_incorp or date.today(),
            valid_to=None,
            is_current=True,
            changed_by=created_by,
            change_reason="Client created",
            **profile,
        )
    )

    for row in directors:
        missing = [f for f in _DIRECTOR_REQUIRED if not row.get(f)]
        if missing:
            raise ProfileError(f"Director row is missing {', '.join(missing)}")
        session.add(Director(client_id=client.client_id, **row))

    for row in kmps:
        if not row.get("name") or not row.get("role"):
            raise ProfileError("Every KMP row needs a name and a role")
        session.add(Kmp(client_id=client.client_id, **row))

    session.add(
        AuditLog(
            entity="client",
            entity_id=str(client.client_id),
            action="insert",
            field="",
            before_json="",
            after_json=json.dumps({"client_code": code, "cin": identifier}),
            reason="Client created",
            actor=created_by,
        )
    )
    session.flush()
    return client


# --------------------------------------------------------------------------
# Partners. Added 17 August 2026: the firm screen listed them read-only, so a
# firm could not record its own partners even though the signing partner's
# name and membership number appear on every document it issues.
# --------------------------------------------------------------------------


def add_partner(
    session: Session,
    *,
    firm_id: int,
    partner_name: str,
    membership_no: str,
    is_signing: bool = False,
    actor: str = LOCAL_ACTOR,
) -> Partner:
    """Add a partner. Membership numbers are unique across the table."""
    name = partner_name.strip()
    if not name:
        raise ProfileError("A partner name is required")
    membership = validate_membership_no(membership_no)

    if session.scalar(select(Partner).where(Partner.membership_no == membership)):
        raise ProfileError(f"Membership number {membership} is already recorded")

    partner = Partner(
        firm_id=firm_id,
        partner_name=name,
        membership_no=membership,
        is_signing=is_signing,
        active=True,
    )
    session.add(partner)
    session.flush()
    session.add(
        AuditLog(
            entity="partner",
            entity_id=str(partner.partner_id),
            action="insert",
            field="",
            before_json="",
            after_json=json.dumps(
                {"partner_name": name, "membership_no": membership, "is_signing": is_signing}
            ),
            reason="Partner added",
            actor=actor,
        )
    )
    return partner


def update_partner(
    session: Session,
    partner_id: int,
    changes: dict[str, Any],
    *,
    actor: str = LOCAL_ACTOR,
) -> Partner:
    """Rename a partner, change the membership number, or set the flags.

    `active = False` is how someone leaves the firm, and it stays the right
    answer for anyone who has signed: documents already issued name them, and a
    row removed from under a signed report leaves the audit trail pointing at
    nothing.

    `delete_partner` exists as well, from 20 August 2026, for the case this
    docstring used to deny — a partner recorded by mistake, or one who left
    before signing anything. It refuses the moment anything points at them.
    """
    partner = session.get(Partner, partner_id)
    if partner is None:
        raise ProfileError(f"No partner with id {partner_id}")

    allowed = {"partner_name", "membership_no", "is_signing", "active"}
    unknown = set(changes) - allowed
    if unknown:
        raise ProfileError(f"Not editable: {', '.join(sorted(unknown))}")

    if "membership_no" in changes:
        changes["membership_no"] = validate_membership_no(str(changes["membership_no"]))
        clash = session.scalar(
            select(Partner).where(
                Partner.membership_no == changes["membership_no"],
                Partner.partner_id != partner_id,
            )
        )
        if clash:
            raise ProfileError(
                f"Membership number {changes['membership_no']} belongs to another partner"
            )

    if "partner_name" in changes:
        changes["partner_name"] = str(changes["partner_name"]).strip()
        if not changes["partner_name"]:
            raise ProfileError("A partner name is required")

    before = {name: getattr(partner, name) for name in changes}
    for name, value in changes.items():
        setattr(partner, name, value)
    session.flush()

    if before != changes:
        session.add(
            AuditLog(
                entity="partner",
                entity_id=str(partner_id),
                action="update",
                field=", ".join(sorted(changes)),
                before_json=json.dumps({k: str(v) for k, v in before.items()}),
                after_json=json.dumps({k: str(v) for k, v in changes.items()}),
                reason="Partner updated",
                actor=actor,
            )
        )
    return partner


def signing_partners(session: Session, firm_id: int) -> list[Partner]:
    """Active partners who may sign. The list a report's signature block draws
    from, so an inactive partner cannot be picked by accident."""
    return list(
        session.scalars(
            select(Partner)
            .where(Partner.firm_id == firm_id, Partner.active.is_(True))
            .order_by(Partner.partner_name)
        )
    )


# --------------------------------------------------------------------------
# Firms. Several may share one installation (Gate decision 20, 17 Aug 2026).
#
# THERE IS NO LOGIN, so the active firm is a working filter and not access
# control: anyone using the application can switch to any firm and see its
# clients. That was chosen deliberately and is recorded in
# docs/GATE_A_DECISIONS.md; nothing here should be read as protecting one
# firm's data from another.
# --------------------------------------------------------------------------

ACTIVE_FIRM_COOKIE = "auditcraft_firm"


def create_firm(
    session: Session,
    *,
    firm_name: str,
    frn: str,
    address: str = "",
    default_place: str = "",
    actor: str = LOCAL_ACTOR,
) -> Firm:
    """Add a firm. The FRN is unique and is validated, not merely stored."""
    name = firm_name.strip()
    if not name:
        raise ProfileError("A firm name is required")
    registration = validate_frn(frn)

    if session.scalar(select(Firm).where(Firm.frn == registration)):
        raise ProfileError(f"FRN {registration} is already recorded")

    firm = Firm(
        firm_name=name,
        frn=registration,
        address=address.strip(),
        default_place=default_place.strip(),
    )
    session.add(firm)
    session.flush()
    session.add(
        AuditLog(
            entity="firm",
            entity_id=str(firm.firm_id),
            action="insert",
            field="",
            before_json="",
            after_json=json.dumps({"firm_name": name, "frn": registration}),
            reason="Firm created",
            actor=actor,
        )
    )
    return firm


# --------------------------------------------------------------------------
# Removing a partner or a firm. Partner's request, 20 August 2026.
#
# The rule throughout: a record may be deleted only when nothing that has been
# ISSUED points at it. Everything that would break is counted first and named
# back to the user, because "cannot delete" without saying what is holding it
# is a dead end rather than an answer.
# --------------------------------------------------------------------------


def partner_blockers(session: Session, partner_id: int) -> dict[str, int]:
    """What stands in the way of removing this partner, counted by kind.

    An empty dict means the partner has signed nothing and been named on
    nothing, so removing the row destroys no record.
    """
    partner = session.get(Partner, partner_id)
    if partner is None:
        raise ProfileError(f"No partner with id {partner_id}")

    blockers: dict[str, int] = {}

    # A UDIN is generated against a member's own number and is a public
    # record. The row here is what lets the firm answer "which document was
    # this UDIN for?" years later.
    udins = session.scalar(
        select(func.count()).select_from(UdinRegister).where(UdinRegister.partner_id == partner_id)
    )
    if udins:
        blockers["UDINs generated in their name"] = int(udins)

    locked = session.scalar(
        select(func.count())
        .select_from(Engagement)
        .where(
            Engagement.partner_id == partner_id,
            Engagement.status.in_((EngagementStatus.FINALISED, EngagementStatus.ARCHIVED)),
        )
    )
    if locked:
        blockers["finalised financial years they signed"] = int(locked)

    # An open year is not history, but clearing the signing partner silently
    # would change who a report goes out under. Named so the user reassigns it
    # deliberately.
    open_years = session.scalar(
        select(func.count())
        .select_from(Engagement)
        .where(
            Engagement.partner_id == partner_id,
            Engagement.status.notin_((EngagementStatus.FINALISED, EngagementStatus.ARCHIVED)),
        )
    )
    if open_years:
        blockers["open financial years assigned to them"] = int(open_years)

    return blockers


def delete_partner(session: Session, partner_id: int, *, deleted_by: str = LOCAL_ACTOR) -> str:
    """Remove a partner who has signed nothing. Returns the name removed.

    Where anything points at them, this refuses and says what. Retiring them
    -- `active = False` -- is the answer in that case, and it is not a lesser
    one: a partner who has signed reports SHOULD stay in the register.
    """
    partner = session.get(Partner, partner_id)
    if partner is None:
        raise ProfileError(f"No partner with id {partner_id}")

    blockers = partner_blockers(session, partner_id)
    if blockers:
        detail = "; ".join(f"{count} {what}" for what, count in sorted(blockers.items()))
        raise ProfileError(
            f"{partner.partner_name} cannot be deleted — {detail}. "
            "Clear the flag on 'Still with the firm' to retire them instead, "
            "which keeps them findable on the documents they signed."
        )

    name = partner.partner_name
    session.add(
        AuditLog(
            entity="partner",
            entity_id=str(partner_id),
            action="delete",
            field="",
            before_json=json.dumps({"partner_name": name, "membership_no": partner.membership_no}),
            after_json="",
            reason="Partner deleted — nothing referenced them",
            actor=deleted_by,
        )
    )
    session.delete(partner)
    session.flush()
    return name


def firm_blockers(session: Session, firm_id: int) -> dict[str, int]:
    """What stands in the way of removing this firm."""
    firm = session.get(Firm, firm_id)
    if firm is None:
        raise ProfileError(f"No firm with id {firm_id}")

    blockers: dict[str, int] = {}

    clients = session.scalar(
        select(func.count()).select_from(Client).where(Client.firm_id == firm_id)
    )
    if clients:
        blockers["clients on its register"] = int(clients)

    users = session.scalar(select(func.count()).select_from(User).where(User.firm_id == firm_id))
    if users:
        blockers["user accounts"] = int(users)

    # A partner who cannot go on their own cannot go as part of the firm
    # either. Counted rather than listed, because the partner screen is where
    # the detail belongs.
    held = sum(
        1
        for partner in session.scalars(select(Partner).where(Partner.firm_id == firm_id))
        if partner_blockers(session, partner.partner_id)
    )
    if held:
        blockers["partners named on issued documents"] = held

    if session.scalar(select(func.count()).select_from(Firm)) == 1:
        blockers["— it is the only firm on this installation"] = 1

    return blockers


def delete_firm(session: Session, firm_id: int, *, deleted_by: str = LOCAL_ACTOR) -> str:
    """Remove a firm that holds no clients. Returns the name removed.

    Its partners and its standing default answers go with it: both are the
    firm's own configuration and mean nothing without it. Nothing else does —
    a firm with a single client keeps everything.
    """
    firm = session.get(Firm, firm_id)
    if firm is None:
        raise ProfileError(f"No firm with id {firm_id}")

    blockers = firm_blockers(session, firm_id)
    if blockers:
        detail = "; ".join(
            what if what.startswith("—") else f"{count} {what}"
            for what, count in sorted(blockers.items())
        )
        raise ProfileError(f"{firm.firm_name} cannot be deleted — {detail}.")

    name = firm.firm_name
    partners = list(session.scalars(select(Partner).where(Partner.firm_id == firm_id)))
    defaults = list(session.scalars(select(FieldDefault).where(FieldDefault.firm_id == firm_id)))

    session.add(
        AuditLog(
            entity="firm",
            entity_id=str(firm_id),
            action="delete",
            field="",
            before_json=json.dumps(
                {
                    "firm_name": name,
                    "frn": firm.frn,
                    "partners_removed": len(partners),
                    "default_answers_removed": len(defaults),
                }
            ),
            after_json="",
            reason="Firm deleted — no clients, no users, no issued documents",
            actor=deleted_by,
        )
    )
    for partner in partners:
        session.delete(partner)
    for default in defaults:
        session.delete(default)
    session.delete(firm)
    session.flush()
    return name


def all_firms(session: Session) -> list[Firm]:
    return list(session.scalars(select(Firm).order_by(Firm.firm_name)))


def active_firm(session: Session, requested_id: str | int | None = None) -> Firm | None:
    """The firm being worked as.

    Falls back to the first firm when nothing valid is requested, so an
    installation with one firm never has to choose and a stale cookie pointing
    at a deleted firm does not leave every screen empty.
    """
    if requested_id not in (None, ""):
        try:
            firm = session.get(Firm, int(requested_id))
        except (TypeError, ValueError):
            firm = None
        if firm is not None:
            return firm
    return session.scalar(select(Firm).order_by(Firm.firm_id))


# --------------------------------------------------------------------------
# Maintaining the registers. Decision 74.
#
# The firm's team reported that a resignation or an appointment during the year
# could not be entered anywhere. It could not: directors and KMP were written
# once, on the new-client form, and no route touched them again.
#
# That is worse than a missing screen. `bdr.directors.kmp` derives the Board's
# Report disclosure from this register precisely so the report cannot disagree
# with it (§18.8) -- so with the register frozen, the disclosure could only ever
# say "no change", however many changes there had been, and it said so in a
# paragraph the directors sign.
#
# Rows are never deleted. A director who leaves is given a cessation date, which
# is what the Act's own register does and what the disclosure reads: deleting
# the row would take the person out of last year's signed report as well.
# --------------------------------------------------------------------------


def add_director(
    session: Session,
    client_id: int,
    *,
    name: str,
    din: str,
    designation: Designation,
    appointment_date: date,
    added_by: str = LOCAL_ACTOR,
) -> Director:
    """Record an appointment."""
    name, din = name.strip(), din.strip()
    if not name:
        raise ProfileError("A director needs a name")
    if not din.isdigit() or len(din) != 8:
        raise ProfileError("A DIN is eight digits")

    clash = session.scalar(
        select(Director).where(
            Director.client_id == client_id,
            Director.din == din,
            Director.is_active.is_(True),
        )
    )
    if clash is not None:
        raise ProfileError(f"DIN {din} is already on the register, as {clash.name}")

    director = Director(
        client_id=client_id,
        name=name,
        din=din,
        designation=designation,
        appointment_date=appointment_date,
        is_active=True,
    )
    session.add(director)
    session.add(
        AuditLog(
            entity="director",
            entity_id=str(client_id),
            action="insert",
            after_json=json.dumps(
                {"name": name, "din": din, "appointment_date": appointment_date.isoformat()}
            ),
            reason="Appointment",
            actor=added_by,
        )
    )
    session.flush()
    return director


def end_director(
    session: Session,
    client_id: int,
    director_id: int,
    *,
    cessation_date: date,
    ended_by: str = LOCAL_ACTOR,
) -> Director:
    """Record a resignation or other cessation."""
    director = session.get(Director, director_id)
    if director is None or director.client_id != client_id:
        raise ProfileError("That director is not on this client's register")
    if director.cessation_date is not None:
        raise ProfileError(f"{director.name} already left on {director.cessation_date}")
    if cessation_date < director.appointment_date:
        raise ProfileError(
            f"{director.name} cannot leave on {cessation_date}, before being appointed "
            f"on {director.appointment_date}"
        )

    director.cessation_date = cessation_date
    director.is_active = False
    session.add(
        AuditLog(
            entity="director",
            entity_id=str(client_id),
            action="update",
            field="cessation_date",
            after_json=json.dumps({"din": director.din, "cessation": cessation_date.isoformat()}),
            reason="Cessation",
            actor=ended_by,
        )
    )
    session.flush()
    return director


def add_kmp(
    session: Session,
    client_id: int,
    *,
    name: str,
    role: KmpRole,
    appointment_date: date,
    pan: str = "",
    added_by: str = LOCAL_ACTOR,
) -> Kmp:
    name = name.strip()
    if not name:
        raise ProfileError("A KMP needs a name")

    kmp = Kmp(
        client_id=client_id,
        name=name,
        role=role,
        pan=pan.strip().upper(),
        appointment_date=appointment_date,
        is_active=True,
    )
    session.add(kmp)
    session.add(
        AuditLog(
            entity="kmp",
            entity_id=str(client_id),
            action="insert",
            after_json=json.dumps(
                {"name": name, "role": role.value, "appointment_date": appointment_date.isoformat()}
            ),
            reason="Appointment",
            actor=added_by,
        )
    )
    session.flush()
    return kmp


def end_kmp(
    session: Session,
    client_id: int,
    kmp_id: int,
    *,
    cessation_date: date,
    ended_by: str = LOCAL_ACTOR,
) -> Kmp:
    kmp = session.get(Kmp, kmp_id)
    if kmp is None or kmp.client_id != client_id:
        raise ProfileError("That person is not on this client's register")
    if kmp.cessation_date is not None:
        raise ProfileError(f"{kmp.name} already left on {kmp.cessation_date}")
    if cessation_date < kmp.appointment_date:
        raise ProfileError(
            f"{kmp.name} cannot leave on {cessation_date}, before being appointed "
            f"on {kmp.appointment_date}"
        )

    kmp.cessation_date = cessation_date
    kmp.is_active = False
    session.add(
        AuditLog(
            entity="kmp",
            entity_id=str(client_id),
            action="update",
            field="cessation_date",
            after_json=json.dumps({"name": kmp.name, "cessation": cessation_date.isoformat()}),
            reason="Cessation",
            actor=ended_by,
        )
    )
    session.flush()
    return kmp


def register(session: Session, client_id: int) -> tuple[list[Director], list[Kmp]]:
    """The whole register, past and present, in the order it happened."""
    directors = list(
        session.scalars(
            select(Director)
            .where(Director.client_id == client_id)
            .order_by(Director.appointment_date, Director.director_id)
        )
    )
    kmps = list(
        session.scalars(
            select(Kmp).where(Kmp.client_id == client_id).order_by(Kmp.appointment_date, Kmp.kmp_id)
        )
    )
    return directors, kmps
