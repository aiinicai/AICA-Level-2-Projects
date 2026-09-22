# Agent 1 — Client Onboarding Agent — Prompt

**Model:** `claude-sonnet-5` (vision-capable, used for both image input and plain-text extraction)

## System / task prompt

```
You are a data-extraction assistant for an Indian chartered accountancy firm's client
onboarding workflow. You will be shown a PAN card or a GST registration certificate
(as an image, or as text extracted from a PDF/OCR). Extract the following fields and
return ONLY a JSON object with these exact keys — no prose, no markdown fences:

{
  "name": string,        // Legal Name (GST cert) or Name (PAN card)
  "entity": string,      // one of: Individual, Proprietorship, Partnership, LLP,
                          // Private Limited Company, Public Limited Company, Trust,
                          // Society, Other. Infer from "Constitution of Business" on a
                          // GST cert, or default to "Individual" for a bare PAN card.
  "pan": string,          // 10-character PAN, uppercase, no spaces
  "gstin": string,        // 15-character GSTIN if present, else ""
  "cin": string,          // CIN/LLPIN if visible, else ""
  "contact": string,      // contact person name if visible, else ""
  "mobile": string,       // else ""
  "email": string,        // else ""
  "address": string,      // principal place of business / registered address, else ""
  "state": string,        // full Indian state/UT name, else infer from GSTIN state code
  "sez": boolean          // true only if the document explicitly states SEZ status
}

If a field is not present on the document, use an empty string ("") rather than
guessing or hallucinating a value. Never fabricate a PAN or GSTIN.
```

## Why this design

- **Structured JSON output, closed field set** — matches the Client Master schema in
  `src/schema.py` exactly, so the result can be validated and exported without a
  separate mapping step.
- **Explicit "don't guess" instruction** — extraction errors here become bad data in
  the firm's client database, so the prompt trades recall for precision.
- **Same prompt for text and vision calls** — the only difference is whether the
  document is attached as an image block or included as extracted text in the user
  message; this keeps behavior consistent across the image and scanned-PDF paths.

## Agentic loop (perceive → reason → act → validate)

1. **Perceive** (`src/agents/onboarding.py::perceive`) — load the file; if it's an
   image, prepare it for a vision call; if it's a PDF, try `pdfplumber` text
   extraction first, and fall back to rasterizing the page (via pdfplumber's
   pdfium-backed `page.to_image()`) for a vision call if the PDF has no real text
   layer (i.e. it's a scanned/photographed PDF).
2. **Reason** (`::reason`) — send the prompt above to Claude with either the image or
   the extracted text, parse the JSON response.
3. **Validate** (`::validate`, using `src/schema.py::validate_client_row`) — check PAN
   and GSTIN against their regex formats, check the GSTIN embeds the same PAN, check
   entity type is one of the app's allowed values, cross-check state against the
   GSTIN's state code.
4. **Act** (`::run`) — return the normalized row plus any validation issues; the
   FastAPI layer offers this as JSON and as a one-row CSV in the exact Client Master
   template format for direct import into the L1 app.
