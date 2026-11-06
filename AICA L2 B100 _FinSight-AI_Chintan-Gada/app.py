import hashlib,io,os
import pandas as pd
import plotly.express as px
import streamlit as st
from finsight.engine import load_excel,calculate,risks,anomaly_table,facts
from finsight.advisor import generate
from finsight.reporting import excel_report,pdf_report
from finsight import workflow

st.set_page_config(page_title='FinSight AI | ICAI Capstone',page_icon='📈',layout='wide')
st.title('📈 FinSight AI')
st.caption('Intelligent Financial Statement Analysis & CFO Advisory | ICAI AI Level 2 capstone')
with st.sidebar:
    st.header('Project settings')
    company=st.text_input('Company','ABC Manufacturing Private Limited')
    unit=st.selectbox('Amounts in',['₹ crore','₹ lakh','₹','USD million','Other consistent unit'])
    st.info('No financial file is transmitted to an LLM. Optional AI receives only calculated summary facts. An API call still transmits those summary facts.')
    use_ai=st.toggle('Use OpenAI commentary',value=False)
    model=st.text_input('OpenAI model',value='gpt-4.1-mini',disabled=not use_ai)
    st.caption('Set OPENAI_API_KEY as a Windows environment variable to enable AI.')
    st.download_button('Download example workbook',data=open('sample_data/sample_financials.xlsx','rb').read(),file_name='sample_financials.xlsx')

uploaded=st.file_uploader('Upload financial statements (.xlsx) — sheet Financials',type=['xlsx'])
if uploaded is None:
    st.info('Download the sample workbook, then upload it to begin the workflow.')
    st.stop()
raw=uploaded.getvalue(); key=hashlib.sha256(raw+company.encode()+unit.encode()).hexdigest()[:16]
if st.session_state.get('run_key')!=key:
    st.session_state.update(run_key=key,advisory=None,advisory_source=None)
    try: workflow.create(key,company)
    except Exception: pass
try:
    df=load_excel(io.BytesIO(raw)); metrics,issues=calculate(df)
except Exception as e:
    st.error(f'Input validation failed: {e}')
    st.stop()
status=workflow.get(key)[2]
if status=='DRAFT' and not issues:
    workflow.transition(key,'VALIDATED');workflow.transition(key,'ANALYSED');workflow.transition(key,'PENDING_REVIEW');status='PENDING_REVIEW'
if issues:
    st.error('Validation issues must be resolved before report approval.')
    for i in issues: st.write('•',i)
    st.stop()
flags=risks(metrics); anomalies=anomaly_table(metrics)
st.success('Financial statement checks passed. Workflow status: '+status)
last=metrics.columns[-1]; prior=metrics.columns[-2]
tabs=st.tabs(['📊 Dashboard','⚠️ Risk & Anomalies','🤖 AI Advisory','✅ Review & Export','📋 Source Data'])
with tabs[0]:
    cols=st.columns(4)
    for c,k,fmt in zip(cols,['Revenue','PAT','Current ratio','EBITDA margin %'],['{:.2f}','{:.2f}','{:.2f}x','{:.2f}%']):
        c.metric(k,fmt.format(metrics.loc[k,last]))
    trend=metrics.loc[['Revenue','EBITDA','PAT','Operating cash flow']].T.reset_index().rename(columns={'index':'Period'})
    st.plotly_chart(px.line(trend,x='Period',y=['Revenue','EBITDA','PAT','Operating cash flow'],markers=True,title=f'Performance trend ({unit})'),use_container_width=True)
    st.subheader('Financial ratios and indicators')
    st.dataframe(metrics.style.format('{:,.2f}',na_rep='N/A'),use_container_width=True)
with tabs[1]:
    st.subheader('Risk rules')
    if flags:
        for f in flags: st.warning(f'**{f["severity"]} — {f["code"]}:** {f["evidence"]}\n\nAction: {f["recommendation"]}')
    else: st.success('No configured rules triggered. This does not imply zero risk.')
    st.subheader('Material period-over-period changes (absolute ≥25%)')
    st.dataframe(anomalies,use_container_width=True)
    st.caption('The standard capstone uses explainable rules, not an untrained predictive ML model.')
with tabs[2]:
    st.subheader('CFO commentary generator')
    st.caption('Deterministic financial metrics are supplied as evidence. AI drafting is optional and requires an API key.')
    if st.button('Generate advisory draft',type='primary'):
        try:
            advisory,source=generate(facts(metrics,flags),use_ai,model)
            st.session_state.advisory=advisory;st.session_state.advisory_source=source
        except Exception as e: st.error(f'Advisory generation failed: {e}')
    if st.session_state.advisory:
        st.caption(st.session_state.advisory_source)
        st.text_area('Editable advisory',key='advisory',height=360)
        st.info('All generated commentary must be checked against source figures before approval.')
with tabs[3]:
    st.subheader('Professional review and export')
    status=workflow.get(key)[2]
    reviewer=st.text_input('Reviewer name')
    notes=st.text_area('Review notes')
    if not st.session_state.advisory: st.warning('Generate an advisory draft before approving the report.')
    if status=='REJECTED' and st.button('Resubmit for review'):
        workflow.transition(key,'PENDING_REVIEW',reviewer,notes);st.rerun()
    if status=='PENDING_REVIEW':
        a,b=st.columns(2)
        if a.button('Approve report',disabled=not (reviewer.strip() and st.session_state.advisory)):
            workflow.transition(key,'APPROVED',reviewer,notes);st.rerun()
        if b.button('Reject report'):
            workflow.transition(key,'REJECTED',reviewer,notes);st.rerun()
    st.write('Current status:',status)
    if status=='APPROVED':
        st.download_button('Download CFO report (PDF)',pdf_report(company,unit,metrics,flags,issues,st.session_state.advisory,'APPROVED'),file_name='FinSight_CFO_Report.pdf',mime='application/pdf')
        st.download_button('Download financial analysis (Excel)',excel_report(metrics,flags,issues,anomalies),file_name='FinSight_Analysis.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else: st.info('Exports unlock after approval. Review is recorded in the local SQLite workflow log.')
with tabs[4]:
    st.dataframe(df,use_container_width=True)
    st.write('Periods:',', '.join(df.columns))
    st.caption('Data is processed in the application process. Workflow records are stored locally under ~/.finsight_ai/workflow.db.')
