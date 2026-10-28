"""Guided Rule 11(g) engagement workflow, built on the ICAI Implementation Guide on Reporting on Audit Trail
(Revised 2024 Edition) and the ICAI EKM "Practical Aspects relating to Audit Trail Reporting".

Paragraph numbers (para N) and FAQ numbers (FAQ N) below refer to the Implementation Guide. Statute references:
  Rule 11(g)  Companies (Audit and Auditors) Rules, 2014 (inserted by GSR 206(E) of 24-03-2021; reporting from FY 2023-24 in practice)
  Rule 3(1) proviso, Rule 3(5)  Companies (Accounts) Rules, 2014 (edit log; cannot be disabled; from 1-04-2023; daily back-up in India)
  s.2(13), s.128(5), s.143(3)(b),(h),(i),(j), s.143(12); SA 230, 250, 402, 580, 600, 700, 705.

The module proposes; the auditor decides. Nothing here is a conclusion until the auditor records it.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

DISCLAIMER = ("Aid to the auditor's professional judgement. It does not replace SA procedures, the ICAI Implementation Guide "
              "or the statute, and it is not legal advice. Check the current text of the Act and Rules before signing.")

# --------------------------------------------------------------------------- workflow
STEPS = [
    ("1", "Applicability", "Is Rule 11(g) applicable, and for which year?", "paras 14-18; FAQ 1, 2, 13"),
    ("2", "Software inventory", "Which software maintains the books of account (s.2(13))?", "paras 11-12, 20-21; Appendix I; FAQ 25"),
    ("3", "Controls and configuration", "Is the feature on, protected and monitored throughout the year?", "paras 20, 23-25; FAQ 3-8, 15"),
    ("4", "Edit Log data", "Load the Tally Edit Log (all versions) and run the tests.", "para 25(v); FAQ 17, 21, 22"),
    ("5", "Preservation", "Back-up in India, 8-year retention, retrievability.", "para 19, 26; Rule 3(5); s.128(5); FAQ 18, 20"),
    ("6", "Management representation", "Obtain the written representations.", "para 34; Appendix II; SA 580"),
    ("7", "Conclusion", "Form the opinion and read across to s.143(3)(b), (h), (i).", "paras 27-33; FAQ 24"),
    ("8", "Report and file", "Draft the wording and assemble the audit documentation.", "paras 28-31, 35; SA 230"),
]

APPLICABILITY_QS = [
    ("entity", "Type of entity", ["Company (incl. Section 8, OPC, small, Nidhi, producer, listed, banks/NBFCs)",
                                  "Foreign company (Chapter XXII)", "LLP / partnership / proprietorship / trust / society"],
     "Rule 11(g) is a Companies Act reporting requirement. LLPs, firms, trusts and societies are outside it (EKM). "
     "Banks and NBFCs that are companies are covered (FAQ 13); there is no exemption for small or Section 8 companies (para 15, FAQ 1)."),
    ("mode", "How are the books maintained?", ["Electronically, in accounting software", "Partly electronic", "Entirely manually"],
     "If the books are entirely manual, Rule 11(g) does not apply and the auditor says so as a statement of fact (para 16)."),
    ("fs", "Financial statements being reported on", ["Standalone", "Consolidated"],
     "Consolidated: report on the parent and rely on the auditors of Indian-company components (SA 600). Non-company and foreign "
     "components are outside the Act (paras 17-18)."),
]

# --------------------------------------------------------------------------- software inventory (Appendix I)
INVENTORY_COLS = ["Software", "Records maintained (books of account)", "Hosting location", "In-house / outsourced",
                  "Database", "Operating system", "Audit trail enabled (Yes/No/Not known)", "Feeds the main ledger directly (Yes/No)"]
INVENTORY_EXAMPLE = [
    {"Software": "TallyPrime", "Records maintained (books of account)": "Vouchers, ledgers, stock", "Hosting location": "Company office, Kochi",
     "In-house / outsourced": "In-house", "Database": "Tally data files", "Operating system": "Windows 11",
     "Audit trail enabled (Yes/No/Not known)": "Yes", "Feeds the main ledger directly (Yes/No)": "Yes"}]
INVENTORY_PROMPTS = [
    "Payroll, fixed-asset register, inventory/ERP, billing, POS, bank-reconciliation tools or spreadsheets that auto-post to the books "
    "belong in this list (para 11; FAQ 25: PPE registers and spreadsheets with a direct auto-feed to the books are accounting software).",
    "Master data (vendors, customers, ledgers, stock items) is part of the books because payments and invoices refer to it - its changes "
    "need an audit trail too (FAQ 25a). The TDL exports ledger, group and stock-item logs for this reason.",
    "Purchase/sales orders and price masters: judgement - include them where terms are fixed at invoice/receipt and they feed the books (FAQ 25b).",
    "Third-party hosted or SaaS software: obtain a SOC 1/SOC 2/SAE 3402 report that specifically covers audit trail and covers the whole "
    "year (paras 22; FAQ 8, 19).",
]

# --------------------------------------------------------------------------- control tests
@dataclass
class Control:
    id: str
    area: str
    test: str
    ref: str
    how: str                       # how to evidence it in TallyPrime
    critical: bool = False        # an exception here points to a modified report


CONTROLS = [
    Control("C1", "Feature present", "The accounting software has an audit trail (edit log) that records each change with date and time.",
            "Rule 3(1) proviso; para 7-8; FAQ 3",
            "TallyPrime: F3 Company > Alter > 'Enable Edit Log' / Company Features; confirm on your release; screenshot with date.", True),
    Control("C2", "Cannot be disabled", "The feature cannot be switched off, or, if it can, access to do so is restricted and changes are logged.",
            "Rule 3(1) proviso; paras 20, 23-25(i)-(iii)",
            "Check which Tally user roles can alter company features / security; look in Company Activity for any change to Edit Log setting "
            "(the TDL exports Company Activity).", True),
    Control("C3", "Operated throughout the year", "The audit trail was on from 1 April to 31 March, with no gap, including months with no transactions.",
            "Rule 11(g); para 25(i),(iii); FAQ 6",
            "Run the checker's gap test (A2); check Company Activity for on/off events; ask management for the date it was first enabled.", True),
    Control("C4", "All transactions covered", "Every voucher in the books has a 'created' entry in the Edit Log; changes and deletions are logged "
            "as separate versions, not only the latest change.", "para 11, 12; FAQ 17",
            "The checker's A1 test compares the voucher register with the Edit Log; the TDL export lists every version.", True),
    Control("C5", "Who, when, what", "The trail records the user, date-and-time and the data changed.", "paras 20, 25(v); Glossary",
            "Check the export has User, LogTime and Version columns filled for a sample.", True),
    Control("C6", "Unique user IDs", "User IDs are individual and not shared; generic IDs (Admin, Accounts) are not used for posting.",
            "para 20 (controls)", "Tally Security > Users and Passwords; the checker's D2 test lists generic IDs."),
    Control("C7", "Configuration changes authorised", "Changes to audit-trail configuration are authorised and logged.",
            "para 20, 25(iii)", "Company Activity export; management's change records."),
    Control("C8", "Access to the trail and its backups", "Access to the audit trail and backups is restricted and access logged.",
            "para 20, 24", "OS folder permissions on the data folder and backup location; Tally security."),
    Control("C9", "Database-level changes", "Direct data changes at database level are also logged (where applicable).",
            "paras 20, FAQ 15",
            "TallyPrime stores data in its own files. Confirm no direct tool (ODBC write-back, third-party utility, file replacement) "
            "is used to change data; record the answer."),
    Control("C10", "Management monitoring", "Management periodically reviews the audit trail and configuration changes, and tested completeness.",
            "para 25(iv), (vi)", "Ask for review evidence (monthly Edit Log review, sign-off). The saved Edit Log reviews and the test results in this tool can serve as evidence."),
    Control("C11", "Software changes and upgrades", "Changes/upgrades and any migration of software during or after the year were assessed for audit-trail impact.",
            "para 21; Scenario 5 of para 31", "Version history; migration note. A migration with no audit-trail controls leads to an inability-to-comment wording."),
    Control("C12", "Service organisation", "Third-party hosted or maintained software: a SOC report covering audit trail and the whole year was obtained.",
            "paras 22; FAQ 8, 19; SA 402", "Obtain the report; check period, scope and exceptions. Write 'Not applicable' for on-premise Tally."),
]
RESULTS = ["Not tested", "Effective", "Exception", "Not applicable"]

PRESERVATION_QS = [
    ("backup_daily", "Daily back-up of books and audit trail is taken", "Rule 3(5): back-up kept on a server physically located in India, daily."),
    ("backup_india", "Back-up server is physically in India", "Rule 3(5); FAQ 18, 20."),
    ("retention8", "Audit trail retained for at least 8 financial years from FY 2023-24", "s.128(5); para 19. Retention clock starts from the date the Accounts Rules apply."),
    ("retrievable", "A sample of old audit-trail records was retrieved and read without alteration", "para 26: retrievability and no alteration."),
    ("accessible", "Records remain accessible in India at all times", "Rule 3(1); FAQ 18."),
]

REP_ITEMS = [
    ("r1", "Management acknowledges responsibility for controls over identifying, maintaining and monitoring audit trails"),
    ("r2", "Management evaluated and assessed the adequacy and effectiveness of its audit-trail compliance procedures"),
    ("r3", "Management's conclusion on that assessment is stated"),
    ("r4", "All deficiencies found by management are disclosed to the auditor"),
    ("r5", "Frauds (if any) found while testing audit-trail disablement are described"),
    ("r6", "Deficiencies communicated to the audit committee in earlier engagements are resolved, or the unresolved ones are listed"),
    ("r7", "No regulator communications on non-compliance with accounting software requirements"),
    ("r8", "Management gave full access and information, including SOC reports and component auditors' reports"),
]


# --------------------------------------------------------------------------- engagement state
@dataclass
class Engagement:
    company: str = ""
    fy_end: date = date(2026, 3, 31)
    entity: str = APPLICABILITY_QS[0][2][0]
    mode: str = APPLICABILITY_QS[1][2][0]
    fs: str = "Standalone"
    software_main: str = "TallyPrime"
    inventory: list = field(default_factory=lambda: [dict(r) for r in INVENTORY_EXAMPLE])
    controls: dict = field(default_factory=dict)        # id -> {"result":..., "note":...}
    preservation: dict = field(default_factory=dict)    # key -> "Yes"/"No"/"Not yet evidenced"
    reps: dict = field(default_factory=dict)            # key -> bool
    mgmt_explanation: str = "Awaited"
    third_party_unable: bool = False
    migration: bool = False
    notes: str = ""
    auditor: str = ""                                   # the auditor / firm that signs the report (not the entity)
    confirmed: dict = field(default_factory=dict)       # question key -> True once the auditor confirmed the suggested answer
    wp_notes: dict = field(default_factory=dict)        # control id -> auditor's conclusion on its working paper


def fy_label(fy_end: date) -> str:
    return f"{fy_end.year - 1}-{str(fy_end.year)[2:]}"


def applicability(e: Engagement) -> dict:
    """Is a Rule 11(g) statement required, and which sentences?"""
    out = {"applies": True, "statement": "", "preservation_sentence": True, "reasons": []}
    if e.entity.startswith("LLP"):
        out.update(applies=False, statement="Rule 11(g) of the Companies (Audit and Auditors) Rules, 2014 does not apply to this entity "
                   "(not a company under the Companies Act, 2013).")
        out["reasons"].append("Entity is not a company.")
        return out
    if e.mode == "Entirely manually":
        out.update(applies=False, statement="The Company has not used accounting software for maintaining its books of account; "
                   "its books are maintained manually. Accordingly, reporting under Rule 11(g) is not applicable.")
        out["reasons"].append("Books wholly manual (para 16).")
        return out
    if e.fy_end <= date(2023, 3, 31):
        out.update(applies=False, statement="As the proviso to Rule 3(1) of the Companies (Accounts) Rules, 2014 is applicable for the "
                   "Company only with effect from April 1, 2023, reporting under this clause is not applicable.")
        out["reasons"].append("Year ended before the first applicable year, FY 2023-24 (para 14 and the illustration after para 30).")
        return out
    if e.fy_end.year == 2024 and e.fy_end.month <= 3:           # FY 2023-24
        out["preservation_sentence"] = False
        out["reasons"].append("First year of reporting (FY 2023-24): the preservation sentence is not reported (footnote to para 28; FAQ 24 note).")
    return out


def _result(e, cid: str) -> str:
    """A suggested answer counts only after the auditor confirms it (entries without the flag are the auditor's own)."""
    r = e.controls.get(cid, {})
    return r.get("result", "Not tested") if r.get("confirmed", True) else "Not tested"


def control_summary(e: Engagement) -> pd.DataFrame:
    rows = []
    for c in CONTROLS:
        r = e.controls.get(c.id, {})
        rows.append({"Ref": c.id, "Area": c.area, "Test": c.test, "ICAI reference": c.ref,
                     "Result": _result(e, c.id), "Status": "Confirmed" if r.get("confirmed", True) else "Suggested, not confirmed",
                     "Note": r.get("note", "")})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- map findings to the ICAI exception types
def exceptions_for_reporting(e: Engagement, res=None, reg=None, masters: pd.DataFrame | None = None) -> list[dict]:
    """Each item: nature (matching para 31 rows), text for the 'except that' clause, severity, evidence."""
    ex: list[dict] = []
    ctrl = e.controls
    bad = lambda i: _result(e, i) == "Exception"
    nt = lambda i: _result(e, i) == "Not tested"
    sw = e.software_main or "the accounting software"
    if bad("C1"):
        ex.append(dict(nature=1, clause=f"the accounting software {sw} did not have a feature of recording audit trail (edit log) facility",
                       severity="Adverse", evidence="C1"))
    if bad("C3") or bad("C2"):
        ex.append(dict(nature=2, clause=f"the audit trail feature of {sw} was not enabled / did not operate throughout the year",
                       severity="Modified", evidence="C2/C3"))
    if bad("C4"):
        ex.append(dict(nature=2, clause="the audit trail did not capture all changes to transactions recorded in the software "
                       "(only the latest change was retained or some vouchers have no trail)", severity="Modified", evidence="C4"))
    if bad("C5"):
        ex.append(dict(nature=2, clause="the audit trail did not record the user, date-and-time or the data changed for all changes",
                       severity="Modified", evidence="C5"))
    if bad("C9"):
        ex.append(dict(nature=2, clause=f"no audit trail was enabled at the database level for {sw} to log direct data changes",
                       severity="Modified", evidence="C9"))
    if bad("C12") or e.third_party_unable:
        ex.append(dict(nature=3, clause="the software is operated by a third party and, in the absence of a service-auditor's report covering "
                       "the audit trail for the whole year, we are unable to comment on whether the audit trail feature was enabled and "
                       "operated throughout the year for all relevant transactions or whether it was tampered with", severity="Inability",
                       evidence="C12"))
    if e.migration or bad("C11"):
        ex.append(dict(nature=5, clause="the Company migrated to [software] during the year / upgraded the software and is in the process of "
                       "establishing the necessary controls and documentation regarding audit trail, so we are unable to comment on the audit "
                       "trail feature of the said software", severity="Inability", evidence="C11"))
    p = e.preservation
    if p.get("backup_daily") == "No" or p.get("backup_india") == "No" or p.get("retention8") == "No" or p.get("retrievable") == "No":
        ex.append(dict(nature=4, clause="the audit trail has not been preserved by the Company as per the statutory requirements for record retention",
                       severity="Modified", evidence="Preservation"))
    # data findings
    if res is not None:
        exc = res.exceptions
        a1 = exc[exc.Test == "A1"]
        if len(a1):
            ex.append(dict(nature=2, clause=f"the audit trail did not record the creation of {len(a1)} voucher(s) found in the voucher register",
                           severity="Modified", evidence="Test A1"))
        for g in res.gaps:
            if g.get("vouchers_without_trail"):
                ex.append(dict(nature=2, clause=f"no audit-trail activity was recorded from {g['start']:%d %B %Y} to {g['end']:%d %B %Y}",
                               severity="Modified", evidence="Test A2"))
    if reg is not None and len(reg) and "R3" in list(reg[reg.Status == "Attention"].Ref):
        ex.append(dict(nature=2, clause="the monitoring record shows the audit trail could not be evidenced as operating for part of the year",
                       severity="Modified", evidence="Monitor R3"))
    return ex


def tamper_flag(res) -> str:
    """Instances that may indicate tampering are for the auditor to resolve with management (para 27; Rule 11(g))."""
    if res is None:
        return ""
    s = res.summary.set_index("Test")
    high = int(s.loc[[t for t in ["B1", "B3", "C1", "C2", "D2"] if t in s.index], "High"].sum())
    return f"{high} high-risk change(s) need explanation before the 'not tampered with' sentence is concluded." if high else ""


def readiness(e: Engagement, res=None) -> pd.DataFrame:
    """What is still open before the auditor can sign off, one line each."""
    rows = []
    nt = [c.id for c in CONTROLS if _result(e, c.id) == "Not tested"]
    rows.append(("Controls tested", "Done" if not nt else f"{len(nt)} not tested: {', '.join(nt)}", not nt))
    rows.append(("Edit Log data loaded and tested", "Done" if res is not None else "Load the Tally Edit Log in the 'Edit Log data' step", res is not None))
    pv = [q[0] for q in PRESERVATION_QS if e.preservation.get(q[0], "Not yet evidenced") == "Not yet evidenced"]
    rows.append(("Preservation evidence", "Done" if not pv else f"{len(pv)} item(s) not evidenced", not pv))
    miss = [r[0] for r in REP_ITEMS if not e.reps.get(r[0])]
    rows.append(("Management representations", "Obtained" if not miss else f"{len(miss)} item(s) outstanding (SA 580: refusal is a scope limitation)", not miss))
    rows.append(("Management explanation of flagged changes", e.mgmt_explanation, e.mgmt_explanation != "Awaited"))
    return pd.DataFrame(rows, columns=["Item", "Status", "Done"])


# --------------------------------------------------------------------------- conclusion and wording
def conclude(e: Engagement, res=None, reg=None) -> dict:
    ap = applicability(e)
    out = {"applicability": ap, "exceptions": [], "conclusion": "", "paras": {}, "caution": []}
    if not ap["applies"]:
        out["conclusion"] = "not applicable"
        out["paras"]["Rule 11(g) statement (not applicable)"] = ap["statement"]
        return out
    ex = exceptions_for_reporting(e, res, reg)
    out["exceptions"] = ex
    ready = readiness(e, res)
    sw = e.software_main or "an accounting software"
    year = f"for the financial year ended {e.fy_end:%B %d, %Y}".replace(" 0", " ")
    cons = e.fs == "Consolidated"

    if any(x["severity"] == "Adverse" for x in ex):
        out["conclusion"] = "adverse"
    elif any(x["severity"] == "Inability" for x in ex):
        out["conclusion"] = "inability to conclude"
    elif ex:
        out["conclusion"] = "modified"
    elif not ready.Done.all():
        out["conclusion"] = "pending"
    else:
        out["conclusion"] = "unmodified"
    tf = tamper_flag(res)
    if tf and e.mgmt_explanation in ("Awaited", ""):
        out["caution"].append(tf + " Management's explanation is awaited.")
        if out["conclusion"] == "unmodified":
            out["conclusion"] = "pending"
    elif tf:
        out["caution"].append(tf)
    out["caution"].append("Rule 11(g) reporting is factual and applies to every change irrespective of amount; test checks and materiality "
                          "only drive the sample, not what is reported (FAQ 9).")
    out["caution"].append("A voucher listing, an error log or a log of only the last change is not an audit trail (FAQ 17, 22, 23).")
    if e.mgmt_explanation == "Awaited":
        out["caution"].append("You cannot rely on management representation alone for this report (FAQ 16).")

    comp = "the Company, subsidiaries, associates and joint ventures/joint operations" if cons else "the Company"
    base_front = ("Based on our examination which included test checks" +
                  (" and that performed by the respective auditors of the subsidiaries, associates and joint ventures/joint operations "
                   "which are companies incorporated in India whose financial statements have been audited under the Act," if cons else "") + " ")
    core = (f"{comp} {'have' if cons else 'has'} used an accounting software for maintaining its books of account {year} which has a "
            "feature of recording audit trail (edit log) facility and the same has operated throughout the year for all relevant "
            "transactions recorded in the software")
    tamp = ("Further, during the course of our audit " + ("we and the respective auditors of the above referred subsidiaries, associates and "
            "joint ventures/joint operations " if cons else "we ") + "did not come across any instance of audit trail feature being tampered with.")
    pres = (f" Additionally, the audit trail has been preserved by {comp} as per the statutory requirements for record retention."
            if ap["preservation_sentence"] else "")
    out["paras"]["A. Rule 11(g): unmodified (para 28/29)"] = base_front + core + ". " + tamp + pres

    inab = [x for x in ex if x["severity"] == "Inability"]
    mods = [x for x in ex if x["severity"] in ("Modified", "Adverse")]
    pres_ex = [x for x in mods if x["nature"] == 4]
    mods_core = [x for x in mods if x["nature"] != 4]
    txt = base_front.replace("Based on our examination which included test checks", "Based on our examination, which included test checks", 1)
    if not cons:
        txt = txt.rstrip() + ", "
    if mods_core:
        txt += core + ", except that " + "; and ".join(x["clause"] for x in mods_core) + ". "
    else:
        txt += core + ". "
    txt += tamp
    if pres_ex:
        txt += " However, " + pres_ex[0]["clause"] + "."
    elif ap["preservation_sentence"]:
        txt += pres
    out["paras"]["B. Rule 11(g): with exception (paras 30-31)"] = txt

    if inab:
        out["paras"]["C. Rule 11(g): unable to comment (para 31, items 3 and 5; para 33)"] = (
            f"Based on our examination, the Company has used {sw} for maintaining its books of account {year}; however, "
            + "; and ".join(x["clause"] for x in inab) + ".")
    adv = [x for x in ex if x["severity"] == "Adverse"]
    if adv:
        out["paras"]["D. Rule 11(g): software has no audit-trail feature (para 27 scenario iii)"] = (
            f"Based on our examination, the Company has used {sw} for maintaining its books of account {year} which does not have a "
            "feature of recording audit trail (edit log) facility. Accordingly, the audit trail could not have operated throughout the "
            "year for all transactions, and we are unable to report that it was not tampered with or has been preserved.")

    # FAQ 24: a modified Rule 11(g) comment flows to s.143(3)(b) and (h)
    if ex:
        out["paras"]["E. Section 143(3)(b): proper books of account (FAQ 24)"] = (
            "In our opinion, proper books of account as required by law have been kept by the Company so far as it appears from our "
            "examination of those books [and proper returns adequate for the purposes of our audit have been received from the branches "
            "not visited by us] except for the matters stated in the paragraph [..] below on reporting under Rule 11(g).")
        out["paras"]["F. Section 143(3)(h): qualification relating to maintenance of accounts (FAQ 24)"] = (
            "The [qualification / adverse remark / reservation] relating to the maintenance of accounts and other matters connected "
            "therewith are as stated in the paragraph [..] above on reporting under Section 143(3)(b) and paragraph [..] below on "
            "reporting under Rule 11(g).")
        out["paras"]["G. Basis for modified opinion on the financial statements (consider; SA 705)"] = (
            "Consider whether the audit-trail exception affects your audit evidence and your opinion on the financial statements. "
            "The Implementation Guide says to evaluate the implication on Other Legal and Regulatory Requirements and on the main audit "
            "opinion under SA 700 (para 31 closing note). Where fraud could not be established or ruled out because logs were unavailable, "
            "assess likelihood and magnitude and link to s.143(12) / CARO 2020 clause (x) (para 32).")
        out["paras"]["H. s.143(3)(i) / IFCoFR read-across (para 33)"] = (
            "Mere non-availability of audit trail does not necessarily imply a material weakness in IFCoFR. If management cannot rely on "
            "the automated controls and IFCoFR is modified, the Rule 11(g) wording may read: 'The Company has used an accounting software "
            "for maintaining its books of account; however, for the reasons stated in [refer the reporting on IFCoFR], management is unable "
            "to rely on automated controls related to financial reporting in the accounting software and consequently we are unable to "
            "comment on audit trail requirements of the said software as envisaged under Rule 11(g).'")
    out["paras"]["_suggested"] = {"unmodified": "A. Rule 11(g): unmodified (para 28/29)", "pending": "A. Rule 11(g): unmodified (para 28/29)",
                                  "modified": "B. Rule 11(g): with exception (paras 30-31)",
                                  "inability to conclude": "C. Rule 11(g): unable to comment (para 31, items 3 and 5; para 33)",
                                  "adverse": "D. Rule 11(g): software has no audit-trail feature (para 27 scenario iii)"}[out["conclusion"]]
    return out


# --------------------------------------------------------------------------- documents
def rep_letter_docx(e: Engagement) -> bytes:
    from docx import Document
    d = Document()
    d.add_paragraph(f"({e.company or 'Entity'} letterhead)")
    d.add_paragraph(f"To: {e.auditor or '[Name of the auditor / firm]'}, Statutory Auditors of {e.company or 'the Company'}\t\t\tDate: ____________")
    d.add_paragraph(f"This representation letter is provided in conjunction with your audit of the {e.fs.lower()} financial statements of "
                    f"{e.company or 'the Company'} for the year ended {e.fy_end.day} {e.fy_end:%B %Y}, for the purpose of reporting on whether the accounting "
                    "software used by the Company for maintaining its books of account has a feature of recording audit trail of each and every "
                    "transaction, creating an edit log of each change made in the books of account along with the date when such changes were "
                    "made and ensuring that the audit trail cannot be disabled (Rule 3(1) proviso, Companies (Accounts) Rules, 2014; "
                    "Rule 11(g), Companies (Audit and Auditors) Rules, 2014).")
    d.add_paragraph("We confirm that, to the best of our knowledge and belief, having made such inquiries as we considered necessary:")
    items = [
        "We are responsible for establishing and maintaining adequate and effective controls [criteria] in respect of use of accounting software "
        "that has the features required by the Accounts Rules.",
        "We have evaluated and assessed the adequacy and effectiveness of the Company's accounting software in recording audit trail of each and "
        "every transaction.",
        "We have not used the procedures performed by you during the audit as part of the basis for our assessment.",
        "Based on our assessment, we conclude that the Company uses accounting software for maintaining its books of account which has a feature "
        "of recording audit trail of each and every transaction, creating an edit log of each change made in the books of account along with the "
        "date of change, that the audit trail cannot be disabled, and that it has been preserved as per the statutory requirements for record "
        "retention, except for: (a) [deficiencies] (b) [impact].",
        "We have disclosed to you all deficiencies identified in our evaluation, including those we believe to be significant deficiencies or "
        "material weaknesses in internal financial controls.",
        "There were no instances of fraud resulting in a material misstatement, and no fraud involving senior management or employees with a "
        "significant role in internal financial controls, [or: the following instances were noted: ...].",
        "Deficiencies communicated to the Company and those charged with governance in the previous engagement have been remediated, except for: "
        "[...] (not applicable in the first year).",
        "There have been no communications from regulatory agencies concerning non-compliance with or deficiencies in accounting software.",
        "We have provided you with all information, records (including SOC reports) and documentation relevant to your assessment, additional "
        "information requested, unrestricted access to people in the entity, and the reports of component auditors where applicable.",
        "There are no changes in the accounting software from the balance sheet date to the date of this letter, except: [...].",
    ]
    for i, t in enumerate(items, 1):
        d.add_paragraph(f"{i}. {t}")
    d.add_paragraph("\nFor and on behalf of the Company\n\n______________________\n[Name, designation]  (Managing Director / CFO)")
    d.add_paragraph("Source: ICAI Implementation Guide on Reporting on Audit Trail under Rule 11(g) (Revised 2024), Appendix II. Adapt to your "
                    "facts; SA 580 covers who signs and the period covered.").italic = True
    buf = io.BytesIO(); d.save(buf); return buf.getvalue()


def working_paper_docx(e: Engagement, concl: dict, res=None) -> bytes:
    from docx import Document
    d = Document()
    d.add_heading(f"Rule 11(g) audit-trail working paper: {e.company or '[Company]'}", 1)
    d.add_paragraph(f"Year ended {e.fy_end:%d %B %Y} | {e.fs} | Software: {e.software_main}" + (f" | Auditor: {e.auditor}" if e.auditor else ""))
    d.add_paragraph(DISCLAIMER).italic = True
    d.add_heading("1. Applicability", 2)
    for r in concl["applicability"]["reasons"] or ["Applicable."]:
        d.add_paragraph(r, style="List Bullet")
    d.add_heading("2. Software inventory (Appendix I)", 2)
    inv = pd.DataFrame(e.inventory)
    if len(inv):
        t = d.add_table(rows=1, cols=len(inv.columns)); t.style = "Table Grid"
        for i, c in enumerate(inv.columns): t.rows[0].cells[i].text = str(c)
        for _, r in inv.iterrows():
            cells = t.add_row().cells
            for i, c in enumerate(inv.columns): cells[i].text = str(r[c])
    d.add_heading("3. Controls and configuration tests", 2)
    cs = control_summary(e)
    t = d.add_table(rows=1, cols=5); t.style = "Table Grid"
    for i, c in enumerate(["Ref", "Test", "ICAI reference", "Result", "Note"]): t.rows[0].cells[i].text = c
    for _, r in cs.iterrows():
        cells = t.add_row().cells
        for i, c in enumerate(["Ref", "Test", "ICAI reference", "Result", "Note"]): cells[i].text = str(r[c])
    d.add_heading("4. Edit Log data tests", 2)
    if res is not None:
        s = res.summary
        t = d.add_table(rows=1, cols=len(s.columns)); t.style = "Table Grid"
        for i, c in enumerate(s.columns): t.rows[0].cells[i].text = str(c)
        for _, r in s.iterrows():
            cells = t.add_row().cells
            for i, c in enumerate(s.columns): cells[i].text = str(r[c])
    else:
        d.add_paragraph("Edit Log data not loaded.")
    d.add_paragraph("Voucher-level detail (every version, user, date-time, old and new values, deleted vouchers, master changes) is in "
                    "Annexure A: voucher_editlog_annexure.xlsx. Keep it and the original Tally export with this working paper.")
    d.add_heading("5. Preservation", 2)
    for k, q, ref in PRESERVATION_QS:
        d.add_paragraph(f"{q}: {e.preservation.get(k, 'Not yet evidenced')}  [{ref}]", style="List Bullet")
    d.add_heading("6. Management representations", 2)
    for k, q in REP_ITEMS:
        d.add_paragraph(f"[{'x' if e.reps.get(k) else ' '}] {q}", style="List Bullet")
    d.add_heading("7. Conclusion", 2)
    d.add_paragraph(f"Suggested: {concl['conclusion'].upper()}.  Management explanation: {e.mgmt_explanation}.")
    for x in concl["exceptions"]:
        d.add_paragraph(f"{x['severity']} ({x['evidence']}): {x['clause']}", style="List Bullet")
    for c in concl["caution"]:
        d.add_paragraph("Caution: " + c, style="List Bullet")
    d.add_heading("8. Draft wording", 2)
    for k, v in concl["paras"].items():
        if k.startswith("_"): continue
        d.add_heading(k + ("  [suggested]" if k == concl["paras"].get("_suggested") else ""), 3)
        d.add_paragraph(str(v))
    if e.notes.strip():
        d.add_heading("Auditor's notes", 2); d.add_paragraph(e.notes)
    d.add_paragraph("Prepared with EditLog Auditor. SA 230: retain with the audit file; sign and date.").italic = True
    buf = io.BytesIO(); d.save(buf); return buf.getvalue()


# --------------------------------------------------------------------------- voucher-level annexure (working paper)
def field_level_sample_frame(vr: pd.DataFrame) -> pd.DataFrame:
    """Risk-ranked list of vouchers whose field-level changes the auditor should read on Tally's own
    'Differences Between Edit Log Versions' screen (ICAI Guide para 25(v), test basis). Blank columns are for the working paper."""
    if vr is None or not len(vr):
        return pd.DataFrame()
    g = vr.groupby("MasterID", sort=False)
    f = g.agg(VoucherType=("VoucherType", "last"), VoucherNo=("VoucherNo", "last"), VoucherDate=("VoucherDate", "last"),
              Party=("Party", "last"), Amount=("Amount", "last"), Versions=("Version", "max"),
              CreatedBy=("User", "first"), CreatedAt=("LogTime", "min"), LastAt=("LogTime", "max"),
              Users=("User", lambda x: ", ".join(sorted(set(map(str, x)))))).reset_index()
    f["Amount"] = pd.to_numeric(f["Amount"].astype(str).str.replace(",", ""), errors="coerce").abs()
    first = vr.sort_values("Version").groupby("MasterID").User.first()
    last = vr.sort_values("Version").groupby("MasterID").User.last()
    dele = g["Action"].apply(lambda x: x.astype(str).str.lower().str.contains("delet|cancel").any())
    f["CreatedBy"] = f.MasterID.map(first)
    f["Deleted"] = f.MasterID.map(dele)
    f["Other user"] = (f.MasterID.map(first) != f.MasterID.map(last)) & (f.Versions > 1)
    f["Days to last change"] = (f.LastAt - f.CreatedAt).dt.days
    big = f.Amount.quantile(0.9) if f.Amount.notna().any() else float("inf")
    f["Score"] = (f.Deleted * 5 + (f.Versions >= 3) * 3 + f["Other user"] * 2 + (f["Days to last change"] > 30) * 2
                  + ((f.Amount >= big) & (f.Versions > 1)) * 2)
    def _why(r):
        return ", ".join(t for t, c in (("deleted", r["Deleted"]), ("3+ versions", r["Versions"] >= 3),
                                        ("changed by a different user", r["Other user"]),
                                        ("changed >30 days after creation", (r["Days to last change"] or 0) > 30),
                                        ("high value", (r["Amount"] >= big) and r["Versions"] > 1)) if c)
    f["Why selected"] = f.apply(_why, axis=1)
    f = f[f.Versions > 1].sort_values(["Score", "Amount"], ascending=False)
    for c in ("Versions compared (e.g. Ver 1 vs 2)", "Field changed", "Old value", "New value", "Business reason / approval seen",
              "Authorised? (Y/N)", "Agreed to Tally screen (Y/N)", "Screenshot / file ref", "Auditor initials"):
        f[c] = ""
    return f.drop(columns=["Other user"]).reset_index(drop=True)


def annexure_xlsx(raw_tdl: pd.DataFrame | None, log: pd.DataFrame, masters: pd.DataFrame | None, reg: pd.DataFrame | None,
                  company: str = "", period: str = "") -> bytes:
    """Voucher-level Edit Log evidence for the audit file (SA 230; ICAI para 25(v): user, date-time, what changed, on a test basis
    or in full). Sheets: Read-me, Version register (every version), Field changes (old -> new), Voucher summary, Deleted vouchers,
    Master and company changes, Reconciliation to the voucher register."""
    import editlog_import as EI
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        notes = pd.DataFrame({"Item": ["Company", "Period", "Prepared with", "Purpose", "Sheets", "Limit"],
            "Detail": [company, period, "EditLog Auditor - data from the Audit Trail TDL (Tally Edit Log, every version)",
                       "Voucher-level audit-trail evidence for Rule 11(g) working papers (ICAI Implementation Guide paras 25(v), 26, 35; SA 230)",
                       "Version register | Field changes (or Field-level sample when the export carries no old/new values) | Voucher summary | Deleted vouchers | Master & company changes | Reconciliation",
                       "Extract only. Agree totals to Tally's own Edit Log screen on a sample; keep the original CSV with the file."]})
        notes.to_excel(xw, sheet_name="Read-me", index=False)
        vr = None
        if raw_tdl is not None and len(raw_tdl):
            d = EI._norm(raw_tdl).copy()
            if "Source" in d and (d["Source"].astype(str).str.strip() != "").any():
                d = d[d["Source"] == "Voucher"]
            d["LogTime"] = EI._dt(d["LogTime"]); d["VoucherDate"] = EI._dt(d["VoucherDate"])
            d["Version"] = pd.to_numeric(d["Version"], errors="coerce")
            vr = d.dropna(subset=["LogTime"]).sort_values(["MasterID", "Version", "LogTime"])
            cols = [c for c in ["MasterID", "VoucherType", "VoucherNo", "VoucherDate", "Party", "Amount", "Version", "Action",
                                "Activity", "User", "LogTime", "Narration"] if c in vr]
            vr[cols].to_excel(xw, sheet_name="Version register", index=False)
            fc = EI.convert(raw_tdl)
            fc = fc[fc.Field != ""] if len(fc) else fc
            fc.to_excel(xw, sheet_name="Field changes", index=False)
            g = vr.groupby("MasterID", sort=False)
            summ = g.agg(VoucherType=("VoucherType", "last"), VoucherNo=("VoucherNo", "last"), VoucherDate=("VoucherDate", "last"),
                         Versions=("Version", "max"), FirstLogged=("LogTime", "min"), LastLogged=("LogTime", "max"),
                         CreatedBy=("User", "first"), LastChangedBy=("User", "last"),
                         UsersInvolved=("User", lambda x: ", ".join(sorted(set(map(str, x)))))).reset_index()
            act = g["Action"].apply(lambda x: x.astype(str).str.lower().str.contains("delet|cancel").any())
            summ["Deleted/Cancelled"] = summ.MasterID.map(act).map({True: "Yes", False: ""})
            summ["Alterations"] = (summ.Versions.fillna(1) - 1).clip(lower=0).astype(int)
            summ["Changed by someone other than creator"] = (summ.CreatedBy.astype(str) != summ.LastChangedBy.astype(str)) & (summ.Alterations > 0)
            summ.sort_values(["Alterations"], ascending=False).to_excel(xw, sheet_name="Voucher summary", index=False)
            summ[summ["Deleted/Cancelled"] == "Yes"].to_excel(xw, sheet_name="Deleted vouchers", index=False)
            if len(fc) == 0:
                fs = field_level_sample_frame(vr)
                fs.to_excel(xw, sheet_name="Field-level sample", index=False)
        else:
            log.to_excel(xw, sheet_name="Log entries", index=False)
        if masters is not None and len(masters):
            masters.to_excel(xw, sheet_name="Master & company changes", index=False)
        rec = []
        if reg is not None and len(reg):
            rec.append(("Vouchers in the voucher register", len(reg)))
        if vr is not None:
            rec.append(("Vouchers with at least one Edit Log version", vr.MasterID.nunique()))
            rec.append(("Total voucher versions logged", len(vr)))
            rec.append(("Versions after the first (alterations / deletions)", int((vr.Version > 1).sum())))
        if masters is not None:
            rec.append(("Master-data changes", int((masters.Object != "Company").sum())))
            rec.append(("Company activities", int((masters.Object == "Company").sum())))
        pd.DataFrame(rec, columns=["Reconciliation line", "Count"]).to_excel(xw, sheet_name="Reconciliation", index=False)
        for ws in xw.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(48, max(10, max(len(str(c.value or "")) for c in col[:60]) + 2))
    return out.getvalue()
