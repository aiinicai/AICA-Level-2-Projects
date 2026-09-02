# Personal Finance & Debt Impact Calculator — Full Session Log

**Project:** `C:\Users\Hp\OneDrive\Desktop\Capstone\Finance.py`
**Version at start:** v2.1  →  **Version at end:** v2.6
**Original preserved as:** `Finance.py.bak`
**Date:** 2026-08-24

> Note: the opening message contained the complete v2.1 source (~3,700 lines).
> It is referenced here rather than reproduced; the untouched original is kept
> at `Finance.py.bak`.

---

## Turn 1 — User

> [Full v2.1 source of `finance_planner.py` / `Finance.py` pasted — ~3,700 lines]
>
> Check this code
> Find bugs and fix it
> Also optimise the same

---

## Turn 1 — Assistant

Located the file at `Capstone/Finance.py`, 3,736 lines. Ran the engine headlessly
before changing anything.

### The headline finding

**The app's own audit failed on its own demo data** — ₹11.06 lakh deviation on the
cash identity. The integrity check built to make the output trustworthy was
reporting a defect, and it was right to.

```
Monthly cash: inflows = outflows      1.105508e+06   FAIL
```

### Bugs found and fixed

| # | Bug | Evidence |
|---|---|---|
| 1 | **`page_assumptions` crashed with `IndexError`** — `ASSUMPTION_FIELDS[22]` on a 22-item list; 11 other help texts off by one | Reproduced on the backup: `IndexError: list index out of range` |
| 2 | **Cash identity wrong.** Goal payments, the sinking fund drawn to make them, and planned-loan proceeds were absent; EF drawdown double-counted as an asset redemption | Deviation == `Withdraw_Net` in the 4 goal months; == `EF_Used` in shock months |
| 3 | **Goal shortfall booked as cash that moved** — full cost recorded as outflow even when partly unfunded | Deviation == shortfall, to the rupee, on 4 goals |
| 4 | **`advice()` crashed for any user with no debt** — `KeyError: 'Verdict'`; empty tables carried no columns | Reproduced on the backup |
| 5 | **Two goals in one month overwrote each other** (`g_out =` not `+=`) | ₹18.9 L of outflow silently lost |
| 6 | **Goals past the horizon reported "ON TRACK" with zero funding** and broke the goal identity | ₹3.09 Cr deviation; now `BEYOND HORIZON` |
| 7 | **Let-out property interest capped at the Sec 24(b) limit** — that cap is self-occupied only; the methodology page itself said "uncapped" | 7.752% vs correct 6.192% on ₹50L @ 9% |
| 8 | **Residual surplus with no investable holding** went to the EF but was booked as a portfolio contribution | ₹347,311 portfolio-identity failure |
| 9 | **Blank month-of-year / bonus month silently disabled the item** for the entire projection | Lumpy total was 0; now ₹488,000 |
| 10 | **Class defaults never applied** — the importer coerced blanks to 0, so a blank row became a 0%-return asset | Blanks now seed correctly from the class |
| 11 | **Deferral advice ignored goal inflation** — measured growth against a frozen cost, so it prescribed a delay even when deferring never catches up | Now reports "not achievable by delay alone" |
| 12 | Prepay-in-`emi` mode re-solved tenure at the base rate, ignoring the rate-shift scenario; prepayment headroom assumed a flat 5% penalty | — |
| 13 | Optimiser could sell the same asset against several loans | — |
| 14 | `TaxConfig(**P["tax"])` would `TypeError` on an edited JSON; `np.average` divided by zero on a zero portfolio | — |

Two new audit tests added (emergency-fund and goal-corpus continuity) — **eight
now, all passing.**

### Optimisation

| | before | after |
|---|---|---|
| Full analysis, 10-yr | 112 ms | **33 ms** (3.4×) |
| Full analysis, 30-yr | 320 ms | **37 ms** (8.6×) |
| Excel report | 252 ms | 193 ms |

