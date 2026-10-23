# LedgerLens

*Tally books in. Reviewed Schedule III statements out.*

LedgerLens turns a TallyPrime trial balance into draft Schedule III (Division I, non-Ind AS) financial statements
with an AS 3 cash flow and numbered notes, reviews them, and separately audits a Day Book for red flags. Rules and
arithmetic run on your computer; an AI review (Google Gemini) is optional and clearly labelled.

## Run

```bash
pip install -r requirements.txt
python -m streamlit run app.py        # run from the project folder so .streamlit/config.toml (the theme) is read
```

After any code change, stop the app (Ctrl+C) and start it again; refreshing the browser does not reload Python modules.

The sidebar has **Home**, three tools and **Settings & AI**:

- **Financial Statements Builder** runs the whole pipeline in six steps: load a trial balance (Excel or CSV upload,
  or live from TallyPrime), check it, review and override the ledger mapping, preview the statements, review (tie-outs,
  ratios, checklist, optional Gemini), and download the four Word/Excel files. Select a line on a statement, or use the
  Notes tab, to open its note. Overrides can be saved as JSON and reloaded next year. If the mapping or numbers change
  after the AI review or the files were produced, the page says they are stale instead of showing old results.
- **Day Book Audit** reads a Day Book and runs the accounting rules, the narration themes, and the amount-pattern tests.
- **Settings & AI** holds the Gemini key, model and consent once for every tool, with a connection test.

**Statements are linked to their notes.** In Excel every statement figure that has a note is a formula reading the note's
total (change a figure in a note and the statements, the check row and the cash flow follow); totals are formulas; each
note number is a link to the note, and each note links back. The calculated values are stored too, so previews that do
not calculate still show numbers. In Word each note number is a link to its note and back.

**Trial balance straight from Tally.** Upload TallyPrime's own Excel trial balance export, unchanged (Trial Balance,
F2 to set the whole financial year, Alt+E, Excel). The tool reads the company and period from the file and takes
Dr/Cr from each cell's number format, where Tally keeps it. Tally's export has no ledger groups, so they are worked
out from the ledger names and balance sides: clear names (Cash, Share Capital, HDFC Bank, GST ledgers) are treated as
certain, while ledgers that could only be guessed (parties, by Dr or Cr) are flagged for confirmation. For an exact
mapping also upload a ledger list with groups. A trial balance for a single day is refused, because it holds no year
of transactions. `samples/tally_trial_balance_export.xlsx` is a full-year example in Tally's layout.

**Trial balance upload (Excel or CSV).** One row per ledger with `name, group, opening_amount, opening_dr_cr,
closing_amount, closing_dr_cr` (`period_debit`, `period_credit` optional). The page has an Excel template and a CSV
layout to download. Excel files may have title rows above the header, several sheets (the first with a trial balance
is used) and a Total row; header names such as Ledger Name, Under and Opening Balance are recognised, and amounts
typed as text such as `1,23,456.00` are read. A Tally trial balance export is group-level, so use the template layout.

Optional AI review: put `GEMINI_API_KEY=your_key` in the `.env` file (copy `.env.example`), or paste the key on the
Settings & AI page. The key is never written to disk by the app and `.env` is git-ignored.

Try it with the fictional sample: upload `samples/sample_daybook.xml`
(regenerate with `python samples/make_sample.py`).

## Formatting checker (not in the app for now)

The Format Check page has been taken out of the app. The checker itself, `daybook_auditor/fs_format.py`, stays in the project:
the tests run it over every Word and Excel file the Builder writes, so the statements keep consistent fonts, dd/mm/yyyy dates
and bracketed negatives. `samples/make_sample_fs.py` still writes the clean and faulty test statements.

## Tally to Schedule III (`fsbuilder/`)

Builds Schedule III (Division I, non-Ind AS) statements from a Tally trial balance.

- `tb.py` loads a ledger-level trial balance (CSV snapshot, or live from TallyPrime's XML server on
  localhost:9000) and fixes the one thing Tally does that would double count: the year's profit
  appearing inside a Reserves ledger. Every change is listed in `TrialBalance.adjustments`.
- `rulebook_non_ind_as.json` is the editable mapping: Tally group / ledger name pattern -> Schedule III line,
  with a `review` note wherever a person must confirm a judgement (bank FD is not an investment,
  outstanding expenses are not provisions, related-party loans, current maturities of term loans).
  Debit balances in creditors and credit balances in debtors are moved to the other side, and GST input
  and output are netted per tax head.
- `mapping.py` applies the rules (user overrides win; unmatched ledgers come out as UNMAPPED), and
  `statements.py` totals the lines and checks assets = equity + liabilities.

Generate the statements (Word and Excel) from the sample or from live Tally:

