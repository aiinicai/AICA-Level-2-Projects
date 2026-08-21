"""The single applicability engine. Build Prompt v2 §7.

Every threshold asserted here is a *derivation*, not a sourced fact — see the
header of `content/applicability_rules.yaml`. These tests lock in the
behaviour of the rules file, so that when the partner corrects a number the
failure is loud and localised rather than silent.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.applicability import (
    FLAGS,
    ApplicabilityError,
    ProfileFacts,
    compute,
    load_rules,
)
from tests.conftest import CONTENT_DIR

RULES = CONTENT_DIR / "applicability_rules.yaml"
FY = date(2026, 3, 31)

CRORE = Decimal(10_000_000)


def _facts(**kwargs: object) -> ProfileFacts:
    base: dict[str, object] = {"company_type": "pvt"}
    base.update(kwargs)
    return ProfileFacts(**base)  # type: ignore[arg-type]


class TestRulesFile:
    def test_every_flag_has_a_rule(self) -> None:
        rules = load_rules(RULES)
        assert set(FLAGS) <= set(rules)

    def test_a_confirmed_threshold_still_states_its_authority(self) -> None:
        """Confirmed on 17 August 2026, so the old assertion — that every rule
        was still flagged `needs_review` — no longer holds and would fail.

        What replaces it is the property that outlives the sign-off: a
        threshold may be presented as settled only while it says which
        provision it comes from. A number with no `reference` is a number
        nobody can check.
        """
        rules = load_rules(RULES)
        unattributed = [
            name
            for name, rule in rules.items()
            if not rule.get("needs_review") and not str(rule.get("reference", "")).strip()
        ]
        assert not unattributed, f"settled thresholds with no authority cited: {unattributed}"

    def test_caro_and_ifc_read_no_thresholds_at_all(self) -> None:
        """Partner's instruction of 20 August 2026 - ask, do not infer.

        Both exemptions turn on facts the profile's figures do not carry: CARO's
        private limb is lost outright if the company is a subsidiary or holding
        company of a public company, and the s.143(3)(i) exemption is lost under
        paragraph 2A of G.S.R. 583(E) if the company has defaulted in filing
        under s.92 or s.137. An engine reading turnover and borrowings is
        confidently wrong in both directions.

        The thresholds stay in each rule's `note` for the auditor to read, and
        nothing evaluates them. Asserted by key name, because a threshold key
        creeping back is exactly how the inference would return.
        """
        rules = load_rules(RULES)
        suffixes = ("_below", "_not_exceeding", "_min", "_max")
        for name in ("caro", "ifc"):
            rule = rules[name]
            assert rule.get("declared") is True, f"{name} is no longer declared"
            assert str(rule.get("note", "")).strip(), f"{name}: the law is not recorded"
            numeric = [
                key
                for key, value in rule.items()
                if key.endswith(suffixes)
                or (isinstance(value, dict) and any(k.endswith(suffixes) for k in value))
            ]
            assert not numeric, f"{name} has thresholds again: {numeric}"

    def test_no_rule_reads_a_figure(self) -> None:
        """Partner's instruction of 20 August 2026, stated as a property.

        No applicability flag is linked to a financial parameter in master
        data. What remains computed turns on company class or on a yes/no fact
        the profile records — never on an amount. Swept over the whole file, so
        a threshold cannot reappear on one rule unnoticed.
        """
        suffixes = ("_min", "_max", "_below", "_not_exceeding")
        offenders = []
        for name, rule in load_rules(RULES).items():
            for key, value in rule.items():
                if key.endswith(suffixes):
                    offenders.append(f"{name}.{key}")
                if isinstance(value, dict):
                    offenders += [f"{name}.{key}.{k}" for k in value if k.endswith(suffixes)]
        assert not offenders, f"applicability still reads figures: {offenders}"

    def test_the_law_survives_where_the_logic_did_not(self) -> None:
        """A declared flag must still tell the auditor what to apply.

        Deleting the thresholds without recording them would leave the tool
        asking a question it gives no help in answering, and the firm reaching
        for a bare act every time.
        """
        for name, rule in load_rules(RULES).items():
            if rule.get("declared"):
                assert str(rule.get("note", "")).strip(), f"{name}: declared with no note"

    def test_the_secretarial_audit_note_keeps_the_2020_limb(self) -> None:
        """The amendment most often missed, now prose rather than a threshold.

        Rule 9 was amended on 3 January 2020 to reach EVERY company borrowing
        Rs. 100 crore or more, private companies included. The old "s.204 does
        not apply to private companies" shortcut is wrong, and the note has to
        keep saying so.
        """
        note = load_rules(RULES)["secretarial_audit"]["note"]
        assert "100 crore" in note
        assert "private" in note.lower()

    def test_a_missing_rule_is_a_loud_error(self, tmp_path) -> None:
        broken = tmp_path / "applicability_rules.yaml"
        broken.write_text("version: x\nrules:\n  caro: {}\n", encoding="utf-8")
        with pytest.raises(ApplicabilityError, match="no rule for"):
            load_rules(broken)


class TestSection197:
    def test_does_not_apply_to_private_companies(self) -> None:
        assert compute(_facts(), FY, RULES).s197.value is False

    def test_applies_to_public_companies(self) -> None:
        assert compute(_facts(company_type="pub_unlisted"), FY, RULES).s197.value is True


class TestKamAndAbridged:
    def test_kam_is_for_listed_companies(self) -> None:
        assert compute(_facts(company_type="pub_listed"), FY, RULES).kam.value is True
        assert compute(_facts(company_type="pvt"), FY, RULES).kam.value is False

    def test_abridged_board_report_for_opc_and_small(self) -> None:
        assert compute(_facts(company_type="small"), FY, RULES).abridged_board_report.value is True
        assert compute(_facts(company_type="pvt"), FY, RULES).abridged_board_report.value is False


class TestUnknowableFacts:
    """§7's input list cannot decide these, and guessing would be worse."""

    def test_cost_records_says_so_rather_than_guessing(self) -> None:
        flag = compute(_facts(), FY, RULES).cost_records
        assert flag.value is False
        assert "must be set on the client" in flag.basis

    def test_cfs_says_so_rather_than_guessing(self) -> None:
        flag = compute(_facts(), FY, RULES).cfs_required
        assert flag.value is False
        assert "not recorded" in flag.basis

    def test_they_answer_correctly_once_told(self) -> None:
        assert compute(_facts(cost_records_industry=True), FY, RULES).cost_records.value is True
        assert compute(_facts(has_subsidiary=True), FY, RULES).cfs_required.value is True


