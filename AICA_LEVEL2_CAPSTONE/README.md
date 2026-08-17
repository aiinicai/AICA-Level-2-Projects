# CA Statutory Compliance & Notice Intelligence Assistant

**ICAI AICA Level-2 Capstone Project**\
**Prepared by: CA R C Hasija**

> **Disclaimer:** All names, amounts, notices, compliance records and
> other information used in this project are dummy data created solely
> for ICAI AICA Level-2 Capstone demonstration purposes. The project
> does not provide legal, tax or professional advice.

## Project Overview

The **CA Statutory Compliance & Notice Intelligence Assistant**
demonstrates how AI-assisted tools, data visualization and Python can
support a Chartered Accountant or compliance team in reviewing statutory
notices, monitoring compliance deadlines, identifying high-risk matters
and prioritizing action.

The project combines several practical components into one workflow:

**Dummy Statutory Notice → AI Notice Analysis → Structured Compliance
Data → Management Dashboard → Risk Prioritization → Recommended Action**

Human professional review remains essential at every stage.

## Objectives

-   Analyse a dummy statutory notice using AI.
-   Extract important compliance information and deadlines.
-   Prepare a structured compliance-monitoring dataset.
-   Visualize compliance status and risk through a management dashboard.
-   Demonstrate AI-assisted application development.
-   Build a Python desktop application for compliance-risk
    prioritization.
-   Maintain an organized evidence trail for the Capstone demonstration.
-   Demonstrate responsible use of AI with dummy data and human
    oversight.

## Tools and Technologies

  -----------------------------------------------------------------------
  Tool / Technology                   Use in Project
  ----------------------------------- -----------------------------------
  Google AI Studio                    AI-assisted analysis of the dummy
                                      statutory notice

  Microsoft Excel                     Dummy statutory compliance dataset

  Bricks                              AI-generated compliance and risk
                                      dashboard

  Antigravity IDE                     AI-assisted application-development
                                      workflow

  Python 3                            Compliance Risk Analyzer
                                      application logic

  Tkinter                             Desktop graphical user interface

  Microsoft Word / PDF                Dummy notice and final project
                                      documentation
  -----------------------------------------------------------------------

## Project Components

### 1. Dummy Statutory Notice

A fictitious Income Tax compliance notice was created for demonstration.
The sample case includes:

-   Assessee: ABC Manufacturing Private Limited
-   Assessment Year: AY 2025-26
-   Difference requiring verification: ₹18,75,000
-   Notice date: 10 August 2026
-   Response due date: 25 August 2026

No actual taxpayer or client information is used.

### 2. Google AI Studio --- Notice Intelligence

The dummy PDF notice was analysed using Google AI Studio.

The AI workflow demonstrates:

-   extraction of notice information;
-   identification of the main issue;
-   deadline identification;
-   risk/action assessment;
-   supporting-document checklist;
-   reconciliation recommendations;
-   management summary; and
-   draft-response assistance.

AI-generated output is treated as assistance only and remains subject to
professional verification.

### 3. Compliance Dataset

`Dummy_Compliance_Data.xlsx` contains illustrative compliance records
covering areas such as:

-   GST
-   Income Tax
-   TDS
-   ROC
-   PF
-   ESI
-   Internal Compliance

The dataset includes due dates, status, days pending, risk level,
responsible person/team and remarks.

### 4. Bricks Compliance Dashboard

The Excel dataset was used to create the **CA Statutory Compliance &
Notice Intelligence Dashboard**.

The dashboard demonstrates:

-   total compliance items;
-   completed items;
-   pending / in-progress / not-started items;
-   overdue items;
-   risk-level mix;
-   compliance categories;
-   high-risk items by responsible team; and
-   upcoming workload by due date.

### 5. Antigravity --- AI-Assisted Development

The complete Capstone workspace was opened in Antigravity IDE and an
application-development prompt was prepared for the Compliance Risk
Analyzer.

This component demonstrates the AI-assisted development workflow covered
during AICA Level-2.

### 6. Python --- CA Statutory Compliance Risk Analyzer

A local Python/Tkinter desktop application was created to evaluate
individual compliance items.

The user can enter:

-   Compliance Type
-   Particulars
-   Due Date
-   Current Status
-   Risk Level
-   Responsible Person
-   Remarks

