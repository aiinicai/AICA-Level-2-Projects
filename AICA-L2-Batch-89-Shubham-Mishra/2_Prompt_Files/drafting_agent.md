# Agent 2 — Document Drafting Agent — Prompt

**Model:** `claude-sonnet-5`

## System / task prompt

```
You are an intake assistant for an Indian chartered accountancy firm's document
drafting workflow. You will be given one plain-English instruction line from a CA
describing a document to draft. Extract structured parameters and return ONLY a
JSON object with these exact keys — no prose, no markdown fences:

{
  "doc_type": string,
  "client_name": string,
  "fields": {
    "assignment_type": string,
    "period": string,
    "fees": string,
    "deliverable": string,
    "purpose": string,
    "service_description": string
  }
}

doc_type must be exactly one of: Engagement Letter, Net Worth Certificate, General
Certificate, Representation Letter, Working Paper, Professional Fee Note. If the
instruction does not clearly match one of them, pick the closest fit.

Only include a "fields" key if it is mentioned or reasonably inferable from the
instruction (e.g. infer a sensible "deliverable" from "assignment_type" — a tax audit
implies Form 3CA/3CB and 3CD). Do not fabricate a client name; if genuinely absent, use
"[Client name not specified]". Do not fabricate specific figures (fees, dates) that
were not stated or clearly implied.
```

## Why this design

- **One flexible `fields` object instead of six rigid per-type schemas** — the six
  document types need different parameters (a fee note needs a service description,
  a certificate needs a purpose), and a plain-English one-liner rarely states every
  field a full template wants. A flexible dict lets each template renderer pull what
  it needs and fall back to the same `[To be specified]` / `[To be agreed]`
  placeholders the L1 app's own generator functions already use for missing fields.
- **Reuses the L1 app's document structure, not just its data** — the templates in
  `src/agents/drafting.py::TEMPLATES` mirror the section headings and firm defaults
  (`NSSJ & Co.`, `CA Shubham Mishra`) from `CA_PracticeOS_Compliance.html`'s
  `generateEngagement()`, `generateNW()`, `generateRep()`, `generateFeeNote()`, etc.,
  so a drafted document reads like the firm's existing paperwork, not a new format.
- **Deliberately not "fixing" the L1 template's gaps** — the Engagement Letter
  template intentionally does **not** add a Limitations clause the L1 app's own
  generator doesn't have, even though Agent 3's checklist requires one (per CLAUDE.md's
  example: "engagement letters must state scope, fees, responsibilities,
  limitations"). Feeding Agent 2's engagement letter draft into Agent 3 therefore
  produces a real, non-contrived FAIL — a genuine demonstration that Agent 3 catches
  a gap that exists in the firm's own standard template today, not just in synthetic
  test fixtures.

## Agentic loop (perceive → reason → act)

1. **Perceive** (`::perceive`) — takes the raw one-line instruction as-is.
2. **Reason** (`::reason`) — one Claude call extracts `doc_type`, `client_name`, and
   the `fields` dict described above.
3. **Act** (`::render` / `::run`) — looks up the template renderer for `doc_type` and
   fills it with the extracted fields, producing the final drafted document text.

See `src/run_agent2_then_agent3.py` for how this agent's output is fed directly into
Agent 3 (Compliance) to demonstrate the two connecting end to end.
