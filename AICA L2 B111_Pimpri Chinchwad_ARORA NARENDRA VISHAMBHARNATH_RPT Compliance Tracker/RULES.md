# Rules and limits

This file sets out every check the app performs, the limit it uses and the legal source. Limits are kept as settings in `src/lib/rules.ts`, not buried in the code, so they can be updated when the law changes.

**Status of limits:** all limits were verified by the author on 20 November 2026 against the sources listed at the end. Always confirm against the current text of the law before relying on the output.

## Scope

| Mode | Law applied | Related parties in scope |
|---|---|---|
| Unlisted public company (with an audit committee) | Companies Act, 2013 and the Companies (Meetings of Board and its Powers) Rules, 2014 | Related parties under Section 2(76) |
| Listed company | Companies Act, plus SEBI (LODR) Regulations, 2015 | Section 2(76) parties, plus promoter group entities and holders of 10% or more under Regulation 2(1)(zb) |

The financial year under review is read from the uploaded file. Only transactions inside that year are tested.

## Checks

| Code | Check | Exception raised when | Source |
|---|---|---|---|
| C1 | Identify related party transactions | Not an exception. A transaction is a related party transaction when the party appears on the related party list in scope | Sec 2(76) Companies Act; Reg 2(1)(zb) LODR in listed mode |
| C2 | Audit committee approval | A transaction is not covered by a valid audit committee approval (approved on or before the transaction date, and the date falls within the validity period) | Sec 177(4)(iv); Reg 23(2) in listed mode |
| C3 | Approved limit | Total transactions with the party for that nature, within the approval's validity, exceed the approved limit | Sec 177(4)(iv), Rule 6A |
| C4 | Market price | The average rate with the related party is more than 10% worse for the company than the average rate with unrelated parties for the same item | Screening test for the Sec 188 arm's length condition (our parameter, not a legal limit) |
| C5 | Board approval | Section 188 applies (transaction outside the ordinary course of business, or fails C4) and there is no board approval | Sec 188(1) |
| C6 | Shareholder approval | Section 188 applies, the yearly total crosses the Rule 15(3) limit, and there is no shareholder resolution | Sec 188(1), Rule 15(3) |
| C7 | Interested director | The board approved the transaction but the interested director did not stay out of the decision | Sec 184(2) |
| L1 | Wider SEBI definition (listed only) | Not an exception. Promoter group entities and holders of 10% or more come into scope, so C2 and C3 apply to them | Reg 2(1)(zb) LODR |
| L2 | Material transaction (listed only) | The yearly total with one party exceeds the SEBI materiality limit and there is no prior shareholder approval | Reg 23(4) and Schedule XII LODR |

## Limits

| Limit | Value used | Source | Status |
|---|---|---|---|
| Rule 15(3)(a)(i), (iii), (iv): goods, leasing, services (Sec 188(1)(a), (c), (d)) | 10% or more of standalone turnover, per the audited accounts of the preceding year; transactions taken individually or together with earlier ones in the year | Companies (Meetings of Board and its Powers) Second Amendment Rules, 2019 | Verified by the author, 20 Nov 2026 |
| Rule 15(3)(a)(ii): sale or purchase of property (Sec 188(1)(b)) | 10% or more of net worth, per the audited accounts of the preceding year; same year-total basis | Same | Verified by the author, 20 Nov 2026 |
| Rule 15(3)(b): office or place of profit (Sec 188(1)(f)) | Monthly remuneration exceeding Rs 2.5 lakh (strictly above; an absolute amount) | Same | Verified by the author, 20 Nov 2026 |
| Resolution under Sec 188 | Ordinary resolution; a member who is a related party for that contract does not vote, except where 90% or more of members by number are relatives of promoters or related parties | Sec 188(1) first to third provisos, as amended in 2015 and 2017 | Verified by the author, 20 Nov 2026 |
| Omnibus approval (Rule 6A) | Valid for a period not exceeding one financial year; Rs 1 crore per transaction where the need cannot be foreseen; not available for selling or disposing of the undertaking. The app tests the approval's dates and limit, not the one-year maximum or the Rs 1 crore cap | Rule 6A | Verified by the author, 20 Nov 2026 |
| SEBI materiality (Schedule XII) | 10% of consolidated turnover up to Rs 20,000 crore; Rs 2,000 crore plus 5% of turnover above that up to Rs 40,000 crore; Rs 3,000 crore plus 2.5% above that, capped at Rs 5,000 crore. Effective 19 December 2025. Brand usage or royalty payments have a separate 5% limit, not modelled | SEBI (LODR) (Fifth Amendment) Regulations, 2025 | Verified by the author, 20 Nov 2026 |
| SEBI related party definition | Section 2(76) and accounting standard related parties, plus any promoter or promoter group person or entity, and anyone holding 10% or more (directly or beneficially) at any time in the preceding financial year (20% before 1 April 2023) | Reg 2(1)(zb) LODR | Verified by the author, 20 Nov 2026 |
| Companies that must have an audit committee | Every listed public company; an unlisted public company with paid-up capital of Rs 10 crore or more, turnover of Rs 100 crore or more, or outstanding loans, borrowings, debentures and deposits exceeding Rs 50 crore in aggregate, per the latest audited accounts; unlisted joint ventures, wholly owned subsidiaries and dormant companies are exempt. The app assumes the company has an audit committee and does not test this | Sec 177(1); Rule 6 of the Meetings of Board Rules, read with Rule 4(1) of the Appointment and Qualification of Directors Rules, as amended in 2017 | Verified by the author, 20 Nov 2026 |
| Market price screening (C4) | Unfavourable deviation of more than 10% | Our test parameter | Not a legal limit |

## Simplifications in this MVP

1. Tally does not tag transactions by legal nature, so the upload file carries a `Nature` column.
2. The market price test (C4) is a screening test. It is not the legal definition of an arm's length price, and items with no unrelated comparable are not tested.
3. Ordinary course of business is decided by nature: sale or purchase of goods and availing or rendering of services are treated as ordinary course; leasing, property, and office or place of profit are not.
4. Exemptions for wholly owned subsidiaries and private companies are not modelled, and nor is underwriting (Sec 188(1)(g), Rule 15(3)(c)).
5. Form AOC-2 Part 2 uses the Rule 15(3) limits as the measure of materiality.
6. Related parties are matched by exact name; hidden related parties (shared directors, addresses or PANs) are not detected.
7. For an office or place of profit, the test uses the monthly amount booked under that nature. Remuneration includes salary, fees, commission, perquisites and rent-free accommodation, so all of these should be tagged to that nature in the upload.
8. The Rule 15(3) limits are tested per related party and per type of transaction, totalled over the year. The Rule does not say expressly whether transactions with different related parties of the same type should be pooled; testing per related party is the reading followed here. In the sample data, pooling would not change any result.
9. Approvals must be prior approvals. A transaction later ratified by the board or shareholders within three months under Section 188(3) still shows as an exception; the reviewer should note the ratification. Voting at the general meeting is recorded in the register but not tested.
10. The app assumes the company has an audit committee. For a company without one, checks C2 and C3 would not apply.

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