The monthly loop no longer touches pandas (`iterrows()` was 53% of runtime);
increment counting is closed-form instead of O(months²); loan run-off skips
DataFrame construction; the demo template and the swap optimiser are cached
rather than rebuilt on every rerun.

### Verification

- **75/75** profile × scenario combinations pass all 8 audit tests, no crashes,
  no NaN/inf — including extreme stress (100% income loss, 70% crash, +400 bps).
- **Optimisations proven behaviour-preserving:** `_hikes` matches brute force
  across all 57,456 cases; income/expense identical to 9 dp; full projections
  bit-identical on core columns.
- **Every one of the 19 pages renders** via Streamlit's AppTest, on both the demo
  and a bare profile — and the two crashes reproduce on the backup, so the tests
  are real.

*Also disclosed: I overwrote an existing `.claude/launch.json` in the Nisho recon
folder before checking it existed, and reconstructed it from `run_planb.bat` /
`server.log`.*

---

## Turn 2 — User

> IN excel input sheet
> Loan type should have select option but it inputs anything we type
> Same with investment asset class
> Self occupied houseproperty and current vehicle is not included in the net worth
> Figures not getting pickedup properly from the input sheet lik ein goals value put in as 12 cr was taken as 120cr
> Also unrealisitic goals are funded by unrealistic debt, repaying capacity is not considered, emis should not exceed 40% is the rule here that is not taken in to consideration hence all goals are marked as on track
>
> Also a loan at 8% interest is a good loan as the asset earns more than that
> So here it takes is as neutral to costly
> I dont understand the logic here

---

## Turn 2 — Assistant

### 1 · Dropdowns accepted anything typed

Root cause: **Excel silently discards a list validation whose source exceeds 255
characters.** Loan Type was 301, Asset Class 295, Expense Category 346 — so those
three dropdowns were never written to the file at all.

```
Loan Type           15 options, source =  301 chars  >>> EXCEEDS 255, Excel DROPS the dropdown
Asset Class         17 options, source =  295 chars  >>> EXCEEDS 255, Excel DROPS the dropdown
Expense Category    14 options, source =  346 chars  >>> EXCEEDS 255, Excel DROPS the dropdown
```

Option lists now live on a hidden `Lists` sheet, referenced as ranges — no length
limit. Free text is also caught by the validator now.

### 2 · Home and vehicle missing from net worth

There was nowhere to put them. Added **Vehicle (Personal Use)** (depreciating,
−12%/yr default) and **Jewellery / Personal Use**; self-occupied property already
existed. These now count in net worth under their own **PERSONAL / USE ASSETS**
section, are **never** sold to plug a deficit or fund a goal, and get **no vote**
on the benchmark.

### 3 · Figures misread

The value round-trips exactly — but two real defects fed the impression:

- **Deleting the grey notes row silently deleted your first data row.** Reproduced:
  4 goals in, 3 out, "Child UG Education" gone with no message. Now identified by
  content, so it's safe either way.
- **The workbook used Western grouping (`120,000,000`) while the app displays
  Indian (`12,00,00,000`).** Both now use the Indian format.

### 4 · Goals "funded" by imaginary debt

A goal counted as funded the moment a loan could be *imagined* for it, with no
affordability test. The 40% ceiling existed but was only used for a warning after
the fact.

New borrowing is now capped by the EMI-to-income ceiling; what won't fit is
reported as **Borrowing_Refused** and becomes a shortfall. A ₹50 Cr goal now
correctly reads **SHORTFALL** with ₹60.6 Cr of borrowing refused, and peak
EMI/income stays at 39.8%.

### 5 · Why the 8% loan looked bad

Three compounding errors:

| | was | now |
|---|---|---|
| Capital-gains tax | charged **every year** at the full exit rate → 12% became 10.44% | charged **once at exit** → 11.20% over 14 yrs |
| Risk haircut | a **full year's** volatility (0.25 × 18 = **−4.5 pts**) against a 14-year decision | scaled by horizon (vol ÷ √years) → **−1.1 pts** |
| Benchmark | averaged in the liquid parking fund at ~4% → **5.30%** | the **marginal** vehicle surplus actually flows into |

