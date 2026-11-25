# NOTICE-MATE — Project Summary

## Project

**NOTICE-MATE: a local-first workbench for organising responses to Indian income-tax notices**  
Author: **CA Kritika Dubey**  
Batch: **AICA Level 2 Batch 112**  
ICAI Membership No.: **483431**  
Programme: **AICA Level 2 Capstone**

## Problem

Responding to a detailed tax notice can require a CA to read the notice, locate relevant records across many files, connect evidence to each query, identify missing or inconsistent facts, and prepare a structured draft. A disconnected manual process makes it harder to track what supports each paragraph and what still needs confirmation.

## Proposed solution

NOTICE-MATE provides a guided desktop-style case workspace. It reads a notice and supporting records on the user's computer, organises the notice into issues, suggests document-to-query matches, supports reconciliation and research notes, and helps prepare an editable response for professional review.

## Intended users

Chartered Accountants and their authorised staff preparing a draft response for a taxpayer. The taxpayer or CA remains responsible for checking the facts, selecting enclosures, verifying applicable law and approving the final response.

## Workflow

1. Upload a notice and optionally supporting records.
2. Review the extracted assessee and notice details.
3. Review issues, evidence matches, record availability and contradictions.
4. Optionally reconcile selected records.
5. Review research propositions and sources.
6. Prepare and edit a query-wise reply draft.
7. Complete CA review and export the approved draft.

## AI and retrieval

The optional AI drafting path retrieves query-relevant extracts from uploaded records and combines them with the notice question, recorded factual position, evidence status and any verified legal points. An AI provider is not bundled or enabled in this capstone copy. The normal reply path is record-based/template drafting and can be brief where evidence is missing or not linked; this limitation must be disclosed during demonstration.

## Privacy and safeguards

- Fictional records are supplied for demonstration; no real client records are included.
- The running app stores its working documents and database locally.
- API keys and runtime case data are excluded from this repository copy.
- Cloud drafting is optional and gated by a redacted preview and user approval when configured.
- Drafts are not final professional opinions and require independent CA review.

## Scope and limitations

This is a prototype for case workflow and draft assistance, not a tax filing system, legal research database, or replacement for professional judgement. OCR quality depends on scan quality and installed OCR tools. Extraction and document matching can be wrong or incomplete. The offline reply can be too brief, and the optional AI path requires a separately configured provider or local model. The application does not submit responses to government portals.

## Demonstration data

Use only the fictional records in `sample-files/` and `sample_data/`. Do not substitute client data in a public capstone repository or recorded video.


