"""Headless, local-only case model. No macros, browser, or network calls."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import copy, datetime, json, re, uuid
from pathlib import Path
import legacy_engine as engine

VERSION = '2.1.2'
PASSPORT_FIELDS = {
 'full_name':'Full name', 'given_names':'Given names', 'surname':'Surname',
 'passport_number':'Passport number', 'document_type':'Document type',
 'issuing_country':'Issuing country / code', 'nationality':'Nationality', 'sex':'Sex',
 'date_of_birth':'Date of birth', 'place_of_birth':'Place of birth',
 'place_of_issue':'Place of issue', 'date_of_issue':'Date of issue', 'date_of_expiry':'Date of expiry',
 'father_name':'Father / legal guardian', 'mother_name':'Mother', 'spouse_name':'Spouse / husband',
 'address':'Full address', 'file_number':'File number', 'personal_number':'Personal number',
 'old_passport_number':'Old passport number', 'old_date_of_issue':'Old passport issue date',
 'old_place_of_issue':'Old passport issue place', 'observations':'Observations / endorsements',
 'mrz_line_1':'MRZ line 1', 'mrz_line_2':'MRZ line 2',
 'emigration_status':'ECR / non-ECR status', 'issuing_authority':'Issuing authority',
 'emergency_contact':'Emergency contact', 'other_identifiers':'Other identifiers',
}
BOLD_PERSON = {'name','parent','passport','address'}
BOLD_ASSET = {'nature','details','holder','relation','valuer','val_date'}

def uid(): return uuid.uuid4().hex

def money(value, positive=False):
    try:
        n=Decimal(str(value).replace(',','').replace('₹','').replace('Rs.','').strip())
        if not n.is_finite() or (positive and n <= 0): raise ValueError()
        return n.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    except (InvalidOperation,ValueError,TypeError):
        raise ValueError('Enter a finite rupee amount' + (' greater than zero.' if positive else '.'))

def norm(value):
    return re.sub(r'[^a-z0-9]','',re.sub(r'^(?:mr|mrs|ms|miss|sh|shri|smt)\.?\s+','',str(value).strip(),flags=re.I).casefold())

def literal(cell, value):
    """Excel user data is literal text, never an executable formula."""
    cell.value = str(value or '')
    cell.data_type = 's'
    return cell

SECRET_KEYS={'password','passwd','icai_pwd','icai_id','otp','totp','access_token','refresh_token','session_token','cookies','api_key','authorization','client_secret','credentials','credential','cookie','session'}
def strip_secrets(value):
    if isinstance(value,dict):return {k:strip_secrets(v) for k,v in value.items() if str(k).casefold().replace('-','_') not in SECRET_KEYS and not re.search(r'(?:^|_)(?:password|passwd|pwd|otp|totp|token|secret|cookies?)(?:$|_)',str(k).casefold().replace('-','_'))}
    if isinstance(value,list):return [strip_secrets(v) for v in value]
    return value

def asset_bold_fields(category):
    if category=='Immovable Property':return {'asset_name','nature','holder','relation','valuer','valuer_name','valuer_firm','valuer_credentials'}
    if category in ('Bank Account (Savings / Current)','Fixed Deposit'):return {'asset_name','bank','acno','holder','relation','as_on','evidence_type'}
    return {'asset_name','details','holder','relation'}

@dataclass
class Person:
    id: str = field(default_factory=uid)
    title: str = 'Mr.'
    name: str = ''
    role: str = 'Applicant'
    fields: dict = field(default_factory=lambda:{k:'' for k in PASSPORT_FIELDS})
    passports: list = field(default_factory=list)
    use_father: bool = False
    parent_override: str = ''
    relation_override: str = ''
    bold: dict = field(default_factory=lambda:{k:True for k in BOLD_PERSON})

    def parent_line(self, mode='double'):
        """Excel Sheet1 C3 logic; single's A13 condition is modeled in Case below."""
        father=self.fields.get('father_name','').strip()
        spouse=self.fields.get('spouse_name','').strip()
        if self.parent_override:
            return (self.relation_override or 'S/o')+' '+self.parent_override
        if spouse and not self.use_father:
            return 'W/o Sh. '+spouse
        # Both supplied Excel functions test Ms, not Mrs. Preserve that literal rule.
        return (('D/o Sh. ' if 'Ms' in self.title else 'S/o Sh. ')+father) if father else ''

