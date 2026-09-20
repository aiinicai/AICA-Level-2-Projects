# Capstone Project Summary

## Tax Audit Applicability Decision System

**ICAI AICA Level 2 — Certificate Course**
**Individual Capstone Project**

| | |
| --- | --- |
| **Participant** | _[Your name]_ |
| **Membership number** | _[M. No.]_ |
| **Firm** | T R S & Associates, Chartered Accountants |
| **Batch** | _[Batch number / dates]_ |
| **Date of submission** | _[Date]_ |
| **Project title** | Tax Audit Applicability Decision System |
| **Domain** | Direct tax — section 44AB, read with ss. 44AD and 44ADA |
| **Law applied** | Income-tax Act, 1961 — FY 2025-26 / AY 2026-27, as amended up to the Finance Act 2025 |

> **Convert this file to PDF before zipping.** Paste into Word, apply heading styles, export
> as PDF, and save as `01_PROJECT_SUMMARY.pdf`. Fill in the bracketed fields first.

---

## 1. Problem statement

Whether tax audit under section 44AB applies is not a single threshold test. On one set of
facts it turns on turnover, the cash composition of receipts and payments, whether a
presumptive scheme is available **and declared**, whether it was used in an earlier year,
profit against a deemed rate, the constitution, residential status and the basic exemption.

The law also moved. Since AY 2024-25, the **first proviso to s. 44AB, substituted by the
Finance Act 2023**, takes a person declaring under s. 44AD(1) or s. 44ADA(1) outside
s. 44AB altogether. Many checklists still do not reflect it.

Three failures recur:

1. **Turnover-only thinking.** Under s. 44AB(d) and (e), audit can apply with turnover far
   below any limit.
2. **Undocumented conclusions.** "Not applicable" on a file evidences nothing if a notice
   arrives two years later.
3. **Guessing.** An unanswered question quietly becomes an answer.

---

## 2. Solution

A browser-based decision-support and working-paper system that:

- asks **only the questions the law needs on the facts entered**, marks each required field,
  and takes the user straight to it;
- gives a definite **APPLICABLE** or **NOT APPLICABLE**, naming the section of s. 44AB relied on;
- shows the statutory words behind each limb, with their source;
- generates a detailed working paper, a one-page summary, a Word document and an audit trail.

It never stops at "cannot conclude". Until the answers are in, it lists exactly what is still
needed and why, each with a **Go to** link. As soon as a ground for audit is certain, it
decides — it does not ask questions that can only add further grounds.

---

## 3. Legal basis — verified

The engine applies the law for FY 2025-26, verified on 18 September 2026:

| Source | Finding |
| --- | --- |
| **Finance Act 2023, ss. 15–17** (Gazette text) | First proviso to s. 44AB substituted; s. 44AD ceiling ₹3 crore where cash receipts ≤ 5% of turnover; s. 44ADA ceiling ₹75 lakh where cash receipts ≤ 5% of gross receipts |
| **Finance (No. 2) Act 2024**, full text | No amendment to ss. 44AB, 44AD, 44ADA |
| **Finance Act 2025**, full text | No amendment to these sections; new-regime nil slab ₹4,00,000 for AY 2026-27 |
| **Income Tax Department e-filing portal** | Income-tax Act, 1961 governs FY 2025-26; s. 44ADA is not available to an HUF |

The research record, with a sign-off sheet for the Chartered Accountant, is in
`legal/sources.md`.

---

## 4. Human-in-the-loop: what verification caught

The first version of this tool was built on thresholds carried over from an earlier
spreadsheet-style implementation. Checking them against the statute found eight errors,
now corrected and each covered by a test. Two could have told a client that no audit was
needed when it was:

- **s. 44AB(d)** — the tool required a professional to have used s. 44ADA in an earlier year
  before a low-profit declaration triggered audit. The clause contains no such condition.
- **s. 44AD(4) bar** — not modelled. During the five-year bar, audit applies whenever total
  income exceeds the basic exemption, whatever the turnover.

