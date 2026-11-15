"""Conservative, evidence-preserving classification and OCR/document extraction."""
from __future__ import annotations
import copy,csv,io,re,datetime
from pathlib import Path
from runtime_io import decode_output,reset_evidence,take_evidence

# Reversible punctuation artifacts only: never 'repair' names, identifiers or numbers.
MOJIBAKE={'â€”':'—','â€“':'–','â€˜':'‘','â€™':'’','â€œ':'“','â€\x9d':'”','â€':'”','Â ':'\u00a0','ï»¿':''}
def repair_text(text):
    original=text;changes=[]
    for broken,fixed in MOJIBAKE.items():
        if broken in text:text=text.replace(broken,fixed);changes.append(dict(original=broken,replacement=fixed))
    return text,changes

def detect_type(text):
    low=text.casefold()
    markers=[]
    ca_report=bool(re.search(r'net\s+asset\s+report|detail\s+of\s+(?:im)?movable\s+assets|annexure[- ]?[ab]',low))
    passport=bool(re.search(r'(?m)^\s*P<[A-Z<]{3}',text))
    identity=sum(bool(re.search(p,low)) for p in (r'given\s+name',r'surname',r'date\s+of\s+birth',r'nationality|nationaitly',r'name\s+of\s+(?:father|mother|spouse)'))
    passport=passport or bool(re.search(r'passport\s*(?:no\.?|number)',low) and identity>=2)
    itr=bool(re.search(r'income\s*tax\s*return|\bitr[- ]?v\b|form\s+itr[- ]?\d',low) or ('acknowledgement number' in low and 'assessment year' in low))
    computation=bool(re.search(r'computation\s+of\s+(?:total\s+)?income|income\s+computation',low))
    assets=bool('valuation report' in low and re.search(r'property|owner|value\s+of\s+land',low))
    # An issued CA report contains passport words and identifiers as evidence;
    # it must be classified as an asset report, not as a passport.
    if ca_report:
        markers=['Assets']
    else:
        if passport:markers.append('Passport')
        if itr:markers.append('ITR')
        if computation and not itr:markers.append('Computation')
        if assets:markers.append('Assets')
    return ('Mixed' if len(markers)>1 else markers[0] if markers else ''),markers

def valid_date(value):
    m=re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-]((?:19|20)\d{2})\b',value)
    if not m:return ''
    try:datetime.date(int(m[3]),int(m[2]),int(m[1]));return m[0]
    except ValueError:return ''

def clean_name(value):
    value=re.split(r'\s+[SDW]\s*[/\\]\s*[Oo]\b',value,flags=re.I)[0].strip(' :|,.-')
    if not value or re.search(r'\d|[/|:]',value):return '',False
    words=value.split();upper=[]
    for word in words:
        letters=re.sub(r"[^A-Za-z]",'',word)
        if letters and letters.isupper():upper.append(word)
        else:break
    # All-capital printed names followed by lowercase OCR garbage remain reviewable.
    if len(upper)>=2 and len(upper)<len(words):return ' '.join(upper),True
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'’-]*",value):return '',False
    if len(words)==1 and len(value)<2:return '',False
    return value,False

