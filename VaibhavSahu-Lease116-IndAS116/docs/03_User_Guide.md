# Lease116 — User Guide

| Item | Detail |
|---|---|
| Document | 03 — User guide (v1.1.0 — adds lessor accounting) |
| Audience | Preparers, reviewers, approvers and auditors |
| Address | http://127.0.0.1:8116 (opens automatically when Lease116 starts) |

## 1. First sign-in

| Step | Action |
|---|---|
| 1 | Start Lease116 from the desktop shortcut (or `Lease116.exe` in the program folder). The browser opens by itself; a Lease116 icon appears next to the clock — right-click it → **Stop Lease116** when you finish. |
| 2 | Sign in as **admin / admin116**. Change the password when prompted (top-right menu → *Change password*). |
| 3 | *Settings → Company & policies*: company name, framework (Ind AS 116 / IFRS 16), financial-year start, **low-value threshold** (never assumed), tax rate. |
| 4 | *Settings → Master data*: entities, asset classes (short-term election and non-lease expedient are set per class), counterparties (mark related parties). |
| 5 | *Settings → Discount rates (IBR)*: enter the approved IBR table by currency and tenor; an approver approves each rate. |
| 6 | *Settings → GL mapping*: map accounting roles to your chart of accounts (Tally ledger names if you export to Tally). |
| 7 | *Settings → Users & roles*: create users; the preparer and approver must be different people (segregation of duties). |
| Optional | *Settings → System → Load demonstration portfolio* to explore 12 illustrative leases — 10 as lessee, 2 as lessor (DEMO-010 operating lease with deposit and a para 87 modification; DEMO-012 finance lease with residual value, IDC and an expected-credit-loss allowance). Use a practice workspace, not a client database. |

## 2. Roles

| Role | Can do |
|---|---|
| Administrator | Everything, incl. users, settings, reopening locked periods |
| Lease Accountant / Preparer | Create and edit leases, run the agreement reader, calculate, record events, submit |
| Reviewer | Start review, return with comments |
| Approver | Approve calculations, events, rates and imports; post journals; lock periods |
| Auditor | Read everything incl. audit trail; export |
| Read-only | Dashboard and reports |

## 3. Adding a lease

### 3.1 From the agreement (recommended)

1. *New lease* → drop the agreement (PDF — text or scanned, photo, Word or text).
2. Choose the reading engine: **Offline** (rules + OCR + computer vision — nothing leaves the PC), **Offline + local AI model** (Ollama / LM Studio on the same PC), or **Claude API** (only if the administrator allowed it; you must tick the consent box for each document — the consent is audit-logged).
3. Review screen: the page image is on the left; click any field to highlight its source clause. Each field shows its status (*Rule-based*, *AI · quote verified*, *Conflict*, *Not found*…) and confidence. Correct anything — edits are logged.
4. *Judgments* tab: answer the lease-term questions (e.g. reasonably certain to continue after the lock-in?), the IBR, deposit market rate and restoration estimate. The reader never answers judgments for you.
5. *Create lease* → choose **Our entity is the Lessee / Lessor** (for a lessor the counterparty becomes the lessee named in the agreement and no IBR is asked) → a **Draft** lease is created with the payment schedule, options, deposit and initial direct costs.
6. Housekeeping (Administrator): in *Recent agreement reads*, the bin icon deletes a read that was not used to create a lease — with its uploaded copy and page previews — and *Delete reads not used for a lease* clears all of them at once. A read that created a lease shows a lock: it is kept as that lease's source evidence. Every deletion is recorded in the audit trail.

### 3.2 Manual entry or import

* *New lease → Manual entry*: step 1 asks whether your entity is the **lessee** or the **lessor**. Lessee: basics, term & options, payments, discount rate, ROU inputs, review. Lessor: basics, term & options, payments, classification inputs, deposit received, review.
* *Imports*: download the template, fill it, upload → the file is validated row by row → correct errors → an approver imports the batch. For a lessor lease set `role` = LESSOR, put the tenant in `lessor_name` (the counterparty column) and fill `fair_value`, `carrying_amount`, `economic_life_months` (and `unguaranteed_residual` / `implicit_rate_pct` for a finance lease); `classification` + `classification_rationale` only to record a documented judgment.

### 3.3 Leases where your entity is the lessor

