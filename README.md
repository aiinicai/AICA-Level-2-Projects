# PO Compliance Dashboard

Role

Act as a senior Internal Auditor, Procurement Control Specialist, Data Analyst, and full-stack application architect.

I want to build a professional PO Compliance Dashboard for an audit/finance use case.

The objective is to analyse Purchase Order data, automatically perform predefined audit and compliance tests, identify exceptions, assign risk scores, and present the results through an interactive management dashboard.

1. Project Objective

Build a web-based PO Compliance Audit & Risk Analytics System that helps an auditor answer:

Are POs being created according to procurement procedures?

Are POs properly approved?

Are POs being created before invoices/GRNs?

Are there potential cases of purchase splitting?

Are POs being modified unusually?

Are POs expired or remaining open for excessive periods?

Are mandatory PO fields complete?

Are there unusual vendor/PO patterns?

Which POs require immediate audit attention?

The system must support an audit-by-exception approach, allowing an auditor to focus on high-risk transactions rather than manually reviewing the entire population.

2. Target Users

Primary users:

Internal Auditors

Finance & Accounts teams

Procurement teams

Management

Compliance teams

The interface should be professional and suitable for CFO and top management.

3. Data Sources

Design the application to accept CSV/XLSX files.

Primary PO Register fields may include:

PO Number

PO Date

Vendor Code

Vendor Name

Material/Service Description

Category

Quantity

Unit Rate

PO Value

Currency (INR)

Department

Cost Centre

Plant

Requester

Approver

Approval Level

Required Approval Level

Approval Date

Valid From

Valid To

Delivery Date

Payment Terms

PO Status

Modification Date

Original PO Value

Invoice Date

GRN Date

Other supporting datasets:

Vendor Master

Vendor Code

Vendor Name

GSTIN

PAN

Vendor Status

Vendor Category

UDIN (MSME vendor)

Vendor Creation Date

Invoice Register

Invoice Number

Invoice Date

PO Number

Vendor Code

Vendor Name

Base Invoice Amount

GST Amount

Total Invoice Value

GRN Register

GRN Number

GRN Date

PO Number

Vendor Code

Vendor Name

Received Quantity

Received Value

If some fields are unavailable in excel, the application must clearly state as Not Applicable and identify the corresponding audit test as "Not Tested" rather than inventing data.

4. Audit Rules Engine

Implement configurable audit rules.

A. PO Process Compliance

Rule 1 — PO Created After Invoice

Flag when Invoice Date < PO Date.

Risk: HIGH

Rule 2 — PO Created After GRN

Flag when GRN Date < PO Date.

Risk: HIGH

Rule 3 — Missing Approval

Flag when required approval information is missing.

Risk: HIGH

Rule 4 — Approval Level Exception

Compare Actual Approval Level against Required Approval Level.

Flag when Actual Approval Level is lower than Required Approval Level.

Risk: CRITICAL

Rule 5 — Missing Mandatory Fields

Check configurable mandatory fields such as:

Vendor

PO value

Approval

Payment terms

Cost centre

Delivery date

Risk: MEDIUM

Rule 6 — Expired PO

Flag open POs where Valid To is before the current date.

Risk: MEDIUM

Rule 7 — Long-Open PO

Flag open POs exceeding configurable aging thresholds:

30 days - OKAY

90 days -MEDIUM

180 days - HIGH

365 days - HIGH

Risk: MEDIUM/HIGH depending on aging.

5. Purchase Splitting Detection

Create an analytical rule to identify potential purchase splitting.

Look for multiple POs:

For the same vendor

Within a configurable number of days

In the same/similar category

With individual values close to an approval threshold

Example:

PO 1 = ₹4.8 lakh
PO 2 = ₹4.7 lakh
PO 3 = ₹4.9 lakh

If the approval threshold is ₹5 lakh, flag the combined transaction pattern for review.

Important:
Do NOT label this as confirmed fraud or misconduct.

Use wording such as:

"Potential Purchase Splitting — Requires Audit Review."

6. PO Value and Modification Analytics

Identify:

PO value exceeding approval thresholds

Significant PO modifications

PO value increasing materially after initial approval

Unusual PO values

Repeated modifications

Large deviations from original PO value

Calculate:

Modification % =
(Current PO Value - Original PO Value) / Original PO Value × 100

Create configurable thresholds, for example:

10% = Review

25% = High Risk

50% = Critical Review

7. Vendor-Level Analytics

Provide vendor-level analysis including:

Number of POs

Total PO value

Average PO value

