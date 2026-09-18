
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import calendar, io

st.set_page_config(page_title="Statutory Compliance Tracker", page_icon="📅", layout="wide")

st.markdown("""
<style>
.stApp{background:#F8FAFC}
.block-container{padding-top:1rem}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid #E2E8F0}
.top{background:#fff;border:1px solid #E2E8F0;border-radius:16px;padding:.8rem 1rem;
display:flex;justify-content:space-between;align-items:center}
.brand{font-weight:800;font-size:1.25rem;color:#0F172A}
.attr{background:#0F172A;color:#fff;border-radius:999px;padding:.45rem .8rem;font-size:.8rem;font-weight:700}
.card{background:#fff;border:1px solid #E2E8F0;border-radius:15px;padding:1rem;margin:.55rem 0}
.critical{background:#FFFBEB;border-color:#F59E0B}
.small{font-size:.82rem;color:#64748B}
.metric{background:#fff;border:1px solid #E2E8F0;border-radius:15px;padding:1rem}
.num{font-size:2rem;font-weight:800;color:#0F172A}
</style>
<div class="top"><div class="brand">Statutory Compliance Tracker</div>
<div class="attr">Engineered via RRRR App Builder</div></div>
""", unsafe_allow_html=True)

YEAR = 2026
TODAY = date.today()

PERSONS = ["Individual","HUF","Partnership Firm","LLP","Private Limited Company",
           "Public Limited Company","Trust/AOP"]
LAWS = ["Income Tax Act","GST Act","Companies Act","LLP Act"]
STREAMS = ["Business & Profession","Salary","Capital Gains","House Property",
           "Online/E-commerce Sales","Cross-Border/Export"]

GROUP_A = {"Chhattisgarh","Madhya Pradesh","Gujarat","Maharashtra","Karnataka","Goa",
"Kerala","Tamil Nadu","Telangana","Andhra Pradesh","Puducherry","Andaman and Nicobar Islands","Lakshadweep"}
GROUP_B = {"Himachal Pradesh","Punjab","Uttarakhand","Haryana","Rajasthan","Uttar Pradesh",
"Bihar","Sikkim","Arunachal Pradesh","Nagaland","Manipur","Mizoram","Tripura","Meghalaya",
"Assam","West Bengal","Jharkhand","Odisha","Jammu and Kashmir","Ladakh","Chandigarh","Delhi"}
STATES = sorted(GROUP_A | GROUP_B)

def fmt(d): return d.strftime("%d %b %Y")
def nxt(y,m): return (y+1,1) if m==12 else (y,m+1)

def add(items,key,form,law,desc,due,freq="Annual",note=""):
    items.append({"key":key,"Form":form,"Law":law,"Description":desc,"Due Date":due,
                  "Frequency":freq,"Note":note})