Equity was entering the comparison at **5.94%**, so an 8.6% loan looked 3.3 points
loss-making. The volatility term was doing most of the damage.

How a 12% equity fund competes at different horizons:

```
 1y: after-tax 10.44%  - risk  4.50  = competes at  5.94%
 3y: after-tax 10.58%  - risk  2.60  = competes at  7.99%
 5y: after-tax 10.71%  - risk  2.01  = competes at  8.70%
10y: after-tax 10.97%  - risk  1.42  = competes at  9.55%
16y: after-tax 11.20%  - risk  1.12  = competes at 10.07%
20y: after-tax 11.31%  - risk  1.01  = competes at 10.30%
```

**Result:** an 8.0% home loan is now **HEALTHY LEVERAGE** (+1.84 New regime, +3.32
Old). The 40% credit card is still condemned (−31), the 15.5% personal loan still
loss-making.

Every loan card now has a **"Why this verdict"** panel showing the full arithmetic.

*Judgement call flagged: default benchmark mode changed from "Liquid portfolio
blended" to "Marginal surplus vehicle".*

---

## Turn 3 — User

> Now again in methodology
> When its house upgrade
> Is the sale of current house considered
> And if considered the corresponding loan should also be closed
> And again the repaying capacity should be improvised accordingly
> Here i feel that is missing wrt goals

---

## Turn 3 — Assistant

Confirmed — and worse than suspected. The engine kept the old flat on the books,
kept servicing its loan *alongside* a second new home loan (EMI ₹80,690 →
₹198,602 for one house), and wrote the entire ₹1.93 Cr purchase off to nowhere.
Net worth fell ₹1.83 Cr in a single month.

### What a replacement purchase does now

Two new Goals columns — **Sell to Fund (asset name)** and **Becomes Asset
(class)** — drive this sequence at the goal date:

1. The named asset is **sold in full** at its projected value.
2. Any loan whose **Linked Investment (collateral)** is that asset is **settled
   from the proceeds**, with its prepayment penalty.
3. The **freed EMI is added back to borrowing capacity *before* the new loan is
   sized**.
4. Remaining proceeds meet the cost first; **% From Own Corpus applies only to
   what's still left to find**.
5. What you buy is **capitalised onto the balance sheet** at what was paid.
6. Sold for more than the new one cost? The difference is invested.

| | before | after |
|---|---|---|
| Old flat | still owned | sold, ₹1.28 Cr net |
| Old home loan | still running | **closed at month 84**, ₹43,700/mo freed |
| New borrowing | ₹1.35 Cr | **₹63.9 L** |
| EMI after | ₹198,602 | **₹89,345** |
| New house on balance sheet | nothing | ₹1.93 Cr capitalised |
| Net worth at the goal | −₹1.83 Cr | rises |

Engine narrative:

```
sold 'Flat - Pune (self-occupied)' for ₹1.28 Cr gross, ₹1.28 Cr net
  (Section 54 rollover applied, no capital-gains tax)
settled 'HDFC Home Loan' with ₹26.40 L of the sale proceeds,
  freeing ₹43,700 a month of EMI capacity
```

**Section 54** rollover added on a home-to-home upgrade — without it the model
would charge ~12.5% on the gain, inventing a cost the law doesn't impose.

### Edge cases handled

- **Underwater sale:** flat worth ₹12 L against a ₹26.65 L loan leaves ₹8.36 L,
  serviced 21 more months, with an explicit warning.
- **Consumption goals** capitalise nothing and sell nothing.
- **Naming a non-existent asset** is a validator BLOCKER.
- **House/Vehicle Purchase goals with a blank *Becomes Asset*** raise a warning.

---

## Turn 4 — User

> [Screenshot: goal roadmap table showing raw floats — `29714441.735167`,
> `20285558.264833`, `270000.000000`, `139859564.373439`]
>
> This deosnt look good on presentation aspect
> Also when it is said that goal funded through other assets what are the other assets , details if asked should be mentioned

