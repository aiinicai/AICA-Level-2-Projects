# Rule-pack verification (Phase 0)

**Status:** draft for partner review. No rule has been signed off yet: every row loads with `verified: false`.
**Prepared:** 25-09-2026 (as-of date for "current law" in this document).
**Scope:** every row in Section 6.4 A–F of the brief, plus scheme and extension overlays.

---

## 1. How to read this document

### 1.1 Verdicts

| Verdict | Meaning |
|---|---|
| **MATCH** | The brief's row agrees with the source. |
| **PARTIAL** | Broadly right, but a detail (scope, slab, exclusion, day-count) needs changing. The correction is given. |
| **MISMATCH** | The brief is wrong on a point that changes a date, fee or applicability. The correction is given, and the seed data uses the corrected value. |
| **NOT FOUND** | I could not locate a source for the brief's statement. The row is kept as an interpretation and flagged. |

### 1.2 Evidence level (be honest about what was actually read)

The mca.gov.in and indiacode.nic.in servers returned **HTTP 403** to automated fetches from this environment. MCA document downloads open a save dialog, which I did not accept without your permission. As a result, **no primary gazette PDF was read directly in this session.** The evidence level below says exactly what the verdict rests on:

| Level | Meaning |
|---|---|
| **Q** | The primary text was read as a *verbatim reproduction* on a secondary site (the rule wording or fee table as quoted). This is strong, but still needs a primary check. |
| **K** | The text of the Act or Rules is well known and stable. It was stated from my working knowledge and **not re-read this session**. India Code link given. |
| **S** | Secondary summary only (a professional firm's or news article). Treat as a pointer. |

**Partner action:** for each row, open the primary URL, compare it with the "What the source says" column, then press *Verify* in the app. Rows at level S should be checked first.

### 1.3 Source register

| ID | Source | URL |
|---|---|---|
| CA13 | Companies Act, 2013 (India Code) | https://www.indiacode.nic.in/handle/123456789/2114?locale=en · PDF https://www.indiacode.nic.in/bitstream/123456789/2114/3/a2013-18.pdf |
| LLPA | LLP Act, 2008 (India Code) | https://www.indiacode.nic.in/handle/123456789/2023 · PDF https://www.indiacode.nic.in/bitstream/123456789/2023/1/A2009-06.pdf |
| LLPR | LLP Rules, 2009 as notified (MCA) | https://www.mca.gov.in/Ministry/pdf/LLPRulesasnotified.pdf |
| LLPR24 | LLP Rules r.24(8) text | https://indiankanoon.org/doc/21257880/ |
| GSR880 | Cos (Specification of Definition Details) Amdt Rules 2025, G.S.R. 880(E) dt 01-12-2025 | secondary: https://taxguru.in/company-law/small-company-definition-revised-capital-rs-10-cr-turnover-rs-100-cr-w-e-f-1-dec-2025.html · https://www.taxmann.com/post/blog/mca-raises-small-company-thresholds-to-rs-10-cr-capital-and-rs-100-cr-turnover/ |
| GSR943 | Cos (Appointment & Qualification of Directors) Amdt Rules 2025, G.S.R. 943(E) dt 31-12-2025, w.e.f. 31-03-2026 | secondary: https://taxguru.in/company-law/mca-notifies-significant-amendment-director-kyc-framework-w-e-f31-03-2026.html |
| KYCILL | MCA "Important MCA Update for Directors" (illustrations) | https://www.mca.gov.in/bin/dms/getdocument?mds=5wBuXrnw5F5hFYBugmtq1Q%3D%3D&type=open (403 / download here). Quoted at https://www.corplawupdates.in/updates/dir-3-kyc-web-2026-complete-guide |
| FEE26 | Cos (Registration Offices & Fees) Amdt Rules 2026, dt 21-04-2026 | https://www.scconline.com/blog/post/2026/04/24/companies-registration-offices-fees-amendment-rules-2026-dir-3-kyc-fee-changes/ |
| ROF12 | Cos (Registration Offices & Fees) Rules 2014, r.12 + Annexure (as amended) | https://ca2013.com/rule-12-companies-registration-offices-and-fees-rules-2014/ |
| LLP22 | LLP (Amendment) Rules 2022, G.S.R. 109(E) dt 11-02-2022, w.e.f. 01-04-2022 | https://taxguru.in/corporate-law/limited-liability-partnership-amendment-rules-2022.html |
| GSR464 | Exemptions to private companies, G.S.R. 464(E) dt 05-06-2015 | https://ca2013.com/notifications/exemptions-to-private-companies-05062015-gsr-464-e/ |
| MSME24 | Specified Cos (MSE payment info) Amdt Order 2024, dt 15-07-2024 | https://taxguru.in/company-law/msme-form-1-amended-companies-report-mses-overdue-payment.html |
| PAS23 | Cos (Prospectus & Allotment) Second Amdt Rules 2023, G.S.R. 802(E) (Rule 9B) | https://taxguru.in/company-law/companies-prospectus-allotment-securities-second-amendment-rules-2023.html |
| PAS25 | Cos (PAS) Amdt Rules 2025, dt 12-02-2025 (9B deadline extended to 30-06-2025) | https://foxmandal.in/News/mca-extends-dematerialisation-deadline-for-private-companies/ |
| LLP4D | LLP (Third Amendment) Rules 2023, dt 27-10-2023 (r.22A/22B, Forms 4A–4D) | https://taxguru.in/corporate-law/llp-third-amendment-rules-2023-register-of-partners-beneficial-interest.html |
| CSR2 | CSR-2 filing timelines (Accounts Rules r.12(1B)) | https://lexplosion.in/mca-extends-due-date-for-filing-form-csr-2-report-on-csr-for-fy-2023-2024-till-30th-june-2025/ |
| GC01-26 | General Circular 01/2026 dt 24-02-2026 (CCFS-2026) | https://x.com/MCA21India/status/2026661150923120877 · copy: https://www.mehta-mehta.com/static/pdfs/mca/MCA-CIRCULAR-CCFS-compressed.pdf · summary: https://www.pwc.in/research-insights/news_alert/regulatory-insights/mca-introduces-companies-compliance-facilitation-scheme-2026-path-to-regularise-pending-filings-dormancy-and-closure-with-reduced-fees-and-immunity-benefits.html |
| GC03-26 | General Circular 03/2026 dt 08-07-2026 (CCFS to 31-08-2026) | https://ibclaw.in/extension-of-companies-compliance-facilitation-scheme-2026-ccfs-2026-up-to-31st-august-2026-reg-mca-general-circular-no-03-2026-dated-08-07-2026/ |
| GC04-26 | General Circular 04/2026 dt 31-08-2026 (CCFS to 15-09-2026) | https://www.india-briefing.com/news/india-mca-extends-ccfs-2026-deadline-15-september-46746.html/ |
| GC02-26 | General Circular 02/2026 dt 19-06-2026 (DPT-3 FY 2025-26, no additional fee till 31-07-2026) | https://www.corplawupdates.in/updates/mca-dpt3-due-date-extended-31-july-2026 |
| GC08-25 | General Circular 08/2025 dt 30-12-2025 (AOC-4/MGT-7 FY 2024-25, no additional fee till 31-01-2026) | https://www.taxmann.com/post/blog/mca-extends-due-date-filings/ |

---

## 2. A — Company, one-time / first year

| Code | Brief says | What the source says | Verdict | Ev. | Correction / seed value |
|---|---|---|---|---|---|
| FIRST_BM | Incorporation + 30 days | s.173(1): "first meeting of the Board within thirty days of the date of its incorporation". s.173(5) 2nd proviso: s.173 does not apply to an OPC with only one director. | MATCH | K [CA13] | None. Alpha: 20-01-2026 + 30 = **19-02-2026**. |
| FIRST_AUDITOR | Incorp + 30 days; if Board fails, EGM within 90 days | s.139(6): the Board appoints the first auditor within 30 days of registration. If it fails, it informs members, who appoint at an EGM within 90 days. Government companies: the C&AG appoints within 60 days (s.139(7)). | PARTIAL | K [CA13] | Add a Government-company branch (s.139(7), C&AG, 60 days). Flag only, not computed. |
| ADT1_FIRST | Appointment + 15 days; Partner setting | Rule 4(2) Audit & Auditors Rules ties ADT-1 to "the meeting in which the auditor is appointed". Practice is divided on the first auditor. | MATCH (interpretation) | K | Firm-level setting `adt1_for_first_auditor` (default **file**). The row carries an "Interpretation" badge. |
| SHARE_CERT | Incorporation + **60 days** | s.56(4)(a): within **two months** from the date of incorporation (subscribers to the memorandum). | **MISMATCH** | K [CA13] | Use `{months: 2}`. Alpha: **20-03-2026** (not 21-03-2026). **Golden test 1 is changed.** Also: where Rule 9B applies, certificates must be issued in demat form only. |
| MBP1_DIR8_FIRST | At first BM | s.184(1): at the first Board meeting the director participates in, then at the first BM of every FY and on change. Rule 14(1) AQD: DIR-8 **before appointment or re-appointment** (not annual by law; annual in practice). | PARTIAL | K | Keep the checklist item. Label DIR-8 "on appointment/re-appointment (statutory); annual (firm practice)". |
| REGISTERS | ss.85, 88, 170, 189 | Also s.186(9) (register of loans, guarantees, investments, MBL-2). | PARTIAL | K | Add s.186(9). |
| BOOKS | s.128 | s.128(1): at the registered office, or at another place in India decided by the Board (intimate the ROC within 7 days, Rule 2A Accounts Rules). | MATCH | K | Add a note on the alternative place. |
| INC22_VERIFY | +30 days, only if RO not furnished | s.12(2): verification of RO within 30 days of incorporation. SPICe+ captures the RO address at incorporation, so this is normally not needed. | MATCH | K | Applicability predicate `ro_not_furnished_at_incorporation`. |
| INC20A | +180 days, share capital, incorporated on/after 02-11-2018 | s.10A(1)(a): within 180 days of incorporation, for a company incorporated after the Companies (Amendment) Ordinance 2018 (02-11-2018) **and having share capital**. This includes s.8 companies with share capital. | MATCH | K | Alpha: **19-07-2026**. Fee regime: MULTIPLIER. Penalty text s.10A(2). |

## 3. B — Company, recurring

| Code | Brief says | What the source says | Verdict | Ev. | Correction / seed value |
|---|---|---|---|---|---|
| BOARD_MTGS | REGULAR ≥4/yr, gap ≤120 d; RELAXED 1 per half of calendar year, gap ≥90 d | s.173(1) and s.173(5) as stated. The private start-up relaxation comes from the exemption notification G.S.R. 583(E) dt 13-06-2017, which reads "private company (start-up)" into s.173(5). | MATCH | K | Cite G.S.R. 583(E) for the start-up branch (S-level; verify). |
| MBP1_ANNUAL | First BM of each FY and on change | s.184(1). | MATCH | K | — |
| AGM | First: FY1 close + 9 months; later: FY close + 6 months, ≤ 15 months after previous AGM; not OPC | s.96(1) as stated. OPC exempt. The ROC may extend a non-first AGM by up to 3 months (s.96(1) 3rd proviso). | PARTIAL | K | Add optional `agm_extension_granted_until` (entity × FY) with an SRN or letter reference. Alpha: first AGM deadline **31-12-2027**. |
| AOC4 | AGM + 30 days, or last permissible AGM date + 30 | s.137(1) and its proviso for when no AGM was held. | MATCH | K | Alpha provisional: **30-01-2028**. |
| AOC4 variant | XBRL: listed or its subsidiary; paid-up ≥ ₹5 cr; turnover ≥ ₹100 cr; Ind AS company (excl. banking, insurance, power, NBFC) | Cos (Filing of Documents & Forms in XBRL) Rules 2015 r.3: same. The exclusion list also covers **housing finance companies**. | PARTIAL | K | Add HFC to the exclusions. Note: **Delta (paid-up ₹8 cr) needs AOC-4 XBRL even though it is small**. |
| AOC4_OPC | FY close + 180 days | s.137(1) proviso (OPC). | MATCH | K | Beta FY 2025-26: **27-09-2026**. |
| MGT7 | AGM + 60 days or deemed AGM + 60; MGT-7A for small co and OPC | s.92(4); Rule 11(1) Mgmt & Admin Rules. | MATCH | K | Alpha provisional MGT-7A: **29-02-2028**. Beta (OPC): **29-11-2026** (interpretation: 30-09-2026 + 60). |
| MGT8 | Listed, or paid-up ≥ ₹10 cr, or turnover ≥ ₹50 cr | Rule 11(2). | MATCH | K | **New interaction:** under the ₹100 cr turnover limit, a *small* company can have turnover ≥ ₹50 cr (Delta: ₹80 cr), so it needs MGT-8 while filing MGT-7A. **Open question Q4:** how the V3 MGT-7A attaches MGT-8. The seed keeps `mgt8_required` independent of the variant. |
| ADT1 | AGM + 15 days | s.139(1); Rule 4(2). | MATCH | K | Fee: MULTIPLIER **with the s.139 slab ≤ 15 days = 1×** (see F). |
| DPT3 | 30 June yearly; excl. Govt/bank/NBFC/HFC | Rule 16, Acceptance of Deposits Rules: return by 30 June, for the position as at 31 March. Rule 1(3) excludes banking companies, NBFCs, HFCs and companies notified by the Central Government. It does **not** list Government companies. | PARTIAL | K | Drop "Govt" from the exclusion predicate unless the partner confirms a notification (open question Q6). Add overlay **GC 02/2026**: DPT-3 FY 2025-26 without additional fee till **31-07-2026**. Alpha: **30-06-2026**. |
| MSME1_H1 / H2 | 31 Oct / 30 Apr; only if > 45 days; fee "verify" | Specified Companies Order 2019 as amended 15-07-2024: only companies with payments to micro/small suppliers outstanding > 45 days file. Half-yearly: 31 Oct (Apr–Sep), 30 Apr (Oct–Mar). No nil return. | PARTIAL | S [MSME24] | **Fee regime `NONE`**: MSME-1 carries no filing fee. Non-filing falls under s.405(4) penalty (text only). Test 9 is unchanged. |
| PAS6 | Half-year + 60 days; 9A cos; 9B cos once ISIN obtained | r.9A(8): within 60 days of each half-year. r.9B applies r.9A(4)–(10) *mutatis mutandis*, so PAS-6 also applies to 9B companies. Government companies are excluded from 9B. | MATCH | Q [PAS23] | Gamma: **29-11-2026** (H1 FY 2026-27), **30-05-2027** (H2). Fee: MULTIPLIER. |
| DEMAT_9B | 18 months from end of FY in which company first ceased to be small | r.9B(1)/(2): a private company that is not small as on the last day of a FY ending on/after 31-03-2023 complies within 18 months of that FY's closure. First cohort extended to **30-06-2025** (PAS Amdt Rules 2025, 12-02-2025). Producer companies: 31-03-2028. | PARTIAL | Q/S [PAS23, PAS25] | Add transitional row `DEMAT_9B_FIRST` (FY 2022-23 cohort, due 30-06-2025). **Ambiguity:** whether 9B obligations fall away if the company becomes small again (many will, under the Dec-2025 limits). The seed returns AMBIGUOUS and needs a partner decision (Q5). |
| CSR2 | "With/after AOC-4 — verify" | Accounts Rules r.12(1B): CSR-2 is filed as an addendum to AOC-4 / AOC-4 XBRL / AOC-4 NBFC. Separate cut-off dates applied to earlier years (e.g. FY 2023-24 extended to 30-06-2025). For current years it is linked to AOC-4 on V3. | PARTIAL | S [CSR2] | Due = **same date as AOC-4** for FY 2024-25 onward. Earlier years are historic rows, left unverified. |
| MGT14_FS | Public cos; private exempt | G.S.R. 464(E): s.117(3)(g) does not apply to private companies. Condition: this and all s.462 exemptions apply only to a private company that is **not a subsidiary of a public company**. | PARTIAL | Q [GSR464] | Predicate: `public_company OR private_subsidiary_of_public`. Same condition for all private-company exemptions (MR-1 and board-resolution MGT-14 items). |
| CRA2 | BM + 30 d or FY start + 180 d, earlier | Cost Records & Audit Rules r.6(2). | MATCH | K | — |
| CRA4 | Receipt + 30 days | r.6(6); the report is due to the Board within 180 days of FY close (r.6(5)). | MATCH | K | Anchor `EVENT_DATE` (report receipt). Provisional anchor = FY close + 180. |
| SEC_AUDIT | Listed; public paid-up ≥ ₹50 cr or turnover ≥ ₹250 cr; any company with bank/PFI borrowings ≥ ₹100 cr; brief's facts field = *max during year* | Rule 9(1), Appointment & Remuneration Rules, as stated. **Explanation:** paid-up, turnover and outstanding borrowings are taken **"as on the last date of the latest audited financial statement"**. | **MISMATCH** (input) | K | Classifier must use **borrowings at FY end**, not the maximum during the year. Add AnnualFacts field `bank_borrowings_at_fy_end`. Keep `bank_borrowings_max_in_year` for internal audit (r.13 uses "at any point of time during the preceding FY"). |

## 4. C — Directors (per DIN)

| Code | Brief says | What the source says | Verdict | Ev. | Correction / seed value |
|---|---|---|---|---|---|
| DIR3KYC_ANNUAL | 30 Sep each year; to 30-03-2026 | Rule 12A (pre-substitution): a DIN holder as at 31 March files by 30 September of the next FY. | MATCH | K | FY 2024-25 → **30-09-2025**. The amending G.S.R. that moved the date to 30 Sep (2019) is still to be captured. Row `effective_to: 2026-03-30`. |
| DIR3KYC_TRIENNIAL | 30 June after every third consecutive FY in which DIN held at 31 March; G.S.R. 943(E) dt 31-12-2025; from 31-03-2026 | Substituted r.12A: *"Every individual who holds a DIN as on the 31st March of a financial year, shall file … DIR-3 KYC Web … on or before the 30th June of the immediately following every third consecutive financial year."* **MCA illustrations [KYCILL]:** (a) DIN on/before 31-03-2025 and KYC done → next due **Apr–Jun 2028**; (b) **DIN allotted during FY 2025-26 → next due Apr–Jun 2029** (cycle reckoned from the FY of allotment); (c) interim updates do not reset the cycle. | **MISMATCH** (golden test 3) | Q [GSR943, FEE26] + S [KYCILL via secondary] | `kyc_due()` seed: **legacy DIN (≤ 31-03-2025) → 30-06-2028**, then +3 years. **DIN allotted in FY *Y* (≥ 2025-26) → 30 June of (end-year of *Y* + 3)**, so FY 2025-26 → **30-06-2029**, FY 2026-27 → 30-06-2030. **Alpha's directors (DIN Jan 2026) → 30-06-2029, not 30-06-2028.** The plain rule text arguably gives 2028 for them; MCA's own illustration says 2029. The seed follows MCA, is marked Interpretation and unverified, and the partner can override per person. |
| DIR3KYC_CHANGE | Change + 30 days; from 31-03-2026 | Substituted r.12A(2): update within 30 days of a change in mobile, e-mail or residential address. | MATCH | Q | 05-08-2026 → **04-09-2026**. Does not reset the triennial cycle. |
| DIR3KYC_FEES | Nil on time; ₹5,000 late/reactivation; ₹500 per event-based filing; notified 21-04-2026 | FEE26 Annexure: nil if filed by 30 June after every third FY; ₹5,000 if late or for reactivation; ₹500 "for every filing" for a change. In force 21-04-2026. | MATCH | Q [FEE26] | **Gap window:** 31-03-2026 → 20-04-2026 (new rule in force, new fee entry not yet). The fee for event filings in that window is uncertain. Seed = ₹500, marked uncertain. |

## 5. D — Company, event-driven

| Code | Brief says | What the source says | Verdict | Ev. | Correction |
|---|---|---|---|---|---|
| DIR12 | +30 d | s.170(2); Rules 15, 18 AQD. | MATCH | K | Epsilon: 10-10-2026 → **09-11-2026**. |
| DIR11 | +30 d, optional by director | s.168(1) proviso ("may"); r.16. | MATCH | K | Status default = optional (not counted in KPIs). |
| MR1 | +60 d; verify private | s.196(4). **G.S.R. 464(E): s.196(4) and (5) do not apply to private companies** (not subsidiaries of public cos). | PARTIAL | Q [GSR464] | Applicability: public, or private subsidiary of public. Not PRIVATE/OPC otherwise. |
| PAS3_PP | +15 d | s.42(9) (as amended 2017). | MATCH | K | Epsilon: **16-10-2026**. |
| PAS3 | +30 d | s.39(4); r.12 PAS. | MATCH | K | Epsilon: **31-10-2026**. Higher additional fee on repeat default (see F). |
| SH7 | +30 d | s.64(1). | MATCH | K | Fee regime for SH-7 is a separate Annexure line (increase in nominal capital). **NOT FOUND** in this session; seed MULTIPLIER, unverified. |
| MGT14 | +30 d | s.117(1). | MATCH | K | Epsilon: **04-11-2026**. |
| INC22 | +30 d (+MGT-14 if SR) | s.12(4) as amended by Companies (Amendment) Act 2017 (15 → 30 days). | MATCH | K | Higher additional fee on repeat default (see F). |
| CHG1 | +30 d; further period on additional/ad-valorem fees — verify | s.77(1) as amended 2019: 30 days. The ROC may allow up to **60 days from creation** on additional fee. After that, a further **60 days** on ad-valorem fee. Beyond that, only condonation by the Central Government (RD) under s.87. | PARTIAL | Q [ROF12] + K | Model three windows: ≤ 30 normal; 31–60 additional; 61–120 additional + ad valorem; > 120 → "s.87 condonation required", no fee computed. |
| CHG4 | +30 d | s.82(1); the ROC may allow up to 300 days on additional fee. | MATCH | K | — |
| ADT3 | +30 d by auditor | s.140(2). | MATCH | K | Obligation of the auditor; tracked as informational. |
| CASUAL_VACANCY | Board 30 d; ADT-1 + 15 | s.139(8)(i): Board within 30 days. **If the vacancy is caused by resignation**, members must approve at a GM within **3 months** of the Board's recommendation. | PARTIAL | K | Add a linked item `CASUAL_VACANCY_GM` (+3 months) when the cause = resignation. |
| BEN2 | +30 d | s.90(4); SBO Rules r.4. | MATCH | K | — |
| MGT6 | +30 d | s.89(6); r.9(3) Mgmt & Admin Rules. | MATCH | K | — |
| SH11 | +30 d | s.68(10). | MATCH | K | — |
| MSC1 / MSC3 | Event; MSC-3 annually — verify | s.455; Companies (Miscellaneous) Rules 2014: MSC-3 (return of dormant company) within 30 days from the end of each FY. | MATCH | K | MSC3 anchor FY_END + 30 d, while status = Dormant. |

## 6. E — LLP

| Code | Brief says | What the source says | Verdict | Ev. | Correction |
|---|---|---|---|---|---|
| LLP FY | Election if incorporated on/after 1 Oct | s.2(1)(l) proviso: an LLP registered **after 30 September** may close its first FY on 31 March of the next year. | MATCH | K [LLPA] | Eta's elected first FY (15-11-2025 → 31-03-2027) is **~16½ months, not 18**. The label is corrected; the dates are unchanged. |
| LLP_FORM3_INC | +30 d | s.23; r.21. | MATCH | K | Eta: **15-12-2025**. |
| LLP_FORM3_CHG | +30 d | r.21. | MATCH | K | — |
| LLP_FORM4 | +30 d | s.25; r.22. | MATCH | K | — |
| LLP_FORM15 | +30 d | s.13(3); r.17. | MATCH | K | — |
| LLP_FORM11 | FY close + 60 d (30 May) | s.35; r.25. | MATCH | K | Eta: **30-05-2027** with election / **30-05-2026** without. |
| LLP_FORM8 | 30 d after 6 months of FY (30 Oct) | s.34; r.24. | MATCH | K | Eta: **30-10-2027** / **30-10-2026**. |
| LLP_AUDIT | Required if turnover > ₹40 L **or** contribution > ₹25 L | r.24(8) proviso: an LLP "whose turnover does not exceed, in any financial year, forty lakh rupees, **or** whose contribution does not exceed twenty-five lakh rupees" is **not** required to be audited. | **MISMATCH** | Q [LLPR24] | Audit is required only if turnover > ₹40 L **AND** contribution > ₹25 L. The brief's `llp_audit_required` is inverted for the mixed case. |
| is_small_llp | Contribution ≤ ₹25 L and turnover ≤ ₹40 L | s.2(1)(ta) (inserted 2021, w.e.f. 01-04-2022): contribution ≤ ₹25 L **and** turnover **as per the Statement of Accounts and Solvency for the immediately preceding FY** ≤ ₹40 L. The Government may raise these to ₹5 cr / ₹50 cr; no higher limits were found to be notified. | PARTIAL | S | Use **preceding-FY** turnover. The seed needs Zeta's FY 2024-25 turnover. |
| LLP_BEN2 | +30 d, verify | LLP (Significant Beneficial Owners) Rules 2023 (Nov 2023): LLP BEN-2 within 30 days of receiving LLP BEN-1. | MATCH | S | G.S.R. number to be captured. |
| LLP_4D | "Verify; LLP Rules as amended 2024" | **LLP (Third Amendment) Rules 2023, dt 27-10-2023**: r.22A register of partners (Form 4A); r.22B declarations by non-beneficial partner (4B) and beneficial owner (4C), each within 30 days. The LLP files **Form 4D** with the ROC **within 30 days of receiving the declaration**. | PARTIAL | S [LLP4D] | Correct the citation (2023, not 2024). Due = receipt + 30 d. |

## 7. F — Fee engine

| Regime | Brief says | What the source says | Verdict | Ev. | Correction |
|---|---|---|---|---|---|
| NORMAL (share capital) | < 1 L ₹200; 1–<5 L ₹300; 5–<25 L ₹400; 25 L–<1 cr ₹500; ≥ 1 cr ₹600 | Same [ROF12]. The "no fee" relief for companies with nominal capital up to ₹15 lakh (earlier ₹10 lakh) applies to **incorporation** fees, not to later forms. | MATCH | Q | Alpha (nominal ₹10 L) pays ₹400 on post-incorporation forms. |
| NORMAL (no share capital) | ₹200 | ca2013's table mixes this with incorporation fees by member count. | PARTIAL | S | Keep ₹200, unverified (Q7). |
| PER_DAY_100 | ₹100/day, no cap, per form; AOC-4 family, MGT-7/7A | Annexure (2018 amendment): documents under s.92 and s.137 → ₹100 per day. | MATCH | Q [ROF12] | Tests 13 unchanged: ₹73,400; ₹6,000 + ₹6,000. |
| MULTIPLIER | ≤ 30 d 2×; 31–60 4×; 61–90 6×; 91–180 10×; > 180 12× | Same, **plus** (Amdt Rules 2022): for forms under **s.139 (ADT-1) and s.157** there is a first slab **≤ 15 days = 1×**, then 16–30 = 2×. | PARTIAL | Q [ROF12] | Add the s.139/s.157 slab. Test 12 (109 days → 10×, ₹4,400) is unchanged. |
| HIGHER_MULTIPLIER | 3×/6×/9×/15×/18×, form list for Phase 0 | "Higher additional fee" applies where **INC-22 or PAS-3** is filed late on **two or more occasions within 365 days** of the last belated filing of that form. The 15–30 day slab is 3× (no ≤ 15 slab). | PARTIAL (list resolved) | Q [ROF12] | Form list = {INC22, INC22_VERIFY, PAS3, PAS3_PP}. `prior_defaults` counts belated filings of the same form in the last 365 days. |
| CHARGE | Verify | Charges created on/after 02-11-2018: delay ≤ 30 d (beyond the first 30) → small co/OPC 3×, others 6× normal. Next 60 d → same multiple **+ ad valorem 0.025% (max ₹1 lakh) small/OPC, 0.05% (max ₹5 lakh) others** of the amount secured. | PARTIAL | Q [ROF12] | Implement as above. Inputs: `charge_amount`, `is_small_or_opc`. |
| FIXED (DIR-3 KYC) | 0 / 5,000 / 500 | FEE26. | MATCH | Q | — |
| LLP_MATRIX normal | ≤ 1 L ₹50; 1–5 L ₹100; 5–10 L ₹150; 10–25 L ₹200; 25 L–1 cr ₹400; > 1 cr ₹600 | Same [LLP22 Annexure A]. | MATCH | Q | — |
| LLP_MATRIX additional | ≤ 15 / 16–30 / 31–60 / 61–90 / 91–180 / 181–360 / > 360; small 1,2,4,6,10,15; other 1,4,8,12,20,30; > 360 for Forms 8/11 add ₹10/₹20 per day | Same multipliers. **Missing slab:** beyond 360 days, *other* forms pay **25× (small) / 50× (other)**. Forms 8 and 11 beyond 360 days pay **15× / 30× plus ₹10 / ₹20 per day for each day beyond 360**. | PARTIAL | Q [LLP22] | Add the > 360 slab for non-annual forms; per-day accrual only on days > 360. Test 14 (Zeta 113 days → ₹150 + 10 × ₹150 = **₹1,650**) is unchanged. |

## 8. Scheme and extension overlays (`schemes.yaml`)

| Code | Source says | Verdict | Ev. | Seed |
|---|---|---|---|---|
| CCFS_2026 | GC 01/2026 (24-02-2026): window 15-04-2026 → 15-07-2026. Extended to 31-08-2026 by GC 03/2026 (08-07-2026, citing the MCA21 data-centre fire of 05-06-2026) and to **15-09-2026** by GC 04/2026 (31-08-2026). Relief: normal fee + **10% of additional fee**. Covered forms: MGT-7, MGT-7A, AOC-4, AOC-4 CFS, AOC-4 XBRL, AOC-4 NBFC (Ind AS), AOC-4 CFS NBFC (Ind AS), **ADT-1**, FC-3, FC-4 and 1956-Act equivalents. Excluded: companies already under strike-off action, those that applied for strike-off, those that applied for dormancy before the scheme, those dissolved by amalgamation, and vanishing companies. Immunity from penalty if filed before, or within 30 days of, an adjudication notice. Companies only. | MATCH (+ details) | S | Window 15-04-2026 → 15-09-2026. `form_codes` as listed. `entity_types` excludes LLP. Exclusion flags on the entity. Test 15 unchanged (Theta 10-09 → 10%; 20-09 → full; LLP → none). |
| EXT_DPT3_FY2526 | GC 02/2026 (19-06-2026): DPT-3 FY 2025-26 may be filed without additional fee up to 31-07-2026 (statutory due date unchanged). | NEW | S | `waive_additional_until: 2026-07-31`. The due date stays 30-06-2026. |
| EXT_ANNUAL_FY2425 | GC 08/2025 (30-12-2025): AOC-4 family and MGT-7/7A for FY 2024-25 without additional fee up to 31-01-2026. | NEW | S | Overlay for FY 2024-25. Relevant to Delta's AMBIGUOUS small-company case: many FY 2024-25 filings fell after 01-12-2025 *because of* this extension. |

## 9. Classification thresholds

| Classifier | Source | Verdict | Ev. | Note |
|---|---|---|---|---|
| is_small_company | s.2(85); G.S.R. 880(E) dt 01-12-2025 raises limits to paid-up ≤ ₹10 cr and turnover ≤ ₹100 cr (earlier ₹4 cr / ₹40 cr, from 2022). Turnover = **immediately preceding FY** P&L. Excludes public, holding, subsidiary, s.8, and special-Act companies. | MATCH | S [GSR880] | The earlier ₹4 cr / ₹40 cr row starts 15-09-2022 (Amdt Rules 2022); rows before that are ₹2 cr / ₹20 cr. Add them so back-years classify correctly. |
| mgt8_required | Rule 11(2) | MATCH | K | See the Delta note above. |
| csr_applicable | s.135(1) "immediately preceding FY" (after 2019/2021 amendments): net worth ≥ ₹500 cr / turnover ≥ ₹1,000 cr / net profit ≥ ₹5 cr. | MATCH | K | — |
| secretarial_audit | Rule 9 | MISMATCH (input field) | K | See SEC_AUDIT row above. |
| internal_audit | Rule 13: listed; unlisted public with paid-up ≥ ₹50 cr, turnover ≥ ₹200 cr, borrowings ≥ ₹100 cr **or** deposits ≥ ₹25 cr; private with turnover ≥ ₹200 cr **or** borrowings ≥ ₹100 cr "at any point of time during the preceding FY". | MATCH | K | Add AnnualFacts `deposits_outstanding_max`. |
| rule_9b | See DEMAT_9B | PARTIAL | Q | AMBIGUOUS on reversion to small. |
| board_meeting_regime | s.173 + G.S.R. 583(E) (start-up) | MATCH | K | — |
| is_small_llp / llp_audit_required | See E | MISMATCH (audit) | Q | — |

---

## 10. Golden tests affected

| # | Brief value | Corrected value | Reason |
|---|---|---|---|
| 1 | Share certificates 21-03-2026 | **20-03-2026** | s.56(4)(a) says "two months", not 60 days. |
| 3 | Alpha directors' KYC 30-06-2028 | **30-06-2029** (interpretation, MCA illustration) | DIN allotted in FY 2025-26; the cycle is reckoned from the FY of allotment. A legacy DIN is still 30-06-2028 and is tested separately. |
| 6 | Delta small under new limits | Unchanged, but seed data needs **FY 2024-25 turnover**. Delta additionally needs **AOC-4 XBRL** (paid-up ≥ ₹5 cr) and **MGT-8** (turnover ≥ ₹50 cr). | The definition uses preceding-FY turnover. |
| 8 | "18-month" election | ~16½-month first FY; dates unchanged | Arithmetic. |
| 14 | ₹1,650 | Unchanged (multipliers confirmed) | — |

All other golden-test dates and fees were re-computed by hand and match.
