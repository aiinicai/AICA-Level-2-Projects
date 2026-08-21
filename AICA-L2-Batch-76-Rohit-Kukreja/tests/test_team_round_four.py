"""The firm's team, fourth round — 21 August 2026. Decision 68.

Three observations on the auditor's report: the CIN was absent, Rule 11(g) was
short of its preservation limb, and the letterhead repeated on every page.
"""

from __future__ import annotations

import tempfile
import zipfile
from datetime import date
from pathlib import Path

from app.clauses.model import CONTEXT_VARIABLES, ClauseSet
from app.render import docx as docx_renderer
from app.render.base import Document, Heading, Para
from app.services.document import build_document

FY_END = date(2026, 3, 31)
CIN = "U51909DL2015PTC123456"


def _context(**over: object) -> dict[str, object]:
    context: dict[str, object] = dict.fromkeys(CONTEXT_VARIABLES, "")
    context.update(
        {
            "opinion_type": "clean",
            "going_concern": "none",
            "framework": "igaap",
            "company_name": "Sample Traders Private Limited",
            "cin": CIN,
            "cash_flow_required": False,
            "has_group_companies": False,
            "is_listed_company": False,
            "fy_end_long": "31 March 2026",
            "firm_name": "Example & Co",
            "firm_frn": "123456W",
        }
    )
    context.update(over)
    return context


def _report(clause_set: ClauseSet, **responses: str) -> str:
    built = build_document(
        clause_set,
        "auditors_report",
        FY_END,
        responses=dict(responses),
        context=_context(),
        applicable=frozenset({"caro", "ifc"}),
    )
    return " ".join(" ".join(built.document.text_nodes()).split())


class TestTheCinIsQuoted:
    """The CIN identifies the company beyond doubt; a name alone does not."""

    def test_it_appears_in_the_report(self, production_clause_set: ClauseSet) -> None:
        assert f"CIN: {CIN}" in _report(production_clause_set)

    def test_it_comes_from_the_client_record(self, production_clause_set: ClauseSet) -> None:
        """Interpolated, never typed — the report cannot name a different CIN
        from the one on the client's own record."""
        clause = production_clause_set.get("iar.addressee")
        assert clause is not None
        assert "{{ cin }}" in clause.variants[0].body


class TestRuleElevenGReportsPreservation:
    """Rule 11(g) asks about three things. The clean variant asserted two."""

    def test_the_clean_answer_covers_preservation(self, production_clause_set: ClauseSet) -> None:
        text = _report(production_clause_set, **{"rule11.g.status": "throughout"})
        assert "operated throughout the year" in text
        assert "not come across any instance of the audit trail feature being tampered" in text
        assert (
            "preserved by the Company as per the statutory requirements for record retention"
            in text
        )

    def test_all_three_limbs_are_answerable(self, production_clause_set: ClauseSet) -> None:
        """A clause whose label promises three things must let all three be
        answered. The label said "use, operation and preservation" for months
        while the wording covered only the first two, which is exactly how a
        gap reads as covered.
        """
        clause = production_clause_set.get("rule11.g")
        assert clause is not None and clause.input is not None
        assert "not_preserved" in clause.input.option_values

    def test_the_not_preserved_answer_says_so_and_is_an_exception(
        self, production_clause_set: ClauseSet
    ) -> None:
        text = _report(production_clause_set, **{"rule11.g.status": "not_preserved"})
        assert "has not been preserved by the Company" in text

        clause = production_clause_set.get("rule11.g")
        assert clause is not None
        variant = next(v for v in clause.variants if v.when and "not_preserved" in v.when)
        assert variant.requires_narrative, "the auditor must be able to describe it"
        assert variant.severity is not None


