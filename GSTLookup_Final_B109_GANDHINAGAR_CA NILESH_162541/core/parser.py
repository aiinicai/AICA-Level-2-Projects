"""Tolerant conversion of observed GST payload fields to export records."""
import json
from datetime import datetime
from bs4 import BeautifulSoup
from config import ALIASES, COLUMNS, NA, RETURN_FIELDS, FIELDS, STRUCTURE, STATUS_DATE_FIELD

def text(value: object, sep: str = " | ") -> str:
    if value is None or value == "" or value == [] or value == {}: return NA
    if isinstance(value, dict):
        if STRUCTURE["address"] in value: return text(value[STRUCTURE["address"]])
        return sep.join(str(v) for v in value.values() if v not in (None,"")) or NA
    if isinstance(value,list): return sep.join(text(v) for v in value) or NA
    return str(value)

def date(value: object):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try: return datetime.strptime(str(value),fmt).date()
        except ValueError: pass
    return NA

def financial_year(value: object) -> str:
    """Normalize 2025-26, 2025-2026 and portal-style compact labels."""
    import re
    digits=re.sub(r'[^0-9]','',str(value))
    if len(digits)==8: return digits[:4]+'-'+digits[-2:]
    if len(digits)==6: return digits[:4]+'-'+digits[-2:]
    return str(value).strip()

def has_filing_status(data) -> bool:
    if isinstance(data,dict):
        return FIELDS['returns'] in data or any(has_filing_status(v) for v in data.values() if isinstance(v,(dict,list)))
    if isinstance(data,list): return any(has_filing_status(v) for v in data)
    return False

def filing_entries(data):
    """Find filing lists through wrappers while retaining every published row."""
    if isinstance(data,dict):
        if FIELDS['returns'] in data: yield from flatten(data[FIELDS['returns']])
        else:
            for value in data.values():
                if isinstance(value,(dict,list)): yield from filing_entries(value)
    elif isinstance(data,list):
        for value in data: yield from filing_entries(value)

def flatten(value):
    if isinstance(value,list):
        for item in value: yield from flatten(item)
    elif isinstance(value,dict):
        if RETURN_FIELDS["type"] in value: yield value
        else:
            for item in value.values(): yield from flatten(item)

def parse(payload: dict | str, gstin: str, year: str, returns: dict | None = None) -> tuple[dict,list]:
    if isinstance(payload,str):
        soup=BeautifulSoup(payload,"html.parser")
        script=soup.find("script",attrs={"type":"application/json"})
        if script: payload=json.loads(script.string or "{}")
        else: payload={row.get("data-field"):row.get_text(" ",strip=True) for row in soup.select("[data-field]")}
    row={k:NA for k in COLUMNS}; row.update({"PAN":gstin[2:12],"GST NUMBER":gstin,"RETURN STATUS YEAR":year})
    used=set()
    for column,keys in ALIASES.items():
        if column not in row: continue
        for key in keys:
            if key in payload:
                row[column]=text(payload[key]);used.add(key);break
    row["DATE OF REGISTRATION"]=date(row["DATE OF REGISTRATION"])
    status=str(row['GSTIN/UIN STATUS'])
    if 'cancel' in status.casefold() or 'suspend' in status.casefold():
        effective=date(payload.get(STATUS_DATE_FIELD))
        label=effective.strftime('%d/%m/%Y') if hasattr(effective,'strftime') else NA
        row['GSTIN/UIN STATUS']=f'{status} (Effective date: {label})'

    for field,label in ((STRUCTURE['centre'],'Centre'),(STRUCTURE['state'],'State')):
        jurisdiction=payload.get(field)
        if jurisdiction:
            target='ADMIN OFFICE' if 'Jurisdictional Office' in str(jurisdiction) else 'OTHER OFFICE'
            if row[target]==NA: row[target]=label+': '+str(jurisdiction).replace('(Jurisdictional Office)','').strip()
    lines=[]
    goods=payload.get(STRUCTURE["business"],{}) or {}
    if not isinstance(goods,dict): goods={}
    for kind,col in (("HSN","GOODS"),("SAC","SERVICES")):
        observed=payload.get(STRUCTURE['goods_list' if kind=='HSN' else 'services_list'])
        entries=observed if isinstance(observed,list) else next((goods.get(k,payload.get(k)) for k in ALIASES[col] if goods.get(k,payload.get(k)) is not None),[]) or []
        if isinstance(entries,list):
            for item in entries:
                if isinstance(item,dict): lines.append(f"{kind} {text(item.get(STRUCTURE['goods_code'],item.get(STRUCTURE['service_code'])))} - {text(item.get(STRUCTURE['goods_description'],item.get(STRUCTURE['service_description'])))}")
    row[COLUMNS[11]]="\n".join(lines) or NA
    details=[];summary={}
    data=returns if returns is not None else payload
    for r in filing_entries(data):
        if r.get(RETURN_FIELDS['year']) and financial_year(r[RETURN_FIELDS['year']]) != financial_year(year): continue
        typ=text(r.get(RETURN_FIELDS['type'])); period=text(r.get(RETURN_FIELDS['period'])); status=text(r.get(RETURN_FIELDS['status'])); filed=date(r.get(RETURN_FIELDS['date']))
        details.append({"GST NUMBER":gstin,"Return Type":typ,"Tax Period":period,"Status":status,"Filing Date":filed,"Financial Year":year})
        column={"GSTR3B":"GSTR-3B","GSTR1":"GSTR-1/IFF","IFF":"GSTR-1/IFF","GSTR9":"GSTR-9","GSTR9C":"GSTR-9C","GSTR1/IFF":"GSTR-1/IFF"}.get(typ.upper().replace('-','').replace(' ',''))
        if column: summary.setdefault(column,[]).append(f"{period}: {status}; {filed.strftime('%d/%m/%Y') if hasattr(filed,'strftime') else NA}")
    for column,values in summary.items(): row[column]="\n".join(values)
    extras={k:v for k,v in payload.items() if k not in used|{FIELDS['GSTIN'],STRUCTURE['business'],FIELDS['returns']}}
    if extras: row['Other']=json.dumps(extras,ensure_ascii=False)
    return row,details
