import { StudioNote } from '../types';

export const INITIAL_SAMPLE_NOTES: StudioNote[] = [
  {
    id: 'note-1',
    title: 'written-submission-with-case-law',
    type: 'report',
    sourcesCount: 4,
    sourceNames: [
      'Union Budget 2025-26 Speech.pdf',
      'Finance Bill 2025 Clauses.docx',
      'Income Tax Appellate Guidelines.pdf',
      'Case Law Precedents (SC & HC).txt',
    ],
    promptUsed: 'Prepare a written submission with citations of landmark case laws regarding unexplained cash credits and additions under Section 68.',
    content: `# Written Submission with Landmark Case Law Precedents

**Before the Commissioner of Income Tax (Appeals)**  
**In the matter of:** Assessment Year 2024-25  
**Subject:** Ground of Appeal regarding addition under Section 68 / 115BBE

---

## 1. Statement of Material Facts
1. The Appellant is a registered tax-paying assessee maintaining audited books of accounts under Section 44AB.
2. During the course of assessment, the Assessing Officer made an addition under Section 68 without rebutting the identity, creditworthiness, and genuineness of transactions established through banking channels.

## 2. Core Legal Submissions & Grounding
- **Identity of Creditor:** The assessee provided PAN cards, IT returns, and bank statements of the investing entities.
- **Initial Onus Discharged:** As held by the Hon'ble Supreme Court in *CIT v. Lovely Exports (P) Ltd.* [216 CTR 195 (SC)], once identity is proved, no addition under Section 68 can be made in the hands of the company.
- **Rebuttal of Section 115BBE:** The peak credit theory and documented source of source fully demonstrate commercial genuineness.

## 3. Prayer & Relief Sought
It is humbly prayed that the unwarranted additions made under Section 68 be deleted in full in the interest of natural justice.`,
    createdAt: new Date(Date.now() - 9 * 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 9 * 86400000).toISOString(),
  },
  {
    id: 'note-2',
    title: 'The Taxation of Unexplained Cash Credits',
    type: 'study_guide',
    sourcesCount: 1,
    sourceNames: ['Income Tax Assessment Manual.pdf'],
    promptUsed: 'Synthesize the statutory framework and judicial tests for unexplained cash credits under Section 68 and enhanced tax rates under Section 115BBE.',
    content: `# The Taxation of Unexplained Cash Credits (Section 68 & 115BBE)

## Executive Summary of Statutory Provisions
Section 68 of the Income Tax Act casts a statutory onus upon the assessee to explain the nature and source of any sum credited in the books of account.

---

### The Three Golden Ingredients
To successfully discharge the burden of proof under Section 68, the taxpayer must establish:
1. **Identity** of the lender/investor (PAN, CIN, registration certificates).
2. **Creditworthiness / Capacity** of the creditor (Bank balances, Audited financials, Net worth).
3. **Genuineness** of the transaction (Banking channels, board resolutions, commercial rationale).

---

### Punitive Tax Rates under Section 115BBE
- **Base Tax Rate:** 60%
- **Surcharge:** 25% on tax (= 15%)
- **Health & Education Cess:** 4% on tax + surcharge (= 3%)
- **Effective Tax Rate:** **78%** + mandatory penalty under Section 271AAC (10%).

---
*Note: Always maintain verifiable banking trails to substantiate transactions.*`,
    createdAt: new Date(Date.now() - 237 * 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 237 * 86400000).toISOString(),
  },
  {
    id: 'note-3',
    title: 'Grounds of Appeal Against Section 144 Assessment',
    type: 'report',
    sourcesCount: 2,
    sourceNames: ['Assessment Order u-s 144.pdf', 'Show Cause Notice Response.docx'],
    promptUsed: 'Draft structured grounds of appeal challenging best judgment assessment passed ex-parte without providing reasonable opportunity of being heard.',
    content: `# Formal Grounds of Appeal

### Ground No. 1: Violation of Principles of Natural Justice
The learned Assessing Officer erred in passing the ex-parte assessment order under Section 144 without allowing reasonable and adequate time to respond to the final show-cause notice, thereby violating the fundamental principles of natural justice (*Audi Alteram Partem*).

### Ground No. 2: Arbitrary Best Judgment Additions
The learned AO erred in making arbitrary additions purely on conjectures and surmises without any incriminating material on record.

### Ground No. 3: Denial of Statutory Cross-Examination
The learned AO erred in relying upon third-party statements without providing opportunity for cross-examination despite explicit requests made by the Appellant.`,
    createdAt: new Date(Date.now() - 241 * 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 241 * 86400000).toISOString(),
  },
];
