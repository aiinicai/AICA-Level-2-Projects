"""What the production clause repository actually contains.

Separate from the machinery tests, which run against an authored fixture.
These assert the state of `content/`, which is now fully authored: every
clause in all six documents has wording and resolves for every option.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from app.clauses.model import CONTEXT_VARIABLES, ClauseSet
from app.clauses.resolve import resolve, unresolved_tokens

CONTENT = Path(__file__).resolve().parent.parent / "content"

FY = date(2026, 3, 31)

# Enough context to resolve any clause: every render-context name, present
# but empty. These tests are about wording, not about a particular
# engagement's values.
PROBE = dict.fromkeys(CONTEXT_VARIABLES, "")

# The same, with the engagement's own decisions made. Needed since 21 August
# 2026: two Board's Report clauses deliberately resolve to NOTHING until the
# opinion type is stated, rather than falling through to "the report contains a
# qualification" — see decision 69. An empty probe is the undecided case, and
# the undecided case is now supposed to be unresolvable.
DECIDED = {**PROBE, "opinion_type": "clean", "going_concern": "none", "framework": "igaap"}


def _is_authored(clause) -> bool:
    """A clause is authored once no variant still carries a marker."""
    return not any("AUTHORING REQUIRED" in v.body for v in clause.variants)


class TestCoverage:
    """§4 — the statutory coverage the build prompt requires."""

    def test_every_document_exists(self, production_clause_set: ClauseSet) -> None:
        """§4's six, plus the MGT-9 annexure the partner asked for on 20 Aug 2026."""
        assert set(production_clause_set.documents) == {
            "mgt9",
            "auditors_report",
            "caro_2020",
            "ifc_report",
            "mrl",
            "engagement_letter",
            "directors_report",
        }

    def test_caro_has_all_twenty_one_clauses(self, production_clause_set: ClauseSet) -> None:
        numbers = {
            c.number.split(")")[0] + ")"
            for c in production_clause_set.for_document("caro_2020", FY)
        }
        expected = {
            f"({n})"
            for n in [
                "i",
                "ii",
                "iii",
                "iv",
                "v",
                "vi",
                "vii",
                "viii",
                "ix",
                "x",
                "xi",
                "xii",
                "xiii",
                "xiv",
                "xv",
                "xvi",
                "xvii",
                "xviii",
                "xix",
                "xx",
                "xxi",
            ]
        }
        assert expected <= numbers, f"missing CARO clauses: {expected - numbers}"

    def test_caro_clauses_the_prototype_omitted_are_present(
        self, production_clause_set: ClauseSet
    ) -> None:
        # The HTML prototype had no (iv), (x), (xv), (xvi) or (xxi).
        for clause_id in ("caro.iv", "caro.x.a", "caro.x.b", "caro.xv", "caro.xvi.a", "caro.xxi"):
            assert clause_id in production_clause_set, clause_id

    def test_rule_11_has_no_clause_d(self, production_clause_set: ClauseSet) -> None:
        """§4.2, §19 — there is no Rule 11(d); it stands omitted.

        Checked by clause *id*, which carries the statutory letter. The
        rendered `number` follows the firm's own format, which lists Rule 11
        as (1)-(6) under section 143(3)(g) — so the two must be asserted
        separately or a renumbering could hide a missing clause.
        """
        auditors = production_clause_set.for_document("auditors_report", FY)
        rule11 = [c for c in auditors if c.id.startswith("rule11.") and c.id != "rule11.header"]
        letters = {c.id.removeprefix("rule11.") for c in rule11}
        assert "d" not in letters
        assert letters == {"a", "b", "c", "e", "f", "g"}

    def test_rule_11_renders_in_the_firms_numbering(self, production_clause_set: ClauseSet) -> None:
        auditors = production_clause_set.for_document("auditors_report", FY)
        rule11 = [c for c in auditors if c.id.startswith("rule11.") and c.id != "rule11.header"]
        # Contiguous (1)-(6), in order, with no gap where (d) would have been.
        assert [c.number for c in rule11] == ["(1)", "(2)", "(3)", "(4)", "(5)", "(6)"]

    def test_each_rule_11_clause_still_cites_its_statutory_letter(
        self, production_clause_set: ClauseSet
    ) -> None:
        """A reviewer checks the statute by reference, not by list position."""
        for letter in ("a", "b", "c", "e", "f", "g"):
            clause = production_clause_set.get(f"rule11.{letter}")
            assert f"Rule 11({letter})" in clause.clause_ref

    def test_the_mgt9_annexure_carries_why_it_is_not_required(
        self, production_clause_set: ClauseSet
    ) -> None:
        """MGT-9 is attached on instruction, not because a rule asks for it.

        Rule 12 omitted the extract by G.S.R. 159(E) dated 5 March 2021,
        including for a company with no website. The partner directed on
        20 Aug 2026 that it is attached anyway, which is theirs to decide --
        but the reason has to stay next to the text, so that whoever reads
        these files next does not take the annexure as evidence of a
        requirement that no longer exists.
        """
        ids = {c.id for c in production_clause_set.clauses}
        assert any(cid.startswith("mgt9.") for cid in ids)
        header = production_clause_set.get("mgt9.header")
        assert header is not None
        source = (CONTENT / "mgt9" / "mgt9_header.yaml").read_text(encoding="utf-8")
        assert "5 March 2021" in source
        assert "partner has directed" in source


