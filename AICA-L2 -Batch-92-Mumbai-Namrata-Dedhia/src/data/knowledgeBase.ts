import { FAQRecord } from '../types/advisory';

export const INITIAL_KNOWLEDGE_BASE: FAQRecord[] = [
  // 1. REPATRIATION - NRO ACCOUNT USD 1M LIMIT
  {
    faq_id: 'REP-001',
    category: 'Repatriation Limits',
    subcategory: 'NRO Account Outward Remittance',
    user_question: 'How much money can an NRI repatriate abroad from an NRO account?',
    question_variations: [
      'What is the annual repatriation limit from an NRO account for NRIs?',
      'Can an NRI remit money from India to foreign country from NRO?',
      'How much funds can be sent overseas under FEMA from NRO account?',
      'Is there a USD 1 million limit for NRI repatriation?'
    ],
    short_answer: 'An NRI, PIO, or OCI is permitted to repatriate up to USD 1,000,000 (one million US Dollars) per financial year (April to March) from balances held in their Non-Resident Ordinary (NRO) account, subject to payment of applicable taxes and submission of Form 15CA and Form 15CB.',
    detailed_answer: 'Under Regulation 4(2) of the Foreign Exchange Management (Remittance of Assets) Regulations, 2016 and RBI Master Direction No. 13/2015-16, an Authorized Dealer (AD Category-I) bank may allow NRIs/PIOs to remit up to USD 1,000,000 per financial year out of balances held in their NRO account arising from legitimate sources (such as current income, sale proceeds of assets, or inheritance). The remitter must complete an online declaration in Form 15CA on the Income Tax e-filing portal and obtain an accountant certificate in Form 15CB from an Indian Chartered Accountant for taxable remittances exceeding ₹5,00,000. Remittances exceeding USD 1,000,000 in a financial year require prior specific approval from the Reserve Bank of India.',
    applicability: 'Non-Resident Indians (NRIs), Persons of Indian Origin (PIOs), and Overseas Citizens of India (OCIs) holding legitimate funds in Indian NRO accounts.',
    taxpayer_type: 'Individual',
    NRI_status: 'NRI / PIO / OCI',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Remittance must be made through an Authorized Dealer (AD) Bank.',
      'Funds must represent legitimate dues/assets in India.',
      'Applicable Indian income taxes must have been paid or withheld.',
      'Mandatory filing of Form 15CA (undertaking by remitter) and Form 15CB (Chartered Accountant certification for taxable amounts > ₹5 Lakhs).'
    ],
    exceptions: [
      'Remittances exceeding USD 1,000,000 per financial year require prior approval from the Reserve Bank of India (RBI).',
      'Citizens of Pakistan, Bangladesh, Sri Lanka, Afghanistan, China, Iran, Nepal, or Bhutan have separate restrictions.'
    ],
    thresholds: 'USD 1,000,000 per Financial Year (April 1 to March 31); Form 15CB required if taxable remittance exceeds ₹5,00,000.',
    rates: 'No FEMA levy; subject to applicable Indian income-tax on underlying income/gains.',
    limits: 'USD 1 Million / financial year under general permission.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '2016-04-01',
    source_type: 'Master Direction',
    source_authority: 'Reserve Bank of India (RBI)',
    act_or_regulation: 'Foreign Exchange Management (Remittance of Assets) Regulations, 2016',
    section_rule_regulation: 'Regulation 4(2) & RBI Master Direction No. 13/2015-16 (Part I, Section B)',
    circular_notification: 'Notification No. FEMA 13(R)/2016-RB',
    source_url: 'https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=10204',
    source_excerpt_or_summary: 'An Authorized Dealer may allow remittance up to USD 1,000,000 per financial year by an NRI/PIO out of balances held in the NRO account / sale proceeds of assets / assets acquired by way of inheritance / legacy.',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'REVIEW',
    keywords: ['repatriation', 'repatriate', 'NRO', 'USD 1 million', 'limit', '15CA', '15CB', 'remittance', 'FEMA', 'outward remittance'],
    related_faq_ids: ['REP-002', 'REP-003', 'TDS-001']
  },

  // 2. REPATRIATION - NRE / FCNR FULL REPATRIABILITY
  {
    faq_id: 'REP-002',
    category: 'Repatriation Limits',
    subcategory: 'NRE and FCNR(B) Accounts',
    user_question: 'Are funds held in NRE and FCNR(B) accounts freely repatriable?',
    question_variations: [
      'Can I transfer money from NRE account to my foreign account without limit?',
      'Is there any repatriation ceiling on FCNR deposits?',
      'Do I need RBI permission to transfer NRE funds abroad?'
    ],
    short_answer: 'Yes. Funds (both principal and interest earned) held in Non-Resident External (NRE) and Foreign Currency Non-Resident (Bank) [FCNR(B)] accounts are freely, fully, and unconditionally repatriable outside India without any monetary cap or requirement for RBI approval.',
    detailed_answer: 'Under the Foreign Exchange Management (Deposit) Regulations, 2016 (Schedule 1 and Schedule 2) and RBI Master Direction No. 14/2015-16, NRE and FCNR(B) accounts enjoy unrestricted repatriation. Because the initial credits to these accounts must come from inward remittances in foreign exchange or transfers from other NRE/FCNR accounts, the funds can be remitted overseas at any time without limitation. Furthermore, under Section 10(4)(ii) of the Income-tax Act, 1961, interest earned on NRE and FCNR(B) deposits is completely exempt from Indian income tax for persons resident outside India under FEMA.',
    applicability: 'NRIs and OCIs maintaining NRE or FCNR(B) accounts.',
    taxpayer_type: 'Individual',
    NRI_status: 'NRI / OCI',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Account holder must maintain non-resident status under FEMA.',
      'Debits for remittance must be executed through the designated Authorized Dealer bank.'
    ],
    exceptions: ['None for bona fide non-residents under FEMA.'],
    thresholds: 'No upper monetary limit.',
    rates: 'Interest earned is 100% tax-free under Section 10(4)(ii) of Income-tax Act.',
    limits: 'Unlimited / Full Repatriability.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '2016-04-01',
    source_type: 'Regulation',
    source_authority: 'Reserve Bank of India (RBI)',
    act_or_regulation: 'Foreign Exchange Management (Deposit) Regulations, 2016',
    section_rule_regulation: 'Schedule 1 (NRE) & Schedule 2 (FCNR(B)); Section 10(4)(ii) Income-tax Act',
    circular_notification: 'Notification No. FEMA 5(R)/2016-RB',
    source_url: 'https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=10202',
    source_excerpt_or_summary: 'The balance in the NRE/FCNR(B) account may be freely remitted outside India by the authorized dealer without prior RBI approval.',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'NO',
    keywords: ['NRE', 'FCNR', 'freely repatriable', 'tax free interest', 'unlimited remittance', 'Section 10(4)'],
    related_faq_ids: ['REP-001', 'FEMA-ACC-001']
  },

  // 3. REPATRIATION - SALE PROCEEDS OF INDIAN PROPERTY
  {
    faq_id: 'REP-003',
    category: 'Repatriation Limits',
    subcategory: 'Property Sale Proceeds',
    user_question: 'Can an NRI repatriate money from selling a flat or property in India?',
    question_variations: [
      'Can I send the money from selling my Mumbai flat to my US bank account?',
      'How to repatriate property sale proceeds from India?',
      'Is repatriation allowed on sale of inherited property in India?',
      'Can NRI remit flat sale proceeds under FEMA?',
      'I live in Dubai and sold my flat in India. How much can I transfer?',
      'How much money can I transfer after selling a flat in India?'
    ],
    short_answer: 'Yes. An NRI can repatriate the sale proceeds of immovable property in India. If the property was originally purchased using foreign currency/NRE funds, repatriation up to the original foreign acquisition cost can be remitted directly (capped at a maximum of two residential properties). Any capital appreciation or proceeds from properties purchased in INR / inherited can be repatriated through the NRO route up to USD 1,000,000 per financial year after paying applicable capital gains tax and obtaining Form 15CA/15CB.',
    detailed_answer: 'Repatriation of property sale proceeds is governed by Rule 28 of the Foreign Exchange Management (Non-debt Instruments) Rules, 2019 and RBI Master Direction on Remittance of Assets. Two distinct channels apply:\n1. Foreign Exchange Acquisition Route: Where residential/commercial property was acquired out of foreign currency remittances or NRE/FCNR funds in accordance with FEMA, the Authorized Dealer may allow repatriation of an amount not exceeding the foreign exchange equivalent originally brought in (limited to two residential properties).\n2. NRO Account Route (USD 1M Scheme): Capital gains, excess proceeds, or sale proceeds of properties acquired out of rupee/NRO funds or through inheritance can be credited to the seller\'s NRO account and repatriated under the USD 1,000,000 per financial year scheme upon clearance of Indian capital gains taxes, supported by Form 15CA and Form 15CB.',
    applicability: 'NRIs, PIOs, and OCIs selling residential or commercial immovable property in India.',
    taxpayer_type: 'Individual',
    NRI_status: 'NRI / PIO / OCI',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'The property must have been acquired in accordance with foreign exchange law in force at the time of acquisition.',
      'Applicable capital gains tax must be paid/withheld in India.',
      'Form 15CA and Form 15CB (Chartered Accountant certification) must be furnished to the Authorized Dealer bank.',
      'Direct foreign exchange route is restricted to a maximum of two residential properties.'
    ],
    exceptions: [
      'Properties purchased in violation of FEMA cannot be repatriated without RBI compounding.',
      'Remittances exceeding USD 1 Million/FY through NRO route require prior RBI approval.'
    ],
    thresholds: 'USD 1,000,000 per financial year under the NRO route; up to original foreign currency cost for 2 residential properties.',
    rates: 'Subject to capital gains tax (LTCG / STCG) under Income-tax Act before remittance.',
    limits: 'Max 2 residential properties for direct foreign exchange repatriation; USD 1M/FY for NRO route.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '2019-10-17',
    source_type: 'Regulation',
    source_authority: 'Reserve Bank of India (RBI)',
    act_or_regulation: 'FEMA (Non-debt Instruments) Rules, 2019 & Remittance of Assets Regulations, 2016',
    section_rule_regulation: 'Rule 28 of NDI Rules 2019 & Reg 4(2) of Remittance of Assets Regulations',
    circular_notification: 'RBI Master Direction No. 13/2015-16',
    source_url: 'https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=10204',
    source_excerpt_or_summary: 'Repatriation of sale proceeds of residential property purchased by NRI out of foreign funds is limited to maximum two such properties; capital gains and rupee-funded property proceeds are repatriable under USD 1M NRO facility.',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'REVIEW',
    keywords: ['property sale', 'flat sale', 'repatriation', 'NRO', 'USD 1 million', 'two properties', 'Form 15CA', 'Form 15CB', 'inherited property'],
    related_faq_ids: ['TDS-001', 'TDS-002', 'REP-001', 'PROP-001']
  },

  // 4. TDS ON SALE OF PROPERTY - SECTION 195 AND RATES
  {
    faq_id: 'TDS-001',
    category: 'TDS on Sale of Indian Property',
    subcategory: 'Section 195 Withholding & Rates',
    user_question: 'What is the TDS rate when an NRI sells a property in India?',
    question_variations: [
      'How much TDS is deducted on sale of property by NRI?',
      'What is the difference between Section 194-IA and Section 195 TDS on property?',
      'Does buyer have to deduct 20% or 12.5% TDS on NRI property sale?',
      'TDS on NRI real estate sale in India'
    ],
    short_answer: 'When an NRI sells immovable property in India, the buyer is legally obligated under Section 195 of the Income-tax Act to deduct TDS on the payment. For Long-Term Capital Gains (LTCG - held > 24 months), following the Finance (No. 2) Act 2024, the statutory tax rate is 12.5% without indexation (plus applicable surcharge and 4% cess). For Short-Term Capital Gains (STCG - held ≤ 24 months), TDS is deducted at maximum slab rates (30% plus surcharge and cess). Crucially, unless a Lower/Nil Deduction Certificate is obtained under Section 197, buyers often deduct TDS on the ENTIRE gross sale consideration.',
    detailed_answer: 'Unlike property sales between resident Indians (which fall under Section 194-IA at 1% only for transactions above ₹50 lakh), sales by a Non-Resident seller are governed strictly by Section 195 of the Income-tax Act, 1961. Key provisions include:\n1. No ₹50 Lakh threshold: Section 195 applies regardless of transaction value (even for properties under ₹50 Lakhs).\n2. Holding Period: Immovable property is Long-Term if held for more than 24 months from the date of acquisition; Short-Term if held for 24 months or less.\n3. Tax Rates Post Finance (No. 2) Act, 2024 (effective July 23, 2024):\n   - Long-Term Capital Gains (LTCG): 12.5% without indexation benefit, plus applicable surcharge (10% to 15%) and 4% Health & Education Cess, resulting in an effective rate between ~13.0% and ~14.95%.\n   - Short-Term Capital Gains (STCG): Taxed at applicable normal slab rates (up to 30% plus surcharge and cess, yielding an effective rate up to ~35.88% or ~39%).\n4. Gross vs Net Issue: Under Section 195, Authorized Dealers and buyers are required to deduct TDS on the gross consideration unless the seller furnishes a certificate for Lower or Nil Deduction of TDS issued by the Income Tax Department under Section 197.',
    applicability: 'All non-resident sellers (NRIs, OCIs) of immovable property located in India.',
    taxpayer_type: 'Individual / HUF',
    NRI_status: 'Non-Resident',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Buyer must possess or obtain a Tax Deduction and Collection Account Number (TAN) under Section 203A (Form 26QB cannot be used for NRI sellers; buyer must file Form 27Q).',
      'TDS must be deposited with the government within 7 days of the following month.',
      'Holding period > 24 months determines LTCG; ≤ 24 months determines STCG.'
    ],
    exceptions: [
      'Seller can obtain a Lower or Nil Deduction Certificate under Section 197 from the Assessing Officer to restrict TDS to the actual capital gains rather than the full sale consideration.'
    ],
    thresholds: 'No minimum threshold under Section 195; applies from ₹1. Holding period threshold: 24 months.',
    rates: 'LTCG: 12.5% (plus surcharge & 4% cess). STCG: 30% (plus surcharge & 4% cess). Surcharge: 10% (income ₹50L-₹1Cr), 15% (₹1Cr-₹2Cr).',
    limits: 'Applies to total consideration unless Section 197 certificate obtained.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '2024-07-23',
    source_type: 'Statute',
    source_authority: 'CBDT / Income Tax Department',
    act_or_regulation: 'Income-tax Act, 1961 (amended by Finance (No. 2) Act, 2024)',
    section_rule_regulation: 'Section 195, Section 112, Section 197, Section 2(42A)',
    circular_notification: 'CBDT Circular on Finance (No. 2) Act, 2024 & Section 195 Guidelines',
    source_url: 'https://incometaxindia.gov.in/pages/acts/income-tax-act.aspx',
    source_excerpt_or_summary: 'Any person responsible for paying to a non-resident any sum chargeable under the Act shall deduct income-tax thereon at the rates in force (Section 195). LTCG on unlisted property is 12.5% post July 23, 2024.',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'REVIEW',
    keywords: ['TDS', 'property sale', 'Section 195', '12.5%', 'LTCG', 'STCG', 'holding period', '24 months', 'surcharge', 'cess', 'TAN', 'Form 27Q'],
    related_faq_ids: ['TDS-002', 'REP-003', 'PROP-001']
  },

  // 5. TDS LOWER DEDUCTION CERTIFICATE (SECTION 197)
  {
    faq_id: 'TDS-002',
    category: 'TDS on Sale of Indian Property',
    subcategory: 'Lower or Nil TDS Certificate (Section 197)',
    user_question: 'How can an NRI avoid heavy TDS on the entire sale price of property?',
    question_variations: [
      'Can an NRI get a lower TDS certificate for property sale in India?',
      'How to apply for Section 197 certificate on TRACES?',
      'Form 13 application for NRI property sale TDS',
      'Can TDS be deducted only on capital gains instead of full selling price?'
    ],
    short_answer: 'An NRI seller can apply for a Lower or Nil Deduction Certificate under Section 197 of the Income-tax Act using Form 13 electronically on the TRACES portal. Once issued by the Jurisdictional Assessing Officer, the buyer is directed to deduct TDS only on the estimated net capital gains (or at a lower/nil rate) rather than on the gross sale consideration.',
    detailed_answer: 'Because Section 195 strictly directs tax deduction on payments to non-residents, buyers without a Section 197 certificate are required by law to withhold tax on the full transaction amount, causing severe liquidity blockage for NRI sellers. Under Section 197 read with Rule 28 / Rule 28AA of the Income Tax Rules, 1962, the NRI seller may submit Form 13 on the TRACES portal (www.tdscpc.gov.in) with:\n1. Agreement to sell / buyer details and buyer\'s TAN.\n2. Original purchase deed and proof of acquisition cost / improvements.\n3. Computation of estimated capital gains and planned exemptions (such as Section 54 or 54EC bonds).\n4. Past 3 years\' ITRs and bank statements.\nThe certificate specifies the specific buyer TAN, seller PAN, property details, and the reduced TDS percentage. The application should typically be initiated 4 to 8 weeks before property registration.',
    applicability: 'NRIs and OCIs selling immovable property or receiving other income subjected to Section 195 TDS.',
    taxpayer_type: 'Individual / HUF',
    NRI_status: 'Non-Resident',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Application must be filed online through TRACES portal in Form 13 before payment is credited or made.',
      'Buyer must have a valid TAN.',
      'Supporting documentary evidence of acquisition cost, indexed cost, and computation must be uploaded.',
      'The certificate is valid only for the specific buyer TAN and transaction amount mentioned therein.'
    ],
    exceptions: ['Cannot be applied retroactively after TDS has already been deducted and deposited.'],
    thresholds: 'No statutory monetary threshold; can be applied for nil (0%) or lower rate (e.g. 3%-5% on gross value corresponding to net gain).',
    rates: 'Specified by the Assessing Officer in the certificate based on verified gain computation.',
    limits: 'Valid for the financial year specified in the certificate.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '1962-04-01',
    source_type: 'Rule',
    source_authority: 'CBDT / Income Tax Department',
    act_or_regulation: 'Income-tax Act, 1961 & Income-tax Rules, 1962',
    section_rule_regulation: 'Section 197, Rule 28, Rule 28AA, Form 13',
    circular_notification: 'CBDT Notification No. 8/2018 (Electronic Form 13)',
    source_url: 'https://contents.tdscpc.gov.in/',
    source_excerpt_or_summary: 'Where the Assessing Officer is satisfied that total income of recipient justifies deduction at lower rates or no deduction, he shall give such certificate as appropriate (Section 197).',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'REVIEW',
    keywords: ['lower TDS', 'Section 197', 'Form 13', 'TRACES', 'nil deduction', 'capital gains', 'TAN', 'property sale'],
    related_faq_ids: ['TDS-001', 'REP-003']
  },

  // 6. PAN - AADHAAR LINKING FOR NRIS
  {
    faq_id: 'PAN-001',
    category: 'PAN/Aadhaar Linking',
    subcategory: 'NRI Exemption & Inoperative PAN',
    user_question: 'Do NRIs need to link their PAN with Aadhaar?',
    question_variations: [
      'Is Aadhaar PAN linking mandatory for Non-Resident Indians?',
      'Are NRIs exempt from PAN-Aadhaar linking under Indian tax law?',
      'My PAN became inoperative because I did not link Aadhaar. How can I fix it as an NRI?',
      'Can an NRI file ITR without Aadhaar?'
    ],
    short_answer: 'No. NRIs who qualify as Non-Residents under Section 6 of the Income-tax Act and do not possess an Aadhaar number are explicitly EXEMPT from the requirement of linking PAN with Aadhaar under CBDT Notification No. 37/2017. However, if your residential status in the Income Tax e-filing profile was not updated to Non-Resident, your PAN may have been erroneously flagged as inoperative and must be updated with proof of foreign residency.',
    detailed_answer: 'Under Section 139AA(3) of the Income-tax Act, 1961 read with CBDT Notification No. 37/2017 dated May 11, 2017, the requirement to quote or link Aadhaar does not apply to individuals who are:\n1. Residing in the States of Assam, Jammu & Kashmir, and Meghalaya;\n2. Non-residents as per Section 6 of the Income-tax Act, 1961;\n3. Of the age of 80 years or more at any time during the previous year;\n4. Not citizens of India.\n\nHowever, the Income Tax Department automated inoperative PAN flagging by cross-checking e-filing profiles. If an NRI had registered their PAN originally with an Indian address or did not update their status to "Non-Resident", their PAN may be marked "Inoperative" under Rule 114AAA. Consequences of inoperative PAN include higher TDS deduction under Section 206AA (up to 20%), withholding of tax refunds, and non-payment of refund interest. To restore operative status, the NRI must submit proof of foreign residency (such as copy of passport, foreign visa, overseas utility bill, or Tax Residency Certificate) to their Jurisdictional Assessing Officer (JAO) or update their profile on the e-filing portal.',
    applicability: 'All individuals qualifying as Non-Resident under Section 6 of the Income-tax Act, 1961.',
    taxpayer_type: 'Individual',
    NRI_status: 'Non-Resident',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Must qualify as a Non-Resident under Section 6 of the Income-tax Act.',
      'Must not have been allotted an Aadhaar number (if allotted an Aadhaar, quoting/linking is required).',
      'Residential status on the Income Tax e-filing portal profile must reflect "Non-Resident".'
    ],
    exceptions: [
      'If an NRI subsequently returns to India and becomes a resident under Section 6, the exemption ceases to apply.',
      'If an NRI has voluntarily obtained an Aadhaar card, they are advised to link it.'
    ],
    thresholds: 'Exemption applies to non-residents regardless of income level.',
    rates: 'Penalty of ₹1,000 applicable to residents does NOT apply to exempt NRIs.',
    limits: 'N/A',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '2017-07-01',
    source_type: 'Notification',
    source_authority: 'CBDT / Income Tax Department',
    act_or_regulation: 'Income-tax Act, 1961 & Income-tax Rules, 1962',
    section_rule_regulation: 'Section 139AA, Rule 114AAA, Notification No. 37/2017/F. No. 370133/6/2017-TPL',
    circular_notification: 'CBDT Circular No. 03/2023 dated 28 March 2023',
    source_url: 'https://incometaxindia.gov.in/communications/notification/notification37_2017.pdf',
    source_excerpt_or_summary: 'Central Government notifies that provisions of Section 139AA shall not apply to an individual who is not a resident as per the Income-tax Act, 1961.',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'NO',
    keywords: ['PAN', 'Aadhaar', 'linking', 'inoperative PAN', 'Notification 37/2017', 'Section 139AA', 'exemption', 'Rule 114AAA'],
    related_faq_ids: ['RES-001', 'TDS-001']
  },

  // 7. DTAA RELIEF AND DOCUMENTATION
  {
    faq_id: 'DTAA-001',
    category: 'DTAA Relief and Conditions',
    subcategory: 'TRC, Form 10F and Beneficial Tax Rates',
    user_question: 'How does an NRI claim Double Tax Avoidance Agreement (DTAA) relief in India?',
    question_variations: [
      'What documents are needed to claim lower tax rate under DTAA for NRI?',
      'Is Tax Residency Certificate (TRC) mandatory for DTAA?',
      'How to file Form 10F online on income tax portal?',
      'Can NRI claim benefit of DTAA over domestic income tax law?'
    ],
    short_answer: 'Under Section 90(2) of the Income-tax Act, an NRI is entitled to opt for the provisions of the Indian domestic tax law or the applicable bilateral DTAA between India and their country of residence, whichever is more beneficial. To claim treaty benefits (such as lower withholding tax on interest, royalties, or dividends), the NRI must furnish a valid Tax Residency Certificate (TRC) issued by their foreign government and file Form 10F electronically on the Indian Income Tax e-filing portal.',
    detailed_answer: 'India has signed comprehensive Double Tax Avoidance Agreements (DTAAs) with over 85 countries (including USA, UK, UAE, Canada, Singapore, Australia). Key mechanisms and rules include:\n1. Section 90(2) Principle: The provisions of the Act apply only to the extent they are more beneficial than the DTAA.\n2. Mandatory TRC (Section 90(4)): An NRI cannot claim relief under any DTAA unless they obtain a Tax Residency Certificate from the government/tax authority of the foreign country where they reside.\n3. Electronic Form 10F (Rule 21AB): If the TRC does not contain all particulars required under Rule 21AB (such as status, nationality, country of tax residence, tax identification number, and address), the taxpayer must file Form 10F electronically on the Income Tax e-filing portal.\n4. Foreign Tax Credit (FTC) & Form 67: If tax is paid in India on Indian income, the NRI can claim Foreign Tax Credit in their home country, or vice versa. When claiming FTC in India under Rule 128, Form 67 must be filed on or before the due date of filing the ITR under Section 139(1).\n5. Common Treaty Rates: Many DTAAs restrict withholding tax on interest (e.g. NRO interest) to 10%–15%, compared to the domestic rate of 30% under Section 195.',
    applicability: 'Non-residents earning income sourced or taxable in India residing in treaty-partner jurisdictions.',
    taxpayer_type: 'Individual / Company / Entity',
    NRI_status: 'Non-Resident',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Must be a tax resident of a country with which India has an active DTAA.',
      'Must obtain a valid Tax Residency Certificate (TRC) for the relevant financial year.',
      'Must e-file Form 10F on the Income Tax e-filing portal if TRC lacks statutory fields.',
      'Must submit a "No Permanent Establishment (PE) / Business Connection" declaration where applicable.'
    ],
    exceptions: [
      'Cannot be claimed if transaction is deemed an impermissible avoidance arrangement under General Anti-Avoidance Rules (GAAR - Chapter X-A) or fails Multilateral Instrument (MLI) Principal Purpose Test (PPT).'
    ],
    thresholds: 'No minimum threshold; treaty rates apply as agreed in respective bilateral articles.',
    rates: 'Varies by treaty article (e.g. 10% to 15% on interest/royalties vs 30% domestic rate).',
    limits: 'Relief capped at tax liability under domestic law.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '1962-04-01',
    source_type: 'Statute',
    source_authority: 'CBDT / Income Tax Department',
    act_or_regulation: 'Income-tax Act, 1961 & Income-tax Rules, 1962',
    section_rule_regulation: 'Section 90, Section 90A, Section 91, Rule 21AB, Rule 128 (Form 67)',
    circular_notification: 'CBDT Electronic Form 10F Order & DGIT (Systems) Notification 03/2022',
    source_url: 'https://incometaxindia.gov.in/pages/international-taxation/dtaa.aspx',
    source_excerpt_or_summary: 'An assessee not being a resident shall not be entitled to claim any relief under DTAA unless a certificate of his being a resident in that country (TRC) is obtained from the government of that country (Section 90(4)).',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'REVIEW',
    keywords: ['DTAA', 'TRC', 'Tax Residency Certificate', 'Form 10F', 'Form 67', 'Section 90', 'Foreign Tax Credit', 'treaty relief', 'withholding tax'],
    related_faq_ids: ['FINC-001', 'TDS-001', 'RES-001']
  },

  // 8. FEMA BANK ACCOUNT CONVERSION
  {
    faq_id: 'FEMA-ACC-001',
    category: 'FEMA Bank Account Conversion',
    subcategory: 'Redesignation of Resident Accounts to NRO',
    user_question: 'What happens to my Indian bank account when I move abroad and become an NRI?',
    question_variations: [
      'Can an NRI keep a regular resident savings account in India?',
      'Is it mandatory to convert resident bank account to NRO under FEMA?',
      'What is the penalty for holding a resident account after becoming an NRI?',
      'How to convert savings account to NRO account?'
    ],
    short_answer: 'Under FEMA regulations, an Indian resident who moves abroad for employment, business, or an indefinite stay MUST immediately notify their Indian bank to re-designate their existing resident savings accounts to Non-Resident Ordinary (NRO) accounts. Continuing to operate a resident savings account as an NRI is a violation of FEMA Section 10(6) and Section 13, attracting penalties of up to three times the sum involved.',
    detailed_answer: 'Governed by the Foreign Exchange Management (Deposit) Regulations, 2016 (Notification No. FEMA 5(R)/2016-RB) and RBI Master Direction No. 14/2015-16:\n1. Mandatory Re-designation: As soon as a person\'s residential status shifts from resident to "person resident outside India" under Section 2(w) of FEMA, their existing resident accounts must be re-designated as NRO accounts by submitting a status change application, overseas address proof, visa/work permit, and passport copy to the bank.\n2. Permitted Account Types for NRIs:\n   - NRO (Non-Resident Ordinary): For receiving Rupee income in India (rent, pension, dividends, sale proceeds). Repatriable up to USD 1 Million/FY.\n   - NRE (Non-Resident External): Maintained in INR, funded strictly via foreign inward remittances. Freely repatriable; interest earned is 100% tax-free under Section 10(4)(ii).\n   - FCNR(B) (Foreign Currency Non-Resident): Term deposits in foreign currency (USD, GBP, EUR, etc.), protecting against exchange risk. Freely repatriable and tax-free.\n3. Resident Account Prohibition: Holding a resident account as an NRI is strictly illegal under FEMA. Under Section 13 of FEMA, contraventions attract a penalty up to three times the sum involved or ₹2,00,000 where the amount is unquantifiable, plus continuing daily penalties.\n4. Investments & PPF: Existing Public Provident Fund (PPF) accounts opened while resident may be continued until the 15-year maturity on a non-repatriable basis, but extensions beyond maturity are not permitted for NRIs.',
    applicability: 'All Indian citizens and persons moving abroad who qualify as non-residents under FEMA.',
    taxpayer_type: 'Individual',
    NRI_status: 'NRI under FEMA Section 2(w)',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Notice must be given to the bank promptly upon departure from India with intention of uncertain duration.',
      'Overseas address proof, foreign visa / work permit copy must be submitted.',
      'Resident fixed deposits must also be converted to NRO FDs.'
    ],
    exceptions: [
      'Returning NRIs who re-establish permanent residence in India must convert NRE/NRO back to resident savings accounts or Resident Foreign Currency (RFC) accounts.'
    ],
    thresholds: 'Penalty under Section 13 FEMA: up to 3x the sum involved, or ₹2,00,000 if unquantifiable.',
    rates: 'Interest on NRO is taxable in India (TDS deducted @ 30% plus cess, unless DTAA applied). NRE/FCNR interest is 0% tax.',
    limits: 'Mandatory for all resident accounts.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '2016-04-01',
    source_type: 'Regulation',
    source_authority: 'Reserve Bank of India (RBI)',
    act_or_regulation: 'Foreign Exchange Management (Deposit) Regulations, 2016 & FEMA 1999',
    section_rule_regulation: 'Schedule 3 of FEMA 5(R)/2016-RB; Section 10(6) & Section 13 of FEMA 1999',
    circular_notification: 'RBI Master Direction No. 14/2015-16',
    source_url: 'https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=10202',
    source_excerpt_or_summary: 'NRO accounts may be opened / maintained by any person resident outside India. When a person resident in India leaves India for taking up employment or business outside India, his existing account should be designated as an NRO account.',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'NO',
    keywords: ['bank account', 'convert', 'NRO', 'NRE', 'FCNR', 'FEMA 5(R)', 'Section 13', 'penalty', 'redesignate', 'resident savings'],
    related_faq_ids: ['REP-001', 'REP-002', 'RES-001']
  },

  // 9. PURCHASE OF IMMOVABLE PROPERTY BY NRIS / OCIS
  {
    faq_id: 'PROP-001',
    category: 'FEMA Immovable Property',
    subcategory: 'Purchase Rules & Agricultural Land Prohibition',
    user_question: 'Can an NRI or OCI buy property in India? Are there any restrictions?',
    question_variations: [
      'Can an NRI purchase agricultural land, farm house, or plantation in India?',
      'What types of real estate can an NRI buy in India under FEMA?',
      'Can an OCI buy commercial property in India?',
      'How can an NRI pay for buying a house in India?'
    ],
    short_answer: 'Under FEMA regulations, an NRI or OCI has general permission to purchase any residential or commercial immovable property in India without prior RBI approval. However, there is a STRICT STATUTORY PROHIBITION: NRIs and OCIs CANNOT purchase agricultural land, plantation property, or a farm house under any circumstances without specific prior approval from the Reserve Bank of India (which is rarely granted).',
    detailed_answer: 'Governed by Chapter IX (Rules 24 and 28) of the Foreign Exchange Management (Non-debt Instruments) Rules, 2019 and RBI Master Direction on Immovable Property in India:\n1. Permitted Real Estate: NRIs and OCIs are permitted to freely acquire any number of residential or commercial properties in India. No registration or approval with RBI is necessary.\n2. Strict Statutory Prohibition: Rule 24 explicitly states that an NRI or OCI SHALL NOT acquire any agricultural land, farm house, or plantation property in India by way of purchase. Doing so is an illegal transaction under FEMA.\n3. Inheritance Exception: An NRI or OCI may hold agricultural land, farm house, or plantation property if it was acquired by way of inheritance from a person who was resident in India or who had acquired it under foreign exchange law.\n4. Permitted Modes of Payment: Consideration must be paid out of:\n   - Funds received in India through normal banking channels by way of inward remittance from abroad; OR\n   - Funds held in NRE / FCNR(B) / NRO accounts maintained in accordance with FEMA.\n5. Prohibited Payment Modes: Payment cannot be made by traveller\'s cheque, foreign currency notes, cash, or crypto-assets.',
    applicability: 'Non-Resident Indians (NRIs) and Overseas Citizens of India (OCIs). Foreign nationals of non-Indian origin residing abroad cannot buy any property in India without RBI approval.',
    taxpayer_type: 'Individual',
    NRI_status: 'NRI / OCI',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Property must be residential or commercial (strictly non-agricultural).',
      'Payment must be made through banking channels or NRE/NRO/FCNR accounts.',
      'Buyer must comply with applicable state land ceiling and registration laws.'
    ],
    exceptions: [
      'Agricultural land, plantation property, or farm houses CANNOT be purchased. They can only be acquired by inheritance from a resident, or held if acquired when the person was an Indian resident.'
    ],
    thresholds: 'No statutory ceiling on the number of residential or commercial properties that may be purchased.',
    rates: 'Standard state stamp duty and registration charges apply as for resident buyers.',
    limits: 'Total prohibition on purchasing agricultural land, farm houses, and plantations.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '2019-10-17',
    source_type: 'Regulation',
    source_authority: 'Reserve Bank of India (RBI)',
    act_or_regulation: 'FEMA (Non-debt Instruments) Rules, 2019',
    section_rule_regulation: 'Rule 24, Rule 28, Chapter IX',
    circular_notification: 'Notification No. S.O. 3732(E) dated 17 October 2019',
    source_url: 'https://egazette.gov.in/WriteReadData/2019/213271.pdf',
    source_excerpt_or_summary: 'An NRI or an OCI may acquire by way of purchase any immovable property in India other than agricultural land/farm house/plantation property.',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'NO',
    keywords: ['buy property', 'agricultural land', 'farm house', 'plantation', 'commercial property', 'residential property', 'FEMA NDI Rules 2019', 'Rule 24', 'OCI'],
    related_faq_ids: ['REP-003', 'TDS-001', 'FEMA-ACC-001']
  },

  // 10. RESIDENTIAL STATUS DETERMINATION (INCOME TAX)
  {
    faq_id: 'RES-001',
    category: 'Residential Status',
    subcategory: 'Day-Count Rules, 120-Day Rule, and Deemed Residency',
    user_question: 'How is residential status determined for an NRI under Indian Income-tax law?',
    question_variations: [
      'How many days can an NRI stay in India without becoming a tax resident?',
      'What is the 182-day rule and 120-day rule for NRI tax status?',
      'What is Section 6(1A) Deemed Resident rule in India?',
      'Difference between ROR, RNOR, and Non-Resident under Income-tax Act'
    ],
    short_answer: 'Under Section 6 of the Income-tax Act, an individual is a Non-Resident if they stay in India for less than 182 days in the financial year (or less than 60 days if they were in India for 365+ days in the preceding 4 years). For Indian citizens or PIOs visiting India whose total Indian income exceeds ₹15 Lakhs, the threshold is reduced to 120 days. Under Section 6(1A), an Indian citizen with Indian income > ₹15 Lakhs who is not liable to tax in any other country is deemed to be a resident (RNOR).',
    detailed_answer: 'Residential status is evaluated afresh for each Financial Year (April 1 to March 31) under Section 6 of the Income-tax Act, 1961:\n1. Basic Resident Test (Section 6(1)):\n   - Condition A: Stay in India of 182 days or more during the FY; OR\n   - Condition B: Stay in India of 60 days or more during the FY AND 365 days or more during the 4 preceding FYs.\n2. Relaxations (Condition B 60 days replaced by 182 days):\n   - Indian citizen who leaves India during the FY for employment abroad or as a member of the crew of an Indian ship.\n   - Indian citizen or Person of Indian Origin (PIO) who resides abroad and visits India, IF their total income (other than income from foreign sources) is up to ₹15 Lakhs.\n3. The 120-Day Rule for Visiting Citizens/PIOs (Finance Act 2020):\n   - If total income from Indian sources exceeds ₹15 Lakhs, Condition B\'s 60-day threshold is replaced by 120 days. If stay is 120 days or more (but < 182 days) and 365+ days in 4 years, status is Resident but Not Ordinarily Resident (RNOR).\n4. Deemed Resident (Section 6(1A)):\n   - An Indian citizen having total income from Indian sources exceeding ₹15 Lakhs who is not liable to tax in any other country or territory by reason of domicile or residence (e.g. resident in zero-tax jurisdictions like UAE) is deemed to be an Indian resident, classified as RNOR under Section 6(6)(d).\n5. Tax Categories:\n   - Non-Resident (NR): Taxed ONLY on income received or accrued in India.\n   - RNOR: Taxed on Indian income + business income from a business controlled in India. Foreign income not taxed in India; no Schedule FA foreign asset reporting!\n   - ROR (Resident & Ordinarily Resident): Worldwide/global income is taxed in India; mandatory Schedule FA reporting.',
    applicability: 'All individuals having presence in India or foreign income/assets.',
    taxpayer_type: 'Individual',
    NRI_status: 'Non-Resident / RNOR / ROR',
    OCI_status: 'Applicable',
    resident_status: 'All',
    conditions: [
      'Day count includes the day of arrival and day of departure in India (calculated by passport immigration stamps).',
      'Financial year runs from April 1 to March 31.',
      'Income threshold of ₹15 Lakhs strictly excludes income from foreign sources.'
    ],
    exceptions: [
      'FEMA residential status is determined separately under Section 2(v) of FEMA based on intention of stay, not purely mathematical day count.'
    ],
    thresholds: 'Basic tests: 182 days; 60 days + 365 days in 4 years; 120 days for visiting citizens/PIOs with Indian income > ₹15 Lakhs; ₹15 Lakhs threshold for deemed residency.',
    rates: 'Determines scope of total income under Section 5.',
    limits: 'Day counts evaluated on a 365-day fiscal year basis.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '2020-04-01',
    source_type: 'Statute',
    source_authority: 'CBDT / Income Tax Department',
    act_or_regulation: 'Income-tax Act, 1961 (amended by Finance Act, 2020)',
    section_rule_regulation: 'Section 6(1), Section 6(1A), Section 6(6), Explanation 1(b)',
    circular_notification: 'CBDT Circular No. 13/2020 & Explanatory Memorandum to Finance Act 2020',
    source_url: 'https://incometaxindia.gov.in/pages/acts/income-tax-act.aspx',
    source_excerpt_or_summary: 'An individual is resident if in India for 182 days or 60 days + 365 days in 4 preceding years. For Indian citizens/PIOs visiting India with Indian income > ₹15L, the 60-day period is substituted by 120 days.',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'REVIEW',
    keywords: ['residential status', '182 days', '120 days', '60 days', 'deemed resident', 'Section 6(1A)', 'RNOR', 'ROR', '15 lakhs', 'Indian citizen', 'PIO'],
    related_faq_ids: ['FINC-001', 'FA-001', 'PAN-001']
  },

  // 11. FOREIGN ASSETS DISCLOSURE AND SCHEDULE FA
  {
    faq_id: 'FA-001',
    category: 'Foreign Assets & Accounts',
    subcategory: 'Schedule FA and Black Money Act Reporting',
    user_question: 'Do NRIs need to disclose their foreign bank accounts and assets in Indian tax returns?',
    question_variations: [
      'Does an NRI have to file Schedule FA in Indian ITR?',
      'Are foreign bank accounts reportable by non-residents in India?',
      'Does Black Money Act penalty apply to NRIs holding foreign assets?',
      'Do RNORs need to report foreign assets in India?'
    ],
    short_answer: 'No. NRIs (Non-Residents) and RNORs (Resident but Not Ordinarily Resident) are completely EXEMPT from disclosing their foreign bank accounts, shares, real estate, or foreign assets in Schedule FA of the Indian Income Tax Return. Schedule FA reporting is strictly mandatory ONLY for taxpayers who qualify as Resident and Ordinarily Resident (ROR) under Section 6 of the Income-tax Act.',
    detailed_answer: 'Governed by the Fourth and Fifth Provisos to Section 139(1) of the Income-tax Act, 1961 read with the Black Money (Undisclosed Foreign Income and Assets) and Imposition of Tax Act, 2015:\n1. Mandatory Reporting Exclusively for ROR: Any person who is a Resident and Ordinarily Resident (ROR) in India who holds any foreign asset (including foreign bank accounts, shares, ESOPS, immovable property, or signing authority in foreign accounts) is legally required to file an Indian ITR and disclose all such assets in Schedule FA, even if their total taxable income is below the basic exemption threshold.\n2. Complete Exemption for NRIs & RNORs: A genuine Non-Resident (NR) or RNOR is NOT required to disclose foreign assets or overseas bank accounts in Schedule FA.\n3. Returning NRIs Warning: When an NRI returns to India permanently and transitions from RNOR to ROR (typically after 2 to 3 financial years), they must immediately begin reporting all global assets in Schedule FA. Failure to disclose foreign assets by an ROR attracts a severe penalty of ₹10,00,000 (Ten Lakh Rupees) under Section 43 of the Black Money Act, along with potential prosecution.',
    applicability: 'Taxpayers filing Indian Income Tax Returns holding overseas assets.',
    taxpayer_type: 'Individual / HUF',
    NRI_status: 'Non-Resident / RNOR',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Exemption applies only while residential status remains Non-Resident or RNOR.',
      'If status becomes ROR, disclosure in Schedule FA becomes mandatory by July 31 of assessment year.'
    ],
    exceptions: [
      'Taxpayers who become ROR must report all foreign assets, even minor employee stock options (ESOPs) or foreign bank accounts with minimal balances.'
    ],
    thresholds: 'Nil for NRIs/RNORs; for RORs, ₹10 Lakh penalty under Section 43 Black Money Act for non-disclosure.',
    rates: 'Penalty of ₹10 Lakhs plus 30% tax and 90% penalty under Black Money Act for undisclosed income.',
    limits: 'NRIs & RNORs have 0 disclosure obligation for overseas assets in Schedule FA.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '2015-07-01',
    source_type: 'Statute',
    source_authority: 'CBDT / Income Tax Department',
    act_or_regulation: 'Income-tax Act, 1961 & Black Money Act, 2015',
    section_rule_regulation: 'Section 139(1) Provisos, Schedule FA, Section 43 Black Money Act',
    circular_notification: 'CBDT Instruction No. 02/2022 on Foreign Assets Disclosure',
    source_url: 'https://incometaxindia.gov.in/pages/acts/black-money-act.aspx',
    source_excerpt_or_summary: 'Fourth and Fifth Provisos to Section 139(1) mandate return filing and foreign asset disclosure for persons being resident and ordinarily resident in India. Non-residents and RNORs are not covered.',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'NO',
    keywords: ['Schedule FA', 'foreign assets', 'foreign bank account', 'Black Money Act', 'ROR', 'RNOR', 'Section 139(1)', 'Section 43 penalty'],
    related_faq_ids: ['RES-001', 'FINC-001']
  },

  // 12. TAXABILITY OF FOREIGN INCOME
  {
    faq_id: 'FINC-001',
    category: 'Foreign Income Taxability',
    subcategory: 'Scope of Total Income under Section 5',
    user_question: 'Is foreign salary, rental, or overseas investment income taxable in India for an NRI?',
    question_variations: [
      'Does an NRI have to pay Indian income tax on income earned outside India?',
      'Is foreign income exempt from tax in India for non-residents?',
      'If I earn salary in USA or Dubai, do I pay tax in India?',
      'Under what conditions is foreign income taxed in India?'
    ],
    short_answer: 'No. Under Section 5(2) of the Income-tax Act, 1961, an NRI is taxed in India ONLY on income that is received, deemed to be received, accrued, or deemed to accrue or arise in India. Foreign salary earned for services rendered outside India, foreign rental income, and capital gains on foreign assets are 100% EXEMPT from Indian income tax, provided the salary is not directly deposited into an Indian bank account.',
    detailed_answer: 'Governed by Section 5 of the Income-tax Act, 1961 (Scope of Total Income):\n1. Non-Resident (NR):\n   - Taxable: Income received or deemed to be received in India during the year; income accruing or arising or deemed to accrue or arise in India (e.g. Indian rental, Indian bank interest, capital gains on Indian property or shares).\n   - NOT Taxable: Income accruing or arising outside India and received outside India. Foreign salary, business profits abroad, foreign interest, foreign dividends, and overseas capital gains are completely exempt from Indian tax.\n2. Crucial Precaution on Salary Receipt: If foreign salary is credited directly by an overseas employer into a resident or Indian bank account, the tax department may argue it was "first received in India" under Section 5(2)(a). NRIs should always ensure foreign salary is credited into an overseas bank account first before being transferred to an Indian NRE/NRO account.\n3. Resident but Not Ordinarily Resident (RNOR):\n   - Taxable on Indian-sourced income PLUS income derived from a business controlled in India or profession set up in India.\n   - Pure foreign salary and passive foreign investments remain exempt in India.\n4. Resident and Ordinarily Resident (ROR):\n   - Worldwide/global income is taxable in India, subject to foreign tax credits under applicable DTAAs (Section 90/91).',
    applicability: 'All non-residents earning income from sources outside India.',
    taxpayer_type: 'Individual',
    NRI_status: 'Non-Resident',
    OCI_status: 'Applicable',
    resident_status: 'Non-Resident',
    conditions: [
      'Services must be rendered outside India.',
      'Income must accrue outside India and be received into an overseas bank account (not directly remitted to an Indian account by the employer/payer).'
    ],
    exceptions: [
      'If salary is paid by the Government of India to an Indian citizen for service outside India (Section 9(1)(iii)), it is deemed to accrue in India (subject to treaty provisions).'
    ],
    thresholds: 'Foreign income has zero taxable liability in India for genuine non-residents.',
    rates: '0% in India for non-resident on foreign source income.',
    limits: 'Exemption applies to all bona fide foreign income.',
    relevant_FY: 'FY 2024-25 / FY 2025-26',
    relevant_AY: 'AY 2025-26 / AY 2026-27',
    effective_from: '1962-04-01',
    source_type: 'Statute',
    source_authority: 'CBDT / Income Tax Department',
    act_or_regulation: 'Income-tax Act, 1961',
    section_rule_regulation: 'Section 5(2), Section 9',
    circular_notification: 'CBDT Circular No. 13/2017 & Circular No. 17/2017 on Salary Earned by Non-Resident Seafarers',
    source_url: 'https://incometaxindia.gov.in/pages/acts/income-tax-act.aspx',
    source_excerpt_or_summary: 'Subject to provisions of this Act, total income of a non-resident includes all income from whatever source derived which is received or deemed to be received in India or accrues or arises or is deemed to accrue or arise to him in India (Section 5(2)).',
    last_verified: '2026-09-20',
    review_status: 'VERIFIED',
    professional_review_required: 'NO',
    keywords: ['foreign income', 'foreign salary', 'Section 5', 'exempt', 'accrue outside India', 'overseas income', 'received in India', 'taxability'],
    related_faq_ids: ['RES-001', 'DTAA-001', 'FA-001']
  }
];
