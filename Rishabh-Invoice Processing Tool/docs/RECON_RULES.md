# Reconciliation rules (task 4C)

Matching runs per supplier GSTIN in five stages. A record is matched only when exactly one
candidate qualifies; two or more candidates always go to manual review.

## Invoice number normalisation
Stored as `invoice_no_normalized`; the original is always kept. Uppercase; remove spaces and
`/ - _ . \ #`; strip FY fragments (`2025-26`, `25-26`, `2526`) only when they are a separate
prefix/suffix segment; strip leading zeros of the trailing number block.
`INV/001`, `INV-001`, `inv 0001` → `INV1`. A normalised match alone gives at most
PARTIALLY_MATCHED unless amounts and date also agree.

## Stages
1. Exact – same GSTIN + identical raw invoice no + same doc type. Confidence 1.00.
2. Normalised – same GSTIN + same normalised no. 0.95 if date and amounts within tolerance.
3. Financial – same GSTIN + date within tolerance + taxable and each tax head within
   tolerance, only one candidate. 0.85.
4. Fuzzy – same GSTIN + invoice-no similarity ≥ threshold (rapidfuzz ratio on normalised
   numbers) + amounts within tolerance. 0.70.
5. Manual – user links records with a remark ("Manual").

Three-way mode pairs Tally ↔ 2B first (the statutory pair), then attaches the IPT invoice.

## Default tolerances (conservative, user-configurable)
| Setting | Default |
| --- | --- |
| Taxable value | ₹1.00 |
| CGST / SGST / IGST / Cess (each) | ₹1.00 |
| Invoice total | ₹1.00 |
| Date difference | 0 days |
| Invoice-number similarity | 90% |

## Status order (first rule that fires wins; all differences still listed in reasons)
| # | Status | Rule |
| --- | --- | --- |
| 1 | DUPLICATE | Same GSTIN + normalised no + doc type twice within one source |
| 2 | AMENDED | 2B row from B2BA/CDNRA whose original doc no matches; latest amendment is effective |
| 3 | GSTIN_MISMATCH | Number, date, amounts match a record under a different GSTIN |
| 4 | CDN_DIFFERENCE | Credit/debit note doc type or net effect differs between sources |
| 5 | NOT_IN_2B / NOT_IN_BOOKS | No counterpart in that source after stages 1–4 |
| 6 | AMOUNT_MISMATCH | Matched, but taxable or any tax head outside tolerance |
| 7 | PARTIALLY_MATCHED | Amounts within tolerance; number beyond normalisation or date outside tolerance |
| 8 | NOT_IN_IPT | Books and 2B agree but there is no IPT invoice (ranked here so it never hides a books-vs-2B difference; the reason list always shows it) |
| 9 | MATCHED | All critical fields within tolerance; GSTIN identical |

A GSTIN difference or any tax head outside tolerance can never be MATCHED.

## Suggested actions
| Status | Action |
| --- | --- |
| NOT_IN_2B | Check supplier's GSTR-1/IFF filing; confirm the invoice was reported; follow up; consider deferring ITC |
| NOT_IN_BOOKS | Check if received but not booked; verify purchase entry; check other party/period |
| AMOUNT_MISMATCH | Verify taxable value and rate; check credit/debit notes; check rounding; ask supplier to amend if wrong |
| GSTIN_MISMATCH | Verify GSTIN on invoice; correct Tally party ledger GSTIN; check multiple registrations |
| PARTIALLY_MATCHED | Verify invoice number, series and date on the original document |
| DUPLICATE | Confirm double booking; cancel duplicate voucher after review |
| AMENDED | Use amended values; check books reflect the amendment |
| CDN_DIFFERENCE | Match note to original invoice; check note type and sign in books |
| NOT_IN_IPT | Upload the source invoice for document support |

Action status values: Pending, Under Review, Resolved, Accepted, Rejected.
