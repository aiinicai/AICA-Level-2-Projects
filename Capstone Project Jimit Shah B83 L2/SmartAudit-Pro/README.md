# SmartAudit Pro - Audit Sample Selector

## ICAI Level 2 Capstone Project

SmartAudit Pro is a desktop-based audit sampling and population analytics application built in Python. It demonstrates how technology can support an auditor in analysing a transaction population, selecting samples using different approaches, identifying rule-based higher-risk items, visualising the population, and documenting the output.

> **Important:** SmartAudit Pro is an educational decision-support tool. It does not replace professional judgement. Risk-based selection is targeted testing and should not be represented as statistical sampling. Sample size and selection must be designed having regard to the audit objective, population characteristics, sampling risk and the requirements of SA 530.

## Key features

- Excel (`.xlsx/.xlsm`) and CSV population upload
- Automatic field mapping for Amount, Date, User and Narration
- Population analytics
- Random sampling with reproducible random seed
- Systematic sampling
- Value-based stratified sampling
- Rule-based risk selection
- Dashboard charts
- Indicative attribute sample-size calculator
- Excel audit report
- PDF audit report
- Included 500-record demonstration GL population

## Risk rules demonstrated

The current prototype assigns points for:
- amount at or above the user-defined threshold;
- round-value transactions;
- weekend postings;
- transactions posted from 25-31 March; and
- sensitive narration such as manual adjustment, provision, reversal, miscellaneous or suspense.

These rules are illustrative and are not a substitute for an engagement-specific fraud-risk assessment.

## Project structure

```text
SmartAudit-Pro/
├── SmartAudit_Pro.py
├── README.md
├── requirements.txt
├── LICENSE
├── .gitignore
├── sample_data/
│   └── SmartAudit_Demo_Population.xlsx
├── documentation/
│   ├── ICAI_Capstone_Project_Report.docx
│   ├── ICAI_Capstone_Project_Report.pdf
│   ├── SmartAudit_User_Manual.docx
│   ├── SmartAudit_User_Manual.pdf
│   └── Video_Narration_Script.md
└── screenshots/
    └── README.txt
```

## Installation

1. Install Python 3.10 or later.
2. Download or clone this repository.
3. Open a terminal in the project folder.
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Start the application:

```bash
python SmartAudit_Pro.py
```

The application also attempts to install missing packages on first run.

## Quick demonstration

1. Launch SmartAudit Pro.
2. Click **Browse** and select `sample_data/SmartAudit_Demo_Population.xlsx`.
3. Confirm mapping:
   - Amount -> `Amount`
   - Date -> `Date`
   - User -> `User`
   - Narration -> `Narration`
4. Enter threshold `1000000`.
5. Enter sample size `25`.
6. Keep seed `42`.
7. Demonstrate Random, Systematic, Stratified and Risk-based selection.
8. Open the Dashboard tab.
9. Export the Excel and PDF audit reports.

## Sampling approaches

| Method | Prototype logic | Audit interpretation |
|---|---|---|
| Random | Randomly selects N population items using a fixed seed | Each item is selected by the program's pseudo-random generator |
| Systematic | Random start followed by approximately equal intervals | Useful for demonstrating systematic selection |
| Stratified | Sorts by absolute amount and divides the population into three value strata | Demonstrates value-based stratification |
| Risk-based | Ranks transactions by rule-based risk score and amount | Targeted testing; not statistical sampling |

## Indicative sample-size calculator

The calculator uses a finite-population proportion formula based on population size, confidence level, tolerable deviation and expected deviation. It is included for educational demonstration only and is **not an ICAI/SA 530 prescribed sample-size table**.

## Technology

- Python
- Tkinter
- openpyxl
- matplotlib
- ReportLab

## Suggested viva explanation

**Problem:** Manual population analysis and sample documentation can be repetitive and prone to inconsistency.

**Solution:** SmartAudit Pro provides a local desktop workflow to upload a population, analyse it, apply different sample-selection approaches, identify rule-based higher-risk items, visualise results and export documentation.

**Control:** The tool does not make the audit conclusion. The auditor remains responsible for population completeness, relevance of the sampling approach, sample size, evaluation of exceptions and the final audit conclusion.

## Future enhancements

- Configurable risk-rule builder
- Monetary Unit Sampling
- User-defined strata
- Duplicate and unusual-user analytics
- Complete population reconciliation
- Saved engagement profiles
- Audit-trail logging
- Encrypted local project files

## Disclaimer

This project is for academic/demonstration purposes. Users should validate the population, configuration, sampling methodology and outputs before using any result in an actual audit engagement.
