# Video script — 8 minutes

The brief requires the video to show **both the participant's face and the
technical content**. Record with the camera picture-in-picture in a corner
for the whole runtime. Record in two takes and cut; do not attempt a single
continuous run.

Upload unlisted to YouTube or Google Drive, set sharing to **Anyone with the
link — Viewer**, and open the link in an incognito window before submitting
it to the Google Form.

---

### 0:00 — 0:45 · The problem, from the practice
*Camera full frame. No screen share yet.*

Introduce yourself and the firm. Then the problem in one sentence: every
statutory audit begins with the same work — mapping a trial balance to
Schedule III, computing eleven ratios that MCA made mandatory in 2021,
testing journal entries under SA 240, and working through twenty-one CARO
clauses. It is identical across clients, it consumes the first week of every
engagement, and it is done by hand.

### 0:45 — 1:30 · Architecture
*Share the architecture diagram from `docs/architecture.md`.*

Say the governing rule out loud, because it is the point an evaluator who is
a CA will test you on:

> The engine computes. The model writes prose. Nothing else.

Explain why: a Chartered Accountant signs the report, so every figure must be
traceable to a calculation that can be re-performed.

### 1:30 — 2:30 · Ingest and mapping
*Open the app. Click "Use the sample client".*

State clearly that the client is fictitious and no real client data is used
anywhere in the project.

Show the summary tiles. Then open **Mapping queue** and make the important
point: 59 of 61 ledgers were mapped on the account code and the engine says
nothing about them. Two are in the queue — one mapped on its name, one it
could not map at all. Show that it returned `UNMAPPED` rather than guessing.

### 2:30 — 3:30 · The balance sheet that does not tie
*Open **Statements**, then point at the reconciliation banner.*

This is the strongest thirty seconds in the demo. The balance sheet is out by
exactly Rs 4,20,000 — precisely the amount sitting in the suspense account
the engine refused to classify. Say what a lesser tool would have done:
forced the difference to a rounding line and produced statements that tie and
are wrong.

### 3:30 — 4:45 · The eleven ratios
*Open **Ratios**.*

Cite the authority: MCA notification G.S.R. 207(E) dated 24 March 2021,
applicable from FY 2021-22. Four ratios moved beyond 25 per cent and must be
explained in the notes.

Open one card and read the numerator and denominator off it. Point out that
the movement is shown in neutral colour — whether a fall in the debt-equity
ratio is good is the auditor's judgement, not the tool's.

### 4:45 — 5:45 · Journal entry testing
*Open **Journal entries**.*

SA 240 requires the auditor to test journal entries for management override.
Walk the six routines and the flag rate on each — all under one per cent, so
the output is a work programme rather than a haystack.

Show the Benford chart. The population conforms, so the departures the other
routines found are what matter. Say the sentence that shows judgement: **a
flag is a selection for examination, not a finding.**

### 5:45 — 6:30 · Materiality, sampling and CARO
*Open **Sample**, then **CARO 2020**.*

Show the warning: the computed sample covers 51 per cent of the population,
so the tool says sampling is not an efficient response here and points to
controls reliance or SA 520 analytical procedures. A tool that handed over a
466-item programme without saying that would be worse than useless.

Then CARO: all twenty-one clauses, eight pre-populated from the books, none
of them answered. Say why: the tool never concludes on a clause.

### 6:30 — 7:15 · Drafts, automation and deployment
*Open **Drafts**, click Generate. Then the n8n canvas, then a phone.*

Show the memorandum and one ratio note. Point at the bracketed instruction:
`[Management to state the commercial reason for the movement.]` — the prompt
forbids inventing a reason.

Show `prompts/` in the repository: four versioned system instructions with
changelogs recording what was tightened and why.

Show the two n8n workflows and an execution log. Then install the PWA on a
phone and download the Excel workpaper.

### 7:15 — 8:00 · Limitations and close
*Camera full frame.*

Name what it does not do, without being asked: Division I only, no Ind AS, no
audit opinion, no conclusion on any clause, and no verification of any
balance — it analyses what the books say, and the evidence remains the
auditor's to obtain.

Close by tying each piece to the day of Level 2 it came from: agents and
prompt engineering from Day 1, the Gemini system-instruction pattern from
Day 2, Python and the libraries from Day 3, the PWA and deployment from
Day 4, n8n from Day 5.
