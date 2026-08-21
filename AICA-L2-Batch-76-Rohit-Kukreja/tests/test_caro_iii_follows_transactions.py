"""CARO 3(iii)(b) to (f) follow the transactions. Decisions 77 and 78.

Paragraph 3(iii) opens "whether during the year the company has made
investments in, provided any guarantee or security or granted any loans or
advances in the nature of loans ... **if so**, --". Everything from (a) to (f)
hangs off that chapeau.

The tool did not honour it. Each limb defaulted to its positive wording, so a
company that had granted nothing still issued an annexure opining that the
terms of its loans were "not prejudicial to the interest of the Company" and
that repayments "have been regular" — assertions about transactions that never
happened, in a document the auditor signs.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.clauses.model import CONTEXT_VARIABLES, ClauseSet
from app.services.document import _transaction_facts, build_document

FY_END = date(2026, 3, 31)
LIMBS = ("b", "c", "d", "e", "f")

#: Wording that asserts something about loans. None of it may appear in a
#: report for a company that granted none.
POSITIVE_ASSERTIONS = (
    "not prejudicial to the interest of the Company",
    "repayments or receipts have been regular",
    "there is no amount which is overdue",
    "has been stipulated",
)


def _context() -> dict[str, object]:
    context: dict[str, object] = dict.fromkeys(CONTEXT_VARIABLES, "")
    context.update({"company_name": "Sample Traders Private Limited", "opinion_type": "clean"})
    return context


def _render(clause_set: ClauseSet, responses: dict[str, str]):
    return build_document(
        clause_set,
        "caro_2020",
        FY_END,
        responses=responses,
        context=_context(),
        applicable=frozenset({"caro"}),
    )


def _text(built) -> str:
    return " ".join(" ".join(built.document.text_nodes()).split())


NOTHING_HAPPENED = {
    "caro.iii.a.A": "none",
    "caro.iii.a.B": "none",
    "caro.iii.investments": "none",
}


class TestTheFactsAreDerivedNotAsked:
    def test_both_limbs_of_the_chapeau_must_say_none(self) -> None:
        assert _transaction_facts(NOTHING_HAPPENED) == {
            "caro_no_loans_granted": True,
            "caro_nothing_under_iii": True,
        }

    @pytest.mark.parametrize(
        "responses",
        [
            {},
            {"caro.iii.a.A": "none"},
            {"caro.iii.a.A": "none", "caro.iii.a.B": "granted"},
            {"caro.iii.a.A": "granted", "caro.iii.a.B": "none"},
        ],
    )
    def test_unanswered_is_not_none(self, responses: dict[str, str]) -> None:
        """The distinction the whole change rests on.

        An auditor who has not yet reached clause (a) has not said there were
        no loans. Treating silence as a nil determination would put the same
        false assertion back with a different provenance.
        """
        assert not _transaction_facts(responses)["caro_no_loans_granted"]

    def test_investments_alone_keep_the_chapeau_open(self) -> None:
        facts = _transaction_facts(
            {"caro.iii.a.A": "none", "caro.iii.a.B": "none", "caro.iii.investments": "made"}
        )
        assert facts["caro_no_loans_granted"]
        assert not facts["caro_nothing_under_iii"]


class TestNothingGrantedReportsNotApplicable:
    def test_every_limb_says_so(self, production_clause_set: ClauseSet) -> None:
        text = _text(_render(production_clause_set, NOTHING_HAPPENED))
        for limb in LIMBS:
            assert (
                f"3(iii)({limb}) of the Order is not applicable" in text
            ), f"3(iii)({limb}) did not report not applicable"

    @pytest.mark.parametrize("phrase", POSITIVE_ASSERTIONS)
    def test_no_generic_positive_assertion_survives(
        self, production_clause_set: ClauseSet, phrase: str
    ) -> None:
        """The complaint itself, one phrase at a time."""
        assert phrase not in _text(_render(production_clause_set, NOTHING_HAPPENED))

    def test_the_document_still_exports(self, production_clause_set: ClauseSet) -> None:
        """Not applicable is an answer. None of the five may be left blocking."""
        built = _render(production_clause_set, NOTHING_HAPPENED)
        stuck = {f"caro.iii.{limb}" for limb in LIMBS} & set(built.unanswered)
        assert stuck == set(), f"still unanswered after a nil determination: {sorted(stuck)}"

    def test_nothing_is_reported_as_an_exception(self, production_clause_set: ClauseSet) -> None:
        """A company with no loans has no CARO exception under 3(iii)."""
        built = _render(production_clause_set, NOTHING_HAPPENED)
        assert not [e for e in built.exceptions if e.startswith("caro.iii.")]


class TestTransactionsKeepTheQuestionsOpen:
    def test_loans_granted_leaves_all_five_to_be_answered(
        self, production_clause_set: ClauseSet
    ) -> None:
        built = _render(
            production_clause_set,
            {"caro.iii.a.A": "granted", "caro.iii.a.B": "none", "caro.iii.investments": "none"},
        )
        for limb in LIMBS:
            assert f"caro.iii.{limb}" in built.unanswered, f"3(iii)({limb}) answered itself"

    def test_investments_without_loans_keep_b_open_but_close_the_rest(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The distinction that needed the extra question.

        Clause (b) reports on "the INVESTMENTS made, guarantees provided,
        security given and the terms and conditions of the grant of all loans".
        (c) to (f) concern loans alone. A company that made investments but
        granted no loans must still be asked (b).
        """
        built = _render(
            production_clause_set,
            {"caro.iii.a.A": "none", "caro.iii.a.B": "none", "caro.iii.investments": "made"},
        )
        assert "caro.iii.b" in built.unanswered, "(b) reported on investments nobody assessed"

        text = _text(built)
        for limb in ("c", "d", "e", "f"):
            assert f"3(iii)({limb}) of the Order is not applicable" in text

    def test_silence_defaults_nothing(self, production_clause_set: ClauseSet) -> None:
        """With nothing answered, every limb stays a question and blocks export.

        Absent-and-blocked beats present-and-wrong — the same rule the Board's
        Comments paragraph was fixed under.
        """
        built = _render(production_clause_set, {})
        for limb in LIMBS:
            assert f"caro.iii.{limb}" in built.unanswered

        text = _text(built)
        for phrase in POSITIVE_ASSERTIONS:
            assert phrase not in text


