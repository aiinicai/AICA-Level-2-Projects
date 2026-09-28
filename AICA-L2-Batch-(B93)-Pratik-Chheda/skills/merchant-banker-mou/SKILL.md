---
name: merchant-banker-mou
description: Fills the approved Sample Advisory Memorandum of Understanding with a Book Running Lead Manager (BRLM, SEBI registered merchant banker) for an IPO mandate, producing a .docx plus matching .pdf in the exact approved wording and layout. Use whenever a merchant banker MOU, BRLM MOU, lead manager MOU or MOU with a merchant banker is requested for a Sample Advisory client. Never rewrites clauses; it only fills the template's blanks (parties, Issuer, periods, fees, milestones, signatories, dates).
---

# Merchant banker MOU (Sample Advisory and BRLM)

The approved MOU lives in `assets/MOU_with_BRLM_template.docx`. Its 15 clauses,
Annexure A, tables and formatting are final. Do not redraft, summarise, reorder
or "improve" any wording. The only job is to fill the blanks with
`scripts/fill_mou.py`, then convert to PDF.

## Inputs

Build a `content.json` shaped like `references/sample_content.json`:

| Field | Meaning |
|---|---|
| `effective_date` | YYYY-MM-DD; default today (India) |
| `issuer` | Client legal name, the IPO Issuer |
| `brlm.name`, `brlm.sebi_registration`, `brlm.cin`, `brlm.companies_act` (2013 or 1956), `brlm.registered_office`, `brlm.signatory_name`, `brlm.signatory_designation` | Merchant banker details |
| `advisor.signatory_name`, `advisor.signatory_designation` | Sample Advisory signatory; default Mr. A. Partner, Director |
| `retainer_inr` | Fixed retainership fee in rupees (number) |
| `success_fee_pct`, optional `success_fee_inr` | Success fee; the "(or INR …)" alternative is removed when no amount is given |
| `milestones` | Exactly 5 objects `{pct, inr}`; percentages must total 100 when all are given |
| `confidentiality_years`, `non_poaching_months`, `term_months`, `notice_days`, `cure_days` | Integers; written out as "2 (two) years" etc. |
| `arbitration_city`, optional `courts_city` | Default Mumbai |
| `invoice_days` | Default 15 |

Sample Advisory's own name, CIN (U00000MH2020PTC000000), Companies Act 2013 and
registered office (Registered office address, City 400001) are built into the script.

If a required value is missing, do not invent it: stop and report which field
is missing. Do not use placeholders in a final MOU.

## Steps

1. Write `content.json` from the request.
2. Fill the template:
   ```
   python scripts/fill_mou.py content.json "<Output name>.docx"
   ```
   The script replaces blanks inside their own runs, writes amounts in Indian
   words (Rupees Two Lakh Fifty Thousand Only) and periods in words, and exits
   with code 2 listing anything left unfilled. Fix the input and rerun until it
   prints "Saved".
3. Convert to PDF:
   ```
   python /mnt/skills/public/docx/scripts/office/soffice.py --headless --convert-to pdf "<Output name>.docx"
   ```
   If that helper path is missing, use `soffice --headless --convert-to pdf`.
4. Check the PDF: open it and confirm the date, both party paragraphs, clause
   1.1 Issuer, clauses 9.3, 11.1, 12.1, 12.2, 15.4, Annexure A fees, the
   milestone table and both signature blocks read correctly.
5. Save both files to `/mnt/user-data/outputs/` named
   `MB_MOU_<BRLM short name>_Project_<Code>.docx` and `.pdf`.

Finish with a short summary listing the values used.
