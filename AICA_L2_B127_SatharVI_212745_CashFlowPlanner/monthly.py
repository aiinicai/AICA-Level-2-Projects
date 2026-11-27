"""Monthly cash-flow presentation using the same signed amounts as the Excel export."""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from openpyxl import load_workbook

from engine import PAYMENTS, RECEIPTS, ZERO
from native_book import number
from sources import InputError
from weekly_model import WeeklyModel


OPEN, CLOSE, MOVE = "Opening cash", "Closing cash", "Net movement"
IN, OUT, FUND = "Total receipts", "Total payments", "Net funding"
PDC = "Post-dated cheques"


def money(value):
    if value is None:
        return "—"
    return f"({abs(value):,.3f})" if value < 0 else f"{value:,.3f}"


def period_title(period, cutoff):
    month, phase = period.split()
    name = datetime.strptime(month, "%Y-%m").strftime("%b %Y")
    description = {"closed":"Closed actual", "actual":f"Actual to {cutoff:%d %b}",
                   "remaining":"Remaining forecast", "forecast":"Forecast", "combined":"Actual + remaining"}
    return name, description[phase]


def combine(values, row):
    if row == OPEN:
        return values[0]
    if row == CLOSE:
        return values[-1]
    return None if None in values else sum(values, ZERO)


