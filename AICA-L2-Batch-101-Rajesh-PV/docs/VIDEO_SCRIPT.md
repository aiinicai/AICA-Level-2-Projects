# Demo video script (about 12-15 minutes)

Use `examples/Fictitious_Sample_ITAT_Order.pdf` (invented data) and a dummy recipient list. Never show a real API key, client name or email address.

| # | Time | Show on screen | Say |
|---|---|---|---|
| 1 | 0:00 | Title slide | Who you are, batch, project name; the problem: litigation teams read many orders, summaries are not reused, AI can misquote and is not repeatable |
| 2 | 1:00 | README "Technology and architecture" table + docs/ARCHITECTURE.md diagram | Front end CustomTkinter, back end Python, AI Gemini via google-genai, database SQLite, secrets in keyring, email via Outlook/SMTP/.eml, distribution through GitHub - no server |
| 3 | 2:30 | App start: register location prompt, API key, Test API Key, ↻ models | Where the register lives (shown in header badge); free API key from AI Studio; key stored in Windows Credential Manager, never in a file |
| 4 | 3:30 | Upload the sample PDF; options (para references, consistency check) | Paragraph detection - why para numbers, not page numbers (Taxmann / TMI / official copies paginate differently); Double-check key facts |
| 5 | 4:30 | Analyze ("Analysis complete"); Summary and Full Report tabs | 14 sections; green [Court Finding] vs red [AI Observation] labels are for the reviewer only; (para N) references |
| 6 | 6:00 | Source Check tab | Every quote, citation, section, date, amount and para reference looked up in the judgment by Python - show a "Not found" item and explain why it matters |
| 7 | 7:00 | Review & Approve: pick Run 1 / Run 2 where red, citation lookup, Source Check tick, save to register, approve | Why we do not trust one run; citation lookup shows its web sources and is only a suggestion; Save / Word / PDF / Email stay disabled until approval |
| 7b | 8:00 | Word and PDF output | Clean output: Generated on, Case, Citation; no labels, page numbers or AI footer; justified |
| 8 | 8:30 | Register window: type section 68 (filters as you type), open summary, Update details, Return for correction, Mark verified | Knowledge bank; maker / checker: preparer approves (Draft), reviewer verifies or returns; duplicate detection by PDF fingerprint |
| 9 | 9:30 | Select two entries → Compare | Structured comparison; agreement, conflict, precedential weight; export to Word |
| 10 | 10:30 | Email window: separate Clients and Employees lists, Send to Both, client vs team tabs, preview | Labels highlighted in the editor but removed from the email; HTML with bold headings and bullets; Gmail App Password and 465→587 fallback; Send test to me; audit log |
| 11 | 12:00 | `prompts.py`, `verifier.py`, `consistency.py` in an editor | The prompts and the checks - what each does and why |
| 12 | 13:00 | `python -m pytest` and `tools/reliability_eval.py` results sheet | Automated tests; measured agreement and accuracy on your test set |
| 13 | 14:00 | Closing slide | Limitations (OCR quality, long judgments, free-tier data use, not legal advice), future work |