Others: the first proviso was missing; the ₹3 crore s. 44AD ceiling was gated on the wrong
cash test; an HUF was allowed s. 44ADA; the 6% / 8% deemed rate was applied to the whole
turnover instead of by component; the transfer-pricing audit report date was wrong; and nil
receipts stalled the decision instead of satisfying the cash test.

This is the central lesson of the project: **AI accelerated the build; a professional
check of the law made it correct.**

---

## 5. Features

**Decision** — one function per limb of s. 44AB, plus the first proviso; eligibility for
ss. 44AD and 44ADA derived from constitution, residential status, exclusions and profession;
deemed income split by channel; the s. 44AD(4) bar and opt-out.

**Explanation** — reasoning chain, applicability matrix, reference cards separating
statutory text, the firm's explanation, and application to the facts.

**Documents** — ten-section working paper (PDF), one-page summary (PDF), Word, JSON audit
trail, all generated from one model.

**Interface** — three visual modes, "Needed" tags, jump-and-highlight navigation, responsive
layout, keyboard accessible.

---

## 6. Technology

| Layer | Choice | Reason |
| --- | --- | --- |
| Runtime | Browser, plain scripts | Opens by double-clicking; no toolchain |
| Logic | JavaScript in four layers: parameters → arithmetic → legal rules → presentation | Testable; every threshold in one file |
| Documents | Print CSS (A4) and Word page setup | No libraries to maintain |
| AI at run time | **None** | Determinism and confidentiality |

---

## 7. AI components

Used during development to structure the decision logic, draft the explanations, build the
document templates and propose exception conditions. The prompts are published in `prompts/`.

Not trusted for the law: every threshold was checked against Gazette text or an official
source, and the statutory words in the reference cards are quoted only where they were read
from a source — gaps are marked `[...]` rather than filled in.

The engine is deterministic. The final conclusion and any filing remain with the Chartered
Accountant.

---

## 8. Testing

**83 assertions, all passing**, including every limit at, one rupee above and one rupee
below; each Finance Act 2023 change; a regression test for each error found in
verification; and the exact data that failed in the first version. All twelve one-page
summaries fit a single A4 page. Report: `documentation/qa-test-report.md`.

---

## 9. Limitations

- Chartered Accountant sign-off on the verification record is pending.
- The s. 44AD(4) bar follows the conservative reading — audit in each barred year where
  income exceeds the basic exemption.
- Section 44AA (books of account) is not evaluated; every conclusion says so.
- FY 2025-26 only. AY 2027-28 onwards falls under the Income-tax Act, 2025.

Full register: `documentation/limitations.md`.

---

## 10. Demonstration

The video walks through: the user's own test data typed live, with the tool asking two
questions and one answer flipping the result; **Case 4**, a ₹2.5 crore trader taken outside
s. 44AB by the 2023 proviso; **Case 8**, the s. 44AB(d) error caught by verification; and
**Case 10**, audit applying during the s. 44AD(4) bar at ₹75 lakh turnover.

---

## 11. Future roadmap

1. Complete the Chartered Accountant sign-off; check for any CBDT due-date extension
2. A new engine for the Income-tax Act, 2025 from AY 2027-28
3. A companion engine for s. 44AA
4. Batch screening across a client list

---

## 12. Originality and disclaimer

The interface, design system, decision architecture, documents and icon set are original to
this project. It is an independent work product of T R S & Associates, not an official
application of, or endorsed by, the Institute of Chartered Accountants of India.

> This application is a professional decision-support and documentation tool. It is not a
> substitute for independent examination of the Income-tax Act, Rules, Finance Act
> amendments, CBDT notifications and circulars, judicial precedents, ICAI Guidance Notes and
> the facts of the particular assessee. Final professional conclusion should be made after
> verification of complete facts and applicable law.

---

## Contents of this submission

```
01_PROJECT_SUMMARY.pdf   this document
app/                     executable — open app/index.html
prompts/                 prompt library
example-outputs/         generated working paper, summary, Word file, audit trail
sample-data/             twelve synthetic cases
documentation/           methodology, engine, user guide, limitations, QA report
legal/                   section notes and the verification record
tests/                   the 83-assertion suite
demo/                    demonstration script, recording guide, video link
screenshots/             interface captures
```
