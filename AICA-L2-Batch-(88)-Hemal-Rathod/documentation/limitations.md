# Limitations

What this system does not do, and where it takes a position a reviewer may want to revisit.
Read this before relying on any output.

---

## A. Legal basis

### L-00 — Chartered Accountant sign-off is pending

The thresholds, rates and due dates were cross-checked on 18 September 2026 against the
Finance Act 2023 (ss. 15–17), the Finance (No. 2) Act 2024, the Finance Act 2025 and the
Income Tax Department e-filing portal. See [`../legal/sources.md`](../legal/sources.md).

That is research, not professional sign-off. Complete section 6 of `sources.md` and the
`caSignOff` block in `app/js/ruleset.js` before issuing working papers from this tool.

### L-01 — The s. 44AD(4) bar: conservative reading adopted

Where the assessee is within a five-year bar under s. 44AD(4), the engine treats audit as
required **in every barred year** in which total income exceeds the basic exemption,
whatever the turnover.

This is the literal reading of ss. 44AD(4), 44AD(5) and 44AB(e), and the position reported
from the ICAI Guidance Note (Revised 2026). A narrower view — audit only in the year of
opting out — exists. The conservative reading was chosen because the cost of a wrong "not
applicable" (a notice for failure to audit) is far greater than the cost of a wrong
"applicable". Every barred-year result carries a note saying so.

### L-02 — Opting out while profit still meets the deemed rate

If an assessee who used s. 44AD in the preceding five years now computes income under the
regular provisions but still declares at least the deemed rate, the engine does not treat
this as triggering s. 44AD(4). The limb is applied only where profit falls below the deemed
income. This is the prevalent reading; a stricter one exists.

### L-03 — Verbatim text is partial

Statutory text is quoted from the Finance Act 2023 Gazette and from the consolidated
s. 44AB. Gaps in the fetched text are marked `[...]`. The verbatim text of s. 44AD(4) and
(5) was not retrieved; those reference cards say so and do not paraphrase the section as
though quoting it.

### L-04 — Due dates move

Due dates are the statutory dates. No CBDT extension had been reported for AY 2026-27 as at
16 September 2026. Check for an extension before relying on any date.

### L-05 — Section 44AA is not evaluated

Books of account are a separate obligation with different thresholds. Every conclusion says
so. Determine the s. 44AA position separately.

### L-06 — FY 2025-26 only

AY 2027-28 onwards falls under the **Income-tax Act, 2025**, with renumbered provisions. That
needs a new engine, not a new parameter block.

---

## B. Scope

### L-07 — Not modelled

| Not modelled | How it is handled |
| --- | --- |
| Turnover computation for derivatives and speculative transactions | Enter turnover computed per the ICAI Guidance Note; a note reminds the reviewer |
| Business and profession carried on together | Evaluate each separately; a note explains |
| Trust / institution audit under its own provisions | Constitution note says it is not evaluated |
| Audit under the Companies Act, LLP Act or a co-operative law as an obligation | Affects the report form only |
| The return due date where audit is not applicable | Not computed |

### L-08 — Facts are taken as answered

Eligibility for the presumptive schemes is derived from the facts entered — constitution,
residential status, the exclusions ticked and the profession. The engine cannot detect, for
example, commission income from a profit figure. A wrong answer produces a wrong result.

### L-09 — Inclusions in "all amounts received" and "all payments made"

The s. 44AB(a) cash test uses all amounts received and all payments made, as the statute
words it. Which items belong in those totals (loans, capital receipts and so on) is a
question for the ICAI Guidance Note. The tool takes the figures as entered.

---

## C. Computation

### L-10 — Boundary convention

"Exceeds" means strictly greater than. A figure exactly equal to a limit does not exceed it.
The 5% tests are "does not exceed 5%": exactly 5.00% passes. Both are implemented once and
tested at the boundary.

### L-11 — Nil totals

Where total receipts or total payments are nil and cash is nil, the cash test is treated as
satisfied — nil does not exceed 5% of nil. The engine adds a note asking the reviewer to
confirm that nothing was realised or paid.

### L-12 — Deemed income without the split

Section 44AD deemed income lies between 6% and 8% of turnover. Where declared profit is at
least 8%, or below 6%, the comparison is settled without the banking / non-banking split,
and the tool does not ask for it.

---

## D. Outputs

### L-13 — Word pagination belongs to Word

The `.doc` file carries Word page setup, running header, footer and page-number fields.
Word controls the final layout. Check before sending.

### L-14 — One-page fit is measured on the sample cases

All twelve sample cases produce a one-page executive summary. Unusually long names or many
notes could overflow. The detailed working paper has no such limit.

### L-15 — Print settings

Choose A4, portrait, with background graphics on, or the status colours will not print.

### L-16 — Nothing is saved

Only the theme choice persists. Figures are lost on refresh. Export before closing.

---

## E. AI and privacy

### L-17 — AI built it; AI did not supply the law

AI assisted with structure, drafting and templates. The legal parameters were checked
against Gazette text and official sources, recorded in `legal/sources.md`. The engine makes
no AI call at run time.

### L-18 — Client-side only

Nothing is transmitted. That protection ends if figures are pasted into a chat assistant or
an online converter.

---

## Summary for a reviewer

The tool applies the verified law for FY 2025-26 to the facts it is given, asks for exactly
the facts the law needs, and names the section on which its conclusion rests. It takes the
conservative position on the s. 44AD(4) bar, it does not evaluate s. 44AA, and it depends
on the accuracy of the answers. The final conclusion and any filing remain with the
Chartered Accountant.
