# Prompt 4 — Development prompts

The prompts used to build SurakshaScan with an AI assistant (Claude, in
Cowork), in the order they were given. Each is followed by what it produced
and, where it matters, what it taught.

The point of recording these is the AICA Level 2 safe working method: define
the deliverable, handle confidential data deliberately, require sources, ask
for uncertainty, review against originals, and approve external actions
separately. Several of the prompts below are exactly those steps.

---

## Stage 1 — Starting point

> **Prompt:** *"Want to upgrade this project for AICA Level 2 Capstone."*
> (with the compiled `SurakshaScan.exe` from version 1 attached)

**Produced:** the v1 source was recovered from the executable by extracting
the PyInstaller archive and reading the bytecode. That revealed the central
problem: v1's `ai_analyzer.py` returned hardcoded placeholder text, and its
Word report presented that text as AI analysis. The recovered source is kept
in `05_Supporting_Documents/12_Version_1_Baseline` as the documented "before".

**Lesson:** read what you actually have before improving it.

---

> **Prompt:** *"Capstone should have learning of all 5 days in this project."*
> (with the AICA Level 2 five-day course summary attached)

**Produced:** the project was re-planned around the syllabus — structured
prompting and a reusable skill (Day 1), vision and two-perspective analysis
(Day 2), the Python desktop stack (Day 3), the audit working-paper pattern
(Day 4), and MCP and workflow automation (Day 5). See
`05_Supporting_Documents/02_Five_Day_Syllabus_Map.md`.

---

## Stage 2 — Verifying the law before encoding it

Before any obligation was written into code, the DPDP Rules 2025 were checked
against current sources: the notification date (13 November 2025), the phased
commencement (13 Nov 2025 / 14 Nov 2026 / 14 May 2027), Rule 10 on verifiable
parental consent, and Rule 12 with the Fourth Schedule.

**Lesson:** AICA Day 1 — *"Always recheck due dates on official portals —
extensions and rule changes happen mid-year."* The Fourth Schedule finding —
that the school exemption is purpose-bound and does not cover promotion —
became the central legal point of the whole project.

---

## Stage 3 — Extending to where the data actually lives

> **Prompt:** *"Schools and other educational institutions post photographs on
> social media as well. Does DPDP need any specific approval there, and can
> this app help, or is just the website scan sufficient?"*

**Produced:** the legal analysis (a promotional post is outside the Fourth
Schedule, so s.9(1) verifiable parental consent applies), and a social media
module with four new obligations. Built so that it **never scrapes** — it
reads only the school's own posts — and analyses captions, never faces.

---

> **Prompt:** *"Also, the school has student data in its fees software or ERP.
> Would that also be covered under DPDP?"*

> **Follow-up:** *"Also include any data check in school LMS. Note that Tally
> just records students' name and receipt details to include it in total
> school fees revenue. All other fee records and student profile are listed in
> school ERP."*

**Produced:** the core systems module. The clarification about Tally changed
the design: the Tally check became deliberately narrow, and surfaced a real
finding — the books of account must be preserved under the Income-tax and
Companies Act rules, so a student erased from the ERP still exists in the
ledger. Built to read **the shape of the data, never the data**: column names
and counts only.

**Lesson:** a precise domain correction from the user produced a better
finding than the original design would have.

---

## Stage 4 — Getting the ethics right

> **Prompt:** *"Targeting the other school's website and Facebook without taking
> consent of the other school won't lead to violation of DPDP?"*

**Produced:** confirmation that it would. Section 3(c)(ii) exempts publicly
available data only where the Data Principal published it or a law required
it — a school posting a child's photograph is neither. Reading another
school's feed without consent would make the reviewer a Data Fiduciary with
no lawful basis. This led to the authorisation requirement: the tool records
who authorised each review and refuses to run without it.

> **Follow-up:** *"I have received authorisation from 4 school principals."*

**Lesson:** the most important question in the project was asked by the user,
not the assistant.

---

## Stage 5 — Usability, from real testing

These prompts came from running the tool on real data and reporting what went
wrong:

> *"The scanning activity is almost not visible."* → the Activity log was
> being squeezed to one line; the Scan tab was re-laid out.

> *"Under the Social tab, add post screenshot should have a copy-paste or drag
> and drop functionality as well."* → clipboard paste and drag-and-drop. The
> first attempt at Ctrl+V did not work because the key was bound to a widget
> that never receives focus; the fix was found from the report.

> *(A screenshot of a real post in Hindi)* → the caption analyser only read
> Latin script, so a Hindi feed would have looked clean. Devanagari support
> was added, with an honest limit: Hindi captions are flagged for a person to
> read rather than guessed at.

> *"Remove the authorisation required fields. Just keep Authorised by followed
> by the name and designation."* → the authorisation card was reduced to one
> mandatory field.

**Lesson:** AICA's "review a sample against originals" — every one of these
was found by using the tool, not by the tests.

---

## Stage 6 — Packaging and submission

> *"How to access this app without running a Python command. Make it in such a
> way that it can be shared as well."* → the PyInstaller build, double-click
> launchers, an icon, and crash logging for the windowed build.

> *"Smart App Control blocked the app."* → an explanation of the difference
> between SmartScreen and Smart App Control, and the recommendation to run
> from source on the development machine rather than disable a security
> feature.

> *(The GitHub upload guide attached)* → the Fork and Pull Request steps, and
> a clean submission folder with the virtual environment, build output and all
> real school reports removed.

---

## Stage 7 — Narrowing the scope for the capstone

> *"I think for capstone let's remove the functionality of Facebook and school
> system scan, we can upgrade it later for hackathon. For now let's just scan
> the school website and create reports."*

**Produced:** a deliberate de-scope. Real testing showed that social media
exports and ERP fee reports arrive in many formats, and making every one of
them reliable was a project of its own. The social media module, the ERP /
fee-software / TallyPrime reader, their eight obligations (C5–C8, S1–S4), the
two working-paper tabs and the two app tabs were removed from the capstone
build and archived intact for a later hackathon version. The capstone now
does one thing reliably: it scans the school website, reads the published
policy and supporting documents, takes the internal working paper, and
produces the reports. The catalogue went back to 25 obligations in seven
domains and the working paper to 26 lines in five tabs; tests were rewritten
to prove the removal was clean.

---

## What the assistant was asked to do throughout

- **Verify, don't recall.** Legal dates and provisions were checked against
  current sources before being encoded.
- **Test, then show the test.** The suite grew to 95 tests with social media and core systems, and stands at 42 for the website-only capstone build; the offline
  self-test caught two real wiring bugs that the unit tests missed.
- **Say what it could not check.** The desktop window could not be run in the
  assistant's environment, so a headless build test was written and that
  limit was stated plainly.
- **Never send anything.** No step emails, posts or submits on the user's
  behalf. External actions stay with the user.
