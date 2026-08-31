# AI-Powered Invoice Extras Extraction

**AICA Level 2 Capstone Project**  
**Candidate:** Nagaraju Gorantla  
**Membership No.:** 222822  
**Batch:** AI CA Level 2 - B91

## Project Overview

This capstone demonstrates a hybrid **Rule + AI + Human Validation** workflow for extracting customer-recoverable additional logistics charges from unstructured email text.

The solution combines deterministic rule-based extraction with Gemini AI-assisted interpretation and validation. Cases that are incomplete, ambiguous, approximate, or otherwise require judgement can be routed for human review before approval or rejection.

## Project Contents

- `01_Project_Summary/` - Final capstone project report (PDF)
- `02_Prompts/` - AI prompts used in the project
- `03_Examples/` - Synthetic/anonymized sample email inputs and sample outputs
- `04_Source_Code/` - Python application source code and automated test runner
- `05_Test_Evidence/` - Excel evidence for the defined 8-case test pack
- `06_Demo_Link/` - Unlisted YouTube demonstration link

## Main Features

- Rule-based extraction for structured/recognizable charge patterns
- AI-assisted extraction for unstructured natural-language inputs
- Validation and confidence/review workflow
- Human approval/rejection control
- Predefined automated capstone test scenarios
- Test evidence for the defined 8-case test pack

## Requirements

- Python
- `google-genai`
- `pydantic`
- A valid Gemini API key and available API quota for AI extraction/tests

Install the required Python packages using:

```bash
pip install google-genai pydantic
```

## API Key Configuration

The API key is intentionally **not included** in this repository.

Configure `GEMINI_API_KEY` as an environment variable before using the AI functionality.

Example on Windows Command Prompt:

```cmd
set GEMINI_API_KEY=YOUR_API_KEY
```

For a persistent Windows environment variable, configure it through Windows Environment Variables rather than storing the key in source code.

## Run the Application

Open a terminal in `04_Source_Code` and run:

```bash
python app.py
```

To run the automated test pack:

```bash
python run_tests.py
```

The AI-assisted tests make live Gemini API requests and therefore require internet access, a valid API key, and available quota. Rule extraction runs locally.

## Demonstration Video

Unlisted YouTube demonstration:  
https://youtu.be/4c2R7rMmiII

## Security and Privacy

This public submission intentionally excludes API keys, OAuth tokens, `credentials.json`, `token.json`, real customer emails, and `__pycache__` files. Example inputs are synthetic/anonymized for demonstration purposes.

## Test Result Scope

The documented **8/8** result applies only to the defined capstone test pack. It should not be interpreted as a claim of universal production accuracy.

## Submission Note

Prepared for the ICAI AI for Chartered Accountants (AICA) Level 2 Capstone Project submission.
