"""Reversible document detachment. Never deletes source files or applicant identities."""
import copy,hashlib,json

def fingerprint(record):
    clean={k:v for k,v in record.items() if k not in ('source_evidence','applied_fingerprint','document_id','source_document_removed')}
    return hashlib.sha256(json.dumps(clean,sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()

def link_record(record,document):
    record['document_id']=document.get('id');record['applied_fingerprint']=fingerprint(record)

def remove_document(case,document_id,remove_records=False):
    bundle=dict(documents=[],items=[],incomes=[],passports=[],detached=[],protected=0,income_reviews={})
    for index,doc in enumerate(case.documents):
        if doc.get('id')==document_id:bundle['documents'].append((index,copy.deepcopy(doc)))
    case.documents[:]=[d for d in case.documents if d.get('id')!=document_id]
    for kind,records in [('items',case.items),('incomes',case.incomes)]:
        kept=[]
        for index,record in enumerate(records):
            source=record.get('source_evidence',{}) if kind=='items' else record
            if source.get('document_id')!=document_id:kept.append(record);continue
            imported=source.get('applied_fingerprint') or record.get('applied_fingerprint')
            unchanged=bool(imported and imported==fingerprint(record))
            if remove_records and unchanged:bundle[kind].append((index,copy.deepcopy(record)));continue
            if remove_records:bundle['protected']+=1
            bundle['detached'].append((kind,record['id'],copy.deepcopy(source)))
            source.pop('document_id',None);source['source_document_removed']=True
            kept.append(record)
        records[:]=kept
    for person in case.people:
        kept=[]
        for index,record in enumerate(person.passports):
            if record.get('document_id')!=document_id:kept.append(record);continue
            if remove_records:bundle['passports'].append((person.id,index,copy.deepcopy(record)));continue
            bundle['detached'].append(('passport',record['id'],copy.deepcopy(record)))
            record.pop('document_id',None);record['source_document_removed']=True;kept.append(record)
        person.passports[:]=kept
    removed={record['id'] for _,record in bundle['incomes']}
    for key,review in list(case.income_reviews.items()):
        if removed.intersection(review.get('source_fingerprints',{})):
            bundle['income_reviews'][key]=copy.deepcopy(review);case.income_reviews.pop(key)
    return bundle

def undo_removal(case,bundle):
    for key,review in bundle.get('income_reviews',{}).items():case.income_reviews.setdefault(key,copy.deepcopy(review))
    for key in ('documents','items','incomes'):
        existing={r['id'] for r in getattr(case,key)}
        if any(r['id'] in existing for _,r in bundle[key]):raise ValueError('An identifier already exists. Cannot merge this undo safely.')
    for key in ('documents','items','incomes'):
        records=getattr(case,key)
        for index,record in bundle[key]:records.insert(min(index,len(records)),copy.deepcopy(record))
    for person_id,index,record in bundle['passports']:
        person=case.person(person_id)
        if not any(r['id']==record['id'] for r in person.passports):person.passports.insert(min(index,len(person.passports)),copy.deepcopy(record))
    for kind,record_id,original in bundle['detached']:
        records=[r for p in case.people for r in p.passports] if kind=='passport' else getattr(case,kind)
        record=next((r for r in records if r['id']==record_id),None)
        if not record:continue
        if kind=='items':record['source_evidence']=copy.deepcopy(original)
        else:
            record['document_id']=original.get('document_id');record.pop('source_document_removed',None)