class TestBasisIsAlwaysGiven:
    def test_every_flag_explains_itself(self) -> None:
        # §7 — the basis is shown in the UI tooltip. A blank one is useless.
        result = compute(_facts(company_type="pub_listed"), FY, RULES)
        for name in FLAGS:
            assert result[name].basis.strip(), f"{name} has no basis"


class TestOverrides:
    """Demonstrated on `kam`, one of the flags the engine still computes.

    The example has moved twice. CARO and IFC became declared on 20 August
    2026, then CSR followed the same afternoon along with internal audit and
    secretarial audit. What is left computed turns on company class, never on a
    figure — and only a computed flag has an answer worth overruling.
    """

    def test_an_override_replaces_the_value(self) -> None:
        result = compute(_facts(), FY, RULES, overrides={"kam": True})
        assert result.kam.value is True
        assert result.kam.overridden is True

    def test_an_override_keeps_the_computed_reasoning_visible(self) -> None:
        result = compute(_facts(), FY, RULES, overrides={"kam": True})
        assert "computed: False" in result.kam.basis

    def test_nothing_else_is_marked_overridden(self) -> None:
        result = compute(_facts(), FY, RULES, overrides={"kam": True})
        assert all(not result[n].overridden for n in FLAGS if n != "kam")

    def test_an_unknown_flag_is_refused(self) -> None:
        with pytest.raises(ApplicabilityError, match="not an applicability flag"):
            compute(_facts(), FY, RULES, overrides={"nonsense": True})


class TestPurity:
    def test_the_same_inputs_give_the_same_result(self) -> None:
        facts = _facts(company_type="pub_listed")
        assert compute(facts, FY, RULES) == compute(facts, FY, RULES)

    def test_all_six_documents_would_read_one_result(self) -> None:
        """§7 — the prototype had company type wired to nothing and s.197
        driven by an unrelated toggle. One dataclass makes that impossible."""
        result = compute(_facts(company_type="pub_listed"), FY, RULES)
        assert set(result.as_dict()) == set(FLAGS)


CRORE_ = Decimal(10_000_000)


class TestConsolidatedFinancialStatements:
    """s.129(3) reaches associates and joint ventures too, and Rule 6 exempts."""

    def test_an_associate_alone_triggers_cfs(self) -> None:
        result = compute(_facts(has_associate=True), FY, RULES)
        assert result.cfs_required.value is True
        assert "associate" in result.cfs_required.basis

    def test_a_joint_venture_alone_triggers_cfs(self) -> None:
        result = compute(_facts(has_joint_venture=True), FY, RULES)
        assert result.cfs_required.value is True

    def test_none_of_the_three_means_no_cfs(self) -> None:
        result = compute(
            _facts(has_subsidiary=False, has_associate=False, has_joint_venture=False),
            FY,
            RULES,
        )
        assert result.cfs_required.value is False

    def test_rule_6_exempts_a_wholly_owned_unlisted_subsidiary(self) -> None:
        result = compute(
            _facts(
                has_subsidiary=True,
                is_wholly_owned_or_unopposed_partially_owned=True,
                not_listed_or_in_process_of_listing=True,
                parent_files_compliant_cfs=True,
            ),
            FY,
            RULES,
        )
        assert result.cfs_required.value is False
        assert "Rule 6" in result.cfs_required.basis

    def test_the_exemption_needs_all_three_limbs(self) -> None:
        # Listed, so the exemption is unavailable however else it qualifies.
        result = compute(
            _facts(
                has_subsidiary=True,
                is_wholly_owned_or_unopposed_partially_owned=True,
                not_listed_or_in_process_of_listing=False,
                parent_files_compliant_cfs=True,
            ),
            FY,
            RULES,
        )
        assert result.cfs_required.value is True

    def test_unrecorded_status_says_so_rather_than_guessing(self) -> None:
        flag = compute(_facts(), FY, RULES).cfs_required
        assert flag.value is False
        assert "not recorded" in flag.basis


