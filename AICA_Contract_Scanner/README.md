# AI Contract Risk Scanner

## AICA Level 2 Project

### Project Overview

AI Contract Risk Scanner is an AI-powered application designed to analyse commercial contracts from a business and financial risk perspective.

The application helps Chartered Accountants, finance professionals and management identify commercially significant contractual provisions and potential areas of financial exposure during contract review.

The application is designed as a decision-support tool and is not intended to provide legal advice or replace professional legal review.

---

## Problem Statement

Commercial contracts often contain important financial and operational provisions that may be difficult to identify quickly during a manual review.

These may include:

- Payment terms
- Payment delays and credit exposure
- Termination provisions
- Automatic renewal
- Liability limitations
- Indemnities
- Penalties and liquidated damages
- Exclusivity
- Price escalation
- Currency and foreign exchange exposure
- Performance obligations
- Service levels
- Unusual or asymmetric obligations
- Missing commercial protections
- Material operational dependencies

The objective of this application is to use artificial intelligence to assist management and finance professionals in identifying these areas efficiently.

---

## Key Features

### 1. Contract Upload

Users can upload commercial contracts in:

- PDF
- DOCX

### 2. Contract Text Extraction

The application extracts the contract text and displays extraction statistics including:

- Word count
- Character count

The extracted contract text can also be reviewed by the user.

### 3. AI Contract Risk Analysis

The application analyses the extracted contract and identifies commercially significant risks.

Each risk finding may include:

- Risk category
- Severity
- Clause or section
- Page reference where available
- Evidence from the contract
- Contract fact
- Commercial interpretation
- Potential financial or business impact
- Management recommendation
- Confidence

### 4. Risk Classification

Risks are classified as:

- High
- Medium
- Low
- Informational

The application provides reasoning and supporting evidence for the identified risks.

### 5. Executive Summary

The application provides an executive-level summary of the major commercial, financial and operational risks identified in the contract.

### 6. Risk Dashboard

The dashboard provides an overview of identified risks and highlights priority management issues.

### 7. Contract Q&A

Users can ask business and financial questions about the uploaded contract, such as:

- What could cost us money?
- What are our major payment and cash-flow risks?
- Does this contract expose us to significant liability?
- What should management negotiate?
- Are there automatic renewal provisions?
- What are the major performance obligations?

---

## AI Analysis Approach

The application follows the principle:

**Evidence → Interpretation → Financial Impact → Recommendation**

The AI is instructed to distinguish between:

1. Contract facts
2. Commercial interpretation
3. Financial or business impact
4. Management recommendation

The application also attempts to identify the relevant contractual evidence supporting each finding.

Where sufficient evidence cannot be established from the available contract text, the application should state:

**"Not determinable from the available contract text."**

The system is designed to minimise unsupported conclusions and avoid inventing contractual provisions, amounts, dates or obligations.

---

## Application Workflow

```text
Commercial Contract
        ↓
Upload PDF / DOCX
        ↓
Text Extraction
        ↓
AI Contract Analysis
        ↓
Risk Identification
        ↓
Risk Classification
        ↓
Financial / Business Impact
        ↓
Management Recommendation
        ↓
Executive Risk Dashboard
        ↓
Business & Financial Q&A