"""Prepare a same-month refresh of a dated management workbook from ERP source files."""
import calendar
import hashlib
import io
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote, urlsplit

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter as letter, coordinate_to_tuple
from openpyxl.utils.datetime import from_excel

from engine import Model
from erp_pdf import cheques, read_flow
from native_book import NativeBook, number, xml
from sources import InputError, Source, shift
from weekly_folder import manifest_at, week_date, digest

TOL = Decimal("0.001")
ACTUAL_ROWS = {14:"Other Income",17:"VAT & TAX",19:"Wages",20:"Site Overhead",21:"General Overhead",
               22:"Manpower OH",23:"Marketting Expense",24:"Finance Charges",29:"Purchse/Sale Fixed Asset",
               38:"Loan Others",39:"Stake Holders"}
FLOW_ROWS = [4,*range(6,15),*range(17,30),*range(32,40)]


def close(a,b,label):
    if abs(number(a)-number(b))>TOL:
        raise InputError(f"{label} — {a} compared with {b}.")


def snapshot(role,path):
    data=path.read_bytes()
    return Source(role,path.name,hashlib.sha256(data).hexdigest(),data)


def table(source,sheet):
    book=load_workbook(io.BytesIO(source.data),read_only=True,data_only=True,keep_links=False)
    try:
        if sheet not in book.sheetnames:
            raise InputError(f"{source.name} — sheet {sheet} is missing.")
        result={}
        for row in book[sheet].iter_rows():
            for c in row:
                if c.value is not None:
                    result[c.coordinate]=c.value
        return result
    finally:
        book.close()


def keys_in_col(cells,col):
    return [(int(a[len(col):]),v) for a,v in cells.items() if a.startswith(col) and a[len(col):].isdigit()]


def exact(rows,label):
    hits=[values for text,values,_ in rows if text==label]
    if len(hits)!=1 or None in hits[0]:
        raise InputError(f"Expected one fully populated ERP report line for '{label}'.")
    return hits[0]


def month_of(value):
    if isinstance(value,(int,float)) and 30000<value<100000:
        value=from_excel(value)
    if isinstance(value,datetime):value=value.date()
    return value.replace(day=1) if isinstance(value,date) else None


def normalize(text):
    return " ".join(str(text or "").upper().split())


def same_record(record, files, sources):
    expected={Path(x["path"]).name.casefold():x["sha256"].lower() for x in record.get("sources",[])}
    return (record.get("status")=="validated" and
            record.get("baseline",{}).get("sha256","").lower()==sources["Model"].digest and
            expected=={v.name.casefold():v.digest for k,v in sources.items() if k!="Model"})


def prior_location(files,book):
    if files.prior_folder:
        return files.prior_folder
    # A copied seed can identify its original archive through its own absolute support links.
    for part,_ in book.links.values():
        rel=Path(part).parent/"_rels"/(Path(part).name+".rels")
        for entry in xml(book.parts[rel.as_posix()]):
            target=urlsplit(entry.get("Target",""))
            if target.scheme!="file" or target.netloc:
                continue
            path=Path(unquote(target.path).lstrip("/"))
            if not path.drive or not week_date(path.parent):
                continue
            seed=path.parent/files.baseline.name
            if seed.is_file() and digest(seed)==hashlib.sha256(book.original_data).hexdigest():
                return path.parent


def find_evidence(files,book,sources):
    prior=prior_location(files,book)
    if same_record(files.record,files,sources):
        return files.record,prior
    if prior and week_date(prior):
        # Match all input hashes before reusing any decision from an archived run.
        for folder in prior.parent.iterdir():
            if folder.is_dir() and week_date(folder) and week_date(prior)<week_date(folder)<=files.snapshot:
                record=manifest_at(folder)
                if same_record(record,files,sources):
                    return record,prior
    return {},prior


