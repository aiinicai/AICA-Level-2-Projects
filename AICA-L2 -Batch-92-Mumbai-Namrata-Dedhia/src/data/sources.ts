import { SourceRecord } from '../types/advisory';

export const OFFICIAL_SOURCES: SourceRecord[] = [
  {
    source_id: 'SRC-ITA-1961',
    authority: 'CBDT / Income Tax Department',
    source_title: 'Income-tax Act, 1961 (as amended by Finance (No. 2) Act, 2024)',
    source_type: 'Central Primary Legislation',
    url: 'https://incometaxindia.gov.in/pages/acts/income-tax-act.aspx',
    publication_date: '1961-09-13',
    effective_date: '1962-04-01',
    subject: 'Direct taxation of income, residential status (Sec 6), scope of total income (Sec 5), TDS (Sec 195/197), capital gains, PAN-Aadhaar (Sec 139AA), DTAA (Sec 90).',
    last_checked: '2026-09-20',
    notes: 'Updated with latest amendments under Finance (No. 2) Act, 2024 for capital gains rates (12.5% unlisted/real estate) and indexation adjustments.'
  },
  {
    source_id: 'SRC-FEMA-1999',
    authority: 'Ministry of Law & Justice / RBI',
    source_title: 'Foreign Exchange Management Act, 1999 (FEMA 42 of 1999)',
    source_type: 'Primary Central Legislation',
    url: 'https://rbi.org.in/Scripts/BS_ViewFemaActs.aspx',
    publication_date: '1999-12-29',
    effective_date: '2000-06-01',
    subject: 'Cross-border foreign exchange management, residential status under FEMA Section 2(v), penalties under Section 13.',
    last_checked: '2026-09-20',
    notes: 'Statutory basis for non-debt instrument investments, deposit accounts, and asset remittances.'
  },
  {
    source_id: 'SRC-RBI-MD-REMIT',
    authority: 'Reserve Bank of India (RBI)',
    source_title: 'Master Direction – Remittance of Assets (FED Master Direction No. 13/2015-16)',
    source_type: 'RBI Master Direction',
    url: 'https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=10204',
    publication_date: '2016-01-01',
    effective_date: '2016-01-01',
    subject: 'Remittance facilities for NRIs/PIOs from NRO account up to USD 1,000,000 per financial year; sale of property remittance limits; inheritance remittance; Form 15CA/15CB verification.',
    last_checked: '2026-09-20',
    notes: 'Authoritative rules for NRO account outward remittances.'
  },
  {
    source_id: 'SRC-RBI-MD-DEPOSIT',
    authority: 'Reserve Bank of India (RBI)',
    source_title: 'Master Direction – Deposits and Accounts (FED Master Direction No. 14/2015-16) & FEMA 5(R)/2016-RB',
    source_type: 'RBI Master Direction & Regulations',
    url: 'https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=10202',
    publication_date: '2016-04-01',
    effective_date: '2016-04-01',
    subject: 'Non-Resident Ordinary (NRO) Rupee Account, Non-Resident External (NRE) Rupee Account, Foreign Currency Non-Resident (Bank) FCNR(B) Account schemes. Mandatory re-designation on change of resident status.',
    last_checked: '2026-09-20',
    notes: 'Governs immediate re-designation of resident accounts to NRO upon leaving India.'
  },
  {
    source_id: 'SRC-FEMA-NDI-2019',
    authority: 'Ministry of Finance (DEA) / RBI',
    source_title: 'Foreign Exchange Management (Non-debt Instruments) Rules, 2019 (Rules 24, 28, Chapter IX)',
    source_type: 'Central Government Rules',
    url: 'https://egazette.gov.in/WriteReadData/2019/213271.pdf',
    publication_date: '2019-10-17',
    effective_date: '2019-10-17',
    subject: 'Acquisition and transfer of immovable property in India by NRIs/OCIs; permission for residential/commercial property; strict statutory prohibition on agricultural land, plantation property, farm houses.',
    last_checked: '2026-09-20',
    notes: 'Replaced FEMA 21/2000. Core statutory authority on property purchase.'
  },
  {
    source_id: 'SRC-CBDT-PAN-AADHAAR',
    authority: 'CBDT / Income Tax Department',
    source_title: 'CBDT Notification No. 37/2017/F. No. 370133/6/2017-TPL & Circular No. 03/2023',
    source_type: 'CBDT Notification & Circular',
    url: 'https://incometaxindia.gov.in/communications/notification/notification37_2017.pdf',
    publication_date: '2017-05-11',
    effective_date: '2017-07-01',
    subject: 'Exemption from Aadhaar-PAN linking under Section 139AA for non-resident individuals under Income-tax Act. Consequences of inoperative PAN under Rule 114AAA.',
    last_checked: '2026-09-20',
    notes: 'Confirms that individuals who are Non-Residents under Section 6 are explicitly exempt from mandatory Aadhaar quoting/linking.'
  },
  {
    source_id: 'SRC-IT-RULE-21AB',
    authority: 'CBDT / Income Tax Department',
    source_title: 'Income Tax Rules, 1962 – Rule 21AB & Form 10F (Electronic Filing Order 2023)',
    source_type: 'Income Tax Rules',
    url: 'https://incometaxindia.gov.in/rules/income-tax-rules-1962.aspx',
    publication_date: '2012-09-17',
    effective_date: '2013-04-01',
    subject: 'Mandatory documentation for claiming DTAA relief under Section 90(4): Tax Residency Certificate (TRC) + Form 10F (electronic filing on portal).',
    last_checked: '2026-09-20',
    notes: 'Electronic Form 10F is mandatory for non-residents where TRC does not contain all prescribed details.'
  },
  {
    source_id: 'SRC-BLACK-MONEY-ACT',
    authority: 'Ministry of Finance / CBDT',
    source_title: 'Black Money (Undisclosed Foreign Income and Assets) and Imposition of Tax Act, 2015',
    source_type: 'Primary Central Legislation',
    url: 'https://incometaxindia.gov.in/pages/acts/black-money-act.aspx',
    publication_date: '2015-05-26',
    effective_date: '2015-07-01',
    subject: 'Reporting of undisclosed foreign assets, Schedule FA reporting obligations applicable to Resident & Ordinarily Residents (ROR). Immunity/non-applicability to Non-Residents and RNORs.',
    last_checked: '2026-09-20',
    notes: 'Non-residents and RNORs are not required to furnish Schedule FA for foreign assets.'
  }
];
