"""Generate the Phase 2 clause skeleton. Build Prompt v2 §4, protocol §3.

    python scripts/scaffold_clauses.py [--force]

Writes one YAML file per clause across all six documents, carrying the
*structure* the approved Clause Register defines — id, number, statutory
reference, effective dates, applicability flags, input type, option set,
repeating blocks — and **no statutory prose**.

Why prose is not generated
--------------------------
Protocol §3: "forty thousand words of generated statutory prose in front of
you under deadline… is the condition under which a well-written fabrication
passes."

So each variant body is a bracketed authoring marker, not a sentence. That is
deliberate and load-bearing: §18.4's pre-export scan rejects any unresolved
`[...]` token, so an unauthored clause **physically cannot reach a signed
document**. The repository is complete and testable; the content is blocked
until a human writes it.

Authoring one clause = replacing its markers with real wording and clearing
`needs_review`. See docs/CONTENT_AUTHORING.md.

Existing files are never overwritten without --force, so the six already
authored clauses survive.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings

MARKER = "[AUTHORING REQUIRED — {clause} / {option}]"

# --------------------------------------------------------------------------
# Clause table
#
# (id, order, number, title, clause_ref, eff_from, eff_to, requires,
#  options, carry_forward, repeating)
#
# `options` is a tuple of (value, label). An empty tuple means a static
# clause with no input. `repeating` is (entity, ((key, label, datatype,
# required), ...)) or None.
# --------------------------------------------------------------------------

SELECT = "select"
CARO = ("caro",)

_YESNO = (("none", "No"), ("yes", "Yes — particulars"))


def caro(num, title, ref_suffix, options=_YESNO, order=0, repeating=None, eff="2021-04-01"):
    return (
        f"caro.{ref_suffix}",
        order,
        num,
        title,
        f"CARO 2020, para 3{num}",
        eff,
        None,
        CARO,
        options,
        "prompt",
        repeating,
    )


DISPUTED_DUES = (
    "statutory_due",
    (
        ("statute", "Name of the Statute", "text", True),
        ("nature", "Nature of the Dues", "text", True),
        ("amount", "Amount (₹)", "amount", True),
        ("period", "Period to which the Amount Relates", "text", True),
        ("forum", "Forum where Dispute is Pending", "text", True),
        ("amount_paid", "Amount Paid under Protest (₹)", "amount", False),
    ),
)

IFC_DEFICIENCIES = (
    "ifc_deficiency",
    (
        ("title", "Deficiency", "text", True),
        ("process", "Process", "text", False),
        ("control", "Control", "longtext", False),
        ("nature", "Nature", "longtext", False),
        ("risk", "Risk", "longtext", False),
        ("severity", "Severity", "text", False),
        ("management_response", "Management Response", "longtext", False),
        ("auditor_assessment", "Auditor Assessment", "longtext", False),
        ("remediation_status", "Status", "text", False),
    ),
)

BOARD_MEETINGS = (
    "board_meeting",
    (
        ("meeting_date", "Date of Meeting", "date", True),
        ("directors_present", "Directors Present", "number", False),
        ("total_directors", "Total Directors", "number", False),
    ),
)

# ---- CARO 2020, all twenty-one clauses at sub-clause granularity ---------

CARO_CLAUSES = [
    caro(
        "(i)(a)(A)",
        "Records of Property, Plant and Equipment",
        "i.a.A",
        order=10,
        options=(
            ("maintained", "Proper records maintained"),
            ("not_maintained", "Records not maintained"),
            ("none", "No property, plant and equipment"),
        ),
    ),
    caro(
        "(i)(a)(B)",
        "Records of Intangible Assets",
        "i.a.B",
        order=20,
        options=(
            ("maintained", "Proper records maintained"),
            ("not_maintained", "Records not maintained"),
            ("none", "No intangible assets"),
        ),
    ),
    caro(
        "(i)(b)",
        "Physical Verification of Property, Plant and Equipment",
        "i.b",
        order=30,
        options=(
            ("verified", "Verified — no material discrepancy"),
            ("discrepancy", "Material discrepancies — dealt with in books"),
            ("not_verified", "Not verified"),
            ("none", "No property, plant and equipment"),
        ),
    ),
    caro(
        "(i)(c)",
        "Title Deeds of Immovable Properties",
        "i.c",
        order=40,
        options=(
            ("held", "Title deeds held in the name of the Company"),
            ("not_held", "Not held in the Company's name — particulars"),
            ("none", "No immovable property"),
        ),
    ),
    caro(
        "(i)(d)",
        "Revaluation of Property, Plant and Equipment or Intangible Assets",
        "i.d",
        order=50,
        options=(
            ("none", "No revaluation during the year"),
            ("below_10", "Revalued by a registered valuer — change below 10%"),
            ("above_10", "Revalued — change of 10% or more"),
        ),
    ),
    caro(
        "(i)(e)",
        "Proceedings under the Benami Transactions (Prohibition) Act, 1988",
        "i.e",
        order=60,
        options=(
            ("none", "No proceedings initiated or pending"),
            ("pending", "Proceedings initiated or pending — particulars"),
        ),
    ),
    caro(
        "(ii)(a)",
        "Physical Verification of Inventory",
        "ii.a",
        order=70,
        options=(
            ("verified", "Verified — no discrepancy of 10% or more"),
            ("discrepancy", "Discrepancies of 10% or more — dealt with in books"),
            ("not_verified", "Not verified"),
            ("none", "No inventory"),
        ),
    ),
    caro(
        "(ii)(b)",
        "Working Capital Limits against Security of Current Assets",
        "ii.b",
        order=80,
        options=(
            ("none", "No sanction in excess of ₹5 crore"),
            ("agree", "Quarterly returns agree with the books"),
            ("differ", "Quarterly returns do not agree — particulars"),
        ),
    ),
    caro(
        "(iii)(a)",
        "Loans, Advances, Guarantees and Security Granted",
        "iii.a",
        order=90,
        options=(("none", "None granted"), ("granted", "Granted — particulars")),
    ),
    caro(
        "(iii)(b)",
        "Terms and Conditions Not Prejudicial to the Company's Interest",
        "iii.b",
        order=100,
        options=(
            ("not_prejudicial", "Not prejudicial"),
            ("prejudicial", "Prejudicial — particulars"),
            ("na", "Not applicable"),
        ),
    ),
    caro(
        "(iii)(c)",
        "Schedule of Repayment and Regularity of Receipts",
        "iii.c",
        order=110,
        options=(
            ("regular", "Stipulated and regular"),
            ("irregular", "Not regular — particulars"),
            ("na", "Not applicable"),
        ),
    ),
    caro(
        "(iii)(d)",
        "Amounts Overdue for More than Ninety Days",
        "iii.d",
        order=120,
        options=(
            ("none", "No amount overdue"),
            ("overdue", "Overdue — particulars and steps taken"),
        ),
    ),
    caro("(iii)(e)", "Loans Renewed, Extended or Settled by Fresh Loans", "iii.e", order=130),
    caro("(iii)(f)", "Loans Repayable on Demand or Without Terms of Repayment", "iii.f", order=140),
    caro(
        "(iv)",
        "Compliance with Sections 185 and 186",
        "iv",
        order=150,
        options=(
            ("complied", "Complied"),
            ("not_complied", "Not complied — particulars"),
            ("na", "Not applicable"),
        ),
    ),
    caro(
        "(v)",
        "Deposits and Amounts Deemed to be Deposits",
        "v",
        order=160,
        options=(
            ("none", "No deposits accepted"),
            ("complied", "Complied with sections 73 to 76"),
            ("not_complied", "Not complied — particulars"),
        ),
    ),
    caro(
        "(vi)",
        "Maintenance of Cost Records under Section 148(1)",
        "vi",
        order=170,
        options=(
            ("na", "Not applicable"),
            ("maintained", "Maintained"),
            ("not_maintained", "Not maintained"),
        ),
    ),
    caro(
        "(vii)(a)",
        "Regularity in Depositing Undisputed Statutory Dues",
        "vii.a",
        order=180,
        options=(
            ("regular", "Regular — no arrears beyond six months"),
            ("arrears", "Arrears outstanding — particulars"),
        ),
    ),
    # caro.vii.b is already authored; skipped by the writer.
    caro(
        "(viii)", "Unrecorded Income Surrendered or Disclosed in Tax Assessments", "viii", order=200
    ),
    caro(
        "(ix)(a)",
        "Default in Repayment of Borrowings or Interest",
        "ix.a",
        order=210,
        options=(("none", "No default"), ("default", "Default — particulars")),
    ),
    caro(
        "(ix)(b)",
        "Declared Wilful Defaulter",
        "ix.b",
        order=220,
        options=(
            ("none", "Not a declared wilful defaulter"),
            ("declared", "Declared — particulars"),
        ),
    ),
    caro(
        "(ix)(c)",
        "Term Loans Applied for the Purpose Obtained",
        "ix.c",
        order=230,
        options=(
            ("applied", "Applied for the purpose obtained"),
            ("diverted", "Not so applied — particulars"),
            ("none", "No term loans"),
        ),
    ),
    caro("(ix)(d)", "Short-term Funds Used for Long-term Purposes", "ix.d", order=240),
    caro(
        "(ix)(e)",
        "Funds Taken to Meet Obligations of Subsidiaries, Associates or Joint Ventures",
        "ix.e",
        order=250,
    ),
    caro(
        "(ix)(f)",
        "Loans Raised on Pledge of Securities of Subsidiaries, Joint Ventures or " "Associates",
        "ix.f",
        order=260,
    ),
    caro(
        "(x)(a)",
        "Money Raised by Initial or Further Public Offer",
        "x.a",
        order=270,
        options=(
            ("none", "No money raised"),
            ("applied", "Applied for the purposes raised"),
            ("not_applied", "Not so applied — particulars"),
        ),
    ),
    caro(
        "(x)(b)",
        "Preferential Allotment or Private Placement",
        "x.b",
        order=280,
        options=(
            ("none", "No such allotment"),
            ("complied", "Complied with sections 42 and 62"),
            ("not_complied", "Not complied — particulars"),
        ),
    ),
    caro(
        "(xi)(a)",
        "Fraud by the Company or on the Company",
        "xi.a",
        order=290,
        options=(
            ("none", "No fraud noticed or reported"),
            ("noticed", "Fraud noticed or reported — nature and amount"),
        ),
    ),
    caro(
        "(xi)(b)",
        "Report under Section 143(12) in Form ADT-4",
        "xi.b",
        order=300,
        options=(
            ("na", "No report required"),
            ("filed", "Filed"),
            ("not_filed", "Required but not filed"),
        ),
    ),
    caro(
        "(xi)(c)",
        "Whistle-blower Complaints Considered",
        "xi.c",
        order=310,
        options=(("none", "None received"), ("received", "Received and considered — particulars")),
    ),
    caro(
        "(xii)(a)",
        "Nidhi Company — Net Owned Funds to Deposits Ratio",
        "xii.a",
        order=320,
        options=(
            ("na", "Not a Nidhi company"),
            ("maintained", "Ratio maintained"),
            ("not_maintained", "Ratio not maintained"),
        ),
    ),
    caro(
        "(xii)(b)",
        "Nidhi Company — Unencumbered Term Deposits",
        "xii.b",
        order=330,
        options=(
            ("na", "Not a Nidhi company"),
            ("maintained", "Maintained"),
            ("not_maintained", "Not maintained"),
        ),
    ),
    caro(
        "(xii)(c)",
        "Nidhi Company — Default in Payment of Interest or Repayment of Deposits",
        "xii.c",
        order=340,
        options=(
            ("na", "Not a Nidhi company"),
            ("none", "No default"),
            ("default", "Default — particulars"),
        ),
    ),
    caro(
        "(xiii)",
        "Related Party Transactions — Sections 177 and 188",
        "xiii",
        order=350,
        options=(
            ("complied", "Complied and disclosed"),
            ("not_complied", "Not complied — particulars"),
            ("none", "No related party transactions"),
        ),
    ),
    caro(
        "(xiv)(a)",
        "Internal Audit System Commensurate with Size and Nature of Business",
        "xiv.a",
        order=360,
        options=(
            ("commensurate", "System commensurate"),
            ("not_commensurate", "System not commensurate"),
            ("na", "Internal audit not applicable"),
        ),
    ),
    caro(
        "(xiv)(b)",
        "Internal Audit Reports Considered by the Statutory Auditor",
        "xiv.b",
        order=370,
        options=(
            ("considered", "Considered"),
            ("not_available", "Not made available"),
            ("na", "Not applicable"),
        ),
    ),
    caro(
        "(xv)",
        "Non-cash Transactions with Directors — Section 192",
        "xv",
        order=380,
        options=(
            ("none", "No such transactions"),
            ("complied", "Complied"),
            ("not_complied", "Not complied — particulars"),
        ),
    ),
    caro(
        "(xvi)(a)",
        "Registration under Section 45-IA of the Reserve Bank of India Act, 1934",
        "xvi.a",
        order=390,
        options=(
            ("na", "Registration not required"),
            ("obtained", "Required and obtained"),
            ("not_obtained", "Required and not obtained"),
        ),
    ),
    caro(
        "(xvi)(b)",
        "Non-Banking Financial or Housing Finance Activity without a Valid "
        "Certificate of Registration",
        "xvi.b",
        order=400,
    ),
    caro(
        "(xvi)(c)",
        "Core Investment Company Criteria",
        "xvi.c",
        order=410,
        options=(
            ("na", "Not a Core Investment Company"),
            ("fulfils", "Is a CIC and fulfils the criteria"),
            ("not_fulfils", "Is a CIC and does not fulfil the criteria"),
        ),
    ),
    caro(
        "(xvi)(d)",
        "Number of Core Investment Companies in the Group",
        "xvi.d",
        order=420,
        options=(("none", "None"), ("one", "One"), ("more", "More than one — number")),
    ),
    caro(
        "(xvii)",
        "Cash Losses in the Current and Immediately Preceding Financial Year",
        "xvii",
        order=430,
        options=(
            ("none", "No cash losses in either year"),
            ("incurred", "Cash losses incurred — amounts"),
        ),
    ),
    caro(
        "(xviii)",
        "Resignation of the Statutory Auditors",
        "xviii",
        order=440,
        options=(
            ("none", "No resignation during the year"),
            ("considered", "Resignation — issues considered"),
            ("no_issues", "Resignation — no issues raised"),
        ),
    ),
    caro(
        "(xix)",
        "Material Uncertainty on Meeting Liabilities within One Year",
        "xix",
        order=450,
        options=(
            ("none", "No material uncertainty exists"),
            ("exists", "Material uncertainty exists — particulars"),
        ),
    ),
    caro(
        "(xx)(a)",
        "Unspent CSR Amount Transferred to a Schedule VII Fund",
        "xx.a",
        order=460,
        options=(
            ("na", "CSR not applicable"),
            ("none", "No unspent amount"),
            ("transferred", "Transferred within time"),
            ("not_transferred", "Not transferred — particulars"),
        ),
    ),
    caro(
        "(xx)(b)",
        "Unspent Amount for Ongoing Projects Transferred to a Special Account",
        "xx.b",
        order=470,
        options=(
            ("na", "CSR not applicable"),
            ("none", "No ongoing projects"),
            ("transferred", "Transferred within thirty days"),
            ("not_transferred", "Not transferred — particulars"),
        ),
    ),
    caro(
        "(xxi)",
        "Qualifications or Adverse Remarks in the CARO Reports of Companies Included "
        "in the Consolidated Financial Statements",
        "xxi",
        order=480,
        options=(
            ("none", "No qualifications or adverse remarks"),
            ("exist", "Qualifications or adverse remarks — particulars"),
        ),
    ),
]


def _clause(
    cid,
    doc,
    order,
    number,
    title,
    ref,
    eff_from,
    eff_to,
    requires,
    options,
    carry_forward,
    repeating,
    datatype=SELECT,
):
    return {
        "id": cid,
        "document": doc,
        "order": order,
        "number": number,
        "title": title,
        "clause_ref": ref,
        "effective_from": eff_from,
        "effective_to": eff_to,
        "requires": requires,
        "options": options,
        "carry_forward": carry_forward,
        "repeating": repeating,
        "datatype": datatype,
    }


def caro_specs() -> list[dict]:
    out = []
    for row in CARO_CLAUSES:
        cid, order, number, title, ref, eff, eff_to, requires, options, cf, rep = row
        out.append(
            _clause(
                cid, "caro_2020", order, number, title, ref, eff, eff_to, requires, options, cf, rep
            )
        )
    return out


# ---- Auditor's Report: s.143(3) and the signature block -----------------

S143 = [
    (
        "iar.143.3.a",
        500,
        "(a)",
        "Information and Explanations Sought and Obtained",
        "s.143(3)(a)",
        (("obtained", "Obtained"), ("not_obtained", "Not obtained — effect stated")),
    ),
    (
        "iar.143.3.b",
        510,
        "(b)",
        "Proper Books of Account Kept",
        "s.143(3)(b)",
        (("kept", "Proper books kept"), ("not_kept", "Not kept — particulars")),
    ),
    (
        "iar.143.3.c",
        520,
        "(c)",
        "Branch Audit Reports Received and Dealt With",
        "s.143(3)(c); s.143(8)",
        (
            ("none", "No branches"),
            ("by_us", "Branch audited by us"),
            ("by_other", "Branch audited by another auditor"),
        ),
    ),
    (
        "iar.143.3.d",
        530,
        "(d)",
        "Financial Statements in Agreement with the Books",
        "s.143(3)(d)",
        (("agree", "In agreement"), ("differ", "Not in agreement")),
    ),
    (
        "iar.143.3.e",
        540,
        "(e)",
        "Compliance with the Accounting Standards",
        "s.143(3)(e); s.133",
        (("comply", "Comply"), ("not_comply", "Do not comply — particulars")),
    ),
    (
        "iar.143.3.f",
        550,
        "(f)",
        "Observations Having an Adverse Effect on the Functioning of " "the Company",
        "s.143(3)(f)",
        (("none", "No such observations"), ("exist", "Observations — particulars")),
    ),
    (
        "iar.143.3.g",
        560,
        "(g)",
        "Disqualification of Directors under Section 164(2)",
        "s.143(3)(g); s.164(2)",
        (("none", "No director disqualified"), ("disqualified", "Disqualified — names")),
    ),
    (
        "iar.143.3.h",
        570,
        "(h)",
        "Qualification, Reservation or Adverse Remark on the " "Maintenance of Accounts",
        "s.143(3)(h)",
        (("none", "None"), ("exist", "Particulars")),
    ),
    (
        "iar.143.3.i",
        580,
        "(i)",
        "Adequacy and Operating Effectiveness of Internal Financial " "Controls",
        "s.143(3)(i)",
        (
            ("applicable", "Reporting applicable — see Annexure B"),
            ("exempt private company", "Exempt private company"),
        ),
    ),
    (
        "iar.197.16",
        590,
        "—",
        "Managerial Remuneration under Section 197",
        "s.197(16)",
        (
            ("complied", "Paid in accordance with section 197"),
            ("not_complied", "Not in accordance — particulars"),
            ("na", "Not applicable to a private company"),
        ),
    ),
]

RULE11_A_COLUMNS = (
    ("forum", "Court / Forum", "text", True),
    ("case_number", "Case No.", "text", False),
    ("nature", "Nature of Dispute", "text", True),
    ("amount", "Amount Involved (₹)", "amount", False),
    ("period", "Period / AY", "text", False),
    ("status", "Status", "text", False),
    ("mgmt_assessment", "Management Assessment", "longtext", False),
)


def auditors_report_specs() -> list[dict]:
    out = []
    for cid, order, number, title, ref, options in S143:
        requires = ("ifc",) if cid == "iar.143.3.i" else ()
        if cid == "iar.197.16":
            requires = ("s197",)
        out.append(
            _clause(
                cid,
                "auditors_report",
                order,
                number,
                title,
                ref,
                "2014-04-01",
                None,
                requires,
                options,
                "prompt",
                None,
            )
        )
    # The narrative behind a modified opinion. §9 blocks export without it.
    out.append(
        _clause(
            "iar.basis.modified",
            "auditors_report",
            20,
            "—",
            "Basis for Qualified, Adverse or Disclaimer of Opinion",
            "SA 705 paras 20-22",
            "2014-04-01",
            None,
            (),
            (("qualified", "Qualified"), ("adverse", "Adverse"), ("disclaimer", "Disclaimer")),
            "never",
            None,
            SELECT,
        )
    )
    return out


# ---- The four documents with no clauses at all --------------------------

IFC_SPECS = [
    (
        "ifc.opinion",
        10,
        "—",
        "Opinion on Internal Financial Controls",
        "Guidance Note on Audit of Internal Financial Controls",
        (
            ("adequate", "Adequate and operating effectively"),
            ("material weakness", "Material weakness identified"),
            ("significant deficiency", "Significant deficiency identified"),
        ),
        None,
    ),
    (
        "ifc.deficiencies",
        20,
        "—",
        "Control Deficiencies",
        "Guidance Note on Audit of Internal Financial Controls",
        (("none", "None"), ("exist", "Deficiencies — see table")),
        IFC_DEFICIENCIES,
    ),
]

BDR_SPECS = [
    ("bdr.annual.return", 10, "(a)", "Web Address of the Annual Return", "s.134(3)(a)"),
    ("bdr.board.meetings", 20, "(b)", "Number of Meetings of the Board", "s.134(3)(b)"),
    ("bdr.drs", 30, "(c)", "Directors' Responsibility Statement", "s.134(3)(c); s.134(5)"),
    (
        "bdr.fraud.143.12",
        40,
        "(ca)",
        "Frauds Reported by Auditors under Section 143(12)",
        "s.134(3)(ca)",
    ),
    ("bdr.id.declaration", 50, "(d)", "Declaration by Independent Directors", "s.134(3)(d)"),
    (
        "bdr.nrc.policy",
        60,
        "(e)",
        "Policy on Directors' Appointment and Remuneration",
        "s.134(3)(e); s.178(3)",
    ),
    (
        "bdr.auditor.remarks",
        70,
        "(f)",
        "Board's Explanation on the Auditor's Qualifications",
        "s.134(3)(f)",
    ),
    (
        "bdr.loans.186",
        80,
        "(g)",
        "Loans, Guarantees and Investments under Section 186",
        "s.134(3)(g)",
    ),
    ("bdr.rpt.188", 90, "(h)", "Related Party Contracts — Form AOC-2", "s.134(3)(h); Rule 8(2)"),
    ("bdr.state.affairs", 100, "(i)", "State of the Company's Affairs", "s.134(3)(i)"),
    ("bdr.reserves", 110, "(j)", "Amounts Carried to Reserves", "s.134(3)(j)"),
    ("bdr.dividend", 120, "(k)", "Dividend Recommended", "s.134(3)(k)"),
    (
        "bdr.material.changes",
        130,
        "(l)",
        "Material Changes and Commitments after the Year End",
        "s.134(3)(l)",
    ),
    (
        "bdr.conservation",
        140,
        "(m)",
        "Conservation of Energy, Technology Absorption and " "Foreign Exchange",
        "s.134(3)(m); Rule 8(3)",
    ),
    ("bdr.risk.management", 150, "(n)", "Risk Management Policy", "s.134(3)(n)"),
    ("bdr.csr", 160, "(o)", "Corporate Social Responsibility", "s.134(3)(o); Rule 9 CSR Rules"),
    ("bdr.board.evaluation", 170, "(p)", "Annual Evaluation of Board Performance", "s.134(3)(p)"),
    ("bdr.vigil.mechanism", 180, "—", "Vigil Mechanism", "s.177(9)"),
    (
        "bdr.employees.remuneration",
        190,
        "—",
        "Particulars of Employees and Remuneration",
        "s.197(12); Rule 5",
    ),
    ("bdr.financial.summary", 200, "Rule 8(5)(i)", "Financial Summary", "Rule 8(5)(i)"),
    (
        "bdr.nature.business",
        210,
        "Rule 8(5)(ii)",
        "Change in the Nature of Business",
        "Rule 8(5)(ii)",
    ),
    (
        "bdr.directors.kmp",
        220,
        "Rule 8(5)(iii)",
        "Directors and Key Managerial Personnel " "Appointed or Resigned",
        "Rule 8(5)(iii)",
    ),
    (
        "bdr.subsidiaries",
        230,
        "Rule 8(5)(iv)",
        "Subsidiaries, Joint Ventures and Associates",
        "Rule 8(5)(iv)",
    ),
    ("bdr.deposits", 240, "Rule 8(5)(v)", "Deposits under Chapter V", "Rule 8(5)(v)"),
    (
        "bdr.deposits.noncompliant",
        250,
        "Rule 8(5)(vi)",
        "Deposits Not in Compliance with " "Chapter V",
        "Rule 8(5)(vi)",
    ),
    (
        "bdr.regulator.orders",
        260,
        "Rule 8(5)(vii)",
        "Significant Orders of Regulators, Courts " "or Tribunals",
        "Rule 8(5)(vii)",
    ),
    (
        "bdr.ifc.adequacy",
        270,
        "Rule 8(5)(viii)",
        "Adequacy of Internal Financial Controls",
        "Rule 8(5)(viii)",
    ),
    ("bdr.cost.records", 280, "Rule 8(5)(ix)", "Maintenance of Cost Records", "Rule 8(5)(ix)"),
    (
        "bdr.posh",
        290,
        "Rule 8(5)(x)",
        "Sexual Harassment of Women at Workplace Act, 2013",
        "Rule 8(5)(x)",
    ),
    (
        "bdr.ibc",
        300,
        "Rule 8(5)(xi)",
        "Proceedings under the Insolvency and Bankruptcy Code",
        "Rule 8(5)(xi)",
    ),
    (
        "bdr.otsettlement",
        310,
        "Rule 8(5)(xii)",
        "Difference in Valuation on One-time Settlement",
        "Rule 8(5)(xii)",
    ),
    ("bdr.secretarial.audit", 320, "—", "Secretarial Audit Report", "s.204"),
    (
        "bdr.secretarial.standards",
        330,
        "—",
        "Compliance with Secretarial Standards",
        "SS-1 and SS-2",
    ),
]

MRL_SPECS = [
    ("mrl.resp.fs", 10, "Responsibility for the Financial Statements", "SA 580 para 10(a)"),
    (
        "mrl.framework",
        20,
        "Compliance with the Applicable Financial Reporting Framework",
        "SA 580 para 10(a)",
    ),
    ("mrl.info.access", 30, "Provision of Information and Access", "SA 580 para 11(a)"),
    ("mrl.transactions.recorded", 40, "All Transactions Recorded", "SA 580 para 11(b)"),
    ("mrl.estimates", 50, "Significant Assumptions in Accounting Estimates", "SA 540"),
    ("mrl.related.parties", 60, "Related Party Relationships and Transactions", "SA 550 para 26"),
    ("mrl.subsequent.events", 70, "Subsequent Events", "SA 560"),
    ("mrl.uncorrected", 80, "Uncorrected Misstatements", "SA 450 para 14"),
    (
        "mrl.fraud.responsibility",
        90,
        "Responsibility for Internal Control over Fraud",
        "SA 240 para 39(a)",
    ),
    ("mrl.fraud.disclosure", 100, "Disclosure of Known or Suspected Fraud", "SA 240 para 39(b)"),
    ("mrl.laws", 110, "Non-compliance with Laws and Regulations", "SA 250 para 16"),
    ("mrl.litigation", 120, "Litigation and Claims", "SA 501 para 12"),
    ("mrl.going.concern", 130, "Going Concern Plans", "SA 570 para 16(b)"),
    ("mrl.inventory", 140, "Existence, Condition and Valuation of Inventory", "SA 501"),
    ("mrl.title.assets", 150, "Title to Assets and Encumbrances", "SA 580 Appendix 2"),
    ("mrl.contingent", 160, "Contingent Liabilities and Commitments", "Schedule III"),
    ("mrl.bank.balances", 170, "Completeness of Bank Accounts and Balances", "SA 505"),
    ("mrl.companies.act", 180, "Compliance with the Companies Act, 2013", "Companies Act, 2013"),
    ("mrl.deposits", 190, "Deposits under Sections 73 to 76", "ss.73-76"),
    ("mrl.185.186", 200, "Compliance with Sections 185 and 186", "ss.185, 186"),
    ("mrl.csr", 210, "Corporate Social Responsibility Obligations", "s.135"),
    ("mrl.audit.trail", 220, "Audit Trail Feature", "Rule 3(1) proviso"),
    ("mrl.benami", 230, "Benami Transactions (Prohibition) Act, 1988", "Benami Act, 1988"),
    ("mrl.crypto", 240, "Crypto Currency and Virtual Digital Assets", "Schedule III"),
    (
        "mrl.undisclosed.income",
        250,
        "Undisclosed Income Surrendered in Tax Assessments",
        "Income Tax Act, 1961",
    ),
    (
        "mrl.ultimate.beneficiary",
        260,
        "Intermediaries, Funding Parties and Ultimate " "Beneficiaries",
        "Rule 11(e)",
    ),
    ("mrl.wilful.defaulter", 270, "Wilful Defaulter Status", "RBI Master Circular"),
    ("mrl.struck.off", 280, "Transactions with Companies Struck Off", "Schedule III"),
    ("mrl.charges", 290, "Registration and Satisfaction of Charges", "s.77"),
    ("mrl.layers", 300, "Restriction on the Number of Layers of Subsidiaries", "s.2(87) proviso"),
]

ENG_SPECS = [
    ("eng.objective", 10, "Objective and Scope of the Audit", "SA 210 para 10(a)"),
    ("eng.resp.auditor", 20, "Responsibilities of the Auditor", "SA 210 para 10(b)"),
    (
        "eng.resp.mgmt",
        30,
        "Responsibilities of Management and the Premise of the Audit",
        "SA 210 para 10(c)",
    ),
    ("eng.framework", 40, "Applicable Financial Reporting Framework", "SA 210 para 10(d)"),
    ("eng.report.form", 50, "Expected Form and Content of Reports", "SA 210 para 10(e)"),
    ("eng.limitations", 60, "Inherent Limitations of an Audit", "SA 210 para A23"),
    ("eng.caro.scope", 70, "Reporting under CARO 2020 and Rule 11", "s.143(11); Rule 11"),
    ("eng.ifc.scope", 80, "Reporting on Internal Financial Controls", "s.143(3)(i)"),
    (
        "eng.independence",
        90,
        "Independence and Eligibility under Section 141",
        "s.141; ICAI Code of Ethics",
    ),
    ("eng.nonaudit", 100, "Restriction on Non-audit Services", "s.144"),
    ("eng.fees", 110, "Fees and Billing", "SA 210 para A24"),
    (
        "eng.experts",
        120,
        "Auditor's Experts, Internal Auditors and Component Auditors",
        "SA 620; SA 610; SA 600",
    ),
    (
        "eng.confidentiality",
        130,
        "Confidentiality and Handling of Client Data",
        "ICAI Code of Ethics",
    ),
    ("eng.workpapers", 140, "Ownership and Retention of Working Papers", "SQC 1 paras 45-47"),
    (
        "eng.peer.review",
        150,
        "Access for Peer Review and Regulatory Inspection",
        "ICAI Peer Review Guidelines",
    ),
    ("eng.udin", 160, "Unique Document Identification Number", "ICAI UDIN Guidelines"),
    ("eng.duration", 170, "Continuing Nature of the Engagement", "SA 210 para 13"),
    (
        "eng.acknowledgement",
        180,
        "Acknowledgement by Those Charged with Governance",
        "SA 210 para 10",
    ),
]

CONFIRM = (("confirmed", "Confirmed"), ("exception", "Exception — particulars"))


def other_specs() -> list[dict]:
    out: list[dict] = []
    for cid, order, number, title, ref, options, rep in IFC_SPECS:
        out.append(
            _clause(
                cid,
                "ifc_report",
                order,
                number,
                title,
                ref,
                "2015-04-01",
                None,
                ("ifc",),
                options,
                "prompt",
                rep,
            )
        )
    for cid, order, number, title, ref in BDR_SPECS:
        rep = BOARD_MEETINGS if cid == "bdr.board.meetings" else None
        out.append(
            _clause(
                cid,
                "directors_report",
                order,
                number,
                title,
                ref,
                "2014-04-01",
                None,
                (),
                CONFIRM,
                "prompt",
                rep,
            )
        )
    for cid, order, title, ref in MRL_SPECS:
        out.append(
            _clause(
                cid, "mrl", order, "—", title, ref, "2014-04-01", None, (), CONFIRM, "prompt", None
            )
        )
    for cid, order, title, ref in ENG_SPECS:
        out.append(
            _clause(
                cid,
                "engagement_letter",
                order,
                "—",
                title,
                ref,
                "2014-04-01",
                None,
                (),
                CONFIRM,
                "prompt",
                None,
            )
        )
    return out


# --------------------------------------------------------------------------
# Writer
# --------------------------------------------------------------------------

DOC_DIR = {
    "caro_2020": "caro_2020",
    "auditors_report": "auditors_report",
    "ifc_report": "ifc_report",
    "directors_report": "directors_report",
    "mrl": "mrl",
    "engagement_letter": "engagement_letter",
}


def _yaml_for(spec: dict) -> str:
    lines = [
        "# SKELETON — structure only. No statutory wording has been written.",
        "#",
        "# Each variant body is an authoring marker, not a sentence. The §18.4",
        "# pre-export scan rejects any unresolved [...] token, so this clause",
        "# cannot reach a signed document until someone writes the wording and",
        "# clears needs_review. See docs/CONTENT_AUTHORING.md.",
        "",
        f"id: {spec['id']}",
        f"document: {spec['document']}",
        f"order: {spec['order']}",
        f'number: "{spec["number"]}"',
        f'title: "{spec["title"]}"',
        f'clause_ref: "{spec["clause_ref"]}"',
        f'effective_from: "{spec["effective_from"]}"',
        f"effective_to: {spec['effective_to'] or 'null'}",
        "",
        "needs_review: true",
        "",
    ]
    if spec["requires"]:
        lines += ["applicability:", f"  requires: [{', '.join(spec['requires'])}]", ""]

    lines += [
        "input:",
        f"  key: {spec['id']}",
        f'  label: "{spec["title"]}"',
        f"  datatype: {spec['datatype']}",
        f"  carry_forward: {spec['carry_forward']}",
        "  mandatory: true",
        "  options:",
    ]
    for value, label in spec["options"]:
        lines.append(f'    - {{ value: "{value}", label: "{label}" }}')
    lines.append("")

    if spec["repeating"]:
        entity, columns = spec["repeating"]
        adverse = spec["options"][-1][0]
        lines += [
            "repeating_block:",
            f"  when: \"value == '{adverse}'\"",
            f"  entity: {entity}",
            "  min_rows: 1",
            "  carry_forward: prompt",
            "  columns:",
        ]
        for key, label, datatype, required in columns:
            required_bit = ", required: true" if required else ""
            lines.append(
                f'    - {{ key: {key}, label: "{label}", datatype: {datatype}{required_bit} }}'
            )
        lines.append("")

    lines.append("variants:")
    for index, (value, _label) in enumerate(spec["options"]):
        marker = MARKER.format(clause=spec["id"], option=value)
        lines += [f"  - when: \"value == '{value}'\"", f'    body: "{marker}"']
        if index == len(spec["options"]) - 1 and len(spec["options"]) > 1:
            lines.append("    severity: exception")
            lines.append("    requires_narrative: true")
            if spec["repeating"]:
                lines.append("    render_block: table")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing clause files")
    args = parser.parse_args()

    content = get_settings().content_path
    specs = caro_specs() + auditors_report_specs() + other_specs()

    # Skip by clause *id*, not by filename. An authored clause may live under
    # any filename, and writing a second file with the same id would make the
    # repository refuse to load.
    existing_ids: set[str] = set()
    for path in content.rglob("*.yaml"):
        if path.name in {"manifest.yaml", "applicability_rules.yaml"}:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("id:"):
                existing_ids.add(line.split(":", 1)[1].strip())
                break

    written = skipped = 0
    by_document: dict[str, int] = {}

    for spec in specs:
        folder = content / DOC_DIR[spec["document"]]
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{spec['id'].replace('.', '_')}.yaml"
        if spec["id"] in existing_ids and not args.force:
            skipped += 1
            continue
        path.write_text(_yaml_for(spec), encoding="utf-8")
        written += 1
        by_document[spec["document"]] = by_document.get(spec["document"], 0) + 1

    print(f"written: {written}   skipped (already exist): {skipped}")
    for document, count in sorted(by_document.items()):
        print(f"  {document:22s} {count}")
    print()
    print("Every clause is needs_review and every body is an authoring marker.")
    print("None can reach an export until the wording is written.")
    print("Add the new clause ids to content/manifest.yaml, then run scripts/seed.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
