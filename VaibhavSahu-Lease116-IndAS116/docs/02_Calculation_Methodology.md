# Lease116 — Calculation Methodology

| Item | Detail |
|---|---|
| Document | 02 — Calculation methodology (engine v1.0.0) |
| Applies to | Lessee, lessor, sublease and sale-and-leaseback calculations in `app/engine` |
| Framework | Ind AS 116 (primary); IFRS 16 selectable — presentation and cash-flow differences only |
| Date | 25 September 2026 |

This document states exactly how every number is produced, so that a reviewer can re-perform any figure. Paragraph references are to Ind AS 116 unless stated otherwise; Ind AS 116 follows the IFRS 16 paragraph numbering, and the Ind AS carve-outs that matter here (interest paid presented in financing activities under Ind AS 7; no fair-value model for investment property under Ind AS 40) are handled in presentation. Entity policies that change a result are listed in section 12 and are recorded, with the calculation, in each calculation run's input snapshot.

---

## 1. Numerical conventions

| Topic | Convention | Why |
|---|---|---|
| Arithmetic | Python `Decimal`, 40 significant digits; no binary floating point anywhere in the engine, API or UI totals | Exact, reproducible results |
| Rounding | Half-up to the currency's decimals (default 2) | Accounting convention |
| Balance-driven rounding (default) | Each closing balance is rounded; the period movement (interest, depreciation) is the difference between rounded balances, so every row reconciles exactly | No rounding plugs |
| Alternative | Round interest per period and true-up at the end; any true-up above ₹1.00 is raised as an exception | Policy option |
| Dates | Every date is the start of that day. A period ending on E closes at the start of E + 1, i.e. it includes the whole of day E | Unambiguous day counts |
| Event timing | Modifications and reassessments take effect at the start of the effective date: payments due that day follow the revised terms (option: "apply after payments due on the effective date") | Assumption A3 |
| Commencement payments | A payment dated on the commencement date is treated as paid at commencement: excluded from the liability and added to the ROU asset (para 24(b)) | Policy A2 |

## 2. Discount rate and time basis

**Rate convention.** The quoted annual rate *r* is converted to an effective annual rate *R*:

| Convention | Effective annual rate |
|---|---|
| Effective annual (default) | R = r |
| Nominal, compounded monthly | R = (1 + r/12)^12 − 1 |
| Nominal, compounded quarterly | R = (1 + r/4)^4 − 1 |
| Nominal, compounded half-yearly | R = (1 + r/2)^2 − 1 |

**Year fraction τ between two dates.**

| Day count | τ | Equivalent |
|---|---|---|
| Actual/365 fixed (default) | actual days ÷ 365 | Excel `XNPV` / `XIRR` |
| Months/12 | whole months ÷ 12, broken months by actual days in the month | Periodic "rate ÷ 12" schedules |

**Discount factor** DF(t) = (1 + R)^(−τ(commencement, t)). **Growth factor** over an interval = (1 + R)^(Δτ).

The rate itself is an input (para 26): the rate implicit in the lease if readily determinable, otherwise the lessee's incremental borrowing rate. The application never assumes a rate — a capitalised lease without a rate cannot be calculated. The IBR table (currency × tenor band × effective date × entity) is maker-checker controlled; approved rates are locked.

## 3. Lease term (paras 18–21, B34–B41)

1. Start with the non-cancellable period: commencement to contract end.
2. **Termination options held by the lessee**: the lease term ends at the earliest option date unless the lessee is reasonably certain *not* to exercise it (e.g. lock-in exit rights in leave-and-licence agreements).
3. **Extension options held by the lessee**: periods are added only if reasonably certain to be exercised.
4. **Options held only by the lessor** are ignored (B35).
5. **Enforceability cap** (B34): if both parties can terminate without more than an insignificant penalty, the term cannot extend beyond that point — an explicit judgment field.
6. **Purchase option** reasonably certain → depreciation runs to the end of the asset's useful life (para 32).

Every option requires an explicit Yes/No judgment with a rationale; a "Not assessed" option blocks calculation ("Accounting judgment required"). The engine records the reasoning (shown under *Lease term determination*) and a judgment flag.

## 4. Lease payments (paras 27–28, 38, B42)

