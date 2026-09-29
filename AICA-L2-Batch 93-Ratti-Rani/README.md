# AI-Powered Session Quiz & Feedback System

**AICA Level 2 Capstone** | Ratti Rani | Batch completion: Sept 18, 2026

## Purpose

Automates post-session quizzes for faculty: AI generates questions from session notes, students take a verified single-attempt quiz, and (next phase) get auto-graded feedback. Built in n8n + Google Gemini. Branding fully configurable.

## Built & tested

- **Workflow 1 — Question Bank Generator:** faculty submit topic + notes → Gemini AI Agent generates 12 questions (10 MCQ + 2 short-answer) → Structured Output Parser → written to `Question_Bank` sheet. Tested: 24 real questions across 2 topics.
- **Workflow 2 — Student Portal & Quiz:** student registers (BSP number, name, email, section, subject) → verified against `Students` sheet (BSP number + email must both match) → checked against `Attempts` sheet (one attempt per quiz) → cleared student answers a real 2-page quiz pulled from `Question_Bank`. Tested end-to-end incl. a rejected mismatched-email case.

## Planned next phase

- Randomized question/option selection per student
- Workflow 3: auto-grading + AI-evaluated short answers + emailed feedback
- Faculty analytics on class-wide weak concepts
- Role-based result views (student: own results; faculty: all + filters)

## Architecture

n8n (Form Trigger → AI Agent → Structured Output Parser → Split Out → Google Sheets; If-branching for access control) + Google Gemini + Google Sheets as the data store (Settings, Students, Quizzes, Question_Bank, Attempts, Results).

## Setup

1. Create the Google Sheet (6 tabs above), populate Settings + Students.
2. Import `n8n_workflow_export.json` into n8n; connect Google Sheets + Gemini credentials.
3. Point Google Sheets nodes to your spreadsheet URL.
4. Run Workflow 1 per session; share Workflow 2's form link with students.

## Files

`n8n_workflow_export.json` · `landing_page.html` · `architecture_diagram.html` · `presentation_script.md` · `screenshots/`

Presentation deck: https://gamma.app/docs/lurn7xgoz7k5q6e

## Disclaimer

This is an academic capstone project built for the AICA Level 2 course and is a prototype/pilot, not a production system. All student records (BSP001–BSP004, names, emails) are fictitious test data created for demonstration only — no real student or institutional data was used. Quiz questions are AI-generated (Google Gemini) and have not been independently verified for factual or academic accuracy; faculty should review all AI-generated content before using it in an actual classroom setting. This project is provided as-is, without warranty, for educational and evaluation purposes.