Number of exceptions

High-risk POs

Modification frequency

Potential split-PO patterns

Open PO value

Expired PO value

Allow the auditor to click a vendor and drill down into its PO history.

8. Risk Scoring

Create a transparent, rule-based risk score.

Example:

Critical approval exception: +40

PO after invoice: +30

PO after GRN: +30

Potential purchase splitting: +35

Significant PO modification: +20

Expired PO: +15

Missing mandatory information: +10

Long-open PO: +10

Cap the score at 100.

Risk categories:

0–29 = LOW
30–59 = MEDIUM
60–79 = HIGH
80–100 = CRITICAL

Display both:

Overall risk score

Individual reasons contributing to the score

The system must never present the risk score as proof of fraud. It is an audit prioritisation mechanism.

9. Dashboard

Create a professional executive dashboard.

Top KPI cards:

Total POs

Total PO Value

Compliant POs

Exception POs

Compliance %

High/Critical Risk POs

Open PO Value

Potential Financial Exposure

Charts:

Compliance vs Exceptions

Risk Distribution

Exceptions by Audit Rule

PO Value by Department

PO Value by Vendor

Monthly PO Trend

Open PO Aging

High-Risk Vendors

Use professional finance/audit colours:

Green = Compliant

Amber = Medium Risk

Orange = High Risk

Red = Critical Risk

Blue = Neutral/Information

Avoid excessive decorative graphics.

10. Exception Register

Create a detailed audit exception table containing:

PO Number

PO Date

Vendor

PO Value

Department

Audit Rule

Exception Description

Risk Score

Risk Category

Financial Impact/Exposure

Status

Recommended Action

Allow filtering by:

Risk

Vendor

Department

Date

PO value

Audit rule

Status

Provide search and sorting.

11. PO Drill-Down

When a user selects a PO, show:

PO Information

Vendor, amount, date, department, status, approver.

Compliance Tests

Show each test as:

PASS
FAIL
NOT TESTED

Exception Explanation

Clearly explain why the PO was flagged.

Risk Score

Show the score and contributing rules.

Audit Recommendation

Provide a concise suggested audit action.

12. Audit Report

Allow the user to export an audit-ready exception report.

The report should contain:

Executive summary

Population analysed

Total PO value

Compliance rate

Number of exceptions

High/Critical risk items

Exception categories

Top risky vendors

Key observations

Recommended actions

Do not make unsupported claims such as "fraud detected."

Use professional audit language:

"Exception identified"

"Potential control weakness"

"Requires management review"

"Requires further audit verification"

13. Data Quality

Before analysing data, perform validation for:

Missing values

Duplicate PO numbers

Invalid dates

Negative values

Incorrect data types

Missing vendor codes

Inconsistent vendor names

Invalid approval levels

Display a separate Data Quality Summary.

14. Configurable Audit Parameters

Do not hard-code business rules unnecessarily.

Provide an Audit Settings section where an administrator can configure:

Approval thresholds

PO aging thresholds

Purchase splitting time window

PO modification percentage

Mandatory fields

Risk scoring weights

Don’t generate any illustrative things.

Clearly state that these thresholds are illustrative and should be replaced by the organisation's actual procurement policy.

15. User Experience

Design a modern, clean and professional interface suitable for:

CFO/Finance Head

Internal Audit Head

Procurement Head

Navigation:

Dashboard

PO Analysis

Exception Register

Vendor Risk

Aging Analysis

Data Quality

Audit Rules

Settings

Reports

Include:

Responsive design

Search

Filters

Sorting

Drill-down

Export functionality

Clear legends

Tooltips explaining audit rules

16. Important Audit Principles

The application must distinguish between:

Fact
and
Audit inference

For example:

Do NOT say:
"Vendor committed fraud."

Say:
"Transaction exhibits indicators requiring further audit investigation."

Every exception should show the underlying data and rule that caused the exception.

17. Final Deliverable

Build a fully functional prototype rather than a static mock-up.

Prioritise:

Correct audit logic

Transparent calculations

Useful exception identification

Professional dashboard

Easy drill-down

Audit-ready reporting

Data privacy and security

 

The final product name should be:

PO-COMPLIANCE DASHBOARD

Purchase Order Compliance & Audit Risk Analytics

Include a subtitle:

"From Transaction Data to Audit Exceptions."

This project was built with [Lovable](https://lovable.dev).

**Live app**: https://pocompliancedashboard.lovable.app

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/b7cc2c9f-fea7-4c1f-ab32-b31b4c5c1199).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
