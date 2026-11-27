# Advance Tax Desk

**AICA Level 2 Capstone Project - CA Chandra Prakash Bhutra - Batch AICA-L2-B122-JODHPUR**

A small desktop tool for a CA office that estimates each client's advance tax from the books to date,
tells the client in plain words what to pay and by when, and gives the office one list of all clients
sorted by the amount due.

Tax year covered: **2026-27** (Income-tax Act, 2025).

## The problem

- **Office side:** nobody has one view of which clients must pay advance tax before 15 June, 15 September,
  15 December and 15 March. Estimates are done client by client in Excel, usually in the last week.
- **Client side:** the client hears about the amount at the last minute, does not understand how it was
  arrived at, and ends up paying interest for deferment and default.

## What it does

1. **Reads a trial balance from any accounting software** - Tally, Busy, Zoho Books, QuickBooks, Marg or
   the bundled Excel template. The columns are auto-detected and can be re-matched on screen.
2. **Classifies each ledger** as Income, Expense, Opening Stock or Ignore (balance-sheet items), using
   group names where present and ledger names otherwise. Every row can be corrected on screen, and
   one-off items can be ticked so they are not annualised.
3. **Projects the profit to the full year** on a time basis, with an adjustment for a stronger or weaker
   remaining season, plus add-backs and deductions.
4. **Takes the other heads of income**: salary, house property, capital gains (equity and other assets,
   short and long term) and other sources, plus old-regime deductions. **Capital gains can be imported from
   any broker, mutual fund or app statement**: match the columns, check each sale's class and term, and the
   app fills the four capital gains boxes after setting off losses.
5. **Computes tax under both regimes** for individuals and HUFs and uses the lower one (or the one you
   fix). Firms and LLPs are taxed at the flat rate. Rebate, marginal relief, surcharge and cess are applied.
6. **Works out the instalment position**: required cumulative amount on each due date, amount paid,
   shortfall, interest for deferment already arisen, and the amount to pay now.
7. **Produces the client message**: a WhatsApp / email text and a one-page Word note.
8. **Dashboard**: all saved clients with status, amount due, days left and interest, largest amount due
   first. Search, filter by status, sort by any column, and click a row to see that client's position with
   one-click actions (open, WhatsApp reminder, Word note). The **Reminders** tab lists every client with an
   amount due and builds all the Word notes in one ZIP; the **Chart** tab shows the amounts due.
9. **Keeps the working papers locally**: the client's figures, the uploaded trial balance file with its
   ledger classification, and a dated copy of every estimate and the message sent with it.

## Where AI is used

AI is optional and works with a key from any of three providers: **Claude (Anthropic), ChatGPT (OpenAI) or
Gemini (Google)**. Paste the key under **Settings** in the sidebar. The app recognises the provider from the
key, reads the list of models that key can use, and shows a **Model** box to pick from. The key is kept only
in memory for the session.

| Use | What is sent | What is not sent |
|---|---|---|
| Plain-language explanation for the client (English, Hindi, Gujarati, Marathi) | Rounded totals and dates | Client name, ledgers |
| Classifying ledgers that the rules could not place | Ledger and group names only | Amounts, client name |
| Flagging unusual or one-off items before projecting | Profit and loss ledger names with amounts | Client name |

**The tax calculation never uses AI.** It is rule-based, driven by `config/tax_rules_ty2026_27.json`, and
covered by tests, so every figure can be re-performed by hand. Without a key the app uses a standard
explanation and works fully.

## Form 26AS download (browser robot)

In **Client**, tab **5 Form 26AS** has a **Download Form 26AS** button. It opens the e-filing portal in a normal Chrome or Edge window, fills the PAN,
waits while you sign in, then goes to Form 26AS on TRACES and saves the file in that client's folder
(`data/26AS/<client>/`), where the app lists it for download.

- You type the password and any OTP yourself in the portal's own page. The app never asks for, sees or
  stores them, and it does not try to get past any captcha.
- The PAN is used only to fill the login box and is not saved.
- Use it only for clients who have authorised the firm to use their login.
- The robot follows the portal's screens as they stood when it was written. If the portal changes and a
  step cannot be done, it says which step to do by hand and still collects the file from the download.
- It was checked against a local copy of the screen flow, not against the live portal.

**Reading the 26AS.** The same tab reads a 26AS file (PDF or text, downloaded above or uploaded), lists
each deductor with TAN, tax deducted and tax deposited, and fills the TDS / TCS box with the total after
review. Form 26AS now carries only TDS and TCS; advance tax challans are in the AIS and are entered in tab 4.
Entries shown against a PAN instead of a TAN (TDS on property or rent) are not read. The reader was built
on the published layout and invented files, so compare the total with the file the first few times.