class TestTheLetterheadPrintsOnce:
    """Word repeats a section header on every page. A letterhead is stationery:
    the firm's name belongs on the sheet the report starts on, and continuation
    sheets are plain."""

    @staticmethod
    def _render_a_long_report() -> Path:
        document = Document(id="auditors_report", title="Independent Auditor's Report")
        document.nodes.append(Heading(text="Independent Auditor's Report", level=1))
        for index in range(60):
            document.nodes.append(Para(text=f"Paragraph {index} — filler, to force several pages."))

        out = Path(tempfile.mkdtemp()) / "report.docx"
        docx_renderer.render(
            document,
            out,
            client_name="Sample Traders Private Limited",
            fy_code="2025-26",
            letterhead=docx_renderer.LetterheadBlock(
                name="Example & Co",
                subtitle="Chartered Accountants",
                lines=("New Delhi", "FRN 123456W"),
            ),
        )
        return out

    @staticmethod
    def _headers_by_type(path: Path) -> dict[str, str]:
        """Map each header TYPE — "first", "default", "even" — to its XML.

        Resolved through the relationship id rather than by part filename.
        `header1.xml` and `header2.xml` carry no meaning; which one Word uses
        for page one is decided by the reference in the section properties, and
        an earlier version of this test asserted only that the firm appeared in
        exactly ONE header part. That is equally true when the letterhead is on
        every page except the first, which is the opposite defect.
        """
        import re

        with zipfile.ZipFile(path) as archive:
            body = archive.read("word/document.xml").decode("utf-8", "replace")
            rels = archive.read("word/_rels/document.xml.rels").decode("utf-8", "replace")
            targets = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels))
            out: dict[str, str] = {}
            for kind, rid in re.findall(
                r'<w:headerReference[^>]*w:type="([^"]+)"[^>]*r:id="([^"]+)"', body
            ) + re.findall(r'<w:headerReference[^>]*r:id="([^"]+)"[^>]*w:type="([^"]+)"', body):
                # The two patterns differ only in attribute order; normalise.
                if kind.startswith("rId"):
                    kind, rid = rid, kind
                target = targets.get(rid)
                if target:
                    out[kind] = archive.read(f"word/{target}").decode("utf-8", "replace")
            return out

    def test_the_firm_is_on_the_first_page_header_and_nowhere_else(self) -> None:
        headers = self._headers_by_type(self._render_a_long_report())
        assert "first" in headers, "no first-page header was written"
        assert "Example" in headers["first"], "the letterhead is not on page one"
        for kind, xml in headers.items():
            if kind == "first":
                continue
            assert "Example" not in xml, f"the letterhead also repeats in the {kind!r} header"

    def test_a_document_with_no_letterhead_is_unaffected(self) -> None:
        document = Document(id="auditors_report", title="Independent Auditor's Report")
        document.nodes.append(Para(text="One paragraph."))
        out = Path(tempfile.mkdtemp()) / "plain.docx"
        docx_renderer.render(document, out, client_name="X", fy_code="2025-26")
        assert out.exists()


class TestNothingAdverseIsAsserted:
    """The team's fifth observation, generalised. Decision 69.

    `bdr.auditor.remarks` had a variant for a clean opinion and an
    unconditional fallback for everything else. "Everything else" included
    "nobody has said yet", so a Board's Report drafted before the opinion was
    decided told the directors their audit report was qualified.

    An adverse statement is the worst possible default: it is wrong about the
    client, and on the page it reads as deliberate.
    """

    OPINIONS = ("clean", "qualified", "adverse", "disclaimer")

    def _built(self, clause_set: ClauseSet, document: str, opinion: str):
        context = _context(opinion_type=opinion, going_concern="none")
        return build_document(
            clause_set,
            document,
            FY_END,
            responses={},
            context=context,
            applicable=frozenset(
                {
                    "full_board_report",
                    "caro",
                    "ifc",
                    "csr",
                    "cost_records",
                    "internal_audit",
                    "secretarial_audit",
                    "kam",
                    "cfs_required",
                    "s197",
                }
            ),
        )

    def test_an_undecided_engagement_asserts_no_exception_anywhere(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Swept over every document, not just the two that were wrong.

        With nothing answered and nothing decided, no clause may resolve to a
        variant marked `severity: exception` — that marking is the repository's
        own word for "this says something went wrong".
        """
        offenders = {}
        for document in production_clause_set.documents:
            built = self._built(production_clause_set, document, "")
            if built.exceptions:
                offenders[document] = list(built.exceptions)
        assert offenders == {}, f"asserted from an undecided engagement: {offenders}"

    def test_the_boards_comments_follow_the_opinion(self, production_clause_set: ClauseSet) -> None:
        clean = "have not made any qualification"
        modified = "contains a qualification"

        for opinion in self.OPINIONS:
            built = self._built(production_clause_set, "directors_report", opinion)
            text = " ".join(" ".join(built.document.text_nodes()).split())
            if opinion == "clean":
                assert clean in text and modified not in text
            else:
                assert modified in text and clean not in text, f"{opinion} read as clean"

    def test_an_unset_opinion_blocks_rather_than_guessing(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Neither paragraph prints, and both clauses are reported unanswered.

        Absent-and-blocked beats present-and-wrong: the workspace shows the
        question, and export waits.
        """
        built = self._built(production_clause_set, "directors_report", "")
        text = " ".join(" ".join(built.document.text_nodes()).split())
        assert "contains a qualification" not in text
        assert "have not made any qualification" not in text
        assert "bdr.auditor.remarks" in built.unanswered
        assert "bdr.auditor.report" in built.unanswered

    def test_no_clause_keeps_an_unconditional_adverse_fallback(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The shape itself, caught at the repository level.

        A variant with no `when` is the catch-all. A catch-all that is marked
        as an exception says something went wrong whenever nothing else
        matched — including when nothing is known.
        """
        offenders = []
        for clause in production_clause_set.clauses:
            conditional = [v for v in clause.variants if v.when]
            fallback = [v for v in clause.variants if v.when is None]
            if not conditional or not fallback:
                continue
            if fallback[0].severity is not None:
                offenders.append(clause.id)
        assert offenders == [], f"an exception is the catch-all in: {offenders}"
