# Lovable: how the dashboard screen was built

This file records one more tool used in the project: **Lovable**, an online builder that turns written instructions into a working web page. It was used for the dashboard screen only. All data in it is dummy data.

## 1. Why Lovable was used

The first dashboard was built by Python and Claude. It worked and its numbers were checked, but the screen design looked plain. The owner asked for a better-looking version. Lovable builds screens from written instructions, so it was used for the look. The calculations were not given to Lovable to redo.

## 2. The rule that kept the numbers safe

Lovable was given two finished calculation files, `engine.js` and `life.js`. They were already tested against the Python calculation. Every message told Lovable:

- Do not change these two files, except the last lines that let the page load them.
- Every number on screen must come from these two files. Do not work out totals, gains or dates anywhere else.
- Dummy data only. No login, no database, no internet calls, no AI service, no secrets. The page must work offline.

## 3. Commands sent to Lovable

Eight messages are on record for the project. Times are Muscat time, 26 November 2026.

| # | Time | Sent by | What the message asked | Result |
|---|---|---|---|---|
| 1 | 08:46 | Claude | Project brief: nine pages, look and feel, colours per asset class, Indian number format, accessibility, phone width. Added the two calculation files. | Project set up with an empty state, no numbers yet |
| 2 | 08:53 | Claude | Step 2 of 3: save the dummy data file, connect all nine pages to the two calculation files, delete unused parts to keep the file count low. | Stopped: the plan's credits ran out |
| 3 | 09:02 | Claude | Same message as 2, sent again after the plan was upgraded. | Pages connected to the data |
| 4 | 09:33 | Owner, typed in the Lovable editor | Add an AI-written summary of gains and losses on the Overview page. | Added using an AI service. Cancelled in message 5 |
| 5 | 09:44 | Claude | Cancel the AI summary and any internet call. Part 1 of 3 of the NRI treaty (DTAA) page, as a finished static page. | Page file started |
| 6 | 09:48 | Claude | Part 2 of 3 of the same page. | Page file extended |
| 7 | 09:51 | Claude | Part 3 of 3 of the same page. | Page file complete (695 lines) |
| 8 | 09:53 | Claude | Show the DTAA page in its tab. Replace the AI summary with a plain-code summary built from the calculation numbers only. Remove "NRI" from titles and descriptions outside the DTAA tab, so the dashboard reads as for any investor. | Done |

The treaty page is sent in three parts because one message has a size limit. The page text was copied across character by character, and afterwards its checksum was compared with the original file. It matched.

## 4. Checks after Lovable finished

| Check | Result |
|---|---|
| Total value on 25 Nov 2026 against the Python calculation | INR 20,59,65,739 on both |
| Fund return per year (XIRR) | 13.92% on both |
| Month ends 31 Mar 2026 and 30 Jun 2026 | INR 15,59,77,517 and INR 18,45,77,457, same as Python |
| Plain-English summary | Allocation 24.9, 30.6, 11.7, 32.7 per cent; 14.14% gain on cost; up INR 66.54 L since 31 Oct 2026 |
| All nine pages open | Yes, no errors |
| Internet calls while the page runs | None |
| Excel export | Downloads a file |
| Phone width (390 pixels) | Fits, no sideways scroll |
| NRI DTAA page | Same text as the original (57,876 characters) |

## 5. From Lovable to one file anyone can open

Lovable shows the page from its own website. A reviewer should not need an account or a link that may stop working. So the Lovable source was packed and rebuilt on the laptop side into **one HTML file** that holds all its code and data and runs offline:

- `dashboard/HisaabKitaab_Dashboard.html`: the file to open. Double-click, no setup.
- `lovable/hisaab-kitaab-lovable-source.zip`: the Lovable source. `BUILD.txt` inside lists the two commands to rebuild the file.

The totals on this page are checked against the Python calculation in `app/` by the tests. No separate Python-built dashboard file is kept in the project.

## 6. What was learned about the tool

- Write the rules first. Telling Lovable "do not touch the calculation files" kept every number identical to the tested Python calculation.
- One message has a size limit. Large files go in parts, each part saying what it is and what not to touch.
- Lovable has credits. A message sent when credits had run out did nothing and had to be sent again.
- Lovable can add what was not asked, such as the AI summary typed in its editor. Check what it changed after each message, and cancel in writing.
- A built page must be checked by running it. Totals were compared with Python and the page was run offline before it was accepted.
- The screen design is Lovable's work. The numbers are not. The project keeps these two apart on purpose.

## 7. Boundaries

- Dummy data only was sent to Lovable. No real statement, name, PAN or account number was used.
- No password, key or token was given to Lovable or stored in this project.
- The real dashboard, built from real statements, is made on the owner's laptop only and is never uploaded.
