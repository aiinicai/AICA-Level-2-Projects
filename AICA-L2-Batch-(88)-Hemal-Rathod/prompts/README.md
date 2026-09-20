# Prompt library

The prompts used while building the Tax Audit Applicability Decision System, published so
that the AI component of this Capstone is auditable rather than asserted.

---

## Important: these prompts do not run at run time

The shipped application makes **no AI calls**. The decision engine is deterministic
JavaScript applying parameters a Chartered Accountant has verified. Open the browser
network tab while using it — nothing leaves the machine.

These prompts were used during **development**, to:

- structure the decision logic before it was written
- draft the plain-language explanations that the engine emits
- draft the working paper narrative and document templates
- generate candidate exception conditions for the firm to accept or reject
- produce review checklists used while testing

Every output was reviewed, edited and accepted by a human before it entered the codebase.

---

## The one thing AI was not allowed to do

**Supply the law.**

No threshold, rate, percentage, due date, section number or statutory quotation in this
project came from a language model's memory. The numeric parameters were first carried over
from the firm's own earlier implementation. On 18 September 2026 every one of them was
cross-checked against primary sources — the Gazette texts of the Finance Act 2023, the
Finance (No. 2) Act 2024 and the Finance Act 2025, and the Income Tax Department e-filing
portal. That check found eight errors in the first version, all now corrected. The record,
and the Chartered Accountant sign-off table, are in [`../legal/sources.md`](../legal/sources.md).

Statutory text is quoted only where it was read from a source, and each quotation names
that source. `01_legal_rule_extraction.md` is built around this constraint: it is a prompt
for *structuring* a provision the human has already read, not for *recalling* one.

The prompts below are kept **as used**. Where a prompt describes the first version's
REVIEW REQUIRED outcome, a revision note at its head says what replaced it.

---

## Files

| File | Purpose |
| --- | --- |
| [`01_legal_rule_extraction.md`](01_legal_rule_extraction.md) | Turn a provision the human has read into a machine-evaluable test record |
| [`02_tax_audit_reasoning.md`](02_tax_audit_reasoning.md) | Generate the ordered reasoning chain from test records |
| [`03_non_applicability_reason.md`](03_non_applicability_reason.md) | Write a positively-reasoned NOT APPLICABLE conclusion |
| [`04_applicability_reason.md`](04_applicability_reason.md) | Write an APPLICABLE conclusion with grounds and consequences |
| [`05_section_reference_generation.md`](05_section_reference_generation.md) | Build a reference card separating text, interpretation and application |
| [`06_working_paper_generation.md`](06_working_paper_generation.md) | Assemble the ten-section working paper |
| [`07_exception_detection.md`](07_exception_detection.md) | Propose conditions the engine should refuse to conclude on |
| [`08_review_checklist.md`](08_review_checklist.md) | Produce the reviewer checklist and the QA boundary matrix |

---

## Structure

Each file carries: **Objective**, **Inputs**, **Instructions**, **Expected output**,
**Validation requirements**, **Limitations**.

The Validation section is the important one. It states what a human must check before the
output is used, and every prompt has at least one check that cannot be delegated back to
the model.

---

## Reusing these

These prompts assume a competent reviewer who will reject bad output. They are not
autonomous agents and should not be wired to one. In particular, do not remove the
"do not supply the law" constraint from `01`: it is what keeps the project's legal content
traceable to a human who read a primary source.