Each dated payment line carries a category and an inclusion decision with a reason:

| Category | In the liability? | Ref. |
|---|---|---|
| Fixed / in-substance fixed (incl. contractual escalations, stepped rent, nil rent-free periods) | Yes | 27(a), B42 |
| Lease incentive receivable | Yes (negative) | 27(a) |
| Index- or rate-linked | Yes, at the index/rate at commencement (or last reset) | 27(b), 28 |
| Residual value guarantee | Yes — amount expected to be payable | 27(c) |
| Purchase option price | Only if reasonably certain | 27(d) |
| Termination penalty | Only if the lease term reflects the termination | 27(e) |
| Variable — sales / usage based | No — expensed when incurred | 38(b) |
| Non-lease component (CAM, services) | No — unless the para 15 expedient is elected for the asset class | 12–16 |
| Payments in optional periods not in the lease term | No — disclosed as exposure (59(b)(ii)) | 18, 59 |

A reviewer may override inclusion only with a written reason (audit-logged).

**Payment generator.** Base amount per period, frequency (monthly / quarterly / half-yearly / annual), advance or arrears, anniversary or calendar alignment, due day, broken-period pro-rating by days, escalations (percentage or amount; compound on last rent or simple on base; any interval; first effective date), stepped-rent table and rent-free windows (lease or lease + non-lease). Extension-option periods are generated as separate "option" lines (with any renewal uplift) and included only when the option is reasonably certain.

## 5. Initial measurement (paras 23–28)

**Lease liability** at commencement date C:

> L₀ = Σ over included unpaid payments *p* with date *t* > C (or = C under policy A2 "not paid"): amount(p) × (1 + R)^(−τ(C, t))

**Right-of-use asset** (para 24):

| Component | Treatment |
|---|---|
| Initial lease liability | + L₀ |
| Lease payments made at or before commencement | + (net of incentives received) |
| Lease incentives received | − |
| Initial direct costs (e.g. stamp duty, registration, brokerage borne by the lessee) | + |
| Restoration / dismantling estimate (Ind AS 37) | + PV at the provision's pre-tax rate |
| Security deposit: cash paid − fair value (policy) | + as prepaid lease payment |

The workpaper export recomputes L₀ with live Excel formulas (`=1/(1+R)^t`) and shows the difference to the engine (expected: nil).

## 6. Subsequent measurement of the liability (paras 36–38)

Between two consecutive "state-change" dates (payment, event, period end) the balance accrues interest continuously:

> Interest(interval) = L × [(1 + R)^(Δτ) − 1]

A payment reduces the balance on its due date after interest has accrued to that date. The period's interest is the sum of its sub-intervals (visible in *How was this calculated?*). Because interest compounds only at state-change dates, the method is the effective-interest method on exact dates; with Months/12 and payments at month boundaries it reduces to the familiar "rate ÷ 12" schedule.

**Current / non-current split** (para 47; Schedule III): default = principal reduction over the next 12 months (liability now − liability in 12 months, ignoring later events); alternative = present value of payments due within 12 months.

**Maturity analysis** (para 58; Ind AS 107 B11): undiscounted remaining included payments by year band (≤1, 1–2, 2–3, 3–4, 4–5, >5 by default; configurable).

## 7. Right-of-use asset (paras 29–35)

**Depreciation** — straight-line from commencement to the *depreciation end*: the earlier of the end of the lease term and the end of the useful life; the end of the useful life if ownership transfers or a purchase option is reasonably certain (paras 31–32).

The schedule is built in *segments*. A new segment starts at commencement and after every remeasurement, modification or impairment:

> Depreciation(period) = carrying amount at segment start × weight(period) ÷ weight(segment start → depreciation end)

Weights are days (daily method, default) or months (equal-monthly method; broken months by days). Gross cost, accumulated depreciation and accumulated impairment are tracked and rounded separately so the note to accounts reconciles.

**Impairment** (para 33; Ind AS 36): a loss (entered directly, or derived from a recoverable amount) reduces the carrying amount; depreciation is re-based prospectively. A reversal is capped at the carrying amount that would have existed without the impairment (shadow carrying amount tracked by the engine; Ind AS 36.117).

## 8. Events

### 8.1 Reassessments (paras 39–43)

