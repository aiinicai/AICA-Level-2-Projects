# Related Party Transactions Compliance Tracker

**AICA Level 2 Capstone Project | Batch 111, Pimpri Chinchwad**
**Author:** CA Narendrra V Arora (Membership No. 048714)

**Live app:** https://rpt-compliance-tracker.lovable.app
**Video walkthrough:** link to be added

---

## The problem

Related party transactions are among the most closely watched areas in Indian corporate governance. A company has to identify every related party transaction, make sure the audit committee, the board and, where required, the shareholders approved it before it happened, check that it was at a market price, and then disclose it correctly under Ind AS 24 and in Form AOC-2.

In practice this is done by hand: the ledger is exported from Tally, matched against a list of related parties, and checked line by line against minutes and approval registers. Listed companies face a second layer of rules under the SEBI listing regulations. The work is slow, error-prone and hard to evidence for the auditor.

## What the app does

Upload one Excel file (a Tally day book export plus the related party list and the approvals register), choose whether the company is **listed or unlisted**, and the app:

1. Identifies every related party transaction in the year.
2. Runs seven checks under the Companies Act, plus two extra checks under SEBI for listed companies.
3. Lists every exception with the amount, the finding and the section of law.
4. Tests prices against the same items bought or sold with unrelated parties.
5. Prepares the Ind AS 24 summary and Form AOC-2 (Parts 1 and 2).
6. Drafts an audit committee summary with AI, where AI writes only the words and every number comes from the calculation.

The file is processed in the browser and is not stored anywhere.

## How to use it

1. Open the live app and click **Load sample data**, or download the sample file, replace it with your own data and upload it.
2. Choose **Unlisted public company** or **Listed company**. You can switch at any time; results recalculate instantly.
3. Review the Overview, Exceptions, Transactions and Disclosures pages, and draft the audit committee summary.

## The checks

| Code | Check | Applies to |
|---|---|---|
| C1 | Identify related party transactions | Both |
| C2 | Audit committee approval on record and valid | Both |
| C3 | Approved limit not exceeded | Both |
| C4 | Price in line with unrelated parties (10% screening test) | Both |
| C5 | Board approval where Section 188 applies | Both |
| C6 | Shareholder approval above the Rule 15(3) limits | Both |
| C7 | Interested director stayed out of the decision | Both |
| L1 | Wider SEBI definition of related party | Listed only |
| L2 | Material transaction needs prior shareholder approval | Listed only |

Full rules, limits, legal sources and simplifications are in [RULES.md](RULES.md).

## Results on the sample data

The sample company, Sahyadri Precision Components Ltd, is fictitious. The same file gives different results depending on listing status:

| | Unlisted | Listed |
|---|---|---|
| Related party transactions | Rs 105.56 crore | Rs 115.76 crore |
| Related parties transacted with | 6 | 8 |
| Exceptions | 6 | 8 |

The two extra exceptions in listed mode: a promoter group transporter with no audit committee approval (related only under the SEBI definition), and purchases from a subsidiary that are ordinary course and at market price, and so need no shareholder approval under the Companies Act, but cross the SEBI materiality limit.

## How it was built

| Step | Tool | Output |
|---|---|---|
| 1. Rules written in plain English and checked against the law | Research and review | [RULES.md](RULES.md) |
| 2. Realistic dummy data with planted exceptions | Python (pandas) | `data/RPT_Sample_Upload.xlsx` |
| 3. Independent answer key, calculated separately from the app | Python | `data/RPT_Answer_Key.xlsx` |
| 4. Web app built from a detailed written specification | Lovable (React, TypeScript) | Live app, `app/` |
| 5. Audit committee summary | Lovable AI | Drafted from computed figures only |
| 6. Acceptance test: the app's results compared with the answer key | Built into the app | 24 of 24 tests passed; 37 of 37 automated tests passed, including real Excel dates |

Claude (Anthropic) was used as a build assistant for research, data generation, the specification and testing.

**Design principle:** every number is produced by code that can be audited (`src/lib/rpt.ts`). AI is used only to put those numbers into words.

## Folder contents

| Path | Contents |
|---|---|
| `README.md` | This file |
| `RULES.md` | Checks, limits, legal sources and simplifications |
| `data/RPT_Sample_Upload.xlsx` | Sample upload file (fictitious company) |
| `data/RPT_Answer_Key.xlsx` | Expected results for both modes |
| `scripts/gen_rpt.py` | Generates the sample data and the answer key |
| `prompts/lovable_build_prompt.md` | The specification given to Lovable |
| `app/src/` | Core source code of the web app: the parser, the rules, the checks, the acceptance test and the AI drafting function |
| `presentation/` | Presentation used in the video |