---

## Turn 4 — Assistant

### 1 · The raw floats

My omission — those columns were added but never registered as money, so they fell
through to Python's default float repr. Fixed at the source: the display formatter
now has a money mode using the **same Indian grouping as the rest of the app**,
plus a compact mode and a `%` suffix on percentages.

| | was | now |
|---|---|---|
| From sale of asset | `29714441.735167` | **₹2,97,14,442** |
| Old loan settled | `20285558.264833` | **₹2,02,85,558** |
| EMI freed | `270000.000000` | **₹2,70,000** |
| Asset acquired | `139859564.373439` | **₹13,98,59,564** |

Headers renamed to plain English and columns reordered so cost → sources → outcome
reads left to right. One related bug caught: `DecisionYears` was in the percent
group and would have rendered "13.67%" instead of 13.7 years.

### 2 · "From other assets" — which assets?

The engine now records **every source it draws on, per goal**: the holding, its
asset class, gross realised, tax paid, exit load, and what actually reached the
goal.

| Source | Kind | Gross | Tax | Exit load | Applied |
|---|---|---|---|---|---|
| Goal sinking fund | Sinking fund | ₹7,83,924 | ₹0 | ₹0 | ₹7,83,924 |
| Bank FD 3yr | Earmarked investment | ₹10,94,829 | ₹76,387 | ₹10,948 | ₹10,07,494 |
| Debt Fund Parking | Other investment redeemed | ₹1,05,750 | ₹7,600 | ₹0 | ₹98,150 |

The friction is now visible: ₹10.94 L of FD broken to deliver ₹10.07 L, losing
₹87,335 to tax and premature-closure penalty.

Each row carries a note explaining *why* it was chosen. Shortfalls appear as an
explicit `UNFUNDED` row. Available in three places: per-goal expander, full table
on the Goal roadmap page, and a new Excel sheet `24b Goal Funding Detail`.

---

## Turn 5 — User

> Now can you get me an exe file for the same

---

## Turn 5 — Assistant

### One thing to flag

The true single-file version built (131 MB) but **did not run**:

```
Failed to start embedded python interpreter:
failed to get the Python codec of the filesystem encoding
```

Verified it wasn't a misconfiguration — a hello-world onefile exe built and ran
fine on the same toolchain, and the bundle had `encodings` present with no
duplicate or shadowed entries. Switched to a **onedir** build: one
`FinancePlanner.exe` (37 MB) plus an `_internal` folder. Also much faster — a
onefile build would unpack ~300 MB to temp on *every* launch (30–60s each time).

### A real bug the packaging found

The built-in self-test surfaced a defect unrelated to packaging:

```
Unknown worksheet reference 'AM05 Car Replacement — planned '
```

The v2.1 sheet-name sanitiser wasn't idempotent — truncating at Excel's 31-char
limit can land on a space, which a second pass strips. Chart series pointed at a
sheet that didn't exist, **silently breaking the amortisation chart for any loan
with a long name** — which every planned goal loan has. Fixed and verified by
rebuilding the report with warnings escalated to errors. Now **v2.6**.

### Verified in the frozen build

```
[ok] loaded Finance.py (v2.6)
[ok] projection ran: 120 months, 7 loans
[ok] audit: 8/8 identity tests passed
[ok] Excel report (xlsxwriter): 130 KB
[ok] Excel input template: 28 KB
[ok] JSON profile: 13 KB
[ok] import pandas / numpy / plotly / xlsxwriter / openpyxl / streamlit / pyarrow
RESULT: ALL CHECKS PASSED
```

Through the real UI: sidebar and all 19 pages, "Done. All audit tests passed.",
dashboard rendering 3 Plotly charts with correct Indian formatting (₹1.74 Cr,
benchmark 9.55%).

---

## Turn 6 — User

> I believe if i share this folder to someone this app will start just on a click and install everything needed on its own?

---

## Turn 6 — Assistant

Half right.

### "Starts on a click" — yes

