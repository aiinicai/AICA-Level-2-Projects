# DCF Valuation Professional v3.0.5

## AICA Level 2 – Batch 104 Capstone Project

**Participant:** Rajesh Kamath  
**ICAI Membership No.:** 100524  
**Batch:** AICA Level 2 – Batch 104  
**Project:** DCF Valuation Professional v3.0.5  

---

## 1. Project Overview

DCF Valuation Professional is a Python-based AI-assisted valuation application designed to automate and enhance the Discounted Cash Flow (DCF) valuation process for listed as well as unlisted companies.

The project combines conventional financial valuation methodology with Artificial Intelligence while retaining professional judgement and human validation at critical stages.

---

## 2. Problem Statement

Preparation of a professional DCF valuation normally requires:

- extraction of historical financial information;
- normalisation of financial statements;
- preparation of financial forecasts;
- determination of EBITDA and EBIT;
- estimation of capital expenditure;
- working capital forecasting;
- computation of Free Cash Flow to Firm (FCFF);
- determination of WACC;
- terminal value estimation;
- sensitivity analysis; and
- preparation of valuation reports.

The objective of this project is to automate substantial portions of this workflow while maintaining transparency, auditability and professional control.

---

## 3. AI-Driven Solution

The application incorporates AI-assisted functionality for:

- interpretation of imported financial information;
- identification of relevant financial parameters;
- generation of forecast assumptions;
- analysis of historical trends;
- reasonableness assessment;
- assistance in developing DCF assumptions; and
- generation of explanatory valuation narratives.

The application supports both:

### Offline AI
Local AI models through **Ollama**, enabling financial information to remain on the user's computer.

### Online AI
Optional integration with supported online AI providers where required.

---

## 4. Human-in-the-Loop Approach

AI-generated information is not treated as the final valuation conclusion.

The application incorporates professional review controls including:

- confidence grading of imported financial data;
- identification of source financial-statement rows;
- review of imported figures before posting;
- rejection of questionable mappings;
- editable forecast assumptions;
- user-controlled WACC parameters;
- editable terminal growth assumptions; and
- scenario and sensitivity analysis.

The final valuation therefore remains subject to professional judgement.

---

## 5. DCF Methodology

The application follows the FCFF approach:

**FCFF = EBIT × (1 – Tax Rate) + Depreciation & Amortisation – Capital Expenditure – Change in Net Working Capital**

Enterprise Value is determined by discounting forecast FCFF at the Weighted Average Cost of Capital (WACC).

Terminal Value is estimated using the perpetual growth methodology:

**Terminal Value = FCFF(n+1) / (WACC – g)**

Enterprise Value is subsequently converted into Equity Value after considering debt, cash and other relevant adjustments.

---

## 6. Major Features

- Python desktop application
- Excel financial statement import
- PDF financial statement import
- Schedule III-aware financial mapping
- Revenue identification
- EBITDA / EBIT identification and derivation
- Depreciation and amortisation mapping
- Capital expenditure mapping
- Net Working Capital analysis
- AI-assisted forecast assumptions
- Offline AI through Ollama
- Optional online AI
- FCFF computation
- WACC calculation
- Terminal value calculation
- Enterprise Value to Equity Value bridge
- Scenario analysis
- Sensitivity analysis
- Automated valuation outputs
- Human review and validation controls

---

## 7. Technology Stack

- Python
- Tkinter
- OpenPyXL
- PyPDF
- python-docx
- ReportLab
- python-pptx
- Ollama
- Local Large Language Models
- Optional cloud-based Generative AI

---

## 8. Repository Structure

- `source/` – Python application and build files
- `documentation/` – Project report, AI prompt log and user documentation
- `presentation/` – Capstone presentation
- `sample_input/` – Anonymised demonstration financial statements
- `sample_output/` – Demonstration valuation outputs
- `screenshots/` – Application screenshots
- `video/` – Demonstration video script

---

## 9. Privacy and Security

Financial statement parsing is performed locally.

When Offline AI through Ollama is selected, financial information can be processed locally without transmitting the financial statements to an external AI provider.

No API keys, passwords, private signing keys or confidential client financial statements are included in this repository.

---

## 10. Professional Use

The application is intended as a decision-support and valuation-assistance tool.

AI-generated assumptions and automatically extracted financial information must be reviewed by the valuer before being relied upon.

The software does not replace professional judgement or applicable valuation standards.

---

## 11. Capstone Learning Outcomes

This project demonstrates practical application of:

- Artificial Intelligence
- Generative AI
- Prompt engineering
- Python automation
- Financial statement analysis
- DCF valuation
- Local LLM deployment
- Data privacy
- Human-in-the-loop AI
- Professional reporting

## 12. Author

**Rajesh Kamath**  
**ICAI Membership No.:** 100524  
**AICA Level 2 – Batch 104**

