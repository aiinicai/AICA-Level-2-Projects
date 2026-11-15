"""Curated review prompts, not automatically asserted legal conclusions.
Sources were inspected 9 November 2026. Recheck amendments for a live matter.
"""
ACT = 'https://www.indiacode.nic.in/handle/123456789/15689?locale=en'
RULE99 = 'https://taxinformation.cbic.gov.in/content/html/tax_repository/gst/rules/cgst_rules/active/chapter11/rule99_v1.00.html'
RULE142 = 'https://taxinformation.cbic.gov.in/content/html/tax_repository/gst/rules/cgst_rules/active/chapter18/rule142_v1.00.html'
S74A = 'https://taxinformation.cbic.gov.in/content/html/tax_repository/gst/acts/2017_CGST_act/active/chapter15/Section74A_v1.00.html'
S17 = 'https://taxinformation.cbic.gov.in/content/html/tax_repository/gst/acts/2017_CGST_act/active/chapter5/section17_v1.00.html'
ISSUES = {
 'itc_mismatch': {
  'title': 'ITC mismatch: supplier data vs credit claimed',
  'patterns': [r'(?:gstr[ -]?2[ab]|2b|2a).{0,160}(?:gstr[ -]?3b|mismatch|excess|difference)', r'(?:itc|input tax credit).{0,80}(?:mismatch|not reflected|not appearing|excess.{0,30}2b)', r'(?:gstr[ -]?3b).{0,100}(?:gstr[ -]?2[ab])'],
  'provisions': 'CGST section 16 (eligibility and conditions); section 38 (inward-supply information). Apply the law and circulars for the actual tax period, including the commencement of section 16(2)(aa). A difference alone is not a final eligibility decision.',
  'facts': ['Reconcile invoice-wise GSTR-2A/2B, purchase register and GSTR-3B for the relevant period.', 'Identify timing differences, amendments, reversals and reclaims; distinguish imported services, RCM and imports from supplier-reported credits.', 'Verify invoice possession, receipt, supplier reporting, payment and all other period-specific eligibility conditions.'],
  'documents': ['Invoice-wise reconciliation with month and reason codes', 'Purchase invoices, receipt records and supplier communications', 'Relevant GSTR-2A/2B, GSTR-3B and reversal/reclaim workings'],
  'position': 'After verifying the reconciliation, identify which items are explained timing/classification differences and which remain unsupported. State the applicable period-specific legal basis for each item. Do not assert eligibility merely because an invoice exists.',
  'source': 'https://taxinformation.cbic.gov.in/content/html/tax_repository/gst/acts/2017_CGST_act/active/chapter5/section16_v1.00.html',
 },
 'liability_gap': {
  'title': 'Output liability: GSTR-1 vs GSTR-3B',
  'patterns': [r'gstr[ -]?1\b.{0,180}gstr[ -]?3b', r'(?:outward|output).{0,70}(?:short.?paid|short.?payment|liability.{0,15}(?:gap|difference)|under.?reported)'],
  'provisions': 'CGST sections 37 and 39 (outward-supply details and returns); section 50 may require review for interest. A return difference needs reconciliation before liability is concluded.',
  'facts': ['Reconcile taxable value and tax heads by return period, including amendments and credit notes.', 'Check advances, subsequent-period reporting and any payments already made.', 'Separate tax, interest and penalty; verify the demand basis and prevent double counting.'],
  'documents': ['GSTR-1 versus GSTR-3B month-wise bridge', 'Sales register, credit/debit notes and amendment trail', 'Electronic liability/cash/credit ledgers and DRC-03 evidence, if any'],
  'position': 'Explain each reconciling item with supporting records. Quantify any residual difference only after checking prior payments and tax-head allocation. Do not claim that every timing difference removes interest.',
  'source': ACT,
 },
 'rcm': {
  'title': 'Reverse-charge liability under review',
  'patterns': [r'\brcm\b', r'reverse[ -]charge'],
  'provisions': 'CGST section 9(3)/(4), or IGST section 5(3)/(4) where relevant, plus the applicable supply-specific notification for the period. Section 50 may require interest review. Not every purchase from an unregistered supplier attracts RCM.',
  'facts': ['Identify the exact service/goods, supplier status, recipient status and applicable notification for the period.', 'Verify taxable base, rate, time of supply and whether the supplier paid under forward charge.', 'Check cash payment evidence and separately assess any resulting ITC eligibility.'],
  'documents': ['Expense ledger and service agreements', 'Supplier invoices, declarations and relevant notification', 'RCM workings, cash ledger, returns and payment challans'],
  'position': 'State whether the transaction falls within a notified RCM category, supported by the notification and facts. Reconcile any amount already discharged. Do not assume forward-charge ITC offsets an unpaid RCM liability.',
  'source': 'https://taxinformation.cbic.gov.in/content/html/tax_repository/gst/acts/2017_CGST_act/active/chapter3/section9_v1.00.html',
 },
 'blocked_itc': {
  'title': 'Blocked or ineligible input tax credit',
  'patterns': [r'blocked.{0,30}(?:credit|itc)', r'(?:ineligible|inadmissible).{0,30}(?:credit|itc)', r'section\s*17\s*\(\s*5\s*\)', r'17\s*\(\s*5\s*\)'],
  'provisions': 'CGST section 17(5) (blocked credits) read with section 16. Exceptions are fact-specific; also consider apportionment under section 17(1)/(2) where actually relevant.',
  'facts': ['Classify each disputed inward supply and its actual use.', 'Check the precise blocked-credit clause and all relevant exceptions for the period.', 'Verify whether credit was availed, utilised or already reversed; assess interest separately.'],
  'documents': ['Disputed invoices and expense/asset ledger', 'Business-use records, contracts and exception evidence', 'Credit reversal and utilisation workings'],
  'position': 'For each invoice, explain the relevant clause and whether a documented exception applies. Do not assert that business use alone overrides section 17(5). Quantify any reversal only after verification.',
  'source': S17,
 },
 'late_filing': {
  'title': 'Delayed filing or return non-filing',
  'patterns': [r'late[ -]fil|delayed.{0,25}(?:fil|return)|late[ -]fee|non[ -]fil|failure to (?:file|furnish)'],
  'provisions': 'CGST sections 39/44/45 as applicable to the return, section 47 (late fee) and section 50 where delayed tax payment is involved. Verify due-date extensions, waivers and caps for the exact return and period; no fee is computed by this app.',
  'facts': ['Verify return type, original/extended due date and actual filing date.', 'Check notified waivers/caps and any amount already paid.', 'Distinguish late filing fee from interest on delayed payment.'],
  'documents': ['Return acknowledgements with filing dates', 'Applicable due-date extension / waiver notifications', 'Portal fee computation and ledger/payment evidence'],
  'position': 'Set out the verified filing chronology and applicable notifications. Reconcile any late fee already paid. Do not state a daily rate or waiver without period-specific verification.',
  'source': ACT,
 },
}
PROCEDURE = {
 'ASMT-10': ('Scrutiny notice', 'Review CGST section 61 and rule 99. Explanation is ordinarily furnished in ASMT-11. Verify service date and the notice deadline; do not infer it from the issue date.', RULE99),
 'DRC-01': ('Summary of show-cause notice', 'Rule 142(1) concerns the DRC-01 summary; obtain the complete SCN and relied-upon annexures. Rule 142(4) provides for reply in DRC-06. The summary alone may omit the factual grounds.', RULE142),
 'DRC-01A': ('Pre-notice intimation', 'Rule 142(1A) concerns pre-notice communication in Part A. Submissions against proposed liability may be made in Part B under rule 142(2A). This is not itself a final demand order.', RULE142),
 'Unknown': ('Unrecognised document', 'Confirm the form, applicable procedure and complete document before preparing a response. The supported forms are ASMT-10, DRC-01 and DRC-01A.', ACT),
}
