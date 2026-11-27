from stamp74 import stamp_rows
import streamlit as st
import requests, io
from panindia import STATES, PORTALS, DEFAULTS, search, load, save, fetch, pdftext, evidence
from bs4 import BeautifulSoup
from engine import finance, official, validate
from answer68 import rank as evidence, structured
from answer72 import capital_rows, checked_quote
from multi64 import TYPES, research_link, combined
st.set_page_config(page_title="IncentiveIQ India V7.4 Pan India",layout="wide")
st.title("IncentiveIQ India | ICAI AI demo V7.4 Pan India")
st.caption("Official source retrieval • Local AI • Human verification required")
state=st.selectbox("State / Union Territory",STATES,index=STATES.index("Uttar Pradesh"))
if "state_docs" not in st.session_state: st.session_state.state_docs={}
if state not in st.session_state.state_docs: st.session_state.state_docs[state]=load(state)
docs=st.session_state.state_docs[state]
a,b,c,d=st.tabs(["Live research","Ask AI","Business case","Compare states"])
with a:
    topic=st.text_input("Policy search keywords","industrial investment incentive policy")
    st.markdown("[Search government policy documents]("+search(state,topic)+")")
    st.caption("Directory search domain: "+PORTALS[state]+". Verify policy dates and official results; directory domains are not verified live.")
    with st.expander("Find related policy documents — multi-document research", expanded=True):
        for kind in TYPES:
            st.markdown(f"[{kind}]({research_link(state,kind,topic)})")
        st.caption("Open relevant official results and paste each URL below, one per line. Verify dates, scope and amendments; discovery is browser-assisted.")
    urls=st.text_area("Official policy URLs (one per line)","\n".join(DEFAULTS.get(state,[])),key="urls_"+state)
    st.caption("Maharashtra 2019 link is historical, not confirmed current. For other states use government search to find policy URLs.")
    from ocr66 import executable, languages
    enable_ocr=st.checkbox("Automatic OCR for scanned pages",value=True)
    try: langs=languages()
    except Exception: langs=[]
    st.caption("Tesseract: "+("Detected" if executable() else "Not installed — see OCR_SETUP.txt"))
    selected=st.multiselect("OCR languages (installed)",langs,default=["eng"] if "eng" in langs else langs[:1])
    limit=st.number_input("Maximum OCR pages per document",1,250,30)
    status=st.empty()
    opts=dict(ocr=enable_ocr,lang="+".join(selected) or "eng",limit=limit,progress=lambda i,n:status.info(f"Reading PDF page {i}/{n} — scanned pages may take longer"))
    if st.button("Fetch live sources"):
        for url in dict.fromkeys(urls.splitlines()):
            if not url.strip(): continue
            try:
                src,body=fetch(url.strip(), **opts); docs[src]=body; save(state,docs); st.success(f"{src}: {len(body)} characters")
            except Exception as e: st.error(f"{e}. Try another official URL or download using your browser and upload below. Do not bypass certificate warnings.")
    uploads=st.file_uploader("Upload downloaded policy PDFs (20 MB processing limit)",type=["pdf"],accept_multiple_files=True,key="pdf_"+state)
    if st.button("Import PDFs"):
        for f in uploads or []:
            try:
                body=pdftext(f.getvalue(), **opts); docs["Uploaded PDF (unverified provenance): "+f.name]=body; save(state,docs); st.success(f"Imported {f.name}: {len(body)} characters")
            except Exception as e: st.error(str(e))
    if st.button("Clear captured sources for this state"):
        docs.clear(); save(state,docs)
    st.write(f"Research library: {len(docs)} captured documents for {state}")
    for src,body in docs.items():
        with st.expander(f"{src} | {len(body)} characters"): st.text(body[:20000])