def parse_passport(text):
    import asset_model as model
    cleaned,repairs=repair_text(text);fields={k:'' for k in model.PASSPORT_FIELDS};evidence={};unknown=[];warnings=[];conflicts={};pending=[];dates=[]
    # English label fragments may follow multilingual OCR junk. Long/old labels first.
    patterns=[]
    for key,ps in model.LABELS.items():
        for pat in ps:patterns.append((key,re.compile(r'(?<![A-Za-z])(?:'+pat+r')(?![A-Za-z])',re.I)))
    patterns.extend([('old_passport_number',re.compile(r'(?<![A-Za-z])(?:old|ld)\s+passport\s*(?:no\.?|number)',re.I)),('given_names',re.compile(r'given\s+name\s*\(s\)',re.I)),('nationality',re.compile(r'nationaitly',re.I)),('issuing_country',re.compile(r'(?<![A-Za-z])code\b',re.I))])
    patterns.sort(key=lambda pair:0 if pair[0].startswith('old_') else 1)
    names={'full_name','surname','given_names','father_name','mother_name','spouse_name'}
    datekeys={'date_of_birth','date_of_issue','date_of_expiry','old_date_of_issue'}
    def assign(key,value,line_number,line):
        if not value:return
        if fields[key] and fields[key]!=value:
            conflicts.setdefault(key,[fields[key]])
            if value not in conflicts[key]:conflicts[key].append(value)
        elif not fields[key]:fields[key]=value
        evidence.setdefault(key,[]).append(dict(line=line_number,text=line))
        if key in pending:pending.remove(key)
    def candidate(key,value):
        value=value.strip(' \t:#|-,')
        if key in names:
            name,trimmed=clean_name(value)
            if trimmed:warnings.append('Trailing OCR text omitted from '+key+' candidate; verify original evidence.')
            return name
        if key in datekeys:return valid_date(value)
        if key in ('passport_number','old_passport_number'):
            m=re.fullmatch(r'[A-Z0-9]{7,9}',value.upper());return m[0] if m else ''
        if key=='sex':return value.upper() if value.upper() in ('M','F','X') else ''
        if key=='document_type':return value.upper() if value.upper() in ('P','D','S') else ''
        if key=='issuing_country':return value if re.fullmatch('[A-Z]{3}',value) else ''
        if key=='nationality':
            m=re.search(r'\bINDIAN\b',value,re.I);return m[0] if m else (value if re.fullmatch(r'[A-Z]{3,30}',value) else '')
        return value
    lines=cleaned.splitlines()
    for number,raw in enumerate(lines,1):
        line=raw.strip()
        if not line:continue
        if line.startswith('SHEET:'):continue
        if line.upper() in ('ECR','NON-ECR','ECNR','EMIGRATION CHECK REQUIRED','EMIGRATION CHECK NOT REQUIRED'):
            assign('emigration_status',line,number,raw);continue
        if re.match(r'^P<',line,re.I) or (len(line)>=40 and re.fullmatch(r'[A-Z0-9<]+',line)):
            unknown.append(dict(line=number,text=raw));continue
        matched=None
        for key,pat in patterns:
            m=pat.search(line)
            if m:
                if key=='address' and m.start()>0 and '/' not in line[:m.start()] and ':' not in line[:m.start()]:continue
                # Generic current issue labels inside an old-passport combined heading are not current data.
                if 'old passport' in line.lower() and not key.startswith('old_'):continue
                matched=(key,m);break
        if matched:
            key,m=matched
            if key=='given_names':
                # Consume Name(s) completely, rather than leaving '(s)' as a proposed value.
                suffix=re.sub(r'^\s*\(s\)','',line[m.end():],flags=re.I)
            else:suffix=line[m.end():]
            pending[:]=[k for k in pending if k not in names or k==key]
            if key not in pending:pending.append(key)
            value=candidate(key,suffix)
            # Family label tails are often random OCR fragments; only a plausible value is accepted.
            if key in names and suffix and re.search(r'\d',suffix):value=''
            if value:assign(key,value,number,raw)
            else:evidence.setdefault(key,[]).append(dict(line=number,text=raw))
            continue
        # Indian printed passport numbers can be vertically displaced under the surname label.
        bare=re.fullmatch(r'[A-Z]\d{7}',line)
        if bare and 'old_passport_number' not in pending:
            assign('passport_number',bare[0],number,raw);continue
        if 'old_passport_number' in pending:
            old=re.match(r'([A-Z0-9]{7,9})\s+',line)
            if old and valid_date(line):
                assign('old_passport_number',old[1],number,raw)
                assign('old_date_of_issue',valid_date(line),number,raw)
                after=line.split(valid_date(line),1)[-1]
                place=re.search(r'[A-Z][A-Z .-]{2,}',after)
                if place:
                    assign('old_place_of_issue',place[0].strip(' .-'),number,raw)
                    warnings.append('Old issue place is an OCR candidate; verify its exact spelling against the source.')
                unknown.append(dict(line=number,text=raw));continue
        date=valid_date(line)
        if date:
            eligible=[k for k in pending if k in datekeys]
            if eligible:assign(eligible[0],date,number,raw)
            else:dates.append(dict(line=number,value=date,text=raw));unknown.append(dict(line=number,text=raw))
            continue
        handled=False
        # Type-aware pending queues tolerate DOB/Sex headings appearing before their values.
        for key in reversed(pending):
            if key in datekeys:continue
            value=candidate(key,line)
            if key in names and not re.fullmatch(r"[A-Za-z][A-Za-z .'’-]*",line):value=''
            if key=='address':
                if re.search(r'old\s+passport|file\s*(?:no|number)',line,re.I):continue
                fields[key]=(fields[key]+' '+line).strip();evidence.setdefault(key,[]).append(dict(line=number,text=raw));handled=True;break
            if key=='observations':
                fields[key]=(fields[key]+' '+line).strip();evidence.setdefault(key,[]).append(dict(line=number,text=raw));handled=True;break
            if value:assign(key,value,number,raw);handled=True;break
        if not handled:unknown.append(dict(line=number,text=raw))
    # Use the original rigorously check-digit-validated TD3 implementation only for MRZ.
    mrz_lines=[line.strip() for line in lines if line.strip().startswith('P<') or (len(line.strip())>=40 and re.fullmatch(r'[A-Z0-9<]+',line.strip()))]
    if mrz_lines:
        mrz=model._canonical_passport_parser('\n'.join(mrz_lines))
        for key in ('mrz_line_1','mrz_line_2'):
            idx=0 if key.endswith('1') else 1
            if len(mrz_lines)>idx:fields[key]=mrz_lines[idx]
        grammar_ok=(len(mrz_lines)>=2 and all(len(x)==44 for x in mrz_lines[:2]) and bool(re.fullmatch(r'P<[A-Z<]{42}',mrz_lines[0])) and bool(re.fullmatch(r'[A-Z0-9<]{44}',mrz_lines[1])) and bool(re.fullmatch(r'[A-Z<]{3}',mrz_lines[1][10:13])))
        if not grammar_ok:warnings.append('Malformed MRZ retained; no uncertain MRZ identity/date values accepted.')
        else:
            for key,value in mrz['passport_details'].items():
                if key=='full_name' or not value:continue
                if not fields[key]:fields[key]=value;evidence[key]=mrz['evidence'].get(key,[])
                elif key in ('passport_number','date_of_birth','date_of_expiry') and model.norm(fields[key])!=model.norm(value):
                    # Date separator differences are not identity conflicts.
                    if key.startswith('date') and valid_date(fields[key]).replace('/','.').replace('-','.')==valid_date(value).replace('/','.').replace('-','.'):continue
                    conflicts.setdefault(key,[fields[key]]).append(value)
            warnings.extend(mrz['warnings'])
    if not fields['address']:
        # Address labels may be lost; require explicit postal PIN + street/address wording.
        for i,line in enumerate(lines):
            if re.search(r'\bPIN\s*[: -]?\s*\d{6}',line,re.I):
                start=next((j for j in range(max(0,i-6),i) if re.search(r'\bROAD\b|\bNAGAR\b|\bST\s*(?:NO|\d)|\bH\.?\s*NO\.?\b|\bHOUSE\b|\bWARD\b|\bVPO\b|\bCIVIL\s+DISPENSARY\b',lines[j],re.I)),None)
                if start is not None:
                    raw=' '.join(x.strip() for x in lines[start:i+1])
                    raw=re.sub(r'\s+', ' ', raw).replace('“',' ').replace('”',' ')
                    raw=re.sub(r'\b(?:Di\s+i|2a|See)\b', ' ', raw, flags=re.I)
                    raw=re.sub(r'\s*,\s*', ', ', raw)
                    raw=re.sub(r'\bH\s*\.\s*NO\s*\.?', 'H.NO.', raw, flags=re.I)
                    raw=re.sub(r'\bWARD\s+NO\s*\.?(\d+)', r'WARD NO. \1', raw, flags=re.I)
                    raw=re.sub(r'(PIN\s*:\s*\d{6}.*?\bINDIA)\b.*$', r'\1', raw, flags=re.I)
                    fields['address']=raw.strip(' ,.;')
                    evidence['address']=[dict(line=j+1,text=lines[j]) for j in range(start,i+1)];warnings.append('Address proposed from street/PIN evidence; verify the full address.')
    fields['full_name']=fields['full_name'] or ' '.join(x for x in (fields['given_names'],fields['surname']) if x)
    if dates:warnings.append('Unassigned printed date candidate(s) retained; do not guess expiry from position alone.')
    warnings.extend('Conflicting repeated field: '+k+' - review original source' for k in conflicts)
    multiple=len(set(conflicts.get('passport_number',[])))>1
    if multiple:warnings.append('Multiple passport identities detected: split the source by applicant.')
    if repairs:warnings.append('Reversible punctuation mojibake repaired for parsing; original text retained.')
    return dict(passport_details=fields,evidence=evidence,unknown_fields=unknown,text=cleaned,original_text=text,
                text_repairs=repairs,warnings=warnings,field_conflicts=conflicts,date_candidates=dates,multiple_passports=multiple)

