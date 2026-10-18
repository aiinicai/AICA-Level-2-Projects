# My Work Diary

A personal performance and time tracker for a chartered accountant's day-to-day office work.
Log tasks and time daily, set monthly and yearly KPIs, see where the time actually goes, and
produce a summary for an appraisal or a discussion with the partner.

AICA Level 2 capstone project · Developed by CA Sapan

## Problem

Office work arrives as a mix of planned client work, internal jobs and unplanned requests.
By month-end it is hard to answer simple questions: how much time did client work really take,
how much of my time went to additional tasks, which tasks keep getting carried forward, and am I
on track against my targets? This tool answers them from a few minutes of daily entry.

## What it does (Phase 1)

| Page | Purpose |
|---|---|
| Today | Add tasks, log time against them, update status, carry overdue tasks forward in one click |
| All tasks | Filter by status, category or client; move a task to a new date; delete |
| KPIs | Define monthly and yearly targets; achievement is calculated automatically |
| Dashboard | Hours by category and by day, additional-work share, planned vs actual, longest-running open tasks, KPI achievement |
| Report | Download a monthly (or any period) summary as Excel and Word |

Key rules built in:

- **Task movement.** Carrying a task forward changes its scheduled date and counts the carry, but
  never changes its original date, so the real age of a task stays visible.
- **Additional work.** Anything categorised "Additional / ad-hoc", or ticked as unplanned, counts
  towards the additional-work percentage.
- **Three KPI types.** *Tasks completed* and *Hours logged* are calculated from your entries (each
  can be limited to one category). *Manual count* is for things you add yourself, such as client calls.
- **Validation.** Empty titles, zero minutes, non-positive targets, carrying a completed task, or
  moving a task to an earlier date are rejected with a clear message.

## How to run

1. Install Python 3.10 or later from python.org. On Windows, tick **Add Python to PATH**.
2. Open a terminal in this folder and run:

```
pip install -r requirements.txt
streamlit run app.py
```

3. The app opens in your browser. Click **Load sample data** in the sidebar to see it with
   fictional data, or just start adding your own tasks.

Your data is kept in `work_diary.db` in this folder. Back that one file up to back up everything.

## Optional: package as a Windows program

```
pip install pyinstaller
pyinstaller --onefile --collect-all streamlit --add-data "app.py;." --add-data "core.py;." run_app.py
```

`run_app.py` keeps the database next to the .exe so data survives between runs. **This packaging
step has not been tested**; Streamlit with PyInstaller often needs a few counter-prompts to your
AI tool (missing files, hidden imports). If it gets stubborn, `streamlit run app.py` is a
perfectly good delivery. Build on the operating system you will run it on.

## Files

```
app.py            screens (Streamlit)
run_app.py        launcher, only for the optional .exe package
core.py           all the logic: database, KPI maths, exports
test_core.py      15 tests of the logic          -> python test_core.py
test_app_smoke.py checks every page runs         -> python test_app_smoke.py
requirements.txt  libraries
sample_data/      example Excel and Word reports made from the fictional sample data
docs/             build prompt and privacy note
```

## Privacy and governance

Everything is stored locally; nothing is uploaded or sent to any AI service. Do not enter
passwords, PAN, Aadhaar, bank details or other client identifiers in task names or notes; use
short client codes instead. See `docs/privacy_and_governance.md`.

## How this was built (Design, Develop, Debug, Deploy, Deliver)

- **Design:** the specification is in `docs/build_prompt.md`: inputs, rules, outputs and constraints.
- **Develop:** the first version was generated with an AI assistant (Claude) from that specification.
- **Debug:** issues found and fixed while building are listed below. Add your own counter-prompts
  here as you test the app on real days of work.
  - Excel export failed on the current pandas release because the sheet name must be passed by
    keyword; fixed and covered by a test.
  - The page test initially failed because the test double behaved differently from real
    Streamlit columns; the test was corrected, not the app.
  - *(Add yours: what you saw on screen, the exact error, and the instruction that fixed it.)*
- **Deploy:** runs locally on the practitioner's machine; optional single-file package above.
- **Deliver:** this repository, the README, sample reports, and a fallback: the same data file
  can be opened with any SQLite viewer.

## Phase 2 ideas (not built)

- Import a mail export (sender, subject, date) to pre-fill tasks by client name or email ID
- Weekly AI-written "where did my time go" note, using only masked data
- Automatic capture through a workflow tool, after consent and a data-flow review

Developed by CA Sapan
