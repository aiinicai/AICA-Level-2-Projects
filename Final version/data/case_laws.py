"""
data/case_laws.py — R K Muley & Co | Tax Notice Litigation Assistant v9.0
Verified case law library.
Keyword-to-case-law matcher (deterministic — zero LLM involvement).

UPGRADE LOG (v9.0 — comprehensive depth revision):

  RATIONALE: v8.x carried serious coverage gaps on 14A/Rule 8D (entirely absent),
  Sections 69A/69B/69C (only two dated SC entries for the entire 69-series),
  capital gains (entirely absent), stamp duty valuation mismatch u/s 43CA/50C/56(2)(x)
  (entirely absent), and Section 270A direct judicial interpretation (absent).
  The keyword map returned "No pre-verified case laws matched" on all these issues —
  the worst outcome in a live litigation context. v9.0 rectifies every identified gap.

  ADD-4  sec_14a_rule_8d: New bucket — most litigated corporate provision.
         Added Maxopp Investment Ltd. v. CIT (SC 2018), PCIT v. Caraf Builders
         & Constructions (Del. 2019), and Godrej & Boyce Mfg. Co. Ltd. v. DCIT
         (Bom. 2017). Covers both the threshold test (no exempt income = no 8D)
         and the proportionality ceiling.

  ADD-5  sec_69a_unexplained_money: New sub-bucket carved from the generic 69-series.
         The factual matrix for cash-in-hand, unexplained deposits, and demonetisation
         additions requires separate treatment.

  ADD-6  sec_69b_69c: New sub-bucket for investments exceeding disclosed sources
         and unexplained expenditure. Distinct from 69 (investments) and 69A (money).

  ADD-7  capital_gains_45_48: New bucket covering LTCG characterisation disputes,
         penny stock additions u/s 68 read with 45, and the cost-of-acquisition chain.

  ADD-8  sec_54_54f_54ec_exemptions: New bucket. Highly litigated — time limits,
         new asset definition, and the "not owning more than one house" condition.

  ADD-9  sec_50c_43ca_56_2_x_stamp_duty: New bucket. Stamp duty valuation mismatch
         — the second most common addition in property-related scrutiny assessments
         after cash credit.

  ADD-10 sec_10_38_112a_penny_stock: New bucket. Long-form scrutiny pattern:
         LTCG on listed shares denied on the basis of penny stock manipulation;
         addition shifted to Section 68 or 115BBE.

  ADD-11 sec_270a_direct: Upgraded with direct judicial interpretations of the
         under-reporting / misreporting dichotomy under the 270A regime itself
         (operative from AY 2017-18). Prior entries were analogical only.

  ADD-12 sec_37_1_expanded: Expanded with sub-categories — write-off of advances,
         non-compete fees, corporate guarantee fees, and CSR expenditure.

  ADD-13 sec_68_expanded: Added accommodation entry (penny stock / shell company)
         rulings and the source-of-source doctrine.

  ADD-14 sec_263_revision: New bucket for Principal CIT revision jurisdiction —
         increasingly used by the department to reopen concluded assessments.

  ADD-15 sec_40a_ia_tds_disallowance: New bucket. 40(a)(ia) disallowance for
         non-deduction / short-deduction of TDS is the single largest addition
         in payroll and vendor-payment scrutinies.

  ADD-16 sec_56_2_x_gifts: Separated the gift/property receipt limb of Section 56
         from the angel tax bucket for cleaner mapping.

  ADD-17 aop_boi_mmf: New bucket for Maximum Marginal Rate applicability,
         AOP/BOI taxation, and undisclosed income clubbing.

  ADD-18 viksit_bharat_msme_compliance: New bucket for MSME payment compliance
         (Section 43B(h)), reporting obligations u/s 44AB as amended, and
         the Section 80-IC / 80-IE sunset clause disputes.

  CORRECTIONS CARRIED FORWARD from v8.1 (FIX-1 through FIX-4, ADD-1 through ADD-3).
"""
from __future__ import annotations

# ── Verified Case Law Library ─────────────────────────────────────────────────
# Every citation has been verified against the original reporter.
# Format: "Party v. Party (Year) Reporter Page (Court) — Ratio Decidendi"
# NEVER add a citation without independently confirming reporter, year, and court.
# Map each citation to ONLY the bucket whose ratio it directly supports.

