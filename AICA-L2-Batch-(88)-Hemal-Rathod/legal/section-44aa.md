# Section 44AA — Maintenance of books of account

> **Statutory text is not reproduced in this file.** See §5 of [`sources.md`](sources.md).

---

## This section is NOT evaluated by the application

State this plainly, because it is the most likely misreading of a "tax audit not
applicable" conclusion.

Section 44AA imposes an obligation to **keep and maintain books of account**. Section 44AB
imposes an obligation to have accounts **audited**. They are different obligations with
different thresholds. Books may be required where audit is not.

The application evaluates section 44AB only. It does **not** compute the section 44AA
position, and it must not be read as clearing the assessee of that obligation.

---

## How the application handles it

**1. A reference card that says so.** Every result set includes a section 44AA card whose
conclusion reads "Not evaluated — determine separately", marked with the same review
styling as any unresolved limb. It is not tucked into a footnote.

**2. In the NOT APPLICABLE narrative.** Where audit is not applicable, one of the stated
consequences is:

> The obligation to maintain books of account under section 44AA is separate and continues
> to apply where the thresholds of that section are crossed. It has not been evaluated here.

That sentence is generated as part of the conclusion, so it appears on screen, in the
executive one-pager, in the detailed working paper and in the Word document.

**3. In the audit trail.** The section 44AA card is included in the reference set recorded
in the exported JSON, carrying its "not evaluated" status.

---

## Simplified professional explanation

Specified professions are required to maintain prescribed books. Other persons carrying on
business or a non-specified profession are required to maintain books where income or
turnover exceeds the prescribed limits. Separate limits apply where a presumptive scheme
has been availed and later departed from.

---

## Why it was left out of the engine

Two reasons, both deliberate:

- **Different fact pattern.** Section 44AA turns on income as well as turnover, and on
  whether the profession is a specified one, across a different set of thresholds. Bolting
  it onto a 44AB engine would have meant a second parameter set to verify for the same
  release, with no shared logic.

- **Scope discipline.** The project brief is a tax-audit applicability system. Extending it
  to a books-of-account determination without the same verification rigour would produce a
  second confident answer on an unverified basis — the failure mode this whole design is
  built to avoid.

If the firm later wants it, the natural shape is a sibling engine module with its own
parameter block in `ruleset.js` and its own entries in `sources.md`, surfaced as a second
result alongside the audit result rather than folded into it.

---

## What the reviewer should do

Determine the section 44AA position separately for every assessee, whatever this
application concludes about section 44AB, and record that determination on the file
alongside this working paper.