@dataclass
class Case:
    people: list = field(default_factory=lambda:[Person()])
    items: list = field(default_factory=list)
    incomes: list = field(default_factory=list)
    documents: list = field(default_factory=list)
    relationships: list = field(default_factory=list)
    income_reviews: dict = field(default_factory=dict)
    report: dict = field(default_factory=dict)
    settings: dict = field(default_factory=dict)
    formula_mode: str = 'double'
    schema: int = 2
    app_version: str = VERSION

    @property
    def applicants(self): return [p for p in self.people if p.role=='Applicant']
    def person(self, person_id):
        return next(p for p in self.people if p.id==person_id)
    def parent_line(self,p):
        if self.formula_mode=='single' and not p.use_father and not p.parent_override:
            q=copy.deepcopy(p);q.use_father=True;return q.parent_line()
        return p.parent_line()
    def formula_warnings(self):
        warnings=[]
        for index,p in enumerate(self.applicants,1):
            line=self.parent_line(p)
            if p.title=='Mr.' and line.startswith('W/o'):
                warnings.append(f'Applicant {index}: supplied Excel spouse function produces W/o for Mr. Review the source rule or use the father override.')
            if p.title in ('Ms.','Mrs.','Miss') and line.startswith('S/o'):
                warnings.append(f'Applicant {index}: supplied Excel title test produces S/o for {p.title}. The source tests Ms, not all female titles. Review before issuing.')
        if self.report.get('currency','None') in ('', 'None'):
            try:
                from currency_rates import selected_date,IST
                chosen=selected_date(self.report);today=datetime.datetime.now(IST).date()
                if chosen>today:warnings.append('Future report/FX date: no historical rate exists yet. Any manual forecast rate is user supplied, not independently verified.')
                elif chosen<today:warnings.append('Past report/FX date: this is a historical report. Confirm the source valuation and chosen effective rate date apply to that date.')
            except ValueError:pass
        return warnings

    def add_person(self,role='Applicant'):
        p=Person(role=role);self.people.append(p);return p
    def remove_person(self,person_id):
        p=self.person(person_id)
        if p.role=='Applicant' and len(self.applicants)==1:raise ValueError('Keep at least one applicant.')
        if p.passports or any(i.get('owner_id')==person_id for i in self.items) or any(r.get('person_id')==person_id for r in self.incomes):
            raise ValueError('This person has linked evidence/assets/income. Keep their history, or start a separate case.')
        self.people.remove(p)
        self.relationships=[r for r in self.relationships if r['subject']!=person_id and r['relative']!=person_id]

    def import_passport(self, person_id, proposal, replace=False):
        p=self.person(person_id)
        if proposal.get('multiple_passports'):raise ValueError('More than one passport identity detected. Split the source by person before importing; the raw text remains available for review.')
        record={'id':uid(),'document_id':proposal.get('id'),'sha256':proposal.get('sha256'),'source':proposal.get('path',''),'fields':copy.deepcopy(proposal.get('passport_details',{})),
                'raw_text':proposal.get('original_text',proposal.get('text','')),'readable_text':proposal.get('text',''),'runtime_evidence':copy.deepcopy(proposal.get('runtime_evidence',[])),'text_repairs':copy.deepcopy(proposal.get('text_repairs',[])),'evidence':copy.deepcopy(proposal.get('evidence',{})),
                'source_bytes_base64':proposal.get('source_bytes_base64',''),'field_conflicts':copy.deepcopy(proposal.get('field_conflicts',{})),'date_candidates':copy.deepcopy(proposal.get('date_candidates',[])),'warnings':list(proposal.get('warnings',[])), 'unknown_fields':copy.deepcopy(proposal.get('unknown_fields',[]))}
        if not any(record['fields'].values()): raise ValueError('No passport fields detected. Review raw text and enter fields manually.')
        conflicts=[]
        for k,v in record['fields'].items():
            if not isinstance(v,str) or not v: continue
            if p.fields.get(k) and p.fields[k]!=v and not replace: conflicts.append(k);continue
            p.fields[k]=v
        p.passports.append(record)
        p.name=p.name or p.fields.get('full_name','')
        # Do not infer sex/title from a name; only explicit passport sex.
        if not p.name and p.fields.get('given_names'):p.name=' '.join([p.fields['given_names'],p.fields.get('surname','')]).strip()
        sex=p.fields.get('sex','').upper()
        if sex=='F' and p.title=='Mr.': p.title='Ms.'
        return conflicts
    def relationship_candidates(self):
        result=[]
        for subject in self.people:
            for relative in self.people:
                if subject.id==relative.id or not norm(relative.name):continue
                for key,relation in [('father_name','Father'),('mother_name','Mother'),('spouse_name','Spouse')]:
                    if norm(subject.fields.get(key,''))==norm(relative.name):
                        result.append({'subject':subject.id,'relative':relative.id,'relation':relation,
                                       'evidence':key+' matches exact normalized name; identity must be reviewed', 'confirmed':False})
                shared=[k for k in ('father_name','mother_name') if norm(subject.fields.get(k,'')) and norm(subject.fields.get(k,''))==norm(relative.fields.get(k,''))]
                if shared:
                    result.append({'subject':subject.id,'relative':relative.id,'relation':'Sibling',
                                   'evidence':'Shared '+', '.join(shared)+'; not proof of sibling identity', 'confirmed':False})
        return result
    def confirm_relationship(self,subject,relative,relation,evidence):
        self.person(subject);self.person(relative)
        if subject==relative or not evidence.strip(): raise ValueError('Distinct people and source evidence are required.')
        allowed={'Father','Mother','Spouse','Brother','Sister','Sibling','Son','Daughter','Other'}
        if relation not in allowed:raise ValueError('Choose an explicit reviewed relation.')
        self.relationships=[r for r in self.relationships if not(r['subject']==subject and r['relative']==relative)]
        self.relationships.append(dict(subject=subject,relative=relative,relation=relation,evidence=evidence,confirmed=True))
    def owner_relation(self,owner_id,applicant_id):
        if owner_id==applicant_id:return 'Applicant'
        return next((r['relation']+' of Applicant' for r in self.relationships if r.get('confirmed') and r['subject']==applicant_id and r['relative']==owner_id),'Co-applicant' if self.person(owner_id).role=='Applicant' else 'Relationship not confirmed')
    def report_owner_relation(self,owner_id):
        owner=self.person(owner_id);labels=[]
        for index,applicant in enumerate(self.applicants,1):
            suffix=(' '+str(index)+' ('+applicant.name+')') if len(self.applicants)>1 else ''
            if applicant.id==owner_id:
                labels.append('Applicant'+suffix);continue
            for r in self.relationships:
                if r.get('confirmed') and r['subject']==applicant.id and r['relative']==owner_id:
                    labels.append(r['relation']+' of Applicant'+suffix)
        return '; '.join(labels) if labels else ('Co-applicant' if owner.role=='Applicant' else 'Relationship not confirmed')

    def add_asset(self,category,amount,owner_id,details='',fields=None,section=None,index=None,asset_name=None):
        owner=self.person(owner_id)
        if not owner.name.strip():raise ValueError('Enter the owner’s name first.')
        if category in ('Bank Account (Savings / Current)','Fixed Deposit') and owner.role!='Applicant':
            raise ValueError('Bank assets can only be owned by an Applicant.')
        if category not in engine.CATS:raise ValueError('Choose an asset or liability type.')
        cat=engine.CATS[category];f=dict(fields or {});asset_name=(asset_name or f.get('asset_name') or category).strip()
        f['holder']=f'{owner.title} {owner.name}'.strip()
        if category in ('Bank Account (Savings / Current)','Fixed Deposit') and f.get('as_on'):
            f['as_on']=engine.format_smart_date(f['as_on'],'-')
        rel=self.report_owner_relation(owner_id) if self.applicants else 'Relationship not confirmed'
        f['relation']='Self' if rel=='Applicant' else rel
        bold={k:k in asset_bold_fields(category) for k,_,_,_ in cat.get('fields',[])}
        if details.strip():
            desc=engine.mark(asset_name,True)+' — '+details.strip()+'. '+engine.mark('Held by '+f['holder'],True)+' ('+rel+')'
            note='(As per self-declaration by the party)' if category=='Cash in Hand' else '(As per documents supplied; review valuation basis)'
            if any(f.get(k) for k in ('valuer','val_date','as_on')) and callable(cat['note']):note=cat['note'](dict(f,_bold=bold))
        else:
            if not callable(cat['desc']):raise ValueError('Enter particulars for this item.')
            gen=dict(f,_bold=bold);desc=cat['desc'](gen);note=cat['note'](gen)
        if category=='Immovable Property':
            valuer=' / '.join(x for x in (f.get('valuer_name',''),f.get('valuer_firm','')) if x) or f.get('valuer','')
            note='(Valuation report: '+(valuer or '[valuer to review]')+(', dated '+f['val_date'] if f.get('val_date') else '')+(', Ref. '+f['val_ref'] if f.get('val_ref') else '')+')'
        if f.get('_note'):note=f['_note']
        it=dict(id=uid(),asset_name=asset_name,category=category,kind=cat['kind'],section=section or cat['section'],owner_id=owner_id,
                fields=f,bold=bold,desc=desc,note=note,amount=float(money(amount,True)),details=details)
        if it['section'] not in 'ABC' or len(it['section'])!=1:raise ValueError('Invalid section.')
        if cat['kind']=='liability':it['section']='C'
        elif it['section']=='C':raise ValueError('An asset cannot be classified as a liability.')
        if index is None:self.items.append(it)
        else:
            original=self.items[index];it['id']=original['id']
            if original.get('source_evidence'):it['source_evidence']=copy.deepcopy(original['source_evidence'])
            self.items[index]=it
        return it
    def add_income(self,person_id,values,doc_type,source,year='',include=True,metadata=None,evidence=None):
        self.person(person_id)
        if doc_type not in ('ITR','Computation'): raise ValueError('Select ITR or Computation.')
        record=dict(id=uid(),person_id=person_id,values={k:float(money(v)) for k,v in values.items() if v is not None},
                    document_type=doc_type,source=source,year=year,include=bool(include and doc_type=='ITR'))
        from income_intake import canonical_year
        record['year']=canonical_year(year);record['metadata']=copy.deepcopy(metadata or {});record['evidence']=copy.deepcopy(evidence or {})
        self.incomes.append(record);return record
    @property
    def has_itr(self):return any(r['document_type']=='ITR' for r in self.incomes)
    def income_comparison(self):
        rows=[]
        for p in self.people:
            years={r.get('year','') for r in self.incomes if r['person_id']==p.id}
            for year in sorted(years):
                records=[r for r in self.incomes if r['person_id']==p.id and r.get('year','')==year]
                itr=[r for r in records if r['document_type']=='ITR'];comp=[r for r in records if r['document_type']=='Computation']
                if len(itr)!=1 or len(comp)!=1:continue
                for key in set(itr[0]['values'])|set(comp[0]['values']):
                    a=itr[0]['values'].get(key);b=comp[0]['values'].get(key)
                    status='Missing figure' if a is None or b is None else ('Matches' if money(a)==money(b) else 'Difference '+str(money(a)-money(b)))
                    rows.append((p.id,year,key,a,b,status))
        return rows
    def annual_rows(self):
        from income_intake import canonical_year
        from document_records import fingerprint
        rows=[];seen=set();selected_year=canonical_year(self.report.get('income_report_year',''))
        for r in self.incomes:
            if not r.get('include') or r['document_type']!='ITR':continue
            year=canonical_year(r.get('year',''))
            if selected_year and selected_year!=year:continue
            key=(r['person_id'],year)
            if key in seen:raise ValueError('Select only one ITR per person and assessment year for the report.')
            seen.add(key)
            if 'total_income' not in r['values']:raise ValueError('Enter/review Total income for each selected ITR.')
            review=self.income_reviews.get(r['person_id']+'|'+year)
            if review:
                present={i['id']:i for i in self.incomes}
                if any(rid not in present or fingerprint(present[rid])!=snap for rid,snap in review.get('source_fingerprints',{}).items()):raise ValueError('An income source changed or was removed. Review the paired annual-income figures again.')
                row=copy.deepcopy(r);row['source_values']=row['values'].copy();row['values']['total_income']=review['report_total'];row['reconciliation']=copy.deepcopy(review);rows.append(row)
            else:
                additional=[i for i in self.incomes if i['person_id']==r['person_id'] and canonical_year(i.get('year',''))==year and any(i['values'].get(k) for k in ('agricultural_income','exempt_income'))]
                if additional:raise ValueError('Review paired taxable / agricultural / other exempt income for this person and year before reporting; additional components are not automatically added or ignored.')
                rows.append(r)
        if len({canonical_year(r.get('year','')) for r in rows})>1:raise ValueError('Choose the Report assessment year in Tax review. Other years remain independently available for comparison.')
        return rows
    def totals(self):
        t={k:sum((money(i['amount']) for i in self.items if i['section']==k),Decimal(0)) for k in 'ABC'}
        return dict(t,net=t['A']+t['B']-t['C'])
    def to_dict(self):return strip_secrets(asdict(self))
    def save(self,path):
        from file_ops import atomic_json
        atomic_json(path,self.to_dict())
    @classmethod
    def load(cls,path):return cls.from_dict(json.loads(Path(path).read_text(encoding='utf-8')))
    @classmethod
    def from_dict(cls,d):
        d=strip_secrets(d)
        if d.get('schema') not in (None,2):raise ValueError('Unsupported case schema. Use a compatible app version.')
        if d.get('schema')==2:
            obj=cls(**{k:copy.deepcopy(v) for k,v in d.items() if k in cls.__dataclass_fields__ and k!='people'})
            obj.people=[Person(**{k:v for k,v in p.items() if k in Person.__dataclass_fields__}) for p in d['people']]
            if not obj.people:obj.people=[Person()]
            ids=[p.id for p in obj.people]
            if len(ids)!=len(set(ids)):raise ValueError('Duplicate person IDs in this case; import was not applied.')
            for item in obj.items:
                money(item['amount']);item.setdefault('id',uid())
                if item.get('owner_id') and item['owner_id'] not in ids:raise ValueError('Asset owner link is missing from this case.')
            itemids=[i['id'] for i in obj.items]
            if len(itemids)!=len(set(itemids)):raise ValueError('Duplicate asset IDs in this case; import was not applied.')
            for collection in (obj.incomes,obj.documents):
                records=[r['id'] for r in collection if r.get('id')]
                if len(records)!=len(set(records)):raise ValueError('Duplicate source/income IDs in this case.')
            if any(r.get('person_id') not in ids for r in obj.incomes):raise ValueError('Income person link is missing from this case.')
            if any(r.get('subject') not in ids or r.get('relative') not in ids for r in obj.relationships):raise ValueError('Relationship person link is missing from this case.')
            return obj
        # Backwards compatible with both uploaded apps' saved client data.
        obj=cls();a=d.get('applicant',{});obj.report=dict(a);obj.items=copy.deepcopy(d.get('items',[]))
        for prefix in ('','co_'):
            if prefix and not a.get('co_name'):continue
            p=obj.people[0] if not prefix else obj.add_person()
            p.name=a.get(prefix+'name','');p.title=a.get(prefix+'title','Mr.')
            p.fields.update(full_name=p.name,passport_number=a.get(prefix+'passport',''),address=a.get(prefix+'address',''))
            p.parent_override=a.get(prefix+'parent','');p.relation_override=a.get(prefix+'relation','')
        for it in obj.items:it.setdefault('owner_id','');it.setdefault('details','')
        for family in d.get('family_members',[]):
            p=obj.add_person('Family / owner');p.name=family.get('name','');p.fields.update(family.get('passport_fields',{}))
            # Legacy roles remain source metadata, not newly inferred relationships.
            p.fields['_legacy_role']=family.get('role','Family member')
        for rec in d.get('passport_records',[]):
            role=rec.get('role','')
            if role=='Applicant 1':target=obj.people[0]
            elif role=='Applicant 2':
                if len(obj.applicants)<2:obj.add_person()
                target=obj.applicants[1]
            else:
                name=rec.get('fields',{}).get('full_name','')
                target=next((p for p in obj.people if p.role!='Applicant' and norm(p.name)==norm(name) and name),None)
                if target is None:target=obj.add_person('Family / owner');target.name=name
                target.fields['_legacy_role']=role
            target.passports.append(copy.deepcopy(rec));target.fields.update(rec.get('fields',{}))
        for rec in d.get('income_records',[]):
            rec=copy.deepcopy(rec);rec.update(person_id=obj.people[0].id,id=uid(),include=False,year=rec.get('year',''))
            obj.incomes.append(rec)
        obj.documents=[dict(path=x,text='',legacy=True) for x in d.get('source_documents',[])]
        return obj