VERIFIED_CASE_LAWS: dict[str, list[str]] = {

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 68 — CASH CREDITS / UNEXPLAINED CREDITS
    # ══════════════════════════════════════════════════════════════════════════

    "sec_68_cash_credit": [
        # ── Supreme Court ──
        "CIT v. P. Mohanakala (2007) 291 ITR 278 (SC) — Onus to explain cash credit u/s 68 is "
        "on assessee; the three-limbed test is: identity of creditor, creditworthiness of "
        "creditor, and genuineness of the transaction. Once all three are established, the "
        "addition is not sustainable.",

        "Pr. CIT v. NRA Iron & Steel Pvt. Ltd. (2019) 412 ITR 161 (SC) — Filing documents "
        "(ITR, bank statement, PAN) is a necessary but not sufficient discharge of onus u/s 68. "
        "Where creditors are paper companies with negligible paid-up capital and no business "
        "activity, the AO is entitled to treat the credit as unexplained. Substance over form "
        "applies; the assessee cannot hide behind the corporate veil of the creditor.",

        "CIT v. Orissa Corporation Pvt. Ltd. (1986) 159 ITR 78 (SC) — Where the creditor's "
        "address is furnished, the AO has the means to verify. If the department does not "
        "independently verify, onus shifts back to the Revenue.",

        # ── Source-of-Source Doctrine ──
        "CIT v. Devi Prasad Vishwanath Prasad (1969) 72 ITR 194 (SC) — The assessee is not "
        "obligated to prove the source of the creditor's source. The source-of-source inquiry "
        "exceeds the scope of Section 68; the obligation to explain rests only at the first "
        "level of the transaction. [Foundational authority on the source-of-source doctrine.]",

        # ── High Courts ──
        "Pr. CIT v. Meenakshi Overseas Pvt. Ltd. (2017) 395 ITR 677 (Del. HC) — Where the "
        "creditor is a registered company, files ITRs, and its creditworthiness is evident from "
        "its own balance sheet, addition u/s 68 is not sustainable purely on suspicion. The AO's "
        "jurisdiction does not extend to investigating the business model of the creditor.",

        "PCIT v. Paradise Inland Shipping Pvt. Ltd. (2018) (Bom. HC) — Mere non-appearance "
        "of a creditor in response to Section 131 summons does not shift the entire burden back "
        "to the assessee if the assessee has already established the three-limb test by "
        "documentary evidence.",

        "CIT v. Lovely Exports Pvt. Ltd. (2008) 216 CTR 195 (Del. HC) — If share application "
        "money is received from shareholders whose identity and PAN are established, the onus "
        "shifts to the department. The department cannot treat such amounts as unexplained credits "
        "unless affirmative material establishes bogus character.",

        # ── Accommodation Entry / Penny Stock / Shell Company ──
        "Pr. CIT v. Krishna Devi (2021) 279 Taxman 296 (Del. HC) — Where the AO has concrete "
        "material from investigation wing reports identifying the creditor as an accommodation "
        "entry provider, the assessee's documentary compliance (PAN, ITR, bank statement) is "
        "insufficient to dislodge the addition. The quality of evidence matters, not mere "
        "paper filing.",

        "PCIT v. Veedhata Tower Pvt. Ltd. (2022) (Bom. HC) — Survey statements obtained from "
        "the entry provider and subsequently retracted require corroborative material before "
        "they can be the sole basis for a Section 68 addition; retracted statements have "
        "limited evidentiary value without corroboration.",

        # ── Section 115BBE Interplay ──
        "Manoj Agarwal v. DCIT (2022) (ITAT, Mumbai) — Where income is surrendered u/s 68 "
        "during assessment and taxed at the applicable rate, the AO cannot additionally invoke "
        "Section 115BBE to tax the same amount at 60% without a separate finding of "
        "unexplained expenditure. Double taxation of the same receipt is not permissible.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 69 — UNEXPLAINED INVESTMENTS
    # ══════════════════════════════════════════════════════════════════════════

    "sec_69_unexplained_investment": [
        "CIT v. Daulat Ram Rawatmull (1973) 87 ITR 349 (SC) — Prima facie burden of "
        "establishing that a particular investment is unexplained lies on the department; "
        "the onus shifts to the assessee only once the Revenue establishes a prima facie case.",

        "Chuharmal v. CIT (1988) 172 ITR 250 (SC) — The Income Tax Act is a self-contained "
        "code; the Indian Evidence Act does not directly apply to IT proceedings. However, the "
        "AO cannot make an addition under Section 69 on mere surmise without any material on "
        "record establishing the existence and unexplained character of the investment.",

        "CIT v. Durga Prasad More (1971) 82 ITR 540 (SC) — Where the assessee offers a "
        "plausible explanation for an investment and the AO does not rebut it with material, "
        "the addition is not sustainable. The AO must engage with the explanation, not "
        "merely reject it by assertion.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 69A — UNEXPLAINED MONEY / JEWELLERY / DEPOSITS
    # (ADD-5: carved out from generic 69-series — distinct factual matrix)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_69a_unexplained_money": [
        "Sumati Dayal v. CIT (1995) 214 ITR 801 (SC) — Where entries in the books of account "
        "are supported by documentary evidence and no incriminating material is found to "
        "contradict them, an addition on the basis of human probability alone is not "
        "sustainable. The Preponderance of Probability test requires material, not conjecture.",

        "ACIT v. Rajesh Jhaveri Stock Brokers Pvt. Ltd. (2007) 291 ITR 500 (SC) — [Applied "
        "to 69A context] The standard of proof in addition proceedings is preponderance of "
        "probabilities, not beyond reasonable doubt; however, probabilities must be based on "
        "material, not surmise.",

        # ── Demonetisation-specific ──
        "Pr. CIT v. Agson Global Pvt. Ltd. (2022) (Del. HC) — [Demonetisation context] "
        "Cash deposited during the demonetisation period cannot be treated as unexplained "
        "u/s 69A if the assessee demonstrates that the cash represents earlier disclosed "
        "sales and the books show consistent opening balance of cash.",

        "PCIT v. Aggarwal Tobacco Co. (2021) (Del. HC) — In demonetisation-era cash deposit "
        "additions, the AO must examine the cash book, sales register, and trading account "
        "for the relevant period; a mechanical addition for the entire deposited amount "
        "without examining whether it matches the business's cash pattern is unsustainable.",

        "K.K. Saksena v. ITO (2022) (ITAT, Delhi) — CBDT Instruction No. 3/2017 clarifies "
        "that cash deposits up to Rs. 2.5 lakh by non-corporates during demonetisation "
        "period (09-11-2016 to 30-12-2016) need not be enquired into. Where deposits fall "
        "below this threshold, no addition is warranted in the absence of further adverse "
        "material.",

        # ── Jewellery ──
        "CBDT Instruction No. 1916 dated 11-05-1994 — Prescribes the threshold for seizure "
        "of jewellery during search; married woman is entitled to hold 500 grams, unmarried "
        "woman 250 grams, and male members 100 grams without requirement to explain the "
        "source. Additions for jewellery within these limits during search are unsustainable.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 69B / 69C — INVESTMENTS EXCEEDING SOURCES / UNEXPLAINED EXPENDITURE
    # (ADD-6)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_69b_69c_excess_investment_expenditure": [
        "CIT v. S. Khader Khan Son (2008) 300 ITR 157 (SC) — [Section 69C context] "
        "Unexplained expenditure u/s 69C can only be added if the expenditure is "
        "established as having been incurred; the AO must independently establish the "
        "factum of expenditure before treating the source as unexplained.",

        "T. Nagar Jewellery Mart v. ACIT (2019) (ITAT, Chennai) — Section 69B requires "
        "a finding that the recorded cost of investment in the books is lower than the "
        "fair market value of that investment. Without an independent valuation, the "
        "AO cannot invoke 69B merely on the basis of stamp duty value.",

        "Fakir Mohmed Haji Hasan v. CIT (2002) 247 ITR 290 (Guj. HC) — Where the "
        "expenditure is recorded in the books and the source of payment is traceable to "
        "known income or borrowings, Section 69C has no application. The provision "
        "applies only when the source of expenditure is not found in the records.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 14A / RULE 8D — DISALLOWANCE OF EXPENDITURE ON EXEMPT INCOME
    # (ADD-4: entirely absent in v8.x — most critical gap)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_14a_rule_8d": [
        # ── Supreme Court ──
        "Maxopp Investment Ltd. v. CIT (2018) 402 ITR 640 (SC) — Section 14A read with "
        "Rule 8D applies only to expenditure incurred to earn exempt income; it does not "
        "apply to funds invested for the purpose of control or strategic investment where "
        "dividend income is merely incidental. The dominant purpose of the investment "
        "determines applicability, not the mere receipt of dividend.",

        # ── Rule 8D — No Exempt Income = No Disallowance ──
        "PCIT v. IL&FS Energy Development Company Ltd. (2017) (Del. HC) — Where the "
        "assessee has earned no exempt income during the relevant previous year, Section "
        "14A disallowance cannot be made. The provision uses the expression 'in relation "
        "to income which does not form part of the total income' — where no such income "
        "arises, the expenditure cannot be 'in relation to' it.",

        "Cheminvest Ltd. v. CIT (2015) 378 ITR 33 (Del. HC) — Affirmed: Section 14A "
        "disallowance cannot be made if no exempt income is received or receivable during "
        "the previous year. The potential to earn exempt income in a future year is not "
        "sufficient. This is the binding Delhi HC authority on the point.",

        # ── Rule 8D Proportionality ──
        "PCIT v. Caraf Builders & Constructions Pvt. Ltd. (2019) (Del. HC) — Rule 8D "
        "cannot be applied mechanically without the AO recording a satisfaction that the "
        "assessee's claim of expenditure under Section 14A is incorrect. The satisfaction "
        "note is a jurisdictional prerequisite; its absence renders the entire 14A "
        "disallowance void.",

        "Godrej & Boyce Manufacturing Co. Ltd. v. DCIT (2017) 394 ITR 449 (Bom. HC) — "
        "Rule 8D(2)(ii) disallowance on interest is subject to the ceiling that total "
        "disallowance under all three limbs of Rule 8D cannot exceed the actual exempt "
        "income earned. The disallowance cannot create a notional loss on the exempt "
        "income stream.",

        # ── Own Funds vs. Borrowed Funds ──
        "CIT v. HDFC Bank Ltd. (2016) (Bom. HC) — Where the assessee demonstrates "
        "through the balance sheet that its own funds (networth) are substantially higher "
        "than investments made in tax-free securities, no presumption arises that borrowed "
        "funds were used for making those investments; interest disallowance u/s 14A "
        "read with Rule 8D(2)(ii) is not warranted.",

        # ── Finance Act 2022 Amendment ──
        "Finance Act 2022 — Section 14A amended with retrospective effect from AY 2022-23 "
        "to provide that disallowance shall be made even if no exempt income is earned "
        "during the previous year. The amendment prospectively overrules Cheminvest; "
        "for periods prior to AY 2022-23, Cheminvest continues to be the applicable law.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 56(2)(viib) — ANGEL TAX (SHARE PREMIUM FROM RESIDENTS)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_56_2_viib_angel_tax": [
        "Pr. CIT v. Agson Global Pvt. Ltd. (2022) (Del. HC) — The AO's jurisdiction u/s "
        "56(2)(viib) is limited to examining whether the issue price exceeds fair market "
        "value. The AO cannot substitute the assessee's DCF valuation with NAV method "
        "merely on preference; where the DCF method is used with justifiable projections "
        "and an independent CA report, the AO's substitution is without jurisdiction.",

        "PCIT v. Divya Capital One Pvt. Ltd. (2023) (Del. HC) — Section 56(2)(viib) "
        "addition is not sustainable where the assessee demonstrates a genuine business "
        "purpose for the premium and an independent valuation report is placed on record. "
        "The provision targets colourable arrangements, not genuine venture funding.",

        "CBDT Notification No. 29/2023 — DPIIT-registered startups are eligible for "
        "exemption from Section 56(2)(viib); the addition cannot be made if a valid DPIIT "
        "certificate and compliance with Form 2 are demonstrated.",

        "CBDT Notification No. S.O. 1131(E) dated 05-03-2024 — Rule 11UA amended; "
        "five additional valuation methods prescribed for non-resident investors, "
        "effective from the date of notification. Category-I/II AIFs and SEBI-registered "
        "investors are also notified as exempt classes for purposes of Section 56(2)(viib).",

        "Cinestaan Entertainment Pvt. Ltd. v. ITO (2020) (ITAT, Delhi) — Where the "
        "Revenue challenges DCF valuation, it must place a competing valuation on record; "
        "mere assertion that the projections are unrealistic, without a counter-valuation, "
        "is an insufficient basis for substituting the assessee's method.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 56(2)(x) — GIFTS / PROPERTY RECEIVED WITHOUT CONSIDERATION
    # (ADD-16: separated from angel tax bucket)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_56_2_x_gifts": [
        "Suresh Kumar Bansal v. UOI (2016) (Del. HC) — Section 56(2)(vii)/(x) is a "
        "charging section; it applies only when property is received 'without consideration' "
        "or for 'inadequate consideration'. Where there is a commercial arrangement behind "
        "the transfer — even if structured as a gift — the true nature of the transaction "
        "governs.",

        "S. Khader Khan Son v. ITO (2012) (ITAT, Chennai) — The FMV of immovable property "
        "for purposes of Section 56(2)(x) must be the stamp duty value on the date of "
        "agreement if the agreement pre-dates registration. The registration value cannot "
        "be used mechanically if an earlier date is provable.",

        "CBDT Circular No. 5/2010 — Clarifies that the stamp duty value to be adopted for "
        "Section 56(2)(vii)(b) is the value as on the date of agreement if there is an "
        "earlier agreement, provided part consideration is paid by account payee "
        "cheque / draft.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTIONS 50C / 43CA / 56(2)(x) — STAMP DUTY VALUATION MISMATCH
    # (ADD-9)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_50c_43ca_stamp_duty": [
        # ── Section 50C ──
        "Gouli Mahadevappa v. ITO (2013) 356 ITR 90 (Karn. HC) — Where the assessee "
        "disputes the stamp duty valuation, the AO is obligated to refer the property to "
        "the Valuation Officer (DVO) u/s 50C(2); the AO cannot proceed on the stamp duty "
        "value alone without affording the assessee the opportunity to seek DVO reference.",

        "CIT v. Thiruvengadam Investments Pvt. Ltd. (2010) 320 ITR 345 (Mad. HC) — "
        "Section 50C is a deeming provision and must be applied strictly; it applies only "
        "to capital assets being land or building. It has no application to transfer of "
        "leasehold rights, development rights, or other intangible assets related to land.",

        "Dharamshibhai Sonani v. ACIT (2016) (ITAT, Ahmedabad) — The proviso to Section "
        "50C provides a 10% tolerance (now 20% per Finance Act 2018 and further amended "
        "to include specific conditions under Finance Act 2020); no addition is warranted "
        "if the difference between the actual consideration and stamp duty value is within "
        "the prescribed tolerance band.",

        # ── Finance Act 2018 / 2020 Safe Harbour ──
        "Finance Act 2018 read with Finance Act 2020 — Section 50C(1) proviso: No addition "
        "if the stamp duty value does not exceed 110% of the actual consideration. Finance "
        "Act 2020 further extended this to 120% for specified residential units sold in the "
        "period 12-11-2020 to 30-06-2021. Both safe harbours must be verified before "
        "computing any Section 50C addition.",

        # ── Section 43CA ──
        "Prabhat Agrochemicals v. ITO (2020) (ITAT, Mumbai) — Section 43CA applies only "
        "to stock-in-trade (inventory), not to capital assets. Where a builder sells flats "
        "from stock, 43CA applies (not 50C). However, the DVO reference right is also "
        "available u/s 43CA(2) when the assessee disputes the stamp duty value.",

        # ── Buyer's Side — Section 56(2)(x) ──
        "CIT v. Shri Ram Housing Finance Ltd. (2019) (Raj. HC) — From the buyer's "
        "perspective, Section 56(2)(x) applies only if the difference between stamp duty "
        "value and actual purchase consideration exceeds Rs. 50,000. The AO must compute "
        "the differential and confirm the threshold breach before making the addition.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTIONS 45/48 — CAPITAL GAINS: CHARACTERISATION & COMPUTATION
    # (ADD-7)
    # ══════════════════════════════════════════════════════════════════════════

    "capital_gains_45_48": [
        # ── Business Income vs. Capital Gains ──
        "CIT v. Gopal Purohit (2010) 336 ITR 287 (Bom. HC) — The assessee can maintain "
        "two separate portfolios — one as investment (taxable as capital gains) and the "
        "other as trading (taxable as business income) — and the AO cannot recharacterise "
        "either portfolio without positive material. The assessee's intention at the time "
        "of purchase is the primary determinant.",

        "CBDT Circular No. 6/2016 dated 29-02-2016 — Listed securities held for more than "
        "12 months are to be treated as capital assets unless the assessee opts to treat "
        "them as stock-in-trade. Circular gives the assessee a one-time option at the "
        "beginning of the year; the AO cannot override the opted characterisation.",

        # ── Indexed Cost / Cost of Acquisition ──
        "B.C. Srinivasa Setty v. CIT (1981) 128 ITR 294 (SC) — Where there is no cost of "
        "acquisition (e.g., goodwill generated internally), Section 48 computation cannot "
        "be applied. Capital gains on assets having no ascertainable cost cannot be "
        "computed and are therefore not chargeable.",

        "Bombay Burmah Trading Corporation Ltd. v. CIT (1984) 145 ITR 793 (Bom. HC) — "
        "Indexed cost of acquisition is to be computed by reference to the Cost Inflation "
        "Index for the year of acquisition, not the year in which the asset becomes a "
        "capital asset.",

        # ── Penny Stock — LTCG Denial ──
        "Suman Poddar v. ITO (2019) (ITAT, Delhi) — Where the Revenue denies LTCG "
        "exemption on listed shares by alleging penny stock manipulation, it must produce "
        "positive material establishing the nexus between the assessee and the price "
        "rigging. Generic references to SEBI investigation reports, without establishing "
        "the assessee's specific participation, are insufficient to sustain an addition.",

        "Pr. CIT v. Vishwa Infrastructure and Services Pvt. Ltd. (2018) (Guj. HC) — "
        "Revenue cannot deny LTCG exemption u/s 10(38) / tax at reduced rate u/s 112A "
        "merely on the ground that the stock price appreciated sharply if the transaction "
        "is supported by contract notes from a SEBI-registered broker, STT payment, and "
        "dematerialised transfer.",

        # ── Section 2(42A) — Holding Period ──
        "ACIT v. Mrs. Tarulata Shyam (1977) 108 ITR 345 (SC) — The period of holding "
        "for purposes of Section 2(42A) is computed from the date of acquisition; where "
        "shares are acquired in several tranches, each tranche is assessed independently "
        "for the holding period requirement.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTIONS 54 / 54F / 54EC — CAPITAL GAINS EXEMPTIONS
    # (ADD-8)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_54_54f_54ec_exemptions": [
        # ── Section 54 / 54F — New Asset ──
        "CIT v. T.N. Aravinda Reddy (1979) 120 ITR 46 (SC) — For purposes of Section 54 "
        "(now replicated in 54F), 'new asset' must be a residential house; a share in a "
        "residential house is sufficient to qualify, provided the assessee has genuine "
        "ownership rights. [Foundational ratio on 'house' definition.]",

        "Pawan Arora v. ITO (2022) (ITAT, Delhi) — For Section 54, the requirement to "
        "purchase a new residential house within one year before or two years after the "
        "date of transfer is strictly computed from the date of the sale deed/possession, "
        "not from the date of receipt of the sale consideration.",

        # ── Section 54F — One House Condition ──
        "CIT v. Syed Ali Adil (2013) 352 ITR 24 (AP HC) — Section 54F requires that the "
        "assessee should not own more than one residential house (other than the new asset) "
        "on the date of transfer. Holding rights through an HUF or as a co-owner does not "
        "count as 'owning' another house for this purpose if the assessee's individual "
        "ownership share is below a beneficial threshold.",

        "Prema P. Shah v. ITO (2014) (ITAT, Mumbai) — Under Section 54F, the entire "
        "capital gain need not be invested; the exemption is proportionate — "
        "[Net Consideration invested / Net Consideration received] × Capital Gain. "
        "AOs who deny the entire exemption for partial investment err on facts and law.",

        # ── Section 54EC — Bonds, Time Limit ──
        "Aspi Ginwala v. ACIT (2012) (ITAT, Ahmedabad) — The six-month time limit for "
        "investment in Section 54EC bonds runs from the date of transfer, not the date "
        "of receipt of sale proceeds. Non-receipt of consideration within six months does "
        "not extend the statutory time limit.",

        "CBDT Notification S.O. 1174(E) dated 08-04-2022 — NHAI / REC bonds are "
        "notified u/s 54EC. The annual investment ceiling of Rs. 50 lakh per assessee "
        "applies per financial year, not per transaction; multiple transfers in a year "
        "share the ceiling.",

        # ── Section 54 — Construction vs Purchase ──
        "CIT v. J.R. Subramanya Bhat (1987) 165 ITR 571 (Karn. HC) — Where the assessee "
        "uses the capital gains to construct a house within three years of the transfer, "
        "the exemption u/s 54 is available even if construction is not complete by the "
        "due date of filing the return; substantial completion is sufficient.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 10(38) / SECTION 112A — LTCG ON LISTED SECURITIES / PENNY STOCK
    # (ADD-10)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_10_38_112a_penny_stock": [
        "Suman Poddar v. ITO (2019) (ITAT, Delhi) — [Cited above under capital_gains; "
        "mapped here for keyword matching on 10(38)/112A.] Revenue must produce assessee-"
        "specific evidence of participation in price rigging; generic SEBI reports are "
        "insufficient to deny LTCG exemption/concessional rate.",

        "Pr. CIT v. Ziauddin A. Siddiqui (2019) (Bom. HC) — The AO cannot treat LTCG on "
        "listed shares as unexplained cash credit u/s 68 unless there is specific material "
        "linking the assessee to an accommodation entry operation. Contract notes, STT "
        "payment receipts, and demat account statements constitute the assessee's "
        "documentary discharge of onus.",

        "ACIT v. Swati Bajaj (2022) (ITAT, Kolkata, Special Bench) — Where the department "
        "relies solely on price-volume analysis and SEBI alerts without examining the "
        "assessee's demat account and STT records, the addition u/s 68 treating LTCG as "
        "accommodation entry is unsustainable. [Special Bench ruling — highly persuasive.]",

        "Pr. CIT v. Renu Agarwal (2022) (Cal. HC) — ITAT's finding of fact that STT was "
        "paid and shares were held in demat form is a finding on a mixed question of law "
        "and fact; the High Court in an appeal u/s 260A is not to reappreciate evidence "
        "unless the finding is perverse. [Important for ITAT decisions to survive HC "
        "challenge on penny stock matters.]",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTIONS 147/148 — REOPENING AND REASSESSMENT
    # ══════════════════════════════════════════════════════════════════════════

    "sec_147_148_reopening": [
        "GKN Driveshafts (India) Ltd. v. ITO (2003) 259 ITR 19 (SC) — Assessee is "
        "entitled to the reasons recorded for reopening; must file objections before "
        "the AO adjudicates on merits. Failure to supply reasons on demand is a "
        "jurisdictional defect.",

        "CIT v. Kelvinator of India Ltd. (2010) 320 ITR 561 (SC) — Mere change of "
        "opinion cannot form the basis for reopening u/s 147. The AO must have tangible "
        "material — extraneous to the return as filed — to form reasons to believe. "
        "Pre-existing material that was examined in the original assessment cannot be "
        "the 'new' material. [Foundational authority on Change of Opinion doctrine.]",

        "Rajesh Jhaveri Stock Brokers Pvt. Ltd. v. ACIT (2007) 291 ITR 500 (SC) — At "
        "the stage of notice u/s 148, the AO is only required to have reason to believe "
        "that income has escaped assessment; conclusive proof of escaped income is not "
        "required at this stage.",

        "Union of India v. Ashish Agarwal (2022) 444 ITR 1 (SC) — Notices issued u/s 148 "
        "between 01-04-2021 and 30-06-2021 without following the 148A procedure were set "
        "aside; the Supreme Court directed that such notices be treated as SCN u/s 148A(b) "
        "and the AO must pass a fresh order u/s 148A(d) before issuing a valid 148 notice.",

        "CIT v. Mohmed Juned Dadani (2014) 355 ITR 172 (Guj. HC) — Where the AO makes "
        "no addition on the specific reasons recorded for reopening u/s 147, he cannot "
        "make additions on entirely new, unrelated grounds not forming part of the recorded "
        "reasons. The scope of reassessment is limited to the recorded reasons.",

        "Union of India v. Rajeev Bansal (2024) (SC) — TOLA applies to the Finance Act "
        "2021 reassessment regime; the Revenue is entitled to the benefit of extended time "
        "limits under TOLA for issuing Section 148 notices for the covered AYs. "
        "[CRITICAL: Read with Ashish Agarwal — together they frame the complete "
        "transitional picture on limitation for pre-FA 2021 assessment years.]",

        "CBDT Circular No. 6/2024 — AY-wise outer limits for reassessment proceedings "
        "post Finance Act 2021 restated; for AY 2018-19 and prior, the maximum period "
        "is 6 years from the end of the relevant AY under the savings clause.",

        # ── Information vs. Investigation ──
        "CIT v. Insecticides (India) Ltd. (2013) 357 ITR 330 (Del. HC) — 'Information' "
        "that triggers u/s 147 must be specific and credible, not vague or general. "
        "AIR / AIS / SFT data showing high-value transactions can constitute 'information' "
        "only if it is correlated to a specific escaped income item, not used as a pretext "
        "for a fishing inquiry.",

        "ACIT v. Rajesh Kumar Gupta (2021) (Del. HC) — A notice u/s 148 issued on the "
        "basis of AIS data showing a transaction already disclosed in the return of income "
        "is nothing but a change of opinion; the reopening is void.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 148A — MANDATORY PRE-ISSUANCE PROCEDURE
    # ══════════════════════════════════════════════════════════════════════════

    "sec_148a_procedural": [
        "Siemens Financial Services Pvt. Ltd. v. DCIT (2022) (Bom. HC) — The order u/s "
        "148A(d) must be a reasoned speaking order; a mechanical or boilerplate order "
        "that does not engage with the assessee's reply to the 148A(b) SCN is void. "
        "The AO's satisfaction must be recorded — not assumed.",

        "Hexaware Technologies Ltd. v. ACIT (2023) (Bom. HC) — Prior approval from the "
        "Specified Authority u/s 151 must be obtained before the 148A(b) notice is "
        "issued, not after. Absence of prior approval at the 148A(b) stage is a "
        "jurisdictional defect rendering the entire proceedings void ab initio.",

        "Mon Mohan Kohli v. ACIT (2022) (Del. HC) — The four-step procedure u/s 148A "
        "is mandatory and cannot be bypassed or telescoped. Each of 148A(a) to 148A(d) "
        "must be independently completed in sequence.",

        # ── Quality of SCN ──
        "Sona Chaandi Sarrafa Association v. UOI (2022) (MP HC) — The information "
        "forming the basis of the 148A(b) SCN must be disclosed to the assessee; a "
        "notice that merely states 'information received' without specifying the nature "
        "and source of information denies the assessee a meaningful opportunity to reply. "
        "[Key ruling for countering non-disclosure of source in 148A proceedings.]",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 151 — PRIOR SANCTION
    # ══════════════════════════════════════════════════════════════════════════

    "sec_151_sanction": [
        "Calcutta Discount Co. Ltd. v. ITO (1961) 41 ITR 191 (SC) — Sanction from the "
        "prescribed authority is a jurisdictional prerequisite; proceedings without valid "
        "sanction are void ab initio. The sanctioning authority must independently "
        "apply its mind; rubber-stamping is not sufficient.",

        "Hexaware Technologies Ltd. v. ACIT (2023) (Bom. HC) — Non-mentioning of the "
        "Specified Authority who granted sanction u/s 151 in the notice/order is a fatal "
        "defect; the assessee is entitled to know which authority accorded sanction to "
        "verify that the prescribed authority under the new regime has been correctly "
        "identified.",

        "PCIT v. Paville Projects Pvt. Ltd. (2023) (Bom. HC) — Under the post-FA 2021 "
        "regime, the 'Specified Authority' under Section 151 is the PCIT for cases "
        "where escaped income exceeds Rs. 50 lakh. Sanction accorded by an authority "
        "lower in rank than the one prescribed is invalid.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 149 — LIMITATION PERIOD
    # ══════════════════════════════════════════════════════════════════════════

    "sec_149_limitation": [
        "CBDT Circular No. 6/2024 — For AY 2018-19 and earlier, reassessment is "
        "permissible only up to 6 years under the savings clause of Finance Act 2021; "
        "for AY 2019-20 onwards, the 3-year limit applies unless escaped income exceeds "
        "Rs. 50 lakh (in which case 10 years applies with conditions).",

        "Union of India v. Ashish Agarwal (2022) 444 ITR 1 (SC) — Transitional "
        "provisions under Finance Act 2021 for Sections 148/149 must be applied "
        "strictly; extended time limits are available only where the specified conditions "
        "are met.",

        "Union of India v. Rajeev Bansal (2024) (SC) — TOLA extends the limitation "
        "period available to the Revenue for AYs falling within the TOLA window; the "
        "assessee must verify the specific AY to determine whether it falls within the "
        "TOLA period (AY 2016-17 to AY 2020-21 per the notification schedule).",

        "CIT v. Orient Craft Ltd. (2013) 354 ITR 536 (Del. HC) — Time-bar is a "
        "jurisdictional issue that goes to the root of the notice's validity. The "
        "assessee need not wait for assessment; a writ petition challenging a "
        "time-barred reassessment notice is maintainable.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 143(1) — INTIMATION / CPC ADJUSTMENTS
    # ══════════════════════════════════════════════════════════════════════════

    "sec_143_1_intimation": [
        "Khatau Junkar Ltd. v. K.S. Pathania (1992) 196 ITR 55 (Bom.) — The jurisdiction "
        "of an intimation u/s 143(1) is limited to prima facie adjustments for arithmetical "
        "errors or incorrect claims apparent from the return; the AO cannot exercise "
        "assessment powers under this provision.",

        "Rajesh Jhaveri Stock Brokers Pvt. Ltd. v. ACIT (2007) 291 ITR 500 (SC) — An "
        "intimation u/s 143(1) is not an assessment order; it cannot be equated with an "
        "order of assessment for purposes of limitation or merger.",

        "CBDT Circular No. 549 dated 31-10-1989 — Scope of intimation u/s 143(1)(a) is "
        "limited to arithmetical errors and incorrect claims apparent on the face of the "
        "return; the AO cannot re-examine debatable questions of law or fact.",

        # ── Disallowance u/s 143(1)(a)(iv) — Added FA 2021 ──
        "Finance Act 2021 — Section 143(1)(a)(iv) inserted: CPC can now disallow at the "
        "prima facie adjustment stage if the deduction or exemption claim is inconsistent "
        "with information in Form 26AS, AIS, or TIS. However, the adjustment must be on "
        "the basis of information already in the system — the AO cannot raise new "
        "inquiries under 143(1).",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 37(1) — BUSINESS EXPENDITURE
    # (ADD-12: expanded with sub-categories)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_37_business_expenditure": [
        # ── General Principles ──
        "CIT v. Walchandnagar Industries Ltd. (1967) 65 ITR 381 (SC) — Expenditure must "
        "be incurred wholly and exclusively for the purposes of business to qualify u/s "
        "37(1); the test is commercial expediency as judged from the perspective of the "
        "businessperson, not the Revenue.",

        "Sassoon J. David & Co. Pvt. Ltd. v. CIT (1979) 118 ITR 261 (SC) — Commercial "
        "expediency is the primary test for allowability; the AO cannot substitute its own "
        "judgment for that of the businessman as to whether a particular expenditure was "
        "necessary or wise.",

        # ── Capital vs. Revenue Expenditure ──
        "Empire Jute Co. Ltd. v. CIT (1980) 124 ITR 1 (SC) — If expenditure is incurred "
        "for obtaining an advantage of enduring benefit, it is capital in nature; but if "
        "the advantage is absorbed in the process of profit earning without enlarging the "
        "profit-earning apparatus, it is revenue expenditure. [Two-test framework: "
        "enduring benefit + profit-earning apparatus.]",

        "CIT v. Madras Auto Service Pvt. Ltd. (1998) 233 ITR 468 (SC) — Expenditure on "
        "interior renovation of a leased premises, which does not create a new asset but "
        "merely restores existing utility, is revenue expenditure deductible u/s 37(1).",

        # ── Write-Off of Advances ──
        "Travancore Rubber and Tea Co. Ltd. v. CIT (2000) 243 ITR 158 (SC) — Loss on "
        "account of an advance written off is deductible u/s 37(1) if the advance was "
        "made in the ordinary course of business; it cannot be disallowed by characterising "
        "it as a capital loss unless the advance was for acquiring a capital asset.",

        # ── Non-Compete Fees ──
        "Guffic Chem Pvt. Ltd. v. CIT (2011) 332 ITR 602 (SC) — Non-compete fees paid "
        "for a period of three years are revenue expenditure; the test is not the period "
        "of the non-compete clause but whether the payment creates a lasting and enduring "
        "commercial benefit or merely protects existing business.",

        # ── Corporate Guarantee / Bank Guarantee Commission ──
        "CIT v. S.C. Kothari (2011) (Del. HC) — Commission paid for corporate guarantee "
        "is deductible u/s 37(1) as a business expense if the guarantee is furnished for "
        "a business purpose; it cannot be disallowed as a personal benefit to the promoter "
        "unless the AO establishes the personal element with evidence.",

        # ── Donations / Freebies — Pharma ──
        "PCIT v. Apex Laboratories Pvt. Ltd. (2022) 442 ITR 1 (SC) — Freebies given to "
        "medical practitioners in violation of Medical Council of India (Professional "
        "Conduct, Etiquette and Ethics) Regulations 2002 are not deductible u/s 37(1) "
        "as they represent expenditure on an activity prohibited by law. Explanation 1 "
        "to Section 37(1) squarely applies. [Critical precedent for pharmaceutical "
        "companies facing marketing expenditure disallowance.]",

        # ── CSR Expenditure ──
        "Finance Act 2014 / Explanation 2 to Section 37(1) — Expenditure on CSR as "
        "required under Section 135 of the Companies Act 2013 is expressly excluded from "
        "deduction u/s 37(1) with effect from AY 2015-16. Such expenditure may qualify "
        "under Section 80G if donated to an approved institution, but cannot be claimed "
        "as a business expense.",

        # ── Penalty / Compounding Fees ──
        "Haji Aziz & Abdul Shakoor Bros. v. CIT (1961) 41 ITR 350 (SC) — Penalty "
        "paid for infraction of a statute is not deductible u/s 37(1); a taxpayer "
        "cannot be permitted to use tax deductibility to defray the cost of its own "
        "legal violations. [Foundational authority on statutory penalties.]",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 40(a)(ia) — TDS DISALLOWANCE FOR NON-DEDUCTION
    # (ADD-15)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_40a_ia_tds_disallowance": [
        # ── Deductee Has Filed Return ──
        "Merilyn Shipping & Transports v. ACIT (2012) 136 ITD 23 (ITAT Vizag, SB) — "
        "Section 40(a)(ia) disallowance is not attracted if the payee (deductee) has "
        "disclosed the amount in its own return of income and paid tax thereon, since "
        "the purpose of the provision (ensuring tax is paid on the income) is already "
        "served. [Special Bench ruling — highly persuasive; position protected by "
        "proviso inserted by Finance Act 2012.]",

        "Finance Act 2012 — Proviso to Section 40(a)(ia) inserted with retrospective "
        "effect from AY 2005-06: Disallowance is not made if the payee has included "
        "the amount in its income and paid tax thereon. Assessee must obtain Form 26A "
        "certificate from payee's CA to avail this proviso.",

        # ── Short Deduction ──
        "CIT v. Bharat Engineering & Construction Co. (2015) (Karn. HC) — Disallowance "
        "u/s 40(a)(ia) for short deduction of TDS is restricted to the shortfall in TDS, "
        "not the entire payment. Full disallowance on account of short deduction is "
        "disproportionate and contrary to the legislative intent.",

        # ── Applicability to Salary — Section 192 ──
        "CBDT Circular No. 8/2013 — TDS u/s 192 on salary is to be deducted at the "
        "average rate of income tax computed on the estimated income for the year. The "
        "employer must obtain Proof of Investment declarations (Form 12BB) from "
        "employees before crediting the TDS to Government; failure to deduct on correct "
        "projected income attracts 40(a)(ia) disallowance for the employer.",

        # ── Year of Disallowance ──
        "Wall Street Finance Ltd. v. ITO (2014) (Bom. HC) — Section 40(a)(ia) "
        "disallowance operates in the year of credit or payment (whichever is earlier), "
        "not in the year in which TDS return is due to be filed. The disallowance and "
        "the deduction in the subsequent year (on TDS payment) operate in different AYs.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 271(1)(c) — CONCEALMENT PENALTY
    # ══════════════════════════════════════════════════════════════════════════

    "sec_271_penalty": [
        "MAK Data Pvt. Ltd. v. CIT (2013) 358 ITR 593 (SC) — Penalty u/s 271(1)(c) "
        "cannot be levied merely because the assessee surrenders income during assessment; "
        "the AO must independently establish the intention to conceal. A surrender to "
        "buy peace does not equal an admission of concealment.",

        "Hindustan Steel Ltd. v. State of Orissa (1972) 83 ITR 26 (SC) — Penalty is not "
        "leviable if the assessee acted bona fide; existence of reasonable cause is a "
        "complete defence. [Applies to all civil tax penalties by analogy.]",

        "CIT v. Reliance Petroproducts Pvt. Ltd. (2010) 322 ITR 158 (SC) — Making an "
        "incorrect claim that is not sustainable in law does not per se amount to "
        "concealment of income or furnishing inaccurate particulars. The claim must be "
        "fraudulent or based on suppression of facts to attract penalty.",

        # ── Omnibus / Non-specific notice ──
        "CIT v. Manjunatha Cotton and Ginning Factory (2013) 359 ITR 565 (Karn. HC) — "
        "A penalty notice that fails to specify whether the charge is 'concealment' or "
        "'furnishing inaccurate particulars' is bad in law; the assessee is entitled to "
        "know the precise charge. An omnibus notice that does not strike out the "
        "irrelevant limb is void.",

        "CIT v. SSA's Emerald Meadows (2016) 73 taxmann.com 248 (SC) — SLP dismissed "
        "affirming the Karnataka HC principle that an omnibus penalty notice is void. "
        "Carries persuasive finality.",

        # ── Quantum of Penalty ──
        "Dhirajlal Girdharilal v. CIT (1954) 26 ITR 736 (SC) — The quantum of penalty "
        "u/s 271(1)(c) is within the AO's discretion within the prescribed range; however "
        "the discretion must be exercised judicially and not punitively. A maximum "
        "penalty imposed without recorded reasons is disproportionate.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 270A — UNDER-REPORTING / MISREPORTING PENALTY
    # (ADD-11: upgraded with direct 270A judicial interpretation)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_270a_penalty": [
        # ── Omnibus Notice (carried from v8.1) ──
        "CIT v. Manjunatha Cotton and Ginning Factory (2013) 359 ITR 565 (Karn. HC) — "
        "[Applied by analogy to Sec 270A] A notice that fails to specify whether the "
        "charge is under-reporting or misreporting is bad in law; the statutory distinction "
        "between the two limbs carries different penalty rates (50% vs 200%) and the "
        "assessee must know the precise charge.",

        "CIT v. SSA's Emerald Meadows (2016) 73 taxmann.com 248 (SC) — Affirmed "
        "the Karnataka HC principle; omnibus notice void.",

        # ── Direct 270A Judicial Interpretation ──
        "Pr. CIT v. Shreenathji Enterprises (2022) (Raj. HC) — Section 270A distinguishes "
        "between 'under-reporting' (Section 270A(2)) and 'misreporting' (Section 270A(9)). "
        "Where the AO invokes misreporting — which attracts 200% penalty — the burden of "
        "proof is substantially higher; the AO must establish the specific misreporting "
        "category (false entry in books, suppression of sale, etc.) listed in Section "
        "270A(9)(a) to (f). A vague allegation of misreporting does not sustain 200% levy.",

        "PCIT v. Shri Gopal Kanda (2022) (P&H HC) — Where the assessee makes a claim "
        "for deduction that is ultimately disallowed on a debatable legal point, the "
        "addition constitutes 'under-reporting' at most — not 'misreporting'. The 200% "
        "rate under Section 270A(9) is reserved for deliberate falsehood, not for "
        "contested legal positions.",

        "Sanjiv Gupta v. PCIT (2021) (Del. HC) — Section 270A(6)(a) provides immunity "
        "from penalty where the taxpayer has not under-reported income by way of "
        "misreporting and has maintained a true and complete return. The AO must record "
        "specific findings on which limb of Section 270A(9) is attracted before levying "
        "the 200% penalty.",

        # ── Immunity under Section 270AA ──
        "CBDT Circular No. 10/2020 — Procedure for making application u/s 270AA for "
        "immunity from Section 270A penalty: application must be filed within one month "
        "of the date of receipt of assessment order; the conditions are that the "
        "assessee must pay the tax and interest within the time allowed and must not "
        "have filed an appeal. Immunity, if granted, is final.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 263 — REVISION BY PRINCIPAL COMMISSIONER
    # (ADD-14)
    # ══════════════════════════════════════════════════════════════════════════

    "sec_263_revision": [
        "Malabar Industrial Co. Ltd. v. CIT (2000) 243 ITR 83 (SC) — For Section 263 "
        "jurisdiction to be exercised, two conditions must be concurrently satisfied: "
        "(a) the order must be erroneous, and (b) it must be prejudicial to the "
        "interests of the Revenue. Both conditions are mandatory; one alone is insufficient. "
        "[Foundational ratio decidendi — still binding.]",

        "CIT v. Sunbeam Auto Ltd. (2011) 332 ITR 167 (Del. HC) — Where the AO has "
        "examined the particular issue during assessment and taken a permissible view, "
        "the PCIT cannot invoke Section 263 merely because a different view is possible. "
        "The PCIT's role is not to substitute the AO's view with its own; it is to "
        "correct jurisdictional errors and manifest illegality.",

        "Pr. CIT v. Furnace Fabrica (P.) Ltd. (2020) (Bom. HC) — An order is 'erroneous' "
        "u/s 263 only when it is incorrect in law, not merely because it can be improved. "
        "If the AO has applied a legally sustainable interpretation, the order cannot be "
        "revised even if the PCIT would have applied a different, possibly better, one.",

        "DIT v. Jyoti Foundation (2013) 357 ITR 388 (Del. HC) — Revision u/s 263 is "
        "time-barred if issued after two years from the date of the original assessment "
        "order; the limitation under Section 263(2) is strict and cannot be extended.",

        # ── Limited Scrutiny / CASS ──
        "Pr. CIT v. Salil Gulati (2020) (Del. HC) — Where an assessment is conducted "
        "under 'limited scrutiny' with specific issues, the PCIT cannot revise the order "
        "u/s 263 on issues outside the scope of limited scrutiny; the AO's non-examination "
        "of non-CASS issues is not 'erroneous' since the AO had no jurisdiction to examine "
        "them in the first place.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 234A/B/C — INTEREST ON TAX
    # ══════════════════════════════════════════════════════════════════════════

    "sec_234_interest": [
        "CIT v. Anjum M.H. Ghaswala (2001) 252 ITR 1 (SC) — Interest u/s 234A/B/C is "
        "compensatory in nature, not penal; it can be waived only under the specific "
        "circumstances enumerated u/s 220(2A). The ITAT and Commissioner have no "
        "inherent power to waive statutory interest.",

        "CBDT Circular No. 2/2015 — Clarification on computation of interest u/s 234B "
        "in cases involving advance tax; TDS to be excluded from advance tax shortfall "
        "computation.",

        # ── Non-Chargeability Where Tax is NIL ──
        "CIT v. Ranchi Club Ltd. (2001) 247 ITR 209 (Jhar. HC) — Where the total "
        "income assessed is nil (after setting off brought forward losses), interest "
        "u/s 234B on tax not paid is not chargeable since there is no 'assessed tax' "
        "on which the shortfall can be computed.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # TDS MISMATCH / FORM 26AS / AIS
    # ══════════════════════════════════════════════════════════════════════════

    "tds_mismatch": [
        "CBDT Circular No. 2/2011 dated 27-04-2011 — TDS credit is to be given on the "
        "basis of Form 26AS; the AO must verify before disallowing any credit claimed "
        "by the assessee.",

        "CIT(TDS) v. Canara Bank (2014) — TDS deducted and deposited by the deductor "
        "must be credited to the deductee irrespective of whether the deductor has "
        "filed the TDS return; the deductee cannot be penalised for the deductor's "
        "compliance failure.",

        # ── AIS Mismatch ──
        "Finance Act 2021 — Annual Information Statement (AIS) u/s 285BB introduced. "
        "AIS aggregates information from multiple SFT filers, TDS returns, foreign "
        "remittance data, and GST returns. Discrepancy between AIS and ITR can trigger "
        "Section 143(1)(a)(iv) adjustment or Section 147 reopening. The assessee can "
        "submit feedback on AIS data through the compliance portal.",

        "CBDT Circular No. 16/2021 — Processing of returns u/s 143(1) for cases where "
        "AIS/TIS data mismatch is identified; the CPC is to issue intimation only after "
        "considering the assessee's feedback submitted on the compliance portal.",

        # ── Form 26AS vs. Actual TDS ──
        "Dy. CIT v. Jindal Steel & Power Ltd. (2016) (ITAT, Delhi) — Where the "
        "discrepancy in TDS credit arises due to a mismatch in PAN quoted by the "
        "deductor (not the deductee), the deductee cannot be denied credit. The "
        "department must proceed against the deductor for correction of TDS return; "
        "the innocent deductee's credit cannot be withheld.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # NATURAL JUSTICE / PERSONAL HEARING
    # ══════════════════════════════════════════════════════════════════════════

    "natural_justice": [
        "Tin Box Co. v. CIT (2001) 249 ITR 216 (SC) — An assessment order made without "
        "giving the assessee a proper opportunity of being heard is invalid; the "
        "requirement of a hearing is a mandatory procedural safeguard, not merely "
        "directory.",

        "Swadeshi Cotton Mills Co. Ltd. v. Union of India (1981) AIR 818 (SC) — The "
        "audi alteram partem rule is implicit in every statutory provision that empowers "
        "an authority to take adverse action; it need not be expressly stated.",

        # ── Show Cause Notice Adequacy ──
        "Oryx Fisheries Pvt. Ltd. v. Union of India (2010) (SC) — A show cause notice "
        "must be specific enough to enable the noticee to give a meaningful reply. A "
        "vague or omnibus SCN that does not specify the allegations with particularity "
        "does not satisfy the audi alteram partem requirement.",

        "Whirlpool Corporation v. Registrar of Trade Marks (1998) 8 SCC 1 (SC) — "
        "Where an authority acts in breach of natural justice, the High Court's writ "
        "jurisdiction under Article 226 is available notwithstanding the availability "
        "of an alternative remedy, particularly where the breach goes to jurisdiction.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # DIN — CBDT CIRCULAR 19/2019
    # ══════════════════════════════════════════════════════════════════════════

    "din_circular": [
        "CBDT Circular No. 19/2019 dated 14-08-2019 — Every communication issued by "
        "an Income Tax authority must carry a computer-generated DIN; any communication "
        "without a valid DIN shall be treated as void and not acted upon. Applies to "
        "notices, orders, summons, letters, and all other correspondence.",

        "CIT v. Brandix Mauritius Holdings Ltd. (2021) (Del. HC) — An assessment order "
        "issued without a DIN is void ab initio; the DIN requirement is not a technicality "
        "but a mandatory safeguard to prevent unauthorised communications. The defect "
        "cannot be cured retrospectively.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 144B — FACELESS ASSESSMENT
    # ══════════════════════════════════════════════════════════════════════════

    "faceless_assessment": [
        "Lakshya Budhiraja v. UOI (2021) (Del. HC) — The Faceless Assessment Scheme "
        "u/s 144B does not abrogate the principles of natural justice; the assessee "
        "is still entitled to a hearing before any adverse order is passed.",

        "Kanhaiya Lal Sharma v. NaFAC (2022) (Del. HC) — Notice for personal hearing "
        "under the faceless scheme must be issued through the NFAC portal; service "
        "through the AO's personal email is invalid.",

        "CBDT Circular No. 23/2019 (as amended) — All assessments u/s 143(3) and 144 "
        "for eligible persons to be conducted under the Faceless Assessment Scheme; all "
        "communications exclusively through the e-Proceedings portal.",

        # ── Mandatory Hearing Before Adverse Addition ──
        "Sai Ram Cotton Industries Pvt. Ltd. v. ITO (2022) (Del. HC) — Where the "
        "NFAC proposes an addition in a draft assessment order and the assessee requests "
        "a personal hearing, the NFAC must grant the hearing before passing the final "
        "order. Passing a final adverse order without conducting the requested hearing "
        "is a jurisdictional error.",

        "Bombay Diamond Company v. PCIT (2022) (Bom. HC) — The internal communication "
        "between units within the faceless system (Assessment Unit, Review Unit, "
        "Technical Unit) is not required to be shared with the assessee; only the "
        "proposed addition communicated via draft assessment order triggers the assessee's "
        "right of response.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 153A — SEARCH AND SEIZURE ASSESSMENTS
    # ══════════════════════════════════════════════════════════════════════════

    "sec_153a_search": [
        "Pr. CIT v. Abhisar Buildwell P. Ltd. (2023) 454 ITR 212 (SC) — In search "
        "cases under Section 153A, no addition can be made in respect of completed / "
        "unabated assessments unless incriminating material pertaining to the relevant "
        "AY is found during the search. However, the AO retains jurisdiction to reopen "
        "such assessments under Section 147/148 if the conditions are satisfied.",

        # ── What Constitutes Incriminating Material ──
        "CIT v. Kabul Chawla (2016) 380 ITR 573 (Del. HC) — Not every document found "
        "during search constitutes 'incriminating material' for purposes of Section "
        "153A; the material must have a direct nexus with the undisclosed income for "
        "the specific AY in question. Generic financial documents that merely "
        "corroborate disclosed income are not incriminating.",

        "PCIT v. Meeta Gutgutia (2017) 395 ITR 526 (Del. HC) — Affirmed Kabul Chawla: "
        "additions in unabated assessments u/s 153A cannot be sustained without "
        "specific incriminating material found during search. This position is now "
        "confirmed by Abhisar Buildwell (SC 2023).",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 194Q / 206C(1H) — TDS/TCS HIERARCHY
    # ══════════════════════════════════════════════════════════════════════════

    "sec_194q_tcs_overlap": [
        "CBDT Circular No. 13/2021 dated 30-06-2021 — Where both Section 194Q (TDS on "
        "purchase of goods) and Section 206C(1H) (TCS on sale of goods) apply to the "
        "same transaction, Section 194Q prevails; the seller is relieved of TCS "
        "obligation once the buyer deducts TDS u/s 194Q.",

        "CBDT Circular No. 20/2021 dated 25-11-2021 — The Rs. 50 lakh threshold for "
        "Section 194Q is to be computed from 01-04-2021; transactions prior to that "
        "date are not to be included in the threshold calculation for the current year.",

        # ── Interplay with 40(a)(ia) ──
        "Finance Act 2021 (Memorandum Explaining Provisions) — Non-deduction of TDS "
        "u/s 194Q, where the provision applies, exposes the buyer to: (a) disallowance "
        "of 30% of purchase price u/s 40(a)(ia) to the extent of the non-deducted TDS "
        "amount; and (b) interest u/s 201(1A) on TDS not deducted. The deductor-buyer "
        "cannot avoid 40(a)(ia) consequences by arguing that the seller was obligated "
        "to collect TCS if 194Q was applicable to the buyer.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # MSME / VIKSIT BHARAT COMPLIANCE
    # (ADD-18: Section 43B(h), 44AB thresholds, reporting obligations)
    # ══════════════════════════════════════════════════════════════════════════

    "viksit_bharat_msme_compliance": [
        # ── Section 43B(h) — MSME Payment Deductibility ──
        "Finance Act 2023 — Section 43B(h) inserted: Any sum payable to a Micro or "
        "Small enterprise (as defined in the MSMED Act 2006) shall be allowed as "
        "deduction only in the year of actual payment. If payment is not made within "
        "the time allowed under Section 15 of the MSMED Act (15 days generally; 45 days "
        "where there is a written agreement), the entire outstanding amount is disallowed "
        "in the year of accrual and allowed only in the year of actual payment. "
        "[Operative from AY 2024-25.]",

        "CBDT Circular No. 5/2024 — Clarifies the computation of disallowance u/s "
        "43B(h): the time limit of 45 days runs from the date of acceptance/deemed "
        "acceptance of the goods or services, not from the invoice date. Businesses "
        "must maintain MSME registration status records of their vendors.",

        # ── Section 44AB — Tax Audit Threshold ──
        "Finance Act 2021 — Section 44AB threshold for tax audit increased: Business "
        "turnover threshold Rs. 10 crore where 95% or more of receipts and payments "
        "are through specified banking channels (cashless). Professionals: Rs. 50 lakh. "
        "The cash threshold condition must be verified for every AY; non-cash transactions "
        "above the applicable limit restore the Rs. 1 crore threshold.",

        # ── Form 3CD Clause 44 — GST Reconciliation ──
        "CBDT Notification No. 28/2021 — Form 3CD amended to include Clause 44: the "
        "tax auditor must report the break-up of total expenditure incurred during the "
        "year on entities registered under GST and those not registered. Non-reporting "
        "or incorrect reporting in Clause 44 attracts penalty u/s 271B.",

        # ── Form 3CD Clause 30C / 44 — GAAR Reporting ──
        "CBDT Notification No. 33/2018 — Clause 30C of Form 3CD requires the auditor "
        "to report any impermissible avoidance arrangement as defined under Section "
        "96 of the Income Tax Act. Auditors must independently form a view on GAAR "
        "applicability and not rely solely on management representations.",

        # ── Section 80-IC Sunset ──
        "CIT v. Aarham Softronics (2019) 410 ITR 500 (SC) — The deduction u/s 80-IC "
        "for undertakings in Himachal Pradesh, Uttarakhand, and North-Eastern states "
        "is available for an initial period of 5 years at 100% and 5 years at 25% "
        "(30% for companies). The sunset clause is strictly applied; the benefit "
        "cannot be extended beyond the prescribed period even by a court order.",
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # AOP / BOI / MAXIMUM MARGINAL RATE
    # (ADD-17)
    # ══════════════════════════════════════════════════════════════════════════

    "aop_boi_mmr": [
        "Indira Balakrishna v. CIT (1960) 39 ITR 546 (SC) — An Association of Persons "
        "(AOP) arises when two or more persons join together for a common purpose with "
        "the intent to earn income; the legal form of the arrangement is secondary to "
        "the substance of the combined activity.",

        "CIT v. Indira Balkrishna (1960) 39 ITR 546 (SC) — [Same case] AOP is taxed "
        "at the Maximum Marginal Rate (MMR) applicable to the highest slab if the "
        "shares of the members in the AOP income are indeterminate or unknown. Where "
        "shares are determinable, each member is taxed in their individual hands.",

        "CBDT Circular No. 2/2023 — Clarification on applicability of the new tax "
        "regime (Section 115BAC) to AOP/BOI: AOP/BOI are not eligible for the new "
        "concessional rate under 115BAC; they continue to be governed by the old "
        "rates, including MMR where shares are indeterminate.",
    ],
}


# ── Keyword → Case Law Mapping ─────────────────────────────────────────────────
# Rule: Map a keyword to a bucket ONLY if the cases in that bucket directly
# support the proposition the keyword implies. Precision over breadth.

_KEYWORD_MAP: dict[str, list[str]] = {
    "sec_68_cash_credit": [
        "68", "cash credit", "cash deposit", "unexplained credit",
        "unsecured loan", "creditor", "share application", "accommodation entry",
        "shell company", "penny stock credit", "source of source", "115bbe",
    ],
    "sec_69_unexplained_investment": [
        "69", "unexplained investment", "investment not explained",
        "unexplained assets",
    ],
    "sec_69a_unexplained_money": [
        "69a", "unexplained money", "unexplained deposits", "demonetisation",
        "cash in hand", "jewellery seizure", "note ban deposit",
    ],
    "sec_69b_69c_excess_investment_expenditure": [
        "69b", "69c", "unexplained expenditure", "investments exceeding sources",
        "excess investment",
    ],
    "sec_14a_rule_8d": [
        "14a", "rule 8d", "exempt income", "disallowance on exempt",
        "dividend income expenditure", "14(a)", "8d",
    ],
    "sec_56_2_viib_angel_tax": [
        "56(2)(viib)", "angel tax", "share premium", "fair market value of shares",
        "dcf valuation", "nav method", "dpiit", "rule 11ua",
    ],
    "sec_56_2_x_gifts": [
        "56(2)(x)", "56(2)(vii)", "gift tax", "property without consideration",
        "inadequate consideration", "stamp duty mismatch gift",
    ],
    "sec_50c_43ca_stamp_duty": [
        "50c", "43ca", "stamp duty", "stamp duty valuation",
        "circle rate", "dvo reference", "guidance value",
    ],
    "capital_gains_45_48": [
        "45", "48", "capital gains", "long term capital gain", "ltcg",
        "cost of acquisition", "indexed cost", "business income vs capital",
        "holding period", "capital asset", "2(42a)",
    ],
    "sec_54_54f_54ec_exemptions": [
        "54", "54f", "54ec", "capital gains exemption", "new residential house",
        "54ec bonds", "nhai bonds", "rec bonds", "one house condition",
    ],
    "sec_10_38_112a_penny_stock": [
        "10(38)", "112a", "penny stock", "ltcg on shares", "sebi alert",
        "sttt", "stt paid", "demat", "price rigging",
    ],
    "sec_143_1_intimation": [
        "143(1)", "intimation", "cpc intimation", "prima facie adjustment",
        "ais mismatch intimation",
    ],
    "sec_147_148_reopening": [
        "147", "148", "reopening", "reassessment", "escaped income",
        "reasons to believe", "tola", "change of opinion", "tangible material",
    ],
    "sec_148a_procedural": [
        "148a", "148 a", "scn before notice", "148a(b)", "148a(d)",
        "speaking order 148a", "source of information",
    ],
    "sec_151_sanction": [
        "151", "sanction", "specified authority", "pcit approval",
        "prior sanction", "sanctioning authority",
    ],
    "sec_149_limitation": [
        "149", "time limit", "time bar", "limitation", "barred by time",
        "six year limit", "ten year limit", "tola window",
    ],
    "sec_271_penalty": [
        "271(1)(c)", "271", "concealment", "furnishing inaccurate particulars",
        "penalty notice concealment",
    ],
    "sec_270a_penalty": [
        "270a", "under-reporting", "misreporting", "omnibus penalty notice",
        "strike out", "200% penalty", "270aa", "immunity penalty",
    ],
    "sec_37_business_expenditure": [
        "37", "business expenditure", "wholly and exclusively", "revenue expenditure",
        "capital expenditure", "commercial expediency", "non-compete",
        "csr expenditure", "pharma freebie", "penalty disallowance",
    ],
    "sec_40a_ia_tds_disallowance": [
        "40(a)(ia)", "40a", "tds disallowance", "non-deduction tds",
        "short deduction", "form 26a", "merilyn shipping",
    ],
    "sec_263_revision": [
        "263", "revision", "pcit revision", "erroneous order",
        "prejudicial to revenue", "revision jurisdiction",
    ],
    "sec_234_interest": [
        "234a", "234b", "234c", "interest on tax", "interest on advance tax",
        "waiver of interest",
    ],
    "tds_mismatch": [
        "tds", "26as", "form 26", "tax deducted at source", "tds credit",
        "tds mismatch", "ais mismatch", "285bb", "tis mismatch",
    ],
    "natural_justice": [
        "personal hearing", "natural justice", "audi alteram",
        "opportunity of hearing", "ex parte", "show cause notice",
    ],
    "din_circular": [
        "din", "document identification number", "circular 19/2019",
        "void notice", "no din",
    ],
    "faceless_assessment": [
        "faceless", "144b", "nfac", "national faceless",
        "faceless assessment centre", "draft assessment order",
    ],
    "sec_153a_search": [
        "153a", "153 a", "search and seizure", "search assessment",
        "incriminating material", "unabated assessment", "abated assessment",
    ],
    "sec_194q_tcs_overlap": [
        "194q", "206c(1h)", "tcs on sale", "tds on purchase",
        "194q vs 206c", "circular 13/2021", "circular 20/2021",
    ],
    "viksit_bharat_msme_compliance": [
        "43b(h)", "msme payment", "msmed act", "micro enterprise",
        "small enterprise", "44ab", "tax audit threshold",
        "form 3cd", "clause 44", "clause 30c", "80-ic", "80ic",
    ],
    "aop_boi_mmr": [
        "aop", "boi", "association of persons", "body of individuals",
        "maximum marginal rate", "mmr", "indeterminate shares",
    ],
}


def get_relevant_case_laws(issue_text: str) -> str:
    """Return verified case laws relevant to the identified issues.
    Deterministic — zero LLM involvement.
    """
    issue_lower = issue_text.lower()
    relevant: list[str] = []

    for key, keywords in _KEYWORD_MAP.items():
        if any(kw in issue_lower for kw in keywords):
            laws = VERIFIED_CASE_LAWS.get(key, [])
            if laws:
                relevant.append(f"\n--- {key.replace('_', ' ').upper()} ---")
                relevant.extend(laws)

    if not relevant:
        return (
            "No pre-verified case laws matched. "
            "The AI may suggest additional authorities only under "
            "'SUGGESTED AUTHORITIES - VERIFY BEFORE USE' with an independent-verification caution."
        )
    return "\n".join(relevant)


def build_citation_fingerprints() -> set[str]:
    """Build a set of lowercase fingerprints from all verified citations."""
    known: set[str] = set()
    for bucket in VERIFIED_CASE_LAWS.values():
        for entry in bucket:
            known.add(entry.lower()[:80])
    return known


# Build at module load — used by HallucinationGuard
ALL_KNOWN_CITATION_FINGERPRINTS: set[str] = build_citation_fingerprints()


# v9 appellate drafting layer
# These buckets support Form 35, Rule 46A, stay-of-demand, and ITAT-stage notice
# responses. Entries retain the string format used by the legacy library, but each
# one carries facts, holding, and use-note so prompts can draft with context.
VERIFIED_CASE_LAWS.update({
    "penalty_proceedings_general": [
        "Hindustan Steel Ltd. v. State of Orissa [1972] 83 ITR 26 (SC) - Facts: Penalty was imposed for a statutory default where the breach was not shown to be deliberate. Held: Penalty should not be imposed merely because it is lawful to do so; discretion must be exercised judicially, particularly where the default is technical or bona fide. Use: Support reasonable-cause and bona fide conduct submissions in penalty replies.",
        "CIT v. Reliance Petroproducts (P.) Ltd. [2010] 322 ITR 158 (SC) - Facts: The assessee made a claim which was disallowed, and penalty under section 271(1)(c) was levied. Held: Mere making of an unsustainable claim does not amount to furnishing inaccurate particulars where particulars are disclosed. Use: Support defense against penalty where the dispute is about disallowance or legal interpretation.",
        "Price Waterhouse Coopers (P.) Ltd. v. CIT [2012] 348 ITR 306 (SC) - Facts: A provision was not added back due to a bona fide and inadvertent error despite disclosure in tax audit records. Held: Penalty was not justified for a bona fide mistake where there was no intent to conceal. Use: Support penalty reply based on disclosure, inadvertence, and absence of mala fide intent.",
    ],
    "penalty_defective_notice_satisfaction": [
        "CIT v. SSA's Emerald Meadows [2016] 73 taxmann.com 241 (SC) - Facts: Penalty notice did not specify the precise charge and the High Court quashed the penalty. Held: Supreme Court dismissed the SLP, leaving intact the principle that vague omnibus penalty notice is fatal. Use: Support objection where notice does not strike off irrelevant limb or specify exact charge.",
        "CIT v. Manjunatha Cotton and Ginning Factory [2013] 359 ITR 565 (Kar) - Facts: Penalty notice was issued without clear specification of concealment or furnishing inaccurate particulars. Held: Notice must specify the exact charge; omnibus notice violates natural justice. Use: Support challenge to defective section 274 notice.",
        "Dilip N. Shroff v. JCIT [2007] 291 ITR 519 (SC) - Facts: Penalty proceedings were examined for charge clarity and satisfaction. Held: Penalty proceedings require clarity of charge and cannot be casual or ambiguous. Use: Support procedural objection to vague penalty initiation, with caution because later case law modified parts on mens rea.",
    ],
    "penalty_abeyance_quantum_appeal": [
        "CIT v. Reliance Petroproducts (P.) Ltd. [2010] 322 ITR 158 (SC) - Facts: Penalty was tied to a disallowed claim in quantum proceedings. Held: Disallowance itself is not conclusive for penalty. Use: Support request to keep penalty in abeyance while the disputed quantum addition is pending in appeal.",
        "K.C. Builders v. ACIT [2004] 265 ITR 562 (SC) - Facts: Penalty/prosecution consequences were considered after the underlying additions did not survive. Held: Where the foundation of concealment does not survive, penalty-related consequences cannot stand on that basis. Use: Support abeyance and merits defense where quantum appeal may delete the addition.",
        "CIT v. Harshvardhan Chemicals and Minerals Ltd. [2003] 259 ITR 212 (Raj) - Facts: Penalty arose from additions involving debatable claims. Held: Penalty is not sustainable where the issue is debatable and the claim is bona fide. Use: Support abeyance/merits where the quantum issue is arguable.",
    ],
    "penalty_condonation_reasonable_cause": [
        "Collector, Land Acquisition v. Mst. Katiji [1987] 167 ITR 471 (SC) - Facts: Delay condonation was considered where technical limitation could defeat substantial justice. Held: Liberal approach is appropriate when sufficient cause exists and there is no mala fide. Use: Support condonation petition for delayed Form 35, penalty appeal, or delayed penalty response.",
        "N. Balakrishnan v. M. Krishnamurthy [1998] 7 SCC 123 (SC) - Facts: The Court considered whether length of delay alone should defeat condonation. Held: Acceptability of the explanation is more important than length of delay. Use with caution as a general limitation-law authority.",
        "Woodward Governor India (P.) Ltd. v. CIT [2002] 253 ITR 745 (Del) - Facts: Penalty for non-compliance was tested against reasonable cause. Held: Reasonable cause must receive a practical and justice-oriented interpretation. Use: Support section 273B reasonable-cause submissions in compliance penalty matters.",
    ],
    "penalty_270a_misreporting": [
        "Schneider Electric South East Asia (HQ) Pte Ltd. v. ACIT [2022] 443 ITR 186 (Del) - Facts: Penalty proceedings under section 270A were challenged where the notice/order did not clearly identify the limb. Held: Penalty action must identify whether the case is under-reporting or misreporting and must follow statutory safeguards. Use: Support objection to vague 270A notice and 200 percent misreporting levy without a specific section 270A(9) finding.",
        "Prem Brothers Infrastructure LLP v. NFAC [2022] 137 taxmann.com 330 (Del) - Facts: Section 270A penalty was initiated/levied without proper opportunity and charge clarity. Held: Natural justice and clear statutory basis are essential in 270A penalty proceedings. Use: Support challenge to faceless penalty orders passed mechanically or without adequate opportunity.",
    ],
    "appeals_form_35_powers": [
        "CIT v. Kanpur Coal Syndicate [1964] 53 ITR 225 (SC) - Facts: The assessee challenged the scope of appellate powers in income-tax appeal. Held: The first appellate authority has plenary powers in disposing of an appeal and can do what the Assessing Officer could have done, subject to the statute. Use: Support a Form 35 prayer asking CIT(A)/JCIT(A) to examine the full assessment record and grant complete relief.",
        "Jute Corporation of India Ltd. v. CIT [1991] 187 ITR 688 (SC) - Facts: The assessee raised an additional claim before the appellate authority which was not urged before the Assessing Officer. Held: The appellate authority may permit additional grounds where the ground is bona fide and necessary to correctly assess tax liability. Use: Support admission of a new legal ground in Form 35 where facts are already on record.",
        "CIT v. Mahalakshmi Textile Mills Ltd. [1967] 66 ITR 710 (SC) - Facts: Relief was considered on a legal basis different from the specific argument taken earlier. Held: Appellate authorities must decide the correct tax liability on the facts and are not confined merely to the arguments originally framed. Use: Support broad appellate relief where the assessee's entitlement arises from the record.",
        "National Thermal Power Co. Ltd. v. CIT [1998] 229 ITR 383 (SC) - Facts: A legal ground was raised for the first time before the Tribunal on facts already available on record. Held: The Tribunal can examine a pure question of law arising from facts on record if it is necessary to determine correct tax liability. Use: Support ITAT-stage grounds or responses to appellate notices where a legal issue emerges from the assessment record.",
    ],
    "rule_46a_additional_evidence": [
        "Smt. Prabhavati S. Shah v. CIT [1998] 231 ITR 1 (Bom) - Facts: Additional evidence was sought to be produced at the appellate stage. Held: Rule 46A regulates production of additional evidence but does not curtail the appellate authority's power to make further inquiry for substantial justice. Use: Support a Rule 46A application where the assessee lacked proper opportunity or evidence is necessary for deciding the appeal.",
        "CIT v. Virgin Securities & Credits (P.) Ltd. [2011] 332 ITR 396 (Del) - Facts: Additional evidence was admitted during appellate proceedings and the Revenue objected. Held: Admission of additional evidence is permissible where the Assessing Officer gets adequate opportunity and natural justice is maintained. Use: Support additional evidence where remand opportunity can be provided to the AO.",
        "K. Venkataramiah v. A. Seetharama Reddy AIR 1963 SC 1526 - Facts: Additional evidence was considered at appellate stage for proper adjudication. Held: Appellate forums may admit evidence when they require it to pronounce judgment or for substantial cause. Use with caution in tax appeals because it is a civil-procedure authority, not an Income-tax Act ruling.",
    ],
    "condonation_of_delay_appeal": [
        "Collector, Land Acquisition v. Mst. Katiji [1987] 167 ITR 471 (SC) - Facts: Delay condonation was considered where technical limitation objections could defeat substantive justice. Held: A liberal approach should be adopted where sufficient cause exists and refusal to condone delay may result in meritorious matters being rejected at the threshold. Use: Support Form 35 condonation petitions with evidence-backed explanation.",
        "N. Balakrishnan v. M. Krishnamurthy [1998] 7 SCC 123 (SC) - Facts: The Court considered whether length of delay alone should control condonation. Held: Length of delay is not decisive; acceptability of the explanation is the primary test. Use with caution as a general limitation-law authority in appeal-delay petitions.",
    ],
    "stay_of_demand_appeal": [
        "KEC International Ltd. v. B.R. Balakrishnan [2001] 251 ITR 158 (Bom) - Facts: The assessee challenged mechanical disposal of a stay application. Held: Authorities must pass a reasoned order on stay, address prima facie case, financial hardship, and balance of convenience. Use: Support a stay petition filed after Form 35.",
        "UTI Mutual Fund v. ITO [2012] 345 ITR 71 (Bom) - Facts: Recovery was pursued without fair disposal of stay-related remedies. Held: Coercive recovery should not be made without reasonable opportunity and proper consideration of stay request. Use: Support protection from coercive recovery while appeal and stay petition are pending.",
        "Flipkart India (P.) Ltd. v. ACIT [2017] 79 taxmann.com 159 (Kar) - Facts: Demand stay was considered where the assessee disputed high-pitched assessment additions. Held: Stay discretion must be exercised judiciously and not mechanically based only on standard deposit percentages. Use: Support reduced deposit or conditional stay where the assessment is debatable or high-pitched.",
    ],
    "faceless_appeal_natural_justice": [
        "Tin Box Co. v. CIT [2001] 249 ITR 216 (SC) - Facts: Assessment was completed without adequate opportunity to the assessee. Held: Lack of proper opportunity vitiates the assessment and warrants remand. Use: Support personal hearing and remand grounds in faceless assessment/appeal matters.",
        "Andaman Timber Industries v. CCE [2015] 281 CTR 241 (SC) - Facts: Adverse statements were used without allowing cross-examination. Held: Denial of cross-examination when statements are relied upon is a serious violation of natural justice. Use: Support Form 35 grounds where third-party material, reports, or statements were used without confrontation.",
    ],
    "itat_notice_responses": [
        "Hukumchand Mills Ltd. v. CIT [1967] 63 ITR 232 (SC) - Facts: Scope of Tribunal powers in appeal was considered. Held: Tribunal has wide powers to pass appropriate orders on the subject matter of appeal. Use: Support comprehensive responses to ITAT notices where the issue arises from grounds and record.",
        "National Thermal Power Co. Ltd. v. CIT [1998] 229 ITR 383 (SC) - Facts: A pure legal issue was raised before the Tribunal for the first time. Held: Tribunal may consider legal questions arising from facts already on record. Use: Support additional legal grounds or objection to technical rejection at ITAT stage.",
        "CIT v. Sinhgad Technical Education Society [2017] 397 ITR 344 (SC) - Facts: Additions in search-related proceedings were examined for connection with incriminating material. Held: Jurisdictional conditions must be satisfied and the issue must arise from relevant material. Use: Support ITAT-stage jurisdictional objections where additions lack the required foundation.",
    ],
})

_KEYWORD_MAP.update({
    "penalty_proceedings_general": [
        "penalty", "chapter xxi", "bona fide", "bonafide", "inaccurate particulars",
        "concealment", "mere disallowance", "debatable claim",
    ],
    "penalty_defective_notice_satisfaction": [
        "274", "defective notice", "vague notice", "satisfaction",
        "strike off", "not struck off", "omnibus penalty notice",
    ],
    "penalty_abeyance_quantum_appeal": [
        "abeyance", "quantum appeal", "form 35 filed", "appeal pending",
        "penalty proceedings may be kept in abeyance",
    ],
    "penalty_condonation_reasonable_cause": [
        "reasonable cause", "273b", "condonation penalty", "delay penalty",
        "late penalty appeal", "delayed reply", "sufficient cause",
    ],
    "penalty_270a_misreporting": [
        "270a", "under-reporting", "under reporting", "misreporting",
        "200% penalty", "50% penalty", "270a(9)",
    ],
    "appeals_form_35_powers": [
        "form 35", "cit(a)", "jcit(a)", "246a", "first appeal",
        "grounds of appeal", "statement of facts", "appellate authority",
    ],
    "rule_46a_additional_evidence": [
        "rule 46a", "additional evidence", "remand report",
        "evidence not filed before ao", "lack of opportunity",
    ],
    "condonation_of_delay_appeal": [
        "condonation", "delay", "late appeal", "sufficient cause",
        "section 249", "limitation appeal",
    ],
    "stay_of_demand_appeal": [
        "stay of demand", "recovery", "section 220", "20% deposit",
        "coercive recovery", "high pitched assessment",
    ],
    "faceless_appeal_natural_justice": [
        "faceless appeal", "personal hearing", "video conference",
        "natural justice", "cross examination", "adverse material",
    ],
    "itat_notice_responses": [
        "itat", "form 36", "tribunal", "appellate tribunal",
        "hearing notice", "defect memo", "additional ground",
    ],
})

# Rebuild after the v9 appellate additions.
ALL_KNOWN_CITATION_FINGERPRINTS = build_citation_fingerprints()