with b:
    model=st.text_input("Local Ollama model","qwen2.5:1.5b")
    q=st.text_area("Question (English recommended)","What percentage of stamp duty exemption is available in Gautam Buddha Nagar and Ghaziabad?")
    mode=st.radio("Answer mode",["Smart answer (fast)","Evidence only (fast)","Local AI + evidence"])
    if mode=="Local AI + evidence":
        from local73 import status, select_answer
        if st.button("Check Ollama connection"):
            try:
                installed,names=status(model)
                if installed: st.success("Ollama connected — selected model installed")
                else: st.warning("Ollama connected, model not found: "+", ".join(names))
            except Exception as e: st.error(f"Ollama connection failed: {e}")
        ai_timeout=st.number_input("AI timeout (seconds)",30,600,180,30)
    if st.button("Find answer"):
        result,hits=combined(docs,q,state)
        diagnostics=[]
        stamp=stamp_rows(docs,q,state)
        if stamp:
            hits=[(3000,r["source"],r["excerpt"]) for r in stamp]+hits
        capital=capital_rows(docs,q,state,diagnostics)
        table_rows=structured(docs,q)
        if capital:
            hits=[(2000,r["source"],r["excerpt"]) for r in capital]+hits
            hits=list(dict.fromkeys(hits))
        if table_rows:
            hits=[(1000,r["source"],r["excerpt"]) for r in table_rows]+[h for h in hits if h[2] not in {r["excerpt"] for r in table_rows}]
        if any("[OCR transcription" in v or "[Coverage warning:" in v for v in docs.values()):
            st.warning("Library includes OCR or incomplete documents. Verify rates and clauses against original PDF images before relying on answers.")
        st.caption(f"Searched {len(docs)} captured documents. Evidence is ranked across sources; applicability and amendment precedence require review.")
        if not hits: st.warning("No matching evidence. Fetch official sources first or use more specific English keywords.")
        else:
            if mode != "Evidence only (fast)":
                # Result computed across all captured documents above.
                if stamp:
                    st.subheader("Stamp duty benefits — source clauses")
                    st.dataframe([{"Eligibility / scope":r["scope"],"Rate":r["rate"],"Benefit":r["kind"],"Policy year (URL hint)":r["year"],"PDF page":r["page"],"Source":r["source"]} for r in stamp],use_container_width=True)
                    st.warning("Partial, scope-specific extracts only. Not a universal manufacturing entitlement. Read full conditions and exclusions below; OCR is provisional and historical policies require current verification.")
                elif capital:
                    st.subheader("Base capital subsidy — source table")
                    st.dataframe([{"Region":r["region"],"Industry":r["size"],"Rate":r["rate"],"Basis":r["basis"],"Years":r["years"],"Page":r["page"],"Source":r["source"]} for r in capital],use_container_width=True)
                    st.warning("Base subsidy only; verify original table, policy year, eligibility, ceilings, amendments and any capacity utilisation adjustment. OCR values are provisional.")
                elif table_rows:
                    st.subheader("Combined incentive ceilings — source based")
                    st.dataframe([{"Industry category":r["size"].title(),"Sector":r["sector"].title(),"Category A":r["a"]+"%","Category B":r["b"]+"%","Basis":r["basis"],"Years":r["years"],"PDF page":r["page"],"Source":r["source"]} for r in table_rows],use_container_width=True)
                    st.warning("These are combined ceilings, not standalone capital subsidy rates. OCR values are provisional; verify original pages, project eligibility and effective dates.")
                    if not __import__("re").search(r"combined|ceiling",q,__import__("re").I): st.info("Partial answer: individual subsidy rates are not established by this table.")
                elif result:
                    st.subheader("Smart answer — source based")
                    st.write(result[1])
                    st.text(result[2])
                    st.markdown(f"[Official source]({result[0]})")
                    st.caption("Other document excerpts below provide context; they do not establish that the rate applies to every project.")
                    st.warning("Check eligibility, ceilings and amendments before relying on this answer.")
                else:
                    st.subheader("Relevant policy evidence")
                    st.info("No unambiguous structured rate found. Review the ranked source excerpts below; no rate has been inferred.")
                    if diagnostics:
                        with st.expander("Capital subsidy extraction diagnostics"):
                            for message in diagnostics: st.write(message)
            if mode=="Local AI + evidence":
                st.subheader("Local AI — evidence selection")
                try:
                    installed,names=status(model)
                    if not installed: st.warning("Ollama connected, but selected model is not installed.")
                    else:
                        st.success("Ollama connected — "+model)
                        with st.spinner("Local AI selecting relevant evidence..."):
                            idx,excerpt,elapsed,raw=select_answer(model,q,hits,ai_timeout)
                        st.caption(f"AI response received in {elapsed:.1f} seconds")
                        if idx is not None:
                            st.write(f"AI selected Evidence [{idx}]")
                            st.text(excerpt)
                            st.caption("Original source text, not an AI paraphrase. Selection relevance and eligibility require human review.")
                        else: st.warning("AI selection rejected: no valid evidence index or exact quote. Use the source-based answer above.")
                        with st.expander("Local AI diagnostics — raw model output (unverified)"):
                            st.text(raw)
                except Exception as e: st.warning(f"Local AI unavailable: {e}. Source-based answer remains available.")
            for i,(_,url,part) in enumerate(hits,1):
                if official(url):
                    st.markdown(f"**Evidence [{i}]** — [Official source]({url})")
                else:
                    st.write(f"Evidence [{i}] — {url}")
                import re
                page = re.match(r"\[Page (\d+)\]",part)
                if page:
                    st.caption(f"PDF page {page.group(1)} (file page, not printed numbering)")
                st.text(part)

