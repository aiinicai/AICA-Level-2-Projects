# Methodology

How the system was built, the decisions taken along the way, and the reasoning behind them.

---

## Phase 1 — Audit of the reference implementation

The starting point was `Tax_Audit_Applicability_Dashboard_TRS.html`: a single 1,100-line
file, HTML, CSS and JavaScript together.

### What it did well

- The legal logic was sound in structure: cash tests gating the threshold, presumptive
  ceilings, a low-profit limb gated on prior-year opt-in.
- It already distinguished the base and enhanced turnover limits correctly.
- It already had a one-page print sheet.
- The reasoning steps were written in real professional language, not template filler.

### What limited it

| # | Finding |
| --- | --- |
| A-01 | Thresholds hard-coded throughout the calculation. No way to verify them as a set, no way to handle a second Assessment Year. |
| A-02 | Due dates hard-coded as literal 2026 strings inside the calculation. |
| A-03 | Binary result only. No way to express "cannot conclude on this information". |
| A-04 | Presumptive eligibility and prior-year history were checkboxes. Unchecked silently meant "no" — and on the lock-in limb that is the difference between audit and no audit. |
| A-05 | No input validation. Cash receipts could exceed total receipts and still produce a confident verdict. |
| A-06 | A nil denominator produced a 0% cash ratio, silently granting the enhanced threshold. |
| A-07 | All logic in one 170-line `calc()` function that also wrote to the DOM. Untestable. |
| A-08 | No statutory references beyond section numbers in prose. |
| A-09 | Conditions outside the model (derivatives, commission, aggregation) were mentioned in a footnote and had no effect on the output. |
| A-10 | Print sheet only; no Word output, no audit trail, no export gating. |
| A-11 | The `NOT APPLICABLE` narrative reasoned from absence: "no trigger was found" rather than "each limb was tested and is satisfied". |
| A-12 | Single visual mode. |

### Retained

The legal logic, unchanged, including its interpretive choices — because silently changing
a legal reading during a rebuild would have been the wrong call. Where a reading is
arguable it is flagged (L-01, L-02) rather than altered.

### Rebuilt

Everything else: architecture, result model, validation, statutory references, documents,
design system, output channels.

---

## Phase 2 — Design decisions

> Phases 1–5 are the original build record. **D-02, D-03 and D-04 were superseded in Phase 6**: the legal basis was verified, and the REVIEW REQUIRED outcome and "not known" answers were replaced by explicit questions that always lead to a decision. Phase 4's 48 assertions became 83.

### D-01 — One file for the law

Every threshold, rate and date in `ruleset.js`, keyed by Assessment Year, carrying its own
verification metadata. Verification becomes checking a short list against the bare Act
instead of auditing a codebase.

### D-02 — Unverified until signed off

The application shows an UNVERIFIED banner on screen and on every export until a CA
completes the verification block. It cannot be dismissed from the UI.

Numbers carried over from an earlier implementation are not verified numbers. A tool that
presents them as though they were is doing the opposite of its job.

### D-03 — Three results, not two

REVIEW REQUIRED is a first-class outcome. A tool that always produces a verdict trains its
user to trust it in exactly the cases where it should not be trusted.

### D-04 — Tri-state questions

`yes` / `no` / `unknown`. A checkbox cannot express "I have not checked yet", and on the
lock-in limb that distinction decides the answer.

### D-05 — Test records, not booleans

Every limb returns its evidence. The reasoning, matrix, references, working paper and audit
trail all render from the same records. No second copy of the logic, so no channel can
disagree with another.

### D-06 — No statutory text from memory

Reference cards render an explicit "not reproduced" state. Text that reads authoritative and
is subtly wrong is worse than a visible gap.

### D-07 — Special conditions are surfaced, never absorbed

Ticking a condition outside the model produces a review point, and several force REVIEW
REQUIRED. The reference implementation listed them in a footnote with no effect.

### D-08 — Non-applicability reasoned positively

The NOT APPLICABLE narrative states each limb examined and why it is satisfied, including
limbs that did not arise and conditions that failed without being decisive. A working paper
that says only "not applicable" evidences nothing.

### D-09 — Export gated on completeness