## Capital gains import

In **Client > 3 Other income > Capital gains**, upload a transaction-wise capital gains or tax P&L
sheet (Excel or CSV) from any broker or app, or fill `demo_clients/templates/capital_gains_template.xlsx`.
Try it with `demo_clients/D02 Dr A Mehta/capital_gains_broker_tax_pnl.xlsx`.

- Listed shares and equity funds: long-term when held for more than 12 months. Other assets: more than
  24 months. Debt funds: always short-term at slab rates. Intraday and F&O rows are left out.
- Class and term can be changed row by row before the figures are used.
- Losses are set off within capital gains only: long-term loss against long-term gains; short-term loss
  against slab-rate gains first, then short-term equity, then long-term. The balance is shown as carried
  forward.
- Not adjusted: cost as on 31 Jan 2018 for old equity holdings, indexation on land or building bought
  before 23 Jul 2024, exemptions, and brought-forward losses.

## How to run

Requires Python 3.10 or later, and Chrome or Edge for the Form 26AS robot.

**Windows, one click:** double-click `Start Advance Tax Desk.bat` once. It installs anything that is missing
(a few minutes, needs internet), puts an **Advance Tax Desk** icon on the Desktop and opens the app in the
browser. From then on, click the Desktop icon. A small window stays minimised on the taskbar while the app
runs; close it to stop the app. On macOS or Linux run `./start.sh`.

**By hand:**

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens in the browser at `http://localhost:8501`. On an empty database the dashboard offers a
**Load demo clients** button; the same button is in the sidebar under **Data folder and backup**. It loads
the six clients in `demo_clients/`. `python seed_demo.py` loads those six and also the 20 tax cases.

Run the tests:

```bash
python -m pytest
```

## Demo clients and verification

All demo data is invented. There are two sets.

**1. Six clients with their own test files - `demo_clients/`.** Each folder has a `client.json` and the
files a real client would send. Loading puts the files through the same importers as the screens, so the
client opens with the trial balance, capital gains, TDS and mobile number already in place. The same files
can be uploaded by hand to try each screen.

| Folder | What it tests | Files |
|---|---|---|
| D01 Marudhar Hardware Stores | Proprietor, Tally trial balance without group names, 26AS | `trial_balance_tally.xlsx`, `26AS.txt` |
| D02 Dr A Mehta | Presumptive profession, broker tax P&L with a loss, debt fund and F&O row | `capital_gains_broker_tax_pnl.xlsx`, `26AS.txt` |
| D03 Mrs K Iyer | Salaried, old versus new regime, fund-app statement with a short / long column | `capital_gains_fund_app.csv`, `26AS.txt` |
| D04 S Verma HUF | HUF, Busy CSV with Dr/Cr column, let-out property | `trial_balance_busy.csv`, `26AS.txt` |
| D05 Demo Traders Firm | Firm, Zoho export, partner remuneration, TDS and TCS | `trial_balance_zoho.xlsx`, `26AS.txt` |
| D06 Demo Textiles LLP | LLP, property sale with a short-term loss set off | `capital_gains_sheet.xlsx` |

For the three trial balance clients, books are up to 31 Oct 2026; the closing stock is in `client.json`.
The `26AS.txt` files are laid out like the TRACES text download and are marked as invented. The mobile
numbers start with 0 so they cannot belong to anyone; put your own number in to try WhatsApp. The PANs
are invented, so do not use them with the Form 26AS robot. `demo_clients/templates/` has the blank trial
balance and capital gains sheets. `python make_demo_clients.py` recreates the whole folder.

The business income, capital gains and TDS of these six are worked by hand from the files in
`tests/test_demo_folder.py`.

**2. Twenty tax cases - `seed_demo.py`** (loaded from the command line; used to verify the tax engine). 13 individuals (below 60, senior, super senior, non-resident,
salaried, presumptive, surcharge cases, business loss), 2 HUFs, 3 partnership firms and 2 LLPs, with
different payment histories (on time, late, short, none). The expected tax, advance tax, amount due and
interest for each are worked by hand, with the arithmetic written out, in `tests/test_demo_clients.py`.
The tests compare the app's engine with those figures as on 22 Nov 2026.

## Folder structure

