"""The firm's team, fifth round — 21 August 2026. Decision 72.

Items 3, 7 and 8. The crash (item 11) is covered by
`tests/test_negative_amounts.py`; the financial summary (item 4), the director
register (item 5) and the long-page navigation (items 6 and 10) have their own
files.
"""

from __future__ import annotations

from datetime import date

from app.clauses.model import CONTEXT_VARIABLES, ClauseSet
from app.services.document import build_document

FY_END = date(2026, 3, 31)


def _context(**over: object) -> dict[str, object]:
    context: dict[str, object] = dict.fromkeys(CONTEXT_VARIABLES, "")
    context.update(
        {
            "opinion_type": "clean",
            "going_concern": "none",
            "framework": "igaap",
            "company_name": "Sample Traders Private Limited",
            "firm_name": "Example & Co",
            "firm_frn": "123456W",
            "partner_name": "A Partner",
            "partner_mno": "654321",
            "udin": "26654321ABCDEF1234",
            "place": "New Delhi",
            "report_date_long": "1 September 2026",
            "fy_end_long": "31 March 2026",
        }
    )
    context.update(over)
    return context


def _text(clause_set: ClauseSet, document: str, applicable: frozenset[str]) -> str:
    built = build_document(
        clause_set, document, FY_END, responses={}, context=_context(), applicable=applicable
    )
    return " ".join(" ".join(built.document.text_nodes()).split())


class TestEverySignedDocumentIsSigned:
    """Item 3. CARO ended on clause 3(xxi) with nothing beneath it.

    CARO 2020 is an annexure to the auditor's report and carries the same
    signature. Annexure B had a block from the first build; this one was never
    written, and the document rendered, validated and exported perfectly well
    without it -- which is exactly why it survived four rounds of review.
    """

    #: Documents a person signs. MGT-9 and the Board's Report are signed by the
    #: directors, the rest by the auditor; either way the page ends with a name.
    SIGNED = ("auditors_report", "caro_2020", "ifc_report", "directors_report", "mgt9", "mrl")

    def test_no_signed_document_lacks_a_signature_clause(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Swept, not listed. A document added next month is covered too."""
        offenders = []
        for document in self.SIGNED:
            clauses = [c for c in production_clause_set.clauses if c.document == document]
            if not any(c.render_as == "signature" for c in clauses):
                offenders.append(document)
        assert offenders == [], f"these documents end unsigned: {offenders}"

    def test_caro_is_signed_by_the_firm_that_signed_the_report(
        self, production_clause_set: ClauseSet
    ) -> None:
        text = _text(production_clause_set, "caro_2020", frozenset({"caro"}))
        assert "For Example & Co" in text
        assert "Firm's Registration No: 123456W" in text
        assert "Membership No: 654321" in text

    def test_the_caro_signature_is_interpolated_never_typed(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The annexure cannot name a different partner from the report."""
        clause = production_clause_set.get("caro.sig")
        assert clause is not None
        body = clause.variants[0].body
        for field in ("{{ firm_name }}", "{{ firm_frn }}", "{{ partner_name }}", "{{ udin }}"):
            assert field in body, f"{field} is not taken from the firm record"
        assert clause.input is None, "nothing about the signature is retyped"

    def test_it_goes_last(self, production_clause_set: ClauseSet) -> None:
        caro = [c for c in production_clause_set.clauses if c.document == "caro_2020"]
        signature = next(c for c in caro if c.render_as == "signature")
        assert signature.order == max(c.order for c in caro)

    def test_it_follows_the_caro_flag(self, production_clause_set: ClauseSet) -> None:
        """No CARO, no CARO signature — the annexure is not produced at all."""
        clause = production_clause_set.get("caro.sig")
        assert clause is not None
        assert "caro" in clause.requires


class TestTheEngagementLetterOpensOnTheCommonCase:
    """Items 7 and 8."""

    def test_the_fee_defaults_to_agreement_with_the_board(
        self, production_clause_set: ClauseSet
    ) -> None:
        text = _text(production_clause_set, "engagement_letter", frozenset())
        assert "mutually agreed between the Board of Directors" in text
        assert "fixed by the members at the annual general meeting" not in text

    def test_the_appointment_defaults_to_continuing(self, production_clause_set: ClauseSet) -> None:
        text = _text(production_clause_set, "engagement_letter", frozenset())
        assert "ratification" in text

    def test_both_remain_answerable(self, production_clause_set: ClauseSet) -> None:
        """A default is a starting point, not a decision taken away."""
        for key, other in (("eng.fees", "agm"), ("eng.header", "first")):
            clause = production_clause_set.get(key)
            assert clause is not None and clause.input is not None
            assert other in clause.input.option_values, f"{key} lost its alternative"

    def test_a_default_is_not_a_confirmed_answer(self, production_clause_set: ClauseSet) -> None:
        """Defaulted clauses still print; the question still stands on screen."""
        for key in ("eng.fees", "eng.header"):
            clause = production_clause_set.get(key)
            assert clause is not None and clause.input is not None
            assert clause.input.mandatory, f"{key} stopped being asked"
