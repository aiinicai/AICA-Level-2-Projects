# Legal notes: interpretations, conventions and corrections to the brief

This file records every place where the build **departs from or adds to** the project brief, and every interpretation the engine relies on. Evidence for each item is in `RULEPACK_VERIFICATION.md`. Nothing here is signed off: each item awaits partner verification in the app.

---

## Part 1: Corrections to the brief

| # | Brief | Correction | Authority | Effect |
|---|---|---|---|---|
| C1 | DIR-3 KYC for a DIN allotted Jan 2026 is due 30-06-2028 (golden test 3) | **30-06-2029.** MCA's own illustration reckons the triennial cycle from the FY in which the DIN was allotted: a DIN allotted in FY 2025-26 is due April–June 2029. Legacy DINs (allotted on or before 31-03-2025 and KYC-compliant) are due 30-06-2028. Interim change filings do not reset the cycle. | r.12A as substituted by G.S.R. 943(E) dt 31-12-2025 (w.e.f. 31-03-2026); MCA "Important update for Directors" illustrations | Golden test 3 changed; `kyc_due()` has two branches (see Part 3). |
| C2 | Share certificates = incorporation + 60 days | **Two months** (calendar), so Alpha's date is 20-03-2026, not 21-03-2026. | s.56(4)(a) | Golden test 1 changed. |
| C3 | `llp_audit_required` = turnover > ₹40 L **or** contribution > ₹25 L | Audit is required only if turnover > ₹40 L **and** contribution > ₹25 L. The proviso exempts an LLP meeting *either* limit. | LLP Rules r.24(8) first proviso | Predicate rewritten. |
| C4 | Small LLP uses turnover (year unspecified) | Turnover of the **immediately preceding FY** (from its Form 8). | LLP Act s.2(1)(ta) | Seed needs preceding-year turnover for Zeta. |
| C5 | LLP additional-fee slabs stop at "> 360 days" only for Forms 8/11 | Other LLP forms beyond 360 days pay **25× (small) / 50× (other)**. Forms 8 and 11 beyond 360 days pay 15× / 30× plus ₹10 / ₹20 per day, **only for days beyond 360**. | LLP (Amendment) Rules 2022, G.S.R. 109(E) | Fee table extended. |
| C6 | Company MULTIPLIER starts at "≤ 30 days = 2×" for all forms | For forms under **s.139 (ADT-1) and s.157**, there is an extra first slab: ≤ 15 days = 1×, then 16–30 days = 2×. | ROF Rules, Annexure (Amdt 2022) | ADT-1 filed 1–15 days late costs 1×, not 2×. |
| C7 | Higher additional fee (3/6/9/15/18×) for "specified forms", list open | The list is **INC-22 and PAS-3**, on a delay on two or more occasions within 365 days of the last belated filing of that form. | ROF Rules, Annexure | `prior_defaults` counted per form. |
| C8 | CHG-1: "Registrar may allow further period (verify)" | Three windows: ≤ 30 d normal; 31–60 d additional fee (3× small/OPC, 6× others); 61–120 d additional fee **plus** ad valorem 0.025% (cap ₹1 L) or 0.05% (cap ₹5 L). Beyond 120 d, only s.87 condonation by the Regional Director; the app computes no fee and shows "condonation required". | s.77(1) as amended 2019; ROF Annexure | CHARGE regime implemented. |
| C9 | MSME-1 fee "verify" | **No filing fee**; regime `NONE`. Non-compliance is a s.405(4) matter (penalty text only). | Specified Cos Order 2019, amended 15-07-2024 | — |
| C10 | Secretarial audit test uses maximum borrowings during the year | Rule 9's Explanation uses figures **as on the last date of the latest audited FS**. Internal audit (Rule 13) *does* use "at any point of time during the preceding FY". | Rule 9, Appointment & Remuneration of Managerial Personnel Rules; Rule 13, Accounts Rules | Two AnnualFacts fields: `bank_borrowings_at_fy_end`, `bank_borrowings_max_in_year`; also add `deposits_outstanding_max`. |
| C11 | MR-1: verify private applicability | **Not applicable** to private companies. s.196(4)–(5) is exempted by G.S.R. 464(E), unless the private company is a subsidiary of a public company. | G.S.R. 464(E) dt 05-06-2015 | Predicate `public_or_private_sub_of_public`. |
| C12 | Private-company exemptions (MGT-14 for s.179(3), etc.) treated as unconditional | All s.462 exemptions in G.S.R. 464(E) apply only to a private company that is **not a subsidiary of a public company**. | G.S.R. 464(E) | New entity field: `holding_company_type`. |
| C13 | CSR-2 timing "verify" | Filed as an **addendum to AOC-4**, so due on the AOC-4 date for current years. Earlier years had standalone cut-offs; these are kept as historic rows. | Accounts Rules r.12(1B) | — |
| C14 | Form 4D: "LLP Rules as amended 2024" | **LLP (Third Amendment) Rules, 2023** (27-10-2023), r.22A/22B. Form 4D is due within 30 days of receiving a Form 4B/4C declaration. | as stated | Citation fixed. |
| C15 | Eta LLP "18-month first FY" | 15-11-2025 → 31-03-2027 is about **16½ months**. The dates in golden test 8 are unaffected. | LLP Act s.2(1)(l) proviso | Label only. |
| C16 | DPT-3 excludes Government companies | Rule 1(3) of the Deposits Rules excludes banking companies, NBFCs, HFCs and notified companies. **Government companies are not listed.** | Acceptance of Deposits Rules r.1(3) | Govt exclusion removed pending Q6. |
| C17 | AOC-4 XBRL exclusions | Add **housing finance companies**. | XBRL Rules 2015 r.3 | — |
| C18 | Delta: "small only under new thresholds, so MGT-7A" (no mention of other forms) | Delta (paid-up ₹8 cr, turnover ₹80 cr) also needs **AOC-4 XBRL** (paid-up ≥ ₹5 cr) and **MGT-8** (turnover ≥ ₹50 cr). The small-company test uses the **preceding FY's** turnover (FY 2024-25 for FY 2025-26). | XBRL r.3; MGT r.11(2); s.2(85) | Seed and golden test 6 expectations extended. |
| C19 | Small-company threshold history has two rows | It needs four rows: ₹50 L / ₹2 cr (to 31-03-2021); ₹2 cr / ₹20 cr (01-04-2021, G.S.R. 92(E)); ₹4 cr / ₹40 cr (15-09-2022, G.S.R. 700(E)); ₹10 cr / ₹100 cr (01-12-2025, G.S.R. 880(E)). | Specification of Definition Details Rules r.2(1)(t) as amended | Needed for back-year classification (e.g. Theta FY 2023-24). The G.S.R. numbers for 2021 and 2022 are from memory: **unverified**. |
| C20 | Casual vacancy (auditor): Board fills within 30 days | If the vacancy is caused by **resignation**, a general meeting must also approve within **3 months**. | s.139(8)(i) | Linked obligation added. |
| C21 | AGM: no mention of ROC extension | The ROC can extend a non-first AGM by up to 3 months. | s.96(1) 3rd proviso | Optional field `agm_extension_until`. |
| C22 | Overlays: only CCFS-2026 named | Also model **GC 02/2026** (DPT-3 FY 2025-26: no additional fee to 31-07-2026) and **GC 08/2025** (AOC-4/MGT-7 FY 2024-25: no additional fee to 31-01-2026). | as stated | `schemes.yaml`. |
| C23 | CCFS covered forms: "AOC-4, MGT-7…" | The list includes **ADT-1** and FC-3/FC-4. Exclusions exist (strike-off initiated, strike-off applied, dormancy applied, amalgamated, vanishing). | GC 01/2026 | Overlay form list and eligibility flags. |

