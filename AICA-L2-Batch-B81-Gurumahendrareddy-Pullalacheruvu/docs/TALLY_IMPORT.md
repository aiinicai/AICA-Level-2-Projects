# Importing the demonstration data into Tally Prime

**Seventeen months** — FY 2025-26 in full, plus FY 2026-27 to 31-Aug-2026 —
so the tool has a prior year to compare against.

Five files, imported in this order:

| # | File | Import menu | What it holds |
|---|---|---|---|
| 1 | `Northwind_Masters.xml` | **Masters** | 50 ledgers with opening balances at 1-Apr-2025 |
| 2 | `Northwind_Vouchers_FY2526.xml` | **Transactions** | 264 receipts, payments and transfers, Apr-25 → Mar-26 |
| 3 | `Northwind_Sales_FY2526.xml` | **Transactions** | 71 sales invoices, same year |
| — | *change the period — step 3c* | `Alt+F2` | |
| 4 | `Northwind_Vouchers_FY2627.xml` | **Transactions** | 110 receipts, payments and transfers, Apr-26 → Aug-26 |
| 5 | `Northwind_Sales_FY2627.xml` | **Transactions** | 30 sales invoices, same period |

Only the first file goes in under **Masters**. Every voucher file goes in
under **Transactions** — called **Vouchers** in older Tally Prime builds and
in Tally.ERP 9.

