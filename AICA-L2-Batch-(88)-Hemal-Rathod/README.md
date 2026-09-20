# Tax Audit Applicability Decision System

**Section 44AB | 44AD | 44ADA · Professional Working Paper**

Determines whether tax audit under section 44AB of the Income-tax Act, 1961 applies for
**FY 2025-26 (AY 2026-27)**, explains the decision limb by limb with the section relied on,
and produces the working paper that evidences it.

**T R S & Associates, Chartered Accountants**
Prepared and developed as an **ICAI AICA Level 2 Capstone Project**

---

> ### Legal basis — verified 18 September 2026
>
> Built on the **Finance Act 2023** (ss. 15–17), read from the Gazette — the last amendment
> to ss. 44AB, 44AD and 44ADA. The Finance (No. 2) Act 2024 and the Finance Act 2025 were
> searched in full: neither amends these sections. The e-filing portal confirms the 1961 Act
> governs FY 2025-26. Full record and CA sign-off sheet: [`legal/sources.md`](legal/sources.md).

> ### Confidentiality
>
> Runs entirely in your browser; nothing is transmitted. Do not paste client figures into
> chat assistants or other uncontrolled AI services.

---

## Problem statement

Tax audit applicability is not a single threshold test. It turns on turnover, the cash
composition of receipts and payments, whether a presumptive scheme is available **and
declared**, whether it was used in an earlier year, profit against a deemed rate, the
constitution, residential status and the basic exemption.

And the law moved: since **AY 2024-25**, the first proviso to s. 44AB (substituted by the
Finance Act 2023) takes a person who declares under s. 44AD(1) or s. 44ADA(1) outside
s. 44AB altogether. A ₹2.5 crore trader or a ₹60 lakh professional may need no audit.

Three failures recur:

1. **Turnover-only thinking.** Under s. 44AB(d) and (e), audit can apply with turnover far
   below any limit.
2. **Undocumented conclusions.** "Not applicable" on a file evidences nothing.
3. **Guessing.** An unanswered question quietly becomes an answer.

## Solution

A browser-based system that:

- asks **only the questions the law needs on the facts entered**, and takes you straight to
  each one;
- gives a definite **APPLICABLE** or **NOT APPLICABLE**, naming the section;
- shows the statutory words it relied on, with their source;
- produces a detailed working paper, a one-page summary, a Word file and an audit trail.

It never stops at "cannot conclude". Until the answers are in, it shows the list of what is
still needed, each with a **Go to** link.

---

## Features

**Decision**
- One function per limb of s. 44AB — (a), (b), (c), (d), (e) and the first proviso
- Eligibility for ss. 44AD and 44ADA derived from facts: constitution, residential status,
  exclusions (commission, agency, goods carriage, specified deductions), profession
- s. 44AD deemed income split 6% (banking channels) / 8% (rest)
- s. 44AD(4) five-year bar and opt-out modelled
- Decides as soon as a ground is certain; asks nothing that cannot change the answer

**Explanation**
- Reasoning chain, applicability matrix, reference cards with statutory text and source
- Every conclusion carries the s. 44AA carve-out

**Documents**
- Ten-section working paper (PDF), one-page executive summary (PDF), Word, JSON audit trail
- All generated from one model

**Interface**
- Three visual modes, "Needed" tags on fields, jump-and-highlight navigation, responsive

---

## Legal framework — FY 2025-26

| Provision | Rule applied | Source |
| --- | --- | --- |
| s. 44AB(a) | Turnover > ₹1 crore; ₹10 crore where cash received ≤ 5% of all receipts **and** cash paid ≤ 5% of all payments | Consolidated Act |
| s. 44AB(b) | Gross receipts > ₹50 lakh | Consolidated Act |
| s. 44AB(c) | s. 44AE / 44BB / 44BBB income declared lower than deemed | Consolidated Act |
| s. 44AB(d) | 44ADA applies, profit < 50%, income > basic exemption — **no prior-year condition** | Consolidated Act |
| s. 44AB(e) | s. 44AD(4) applies, income > basic exemption | Consolidated Act |
| First proviso | Declaring under s. 44AD(1) / 44ADA(1) → s. 44AB does not apply | **FA 2023 s. 15** |
| s. 44AD | Ceiling ₹2 crore; ₹3 crore where cash received ≤ 5% of **turnover**; deemed 6% / 8% | **FA 2023 s. 16** |
| s. 44ADA | Ceiling ₹50 lakh; ₹75 lakh where cash received ≤ 5% of gross receipts; 50%; individual or non-LLP firm — **not HUF** | **FA 2023 s. 17**; e-filing portal |
| Basic exemption | ₹4,00,000 new regime; ₹2,50,000 old regime; nil for firms | **FA 2025** |
| Due dates | Report 30 Sep 2026 (31 Oct TP); return 31 Oct 2026 (30 Nov TP) | s. 139(1), s. 44AB |
| s. 44AA | **Not evaluated** — stated on every conclusion | — |

---

## Installation and use

```
1. Download this folder.
2. Open app/index.html in a browser.
```

No installation, no server. Full guide: [`documentation/user-guide.md`](documentation/user-guide.md).

---

## Sample cases

Twelve synthetic cases: [`sample-data/README.md`](sample-data/README.md). Worth seeing first:
**Case 4** (₹2.5 crore trader outside s. 44AB under the 2023 proviso), **Case 8**
(professional below 50% — audit in the first year), **Case 10** (the s. 44AD(4) bar).

---

## Testing

**83 assertions, all pass** — every limit at, one rupee above and one rupee below; each
Finance Act 2023 change; each error found in verification; the exact data that failed in
the earlier version. Report: [`documentation/qa-test-report.md`](documentation/qa-test-report.md).

---

## AI components and human review

AI assisted with structuring the logic, drafting explanations and building the document
templates. Prompts are in [`prompts/`](prompts/).

**The law was checked by a person against primary sources**, and that check found errors in
the first version — two of which could have produced a wrong "not applicable". They are
recorded in `legal/sources.md` §5 and each has a regression test.

The engine is deterministic and makes no AI call at run time. The final conclusion and any
filing remain with the Chartered Accountant.

---

## Limitations

[`documentation/limitations.md`](documentation/limitations.md). The main ones:

- **L-00** — CA sign-off on the verification record is pending
- **L-01** — the s. 44AD(4) bar follows the conservative reading (audit in each barred year)
- **L-05** — s. 44AA is not evaluated
- **L-06** — FY 2025-26 only; AY 2027-28 onwards falls under the Income-tax Act, 2025

---

## Project structure

```
app/              the application — open app/index.html
legal/            section notes and the verification record (sources.md)
prompts/          the development prompts
sample-data/      twelve synthetic cases
example-outputs/  generated working paper, summary, Word file, audit trail
documentation/    summary, methodology, engine, user guide, limitations, QA report
tests/            the 83-assertion suite
demo/             demonstration script and recording guide
screenshots/      interface captures
```

---

## Capstone context and disclaimer

An independent work product of T R S & Associates, prepared as an ICAI AICA Level 2
Capstone Project. Not an official application of, endorsed by, or affiliated with the
Institute of Chartered Accountants of India.

> This application is a professional decision-support and documentation tool. It is not a
> substitute for independent examination of the Income-tax Act, Rules, Finance Act
> amendments, CBDT notifications and circulars, judicial precedents, ICAI Guidance Notes and
> the facts of the particular assessee. Final professional conclusion should be made after
> verification of complete facts and applicable law.

Licence: MIT with a professional-use notice — [`LICENSE`](LICENSE).
