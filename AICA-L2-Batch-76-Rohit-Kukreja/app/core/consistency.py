"""Consistency and completeness gate. Build Prompt v2 §9.

Runs before every export. A `block` finding stops export and status
advancement; a `warn` is advisory.

The rules here are cross-document checks — the class of error where each
document is individually plausible and the set contradicts itself. That is
precisely what a reviewer reading one document at a time cannot catch.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.core.applicability import DECLARED_FLAGS, Applicability
from app.models.engagement import Engagement, EngagementResponse, FieldCatalog
from app.models.enums import CompanyType, GoingConcern, OpinionType, ResponseSource
from app.models.masters import Client, ClientProfile
from app.services.client import directors_during_fy

MAX_REPORT_LAG_DAYS = 180


class Severity(StrEnum):
    BLOCK = "block"
    WARN = "warn"


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    severity: Severity
    message: str
    field_key: str = ""
    document: str = ""

    @property
    def blocks(self) -> bool:
        return self.severity is Severity.BLOCK


def _answers(session: Session, engagement_id: int) -> dict[str, str]:
    return {
        row.field_key: (row.value_text or "")
        for row in session.scalars(
            select(EngagementResponse).where(EngagementResponse.engagement_id == engagement_id)
        )
    }


@dataclass(frozen=True, slots=True)
class DocumentBlocks:
    """Everything `build_document` could not resolve, by kind. Decision 76.

    All three hold CLAUSE ids. They are carried separately rather than merged
    so each can be reported in the words that describe it: a table with no rows
    and a modified opinion with no explanation are not the same problem, and
    "something is unanswered" helps nobody find either.
    """

    unanswered: frozenset[str] = frozenset()
    missing_narratives: frozenset[str] = frozenset()
    missing_rows: frozenset[str] = frozenset()

    @property
    def every_clause(self) -> frozenset[str]:
        return self.unanswered | self.missing_narratives | self.missing_rows

    def __bool__(self) -> bool:
        return bool(self.every_clause)


def check(
    session: Session,
    engagement: Engagement,
    clause_set: ClauseSet,
    *,
    applicability: Applicability | None = None,
    rendered_placeholders: dict[str, tuple[str, ...]] | None = None,
    blocks: DocumentBlocks | None = None,
) -> list[Finding]:
    """Every §9 rule. Order: blocks first, then warnings."""
    findings: list[Finding] = []
    answers = _answers(session, engagement.engagement_id)
    rendered_placeholders = rendered_placeholders or {}

    findings.extend(_cross_document_rules(engagement, answers))
    findings.extend(_company_class_rules(session, engagement, answers))
    findings.extend(_declared_flag_rules(applicability))
    findings.extend(_applicability_rules(engagement, answers, applicability))
    findings.extend(_completeness_rules(session, engagement, clause_set, answers, blocks))
    findings.extend(_carry_forward_rules(session, engagement))
    findings.extend(_placeholder_rules(rendered_placeholders))
    findings.extend(_identity_rules(session, engagement))
    findings.extend(_director_rules(session, engagement))
    findings.extend(_date_rules(engagement))

    return sorted(findings, key=lambda f: (f.severity is not Severity.BLOCK, f.rule))


# Read for the finding's message. Kept beside the rule rather than taken from
# the YAML label, because a finding a firm sees at export should read as a
# sentence, and the labels are column headings.
DECLARED_LABELS: dict[str, str] = {
    "caro": "CARO 2020",
    "ifc": "internal financial controls reporting under section 143(3)(i)",
    "csr": "corporate social responsibility under section 135",
    "internal_audit": "internal audit under section 138",
    "secretarial_audit": "secretarial audit under section 204",
}


def _declared_flag_rules(applicability: Applicability | None) -> list[Finding]:
    """CARO and IFC are stated by the auditor, and must actually be stated.

    An undecided flag reads as False everywhere downstream, which would drop a
    whole annexure without anyone choosing to. Blocking here is what makes
    "the auditor decides" different from "the auditor forgot".
    """
    if applicability is None:
        return []
    return [
        Finding(
            rule=f"{name}_applicability_not_stated",
            severity=Severity.BLOCK,
            message=(
                f"Whether {DECLARED_LABELS[name]} applies to this company has not been "
                "stated. It is not inferred from any figure — set it on the Applicability "
                "screen."
            ),
            field_key=name,
        )
        for name in sorted(DECLARED_FLAGS)
        if not applicability[name].decided
    ]


def _company_class_rules(
    session: Session, engagement: Engagement, answers: dict[str, str]
) -> list[Finding]:
    """Statements the company's own class says it should not be making.

    A derived answer only fills a gap -- it never overrides one already stored,
    which is right, but it means an engagement answered before the derivation
    existed keeps whatever it was given. So the contradiction is reported rather
    than silently corrected: the auditor decides, and cannot miss it.
    """
    out: list[Finding] = []

    profile = session.scalar(
        select(ClientProfile)
        .join(Client, Client.client_id == ClientProfile.client_id)
        .where(
            Client.client_id == engagement.client_id,
            ClientProfile.is_current.is_(True),
        )
    )
    if profile is None:
        return out

    # Clause (e) of s.134(5) applies by its own words only "in the case of a
    # listed company". Asserting that the directors laid down internal
    # financial controls, and that those controls operated effectively, is a
    # statement the directors sign; an unlisted company is not asked to make it.
    if (
        answers.get("bdr.drs", "") == "with_ifc"
        and profile.company_type is not CompanyType.PUB_LISTED
    ):
        out.append(
            Finding(
                rule="drs_ifc_limb_for_unlisted_company",
                severity=Severity.BLOCK,
                message=(
                    "The Directors' Responsibility Statement includes the internal "
                    "financial controls limb, but the company is not a listed company. "
                    "Clause (e) of section 134(5) applies only to a listed company."
                ),
                field_key="bdr.drs",
                document="directors_report",
            )
        )

    return out


def _cross_document_rules(engagement: Engagement, answers: dict[str, str]) -> list[Finding]:
    out: list[Finding] = []

    # CARO (xi) reports fraud but the MRL states none known.
    fraud_caro = answers.get("caro.xi.a", "")
    fraud_mrl = answers.get("mrl.fraud.disclosure", "")
    if fraud_caro and fraud_caro != "none" and fraud_mrl == "none":
        out.append(
            Finding(
                rule="fraud_contradiction",
                severity=Severity.BLOCK,
                message=(
                    "CARO clause (xi)(a) reports a fraud, but the management "
                    "representation letter states that no fraud is known."
                ),
                field_key="mrl.fraud.disclosure",
            )
        )

    # Going concern material uncertainty but CARO (xix) reports none.
    if (
        engagement.going_concern is GoingConcern.MATERIAL_UNCERTAINTY
        and answers.get("caro.xix", "") == "none"
    ):
        out.append(
            Finding(
                rule="going_concern_contradiction",
                severity=Severity.BLOCK,
                message=(
                    "The auditor's report carries a material uncertainty on going "
                    "concern, but CARO clause (xix) reports no material uncertainty."
                ),
                field_key="caro.xix",
            )
        )

    # Opinion modified but the Directors' Report claims a clean report.
    if engagement.opinion_type and engagement.opinion_type is not OpinionType.CLEAN:
        if answers.get("bdr.auditor.remarks", "").strip() in {"", "none", "clean"}:
            out.append(
                Finding(
                    rule="board_report_contradiction",
                    severity=Severity.BLOCK,
                    message=(
                        f"The opinion is {engagement.opinion_type.value}, but the Board's "
                        "Report records no explanation of the auditor's remarks "
                        "(section 134(3)(f))."
                    ),
                    field_key="bdr.auditor.remarks",
                )
            )

        # Opinion modified but no basis narrative supplied.
        if not answers.get("iar.basis.modified.narrative", "").strip():
            out.append(
                Finding(
                    rule="missing_basis_narrative",
                    severity=Severity.BLOCK,
                    message=(
                        f"The opinion is {engagement.opinion_type.value}, but no basis "
                        "narrative has been supplied."
                    ),
                    field_key="iar.basis.modified.narrative",
                )
            )

    return out


def _applicability_rules(
    engagement: Engagement,
    answers: dict[str, str],
    applicability: Applicability | None,
) -> list[Finding]:
    if applicability is None:
        return []
    out: list[Finding] = []

    # The option values come from `content/auditors_report/iar_143_3_i.yaml`:
    # exempt / unmodified / modified. This test USED to look for the literal
    # "exempt private company", which the clause has never offered -- so the
    # only correct answer for an exempt company still tripped the rule, and an
    # IFC-exempt company could never clear its findings, never be approved and
    # never be finalised. The commonest case in the practice, blocked outright.
    if not applicability.ifc.value and answers.get("iar.143.3.i", "").strip() not in {
        "",
        "exempt",
    }:
        out.append(
            Finding(
                rule="ifc_cross_reference",
                severity=Severity.BLOCK,
                message=(
                    "Internal financial controls reporting is not applicable "
                    f"({applicability.ifc.basis}), but the auditor's report enables the "
                    "Annexure B cross-reference."
                ),
                field_key="iar.143.3.i",
            )
        )

    if not applicability.caro.value and any(
        key.startswith("caro.") and value for key, value in answers.items()
    ):
        out.append(
            Finding(
                rule="caro_not_applicable",
                severity=Severity.WARN,
                message=(
                    f"CARO is not applicable ({applicability.caro.basis}), but CARO "
                    "answers have been recorded."
                ),
            )
        )

    return out


def _completeness_rules(
    session: Session,
    engagement: Engagement,
    clause_set: ClauseSet,
    answers: dict[str, str],
    blocks: DocumentBlocks | None = None,
) -> list[Finding]:
    """What still has to be answered before this engagement can be exported.

    `blocks` is what `build_document` actually could not resolve, gathered by
    rendering every document. **When it is supplied it is the authority**, and
    this walks it -- not the field catalogue.

    Why it has to be. The catalogue knows nothing about the engagement: not
    that a clause was excluded because Rule 8 does not reach a small company,
    nor that an answer was derived from master data. On 20 August 2026 that was
    41 of 129 mandatory fields for a small company -- export blocked by
    questions that never appear on screen.

    That was fixed by FILTERING the catalogue sweep by the build's findings,
    which fixed the false blocks and introduced the mirror-image defect: a
    blocking item the catalogue has no row for produced no finding at all. The
    firm hit it on 21 August 2026 -- "1 finding(s) block export of this
    document" beside a findings table reading "Nothing to report" and a badge
    reading "no blocking findings". A table with no rows has no catalogue row
    by its nature, so it could never have appeared.

    Walking the authority and reaching into the catalogue for a LABEL cannot
    produce that: every blocking clause yields a finding, whether the catalogue
    has heard of it or not.
    """
    out: list[Finding] = []
    catalog = [
        entry
        for entry in session.scalars(select(FieldCatalog))
        if not (entry.effective_from and engagement.fy_end < entry.effective_from)
        and not (entry.effective_to and engagement.fy_end > entry.effective_to)
    ]

    if blocks is None:
        # No build to ask -- the catalogue is all there is. Kept for callers
        # that check an engagement without rendering it.
        for entry in catalog:
            if entry.is_mandatory and not answers.get(entry.field_key, "").strip():
                out.append(
                    Finding(
                        rule="mandatory_empty",
                        severity=Severity.BLOCK,
                        message=f"{entry.label} has no answer.",
                        field_key=entry.field_key,
                    )
                )
        return out

    by_clause: dict[str, list[FieldCatalog]] = {}
    for entry in catalog:
        by_clause.setdefault(entry.clause_id, []).append(entry)

    def title_of(clause_id: str) -> str:
        try:
            return clause_set.get(clause_id).title or clause_id
        except KeyError:
            return clause_id

    for clause_id in sorted(blocks.unanswered):
        empty = [
            entry
            for entry in by_clause.get(clause_id, [])
            if entry.is_mandatory and not answers.get(entry.field_key, "").strip()
        ]
        if empty:
            out.extend(
                Finding(
                    rule="mandatory_empty",
                    severity=Severity.BLOCK,
                    message=f"{entry.label} has no answer.",
                    field_key=entry.field_key,
                )
                for entry in empty
            )
            continue
        # The build could not resolve it and the catalogue has nothing to point
        # at. Reported anyway, naming the clause: an unattributable block is
        # still a block, and silence here is what produced the contradiction.
        out.append(
            Finding(
                rule="clause_unresolved",
                severity=Severity.BLOCK,
                message=(f"{title_of(clause_id)} could not be completed from the answers given."),
                field_key=clause_id,
            )
        )

    for clause_id in sorted(blocks.missing_narratives):
        out.append(
            Finding(
                rule="narrative_missing",
                severity=Severity.BLOCK,
                message=f"{title_of(clause_id)} needs the explanation that goes with this answer.",
                field_key=f"{clause_id}.narrative",
            )
        )

    for clause_id in sorted(blocks.missing_rows):
        out.append(
            Finding(
                rule="rows_missing",
                severity=Severity.BLOCK,
                message=f"{title_of(clause_id)} needs at least one row in its table.",
                field_key=clause_id,
            )
        )

    return out


def _carry_forward_rules(session: Session, engagement: Engagement) -> list[Finding]:
    """§6.2 — carried forward is not the same as verified for this year.

    Independent of the document build, and so of `blocks`: a carried answer
    resolves perfectly well, prints perfectly well, and is exactly as
    exportable as a confirmed one. The only thing wrong with it is that nobody
    has looked at it yet, which no renderer can discover.

    Held in its own rule since decision 76. It used to sit inside the
    completeness sweep, and rewriting that sweep dropped it -- caught by its
    own test, which is the reason to write one per rule rather than one per
    screen.
    """
    unconfirmed = session.scalars(
        select(EngagementResponse).where(
            EngagementResponse.engagement_id == engagement.engagement_id,
            EngagementResponse.source == ResponseSource.CARRIED_FORWARD,
            EngagementResponse.reviewed.is_(False),
        )
    )
    return [
        Finding(
            rule="unconfirmed_carry_forward",
            severity=Severity.BLOCK,
            message=(
                f"{row.field_key} was carried forward from last year and has not been "
                "confirmed for this one."
            ),
            field_key=row.field_key,
        )
        for row in unconfirmed
    ]


def _placeholder_rules(rendered: dict[str, tuple[str, ...]]) -> list[Finding]:
    return [
        Finding(
            rule="unresolved_placeholder",
            severity=Severity.BLOCK,
            message=f"Unresolved placeholder {token} in {document}.",
            document=document,
        )
        for document, tokens in rendered.items()
        for token in tokens
    ]


def _identity_rules(session: Session, engagement: Engagement) -> list[Finding]:
    """Company name, CIN, FRN, partner and membership number must agree.

    They are read from one pinned profile and one firm record, so a mismatch
    means the engagement has lost its profile — which would otherwise show
    up as a blank name in a signed document.
    """
    out: list[Finding] = []
    client = session.get(Client, engagement.client_id)
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None

    if profile is None:
        out.append(
            Finding(
                rule="no_pinned_profile",
                severity=Severity.BLOCK,
                message=(
                    "This engagement has no client profile pinned, so the company name "
                    "and address cannot be resolved."
                ),
            )
        )
    elif not profile.company_name.strip():
        out.append(
            Finding(
                rule="blank_company_name",
                severity=Severity.BLOCK,
                message="The pinned client profile has no company name.",
            )
        )

    if client is not None and not client.cin.strip():
        out.append(
            Finding(
                rule="blank_cin",
                severity=Severity.BLOCK,
                message="The client has no CIN recorded.",
            )
        )

    return out


def _director_rules(session: Session, engagement: Engagement) -> list[Finding]:
    directors = directors_during_fy(
        session, engagement.client_id, engagement.fy_start, engagement.fy_end
    )
    if not directors:
        return [
            Finding(
                rule="no_directors_in_office",
                severity=Severity.BLOCK,
                message=(
                    "No director held office during the financial year, so the "
                    "Directors' Report and signature blocks cannot be produced."
                ),
            )
        ]
    return []


def _date_rules(engagement: Engagement) -> list[Finding]:
    out: list[Finding] = []
    if engagement.report_date is None:
        return out

    if engagement.report_date < engagement.fy_end:
        out.append(
            Finding(
                rule="report_date_before_year_end",
                severity=Severity.WARN,
                message=(
                    f"The report date {engagement.report_date} precedes the financial "
                    f"year end {engagement.fy_end}."
                ),
            )
        )
    elif engagement.report_date > engagement.fy_end + timedelta(days=MAX_REPORT_LAG_DAYS):
        out.append(
            Finding(
                rule="report_date_late",
                severity=Severity.WARN,
                message=(
                    f"The report date is more than {MAX_REPORT_LAG_DAYS} days after the "
                    "financial year end."
                ),
            )
        )
    return out


def udin_finding(engagement: Engagement, udin: str | None) -> Finding | None:
    """Checked at finalisation only (§9)."""
    if udin and udin.strip():
        return None
    return Finding(
        rule="udin_missing",
        severity=Severity.BLOCK,
        message="A UDIN must be entered before the engagement can be finalised.",
    )


def blocking(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.blocks]


def summarise(findings: list[Finding]) -> dict[str, int]:
    return {
        "block": sum(1 for f in findings if f.severity is Severity.BLOCK),
        "warn": sum(1 for f in findings if f.severity is Severity.WARN),
    }
