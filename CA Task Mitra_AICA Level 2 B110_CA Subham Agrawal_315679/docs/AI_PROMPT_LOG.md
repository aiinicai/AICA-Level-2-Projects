# AI use log – how CA Task Mitra was built

Author: CA Subham Agrawal. The author defined the problem, the firm's workflow and all requirements, reviewed every output, tested every screen with fictional data, and decided what to keep or change. AI tools did the drafting, coding and checking. No real client or personal data was given to any AI tool.

## Tools used
| Tool | Used for |
|------|----------|
| ChatGPT (project "CA Firm Workflow Management") | Early discussion: how a CA firm tracks work; the software options (two chats: "Track CA Workflow" and "Suggest CA Workflow Software") |
| Claude | Reading the course brief, reviewing direction, designing the architecture, writing and testing the Python app and the browser screens, fixing issues, writing documents and the video plan |
| Claude computer use | Reading the ChatGPT conversations directly from the desktop app instead of copying them by hand |
| Claude + Tally MCP (course Annexure G) | Linking TallyPrime for reading data and designing the posting of invoices and receipts |
| n8n | Receiving the alert webhook and e-mailing the CA |
| Python 3, SQLite | The application itself |

## Main prompts and decisions (paraphrased)
| # | Stage | What the author asked | What AI produced | Author's review / decision |
|---|-------|----------------------|------------------|----------------------------|
| 1 | Discovery | Discuss how a CA firm manages tasks; list modules and options | Workflow notes, module ideas, software suggestions | Chose to keep the discussion as the requirement base |
| 2 | Reading | Read both ChatGPT conversations and extract everything | Detailed extraction via computer use | Pasted one chat manually when it would not load |
| 3 | Understanding | "Tell me in 500 words what you understood" | Summary of goal, modules and decisions | Confirmed the understanding |
| 4 | Course fit | Review the AICA Level 2 brief for what the capstone must be | Capstone checklist: video, GitHub, form, marks | Used it to shape the plan |
| 5 | Direction | Are we on the right track? Python app or website? | Gap analysis; recommended Python + SQLite + browser UI | Accepted; earlier Node.js demo had failed on the PC |
| 6 | Design | Build from scratch, modular, viable for the capstone, within limited time and credits | Architecture, 12 modules, build plan | Approved the plan |
| 7 | Features added by author | Skills library; "documents insufficient" e-mail with CA approval; Tally integration; n8n alert on 18th, 20th and 21st | Designs and implementation | Author specified the behaviour |
| 8 | Modularity | 10-12 modules with sub-modules and an on/off switch; must become an EXE later | Module registry, switches, dependency checks, EXE build script | Reviewed in the Module manager screen |
| 9 | Build and test | Build it | Python server, 12 module files, browser screens, 33 then 57 automated checks | Author tested on own PC |
| 10 | Chrome and desktop feel | Open in Chrome, as a desktop-style app | Chrome app-window launcher, desktop shortcut | Verified by author |
| 11 | Issue list (21 points) | Fixed header and scrolling, Excel characters, clearer dashboards, remarks, fee options, grouping, imports, bulk actions, auto-billing to Tally, announcements, skills approval, e-mail sign-off, guided tour | Changes for every point | Author retested |
| 12 | Sharing | Share a single test file over WhatsApp | One-file self-extracting launcher | Used for testers |
| 13 | Presentation | Video structure, problem statement with 10 issues, opening lines | Video plan and opening script | Author chose the energetic opening |
| 14 | Rename | Rename to CA Task Mitra | Renamed across code, docs and scripts | Confirmed |

## Verification
- 57 automated end-to-end checks (`python tests/test_workflow.py`) run against a temporary database and a mock Tally server.
- Every screen opened in a browser by the AI and then used manually by the author.
- Items not tested live are listed honestly in [LIMITATIONS.md](LIMITATIONS.md).

## Responsible use
Only fictional demo data; no secrets in prompts or code; AI suggestions are confirmed by a person; clients receive nothing without CA approval.
