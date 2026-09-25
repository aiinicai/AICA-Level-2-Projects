# Cash Runway — Interface Layout Specification

**Specified by:** CFO · **Purpose:** what I want to see, where, and what it should be called
**Status:** LOCKED. This is the contract. Any change goes through a dated amendment at the bottom.

**Currency and format convention:** ₹ in Lakh / Crore, Indian digit grouping (₹ 4,25,00,000 → ₹ 4.25 Cr).
Dates as DD-Mmm-YY. All timestamps IST.

---

## Design principles

1. **One question per tab.** If I can't say in a sentence what a tab answers, it shouldn't be a tab.
2. The landing screen must answer **"am I fine?"** in five seconds without scrolling.
3. **Every number is clickable down to the entries behind it.** A figure I can't trace is a figure I can't quote.
4. **No number appears without its as-on date and its basis.** "Burn ₹ 62 L" is meaningless; "Net burn, 3-month average, normalised, as on 31-Aug-26" is usable.
5. **Colour means one thing only:** Red = act this week · Amber = watch · Green = within tolerance · Grey = data incomplete, don't rely on it. Never used decoratively.
6. **Plain labels, no jargon dressing.** "Money Coming In", not "Inflow Analytics".

---

## Global elements — visible on every tab

### Top strip (always fixed)

| Label | Content |
|---|---|
| Entity | Dropdown — India / Singapore / Consolidated |
| As On | Date selector, defaults to latest closed data |
| Books Position | ₹ figure from books |
| Bank Position | ₹ figure from bank |
| Difference | ₹ and %, with Red / Amber / Green badge |
| Data Updated | Timestamp + "Books: Open / Closed for month" |
| Alerts | Bell with count of unacknowledged |
| User | Name, role, sign out |

### Confidence banner (appears only when needed)

A single amber or grey bar directly under the top strip — *"Bank difference ₹ 12.4 L unexplained. Treat runway figures as indicative."*
When this bar is showing, every headline number on every tab carries a small grey dot. **No silent staleness.**

---

## TAB 1 — TODAY
*Answers: am I fine, and what needs me this week?*

### Band 1 — The Five Numbers (large, single row, no scrolling)

| Label | Shows | Sub-line |
|---|---|---|
| Cash-Out Date | Calendar date | "Fundraise trigger: DD-Mmm-YY" |
| Cash Available | ₹ (unrestricted only) | "Restricted ₹ __ · Undrawn credit ₹ __" |
| Net Burn / Month | ₹ | "3-mth average · ↑/↓ __% vs prior 3 mths" |
| Runway | Months | "Current __ · Committed __ · Austerity __" |
| Liquidity Health | Score /100 + word (Strong / Adequate / Tight / Critical) | "Down 6 pts this month" |

### Band 2 — What Needs Me This Week

A single prioritised list, **maximum seven rows**, ranked by cash impact. Not a dashboard widget — a to-do list.

Columns: Priority · Item · Amount ₹ · By When · Owner · Action

Example rows: "₹ 84 L HDFC invoice 47 days overdue — call finance contact" · "GST payment ₹ 22 L due 20-Sep, funding gap ₹ 6 L" · "Week 5 cash dips to ₹ 31 L, below floor"

### Band 3 — The Week Ahead (7-day strip)

| Label | Content |
|---|---|
| Opening Cash | ₹ |
| Expected In | ₹ gross · ₹ weighted (weighted shown larger) |
| Committed Out | ₹ |
| Net Movement | ₹ +/− |
| Closing Cash | ₹ |
| If Top Client Slips | ₹ closing under that single assumption |

### Band 4 — Reading of the Position

Plain-language commentary, **4–6 sentences maximum**. Structure:

- What changed since last week and why
- The single biggest risk in the next 30 days
- What I should be deciding now
- **"Not visible to me:"** — an explicit line naming data gaps

Footer: *"Based on data as on __. Confidence: High / Medium / Low."*
If **Low**, the box collapses to the gaps line only. *I'd rather have silence than confident narration on bad data.*

### Band 5 — Two Charts, Side by Side

- **Left:** "Cash — Last 12 Months and Next 13 Weeks." One continuous line, actuals solid, forecast dashed, shaded confidence band, horizontal "minimum cash floor" line.
- **Right:** "Where the Cash Went — Last 3 Months." Horizontal bars by category, with Fixed / Variable / Discretionary shading.

---

## TAB 2 — RUNWAY & BURN
*Answers: how fast am I spending, on what, and how long does that leave me?*

### 2A — Runway

- **Runway Table** — one row per scenario: Scenario · Monthly Burn Assumed · Months Left · Cash-Out Date · What This Assumes (plain sentence)
  Rows: Current run-rate · Committed plan · Austerity case · Board-approved plan
