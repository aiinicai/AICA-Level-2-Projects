# Gate decisions taken by the signing partner

Decisions 1 to 14 are Gate A (clause wording), 15 is Gate B (rendered
documents), 16 to 19 are Gate C (carry-forward rollover), 20 to 22 concern the
interface, 23 the applicability thresholds, **24 to 27 remove questions from the
auditor's report** — including one that supersedes decision 4 — **28 is the
firm-wide master answer sheet**, **29 to 33 are the five interface changes of
17 August**, and **34 to 41 are the usability review of the same day**. Each entry records what was asked, what was
decided, the date, and which files carry the consequence.

Gate A's questions came from `gate_a_pack/QUESTIONS.md`; Gate C's came from a
live roll-forward.

Decisions 1 to 13 each settle the point they name and nothing else. Decision
14 is the sign-off itself: on 16 August 2026 the partner directed that all
189 clauses be treated as reviewed, and `needs_review` was cleared across the
repository.

**That sign-off was a blanket instruction, not a clause-by-clause reading.**
It is recorded as such here and in the `review:` block of
`content/manifest.yaml`, because a cleared flag looks identical either way.

---

## 1. Statutory phrase for internal financial controls reporting

**Decided 16 August 2026.**

**Question.** Section 143(3)(i) said "internal financial controls **over
financial reporting**" until the Companies (Amendment) Act, 2017 replaced it
with "internal financial controls **with reference to financial
statements**". The firm's own Annexure B uses the older phrase throughout,
and its report format uses the newer phrase in the exempt case and the older
one in the applicable case — so the two branches contradicted each other.

**Decision.** Use **"with reference to financial statements"**.

**Effect.** No wording changed: the clauses were already authored in that
form, and this confirms the reading rather than altering it. The phrase is
now consistent across the auditor's report paragraph, Annexure B and the
engagement letter.

**One deliberate exception.** The ICAI's *Guidance Note on Audit of Internal
Financial Controls Over Financial Reporting* keeps "Over Financial
Reporting" in its own title, and is cited verbatim wherever it is named.
That is the name of the document, not a statutory test, and it is the only
place the older phrase appears. Three occurrences in Annexure B, all of them
that citation.

**Clause files affected:**

- `content/auditors_report/iar_143_3_i.yaml`
- `content/engagement_letter/eng_ifc_scope.yaml`
- all eleven clauses in `content/ifc_report/`

**Still open on the same clauses:** the wording of the modified and
disclaimed IFC opinions, which are authored because the precedent is a
clean-opinion file. (The separate-criteria-paragraph question that stood here
was settled by decision 10.)

---

## 2. Audit trail reporting — first applicable financial year

**Decided 16 August 2026.**

**Question.** Rule 11(g) audit trail reporting was deferred twice and Build
Prompt v2 gives no effective date. I had derived financial years commencing
on or after 1 April 2023 but could not source it.

**Decision.** **1 April 2023**, fixed. Financial years commencing on or after
that date.

**Effect.** No change — the derivation was right. Both `rule11.g` and
`mrl.audit.trail` keep `effective_from: 2024-03-31`.

**Read that date carefully before changing it.** The decision is stated as a
year *commencement*; `effective_from` is compared against the engagement's FY
*end*. A year commencing 01-04-2023 ends 31-03-2024. The two are the same
rule from opposite ends. Setting `2023-04-01` would pull the clause into FY
2022-23, where it must not appear.

**Clause files:** `content/auditors_report/rule11_g.yaml`,
`content/mrl/mrl_audit_trail.yaml`. They move together.
Pinned by `TestGateADecisions`.

---

## 3. Maternity Benefit Act statement — citation and commencement

**Decided 16 August 2026.**

**Question.** Which Rule 8(5) sub-clause the statement sits under, and the
year it first applies. I had cited Rule 8(5)(xi), which collides with the
Insolvency and Bankruptcy Code disclosure.

**Decision.** **Cite no rule number and no commencement year.**

**Effect.** `clause_ref` names the Maternity Benefit Act, 1961 alone.
`effective_from` is now null.

**Consequence, accepted.** With no commencement date the statement prints in
the Board's Report for every year the tool generates, including a year before
the requirement existed. The exposure is small — a Board's Report is prepared
for one year at a time and is not regenerated for comparatives the way an
auditor's report is — but it is a deliberate choice. Do not add a date back
without asking.

**Clause file:** `content/directors_report/bdr_maternity.yaml`.

---

## 4. Branch audited by another auditor — keep or remove the paragraph

> **SUPERSEDED on 17 August 2026 by decision 26.** The partner has since
> directed that the question be removed and the paragraph never printed. The
> reasoning below is left as written, unamended, because it is the reasoning
> the partner overruled and it states what the tool can no longer do.

**Decided 16 August 2026.** The partner directed that the standard case is a
company with no branch and no branch auditor, and left the call to me.

**Decision. The clause stays.** Nothing about the standard case changes: the
first option is "no branch offices", it omits, and the paragraph does not
print. A clean report is lettered (a) to (h), exactly as the firm's precedent
is.

**Why.** Section 143(3)(c) is not optional when the facts arise. Where a
branch is audited under section 143(8) by someone other than the company's
auditor, the report must state that the branch auditor's report was sent and
how it was dealt with. Deleting the clause would leave the tool unable to
produce a lawful report for such a company, and would leave whoever met that
case editing a signed document by hand — the failure mode this tool exists to
remove. Keeping it costs one dropdown that already defaults correctly.

**Clause file:** `content/auditors_report/iar_143_3_c.yaml`.

---

## 5. Adverse-effect observations — never print the nil case

**Decided 16 August 2026.**

**Decision.** **Never print.** The nil case produces no paragraph.

**Effect.** The express-negative option ("there are no such observations") has
been **removed from the clause**, not merely left unselected — an option
nobody is to choose is one that can be chosen by accident. Two options
remain: nothing to report, which prints nothing; and observations exist,
which prints them and demands a narrative.

**Clause file:** `content/auditors_report/iar_143_3_f.yaml`.

---

## 6. Addressee and the first heading — keep them separate

**Decided 16 August 2026.** The firm's format runs them on one line; SA 700
treats them as separate elements. **The split stands.**

**Clause file:** `content/auditors_report/iar_addressee.yaml`.

---

## 7. Emphasis of Matter is not for qualifications — acknowledged

**Decided 16 August 2026.** The firm's template carries the instruction line
"Emphasis of Matter (if there are any qualifications or other remarks)". An
Emphasis of Matter is the opposite case: SA 706 para 7 covers a matter
*appropriately* presented that is fundamental to understanding, whereas a
qualification is a matter *not* appropriately dealt with and belongs in the
Basis for Qualified Opinion.

**The partner acknowledged the point.** The instruction line is not
reproduced. **The firm's own template still carries it and should be
corrected separately — this tool cannot do that for it.**

**Clause file:** `content/auditors_report/iar_eom.yaml`.

---

## 8. CARO scope paragraph in the engagement letter — keep it

**Decided 16 August 2026.** Neither ICAI source has a CARO or Rule 11 scope
paragraph; I added one because a letter setting out the scope of the
engagement without naming mandatory reporting understates it. **Kept.**

**Clause file:** `content/engagement_letter/eng_caro_scope.yaml`.

---

## 9. Position of the financial statements identification — unchanged

**Decided 16 August 2026.** ICAI puts the "statements which comprise…"
sentence in the opening paragraph; the approved register places it at order
50, after both responsibilities sections. **The register's order stands.**

**Clause file:** `content/engagement_letter/eng_framework.yaml`.

---

## 10. IFC control criteria — inline, no separate paragraph

**Decided 16 August 2026.** The criteria are named inline in the management
responsibility paragraph and again in the opinion, as the firm's annexure
does. **No separate criteria paragraph is printed** — that is the clause's
default and it stays.

**Clause file:** `content/ifc_report/ifc_criteria_ref.yaml`.

---

## 11. Who signs the management representation letter

**Decided 16 August 2026.** The firm's precedent is signed "Director /
Authorized Signatory", unnamed. **Confirmed: a named Director and the Chief
Financial Officer**, drawn from the client's director and KMP registers, as
SA 580 para 9 requires.

**Clause file:** `content/mrl/mrl_sig.yaml`.

---

## 12. Engagement letter date in the MRL — omitted

**Decided 16 August 2026.** The firm's precedent cites the engagement letter
by date. **The date is omitted**; no field was added to the engagement and no
migration was made. The letter refers to "the terms of the audit engagement
letter" without a date.

**Clause file:** `content/mrl/mrl_header.yaml`.

---

## 13. Engagement letter voice — "we"

**Decided 16 August 2026.** Both ICAI sources are written "I / we" so that a
sole practitioner and a firm can share the template. **"We" throughout**,
representing the team of auditors. All 21 engagement letter clauses use it.

**Clause files:** all of `content/engagement_letter/`.

---

## 14. Gate A sign-off

**16 August 2026.** The partner directed that all 189 clauses be treated as
reviewed. `needs_review` is cleared across the repository and
`template_version` is `1.0.0-approved`.

**How this was actually done is recorded in `content/manifest.yaml`**, in a
`review:` block giving the date, the reviewer and the method. It says, in
terms, that this was a **blanket sign-off on the partner's instruction and
not a clause-by-clause reading**, which is what the Review and Sign-Off
Protocol contemplates.

That distinction is recorded rather than smoothed over for a plain reason: a
cleared flag looks identical either way, and these clauses go into documents
that get signed and filed. Anyone later asking what "approved" meant here is
entitled to the answer.

The thirteen substantive questions above **were** answered individually
before this sign-off. What was not done is a reading of the prose of all 189
clauses. The pack in `gate_a_pack/` remains the way to do that, and doing it
later costs nothing but time.

`test_repository_state.py::test_a_cleared_review_flag_is_attributable`
enforces the record: clauses may be marked approved only while the manifest
says who approved them, when, and how.

---

# Gate B — rendered documents

## 15. Gate B approved

**17 August 2026.** The partner approved Gate B on the pack in
`gate_a_pack/` — six documents across six scenarios, plus PROVENANCE.md and
QUESTIONS.md.

As with Gate A, this is recorded as it happened rather than as the protocol
describes it: the approval was given without a defect list coming back. The
pack is regenerated by `python scripts/gate_a_pack.py` and remains available
if anything needs re-reading.

---

# Gate C — carry-forward rollover

Four questions were put to the partner on 17 August 2026 after a live
roll-forward of FY 2025-26 into FY 2026-27.

## 16. Stale financial figures on roll-forward — clear them

**Decided 17 August 2026.**

**Problem.** Roll-forward pinned the previous year's `client_profile` row, so
the new engagement decided CARO, IFC, CSR, internal audit and secretarial
audit applicability from last year's turnover, capital and borrowings. The
What Changed screen reported those figures as "Same", which was true and
misleading — the same row, not a figure anyone had confirmed for the new year.

**Decision. Blank the financials.** Roll-forward now opens a new profile
version with `paid_up_capital`, `turnover`, `borrowings`, `net_worth`,
`net_profit`, `reserves` and `deposits` cleared. Company name, address, type
and framework carry over; those describe the company and rarely move.

**Consequence, intended.** Until this year's figures are entered, a small
private company reads as CARO-exempt and the annexure is reported as not
applicable rather than printed. That is the point: no document is issued on
applicability computed from numbers belonging to the year before.

**Implementation.** `app/routers/rollover.py::_profile_for_new_year`, using
the existing SCD-2 writer so the prior year keeps its own pinned row (§18.6).
Rolling forward twice does not stack empty versions. Pinned by
`tests/test_carryforward.py::TestRollForwardClearsStaleFinancials`.

## 17. Source year need not be finalised

**Decided 17 August 2026.** Roll-forward may be run from an engagement still
in data collection, so next year's planning can begin before this year's
report is signed. **No change — this was already the behaviour.**

## 18. Engagement letter — always reissue

**Decided 17 August 2026.** A fresh engagement letter is issued every year;
the tool does not offer "confirm the existing terms".

**Already satisfied, with a caveat worth knowing.** Engagement letter answers
are not carried forward, so each new year's letter starts blank. That is
because `DOCUMENT_CATEGORIES` in `app/routers/rollover.py` lists only the
auditor's report and the CARO annexure — **the MRL, IFC annexure, engagement
letter and Board's Report carry nothing forward at all.** For the engagement
letter that matches this decision. For the MRL and the Board's Report it is
probably not what anyone intended, and it has not been changed here because
no decision was taken on it.

## 19. Every carried-forward answer must be confirmed

**Decided 17 August 2026.** All carried-forward answers arrive unconfirmed and
block export until reviewed, including nil ones — §6.2's distinction between
"same as last year" and "verified for this year" holds for every answer.
**No change — this was already the behaviour.**

---

# Interface gaps reported from use

## 20. Several CA firms in one installation, no login

**Decided 17 August 2026.** The partner asked for multiple CA firms. Because
there is no authentication (the single-user decision), this was put back with
its consequence stated:

> With no login, anyone who opens the application can see every firm's
> clients, engagements and audit files.

