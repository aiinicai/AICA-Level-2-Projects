# Synthetic dataset guide

This dataset is entirely fictional and created for the AuditSense demonstration. It must not be replaced with real audit findings, bank records, customer information, or internal policies.

## Fields

- `id`: synthetic finding identifier.
- `process`: fictional banking process.
- `title`: short finding title.
- `draft_observation`: text submitted for AI review.
- `evidence`: fictional evidence supplied to the reviewer.
- `manual_status`: expected review status assigned by a human before testing the AI.
- `missing_elements`: deliberately missing or weak C-C-C-I-R elements.
- `unsupported_claims`: claims that should be flagged for verification.

## Labelling approach

- `review_ready` means all five elements are sufficiently represented and the evidence is aligned with the wording.
- `needs_minor_revision` means the observation is substantially usable but needs one or more clarifications.
- `needs_major_revision` means multiple elements are missing, vague, or unsupported.

The labels are reference answers for evaluation, not automatic audit conclusions.