Tested properly: copied to a folder with spaces and non-ASCII characters, wiped
`PATH` down to `C:\Windows\system32`, removed every `PYTHON*` variable.
**All checks passed.** No Python on the machine, no admin rights, no internet.

### "Installs everything it needs" — no, and that's better

It doesn't install anything. It *already contains* everything — Python 3.14,
pandas, numpy, plotly, Streamlit, and the Visual C++ runtime — all bundled.
Nothing written to Program Files or the registry. Delete the folder to uninstall.

The practical difference: **it can't repair itself.** If files go missing in
transit, it just fails.

### The one thing that will bite you

Sending only the exe is the obvious mistake, and it fails exactly like this:

```
Failed to load Python DLL '...\_internal\python314.dll'.
LoadLibrary: The specified module could not be found.
```

The exe is 37 MB; `_internal` is another 280 MB across 7,253 files. **Both must
travel together.**

Packaged: **`C:\Users\Hp\FinancePlanner.zip` — 128 MB**

Built twice — PowerShell's zip wrote all 7,253 entries with backslash separators,
violating the ZIP spec (7-Zip / macOS / Linux can extract a flat pile of files with
literal backslashes in their names). Rebuilt with correct separators, verified
0 bad entries and archive integrity, then extracted fresh and ran as a recipient
would. **All checks passed.**

### Tell whoever you send it to

1. Extract the whole zip, then run `FinancePlanner\FinancePlanner.exe`.
2. **SmartScreen will appear** (unsigned) → *More info* → *Run anyway*. If
   downloaded, right-click the zip → Properties → **Unblock** first.
3. Some antivirus quarantines fresh PyInstaller exes — known false positive.
4. Requires **64-bit Windows 10 or 11**.
5. Keep the console window open; closing it quits the app.

Points 2 and 3 disappear only with a purchased code-signing certificate.

---

## Turn 7 — User

> Can you provide this whole chat in copy paste format

---

## Final state

| Item | Location |
|---|---|
| Application source (v2.6) | `C:\Users\Hp\OneDrive\Desktop\Capstone\Finance.py` |
| Original v2.1 (untouched) | `C:\Users\Hp\OneDrive\Desktop\Capstone\Finance.py.bak` |
| Packaging entry point | `C:\Users\Hp\OneDrive\Desktop\Capstone\launcher.py` |
| PyInstaller spec | `C:\Users\Hp\OneDrive\Desktop\Capstone\FinancePlanner.spec` |
| Installed app | `C:\Users\Hp\FinancePlanner\FinancePlanner.exe` |
| Shareable zip (128 MB) | `C:\Users\Hp\FinancePlanner.zip` |
| Usage notes | `C:\Users\Hp\FinancePlanner\README.txt` |
| This log | `C:\Users\Hp\OneDrive\Desktop\Capstone\Session_Log.md` |

### Version history

| Version | Change |
|---|---|
| v2.1 | Starting point (as supplied) |
| v2.2 | 14 correctness bugs; 2 new audit tests; monthly loop 3–8× faster |
| v2.3 | Excel dropdowns, notes-row data loss, Indian number format, personal-use assets, EMI affordability gate, corrected verdict model |
| v2.4 | Replacement purchases: trade-in sale, loan settlement, restored capacity, capitalised purchase, Section 54 rollover |
| v2.5 | Display formatting; full per-goal funding-source detail |
| v2.6 | Idempotent Excel sheet names (broken charts); packaged as a Windows application |

### Standing caveats

- The engine does **not** forecast markets. Returns are your inputs compounded
  deterministically.
- It does **not** compute income tax — enter post-tax figures.
- No statutory contribution caps (e.g. PPF ₹1.5 L/yr).
- Section 54 is modelled as a simple full rollover to the extent reinvested; the
  real provision has holding-period, timing and one-house conditions. Confirm
  with a CA before relying on it for a large disposal.
- A replacement purchase is assumed to complete in a single month — no bridging
  finance, no rent in between.
- Run `FinancePlanner.exe --selftest` any time to confirm a copy is intact.
