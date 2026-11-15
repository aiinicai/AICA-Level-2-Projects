"""Source-grounded jewellery proposals; never turn a gold report into a plot."""
import re

def jewellery_proposals(text,path=''):
    from valuation_intake import valuation_proposals
    from document_intake import valid_date
    parsed=valuation_proposals(text,path);base=parsed['assets'][0];lines=[s.strip() for s in text.splitlines() if s.strip()]
    def labelled(pattern):
        m=re.search(pattern+r'\s*[:.-]\s*([^\n]+)',text,re.I);return m[1].strip() if m else ''
    valuer=labelled(r'(?:valued\s+by|name\s+of\s+jewell?er|jewell?er\s+name|valuer|issued\s+by)')
    if not valuer:valuer=next((l for l in lines if re.search(r'\bjewell?ers?\b',l,re.I) and not re.search(r'valuation|certificate|owner|holder',l,re.I)),'')
    date=valid_date(labelled(r'(?:valuation\s+date|date\s+of\s+valuation|as\s+on|date)'))
    weight=labelled(r'(?:net\s+weight)');purity=labelled(r'(?:purity|fineness)')
    description='; '.join(x for x in ('Gold / jewellery as described in source',('Net weight: '+weight) if weight else '',('Purity: '+purity) if purity else '') if x)
    fields=dict(details=description,holder=parsed['owner_candidate'].get('name',''),relation='Unconfirmed',valuer=valuer,val_date=date)
    if weight:fields['net_weight']=weight
    if purity:fields['purity']=purity
    item=dict(base,category='Jewellery',asset_name='Gold Valuation',fields=fields,desc='')
    parsed['assets']=[item];return parsed