class TestAuthoringState:
    """Phase 2 is complete and Gate A has been signed off.

    Every clause carries wording and every clause is now marked approved. The
    checks below guard what that approval must carry with it: attribution in
    the manifest, no half-authored clause, and no placeholder anywhere.
    """

    def test_a_cleared_review_flag_is_attributable(self, production_clause_set: ClauseSet) -> None:
        """Approved wording must say who approved it, when, and how.

        This replaced a test asserting that EVERY clause was still
        `needs_review`, which held while nothing had been signed off. Gate A
        has now happened, so the check inverts: a clause may be marked
        approved only if the manifest records the sign-off behind it.
        Otherwise 189 flags could be flipped by anyone, at any time, leaving
        no trace of who did it or on what basis.
        """
        manifest = production_clause_set.manifest
        approved = [c.id for c in production_clause_set.clauses if not c.needs_review]
        if not approved:
            return
        assert manifest.reviewed_on is not None, (
            f"{len(approved)} clauses are marked approved but manifest.yaml records "
            "no review date"
        )
        assert manifest.reviewed_by.strip(), "no reviewer recorded"
        assert manifest.review_method.strip(), (
            "no review method recorded — a blanket sign-off and a clause-by-clause "
            "reading must not leave identical traces"
        )

    def test_every_clause_is_either_authored_or_marked(
        self, production_clause_set: ClauseSet
    ) -> None:
        """No third state. A clause is finished, or it is visibly not."""
        for clause in production_clause_set.clauses:
            if clause.input is None:
                continue
            bodies = [
                resolve(clause, {**PROBE, "value": option.value}).body
                for option in clause.input.options
            ]
            marked = [b for b in bodies if "AUTHORING REQUIRED" in b]
            assert len(marked) in (0, len(bodies)), (
                f"{clause.id} is half-authored: {len(marked)} of {len(bodies)} "
                "variants still carry a marker"
            )

    def test_the_repository_is_fully_authored(self, production_clause_set: ClauseSet) -> None:
        """Phase 2 is complete: no clause still carries an authoring marker.

        This replaced a test which asserted that a skeleton still EXISTED, so
        that the §18.4 guard could be demonstrated against a real one. There
        are none left. The guard itself is now proved against a synthetic
        clause below, which is the honest way round — the proof should not
        depend on the repository staying unfinished.
        """
        unauthored = [c.id for c in production_clause_set.clauses if not _is_authored(c)]
        assert not unauthored, f"still carrying authoring markers: {unauthored}"

    def test_the_placeholder_guard_still_works(self) -> None:
        """§18.4's pre-export scan, proved against a clause built here.

        If this ever stops catching a marker, an unauthored clause could
        reach a signed document — which is the whole reason the marker
        convention exists.
        """
        from app.clauses.loader import clause_from_dict

        skeleton = clause_from_dict(
            {
                "id": "test.skeleton",
                "document": "caro_2020",
                "title": "Synthetic skeleton",
                "input": {
                    "key": "test.skeleton",
                    "datatype": "select",
                    "options": [{"value": "a"}, {"value": "b"}],
                },
                "variants": [
                    {"when": "value == 'a'", "body": "[AUTHORING REQUIRED — test.skeleton / a]"},
                    {"when": "value == 'b'", "body": "[AUTHORING REQUIRED — test.skeleton / b]"},
                ],
            }
        )
        for option in ("a", "b"):
            body = resolve(skeleton, {**PROBE, "value": option}).body
            assert unresolved_tokens(body), f"a marker for {option!r} would export silently"

    def test_authored_clauses_carry_no_placeholder_of_any_kind(
        self, production_clause_set: ClauseSet
    ) -> None:
        """An authored clause must be exportable, not merely marker-free."""
        for clause in production_clause_set.clauses:
            if clause.input is None or not _is_authored(clause):
                continue
            for option in clause.input.options:
                body = resolve(clause, {**PROBE, "value": option.value}).body
                assert not unresolved_tokens(body), f"{clause.id}/{option.value}: {body[:60]}"

    def test_the_gate_a_clauses_are_authored_first(self, production_clause_set: ClauseSet) -> None:
        """Protocol Gate A names these for spot-reading because the prototype
        got them wrong. They are the ones worth writing first."""
        gate_a = [
            "caro.viii",
            "caro.ix.a",
            "caro.ix.b",
            "caro.ix.c",
            "caro.ix.d",
            "caro.ix.e",
            "caro.ix.f",
            "caro.x.a",
            "caro.x.b",
            "caro.xi.a",
            "caro.xi.b",
            "caro.xi.c",
            "caro.xvi.a",
            "caro.xvi.b",
            "caro.xvi.c",
            "caro.xvi.d",
            "caro.xxi",
            "rule11.e",
            "rule11.f",
            "rule11.g",
        ]
        unwritten = [cid for cid in gate_a if not _is_authored(production_clause_set.get(cid))]
        assert not unwritten, f"Gate A clauses still unauthored: {unwritten}"

    def test_every_option_of_every_clause_resolves(self, production_clause_set: ClauseSet) -> None:
        """The real coverage check, now that Phase 2 is complete.

        Replaced `test_progress_is_measurable`, which asserted the repository
        was still unfinished. Every option of every clause must select a
        variant and produce a body with nothing left to substitute — an
        option that resolves to a placeholder, or to no variant at all, is a
        control the user can set that would break the document.

        Probed against a DECIDED engagement. Against an undecided one, two
        clauses are now meant not to resolve at all: falling through to a
        catch-all told the directors their audit report was qualified before
        anyone had said what the opinion was.
        """
        for clause in production_clause_set.clauses:
            options = [o.value for o in clause.input.options] if clause.input else [None]
            for option in options:
                resolved = resolve(clause, {**DECIDED, "value": option})
                assert resolved.body.strip(), f"{clause.id}/{option}: empty body"
                assert not unresolved_tokens(
                    resolved.body
                ), f"{clause.id}/{option}: {unresolved_tokens(resolved.body)}"