**The partner chose it knowing that.** Recorded here because it is a
confidentiality decision, not a user-interface preference, and because the
alternative offered — one installation per firm — carried no such cost.

**Built as a working filter, never as a boundary.** The active firm is a cookie
that scopes the client register and the dashboard. A client belonging to another
firm remains reachable by its own URL, which
`tests/test_multi_firm.py::test_switching_is_not_access_control` asserts on
purpose so that a later reader cannot mistake the picker for a permission
system. The admin page says so in as many words.

If this ever needs to be a real boundary, the single-user decision has to be
reopened first: it means user accounts, passwords, sessions and roles, and the
change log begins attributing actions again.

## 21. New client form captures everything at once

**Decided 17 August 2026.** One long form — master data, financials, directors
and KMP together — rather than a minimal record edited afterwards.

The cost was flagged when the choice was offered: a validation failure in a
form that long would throw away everything typed. That is mitigated rather than
accepted. Every value comes back on a refusal, including the repeated director
and KMP rows, and `tests/test_new_client.py` asserts it.

## 22. Partners are retired, never deleted

**Decided by me, 17 August 2026, and open to reversal.** The partner asked for
partner management; how removal should work was not specified.

There is no delete. A partner named on a document already issued must stay
findable — deleting the row would leave the audit trail pointing at nothing —
so leaving the firm sets `active = False`, and `signing_partners` excludes them
from the signature block. If a partner recorded in error needs to be removed
outright, that should be a separate, explicit action.

---

## 23. Applicability thresholds confirmed

**17 August 2026.** All ten rules in `content/applicability_rules.yaml` are
confirmed and `needs_review` is cleared on each.

**How the confirmation was given, recorded as it happened.** I offered to set
the thresholds out with their statutory basis so they could be read before
being signed off. The partner answered "Confirmed" without waiting for that
list. The values were then read back in crore in the same exchange, so they
were seen — but after the confirmation, not before it.

This is the same pattern as decision 14, and is noted for the same reason: a
cleared flag looks identical whether or not anyone read what it was hiding.

**Why these ten matter more than the wording.** A wrong threshold does not
produce a wrongly worded document. It produces a document that should never
have been generated, or omits one that should have been, and nothing in the
tool will flag it. The clause text at least gets read by whoever signs the
report; these numbers never appear on the page.

**Two that were specifically drawn to the partner's attention:**

- CARO's private exemption is **"not exceeding" (<=)**; the IFC exemption is
  strictly **"less than" (<)**. A company with turnover of exactly Rs 50 crore
  is NOT IFC-exempt. Pinned by
  `test_the_caro_and_ifc_tests_are_not_the_same_comparison`.
- **Secretarial audit reaches private companies** at borrowings of Rs 100
  crore or more, by the 2020 amendment. Pinned by
  `test_secretarial_audit_reaches_private_companies`.

**Test changed deliberately.** `test_every_rule_is_flagged_needs_review`
asserted that nothing had been confirmed and could not survive this. It is
replaced by `test_a_confirmed_threshold_still_states_its_authority`: a
threshold may be presented as settled only while it names the provision it
comes from, because a number with no citation is a number nobody can check.

The fixture copy at `tests/fixtures/content/applicability_rules.yaml` was
updated in step — `TestRulesFileIsNotDuplicated` caught the drift immediately,
which is what it is for.

---

## 24. Every dropdown opens on the clean answer

**Decided 17 August 2026.** "Please set all dropdown as default clean report."

**Decision.** Every clause lists its nil answer first and the workspace
preselects it, across all six documents. The "— not answered —" option is still
there, below, so a field can be put back to unanswered deliberately.

**A default is not an answer.** Nothing is stored until the field is saved, so
a preselected dropdown does not satisfy §18.4's export block and does not count
towards readiness. Pinned by `test_a_default_is_not_a_stored_answer` — if
preselecting ever started writing rows, an untouched engagement would look
complete and export.

**Defect reported by the user the same day, and fixed.** Those two halves were
right separately and unusable together. The workspace autosaves on `change`,
and an untouched dropdown never fires one — so 106 fields showed the right
answer, stored nothing, went on blocking export, and gave no reason on screen.
The report was "even after saving the answer with dropdown boxes, still showing
findings blocking export"; saving was in fact working.

Two changes, neither of which weakens the rule above:

- A dropdown whose answer is not stored is **marked "not saved"** on the page.
  Only dropdowns — an empty textarea already looks empty, and marking every
  unanswered field put a border on 93 fields out of 98 and said nothing.
- **"Accept the N clean defaults in this document"** stores them in one act:
  `POST /engagements/{id}/accept-defaults` → `accept_clean_defaults`. It is
  something the auditor does, not something a page load does on their behalf,
  so the answers are attributed, logged and reviewed. It never overwrites an
  existing answer, including an unconfirmed carry-forward. Scoped to the
  document on screen: accepting a clean auditor's report says nothing about the
  Board's Report.

Verified end to end on the demo engagement: 106 blocking findings to 1, and
readiness to 100%. **The one that remained is the consistency engine working
correctly** — the clean-first default for `iar.143.3.i` enables the Annexure B
cross-reference on a company that is IFC-exempt. Accepting defaults can produce
a combination that is individually clean and jointly wrong; that check is what
catches it, and it names the contradiction in full.

---

## 25. Agreement with the books, and section 133 compliance — hard-coded

**Decided 17 August 2026.** "Always assume it is in agreement with financial
statements in all circumstances." "Always complied."

**Decision.** `iar.143.3.d` and `iar.143.3.e` no longer ask anything. Each
prints the compliant wording, still keyed on the reporting framework so an
Ind AS company names the two extra statements and the right rule. Pinned by
`test_they_still_follow_the_reporting_framework`.

**Also decided in the same instruction.** Key Audit Matters prints only where
SA 701 applies. The workspace had been asking for KAM on every engagement and
the preview printed the section, because the document was built with no
applicability filter at all — `clause.requires` was parsed and never read.

---

## 26. Sections 143(3)(a), (b), (c), (g) and (h) — questions removed

**Decided 17 August 2026**, superseding decision 4.

| Clause | Instruction | Effect |
|---|---|---|
| `iar.143.3.a` | Assume information and explanations sought and obtained | Prints the clean wording |
| `iar.143.3.b` | Assume there is no branch | Prints "proper books kept", branch-returns limb gone |
| `iar.143.3.c` | No branch, no paragraph required | **Never prints** |
| `iar.143.3.g` | Assume no director disqualified; remove the explanation too | Prints the clean wording |
| `iar.143.3.h` | Remove it and its explanation | **Never prints** |

**What the tool can no longer report.** Each of these is a statutory reporting
obligation that arises on the facts, and the facts can no longer be recorded:

- **143(3)(a)** — the *effect* on the financial statements of information not
  obtained.
- **143(3)(b)** — that proper returns were received from branches not visited,
  and equally that proper books were **not** kept.
- **143(3)(c)** — that a branch auditor's report under section 143(8) was
  received and how it was dealt with. **This is the point I made when the
  partner first delegated the call, and it has not changed:** a company with a
  branch audited by another auditor cannot be reported on by this tool.
- **143(3)(g)** — the naming of a disqualified director.
- **143(3)(h)** — any qualification or adverse remark on the maintenance of
  accounts.

Where one of those arises, the report has to be written outside AuditCraft.
Nothing in the tool will notice or warn.

**Reversible without re-authoring.** Every removed variant is preserved as a
comment at the foot of its own clause file, together with the instruction that
removed it and the consequence. Restoring a question means uncommenting the
variants and the input block — not writing the statutory wording again.

**The clauses were kept rather than deleted**, for two reasons. The decision
stays visible next to the statute it concerns; and the section 143(3) lettering
is positional (`auto:alpha`), so the letters close up over an omitted clause on
their own. A clean report now letters **(a) to (g)** rather than (a) to (h).
`test_the_section_143_3_lettering_closes_up_over_them` asserts the run is
contiguous from (a) with no gap or repeat — it was verified to fail when a
letter was hard-coded, which is the mistake it exists to catch.

**Two questions remain in the group**, deliberately: `iar.143.3.f`
(observations having an adverse effect on the functioning of the company) and
`iar.143.3.i` (adequacy and operating effectiveness of internal financial
controls). Both are auditor judgements on every file and neither was withdrawn.
`test_only_the_two_intended_section_143_3_questions_remain` pins the list, so a
question reappearing anywhere in the group fails rather than arriving as a
dropdown nobody meant to ask.

---

## 27. The tool is for private limited companies only

**Decided 17 August 2026.** "This utility is for private limited companies only
and assume it as always not applicable" — of section 197(16).

**Decision.** `iar.197.16` asks nothing and always states that the section 197
limit on managerial remuneration does not apply, the Company being a private
limited company.

**This narrows what the tool may be used for, and should be read against
decision 20.** That decision made the installation usable by any CA firm, with
no fixed firm name. This one fixes the *client* side: the paragraph is true of
a private company and **false of a public one**. If a public company is ever set
up here, this paragraph will be wrong and nothing will flag it — the clause was
never gated by the `s197` applicability flag, the question was what stood in for
that check, and the question is now gone.

The `s197` flag still governs `bdr.employees.remuneration` in the Board's
Report, which is unaffected.

**If the firm ever audits a public company**, the three removed variants are
commented at the foot of `content/auditors_report/iar_197_16.yaml`, and the note
there says what has to come back with them.

---

## How these seven instructions were given, and what that is worth

Decisions 24 to 27 removed **eleven** questions from the auditor's report in a
single sitting. They were given as a list, in the partner's own words, each one
naming the clause by the label the workspace shows — so what was being removed
was identified precisely, unlike the blanket sign-offs recorded in decisions 14
and 23.

What was **not** put to the partner beforehand is the loss of reporting
capability set out under decision 26. It was raised once, at the time, and the
instruction was repeated. It is recorded here rather than in a commit message
because the person affected by it is whoever next audits a company with a
branch, a disqualified director, or books that were not properly kept.

---

## 28. A firm-wide master answer sheet, overridable per engagement

**Decided 17 August 2026.** "A one-time configuration sheet where the user can
select the required answers for all the dropdown fields... these answers should
become the default responses... if any user wants to modify a particular
response, they should be able to open the relevant dropdown in the utility,
change the answer, and save."

**Where it is.** **Admin → Default Answers** (`/admin/defaults`). Every dropdown
in all six documents on one page — **119 of them**: 13 in the auditor's report,
49 in CARO, 3 in Annexure B, 20 in the MRL, 4 in the engagement letter, 30 in the
Board's Report. Grouped by document, nothing preselected.

**Three answers the partner gave when asked:**

| Question | Answer |
|---|---|
| A screen, an Excel round-trip, or both? | **A screen**, applicable to all clients, not re-uploaded per client |
| Which engagements does an edit affect? | **New engagements only** |
| Should an engagement nobody opened be exportable? | **Yes — defaults count as answered** |

### How it works, and why it is built this way

**The default is copied onto the engagement, not read through it.** An
engagement's answers are its own `engagement_response` rows, written when the
year is opened and marked `ResponseSource.DEFAULT`. So editing the master sheet
cannot reach a file already in progress — an audit file must not shift because
someone edited a settings screen — and every answer behind a signed report is
recorded against that report rather than inferred from settings as they stand
later.

**Overriding is just answering.** Change the dropdown in the engagement's
workspace and save. The row becomes `USER`, and the firm's sheet is untouched:
one client's facts must never become the house position, so there is no
write-back.

**Carried-forward answers beat the sheet.** On a roll-forward the defaults fill
only what carry-forward did not. Last year's answer for *this* client is better
evidence than the firm's general position, and it is the one decision 19 asks the
auditor to confirm.

**Firm-scoped, not global.** Two practices sharing an installation keep separate
sheets. `field_default` is keyed on `(firm_id, field_key)`.

**A default whose option was withdrawn is reported, not deleted.** Eleven
questions left the auditor's report the same day this was built. A firm that
answered one deliberately is told the question changed; the record survives and
is ignored when applied.

### What this changes about the export gate — read this before relying on it

**An answer taken from the sheet counts as answered.** That is the instruction,
and it is what makes a clean file finalisable without repeating 119 selections.
The consequence, accepted: **an engagement nobody has opened reads 100% ready and
can be exported** on the strength of the standing answers alone. Readiness no
longer distinguishes "the firm's standing answer" from "someone examined this
client's file".

`source` still does, and it is the only thing that does. The audit log and the
change history separate the two; the percentage on the workspace does not.
`test_an_applied_default_counts_as_answered` asserts the consequence rather than
hiding it.

Verified end to end: a first-year engagement opened after the sheet was filled
arrived with **119 answers, all `DEFAULT`, readiness 100%, no dropdown showing
"not saved"**, and two blocking findings — both genuine cross-checks, not empty
fields. A roll-forward arrived with 34 carried forward and 85 from the sheet, and
**zero `mandatory_empty` findings**, which was the point.

### A missing route this exposed, now built