```bash
python -m fsbuilder samples/rpi_trial_balance.csv --groups samples/rpi_groups.csv   --company "Rajasthan Precision Industries Private Limited" --from 2024-04-01 --to 2025-03-31 --out out
python -m fsbuilder --tally --company "<name as in Tally>" --from 2024-04-01 --to 2025-03-31 --out out
```

Output: Balance Sheet, Statement of Profit and Loss, AS 3 Cash Flow Statement (indirect method) and numbered notes, with the previous-year column taken
from Tally's opening balances. Judgement calls are marked `[R#]` on the face of the statements and listed
under "Open items for the reviewer" with preliminary observations `[O#]` (no tax provision, stock unchanged,
no previous-year P&L). Information the Companies Act requires that Tally cannot hold (ageing, share capital
details, auditors' payments, related parties) is listed as "information required", never invented. The Excel
file also has an Open items sheet with a reviewer-response column and the full ledger Mapping sheet.
The cash flow statement is built from the same rounded figures as the Balance Sheet, with every movement classified
as operating, investing or financing, and must reconcile to closing cash (opening cash + net movement = closing cash)
or the build reports the difference. Bank deposits are treated as investing until maturity is confirmed; interest paid
and received are taken from the P&L; previous-year cash flows need the earlier year's data.
The generated files pass this project's own formatting checker (fonts, dd/mm/yyyy, bracketed negatives).
Excel shows lakh grouping only if Windows is set to the English (India) region; Word always does.

### Reviewer (`fsbuilder/reviewer/`)

`python -m fsbuilder ... --review` writes a reviewer's report (Word memo + Excel detail) next to the statements:

- **Casting and tie-outs** (72 checks on the sample): every statement foots, every note adds up and agrees to its
  face, profit agrees between the P&L and the reserves, cash flow rolls and agrees to the balance sheet, PPE rolls
  forward, and the statements agree to the unrounded Tally books. The tests break the statements on purpose and
  require the right check to fail.
- **The 11 Schedule III ratios** with the 25% change test. Only ratios computable from both balance sheets are
  tested (current ratio and debt-equity here); the rest need the previous year's profit and loss and are shown as
  not measurable rather than guessed.
- **Disclosure checklist** (about 50 items) and **applicability screens** (small company, CARO 2020, internal
  financial controls report, tax audit, CSR) judged from the books. Items Tally cannot answer are listed as
  "Information required" with what to obtain. Thresholds live in `reviewer/checklist.py`; verify them.
- **AI (Gemini), optional:** `--ai` with `GEMINI_API_KEY` drafts the explanation for ratios that moved more than
  25% and raises analytical observations. The model gets a table of facts with IDs and must cite them as `{F12}`;
  our code inserts the figures. Figures it writes itself, unknown IDs and uncited observations are labelled
  "verify". Only figures and labels are sent to Google, never ledger or party names. Without a key the AI sections
  say they were not run. Everything labelled "AI draft" must be checked by a person.

On the sample company (`samples/rpi_trial_balance.csv`) all 68 ledgers map and the totals agree to the
rupee with Tally's own Balance Sheet (Rs 1,50,86,416.08) and P&L (profit Rs 24,89,415.93).
The live Tally client follows Tally's documented XML format and is covered by tests against a stand-in
for the HTTP call, but has not yet been run against a live TallyPrime.

## Exporting from Tally Prime

Day Book → **Alt+E** (Export) → format **XML** (best) or Excel, **Detailed** view, for the period to review.
XML carries every ledger line, which the cash, TDS, GST and Dr = Cr checks need. A condensed
one-line-per-voucher Excel export still loads, but those checks are skipped and the app says so.

The Day Book reader has been run on a real TallyPrime Excel export (detailed view, 200 vouchers) and copes with its
traits: a title block with merged cells, a header split over two rows, every voucher's first ledger line on the voucher
row, narration on a row of its own, and a Total row. It also handles real date cells, text dates, voucher numbers stored
as numbers, a date shown only once per day, and a single Amount column whose Dr/Cr sits in the number format or as a
`Dr`/`Cr` suffix. An amount whose side cannot be told is refused with the row number rather than guessed.

**Hidden dates.** TallyPrime Educational Mode writes the word `Educational` in place of every date except the 1st, 2nd
and 31st. Those dates are treated as unknown, never copied from the previous voucher, and the file's own order (which
is chronological) is kept. The tests that need a date then degrade honestly: one finding says how many dates are hidden;
cash is tested per voucher instead of per day; the negative-cash test is skipped; weekend and repeated-amount tests run
only on dated vouchers; every other test runs on all vouchers. `samples/tally_daybook_export.xlsx` reproduces this
layout; `samples/make_native_daybook.py` regenerates it.

## Checks