class TestRulesFileIsNotDuplicated:
    """The fixture repository carries a copy of the applicability rules.

    Two copies can drift, and a drifted threshold is exactly the silent
    failure the rules file exists to prevent — so they must stay identical.
    """

    def test_the_fixture_rules_match_production(self) -> None:
        from tests.conftest import CONTENT_DIR, PRODUCTION_CONTENT

        production = (PRODUCTION_CONTENT / "applicability_rules.yaml").read_text(encoding="utf-8")
        fixture = (CONTENT_DIR / "applicability_rules.yaml").read_text(encoding="utf-8")
        assert production == fixture, (
            "tests/fixtures/content/applicability_rules.yaml has drifted from "
            "content/applicability_rules.yaml — copy the production file over it"
        )


class TestGateADecisions:
    """Decisions the partner has taken, pinned so they cannot drift.

    `docs/GATE_A_DECISIONS.md` records what was decided. A record in prose
    and wording in YAML can diverge without anyone noticing, so each decision
    that can be expressed as a check is checked here.
    """

    # The only legitimate use of the pre-2017 phrase: the ICAI publication's
    # own title, cited verbatim wherever it is named.
    GUIDANCE_NOTE = "guidance note on audit of internal financial controls over financial reporting"

    def test_the_ifc_phrase_is_the_post_2017_one(self, production_clause_set: ClauseSet) -> None:
        """Decision 1, 16 August 2026 — "with reference to financial statements".

        Section 143(3)(i) said "over financial reporting" until the Companies
        (Amendment) Act, 2017 replaced it. The firm's own Annexure B still
        uses the old phrase throughout and its report format used one in each
        branch, so this had to be settled before Gate A.
        """
        offenders: list[str] = []
        for clause in production_clause_set.clauses:
            for variant in clause.variants:
                body = variant.body.lower()
                # Remove the Guidance Note's title before looking, so citing
                # it does not read as a use of the old statutory phrase.
                stripped = body.replace(self.GUIDANCE_NOTE, "")
                if "over financial reporting" in stripped:
                    offenders.append(clause.id)
        assert not offenders, (
            "these clauses use the pre-2017 phrase 'over financial reporting' "
            f"outside the Guidance Note's title: {sorted(set(offenders))}"
        )

    def test_the_three_documents_that_must_agree_all_use_it(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The phrase spans the report paragraph, Annexure B and the letter.

        Matched loosely enough to allow the annexure's heading form, "with
        reference to **the aforesaid** financial statements", which is how
        the heading is properly worded.
        """
        pattern = re.compile(r"with reference to (the aforesaid )?financial statements")
        for clause_id in ("iar.143.3.i", "ifc.title", "ifc.scope", "eng.ifc.scope"):
            clause = production_clause_set.get(clause_id)
            bodies = " ".join(v.body.lower() for v in clause.variants)
            assert pattern.search(bodies), clause_id

    def test_audit_trail_starts_with_fy_2023_24(self, production_clause_set: ClauseSet) -> None:
        """Decision 2, 16 August 2026 — commencement fixed at 1 April 2023.

        Stated as a year COMMENCEMENT; `effective_from` is compared against
        the FY END. A year commencing 01-04-2023 ends 31-03-2024. Anyone
        "correcting" the stored date to 2023-04-01 would pull the clause into
        FY 2022-23, where it must not appear — so both ends are asserted.
        """
        for clause_id in ("rule11.g", "mrl.audit.trail"):
            clause = production_clause_set.get(clause_id)
            assert clause.effective_from == date(2024, 3, 31), clause_id
            assert clause.in_force(date(2024, 3, 31)) is True, clause_id
            assert clause.in_force(date(2023, 3, 31)) is False, clause_id

    def test_the_two_audit_trail_clauses_move_together(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The report and the representation letter must cover the same years."""
        assert (
            production_clause_set.get("rule11.g").effective_from
            == production_clause_set.get("mrl.audit.trail").effective_from
        )

    def test_maternity_cites_rule_8_5_xiii_and_its_commencement(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Decision 3 of 16 August 2026, superseded on 20 August 2026.

        That decision stripped the rule number and the commencement year,
        because the citation then in the file collided with Rule 8(5)(xi),
        which the register gives to the IBC disclosure — and two requirements
        cannot share a sub-clause. The reasoning was sound; the conclusion was
        too cautious. The maternity statement is Rule 8(5)(**xiii**), inserted
        by G.S.R. 357(E) dated 30 May 2025 and effective 14 July 2025, which
        collides with nothing. The partner confirmed the sub-clause and quoted
        its text.

        The commencement date matters as much as the number: without it the
        clause would print in an FY 2024-25 report, where the requirement did
        not yet exist.
        """
        clause = production_clause_set.get("bdr.maternity")
        assert clause.effective_from == date(2025, 7, 14)
        assert "8(5)(xiii)" in clause.clause_ref
        # The collision that prompted the original decision must stay absent.
        assert "8(5)(xi)" in production_clause_set.get("bdr.ibc").clause_ref
        assert "8(5)(xii)" in production_clause_set.get("bdr.otsettlement").clause_ref

    def test_the_branch_paragraph_asks_nothing_and_never_prints(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Decision 26, 17 August 2026 — supersedes decision 4.

        This test asserted the opposite until today: that the clause kept its
        question, because s.143(3)(c) is not optional where a branch is audited
        under s.143(8) by another auditor. The partner has directed that the
        question go and the paragraph never print. Reversed here rather than
        deleted, so the reversal is visible in the test that pinned it.

        The clause must still exist — the decision stays next to the statute,
        and the auto:alpha lettering closes up over it — and must omit whatever
        it is asked.
        """
        clause = production_clause_set.get("iar.143.3.c")
        assert clause.input is None, "the question is back"
        assert len(clause.variants) == 1
        assert resolve(clause, {**PROBE, "value": None}).variant.omit is True

    def test_the_adverse_observations_express_negative_is_gone(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Decision 5, 16 August 2026 — never print the nil case.

        The express-negative option was removed rather than left unselected:
        an option nobody should choose is one that can be chosen by accident.
        """
        clause = production_clause_set.get("iar.143.3.f")
        assert clause.input is not None
        assert {o.value for o in clause.input.options} == {"none", "exist"}
        assert resolve(clause, {**PROBE, "value": "none"}).variant.omit is True

    def test_the_engagement_letter_speaks_as_we(self, production_clause_set: ClauseSet) -> None:
        """Decision 13, 16 August 2026 — "we" throughout, not "I / we"."""
        offenders = [
            c.id
            for c in production_clause_set.clauses
            if c.document == "engagement_letter"
            and any(re.search(r"\bI / we\b|\bmy / our\b", v.body, re.I) for v in c.variants)
        ]
        assert not offenders, f"ICAI's 'I / we' form survives in: {offenders}"
