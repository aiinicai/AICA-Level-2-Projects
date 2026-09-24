from html import escape
from . import scoring, db

def make_report(record):
    a=scoring.analyse(record)
    def value(v):return f'{float(v):,.2f}' if scoring.has(v) else 'Pending'
    rows=''.join(f'<tr><td>{escape(scoring.FACTOR_NAMES[k])}</td><td>{scoring.RAW_WEIGHTS[k]/scoring.RAW_TOTAL*100:.1f}%</td><td>{value(v)}</td></tr>' for k,v in a['factors'].items())
    financials=''.join('<tr><td>'+escape(k.upper())+'</td>'+''.join('<td>'+value(v)+'</td>' for v in record.get(k,[None]*3))+'</tr>' for k in ('revenue','ebitda','pat','cfo','fcf'))
    sources=''.join('<li>'+escape(x['name'])+' — '+escape(x['at'])+'<br>'+('<a href="'+escape(x['url'],quote=True)+'">'+escape(x['url'])+'</a>' if x['url'].startswith('https://') else 'Manual input')+'</li>' for x in db.sources_for(record['id']))
    research=record.get('research') or {}
    evidence=''.join(f'<tr><td>{escape(e["metric"])}</td><td>{e["year"]}</td><td>{value(e["value"])}</td><td>{escape(e["method"])}</td></tr>' for e in research.get('evidence',[]))
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IPO Compass analysis</title><style>body{{font:15px/1.6 Arial;max-width:1100px;margin:auto;padding:24px;color:#102536}}table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #ccd6de;padding:8px;text-align:left}}h1{{color:#087d75}}.scroll{{overflow:auto}}a{{overflow-wrap:anywhere}}</style></head><body>
<h1>{escape(record['name'])}</h1><p>{escape(record.get('sector') or 'Sector pending')} · {escape(record.get('location') or 'Location pending')}</p>
<h2>{escape(a['final'])} · {value(a['score'])}/10 · Coverage {a['coverage']:.0f}%</h2>
<p>System verdict: {escape(a['auto'])}. Analyst override reason: {escape(record.get('override_reason') or 'None')}.</p>
<table><tr><th>Factor</th><th>Weight</th><th>Score /10</th></tr>{rows}</table>
<h2>Annual figures (₹ crore)</h2><div class="scroll"><table><tr><th>Metric</th>{''.join('<th>'+escape(str(y))+'</th>' for y in record['years'])}</tr>{financials}</table></div>
<p>CFO/PAT: {value(a['ratio'])}x; cumulative conversion: {value(a['cum'])}x.</p><h2>Risks and missing evidence</h2><p>{escape('; '.join(a['flags']))}</p><p>{escape(', '.join(a['missing']))}</p>
<h2>Statement evidence</h2><p>{escape(research.get('level','No statement import'))} — {escape(research.get('at',''))}</p><p>{escape(research.get('method',''))}</p><table><tr><th>Metric</th><th>FY</th><th>₹ crore</th><th>Method</th></tr>{evidence}</table>
<h2>Sources</h2><ul>{sources}</ul><p>{escape(record.get('notes') or '')}</p><p>GMP is unofficial. A provisional point score is calculated only from available inputs; it is not a prediction of listing returns. Check secondary statement figures against the prospectus.</p></body></html>'''
