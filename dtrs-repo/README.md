# DTRS – Department Task & Review System

A web application for a manufacturing company to track tasks within each department, requests between departments, and monthly management review ("vouching") of department performance.

> **All data in this repository is fictitious.** The company "Sample Manufacturing Industries Pvt Ltd", its employees, codes and email addresses are invented for design, testing and the ICAI AI course (Level 2) submission.

## Status

| Phase | Status |
| --- | --- |
| P0 Requirements (BRD) | Draft v0.1 – awaiting management sign-off |
| P1 Prototype and data model | Clickable prototype done; data model next |
| P2 Build (Django MVP) | Not started |
| P3 Finance pilot | Not started |

## What is in this repository

| Folder / file | Contents |
| --- | --- |
| `docs/BRD.md`, `docs/BRD.pdf` | Business Requirement Document: org structure, roles and access matrix, task lifecycle, categories, requests between departments, working-day calendar, escalation, KPI scoring, management vouching, screens, technology, rollout |
| `docs/images/` | Diagrams used in the BRD |
| `prototype/index.html` | Clickable prototype – open in any modern browser, no installation |
| `data/DTRS_Dummy_Org_Data.xlsx` | 100 dummy employees in 15 units with reporting lines, categories, recurring templates, sample tasks and requests, KPI and escalation settings, holiday calendar |
| `prompts/PROMPT_LOG.md` | Record of how AI (Claude) was used at each step |

## Key design rules

- **Hierarchy:** L1 Executive → L2 Senior Executive → L3 Assistant Manager → L4 Deputy Manager → L5 HOD → L6 CEO. Every user has one "reports to".
- **Visibility:** own items plus the whole sub-tree below; HODs see only their department; the CEO and Head – Finance & Legal see all departments.
- **Review:** only the immediate senior reviews and closes a task; nobody reviews their own work; a Management Viewer never vouches their own department.
- **Assigning:** downward to anyone in the sub-tree, or to a peer or one level up in the same department; other departments through requests.
- **Task or Request:** a Task is reviewed by a senior; a Request (data, confirmation, approval) is confirmed closed by the requester. Every item has one of 15 categories.
- **Dates:** raised-on date captured by the system; original due date never changes; every revision is logged with reason and approver; third revision needs the HOD.
- **Mandatory reasons** for decline, hold, rework, reopen and rejecting a date change.
- **Working days:** 6-day week (Sunday off) plus an Admin-maintained holiday calendar.
- **Dashboards at every level**, department summaries for the CEO, monthly scorecards with K1–K5 measures.

## Trying the prototype

1. Download or clone this repository.
2. Open `prototype/index.html` in Chrome or Edge.
3. Use **View as** to switch between Executive, Senior Executive, HOD Finance, CEO, Functional Admin and IT Admin.

The prototype keeps data in memory only; reloading the page resets it. Dates are fixed at 22-Oct-2026.

## Planned technology

Python 3.12, Django 5.2 (LTS), PostgreSQL, Bootstrap 5 + HTMX, hosted on the company Windows Server behind IIS with Waitress, Active Directory login. Details in BRD section 16.

## AI usage

Requirements, policies, dummy data and the prototype were produced with Claude (Anthropic) under the direction and review of the project owner. See `prompts/PROMPT_LOG.md`.

## Author

Pearl – Head, Finance & Legal (CA, lawyer). Project for the ICAI AI course, Level 2.