## Limitations and next steps

- Rules and limits were verified by the author on 20 November 2026; they must be checked against the current law before any real use, since they change (SEBI revised its materiality limits in 2025).
- Ordinary course of business is decided by the nature of the transaction; in practice it needs judgement.
- The market price test is a screening test, not a full arm's length analysis, and items without comparables are not tested.
- Hidden related parties (shared directors, addresses or PANs) are not detected.
- Next steps: read data directly from Tally through an MCP connector, add detection of hidden related parties, and keep an approval trail for each judgement.

## Legal sources relied on

All limits and rules were checked by the author on 20 November 2026 using the sources below. The primary texts govern; the commentaries were used to locate and interpret them.

**Primary law**

- Companies Act, 2013: Section 2(76) (related party), Section 177 (audit committee), Section 184 (disclosure of interest) and Section 188 (related party transactions), including the provisos as amended by the Companies (Amendment) Act, 2015 and the Companies (Amendment) Act, 2017
- Companies (Meetings of Board and its Powers) Rules, 2014: Rule 6 (audit committee), Rule 6A (omnibus approval) and Rule 15(3) (limits for shareholder approval), as amended by the Second Amendment Rules, 2019
- Companies (Appointment and Qualification of Directors) Rules, 2014: Rule 4(1), as amended in 2017
- Companies (Accounts) Rules, 2014: Rule 8(2) and Form AOC-2
- SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015: Regulation 2(1)(zb), Regulation 23 and Schedule XII, as amended by the SEBI (LODR) (Fifth Amendment) Regulations, 2025, effective 19 December 2025
- Ind AS 24, Related Party Disclosures

**Commentary and reference texts consulted**

- Indian Institute of Corporate Affairs, Independent Directors Databank: amendment to Rule 15 (2019) <https://www.independentdirectorsdatabank.in/newsletter/2020/01/3/127>
- AZB & Partners: amendment to threshold limits for related party transactions <https://www.azbpartners.com/bank/amendment-to-threshold-limits-for-related-party-transactions-by-a-public-company-amended/>
- ca2013.com: text of Rule 15 <https://ca2013.com/rule-15-companies-meetings-of-board-and-its-powers-rules2014/>, Rule 6 <https://ca2013.com/rule-6-companies-meetings-of-board-and-its-powers-rules2014/> and Section 188 <https://ca2013.com/188-related-party-transactions/>
- Indian Kanoon: text of Rule 6A <https://indiankanoon.org/doc/55344461/>
- TaxGuru: omnibus approval under Rule 6A <https://taxguru.in/company-law/omnibus-approval-related-party-transaction-companies-act-2013.html>
- LexComply: Section 188 related party transactions <https://lexcomply.com/feeds/section-188-related-party-transactions>
- Treelife: related party transactions under Section 188 <https://treelife.in/compliance/related-party-transactions-section-188/>
- RSM India: Related Party Transactions, note on regulatory and practical considerations <https://www.rsm.global/india/sites/default/files/media/thumbnails/RSM%20India%20Publication%20-%20Related%20Party%20Transactions%20-%20Note%20on%20Regulatory%20and%20Practical%20Considerations.pdf>
- KPMG India: related party transactions, recent developments (December 2025) <https://assets.kpmg.com/content/dam/kpmgsites/in/pdf/2025/12/chapter-1-related-party-transactions-recent-developments.pdf.coredownload.pdf>
- Maheshwari & Co: SEBI LODR Fifth Amendment and the revised materiality framework <https://www.maheshwariandco.com/press-release/sebi-notifies-fifth-amendment-to-lodr-revised-materiality-framework-for-related-party-transactions/>
- Vinod Kothari Consultants: SEBI's revised related party transaction norms <https://vinodkothari.com/2025/11/sebi-approves-relaxed-norms>
- KNAV: related party transactions under the SEBI lens <https://in.knavcpa.com/insights/related-party-transactions-under-sebi-lens-your-questions-answered/>

## Disclaimer

This is a demonstration project built for the ICAI AICA Level 2 course. All company names, people and figures are fictitious. It is not legal advice.
