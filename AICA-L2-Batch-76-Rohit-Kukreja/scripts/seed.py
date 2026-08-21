"""Seed data and first run. Build Prompt v2 §15.

    python scripts/seed.py

Idempotent: safe to re-run. Creates a placeholder firm, one client with a
director register, and the field catalogue built from the clause repository.

**Single-user build: no user accounts are created.** There is no login. The
firm record is a placeholder — set the real name, FRN, address and signing
partner on the Admin -> Firm & Partners screen before issuing anything.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.loader import load_clause_set
from app.config import get_settings
from app.db import SessionLocal
from app.models.engagement import Engagement, FieldCatalog
from app.models.enums import (
    CompanyType,
    Designation,
    EngagementStatus,
    Framework,
    KmpRole,
    OpinionType,
)
from app.models.masters import (
    Client,
    ClientProfile,
    Director,
    Firm,
    Kmp,
    Partner,
)
from app.services.catalog import sync_field_catalog


def seed_firm(session: Session) -> Firm:
    firm = session.scalar(select(Firm).where(Firm.frn == "000000W"))
    if firm is not None:
        return firm
    # A placeholder, not a real firm. Any CA firm using this tool sets its
    # own details on the Admin screen; nothing here is baked into the code.
    firm = Firm(
        # The name only. Every signature block renders "For {{ firm_name }}"
        # and then "Chartered Accountants" on its own line, so a firm name
        # carrying the suffix prints it twice.
        firm_name="Your Firm Name",
        frn="000000W",
        address="",
        default_place="",
        logo_path="/static/Firm_logo.png",
    )
    session.add(firm)
    session.flush()
    session.add(
        Partner(
            firm_id=firm.firm_id,
            partner_name="Signing Partner",
            membership_no="000000",
            is_signing=True,
        )
    )
    return firm


def seed_client(session: Session, firm: Firm) -> Client:
    client = session.scalar(select(Client).where(Client.client_code == "ABC001"))
    if client is not None:
        return client

    client = Client(
        firm_id=firm.firm_id,
        client_code="ABC001",
        cin="U72200MH2010PTC054288",
        pan="AABCA1234C",
        date_of_incorp=date(2010, 6, 14),
        created_by="seed",
    )
    session.add(client)
    session.flush()

    session.add(
        ClientProfile(
            client_id=client.client_id,
            valid_from=date(2010, 6, 14),
            is_current=True,
            company_name="ABC Private Limited",
            registered_addr="401, Nariman Point, Mumbai 400021",
            company_type=CompanyType.PVT,
            framework=Framework.IGAAP,
            # CARO and IFC are stated, not inferred (decision 59): the engine
            # reads no thresholds for either, so the sample engagement has to
            # say where it stands or both annexures are filtered out as
            # undecided. `_override` is how a declared answer is stored.
            caro=True,
            caro_override=True,
            ifc=True,
            ifc_override=True,
            # Stated as not applicable, which for a company this size is the
            # answer an auditor would give. "Not stated" would leave the sample
            # engagement blocked at export, which is not a useful sample.
            csr=False,
            csr_override=True,
            internal_audit=False,
            internal_audit_override=True,
            secretarial_audit=False,
            secretarial_audit_override=True,
            # The group-structure and cost-records facts, which decision 62
            # made capturable for the first time. Seeded as recorded rather
            # than left null so the sample client demonstrates the answered
            # state rather than the "not recorded" one.
            has_subsidiary=False,
            has_associate=False,
            has_joint_venture=False,
            cost_records_industry=False,
            website="",
            changed_by="seed",
            change_reason="Initial record",
        )
    )

    # Directors carry effective dates so the Directors' Report can be
    # computed rather than typed (§18.8). One resignation and one
    # appointment mid-year, which is the Gate C rollover scenario.
    session.add_all(
        [
            Director(
                client_id=client.client_id,
                name="R. Mehta",
                din="00123456",
                designation=Designation.MANAGING,
                appointment_date=date(2010, 6, 14),
            ),
            Director(
                client_id=client.client_id,
                name="K. Iyer",
                din="00234567",
                designation=Designation.NON_EXECUTIVE,
                appointment_date=date(2015, 4, 1),
                cessation_date=date(2025, 10, 17),
                is_active=False,
            ),
            Director(
                client_id=client.client_id,
                name="N. Bose",
                din="00345678",
                designation=Designation.INDEPENDENT,
                appointment_date=date(2026, 1, 12),
            ),
        ]
    )
    session.add(
        Kmp(
            client_id=client.client_id,
            name="D. Shah",
            role=KmpRole.CFO,
            appointment_date=date(2024, 7, 1),
        )
    )
    return client


def seed_engagements(session: Session, client: Client) -> None:
    """One finalised year and one open year.

    The finalised FY 2024-25 engagement is what makes "never silently alter a
    finalised engagement" (§8.3) testable rather than aspirational.
    """
    if session.scalar(select(Engagement).where(Engagement.client_id == client.client_id)):
        return

    profile = session.scalar(
        select(ClientProfile).where(
            ClientProfile.client_id == client.client_id,
            ClientProfile.is_current.is_(True),
        )
    )
    profile_id = profile.profile_id if profile else None

    session.add_all(
        [
            Engagement(
                client_id=client.client_id,
                fy_code="2024-25",
                fy_start=date(2024, 4, 1),
                fy_end=date(2025, 3, 31),
                profile_id=profile_id,
                opinion_type=OpinionType.CLEAN,
                report_date=date(2025, 8, 12),
                place="Mumbai",
                status=EngagementStatus.FINALISED,
                locked_at=datetime(2025, 8, 12, 17, 30),
                locked_by="local user",
            ),
            Engagement(
                client_id=client.client_id,
                fy_code="2025-26",
                fy_start=date(2025, 4, 1),
                fy_end=date(2026, 3, 31),
                profile_id=profile_id,
                status=EngagementStatus.DATA_COLLECTION,
            ),
        ]
    )


# A worked set of answers for the open year, chosen to exercise every
# rendering path: a nil answer, a clean answer, an exception that forces a
# narrative, and both repeating blocks.
_DEMO_ANSWERS: dict[str, str] = {
    # The year the auditors' term ends. Seeded because the clause prints
    # "[year the term ends]" until it is answered, and that bracket is caught
    # by the pre-export placeholder scan -- which is the point of it, but it
    # leaves the sample engagement permanently unapprovable.
    "bdr.statutory.auditors": "2027",
    "rule11.a.status": "disclosed",
    "rule11.e.status": "nil_both",
    "rule11.f.status": "none",
    "rule11.g.status": "throughout",
    "caro.vii.b.status": "disputed",
    "caro.viii": "none",
}

_DEMO_LITIGATION: tuple[dict[str, str], ...] = (
    {
        "forum": "Commissioner of Income Tax (Appeals), Mumbai",
        "case_number": "CIT(A)/2024-25/1187",
        "nature": "Disallowance under section 14A",
        "amount": "4260000",
        "period": "AY 2022-23",
        "status": "pending",
        "mgmt_assessment": "Favourable outcome expected; no provision considered necessary.",
    },
    {
        "forum": "CESTAT, Mumbai",
        "case_number": "ST/86412/2023",
        "nature": "Service tax on reverse charge",
        "amount": "815000",
        "period": "FY 2016-17",
        "status": "appealed",
        "mgmt_assessment": "Appeal filed; covered by a favourable precedent.",
    },
)

_DEMO_DUES: tuple[dict[str, str], ...] = (
    {
        "statute": "Income Tax Act, 1961",
        "nature": "Income tax demand",
        "amount": "4260000",
        "period": "AY 2022-23",
        "forum": "Commissioner of Income Tax (Appeals), Mumbai",
        "amount_paid": "852000",
    },
    {
        "statute": "Finance Act, 1994",
        "nature": "Service tax",
        "amount": "815000",
        "period": "FY 2016-17",
        "forum": "CESTAT, Mumbai",
    },
)


def seed_responses(session: Session, client: Client) -> int:
    """Answers for the open FY 2025-26 engagement.

    Replaces the Phase 3 `app/services/fixture.py` stand-in — the workspace
    and the preview now read the same rows a real user would write.
    """
    from app.services.engagement import add_child_row, set_response

    engagement = session.scalar(
        select(Engagement).where(
            Engagement.client_id == client.client_id, Engagement.fy_code == "2025-26"
        )
    )
    if engagement is None or engagement.responses:
        return 0

    # Skipped rather than raised when the catalogue does not carry the field.
    # The test suite seeds against a six-clause fixture repository, so an
    # answer written for a production clause has nowhere to go there — and a
    # sample answer is not worth failing a test run over.
    catalogued = set(session.scalars(select(FieldCatalog.field_key)))
    for field_key, value in _DEMO_ANSWERS.items():
        if field_key not in catalogued:
            continue
        set_response(session, engagement.engagement_id, field_key, value, updated_by="seed")

    for row in _DEMO_LITIGATION:
        add_child_row(session, engagement.engagement_id, "litigation", dict(row), added_by="seed")
    for row in _DEMO_DUES:
        add_child_row(
            session, engagement.engagement_id, "statutory_due", dict(row), added_by="seed"
        )

    return len(_DEMO_ANSWERS)


# `sync_field_catalog` moved to `app.services.catalog` so the packaged build
# can run it at startup -- a colleague opening the .exe never runs this script,
# and without the catalogue the workspace shows no questions at all. Imported
# rather than duplicated: two copies would drift, and the one that drifts is
# the one nobody runs.


def main() -> int:
    settings = get_settings()
    settings.ensure_directories()
    clause_set = load_clause_set(settings.content_path)

    with SessionLocal() as session:
        firm = seed_firm(session)
        session.flush()
        client = seed_client(session, firm)
        session.flush()
        seed_engagements(session, client)
        session.flush()
        # The catalogue must exist before responses can reference it.
        fields = sync_field_catalog(session, clause_set)
        session.flush()
        answers = seed_responses(session, client)
        session.commit()

        print(f"firm:            {firm.firm_name} (FRN {firm.frn})")
        print(f"client:          {client.client_code} / {client.cin}")
        print(
            f"field_catalog:   {fields} field(s) from template "
            f"{clause_set.manifest.template_version}"
        )
        print(f"responses:       {answers} answer(s) on FY 2025-26")
        if clause_set.needs_review:
            print(f"needs_review:    {', '.join(c.id for c in clause_set.needs_review)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
