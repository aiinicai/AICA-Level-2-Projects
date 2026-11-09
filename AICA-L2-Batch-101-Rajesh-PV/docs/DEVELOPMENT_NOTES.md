# Development notes – Judgement Insights Analyser

How the app was refined through rounds of user testing on Windows. Each round lists what the tester reported and what changed.

## Base build
- Structured 14-section analysis, long-judgment sectioning, OCR for scanned pages, editing, Word / PDF export, client emails through Outlook with approval and an audit log.
- **Source Check**: deterministic verification of quotations, citations, case numbers, sections, dates, amounts and paragraph references against the judgment text, with a score and a "Not found" list; re-runs after edits.
- **Consistency Check**: key facts extracted twice (Gemini JSON mode) and compared field by field; disagreements must be confirmed before approval.
- **Paragraph references**: numbered paragraphs detected and marked `[Para N]`; reports cite `(para N)`.
- **Precedent register** (SQLite): save with a PDF copy, search by text / section / status / outcome, duplicate detection by SHA-256, Excel export, dashboard counts.
- **Compare rulings**: structured AI comparison of two register entries, export to Word.
- **Email**: recipient groups (Clients / Employees), client and team versions, SMTP delivery (Gmail App Password, Microsoft 365, Zoho, custom) with the password in the OS vault, audit log.
- **Reliability test kit**: `tools/reliability_eval.py` measures run-to-run agreement and accuracy against an answer key.

## Review round 1
- **Review & Approve** step: key facts (choose Run 1 / Run 2 where the readings disagree), citation, Source Check acknowledgment, approver name. Save and Email are enabled only after approval; edits cancel it.
- **Citation lookup** (optional): Gemini with Google Search suggests a citation for an unreported order, showing its web sources; the reviewer must accept it.
- **Clean outputs**: Word, PDF and email start with Generated on / Case / Citation; no source file, model, processing mode, labels, page numbers or AI footer; justified text.
- **Paragraph references only**: page references removed (pagination differs between publishers; paragraph numbers do not).
- Email: separate Clients and Employees lists and templates; HTML with bold headings, bullets and justified text.

## Review round 2
- **Two Acts tracked separately**: *Sections – Income-tax Act, 1961* and *Sections – Income-tax Act, 2025* are kept apart in key facts, approval, register columns, search filter, Excel export and statistics. A section above 298 can only be a 2025 Act section and is moved automatically; for numbers up to 298 the Act named next to the section in the judgment decides, and doubtful placements are flagged.
- **Citation**: online lookup offered only when the citation box is empty; manual entry; the citation can be added or corrected later from the register (who and when are recorded).
- **Email drafts without recipients**: Outlook drafts and .eml files can be created with 'To' empty.
- **Email account test**: a step-by-step connection test shows exactly where sign-in stops and why.

## Review round 3
- **Key facts never empty**: retried when a reading fails; one good reading is kept; fields still empty are filled from the report and the judgment text (marked ⓘ for checking).
- **One Save ▾ button** (Word / PDF / text / JSON); Review & Approve saves to the register.
- **Register**: filters as you type, *Clear filters*, **Update details…**, **Return for correction**, maker / checker warning when the approver verifies their own entry; content changes on a Verified entry send it back to Draft.

## Review round 4
- **Return for correction** opens a checklist of key details and analysis sections to correct, with a note.
- **Update details** shows every analysis section; items the reviewer ticked are marked in red and shown first; corrections are checked against the judgment PDF stored with the register.
- A Returned entry always goes back to Draft when the preparer saves the correction.
- Drafts without recipients greet 'Dear <<Recipient name>>,'.

## Review round 5
- Flickering buttons in the email window fixed (labels refresh only when something changes).
- Richer email account test (certificate issuer, sign-in offer, security software running).
- Formatted Excel recipient templates and a formatted Excel copy of the audit log.

## Review round 6
- **Gmail App Password** check before connecting; invisible characters copied from Google's page are removed.
- **Email from the register** for a selected entry.
- Windows open in front with the cursor in place; main-window buttons keep a fixed width.

## Review round 7
- **Saved recipient lists**: client and employee lists reopen automatically (stored in this user's app data folder, not in the shared register); *Forget* deletes a list.
- **Audit log repair**: logs with an older 12-column header and newer 14-column rows are read row by row and rewritten with the current header (the original is kept as a backup).

## Review round 8
- **Client emails only for verified entries**: the Client version is blocked until a reviewer marks the register entry *Verified*, checked again at the moment of sending. The Team version can go to employees while the entry is Draft.
- Word / PDF / text / JSON of an unverified entry carry *Status: DRAFT – for internal review*.
- **Mix-up checks**: team material in the Client version blocks approval; client wording in the Team version, identical versions, colleagues in the client list and outsiders in the employee list are flagged.
