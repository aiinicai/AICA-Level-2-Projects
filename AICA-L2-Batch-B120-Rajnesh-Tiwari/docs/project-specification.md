# AuditSense — Project Specification

## Project objective

AuditSense is a Streamlit application that reviews fictional internal-audit findings and helps an auditor identify missing or weak elements in the observation.

The application checks five elements:

1. Condition — what happened?
2. Criteria — what should have happened?
3. Cause — why did it happen?
4. Impact — why does it matter?
5. Recommendation — what should management do?

It also identifies claims that are not supported by the supplied evidence and proposes questions or clearer wording.

## Intended user

An internal auditor preparing or reviewing a draft finding in a banking environment.

## Minimum viable product

- A Streamlit page for entering a draft finding and its supporting evidence.
- A sample-finding selector using fictional banking scenarios.
- An LLM-powered structured review.
- Status for each of the five finding elements: present, weak, missing, or requires verification.
- Unsupported-claim warnings.
- Questions for the auditor.
- An optional suggested rewrite that does not add unverified facts.
- Export of the review as JSON or Markdown.

## Explicit boundaries

- All data is fictional and created for demonstration purposes.
- No customer records, bank policies, real audit findings, or work-derived data may be used.
- The application must not make fraud, legal, regulatory, compliance, or final-audit conclusions.
- The application must not invent facts, dates, amounts, causes, impacts, controls, or evidence.
- AI output is advisory. The auditor remains responsible for evidence assessment, materiality, risk assessment, wording, and final approval.

## Initial synthetic scenarios

- Privileged-user access reviews
- Payment processing exceptions
- Loan-file documentation
- Account reconciliations
- KYC file completeness

## Success criteria

The first version is successful if it can:

- Review a finding end to end from the Streamlit interface.
- Return valid structured output reliably.
- Correctly identify most deliberately missing elements in the synthetic evaluation set.
- Flag unsupported or overly broad claims without presenting them as facts.
- Keep AI suggestions visibly separate from auditor-entered evidence and judgment.
- Run using only fictional data and an environment-provided API key.

## Evaluation targets

These are project targets, not guarantees:

- At least 80% accuracy for deliberately missing-element detection.
- At least 75% accuracy for unsupported-claim detection.
- 100% valid output against the defined JSON schema during the final test run.
- No observed invented facts in the final evaluation set.

## Proposed review statuses

- `review_ready`
- `needs_minor_revision`
- `needs_major_revision`
- `requires_auditor_verification`

## Day 1 completion checklist

- [x] Use case selected
- [x] MVP boundaries documented
- [x] Synthetic-data rule documented
- [x] Human-in-the-loop rule documented
- [x] Evaluation targets documented
- [ ] Synthetic dataset created on Day 2
- [x] Synthetic dataset created on Day 2
- [ ] Streamlit scaffold created on Day 3