| Check | Severity | Basis |
|---|---|---|
| Cash payment above limit (aggregated per party per day) | Medium/High | Sec 40A(3) |
| Cash payment just under the limit | Low | splitting indicator |
| Cash receipt of Rs 2 lakh+ per party per day | High | Sec 269ST |
| Cash balance goes negative (needs opening cash if the book starts mid-year) | High | book integrity |
| Possible duplicate voucher (same type, ledgers, amounts within 7 days) | High | duplicate payment |
| Debit not equal to credit | High | double entry |
| Voucher number gaps per series (judged by which numbers exist, so batch-entered or back-dated numbering is not a false alarm; a series that repeats numbers is read as restarting) | Low | completeness |
| Date outside the financial year; dates hidden in the export | High / Medium | cut-off |
| Large entry on Sunday, round-sum entry, missing narration | Low/Medium | unusual timing / documentation |
| Suspense ledgers (Medium); "Miscellaneous" ledgers (Low) | Medium/Low | clearing before finalisation |
| **The 999 test:** amounts ending in 999, or within 2% under Rs 10,000 / 20,000 / 30,000 / 50,000 / 1 lakh / 2 lakh / 5 lakh | Low/Medium | threshold avoidance |
| **Narration themes:** fraud, bribe, gift, penalty, donation, "as instructed", suspense or plug, write-off, personal or family spend, director loan, no supporting document, MSME supplier, TDS probably not deducted, correction or back-dating (cash wording where there are no ledger lines). Negated mentions such as "no penalty levied" are not flagged | High/Medium/Low | SA 240, Sec 37, Sec 17(5)(h) CGST, Sec 43B(h), Sec 40(a)(ia) and others, each cited on the finding |
| Same amount to the same party 3 or more times within 31 days | Medium | splitting / duplicate processing |
| Benford first-digit screen over all amounts (needs 100+ vouchers) | Low/Medium | screening indicator only |
| Possible TDS non-deduction (194C/J/I/H/A by ledger name) | Medium/Low | TDS |
| IGST with CGST/SGST in one voucher; CGST not equal to SGST | High/Medium | GST |
| **AI:** narration vs ledger mismatch, capital vs revenue, personal expense, wrong voucher type, related party | AI-rated | judgement |

## Dashboards, rounding and the Guidance Note

- **Dashboards.** Day Book Audit and the Financial Statements Builder each open on a Dashboard tab (KPIs, findings by
  severity, top parties, monthly view; P&L bridge, cash flow bridge, composition, working-capital days, review health).
  They need no key; the numbers come from `daybook_auditor/analytics.py` and `fsbuilder/analytics.py`, which are tested.
- **Rounding.** Amounts are shown in the unit Schedule III requires for the company's size (rupees to millions or
  lakhs), rounded so that totals still foot. The unit can be changed on the page.
- **Guidance Note.** `reference/` holds the ICAI Guidance Note (Revised January 2022). It was used to correct the ratio
  definitions (Annexure B), add rounding and the ratios note, extend the disclosure checklist and stop clause numbers
  such as "GN 8.9.13" being read as dates. The PDF is copyrighted and is not committed.
- The statements page works on your own trial balance only (Tally export, template or the connector). The fictional
  company in `samples/` is kept for the tests and the command line.

## Limits to know

- **Statutory references and thresholds** follow the Income-tax Act, 1961 and FY 2025-26 limits. From
  FY 2026-27 the Income-tax Act, 2025 renumbers sections; verify before relying on them. Thresholds
  live in `rules.py` (`Config`, `DEFAULT_TDS_RULES`, `REF`) and the main ones are editable in the sidebar.
- TDS and GST checks are **name-based heuristics** on ledger names and single vouchers. They flag items
  to examine, not conclusions. Annual per-party aggregation is not done.
- Findings are **leads for a reviewer**, not audit conclusions. AI findings in particular can be wrong.
- **Privacy:** rule checks run locally. The AI review sends ledger names, amounts and narrations of the
  selected vouchers to Google's Gemini API, and only after the user ticks a consent box.

## Layout

```
app.py                        entry point: theme and navigation
ui/                           pages: home, statements, day_book, settings; theme.py, ai.py (shared key), charts.py (dashboards)
.streamlit/config.toml        colours and fonts
daybook_auditor/parser.py     Day Book XML / XLSX / CSV -> one row per ledger line
daybook_auditor/rules.py      accounting rules
daybook_auditor/narration.py  narration themes, the 999 test, repeated amounts, Benford
daybook_auditor/analytics.py  numbers behind the Day Book dashboard
daybook_auditor/ai_review.py  Gemini review of vouchers (batched, JSON output)
daybook_auditor/fs_format.py  font, date and negative-number checker (used by the tests; no page)
fsbuilder/analytics.py        numbers behind the statements dashboard
fsbuilder/                    trial balance -> Schedule III statements, notes, cash flow, reviewer (see above)
docs/                         project report (LedgerLens_Project_Report.docx) and the script that builds it
reference/                    ICAI Guidance Note on Schedule III (your copy; not committed)
samples/                      fictional data, seeded issues, and files in Tally's native export layouts
tests/                        pytest (python -m pytest): 312 tests
```
