"""Deterministic financial analytics; monetary amounts are in a consistent user-selected unit."""
from __future__ import annotations
import math
import pandas as pd

REQUIRED = ['revenue','cogs','operating_expenses','depreciation','interest','tax','current_assets','inventory','prepayments','cash','receivables','noncurrent_assets','current_liabilities','payables','short_term_debt','long_term_debt','equity','cfo','capex']
OPTIONAL = ['credit_sales','credit_purchases','opening_receivables','opening_inventory','opening_payables']
LABELS = {x:x.replace('_',' ').title() for x in REQUIRED+OPTIONAL}

def load_excel(source):
    df = pd.read_excel(source, sheet_name='Financials', engine='openpyxl')
    if 'metric' not in df.columns: raise ValueError("Sheet 'Financials' must contain a 'metric' column")
    df['metric'] = df['metric'].astype(str).str.strip().str.lower().str.replace(' ','_',regex=False)
    if df['metric'].duplicated().any(): raise ValueError('Duplicate metric names: '+', '.join(df.loc[df['metric'].duplicated(),'metric']))
    missing = set(REQUIRED)-set(df.metric)
    if missing: raise ValueError('Missing required metrics: '+', '.join(sorted(missing)))
    years = [str(c) for c in df.columns if str(c)!='metric']
    if len(years)<2: raise ValueError('At least two financial periods are required')
    if len(set(years))!=len(years): raise ValueError('Duplicate period labels')
    for y in years:
        df[y] = pd.to_numeric(df[y], errors='coerce')
        if df.loc[df.metric.isin(REQUIRED),y].isna().any():
            bad = df.loc[df.metric.isin(REQUIRED)&df[y].isna(),'metric'].tolist()
            raise ValueError(f'Non-numeric or missing amounts in {y}: {bad}')
        if not df[y].map(lambda v: pd.isna(v) or math.isfinite(float(v))).all():
            raise ValueError(f'Non-finite values in {y}')
    return df.set_index('metric')[years].astype(float)

def div(n,d): return None if d is None or abs(d)<1e-12 else n/d

def calculate(df):
    result={}; issues=[]; years=list(df.columns)
    for ix,y in enumerate(years):
        g=lambda k: float(df.loc[k,y]) if k in df.index and pd.notna(df.loc[k,y]) else None
        rev,cogs,opex,dep,interest,tax=[g(x) for x in ['revenue','cogs','operating_expenses','depreciation','interest','tax']]
        gp=rev-cogs; ebitda=gp-opex; ebit=ebitda-dep; pbt=ebit-interest; pat=pbt-tax
        ca,inv,prep,cash,rec,na,cl,pay,sd,ld,eq,cfo,capex=[g(x) for x in ['current_assets','inventory','prepayments','cash','receivables','noncurrent_assets','current_liabilities','payables','short_term_debt','long_term_debt','equity','cfo','capex']]
        debt=sd+ld
        assets=ca+na; liabilities=cl+ld
        if abs(assets-liabilities-eq)>0.01: issues.append(f'{y}: Balance sheet mismatch (Assets {assets:.2f} vs Liabilities + Equity {liabilities+eq:.2f}).')
        if inv+prep+cash+rec>ca+0.01: issues.append(f'{y}: Listed current asset components exceed total current assets.')
        if sd+pay>cl+0.01: issues.append(f'{y}: Listed current liability components exceed total current liabilities.')
        if any(g(k)<0 for k in ['revenue','cogs','depreciation','interest','inventory','current_assets','current_liabilities','noncurrent_assets']): issues.append(f'{y}: Unexpected negative amount in a nonnegative financial field.')
        prev=lambda k: float(df.loc[k,years[ix-1]]) if ix and k in df.index and pd.notna(df.loc[k,years[ix-1]]) else None
        avg=lambda k: ((prev(k)+g(k))/2) if prev(k) is not None else None
        credit_sales=g('credit_sales') or rev
        credit_purchases=g('credit_purchases')
        ar_avg=avg('receivables') if avg('receivables') is not None else g('opening_receivables')
        inv_avg=avg('inventory') if avg('inventory') is not None else g('opening_inventory')
        pay_avg=avg('payables') if avg('payables') is not None else g('opening_payables')
        dso=div(ar_avg*365,credit_sales) if ar_avg is not None else None
        dio=div(inv_avg*365,cogs) if inv_avg is not None else None
        dpo=div(pay_avg*365,credit_purchases or cogs) if pay_avg is not None else None
        result[y]={
          'Revenue':rev,'Gross profit':gp,'EBITDA':ebitda,'EBIT':ebit,'PBT':pbt,'PAT':pat,
          'Gross margin %':div(gp*100,rev),'EBITDA margin %':div(ebitda*100,rev),'Net margin %':div(pat*100,rev),
          'Revenue growth %':div((rev-prev('revenue'))*100,prev('revenue')) if prev('revenue') is not None else None,
          'PAT growth %':div((pat-(prev('revenue')-prev('cogs')-prev('operating_expenses')-prev('depreciation')-prev('interest')-prev('tax')))*100,(prev('revenue')-prev('cogs')-prev('operating_expenses')-prev('depreciation')-prev('interest')-prev('tax'))) if ix else None,
          'Current ratio':div(ca,cl),'Quick ratio':div(ca-inv-prep,cl),'Working capital':ca-cl,
          'Debt / Equity':div(debt,eq),'Interest coverage':div(ebit,interest),'Net debt / EBITDA':div(debt-cash,ebitda),
          'ROE %':div(pat*100, (eq+prev('equity'))/2) if ix else None,
          'ROCE %':div(ebit*100,((eq+debt)+(prev('equity')+prev('short_term_debt')+prev('long_term_debt')))/2) if ix else None,
          'Receivable days':dso,'Inventory days':dio,'Payable days':dpo,
          'Cash conversion cycle':dso+dio-dpo if None not in (dso,dio,dpo) else None,
          'Operating cash flow':cfo,'Free cash flow':cfo-capex,'CFO / PAT':div(cfo,pat),'CFO / Debt':div(cfo,debt),
          'Capex / Revenue %':div(capex*100,rev),'Total assets':assets,'Total debt':debt,'Equity':eq
        }
    return pd.DataFrame(result),issues