**A client created at Clients → New client had no financial year and no way to be
given one.** The only path to a new engagement was rolling an existing one
forward, so a brand-new client was a dead end reading "No financial years yet" —
and decision 28 was unreachable for the case that matters most, a new client's
first year. `POST /clients/{id}/engagements` and the **Open a financial year**
form on the client's Financial Years tab close it, applying the firm's defaults
as the year opens.

Pinned by `tests/test_default_answers.py` (17 tests) and migration
`4f2b8e1c9a37`.

---

## 29. The two review states are removed

**Decided 17 August 2026.** "The statuses Data Pending Review and Partner
Pending Review are not relevant. The user who prepares the form will be
responsible for finalising it."

**Decision.** `MANAGER_REVIEW` and `PARTNER_REVIEW` are gone from
`EngagementStatus`. The workflow is now:

> Not started → Data collection → **Prepared** → Approved → Finalised → Archived

Returning a file for correction still works, from Prepared.

**The gates they carried did NOT go with them.** Blocking findings used to stop
the move into manager review, and open comments stopped approval. Both checks
now sit on the single move to **Approved**. Removing a reviewer is a decision
about who works on the file; it is not a decision to let an incomplete file
through, and deleting both checks along with the states was the easy mistake
here. `test_the_gates_they_carried_did_not_go_with_them` pins it.

The dashboard's two review tiles become one, **"Prepared, awaiting approval"**,
and the Excel pack's "pending" sheet now means prepared-but-not-approved.

---

## 30. One IFC question, in the IFC section

**Decided 17 August 2026.** "In the IFC section, ask a single question whether
the IFC report is applicable, and prepare it automatically where applicable."

**Decision.** The IFC section of the workspace opens with one control:
*Is the Internal Financial Controls report applicable?* — decide from the
figures / **Yes, prepare Annexure B** / **No, do not prepare it**. Answering Yes
produces the full annexure and puts the matching s.143(3)(i) paragraph in the
auditor's report.

**It writes the applicability override, not an answer.** That is the whole
design of it. Annexure B, the auditor's report paragraph and the engagement
letter's scope all read one flag, so answering the question here moves all three
together. A separate answer row would have let the report say IFC applies while
the annexure stayed empty — which is exactly the state the partner found the
tool in, and what prompted this. Overruling the computed answer is logged with a
reason naming this control, so a reviewer can tell a decision from a threshold.

---

## 31. Delete a client's data for one financial year

**Decided 17 August 2026.** Clients → the client → **Financial Years**, one row
per year, each with a delete control. Removes that year's answers, tables,
generated documents, comments and history. The **client is untouched** — other
years, profile versions and the director register all survive.

**The FY code has to be typed to confirm.** This cannot be undone, and a bare
button beside a list of years is one misclick from a year's work.

**A finalised or archived year cannot be deleted at all**, and shows no control
rather than one that always fails. Documents have been issued from it and its
snapshots are what make a reprint byte-identical; destroying that leaves a
signed report with nothing behind it. Corrections there go through Create
Revision, which is what §18.7 exists for.

The tables to clear are **discovered from the schema**, not listed by hand — ten
child tables were missing from a hand-written list as recently as this week.

---

## 32. Draft export on the firm's letterhead, during data collection

**Decided 17 August 2026.** "In Data Collection Mode, provide an option to
export the preview file along with the firm's letterhead."

**Decision.** Every document in the workspace has *Download this preview on the
firm's letterhead (.docx)*. The header carries the firm's logo, name,
"Chartered Accountants", address and FRN — all from Admin → Firm & Partners,
nothing hard-coded.

**It bypasses the export gate on purpose, so it is stamped.** Unanswered fields
and unresolved placeholders print exactly as they stand, because that is what
there is to look at. Every page carries **"DRAFT FOR DISCUSSION — NOT AN ISSUED
DOCUMENT"** in the body, not as a watermark: a draft on firm letterhead is
indistinguishable from a signed report once it is on a desk, and that stamp is
the only thing preventing it.

**Nothing is frozen, hashed, versioned or registered.** A draft is not an issued
document: it never appears in the document register or the audit pack, and it
does not consume a version number. It is written to a scratch folder, outside
the client's documents directory, and overwritten each time.

A document with no content — every clause ruled out by applicability — is
refused rather than exported blank.

---

## 33. AuditCraft and the firm, on the first page

**Decided 17 August 2026.** The dashboard opens with a masthead: the firm's logo
where one is uploaded, **AuditCraft** and its description, then the firm's name,
"Chartered Accountants" and FRN.

Read from the firm record, never written into the template — decision 20 made
the installation usable by any practice, and a hard-coded name would undo that.
With no firm set up it links to Admin → Firm & Partners instead; with a firm but
no logo it says where to add one.

---

## 34. One question decides a whole document — CARO as well as IFC

**Decided 17 August 2026.** "In the CARO section, first ask a single question
whether CARO reporting is applicable. Where it is not, the related inputs and
sections should be hidden."

**Decision.** The IFC control of decision 30 is now **general**. A document
whose every clause requires the same single flag gets one question at the top of
its section: *Does CARO 2020 reporting apply to this company?* /
*Is the Internal Financial Controls report applicable?*

**Derived, not listed.** `governing_flag()` asks the repository: CARO's 51
clauses all require `caro`, Annexure B's 11 all require `ifc`, and nothing else
qualifies — the auditor's report has one gated clause out of 34, so it is not
governed by anything and offers no question. A document that later stops being
wholly gated stops being asked about, without a code change.

**A defect this exposed.** Answering "CARO does not apply" first hid only **49
of 96** fields. A narrative is catalogued as `<clause id>.narrative`, not under
the clause's input key, so filtering on input keys alone left every explanation
box on screen for a document the engine had ruled out. The same trap recorded in
`field_states` from the other direction. Now 96 of 96.

---

## 35. The client profile asks only what is used

**Decided 17 August 2026.** "Remove all irrelevant inputs... capture only
information actually required."

**Six questions removed** — corporate address, phone, email, industry, nature of
business, and "amounts in". No clause interpolated them, the applicability
engine did not read them, and no document printed them. They were asked once and
never used again. **The columns are left in place**: only the questions are
gone, so a firm that filled them in has not lost anything.

`website` stays — the Board's Report cites the annual-return web address under
s.134(3)(a), the paragraph that replaced Form MGT-9.

**Nine questions ADDED, which is the more serious half.** The applicability
engine reads nine facts that **no screen could set**: subsidiary/holding of a
public company, has subsidiary / associate / joint venture, the three limbs of
the Rule 6 consolidation exemption, and whether the company is in a cost-records
industry. Every one defaulted silently to False or NULL, so consolidation, cost
records, s.197 and secretarial audit were decided from answers nobody had been
asked. The mirror image of the financial figures being uneditable, and found the
same way — by comparing what reads a column against what writes it.

`test_every_fact_the_engine_reads_can_be_set` sweeps `facts_from_profile`
against the form, so a threshold that starts reading a new column fails there
rather than defaulting quietly.

---

## 36. A five-step workflow bar

**Decided 17 August 2026.** Client profile → Data collection → Review → Reports
→ Finalisation, with the current step marked, on every workspace screen.

Five steps rather than the eight statuses behind them: "Prepared" and "Approved"
are one thing to a person finishing a file, and a progress bar that names
database states is a progress bar nobody reads. `done` means the file has passed
a step — not that everything in it was answered, which is what readiness and the
section markers are for.

---

## 37. Not started / In progress / Completed, per section

**Decided 17 August 2026.** Every document in the switcher carries its state and,
on hover, its counts — "In progress — 3 of 29 answered". A document the engine
has ruled out reads **Not applicable**.

**Derived from the file, never stored.** A stored "this section is done" flag is
a second source of truth that drifts the moment an answer changes, and what it
would drift about is whether a document can be signed. The state is computed
from the same gated field set the form uses, passed in rather than recomputed, so
the marker and the questions can never disagree.

Colour is never the only signal: the state is written out and repeated in the
link's title.

---

## 38. Quick actions on the dashboard

**Decided 17 August 2026.** Create new client, Continue audit, Carry forward
previous year, View previous year, Preview report, Finalise audit, Export data.

Every one of these already existed and was reachable only from inside something
else. "Continue audit" in particular — the commonest thing anyone does here —
was three clicks deep. It points at the most recently touched engagement that is
still open; a finalised one is not something to continue, and offering it would
be a dead action. `test_every_quick_action_points_somewhere_real` follows each
link, because this codebase has already shipped one dead link and one page
reachable only by typing its address.

---

## 39. The preview shows the letterhead

**Decided 17 August 2026.** "Provide a proper report preview before
finalisation, showing exactly how the final document will look."

Both preview surfaces — the standalone preview and the workspace pane — now open
with the firm's letterhead: logo, name, "Chartered Accountants", address and FRN,
the same header the .docx carries. Fixing one and not the other is exactly how
this class of defect has survived here before, so the test checks both.

**It does not invent a page count.** A browser cannot know where the .docx page
breaks fall, so instead of a simulated "Page 1 of 4" the foot of the preview
states that page numbering, headers and footers are applied by Word on export. A
preview that lied about the one thing it exists to show would be worse than no
preview.

---

## 40. Guidance beside technical questions

**Decided 17 August 2026.** An information icon on every clause question and on
each of the nine new group-structure facts.

**The guidance is what the tool knows, not a restatement of the statute**: the
provision the question comes from, whether it blocks export, and what happens to
the answer on roll-forward. Writing a plain-language explanation of Indian law
next to the box is the same risk the whole clause repository exists to control,
and a tooltip is exactly where nobody would check it. Where a real explanation is
needed it belongs in the clause file, where Gate A can read it.

---

## 41. Consistent branding and a cleaner interface

**Decided 17 August 2026.** The sidebar carries the AuditCraft mark and the
firm's logo on every screen — it is the one element present on all of them. A
single type scale, one shape for every form control, one button style, and the
document pane set at a readable measure rather than full width.

There is no login page to brand: decision 20 made this a single-user local
application with no authentication.

---

## Already built, confirmed rather than rebuilt

**Carry-forward of previous-year data** was asked for in the same list and has
been in place since Gate C (decisions 16 to 19): the roll-forward screen chooses
what to bring across per document, What Changed compares the two years, and every
carried answer arrives unconfirmed and blocks export until reviewed. What was
missing was not the feature but the way in, which decision 38 supplies.

---

## 42. The stylesheet is fingerprinted

**Found 17 August 2026**, from a screenshot of the dashboard rendering with the
new markup and none of its rules: the firm logo at its full 800-pixel height,
the quick actions as a run of underlined links, the masthead as plain text.

**Nothing was broken.** `app.css` was served under a fixed name, so a browser
that had held the page open across the day's changes kept its cached copy — new
HTML, old stylesheet. It survives an ordinary reload, and it looks identical to
a failed deploy.

`app/templating.py::asset_url` now stamps an eight-character hash of the file's
**content** onto `app.css` and `workspace.js`, so a change is a new URL and the
cache cannot serve the old one. Content rather than modification time: a file
restored from a backup keeps its identity, and two machines serving the same
bytes agree.

`build_templates()` registers it as a Jinja global — every router uses that
instead of constructing its own environment, or `asset_url` is undefined there.
The vendored HTMX and Alpine files need none of this: their version is already
in the filename.

Telling someone to hard-refresh is not a fix. It moves the failure to the next
person who does not.

---

## 43. No tool stamp on the document

**Decided 19 August 2026.** "Do not mention on the output footer that it is
generated by the AuditCraft tool."

Every export carried, at its foot:

> Generated by AuditCraft · Template 1.0.0-approved · 19-Aug-2026 09:20 UTC

**Removed from both renderers.** A statutory report is issued over the firm's
name, the signing partner's membership number and a UDIN; the software that
typeset it is not a party to it and has no business on the page. The document
now ends where it should — with the signature block.

Removed from the HTML preview as well, not only the .docx: the preview exists to
show what will be signed, so a version marker printed inside it would be the one
thing on the page the exported document does not carry.

**Nothing is lost from the audit trail.** The template version, the generation
timestamp, the actor and the SHA-256 of the content all live on the
`document_instance` row — which is what §18.7 rebuilds a reprint from, and what
makes that reprint byte-identical. They were never load-bearing on the page. The
template version is still shown in the page **chrome** above the preview, where
it describes the file rather than forming part of it.

**Two tests were inverted, not deleted.** `test_the_template_version_is_stamped`
and `test_template_version_stamped` asserted the stamp was present. They now
assert its absence, under names that say so, so the reversal is visible in the
tests that pinned the old behaviour.

What stays on the page: the firm's letterhead, the client and financial year in
the footer, Word's "Page X of Y", and — on a draft only — the "DRAFT FOR
DISCUSSION — NOT AN ISSUED DOCUMENT" banner.

---

## 44. Every engagement screen is reachable from the workspace

**Reported 19 August 2026.** "I am not able to trace the Finalise audit option
whereas readiness is showing 100%."

**The file was ready and there was nothing on the page to press.** Finalise lives
on the Review screen, and the only link to it anywhere in the application was
the dashboard's quick action — which points at whichever engagement was touched
last, not the one open. From inside an engagement, its own **Applicability**,
**What Changed**, **roll forward** and **Review** screens could be reached only
by typing the address.

