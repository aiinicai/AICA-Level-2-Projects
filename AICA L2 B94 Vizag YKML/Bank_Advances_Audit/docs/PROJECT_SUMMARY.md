# Bank Advances Audit and Exception Review Assistant

Participant: [Enter name]. Batch: [Enter batch]. ICAI AICA Level 2.

## Problem and objective
Branch advances review combines sanctions, asset eligibility, repayment, account conduct
and evidence. A snapshot can conceal missing history or be mistaken for continuous
irregularity. This project creates reproducible source-referenced working papers while
retaining explicit auditor judgment on classification and reporting.

## Architecture
Five normalized sources -> validation/policy -> DP/conduct/dues/document screens ->
borrower cross-facility review -> findings/account coverage -> Excel/HTML reports.
Optional selected-case AI drafting supports observation wording, never approval.

## Professional decisions encoded
Differentiate creditor-deduction methods. Separate stale evidence/snapshot excess from
complete daily-window results. Check coverage before full-period conclusions. Link borrower
facilities without propagating classification. Treat branch response as an assertion.
Retain coverage review for accounts with no findings. Count distinct-account exposure.

## Demonstration and validation
Eight fictional accounts, seven borrowers, 390 daily rows. Baseline 18 findings,
4,650,000 INR exposure; high-priority unique-account exposure 3,550,000 INR.
Tests cover methods, date boundaries, missing data, borrower links, review controls,
session guards, safe exports and mocked API contract. No actual bank/client accuracy,
regulatory compliance or time-saving claim is made.

## AI contribution and limits
A previewed evidence prompt includes selected account/finding, policy, document register
and computed summaries. Optional API/manual AI produces an unapproved observation draft.
No automatic legal-source retrieval, document authentication, NPA decision or provision
calculation is implemented. Live API operation remains to be verified by the participant.

## Future scope
CBS mapping, debtor invoice ageing, receipt appropriation, document-page citations,
verified period-specific regulatory profiles and authenticated multi-reviewer sign-off.