## Part 2: Conventions

### 2.1 Day-count: `due_date(anchor, offset)`

- **"Within N days from X"**: due = X + N calendar days. Section 9 of the General Clauses Act, 1897 excludes the first day of a period expressed with "from", so the Nth day after X is the last day. Examples: 20-01-2026 + 30 = 19-02-2026; 26-09-2026 + 60 = 25-11-2026.
- **"Within N months"**: `relativedelta(months=N)`. "Month" means a British calendar month (s.3(35) GCA). The day of month is kept, and clipped to the month's end when that day does not exist (31-08 + 6 months = 28/29-02). Examples: 20-01-2026 + 2 months = 20-03-2026; 31-03-2027 + 9 months = 31-12-2027.
- **No weekend or holiday shift.** MCA filing is online, and no rule moves an ROC due date for holidays. The UI shows a "falls on Sunday / gazetted holiday" hint only. The holiday list is maintained in settings.
- **"Delay"** for fee purposes = filing date − due date, in days (filed on the due date → 0).
- **Slab boundaries** are inclusive of the upper bound ("up to 30 days" includes day 30).

### 2.2 Financial year

- **Company (s.2(41)):** a company incorporated on or after 1 January has its first FY end on 31 March of the following calendar year. Otherwise the first FY ends on the next 31 March. The invariant "first FY ends 31 March of (incorporation year + 1)" holds for all dates. Tribunal-approved non-March FYs (s.2(41) proviso, foreign holding company) are **not modelled**; such entities are flagged.
- **LLP (s.2(1)(l)):** registered **after 30 September**, so the LLP *may* end its first FY on 31 March of the next-following year. This is stored as an election field. The default is the shorter FY, and both outcomes are shown.