The workspace now carries a nav bar to all four, with **Review & finalise** as
the primary action.

**This had already happened once, to the workspace itself**, and the sweep
written then could not catch it a second time: it asserted that the workspace
was linked, which is a fact about the previous bug rather than a property.

The replacement is a property, with the routes discovered from the application's
own OpenAPI schema so a screen added later cannot be orphaned quietly:

> **A screen that answers must be reachable by clicking.**

Stated that way rather than "every screen is linked", because What Changed
correctly 404s on a first year — there is no prior year to compare against — and
linking it unconditionally would only move the fault to the dead-link sweep.
Asking the application which screens work for the engagement under test keeps
both halves honest with no list to maintain.

---

## 45. Each document goes out on the right party's letterhead

**Reported 19 August 2026.** "The MRL should be on the company's letterhead."

Correct, and it was wrong on **two** documents, not one:

| Document | Letterhead | Why |
|---|---|---|
| Independent Auditor's Report | Firm | The firm's own report |
| Annexure A — CARO 2020 | Firm | Part of that report |
| Annexure B — IFC | Firm | Part of that report |
| Engagement letter | Firm | The firm writes it to the client |
| **Management Representation Letter** | **Company** | Written BY the company TO the auditor |
| **Board's Report** | **Company** | Issued by the directors under s.134 |

The firm's letterhead on a representation letter makes the auditor appear to
have written the client's own representations. On a Board's Report it puts the
auditor's name on a document the auditor is not a party to.

**Declared in the manifest, not in code.** `issued_by: firm | company` sits
beside the document's title, because it is a fact about the instrument — and
because a document added later should have to state whose paper it is rather
than silently inheriting the firm's. An unrecognised value is **rejected at
load**: defaulting a typo to the firm would reintroduce exactly this bug,
silently.

A company letterhead carries the company name, registered address and **CIN**,
with no "Chartered Accountants" subtitle and no logo — the tool holds no client
artwork. Labelling a company's CIN "FRN" is the sort of detail that survives
review because nobody reads a letterhead twice, so a test asserts it.

The preview and the .docx are built by **one function**, `letterhead_for`. A
preview showing one party's letterhead while the export carries another would
defeat the purpose of previewing.

---

## 46. The firm's name never actually reached any document

**Found while fixing decision 45**, when the firm's letterhead came off the MRL
and there was nothing underneath it.

`render_context_for` took `firm` and `partner` as optional arguments and **not
one of its four call sites passed either**. `firm_name`, `firm_frn`,
`firm_address`, `partner_name` and `partner_mno` were empty strings in **every
document the tool has ever produced** — the auditor's report signed by nobody,
and the representation letter addressed to a blank line above "Chartered
Accountants".

It stayed invisible because the clause bodies carry the labels. A signature
block reading "Membership No:" with nothing after it looks like a template
waiting to be filled, not a defect.

`signing_context` now fills both, and a sweep asserts that **no module outside
`render_context.py` calls `render_context_for` directly** — a list of four fixed
call sites is how this survived four call sites.

**The firm is resolved from the CLIENT, not the active-firm cookie.** For one
turn they disagreed and the auditor's report carried one firm's letterhead above
another firm's signature block. A cookie chooses what the person at the screen is
looking at; it does not decide whose name goes on a report.

**Where a firm has several signing partners**, the first active one is used.
Choosing between them is properly an engagement-level decision and is not
modelled — this fills the block rather than leaving it blank, and the partner is
named on screen before anything is signed.

---

## 47. Three defects reported by the firm's team, 19 August 2026

Five observations, in a workbook. Four were defects; one is a content question
still open.

### A nil answer demanded a table anyway (their points 1, 2 and 4)

Every repeating block carried `min_rows: 1` with **no condition**, so answering
"None" printed the correct nil paragraph *and* still blocked export with "the
table needs at least one row". **Twelve of fourteen blocks were unguarded** —
only `rule11.a` and `caro.vii.b` had ever had the rule applied.

It reached far past the Board's Report: a clean audit could not export without
inventing Key Audit Matters, IFC deficiencies and uncorrected misstatements that
did not exist. A colleague worked around it by typing the nil sentence into the
**Name of the party** column, producing a document that said the right thing in
the wrong place with a stray `0` beside it.

**The nil wording already existed and was already approved.** Nothing was
authored here; the guard makes wording the partner had signed off reachable.

Eight clauses gained a guard. Four keep `min_rows: 1` because the table *is* the
disclosure: `bdr.financial.summary`, `bdr.board.meetings`,
`bdr.employees.remuneration` and `iar.kam`.

A nil Board's Report went from **31 blocking findings to 5**, and the five left
are real work — financial summary, board meetings, forex particulars, and two
narratives.

### The two mechanisms could contradict each other

`repeating_block.when` decides whether the workspace **offers** a table;
`variant.render_block` decides whether the document **prints** one, and
`min_rows` is enforced from the second. Two mechanisms, one question.

The loader now refuses a combination where an answer prints a table the guard
hides — which would demand a row that no screen offers. **It caught a real one
the moment it was added**: Form AOC-2 has a part for contracts *at* arm's length
as well as not, so `bdr.rpt.188` needed `value != 'none'`, not
`value == 'not_arms_length'` as first written.

### A required figure on a narrative row (their point 3)

`bdr.conservation` demanded a **Current year** amount. Rule 8(3) has three limbs
and only foreign exchange earnings and outgo carries figures — conservation of
energy and technology absorption are prose. Both amount columns are now
optional.

**No guard on this clause, deliberately.** Both answers print a table: the
not-applicable wording still ends "The foreign exchange earned and used during
the year is set out below:", so hiding the table there would leave a lead-in
sentence with nothing under it.

### 31 findings and nothing to fill (their point 5)

`field_catalog` is what turns a clause into a question, and it was built only by
`scripts/seed.py` — a script nobody runs on a copy of the application. Their
catalogue predated the Board's Report clauses, so the document knew every clause
was unanswered and no control rendered anywhere.

Reproduced exactly by emptying the catalogue for one document: **0 fields, 32
findings.**

The sync now happens in the application's own startup, so it runs however the
application is launched. It had been wired into the packaged launcher alone,
which would have left everyone running from source still broken.

Orphaned fields are pruned only where nothing has answered them: a foreign key
protects an answered field, so deleting one fails outright and would stop the
application opening — and an answer on a live engagement is evidence, not
litter.

**Tests were writing to the real database.** `SessionLocal` bound to
`data/auditcraft.db`, and startup now uses it, so every test run would have
touched the developer's own data. `conftest` points it at a per-process
temporary file.

### Still open — a content question for the partner

Should conservation of energy, technology absorption and foreign exchange be
**one table or three clauses**, two narrative and one with figures? That is how
the Rule is structured, and it is a presentation decision, not a defect.

---

## 48. The interface, rebuilt as one system

**Asked 19 August 2026**, against a reference layout the partner supplied:
"I want UI like this or better. It should feel like software from a reputed
firm."

### What the reference does better, and was adopted

A **page header** on every screen — small uppercase eyebrow, serif title, one
line of explanation, and the two actions people arrive to perform on the right.
Leading with a sentence rather than a logo band is the single biggest
improvement; the dashboard now opens "Statutory audit documentation, prepared
once."

A **serif display face** for titles against a sans UI. It is most of what makes
software look considered rather than assembled. **§1 forbids fetching a webfont
and shipping one raises a licence question nobody has answered**, so the display
face is the serif already on every Windows machine.

**Cards with real containment** — hairline, 10px radius, a shadow soft enough to
read as paper rather than a button. And **rows you can open**, with an initials
avatar, title and one line beneath, instead of a bare table.

Documents as **cards carrying their own state**, which the workspace had as a
row of pills.

### What the reference does worse, and was not copied

- Every document card in it reads **"Ready to review"** while seven responses
  are outstanding. That status is decorative. Ours is computed from the answers
  and says Not started / In progress / Completed / Not applicable.
- Every field is labelled **"Carried forward — confirm for this year"**,
  including on a first-year file where nothing was carried. If everything is
  flagged, nothing is.
- **Finalise is enabled** beside "7 responses outstanding". Ours refuses.
- Its CARO list runs (i), (ii), (iii), **(v)** — clause (iv) is missing. That is
  the prototype defect Build Prompt v2 exists to prevent.

Copying the visual craft was right. Copying the information design would have
undone a fortnight of correctness work.

### The stylesheet is now one system

It had grown by appending a block per feature for a week: a button was styled in
four places, three type scales were in use, and nothing shared a spacing rhythm.
Rewritten as tokens, then layout, then components — 1236 lines of accumulation
to a system with a single scale. The document surface and the §8.8 print rules
were carried over untouched.

### The measured problem, which was not visual at all

The clause workspace put **1514 pixels of furniture above the first question**.
On CARO an auditor scrolled nearly two screens before answering anything.

| | Before | After |
|---|---|---|
| To the first question | 1514px | **692px** |
| Engagement details | 567px, always open | 50px, collapsed with its values in the summary |
| Document switcher | 236px of wrapped statutory titles | 166px of short-named cards |
| Applicability question | 227px | 98px |
| Workflow bar and links | inside the 480px column | full-width header above both panes |

**Documents now carry a short name**, declared in the manifest beside the full
title: "Annexure A — CARO 2020" rather than "Annexure A to the Independent
Auditor's Report — CARO 2020". In the manifest and not in a template, because an
abbreviation of a statutory instrument is content, and content does not belong
in markup.

The engagement details collapse to a summary that still shows the values —
"clean · none · 17 Aug 2026 · Delhi" — so collapsing hides the controls, not the
facts.

### Verified

Rendered at 1512, 1280 and 1100 wide: no horizontal scrolling at any of them,
and the two-pane workspace stacks below 1180 rather than crushing the form
column. 751 tests pass — the markup hooks the suite asserts on were preserved
deliberately rather than discovered by breakage.

---

## 49. The firm's team on the auditor's report, MRL and engagement letter

**Eleven observations, 20 August 2026**, against the .exe shared with the team.
Seven were one already-fixed defect; four were real.

### Seven were the field-catalogue bug (their queries 1, 2, 6, 7)

"These points are not available to fill" on three documents — 13 findings on
the auditor's report, 20 on the MRL, 4 on the engagement letter. That is
decision 47: `field_catalog` was built only by `scripts/seed.py`, which a
packaged installation never runs, so the clauses existed, the document knew they
were unanswered, and no control rendered.

**Query 2 was the same bug wearing a different hat.** "Information Other Than
the Financial Statements" and "Auditor's Responsibilities" were reported
missing; both clauses exist — `iar.other.info` and `iar.resp.auditor` — and both
appear in the team's own blocking list. They carry a question, so with no answer
they do not print.

Confirmed fixed on a clean install of the rebuilt .exe: **field catalogue
synced: 211 field(s)**, and 22 questions on the auditor's report where the team
had none.

### The cash flow statement (their queries 3 and 5) — accepted, narrowed

**Section 2(40), first proviso**: a One Person Company, a small company, a
dormant company and a start-up private company need not include a cash flow
statement.

**The query arrived worded as "not applicable in private limited company".
Taken as written that would have been wrong** — it would drop the statement for
every private company and put a false description of the financial statements
into a signed report. The partner confirmed on 20 August that the tool is used
for **small companies and OPCs**, and the exemption is keyed to those two
classes.

`cash_flow_required` is a render-context variable computed from the company
type, declared in `CONTEXT_VARIABLES` so the loader rejects a typo at load.
**It is `True` when there is no client profile**: a document must not quietly
lose a statement because nobody set the company type — absence of information is
not evidence of exemption.

Five clauses were split, each gaining a guarded variant and a sibling:
`iar.opinion.scope`, `iar.opinion.body` (all three opinion types),
`iar.143.3.d`, `eng.framework`, `mrl.header`. The `mrl.header` split had to
remove the phrase **twice** — the statements audited, and management's own
responsibility paragraph — or the letter contradicts itself within four
sentences.

**Four references were left in place, deliberately**, and are for the partner to
decide:

| Clause | Phrase |
|---|---|
| `iar.resp.mgmt` | "true and fair view of the financial position, financial performance and cash flows" |
| `mrl.resp.fs` | s.134(5) wording: "profit or loss and cash flows for that period" |
| `mrl.framework` | "true and fair view of the state of affairs, profit or loss and cash flows" |
| `eng.objective` | "its profit or loss and its cash flows for the year ended on that date" |

These describe the *responsibility* for preparing statements rather than listing
what was audited, and two of them are close to statutory quotation. Rewriting a
s.134(5) paragraph is not the same act as adjusting a list of financial
statements, and was not authorised by the request.

### Accepted and added (their queries 4, 10, 11)

- **MRL subject line** — confirmed absent; the letter ran addressee, address,
  date, "Dear Sir,". Added above the salutation on both variants.
