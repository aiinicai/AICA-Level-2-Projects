# Statutory basis

Every routine in AuditLens exists because a provision requires it. This
document records the authority for each, so that a reviewer can check the
tool against the law rather than against its own documentation.

**Verify each of these against the bare Act, Rules and Order on
[mca.gov.in](https://www.mca.gov.in/) and the ICAI's pronouncements before
relying on this table.** Positions stated here are current to the best of
the author's knowledge as at September 2026 and are not a substitute for
reading the source.

---

## 1. Presentation — Schedule III to the Companies Act, 2013

| What the tool does | Authority |
| --- | --- |
| Maps every ledger to a Division I presentation head | Schedule III, Division I (companies applying the Companies (Accounting Standards) Rules, 2021) |
| Builds the Balance Sheet in the prescribed order and grouping | Schedule III, Division I, Part I |
| Builds the Statement of Profit and Loss | Schedule III, Division I, Part II |
| Refuses to map a ledger it cannot classify, and reports the rupee value sitting unclassified | No authority requires this; it exists because a silently mis-mapped ledger appears on the face of the financial statements |

Division II applies to companies preparing Ind AS financial statements and
Division III to non-banking financial companies. **AuditLens implements
Division I only.** The head list in `schedule3.py` would need replacing for
either of the others; the engine around it would not.

## 2. The eleven ratios

Inserted into Schedule III by the Ministry of Corporate Affairs by
notification **G.S.R. 207(E) dated 24 March 2021**, applicable to financial
statements for the financial year commencing on or after **1 April 2021**.

The ratios, in the order the Schedule lists them, with the numerator and
denominator the tool uses:

| # | Ratio | Numerator | Denominator |
| --- | --- | --- | --- |
| a | Current Ratio | Current assets | Current liabilities |
| b | Debt-Equity Ratio | Total debt | Shareholders' equity |
| c | Debt Service Coverage Ratio | Earnings available for debt service | Debt service |
| d | Return on Equity | Profit after tax | Average shareholders' equity |
| e | Inventory Turnover Ratio | Cost of goods sold | Average inventory |
| f | Trade Receivables Turnover Ratio | Net credit sales | Average trade receivables |
| g | Trade Payables Turnover Ratio | Net credit purchases | Average trade payables |
| h | Net Capital Turnover Ratio | Net sales | Working capital |
| i | Net Profit Ratio | Profit after tax | Net sales |
| j | Return on Capital Employed | Earnings before interest and tax | Capital employed |
| k | Return on Investment | Income from investments | Cost of investments |

Two points on which the Schedule leaves room, and where the tool records
the basis it used rather than hiding the choice:

- **Averages.** Turnover ratios use the average of the opening and closing
  balances where a comparative is supplied, and the closing balance
  otherwise. Every result carries the basis used.
- **Credit proportion.** Net credit sales and net credit purchases are not
  derivable from a trial balance. The engagement team supplies the
  proportion; the default of 1.0 treats the whole of revenue as credit
  sales and must be overridden where that is not the case.

Schedule III requires an **explanation in the notes for any movement
exceeding 25 per cent** against the preceding year. The tool flags them and
drafts the note; the commercial reason has to come from management.

## 3. Journal entry testing

**SA 240, "The Auditor's Responsibilities Relating to Fraud in an Audit of
Financial Statements"**, requires the auditor to test the appropriateness of
journal entries recorded in the general ledger, because management override
of controls is a risk in every entity.

| Routine | Why the population is selected |
| --- | --- |
| Round-sum entries | Genuine transactions rarely settle on an exact multiple of a lakh |
| Non-working day postings | Entries outside the normal processing calendar |
| Period-end material entries | SA 240 identifies entries at the close of the period as higher risk |
| Back-dated entries | A long lag between the posting date and the recording date |
| Seldom-used account combinations | A debit/credit pairing outside the entity's normal process |
| Infrequent posting users | Postings by a user who does not normally post |
| Benford first-digit distribution | An analytical indicator over the whole population |

**A flag is a selection, not a finding.** The tool never characterises an
entry as irregular, and the prompt that drafts the enquiry letter forbids
the words "fraud", "irregularity", "manipulation" and "override".

Benford conformity is interpreted on the conventional mean-absolute-deviation
bands (Nigrini): below 0.006 close conformity; 0.006 to 0.012 acceptable;
0.012 to 0.015 marginal; above 0.015 non-conforming. These are a convention
of the literature, not a requirement of any standard.

## 4. Materiality

**SA 320, "Materiality in Planning and Performing an Audit"**, requires the
auditor to determine materiality for the financial statements as a whole,
performance materiality, and the amount below which misstatements are clearly
trivial.

**The standard prescribes no percentages.** The benchmark ranges the tool
offers are the commonly applied ones, and the tool records the rate used and
flags any rate outside the customary range as requiring documented
justification. The auditor determines materiality; the tool does the
arithmetic and keeps the record.

## 5. Sampling

**SA 530, "Audit Sampling"**, requires a method under which every sampling
unit has a chance of selection. Monetary unit sampling is implemented, with:

- items at or above the sampling interval selected in full as individually
  significant;
- the remainder selected systematically from a random start;
- the seed and the random start recorded, so a reviewer can re-perform the
  selection exactly.

Where the resulting sample would cover more than a quarter of the population,
the tool says that sampling is not an efficient response and points to
controls reliance, substantive analytical procedures under **SA 520**, or
stratification. An arithmetically correct sample that cannot be performed is
of no use to an engagement team.

## 6. CARO 2020

The **Companies (Auditor's Report) Order, 2020** was issued on **25 February
2020** and applies to statutory audits for financial years commencing on or
after 1 April 2021. Paragraph 3 carries **twenty-one clauses**, all of which
appear in the checklist.

Applicability is tested against paragraph 1(2): one person companies, small
companies, banking companies, insurance companies and companies licensed
under section 8 are outside the Order, as are private companies within all
three of the limits in paragraph 1(2)(iv) — paid-up capital plus reserves not
exceeding Rs 1 crore, borrowings not exceeding Rs 1 crore, and revenue not
exceeding Rs 10 crore — provided they are not a holding or subsidiary of a
public company.

**No clause is ever concluded.** The tool states what the books evidence and
what the auditor should obtain. Every clause is returned with an empty
auditor response.

## 7. What the tool deliberately does not do

- It does not form or suggest an audit opinion.
- It does not conclude on any CARO clause.
- It does not determine materiality; it computes it from the auditor's
  chosen benchmark and rate.
- It does not implement Ind AS (Schedule III, Division II) or NBFC
  presentation (Division III).
- It does not assert a commercial reason for any movement in a ratio.
- It does not verify the existence, completeness or valuation of any
  balance. It analyses what the books say; the audit evidence is the
  auditor's to obtain.
