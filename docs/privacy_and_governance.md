# Privacy and governance note

This note applies the Day 5 data-privacy checklist to this project. It is a prompt to check
your own position, not legal advice.

## Where the data lives
- One local file, `work_diary.db`, on the practitioner's computer.
- The app makes no network calls and sends nothing to any AI service.
- Back up by copying that single file.

## What should and should not be entered
- Enter short client codes (Client A) instead of full names where possible.
- Never enter passwords, OTPs, DSC details, portal credentials, PAN, Aadhaar, or bank and salary details.
- Task notes are free text, so the discipline sits with the user.

## Mapping to the course checklist
| Course point | How this project handles it |
|---|---|
| Prefer local over cloud | Local SQLite and local Streamlit; no cloud database |
| Share the narrowest data | Only task titles, categories, minutes and optional client codes are stored |
| Mask identifiers | Guidance above; no field exists for PAN, Aadhaar or bank details |
| Separate client engagements | Client field and filter on the All tasks page |
| Trace figures to source | Every dashboard number is calculated from visible task and time entries |
| Record who reviewed | Reports are for the practitioner's own review before they go to anyone |
| Take backups | Single-file backup; avoid placing the live file in a synced folder that an AI tool can read |

## If Phase 2 is built later
Importing mail data would bring in personal data of third parties (senders and recipients).
Before building it: confirm what the engagement letter and the firm's policy permit, import only
sender, subject and date, mask where possible, keep it local, and document the data flow.
An AI weekly summary should receive only masked, aggregated data.

## Own-performance data
The diary records the user's own work. If it is ever used for a team, staff members' time and
performance data is personal data too and needs notice and a stated purpose.
