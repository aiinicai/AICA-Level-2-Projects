# User guide

For the Chartered Accountant, manager or article assistant using the Tax Audit
Applicability Decision System for **FY 2025-26 (AY 2026-27)**.

---

## Opening it

Double-click `app/index.html`. No installation or server. Everything runs in your browser;
nothing is transmitted. Do not paste the same figures into chat assistants or online tools.

The green strip at the top states the legal basis — what was checked and when. Details are
in `legal/sources.md`.

---

## How it works — the short version

1. Fill in the **Assessee Profile** and **Financial Inputs**.
2. Open **Decision**.
3. If a result is shown, you are done. If it says **"N more answers needed"**, each item says
   why it matters — click **Go to** and it takes you straight to the field or question,
   highlighted.
4. Generate the working paper.

You never need to fill every field. Fields marked **Needed** are the only ones the law
requires on your facts. The rest may be left blank.

---

## The panels

### 1. Overview
What the tool does, and twelve sample cases. Clicking a case fills everything and opens the
decision — useful for training and demonstrations.

### 2. Assessee Profile
- **Name** — needed for the working paper, not for the decision.
- **Constitution** and **residential status** — these decide whether ss. 44AD / 44ADA are
  available at all. An HUF can use s. 44AD but not s. 44ADA. An LLP, company, AOP or
  co-operative can use neither. A non-resident can use neither.
- **Nature** — business or profession. If both, evaluate each separately.
- **Profession** — only a profession in s. 44AA(1), or notified under it, can use s. 44ADA.
- **Conditions** — tick any that apply: commission / brokerage, agency business, goods
  carriages, specified deductions (all exclude s. 44AD); lower income under s. 44AE / 44BB /
  44BBB (triggers s. 44AB(c)); audit under another law (Form 3CA); transfer pricing (later due
  dates); derivatives; more than one activity.

### 3. Financial Inputs

**Business**

| Field | Needed when |
| --- | --- |
| Turnover | Always |
| Total amounts received / cash received / total payments / cash paid | Turnover is above ₹1 crore and up to ₹10 crore — they decide which limit applies |
| Cash received (alone) | Also when turnover is between ₹2 and ₹3 crore — it decides the s. 44AD ceiling |
| Turnover not received through banking channels by the due date | Only when profit is between 6% and 8% of turnover — it fixes the exact s. 44AD deemed income |
| Declared profit, total income | Whenever the presumptive scheme could apply |

**Profession:** gross receipts; cash received (only between ₹50 and ₹75 lakh); declared
profit; total income.

Enter **0** where there were none. A nil total with nil cash satisfies the 5% test — nil does
not exceed 5% of nil.

### 4. Legal Tests
The yes / no questions the law turns on. They appear only when their answer can change the
result:

- **Is AY 2026-27 within a five-year bar under s. 44AD(4)?** — asked for an individual, HUF
  or firm carrying on business.
- **Was income declared under s. 44AD for any of AY 2021-22 to AY 2025-26?** — asked only when
  profit is below the deemed income and total income exceeds the basic exemption.
- **Will income be declared under s. 44AD(1) / 44ADA(1) in the return?** — asked only when it
  decides the outcome: the limit is crossed but the first proviso (Finance Act 2023) would
  take the assessee outside s. 44AB.

Below the questions: the cash-test meters and the threshold meter.

### 5. Decision
**APPLICABLE** or **NOT APPLICABLE**, with the section, the reasoning chain and the matrix.
Or the list of answers still needed.

### 6. Section References
One card per provision: applicability, the statutory words with their source, the firm's
simplified explanation, how it applies here, and the conclusion.

### 7. Working Paper
Detailed working paper (PDF), one-page summary (PDF), Word document. Needs a decision and
the assessee's name. In the print dialogue: **A4, portrait, background graphics on**.

### 8. Review & Export
Professional notes for the reviewer, and the JSON audit trail.

---

## Worked example

Turnover ₹1,00,00,000; receipts, payments and cash all 0; profit and total income ₹5,00,000;
individual.

1. Decision says **one more answer needed**: the s. 44AD(4) bar. **Go to** → answer **No**.
2. Profit is 5% — below even the 6% minimum deemed income — and income exceeds ₹4 lakh. It
   asks whether s. 44AD was used in the last five years.
3. **No** → NOT APPLICABLE. **Yes** → APPLICABLE under s. 44AB(e).

---

## Reviewer checklist

- [ ] Figures agreed to the sales / fee register, cash book and bank book
- [ ] Constitution and residential status correct
- [ ] Exclusions ticked where applicable (commission, agency, goods carriage, deductions)
- [ ] s. 44AD history verified from earlier returns — including any bar
- [ ] Presumptive declaration choice matches the return being filed
- [ ] Due dates checked for any CBDT extension
- [ ] s. 44AA position determined separately
- [ ] Sign-off completed

---

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Export buttons disabled | Answers still needed, or the assessee name is blank — the notice has a "Take me there" button |
| A question appeared after I entered a figure | That figure made the question relevant — e.g. profit fell below the deemed income |
| A field I filled is no longer marked Needed | It can't change the answer on the current facts |
| Status colours missing in the PDF | Enable background graphics in the print dialogue |
