"""The render context, built once per render. Build Prompt v2 §3.3 and §12.

Every value here is derived from typed columns at render time. Nothing is
read back from a stored formatted string — that is what left the prototype
with the same wrong date interpolated into 34 sentences.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.formatting import DateStyle, financial_year, format_date
from app.models.engagement import Engagement
from app.models.enums import CompanyType
from app.models.masters import Client, ClientProfile, Firm, Partner

# Classes whose financial statements need not include a cash flow statement.
# Section 2(40) of the Companies Act, 2013, first proviso. The proviso also
# covers dormant companies and start-up private companies; neither is a company
# type this tool models, and the partner confirmed on 20 August 2026 that the
# tool is used for small companies and OPCs. Add a type here rather than
# widening the test to `pvt`, which would drop the statement for every private
# company and is the mistake the request arrived with.
CASH_FLOW_EXEMPT: frozenset[CompanyType] = frozenset({CompanyType.SMALL, CompanyType.OPC})

_FRAMEWORK_REF: dict[str, str] = {
    "indas": "Companies (Indian Accounting Standards) Rules, 2015",
    "igaap": "Companies (Accounting Standards) Rules, 2021",
}


def render_context_for(
    engagement: Engagement,
    client: Client | None,
    profile: ClientProfile | None,
    firm: Firm | None = None,
    partner: Partner | None = None,
    udin: str = "",
    directors_changed: bool = False,
) -> dict[str, Any]:
    """Interpolation variables for one engagement's documents.

    The profile passed in should be the one *pinned to the engagement*, not
    the client's current profile — that is what keeps a finalised document
    reproducible after the company moves (§18.6).
    """
    context: dict[str, Any] = {
        "company_name": profile.company_name if profile else "",
        "cin": client.cin if client else "",
        "registered_addr": profile.registered_addr if profile else "",
        "fy_code": engagement.fy_code,
        "financial_year": financial_year(engagement.fy_end),
        "fy_start_long": format_date(engagement.fy_start, DateStyle.LONG),
        "fy_end_long": format_date(engagement.fy_end, DateStyle.LONG),
        "fy_end_numeric": format_date(engagement.fy_end, DateStyle.NUMERIC),
        "place": engagement.place,
        "framework_ref": _FRAMEWORK_REF.get(profile.framework.value if profile else "", ""),
        # The opinion is answered once, on the engagement, and read from
        # there by the consistency engine, the comparison report and the
        # Excel export. Clauses branch on it through this variable rather
        # than asking again — two places to set the opinion is two places
        # for them to disagree.
        # Rule 8(5)(iv). None of the three set means the nil paragraph, and the
        # Board's Report asks nobody: the profile already records them. `None`
        # means "not recorded", which is treated as no group company -- the
        # same reading the CFS applicability flags take.
        "has_group_companies": bool(
            profile
            and (profile.has_subsidiary or profile.has_associate or profile.has_joint_venture)
        ),
        "is_listed_company": bool(profile and profile.company_type is CompanyType.PUB_LISTED),
        "has_website": bool(profile and profile.website.strip()),
        "cost_records_required": bool(profile and profile.cost_records_industry),
        "directors_changed_in_year": directors_changed,
        "date_of_incorp_long": (
            format_date(client.date_of_incorp, DateStyle.LONG)
            if client and client.date_of_incorp
            else ""
        ),
        "opinion_type": engagement.opinion_type.value if engagement.opinion_type else "",
        "going_concern": engagement.going_concern.value,
        "framework": profile.framework.value if profile else "",
        # Section 2(40) proviso. Confirmed by the partner on 20 August 2026:
        # this tool is used for small companies including OPCs, and the cash
        # flow statement is dropped for those classes only.
        #
        # `True` when there is no profile: a document must not quietly lose a
        # statement because the company type is unknown. An unknown company is
        # a full-scope company until someone says otherwise.
        "cash_flow_required": (profile.company_type not in CASH_FLOW_EXEMPT if profile else True),
    }
    context["report_date_long"] = (
        format_date(engagement.report_date, DateStyle.LONG) if engagement.report_date else ""
    )
    # Nothing about the firm is hard-coded anywhere in the tool — every one
    # of these comes from Admin → Firm & Partners, so any CA firm can use it
    # without a code change.
    context.update(
        {
            "firm_name": firm.firm_name if firm else "",
            "firm_frn": firm.frn if firm else "",
            "firm_address": firm.address if firm else "",
            "partner_name": partner.partner_name if partner else "",
            "partner_mno": partner.membership_no if partner else "",
            # Per document, not per engagement: each signed document carries
            # its own UDIN, so it arrives from the DocumentInstance.
            "udin": udin,
        }
    )
    return context


def firm_for_client(session: Session, client: Client | None) -> Firm | None:
    """The practice that holds this client's engagement.

    **Not the active-firm cookie.** That chooses what the person at the screen
    is looking at; it does not decide whose name goes on a report. The two
    disagreed for one turn — the auditor's report carried one firm's letterhead
    and the other firm's signature block — which is precisely the class of
    contradiction a single source of truth exists to stop.
    """
    return session.get(Firm, client.firm_id) if client and client.firm_id else None


def signing_partner(session: Session, engagement: Engagement, firm: Firm | None) -> Partner | None:
    """Who signs THIS engagement.

    `engagement.partner_id` when it is set. The column existed from the start
    and nothing read it, so every report in a firm with more than one signatory
    was signed by whichever partner happened to sort first -- the firm's team
    reported it: partner A signs client Y and partner B signs client Z, both for
    the same firm, and the tool named the same person on both.

    Falls back to the firm's first active signatory, so a report is never signed
    by nobody. **The partner must still belong to this client's firm**: an
    engagement pointing at a partner of another practice would put one firm's
    name over another firm's member, so that is checked rather than assumed.
    """
    if firm is None:
        return None
    if engagement.partner_id is not None:
        chosen = session.get(Partner, engagement.partner_id)
        if chosen is not None and chosen.firm_id == firm.firm_id:
            return chosen
    return session.scalar(
        select(Partner)
        .where(
            Partner.firm_id == firm.firm_id,
            Partner.active.is_(True),
            Partner.is_signing.is_(True),
        )
        .order_by(Partner.partner_id)
    )


def signing_context(
    session: Session,
    engagement: Engagement,
    client: Client | None,
    profile: ClientProfile | None,
    udin: str = "",
) -> dict[str, Any]:
    """`render_context_for`, with the firm and signing partner filled in.

    **Every caller used to omit them.** `render_context_for` took `firm` and
    `partner` as optional arguments and not one of the four call sites passed
    either, so `firm_name`, `firm_frn`, `firm_address`, `partner_name` and
    `partner_mno` were empty strings in every document the tool has ever
    produced -- the auditor's report signed by nobody, and the representation
    letter addressed to a blank line above "Chartered Accountants". Found when
    the firm's letterhead came off the MRL and there was nothing underneath.

    The firm is resolved from the **client**, not from the active-firm cookie: a
    document belongs to the practice that holds the engagement, not to whichever
    firm the person at the screen happens to be looking at.

    The signing partner is the firm's first active signatory. Where a firm has
    several, choosing between them is a decision for the engagement and is not
    modelled yet -- this fills the block rather than leaving it blank, and the
    partner is named on screen before anything is signed.
    """
    firm = firm_for_client(session, client)
    partner = signing_partner(session, engagement, firm)

    # Read from the register rather than asked, so the answer and the table it
    # prints above cannot disagree. Imported here rather than at module level:
    # the engagement service reaches back into this one.
    from app.services.engagement import _director_changes_in_year

    return render_context_for(
        engagement,
        client,
        profile,
        firm=firm,
        partner=partner,
        udin=udin,
        directors_changed=bool(_director_changes_in_year(session, engagement)),
    )
