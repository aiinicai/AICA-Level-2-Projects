# AI-Powered Financial & Tax Analysis Tool

**Capstone Project – AICA Level 2**  
**Candidate:** CA Shivangi Mehta  
**Batch:** AICA-L2 – Batch 83 (Surat)

## 1. Project Overview

This project presents an offline-first financial review and compliance assistant designed to help accounting, audit and tax professionals review structured financial data, identify exceptions, and organize findings for professional review.

The application is packaged for Windows and uses a local SQLite database and local file storage. It supports local use and a controlled private-LAN mode.

## 2. Problem Statement

Financial review work often requires professionals to examine large accounting exports and supporting registers, reconcile information across sources, apply accounting/audit/tax rules, identify exceptions, and document findings. Manual review can be repetitive and makes consistent, traceable screening more difficult.

## 3. Objective

The objective of FINsight is to provide a structured workflow for:
- importing financial data;
- detecting and validating file structures;
- mapping data into the application's expected format;
- running accounting, audit and tax review rules;
- identifying and normalizing findings;
- assessing review readiness and risk;
- maintaining working papers/queries and engagement information; and
- presenting review results in a consistent format.

## 4. Major Functional Areas

- Engagement management
- File upload and validation
- Column/structure mapping
- Data quality checks
- Accounting review
- Audit review
- Tax review
- Unified review and Findings Centre
- Risk scoring
- Query / working-paper support
- Reports and review outputs
- SEBI-related module framework
- Local and private-LAN operation
- Security and engagement isolation controls

## 5. Technology Stack

- Python
- Flask
- SQLAlchemy
- SQLite
- Pandas
- OpenPyXL
- ReportLab
- Pydantic
- Waitress
- Pytest / pytest-cov
- Windows EXE packaging through PyInstaller (build configuration included)

## 6. Offline-First Design

The application is designed to operate locally. The submitted source documentation records that FINsight has no outbound network calls in its application source and that external AI-provider integration is not currently wired into the live application. The AI feature flag is OFF by default.

**Important:** the project title uses “AI-Powered” as the capstone title selected by the candidate. In the current submitted build, the demonstrable core review engine is rule-based/offline; external AI is not required for the application's operation.

## 7. Application Architecture

User → Web UI → Flask API/Blueprints → Services → Rule Engines → SQLite / Local Files → Findings / Reports

The codebase separates UI routes, services, rule logic, data access/models, and local storage.

## 8. How to Run

For the packaged Windows version, use the supplied FINsight executable and follow the deployment instructions in `README_DEPLOYMENT.md`.

For source/development use, install the packages in `requirements.txt` and run the application through the supplied launchers.

## 9. Sample Data

The uploaded project currently contains these financial input workbooks:
- 20260826T190144432939_1eea8b50_Purchase_Register_FY2025-26.xlsx
- 20260826T190144406787_ba659611_General_Ledgers_FY2025-26.xlsx
- 20260826T190144465382_35aa934e_Sales_Register_FY2025-26.xlsx
- 20260826T190144341440_7cc659d6_Fixed_Asset_Register_FY2025-26.xlsx
- 20260826T190144489955_c973ddf4_Trial_Balance_FY2025-26.xlsx

## 10. Testing

The project contains unit and HTTP/integration-oriented tests covering accounting, audit, tax, mapping, upload validation, review orchestration, security, LAN mode, packaging and other services.

A consolidated test matrix is provided in `04_Testing/Test_Cases.xlsx`.

## 11. Security / Privacy

The project includes an explicit security and privacy hardening stage covering upload validation, path traversal protection, engagement isolation, IDOR checks, SQL-injection review, secure session handling, and offline/network posture.

## 12. Limitations

- Output depends on the quality and completeness of input data.
- Rule-based findings are screening aids and require professional judgement.
- The current live application does not make external AI calls.
- A Windows packaged build should be tested on the target machine before production use.

## 13. Future Scope

- Optional, explicitly consented AI-assisted explanations
- Expanded GST and direct-tax rule coverage
- Additional financial statement analytics
- More automated reconciliations
- Richer dashboards and management reporting
- Expanded multi-format ingestion
- More comprehensive report automation

## 14. Disclaimer

This application is a professional review aid. It does not replace the judgement, verification, or statutory responsibility of a Chartered Accountant, auditor, tax professional, or other qualified reviewer.
