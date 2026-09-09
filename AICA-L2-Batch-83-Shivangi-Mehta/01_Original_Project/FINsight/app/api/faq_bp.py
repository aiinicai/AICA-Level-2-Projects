"""
FAQ blueprint (Stage 21, explicitly approved) — "Add a last tab at side
panel at the end for FAQ."

A single, static, read-only screen — no database table, no form, no
POST route. The questions/answers below are FinSight's own plain-
language FAQ content (already shared with the user as a standalone
document); this route just renders the same content inside the app
itself, in the shell's normal navigation, so a user doesn't have to
leave the app to find it.

FAQ_ITEMS is a plain Python list of (question, answer) tuples, not a
database table — there is no admin screen to edit these, and adding a
new one is a one-line code change here, the same "visible, explicit"
pattern already used for the rule-module registries elsewhere in this
codebase (see app/rules/audit/__init__.py's own docstring) rather than
a new schema/content-management surface. Answer text may contain
simple HTML (a <br> or <strong>) since it's rendered with the `safe`
filter in the template — every entry below is FinSight's own authored
copy, never user-supplied input, so this is not an XSS concern.
"""
from __future__ import annotations

from flask import Blueprint, render_template

faq_bp = Blueprint("faq", __name__, url_prefix="/faq")

FAQ_ITEMS: list[tuple[str, str]] = [
    (
        "What kind of files can I upload?",
        "CSV or Excel (.xlsx) files — the same format your ledger, trial balance, or transaction data is "
        "usually already exported in.",
    ),
    (
        "Does my file need to be formatted a particular way?",
        "Yes — for the most reliable results, <strong>Row 1 of the sheet should contain only your column "
        "headings</strong> (Date, Account Name, Debit, Credit, and so on), with nothing else above or mixed "
        "into it — no report title, no company name, no merged/blank cells, no logo row. Your actual data "
        "should start immediately from Row 2. FinSight does try to automatically detect the header row if "
        "Row 1 isn't clean, and will show a warning when it isn't fully confident which row is the header, "
        "but this detection isn't guaranteed to get it right every time. Keeping the file to a plain, single "
        "header row followed by data avoids the mapping and review being run against the wrong row.",
    ),
    (
        "Does my data go online anywhere?",
        "No. FinSight runs entirely on your own computer (or your office LAN if you turn on LAN mode for "
        "your team). Nothing is uploaded to the internet or to any outside server.",
    ),
    (
        "What does the app actually check my data against?",
        "Real, existing professional standards — Accounting Standards, Standards on Auditing (SA), and "
        "Income Tax/GST provisions — the same rules a CA already follows. It doesn't invent its own criteria.",
    ),
    (
        "Does it tell me for sure that something is wrong or fraudulent?",
        "No, and it's built deliberately not to. It only says things like \"review required\" or "
        "\"potential risk\" — it flags things worth a professional's attention, but the judgment and "
        "conclusion is always yours, not the app's.",
    ),
    (
        "What happens if there isn't enough data for a check to run properly?",
        "The app says so honestly — it marks that check as \"Insufficient Data\" instead of guessing or "
        "forcing a result from too little information.",
    ),
    (
        "Can it compare this year's numbers with last year's?",
        "Yes, but only if you've also uploaded last year as its own separate entry for the same client. A "
        "few checks (like depreciation consistency and provision reversals) then automatically look back at "
        "that prior year's data. It won't compare years you haven't uploaded.",
    ),
    (
        "Is there a size/amount cutoff below which small mismatches are ignored?",
        "Yes — this is called materiality. Very small differences that wouldn't matter in a real audit are "
        "not flagged, so you're not chasing negligible amounts.",
    ),
    (
        "Once a query/finding is raised, how do I move it forward?",
        "Every finding starts as \"Open.\" You can change its status right there in the Query table (In "
        "Process, Closed, etc.) as you work through it — no need to open a separate screen for a simple "
        "status change.",
    ),
    (
        "Can I add my own notes or the client's response to a finding?",
        "Yes — there's a spot for your Additional Note and a separate spot for the Client's Remark, right "
        "next to each finding, and both are saved separately from the app's own original finding text (so "
        "nothing gets overwritten).",
    ),
    (
        "Can I download my findings/queries as an Excel file?",
        "Yes, there's a one-click \"Download Excel\" option on the Query &amp; Working Papers screen.",
    ),
    (
        "Can I remove a client's data completely if I no longer need it?",
        "Yes — there's a \"Remove\" option on the Engagements page. It permanently deletes everything for "
        "that client and financial year, so use it carefully; there's no undo.",
    ),
    (
        "Can more than one person in my office use it at the same time?",
        "Yes, using LAN mode — it lets FinSight be accessed by others on the same office network, without "
        "needing the internet.",
    ),
    (
        "Will it work for a fresh year like FY 2025-26, or is it only good for one specific year?",
        "It works for any financial year — there's nothing fixed to one particular year in the app. You "
        "create a separate entry per client per year, so it naturally works across FY 2025-26 and previous "
        "years too.",
    ),
    (
        "Does it replace my own review as a CA?",
        "No. Think of it as a fast, consistent first pass that flags what deserves a closer look — the "
        "actual review, judgment, and sign-off remain entirely yours.",
    ),
]


@faq_bp.route("/")
def index():
    return render_template("faq/index.html", section="FAQ", faq_items=FAQ_ITEMS)