### 2.3 AGM deadline

The AGM deadline is `min(FY_end + 6 months, previous_AGM + 15 months)`, or `FY1_end + 9 months` for the first AGM. An ROC extension replaces this value when recorded. If no AGM is held, AOC-4 and MGT-7 run from the **deadline** (s.137(1) 3rd proviso; s.92(4)) and are labelled *Provisional* until an actual date is entered.

## Part 3: Interpretations awaiting partner sign-off

| ID | Interpretation | Why it is uncertain | Seed behaviour |
|---|---|---|---|
| I1 | **`kyc_due(din_allotment_date, last_kyc_fy, override=None)`**: legacy DIN (allotted ≤ 31-03-2025) and KYC-compliant → 30-06-2028, then every 3 years (2031, 2034 …). DIN allotted in FY *Y* ≥ 2025-26 → 30 June of (end-calendar-year of *Y* + 3), then every 3 years. | The plain words of the substituted r.12A ("holds a DIN as on 31 March of a FY … every third consecutive FY") can be read to give 2028 for a DIN allotted in Jan 2026. MCA's published illustration says 2029. The seed follows MCA; V3 is likely to enforce MCA's reading. Also unclear: a legacy DIN that was *deactivated* at 31-03-2026 (reactivation fee ₹5,000 applies immediately; the cycle after reactivation is not illustrated). | Partner override per person. Both cases are tested. |
| I2 | DIR-3 KYC event-filing fee between 31-03-2026 and 20-04-2026 = ₹500 | The substituted rule was in force, but the new fee entry started only on 21-04-2026. | Marked uncertain. |
| I3 | ADT-1 for the first auditor (s.139(6)) | Rule 4(2) language; practice is divided. | Firm setting, default **file**. |
| I4 | OPC MGT-7A due = (FY end + 6 months) + 60 days, i.e. 29-11 | OPC has no AGM; s.92(4) refers to the date the AGM "should have been held". | As stated; badge "Interpretation". |
| I5 | Small-company status for FY 2024-25 filings made after 01-12-2025. **Refined 25-09-2026:** each FY is judged under the limits in force on the date its MGT-7/7A was actually filed (or today, if unfiled). | The definition applies at the point of each compliance. Practitioners disagree whether the new limits apply to FY 2024-25 returns filed late or under GC 08/2025. | `AMBIGUOUS`; partner decision stored per entity per FY. |
| I6 | Rule 9B after the company becomes small again | 9B is triggered by being non-small at a FY end; the rule is silent on reversion. | `AMBIGUOUS`; partner decision. |
| I7 | MGT-8 for a small company filing MGT-7A (turnover ₹50–100 cr) | Rule 11(2) is not variant-specific; the V3 MGT-7A attachment behaviour is not confirmed. | `mgt8_required` computed independently; flag shown. |
| I8 | Normal filing fee for companies without share capital = ₹200 | The secondary table conflates this with incorporation fees. | Unverified row. |
| I9 | SH-7 additional fee | The Annexure has a separate line for increases in nominal capital; not located this session. | MULTIPLIER, unverified. |
| I10 | Pre-2026 annual DIR-3 KYC 30-September date: amending G.S.R. (2019) | Not re-located this session. | Row `DIR3KYC_ANNUAL` unverified. |
| I11 | LLP longer first FY is available to an LLP registered from 1 October to 31 March | s.2(1)(l) says "registered after the 30th day of September of a year". The seed reads this as the second half of any FY. | `llp_election_available()`; the election field is disabled otherwise. |
| I12 | Small-company status for FY *f* = paid-up at the end of *f* and turnover of FY *f*−1. A first FY has no preceding FY (turnover 0). | s.2(85) refers to the "immediately preceding financial year" turnover. | Used for MGT-7A, Rule 9B and the board-meeting regime. |
| I13 | XBRL and MGT-8 tests use the figures of the FY whose accounts or return are filed. | The rules say "turnover of ₹… or more" without naming the year. | `classify_aoc4`, `classify_mgt8`. |
| I14 | Rule 9B trigger is tested with the threshold in force **on that FY end** (no AMBIGUOUS). | Rule 9B's own wording: "as on the last day of a financial year". | Delta is caught at FY 2022-23 (₹8 cr > ₹4 cr) → due 30-06-2025 (after the extension), then I6 reversion question. |
| I15 | Practical anchors for items with no statutory date: MBP-1 annual = FY start + 120 days; MR-3 = AGM − 21 days; CRA-4 = FY end + 210 days; MGT-14 (accounts) = Board approval + 30 days, else AGM deadline − 21 days; MSC-1 = resolution + 30 days. | These are planning dates, not legal due dates. | All marked Provisional in the UI. |