LABELS={
 'full_name':[r'full name',r'name of holder'], 'surname':[r'surname'], 'given_names':[r'given names?'],
 'passport_number':[r'passport\s*(?:no\.?|number)'], 'document_type':[r'type',r'document type'],
 'issuing_country':[r'country code',r'issuing country',r'code of issuing state'],
 'father_name':[r"name of father(?:\s*/\s*legal guardian)?",r"father(?:'s)? name",r'legal guardian'],
 'mother_name':[r'name of mother',r"mother(?:'s)? name"], 'spouse_name':[r'name of spouse',r"spouse(?:'s)? name",r"husband(?:'s)? name"],
 'nationality':[r'nationality'], 'sex':[r'sex',r'gender'], 'date_of_birth':[r'date of birth',r'dob'],
 'place_of_birth':[r'place of birth'], 'place_of_issue':[r'place of issue'], 'date_of_issue':[r'date of issue'],
 'date_of_expiry':[r'date of expiry',r'expiry date'], 'file_number':[r'file\s*(?:no\.?|number)'],
 'personal_number':[r'personal\s*(?:no\.?|number)'], 'old_passport_number':[r'old passport\s*(?:no\.?|number)'],
 'old_date_of_issue':[r'old (?:passport )?date of issue'], 'old_place_of_issue':[r'old (?:passport )?place of issue'],
 'emigration_status':[r'emigration status',r'ecr status',r'non-ecr status'], 'issuing_authority':[r'issuing authority',r'authority'],
 'emergency_contact':[r'emergency contact'], 'other_identifiers':[r'other identifiers'],
 'observations':[r'observations?',r'endorsements?'], 'address':[r'address',r'residential address'],
}

