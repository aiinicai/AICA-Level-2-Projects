"""Client register listing and dashboard tiles. Build Prompt v2 §8.2, §8.3.

Pagination is server-side (§8.9): the full dataset is never loaded into the
page, so the register stays responsive at a thousand clients.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement
from app.models.enums import CompanyType, EngagementStatus
from app.models.issuance import AuditLog, DocumentInstance
from app.models.masters import Client, ClientProfile

PAGE_SIZE = 25


@dataclass(frozen=True, slots=True)
class RegisterRow:
    client_id: int
    client_code: str
    company_name: str
    cin: str
    company_type: CompanyType
    current_fy: str
    status: EngagementStatus | None
    partner_name: str
    last_activity: date | None


@dataclass(frozen=True, slots=True)
class Page:
    rows: tuple[RegisterRow, ...]
    total: int
    page: int
    page_size: int = PAGE_SIZE

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def first_index(self) -> int:
        return 0 if not self.total else (self.page - 1) * self.page_size + 1

    @property
    def last_index(self) -> int:
        return min(self.page * self.page_size, self.total)


def _base_query() -> Select[tuple[Client, ClientProfile]]:
    return (
        select(Client, ClientProfile)
        .join(ClientProfile, ClientProfile.client_id == Client.client_id)
        .where(ClientProfile.is_current.is_(True))
    )


def search_clients(
    session: Session,
    *,
    query: str = "",
    company_type: CompanyType | None = None,
    page: int = 1,
    firm_id: int | None = None,
) -> Page:
    """Search by code, name, CIN or PAN, filtered and paginated (§8.9).

    `firm_id` restricts the result to one firm's clients. Several firms may
    share an installation (decision 20, 17 Aug 2026) and there is no login, so
    this is a working filter and NOT access control — anyone can change the
    active firm. Passing None deliberately lists everything.
    """
    stmt = _base_query()
    if firm_id is not None:
        stmt = stmt.where(Client.firm_id == firm_id)

    term = query.strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(
            or_(
                Client.client_code.ilike(like),
                Client.cin.ilike(like),
                Client.pan.ilike(like),
                ClientProfile.company_name.ilike(like),
            )
        )
    if company_type is not None:
        stmt = stmt.where(ClientProfile.company_type == company_type)

    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0

    page = max(1, page)
    results = session.execute(
        stmt.order_by(ClientProfile.company_name).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    ).all()

    rows: list[RegisterRow] = []
    for client, profile in results:
        latest = session.scalar(
            select(Engagement)
            .where(Engagement.client_id == client.client_id)
            .order_by(Engagement.fy_end.desc())
            .limit(1)
        )
        rows.append(
            RegisterRow(
                client_id=client.client_id,
                client_code=client.client_code,
                company_name=profile.company_name,
                cin=client.cin,
                company_type=profile.company_type,
                current_fy=latest.fy_code if latest else "",
                status=latest.status if latest else None,
                partner_name="",
                last_activity=profile.changed_at.date() if profile.changed_at else None,
            )
        )

    return Page(rows=tuple(rows), total=total, page=page)


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DashboardTiles:
    total_clients: int
    active_engagements: int
    # One tile, not two. The manager- and partner-review states were removed
    # on 17 August 2026 (decision 29): the preparer finalises, so there was no
    # handover for either tile to count.
    awaiting_approval: int
    incomplete: int
    documents_this_fy: int


def _count(session: Session, stmt: Select[tuple[int]]) -> int:
    return session.scalar(stmt) or 0


def _for_firm(stmt: Any, firm_id: int | None) -> Any:
    """Restrict a Client-based count to one firm."""
    return stmt if firm_id is None else stmt.where(Client.firm_id == firm_id)


def _engagements_for_firm(firm_id: int | None) -> Any:
    """A count over engagements, restricted to one firm's clients."""
    stmt = select(func.count()).select_from(Engagement)
    if firm_id is None:
        return stmt
    return stmt.join(Client, Client.client_id == Engagement.client_id).where(
        Client.firm_id == firm_id
    )


def dashboard_tiles(
    session: Session, fy_end: date | None = None, firm_id: int | None = None
) -> DashboardTiles:
    closed = (EngagementStatus.FINALISED, EngagementStatus.ARCHIVED)
    incomplete_statuses = (
        EngagementStatus.NOT_STARTED,
        EngagementStatus.DATA_COLLECTION,
        EngagementStatus.PREPARED,
    )

    documents = select(func.count()).select_from(DocumentInstance)
    if fy_end is not None:
        documents = documents.join(
            Engagement, Engagement.engagement_id == DocumentInstance.engagement_id
        ).where(Engagement.fy_end == fy_end)

    return DashboardTiles(
        total_clients=_count(session, _for_firm(select(func.count()).select_from(Client), firm_id)),
        active_engagements=_count(
            session,
            _engagements_for_firm(firm_id).where(Engagement.status.not_in(closed)),
        ),
        awaiting_approval=_count(
            session,
            select(func.count())
            .select_from(Engagement)
            .where(Engagement.status == EngagementStatus.PREPARED),
        ),
        incomplete=_count(
            session,
            select(func.count())
            .select_from(Engagement)
            .where(Engagement.status.in_(incomplete_statuses)),
        ),
        documents_this_fy=_count(session, documents),
    )


def recent_engagements(
    session: Session, limit: int = 10, firm_id: int | None = None
) -> list[tuple[Engagement, str]]:
    rows = session.execute(
        select(Engagement, ClientProfile.company_name)
        .join(Client, Client.client_id == Engagement.client_id)
        .join(
            ClientProfile,
            (ClientProfile.client_id == Client.client_id) & ClientProfile.is_current.is_(True),
        )
        .order_by(Engagement.created_at.desc())
        .limit(limit)
    ).all()
    return [(engagement, name) for engagement, name in rows]


def recent_changes(session: Session, limit: int = 15) -> list[AuditLog]:
    """The audit-log feed shown on the dashboard (§8.2)."""
    return list(
        session.scalars(select(AuditLog).order_by(AuditLog.log_id.desc()).limit(limit)).all()
    )