class Monthly:
    def __init__(self, model):
        self.model = model
        self.rows = []
        self.labels = {PDC:PDC, "Creditors":"Net creditors", "Expenses payable":"Other expenses payable",
                       "LC/LTR":"LC / LTR maturities"}
        self.values = {}
        self.records = defaultdict(list)
        self.locations = {}
        self.previous = {}
        self.previous_label = ""
        self.parts = {MOVE:[IN, OUT, FUND]}
        if isinstance(model, WeeklyModel):
            self._native()
        else:
            self._demo()

    def label(self, row):
        return self.labels.get(row, row)

    def groups(self, combined):
        groups = []
        for period in self.model.periods:
            if combined and period.endswith(" remaining") and groups and groups[-1][0] == self.model.actual:
                groups[-1] += (period,)
            else:
                groups.append((period,))
        return groups

    def column_title(self, group):
        period = group[0] if len(group) == 1 else group[0][:7]+" combined"
        return period_title(period, self.model.cutoff)

    def value(self, row, group):
        return combine([self.values[p,row] for p in group], row)

    def month_values(self, month):
        group = [p for p in self.model.periods if p[:7] == month]
        return {row:self.value(row,group) for row in self.rows}

    def _demo(self):
        model = self.model
        def entry_key(category, project):
            if category == "Collections":
                return "project:"+(project or "")
            return {"PDC":PDC,"Funding":FUND}.get(category,category)
        receipts = ["project:"+code for code in model.project_names]
        self.labels.update({"project:"+code:f"{name} · {code}" for code,name in model.project_names.items()})
        if any(e.category=="Collections" and not e.project for e in model.entries):
            receipts.append("project:")
            self.labels["project:"] = "Collections · unallocated history"
        receipts += list(RECEIPTS[1:])
        payments = [entry_key(k,None) for k in PAYMENTS]
        self.parts.update({IN:receipts, OUT:payments})
        self.rows = [OPEN,*receipts,IN,*payments,OUT,FUND,MOVE,CLOSE]
        for e in model.entries:
            key = (e.period,entry_key(e.category,e.project))
            title = " · ".join(filter(None,(e.reference,e.party or e.project)))
            treatment = f"Excluded · {e.reason} ({money(e.value)})" if e.reason else e.basis
            self.records[key].append((title,treatment,e.evidence,ZERO if e.reason else e.value))
        for p in model.periods:
            for row in (*receipts,*payments,FUND):
                self.values[p,row] = sum((rec[-1] for rec in self.records[p,row]),ZERO)
                self.locations[p,row] = "Cash entries · "+p
            for row in (IN,OUT,MOVE):
                self.values[p,row] = sum(self.values[p,child] for child in self.parts[row])
                self.locations[p,row] = "Cash flow · "+p
            self.values[p,OPEN],self.values[p,CLOSE] = model.opening[p],model.closing[p]
            self.locations[p,OPEN] = (model.sources["Model"].name+" · History, opening cash"
                                     if p==model.periods[0] else "Closing cash · "+model.periods[model.periods.index(p)-1])
            self.locations[p,CLOSE] = "Cash flow · "+p

    def _native(self):
        m = self.model
        book = m.book
        sheet = book.values[book.name]
        rows = {45:OPEN, 46:CLOSE, 15:IN, 30:OUT, 40:FUND, 42:MOVE, 27:PDC}
        for i in (4,*range(6,15),*range(17,30),*range(32,40)):
            if 6 <= i <= 13:
                code = sheet.get(f"B{i}")
                if code is None:
                    continue
                rows[i] = "project:"+str(code)
                self.labels[rows[i]] = f"{sheet.get(f'D{i}') or sheet.get(f'C{i}') or 'Collections'} · {code}"
            elif i not in rows:
                rows[i] = {4:"Retention receipts",19:"Labour",26:"Expenses payable",28:"LC/LTR"}.get(i,str(sheet.get(f"B{i}") or f"Row {i}").strip())
        self.rows = [rows[i] for i in (45,4,*range(6,16),*range(17,31),*range(32,41),42,46) if i in rows]
        self.parts.update({IN:[rows[i] for i in (4,*range(6,15)) if i in rows],
                           OUT:[rows[i] for i in range(17,30)], FUND:[rows[i] for i in range(32,40)]})
        self.previous_label = f"{m.files.baseline.name} · actual to {m.previous_cutoff:%d %b %Y}"
        prior_rows = {str(book.initial[f"B{i}"]):i for i in range(6,14) if book.initial.get(f"B{i}")}
        for group in self.groups(True):
            month = group[0][:7]
            for i,row in rows.items():
                previous = []
                for p in group:
                    col = m.period_columns[p]
                    coord = col+str(i)
                    self.values[p,row] = book.value(coord)
                    self.locations[p,row] = book.name+"!"+coord
                    self.records[p,row].extend(m.trace.get(coord,()))
                    prior_row = prior_rows.get(row[8:]) if row.startswith("project:") else i
                    prior_cell = col+str(prior_row)
                    val = book.initial.get(prior_cell)
                    # Empty schedule cells are zero; absent projects and missing formula caches are unknown.
                    if prior_row is None or val is None and prior_cell in book.original_formulas:
                        previous.append(None)
                    else:
                        previous.append(number(val))
                self.previous[month,row] = combine(previous,row)

    def load_demo_previous(self, path):
        """Use only a matching earlier exported workbook with cached, same-month totals."""
        if not path.is_file():
            raise InputError("Previous cash flow.xlsx is missing from this folder. Select an earlier exported demo workbook.")
        book = load_workbook(path,read_only=True,data_only=True,keep_links=False)
        try:
            source = list(book["Sources"].values)
            cutoff = date.fromisoformat(str(source[4][2]))
            cash = list(book["Cash flow"].values)
            if (cash[0][0] != self.model.company+"  /  Management cash flow" or
                    not str(cash[1][0]).startswith(self.model.currency+" ") or cutoff >= self.model.cutoff):
                raise InputError("Choose a workbook for the same company and currency with an earlier actual cutoff.")
            periods = list(cash[3][1:])
            by_row = {r[0]:r[1:] for r in cash[4:]}
            entries = list(book["Cash entries"].values)[4:]
            collections = defaultdict(lambda:ZERO)
            for p,cat,_,code,_,_,_,included,*_ in entries:
                if cat == "Collections":
                    if not isinstance(included,(int,float)):
                        raise InputError("The prior collection ledger needs saved formula results.")
                    collections[p,code or ""] += Decimal(str(included))
            prior = {}
            for group in self.groups(True):
                month = group[0][:7]
                indices = [i for i,p in enumerate(periods) if str(p)[:7] == month]
                if not indices:
                    continue
                for row in self.rows:
                    if row.startswith("project:"):
                        code = row[8:]
                        if code and not any(k[1]==code for k in collections):
                            continue
                        values = [collections[periods[i],code] for i in indices]
                    else:
                        key = {FUND:"Funding",PDC:"PDC"}.get(row,row)
                        cells = by_row.get(key)
                        if cells is None:
                            continue
                        values = [Decimal(str(cells[i])) if isinstance(cells[i],(int,float)) else None for i in indices]
                    prior[month,row] = combine(values,row)
            if not any(row==CLOSE and n is not None for (_,row),n in prior.items()):
                raise InputError("No comparable month-end closing balances are available in this workbook.")
            self.previous = prior
            self.previous_label = f"{path.name} · actual to {cutoff:%d %b %Y}"
        finally:
            book.close()

    def detail(self, row, group):
        if row == CLOSE:
            first,*_ = group
            lines = [(OPEN,"Opening balance",self.locations[first,OPEN],self.values[first,OPEN])]
            return lines+[(MOVE,p,self.locations[p,MOVE],self.values[p,MOVE]) for p in group]
        lines = []
        for p in group[:1] if row==OPEN else group:
            key = (p,row)
            loc = self.locations[key]
            if row in self.parts:
                lines.extend((self.label(child),p,self.locations[p,child],self.values[p,child]) for child in self.parts[row])
                continue
            records = self.records[key]
            if records:
                if len(group)>1:
                    phase=period_title(p,self.model.cutoff)[1]
                    lines.extend((label,phase+" · "+basis,source,value) for label,basis,source,value in records)
                else:
                    lines.extend(records)
                difference = self.values[key]-sum(r[-1] for r in records)
                if abs(difference) < Decimal("0.0000001"):
                    continue
                lines.append(("Workbook adjustment",self._basis(p,row),loc,difference))
            else:
                lines.append((self.label(row),self._basis(p,row),loc,self.values[key]))
        return lines

    def _basis(self,p,row):
        if isinstance(self.model,WeeklyModel):
            book = self.model.book
            coord = self.locations[p,row].split("!")[-1]
            return book.formulas.get(coord) or ("Updated workbook amount" if coord in book.edits else "Carried from "+self.model.files.baseline.name)
        return "Opening balance" if row==OPEN else "No included entries"
