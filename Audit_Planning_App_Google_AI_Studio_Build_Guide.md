# Audit Planning Workbench — Google AI Studio Build Guide

This document is a companion to the working prototype already delivered in the chat (the "Audit Planning Workbench" page). That prototype implements the full workflow and the calculations, but its "AI Assist" and "ICAI Knowledge Base" panels are rule-based simulations — they do not call any external AI model, because that requires your own Gemini API key and billing.

This guide gives you everything needed to (a) recreate or extend the same application inside **Google AI Studio → Build**, and (b) wire the AI Assist and Knowledge Base panels to a real Gemini model, plus retrieval-style access to the ICAI Standards on Auditing.

---

## 1. How to use this document

1. Open [Google AI Studio](https://aistudio.google.com/) and choose **Build** (the app-building mode, sometimes shown as "Build apps with Gemini").
2. Paste **Section 2 — Master Build Prompt** into the Build prompt box as your first message. It describes the whole application in one shot, the way AI Studio expects.
3. Once the first scaffold is generated, use **Section 3 — Module Specifications** as follow-up prompts, one module at a time, to fill in detail AI Studio's first pass typically simplifies (risk logic, materiality formulas, the memo generator).
4. Use **Section 4 — Wiring a Live Gemini Model** to replace the rule-based "AI Assist" buttons with real `generateContent` calls, and to add retrieval over the actual SA 315 / SA 240 / SA 330 / SA 320 text.
5. Section 5 covers data persistence (so a preparer and reviewer can share one file), and Section 6 is a punch-list of what to sanity-check before you rely on it for a real engagement.

---

## 2. Master Build Prompt (paste this first)

```
Build a single-page web app called "Audit Planning Workbench" for a chartered
accountancy firm to plan statutory audits under the Indian Standards on
Auditing (SA 315 Revised, SA 240, SA 330, SA 320), issued by ICAI.

Layout: a left sidebar lists 13 numbered planning stages plus an "Overview"
dashboard at the top; a sticky top bar shows the client name, financial year,
overall completion percentage, and the three materiality figures (Overall
Materiality, Performance Materiality, Clearly Trivial threshold). The main
panel shows the active stage's form.

The 13 stages, in order:
1. Engagement & Client Acceptance/Continuance — client details plus a
   Yes/No/N.A. checklist (independence, competence, integrity of management,
   predecessor auditor communication, KYC/AML, going-concern indicators,
   group instructions) and an overall acceptance conclusion.
2. Understanding the Entity (SA 315) — free-text sections: nature of
   business, ownership & governance, objectives & strategies, industry
   factors, regulatory factors, other external factors, performance
   measures, and entity-level risks arising from all of the above.
3. Control Environment (SA 315) — a table of 8 standard control-environment
   factors (integrity/ethics, competence commitment, board/audit committee
   oversight, management philosophy, organisational structure, authority
   assignment, HR policies, whistle-blower mechanism), each rated
   Effective/Partially Effective/Ineffective with notes, plus an overall
   conclusion.
4. Information Systems — a table of IT systems used by the entity (name,
   purpose, criticality, notes), plus free text on reliance on IT and
   cyber/IT-general-control observations.
5. Process Identification (SA 315) — a table of significant business
   processes (name, owner, Significant/Routine, IT system used, notes).
6. Walkthroughs (SA 315) — one row per process: performed (checkbox), date,
   performed by, observations, control gaps noted, conclusion.
7. Risk Assessment at FS Line-Item Level (SA 315) — a table of ~24 standard
   Schedule III financial statement line items (Revenue, Cost of Materials,
   PPE, Inventories, Trade Receivables, Borrowings, Related Party
   Transactions, etc.), each with: relevant assertions (multi-select chips:
   Existence, Completeness, Accuracy, Valuation, Rights & Obligations,
   Cutoff, Classification), an INHERENT RISK dropdown with exactly three
   options — Low / Medium / Significant — a rationale text field, and a
   quantitative-significance field.
8. Fraud Risk Assessment (SA 240) — two standing, always-present risks
   (revenue recognition presumption, which can be marked "rebutted" with a
   documented rationale; and management override of controls, which cannot
   be rebutted), each with a planned-response field; plus a table of
   additional fraud risks tied to specific FS line items (fraud type,
   identified checkbox, rationale, planned response), with a button that
   suggests a rationale based on which line item is selected.
9. Control Risk & Rating (SA 315) — a register: risk/line item, controls
   identified, Probability (Low/Medium/High), Magnitude (Low/Medium/High),
   a SYSTEM-SUGGESTED rating computed as Probability × Magnitude on a 3×3
   matrix (sum of scale positions 0/1 -> Low, 2 -> Moderate, 3/4 ->
   Significant), and a FINAL RATING dropdown (Low/Moderate/Significant)
   that defaults to the suggestion but can be overridden with a mandatory
   rationale, plus an auto-computed "is this a significant risk" flag.
10. Materiality (SA 320) — pick a benchmark basis (Profit before Tax /
    Revenue / Net Assets / Total Assets), enter the benchmark amount and an
    Overall Materiality percentage (show typical practice ranges as hints:
    5-10% of PBT, 0.5-1% of revenue, 1-2% of net/total assets — and note
    these are practice conventions, not fixed by the standard), then a
    Performance Materiality percentage of OM (typical 50-75%) and a Clearly
    Trivial percentage of OM (typical ~5%, referencing SA 450). Compute and
    display all three amounts live, plus a rationale text box.
11. Audit Strategy (SA 330) — for each risk carried over from the Control
    Risk register: checkboxes for Test of Controls / Test of Details /
    Analytical Procedures, an extent dropdown (Limited/Moderate/Extensive),
    and nature/timing notes. Show a warning when a Significant risk has no
    Test of Details ticked, since SA 330 expects a substantive response to
    significant risks.
12. Planning Memo — an auto-compiled formatted document pulling from every
    prior stage (background, acceptance conclusion, entity understanding,
    materiality figures, significant risks & fraud conclusion, IT strategy,
    overall audit strategy, and a status conclusion), editable section by
    section, with a "regenerate this section" control that restores the
    auto-generated text.
13. Sign-off & Review — two columns: Preparer (name, designation, date,
    a declaration checkbox) and Reviewer (name, designation, date, a list
    of review notes each with an Open/Cleared status and a preparer
    response field, an overall conclusion dropdown — Planning Approved /
    Approved with Conditions / Returned for Revision — and concluding
    remarks). Show a status banner (Draft / Pending Review / Approved /
    Returned) derived from these fields.

Overview dashboard: stat tiles for overall completion %, walkthroughs
completed, FS line items risk-rated, and audit responses defined; a
per-stage progress list; a Low/Moderate/Significant risk-count heat strip;
a materiality snapshot; and a list of specific outstanding/pending items
generated from the data (e.g. "Assess inherent risk for Trade Payables").

Visual style: a professional, understated "audit workpaper" look — warm
paper background, a serif display face for headings, a clean sans for body
text, a monospace face with tabular numerals for all currency/percentage
figures, and three distinct semantic colours for Low/Moderate/Significant
that are separate from the main accent colour. Support both light and dark
mode.

Pre-populate the app with one illustrative sample engagement (a mid-size
Indian textile manufacturer, "Zenith Fabrics Private Limited", FY 2025-26)
so the workflow is visible immediately, clearly labelled as a sample, with
an option to create a new blank engagement.
```

---

## 3. Module specifications AI Studio tends to under-build

Paste these as follow-up turns once the first scaffold exists — AI Studio's first pass usually gets the layout right but flattens the logic in these three places.

**Risk matrix logic**
```
Implement combineRisk(probability, magnitude) exactly as: map Low/Medium/High
to 0/1/2, sum the two, and return "Low" for a sum of 0-1, "Moderate" for a
sum of exactly 2, and "Significant" for a sum of 3-4. This must run live as
either dropdown changes, updating a "Suggested rating" badge next to an
editable "Final rating" dropdown that starts equal to the suggestion. Track
whether the user has manually overridden the final rating (a boolean flag
per row) so that later changes to probability/magnitude don't silently
overwrite a deliberate override.
```

**Materiality formulas**
```
overallMateriality = benchmarkAmount * (omPercent / 100)
performanceMateriality = overallMateriality * (pmPercent / 100)
clearlyTrivialThreshold = overallMateriality * (ctPercent / 100)
All three must recompute live on every keystroke in the benchmark amount or
any percentage field, and must be reflected in the sticky top bar across
every screen of the app, not only on the Materiality screen itself.
```

**Progress / dashboard math**
```
For each of the 13 stages, define "done" and "total" counts from the
underlying data (e.g. for Risk Assessment: number of FS line items with a
non-empty inherentRisk field, divided by the total number of line items),
not from a single "is this tab complete" boolean. Compute each stage's
percentage as done/total, and the overall completion percentage as the
average of all 13 stage percentages. Recompute after every field edit.
```

---

## 4. Wiring a live Gemini model (replacing the simulated AI)

The prototype's "AI Assist" buttons and "ICAI Knowledge Base" panels currently run on hand-written lookup tables in the page's own JavaScript — no network call, no API key, works offline. Google AI Studio apps run Gemini through the `@google/genai` SDK, which AI Studio wires up for you with your API key when you build there. Ask AI Studio to make these three changes:

**a. Fraud-risk / risk-rationale suggestions**

Replace the keyword-matching `suggestFraudHint()` function with a real call, e.g.:

```js
import { GoogleGenAI } from "@google/genai";
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

async function suggestFraudHint(lineItemName, entityContext) {
  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash",
    contents: `You are assisting an Indian statutory auditor applying SA 240
      (fraud) during planning. The financial statement line item is
      "${lineItemName}". Entity context: ${entityContext}.
      In 2-3 sentences, identify the most relevant fraud risk
      considerations for this line item (fraudulent financial reporting
      and/or misappropriation of assets), referencing the applicable SA 240
      concept (incentive/pressure, opportunity, rationalisation) without
      inventing entity-specific facts you were not given.`,
  });
  return response.text;
}
```

Use whichever current Gemini model is available in your AI Studio project at build time — check the model picker there rather than hardcoding a version, since model names and availability change.

**b. "ICAI Knowledge Base" panels**

There is no public API for ICAI's own knowledge base, so "grounding" here means giving Gemini the actual standard text as context, not open web search. Two practical options, in increasing order of effort:

- *Simplest:* keep the static paraphrased summaries already in the prototype (they are safe to ship — they paraphrase, not quote, the standards) and add a "Explain further" button that sends that static summary plus the user's specific question to Gemini for elaboration.
- *Better:* obtain the official ICAI text of SA 315, SA 240, SA 330 and SA 320 (from the ICAI website or a licensed publication — the standards are ICAI copyright, so do not scrape or redistribute them), upload the PDFs as files in your AI Studio project, and use Gemini's file/document input so the model answers questions grounded in the actual clauses, e.g.:

```js
const file = await ai.files.upload({ file: "SA_315_Revised.pdf" });
const response = await ai.models.generateContent({
  model: "gemini-2.5-pro",
  contents: [
    { role: "user", parts: [
      { fileData: { fileUri: file.uri, mimeType: "application/pdf" } },
      { text: `Answer strictly from the attached standard. Question: ${userQuestion}` }
    ]}
  ],
});
```

This keeps the model's answers tied to the actual clause text instead of its own training-data recollection, and lets you cite a paragraph number back to the user.

**c. Planning memo drafting assist**

Add a "Draft with AI" button on the Planning Memo screen per section, sending the same inputs the rule-based `autoMemoText()` function already uses (client name, entity narrative, materiality figures, significant-risk list) as structured context, and asking Gemini to produce a more polished paragraph in the same place the auto-generated text currently goes. Keep the existing rule-based generator as the default/offline fallback so the app still works for a user without an API key configured.

**Cost and access note:** every live call above is billed to whichever Google account's API key is configured in your AI Studio project, and needs that project to have the Generative Language API enabled with billing set up. There is no way to make these calls without an API key you control.

---

## 5. Shared preparer/reviewer data

The prototype already persists to a shared, realtime document store (Claude's Artifact `db` capability) so a preparer and reviewer opening the same link both see the same data. If you rebuild in AI Studio instead, use **Firebase Firestore** (AI Studio integrates with Firebase directly) with one document per engagement holding the whole planning-file JSON, and a Firestore `onSnapshot` listener so the reviewer's screen updates live as the preparer edits. Keep the same last-writer-wins expectation — this is a planning workbook for a small team, not a system that needs operational transforms or field-level locking.

---

## 6. Before you rely on this for a real engagement

- Every SA reference and materiality percentage range in both the prototype and this guide is a paraphrase for planning-aid purposes, not a substitute for reading the actual ICAI-issued Standards on Auditing, and not a substitute for your firm's own audit methodology manual.
- The 3×3 probability/magnitude matrix and the materiality percentage defaults are common practice conventions, not requirements of the standards themselves — your firm's methodology may specify different ones; treat every default in this app as a starting point the engagement partner should confirm.
- "Significant risk" classification in the app is a planning aid; the final judgement always rests with the engagement team, as SA 315 requires.
- Nothing in this app or guide constitutes legal, audit, or professional advice — it is a planning-documentation tool only.