def valuation_proposals(text,path=''):
    from valuation_intake import valuation_proposals as extract
    return extract(text,path)


def reparse(proposal,kind,explicit=False):
    import asset_model as model
    import legacy_engine as engine
    original=proposal.get('original_text',proposal.get('text',''));text,repairs=repair_text(original)
    detected,markers=detect_type(text);requested=kind
    effective=detected if detected and detected!='Mixed' and not explicit else kind
    prop=copy.deepcopy(proposal);prop.update(text=text,original_text=original,text_repairs=repairs,kind=effective,requested_kind=proposal.get('requested_kind',requested),detected_kind=detected,classification_evidence=markers,reclassification_required=bool(detected and detected!='Mixed' and effective!=requested and not explicit),mixed_document=detected=='Mixed')
    prop.update(assets=[],income={},passport_details={},warnings=[])
    administrative_land_record=bool(re.search(r'\b(?:jamabandi|registry|sale\s+deed|khasra|khatauni|mutation)\b',text,re.I))
    valuation_source=bool(re.search(r'\b(?:valuation\s+report|architect|valuer|market\s+value)\b',text,re.I))
    if administrative_land_record and not valuation_source:
        prop['ignored_document']=True;prop['doc_type']='Ignored';prop['warnings'].append('Administrative land record detected; retained as evidence but not imported as an asset. Upload the architect valuation report for property value.')
        return prop
    if effective=='Passport':
        parsed=parse_passport(original);prop.update(parsed)
    else:
        result=engine.extract_document_proposals(prop.get('path',''),[text],'');prop.update({k:v for k,v in result.items() if k not in ('path','text','passport_details','applicant','page_count','ocr_pages')})
        if effective in ('ITR','Computation'):
            from income_intake import extract_income,tax_sections
            parsed=extract_income(text,prop.get('page_texts'));prop.update(parsed);prop.update(assets=[],doc_type=effective)
            sections=tax_sections(prop.get('page_texts') or [text])
            if len(sections)>1:prop['tax_sections']=sections;prop['warnings'].append('Multiple tax sections / years found. Review each independently; no cross-year merge.')
        elif effective=='Assets' and 'valuation report' in text.lower() and re.search(r'property|vacant\s+plot|value\s+of\s+land|construction',text,re.I):prop.update(valuation_proposals(text,prop.get('path','')))
        if effective=='Assets' and re.search(r'gold\s+valuation|jewell?ery\s+valuation|ornaments',text,re.I) and not re.search(r'property\s*:|value\s+of\s+land|immovable\s+property',text,re.I):
            from movable_intake import jewellery_proposals
            prop.update(jewellery_proposals(text,prop.get('path','')))
        if effective=='Assets' and prop.get('cells'):
            structured=model.table_assets(prop['cells'])
            if structured:prop['assets']=structured
        if effective=='Assets' and Path(prop.get('path','')).suffix.lower()=='.csv':
            from openpyxl.utils import get_column_letter
            cells=[dict(sheet='CSV',cell=f'{get_column_letter(c)}{r}',value=value) for r,row in enumerate(csv.reader(io.StringIO(text)),1) for c,value in enumerate(row,1)]
            structured=model.table_assets(cells)
            if structured:prop['assets']=structured
    if effective=='Assets' and not prop.get('assets'):
        prop['assets']=[dict(category='Other Asset',asset_name='Name this asset',amount='',desc='',fields={},amount_candidates=[])]
        prop['warnings'].append('No certified amount was extracted. Enter the asset name, value and owner in this editable proposal; source evidence is retained.')
    prop['doc_type']=effective
    if prop['reclassification_required']:prop['warnings'].append('Selected '+requested+'; strong source markers indicate '+effective+'. Confirm the detected type before applying.')
    if detected=='Mixed':prop['warnings'].append('Multiple document types detected. Split the source into individual documents before applying.')
    if repairs and not any('mojibake' in w for w in prop['warnings']):prop['warnings'].append('Punctuation mojibake repaired; original extraction retained.')
    if prop.get('cells') and any(c.get('formula') and c.get('value') is None for c in prop['cells']):prop['warnings'].append('Some Excel formulas have no cached values. Recalculate/save in Excel. Formulas were not executed.')
    for ev in prop.get('runtime_evidence',[]):prop['warnings'].extend(ev.get('warnings',[]))
    return prop