They live in `demo-tally\` inside the project folder.

**Masters first.** A voucher naming a ledger Tally does not yet have is
rejected, and Tally reports that as an unhelpful "Could not set value" line.

**The years are separate files, and that is the important change.** Tally
imports into the period the company is *currently open for*, which for a new
company is one year wide. A single file spanning both years asks Tally to
accept vouchers it is not open for, and Tally does not say so plainly — it
reports a count of exceptions instead. Two files with a period change between
them removes the ambiguity: if year one lands clean and year two does not,
the period is the problem and nothing else is.

**The sales files are separate on purpose.** Bill-wise references are the
fussiest part of Tally's import. If they give trouble, everything the cash
screens need is already in — burn, runway, the calendar and the year-on-year
comparison all work without them. Only the receivables ageing depends on them.

Menu wording differs between Tally Prime versions and between Prime and
ERP 9. What follows names what to look for rather than promising an exact
path.

---

## 1 · Create the company

`Alt+F3` › **Create Company**, or Gateway of Tally › Create › Company.

| Field | Value |
|---|---|
| Name | `Northwind Robotics Pvt Ltd` |
| Financial year beginning from | `1-Apr-2025` |
| Books beginning from | `1-Apr-2025` |
| Base currency | `INR` |

The name must match exactly — the connector asks Tally for the company by
name, and the XML carries it in `SVCURRENTCOMPANY`.

The date matters more than it looks, and **1-Apr-2025 is not a typo**. The
data spans two financial years; a company created from 1-Apr-2026 will
reject every voucher in the first twelve months, which is most of the file.
Tally carries on into the next year by itself, so one company covers both.

---

## 2 · Import the masters

Gateway of Tally › **Import** › **Masters**.

In older builds this is Gateway of Tally › Import Data › Masters.

Tally asks for the file. Give it the **full path**, including the drive
letter — pasting the path is easier than typing it:

```
C:\Users\Guru Mahendra Reddy\Desktop\Capstone Project\cash-runway\cash-runway\demo-tally\Northwind_Masters.xml
```

If it asks how to treat entries that already exist, **Modify with new
data** is right for a first import. So is **Ignore duplicates** — nothing
here exists yet.

Expect **50 ledgers**.

---

## 3 · Import year one

Gateway of Tally › **Import** › **Transactions**.

**Not Masters.** Masters is for the ledgers file only, and it is the one
place in this sequence you use it. Everything from here on is vouchers, and
vouchers go in under Transactions. Older Tally Prime builds and Tally.ERP 9
call the same option **Import Data › Vouchers** — if that is what you see,
that is the one.

```
C:\Users\Guru Mahendra Reddy\Desktop\Capstone Project\cash-runway\cash-runway\demo-tally\Northwind_Vouchers_FY2526.xml
```

Expect **264 vouchers** — payments, receipts and the transfers between the
company's own accounts, dated 1-Apr-2025 to 28-Mar-2026.

## 3b · Import year one's sales invoices

**Transactions** again:

```
C:\Users\Guru Mahendra Reddy\Desktop\Capstone Project\cash-runway\cash-runway\demo-tally\Northwind_Sales_FY2526.xml
```

Expect **71 invoices**. If this one fails, carry on — see the note at the
top about why it is a separate file.

## 3c · Change the period, then import year two

**`Alt+F2`**, and set the period to **1-Apr-2026 to 31-Aug-2026**.

This is not optional and it is not cosmetic. Tally will not import a voucher
dated outside the period the company is open for, and the way it declines is
a count of exceptions rather than a sentence naming the year.

Then import the two FY 2026-27 files, **Import › Transactions** for both:

```
...\demo-tally\Northwind_Vouchers_FY2627.xml     110 vouchers
...\demo-tally\Northwind_Sales_FY2627.xml         30 invoices
```

When both are in, **`Alt+F2`** once more and set **1-Apr-2025 to
31-Aug-2026** so every report shows both years together.

---

## 4 · Check it landed

**Gateway of Tally › Display More Reports › Trial Balance**, as at
31-Aug-2026. The books balance to zero — that has been checked before the
file was written — and these are the figures to look for:

| Ledger | Closing |
|---|---|
| HDFC Bank — Current 4471 | ≈ ₹ 2.60 Cr |
| ICICI Bank — Collections 8802 | ≈ ₹ 0.84 Cr |
| Axis Bank — Payroll 1156 | ≈ ₹ 0.72 Cr |
| HDFC FD — BG margin | ₹ 0.45 Cr |
| Sundry Debtors | ≈ ₹ 3.70 Cr |
| GST Payable | credit balance |
| HDFC Term Loan | ₹ 3.20 Cr credit |

Bank, cash and deposits come to **₹ 4.62 Cr**, which is the figure every
screen in the tool quotes.

**Day Book**, period 1-Apr-2025 to 31-Aug-2026 — all 374 cash vouchers, 475
with the sales invoices. If it looks empty, the period is wrong, not the
import.

If any payable shows a *debit* balance, something went in wrong — tell me,
because the file is generated with a trial-balance check that would have
caught it.

---

## 5 · Switch on the HTTP endpoint

This is what lets Cash Runway read from Tally. It is off by default.

**Tally Prime:** `F1` (Help) › **Settings** › **Connectivity** ›
**Client/Server configuration**.

| Setting | Value |
|---|---|
| TallyPrime acts as | `Both` (or `Server`) |
| Enable ODBC | `Yes` |
| Port | `9000` |

**Tally.ERP 9:** `F12` › Advanced Configuration, same three settings.

Leave Tally running with the company open. Tally answers on the port even
when no company is loaded, and returns nothing — which looks like a broken
connector rather than a closed company.

---

## 6 · Connect from Cash Runway

Setup › **Tally** › **Test connection**. It should report the company by
name.

Then step 2 choose the company, step 3 map the ledgers. One of the 50 —
`PROJ-B ADJ` — is deliberately unrecognisable, so the mapping screen has
something real to do.

When you sync, set the range to **1-Apr-2025 → 31-Aug-2026** to pull both
years. The tool will then show seventeen months of burn, so Runway & Burn
and Plan vs Actual have a prior year to compare against:

| | Collections | Net burn |
|---|---|---|
| FY 2025-26 | ₹ 94 L / month | ₹ 84 L / month |
| FY 2026-27 (to Aug) | ₹ 170 L / month | ₹ 56 L / month |

That is the story worth telling on camera: collections up 80%, burn down a
third, and the tool showing why.

---

## When it does not work

Tally is strict, and its import log is where the answer is. After an
import it shows a summary — imported, combined, ignored, errors — and
writes the detail to a log file in the Tally installation folder
(`TallyImp.log`, or the name shown on the import screen).

| What you see | What it usually means |
|---|---|
| **`Voucher Date is missing`, on some but not all vouchers** | Fixed in v1.5, and worth knowing why. Three faults fed it: the file carried an `EFFECTIVEDATE` tag, which Tally only honours when *Use effective dates for vouchers* is switched on in F11 — with the feature off it can leave the voucher with no usable date at all; narrations contained typographic dashes, which Tally's reader mangles when the file does not declare its encoding, losing its place mid-voucher; and one file spanned two financial years. All three are gone. Re-import the new files into a **fresh company**. |
| A voucher file imports 0 of everything, no errors | It went in under **Masters**. Voucher files go in under **Import › Transactions** (**Vouchers** in older builds). Tally finds no ledger definitions in a voucher file, imports nothing, and does not treat that as a fault. |
| `Could not set value` on a voucher | The ledger it names was not created. Import the masters first, and check the ledger exists under the exact name. |
| Everything ignored, nothing imported | The dates are outside the period the company is open for. Check the company was created from **1-Apr-2025**, and that you did the `Alt+F2` period change at step 3c before the FY 2026-27 files. |
| `File not found` | The path is wrong. Paste the full path including the drive letter; Tally does not expand `~` or relative paths. |
| Ledgers imported, vouchers all rejected | Almost always the financial year, occasionally a voucher type the company does not have defined (Receipt and Payment exist in every company by default). |
| The import screen never appears | Older Tally Prime builds put Import under `Gateway of Tally › Import Data`. |
| Test connection fails from Cash Runway | Step 5 was not saved, the port differs, or Windows Firewall is blocking it. The wizard lists the five things to check. |
| Bill-wise errors on the sales file | Only file 3 is affected. Skip it — the cash screens and the year-on-year comparison do not depend on it — and send me the log. |
| Receipts show up as payments in the tool | A sign-convention problem, and mine to fix, not yours. Send a screenshot of Runway & Burn. |

**Send me the error text or the log file and I will fix the XML.** Getting
a Tally import clean usually takes a round or two — that is normal, and it
is faster to correct the file than to hand-edit it in Tally.

---

## If Tally will not cooperate

There is a stand-in that speaks the same XML on the same port:

```
cd backend
python mock_tally.py
```

Then Setup › Tally › Test connection, exactly as above. The connector
cannot tell the difference, so the wizard, the mapping screen and the sync
can all be demonstrated without a Tally licence. Do not run it while Tally
is running — they cannot both hold port 9000.