- **`eng.report.form`** now names **SA 700 (Revised)** and **section 143(3)**. A
  clause titled "Expected Form and Content of Reports" that named neither was a
  fair criticism. Their text also restated the CARO and IFC scope; **not taken**
  — `eng.caro.scope` and `eng.ifc.scope` already carry those, each gated on its
  own applicability flag, and repeating them here would tell a CARO-exempt
  company that CARO applies.
- **`eng.header`** now states the letter is prepared under **SA 210**.

### Expanded (their query 8)

`eng.objective` stated the objective and stopped. It now also names the
Standards on Auditing, the reasonable-assurance threshold and the risk-based
nature of the procedures. Source unchanged: ICAI's Implementation Guide to
SA 210, Chapter 3.

### Declined (their query 9)

**`eng.framework` was not replaced.** It was reported missing; it exists, and it
already branches on the client's framework and names the actual statements. The
proposed replacement — "Accounting Standards / Indian Accounting Standards ...
as applicable" — is a template that has not decided which framework applies.
Replacing a clause that decides with one that does not is a step backwards.

**Still open on that clause**: our AS variant cites "Rule 7 of the Companies
(Accounts) Rules, 2014". The Companies (Accounting Standards) Rules, 2021 now
govern. Raised with the partner and **not changed** — correcting a statutory
citation is their call, not mine.

### Scope recorded

The partner confirmed the tool covers **IGAAP only, not Ind AS**. The Ind AS
variants remain in the repository and are untouched; the framework dropdown
still offers Ind AS, which is worth revisiting, since the team's test client was
set to Ind AS and that is what produced two of the eleven observations.

---

## 50. Typed controls, and the signing partner per engagement

**Five observations from the firm's team, 20 August 2026.** All five accepted.

### The master-data editor had one free-text box for every field (their 1 and 5)

Changing the framework or the company class meant **typing an enum token
exactly** — `igaap`, `small` — with a refusal on a near miss. The editor now
renders a control per field: a dropdown for the two enum-backed fields, a
numeric box for the seven amounts, text for the rest.

Swept in the test rather than checked on the two reported, so a third enum added
later cannot arrive as a text box.

### The company classes are named in words (their 5)

The forms offered `pvt`, `opc`, `small` — database tokens, asking the user to
know the schema. They now read:

- **Small Company (s.2(85))**
- **One Person Company**
- **Private Limited (other than a Small Company)**

That last distinction is load-bearing: without it the classification cannot
express the cash-flow exemption of decision 49.

### Indian GAAP only (their 1, and the cause of two earlier observations)

The framework dropdown offered Ind AS, which the tool does not support. **The
team's own test client was set to Ind AS**, and that produced two of the eleven
observations reviewed under decision 49. Only Indian GAAP is now offered.

The Ind AS variants stay in the clause repository — unreachable rather than
deleted — so supporting it later is a manifest change and not re-authoring.

### The document font is chosen from a list (their 3)

A misspelled face is substituted silently by Word, and the page breaks of a
signed report move with it. Seven faces, all shipped with Windows and Word,
serif first because this is a statutory report.

A face already stored that is not in the list is kept as an extra option, so a
firm's existing choice is never silently changed.

### The ICAI logo (their 2)

The ICAI Chartered Accountant mark ships with the application and is now the
**default** for a new installation, and the logo is chosen from a list rather
than typed as a path.

**Offered, not fixed**, for two reasons. Decision 20 makes the installation
usable by any practice, and a firm with its own artwork must not be overruled by
ours. And **the mark is ICAI's**: its use by members is governed by ICAI's own
guidelines, so whether it appears over a particular firm's name on a particular
document is that firm's professional judgement to exercise — not a default this
software should impose silently on every firm that opens it. "No logo" is
always available.

### The signing partner belongs to the engagement (their 4)

> "Partner A signs the audit report of Client Y and Partner B signs the audit
> report of Client Z, both under the firm name Adlakha Kukreja & Co."

**`Engagement.partner_id` existed from the start and nothing ever read or set
it.** `signing_context` picked the firm's first active signatory, so in a firm
with two partners every report named the same person — exactly what the team
described.

The workspace now has a **Signing partner** control beside the opinion and
report date, listing that client's firm's active signatories. `signing_partner`
prefers the engagement's own choice and falls back to the firm's first
signatory, so a report is never signed by nobody.

**The chosen partner must belong to the client's firm.** An engagement naming
one firm's member over another firm's letterhead is the sort of thing noticed
only after a report has gone out, so it is checked on save rather than assumed.

---

## 51. The Accounting Standards citation

**Decided 20 August 2026**, on the partner's instruction.

The clauses cited **"Rule 7 of the Companies (Accounts) Rules, 2014"** as the
provision section 133 is read with for the Accounting Standards. Rule 7 was the
**transitional** provision: it deemed the standards notified under the Companies
Act, 1956 to be the accounting standards until new ones were prescribed. They
have been — by the **Companies (Accounting Standards) Rules, 2021**.

Every AS variant now reads "...specified under Section 133 ... read with the
**Companies (Accounting Standards) Rules, 2021, as amended**."

**Four variants across three documents**, all of which had to move together or
the report and the letters would cite different rules for the same accounts:

| Clause | Document |
|---|---|
| `iar.143.3.e` | Auditor's report — compliance with the Standards |
| `eng.framework` (both AS variants) | Engagement letter — what will be audited |
| `mrl.framework` | Representation letter — the framework relied on |

**Two things deliberately untouched.**

**Ind AS was already right** — section 133 read with the Companies (Indian
Accounting Standards) Rules, 2015 — and the correction did not reach it.

**`bdr.vigil.mechanism` cites a different Rule 7**, of the Companies (Meetings of
Board and its Powers) Rules, 2014, correctly. A search-and-replace on "Rule 7"
would have broken it, and a test now says so. The Board's Report's many
references to the Companies (Accounts) Rules, 2014 are also correct and
unchanged: those rules do govern the Board's Report, and only the
accounting-standards route was stale.

**Raised twice before it was acted on.** The point was flagged on 19 August when
the team proposed replacing the clause wholesale, and again on 20 August, and
left unchanged both times. Correcting a statutory citation in a document the
firm signs is the firm's decision, not the tool's — and the difference between
raising it and acting on it is the whole reason the clause repository is
separate from the code.

## 52. Multi-user LAN deployment — deferred, not declined (20 Aug 2026)

The firm runs a central LAN server holding databases and applications, with no
local copies on staff PCs, and wants AuditCraft the same way: 3–4 concurrent
users, usually on different clients, occasionally the same one.

**Held until the tool is finalised and the team has tested an exe.** The partner
set the sequence: correct the content first, then package, then deploy.
Deployment decisions taken around an unfinished tool get remade.

**What was established, so it need not be re-derived.** The firm's habit — put
the file on the share and let each PC open it — is the one arrangement that does
not work here. SQLite depends on file locking, and Windows shares do not provide
it reliably; concurrent writers can corrupt the file. Sharing only the .exe
shares nothing at all, because a frozen build writes to `%LOCALAPPDATA%`
(`config.py:30`), so ten launches produce ten databases.

The workable form is the inverse: the application runs *on* the server and staff
reach it over HTTP. One process owns the file, so writes queue rather than
collide. SQLite stays — WAL is already enabled (`db.py:86`) and PostgreSQL earns
its keep only well beyond this user count.

**Centralising prevents corruption, not silent overwrite.** Responses are stored
per field, so two users on the same client but different questions never clash,
and `_guard_unlocked` already refuses edits to a finalised engagement. The
residual risk is the same field at the same moment. Three additions were scoped
and not built: a presence indicator, a conflict check at save time, and a name
at sign-in — `set_response()` already carries `updated_by`, currently fed the
constant `LOCAL_ACTOR`, which decision 20 accepted when one person used one copy
and which stops being defensible once four people share a database.

**Open, for the partner:** whether a name chosen from a list is sufficient, or
partners need a PIN so a report cannot be finalised in someone else's name.

## 53. Six Board's Report disclosures reported missing (20 Aug 2026)

The firm's team listed six disclosures absent from the Board's Report. Four of
the six already had approved wording in the repository. They were absent for a
mechanical reason, not an editorial one.

**An unanswered input takes its whole clause out of the document.**
`build_document` skips a clause whose mandatory input has no answer. The
engagement is recorded as incomplete, which blocks export — but the draft in
front of the auditor is simply missing a statutory paragraph, with nothing on
the page to say one was expected. Every nil disclosure in the Board's Report sat
behind a question nobody had answered yet, so a draft taken early was short of
Rule 8(5)(iv) and Rule 8(5)(xii) and looked finished.

The fix is to stop the question existing where master data already answers it.
`input.defaults` is a list of `{when, value}` entries evaluated against the same
context a variant uses; the first match supplies the answer, and only where the
engagement has none of its own, so a derived answer never overrides a person.
`bdr.subsidiaries` derives its nil case from the profile's own subsidiary,
associate and joint-venture flags; a company that has one is still asked, since
what became or ceased to be one during the year is not in any master field.

**`bdr.otsettlement` is defaulted unconditionally, and that is a judgement.**
There is nothing to derive it from: a one-time settlement is an event in the
year, not an attribute of the company, and `borrowings` would prove only the
negative case while leaving every borrowing company unanswered — the state that
lost the disclosure to begin with. So the common answer is assumed and the
auditor reverses it. This is an assertion the *Board* makes about its own year,
and Admin → Default Answers is where a firm that would rather be asked every time
can say so.

**A narrative was demanded with nowhere to type it.** The field catalogue built
explanation fields only for clauses that also asked a question, because the
narrative branch sat inside `if clause.input is None: continue`.
`bdr.state.affairs` asked nothing and demanded an explanation, so export
reported one was required and no screen offered a box — an engagement that could
not be completed by any sequence of actions, which is what the team hit first.
`bdr.auditor.remarks` had the same defect waiting: it follows the engagement's
opinion type and has no input, so the first qualified opinion would have
demanded the Board's explanation with nowhere to give it. Narrative fields are
now built for every clause that can require one.

**State of affairs: one section, two paragraphs.** The request listed "State of
the Company's Affairs" and "Brief description of the Company's working during
the year / State of the Company's affairs" as two disclosures. Both are section
134(3)(i), and the MCA's own Board's Report format prints them as one item — two
headings on one subject would read as a drafting slip in a report the directors
sign. Both supplied texts are kept, in the order given, under one heading.

**The term of appointment uses the statute's words.** The requested wording ran
"until the conclusion of the Annual General Meeting to be held in the year
[20XX]", which needs a second year kept in step with the first. Section 139(1)
fixes the term as running "till the conclusion of its sixth annual general
meeting", so that is used: it cannot fall out of step, and it spares a field per
client. The explicit closing year goes in on request.

**Found while checking the page rather than the tests.** The workspace tooltip
compared `carry_forward.value` against `'auto'`; the enum's member is `always`.
Every carried-forward field therefore fell to the final branch and told the
auditor it was "answered afresh each year" — the opposite of the truth. The same
shape as the flag-name typo that silently deleted clauses, and invisible to 775
tests, because a wrong sentence in a title attribute breaks nothing. Now checked
the same way: every value a template compares against must be a real member.

**Left for the partner.** "No new plans were discussed by the Board of Directors
during the year" is a positive assertion about board proceedings, defaulted for
every client that takes the standard wording. It is theirs to keep or drop.

## 54. The team's third round, and two items disputed (20 Aug 2026)

**Most of the list was the same defect as decision 53.** The Directors and KMP
paragraph, the cost records paragraph, the annual return web address, the
conservation particulars and the "omit the IFC limb" wording of the Directors'
Responsibility Statement all existed, correctly drafted, and were absent from
the team's drafts because an unanswered input takes its clause out of the
document. Each now derives its common answer: cost records from the profile's
own industry flag, the annual return from whether a website is recorded, the
subsidiaries paragraph from the group-company flags, and the rest defaulted and
overridable.

**The DRS was making a statement an unlisted company is not asked to make.**
Clause (e) of s.134(5) applies by its own words only "in the case of a listed
company". The Board's Report was asserting that the directors had laid down
internal financial controls and that those controls operated effectively, for an
unlisted private company. The clause carried both variants and nothing selected
between them. Now derived from the company class.

A derived answer never overrides a stored one, so a file answered before this
landed keeps `with_ifc`. That is right for a default and wrong for this
statement, so `drs_ifc_limb_for_unlisted_company` blocks export instead: the
contradiction is reported, the auditor decides, and nothing is rewritten
underneath them.

**Disputed: the citation in the team's own text.** Their wording read
"sub-clause (e) of Section 134(3) ... pertaining to laying down internal
financial controls". s.134(3)(e) is the company's policy on directors'
appointment and remuneration under s.178(1). The internal financial controls
limb is **s.134(5)(e)**. The substance was right and the reference was not, and
a wrong section in a signed Board's Report is the kind of thing that gets
noticed. The corrected citation is what prints.

**Disputed: MGT-9 was not added.** The extract of the annual return in Form
MGT-9 was omitted from the Board's Report requirement -- s.134(3)(a) was
substituted by the Companies (Amendment) Act, 2017 to require the web address
where the annual return is placed, and Rule 12(1) of the Companies (Management
and Administration) Rules, 2014 was amended in 2020 to drop the MGT-9 extract.
The tool already prints the replacement (`bdr.annual.return`). Building MGT-9
would add eight tables of shareholding, indebtedness and remuneration data --
every cell an opportunity to state something inaccurate over a signature -- for
a disclosure no longer called for. Left out pending the partner's confirmation;
it is a content decision, not a technical one.