with c:
    st.warning("Illustrative assumptions only; not verified scheme entitlement.")
    cap=st.number_input("CAPEX (₹ crore)",min_value=0.01,value=100.0)
    op=st.number_input("Annual operating cash flow (₹ crore)",value=18.0)
    inc=st.number_input("Annual incentive receipts (₹ crore)",min_value=0.0,value=9.6)
    years=st.number_input("Years",min_value=1,max_value=50,value=5)
    rate=st.number_input("Discount rate %",min_value=0.0,value=10.0)
    from finance70 import project
    import pandas as pd
    delay=st.number_input("Incentive delay (whole years)",0,50,0)
    duration=st.number_input("Incentive receipt duration (years)",0,50,int(years))
    f=project(cap,op,inc,years,rate,delay,duration)
    l,m,n=st.columns(3)
    l.metric("NPV without incentives (₹ Cr)",f"{f['npv_base']:.2f}")
    m.metric("NPV with incentives (₹ Cr)",f"{f['npv']:.2f}",f"{f['npv']-f['npv_base']:.2f}")
    def fmt(v,suffix=''): return 'Not achieved / undefined' if v is None else f'{v:.2f}{suffix}'
    n.metric("Simple payback (years)",fmt(f['payback']))
    l,m,n=st.columns(3)
    l.metric("Project IRR",fmt(f['irr'],'%'))
    m.metric("Undiscounted project ROI",fmt(f['roi'],'%'))
    n.metric("Discounted payback (years)",fmt(f['discounted_payback']))
    st.caption("Year-end discounting; payback interpolates within a year. IRR is reported only for conventional cash flows. No terminal value or tax adjustments unless included in inputs.")
    cash=pd.DataFrame({'Year':range(years+1),'Without incentives':f['base'],'Incentives':f['benefit'],'With incentives':f['total'],'Discounted cash flow':f['discounted']})
    cash['Cumulative cash flow']=cash['With incentives'].cumsum()
    st.subheader('Year-wise cash flow (₹ crore)'); st.dataframe(cash,use_container_width=True)
    st.line_chart(cash.set_index('Year')[['Without incentives','With incentives','Cumulative cash flow']])
    st.subheader('NPV sensitivity (₹ crore)')
    rates=sorted(set([max(0,rate-2),rate,rate+2,rate+4]))
    st.dataframe(pd.DataFrame([{'Discount rate %':r,**{f'Delay {d} years':round(project(cap,op,inc,years,r,d,duration)['npv'],2) for d in sorted(set([0,delay,delay+1,delay+2]))}} for r in rates]),use_container_width=True)
    st.download_button('Download cash flow CSV',cash.to_csv(index=False),'cash_flow.csv')

with d:
    chosen=st.multiselect("States to compare",STATES,default=["Uttar Pradesh","Maharashtra","Gujarat"])
    from comparison70 import TOPICS, rows_for
    topic=st.selectbox("Comparison topic",list(TOPICS))
    rows=[]
    for s in chosen:
        rows.extend(rows_for(s,st.session_state.state_docs.get(s,load(s)),topic))
    import pandas as pd
    frame=pd.DataFrame(rows)
    st.dataframe(frame,use_container_width=True)
    st.warning("Rates are candidate source extracts, not verified entitlements. Different schemes, regions and dates may not be comparable. Blank ceilings and periods are not established. Maharashtra 2019 is historical.")
    for i,r in enumerate(rows):
        with st.expander(f"{r['State']} | {r['Rate'] or 'Insufficient evidence'} | {r['PDF page']}"):
            st.text(r['Evidence'])
            if official(r['Source']): st.markdown(f"[Official source]({r['Source']})")
    if rows:
        st.download_button("Download comparison CSV",frame.to_csv(index=False).encode('utf-8-sig'),"comparison.csv")
        buffer=io.BytesIO()
        with pd.ExcelWriter(buffer,engine="openpyxl") as writer:
            summary=frame[['State','Incentive','Rate','Basis','Eligibility / scope','Status']]
            summary.to_excel(writer,index=False,sheet_name='Executive Summary')
            frame.drop(columns=['Evidence']).to_excel(writer,index=False,sheet_name='Detailed Comparison')
            frame[['State','Incentive','PDF page','Source','Evidence']].to_excel(writer,index=False,sheet_name='Source Evidence')
            from openpyxl.styles import Font, PatternFill, Alignment
            for ws in writer.sheets.values():
                ws.freeze_panes='B2'; ws.auto_filter.ref=ws.dimensions
                for cell in ws[1]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='203864')
                for col in ws.columns:
                    ws.column_dimensions[col[0].column_letter].width=65 if col[0].value in ('Evidence','Source') else 38 if col[0].value in ('Eligibility / scope','Status') else 22
                    for cell in col[1:]:
                        if isinstance(cell.value,str): cell.data_type='s'
                        cell.alignment=Alignment(wrap_text=True,vertical='top')
                        if col[0].value=='Status': cell.fill=PatternFill('solid',fgColor='FFF2CC' if any(x in str(cell.value).lower() for x in ('insufficient','candidate','ocr','historical')) else 'E2F0D9')
                for i in range(2,ws.max_row+1): ws.row_dimensions[i].height=105 if ws.title=='Source Evidence' else 55
        st.download_button("Download comparison Excel",buffer.getvalue(),"comparison.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