def build(person,laws,streams,gst_app,gst_freq,state,tds,tax_audit,presumptive,agm,inc):
    a=[]
    if "GST Act" in laws and gst_app:
        if gst_freq=="Monthly":
            for m in range(1,12):
                y2,m2=nxt(YEAR,m)
                add(a,f"g1{m}","GSTR-1","GST Act",f"Outward supplies for {calendar.month_name[m]}",
                    date(y2,m2,11),"Monthly")
                add(a,f"g3{m}","GSTR-3B","GST Act",f"Summary return for {calendar.month_name[m]}",
                    date(y2,m2,20),"Monthly")
        else:
            for q,m in enumerate([3,6,9],1):
                y2,m2=nxt(YEAR,m)
                add(a,f"q1{q}","GSTR-1","GST Act",f"Quarterly outward supplies Q{q}",
                    date(y2,m2,13),"Quarterly")
                day=22 if state in GROUP_A else 24
                add(a,f"q3{q}","GSTR-3B","GST Act",f"QRMP summary return Q{q}",
                    date(y2,m2,day),"Quarterly",f"{state}: {day}th due-date group")
        add(a,"g4","GSTR-4 Annual Return","GST Act","Annual return for composition taxpayers",
            date(YEAR,6,30))

    if "Income Tax Act" in laws and tds:
        for m in range(1,12):
            y2,m2=nxt(YEAR,m)
            due=date(YEAR,4,30) if m==3 else date(y2,m2,7)
            add(a,f"tds{m}","TDS Deposit","Income Tax Act",
                f"TDS deducted in {calendar.month_name[m]}",due,"Monthly")
            add(a,f"tcs{m}","TCS Deposit","Income Tax Act",
                f"TCS collected in {calendar.month_name[m]}",date(y2,m2,7),"Monthly")
        for lab,d in [("Q4 FY25-26",date(YEAR,5,31)),("Q1 FY26-27",date(YEAR,7,31)),
                      ("Q2 FY26-27",date(YEAR,10,31))]:
            add(a,"tdsr"+lab,"Quarterly TDS Return","Income Tax Act",lab,d,"Quarterly")
        for lab,d in [("Q4 FY25-26",date(YEAR,5,15)),("Q1 FY26-27",date(YEAR,7,15)),
                      ("Q2 FY26-27",date(YEAR,10,15))]:
            add(a,"tcsr"+lab,"Quarterly TCS Return","Income Tax Act",lab,d,"Quarterly")

    if "Income Tax Act" in laws:
        if tax_audit:
            add(a,"ta","Tax Audit Report","Income Tax Act","Tax audit report filing",date(YEAR,9,30))
            add(a,"itra","ITR — Audit Case","Income Tax Act","Income tax return for audit case",date(YEAR,10,31))
        else:
            add(a,"itrn","ITR — Non Audit","Income Tax Act","Income tax return for non-audit assessee",date(YEAR,7,31))
        if "Business & Profession" in streams:
            if presumptive:
                add(a,"advp","Advance Tax — Presumptive","Income Tax Act","100% advance tax",date(YEAR,3,15))
            else:
                for pct,d in [("15%",date(YEAR,6,15)),("45%",date(YEAR,9,15)),
                              ("75%",date(YEAR,12,15)),("100%",date(YEAR,3,15))]:
                    add(a,"adv"+pct,"Advance Tax","Income Tax Act",f"Cumulative installment {pct}",d,"Quarterly")

    company = person in {"Private Limited Company","Public Limited Company"}
    if company and "Companies Act" in laws:
        add(a,"dir3","DIR-3 KYC","Companies Act","Annual DIN KYC",date(YEAR,9,30))
        if agm:
            add(a,"aoc4","AOC-4","Companies Act","Financial statements within 30 days of AGM",agm+timedelta(days=30))
            add(a,"mgt7","MGT-7 / MGT-7A","Companies Act","Annual return within 60 days of AGM",agm+timedelta(days=60))
        if inc:
            add(a,"inc20","INC-20A","Companies Act","Commencement declaration within 180 days",inc+timedelta(days=180),"One-time")

    if person=="LLP" and "LLP Act" in laws:
        add(a,"f11","LLP Form 11","LLP Act","Annual Return",date(YEAR,5,30))
        add(a,"f8","LLP Form 8","LLP Act","Statement of Account & Solvency",date(YEAR,10,31))
    return sorted(a,key=lambda x:x["Due Date"])

with st.sidebar:
    st.markdown("## Compliance Configuration")
    person=st.selectbox("Type of Person",PERSONS)
    defaults=["Income Tax Act","GST Act"]
    if "Company" in person: defaults.append("Companies Act")
    if person=="LLP": defaults.append("LLP Act")
    laws=st.multiselect("Applicable Laws",LAWS,default=defaults)
    streams=st.multiselect("Revenue / Income Streams",STREAMS,default=["Business & Profession"])
    st.markdown("### Smart Toggles")
    gst_app=st.toggle("GST Applicable",True)
    tds=st.toggle("Payments liable for TDS",True)
    tax_audit=st.toggle("Tax Audit applicable",False)
    presumptive=st.toggle("Presumptive taxation",False)
    gst_freq="Monthly"; state="Maharashtra"
    if gst_app and "GST Act" in laws:
        gst_freq=st.radio("GST Filing",["Monthly","Quarterly (QRMP)"])
        state=st.selectbox("State / UT",STATES,index=STATES.index("Maharashtra"))
    agm=None; inc=None
    if "Company" in person and "Companies Act" in laws:
        if st.toggle("AGM date available",True): agm=st.date_input("AGM Date",date(YEAR,9,30))
        if st.toggle("Show INC-20A",False): inc=st.date_input("Incorporation Date",date(YEAR,1,1))
    st.caption(f"Calendar year: {YEAR}")
    st.caption(f"System date: {fmt(TODAY)}")

items=build(person,laws,streams,gst_app,gst_freq,state,tds,tax_audit,presumptive,agm,inc)
if "done" not in st.session_state: st.session_state.done=set()
if "rem" not in st.session_state: st.session_state.rem=set()