class TestTheChapeauQuestionPrintsNothing:
    """CARO does not ask for a paragraph saying whether investments exist, only
    for the reporting that follows if they do."""

    def test_it_is_asked(self, production_clause_set: ClauseSet) -> None:
        clause = production_clause_set.get("caro.iii.investments")
        assert clause is not None and clause.input is not None
        assert clause.input.mandatory
        assert set(clause.input.option_values) == {"none", "made"}

    def test_every_variant_is_omitted(self, production_clause_set: ClauseSet) -> None:
        clause = production_clause_set.get("caro.iii.investments")
        assert clause is not None
        assert all(v.omit for v in clause.variants), "the working question prints a paragraph"

    def test_it_never_reaches_the_page(self, production_clause_set: ClauseSet) -> None:
        for answer in ("none", "made"):
            built = _render(
                production_clause_set, {**NOTHING_HAPPENED, "caro.iii.investments": answer}
            )
            text = _text(built)
            assert "has made investments during the year" not in text
            assert "has not made any investments during the year" not in text
            assert "caro.iii.investments" in built.omitted

    def test_it_follows_the_caro_flag(self, production_clause_set: ClauseSet) -> None:
        """No CARO, no question — it must not appear for an exempt company."""
        clause = production_clause_set.get("caro.iii.investments")
        assert clause is not None
        assert "caro" in clause.requires
