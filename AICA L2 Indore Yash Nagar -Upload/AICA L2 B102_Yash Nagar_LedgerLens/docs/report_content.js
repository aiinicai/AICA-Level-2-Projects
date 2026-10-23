body.extend([
  h1("1. Objective and executive summary"),
  p("LedgerLens turns a Tally Prime trial balance into draft Schedule III (Division I, non-Ind AS) financial statements with an AS 3 cash flow, linked notes, statutory disclosures and a reviewer's report, and audits the Tally Day Book for red flags. It takes the repetitive, rule-driven part of year-end work off the accountant and points the accountant's judgement at the items that need it. Every output is a draft; each classification the tool had to guess is listed for confirmation."),
  p([b("In one sentence: "), run("Python does everything that produces a number or a pass or fail; an optional AI model (Gemini, the user's own key) only reads and comments.")]),
  table([2300, 7338], ["Status", "Evidence"], [
    ["Built and tested", "347 automated tests, including tests that break the statements on purpose and require the checks to fail. Excel figures are recalculated independently and compared with the Word output."],
    ["Run on real data", "The user's own Tally exports (a trial balance and a 200-voucher Day Book) and the ICAI Guidance Note on Schedule III (Revised 2022), which corrected ratio definitions and added rounding."],
    ["AI tested live", "Statements review: 5 grounded observations and reasons for the 2 flagged ratios. Day Book review of the 27 rule-flagged vouchers: 7 to 8 findings, including a director's family trip booked as travel."],
    ["Not yet exercised", "A live pull from a running Tally. The previous-year profit and loss stays blank until a second year is loaded."],
  ]),

  h1("2. Problem statement"),
  bullet([b("Tally gives a trial balance, not Schedule III statements. "), run("Each ledger must be placed on a line, notes built, cash flow derived and everything agreed, by hand in Excel. A misplaced ledger can survive until audit.")]),
  bullet([b("The format is demanding. "), run("Schedule III and the ICAI Guidance Note require compulsory rounding, prescribed ratios, ageing schedules and many additional disclosures; a draft can foot and still be non-compliant.")]),
  bullet([b("The Day Book hides what matters. "), run("A reviewer cannot read every voucher. Gifts, penalties and personal spend, cash above the limit, amounts kept just under a threshold and numbering gaps are scattered through it.")]),
  bullet([b("Real exports are awkward. "), run("Tally's Excel trial balance shows Dr and Cr only in cell formats and has no groups; in Educational mode the Day Book hides most dates.")]),
  bullet([b("AI helps but cannot be trusted with numbers. "), run("A model can notice a narration that does not fit its ledger, but it can invent figures. The design problem is to use it for judgement while code keeps every number.")]),

  h1("3. Core features of the tool"),
  table([2300, 7338], ["Feature", "What it does"], [
    ["Financial Statements Builder", "Reads Tally's native trial balance (or a template, or a live pull) and maps ledgers to Schedule III lines with a rulebook; the user can override any placement. Produces the balance sheet, profit and loss, AS 3 cash flow and notes in Word and Excel, rounded to the unit Schedule III requires so totals still foot. Statement lines are hyperlinked to their notes, and the Excel statements are formulas that read the notes."],
    ["Statutory disclosures", "Eleven sections with current and previous year: auditor payment, Sec 197 remuneration, related parties (AS 18), EPS (AS 20), CSR test (Sec 135), contingent liabilities, MSME dues, receivable and payable ageing, and the Schedule III additional regulatory information. Facts in the books are filled in; anything only management can declare stays as a bracketed request, never as nil."],
    ["Reviewer", "72 casting and tie-out checks, the 11 Annexure B ratios with a 25% movement flag, and a disclosure checklist. Signature blocks (audit firm, FRN, partner, directors, DIN, dates) close each statement."],
    ["Day Book Audit", "Reads the native export, including hidden dates. Tests: cash and TDS/GST rules, voucher gaps, the 999 verification (amounts ending in 999 or just under a limit), repeated amounts, a Benford screen and narration themes (fraud, bribe, gift, penalty, donation, as instructed, suspense and more). A Tests run tab lists every test, including those that found nothing."],
    ["AI review (optional)", "One tab on each page, with its explanation, consent tick, run button and results together. Statements: observations and reasons for ratio changes. Day Book: narration read against the ledger. Results also go into the Excel downloads."],
    ["Dashboards and layout", "An overview dashboard on each page. The statements page has five tabs (Load, Check and map, Statements, Review and AI, Download); the Day Book page has Overview, Findings, Tests run, AI review and data."],
  ]),

  h1("4. Technology architecture"),
  p([b("Stack: "), run("Python 3.13 and Streamlit; pandas, openpyxl and python-docx; Altair charts; Google Gemini through the google-genai library (default gemini-2.5-flash, with automatic fallback when a model is busy or out of quota); pytest.")]),
  picture(),
  p("Figure 1. Green boxes are plain Python; only the orange box uses the API key.", { center: true, after: 6 }),
  table([4819, 4819], ["Python code (no key needed)", "LLM (API key)"], [
    ["Reading Tally files: native layouts, Dr/Cr, hidden dates, group inference", "Statements: observations on the figures, citing numbered facts; the model sees figures and labels only, never ledger or party names"],
    ["Mapping ledgers to Schedule III lines (rulebook, entirely rule-based: the key is never used to map)", "Statements: a drafted reason for each ratio that moved over 25%, marked as a draft"],
    ["Notes, rounding, AS 3 cash flow, disclosures, Word and Excel output with links", "Day Book: narration read against ledgers (personal spend, wrong ledger or voucher type, vague narration); ledger names, amounts and narrations are sent"],
    ["Tie-outs, ratios, checklist, all Day Book tests, dashboards", "Never used to compute a figure, map a ledger or decide a pass or fail"],
  ]),
  p([b("Controls on the AI. "), run("Off until a key is present and consent is ticked. Code inserts every figure from the cited fact, and any number the model states that is not in the books is flagged. Calls time out and retry, move to another model if one is busy, and a banner reports failed batches. Identical Day Book reviews are cached. AI results are labelled and the reviewer decides.")], { before: 6 }),

  h1("5. Conclusion and impact"),
  p("The mechanical part of Schedule III reporting and much of Day Book review can be done by explainable, tested code, with AI kept to the narrow job of judgement, under the user's consent and with its figures controlled by code. The accountant receives a draft to review rather than build."),
  table([2300, 7338], ["Impact", "How"], [
    ["Time", "Mapping, notes, cash flow, rounding, disclosures and linking are produced in one run and re-run in seconds after a mapping change."],
    ["Accuracy and compliance", "Totals foot by construction, 72 tie-outs run on every build, and ratios, rounding and disclosures follow the ICAI Guidance Note."],
    ["Audit coverage", "Every voucher is tested rather than a sample; each finding names the voucher and quotes the narration."],
    ["Transparency and cost", "Guesses, hidden dates and ungrounded AI statements are all shown. Everything except the optional AI runs on the user's computer."],
  ]),
  p([b("Limits. "), run("The output is a draft; classification, valuation and policies remain the accountant's and auditor's responsibility. Previous-year profit and loss and cash flow need a second trial balance. Narration tests are keyword-based and the AI can be wrong, so findings are leads. The free Gemini tier has small daily quotas. "), b("Next: "), run("pull a full year through the Tally connector, load the prior year, and review a wider sample of AI findings.")], { before: 6 }),
])
