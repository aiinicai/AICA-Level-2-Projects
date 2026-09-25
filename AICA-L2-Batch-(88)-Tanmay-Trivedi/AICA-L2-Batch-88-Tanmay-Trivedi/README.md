# GST Blocked Credit Checker

**AICA Level-2 (AI for Chartered Accountants) - Individual Capstone Project**

A small, deliberately simple tool that answers one question CAs ask constantly:
*"Can I claim Input Tax Credit on this?"* - for the specific set of expenses that
Section 17(5) of the CGST Act, 2017 blocks. Describe the expense (or upload a
whole expense ledger), and it tells you the verdict, the exact clause, and why.
Alongside that, it also flags possible Reverse Charge Mechanism (RCM)
liability - Section 9(3)/9(4) - since that's a separate question CAs need to
ask about the same expense, and it's easy to check ITC eligibility on an
invoice while forgetting the GST on it was never charged by the supplier to
begin with.

## 1. Problem Statement

Section 17(5) ("Blocked Credits") lists roughly 16 categories of expense on which
ITC cannot be claimed - motor vehicles, food & catering, club memberships,
construction of immovable property, and so on - each with its own carve-out
exceptions that are easy to misremember under time pressure (a cab company
*can* claim ITC on cars; a factory canteen mandated by the Factories Act *can*
claim ITC on the food). Getting this wrong either means an avoidable
disallowance, or leaving legitimate credit unclaimed. This is exactly the kind
of well-defined, rule-bounded question that suits a simple rule-based tool
rather than a from-scratch lookup in the bare Act every time.

## 2. What the Tool Does

Three ways to use it:

