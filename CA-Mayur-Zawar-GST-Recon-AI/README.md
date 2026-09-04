# GST-Recon AI

## AICA Level 2 Capstone Project

**Submitted by:** CA. Mayur N. Zawar, FCA

## Project Title

GST-Recon AI – GST Purchase Reconciliation and Query Tracking System

## Project Overview

GST-Recon AI is a local-first GST reconciliation utility designed to compare GST portal data with client purchase records and identify reconciliation exceptions.

The system supports period-wise reconciliation, accountant review, query resolution, carry-forward tracking and subsequent automatic reconciliation when previously missing transactions appear in later-period data.

## Key Features

- GST portal Excel data upload
- Client Excel workbook upload
- B2B reconciliation
- CDNR reconciliation
- GSTIN-based matching
- Invoice/document number normalization
- Document value and tax comparison
- Missing in Client identification
- Missing in Portal identification
- Amount / Tax Difference identification
- Accountant review and resolution
- Query carry-forward across financial-year periods
- Automatic carry-forward reconciliation
- Audit history
- Excel reconciliation reports
- SQLite-based local tracking
- Client master and GSTIN validation

## Reconciliation Statuses

The system uses four primary reconciliation statuses:

- Matched
- Amount / Tax Difference
- Missing in Client
- Missing in Portal

## Technology Used

- Python
- Streamlit
- Pandas
- SQLite
- Excel / XlsxWriter
- Rule-based reconciliation logic

## Privacy and Data Handling

The application is designed for local-first processing. GST reconciliation data and tracking information are maintained locally through SQLite.

No confidential client database or production client data is included in this repository submission.

## How to Run

Install the required packages:

```bash
pip install -r requirements.txt