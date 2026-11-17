import { StatutoryEvent } from '../types';

export const INITIAL_STATUTORY_EVENTS: StatutoryEvent[] = [
  // November 2026 Deadlines
  {
    id: 'ev-nov-07',
    title: 'TDS/TCS Payment for October',
    date: '2026-11-07',
    category: 'INCOME_TAX',
    description: 'Challan ITNS 281 payment for TDS/TCS deducted in October.',
    urgency: 'HIGH',
    portalLink: 'https://www.incometax.gov.in/iec/foportal/'
  },
  {
    id: 'ev-nov-10',
    title: 'GSTR-7 & GSTR-8 (TDS & TCS on GST)',
    date: '2026-11-10',
    category: 'GST',
    description: 'Filing of monthly return for Tax Deducted & Collected at Source under GST for Oct.',
    urgency: 'MEDIUM',
    portalLink: 'https://www.gst.gov.in/'
  },
  {
    id: 'ev-nov-11',
    title: 'GSTR-1 (Monthly Outward Supplies)',
    date: '2026-11-11',
    category: 'GST',
    description: 'Turnover > ₹5 Cr or monthly non-QRMP taxpayers outward supplies for October.',
    urgency: 'HIGH',
    portalLink: 'https://www.gst.gov.in/'
  },
  {
    id: 'ev-nov-13',
    title: 'GSTR-1 IFF (Invoice Furnishing Facility)',
    date: '2026-11-13',
    category: 'GST',
    description: 'Optional IFF upload for QRMP taxpayers for Month 1 of Quarter.',
    urgency: 'NORMAL',
    portalLink: 'https://www.gst.gov.in/'
  },
  {
    id: 'ev-nov-20',
    title: 'GSTR-3B Monthly Return',
    date: '2026-11-20',
    category: 'GST',
    description: 'Monthly summary return & tax payment for regular taxpayers for October.',
    urgency: 'HIGH',
    portalLink: 'https://www.gst.gov.in/'
  },
  {
    id: 'ev-nov-24',
    title: 'Guru Tegh Bahadur Ji Shaheedi Diwas (Punjab Gazetted Holiday)',
    date: '2026-11-24',
    category: 'PUNJAB_FESTIVAL',
    description: 'Martyrdom Day of Sri Guru Tegh Bahadur Ji observed across Punjab offices and banks.',
    urgency: 'NORMAL'
  },
  {
    id: 'ev-nov-30',
    title: 'ITR Filing - Transfer Pricing (Sec 92E)',
    date: '2026-11-30',
    category: 'INCOME_TAX',
    description: 'Filing of Income Tax Return for assesses subject to international transactions report.',
    urgency: 'HIGH',
    portalLink: 'https://www.incometax.gov.in/iec/foportal/'
  },

  // December 2026
  {
    id: 'ev-dec-07',
    title: 'TDS/TCS Payment for November',
    date: '2026-12-07',
    category: 'INCOME_TAX',
    description: 'Due date for depositing tax deducted/collected for Nov.',
    urgency: 'HIGH',
    portalLink: 'https://www.incometax.gov.in/iec/foportal/'
  },
  {
    id: 'ev-dec-11',
    title: 'GSTR-1 Monthly Return for November',
    date: '2026-12-11',
    category: 'GST',
    description: 'Details of outward supplies of goods or services for Nov.',
    urgency: 'HIGH',
    portalLink: 'https://www.gst.gov.in/'
  },
  {
    id: 'ev-dec-15',
    title: 'Advance Tax 3rd Installment (75%)',
    date: '2026-12-15',
    category: 'INCOME_TAX',
    description: 'Payment of 3rd installment of Advance Tax for FY 2026-27 (Corporate & Non-Corporate).',
    urgency: 'HIGH',
    portalLink: 'https://www.incometax.gov.in/iec/foportal/'
  },
  {
    id: 'ev-dec-20',
    title: 'GSTR-3B Return for November',
    date: '2026-12-20',
    category: 'GST',
    description: 'Monthly summary tax payment and ITC claim for Nov.',
    urgency: 'HIGH',
    portalLink: 'https://www.gst.gov.in/'
  },
  {
    id: 'ev-dec-25',
    title: 'Christmas Day (National Gazetted Holiday)',
    date: '2026-12-25',
    category: 'HOLIDAY',
    description: 'Gazetted Holiday across India.',
    urgency: 'NORMAL'
  },
  {
    id: 'ev-dec-26',
    title: 'Shaheedi Jor Mela - Fatehgarh Sahib (Day 1)',
    date: '2026-12-26',
    category: 'PUNJAB_FESTIVAL',
    description: 'Annual religious gathering commemorating the martyrdom of younger Sahibzadas.',
    urgency: 'NORMAL'
  },
  {
    id: 'ev-dec-27',
    title: 'Shaheedi Jor Mela - Fatehgarh Sahib (Day 2)',
    date: '2026-12-27',
    category: 'PUNJAB_FESTIVAL',
    description: 'Special observances and public gatherings in Punjab.',
    urgency: 'NORMAL'
  },
  {
    id: 'ev-dec-28',
    title: 'Shaheedi Jor Mela - Fatehgarh Sahib (Day 3)',
    date: '2026-12-28',
    category: 'PUNJAB_FESTIVAL',
    description: 'Concluding ceremonies at Gurdwara Fatehgarh Sahib.',
    urgency: 'NORMAL'
  },
  {
    id: 'ev-dec-31',
    title: 'GSTR-9 & GSTR-9C Annual Return',
    date: '2026-12-31',
    category: 'GST',
    description: 'Filing of Annual Return GSTR-9 and Reconciliation Statement 9C for previous FY.',
    urgency: 'HIGH',
    portalLink: 'https://www.gst.gov.in/'
  },
  {
    id: 'ev-dec-31-belated',
    title: 'Belated & Revised ITR for FY 2025-26',
    date: '2026-12-31',
    category: 'INCOME_TAX',
    description: 'Last date for filing belated or revised Income Tax Return u/s 139(4) and 139(5).',
    urgency: 'HIGH',
    portalLink: 'https://www.incometax.gov.in/iec/foportal/'
  },

  // January 2027 & Key Punjab Festivals
  {
    id: 'ev-jan-13',
    title: 'Lohri Festival (Punjab Special Celebration)',
    date: '2027-01-13',
    category: 'PUNJAB_FESTIVAL',
    description: 'Traditional harvest festival celebrated with joy and bonfires across Punjab.',
    urgency: 'NORMAL'
  },
  {
    id: 'ev-jan-14',
    title: 'Maghi / Makar Sankranti (Punjab Gazetted Holiday)',
    date: '2027-01-14',
    category: 'PUNJAB_FESTIVAL',
    description: 'Maghi Mela in Sri Muktsar Sahib; bank and public holiday in Punjab.',
    urgency: 'NORMAL'
  },
  {
    id: 'ev-jan-18',
    title: 'CMP-08 Quarterly Challan for Composition Dealers',
    date: '2027-01-18',
    category: 'GST',
    description: 'Quarterly payment of GST by taxpayers registered under composition scheme.',
    urgency: 'MEDIUM',
    portalLink: 'https://www.gst.gov.in/'
  },
  {
    id: 'ev-jan-22',
    title: 'GSTR-3B Quarterly Return (Punjab & North Category 1)',
    date: '2027-01-22',
    category: 'GST',
    description: 'Quarterly GSTR-3B for Punjab, Haryana, Chandigarh, Himachal Pradesh.',
    urgency: 'HIGH',
    portalLink: 'https://www.gst.gov.in/'
  },
  {
    id: 'ev-jan-26',
    title: 'Republic Day (National Holiday)',
    date: '2027-01-26',
    category: 'HOLIDAY',
    description: 'National Gazetted Holiday across all courts, banks and government offices.',
    urgency: 'HIGH'
  },
  {
    id: 'ev-jan-31',
    title: 'TDS Quarterly Return Q3 (Form 24Q, 26Q, 27Q)',
    date: '2027-01-31',
    category: 'INCOME_TAX',
    description: 'Quarterly statement of tax deducted at source for Quarter ended 31st December.',
    urgency: 'HIGH',
    portalLink: 'https://www.tdscpc.gov.in/'
  },

  // Indian National & Gazetted Holidays (Central Govt & National Observances 2026-2027)
  {
    id: 'gh-jan-23-2026',
    title: 'Netaji Subhas Chandra Bose Jayanti (Parakram Diwas)',
    date: '2026-01-23',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Observance commemorating the birth anniversary of Netaji Subhas Chandra Bose.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-jan-26',
    title: 'Republic Day (National Gazetted Holiday)',
    date: '2026-01-26',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday commemorating the Constitution of India. All banks, courts and offices closed.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-feb-15',
    title: 'Maha Shivratri (Indian Gazetted Holiday)',
    date: '2026-02-15',
    category: 'GAZETTED_HOLIDAY',
    description: 'Central Government Gazetted Holiday across India for Maha Shivratri celebrations.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-mar-04',
    title: 'Holi (Indian Gazetted Holiday)',
    date: '2026-03-04',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Festival of Colors - Gazetted Holiday across all offices and financial institutions.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-mar-21',
    title: 'Id-ul-Fitr / Ramzan Id (Indian Gazetted Holiday)',
    date: '2026-03-21',
    category: 'GAZETTED_HOLIDAY',
    description: 'Gazetted Holiday marking the culmination of the holy month of Ramzan.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-mar-23',
    title: 'Shaheedi Diwas / Martyrs Day (Bhagat Singh, Rajguru & Sukhdev)',
    date: '2026-03-23',
    category: 'GAZETTED_HOLIDAY',
    description: 'National & Punjab State Holiday honoring Shaheed Bhagat Singh, Rajguru, and Sukhdev.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-mar-26',
    title: 'Ram Navami (Indian Gazetted Holiday)',
    date: '2026-03-26',
    category: 'GAZETTED_HOLIDAY',
    description: 'Central Government Gazetted Holiday celebrating the birth of Lord Rama.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-mar-31',
    title: 'Mahavir Jayanti (Indian Gazetted Holiday)',
    date: '2026-03-31',
    category: 'GAZETTED_HOLIDAY',
    description: 'Birth anniversary of Bhagwan Mahavira, 24th Tirthankara of Jainism.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-apr-03',
    title: 'Good Friday (Indian Gazetted Holiday)',
    date: '2026-04-03',
    category: 'GAZETTED_HOLIDAY',
    description: 'Gazetted Holiday observed across all banks, financial institutions and government offices.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-apr-14',
    title: 'Dr. B.R. Ambedkar Jayanti & Vaisakhi (National Holiday)',
    date: '2026-04-14',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday commemorating Dr. B.R. Ambedkar Jayanti and Vaisakhi harvest festival.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-may-01',
    title: 'Buddha Purnima (Indian Gazetted Holiday)',
    date: '2026-05-01',
    category: 'GAZETTED_HOLIDAY',
    description: 'Commemorating the birth, enlightenment, and death of Gautama Buddha.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-may-27',
    title: 'Id-ul-Zuha / Bakrid (Indian Gazetted Holiday)',
    date: '2026-05-27',
    category: 'GAZETTED_HOLIDAY',
    description: 'Gazetted Holiday for Eid al-Adha observed nationwide.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-jun-26',
    title: 'Muharram (Indian Gazetted Holiday)',
    date: '2026-06-26',
    category: 'GAZETTED_HOLIDAY',
    description: 'Gazetted Holiday commemorating the martyrdom of Imam Hussain (Ashura).',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-aug-15',
    title: 'Independence Day (National Gazetted Holiday)',
    date: '2026-08-15',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday celebrating Indian Independence. All offices and markets closed.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-aug-26',
    title: 'Milad-un-Nabi / Id-e-Milad (Indian Gazetted Holiday)',
    date: '2026-08-26',
    category: 'GAZETTED_HOLIDAY',
    description: 'Birthday of Prophet Muhammad (SAW) - Central Government Gazetted Holiday.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-aug-28',
    title: 'Raksha Bandhan (National & Restricted Holiday)',
    date: '2026-08-28',
    category: 'GAZETTED_HOLIDAY',
    description: 'Traditional festival celebrated nationwide across India.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-sep-04',
    title: 'Janmashtami (Indian Gazetted Holiday)',
    date: '2026-09-04',
    category: 'GAZETTED_HOLIDAY',
    description: 'Gazetted Holiday celebrating the birth of Lord Krishna.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-oct-02',
    title: "Mahatma Gandhi's Birthday (National Gazetted Holiday)",
    date: '2026-10-02',
    category: 'GAZETTED_HOLIDAY',
    description: 'Gandhi Jayanti - National Gazetted Holiday observed across all government and commercial establishments.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-oct-20',
    title: 'Dussehra / Vijay Dashami (Indian Gazetted Holiday)',
    date: '2026-10-20',
    category: 'GAZETTED_HOLIDAY',
    description: 'Vijayadashami celebrating victory of good over evil. National Gazetted Holiday.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-oct-26',
    title: 'Maharishi Valmiki Jayanti (Gazetted Holiday)',
    date: '2026-10-26',
    category: 'GAZETTED_HOLIDAY',
    description: 'Gazetted Holiday in Punjab and across North India honoring Adi Kavi Maharishi Valmiki.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-nov-08',
    title: 'Diwali / Deepavali (Indian Gazetted Holiday)',
    date: '2026-11-08',
    category: 'GAZETTED_HOLIDAY',
    description: 'Festival of Lights - Premier National Gazetted Holiday across India.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-nov-14',
    title: "Children's Day / Bal Diwas (National Holiday)",
    date: '2026-11-14',
    category: 'GAZETTED_HOLIDAY',
    description: "National Holiday / Bal Diwas commemorating the birth anniversary of Pandit Jawaharlal Nehru across India.",
    urgency: 'NORMAL'
  },
  {
    id: 'gh-nov-24',
    title: "Guru Nanak's Birthday / Gurpurab (Indian Gazetted Holiday)",
    date: '2026-11-24',
    category: 'GAZETTED_HOLIDAY',
    description: 'Prakash Utsav of Sri Guru Nanak Dev Ji - Central and Punjab Gazetted Holiday.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-nov-26',
    title: 'Constitution Day / Samvidhan Divas (National Observance)',
    date: '2026-11-26',
    category: 'GAZETTED_HOLIDAY',
    description: 'National observance commemorating the adoption of the Constitution of India.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-dec-25',
    title: 'Christmas Day (Indian Gazetted Holiday)',
    date: '2026-12-25',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday celebrated across all states and union territories.',
    urgency: 'NORMAL'
  },
  // 2027 National & Indian Gazetted Holidays
  {
    id: 'gh-jan-26-2027',
    title: 'Republic Day 2027 (National Gazetted Holiday)',
    date: '2027-01-26',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday across all courts, banks and government offices.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-mar-06-2027',
    title: 'Maha Shivratri 2027 (Indian Gazetted Holiday)',
    date: '2027-03-06',
    category: 'GAZETTED_HOLIDAY',
    description: 'Central Government Gazetted Holiday for Maha Shivratri.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-mar-22-2027',
    title: 'Holi 2027 (Indian Gazetted Holiday)',
    date: '2027-03-22',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Festival of Colors - Gazetted Holiday.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-mar-26-2027',
    title: 'Good Friday 2027 (Indian Gazetted Holiday)',
    date: '2027-03-26',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Bank and Public Gazetted Holiday.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-apr-14-2027',
    title: 'Dr. B.R. Ambedkar Jayanti & Vaisakhi 2027 (National Holiday)',
    date: '2027-04-14',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday across India and Punjab.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-apr-19-2027',
    title: 'Mahavir Jayanti 2027 (Indian Gazetted Holiday)',
    date: '2027-04-19',
    category: 'GAZETTED_HOLIDAY',
    description: 'Central Government Gazetted Holiday.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-may-20-2027',
    title: 'Buddha Purnima 2027 (Indian Gazetted Holiday)',
    date: '2027-05-20',
    category: 'GAZETTED_HOLIDAY',
    description: 'Central Government Gazetted Holiday.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-aug-15-2027',
    title: 'Independence Day 2027 (National Gazetted Holiday)',
    date: '2027-08-15',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday across India.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-oct-02-2027',
    title: 'Gandhi Jayanti 2027 (National Gazetted Holiday)',
    date: '2027-10-02',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday honoring Mahatma Gandhi.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-oct-09-2027',
    title: 'Dussehra / Vijay Dashami 2027 (Indian Gazetted Holiday)',
    date: '2027-10-09',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday across India.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-oct-29-2027',
    title: 'Diwali / Deepavali 2027 (Indian Gazetted Holiday)',
    date: '2027-10-29',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday across India.',
    urgency: 'NORMAL'
  },
  {
    id: 'gh-nov-14-2027',
    title: "Children's Day & Guru Nanak Jayanti 2027 (National Holiday)",
    date: '2027-11-14',
    category: 'GAZETTED_HOLIDAY',
    description: "Children's Day (Bal Diwas) and Gurpurab of Sri Guru Nanak Dev Ji.",
    urgency: 'NORMAL'
  },
  {
    id: 'gh-dec-25-2027',
    title: 'Christmas Day 2027 (Indian Gazetted Holiday)',
    date: '2027-12-25',
    category: 'GAZETTED_HOLIDAY',
    description: 'National Gazetted Holiday across India.',
    urgency: 'NORMAL'
  }
];