```
Start Advance Tax Desk.bat     One-click start on Windows (start.sh on macOS / Linux)
app.py                         Streamlit screens
.streamlit/config.toml         Colours and start-up settings (no secrets)
advtax/engine.py               Tax and advance tax computation (rule-based)
advtax/projection.py           Year-to-date to full-year projection
advtax/tb_import.py            Trial balance reader and ledger classifier
advtax/notes.py                WhatsApp text and Word note
advtax/ai.py                   Optional AI helpers (Claude, ChatGPT, Gemini)
advtax/portal_26as.py          Form 26AS download robot
advtax/form26as_read.py        Reads TDS / TCS from a 26AS file
advtax/cg_import.py            Capital gains statement import
assets/icon.ico, tools/        Desktop icon and the script that creates the shortcut
advtax/storage.py              Local SQLite database: clients, trial balances, estimate history
config/tax_rules_ty2026_27.json  Slabs, rates, limits and due dates
demo_clients/                  Six invented clients with their test files, and the blank templates
advtax/demo.py                 Loads demo_clients/ through the importers
tests/                         144 tests; tax figures are hand-worked
make_demo_clients.py, seed_demo.py  Demo data generators
```

## Rules used (tax year 2026-27)

Checked in November 2026 against the Income-tax Act, 2025 on the Income Tax Department's website and the
rates in the Finance Act, 2026. The same list, with the amounts, is on the client screen under
**Computation > Basis of calculation**.

| Item | Provision (2025 Act) | Applied as |
|---|---|---|
| New regime slabs | Section 202 | Nil up to 4 lakh, then 5% / 10% / 15% / 20% / 25% for each further 4 lakh, 30% above 24 lakh |
| Old regime slabs | Finance Act, 2026 | 2.5 lakh / 3 lakh / 5 lakh exemption by age (resident individuals), then 5%, 20%, 30% |
| Rebate, resident individuals | Section 156 | New regime up to Rs 60,000 where income is up to 12 lakh, with marginal relief, not against special-rate gains; old regime up to Rs 12,500 up to 5 lakh, not against long-term equity gains |
| Standard deduction on salary | Section 19 | Rs 75,000 new regime, Rs 50,000 old regime |
| House property | Section 22 | 30% deduction on let-out property; interest on a self-occupied house up to Rs 2 lakh in the old regime only; loss set-off capped at Rs 2 lakh (old regime) |
| Firms and LLPs | Finance Act, 2026 | 30%; surcharge 12% above 1 crore |
| Capital gains | Sections 196, 197, 198 | Short-term listed equity 20%; long-term other assets 12.5%; long-term listed equity 12.5% above Rs 1.25 lakh; other short-term gains at slab rates |
| Surcharge, individuals and HUFs | Finance Act, 2026 | 10% / 15% / 25% / 37% (25% maximum in the new regime); 15% maximum on these capital gains |
| Cess | Finance Act, 2026 | 4% |
| Presumptive income | Section 58 | The percentage of turnover or receipts entered |
| Advance tax liability | Sections 403, 404 | Payable when tax after TDS / TCS is Rs 10,000 or more; resident individuals aged 60 or more with no business or professional income are not liable |
| Instalments | Section 408 | 15% / 45% / 75% / 100% by 15 June / 15 September / 15 December / 15 March; presumptive business or profession, the whole amount by 15 March |
| Interest for deferment | Section 425 | 1% a month for 3 months on the shortfall in each of the first three instalments and 1% on the last; none where 12% and 36% are paid by June and September |
| Interest for default | Section 424 | 1% a month from 1 April where advance tax paid is below 90% of the tax |

The rates, limits and dates sit in `config/tax_rules_ty2026_27.json` and can be changed without touching
the code.

## Limitations

This is an estimating tool, not a return-preparation tool. Not covered: companies, alternate minimum tax,
agricultural income, casual income, brought-forward losses, marginal relief where surcharge applies
together with capital gains, the 15% limit on surcharge on dividend (the app warns when it could matter),
and the relief from deferment interest where a shortfall arises only from capital gains, dividend or a
business begun in the year. The projection is a straight-line estimate and must be reviewed by the
professional before it is sent to a client.

## Data and privacy

- All sample data is invented. No client data is included in this repository.
- Everything is stored locally in one file, `data/advance_tax.db`, which is excluded from Git. It holds
  three things: the latest figures per client, the uploaded trial balance file with the ledger
  classification, and a dated history row for every save (figures, result and the message).
- Reopening a client brings back the saved trial balance, so the ledger list can be reviewed or changed
  without uploading again. An earlier estimate can be opened, its Word note downloaded again, or loaded
  back into the form.
- The folder can be changed from the sidebar (**Data folder and backup**), for example to an office
  drive. The choice is kept in `settings.json`, also excluded from Git. On a shared drive only one person
  should save at a time. The same box has a one-click backup download of the database.
- No API key is stored in the code or on disk.

## Author

CA Chandra Prakash Bhutra, R H A D & CO, Chartered Accountants
