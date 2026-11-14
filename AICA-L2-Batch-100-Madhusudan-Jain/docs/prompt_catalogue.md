# Prompt catalogue and AI guardrails

This document records how generative AI is used in the audit assistant, the
prompts, and the controls that keep the model's output reliable. It is the
"prompt engineering" evidence for the capstone.

## Design principle: rules compute, the model writes

Every number, date and legal reference is produced by deterministic Python
rules (pandas) from the society's data. The language model receives those facts
as a JSON context and is asked only to **write** - audit observations,
letters, summaries. It is never asked to decide whether something is a
violation or to compute a figure. This separation is what makes the output
auditable: a reviewer can trace each sentence to a schedule in the workbook.

## System prompt (used on every call)

```
You are an audit manager at a chartered accountancy firm in Maharashtra drafting documents
for the statutory audit of a co-operative housing society under the Maharashtra Co-operative
Societies Act, 1960.

Rules you must follow:
1. Use only the facts, amounts, dates and legal references supplied in the JSON context. Do not
   add any section number, bye-law number, circular, case law or figure that is not in the
   context. If a reference is needed but not supplied, write "[reference to be confirmed]".
2. Write in formal Indian audit English. Amounts in Indian format with "Rs" (e.g. Rs 1,45,000).
3. Never speculate about intent or allege fraud; describe the control failure and its effect.
4. Do not include personal data beyond flat numbers.
5. Return plain text (no markdown headings) unless the task says otherwise.
```

## Task prompts

| Task | Instruction sent with the JSON context | Context fields |
|---|---|---|
| Audit observations | Draft the 'Audit Observations and Rectification Required' section of the statutory audit report. For each finding write one numbered paragraph with: heading, observation (facts and amount), the provision contravened (only from the context), effect, and the rectification required by the committee. Order: High severity first. End with a paragraph on the overall state of internal control. | society, financial year, list of findings (id, module, area, severity, observation, reference, recommendation, amount, evidence) |
| Management letter | Draft a management letter to the Chairman and Managing Committee summarising the control weaknesses and the actions required, grouped under: Member dues and billing; Funds and investments; Expenditure controls; Statutory compliance; Taxation. Close with a request for a written response within 30 days. Formal letter format, under 600 words. | society, date, findings (id, area, severity, recommendation, amount) |
| Reminder letter (per defaulter) | Draft a firm but courteous final reminder letter from the Hon. Secretary to the member of this flat for unpaid maintenance dues. State the amount, the months of arrears, the interest being charged, the 15-day deadline and the consequence under the recovery provision. Under 200 words. | flat number, closing balance, months of arrears, interest rate text, recovery provision text, deadline |
| Governance summary | Write a one-page governance summary for the auditor's file: meetings held, notice and quorum exceptions, action items not complied with, and three recommendations on governance process. Use short paragraphs. | parsed meetings table, open action items |
| Tax note | Write a short tax position note (under 250 words) for the committee explaining the computation, the regime choice and the advance tax default. | computed tax summary, list of provisions relied on |

## Guardrails

1. **Closed-world context.** The model is told to use nothing outside the JSON. Missing references must be written as "[reference to be confirmed]" rather than invented.
2. **Citation verifier.** After each response the code extracts every statutory reference (s./section, bye-law, rule, circular, notification) with a regular expression and checks it exists in the prompt context. Unverified references are appended to the output as a reviewer note and logged. This is the hallucination control.
3. **Data minimisation.** Names, mobile numbers and PANs are excluded from every context. Only flat numbers and amounts travel to the API (DPDP Act 2023, purpose limitation and data minimisation).
4. **Refusal and fallback handling.** The call uses the server-side fallback feature; if the model declines or the API fails, the deterministic template produces the document so the audit is never blocked.
5. **Full logging.** Every prompt, response, source (model or template) and flagged citation is written to `output/ai_prompt_log.md` for the engagement file.
6. **Human in the loop.** All drafts are marked as drafts in the workbook; the signing partner reviews them against the schedules before issue.

## Model settings

- Model: `claude-opus-5-5` via the official Anthropic Python SDK, streaming, adaptive thinking (default), `max_tokens` sized per task (1,500 for letters up to 12,000 for the observations section).
- Enabled with the `--ai` flag; credentials from `ANTHROPIC_API_KEY` or an `ant auth login` profile. Without credentials the tool runs fully offline on templates.

## Prompting lessons applied from the course

- Role + task + constraints + format structure in every prompt.
- Few-shot not needed because the context is structured; instead the output format is specified explicitly.
- Chain of custody over chain of thought: the prompt forbids new facts rather than asking the model to reason about law.
- Iteration: early drafts cited bye-law numbers from the model's memory; the citation verifier and the "[reference to be confirmed]" rule were added after that was observed in testing.
