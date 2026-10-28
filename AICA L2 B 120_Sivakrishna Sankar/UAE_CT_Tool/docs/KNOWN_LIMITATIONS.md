# Known limitations

Read these before relying on any output. This is a **preliminary-review tool**: it prepares a draft computation and a risk report for a qualified person to review. It does not file returns and does not give tax advice.

## Tax rules
- Rules live in `ct_tool/config/rules.json`, each with a verification status.
  - Only **RB-01** (realisation-basis election) is marked `PRIMARY_READ`.
  - **FX-01, SBR-01, QFZP-01, FIL-01** are `SECONDARY` (not read from the official text).
  - **RATE-01, TR-01, INT-01, PE-01, NDE-01, LOSS-01, RP-01** are `UNVERIFIED`. The 9% rate / AED 375,000 band, 30% EBITDA / AED 12m interest cap, 75% loss cap, 50% entertainment and participation-exemption conditions are applied as configured; **check each against current Federal Decree-Law No. 47 of 2022, Cabinet/Ministerial decisions and FTA guidance before use**.
- Update the file as you verify items (change `verification`, `source`, `date_checked`); the GUI shows the status (Help > Tax rules) and the Word report repeats it.
- Elections and reliefs (realisation basis, Small Business Relief, QFZP, DTA relief, group relief, etc.) are never applied automatically; they follow your recorded answer.

## Computation scope
- Tax EBITDA for the interest limitation is **approximated** from the statements.
- Group relief, business restructuring relief, transfer pricing adjustments, Pillar Two / domestic top-up tax, and deferred tax are flagged for review but **not computed**.
- Opening tax losses, prior-period unrealised gains/losses and elections are taken as you state them; they are not verified to filed returns.
- Foreign tax credit is allowed only with proof of payment and a "not exempt in the UAE" confirmation, capped at 9% x income and at tax payable.

## Data handling
- Account mapping, risk indicators and proposed amounts are rule/pattern based on names, balances and narrations. They can be wrong; every proposal needs a human decision.
- Rates are never fetched online. USD defaults to the 3.6725 peg; every other currency needs rates you enter (P&L average, closing, equity historical). A derived translation difference is shown as a labelled equity line and needs your approval.
- The Tally / Oracle layouts are imitations written from general knowledge, not tested on real exports. Tally group sub-totals are removed only when the printed Grand Total (or debit = credit) proves double counting; side-by-side T-format TBs and multi-currency TB columns are not supported.
- A GL must be Excel or CSV. A GL in PDF is not supported.
- Text-layer PDFs are parsed by position; scanned PDFs need Tesseract. **OCR can misread digits** - the tool warns, and debit and credit totals must agree to the source.
- AI-assisted classification is **not implemented** in this version. Nothing is sent online; no API keys are stored.

## Verification gaps (see TEST_RESULTS.md)
Not tested: a real Windows machine, Excel desktop (formulas were recalculated with LibreOffice), real client data, real scanned documents, large ledgers (performance), and screen-reader accessibility.
