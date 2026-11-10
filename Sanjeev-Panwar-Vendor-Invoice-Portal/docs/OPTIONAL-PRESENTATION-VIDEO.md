# Optional 4-5 minute presentation / narration

The supplied upload guide does not require a video or slides. This outline is optional; no video has been recorded.

1. Title (0:00-0:25): Add your public name. "This Django Vendor Invoice Portal organises vendor registration, invoice submission and Finance review. I will use fictional records."
2. Problem/workflow (0:25-0:55): "Vendors need a controlled way to submit invoices and purchase orders. Finance approves vendor access, verifies extracted fields and exports approved invoices."
3. Browser demo (0:55-2:45): Register a synthetic vendor, show approval gating, approve as Finance, submit the generated invoice/PO and inspect the reference/fields. "The extracted values are suggestions; Finance must verify them." Show approval and staging CSV export.
4. Architecture (2:45-3:20): "Waitress serves Django locally. Django stores metadata in a demo SQLite database and files behind authorized download views. PDF extraction and optional OCR run locally."
5. AI/testing (3:20-4:00): "ChatGPT assisted project development and Codex assisted submission preparation. This application's runtime uses local extraction and heuristics, not a generative AI API. Seven regression checks passed in an isolated Python 3.12 test environment; exact Python 3.13 installation and scanned-document OCR still need verification."
6. Limits/close (4:00-4:40): "This is a prototype. Extraction depends on layout, the CSV is an ERP staging format, and production use needs further security and consistency work. The repository includes sanitized source and instructions."

Suggested slides mirror these six steps: objective, workflow, screenshots/demo, architecture, verification/AI disclosure, limitations. Replace narration with your own tested results after a rehearsal. Do not claim a demonstration succeeded if it did not.

Record only the local browser window, using an available recorder. Hide passwords, personal identity, notifications and unrelated windows. Review every frame and audio. Save the video outside the project folder; use a sanitized share link if desired instead of committing a large MP4.
