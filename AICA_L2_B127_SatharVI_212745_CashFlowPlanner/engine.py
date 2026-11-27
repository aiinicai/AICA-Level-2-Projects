"""Cash-flow rules for the synthetic construction-contractor model."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sources import InputError, amount, iso_date, month, pdf_table, shift, snapshots, xls_table

RECEIPTS = ("Collections", "Retention", "Other income")
COSTS = ("Materials", "Labour", "Site overhead")
PAYMENTS = COSTS + ("Creditors", "Expenses payable", "PDC", "LC/LTR", "Head office",
                    "Management overhead", "Marketing", "Finance charges", "Tax", "Fixed assets")
CATEGORIES = RECEIPTS + PAYMENTS + ("Funding",)
MANUAL = set(RECEIPTS + ("Head office", "Management overhead", "Marketing",
                         "Finance charges", "Tax", "Fixed assets", "Funding"))
HISTORY_FIELDS = ("Month", "Opening cash") + CATEGORIES + ("Closing cash",)
ZERO = Decimal("0.000")


@dataclass
class Entry:
    period: str
    category: str
    value: Decimal
    reference: str
    project: str
    party: str
    evidence: str
    basis: str
    reason: str = ""


@dataclass
class Model:
    company: str
    cutoff: date
    currency: str
    months: list
    sources: dict
    entries: list = field(default_factory=list)
    periods: list = field(default_factory=list)
    totals: dict = field(default_factory=dict)
    opening: dict = field(default_factory=dict)
    closing: dict = field(default_factory=dict)
    checks: list = field(default_factory=list)

    @property
    def current(self):
        return self.cutoff.replace(day=1)

    @property
    def actual(self):
        return self.current.strftime("%Y-%m") + " actual"

    def forecast(self, due):
        m = max(self.current, due.replace(day=1))
        return m.strftime("%Y-%m") + (" remaining" if m == self.current else " forecast")

    def check(self, name, observed, expected, where):
        if observed != expected:
            raise InputError(f"{name} — {observed} versus expected {expected}. Check {where}.")
        self.checks.append((name, observed, expected, where))

    def entry(self, period, category, value, ref, project, party, where, basis, reason=""):
        self.entries.append(Entry(period, category, value, ref, project, party, where, basis, reason))


def required(row, key, where):
    value = row[key]
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{where} — '{key}' requires text. Store identifiers as text to preserve leading zeros.")
    return value.strip()


def unique(seen, key, where):
    if key in seen:
        raise InputError(f"{where} — duplicate reference or period '{key}'.")
    seen.add(key)


def positive(value, where):
    n = amount(value, where)
    if n < 0:
        raise InputError(f"{where} — expected a non-negative payment magnitude.")
    return n


def check_period(table, model, label):
    if (table.cutoff, table.currency) != (model.cutoff, model.currency):
        raise InputError(f"{label} — report shows {table.cutoff} / {table.currency}, "
                         f"expected {model.cutoff} / {model.currency}.")
    return table.rows


def load_model(files):
    control = xls_table(files["Model"], "Settings", ("Setting", "Value"))
    settings = {}
    for row, loc in control.rows:
        key = required(row, "Setting", loc)
        if key in settings:
            raise InputError(f"{loc} — duplicate setting {key}.")
        settings[key] = row["Value"]
    count = settings.get("Forecast months")
    company = settings.get("Company")
    if not isinstance(company, str) or not company.strip() or type(count) is not int or not 1 <= count <= 24:
        raise InputError("Starting Model / Settings — enter a company and 1–24 forecast months, including the current month.")
    if control.currency != "OMR":
        raise InputError("This demonstration model uses OMR with three decimal places.")
    months = [shift(control.cutoff, i) for i in range(count)]
    return Model(company, control.cutoff, control.currency, months, files)


def history(model, table):
    history = {}
    for row, loc in table:
        m = month(row["Month"], loc)
        if m in history or m >= model.current:
            raise InputError(f"{loc} — history needs unique, completed months before the cutoff month.")
        history[m] = row, loc
    if not history or max(history) != shift(model.current, -1):
        raise InputError("Starting Model / History — include the month immediately preceding the actual report.")
    previous = None
    for m, (row, loc) in sorted(history.items()):
        period = m.strftime("%Y-%m") + " closed"
        opening, closing = amount(row["Opening cash"], loc), amount(row["Closing cash"], loc)
        values = {cat: amount(row[cat], loc) for cat in CATEGORIES}
        model.check(f"{period} cash roll-forward", opening + sum(values.values()), closing, loc)
        if previous is not None:
            if m != shift(previous, 1):
                raise InputError(f"{loc} — missing closed month in history.")
            model.check(f"{period} opening continuity", opening, prior_close, loc)
        model.periods.append(period)
        if previous is None:
            model.opening[period] = opening
        for cat, n in values.items():
            if n:
                model.entry(period, cat, n, period, "", "", loc, "Closed history")
        previous, prior_close = m, closing
    return prior_close


def actuals(model, summary_rows, detail_rows, prior_close, projects):
    summary = {}
    names = set(CATEGORIES) | {"Opening cash", "Closing cash"}
    for row, loc in summary_rows:
        cat = row["Category"]
        if cat not in names or cat in summary:
            raise InputError(f"{loc} — unexpected or repeated summary line '{cat}'.")
        summary[cat] = amount(row["Amount"], loc), loc
    if names - summary.keys():
        raise InputError("Actual summary missing: " + ", ".join(sorted(names - summary.keys())))
    model.check("Opening agrees to prior month", summary["Opening cash"][0], prior_close, summary["Opening cash"][1])
    totals, seen, actual_values = defaultdict(lambda: ZERO), set(), {}
    for row, loc in detail_rows:
        day = iso_date(row["Date"], loc)
        cat = row["Category"]
        ref = required(row, "Reference", loc)
        unique(seen, ref, loc)
        if cat not in CATEGORIES or not model.current <= day <= model.cutoff:
            raise InputError(f"{loc} — actual category or date is outside this month-to-date snapshot.")
        project = row["Project"]
        if (cat in ("Collections", "Retention") or project) and project not in projects:
            raise InputError(f"{loc} — unknown project '{project}'.")
        n = amount(row["Amount"], loc)
        actual_values[ref] = n, cat
        totals[cat] += n
        model.entry(model.actual, cat, n, ref, project, "", loc, "Actual detail")
    for cat in CATEGORIES:
        model.check(f"Actual detail · {cat}", totals[cat], summary[cat][0], summary[cat][1])
    model.check("Reported closing cash", prior_close + sum(totals.values()), *summary["Closing cash"])
    return actual_values


def manual_plan(model, rows, projects):
    seen = set()
    for row, loc in rows:
        ref = required(row, "Reference", loc)
        unique(seen, ref, loc)
        m = month(row["Month"], loc)
        cat = row["Category"]
        project = row["Project"] or ""
        if m not in model.months or cat not in MANUAL:
            raise InputError(f"{loc} — plan month or category outside the supported forecast.")
        if (cat in ("Collections", "Retention") or project) and project not in projects:
            raise InputError(f"{loc} — unknown project '{project}'.")
        n = amount(row["Amount"], loc)
        model.entry(model.forecast(m), cat, n, ref, project, "", loc, "Management plan")


def payments(model, read, actual_refs):
    used = set()
    facilities, replaced = {}, defaultdict(list)
    def verify_settlement(ref, status, n, cat, loc):
        if ref in actual_refs:
            if status != "Settled" or actual_refs[ref] != (-n, cat):
                raise InputError(f"{loc} — {ref} also appears in actuals. Reconcile its status, category and amount.")
    for role, sheet, cat in (("Facilities", "Maturities", "LC/LTR"), ("Creditors", "Net", "Creditors"),
                              ("Expenses", "Payables", "Expenses payable")):
        rows = read(role, sheet, ("Reference", "Party", "Due date", "Amount", "Status"))
        for row, loc in rows:
            ref, party = required(row, "Reference", loc), required(row, "Party", loc)
            unique(used, ref, loc)
            due, n = iso_date(row["Due date"], loc), positive(row["Amount"], loc)
            status = row["Status"]
            if status not in ("Outstanding", "Deferred", "Settled"):
                raise InputError(f"{loc} — unknown obligation status '{status}'.")
            verify_settlement(ref, status, n, cat, loc)
            if role == "Facilities":
                facilities[ref] = party, n, status
            reason = "" if status == "Outstanding" else status
            if due.replace(day=1) > model.months[-1]:
                reason = reason or "Beyond forecast horizon"
            model.entry(model.forecast(due), cat, -n, ref, "", party, loc, "Net schedule", reason)
    future = defaultdict(lambda: ZERO)
    for row, loc in read("Cheques"):
        ref, party = required(row, "Cheque", loc), required(row, "Party", loc)
        unique(used, ref, loc)
        due, n = iso_date(row["Cheque date"], loc), positive(row["Amount"], loc)
        status = row["Status"]
        if status not in ("Outstanding", "Replaced", "Security", "Settled", "Deferred"):
            raise InputError(f"{loc} — cheque status '{status}' cannot be mapped.")
        verify_settlement(ref, status, n, "PDC", loc)
        link = row["LTR"]
        reason = "" if status == "Outstanding" else status
        if status == "Replaced":
            if link not in facilities or facilities[link][0] != party or facilities[link][2] != "Outstanding":
                raise InputError(f"{loc} — replacement {link!r} needs an outstanding LTR for {party}.")
            replaced[link].append(n)
            reason = "Replaced by " + link
        elif link:
            raise InputError(f"{loc} — LTR reference requires status Replaced.")
        m = due.replace(day=1)
        if status == "Outstanding" and m > model.current:
            if m in model.months:
                future[m] += n
                reason = "Covered by future PDC Payable"
            else:
                reason = "Beyond forecast horizon"
        model.entry(model.forecast(due), "PDC", -n, ref, "", party, loc, "Cheque register", reason)
    for link, parts in replaced.items():
        model.check(f"Replaced cheques → {link}", sum(parts), facilities[link][1], link)
    seen = set()
    for row, loc in read("Projection"):
        m = month(row["Month"], loc)
        if row["Category"] != "PDC Payable":
            continue
        n = positive(row["Amount"], loc)
        unique(seen, m, loc)
        if m in model.months[1:]:
            model.check(f"Future PDC {m:%Y-%m}", n, future[m], loc)
            model.entry(model.forecast(m), "PDC", -n, f"PDC {m:%Y-%m}", "", "", loc, "CF-Proj payable")
        elif m == model.current:
            model.entry(model.forecast(m), "PDC", -n, f"PDC {m:%Y-%m}", "", "", loc, "CF-Proj payable",
                        "Current month uses cheque detail")
    if set(model.months[1:]) - seen:
        raise InputError("CF-Proj — include PDC Payable for every future forecast month, including explicit zeroes.")


def prepare(folder, paths=None):
    files = snapshots(folder, paths)
    model = load_model(files)
    def read(role, sheet=None, fields=None):
        try:
            table = xls_table(files[role], sheet, fields) if sheet else pdf_table(files[role])
            return check_period(table, model, files[role].name + (f" / {sheet}" if sheet else ""))
        except InputError:
            raise
        except Exception as exc:
            raise InputError(f"Could not read {files[role].name}: {exc}") from exc

    project_rows = read("Model", "Projects", ("Project", "Name", "Billable incl retention", "Collected before month"))
    projects = {}
    model.project_names = {}
    for row, loc in project_rows:
        code = required(row, "Project", loc)
        if code in projects:
            raise InputError(f"{loc} — duplicate project {code}.")
        projects[code] = (positive(row["Billable incl retention"], loc), amount(row["Collected before month"], loc), loc)
        model.project_names[code] = required(row, "Name", loc)
    prior_close = history(model, read("Model", "History", HISTORY_FIELDS))
    model.periods += [model.actual] + [model.forecast(m) for m in model.months]
    actual_refs = actuals(model, read("Summary"), read("Detail"), prior_close, projects)
    manual_plan(model, read("Model", "Plan", ("Reference", "Project", "Month", "Category", "Amount")), projects)
    payments(model, read, actual_refs)
    covered = set()
    for row, loc in read("Costs", "CF-DTLD", ("Month", "Project", "Category", "Amount")):
        m, cat, code = month(row["Month"], loc), row["Category"], row["Project"]
        if m not in model.months or cat not in COSTS or code not in projects:
            raise InputError(f"{loc} — unknown cost category, project, or period.")
        unique(covered, (m, cat, code), loc)
        model.entry(model.forecast(m), cat, -positive(row["Amount"], loc), f"{m:%Y-%m} {cat}", code, "",
                    loc, "Remaining cost")
    for m in model.months:
        for cat in COSTS:
            for code in projects:
                if (m, cat, code) not in covered:
                    raise InputError(f"Material Purchase — missing {m:%Y-%m} {cat} for project {code}. Enter zero if nil.")
    for code, (billable, prior, loc) in projects.items():
        collected = sum(e.value for e in model.entries if e.project == code and e.category in ("Collections", "Retention"))
        model.check(f"Project {code} · prior + actual + planned collections", prior + collected, billable, loc)
    totals = defaultdict(lambda: ZERO)
    for e in model.entries:
        if not e.reason:
            totals[e.period, e.category] += e.value
    model.totals = totals
    balance = model.opening[model.periods[0]]
    for period in model.periods:
        model.opening[period] = balance
        balance += sum(totals[period, cat] for cat in CATEGORIES)
        model.closing[period] = balance
    return model
