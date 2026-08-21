"""The repository must contain every clause the signed-off register approved.

The register is the scope the partner approved. The repository is what the
tool will actually print. Nothing was checking that the second covers the
first, and it did not: `scripts/scaffold_clauses.py` carries a hand-written
clause table rather than reading the register, and 36 approved rows were
never transcribed into it — the whole body of the auditor's report, most of
the IFC annexure, and every signature block.

That is the failure mode this file exists to stop. A missing clause is
invisible in a rendered preview: the document simply reads as though the
paragraph was never meant to be there.

`docs/clause_register_approved.csv` is the approved register exported to a
diffable form and checked in beside the code. Regenerate it only from a
register the partner has signed off.
"""

from __future__ import annotations

import csv
from pathlib import Path

from app.clauses.model import ClauseSet

REGISTER = Path(__file__).resolve().parent.parent / "docs" / "clause_register_approved.csv"

# The register's document names are prose; the repository's are identifiers.
DOCUMENT_IDS: dict[str, str] = {
    "Independent Auditor's Report": "auditors_report",
    "CARO 2020": "caro_2020",
    "IFC Annexure (s.143(3)(i))": "ifc_report",
    "Board's Report": "directors_report",
    "Management Representation Letter": "mrl",
    "Engagement Letter": "engagement_letter",
    "Annexure A - MGT-9": "mgt9",
}

# Deliberate divergences from the register. Each one is a decision taken
# after the register was approved, and each needs the partner to confirm it
# at Gate A — an entry here is a question, not a resolution.
RENAMED: dict[str, tuple[str, ...]] = {
    # The firm letters Rule 11 as a numbered list (1)-(6) under its own
    # paragraph (g). Ids keep the statutory letter, so `iar.r11.a` became
    # `rule11.a`.
    "iar.r11.a": ("rule11.a",),
    "iar.r11.b": ("rule11.b",),
    "iar.r11.c": ("rule11.c",),
    "iar.r11.f": ("rule11.f",),
    "iar.r11.g": ("rule11.g",),
    # Rule 11(e) has three limbs. The register gave each its own row; they
    # are one clause rendering three paragraphs, because the auditor answers
    # them together and the middle limb cannot be true while the first is
    # not addressed.
    "iar.r11.e.i": ("rule11.e",),
    "iar.r11.e.ii": ("rule11.e",),
    "iar.r11.e.iii": ("rule11.e",),
    # CARO (iii)(a) is split into (A) loans and (B) guarantees in the firm's
    # own annexure, which follows the 2020 Order.
    "caro.iii.a": ("caro.iii.a.A", "caro.iii.a.B"),
}

# Approved, then deliberately dropped.
WITHDRAWN: dict[str, str] = {
    # SA 700's title element. The document title already comes from
    # `manifest.yaml`, which is content, and `build_document` emits it as the
    # level-1 heading — a separate title clause printed it a second time.
    "iar.title": "document title comes from manifest.yaml, not a clause",
    # Rule 11(d) was the specified bank notes disclosure. It was relevant
    # only to FY 2016-17 and stands omitted; §19 names the prototype's
    # phantom (d) as a defect not to repeat.
    "iar.r11.d": "Rule 11(d) omitted — SBN disclosure, FY 2016-17 only",
}

# Approved as withdrawn, then reinstated by the partner, knowing why it was
# withdrawn. Kept as a named list rather than quietly deleted, because the
# register is the record of what the firm decided and a reversal is part of it.
REINSTATED: dict[str, str] = {
    # Rule 12 omitted the MGT-9 extract by G.S.R. 159(E) dated 5 March 2021,
    # including for a company with no website -- the 2020 amendment had made it
    # conditional on disclosing the web link, and the 2021 amendment removed it
    # outright. The partner was shown that and directed on 20 Aug 2026 that the
    # annexure is attached by default anyway. Nothing prevents a company giving
    # more than the rules require.
    "bdr.mgt9": "reinstated 20 Aug 2026 as a voluntary attachment",
}


