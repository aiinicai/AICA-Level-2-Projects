# Prompt File 2 — Development Prompts (how the app was built with AI)

The application was designed and built by the participant working with an AI coding agent (Claude), in the style taught in AICA Level 2 Modules 1, 6 and 10: a clear CA-specific brief, hard constraints stated up front, a written master specification kept as the single source of truth, and short feedback prompts after each release, each checked against a live TallyPrime company.

The prompts below are the participant's own instructions, lightly trimmed for length. Client names that appeared in real-data testing have been removed.

---

## Stage 1 — The original brief (Day 1)

> Build an offline Python desktop app for Windows (PyQt6) for my CA practice. We handle many client companies, each with a large volume of purchase / expense invoices every month, and more than one person in the office uses it.
>
> - Read invoices in any format — PDF, scanned PDF, image, Word, Excel — from a folder per company.
> - Connect to TallyPrime on port 9000 (same PC or LAN). Pull ledgers, groups, stock items, voucher types and voucher history live, and post entries by XML import.
> - Always show Dr / Cr before posting. Nothing should be posted silently.
> - Remember ledger choices per company and suggest them next time; share this memory across the office.
> - TDS, RCM and 17(5) blocked credit are all required; narration on every voucher; bill-wise where the party has it.
> - Use Gemini (cheapest model) for invoice parsing only. Mask PAN and bank details before upload and keep an upload log.
> - GSTR-2B cross-check must never block posting; it only flags.
> - It must be beautiful and faster than typing the entry directly in Tally, or nobody will use it.

## Stage 2 — Hard constraints given to the AI

> My PC has Smart App Control. It blocks unsigned exe files and native libraries. Use only pure-Python libraries, launch through the official Python, and do OCR through Windows' own components.

> Banking is NEVER to be processed by Gemini. Gemini is for invoices only. Make it a hard block in code, with tests — not a setting.

> Reminders and emails should only be drafted, never sent automatically. Keep secrets in the Windows keyring, never in files.

> Don't start building while I am still giving feedback, unless I ask. Before you call a fix done, all tests must pass and it must be checked against real Tally.

## Stage 3 — Feature prompts (examples)

> Add a Bank module: import any Indian bank or credit-card statement (Excel, CSV, PDF), detect the columns or let me map them once, remove what is already in Tally, suggest ledgers and post Payment / Receipt / Contra with bill-wise settlement.

> Add dashboards and controls: a TDS tracker by section with due dates and threshold watch, a GST control panel (Rule 37 reversal, RCM, 17(5), 2B mismatches), AP / AR ageing with drafted reminders, and an Office view of all clients.

> Build a suspicious-transactions repository (red flags) across Income-tax, GST, SFT and banking patterns — cash above Rs 10,000, split payments, duplicate payments, director loans, related parties. Each flag should show evidence and need a reviewer sign-off; it is an indicator, not a conclusion.

> The Bank tab takes a lot of time. I need fast processing of every tab.

## Stage 4 — Testing on a demo company, and fixing what it found

> Prepare complete demo data for a fictional company — Tally masters and vouchers, bank statements in different layouts, supplier invoices with planted errors, employee claims, GSTR-2B, an answer key and a test checklist — so the reviewers can test every module.

> Credit-card payment of HDFC, even though it is a duplicate (already entered as HDFC bank CA payment), was not marked as duplicate when the HDFC CC statement was uploaded. Same with ICICI bank — the contra entry was not alerted as a duplicate.

> I deleted a few hardware invoices and debit notes with stock inventory, as those were not imported correctly. Please enter them in Tally directly.

> Net profit shows 20,31,673 in Tally and not 21,51,673 — check.

## Stage 5 — Look and feel

> I want this to be something extraordinary — 3D labels, mouse hovering, multiple colour themes. The app should look like a paid app, not a free one, yet stay professional.

## Stage 6 — Submission

> I can't submit any real data. Remove the real-data folder without affecting the app.

> Prepare a detailed project submission document: features, majorly offline with Gemini only for invoice parsing (bank and credit card never go to Gemini — strict coding), usefulness for professionals and accountants, technology and libraries used.

---

## What worked (lessons on prompting an AI coding agent)

1. **State constraints before features.** The Smart App Control and "banking never to AI" rules shaped the whole architecture; added later they would have meant rewrites.
2. **Keep a written spec.** A master specification file (`SPEC.md`, included in Supporting Documents) records every decision word for word, so nothing is lost between sessions.
3. **Give feedback with real evidence.** Prompts that named the exact entry, amount and statement got precise fixes.
4. **Verify against the real system.** Every fix was checked against live TallyPrime (via its XML interface and the Tally MCP connector) before being accepted.
5. **One test voucher first.** Posting one voucher and checking it in Tally before a batch avoids bulk mistakes.
