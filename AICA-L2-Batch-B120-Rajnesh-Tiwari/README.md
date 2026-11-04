# AuditSense

AuditSense is an educational AICA Level 2 capstone project: an AI-assisted reviewer for fictional banking internal-audit findings.

It helps identify missing or weak Condition, Criteria, Cause, Impact, and Recommendation elements. It is a drafting aid only. It does not replace audit evidence assessment or professional judgment.

## Current status

Day 6 is complete. The project specification is available at [`docs/project-specification.md`](docs/project-specification.md), and the Streamlit interface is in [`app.py`](app.py).

## Run the interface

Install the packages listed in `requirements.txt`, then start the application with:

```text
streamlit run app.py
```

The current version loads fictional samples, validates the dataset schema, performs local pre-flight checks, and sends the entered fictional finding to a structured LLM review only after the user confirms the data is fictional.

## Data policy

Use only fictional data authored for this demonstration. Do not add customer information, real bank information, real policies, or findings derived from employment records.

## Planned stack

- Python
- Streamlit
- LLM API with structured JSON output
- Pandas for synthetic data and evaluation
- Optional n8n workflow

## Planned build sequence

1. Finalize scope and evaluation criteria
2. Create labelled synthetic findings
3. [x] Build the Streamlit interface
4. [x] Add the LLM review layer
5. [x] Add validation and guardrails
6. [x] Add evaluation workflow
7. Evaluate against the synthetic dataset
8. Optionally add n8n
9. Document and polish
10. Test and prepare the demonstration
