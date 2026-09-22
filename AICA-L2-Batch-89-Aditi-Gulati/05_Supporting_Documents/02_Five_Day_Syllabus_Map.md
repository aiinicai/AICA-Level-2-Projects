# Where each day of the course shows up in this project

The capstone is one working tool, not five exercises. This table is how to
check that every day of the AI Level 2 course is actually represented in it,
and where to look.

## Day 1 — Reusable skills, connected apps, scheduling

| Learning | Where it is in the project |
|---|---|
| Prompt structure: Role + Context + Objective + Output Format + Examples | `surakshascan/ai_analyzer.py` — the prompt is assembled from five named constants so it can be reviewed, not buried in an f-string |
| Few-shot prompting | `EXAMPLES` in the same module gives a good finding, a good negative finding, and an explicit counter-example of what must never be produced |
| Multi-step prompting with checkpoint verification | The model's output passes three guards before it is accepted: valid obligation id, valid status, and a quotation that actually occurs in the policy |
| Build a reusable skill | `skill/dpdp-readiness-review/SKILL.md` — a packaged skill with its own interview questions, run instructions and verification checklist |
| Test skills in a fresh chat; no stale values | `surakshascan/tools/export_catalogue.py` regenerates the skill's reference table from the code, so the skill cannot drift from the catalogue |
| Scheduled recurring task | `surakshascan/scheduler.py` and `surakshascan.cli watch` — a quarterly re-scan that reports only when the score moves |
| Approve external actions separately | The scheduler writes to `pending_review/` and sends nothing. The n8n workflow raises a review task rather than an email |
| Connect an external app; review requested permissions; read-only first | Shown through the MCP server (Day 5), which is read-only by default. A connector to the school's own social media page is held back for the hackathon build |

## Day 2 — Computer vision and comparison analysis

| Learning | Where it is in the project |
|---|---|
| Analyse an image or document; extract with an uncertainty flag | `surakshascan/vision.py` — reads admission forms, consent slips, CCTV signage and app screenshots; every extraction carries `uncertainty` and the retrieval timestamp |
| Handwritten and scanned text | A PDF with no text layer is flagged as probably a scan rather than silently returning nothing |
| Two professional perspectives on the same facts | `surakshascan/perspectives.py` — the institution's position and the parent's or the Board's position, with identical agreed facts in both panels |
| Findings anchored to the clause and the exact words | Every perspective pair carries the provision; every policy finding carries the quoted passage |
| Image review feeding a structured table | `vision.py` returns elements present, elements absent and uncertainty per document, shown in the Documents tab and the Word report |

## Day 3 — Python and small desktop applications

| Learning | Where it is in the project |
|---|---|
| Variables, types, operators, strings | Throughout; `dpdp_catalogue.py` is a typed dataclass catalogue rather than loose dictionaries |
| Beautiful Soup — HTML parsing | `surakshascan/scanner.py` |
| python-docx — Word output | `surakshascan/report_docx.py` |
| matplotlib — charts | `surakshascan/charts.py` |
| PyMuPDF — PDF reading | `surakshascan/vision.py` |
| Tkinter — GUI | `surakshascan/ui/app.py` |
| PyInstaller — script to executable | `SurakshaScan.spec`, and `docs/BUILD.md` |
| Test on sample data | `tests/` — 42 tests running against local HTML fixtures, no network |
| Keep the source code | `legacy_v1/` holds the v1 source recovered from the old .exe, as the documented baseline |

## Day 4 — Building business applications

| Learning | Where it is in the project |
|---|---|
| Tabbed checklist application | `ui/app.py` — six tabs (Scan, Working paper, Findings, Two views, Documents, Reports); the working paper itself has five inner tabs |
| Status options Completed / In Progress / Pending / NA | `questionnaire.py` |
| Team member mandatory before Completed | `questionnaire.validate()` refuses a Completed line with no reviewer |
| Auto-generated neutral remark; never asserts unverified work | `questionnaire.NEUTRAL_REMARK` and `finalise()` |
| Editable table with validation and confidence flags | The working-paper tab; `confidence` is one of "document seen", "stated by school", "not verified" |
| Word export: overview page with donut and bar charts, then detail | `report_docx.py` |
| Excel export with status counts by section | `report_xlsx.py` — seven sheets including status counts by domain |
| Dashboard with counts and distribution | `report_html.py` — a self-contained responsive dashboard |
| Responsive for mobile, tablet, desktop | The dashboard CSS collapses to one column below 720px |

## Day 5 — MCP, Tally, workflow automation

| Learning | Where it is in the project |
|---|---|
| Expose a tool or data source over MCP | `surakshascan/mcp_server.py` — four read tools, one write tool |
| Installing an MCP extension does not itself grant safe access | Write tools are registered only when `SURAKSHASCAN_MCP_ALLOW_WRITE=1`; the output directory is fixed and path traversal is refused |
| Connect read-only first | The default server is read-only and cannot write a file |
| Grant narrow folder scope | `SURAKSHASCAN_MCP_OUTPUT_DIR` is the only writable location |
| Workflow automation: trigger → action → review → output | `integrations/n8n_dpdp_quarterly_review.json` |
| TallyPrime connectivity | **Not in the capstone build.** A read-only TallyPrime reader was prototyped and is held back for the hackathon version; the capstone keeps to the website and its reports |
| Credentials in the credential manager, never in workflow text | The workflow references credentials by name; no secret appears in the JSON |
| Inspect imported workflow JSON before activation | Stated in the workflow's own `_documentation` block |

## The running themes

| Theme | How the project honours it |
|---|---|
| Data safety | The scanner reads public pages only, never logs in, obeys robots.txt and rate-limits itself. It refuses to run without recording who authorised the review, and prints that on every report. The MCP server is read-only by default |
| Verification | Every finding names the provision and, where the evidence is textual, quotes it. An AI finding whose quotation is not in the policy is rejected outright |
| Separate approvals | Nothing is ever sent. The scheduler queues for approval; the n8n workflow raises a task; the desktop app only saves files. And the review itself cannot start until the person who authorised it is recorded |
| Reusability | A packaged skill, a CLI, an MCP server and a GUI over one engine, so the same review runs four ways with identical results |
| Compliance | Commencement dates are held in the catalogue and printed against every finding, so what is due now is never confused with what is due on 14 May 2027 |
| Narrow permissions | Config directory scoped to the user; API key from the environment or the OS keyring; never written to disk by the app. |
| Audit trail | Every scan writes a timestamped evidence JSON with secrets redacted, and every report names the evidence file it came from |