**The cash flow statement is now gone from all four remaining places.**
`iar.resp.mgmt`, `mrl.resp.fs`, `mrl.framework` and `eng.objective` describe
responsibility for *preparing* the statements rather than listing what was
audited, which is why they were left on 19 August for the partner to decide.
The team has now raised it twice more. All four split into a cash-flow pair on
the existing `cash_flow_required` flag. A small company's six documents contain
no mention of a cash flow statement; a full-scope company's still contain ten.

**Added:** the auditors' opinion paragraph in the Board's Report
(`bdr.auditor.report`, driven by the engagement's opinion type so it cannot
describe an unmodified opinion while the report is qualified), the SA 210 basis
paragraph in the engagement letter (`eng.sa210`), the four-column board meetings
table, the POSH particulars, and Rule 8(3) restructured into parts A and B --
which settles the question left open on 17 August, since the firm's own format
answers it.

**On "unqualified".** The precedent says "Unqualified Opinion"; SA 700 (Revised)
uses "unmodified". The modern term prints, and the clause file says so.

## 55. The partner's ruling on Rule 8A (20 Aug 2026)

Four questions were put in the first verification report. The signing partner
answered all four. Recorded verbatim in substance, because the whole shape of
the Board's Report now rests on them.

**1. Rule 8A was NOT amended in 2025.** G.S.R. 357(E) of 30 May 2025 amended
Rule 8 — sub-rule (5), clause (x) and the new clause (xiii) — and Rules 5 and
12. No 2025 notification touched Rule 8A, which stands as inserted by G.S.R.
725(E) of 2018. So the new quantitative POSH particulars and the maternity
statement apply **only under Rule 8**, and reach neither a One Person Company
nor a small company.

**2. Rule 8A displaces the Rule 8 disclosures, not section 134 itself.** The
statutory skeleton of s.134 remains; Rule 8A prescribes a **closed, exhaustive**
list of what the abridged report shall contain. A clause of s.134(3), or a
detailed Rule 8(5) item, with no counterpart in Rule 8A is **not required** for
these companies.

**3. Rule 8(5)(xiii) reads:** "a statement by the company with respect to the
compliance of the provisions relating to the Maternity Benefit Act, 1961." No
form of words, quantity or format is prescribed beyond that.

**4. CSR (s.135), the s.197(12) particulars, secretarial audit (s.204), the
vigil mechanism (s.177(9)) and the Secretarial Standards** are governed by their
own provisions, were not altered in 2025, and do not appear in Rule 8A's closed
list.