class WeeklyModel(Model):
    def trace_line(self, cell, label, treatment, location, included):
        self.trace.setdefault(cell, []).append((label, treatment, location, number(included)))

    def note(self,text):
        if text not in self.notes:self.notes.append(text)

    def save(self,path):
        path=Path(path)
        if self.notes and "draft" not in path.stem.lower():
            raise InputError("Review items remain. Include DRAFT in the exported filename.")
        return self.book.export(path)


def prepare_week(files):
    paths=dict(files.paths,Model=files.baseline)
    sources={k:snapshot(k,p) for k,p in paths.items()}
    (start,cutoff),actual_months,summary=read_flow(sources["Summary"])
    detail_dates,detail_months,detail=read_flow(sources["Detail"])
    if detail_dates!=(start,cutoff) or detail_months!=actual_months or actual_months[-1]!=cutoff.replace(day=1):
        raise InputError("The internal dates on ACTCF and CF-Detailed disagree.")
    book=NativeBook(sources["Model"].data,f"CF-{cutoff:%y}")
    book.original_data=sources["Model"].data
    book.baseline_path=files.baseline
    source_sheet=book.values[book.name]
    for a,v in {"B18":"MATERIALS","B19":"LABOR","B20":"SOH","B25":"CREDITORS",
                "B45":"OPENING BALANCE","B46":"CLOSING BALANCE"}.items():
        if normalize(source_sheet.get(a))!=v:
            raise InputError(f"{book.name}!{a} — expected '{v}'. This workbook layout needs a mapping review.")
    dated=[(m,letter(c)) for c in range(1,100) if (m:=month_of(source_sheet.get(letter(c)+"3")))]
    current=cutoff.replace(day=1)
    cols=[c for m,c in dated if m==current]
    if len(cols)!=2:
        raise InputError(f"The baseline needs actual and remaining columns for {current:%B %Y}. "
                         "This importer currently supports refreshes within an existing split month.")
    actual,remaining=cols
    forecast={m:c for m,c in dated if m>=current}
    model=WeeklyModel("Weekly cash flow",cutoff,"OMR",list(forecast),sources)
    model.book,model.files,model.notes=book,files,[]
    model.trace = {}
    model.period_columns = {}
    rec,prior=find_evidence(files,book,sources)
    model.record=rec
    model.prior=prior
    model.evidence=[]
    def check(label,a,b,where):
        close(a,b,label)
        model.checks.append((label,a,b,where))
    before=book.initial
    base_cutoff=re.search(r"ACTUAL TO\s+(\d{2}-\d{2}-\d{4})",str(before.get("A2","")),re.I)
    if not base_cutoff or datetime.strptime(base_cutoff[1],"%d-%m-%Y").date()>=cutoff:
        raise InputError("The baseline caption needs an earlier actual cutoff. Confirm the previous week's workbook.")
    model.previous_cutoff = datetime.strptime(base_cutoff[1], "%d-%m-%Y").date()
    approvals=rec.get("managementApprovals",{}).get(str(files.snapshot),{})
    # Only these source reports contribute actual movements. CF-Detailed allocates the control.
    for name in [*ACTUAL_ROWS.values(),"Contract Income","Material","Banks","PDC Payable"]:
        label="Total "+name
        if name=="Purchse/Sale Fixed Asset":
            label=next((s for s,v,p in detail if s.startswith("Total Purchse/Sale Fixed As")),label)
        for m,a,b in zip(actual_months,exact(summary,name),exact(detail,label)):
            check(f"{name} {m:%Y-%m}",a,b,"ACTCF / CF-Detailed")
    for i,m in enumerate(actual_months):
        check(f"Source closing {m:%Y-%m}",exact(summary,"Opening Balance")[i]+exact(summary,"Net Cash Flow")[i],
              exact(summary,"Closing Balance")[i],"ACTCF")
        if i:close(exact(summary,"Opening Balance")[i],exact(summary,"Closing Balance")[i-1],"Source opening continuity")
        if m<current:
            hist=[c for day,c in dated if day==m]
            if len(hist)!=1:raise InputError(f"Missing unique closed month {m:%Y-%m} in baseline.")
            close(before.get(hist[0]+"46"),exact(summary,"Closing Balance")[i],"Closed historical balance")
    prev=[c for m,c in dated if m<current][-1]
    close(before[prev+"46"],exact(summary,"Opening Balance")[-1],"Opening cash at cutoff month")
    projects={str(before[f"B{r}"]).strip():r for r in range(6,14) if before.get(f"B{r}")}
    retention={str(v).strip() for _,v in keys_in_col(book.values.get("RTNS",{}),"C")}
    allocated={r:Decimal(0) for r in FLOW_ROWS}
    for label,values,page in detail:
        if label=="Total Contract Income":break
        match=re.match(r"^(\d+)\s*-\s*(.+)",label)
        if not match:continue
        code,name=match.groups()
        if code in projects:r=projects[code]
        elif code in retention:r=4
        elif values[-1]:
            spare=next((r for r in range(6,14) if r not in projects.values()),None)
            if not spare:raise InputError(f"Project {code} requires a new row in the baseline.")
            r=spare
            projects[code]=r
            book.set(f"B{r}",code)
            book.set(f"C{r}",re.sub(r"\s*-\s*CR$","",name))
            book.set(f"D{r}",name.split()[0].title())
            book.set(f"AH{r}","Not supplied")
            book.set(f"AI{r}","n.a.")
            for m,v in zip(actual_months[:-1],values[:-1]):
                if v is None or v!=0:
                    raise InputError(f"Project {code} has historical activity in {m:%Y-%m}. Review the historical allocation.")
                oldcol=next(c for day,c in dated if day==m)
                book.set(f"{oldcol}{r}",v)
        else:continue
        if values[-1] is None:raise InputError(f"Missing actual receipt for project {code}.")
        allocated[r]+=values[-1]
        model.trace_line(actual+str(r),label,"Actual receipts",f"{sources['Detail'].name} · p. {page}",values[-1])
    check("Project receipts",sum(allocated.values()),exact(summary,"Contract Income")[-1],"CF-Detailed")
    for r,label in ACTUAL_ROWS.items():allocated[r]=exact(summary,label)[-1]
    allocated[18]=exact(summary,"Material")[-1]+exact(summary,"Banks")[-1]
    allocated[27]=exact(summary,"PDC Payable")[-1]+exact(summary,"NONE")[-1]
    actual_mapping = {name: row for row, name in ACTUAL_ROWS.items()}
    actual_mapping.update({"Material":18, "Banks":18, "PDC Payable":27, "NONE":27})
    for label, values, page in summary:
        if label in actual_mapping:
            model.trace_line(actual+str(actual_mapping[label]),label,"Actual summary",
                             f"{sources['Summary'].name} · p. {page}",values[-1])
    check("Mapped actual net flow",sum(allocated.values()),exact(summary,"Net Cash Flow")[-1],"ACTCF")
    for r,n in allocated.items():book.set(actual+str(r),n)
    book.set(actual+"47",exact(summary,"Closing Balance")[-1])
    book.set("A2",f"CASH FLOW {cutoff.year} - ACTUAL TO {cutoff:%d-%m-%Y}; {cutoff:%B} REMAINING FORECAST".upper())
    for r in (4,*range(6,14),21,22,23,24,38):
        key=remaining+str(r)
        delta=allocated[r]-number(before.get(actual+str(r)))
        if not delta or r in range(6,14) and not before.get("B"+str(r)):continue
        n=number(before.get(key))-delta
        if 21<=r<=24 or r==38:n=min(Decimal(0),n)
        if r<=13 and n<0:
            model.note(f"{key}: receipts exceed the remaining plan. Review timing of future collections.")
            n=Decimal(0)
        if r==38 and not any("loan" in k.lower() and v is True for k,v in approvals.items()):
            model.note(f"{key}: confirm the remaining loan repayment after the actual movement.")
        formula=book.formulas.get(key)
        book.set(key,n,f"{formula}-({delta})" if formula and n==number(before.get(key))-delta else None)
        model.trace_line(key,"Previous remaining forecast","Baseline",f"{files.baseline.name} · {book.name}!{key}",before.get(key))
        model.trace_line(key,"Change in actuals","Offset since prior cutoff",f"{book.name}!{actual}{r} vs {files.baseline.name} · {actual}{r}",-delta)
    schedules(model,forecast,approvals,check)
    for coord in book.formulas:book.value(coord)
    for day,c in dated:
        p=day.strftime("%Y-%m")+(" closed" if day<current else " actual" if c==actual else
                                 " remaining" if day==current else " forecast")
        model.periods.append(p)
        model.period_columns[p] = c
        model.opening[p]=book.value(c+"45")
        model.closing[p]=book.value(c+"46")
        check(f"{p} roll-forward",model.opening[p]+book.value(c+"42"),model.closing[p],book.name+"!"+c+"46")
        if len(model.periods)>1:close(model.closing[model.periods[-2]],model.opening[p],p+" opening continuity")
    check("Actual close at cutoff",model.closing[model.actual],exact(summary,"Closing Balance")[-1],"ACTCF")
    if rec:
        verify=rec.get("validation",{})
        for k,p in (("actualClosing",model.actual),("lowPoint",min((model.forecast(m) for m in model.months),key=model.closing.get))):
            val=verify.get(k)
            if isinstance(val,dict):val=val.get("balance")
            if val is not None:check("Comparison with previous skill run: "+k,model.closing[p],val,"Refresh record")
    model.evidence=[f"Prior workbook: {files.baseline}",f"Reporting cutoff: {cutoff}",f"Snapshot date: {files.snapshot}",
                    *[f"{role}: {p.name}" for role,p in files.paths.items()],*model.notes,
                    *rec.get("limitations",[])]
    book.audit_rows=[
        ("Refresh review","Draft — review the exceptions below" if model.notes else "Reconciled"),
        ("Actual cutoff",str(cutoff)),("Source snapshot",str(files.snapshot)),("Prior workbook",str(files.baseline)),
        ("Input file","SHA-256"),*((s.name,s.digest) for s in sources.values()),
        ("Management decisions","Matched the current input hashes to the recorded skill run." if rec else
         "Used the preceding model and current reports. See any specific review items below."),
        ("Other external links","Billable values and historical comparisons use the baseline workbook's cached data."),
        *(( "Review required",n) for n in model.notes),
        *(( "Source limitation",n) for n in rec.get("limitations",[])),
        ("Reconciliation","Calculated | control | location"),
        *((label,f"{a:,.3f} | {b:,.3f} | {where}") for label,a,b,where in model.checks),
    ]
    return model