- **Quick Check** (one expense at a time) - type a description, and if the
  matched category needs a follow-up fact (e.g. "is the seating capacity over
  13?", "is this obligatory under law?"), it asks one or two Yes/No questions
  before giving the verdict.
- **Bulk Check** (a whole ledger at once) - upload an Excel sheet of expense
  line items (a `Description` column, plus optional Yes/No columns for the
  follow-up questions), and get back a colour-coded, clause-referenced verdict
  for every row - green for eligible, red for blocked, amber for "needs
  review" where a follow-up condition was left unanswered.
- **Invoice Check** (upload a photo or PDF) - upload a purchase invoice and
  the tool reads the goods/services description off it (via Claude if an API
  key is configured, otherwise entirely offline via the PDF's own text layer
  or Tesseract OCR), then runs that description through the *same* matcher as
  Quick Check, asking the same follow-up question(s) if needed. The extracted
  text is shown and is editable before matching, since OCR/AI reading of a
  real invoice can occasionally misread a word or two.

All three interfaces share exactly one rules engine (`src/rules.py`), so the
legal logic is defined once and can't drift between them - Invoice Check adds
a new way to arrive at a description, not a second copy of the rules.

All three interfaces also raise an independent **RCM Alert** (`src/rcm.py`)
whenever the description matches a commonly reverse-charged supply - shown
alongside the Section 17(5) verdict, never instead of it, since RCM liability
(who pays the GST) and ITC eligibility (can it be claimed) are two different
questions about the same expense. See Section 9 below.

## 3. How This Maps to the AICA Level-2 Course

| Course Module | Used in this project |
|---|---|
| Module 6 - Python Fundamentals for CAs | `src/rules.py`'s rule table and matching logic; `src/rcm.py` for the independent RCM alert; `src/bulk_check.py` for the Excel pipeline |
| Module 7 - Full-Stack Web App Development | `app.py` - a Streamlit web app with three working tabs |
| Module 1/2 - AI Agents | `src/ai_explainer.py` - an optional plain-language rewording of a verdict, live via Claude if `ANTHROPIC_API_KEY` is set, with a graceful rule-based fallback if not (nothing about the verdict itself ever depends on the AI call); `src/invoice_reader.py` - AI-based invoice reading (Claude vision/document input) with a free offline OCR fallback (Tesseract) |
| Module 4 (concept) - Structured reporting | Colour-coded Excel bulk-check report, including the RCM Alert column |

## 4. Project Structure

```
gst-blocked-credit-checker/
├── app.py                          # Streamlit app - Quick Check + Bulk Check tabs
├── main.py                         # command-line fallback (same engine, no browser needed)
├── requirements.txt
├── README.md
├── src/
│   ├── rules.py                    # the Section 17(5) rule table + matching/evaluation engine
│   ├── rcm.py                      # independent Section 9(3)/9(4) RCM alert list + matcher
│   ├── bulk_check.py               # Excel template, bulk-run logic, coloured report writer
│   ├── ai_explainer.py             # optional AI plain-language rewording (graceful fallback)
│   ├── invoice_reader.py           # invoice photo/PDF -> text (AI, or offline OCR fallback)
│   └── generate_sample_ledger.py   # regenerates the synthetic sample ledger
├── sample_data/
│   ├── Blocked_Credit_Bulk_Template.xlsx     # blank template with example rows
│   ├── Sample_Expense_Ledger.xlsx            # 17-row fictional demo ledger (2 rows trip the RCM alert)
│   ├── Sample_Invoice_Club_Membership.pdf    # fictional invoice - clean PDF text layer
│   └── Sample_Invoice_Catering_Photo.jpg     # fictional invoice - photo/OCR path
└── output/
    └── Sample_Expense_Ledger_Report.xlsx   # generated report from the sample ledger
```

## 5. How to Run

```bash
pip install -r requirements.txt

# Web app (recommended) - opens in your browser
streamlit run app.py

# Command-line quick check
python main.py check

# Command-line bulk check (safe to demo - the sample ledger is entirely fictional)
python main.py bulk --input sample_data/Sample_Expense_Ledger.xlsx \
                     --output output/Sample_Expense_Ledger_Report.xlsx

# Get a blank bulk-check template for your own ledger
python main.py template --output my_template.xlsx

# Command-line invoice check (reads a photo/PDF, same engine as `check`)
python main.py invoice --input sample_data/Sample_Invoice_Club_Membership.pdf
```

To enable the optional **live AI** features - a plain-language explanation of a
verdict, and AI-based reading of an uploaded invoice in the Invoice Check tab
(more accurate on real-world invoice layouts than the offline OCR fallback):

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key-here"     # Windows (PowerShell): $env:ANTHROPIC_API_KEY="your-key-here"
streamlit run app.py
```

For the plain-language explanation, only the already-computed verdict, the
matched clause, and the (non-identifying) expense description are sent -
never client names, amounts, or transaction-level data - and the verdict
itself never depends on this call succeeding. Invoice Check is different: to
read a photo or PDF, the actual invoice content has to be sent to Anthropic's
API for that one request - see Section 8 below before using it on a real
client invoice. Without a key, Invoice Check still works, using the offline
OCR fallback described there.

## 6. What's Covered

All sub-clauses of Section 17(5), each as its own rule with its own exceptions:

| Clause | Category |
|---|---|
| (a) | Motor vehicles for transport of persons |
| (aa) | Vessels & aircraft |
| (ab) | Insurance, repair & servicing of the above |
| (b)(i) | Food & beverages, outdoor catering, beauty treatment, cosmetic/plastic surgery, health services |
| (b)(i) | Life insurance & health insurance |
| (b)(i) | Leasing/renting/hiring of motor vehicles/vessels/aircraft |
| (b)(iii) | Club, health & fitness centre membership |
| (b)(iv) | Employee travel benefits (LTC/LTA) |
| (c) | Works contract services for construction of immovable property |
| (d) | Goods/services for construction of immovable property on own account |
| (e) | Tax paid under the composition scheme |
| (f) | Non-resident taxable person - domestic purchases |
| (g) | Personal consumption |
| (h) | Goods lost, stolen, destroyed, written off, or given as gifts/free samples |
| (i) | Tax paid pursuant to fraud/suppression demands (Sections 74/129/130) |

**Reflects the Finance Act, 2025 amendment** to clauses (c) and (d), which
replaced "plant or machinery" with "plant and machinery" retrospectively from
01-07-2017 - reversing the favourable reading the Supreme Court had given the
old wording in *Safari Retreats*. The tool flags this with a note whenever a
construction-related clause is matched.

## 7. How Matching Works (and its limits)

The description you type is matched against each category's list of keyword
phrases, using whole-word matching so a short keyword can't false-match inside
an unrelated word (an earlier bug in development: the keyword "ship" was
matching inside "member**ship**" before this was fixed). When more than one
category's keywords match the same description, the **most specific** match
wins - ranked by how many words the matched phrase has - rather than whichever
category happens to be listed first, so "motor insurance premium for the car"
correctly resolves to the insurance/servicing clause (ab), not the motor
vehicle purchase clause (a), even though both keywords appear.

This is still a keyword matcher, not a language model - it only recognises the
phrasing it's been given examples of. If nothing matches, the tool reports "no
block identified, appears eligible" rather than guessing, and that result
should be treated as "double-check manually," especially for a very short or
unusually worded description. When you're not sure your wording will be
picked up, mention the general nature of the expense plainly (car, insurance,
catering, club, construction, etc.) rather than only a specific brand/model
name.

## 8. How Invoice Check Works (and its limits)

Invoice Check doesn't add a second set of legal rules - it only adds a new way
to produce the free-text description that Section 7 above already knows how
to match. The flow is: read the file -> get plain text -> run it through the
exact same `match_categories()` / `evaluate()` used by Quick Check.

**How the file gets read**, tried in this order:

1. **AI reading (Claude)** - only if `ANTHROPIC_API_KEY` is set (and the
   `anthropic` package is installed). The invoice image or PDF is sent to
   Claude directly, which is asked to describe the goods/services supplied in
   plain English - not to give a verdict itself. Generally the most accurate
   option on real invoice layouts (tables, stamps, mixed fonts, poor scans).
2. **PDF text layer** - if the uploaded file is a PDF that already has
   selectable text (i.e. it wasn't just a scanned image saved as a PDF), that
   text is read directly via PyMuPDF. Instant and perfectly accurate, no OCR
   involved.
3. **Tesseract OCR** - the offline fallback for a scanned PDF or a photo/image
   file, used whenever the two options above don't apply or aren't available.
   `pytesseract` is only a Python wrapper - it needs the **Tesseract OCR
   engine** installed separately on the machine (see `requirements.txt` for
   the per-OS install command). OCR accuracy depends heavily on photo
   quality: a flat, well-lit, in-focus scan reads far better than an angled
   phone photo with a shadow across it.

Whichever method read it, the extracted text is shown on screen **and is
editable** before matching runs - correct a misread word or two rather than
re-uploading, especially after OCR. If nothing usable could be read at all
(blank page, totally illegible scan, no Tesseract installed and no API key),
the tool says so plainly rather than guessing.

**Limits**: this reads what the invoice *says*, in the same free-text-keyword
sense as Quick Check - it does not itself decide ITC eligibility, verify the
invoice is genuine, check GSTIN validity, or reconcile it against GSTR-2B. An
invoice line item is often terse ("AMC Services", a product code with no
description) and may simply not carry enough information for the matcher to
recognise the expense type at all - that's expected, not a bug, and the tool
will say "no block identified" rather than force a match. Treat every
Invoice Check verdict exactly as you would a Quick Check one: a first-pass
planning aid, not a substitute for looking at the invoice yourself.

## 9. How the RCM Alert Works (and its limits)

Reverse Charge Mechanism and Section 17(5) answer two different questions
about the same expense - RCM asks *"who is liable to pay the GST in the first
place?"*, Section 17(5) asks *"once GST has been paid, can I claim ITC on
it?"*. An expense can be RCM-liable **and** fully ITC-eligible at the same
time (e.g. legal fees from an advocate: you self-invoice and pay GST under
RCM, and that self-paid tax is itself ordinary eligible ITC, subject to
Section 17(5) like any other tax paid). So `src/rcm.py` is a completely
separate, independent list from `src/rules.py` - it never changes or blocks
the Section 17(5) verdict, it's just shown alongside it, on all three tabs
and in the Bulk Check report's **RCM Alert** column.

It works the same way as Section 17(5) matching - the same word-boundary
keyword technique against a small table of commonly reverse-charged supplies
under Section 9(3)/9(4), CGST Act (Section 5(3)/5(4), IGST Act for
inter-state/import cases), read with Notification No. 13/2017-Central Tax
(Rate) as amended: Goods Transport Agency services, legal services from an
advocate, services of an arbitral tribunal, sponsorship services, a
director's services to the company, import of services, security services,
renting of a motor vehicle (non-body-corporate to body-corporate), renting of
a residential dwelling to a registered person, insurance agent and recovery
agent services, and the (now narrow) Section 9(4) case of a real-estate
promoter's purchases from unregistered suppliers.

**Limits**: this list is a representative, curated set of the RCM entries
most commonly encountered in general practice - it is **not exhaustive** of
every entry in Notification No. 13/2017-CT(Rate) and its amendments. More
importantly, several of these entries have conditions that a bare description
can't verify - whether the *recipient* is a body corporate, whether the
supplier has already opted for forward charge (e.g. a GTA charging 12%
itself, or a cab operator charging 12% GST), or the supplier's own
registration status. Treat every RCM alert exactly as you'd treat a Section
17(5) verdict from this tool: a prompt to go check the specific conditions
against the notification, not a determination.

## 10. Important Simplifications

This is a capstone/demonstration build, not a production compliance system:

- Matching is keyword-based, not a legal-language model - see Section 7 above.
- The materiality/apportionment computation for mixed business-personal use
  under clause (g) is not computed - the tool flags the clause and leaves the
  apportionment to you.
- Bulk-check rows where a follow-up condition column is left blank are marked
  **NEEDS REVIEW** rather than guessed at - by design, not a bug.
- Invoice Check reads what's printed on the invoice - it doesn't verify the
  invoice is genuine, check GSTIN validity, or reconcile it against GSTR-2B.
  See Section 8 above.
- The RCM Alert list is representative, not exhaustive, and can't verify the
  recipient/supplier conditions several entries depend on - see Section 9
  above.
- Clause citations and the Finance Act 2025 amendment are current as of when
  this tool was built (September 2026) - verify against the Act in force
  before relying on any verdict for an actual filing position.

## 11. Sample Data & Data Privacy

`sample_data/Sample_Expense_Ledger.xlsx` and the two sample invoices
(`Sample_Invoice_Club_Membership.pdf`, `Sample_Invoice_Catering_Photo.jpg`)
are entirely fictional (regenerate the ledger with
`python -m src.generate_sample_ledger`) - no real client or transaction data
is used in any of the `sample_data/` files, so they're safe to demo without any
confidentiality concern.

**If you use Invoice Check on a real client invoice**, be aware of what
actually happens to that file, since it's real (potentially confidential)
data, unlike the rest of this tool's demo material:

- Nothing is ever saved to disk by the tool itself - the file is read only
  in memory for that one request.
- With no `ANTHROPIC_API_KEY` set, reading happens entirely offline (PDF text
  layer or Tesseract OCR) - nothing about the invoice leaves the machine.
- With a key set, the invoice's actual image/PDF content is sent to
  Anthropic's API for that one reading request, since a vision model has to
  see it to read it - this is different from the plain-language explainer,
  which only ever sends an already-anonymous description. Treat this the way
  you would any cloud AI tool: don't point it at a real client invoice unless
  that's acceptable under your firm's data-handling policy and the client
  engagement terms, or use the offline OCR path instead.

## 12. Disclaimer

This is an academic/certification capstone project built for the ICAI AICA
Level-2 course. It is a decision-support tool, not a substitute for
professional judgement - every verdict should be reviewed against the current
text of the CGST Act before being relied upon for any GST return, audit
working paper, or client advice.