The application calculates the deadline position and provides a priority
classification and recommended action.

#### Priority Logic

  Condition             Classification
  --------------------- ---------------------------------
  Completed             COMPLETED / NO IMMEDIATE ACTION
  Overdue + High Risk   CRITICAL
  High Risk             HIGH PRIORITY
  Medium Risk           MEDIUM PRIORITY
  Low Risk              NORMAL MONITORING

### Demonstration Test Case

The application was tested using:

-   Compliance Type: Income Tax
-   Particulars: Response to Dummy Notice
-   Due Date: 25-08-2026
-   Status: Pending
-   Risk Level: High
-   Responsible Person: CA / Tax Team
-   Remarks: Reconciliation of Rs. 18,75,000 required

The working demonstration classified the matter as **HIGH PRIORITY** and
displayed the remaining time and recommended action.

## Project Folder Structure

``` text
AICA_LEVEL2_CAPSTONE/
├── 01_Dummy_Data/
│   ├── Dummy_Income_Tax_Notice.docx
│   ├── Dummy_Income_Tax_Notice.pdf
│   └── Dummy_Compliance_Data.xlsx
├── 02_AI-Analysis/
├── 03_Dashboard/
├── 04_Screenshots/
│   ├── 01_AI_Studio_Notice_Analysis.png
│   ├── 02_AI_Studio_Notice_Analysis.png
│   ├── 03_Bricks_Dashboard_Overview.png
│   ├── 04_Bricks_Dashboard_Risk_Analysis.png
│   ├── 05_Antigravity_AI_Assisted_Development.png
│   └── 06_Python_Risk_Analyzer.png
├── 05_Final_Submission/
│   └── CA_Statutory_Compliance_Notice_Intelligence_Assistant_Project_Report.docx
└── 06_Risk_Analyzer/
    ├── risk_analyzer.py
    └── README.txt
```

## How to Run the Python Risk Analyzer

### Requirements

-   Python 3
-   Tkinter (normally included with standard Python installations on
    Windows)

No additional external Python packages are required.

### Run

Open the `06_Risk_Analyzer` folder and run:

``` text
python risk_analyzer.py
```

If `.py` files are associated with Python on Windows, the application
may also be started directly by opening `risk_analyzer.py`.

## Evidence Screenshots

The `04_Screenshots` folder contains evidence of the practical
demonstrations:

1.  Google AI Studio notice analysis
2.  Google AI Studio analysis / deadline output
3.  Bricks dashboard overview
4.  Bricks dashboard risk analysis
5.  Antigravity AI-assisted development workspace
6.  Working Python Risk Analyzer

## Human-in-the-Loop Controls

This project follows a human-supervised approach:

-   AI output must be independently verified.
-   Statutory dates and facts must be checked against source documents.
-   Applicable law, rules, circulars and portal information must be
    independently reviewed.
-   No real statutory response should be filed solely on the basis of
    AI-generated content.
-   Confidential client information should not be provided to external
    AI services without appropriate authorization and safeguards.
-   Sensitive identifiers should be redacted where appropriate.

## Future Enhancements

Possible future extensions include:

-   Excel import directly into the Risk Analyzer;
-   automated deadline reminders and escalation;
-   notice/document classification;
-   searchable compliance-document repository;
-   email workflow for unanswered compliance correspondence;
-   secure local/offline AI for confidential information;
-   approved MCP/connectors for accounting and practice-management
    systems;
-   role-based access and audit trails; and
-   office-wide compliance dashboards.

## Learning Outcomes

The project demonstrates practical application of AICA Level-2 concepts
including:

-   AI-assisted professional workflows
-   document analysis
-   structured prompting
-   data visualization
-   AI-assisted application development
-   Python fundamentals
-   agentic workflow concepts
-   risk prioritization
-   responsible AI and human oversight

## Conclusion

The **CA Statutory Compliance & Notice Intelligence Assistant**
demonstrates how multiple AI and digital tools can be combined into a
practical Chartered Accountancy workflow.

The prototype converts a dummy statutory notice and compliance dataset
into structured analysis, management visualization and risk-prioritized
action while retaining professional judgement and human control.

------------------------------------------------------------------------

**Prepared by: CA R C Hasija**\
**ICAI AICA Level-2 Capstone Project**\
**August 2026**