class TestCaroAndIfcAreStatedNotInferred:
    """Decision 59 - the auditor decides, and must actually decide.

    The classes this replaces - TestCaro, TestIfc, TestCaroPublicRelationship,
    TestExemptionBoundaries - tested an inference that no longer exists. The law
    they encoded is not lost: it is written into each rule's `note`, and why the
    inference went is decision 58. The IFC test read "and" where the
    notification says "or", put One Person Companies and small companies through
    a threshold test that limb (i) exempts them from outright, and could not see
    the filing-default condition in paragraph 2A at all.
    """

    def test_neither_is_decided_until_someone_says_so(self) -> None:
        result = compute(_facts(), FY, RULES)
        for name in ("caro", "ifc"):
            assert result[name].decided is False, f"{name} decided itself"
            assert result[name].value is False, f"{name}: undecided must read as not applicable"
            assert "auditor" in result[name].basis

    def test_no_company_type_moves_either_of_them(self) -> None:
        """The whole point: nothing the profile records changes the answer.

        The figures cannot be passed at all now — `ProfileFacts` stopped
        carrying them on 20 August 2026 — so the sweep is over company class,
        which is the only thing left that could plausibly move a flag.
        """
        for company_type in ("pvt", "pub_unlisted", "pub_listed", "opc", "small", "sec8"):
            result = compute(_facts(company_type=company_type), FY, RULES)
            assert result.caro.decided is False
            assert result.ifc.decided is False

    def test_the_auditors_answer_is_recorded_as_an_answer(self) -> None:
        """Not as an override, because there is nothing to overrule."""
        result = compute(_facts(), FY, RULES, overrides={"caro": True, "ifc": True})
        for name in ("caro", "ifc"):
            assert result[name].value is True
            assert result[name].decided is True
            assert result[name].overridden is False, f"{name} reads as an override"
            assert "stated by the auditor" in result[name].basis

    def test_answering_not_applicable_still_counts_as_answered(self) -> None:
        """The distinction that makes the export gate work.

        "Not applicable" and "nobody has said" both read as False downstream.
        Only `decided` separates them, and without it a forgotten question would
        silently drop a whole annexure.
        """
        result = compute(_facts(), FY, RULES, overrides={"caro": False})
        assert result.caro.value is False
        assert result.caro.decided is True


class TestNoFlagReadsAFigure:
    """Decision 61 — the instruction, swept rather than spot-checked."""

    DECLARED = ("caro", "ifc", "csr", "internal_audit", "secretarial_audit")

    def test_every_financial_flag_is_declared(self) -> None:
        from app.core.applicability import DECLARED_FLAGS

        assert set(self.DECLARED) == set(DECLARED_FLAGS)

    def test_none_of_them_decides_itself(self) -> None:
        result = compute(_facts(), FY, RULES)
        for name in self.DECLARED:
            assert result[name].decided is False, f"{name} decided itself"

    def test_what_is_left_computed_turns_on_class_not_money(self) -> None:
        """The engine may still read the company type and yes/no facts.

        Those are what the partner kept: the Rule 8A gate depends on company
        class, and consolidation depends on whether a subsidiary exists. Both
        are facts the profile records as such, not amounts to be compared.
        """
        from app.core.applicability import DECLARED_FLAGS

        computed = [name for name in FLAGS if name not in DECLARED_FLAGS]
        assert computed, "everything is declared; this test has stopped testing"
        for name in computed:
            rule = load_rules(RULES)[name]
            allowed = {
                "label",
                "reference",
                "effective_from",
                "needs_review",
                "note",
                "company_types",
                "industry_driven",
                "triggers_any_of",
                "rule_6_exemption",
            }
            unexpected = set(rule) - allowed
            assert not unexpected, f"{name} reads something new: {sorted(unexpected)}"

    def test_the_auditors_answer_reaches_the_engine(self) -> None:
        result = compute(_facts(), FY, RULES, overrides=dict.fromkeys(self.DECLARED, True))
        for name in self.DECLARED:
            assert result[name].value is True
            assert result[name].decided is True
            assert "stated by the auditor" in result[name].basis