| Trigger | Revised payments | Discount rate |
|---|---|---|
| Change in lease term / option exercised / reasonable-certainty changed | Remaining payments in the new term | Revised (40(a)) |
| Change in assessment of a purchase option | Incl./excl. exercise price | Revised (40(b)) |
| Change in amounts expected under an RVG | Revised expected amounts | Unchanged (42(a)) |
| Change in future payments from an index or rate | Revised payments when cash flows change | Unchanged (42(b)) |
| Change in floating interest rates | Revised payments | Revised to reflect the rate change (43) |

New liability = PV at the effective date of the revised remaining payments. ΔL adjusts the ROU asset; if the ROU carrying amount would fall below zero, the excess is recognised in profit or loss (para 39). A revised rate entered for a trigger that requires an unchanged rate is ignored and reported as an exception.

### 8.2 Modifications (paras 44–46)

1. **Separate lease test (para 44)** — additional right of use at a price commensurate with its stand-alone price: the original lease is unchanged; the new component is set up as a new lease.
2. **Decrease in scope or term (46(a))** —
   * proportion retained = (1 − fraction of scope surrendered) × (remaining ROU life after ÷ remaining ROU life before);
   * liability for the retained scope is measured at the **original** rate on the **original** payments within the revised term;
   * the reduction in liability less the proportionate reduction in the ROU carrying amount (cost, accumulated depreciation and impairment reduced pro rata) is a gain or loss in profit or loss;
   * the remaining liability is then remeasured with the revised payments at the **revised** rate, with the difference adjusted to the ROU asset.
3. **All other modifications (46(b))** — increase in scope not at stand-alone price, extension of term, change in consideration: remeasure at the revised rate at the effective date; adjust the ROU asset.

This sequence reproduces IFRS 16 Illustrative Examples 16–19 to the unit (see the test report). Pre- and post-event schedules are preserved: each event produces a new calculation run; earlier approved runs remain in history with their inputs hash.

### 8.3 Terminations, restoration revisions, partial derecognition

* **Full termination** — derecognise the liability (after accruing to the effective date) and the ROU asset (cost, accumulated depreciation and impairment); a termination penalty is a liability; gain/loss = liability − ROU carrying amount − penalty. A security deposit's refund is brought forward to the termination date and the restoration provision is settled or remeasured as entered.
* **Restoration estimate revision** — provision remeasured at the current estimate / rate; the change adjusts the ROU cost (cost model, Ind AS 16 Appendix A analogy).
* **Partial derecognition of ROU** — used for finance subleases (B58): the subleased fraction of the ROU asset is derecognised.

## 9. Related balances

| Balance | Method |
|---|---|
| Security deposit (Ind AS 109) | Initial fair value = refund discounted at the market rate on the same time basis; interest income by the effective-interest method; refund at the refund date (or termination). Excess of cash over fair value → prepaid lease payment in the ROU asset (policy, judgment flag) |
| Restoration provision (Ind AS 37) | PV of the estimate (optionally inflated from current prices) at the pre-tax rate; unwinding presented as finance cost; settled at the end of the lease |
| Foreign-currency leases (Ind AS 21) | Liability (monetary) retranslated at the closing rate; interest at the period's average rate; payments at the spot rate of the payment date; ROU asset (non-monetary) at the historical rate on commencement; exchange differences to profit or loss. FX postings are generated in the functional currency |

## 10. Other models

| Model | Method | Ref. |
|---|---|---|
| Short-term / low-value exemption | Validation (term ≤ 12 months, no purchase option, class election; low-value: value when new ≤ entity threshold, B5 conditions, not a head lease subleased); straight-line expense over the lease term with accrual/prepayment tracking | 5–8, B3–B8 |
| Lessor accounting | See §10A | 61–97 |
| Sublease | Classified by reference to the head-lease ROU asset; finance sublease derecognises the subleased ROU and recognises a net investment (gain/loss); the head-lease rate may be used where the sublease rate is not readily determinable | B58, 68 |
| Sale and leaseback | Ind AS 115 transfer assessment required; ROU = carrying amount × (PV of leaseback payments − additional financing + prepayment) ÷ fair value; gain recognised only on rights transferred; off-market terms split into prepayment / additional financing; para 102A policy flag for subsequent measurement; failed sale → financial liability | 98–103 |
| Deferred tax (support) | Temporary differences on ROU and lease liability (tax bases nil unless entered), DTA recoverability and offset flags; income-tax computation add-backs (depreciation, interest, unwinding) less rent paid | Ind AS 12 |