def _register_rows() -> list[dict[str, str]]:
    with REGISTER.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class TestRegisterIsHonoured:
    def test_the_export_is_present(self) -> None:
        assert REGISTER.exists(), f"approved register export missing: {REGISTER}"

    def test_every_register_row_was_approved(self) -> None:
        """The export is only meaningful if it is the signed-off version."""
        unapproved = [
            row["Clause ID"]
            for row in _register_rows()
            if row["Firm review status"].strip().lower() != "approved"
        ]
        assert not unapproved, f"register export contains unapproved rows: {unapproved}"

    def test_every_approved_clause_exists_in_the_repository(
        self, production_clause_set: ClauseSet
    ) -> None:
        present = {c.id for c in production_clause_set.clauses}
        missing: list[str] = []
        for row in _register_rows():
            clause_id = row["Clause ID"]
            if clause_id in WITHDRAWN:
                continue
            expected = RENAMED.get(clause_id, (clause_id,))
            if not any(candidate in present for candidate in expected):
                missing.append(f"{clause_id} ({row['Document']}: {row['Title'][:44]})")
        assert not missing, (
            f"{len(missing)} approved clauses are absent from the repository, so the "
            "documents cannot print them:\n  " + "\n  ".join(missing)
        )

    def test_the_repository_adds_nothing_unapproved(self, production_clause_set: ClauseSet) -> None:
        """Scope runs both ways: a clause nobody approved must not print either."""
        approved = {row["Clause ID"] for row in _register_rows()}
        for renamed in RENAMED.values():
            approved.update(renamed)
        # `rule11.header` is the paragraph the Rule 11 list hangs from. The
        # register's `iar.r11.*` rows have no parent row, so the numbered
        # list would have printed with nothing introducing it.
        approved.add("rule11.header")
        # The sentence identifying the financial statements audited, split
        # out of `iar.opinion.body` — see content/auditors_report/
        # iar_opinion_scope.yaml for why.
        approved.add("iar.opinion.scope")
        # The Board's Report addressee and presenting sentence, the transfer
        # to the Investor Education and Protection Fund, and the closing
        # acknowledgement. All three are in the firm's own precedent and none
        # has a register row — see content/directors_report/.
        approved.update({"bdr.opening", "bdr.iepf", "bdr.acknowledgement"})
        # The paragraph naming the statutory auditors and their eligibility
        # under s.141. Added on the partner's instruction of 20 Aug 2026: the
        # Board's Report had no such paragraph, and the register -- built from
        # the firm's precedent -- had no row for one either.
        approved.add("bdr.statutory.auditors")
        # The statement of what the auditors concluded, and the engagement
        # letter naming SA 210 as the Standard it is written under. Both from
        # the firm's precedent, on their instruction of 20 Aug 2026; neither
        # has a register row for the same reason the three above do not.
        approved.update({"bdr.auditor.report", "eng.sa210"})
        # The MGT-9 annexure, reinstated on the partner's instruction. See
        # REINSTATED above for why it was withdrawn and on what basis it is
        # back; the register row carries the same note.
        approved.update(
            {c for c in {x.id for x in production_clause_set.clauses} if c.startswith("mgt9.")}
        )
        approved.add("bdr.mgt9")
        # The CARO signature block, on the firm's team's observation of
        # 21 Aug 2026. CARO 2020 is an annexure to the auditor's report and is
        # signed with it; the register was built clause by clause from the
        # Order's own paragraphs, which is why it has rows for 3(i) to 3(xxi)
        # and none for the signature beneath them.
        approved.add("caro.sig")
        # The CARO 3(iii) chapeau question, on the firm's instruction of
        # 21 Aug 2026. A working question that prints nothing -- the register
        # has rows for paragraphs, and this is not one.
        approved.add("caro.iii.investments")
        extra = sorted({c.id for c in production_clause_set.clauses} - approved)
        assert not extra, f"clauses not in the approved register: {extra}"

    def test_withdrawn_clauses_are_absent(self, production_clause_set: ClauseSet) -> None:
        present = {c.id for c in production_clause_set.clauses}
        for clause_id, why in WITHDRAWN.items():
            assert clause_id not in present, f"{clause_id} should be withdrawn: {why}"

    def test_documents_match_the_register(self, production_clause_set: ClauseSet) -> None:
        expected = {DOCUMENT_IDS[row["Document"]] for row in _register_rows()}
        assert expected == set(production_clause_set.documents)