- **Runway Movement** — waterfall: "Runway was __ months last month, now __ months." Bars for: collections better/worse than expected · spend above/below plan · one-off items · new funding. *This is the chart I want when the board asks why runway moved.*
- **Milestone markers** — "Runway to next funding milestone" vs "Runway to zero", on one bar with the gap called out.

### 2B — Burn Anatomy

- **Burn Summary** — Gross Burn · Collections · Net Burn, each for This Month / 3-Month Average / 6-Month Average / Same Month Last Year
- **Recurring vs One-Off** — Total Burn ₹ __ = Recurring ₹ __ + One-Off ₹ __, with a visible "One-off items excluded" list showing item, amount, month, and who classified it. **Reclassify button.**
- **Burn by Category** — table: Category · This Month ₹ · 3-Mth Avg ₹ · % of Total · Fixed/Variable/Discretionary · vs Plan ₹ · Trend arrow
  Top-level categories (not buried): People · Statutory & Taxes · Technology & Cloud · Client Delivery / Cost of Sales · Rent & Facilities · Marketing · Professional Fees · Finance Costs · Other
- **Burn per Unit** — Burn per month ÷ headcount, and Burn ÷ revenue. Two numbers, trended.

### 2C — People Cost
*Largest line and the one I control most directly, so it gets its own layer.*

- Funded Headcount · Actual Headcount · Approved but Unfilled · Offers Accepted, Not Joined
- Fully-Loaded Cost per Head, by function
- Monthly People Cost — trended 12 months
- Hiring Plan Cash Impact — next 6 months, and its effect on cash-out date
- Gratuity / leave encashment liability accrued

---

## TAB 3 — LIQUIDITY
*Answers: is my cash actually available, and is my position structurally healthy?*

### 3A — Where the Money Is

- **Account Table** — Bank / Institution · Account Purpose (Operating / Collection / Payroll / Statutory) · Balance ₹ · Available or Restricted · Restriction Reason · Maturity Date · Signatory · Approval Limit
- **Availability Summary** (three tiles): Freely Available ₹ · Restricted or Encumbered ₹ · Undrawn Sanctioned Credit ₹
- **Concentration note** — "__% of cash sits with one bank." Flagged if above threshold.

### 3B — Health & Ratios

- **Liquidity Health Score** — score, band, and a breakdown showing each component's contribution and its direction. **Not a black box.**
- **Primary Measures** (lead with these): Days Cash on Hand · Cash Conversion Cycle (DSO + Inventory Days − DPO) · Receivables Coverage of Payables · Statutory Dues Cover
- **Lender & Covenant Ratios** (secondary, grouped separately, labelled "For lender and covenant reporting"): Current Ratio · Quick Ratio · Debt–Equity · DSCR · Interest Cover
- Every ratio row shows: Label · Value · Formula in words · Balances Used (clickable) · 6-Month Trend · Benchmark or Covenant Threshold · Status
- **Score history** — 12-month line with the events that moved it annotated.

---

## TAB 4 — MONEY COMING IN
*Answers: what's owed to me, will it actually arrive, and how exposed am I?*

- **Collections Summary** (tiles): Total Receivable ₹ · Overdue ₹ · Weighted Collectible Next 30 Days ₹ · DSO (days, with trend) · Collections This Month vs Target
- **Ageing** — buckets Not Yet Due / 0–30 / 31–60 / 61–90 / 90+ / Disputed, in ₹ and % of total, as a stacked bar and as a table
- **By Client** — Client · Total Outstanding ₹ · Overdue ₹ · Oldest Invoice Age · Average Days Taken to Pay (their actual behaviour, not their stated terms) · Weighted Expected Next 30 Days ₹ · % of Total AR · Last Contact · Owner
- **Concentration** — Top 5 clients as % of receivables and % of revenue, side by side. With a plain line: *"If [Client] paid 45 days late, cash-out date moves from __ to __."*
- **Disputed / Withheld** — separate table, never mixed into ageing: Client · Invoice · Amount ₹ · Reason · Raised On · Owner · Expected Resolution
- **Collection Performance** — Promised vs Actually Received, last 6 months. *Calibrates how much I believe the weighted figure.*
- **Invoicing Gap** — work delivered but not yet invoiced, ₹ and days elapsed. *Cash I'm sitting on by my own delay.*

---

## TAB 5 — MONEY GOING OUT
*Answers: what must I pay, what can wait, and what have I already committed to?*

### 5A — Due Now

- Tiles: Due This Week ₹ · Due Next 30 Days ₹ · Of Which Non-Deferrable ₹ · Overdue to Vendors ₹
- **Obligations Table** — Due Date · Item · Vendor / Authority · Category · Amount ₹ · Deferrable? (No / Yes with cost) · Penalty or Interest on Delay · Approver · Status
  Default sort: **non-deferrable first, then by date.** *This ordering is the point of the screen.*