for x in items:
    x["Completed"]=x["key"] in st.session_state.done
    x["Days"]=(x["Due Date"]-TODAY).days
    x["Status"]="Completed" if x["Completed"] else ("Overdue" if x["Days"]<0 else "Pending")

critical=[x for x in items if 0<=x["Days"]<=5 and not x["Completed"]]
month_items=[x for x in items if x["Due Date"].year==TODAY.year and x["Due Date"].month==TODAY.month]

c1,c2,c3=st.columns(3)
for c,label,val in [(c1,"Action Required in Next 5 Days",len(critical)),
                    (c2,"Total Compliances This Month",len(month_items)),
                    (c3,"Completed Tasks",sum(x["Completed"] for x in items))]:
    c.markdown(f'<div class="metric"><div class="small">{label}</div><div class="num">{val}</div></div>',unsafe_allow_html=True)

st.markdown("## Critical Alerts")
if not critical: st.success("No compliance item is due within the next 5 days.")
for x in critical:
    st.markdown(f'<div class="card critical"><b>⚠ {x["Form"]}</b> — {x["Days"]} Days Left<br>'
                f'<span class="small">{x["Description"]} | Due {fmt(x["Due Date"])}</span></div>',unsafe_allow_html=True)

st.markdown("## Compliance Calendar & Timeline")
a,b,c=st.columns([2,1,1])
search=a.text_input("Search",placeholder="GSTR-3B, ITR, AOC-4, Form 11")
status=b.selectbox("Status",["All","Pending","Completed","Overdue"])
view=c.radio("View",["Timeline","Calendar"],horizontal=True)

filtered=items
if search:
    q=search.lower()
    filtered=[x for x in filtered if q in f'{x["Form"]} {x["Description"]} {x["Law"]}'.lower()]
if status!="All": filtered=[x for x in filtered if x["Status"]==status]

if view=="Timeline":
    for x in filtered:
        urgent=0<=x["Days"]<=5 and not x["Completed"]
        st.markdown(f'<div class="card {"critical" if urgent else ""}"><b>{x["Form"]} | {x["Law"]}</b><br>'
                    f'<span class="small">{x["Description"]}</span><br><b>Due:</b> {fmt(x["Due Date"])}'
                    f' &nbsp; <span class="small">{x["Status"]}</span></div>',unsafe_allow_html=True)
        p,q=st.columns(2)
        done=p.checkbox("Completed",x["Completed"],key="d"+x["key"])
        rem=q.checkbox("Set Reminder (demo)",x["key"] in st.session_state.rem,key="r"+x["key"])
        if done: st.session_state.done.add(x["key"])
        else: st.session_state.done.discard(x["key"])
        if rem: st.session_state.rem.add(x["key"])
        else: st.session_state.rem.discard(x["key"])
else:
    m=st.selectbox("Month",range(1,13),index=max(0,min(11,TODAY.month-1)),format_func=lambda z:calendar.month_name[z])
    st.markdown(f"### {calendar.month_name[m]} {YEAR}")
    heads=st.columns(7)
    for i,n in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]): heads[i].markdown(f"**{n}**")
    for week in calendar.Calendar().monthdayscalendar(YEAR,m):
        cols=st.columns(7)
        for i,day in enumerate(week):
            if day==0: cols[i].write("")
            else:
                ds=[x["Form"] for x in filtered if x["Due Date"].year==YEAR and x["Due Date"].month==m and x["Due Date"].day==day]
                cols[i].markdown(f'<div class="card"><b>{day}</b><br><span class="small">{"<br>".join(ds)}</span></div>',unsafe_allow_html=True)

st.markdown("---")
rows=[{"Form":x["Form"],"Law":x["Law"],"Description":x["Description"],"Due Date":fmt(x["Due Date"]),
       "Frequency":x["Frequency"],"Status":("Completed" if x["key"] in st.session_state.done else x["Status"]),
       "Reminder":"Yes" if x["key"] in st.session_state.rem else "No","Note":x["Note"]} for x in items]
df=pd.DataFrame(rows)
buf=io.BytesIO()
with pd.ExcelWriter(buf,engine="openpyxl") as w: df.to_excel(w,index=False,sheet_name="Compliance Checklist")
st.download_button("📥 Export Checklist",buf.getvalue(),f"Compliance_Checklist_{YEAR}.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
st.caption("Planning tool only. Due dates may change through notifications, extensions, state rules or taxpayer-specific circumstances. Verify before filing.")