| Step | What to do | Reference |
|---|---|---|
| 1 | Create the lease with role **Lessor** (reader, wizard or import). The role can be changed only while the lease is in Draft (*Contract & options*). | — |
| 2 | Complete *Contract & options* (lessee's renewal / termination options — the lease term is assessed exactly as for a lessee) and *Payments* (rent, escalations, rent-free, CAM as non-lease, variable rent as *Variable*). | 18–21, 70, B34–B41 |
| 3 | *Classification* tab: fair value, carrying amount and economic life of the asset; for a finance lease the unguaranteed residual value (or the implicit rate); lessor IDC; indicators 63(a)–(e), 64(a)–(c); manufacturer / dealer and market rate (para 73). The benchmarks (90% / 75% by default) are entity policy. Where you conclude the classification yourself, record it with a rationale. | 61–66, 69, 71–74 |
| 4 | Security deposit received: enter the market rate — the interest-free deposit is measured at fair value and the excess is a lease payment received in advance. | Ind AS 109.5.1.1 |
| 5 | **Calculate**. The calculation is blocked — with the paragraph cited — when the classification cannot be concluded, a finance lease has no determinable rate, or a deposit has no market rate. Nothing is assumed. | — |
| 6 | Review the *Lessor schedule* tab: *By period* (monthly / financial-year), *Initial measurement* (PV of receipts), *Maturity & reconciliation* (para 94 / 97 at the 'As of' date), *Security deposit*, *Lease payments* (treatment of each line). | 67–97 |
| 7 | Events (*Record event*): lessor modification — choose the nature: operating lease (para 87), separate lease (para 79), finance lease that would have been operating (para 80(a)) or other finance lease modification (para 80(b) / Ind AS 109.5.4.3); early termination (only where the lease ends when the termination is agreed — otherwise record a modification shortening the term); reduction of the unguaranteed residual (para 77); expected credit losses (Ind AS 109). | 77, 79–80, 87 |
| 8 | Outputs: lessor workpaper (Excel, live formulas) and memo (Word) from *Export*; *Reports → Lessor Income & Net Investment Schedule / Lessor Maturity Analysis & Reconciliation*; *Disclosures → (h) Lessor disclosures*. | 89–97 |

Policy settings: *Settings → Company & policies → Lessor operating-lease income basis* (equal monthly amounts — default — or daily); a lease can override it on the *Classification* tab.

Presentation notes: a lessor that is not a manufacturer / dealer recognises the difference between the fair value and the carrying amount of the asset as a **gain / (loss) on derecognition** (Ind AS 16.68) — shown outside the para 90 table; manufacturer / dealer selling profit appears in 90(a)(i). The current portion of the net investment is the principal expected to be recovered within 12 months after the reporting date.

## 4. Working on a lease (tabs)

| Tab | Use it to |
|---|---|
| Overview | Key figures, liability / ROU chart, lease-term reasoning, judgment flags, totals |
| Contract & options | Master data incl. the role (lessee / lessor); renewal / termination / purchase options with the reasonably-certain judgment and rationale; sublease, sale-and-leaseback or cut-over inputs where relevant |
| Classification (lessor) | Classification inputs and evidence (paras 61–66), policy benchmarks, override with rationale, income basis |
| Assessment | Does the contract contain a lease (para 9, B9–B31); components; short-term / low-value exemption |
| Payments | Payment terms (escalations, rent-free, steps, CAM) → generated schedule; line-level edits with inclusion reason; IDC / incentives / prepayments; security deposit; restoration |
| Discount rate | Rate, basis and source; look up the approved IBR table; lease-level calculation conventions |
| Liability / ROU schedule | Monthly or financial-year view; payment-level amortisation; initial PV table; functional-currency view for FX leases; **?** icon = *How was this calculated?* |
| Lessor schedule | Net investment / finance income or straight-line income, IDC, deposit and loss allowance by period; initial measurement; maturity analysis and reconciliation at the 'As of' date |
| Events | Lessee: modifications, reassessments, terminations, impairment, restoration revisions. Lessor: modifications (79 / 80(a) / 80(b) / 87), termination, residual value reduction, expected credit losses — all with impact preview |
| Journals | Journal entries by financial year with GL accounts |
| Documents | Agreement, addenda, IBR support — stored locally with a SHA-256 hash |
| Disclosures & tax | The lease's contribution to the note (lessee or lessor); current / non-current; maturity; deferred tax and computation add-backs |
| Audit trail | Calculation runs (with full inputs and hash), approval history, change log |

**Calculate** runs the engine and creates a new *calculation run*. If "Inputs changed after the last calculation" appears, calculate again before submitting.

## 5. Review and approval (maker-checker)

| Status | Meaning | Next action |
|---|---|---|
| Draft | Being prepared | Preparer: *Calculate* → *Submit for review* |
| Prepared | Submitted | Reviewer: *Start review* (or *Return* with comment) |
| Under Review | Being reviewed | Approver: *Approve* (or *Return*) |
| Approved / Posted | Figures final; journals from this run can be posted | Record events for changes; *Reopen* only to correct errors (reason mandatory) |
| Modified / Terminated | Approved with an approved modification / termination | — |

The *Approvals* page lists everything waiting for you. A user cannot review or approve their own work.

## 6. Modifications and reassessments

1. Open the lease → *Record event* (or *Modifications / Reassessments → Record…*).
2. Select the event and its nature — the decision guide on the page shows the rule (paras 39–46).
3. Enter the effective date, description / addendum reference, revised rate (where required), new term end, scope fraction and revised payments.
4. *Preview impact* shows liability and ROU before → after, gain / loss, each computation step and the journal. *Record event* saves it; the lease returns to Draft with a new calculation for review and approval. Earlier approved runs stay in history.

## 7. Month-end and year-end

| Step | Where |
|---|---|
| Review exceptions and unapproved leases | Dashboard alerts; *Reports → Missing Data / Exception Report* |
| Review and export journals (Excel, CSV, Tally XML, SAP-style CSV); optionally summarise by event | *Journals* |
| Post the month (approved runs only) | *Journals → Post period* (approver) |
| Reconcile to the trial balance (import GL balances first) | *Reports → GL Reconciliation* |
| Lock the month | *Accounting periods → Lock* |
| Draft the lease note (lessee sections (a)–(g); lessor section (h), paras 89–97 — choose a month-end 'Period to') | *Disclosures* → *Export note (Excel)* |
| Audit file | Lease → *Export* → *Audit workpaper* (Excel with live formulas) and *Accounting memo* (Word) |

## 8. Display options

Top bar: **As of** date (drives dashboard and reports), entity filter, units (₹ absolute / lakh / crore), light / dark theme. Negative amounts appear in brackets; Indian digit grouping by default (switch in *Settings*).

## 9. Getting help inside the app

* Every judgment flag cites the paragraph and says why attention is needed.
* *How was this calculated?* (the **?** icon on any schedule row) shows the formula, interest sub-intervals, depreciation segments and arithmetic checks.
* The API documentation (for integration) is under the user menu → *API documentation*.