def read_proposal(path,kind):
    import asset_model as model
    import legacy_engine as engine
    import import_log
    log_id=import_log.start(path,kind)
    reset_evidence();suffix=Path(path).suffix.lower();cells=[];notes=[];source_bytes=None;page_errors=[]
    try:
        import_log.write(log_id,'detected_extension',extension=suffix)
        if suffix in ('.xlsx','.xlsm','.xls'):
            pages,cells=model.read_workbook(path);ocr=0;import_log.write(log_id,'read_workbook',pages=len(pages),cells=len(cells))
        elif suffix in ('.txt','.csv'):
            source_bytes=Path(path).read_bytes();text,encoding,notes=decode_output(source_bytes);pages=[text];ocr=0;import_log.write(log_id,'read_text',encoding=encoding,bytes=len(source_bytes))
        else:
            tess=engine.find_tesseract();import_log.write(log_id,'ocr_engine',available=bool(tess),path=tess or '')
            pages,ocr=engine.read_document_text(str(path),tess,page_errors=page_errors);import_log.write(log_id,'read_document',pages=len(pages),ocr_pages=ocr,page_errors=page_errors)
        import hashlib
        fingerprint=hashlib.sha256(Path(path).read_bytes()).hexdigest()
        base=dict(page_texts=pages,unread_pages=page_errors,sha256=fingerprint,path=str(path),original_text='\n'.join(pages),cells=cells,ocr_pages=ocr,page_count=len(pages),runtime_evidence=take_evidence())
        if source_bytes is not None:
            import base64
            base['source_bytes_base64']=base64.b64encode(source_bytes).decode('ascii');base['source_encoding']=encoding
        prop=reparse(base,kind);prop['warnings'].extend(notes+page_errors);prop['_import_log_id']=log_id
        import_log.write(log_id,'classified',detected_kind=prop.get('kind',''),warnings=len(prop.get('warnings',[])),assets=len(prop.get('assets',[])),tax_sections=len(prop.get('tax_sections',[])))
        import_log.finish(log_id,page_count=prop.get('page_count',len(pages)))
        return prop
    except Exception as exc:
        import_log.fail(log_id,exc);raise