def risks(metrics):
    years=list(metrics.columns); current=years[-1]; prior=years[-2]; flags=[]
    def flag(severity,code,evidence,recommendation): flags.append(dict(severity=severity,code=code,evidence=evidence,recommendation=recommendation))
    def v(key,y=current): return metrics.loc[key,y]
    if v('Current ratio') is not None and v('Current ratio')<1.2: flag('High','Liquidity pressure',f'Current ratio {v("Current ratio"):.2f}x','Review near-term liabilities and liquidity buffers.')
    if v('Interest coverage') is not None and v('Interest coverage')<2: flag('High','Low interest cover',f'Interest coverage {v("Interest coverage"):.2f}x','Review financing costs and debt servicing headroom.')
    if v('Revenue')>v('Revenue',prior) and v('Operating cash flow')<v('Operating cash flow',prior): flag('High','Profit/cash divergence',f'Revenue {v("Revenue",prior):.2f} → {v("Revenue"):.2f}; CFO {v("Operating cash flow",prior):.2f} → {v("Operating cash flow"):.2f}','Reconcile profits to cash and review working capital movements.')
    if v('Debt / Equity') is not None and v('Debt / Equity')>1.5: flag('Moderate','High leverage',f'Debt/equity {v("Debt / Equity"):.2f}x','Review capital structure and debt covenants.')
    if v('EBITDA margin %')<v('EBITDA margin %',prior)-2: flag('Moderate','Margin deterioration',f'EBITDA margin {v("EBITDA margin %",prior):.1f}% → {v("EBITDA margin %"):.1f}%','Investigate pricing and cost movements.')
    if v('Receivable days') is not None and v('Receivable days',prior) is not None and v('Receivable days')>v('Receivable days',prior)+15: flag('Moderate','Receivable ageing',f'DSO {v("Receivable days",prior):.1f} → {v("Receivable days"):.1f} days','Inspect customer ageing and credit terms.')
    if v('Free cash flow')<0: flag('Moderate','Negative free cash flow',f'FCF {v("Free cash flow"):.2f}','Review capital spending and financing plans.')
    return flags

def anomaly_table(metrics):
    rows=[]; years=list(metrics.columns)
    for k in ['Revenue','EBITDA','PAT','Operating cash flow','Working capital','Total debt']:
        for a,b in zip(years[:-1],years[1:]):
            before,after=metrics.loc[k,a],metrics.loc[k,b]
            change=div((after-before)*100,abs(before))
            if change is not None and abs(change)>=25:
                rows.append({'Metric':k,'From':a,'To':b,'Change %':round(change,2),'Method':'Rule-based threshold (25%)'})
    return pd.DataFrame(rows,columns=['Metric','From','To','Change %','Method'])

def facts(metrics,flags):
    years=list(metrics.columns); keep=['Revenue','Revenue growth %','EBITDA','EBITDA margin %','PAT','Current ratio','Debt / Equity','Interest coverage','Operating cash flow','Free cash flow','Receivable days']
    return {'periods':years,'metrics':{y:{k:(round(float(metrics.loc[k,y]),3) if pd.notna(metrics.loc[k,y]) else None) for k in keep} for y in years},'risk_flags':flags}
