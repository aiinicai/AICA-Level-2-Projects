"""Six Board's Report disclosures reported missing on 20 August 2026.

Decision 53 in `docs/GATE_A_DECISIONS.md`.

Four of the six already had wording in the repository and still did not reach
the document, so most of what follows tests the *mechanism* that lost them
rather than the six paragraphs themselves. An unanswered input takes its whole
clause out of the built document; a disclosure nobody consciously skipped can
therefore go missing from a draft with nothing on screen to say so.
"""

from __future__ import annotations

import pathlib
from datetime import date
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as PlainSession

from app.clauses.model import CONTEXT_VARIABLES, ClauseSet
from app.db import Base
from app.models.engagement import FieldCatalog
from app.services.catalog import sync_field_catalog
from app.services.document import build_document

FY_END = date(2026, 3, 31)


def _context(**over: Any) -> dict[str, Any]:
    """A clean small private company that has no group companies."""
    context: dict[str, Any] = dict.fromkeys(CONTEXT_VARIABLES, "")
    context.update(
        {
            "opinion_type": "clean",
            "has_group_companies": False,
            "fy_end_long": "31 March 2026",
            "firm_name": "Example & Associates",
            "firm_frn": "123456W",
        }
    )
    context.update(over)
    return context


def _board_report(
    clause_set: ClauseSet,
    responses: dict[str, str] | None = None,
    **over: Any,
) -> str:
    built = build_document(
        clause_set,
        "directors_report",
        FY_END,
        responses=responses or {},
        context=_context(**over),
    )
    return "\n".join(built.document.text_nodes())


