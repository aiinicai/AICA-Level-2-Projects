from pathlib import Path
import io
import pytest
import pandas as pd
from finsight.engine import load_excel,calculate,risks,anomaly_table
from finsight.advisor import generate
from finsight.reporting import pdf_report,excel_report

def sample():
    return load_excel(Path(__file__).resolve().parents[1]/'sample_data'/'sample_financials.xlsx')

def test_sample_balances_and_ratios():
    m,issues=calculate(sample())
    assert issues==[]
    assert m.loc['Revenue','FY26']==pytest.approx(127.98)
    assert m.loc['Current ratio','FY26']==pytest.approx(1.48)
    assert m.loc['EBITDA','FY26']==pytest.approx(20.73)
    assert m.loc['PAT','FY26']==pytest.approx(12.03)

def test_cash_flow_risk():
    m,_=calculate(sample())
    assert 'Profit/cash divergence' in [x['code'] for x in risks(m)]

def test_mismatch_detection():
    df=sample();df.loc['equity','FY26']+=1
    _,issues=calculate(df)
    assert any('mismatch' in x.lower() for x in issues)

def test_exports():
    m,issues=calculate(sample());f=risks(m)
    assert pdf_report('ABC','INR crore',m,f,issues,'Reviewed draft','APPROVED').startswith(b'%PDF')
    assert excel_report(m,f,issues,anomaly_table(m)).startswith(b'PK')

def test_offline_advisor():
    from finsight.engine import facts
    m,_=calculate(sample());s,source=generate(facts(m,risks(m)))
    assert 'OPERATING' in s.upper() and 'DETERMINISTIC' in source.upper()

def test_duplicate_metric_rejected():
    data=sample().reset_index().rename(columns={'index':'metric'})
    data=pd.concat([data,data.iloc[:1]],ignore_index=True)
    out=io.BytesIO()
    with pd.ExcelWriter(out) as writer: data.to_excel(writer,sheet_name='Financials',index=False)
    out.seek(0)
    with pytest.raises(ValueError,match='Duplicate'):load_excel(out)