def parse_passport(text):
    """Label-aware, multiline parser. Unknown lines and original evidence are retained.
    No claim that OCR is infallible, and no automatic relationship confirmation.
    """
    fields={k:'' for k in PASSPORT_FIELDS};evidence={};unknown=[];conflicts={};current=None
    combined=[]
    for k,patterns in LABELS.items():
        for pat in patterns:combined.append((k,re.compile(r'^\s*(?:'+pat+r')\s*(?:[:#|\-]\s*|\s+|$)(.*)$',re.I)))
    for n,line in enumerate(text.splitlines(),1):
        line=line.strip()
        if not line:continue
        if line.upper() in ('ECR','NON-ECR','ECNR','EMIGRATION CHECK REQUIRED','EMIGRATION CHECK NOT REQUIRED'):
            fields['emigration_status']=line;evidence.setdefault('emigration_status',[]).append({'line':n,'text':line});current=None;continue
        found=False
        for key,pat in combined:
            m=pat.match(line)
            if m:
                current=key;value=m.group(1).strip(' :|\t')
                if value:
                    if fields[key] and norm(fields[key])!=norm(value) and key not in ('address','observations'):
                        conflicts.setdefault(key,[fields[key]]).append(value)
                    elif not fields[key] or key in ('address','observations'):fields[key]=(fields[key]+' '+value).strip()
                evidence.setdefault(key,[]).append({'line':n,'text':line});found=True;break
        if found:continue
        if current and (not fields[current] or current in ('address','observations')) and not line.startswith('P<'):
            fields[current]=(fields[current]+' '+line).strip();evidence.setdefault(current,[]).append({'line':n,'text':line})
            if current not in ('address','observations'):current=None
        else:unknown.append({'line':n,'text':line});current=None
    # MRZ TD3 extraction for any issuing state, with check digits verified before use.
    warnings=[]
    lines=[re.sub(r'\s','',s.upper()) for s in text.splitlines()]
    for i,line in enumerate(lines):
        if line.startswith('P<') and len(line)==44 and i+1<len(lines) and len(lines[i+1])==44:
            second=lines[i+1];fields['mrz_line_1']=line;fields['mrz_line_2']=second
            fields['issuing_country']=fields['issuing_country'] or line[2:5]
            parts=line[5:].split('<<',1)
            for key,val in [('surname',parts[0]),('given_names',parts[1] if len(parts)>1 else '')]:fields[key]=fields[key] or re.sub('<+',' ',val).strip()
            def check(s,d):
                chars='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';v=lambda c:0 if c=='<' else chars.index(c) if c in chars else -1000
                return d.isdigit() and sum(v(c)*[7,3,1][j%3] for j,c in enumerate(s))%10==int(d)
            for key,val,cd in [('passport_number',second[:9],second[9]),('date_of_birth',second[13:19],second[19]),('date_of_expiry',second[21:27],second[27])]:
                if not check(val,cd):warnings.append('MRZ check digit failed: '+key);continue
                value=val.rstrip('<')
                if key.startswith('date'):
                    yy=int(value[:2]);year=(2000+yy if key=='date_of_expiry' or yy<=datetime.date.today().year%100 else 1900+yy)
                    try:value=datetime.date(year,int(value[2:4]),int(value[4:6])).strftime('%d.%m.%Y')
                    except ValueError:warnings.append('Invalid MRZ date: '+key);continue
                    if key=='date_of_birth':warnings.append('MRZ birth century inferred; verify printed date.')
                if not fields[key]:fields[key]=value;evidence[key]=[{'line':i+2,'text':second}]
                elif norm(fields[key])!=norm(value):
                    warnings.append('Printed/MRZ conflict: '+key);conflicts.setdefault(key,[fields[key]]).append(value)
            fields['nationality']=fields['nationality'] or second[10:13].replace('<','')
            fields['sex']=fields['sex'] or second[20].replace('<','')
            fields['personal_number']=fields['personal_number'] or second[28:42].rstrip('<')
    if not fields['full_name']:fields['full_name']=' '.join(v for v in [fields['given_names'],fields['surname']] if v)
    warnings.extend('Conflicting repeated field: '+key+' — review raw evidence' for key in conflicts)
    multiple_passports=len(set(conflicts.get('passport_number',[])))>1
    if multiple_passports:warnings.append('Multiple passport identities detected: split this source by applicant before applying.')
    return {'passport_details':fields,'evidence':evidence,'unknown_fields':unknown,'text':text,'warnings':warnings,'field_conflicts':conflicts,'multiple_passports':multiple_passports}

