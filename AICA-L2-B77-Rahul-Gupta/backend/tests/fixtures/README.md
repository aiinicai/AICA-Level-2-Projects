# Test fixtures

Illustrative Schedule III financial statements (Balance Sheet, Profit & Loss, Cash Flow)
used to exercise the document pipeline end to end: upload → PyMuPDF extraction →
canonical mapping → reconciliation → review.

These are the documents that surfaced the extraction bug fixed in `extractor.py`: their
tables place each cell as a separate text object, so the old single-physical-line regex
matched nothing and produced zero line items. A correct run over all three yields
**96 line items across 4 fiscal periods** (FY2022-23 → FY2025-26; each statement carries a
comparative prior-year column).

Figures are illustrative simulation data, not real company financials.