def schedules(model, forecast, approvals, check):
    book,files,src = model.book,model.files,model.sources
    current=model.current
    remaining=forecast[current]
    costs=table(src["Costs"],"CF-DTLD")
    creditors=table(src["Creditors"],"NET")
    expenses=table(src["Expenses"],"Sheet1")
    facilities=table(src["Facilities"],"LC")

    def link(role,cell,sheet):
        f=book.formulas.get(cell,"")
        ids=set(int(x) for x in re.findall(r"\[(\d+)\]",f))
        if len(ids)!=1 or sheet not in book.links[next(iter(ids))][1]:
            raise InputError(f"{book.name}!{cell}: expected an external link to {sheet}.")
        idx=ids.pop()
        book.link_files[idx]=files.paths[role]
        return idx
    costlink=link("Costs",remaining+"18","CF-DTLD")
    netlink=link("Creditors",remaining+"25","NET")
    explink=link("Expenses",remaining+"26","Sheet1")

    def setlinked(col,row,formula,source,updates,linkid,sheet):
        for a,v in updates.items():
            book.ext_value(linkid,sheet,a,v)
        book.set(col+str(row),None,formula)
    sections=[r for r,v in keys_in_col(costs,"A") if normalize(v)=="PROJECT CODE"]
    totals=[r for r,v in keys_in_col(costs,"B") if normalize(v)=="TOTAL"]
    if len(sections)!=3 or len(totals)!=3:raise InputError("CF-DTLD — expected three project sections and totals.")
    for head,total,row in zip(sections,totals,(18,19,20)):
        if total<=head:raise InputError("CF-DTLD — section and total rows are misaligned.")
        for i in range(4,60):
            col=letter(i)
            base=month_of(costs.get(col+str(sections[0])))
            month=month_of(costs.get(col+str(head)))
            if not base:break
            v=costs.get(col+str(total))
            if v is None:raise InputError(f"Missing remaining-cost subtotal {col}{total}.")
            if base<current and not number(v):continue
            if month!=base:
                if month and shift(month,1)==base and base>=current:
                    month=base
                    if not any(k.lower().startswith(("costsectionsstart","labourandsiteoverheadsstart")) and val is True
                               for k,val in approvals.items()):
                        model.note("Labour/site overhead headings differ from materials. Draft uses the materials month sequence. Confirm the effective months.")
                else:raise InputError(f"Conflicting cost headings in {col}{head}.")
            if month not in forecast:
                if number(v):raise InputError(f"Nonzero remaining costs outside model horizon in {col}{total}.")
                continue
            addr=col+str(total)
            check(f"Remaining cost {addr}",sum(number(costs.get(col+str(r))) for r in range(head+1,total)),
                  v,src["Costs"].name)
            dest=forecast[month]+str(row)
            for r in range(head+1,total):
                part = number(costs.get(col+str(r)))
                if part:
                    model.trace_line(dest,str(costs.get("B"+str(r)) or costs.get("A"+str(r)) or "Project cost"),
                                     "Remaining cost",f"{src['Costs'].name} · CF-DTLD!{col}{r}",-part)
            old=book.formulas.get(dest)
            pattern=rf"'?\[{costlink}\]CF-DTLD'?!\$?[A-Z]+\$?\d+"
            if old and re.search(pattern,old):
                formula=re.sub(pattern,lambda _:f"'[{costlink}]CF-DTLD'!{addr}",old)
            else:
                if number(book.initial.get(dest)):model.note(f"{dest}: review replacement of a prior unlinked cost forecast.")
                formula=f"=-'[{costlink}]CF-DTLD'!{addr}"
            setlinked(forecast[month],row,formula,src["Costs"],{addr:v},costlink,"CF-DTLD")

    # Translate existing exclusions by account/expense identity, so inserted source rows are harmless.
    def prior_table(role,sheet):
        if model.prior:
            pattern=re.sub(r"\s*-\s*\d\d-\d\d-\d{4}$","",files.paths[role].stem)
            candidates=[p for p in model.prior.glob("*.xlsx") if re.fullmatch(re.escape(pattern)+
                        r"(?:\s*-\s*\d\d-\d\d-\d{4})?",p.stem,re.I)]
            if len(candidates)==1:
                return table(snapshot(role,candidates[0]),sheet)
        return {}
    previous_net=prior_table("Creditors","NET")
    previous_exp=prior_table("Expenses","Sheet1")

    def total_row(cells):
        hits=[r for r,v in keys_in_col(cells,"B") if normalize(v)=="TOTAL"]
        if len(hits)!=1:raise InputError("Cannot identify a unique creditor-schedule total.")
        return hits[0]
    net_total=total_row(creditors)
    refs=re.findall(rf"\[{netlink}\]NET!\$?[A-Z]+\$?(\d+)",book.formulas[remaining+"25"])
    excluded=[]
    for oldrow in set(refs[1:])-set(refs[:1]):
        ident=previous_net.get("A"+oldrow)
        matches=[r for r,v in keys_in_col(creditors,"A") if ident and v==ident]
        if len(matches)==1:excluded.extend(matches)
        else:model.note("Confirm the deferred creditor account. Draft includes the gross scheduled amount before this exclusion.")
    for i in range(1,60):
        col=letter(i)
        month=month_of(creditors.get(col+"3"))
        if not month:continue
        if month<current:raise InputError("Net creditors include an earlier month. Confirm which overdue amounts remain outstanding.")
        if month not in forecast:continue
        addr=col+str(net_total)
        if addr not in creditors:raise InputError(f"Missing NET total {addr}.")
        check(f"Net creditors {month:%Y-%m}",sum(number(creditors.get(col+str(r))) for r in range(4,net_total)),
              creditors[addr],src["Creditors"].name)
        adds=[addr]+[col+str(r) for r in excluded]
        for r in range(4,net_total):
            part = number(creditors.get(col+str(r)))
            if part:
                model.trace_line(forecast[month]+"25",str(creditors.get("B"+str(r)) or creditors.get("A"+str(r))),
                                 f"Deferred ({part:,.3f})" if r in excluded else "Net creditor",
                                 f"{src['Creditors'].name} · NET!{col}{r}",0 if r in excluded else -part)
        formula="=-("+"-".join(f"[{netlink}]NET!{a}" for a in adds)+")"
        setlinked(forecast[month],25,formula,src["Creditors"],{a:number(creditors.get(a)) for a in adds},netlink,"NET")

    total=total_row(expenses)
    asof=re.search(r"(\d{1,2}/\d{1,2}/\d{4})",str(expenses.get("A1","")))
    if not asof or datetime.strptime(asof[1],"%d/%m/%Y").date()!=model.cutoff:
        raise InputError("Other Creditors — statement date differs from the actual cutoff.")
    amt=expenses.get("D"+str(total))
    if amt is None:raise InputError("Other Creditors — schedule is missing the total amount.")
    check("Other expenses total",sum(number(expenses.get("D"+str(r))) for r in range(3,total)),amt,src["Expenses"].name)
    exp_pattern=rf"'?\[{explink}\]Sheet1'?!([A-Z]+)(\d+)"
    substitutions={}
    def remap(match):
        col,r=match.groups()
        old=col+r
        if old in substitutions:return substitutions[old]
        label=normalize(previous_exp.get("B"+r))
        if label=="TOTAL":rr=total
        else:
            matches=[i for i,v in keys_in_col(expenses,"B") if label and normalize(v)==label]
            if len(matches)!=1:
                raise InputError(f"Cannot map prior Other Creditors {old} by expense name. Select the original preceding workbook "
                                 "using Choose baseline so its supporting schedules can be read.")
            rr=matches[0]
        new=col+str(rr)
        if new not in expenses:raise InputError(f"Other Creditors {new} has no amount.")
        substitutions[old]=f"'[{explink}]Sheet1'!{new}"
        book.ext_value(explink,"Sheet1",new,expenses[new])
        return substitutions[old]
    if previous_exp:
        for a,f in list(book.formulas.items()):
            if re.search(exp_pattern,f):
                book.set(a,None,re.sub(exp_pattern,remap,f))
        if not model.record and len(substitutions)>1:
            model.note(f"{remaining}26: prior expense exclusions were matched by name. Confirm the paid items and VAT/PDC offsets still apply.")
    else:
        addr="D"+str(total)
        book.ext_value(explink,"Sheet1",addr,amt)
        book.set(remaining+"26",None,f"=-'[{explink}]Sheet1'!{addr}")
        model.note("Previous expense schedule unavailable. Draft uses the full other-creditors balance. Review tax, PDC and paid-expense offsets.")
    # Expose the expense total and offsets when the linked formula is a signed sum.
    for col in forecast.values():
        cell=col+"26"
        formula=book.formulas.get(cell,"")
        token=rf"'?\[{explink}\]Sheet1'?!([A-Z]+[0-9]+)"
        outer=re.fullmatch(r"=-\((.+)\)",formula)
        body=outer[1] if outer else formula.removeprefix("=-")
        if not (outer or formula.startswith("=-")) or not re.fullmatch(token+rf"(?:[-+]{token})*",body):
            continue
        for term in re.finditer(r"([-+]?)"+token,body):
            sign,addr=term.groups()
            row=re.search(r"\d+",addr)[0]
            model.trace_line(cell,str(expenses.get("B"+row) or addr),"Expense offset" if sign=="-" else "Expense schedule",
                             f"{src['Expenses'].name} · Sheet1!{addr}",number(expenses.get(addr))*(1 if sign=="-" else -1))
    # Treasury schedules use payment dates and actual outstanding instruments.
    end,pdcs=cheques(src["Cheques"])
    if end!=date(current.year,current.month,calendar.monthrange(current.year,current.month)[1]):
        raise InputError("PDC report must cover outstanding cheques through the forecast month end.")
    instruments={}
    monthly={}
    for r,v in keys_in_col(facilities,"E"):
        if r==1:continue
        ref=str(facilities.get("D"+str(r),"")).strip()
        day=month_of(facilities.get("H"+str(r)))
        if not ref or not day or ref in instruments:raise InputError(f"LC row {r}: invalid reference or maturity.")
        instruments[ref]=number(v)
        m=max(current,day)
        if m not in forecast:raise InputError(f"Facility {ref} matures outside the supported horizon.")
        monthly[m]=monthly.get(m,0)+number(v)
        model.trace_line(forecast[m]+"28",ref,f"Maturity {facilities.get('H'+str(r))!s}"[:32],
                         f"{src['Facilities'].name} · LC!E{r}",-number(v))
    recorded={str(x["cheque"]):x for x in model.record.get("paymentExclusions",[])}
    eligible=Decimal(0)
    for row in pdcs:
        if row["day"]>end:raise InputError("PDC cheque date exceeds the printed report horizon.")
        decision=recorded.get(row["ref"])
        label=f"{row['ref']} · {row['party']}"
        loc=f"{src['Cheques'].name} · p. {row['page']} · {row['day']:%d %b}"
        if re.search(r"\bsecurity\b",row["note"],re.I):
            model.trace_line(remaining+"27",label,f"Excluded · security ({row['amount']:,.3f})",loc,0)
            continue
        if decision:
            close(row["amount"],decision["amount"],"Excluded cheque "+row["ref"])
            if normalize(row["party"])!=normalize(decision.get("party")):
                raise InputError("PDC exclusion party changed: "+row["ref"])
            reason=decision.get("excludedReason","")
            if "replac" in reason.lower():
                matching=[ref for ref,v in instruments.items() if ref in reason and abs(v-row["amount"])<=TOL]
                if len(matching)!=1:raise InputError(f"Cannot reconcile replacement LTR for cheque {row['ref']}.")
                model.trace_line(remaining+"27",label,f"Excluded · {reason} ({row['amount']:,.3f})",loc,0)
                continue
            raise InputError(f"Unrecognised exclusion for cheque {row['ref']}: {reason}")
        if not model.record and row["amount"] in instruments.values():
            model.note("Review possible PDC/LTR replacement for cheque "+row["ref"]+". Draft includes both records.")
        eligible+=row["amount"]
        model.trace_line(remaining+"27",label,"Outstanding",loc,-row["amount"])
    book.set(remaining+"27",-eligible)
    pdates,months,proj=read_flow(src["Projection"])
    if months[0]!=current or pdates[0].replace(day=1)!=current:
        raise InputError("CF-Proj periods do not cover the actual cutoff month.")
    for m,v in zip(months[1:],exact(proj,"PDC Payable")[1:]):
        if m in forecast:
            book.set(forecast[m]+"27",v)
            page=next(p for label,_,p in proj if label=="PDC Payable")
            model.trace_line(forecast[m]+"27","PDC Payable","Projected payments",
                             f"{src['Projection'].name} · p. {page}",v)
        elif v:raise InputError("Future PDC falls outside the model horizon.")
    for m,c in forecast.items():
        if m in monthly or book.initial.get(c+"28") is not None:
            book.set(c+"28",-monthly.get(m,0))
        if m>months[-1] and number(book.initial.get(c+"27")):
            model.note(f"{c}27: prior PDC forecast extends beyond the coverage of CF-Proj.")
