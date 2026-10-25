# 1. Claude Skill: GST SCN Reply Drafter

`gst-scn-reply-drafter/SKILL.md` is the Skill. `gst-scn-reply-drafter.zip` is the same folder zipped, ready to
upload as a custom Skill in Claude.

## What it does

The Skill makes Claude work like a careful junior who is not allowed to guess:

1. **Hard rules first.** Use only facts from the notice or from documents the user supplied; never fill a gap
   from assumption; cite sections, circulars and judgments only from authentic sources; present the result as a
   draft for the Consultant's review.
2. **Intake questions (Step 0).** Service date, reply and hearing dates, arguments to avoid, other proceedings on the
   same issue, GSTR-9 status and turnover, documents available. Claude stops until these are answered.
3. **Extraction table (Step 1).** SCN number and date, authority, section, years, head-wise demand, each
   allegation in the notice's own words, RUD, hearing date. Anything missing is marked "not stated in notice".
4. **Authentication and jurisdiction (Step 2).** DIN and signature, officer's competence, service, hearing,
   sufficiency of particulars: each reported as "found", "not found" or "needs confirmation".
5. **Limitation, year by year (Step 3)** under sections 73, 74 and 74A, with the arithmetic shown, and a test of
   whether a section 74 notice states real foundational facts of fraud, wilful misstatement or suppression.
6. **Numbers (Step 4), exemption and threshold check (Step 5), issue-wise reply (Step 6), grounds checklist (Step 7),
   prayer and annexures (Step 8).**
7. **Output order.** Questions, then extraction table, then draft, then a verification list that marks every
   section, date, amount, notification and authority as "from notice", "from user" or "from authentic source".

## How to try it

1. In Claude, add `gst-scn-reply-drafter.zip` as a custom Skill (Settings, then Skills).
2. Start a chat, attach `../5_samples/sample_scn_text.pdf` and write: *"Use the SCN skill to analyse this notice."*
3. Claude should first ask the intake questions and stop. Answer them from `../5_samples/demo_intake_answers.txt`.
4. Check that the extraction table and the year-wise limitation lines match
   `../5_samples/expected_output/check_scn_result_with_text_pdf.txt` (the standard GSTR-9 due dates; Claude should also say that
   extension notifications under section 168A still have to be verified).

## Design notes

* The reply is written in flowing paragraphs without "Facts / Findings" sub-headings, as an advocate would write it.
* Judgments: court, case name, case number, date and paragraph, with the point decided. A judgment known only
  from a news summary is not used; Claude asks for the copy.
* The Skill carries a short reference note on Madhya Pradesh pecuniary limits, marked "confirm against current orders".