**What follows arithmetically.** Of the Board's Report's 43 clauses, 18 survive
for a small company — the eleven Rule 8A items, AOC-2, the four structural
clauses, and the three the firm attaches voluntarily (the statutory auditors
paragraph, the auditors' opinion paragraph and the MGT-9 annexure). Twenty-five
come out. Several of the twenty-five are already excluded for these clients by
the applicability engine; the rest print today and should not.

**Not implemented.** The partner reserved consent on the change itself. Three
options were put: gate on the flag, keep the full report as house policy, or
keep it without the defaults. Nothing moves until that is answered.

## 56. Rule 8 gated on the company class (20 Aug 2026)

The partner's decision, on the ruling recorded as decision 55: gate on the flag.
Flag on, and the Board's Report is the Rule 8A closed list — the Rule 8(5) items
are not inserted, not defaulted, and not left as placeholders. Flag off, and the
full Rule 8 report is produced, including the 2025 additions.

**`full_board_report` is derived, not computed.** It is the strict inverse of
`abridged_board_report`, taken after any override is applied, and it has no
stored column. Two independent determinations of the same question could drift
apart and produce a report that is neither form — abridged by the engine and
full on the page. A test sweeps every company type and both override directions
to hold them inverse. `DERIVED_FLAGS` exempts it from the startup check that
every flag has an override column, since it has no independent value to store.

**Twenty-five clauses now require it.** Two of those already carried a flag of
their own (`s197`, `secretarial_audit`); the requirement is additive, so both
must hold. A small company's report drops from 43 clauses to 18 — the eleven
Rule 8A items, AOC-2, the four structural clauses, and the three attached
voluntarily.

**The exclusion happens before the input is read**, which is what makes the
partner's "no defaults, no placeholders" hold without any extra machinery: a
clause excluded by applicability never reaches the derived-answer logic. Pinned
by a test rather than left to the reading.

**Decision 3 of 16 August superseded.** That decision stripped the rule number
and commencement year from `bdr.maternity`, because the citation then in the
file collided with Rule 8(5)(xi) — which the register gives to the IBC
disclosure — and two requirements cannot share a sub-clause. The reasoning was
sound and the conclusion too cautious: the maternity statement is Rule
8(5)(**xiii**), inserted by G.S.R. 357(E) dated 30 May 2025, effective 14 July
2025, colliding with nothing. The partner confirmed the sub-clause and quoted
its text. `effective_from` now carries the commencement, so the clause does not
appear in an FY 2024-25 report — verified in both years.

A third option was added to that clause: where the Act's thresholds are not met,
non-applicability is stated expressly, which the partner's ruling requires
rather than the disclosure simply being absent.

## 57. The ICAI mark is the default logo (20 Aug 2026)

Confirmed by the partner. It was already the default in `bootstrap.py`; what was
open was whether it should be, given that its use is governed by ICAI's
guidelines for members. A firm can still change it, including to no logo.

## 58. Verification pass 2 — the IFC exemption is wrong (20 Aug 2026)

The auditor's report and CARO 2020 were verified and stand. The rule deciding
whether an IFC annexure exists at all is wrong in three ways. **Reported, not
changed** — the partner reserved consent on the verification pass.

Entry 9A of G.S.R. 583(E) dated 13 June 2017 exempts a private company from
clause (i) of s.143(3) where it "(i) is a one person company or a small company;
**or** (ii) has turnover less than rupees fifty crores ... **or** ... aggregate
borrowings ... less than rupees twenty five crore".

**One — the conjunction.** `_ifc` tests `turnover < 50cr AND borrowings < 25cr`.
The notification joins them with **or**. One limb is enough.

**Two — company class.** Limb (i) exempts an OPC or a small company on class
alone. The engine puts them through the threshold test instead.

**Three — the condition is absent.** Paragraph 2A makes every exemption in that
notification conditional on the private company "not having committed a default
in filing its financial statements under section 137 ... or annual return under
section 92". A client behind on its ROC filings loses the exemption and does
need the annexure. Nothing in the profile records this, and no rule reads it.

**Every error runs the same way** — towards producing an annexure that is not
required. That is the cautious direction and not a reporting failure, but it is
a s.143(3)(i) opinion on internal financial controls, signed, for a company the
law does not ask it of. The rules file's own note calls this "the highest-risk
rule in the file", and names exactly this failure.

The first two are corrections. The third adds a question to the client profile,
which is why none was made without instruction.

**Verified and unchanged.** CARO's applicability is right: sec8, OPC and small
companies excluded outright; the private-company exemption cumulative, lost on
either public-company relationship, and tested as "not exceeding" — the opposite
of the IFC test, deliberately. The auditor's report holds: Rule 11(d) absent,
Rule 11(g) from years ending 31 March 2024, Rule 11(e) and (f) from 1 April
2021, s.143(3)(a)-(i) separately cited, lettering positional.

**Not checked:** the Standards themselves for revision, the 21 CARO clauses
individually, the IFC annexure against the ICAI Guidance Note, s.143(3) for
amendment, and the MRL and engagement letter entirely.

## 59. CARO and IFC are stated by the auditor (20 Aug 2026)

Partner's instruction: "Just ask the simple question of applicability of CARO
and IFC, do not link with the turnover or borrowing. User himself will decide."

Both are now **declared** flags. The engine reads no thresholds for either and
infers nothing. `DECLARED_FLAGS` names them; `compute` skips the rule functions
and returns a flag marked undecided; the auditor's answer arrives through the
same columns an override uses and is recorded as "stated by the auditor" rather
than as an overrule of a computation that no longer happens.

**Beyond the instruction, this was the right call on the merits.** Both
exemptions turn on facts the profile's figures do not carry. CARO's
private-company limb is lost outright if the company is a subsidiary or holding
company of a public company. The s.143(3)(i) exemption is lost under paragraph
2A of G.S.R. 583(E) if the company has defaulted in filing under s.92 or s.137 —
which nothing in the profile records. Decision 58 had just found the IFC
inference wrong in three ways. An engine reading turnover and borrowings was
going to keep being confidently wrong, and the auditor establishes the position
anyway.

**`decided` is the new state that makes this safe.** "Not applicable" and
"nobody has said" both read as False everywhere downstream, so without a third
state a forgotten question silently drops a whole annexure.
`caro_applicability_not_stated` and `ifc_applicability_not_stated` block export
until the question is answered — which is what separates "the auditor decides"
from "the auditor forgot".

**A reason is no longer demanded** for these two: a reason exists to justify
overruling the engine, and there is nothing left to overrule.

**Two pre-existing defects surfaced on the way.**

`_findings` in the review router called `compute` rather than `resolve`, so the
consistency check saw the engine's raw reading and **every override was
invisible to it**. Survivable while the engine's answer was usually the same
one; fatal once the auditor's answer became the only answer. Now `resolve`.

`input.defaults` fills the document but stores no response row, so a defaulted
field still reads as unanswered to the completeness gate. Not addressed here —
noted because it is the same shape as the "findings blocking export" complaint
of 17 August and will need its own decision.

**The law was not deleted with the logic.** Both rules keep their thresholds in
a `note` for the auditor to read, and a test asserts no threshold key returns to
either rule. The four test classes that covered the inference were removed and
replaced by `TestCaroAndIfcAreStatedNotInferred`, which sweeps every company
type and both extremes of every figure to prove nothing moves the answer.

**Seed data now states both**, since a sample engagement that cannot be approved
is not a useful sample. Seeding also skips any answer the catalogue does not
carry — the test suite runs against a six-clause fixture repository.

## 60. Verification pass complete — all six documents (20 Aug 2026)

The remaining documents were checked for whether each clause belongs and rests
on a live provision. Nothing needed changing.

**CARO 2020.** All twenty-one paragraphs present, across fifty-one clauses —
sub-clauses separated where the Order separates them. No amendment to CARO since
it replaced CARO 2016 for years commencing on or after 1 April 2021.

**MRL.** Thirty-two representations, each cited to the Standard it rests on: SA
580 throughout, with SA 540, SA 550, SA 560, SA 450, SA 240, SA 250 and SA 505
where the subject calls for them. The newer Schedule III representations are all
present and separately cited — benami property, crypto currency, undisclosed
income, wilful defaulter, struck-off companies, charges, and the layers
restriction.

**Engagement letter.** Twenty-two clauses following SA 210 clause by clause.

**The audit trail is consistent across documents.** `rule11.g` and
`mrl.audit.trail` both commence for years ending 31 March 2024, and the
representation covers preservation as well as use and operation. A mismatch here
would have the auditor reporting on something the company never represented.

**Two applicability rules verified against a current source.** Internal audit
under s.138 and Rule 13 is correct as coded. Secretarial audit under s.204 and
Rule 9 is correct, including the limb most often missed: the 2020 amendment
reaches *every* company with borrowings of Rs. 100 crore or more, private
companies included, for years commencing on or after 1 April 2020.

**SQM 1 and SQM 2 were deferred.** ICAI issued them on 14 October 2024 to
replace SQC 1 from 1 April 2026, and the Council deferred that date at its 451st
meeting on 30-31 March 2026; SQC 1 continues. No impact here — the repository
references neither, and `eng.peer.review` rests on the Peer Review Guidelines.

**Still unchecked, and the next order of work.** These are line-by-line readings
against a source document rather than questions of applicability: the text of
each CARO paragraph against the Order; the IFC annexure against the ICAI
Guidance Note; the Standards themselves for revision; s.143(3) sub-clauses for
amendment; and, for the Board's Report, CSR thresholds under s.135, the s.197(12)
particulars, the vigil mechanism under s.177(9), SS-1 and SS-2, and the Deposit
Rules. None of the last five affects a small company — all five clauses are now
gated out for those companies by decision 56.

## 61. No applicability flag reads a figure (20 Aug 2026)

Partner's instruction: "Please do not link any clause such as CSR or internal
audit etc to financial parameters feeding in master data. Remove all those
parameters. Ask directly from the user whether it's applicable or not."

**CSR, internal audit and secretarial audit joined CARO and IFC as declared
flags.** Five of the eleven are now stated by the auditor. Every threshold is
gone from `applicability_rules.yaml`, and a test sweeps the whole file for a key
ending `_min`, `_max`, `_below` or `_not_exceeding` so one cannot reappear on a
single rule unnoticed.

**What is left computed reads no money.** `s197` and `kam` turn on company
class; `abridged_board_report` likewise, and `full_board_report` inverts it;
`cost_records` on the industry; `cfs_required` on whether a subsidiary,
associate or joint venture exists. All are facts the profile records as facts,
not amounts to be compared. A test names the keys each remaining rule is allowed
to carry, so a threshold cannot return under a new name either.

**`ProfileFacts` stopped carrying money at all** — paid-up capital, turnover,
borrowings, net worth, net profit, reserves, deposits and revenue are no longer
fields on it, and `facts_from_profile` no longer passes them. Leaving them as
unread inputs is worse than removing them: someone corrects a figure, watches
the determination stay put, and cannot tell whether the tool is broken or the
figure was irrelevant.

**The master-data screen no longer asks for them.** `AMOUNT_FIELDS` is now
empty. This reverses the editing screen built on 17 August at the partner's
request — reasonably, because the reason for wanting it was that those figures
decided CARO, IFC, CSR, internal audit and secretarial audit, and a wrong figure
meant a wrong annexure. That reason no longer exists.

**The columns remain on `client_profile`**, holding whatever was entered before.
Dropping them is a one-way loss of data the firm typed, so it waits on the
partner rather than riding along with a behaviour change. Nothing reads them.

**A bug introduced by decision 56, caught on screen not by tests.**
`overridable()` returned every flag including the derived one, so the
applicability page offered an override control for `full_board_report` — which
would have written to a column that does not exist, or worse succeeded, leaving
a company abridged by the engine and printing the full Rule 8 report. It now
returns `STORED_FLAGS`, `set_override` refuses a derived flag with a message
saying which flag to set instead, and three tests hold it.

**The law survives where the logic did not.** Every declared rule keeps its
thresholds in a `note` for the auditor to read — including the limb most often
missed, that Rule 9 reaches *every* company borrowing Rs. 100 crore or more,
private companies included. A test requires every declared flag to carry one:
asking a question while giving no help in answering it would just move the work.

## 62. The client profile asks only what something reads (20 Aug 2026)

Partner's instruction: keep only what the tool needs, remove what is redundant,
and redesign the screen around what is left.

**Sixteen fields went.** Every one was traced first, by reading the whole of
`app/` and `content/` and asking what consumed it:

- `corporate_addr` — no letterhead used it; the registered address is what the
  company's letterhead and Form MGT-9 print.
- `phone`, `email` — captured and printed nowhere. `letterhead_for` gives a
  company's paper its name, registered address and CIN, and nothing else.
- `industry` — free text sitting beside `cost_records_industry`, the boolean
  that actually decides anything.
- `nature_of_business` — duplicated `bdr.nature.business`, the clause that
  carries it into the Board's Report.
- `amounts_in` — `unit_caption` and `scale` exist in `core/formatting.py` and
  are called from nowhere; the column was never wired to either.
- The seven figures — dead since decision 61.
- `is_subsidiary_of_public`, `is_holding_of_public` — went with CARO's inference.
- `gstin` — never displayed, exported or printed. `validate_gstin` stays in
  `core/validators.py`, tested and unused, in case it comes back.

**The gap this uncovered mattered more than the clutter.** Decision 35 put the
engine's own facts on the new-client form. It never put them on the master-data
editor, so a box mis-ticked at onboarding was permanent — `has_subsidiary`,
`has_associate`, `has_joint_venture`, the three Rule 6 consolidation answers and
`cost_records_industry` could be set once and never corrected. They decide the
Board's Report subsidiaries paragraph, the cost records paragraph and whether
consolidated statements arise. Two tests now hold the pair of properties:
everything editable is read by something, and everything askable at onboarding
is correctable afterwards.

**The form was a field picker.** Choose one field from a dropdown, type a value,
submit; repeat for the next. It showed no current values at all, so the only way
to see what a profile held was to change something and read the version history.
It is now four groups — Company, Group structure, Exemption from consolidation,
Cost records — each field showing what is stored, all saved together under one
change reason. `_submitted_changes` compares against the current profile and
passes only what differs, so one corrected address does not open a version
recording eleven fields as changed.

**Tri-state, not a checkbox.** `has_subsidiary` and friends are `bool | None`,
and the third state is not decoration: the applicability engine says "not
recorded" and means something different by it than "no". A checkbox cannot
express that — unticked would silently become an answer.

**The consolidation exemption appears only when it can apply.** Rule 6 is
meaningless for a company with no group company, and three questions that never
apply are three a reader has to decide to ignore.

**The year-on-year comparison changed with it.** It compared turnover, paid-up
capital, borrowings and net worth. It now compares the website and the group
and cost-records facts — a company that acquires a subsidiary changes its
Board's Report, and that is the change a reviewer needs on that screen.

## 63. Removing a partner or a firm (20 Aug 2026)

Partner's request. `update_partner` previously carried a docstring saying "A
partner is never deleted"; that is now true only of a partner who has signed
something, which is the case the docstring was really about.

**The rule under both: a record goes only when nothing ISSUED points at it.**
What the guards protect is not the row. It is the ability to answer, years
later, who signed a report and under which UDIN.

**A partner is held by** UDINs generated in their name, finalised or archived
years they signed, and — deliberately — open years assigned to them.
`Engagement.partner_id` is nullable, so an open year *could* have been cleared
silently on the way past. It must not be: clearing it changes who an unissued
report goes out under, and nothing on screen would say so. The auditor reassigns
it first.

**A firm is held by** clients on its register, user accounts, partners named on
issued documents, and being the last firm on the installation. That last one is
not fastidiousness: `bootstrap.first_run` creates a firm because a letterhead
and a signature block need one, so removing the final firm would empty the
screen and have a placeholder reappear on the next start.

**What goes with a firm:** its partners and its standing default answers. Both
are the firm's own configuration and mean nothing without it. Nothing else — a
firm with a single client keeps everything.

**The partner guard is not bypassable by deleting the firm instead.**
`firm_blockers` counts partners that `partner_blockers` would refuse.

**Confirmation is a typed name, not a dialog.** A partner is one row in a short
list of similar rows, and an "are you sure?" on the wrong line is confirmed as
readily as on the right one. The name must match, case-insensitively.

**A refusal names what is holding the record**, counted by kind, and the page
shows that in place of the control rather than offering a button that will only
refuse. "Cannot be deleted" on its own is a dead end rather than an answer.

**The removal is recorded.** `audit_log` has no delete path anywhere in the
application, so the entry written on the way out is what later answers "there
used to be a partner here".

**The active-firm cookie is cleared** when its firm is removed. Left pointing at
a row that no longer exists, every screen falls back to "no firm" and reads as
though the installation had been wiped rather than one firm removed.

## 64. The export gate reads the documents, not the catalogue (20 Aug 2026)

Found while answering "can we share an exe" — which is the right moment to look,
because it is the last one before other people meet the defect.

`_completeness_rules` swept `field_catalog` for mandatory fields with no stored
answer. The catalogue knows what is mandatory; it knows nothing about the
engagement. It could not know that a clause had been excluded because Rule 8
does not reach a small company (decision 56), nor that an answer had been
derived from master data (decision 53). It demanded both.

**For a small company that was 41 of 129 mandatory fields** — 22 belonging to
clauses that never print for that company, 19 that the tool answers itself.
Export blocked over questions that appear on no screen. That is the firm's
complaint of 17 August returning in a new form, and it would have been the first
thing the team hit.

`build_document` already resolves both. It is now asked: the route renders every
document once, collects `unanswered`, `missing_narratives` and `missing_rows`,
and passes them in. The catalogue sweep survives as the fallback for a caller
that cannot render — it over-asks, which is the finding above, but a gate that
over-asks beats one that vanishes when a document fails to build.

**`rendered_placeholders` was never passed by anything.** The parameter existed,
the rule existed, and no caller supplied it, so the pre-export placeholder scan
had never once run from the review screen. It runs now, from the same render.

## 65. A field the model no longer has, still on the form (20 Aug 2026)

GSTIN survived decision 62 as a label and a text box on the new-client page
after its column was dropped. Nothing read it and nothing saved it, and 786
tests passed while it asked staff for a number the tool would discard.

Found by reading the page out of the packaged build, which is the one place a
form field cannot hide. A sweep now maps every input name on that form to a real
column, the officer-row prefixes, or a named piece of form machinery — and it
was checked by putting GSTIN back and watching it fail.

## 66. Two long-standing open items closed (21 Aug 2026)

**The state of affairs wording stands as the team drafted it.** The partner
approved it, including the sentence flagged on 20 August: "No new plans were
discussed by the Board of Directors during the year." The concern was that it
asserts something about board proceedings, by default, for every client taking
the standard text. Raised, considered, approved — no change. The clause file
keeps the note so the next reader knows it was a decision rather than an
oversight.

**The modified and disclaimed IFC opinions are reviewed.** These were the last
clauses still carrying the caveat from Gate A: the firm's Annexure B precedent
is a clean-opinion file, so `ifc.opinion`'s `material_weakness` and `disclaimer`
variants — and the criteria reference in `ifc_criteria_ref.yaml` — were authored
rather than adapted. They had never been read by a partner, and would have
surfaced first on the day a client got a modified IFC opinion. Now reviewed.

That closes every clause-level item recorded as open since Gate A.

## 67. Six improvements approved by the partner (21 Aug 2026)

Item 04 — help inside the tool — deferred until the kit is final, so it ships
once rather than twice.

**01. The signing partner follows the client.** `client.default_partner_id`,
copied onto an engagement when the year is opened. On `client`, not
`client_profile`: it is the firm's own assignment, no document prints it, and
versioning it would open a profile version every time a partner changed.
**Copied, not looked up** — the engagement's own partner is what a signed report
names, so reassigning a client next year must not move the name on a report
already issued. A test holds exactly that.

**02. Each annexure names the report it belongs to.** The sidebar had two
"Annexure A" entries. Only `short_title` changed; `title` goes on a signed
document and is untouched, which a test asserts.

**03. The engagement details open until they are complete.** The section already
existed with a heading — the observation in the kit was wrong about that, and is
corrected. It was collapsed by default (decision 48, which measured 567px of
controls between the auditor and the first question), so a new user never saw
it. It now opens while the opinion type or report date is unset and collapses
once decided. Decision 48's reasoning survives; only the empty case changed.

**05. The MGT-9 tables roll forward.** Five child models added to
`ROLLED_CHILD_MODELS`. Every carried row arrives flagged for review, as
litigation has since §6.2 — carrying is not confirming.

**06. The partner rows are valid markup.** Each row put two `<form>` elements
inside one `<tr>`, which may contain only `<td>` and `<th>`. A browser is
entitled to hoist those forms out of the table. Rebuilt as a card per partner,
which also reads better on a narrow window.

**07. Nothing counts the documents.** It produces seven, and the number moves
with the client — a small company gets neither CARO nor the IFC annexure, so its
set is five. A test sweeps the source for "all six".

### A guard that passed while the defect was planted

Worth recording, because it nearly shipped. The test for item 06 was written
with a regex containing `\b`. The script that wrote the test interpreted that
escape itself, so the file received a raw **backspace byte** (0x08) — the
pattern was `<tr\x08[^>]*>`, which matches nothing. The loop never ran,
`offenders` was always empty, and the test passed on every run including four
where an invalid row had been deliberately planted in the template.

It survived four rounds of disbelief because "the test passes" reads the same
whether the guard ran or not. What found it was dumping the file through
`cat -A` and seeing `^H`. The guard is now written with index arithmetic rather
than nested patterns, and there is a sweep for stray backspace bytes across the
source. **A mutation check is not proof unless the mutation actually fails.**

## 68. The team's fourth round (21 Aug 2026)

All three observations were right.

**1. The CIN is now quoted in the auditor's report**, under the addressee,
interpolated from the client record so the report cannot name a different CIN
from the one on file. On whether it is *mandatory*: section 12(3)(c) puts that
obligation on the COMPANY — to print its CIN on its own letters, billheads and
official publications — and does not on its face bind the auditor. Quoting it in
the auditor's report is settled practice rather than a duty imposed on the
auditor. The firm asked for it, nothing is lost by including it, and it removes
a real ambiguity: two companies may share a name across states.

**2. Rule 11(g) was short of its preservation limb.** The rule asks about three
things — that the software has the feature, that it operated throughout the
year, and that the trail "has been preserved by the company as per the statutory
requirements for record retention". The clean variant asserted the first two and
stopped.

**And the input's LABEL said "use, operation and preservation" the whole time.**
That is how the gap survived: on 20 August I told the partner preservation was
covered, having read the label rather than the wording. A label is not an
assertion in a signed report.

A fifth option was added with it — *operated all year, but not preserved*. A
clause whose label promises three answers must let all three be given; without
it, an auditor whose client keeps no retained trail had only the clean answer or
"not enabled", and neither is true.

**3. The letterhead repeated on every page.** It was written into
`section.header`, which Word prints on every page. A letterhead is stationery:
the firm's name belongs on the sheet the report starts on, and continuation
sheets are plain. It now goes into `first_page_header` with
`different_first_page_header_footer` set, and the ordinary header is cleared —
it previously carried the document title, which would otherwise have printed on
every page below a letterhead appearing on one.

### The guard that passed twice before it bit

The first version asserted that the firm's name appeared in exactly ONE header
part. That is equally true when the letterhead is on every page **except** the
first — the opposite defect — and it passed with the fix deliberately reverted.
Header part filenames carry no meaning; which one Word uses for page one is
decided by the `headerReference` type in the section properties. The test now
resolves each header through its relationship id and asserts the firm is in the
`first` header and in no other.

Second time in two days that a guard reported green while the defect it existed
to catch was present. Both were found by reverting the fix and disbelieving the
pass — which is the only way a test earns being trusted.

## 69. An adverse statement was the catch-all (21 Aug 2026)

The firm's team saw the Board's Report say:

> "The Auditors' Report contains a qualification, reservation, adverse remark or
> disclaimer."

on a client whose audit report was clean. **They were right that it was wrong,
and their proposed fix would have made it worse.**

**What was actually broken.** `bdr.auditor.remarks` had one variant for
`opinion_type == 'clean'` and an unconditional fallback for everything else.
"Everything else" includes **"nobody has said yet"** — the render context gives
an unset opinion as an empty string. So a Board's Report drafted before the
opinion was decided told the directors their audit report was qualified.

**Why their fix was not the fix.** They proposed replacing that paragraph with
the clean wording. That deletes the ability to report a real qualification: the
Board's Report would then say "no qualifications" even where the auditor's
report is qualified — which is the precise failure section 134(3)(f) exists to
prevent, and a far worse one than the symptom they saw.

**What was done instead.** Every variant now names the opinions it covers, and
there is no catch-all. An undecided engagement resolves to nothing: the clause
is recorded as unanswered, which blocks export and shows the question on the
workspace. Absent-and-blocked beats present-and-wrong.

**The same shape was in `bdr.auditor.report`** — the opinion-summary paragraph
added the day before. It would have said "the Statutory Auditors have expressed
a modified opinion" on the same facts. Both were mine, both from 20 August.

**Swept rather than spot-fixed.** Four properties now hold: no clause in any
document resolves to an exception-severity variant from an undecided
engagement; the Board's comments follow the opinion for all four opinion types;
an unset opinion blocks instead of guessing; and no clause anywhere keeps an
unconditional fallback marked as an exception. The last is the shape itself, so
the next clause written this way fails at the repository level rather than in
front of a client.

**One existing test had to change.** `test_every_option_of_every_clause_resolves`
probed with an empty context and required every clause to resolve. That premise
was correct while every clause had a catch-all; it is now wrong, because not
resolving is the fix. It probes a decided engagement instead, and says why.

**A default that asserts something adverse is the worst kind.** It is wrong
about the client, it reads on the page as deliberate, and the person most likely
to notice — the auditor who knows the opinion is clean — is the one least likely
to read that paragraph closely.

## 70. The first form a new user touches used to fail (21 Aug 2026)

Found while verifying a packaged build on a clean profile — not by a test, and
not on a developer's browser, because both already had the cookie.

`_issue_csrf_cookie` set the CSRF cookie on the RESPONSE, after `call_next` had
already rendered the page. Every template reads
`request.cookies.get('auditcraft_csrf', '')`. So on a fresh installation the
first page a user opened carried an **empty token in every form**, and their
first submission was refused — `422 Field required`, or a CSRF error. Reloading
fixed it, which is precisely why it survived to a packaged build: nobody's
second page load ever showed the fault.

**The fix is to issue the token before the page is rendered, not after.** The
first attempt wrote it to `request.cookies`, which did nothing: that dict is
cached per Request instance and the endpoint downstream builds its own Request
from the same scope. Writing the cookie header into `request.scope` via
`MutableHeaders` is what both share.

An existing visitor keeps the token they already hold — reissuing on every
request would invalidate a form left open in another tab. Three tests hold it,
and were checked by removing the scope write and watching two of them fail.

**What this says about the verification.** The defect was invisible to 812
passing tests, because `TestClient` carries cookies across requests within a
test the way a browser does after its first page. It took driving the .exe on a
profile that had never seen the application.

## 71. The tool closed when a loss was entered (21 Aug 2026)

The firm's team, fifth round, item 11: "on some Windows systems the tool closes
automatically when negative values are entered in the Financial Summary".

`_coerce_child` converted a typed figure with a bare `Decimal(text)`.
`decimal.InvalidOperation` inherits from **`ArithmeticError`, not
`ValueError`** — so it went straight through every router's
`except (CsrfError, EngagementError, ValueError)` and left the request with no
handler at all.

**The trigger was not the minus sign; it was the brackets.** An accountant
writes a loss as `(1,23,456)`, and `Decimal("(123456)")` raises. So did
`- 1234` with a space, and a figure pasted out of Word carrying a unicode minus.
The first loss-making client anyone opened would hit it.

Every numeric path now goes through one `parse_amount`, which reads the
notation an accountant actually types and raises `EngagementError` — a message
on the screen — when it genuinely cannot. The 22 handlers that meant "the user
typed something we could not read" now say `ArithmeticError` as well as
`ValueError`, and a sweep test fails if a new one does not.

## 72. CARO was never signed (21 Aug 2026)

Items 3, 7 and 8. CARO 2020 ended on clause 3(xxi) with nothing beneath it: the
IFC annexure had carried a signature block since the first build, and this one
was simply never written. The document rendered, validated and exported
perfectly well without it, which is why it survived four rounds of review.

The guard is a sweep — every document a person signs must carry a clause with
`render_as: signature` — rather than a test naming CARO.

The engagement letter now opens on the common case: the fee agreed with the
Board, and a continuing appointment needing no ratification since the
Companies (Amendment) Act, 2017 removed the proviso to s.139(1). Both remain
questions; a default is a starting point, not a decision taken away.

**Item 9 was declined, on the partner's ruling.** The team asked for the
Directors' Responsibility Statement's clause (e) — internal financial controls
— to print in every report. Section 134(5)(e) applies by its own words "in the
case of a listed company". It stays listed-only, and remains switchable per
client.

## 73. A schedule whose lines are prescribed (21 Aug 2026)

Item 4. The Board's Report financial summary was a free table: the preparer
typed the particulars, so eight article assistants produced eight different sets
of line items in eight different orders, and a Board's Report that reads
differently every year is one nobody can compare.

`repeating_block` now takes `fixed_rows` — the lines and their order, declared
in `content/` — and three of the eight are `computed` from the lines above
them, so a sub-total cannot be left disagreeing with them.

The expressions are data, not code. `app/core/arithmetic.py` parses and walks
them, admitting addition and subtraction and nothing else: multiplication is not
something a statutory schedule does, and division would admit dividing by zero.
A sub-total that refers to a row spelled differently, or to one further down the
page, is refused **at load time** — the alternative is a blank line on a signed
report.

A credit is entered in brackets, which decision 71 made readable.

## 74. The register could not be corrected (21 Aug 2026)

Item 5. Directors and KMP were written once, by the new-client form, and no
route touched them again — so a resignation during the year could not be
recorded anywhere.

That is worse than a missing screen. `bdr.directors.kmp` derives its disclosure
from this register precisely so the report cannot disagree with it (§18.8), so
with the register frozen the paragraph the directors sign could only ever say
"there was no change", however many there had been.

Rows are dated, never deleted: last year's signed report names the people who
held office then and has to go on naming them.

**And the answer now follows the register.** The clause defaulted flatly to "no
change". The moment the register could be maintained, that default became a
contradiction — a paragraph saying nothing changed directly above a derived
table listing the appointment and the resignation. It now reads
`directors_changed_in_year` from the register itself.

## 75. Twenty-one thousand pixels (21 Aug 2026)

Items 6 and 10: the applicability screen "cannot be located", and the Board's
Report has "no field to enter the year in which the term ends".

Both existed. The screen was linked from every workspace. The field rendered,
was mandatory, and sat 2,357 pixels down a page 21,283 pixels tall carrying
**312 fields under 41 headings** with no index.

From the far side of a page nobody can traverse, "I cannot find it" and "it is
not there" are the same report, and they have the same fix. The document tab now
carries an index of its clauses, marking the ones with something outstanding,
and the workspace names any DECLARED flag still awaiting an answer — CARO, IFC,
CSR, internal audit, secretarial audit — with a link to the screen that answers
it. "Applicability" is not what someone hunting for "where do I say CSR
applies?" is reading for.

**Items 1 and 2 needed no change.** Choosing the company class "Small Company
(s.2(85))" already produces the abridged report, and "Company has no website" is
already the default whenever the client's Website field is blank. Both were
almost certainly reported because a small private company had been recorded as
"Private Limited (other than a Small Company)".

**A note on how three of these were found.** Not by the suite, which was green
throughout. The 312-field page, the four CSRF fields bound to a variable the
template's context does not carry, and `ClauseSet.get` raising rather than
returning `None` all surfaced from opening the actual screens and driving them.

## 76. "1 finding blocks export" beside "no blocking findings" (21 Aug 2026)

The firm could not issue a set of documents. Export refused with "1 finding(s)
block export of this document"; the screen that exists to say why showed
**Nothing to report** and a green badge reading **no blocking findings**. There
was no way forward at all: nothing to fix, and no way to proceed.

Two computations answered the same question. Export asks `build_document`. The
validation screen asked the **field catalogue**, filtered by what the build had
found.

That filter was itself a fix — decision of 20 August, when the catalogue sweep
demanded 41 of 129 mandatory fields that never appear on screen for a small
company. Filtering the sweep by the build's findings cured the false blocks and
introduced the mirror-image defect: **a blocking item the catalogue has no row
for produced no finding at all.** A table with no rows has no catalogue row by
its nature. Nor does a missing narrative. Neither could ever have appeared.

On the firm's own file that was ten invisible blocks — nine tables and one
explanation.

**The build is now the authority and the catalogue supplies labels**, which is
the right way round: walking the authority and reaching into the catalogue for
a label cannot lose an entry, whichever way the catalogue is wrong. The three
kinds are carried apart, so each reads in the words that describe it rather
than as a generic "unanswered".

**A rule was lost and found in the same hour.** `unconfirmed_carry_forward`
lived inside the completeness sweep; rewriting the sweep dropped it, and its own
test caught it within the minute. It now sits in its own function, called
unconditionally — it cannot be derived from a build, because a carried answer
renders, prints and exports exactly like a confirmed one. The only thing wrong
with it is that nobody has looked at it yet.

## 77. A finalised year handed back a DRAFT (21 Aug 2026)

Every report finalised, and the file that came back still read "DRAFT FOR
DISCUSSION -- NOT AN ISSUED DOCUMENT · FY 2025-26".

Nothing was wrong with the stamp. The draft path is *supposed* to stamp what it
renders: it bypasses the export gate on purpose so that unanswered fields print
as they stand, and that stamp is the only thing between a half-finished file on
firm letterhead and something that reads like a signed report.

The fault was that the preview pane offered the draft **and nothing else**,
whatever state the file was in — so from a finished engagement it was the only
download on the page, and decision 76 had blocked the route that produces the
real one.

A finalised year now offers the issued document: the registered version, from
`DocumentInstance`, unstamped. Where none has been generated it says so rather
than falling back — a document that was never issued has no issued version, and
handing back a draft instead is how this started. The draft route refuses a
finalised year outright, because a bookmarked URL is exactly how the stamped
copy would come back.

## 78. CARO 3(iii) reported on transactions that never happened (21 Aug 2026)

Paragraph 3(iii) of the Order opens "whether during the year the company has
made investments in, provided any guarantee or security or granted any loans or
advances in the nature of loans ... **if so**, --". Everything from (a) to (f)
hangs off that chapeau.

The tool did not honour it. Each limb defaulted to its positive wording, so a
company that had granted nothing still issued an annexure stating that the terms
of its loans were "not prejudicial to the interest of the Company", that
repayments "have been regular", and that no amount was overdue. Assertions about
transactions that did not exist, in a document the auditor signs.

(b) and (c) had "not applicable" wording nobody selected. **(d), (e) and (f) had
no way to say it at all** — only "no amount is overdue", which is a statement
about a loan portfolio.

The facts are now derived from answers already given rather than asked again:
(a)(A) and (a)(B) establish the loans, advances, guarantees and security.

**Investments needed one more question.** They are in the chapeau and in (b) —
which reports on "the *investments made*, guarantees provided, security given
and the terms and conditions of the grant of all loans" — and nothing asked
about them. Without it, (b) could not be defaulted without asserting something
about investments nobody had established. `caro.iii.investments` asks, and
prints nothing: the Order wants the reporting that follows from investments, not
a paragraph saying whether they exist.

So (c) to (f) follow the loans alone, and (b) waits for both. A company that
made investments but granted no loans still gets asked (b) — which is the
distinction the extra question buys.

**Unanswered is not "none".** An auditor who has not reached clause (a) has not
said there were no loans. Defaulting on a question nobody answered would put the
same false assertion back with a different provenance, so `caro_no_loans_granted`
is false until both limbs are answered, and silence leaves all five blocking.