## 10A. Lessor accounting (v1.1 — lessor engine 2.0)

| Topic | Method | Ref. |
|---|---|---|
| Classification | Indicators 63(a)–(e) and 64(a)–(c). 63(c) term test = lease term ÷ economic life; 63(d) PV test = PV of lease payments at the implicit rate ÷ fair value — both against **entity policy** benchmarks (default 90% / 75%; the standard sets no bright lines). Where the implicit rate cannot be solved (no unguaranteed residual), 63(d) is concluded on the undiscounted payments if they fall below the benchmark (their PV at any positive rate is lower still). Any primary indicator met ⇒ finance; all not met ⇒ operating; otherwise **blocked** until the inputs are entered or a classification is recorded with a rationale. Para 64 indicators on an operating lease raise a flag | 61–66 |
| Lease payments | Fixed / in-substance fixed (less incentives payable), index- or rate-linked at the commencement index, RVGs, purchase price if reasonably certain, termination penalty where the term reflects termination. Variable payments not linked to an index / rate: income when earned (by the period they relate to). Non-lease components (CAM, services): always separated — Ind AS 115 revenue | 70, 17, 81, 90 |
| Rate implicit in the lease | Solved so that PV(lease payments) + PV(unguaranteed residual) = fair value + lessor IDC (ACT/365, effective annual); manufacturer / dealer: fair value only, or a market rate where the quoted rate is artificially low (rejected if below the implicit rate) | App. A, 68–69, 73 |
| Finance lease — commencement | Net investment = PV of payments not yet received + PV of the unguaranteed residual. Not a dealer: asset derecognised at carrying amount; the difference (fair value − carrying amount) is a **gain / (loss) on derecognition** (Ind AS 16.68) in other income. Manufacturer / dealer: revenue = lower of fair value and PV at a market rate; cost of sale = carrying amount − PV of the unguaranteed residual; selling profit = revenue − cost; costs of obtaining the lease expensed | 67–69, 71–74 |
| Finance lease — subsequent | Constant periodic rate on the net investment (balance-driven rounding); receipts reduce the net investment; residual realised when the asset is returned; current portion = principal recovered within 12 months | 75–76 |
| Residual value / credit losses | Reduction in the estimated unguaranteed residual: PV of the reduction at the original rate recognised immediately, income re-allocated (increases ignored). Expected credit losses as a separate loss allowance (net investment stays gross) | 77; Ind AS 109.5.5.15(b) |
| Operating lease | Straight-line income over the lease term — **equal monthly amounts** (part months pro-rata by days; policy default) or daily; accrued / deferred balance tracked. IDC added to the carrying amount of the asset and expensed on the same basis. Depreciation / impairment of the asset remain in the fixed-asset register | 81–88 |
| Security deposit received | Financial liability at fair value (market rate required for an interest-free deposit); excess received over fair value = lease payment received in advance (spread through straight-line income / included in the net investment); unwinding at the effective rate in finance cost; early refund catch-up | Ind AS 109.5.1.1, B5.1.1, B5.4.6 |
| Modifications | Operating lease: new lease from the effective date — accrued / deferred balance treated as part of the new lease payments (para 87). Separate lease: this lease unchanged (para 79). Finance lease that would have been operating: asset recognised at the net investment (net of any loss allowance — policy, flagged), then operating-lease accounting (80(a)). Other finance-lease modifications: gross carrying amount recalculated at the original rate, difference in P&L (80(b); Ind AS 109.5.4.3) — a substantial modification (derecognition) is flagged | 79–80, 87 |
| Early termination | Finance lease: net investment derecognised; returned asset and termination payment recognised; difference in P&L. Operating lease: accrued / deferred balance and unamortised IDC released; penalty income; deposit refunded (catch-up). Only where the lease ends when the termination is agreed — otherwise record a modification shortening the term (flag) | App. A, 79–80, 83, 87 |
| Reporting-date position | From the stored result at any date: classification, balances, para 94 / 97 maturity (first five years and later) and, for finance leases, the reconciliation undiscounted payments − unearned finance income + discounted unguaranteed residual = net investment (checked against the schedule at month-ends) | 94, 97 |
| Note (paras 89–97) | Para 90 table (selling profit, finance income, variable income; operating lease income and variable income), para 93 movement with reconciliation check, para 94 maturity and reconciliation net of the loss allowance, para 97 maturity, balance-sheet presentation, para 92 / 95–96 prompts (never generated) | 89–97 |
| Sublease (intermediate lessor) | Classified by reference to the head-lease ROU asset; finance sublease derecognises the subleased ROU (own net-investment ledger role) | B58, 68 |