class TestNothingIsDemandedWithoutAFieldToSupplyIt:
    def test_every_clause_wanting_a_narrative_has_one(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The defect behind the team's first report, stated as a property.

        A clause demanding an explanation used to get a field only when it also
        asked a question. `bdr.state.affairs` asked none, so export reported
        "an explanation is required" and no screen offered anywhere to write
        one -- an engagement that could not be completed by any sequence of
        actions. Swept over the repository, because the same wall stood in
        front of every clause driven by engagement data rather than a question:
        `bdr.auditor.remarks` would have hit it the first time a client got a
        qualified opinion.
        """
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with PlainSession(engine) as session:
            sync_field_catalog(session, production_clause_set)
            session.commit()
            keys = set(session.scalars(select(FieldCatalog.field_key)))

        demanded = {
            clause.id
            for clause in production_clause_set.clauses
            if any(v.requires_narrative for v in clause.variants)
        }
        assert demanded, "no clause demands a narrative; this test has stopped testing"
        stranded = sorted(c for c in demanded if f"{c}.narrative" not in keys)
        assert not stranded, f"a narrative is demanded with nowhere to type it: {stranded}"

    def test_a_qualified_opinion_gives_the_board_somewhere_to_explain(
        self, production_clause_set: ClauseSet
    ) -> None:
        """s.134(3)(f)(i): the Board must explain every qualification in full."""
        built = build_document(
            production_clause_set,
            "directors_report",
            FY_END,
            responses={},
            context=_context(opinion_type="qualified"),
        )
        assert "bdr.auditor.remarks" in built.missing_narratives


class TestTheSixDisclosures:
    def test_they_survive_an_entirely_empty_questionnaire(
        self, production_clause_set: ClauseSet
    ) -> None:
        """A clean company's Board's Report is complete before anything is typed."""
        text = _board_report(production_clause_set)
        for what, needle in {
            "state of affairs (s.134(3)(i))": "main objects as set out in the Memorandum",
            "the year's working": "performance was found satisfactory",
            "subsidiaries (Rule 8(5)(iv))": "no subsidiary, joint venture or associate",
            "one-time settlement (Rule 8(5)(xii))": "no one-time settlement of loans",
            "board's comments (s.134(3)(f))": "not made any qualification, reservation",
            "statutory auditors (s.139/141)": "not disqualified from continuing as",
        }.items():
            assert needle in text, f"absent from an unanswered Board's Report: {what}"

    def test_the_state_of_affairs_asks_for_nothing(self, production_clause_set: ClauseSet) -> None:
        """Settled wording, so no question and no explanation field.

        Both texts the partner supplied print under one heading: they are the
        same disclosure under s.134(3)(i) -- the MCA's own Board's Report
        format prints them as one item -- and two headings on one subject would
        read as a drafting slip in a report the directors sign.
        """
        clause = next(c for c in production_clause_set.clauses if c.id == "bdr.state.affairs")
        assert clause.input is None
        assert not any(v.requires_narrative for v in clause.variants)
        assert _board_report(production_clause_set).count("State of the Company's Affairs") == 1

    def test_the_auditors_paragraph_names_the_firm_from_its_own_master(
        self, production_clause_set: ClauseSet
    ) -> None:
        """No firm's name is hard-coded, in this clause least of all.

        The Board's Report names the auditors, so it must name whichever firm
        signs the audit report -- read from Admin -> Firm & Partners, never
        typed a second time somewhere the two could come to disagree.
        """
        text = _board_report(
            production_clause_set,
            responses={"bdr.statutory.auditors": "2021"},
            firm_name="Quite Another & Co",
            firm_frn="999999S",
        )
        assert "Quite Another & Co" in text
        assert "999999S" in text
        assert "held in the year 2021" in text

    def test_an_unentered_appointment_year_is_visible_not_missing(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The paragraph prints with a bracket rather than disappearing.

        The bracket trips the pre-export placeholder scan, so it cannot reach a
        signed report -- but the draft shows the auditor what is wanted, which
        an absent paragraph does not.
        """
        built = build_document(
            production_clause_set,
            "directors_report",
            FY_END,
            responses={},
            context=_context(),
        )
        assert any("year the term ends" in p for p in built.placeholders)


class TestMasterDataFillsGapsWithoutOverrulingAnyone:
    def test_a_derived_answer_never_replaces_the_auditors_own(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Swept over every clause carrying defaults, not just the two added.

        A default exists to remove the unanswered state, which is what dropped
        these disclosures from the document. It must never decide something the
        auditor has decided: the whole point of the dropdown is that the
        assumption can be reversed for the client that departs from it.
        """
        carrying = [
            c
            for c in production_clause_set.clauses
            if c.input is not None and c.input.defaults and c.input.options
        ]
        assert carrying, "no clause derives an answer; this test has stopped testing"

        for clause in carrying:
            assert clause.input is not None
            derived = {d.value for d in clause.input.defaults}
            contrary = next((o.value for o in clause.input.options if o.value not in derived), None)
            if contrary is None:
                continue
            answered = build_document(
                production_clause_set,
                clause.document,
                FY_END,
                responses={clause.input.key: contrary},
                context=_context(),
            )
            derived_only = build_document(
                production_clause_set,
                clause.document,
                FY_END,
                responses={},
                context=_context(),
            )
            assert (
                clause.id not in answered.unanswered
            ), f"{clause.id}: an explicit answer left the clause unanswered"
            assert "\n".join(answered.document.text_nodes()) != "\n".join(
                derived_only.document.text_nodes()
            ), f"{clause.id}: answering it changed nothing, so the default overruled the auditor"

    def test_the_company_with_a_subsidiary_is_still_asked(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Deriving the nil case must not suppress the real question.

        Where the profile records a subsidiary, an associate or a joint
        venture, what became or ceased to be one during the year is a matter of
        fact no master field knows, and the questionnaire has to ask.
        """
        built = build_document(
            production_clause_set,
            "directors_report",
            FY_END,
            responses={},
            context=_context(has_group_companies=True),
        )
        assert "bdr.subsidiaries" in built.unanswered

    def test_the_nil_subsidiary_paragraph_needs_no_answer(
        self, production_clause_set: ClauseSet
    ) -> None:
        """And where it records none, nobody is asked at all."""
        built = build_document(
            production_clause_set,
            "directors_report",
            FY_END,
            responses={},
            context=_context(has_group_companies=False),
        )
        assert "bdr.subsidiaries" not in built.unanswered

    def test_a_default_can_only_name_an_answer_its_input_offers(
        self, production_clause_set: ClauseSet
    ) -> None:
        """A typo in a default must fail at load, not at render.

        The same class of mistake as the flag-name typo that silently deleted
        clauses: a default naming an option that does not exist would resolve
        to nothing and take the disclosure out of the document again.
        """
        for clause in production_clause_set.clauses:
            if clause.input is None or not clause.input.options:
                continue
            offered = clause.input.option_values
            for default in clause.input.defaults:
                assert (
                    default.value in offered
                ), f"{clause.id}: default {default.value!r} is not an option"


class TestTheWorkspaceDescribesCarryForwardTruthfully:
    def test_no_template_tests_for_a_value_the_enum_does_not_have(self) -> None:
        """A comparison against a value that cannot occur is always false.

        The tooltip tested `carry_forward.value == 'auto'`; the enum's member
        is `always`. Every carried-forward field therefore fell through to the
        final branch and told the auditor it was "answered afresh each year" --
        the opposite of what the field does. Nothing failed, because a wrong
        sentence in a title attribute breaks no test; it surfaced only when the
        first `always` field appeared in the Board's Report.

        The same shape as the flag-name typo that silently dropped clauses, so
        it is checked the same way: every value a template compares against
        must be a real member.
        """
        import re

        from app.clauses.model import CarryForward

        members = {m.value for m in CarryForward}
        pattern = re.compile(r"carry_forward\.value\s*==\s*['\"]([a-z_]+)['\"]")
        checked = 0
        for path in pathlib.Path("app/templates").rglob("*.html"):
            for compared in pattern.findall(path.read_text(encoding="utf-8")):
                checked += 1
                assert compared in members, (
                    f"{path.name}: compares carry_forward against {compared!r}, "
                    f"which is not one of {sorted(members)}"
                )
        assert checked, "no carry_forward comparison found; this test has stopped testing"


class TestTheDirectorsResponsibilityStatement:
    """Clause (e) of s.134(5) applies "in the case of a listed company"."""

    def test_an_unlisted_company_does_not_assert_internal_financial_controls(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The most serious thing on the team's list, though they did not name it.

        The Board's Report was stating that the directors had laid down internal
        financial controls and that those controls were operating effectively --
        for an unlisted private company, which section 134(5)(e) does not ask to
        say it. The wording to omit the limb existed; nothing selected it.
        """
        text = _board_report(production_clause_set, is_listed_company=False)
        assert "laid down internal financial controls" not in text
        assert "clause (e) of sub-section (5)" in text

    def test_a_listed_company_still_asserts_them(self, production_clause_set: ClauseSet) -> None:
        """Deriving the omission must not make the limb unreachable."""
        text = _board_report(production_clause_set, is_listed_company=True)
        assert "laid down internal financial controls" in text

    def test_a_stored_contrary_answer_blocks_export(
        self, db: Session, client_id: int, production_clause_set: ClauseSet
    ) -> None:
        """An engagement answered before the derivation existed keeps its answer.

        That is the right behaviour for a default -- it fills a gap, it does not
        overrule a person -- so the contradiction has to surface somewhere the
        auditor cannot miss it, on a file already part-answered when this
        landed. It blocks export.
        """
        from app.core.consistency import check
        from app.models.engagement import Engagement, EngagementResponse
        from app.models.enums import CompanyType
        from app.models.masters import ClientProfile

        engagement = db.scalar(select(Engagement).where(Engagement.client_id == client_id).limit(1))
        assert engagement is not None, "seed data missing"
        profile = db.scalar(
            select(ClientProfile).where(
                ClientProfile.client_id == client_id, ClientProfile.is_current.is_(True)
            )
        )
        assert profile is not None
        assert profile.company_type is not CompanyType.PUB_LISTED

        # The test database carries the fixture repository's catalogue, and a
        # response is keyed to a catalogued field. Sync production's fields in
        # without pruning, so the fixture's own rows survive for other tests.
        sync_field_catalog(db, production_clause_set, prune=False)
        db.flush()
        db.add(
            EngagementResponse(
                engagement_id=engagement.engagement_id,
                field_key="bdr.drs",
                value_text="with_ifc",
            )
        )
        db.flush()

        rules = {f.rule for f in check(db, engagement, production_clause_set) if f.blocks}
        assert "drs_ifc_limb_for_unlisted_company" in rules


class TestRuleEightDoesNotReachASmallCompany:
    """Decision 56 — the partner's direction of 20 August 2026.

    Rule 8(6): "This rule shall not apply to One Person Company or Small
    Company." Rule 8A then prescribes a closed, exhaustive list. For those
    companies the Rule 8 paragraphs are omitted outright -- not defaulted, not
    left as placeholders.
    """

    SMALL = frozenset({"abridged_board_report"})
    FULL = frozenset({"full_board_report", "s197", "secretarial_audit", "csr", "cost_records"})

    def test_the_two_flags_are_strict_inverses(self) -> None:
        """One determination under two names, so they cannot drift apart.

        Swept over every company type, and over the override, because the
        failure this prevents is a company determined abridged whose report
        still carries the Rule 8 paragraphs -- neither form, and compliant
        with neither rule.
        """
        from datetime import date

        from app.config import get_settings
        from app.core.applicability import ProfileFacts, compute

        rules = get_settings().content_path / "applicability_rules.yaml"

        for company_type in ("pvt", "pub_unlisted", "pub_listed", "opc", "small", "sec8", "nidhi"):
            for override in ({}, {"abridged_board_report": True}, {"abridged_board_report": False}):
                result = compute(
                    ProfileFacts(company_type=company_type),
                    date(2026, 3, 31),
                    rules,
                    overrides=override,
                )
                assert result.full_board_report.value is not result.abridged_board_report.value, (
                    f"{company_type} with override {override}: the flags agree, "
                    "so the company is both abridged and full"
                )

    def test_a_small_company_gets_no_rule_eight_paragraph(
        self, production_clause_set: ClauseSet
    ) -> None:
        built = build_document(
            production_clause_set,
            "directors_report",
            FY_END,
            responses={},
            context=_context(),
            applicable=self.SMALL,
        )
        text = " ".join(built.document.text_nodes())
        for absent in (
            "Internal Complaints Committee",  # Rule 8(5)(x)
            "Conservation of Energy",  # Rule 8(3)
            "subsidiary, joint venture",  # Rule 8(5)(iv)
            "one-time settlement",  # Rule 8(5)(xii)
            "Maternity Benefit Act",  # Rule 8(5)(xiii)
            "cost records",  # Rule 8(5)(ix)
        ):
            assert absent not in text, f"Rule 8 paragraph reached a small company: {absent!r}"

    def test_nothing_gated_is_left_defaulted_or_as_a_placeholder(
        self, production_clause_set: ClauseSet
    ) -> None:
        """ "Do not insert them, do not default them, do not leave placeholders."

        A clause excluded by applicability is dropped before its input is read,
        so no derived answer fires and no bracket survives. Asserted rather than
        assumed, because the derivation and the gate were built a day apart.
        """
        built = build_document(
            production_clause_set,
            "directors_report",
            FY_END,
            responses={},
            context=_context(),
            applicable=self.SMALL,
        )
        gated = {c.id for c in production_clause_set.clauses if "full_board_report" in c.requires}
        assert gated, "nothing is gated; this test has stopped testing"
        assert gated <= set(built.not_applicable)
        assert not (gated & set(built.unanswered))
        assert not (gated & set(built.missing_narratives))
        assert not (gated & set(built.missing_rows))

    def test_a_company_rule_eight_does_reach_still_gets_them(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Gating the small company must not quietly drop them for everyone."""
        built = build_document(
            production_clause_set,
            "directors_report",
            FY_END,
            responses={},
            context=_context(),
            applicable=self.FULL,
        )
        text = " ".join(built.document.text_nodes())
        assert not built.not_applicable
        for present in ("Internal Complaints Committee", "Conservation of Energy", "cost records"):
            assert present in text, f"absent from a full Board's Report: {present!r}"


class TestTheExportGateAsksOnlyWhatIsMissing:
    """Decision 64 — the gate reads the documents, not the field catalogue.

    The catalogue knows what is mandatory. It does not know that a clause was
    excluded because Rule 8 does not reach a small company, nor that an answer
    was derived from master data. It was demanding both: on 20 August 2026,
    41 of 129 mandatory fields for a small company blocked export over
    questions that never appear on screen or that the tool answers itself.
    """

    def test_no_gated_or_defaulted_clause_is_demanded(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        from app.core.consistency import _completeness_rules
        from app.models.engagement import Engagement

        engagement = db.scalar(select(Engagement))
        assert engagement is not None

        gated = {c.id for c in production_clause_set.clauses if "full_board_report" in c.requires}
        defaulted = {
            c.id for c in production_clause_set.clauses if c.input is not None and c.input.defaults
        }
        assert gated and defaulted, "nothing to test against"

        # What the documents actually could not resolve for a small company:
        # neither a gated clause nor a defaulted one is in it.
        # Decision 76 carries the three kinds apart, so the rule can say
        # which sort of gap each one is.
        from app.core.consistency import DocumentBlocks

        resolved_by_the_build = DocumentBlocks()

        findings = _completeness_rules(
            db, engagement, production_clause_set, {}, resolved_by_the_build
        )
        demanded = {f.field_key for f in findings}
        assert demanded == set(), (
            "the gate demanded answers the document build did not ask for: "
            f"{sorted(demanded)[:5]}"
        )

    def test_without_the_build_it_falls_back_to_the_catalogue(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        """The fallback stays, so a caller that cannot render still gets a gate.

        It over-asks -- that is the whole finding above -- but a gate that
        over-asks is safer than one that vanishes when a document fails to
        build.
        """
        from app.core.consistency import _completeness_rules
        from app.models.engagement import Engagement

        engagement = db.scalar(select(Engagement))
        assert engagement is not None
        findings = _completeness_rules(db, engagement, production_clause_set, {}, None)
        assert findings, "the fallback sweep stopped asking anything"
