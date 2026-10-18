# Build prompt (specification)

Written as a specification, not a wish: inputs, logic, outputs, constraints, sample data.
Paste this into any AI coding tool to rebuild the app.

---

**Role:** You are a Python developer building a small personal tool for a chartered accountant.

**Goal:** "My Work Diary", a local web app (Streamlit + SQLite) that tracks daily tasks, time, task
movement, additional work and KPIs, and produces a summary report.

## Inputs
- Task: title (required), category (Client work, Internal, Additional / ad-hoc, Learning, Admin),
  client or person (optional, short code), planned minutes, date, notes, "additional / unplanned" tick.
- Time entry: task, date, minutes (> 0), optional note.
- Status: Not started, In progress, Done.
- KPI: name, period (Monthly or Yearly), year, month (for monthly), target (> 0), measured by
  (Tasks completed, Hours logged, Manual count), optional category filter.
- Manual KPI entry: KPI, date, value.

## Processing logic
1. A task has an **original date** (never changes) and a **scheduled date**. Carrying forward moves
   the scheduled date to a later date and adds one to a carry count. A completed task cannot be
   carried forward. One action carries every open task scheduled before today onto today.
2. **Task age** = days from original date to completion date (or today if still open).
3. **Additional work %** = minutes on tasks categorised Additional / ad-hoc or ticked unplanned,
   divided by all minutes logged in the period.
4. **KPI actuals:** Tasks completed = tasks marked Done with completion date inside the KPI's period
   (optionally one category). Hours logged = time entries inside the period / 60 (optionally one
   category). Manual count = sum of manual entries in the period. Achievement % = actual / target.
   Period boundaries are inclusive; December rolls correctly to the end of the year.
5. **Planned vs actual** compares planned and logged minutes for tasks completed in the period;
   tasks with no plan are excluded from the comparison.

## Outputs
- Pages: Today, All tasks, KPIs, Dashboard, Report.
- Dashboard: hours logged, tasks completed, tasks open, open tasks carried forward, additional work %,
  hours by category, hours per day, planned vs actual table, ten longest-running open tasks, KPI table.
- Report: Excel (Summary, Hours by category, KPIs, Tasks, Time entries, About) and Word
  (highlights, hours by category, KPI table, tasks completed). Works with an empty diary.

## Constraints
- All data in a local SQLite file; no network calls, no AI calls, no telemetry.
- Show a clear message for invalid input instead of crashing.
- Footer on every page and report: "Developed by CA Sapan".
- Warn users not to enter passwords, PAN, Aadhaar or bank details in task text.
- Keep logic in `core.py` (testable) and screens in `app.py`.

## Sample data
Ten fictional tasks over two weeks for Client A to D, with seven completed, two additional / ad-hoc
tasks, some overdue tasks carried forward, and four KPIs (tasks completed this month 10, client
hours this month 20, client calls this month 8, tasks completed this year 120).