export const GOV_PORTALS = [
  {
    name: 'Income Tax e-Filing',
    shortName: 'ITR Portal',
    url: 'https://www.incometax.gov.in/iec/foportal/',
    color: 'from-blue-600 to-indigo-700',
    badge: 'ITR / AIS / 26AS / Challans',
    description: 'Filing ITR-1 to 7, Tax Audits 3CA/3CB-3CD, AIS/TIS inspection, e-Verification, and 26AS.',
    tags: ['ITR Filing', 'Tax Audit', 'AIS/TIS', 'e-Pay Tax']
  },
  {
    name: 'GST Common Portal',
    shortName: 'GST Portal',
    url: 'https://www.gst.gov.in/',
    color: 'from-emerald-600 to-teal-700',
    badge: 'GSTR-1 / 3B / 9 / 9C',
    description: 'Monthly returns, ITC matching via GSTR-2B, registration, CMP-08, and refund applications.',
    tags: ['GSTR-1', 'GSTR-3B', 'ITC 2B', 'Refunds']
  },
  {
    name: 'MSME Udyam Registration',
    shortName: 'MSME Udyam',
    url: 'https://udyamregistration.gov.in/',
    color: 'from-amber-600 to-orange-700',
    badge: 'Micro, Small & Medium',
    description: 'New Udyam Registration, Certificate print, NIC classification, and priority sector banking.',
    tags: ['New Udyam', 'Print Certificate', 'Verify URN']
  },
  {
    name: 'Agriculture Infrastructure Fund',
    shortName: 'AIF Portal',
    url: 'https://agriinfra.dac.gov.in/',
    color: 'from-green-600 to-emerald-800',
    badge: '3% Subvention / CGTMSE',
    description: 'Ministry of Agriculture central scheme for post-harvest agri-infrastructure financing.',
    tags: ['3% Subvention', 'DPR Upload', 'Bank Sanction', 'Agri Infra']
  },
  {
    name: 'TRACES TDS Portal',
    shortName: 'TRACES',
    url: 'https://www.tdscpc.gov.in/',
    color: 'from-purple-600 to-indigo-800',
    badge: 'Form 16/16A / Conso Files',
    description: 'TDS default processing, justification reports, Form 16/16A download, and 26AS reconciliation.',
    tags: ['Form 16/16A', 'Justification', 'Conso File']
  },
  {
    name: 'MCA 21 Portal (RoC)',
    shortName: 'MCA 21 V3',
    url: 'https://www.mca.gov.in/',
    color: 'from-sky-600 to-blue-800',
    badge: 'Company / LLP Compliance',
    description: 'Annual ROC filings AOC-4, MGT-7A, DIR-3 KYC, charge creations, and company incorporations.',
    tags: ['AOC-4', 'MGT-7', 'DIR-3 KYC', 'LLP Form 11']
  },
  {
    name: 'e-Way Bill & e-Invoice',
    shortName: 'E-Way Bill',
    url: 'https://ewaybillgst.gov.in/',
    color: 'from-cyan-600 to-blue-700',
    badge: 'Goods In Transit',
    description: 'Generation of e-Way bills for inter-state and intra-state movement of goods.',
    tags: ['Part-A/B', 'Vehicle Update', 'Consolidated EWB']
  },
  {
    name: 'ICAI UDIN Portal',
    shortName: 'UDIN ICAI',
    url: 'https://udin.icai.org/',
    color: 'from-rose-600 to-red-700',
    badge: 'Mandatory for Certificates & Audits',
    description: 'Unique Document Identification Number generation for all ICAI member certificates & audits.',
    tags: ['UDIN Generation', 'Verify UDIN', 'Audit / Certificates']
  }
];

export const OFFICE_STAFF_MEMBERS = [
  'All Staff',
  'Aman Deep Singh',
  'Pooja Sharma',
  'Harpreet Kaur',
  'Rohit Kumar',
  'Manpreet Singh',
  'Simranjit Kaur'
];
