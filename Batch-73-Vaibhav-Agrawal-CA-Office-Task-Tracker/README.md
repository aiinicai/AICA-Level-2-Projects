# Task Tracker for a CA Office

**AICA Level 2 Project - ICAI**

Submitted by: **Vaibhav Agrawal** (AICA Level 2, Batch 73)

A Python web application that tracks the recurring compliance work of a Chartered
Accountant's office - GST, TDS, income tax, PF/ESI, audit and ROC - together with
day-to-day office tasks.

## Problem statement

Most work in a CA office **repeats**: GSTR-3B every month, TDS returns every quarter,
ROC forms every year. Ordinary to-do lists need the same task to be typed again for
every period, and a missed entry means a missed due date, late fees and interest.

In this application a repeating task is entered **once**. The program works out which
period (cycle) the task is in today, its due date and whether it has been completed for
that period. When the next month, quarter or financial year begins, the task
automatically opens again.

## Features

- **Sections** (GST, TDS, Audit ...) with navy or mustard headers, collapsible, re-orderable
- **Repeat rules**: Daily, Weekly (weekday), Monthly (due day, "from-to" window such as
  28th-5th, or 2nd Saturday), Quarterly (in the last month of the quarter or the month
  after it), Annual and One-time - quarters and years follow the **financial year (Apr-Mar)**
- **Status worked out automatically**: Done, Overdue, Due soon (3 days), Opens later, Open
- **Views**: All work, Needs attention (starred + overdue + due in 7 days), When free,
  Pending today, section-wise and person-wise ("With")
- **Per task**: person handling it, label (e.g. client name), remarks, steps (sub-tasks),
  star, "do when free", "checked for today", history of completed cycles
- **Working tools**: quick-add box in every section, search, bulk select (move / assign /
  done / delete), drag-and-drop re-ordering, undo, phone-friendly layout
- **Dashboard strip**: overdue, due in 7 days, open, pending today, done this month and a
  progress bar of repeating tasks for the current cycle
- **Exports**: all tasks to CSV (Excel) and a printable "Needs Attention" PDF report

## Technology used

| Layer | Tool | File |
|---|---|---|
| Web server and API | Python + Flask | `app.py` |
| Due-date / cycle engine | Python (standard library `datetime`, `calendar`) | `cycles.py` |
| Database | SQLite (built into Python) | `database.py` |
| CSV and PDF reports | Python `csv` + fpdf2 | `reports.py` |
| Automated tests | Python `unittest` | `test_cycles.py` |
| Screen (user interface) | HTML, CSS, JavaScript | `static/index.html` |

### How the parts work together

```
Browser (static/index.html)
      |   JSON over HTTP:  GET /api/state, PUT/PATCH/DELETE /api/tasks/<id>, ...
      v
app.py (Flask)  --->  cycles.py    calculates cycle, due date and status of every task
      |         --->  reports.py   builds the CSV file and the PDF report
      v
database.py  --->  task_tracker.db (SQLite)
```

The page only displays data and sends the user's actions. Every calculation -
which cycle a task is in, when it is due, whether it is overdue - is done in Python.

### Database design

| Table | Columns |
|---|---|
| `sections` | id, name, color, default_frequency, sort_order |
| `people` | name, sort_order |
| `tasks` | id, title, section_id, owner, tag, remarks, frequency, due_date, due_day, due_from, due_rule, due_weekday, due_q_offset, status, done_for, done_at, checked_on, starred, later, sort_order, created_at |
| `subtasks` | id, task_id, position, text, done |
| `history` | task_id, cycle_key, done_at |

`done_for` holds the cycle (for example `2026-09` or `Q2026-1`) for which a repeating
task was completed. When today's cycle is different, the task is open again - this is
how tasks reset themselves without any scheduled job.

## How to run

1. Install Python 3.10 or later.
2. Install the two required packages:

   ```
   python -m pip install -r requirements.txt
   ```

3. Start the application (or double-click `run_app.bat`):

   ```
   python app.py
   ```

   The browser opens at http://127.0.0.1:5000. On the first run the database is created
   and filled with fictitious sample data.

Other commands:

```
python -m unittest -v              run the tests of the due-date engine
python sample_data.py --reset      erase everything and load the sample data again
```

## Possible future enhancements

- Login with separate access for partners and staff
- E-mail / WhatsApp reminders before due dates
- Client master with automatic creation of compliance tasks for each new client
- Hosting on the office network so the whole team shares one tracker

> All names and figures in the sample data are fictitious.