**Engine design note (not a legal change):** director KYC obligations are keyed `person:{DIN}:{rule}:{period}` rather than `{entity_id}:…`, because the duty is per DIN (brief §6.4-C). A director on three boards therefore gets one KYC obligation, not three.

## Part 4: Partner decisions (recorded 25-09-2026)

| Q | Decision | Engine effect |
|---|---|---|
| Q1 | **Accept MCA's illustration**: a DIN allotted in FY 2025-26 is due 30-06-2029. | Golden test 3 asserts 30-06-2029; a legacy DIN asserts 30-06-2028. |
| Q2 | **File ADT-1 for the first auditor.** | Setting `adt1_for_first_auditor = true` by default. |
| Q3 | **Always ask** for FY 2024-25 small-company status. | Classifier returns `AMBIGUOUS` for any FY whose limits changed between FY end and filing; the partner decides. |
| Q4–Q6 | Still open (MGT-8 with MGT-7A; Rule 9B reversion; Govt-company DPT-3). | Kept as flagged interpretations. |
| Q7 | Downloads permitted. The mca.gov.in CDN (Akamai) still returned "Access Denied" to scripted download on 25-09-2026. GC 01/2026 was read from a law firm's summary PDF (mehta-mehta.com). It adds: MSC-1 at **50%** of normal fee and STK-2 at **25%** of normal fee during the scheme. | CCFS overlay extended with `fee_factor` for MSC1 (0.5) and STK2 (0.25). The primary PDFs still need a manual check. |
| Q8 | Folder `AICA-L2-Batch-89-Swapnil` confirmed (no surname). | — |

## Part 5: Penalty exposure (text only, never computed)

The obligation page shows penalty sections as citations: s.92(5), s.137(3), s.10A(2), s.12(8), s.64(2), s.86, s.117(2), s.405(4), s.450; LLP Act ss.34(5), 35(3), 25(3)/(4). These amounts are decided by the adjudicating officer under s.454 (companies) or s.76A (LLPs), so the app never computes them as payable.

## Part 6: Operational conventions added in Phase 3

- **Inherited (pre-engagement) items:** obligations due before the engagement start are generated and tagged *Pre-engagement*. Closed ones are hidden as history. **Open** ones stay visible, because the firm inherits them (e.g. Theta's two-year-old AOC-4). All of them are excluded from on-time KPIs.
- **Planning dates are Provisional:** see I15.
