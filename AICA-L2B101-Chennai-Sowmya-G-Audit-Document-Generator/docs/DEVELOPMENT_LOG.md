# Development Log: how the project was built with AI

The project was built in one working session with an AI assistant (Claude). It started
from a classroom assignment, "create an application of your choice from what you have
learnt", and was refined over many prompts. Each round below shows what I asked for and
what changed. The requirements and professional judgment are mine; the AI wrote and
tested the code.

| Round | My prompt (summary) | What was built or changed |
|---|---|---|
| 1 | Suggest an application idea in a professional context | Ideas: tax notice reader, due-date tracker, and others |
| 2 | *"Can I make an MRL, independent audit report generator?"* | Design: inputs, opinion logic (SA 700/705/706), MRL (SA 580) |
| 3 | *"I am using IDLE. Generate one for IDLE."* | Question-and-answer script creating the report and MRL in Word |
| 4 | *"Create a separate window to collect details and output folder to save"* | tkinter form window, folder picker, validation |
| 5 | *"Collect company name, CIN, registered office, constitution from MCA master data PDF"* | Button to read the MCA PDF and fill the fields |
| 6 | Shared my firm's audit-file Excel template. *"Include letter of engagement, DSC authorisation letter. Engagement letter and audit report on auditor's letterhead. CARO report missing. Only AS, not Ind AS."* | Four documents; letterheads with CA logo; full CARO 2020 annexure with tick-boxes; IFC annexure; Ind AS removed; firm's own engagement and DSC wording |
| 7 | Shared my model Letter of Representation. *"Don't ask where books of accounts are maintained. State AI will be used but confidential data redacted. Leave depreciation, bank balances and related party transactions blank."* | AI and redaction clause (DPDP Act); MRL rebuilt on the firm's model with blank tables and yellow highlights |
| 8 | *"Don't take the books-of-account address or director designation and category. Keep spacing as in master data. Ask whether audit trail is maintained and change the MRL wording."* | New PDF reader (word positions); audit-trail question with 3 answers driving the MRL **and** the report |
| 9 | Shared a redacted real MCA PDF. *"Registered office is still not taken properly."* | Found the cause: MCA centres multi-line values, so the address starts above its label. Values now go to the label with the nearest vertical centre |
| 10 | *"Can we use Streamlit to make it run on any system?"* | Browser version sharing the same engine; optional password for online use |
| 11 | *"Convert to exe so my team can use it without installing Python"* | Exe-ready app (bundled logo, saves to Documents); fixed a packaging bug found by testing; GitHub Actions build |
| 12 | *"Help me test and upload for capstone submission"* | Shared engine + two screens; 232 automated tests; dummy MCA PDFs; sample outputs; this documentation |

## Lessons learnt

- **Real documents beat assumptions.** The registered-office bug only appeared on the
  real MCA printout. Sharing a *redacted* copy was enough to find the cause and to build
  dummy copies of the layout for testing.
- **Professional templates matter.** Building on the firm's own engagement letter, DSC
  letter and representation letter produced documents that fit the practice better than
  generic templates.
- **Consistency across documents.** One answer, such as the audit trail status, must
  change several documents together: the report's Rule 11(g) clause, the clause 2(b)
  exception and the representation letter.
- **Testing finds real bugs.** The automated tests and the exe smoke test found four
  defects before release (see `TEST_REPORT.md`).
- **Confidentiality by design.** Local desktop or exe use, an AI and redaction clause in
  the engagement letter, and no client data in the repository.