### 5B — Statutory Dues
*Its own layer because these are first-charge, carry penal interest, and are never negotiable.*

- Head (GST · TDS · PF · ESI · Professional Tax · Advance Tax · Others) · Period · Due Date · Amount ₹ · Funded? · Days to Due · Status
- **Statutory Funding Cover** — a single line: *"Statutory dues of ₹ __ fall due in the next 30 days. Cash earmarked: ₹ __. Gap: ₹ __."*
- 12-month statutory payment history and any interest or penalty actually paid.

### 5C — Committed but Not Yet Billed
*Money already spent that no invoice has arrived for. The most commonly missed number in any cash tool.*

- Commitment Type (Purchase Order · Cloud & Software Contract · Offer Letter Issued · Lease · Retainer · Other) · Counterparty · Total Value ₹ · Consumed to Date ₹ · Remaining ₹ · Cancellable? · Notice Period · Exit Cost ₹ · Ends On
- Summary line: *"Committed spend not yet in books: ₹ __. Of which non-cancellable: ₹ __."*

### 5D — Vendor Position

- Vendor · Payable ₹ · Overdue ₹ · Average Days We Take to Pay · Credit Terms Agreed · Relationship Criticality (High / Medium / Low) · On Hold?
- Top 10 vendors by exposure.

---

## TAB 6 — CASH CALENDAR
*Answers: which specific week do I have a problem in?*

- Horizon toggle: **13 Weeks (default)** · 4 Weeks · 26 Weeks
- **Week Grid** — one column per week, rows: Opening Cash · Collections Expected · Funding / Other In · Total In · People Cost · Statutory · Vendor Payments · Other Out · Total Out · Net Movement · Closing Cash
- Weekly bar chart above the grid: in, out, net, with the closing-cash line overlaid and the minimum cash floor drawn across
- **Lowest Point callout** — highlighted box: *"Lowest projected cash: ₹ __ in week of DD-Mmm. Floor: ₹ __. Shortfall: ₹ __."* **This is the single most important output of the tab.**
- **Detail depth** — Weeks 1–4 at line-item level (named invoices, named payments); Weeks 5–13 at category level. Labelled so I know which I'm looking at.
- **Confidence per week** — High / Medium / Low against each week, based on how much of it is contracted vs estimated
- **Forecast Accuracy** — *"Over the last 8 weeks, actual closing cash differed from forecast by an average of __% (range __% to __%)."* Without this, I don't know how much to trust the grid.

---

## TAB 7 — PLAN VS ACTUAL
*Answers: are we tracking to what we told ourselves and the board?*

- **Plan selector** (top of tab, mandatory): Which Plan · Version · Approved By · Approved On · Locked? *Every number on this tab is stamped with the plan it's measured against.*
- Tiles: This Month Variance ₹ / % · Year to Date Variance ₹ / % · Cash-Out Date: Per Plan vs Actual Trajectory · Forecast Accuracy Score
- **Cash Position — Plan vs Actual** — monthly line chart, three lines: current plan · actual · previous plan version (ghosted, so plan drift is visible)
- **Monthly Variance Table** — Month · Plan ₹ · Actual ₹ · Variance ₹ · Variance % · Type · Driver · Owner · Comment · Status
  **Type must be a fixed dropdown, not free text:** Timing · Volume · Price · Cost Overrun · One-Off · Permanent. *A slipped collection and a lost deal are different events and the tool must not let them be recorded identically.*
- **Variance Breakdown** — waterfall from Plan cash to Actual cash, bars grouped by Type. Timing variances shown in a distinct shade because they reverse.
- **Line-Item Variance** — same structure by category (revenue lines and cost lines), so I can see whether the miss is top-line or spend.
- **Plan History** — every version uploaded: Version · Uploaded By · Uploaded On · Note · Active? · Locked? · View / Compare

---

## TAB 8 — SCENARIOS
*Answers: what happens if, and which lever should I pull?*

- **Lever panel** (left, sliders and toggles, plain language): Top client pays __ days late · Collections at __% of plan · Hiring: freeze / plan / accelerate · Discretionary spend cut __% · Funding round slips __ months · New funding of ₹ __ closes on DD-Mmm · Revenue at __% of plan · Price increase of __%
- **Result panel** (right, updates live): New Cash-Out Date (with days moved, +/−) · New Runway (months) · Lowest Cash Point and Which Week · Statutory Cover Maintained? Yes/No · Covenants Breached? Yes/No
- **Comparison view** — hold up to four saved scenarios side by side: Scenario Name · Cash-Out Date · Runway · Lowest Cash · Verdict
- **Save & Share** — name a scenario, note the assumptions, share into the Board Pack
- **What Matters Most** — ranked list: *"The three inputs that move your cash-out date most: 1. Collection speed (± __ days) 2. Hiring pace (± __ days) 3. Discretionary spend (± __ days)."* Tells me where to spend management attention.
- **Pre-built cases always available:** Best · Base · Worst · Board Plan · Survival (what does it take to reach 18 months)