## 11. Journals and disclosures

The engine emits postings with *accounting roles* (e.g. `ROU_ASSET`, `LEASE_LIABILITY`, `FINANCE_COST_LEASE`, `DEPRECIATION_ROU`). Roles resolve to GL accounts through the GL mapping (most specific of entity / asset class / cost centre / lease type wins). Every journal is checked Dr = Cr before it can be posted; an automated test confirms that, for every lease and every period end, posted journals roll up exactly to the schedule balances (liability, ROU cost, accumulated depreciation, accumulated impairment).

Disclosures aggregate the reporting run of each lease (approved run; latest draft where none is approved, clearly flagged): para 53 items, ROU movement by class (with a reconciliation-difference check that must be nil), liability movement and the Ind AS 7 para 44A reconciliation, current / non-current split, maturity analysis with future finance charges, weighted-average IBR for additions, leases not yet commenced, and para 59–60 prompts (narrative disclosures are never generated automatically).

## 12. Entity policies that affect results

| Policy | Default | Where |
|---|---|---|
| Day count | Actual/365 fixed | Settings → Calculation policies; lease override |
| Rate convention | Effective annual | Same |
| Payment on commencement date treated as paid | Yes | Settings |
| Depreciation | Straight-line, daily | Settings; lease override |
| Current / non-current | Principal reduction in next 12 months | Settings; lease override |
| Rounding | Balance-driven | Settings |
| Maturity bands | 1, 2, 3, 4, 5 years | Settings |
| Low-value threshold | **Not set** — must be entered before a low-value exemption validates | Settings |
| Deposit difference as prepaid rent | Yes | Settings |
| Lessor "substantially all" / "major part" benchmarks | 90% / 75% | Lease (lessor classification inputs) |
| Lessor operating-lease income basis | Equal monthly amounts (alternative: daily) | Settings → Company & policies; lease override |

## 13. Sources

1. Ind AS 116 *Leases*, Companies (Indian Accounting Standards) Rules, 2015 as amended (incl. para 102A amendment applicable from 1 April 2024, per the research note supplied with the brief).
2. IFRS 16 *Leases* — standard text as published in Commission Regulation (EU) 2017/1986 (EUR-Lex), used for paragraph wording checks; IFRS 16 Illustrative Examples IE13–IE19 and IE24 used as numerical benchmarks.
3. IFRS Interpretations Committee agenda decision (November 2019) — lease term and useful life of leasehold improvements (enforceability, broader economics).
4. Ind AS 7, 12, 16, 21, 36, 37, 107, 109, 115 for the related balances described above.
5. Ind AS Technical Facilitation Group (ITFG) Clarification Bulletin 22 (October 2019), Issue 2 — a lessor straight-lines escalations linked to expected inflation (Ind AS 116 carries no equivalent of the Ind AS 17 inflation exception); read via secondary reproductions (KPMG India Ind AS implementation guide; taxguru.in) — confirm against the ICAI original.
6. KPMG *Lease modifications* (2018) and *Leases handbook* — lessor modifications (paras 79–80, 87) and residual value / credit-loss guidance, used to cross-check the treatments in §10A.

> **Verification note.** The ICAI-hosted PDF of Ind AS 116 could not be retrieved from this environment (site restriction), so paragraph wording was checked against the IFRS 16 text, which Ind AS 116 mirrors. Benchmark figures from the IFRS 16 Illustrative Examples are reproduced by the engine to the unit and are asserted in the automated tests; reviewers should confirm them against their own licensed copy of the standard and examples before relying on them in an audit file.