Working paper generation is blocked while mandatory inputs are missing. The buttons disable
and the reason is shown, rather than producing a document with gaps in it.

### D-10 — The print document is a separate design

Not the screen with colours stripped. A4 grid, hairline rules instead of cards, near-black
text, colour only for status, explicit page-break control. The executive sheet is composed
independently rather than being the detailed paper with sections hidden — a one-page budget
has to be met by deciding what earns its place.

### D-11 — Dark mode designed, not inverted

Surfaces step **up** in lightness with elevation, the opposite of the light theme. Borders
carry structure because shadow is nearly invisible on dark ground. Accents desaturated to
hold meaning without glowing.

### D-12 — No run-time AI

The engine is deterministic. AI was a development tool, not a run-time dependency. A legal
determination that varies between runs is not a determination, and client figures never
leave the machine.

### D-13 — No build step

Plain classic scripts, so `app/index.html` opens by double-clicking. A tool a CA cannot open
without a toolchain will not be used.

---

## Phase 3 — Implementation

Four layers, strictly ordered: parameters → arithmetic → legal rules → presentation. See
[`decision-engine.md`](decision-engine.md).

Design system built first, as tokens. Three themes defined as three token sets, so no
component file contains a literal colour.

---

## Phase 4 — Testing

48 assertions across sample cases, boundaries, form determination and visual modes. All
pass. Every numeric threshold is tested at the limit, one above and one below. Full report:
[`qa-test-report.md`](qa-test-report.md).

Two defects were found and fixed during testing:

- The executive PDF ran to two pages. Fixed by composing it as its own document.
- Horizontal overflow at 390 px. Fixed with a responsive navigation rail.

Expectations were derived from the provisions, not by running the engine and recording what
it did. A fixture written from the code cannot detect a bug in the code.

---

## Phase 5 — Documentation

Nine documents, a prompt library of eight, four legal notes and a verification record. The
verification record is the load-bearing one: it is what converts an unverified tool into a
usable one.

---

## What was deliberately not built

| Not built | Why |
| --- | --- |
| Login, database, server | Client-side only keeps figures on the machine. Nothing here needs a server. |
| Run-time AI | Determinism and confidentiality. |
| Section 44AA evaluation | A second parameter set to verify for no shared logic. Deferred openly rather than guessed. |
| Multi-year comparison | Out of scope; would need verified parameters for each year. |
| A "fix" for L-01 | An interpretive question belongs to the CA, not to a rebuild. |

---

## Honest assessment

**Strong:** the architecture, the refusal to conclude on insufficient facts, the
documentation of what it cannot do, the separation of statutory text from interpretation
from application, test coverage of the boundaries.

**Weak:** the legal parameters are unverified, so the system cannot be used on live files
today. Two interpretive questions are open. Statutory text is absent. One Assessment Year is
configured.

None of these is a coding gap. They are all the same thing: **the parts that require a
Chartered Accountant have been left for the Chartered Accountant**, and marked so they
cannot be overlooked.

---

## Phase 6 — Legal verification and correction (18 September 2026)

Prompted by the question *"is this in accordance with the Income-tax Act, 1961 for FY 2025-26?"*,
every parameter was checked against primary sources:

- the **Finance Act 2023** Gazette text (ss. 15, 16, 17);
- the **Finance (No. 2) Act 2024** and **Finance Act 2025**, searched in full — no amendment to
  ss. 44AB, 44AD or 44ADA;
- the **Income Tax Department e-filing portal** — the 1961 Act governs FY 2025-26; s. 44ADA is
  not open to an HUF.

The check found eight errors in the engine as first built (listed in `legal/sources.md` §5).
Two — the s. 44AB(d) prior-year condition and the unmodelled s. 44AD(4) bar — could have
produced a wrong "not applicable". All eight are corrected, each with a regression test.

At the same time the interaction model changed. The first version could end with
**REVIEW REQUIRED — could not be concluded**, which in practice left the user stuck. It now
asks each fact the law turns on as an explicit question, marks the fields that are needed,
and takes the user straight to them. Once the answers are in, a definite result follows.

The lesson recorded for the Capstone: **AI accelerated the build; checking the statute made it
correct.** The two are not substitutes.
