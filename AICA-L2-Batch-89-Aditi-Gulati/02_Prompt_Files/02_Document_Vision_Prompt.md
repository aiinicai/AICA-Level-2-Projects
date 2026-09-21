# Prompt 2 — Document and screenshot review

**Where it is used:** `surakshascan/vision.py` — AICA Level 2, Day 2 method.
**What it does:** reads an image of a school document — an admission form, a
consent slip, CCTV signage, a transport-app screenshot, or a social media post
— and transcribes only what is visible.

## Design principles

- **Transcribe, don't infer.** Where text is unreadable the model must say
  *illegible* rather than guess.
- **Flag uncertainty explicitly** in a dedicated field, so a doubtful reading
  is visibly marked in the report.
- **Structured output,** so the result feeds the same checks as every other
  source.
- **No face recognition.** The prompt asks about the document's text and
  purpose. It never asks the model to identify a child.

## The prompt

```text
You are reviewing a scanned document from an Indian school as part of a data protection readiness review under the DPDP Act, 2023.

Transcribe only what is actually visible in the image. Then answer:
1. What kind of document is this (admission form, consent slip, notice board, CCTV signage, app screenshot, other)?
2. What categories of personal data does it collect or display?
3. Does it contain a consent clause? Quote it exactly if so.
4. Does it identify who to contact about the data?
5. What is illegible or uncertain?

Do not infer text that is not visible. Where you cannot read something, say 'illegible' rather than guessing. Reply as JSON with keys: document_type, data_categories, consent_clause, contact, uncertainty, full_transcription.
```