def read_workbook(path):
    """Read all cells, not print areas. Preserve formulas alongside cached values."""
    if str(path).lower().endswith('.xls'):
        import xlrd
        book=xlrd.open_workbook(path,formatting_info=False)
        cells=[];pages=[]
        for sheet in book.sheets():
            lines=[]
            for row_index in range(sheet.nrows):
                values=[]
                for col_index in range(sheet.ncols):
                    value=sheet.cell_value(row_index,col_index)
                    if value in ('',None):continue
                    number=col_index+1;letters=''
                    while number:
                        number,remainder=divmod(number-1,26);letters=chr(65+remainder)+letters
                    address=letters+str(row_index+1)
                    cells.append({'sheet':sheet.name,'cell':address,'value':value,'formula':'','bold':False,'print_area':''})
                    values.append(str(value))
                if values:lines.append(' | '.join(values))
            pages.append('SHEET: '+sheet.name+'\n'+'\n'.join(lines))
        return pages,cells
    import openpyxl
    w=openpyxl.load_workbook(path,keep_vba=str(path).lower().endswith('.xlsm'),data_only=False)
    cached=openpyxl.load_workbook(path,data_only=True)
    cells=[];pages=[]
    try:
        for s in w:
            lines=[]
            for row in s:
                values=[]
                for c in row:
                    if c.value is None:continue
                    value=cached[s.title][c.coordinate].value if c.data_type=='f' else c.value
                    cells.append({'sheet':s.title,'cell':c.coordinate,'value':value,'formula':c.value if c.data_type=='f' else '', 'bold':bool(c.font.bold),'print_area':str(s.print_area)})
                    if value is not None:values.append(str(value))
                if values:lines.append(' | '.join(values))
            pages.append('SHEET: '+s.title+'\n'+'\n'.join(lines))
        return pages,cells
    finally:w.close();cached.close()