---

## TAB 9 — CAPITAL & DEBT
*Answers: what do I owe lenders, what can I still draw, and am I about to breach something?*

- **Facilities Table** — Lender · Facility Type · Sanctioned ₹ · Drawn ₹ · Available to Draw ₹ · Rate · Tenure · Next Repayment Date · Next Repayment ₹ · Security Given
- **Repayment Calendar** — next 12 months, principal and interest by month, overlaid on projected cash
- **Covenants** — Covenant · Required · Current · Headroom · Test Date · Status. **Amber before breach, not after.**
- **Funding History** — Round · Date · Amount ₹ · Instrument · Investor · Post-Money Valuation · Cash Remaining From That Round
- **Next Raise** — Target Amount ₹ · Target Close Date · Runway at Close · Trigger Date (when I must start) · Days Until Trigger

---

## TAB 10 — BOARD PACK
*Answers: can I produce the cash story for the board in ten minutes?*

- **Generate Pack** — pick as-on date, pick which sections, pick which scenarios; output as a document
- **Standard sections** (each pulled from a fixed snapshot, so it's reproducible later): Cash & Runway Summary · Burn Analysis · Collections & Concentration · Plan vs Actual with Drivers · 13-Week Forecast · Scenario Summary · Funding Position · Key Risks
- **Snapshot Library** — every pack ever generated, retrievable exactly as issued: Date · Generated By · Runway Stated · Cash-Out Date Stated · View. *When someone asks in March what I told the board in December, I open it rather than reconstruct it.*
- **Commentary field** — my own narrative per section, saved with the pack

---

## TAB 11 — ALERTS
*Answers: what has the tool told me, and did anyone act on it?*

- **Active Alerts** — Severity · Alert · Triggered On · Trigger Value vs Threshold · Amount at Stake ₹ · Acknowledged By · Action Taken · Snooze / Resolve
- **Alert History** — same fields plus: Channel Sent (SMS / Email) · Delivered? · Read? · Time to Acknowledge
- **Alert Performance** — a small honest panel: Alerts Sent (30 days) · Acted On · Ignored · Muted. *If most are being ignored, the thresholds are wrong and I want to see that.*

---

## TAB 12 — SETUP
*Grouped away from the daily screens. Four layers.*

### 12A — Data Sources
Accounting connection status · Last sync · Sync schedule · Sync failure history · Bank statement upload or feed · Manual entries register (things not in books: commitments, expected funding, disputes) with who added what and when

### 12B — Upload Plan
Download template · Upload file · Validation report (rows accepted, rejected with reason, totals check, period continuity, opening cash tie-in) · Column mapping with saveable profiles · Preview with diff against active plan · Save as new version, with note · Mark as Board-Approved (locked, requires a second approver)

### 12C — Alert Rules
Rule · On/Off · Threshold · Severity · Channel · Cooldown · Quiet Hours · Recipients · Escalate After

Rules required:
1. Runway below __ months
2. Cash below ₹ __
3. Statutory dues unfunded within __ days
4. Payables exceed receivables due
5. Plan variance above __%
6. Single client above __% of receivables
7. Covenant headroom below __%
8. Books vs bank difference above ₹ __
9. Data not updated for __ hours
10. Cash-out date moved by more than __ days in a week

### 12D — People & Definitions
- **Users** — Name · Role (Admin / CFO / Finance / Board Read-Only) · Access · Last Login
- **Definitions** — plain-English glossary of every term the tool uses: how net burn is calculated, what counts as restricted cash, how collections are weighted, what the health score is made of. Editable and dated. *Every argument about a number traces back to a definition, so the definitions must be written down and visible.*
- **Activity Log** — who changed a threshold, uploaded a plan, reclassified a one-off, or exported a pack

---

## What was deliberately NOT asked for

- **No profit and loss or balance sheet views.** Those live in the accounting system and duplicating them invites reconciliation arguments. This tool is about cash.
- **No transaction-level browsing as a destination.** Entries are reachable by drilling from a number, never as a tab of their own.
- **No customisable widget dashboard.** If everyone arranges their own screen, no two people in a meeting are looking at the same thing.
- **No mobile version of the full tool.** On the phone: the alert and the five numbers from Tab 1. Nothing else.

---

## Amendments

*(none yet)*
