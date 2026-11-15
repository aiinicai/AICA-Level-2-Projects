"""Source-template asset wording, with optional better original-app evidence fields."""
def template_lines(item):
    f=item.get('fields',{});cat=item['category'];name=item.get('asset_name') or cat;lines=[]
    def add(value,bold=False):
        if value and not any(value==v for v,_ in lines):lines.append((str(value),bold))
    if cat=='Immovable Property':
        add(name if name!=cat else f.get('nature') or cat,True)
        if f.get('area'):add('Land Measuring: '+f['area']+'.')
        if f.get('location'):add('(Situated at '+f['location'].strip('()')+')')
        valuer=' / '.join(x for x in (f.get('valuer_name',''),f.get('valuer_firm','')) if x) or f.get('valuer','')
        add('(Valued by '+(valuer or '[valuer to review]')+')',True)
        add(f.get('valuer_credentials',''),True)
        meta=[]
        if f.get('val_date'):meta.append('Dated: '+f['val_date'])
        if f.get('val_ref'):meta.append('Ref. '+f['val_ref'])
        if meta:add('(Valuation report - '+', '.join(meta)+')')
        if f.get('deed'):add('Deed / land record: '+f['deed'])
        if f.get('tenure'):add('Tenure: '+f['tenure'])
    elif cat in ('Bank Account (Savings / Current)','Fixed Deposit'):
        if name!=cat:add(name,True)
        bank=f.get('bank','').strip();fd=' Fd' if cat=='Fixed Deposit' else ''
        label=(bank+' Bank' if bank and 'bank' not in bank.lower() else bank) or ('Fixed Deposit' if fd else 'Bank Account')
        add(label+fd+(' A/c No. '+f['acno'] if f.get('acno') else ''),True)
        if f.get('branch'):add('Branch: '+f['branch'])
        basis=f.get('evidence_type') or ('Bank Fd Certificate' if fd else 'Bank Certificate')
        add('(As Per '+basis+(' as on '+f['as_on'] if f.get('as_on') else '')+')')
    elif cat=='Jewellery':
        add(name if name!=cat else 'Gold Valuation',True)
        if f.get('details'):add(f['details'])
        if f.get('valuer'):add('(As Valued by '+f['valuer']+(' as on '+f['val_date'] if f.get('val_date') else '')+')')
        elif f.get('val_date'):add('(Valuation report as on '+f['val_date']+')')
    elif cat=='Cash in Hand':
        add(name,True);add('(As per Self Declaration by Party)')
    else:add(name,True)
    detail=item.get('details','').strip()
    # Preserve freely entered particulars, without duplicating intake's structured summary.
    auto_summary=cat=='Immovable Property' and detail.startswith(name) and ('; Area:' in detail or ' at ' in detail or '; Deed:' in detail)
    if detail and detail!=name and not auto_summary and not any(detail in text for text,_ in lines):add(detail)
    if cat not in ('Immovable Property','Bank Account (Savings / Current)','Fixed Deposit','Jewellery','Cash in Hand'):
        import legacy_engine as engine
        generated=engine.strip_marks(item.get('desc',''))
        if generated and generated!=name:add(generated)
        if item.get('note'):add(engine.strip_marks(item['note']))
    if f.get('_note'):add(f['_note'])
    return lines