def read_proposal(path,kind):
    suffix=Path(path).suffix.lower();cells=[]
    if suffix in ('.xlsx','.xlsm','.xls'):pages,cells=read_workbook(path);ocr=0
    elif suffix in ('.txt','.csv'):pages=[Path(path).read_text(encoding='utf-8-sig')];ocr=0
    else:pages,ocr=engine.read_document_text(str(path),engine.find_tesseract())
    text='\n'.join(pages)
    if kind=='Passport':
        # Workbook rows often have label | value. Translate delimiters for parser.
        prop=parse_passport(text);prop.update(assets=[],income={},doc_type='Passport')
    else:
        prop=engine.extract_document_proposals(str(path),pages,'')
        if kind in ('ITR','Computation'):
            prop['doc_type']=kind;prop['income']=engine._extract_income_values(text);prop['assets']=[]
        prop.setdefault('warnings',[])
    prop.update(path=str(path),text=text,kind=kind,cells=cells,ocr_pages=ocr,page_count=len(pages))
    if cells and any(c['formula'] and c['value'] is None for c in cells):prop['warnings'].append('Some Excel formulas have no cached values. Open/recalculate/save in Excel; formulas were not executed.')
    return prop

def table_assets(cells):
    """Conservative structured-table reader and original annexure-column reader.
    Never accepts a total row as an asset. Each result still requires review.
    """
    from collections import defaultdict
    sheets=defaultdict(lambda:defaultdict(dict))
    for c in cells:
        m=re.fullmatch(r'([A-Z]+)(\d+)',c['cell'])
        if m:sheets[c['sheet']][int(m[2])][m[1]]=c['value']
    proposals=[]
    for sheet,rows in sheets.items():
        mapping={};template=sheet.lower() in ('immovable','movable','liabilities')
        for rownum,row in sorted(rows.items()):
            lower={col:str(v or '').strip().lower() for col,v in row.items()}
            if any(v in ('amount','amount (rs.)','amount (₹)','value','value (₹)','amount in inr') for v in lower.values()):
                aliases={'amount':{'amount','amount (rs.)','amount (₹)','value','value (₹)','amount in inr'},'category':{'category','type','asset type'},'details':{'description','particulars','details','asset details'},'holder':{'owner','ownership','holder'}}
                mapping={key:next((col for col,v in lower.items() if v in words),None) for key,words in aliases.items()};continue
            if mapping.get('amount'):
                raw=row.get(mapping['amount']);details=str(row.get(mapping.get('details'),'') or '')
                cat=str(row.get(mapping.get('category'),'') or '')
                if not details and not cat:continue
                if 'total' in (details+' '+cat).lower():continue
                if cat not in engine.CATS:
                    cat=next((k for k in engine.CATS if k.lower()==cat.lower()),'Other Asset')
                if cat not in engine.CATS:continue
                holder=str(row.get(mapping.get('holder'),'') or '')
            elif template:
                raw=row.get('D');details=str(row.get('B','') or '');holder=str(row.get('C','') or '')
                if not details or 'total' in details.lower():continue
                cat='Immovable Property' if sheet.lower()=='immovable' else ('Bank Loan' if sheet.lower()=='liabilities' else ('Cash in Hand' if 'cash' in details.lower() else 'Other Asset'))
                if cat not in engine.CATS:cat='Other Investment / Asset' if 'Other Investment / Asset' in engine.CATS else list(engine.CATS)[-1]
            else:continue
            try:amount=float(money(raw,True))
            except ValueError:continue
            proposals.append(dict(category=cat,amount=amount,fields={'holder':holder},desc=details,source=f'{sheet}!D{rownum}',cell_evidence={'sheet':sheet,'row':rownum}))
    return proposals

_original_read_proposal=read_proposal

def read_proposal(path,kind):
    prop=_original_read_proposal(path,kind)
    if kind=='Assets':
        if prop.get('cells'):
            structured=table_assets(prop['cells'])
            if structured:prop['assets']=structured
        elif Path(path).suffix.lower()=='.csv':
            import csv,io
            cells=[]
            for r,row in enumerate(csv.reader(io.StringIO(prop['text'])),1):
                for c,value in enumerate(row,1):
                    from openpyxl.utils import get_column_letter
                    cells.append(dict(sheet='CSV',cell=f'{get_column_letter(c)}{r}',value=value))
            structured=table_assets(cells)
            if structured:prop['assets']=structured
    return prop

# Public intake entry points use the tolerant, evidence-preserving implementation.
# The clean original parser remains available solely for validated MRZ decoding.
_canonical_passport_parser=parse_passport

def parse_passport(text):
    from document_intake import parse_passport as parse
    return parse(text)

def read_proposal(path,kind):
    from document_intake import read_proposal as read
    return read(path,kind)
