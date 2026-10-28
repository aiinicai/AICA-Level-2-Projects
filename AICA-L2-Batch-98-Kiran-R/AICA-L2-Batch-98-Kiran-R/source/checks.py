"""EditLog Auditor: tests an accounting-software edit log against the voucher register.

Context: Rule 3(1) proviso of the Companies (Accounts) Rules, 2014 requires accounting software with an
audit trail (edit log) that cannot be disabled, and Rule 11(g) of the Companies (Audit and Auditors) Rules,
2014 makes the auditor report on it. The ICAI Implementation Guide on Reporting on Audit Trail lists what
the auditor tests: operated throughout the year, covered all transactions, not tampered with, preserved.

These tests find *indicators*. They support the auditor's judgement; they do not replace ITGC testing,
configuration review or enquiry of management.
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd

LOG_COLS = ["LogTime", "User", "Action", "VoucherType", "VoucherNo", "VoucherDate", "Field", "OldValue",
            "NewValue", "Amount"]
REG_COLS = ["VoucherType", "VoucherNo", "VoucherDate", "Party", "Amount"]
GENERIC_TOKENS = ("admin", "support", "tally", "guest", "test", "default")

TESTS = {
    "A1": "Voucher in the register with no 'Created' entry in the audit trail",
    "A2": "Run of working days with no audit-trail activity (possible logging gap)",
    "B1": "Changes recorded after the books were finalised",
    "B2": "Back-dated entries (created long after the voucher date)",
    "B3": "Deletions and cancellations",
    "C1": "Material changes to voucher amounts",
    "C2": "Voucher date moved (cut-off risk)",
    "C3": "Same voucher altered repeatedly",
    "D1": "Changes at night or on Sunday",
    "D2": "Alterations or deletions by generic / shared user IDs",
}
POINTS = {"High": 40, "Medium": 20, "Low": 5}


def inr(x) -> str:
    x = int(round(float(x)))
    s = str(abs(x))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if x < 0 else "") + "₹" + s


def _num(x):
    try:
        return float(str(x).replace(",", "").replace("₹", "").strip())
    except (ValueError, TypeError):
        return None


def _date(x):
    t = pd.to_datetime(x, errors="coerce")
    return None if pd.isna(t) else t.date()


# --------------------------------------------------------------------------- loading
def norm_action(a) -> str:
    s = str(a).lower()
    if "creat" in s or s in ("new", "add", "insert", "entered"):
        return "Created"
    if "delet" in s or "cancel" in s:
        return "Deleted"
    return "Altered"


def prepare_log(df: pd.DataFrame) -> pd.DataFrame:
    miss = [c for c in LOG_COLS if c not in df.columns]
    if miss:
        raise ValueError(f"Edit log is missing columns: {', '.join(miss)}")
    d = df[LOG_COLS].copy()
    d["LogTime"] = pd.to_datetime(d["LogTime"], errors="coerce")
    d["VoucherDate"] = pd.to_datetime(d["VoucherDate"], errors="coerce")
    d["Action"] = d["Action"].map(norm_action)
    d["Amount"] = pd.to_numeric(d["Amount"].astype(str).str.replace(",", ""), errors="coerce").abs()
    for c in ("User", "VoucherType", "VoucherNo", "Field"):
        d[c] = d[c].fillna("").astype(str).str.strip()
    d = d.dropna(subset=["LogTime"]).sort_values("LogTime", kind="stable").reset_index(drop=True)
    d["Key"] = d["VoucherType"] + "|" + d["VoucherNo"]
    return d


def prepare_register(df: pd.DataFrame) -> pd.DataFrame:
    miss = [c for c in REG_COLS if c not in df.columns]
    if miss:
        raise ValueError(f"Voucher register is missing columns: {', '.join(miss)}")
    d = df[REG_COLS].copy()
    d["VoucherDate"] = pd.to_datetime(d["VoucherDate"], errors="coerce")
    d["Amount"] = pd.to_numeric(d["Amount"].astype(str).str.replace(",", ""), errors="coerce").abs()
    for c in ("VoucherType", "VoucherNo", "Party"):
        d[c] = d[c].fillna("").astype(str).str.strip()
    d = d.dropna(subset=["VoucherDate"]).reset_index(drop=True)
    d["Key"] = d["VoucherType"] + "|" + d["VoucherNo"]
    return d


# --------------------------------------------------------------------------- tests
@dataclass
class Params:
    fy_start: date = date(2025, 4, 1)
    fy_end: date = date(2026, 3, 31)
    finalised_on: date = date(2026, 5, 31)
    backdate_days: int = 30
    big_amount: float = 500_000
    amt_pct: float = 0.20
    amt_min: float = 100_000
    gap_working_days: int = 4
    night_from: int = 21
    night_to: int = 6
    repeat_n: int = 4
    generic: tuple = GENERIC_TOKENS


@dataclass
class Result:
    params: Params
    reg: pd.DataFrame
    log: pd.DataFrame
    exceptions: pd.DataFrame = None
    summary: pd.DataFrame = None
    priority: pd.DataFrame = None
    users: pd.DataFrame = None
    gaps: list = field(default_factory=list)


def run_checks(reg: pd.DataFrame, log: pd.DataFrame, p: Params) -> Result:
    res = Result(p, reg, log)
    rows: list[dict] = []

    def add(test, sev, r=None, detail="", key=None, vtype="", vno="", vdate=None, user="", ts=None, amount=None):
        if r is not None:
            vtype, vno, vdate, user, ts = r.VoucherType, r.VoucherNo, r.VoucherDate, r.User, r.LogTime
            amount = r.Amount if amount is None else amount
        rows.append({"Test": test, "Severity": sev, "VoucherType": vtype, "VoucherNo": vno,
                     "VoucherDate": None if vdate is None or pd.isna(vdate) else pd.Timestamp(vdate).date(),
                     "User": user, "LogTime": ts, "Amount": amount, "Detail": detail})

    created = set(log.loc[log.Action == "Created", "Key"])
    fy_end = pd.Timestamp(p.fy_end)

    # A1 completeness: register vs log
    for r in reg.itertuples():
        if r.Key not in created:
            add("A1", "High" if r.Amount >= p.big_amount else "Medium", vtype=r.VoucherType, vno=r.VoucherNo,
                vdate=r.VoucherDate, amount=r.Amount,
                detail="Present in the register but the audit trail shows no creation entry")

    # A2 logging gaps
    active = set(log.LogTime.dt.date)
    run: list[date] = []
    runs: list[list[date]] = []
    d = p.fy_start
    while d <= p.fy_end:
        if d.weekday() < 6:                       # Mon–Sat are working days
            if d in active:
                if len(run) >= p.gap_working_days:
                    runs.append(run)
                run = []
            else:
                run.append(d)
        d += timedelta(days=1)
    if len(run) >= p.gap_working_days:
        runs.append(run)
    for rn in runs:
        s, e = rn[0], rn[-1]
        inside = reg[(reg.VoucherDate.dt.date >= s) & (reg.VoucherDate.dt.date <= e) & ~reg.Key.isin(created)]
        res.gaps.append({"start": s, "end": e, "working_days": len(rn), "vouchers_without_trail": len(inside),
                         "value": float(inside.Amount.sum())})
        add("A2", "High" if len(inside) else "Low", vdate=s, ts=pd.Timestamp(s), amount=float(inside.Amount.sum()),
            detail=f"No audit-trail activity for {len(rn)} working days ({s} to {e}); "
                   f"{len(inside)} register voucher(s) dated in this window have no trail"
                   + ("" if len(inside) else " (check the holiday calendar)"))

    # per-event tests
    for r in log.itertuples():
        after_fy = r.LogTime.normalize() > fy_end
        after_final = r.LogTime.date() > p.finalised_on
        amt = 0 if pd.isna(r.Amount) else r.Amount

        if after_final:
            add("B1", "High", r, f"{r.Action} on {r.LogTime:%d-%b-%Y %H:%M}, after books were finalised on "
                                 f"{p.finalised_on:%d-%b-%Y}" + (f" ({r.Field})" if r.Field else ""))

        if r.Action == "Created" and pd.notna(r.VoucherDate):
            lag = (r.LogTime.normalize() - r.VoucherDate).days
            if lag > p.backdate_days:
                big = after_fy and r.VoucherDate <= fy_end and amt >= p.big_amount
                add("B2", "High" if big else "Medium", r,
                    f"Voucher dated {r.VoucherDate:%d-%b-%Y} was created {lag} days later"
                    + (" and after year end" if after_fy else ""))

        if r.Action == "Deleted":
            sev = "High" if (amt >= p.big_amount or after_fy) else "Medium" if amt >= 100_000 else "Low"
            add("B3", sev, r, f"Voucher deleted on {r.LogTime:%d-%b-%Y %H:%M}")

        if r.Action == "Altered" and r.Field.lower() == "amount":
            o, n = _num(r.OldValue), _num(r.NewValue)
            if o and n is not None and o > 0:
                delta = abs(n - o)
                if delta / o >= p.amt_pct and delta >= p.amt_min:
                    sev = "High" if (delta >= p.big_amount or after_fy) else "Medium"
                    add("C1", sev, r, f"Amount changed from {inr(o)} to {inr(n)} ({(n - o) / o:+.0%})")

        if r.Action == "Altered" and r.Field.lower() == "date":
            o, n = _date(r.OldValue), _date(r.NewValue)
            if o and n:
                crosses = (o <= p.fy_end) != (n <= p.fy_end)
                shift = abs((n - o).days)
                if crosses:
                    add("C2", "High", r, f"Voucher date moved from {o:%d-%b-%Y} to {n:%d-%b-%Y}, "
                                         f"across the financial year end")
                elif shift >= 10:
                    add("C2", "Medium", r, f"Voucher date moved by {shift} days ({o:%d-%b-%Y} to {n:%d-%b-%Y})")

        night = r.LogTime.hour >= p.night_from or r.LogTime.hour < p.night_to
        sunday = r.LogTime.weekday() == 6
        if night or sunday:
            add("D1", "Low" if r.Action == "Created" else "Medium", r,
                f"{r.Action} at {r.LogTime:%a %d-%b-%Y %H:%M}" + (" (night)" if night else " (Sunday)"))

        if r.Action in ("Altered", "Deleted") and any(t in r.User.lower() for t in p.generic):
            add("D2", "High" if after_fy else "Medium", r, f"{r.Action} by generic/shared ID '{r.User}'")

    # C3 repeated alterations
    alt = log[log.Action == "Altered"]
    for key, g in alt.groupby("Key"):
        if len(g) >= p.repeat_n:
            last = g.iloc[-1]
            add("C3", "Medium", vtype=last.VoucherType, vno=last.VoucherNo, vdate=last.VoucherDate,
                user=", ".join(sorted(set(g.User))), ts=last.LogTime, amount=last.Amount,
                detail=f"Altered {len(g)} times between {g.LogTime.min():%d-%b %H:%M} and {g.LogTime.max():%d-%b %H:%M}")

    ex = pd.DataFrame(rows, columns=["Test", "Severity", "VoucherType", "VoucherNo", "VoucherDate", "User",
                                     "LogTime", "Amount", "Detail"])
    order = {"High": 0, "Medium": 1, "Low": 2}
    ex = ex.sort_values(["Severity", "Test", "LogTime"], key=lambda s: s.map(order) if s.name == "Severity" else s,
                        kind="stable").reset_index(drop=True)
    res.exceptions = ex

    # summary per test
    srows = []
    for t, desc in TESTS.items():
        sub = ex[ex.Test == t]
        srows.append({"Test": t, "What it checks": desc, "Exceptions": len(sub),
                      "High": int((sub.Severity == "High").sum()), "Medium": int((sub.Severity == "Medium").sum()),
                      "Low": int((sub.Severity == "Low").sum()),
                      "Result": "Exceptions" if len(sub) else "No exceptions"})
    res.summary = pd.DataFrame(srows)

    # priority vouchers: where several tests point at the same voucher, test it first
    v = ex[ex.VoucherNo != ""].copy()
    v["Points"] = v.Severity.map(POINTS)
    if len(v):
        pr = v.groupby(["VoucherType", "VoucherNo"]).agg(
            Score=("Points", "sum"), Tests=("Test", lambda s: ", ".join(sorted(set(s)))),
            Amount=("Amount", "max"), Users=("User", lambda s: ", ".join(sorted({x for x in s if x}))),
            Exceptions=("Test", "count")).reset_index()
        pr["Level"] = pr.Score.map(lambda s: "High" if s >= 60 else "Medium" if s >= 30 else "Low")
        res.priority = pr.sort_values(["Score", "Amount"], ascending=False).reset_index(drop=True)
    else:
        res.priority = pd.DataFrame(columns=["VoucherType", "VoucherNo", "Score", "Tests", "Amount", "Users",
                                             "Exceptions", "Level"])

    # activity by user
    u = log.copy()
    u["Night/Sunday"] = (u.LogTime.dt.hour >= p.night_from) | (u.LogTime.dt.hour < p.night_to) | (u.LogTime.dt.weekday == 6)
    u["After year end"] = u.LogTime.dt.normalize() > fy_end
    res.users = (u.groupby("User").agg(Events=("Action", "count"),
                                       Created=("Action", lambda s: int((s == "Created").sum())),
                                       Altered=("Action", lambda s: int((s == "Altered").sum())),
                                       Deleted=("Action", lambda s: int((s == "Deleted").sum())),
                                       Night_Sunday=("Night/Sunday", "sum"), After_year_end=("After year end", "sum"))
                 .reset_index().sort_values("Events", ascending=False))
    return res


# --------------------------------------------------------------------------- conclusion + wording
def indicator(res: Result) -> tuple[str, str]:
    s = res.summary.set_index("Test")
    completeness = s.loc["A1", "Exceptions"] > 0 or s.loc["A2", "High"] > 0
    control = (s.loc[["B1", "B3", "C1", "C2", "D2"], "High"].sum()) > 0
    if completeness:
        return ("Red", "The trail appears not to have recorded all transactions or not to have operated throughout "
                       "the year. Consider a modified Rule 11(g) comment after confirming the cause with management "
                       "and IT.")
    if control:
        return ("Amber", "The trail recorded the transactions, but high-risk changes need explanation. Obtain management's "
                         "rationale and evidence before concluding on tampering and on the Rule 11(g) wording.")
    return ("Green", "No exceptions on these tests. This does not by itself support the unmodified wording; "
                      "ITGC, configuration and preservation evidence are still needed.")


def rule11g_paragraphs(res: Result) -> dict:
    s = res.summary.set_index("Test")
    a1 = res.exceptions[res.exceptions.Test == "A1"]
    base = ("Based on our examination which included test checks, the Company has used accounting software for "
            "maintaining its books of account which has a feature of recording audit trail (edit log) facility "
            "and the same has operated throughout the year for all relevant transactions recorded in the software")
    tail = ("Further, during the course of our audit we did not come across any instance of audit trail feature "
            "being tampered with. Additionally, the audit trail has been preserved by the Company as per the "
            "statutory requirements for record retention.")
    parts = []
    if len(a1):
        parts.append(f"the audit trail did not record the creation of {len(a1)} voucher(s) aggregating "
                     f"{inr(a1.Amount.sum())} in the register")
    for g in res.gaps:
        if g["vouchers_without_trail"]:
            parts.append(f"no audit-trail activity was recorded from {g['start']:%d %B %Y} to {g['end']:%d %B %Y}")
    if parts:
        modified = f"{base}, except that " + "; and ".join(parts) + ". [Describe management's explanation and the " \
                   "effect, and complete per the ICAI Implementation Guide.] " + \
                   "[Reconsider the 'not tampered' sentence in the light of the matters in the findings.] " + tail
    else:
        modified = base + ". [No completeness exceptions were found by these tests.] " + tail
    return {"unmodified": base + ". " + tail, "modified": modified}


# --------------------------------------------------------------------------- memo
def _facts(res: Result) -> dict:
    ex = res.exceptions
    top = {}
    for t in TESTS:
        sub = ex[ex.Test == t].head(6)
        top[t] = [{"voucher": f"{r.VoucherType} {r.VoucherNo}".strip(), "amount": inr(r.Amount) if pd.notna(r.Amount) else "",
                   "user": r.User, "severity": r.Severity, "detail": r.Detail} for r in sub.itertuples()]
    return {"period": f"{res.params.fy_start} to {res.params.fy_end}", "finalised_on": str(res.params.finalised_on),
            "events": len(res.log), "vouchers": len(res.reg),
            "summary": res.summary[["Test", "What it checks", "Exceptions", "High"]].to_dict("records"),
            "examples": top, "indicator": indicator(res)[1]}


def memo_offline(res: Result) -> str:
    f = _facts(res)
    ex, p = res.exceptions, res.params
    L = ["DRAFT – AUDIT TRAIL (EDIT LOG) REVIEW: OBSERVATIONS FOR DISCUSSION WITH MANAGEMENT",
         f"Period: {p.fy_start:%d-%b-%Y} to {p.fy_end:%d-%b-%Y}   |   Books finalised: {p.finalised_on:%d-%b-%Y}",
         f"Population: {f['events']} audit-trail events; {f['vouchers']} vouchers in the register.",
         f"Indicator: {indicator(res)[0]} – {indicator(res)[1]}", ""]
    n = 1
    def sect(title, test, lead, ask):
        nonlocal n
        sub = ex[ex.Test == test]
        if not len(sub):
            return
        L.append(f"{n}. {title} ({len(sub)} exception{'s' if len(sub) > 1 else ''})")
        for r in sub.head(5).itertuples():
            amt = f" {inr(r.Amount)}" if pd.notna(r.Amount) and r.Amount else ""
            L.append(f"   • {r.VoucherType} {r.VoucherNo}{amt}: {r.Detail}".replace("  ", " "))
        if len(sub) > 5:
            L.append(f"   • … and {len(sub) - 5} more (see the Exceptions sheet)")
        L.append(f"   Observation: {lead}")
        L.append(f"   Ask management: {ask}")
        L.append("")
        n += 1

    sect("Vouchers missing from the audit trail", "A1",
         "these vouchers exist in the books but the audit trail has no creation record, which is inconsistent with "
         "the trail having captured every transaction.",
         "how and by whom these were recorded; whether data was imported or changed outside the application; "
         "evidence from the software vendor or database logs.")
    sect("Silent periods in the audit trail", "A2",
         "no activity was logged on consecutive working days while vouchers were dated in the same period.",
         "whether the audit trail feature was switched off, the module changed, or data restored from backup.")
    sect("Changes after the books were finalised", "B1",
         "entries were created, altered or deleted after the finalisation date, outside the normal closing process.",
         "who authorised each change, why it was made after finalisation, and whether the financial statements "
         "were updated for it.")
    sect("Back-dated entries", "B2",
         "vouchers dated at year end were entered several weeks later, which bears on revenue and expense cut-off.",
         "supporting documents and approvals for each entry.")
    sect("Deletions", "B3", "deleted vouchers remove transactions from the books and need a reason on file.",
         "reason and approval for each deletion above the low-value threshold; whether the underlying transaction was reversed.")
    sect("Material amount changes", "C1", "amounts were changed materially after posting.",
         "the document supporting the revised amount and who approved it.")
    sect("Voucher dates moved across year end", "C2",
         "moving a voucher date across 31 March shifts income or expense between years.",
         "the commercial reason and delivery/receipt evidence for the revised date.")
    sect("Repeated alterations", "C3", "the same voucher was changed several times in a short period.",
         "the reason and the final supporting document.")
    sect("Night and Sunday activity", "D1", "changes outside normal working hours are unusual for this entity.",
         "who was working then and why.")
    sect("Generic or shared user IDs", "D2",
         "actions under shared IDs cannot be traced to an individual, which weakens the audit trail.",
         "who holds the credentials and whether the ID can be retired.")
    para = rule11g_paragraphs(res)
    L += ["DRAFT RULE 11(g) WORDING (for the auditor's judgement; align with the ICAI Implementation Guide)",
          "Unmodified: " + para["unmodified"], "", "If exceptions are confirmed: " + para["modified"], "",
          "Limitations: these tests work on the extracts provided. They do not test software configuration, database-level "
          "access, backups or preservation, which also bear on Rule 11(g). A flag is a reason to ask, not a conclusion."]
    return "\n".join(L)


def memo_ai(res: Result, api_key: str | None = None, model: str = "claude-sonnet-5-5") -> tuple[str, str]:
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return memo_offline(res), "offline template (no API key set)"
    try:
        import anthropic
        c = anthropic.Anthropic(api_key=key)
        prompt = ("You are assisting a chartered accountant reviewing the audit trail (edit log) of accounting "
                  "software under Rule 11(g) of the Companies (Audit and Auditors) Rules, 2014. From the test "
                  "results below write: (1) a three-line summary, (2) a numbered list of observations with a "
                  "question to management for each, (3) draft Rule 11(g) wording, unmodified and modified, "
                  "following the structure of the ICAI Implementation Guide, with [brackets] wherever the "
                  "auditor must add facts. Use cautious language, never allege fraud or tampering, do not invent "
                  "facts, do not cite case law, keep it under 600 words.\n\nRESULTS (JSON):\n" + str(_facts(res)))
        m = c.messages.create(model=model, max_tokens=1600, messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in m.content if b.type == "text"), f"AI-generated ({model})"
    except Exception as e:
        return memo_offline(res), f"offline template (AI call failed: {type(e).__name__})"


# --------------------------------------------------------------------------- outputs
def workbook(res: Result) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        res.summary.to_excel(xw, sheet_name="Test summary", index=False)
        res.exceptions.to_excel(xw, sheet_name="Exceptions", index=False)
        res.priority.to_excel(xw, sheet_name="Priority vouchers", index=False)
        res.users.to_excel(xw, sheet_name="Activity by user", index=False)
    return buf.getvalue()


def render_png(res: Result, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    log, p = res.log, res.params
    fig, (a, b) = plt.subplots(1, 2, figsize=(14, 5.2))
    cr = log[(log.Action == "Created") & log.VoucherDate.notna()].copy()
    cr["lag"] = (cr.LogTime.dt.normalize() - cr.VoucherDate).dt.days
    flagged = cr.lag > p.backdate_days
    a.scatter(cr.VoucherDate[~flagged], cr.lag[~flagged], s=10, c="#9db4c0", label="Entered promptly")
    a.scatter(cr.VoucherDate[flagged], cr.lag[flagged], s=60, c="#d62728", label=f"Entered > {p.backdate_days} days later")
    a.axhline(p.backdate_days, color="#d62728", lw=0.8, ls="--")
    a.set_title("Days between voucher date and entry in the books"); a.set_ylabel("days"); a.legend(frameon=False)
    m = log.assign(M=log.LogTime.dt.to_period("M")).groupby(["M", "Action"]).size().unstack(fill_value=0)
    m.index = m.index.to_timestamp()
    bottom = None
    for act, col in (("Created", "#9db4c0"), ("Altered", "#ff9f1c"), ("Deleted", "#d62728")):
        if act in m:
            b.bar(m.index, m[act], width=20, bottom=bottom, color=col, label=act)
            bottom = m[act] if bottom is None else bottom + m[act]
    b.axvline(pd.Timestamp(p.finalised_on), color="#1f2d3d", ls="--", lw=1)
    b.text(pd.Timestamp(p.finalised_on), b.get_ylim()[1] * 0.92, " books finalised", fontsize=9)
    b.set_title("Audit-trail activity by month"); b.legend(frameon=False)
    for ax in (a, b):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
