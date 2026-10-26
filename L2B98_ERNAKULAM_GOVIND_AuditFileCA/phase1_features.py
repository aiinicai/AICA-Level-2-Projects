"""Read-only Phase 1 analytics, search, and engagement archive utilities."""
from collections import Counter, defaultdict
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import csv, hashlib, json, zipfile
import pandas as pd
import streamlit as st
from core import Assignment, Client, Engagement, Folder, Note, Signoff, User, Version, WP, ROOT


def parsed_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def engagement_stats(s, eng):
    papers = s.query(WP).filter_by(engagement_id=eng.id).all()
    counts = Counter(w.status for w in papers)
    notes = s.query(Note).join(WP, Note.wp_id == WP.id).filter(WP.engagement_id == eng.id, Note.status != 'Closed').count()
    deadline = parsed_date(eng.end)
    today = date.today()
    finalised = eng.status != 'Open'
    overdue = bool(deadline and today > deadline and not finalised)
    upcoming = bool(deadline and not finalised and today <= deadline and (deadline - today).days <= 7)
    return dict(total=len(papers), closed=counts['Closed'], draft=counts['Draft'], submitted=counts['Submitted'],
                returned=counts['Returned'], reopened=counts['Reopened'], open=sum(w.status != 'Closed' for w in papers),
                notes=notes, completion=round(100 * counts['Closed'] / len(papers), 1) if papers else 0,
                overdue=overdue, upcoming=upcoming, deadline=deadline,
                days_overdue=(today - deadline).days if overdue else 0,
                state='Finalised' if finalised else 'Overdue' if overdue else 'Not started' if parsed_date(eng.start) and today < parsed_date(eng.start) else 'In progress')


def dashboard(s, engagements, current_user):
    st.header('Engagement progress dashboard')
    st.caption('Engagements shown are restricted to your existing access rights. Overdue = end date passed and engagement not finalised.')
    users = {x.id: x for x in s.query(User).all()}
    clients = {x.id: x for x in s.query(Client).all()}
    assignments = s.query(Assignment).all()
    assigned = defaultdict(list)
    for a in assignments:
        assigned[a.engagement_id].append(a)
    records = []
    for e in engagements:
        stat = engagement_stats(s, e)
        partners = sorted({users[a.user_id].name for a in assigned[e.id] if a.user_id in users and users[a.user_id].designation in ('Senior Partner', 'Junior Partner')})
        records.append((e, stat, partners))
    c = st.columns(4)
    for col, (label, value) in zip(c, [('Engagements',len(records)),('Overdue',sum(x[1]['overdue'] for x in records)),('Due within 7 days',sum(x[1]['upcoming'] for x in records)),('Finalised',sum(x[1]['state']=='Finalised' for x in records))]):
        col.metric(label, value)
    st.subheader('Engagements under each partner')
    counts = Counter(p for _,_,partners in records for p in partners)
    if counts:
        st.dataframe(pd.DataFrame([{'Partner':p,'Assigned engagements':n} for p,n in sorted(counts.items())]), hide_index=True, use_container_width=True)
        # A compact horizontal chart avoids a giant full-width bar when there is only one partner.
        import altair as alt
        chart_data = pd.DataFrame([{'Partner': p, 'Engagements': n} for p, n in sorted(counts.items())])
        chart = (alt.Chart(chart_data)
                 .mark_bar(size=22, cornerRadiusEnd=3)
                 .encode(x=alt.X('Engagements:Q', title=None, scale=alt.Scale(domain=[0, max(2, 2 * max(counts.values()))], nice=False), axis=alt.Axis(tickMinStep=1, format='d', title=None)),
                         y=alt.Y('Partner:N', title=None, sort='-x'),
                         tooltip=['Partner:N', 'Engagements:Q'])
                 .properties(height=max(65, min(240, len(counts) * 42)), padding={'top': 6, 'bottom': 30, 'left': 8, 'right': 12}))
        st.altair_chart(chart, use_container_width=True)
        st.markdown('<div style="text-align:center; font-size:0.82rem; color:#64748b; margin-top:0.1rem;">Number of engagements</div>', unsafe_allow_html=True)
        st.caption('An engagement assigned to multiple partners is counted under each of them.')
    else:
        st.info('No partner assignments recorded for these engagements.')
    if not records:
        st.info('No accessible engagements.');return
    st.subheader('Engagement register')
    options = ['All','Overdue','Due within 7 days','In progress','Finalised','Not started']
    status_filter = st.selectbox('Show engagements',options,key='phase1_eng_filter')
    partner_filter = st.selectbox('Partner', ['All']+sorted(counts),key='phase1_partner_filter')
    rows=[]
    for e,stat,partners in records:
        if status_filter=='Overdue' and not stat['overdue']:continue
        if status_filter=='Due within 7 days' and not stat['upcoming']:continue
        if status_filter not in ('All','Overdue','Due within 7 days') and stat['state']!=status_filter:continue
        if partner_filter!='All' and partner_filter not in partners:continue
        rows.append({'Engagement ID':e.id,'Client':clients[e.client_id].name if e.client_id in clients else f'Client {e.client_id}', 'Type':e.kind,'FY':e.fy,'Partners':', '.join(partners) or 'Unassigned', 'Start':e.start,'End':e.end,'State':stat['state'],'Days overdue':stat['days_overdue'],'Total WPs':stat['total'],'Closed WPs':stat['closed'],'Pending review':stat['submitted'],'Completion %':stat['completion']})
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    st.subheader('Drill down to engagement')
    selected = st.selectbox('Select engagement', [x[0] for x in records],format_func=lambda e:f'{e.id} — {clients[e.client_id].name if e.client_id in clients else e.client_id} — {e.kind} — {e.fy}',key='phase1_eng_drill')
    engagement_detail(s,selected,users)


def engagement_detail(s, e, users=None):
    users = users or {x.id:x for x in s.query(User).all()}
    stat = engagement_stats(s,e)
    st.caption(f'Scheduled: {e.start or "Not set"} to {e.end or "Not set"}  ·  {stat["state"]}' + (f'  ·  {stat["days_overdue"]} days overdue' if stat['overdue'] else ''))
    cells = st.columns(4)
    for cell,(label,value) in zip(cells,[('Total WPs',stat['total']),('Open WPs',stat['open']),('Closed WPs',stat['closed']),('Completion',f'{stat["completion"]}%')]):cell.metric(label,value)
    submitted_papers = s.query(WP).filter_by(engagement_id=e.id, status='Submitted').all()
    pending_l1 = sum(w.level == 1 for w in submitted_papers)
    pending_l2 = sum(w.level == 2 for w in submitted_papers)
    cells = st.columns(4)
    for cell,(label,value) in zip(cells,[('Pending Level 1',pending_l1),('Pending Level 2',pending_l2),('Returned',stat['returned']),('Open observations',stat['notes'])]):cell.metric(label,value)
    st.caption(f'Other pending review levels: {sum(w.level not in (1,2) for w in submitted_papers)}  ·  Draft / reopened: {stat["draft"] + stat["reopened"]}')
    st.caption(f'Working-paper completion: {stat["closed"]} of {stat["total"]} closed ({stat["completion"]}%)')
    st.progress(stat['completion']/100)
    if not stat['total']:st.info('Not yet documented — no working papers have been created.')
    papers=s.query(WP).filter_by(engagement_id=e.id).order_by(WP.idx).all()
    assignments=s.query(Assignment).filter_by(engagement_id=e.id,role='Reviewer').all()
    reviewers=defaultdict(list)
    for a in assignments:reviewers[a.level].append(users[a.user_id].initials or users[a.user_id].name if a.user_id in users else str(a.user_id))
    rows=[]
    for w in papers:
        pending=', '.join(reviewers.get(w.level,[])) if w.status=='Submitted' else ''
        rows.append({'Index':w.idx,'Working paper':w.title,'Status':w.status,'Review level':w.level,'Preparer':users[w.preparer_id].initials if w.preparer_id in users else '—','Pending with':pending,'Version':w.version})
    if rows:
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)


def search_papers(s,eng):
    papers=s.query(WP).filter_by(engagement_id=eng.id).order_by(WP.idx).all()
    if not papers:st.info('No working papers to search.');return
    users={x.id:x for x in s.query(User).all()}
    folders={x.id:x for x in s.query(Folder).filter_by(engagement_id=eng.id).all()}
    assignments=s.query(Assignment).filter_by(engagement_id=eng.id,role='Reviewer').all()
    reviewer_names=', '.join(f'{users[a.user_id].initials or users[a.user_id].name} (L{a.level})' for a in sorted(assignments, key=lambda a:a.level) if a.user_id in users)
    signoffs=s.query(Signoff).filter(Signoff.wp_id.in_([w.id for w in papers]), Signoff.action=='Approve').order_by(Signoff.at).all()
    approved=defaultdict(dict)
    for a in signoffs:
        if a.user_id in users:
            approved[(a.wp_id,a.version)][(a.level,a.user_id)]=f'{users[a.user_id].initials or users[a.user_id].name} (L{a.level})'
    query=st.text_input('Search index, title, folder, preparer or reviewer',key=f'phase1_search_{eng.id}').strip().casefold()
    c1,c2,c3=st.columns(3)
    status=c1.selectbox('Status',['All']+sorted({w.status for w in papers}),key=f'phase1_status_{eng.id}')
    preparer=c2.selectbox('Preparer',['All']+sorted({users[w.preparer_id].name for w in papers if w.preparer_id in users}),key=f'phase1_preparer_{eng.id}')
    folder=c3.selectbox('Folder',['All']+sorted({f'{f.idx} — {f.title}' for f in folders.values()}),key=f'phase1_folder_{eng.id}')
    results=[]
    for w in papers:
        f=folders.get(w.folder_id)
        folder_label=f'{f.idx} — {f.title}' if f else 'Unfiled'
        p=users.get(w.preparer_id)
        pname=p.name if p else 'Unknown'
        initials=p.initials if p else '—'
        searchable=' '.join([w.idx or '',w.title or '',folder_label,pname,initials,reviewer_names]).casefold()
        if query and query not in searchable:continue
        if status!='All' and w.status!=status:continue
        if preparer!='All' and pname!=preparer:continue
        if folder!='All' and folder_label!=folder:continue
        results.append({'WP ID':w.id,'Index':w.idx,'Title':w.title,'Folder':folder_label,'Preparer':initials,'Reviewed by':', '.join(approved.get((w.id,w.version),{}).values()) or '—','Assigned reviewers':reviewer_names,'Status':w.status,'Version':w.version,'Review level':w.level})
    st.caption(f'{len(results)} of {len(papers)} working papers match')
    st.dataframe(pd.DataFrame([{k:v for k,v in row.items() if k!='WP ID'} for row in results]),hide_index=True,use_container_width=True)
    if results:
        selected=st.selectbox('Open working paper in explorer',results,format_func=lambda r:f'{r["Index"]} — {r["Title"]}',key=f'phase1_jump_{eng.id}')
        if st.button('Open selected working paper',key=f'phase1_open_{eng.id}'):
            st.session_state[f'explorer_{st.session_state.uid}_{eng.id}_folder']=next((w.folder_id for w in papers if w.id==selected['WP ID']),None)
            target=next((w.folder_id for w in papers if w.id==selected['WP ID']),None)
            expanded=set(st.session_state.get(f'explorer_{st.session_state.uid}_{eng.id}_expanded',set()))
            visited=set()
            while target in folders and target not in visited:
                visited.add(target)
                parent=folders[target].parent_id
                if parent in folders:expanded.add(parent)
                target=parent
            st.session_state[f'explorer_{st.session_state.uid}_{eng.id}_expanded']=expanded
            st.session_state[f'phase1_focus_wp_{eng.id}']=selected['WP ID']
            st.session_state['phase1_jump_engagement']=eng.id
            st.session_state['phase1_nav_to_wp']=True
            st.rerun()


def export_engagement(s,eng):
    """Build archive in memory; never modify records or original stored files."""
    folders=s.query(Folder).filter_by(engagement_id=eng.id).all()
    papers=s.query(WP).filter_by(engagement_id=eng.id).order_by(WP.idx).all()
    users={x.id:x for x in s.query(User).all()}
    folder_by_id={f.id:f for f in folders}
    def safe(part):
        cleaned=''.join('_' if c in '/\\:*?"<>|\x00\r\n' or ord(c)<32 else c for c in str(part)).strip(' .')
        return cleaned[:95] or 'Unnamed'
    def folder_path(folder_id):
        pieces=[];seen=set()
        while folder_id in folder_by_id and folder_id not in seen:
            seen.add(folder_id);f=folder_by_id[folder_id]
            pieces.append(safe(f'{f.idx} - {f.title}'))
            folder_id=f.parent_id
        return '/'.join(reversed(pieces))
    assignments=s.query(Assignment).filter_by(engagement_id=eng.id,role='Reviewer').all()
    assigned=', '.join(f'{users[a.user_id].initials or users[a.user_id].name} (L{a.level})' for a in sorted(assignments,key=lambda x:x.level) if a.user_id in users)
    signoffs=s.query(Signoff).filter(Signoff.wp_id.in_([w.id for w in papers])).order_by(Signoff.at).all() if papers else []
    approvals=defaultdict(list)
    for a in signoffs:
        if a.action=='Approve':approvals[(a.wp_id,a.version)].append(a)
    versions=s.query(Version).filter(Version.wp_id.in_([w.id for w in papers])).all() if papers else []
    by_version={(v.wp_id,v.number):v for v in versions}
    notes=s.query(Note).filter(Note.wp_id.in_([w.id for w in papers])).all() if papers else []
    index=[];manifest=[];warnings=[]
    archive=BytesIO()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in folders:
            z.writestr('Working_Papers/'+folder_path(f.id)+'/',b'')
        for w in papers:
            v=by_version.get((w.id,w.version))
            path='';hash_value='';file_status='No current version'
            if v:
                file=ROOT/'storage'/Path(v.path).name
                if file.is_file():
                    data=file.read_bytes()
                    hash_value=hashlib.sha256(data).hexdigest()
                    if v.checksum and hash_value!=v.checksum:
                        file_status='CHECKSUM MISMATCH — excluded';warnings.append(f'{w.idx}: checksum mismatch')
                    else:
                        path='Working_Papers/'+(folder_path(w.folder_id)+'/' if w.folder_id in folder_by_id else 'Unfiled/')+safe(f'{w.idx} - {v.filename}')
                        if path in z.namelist():path=path.rsplit('.',1)[0]+f'__WP{w.id}.'+path.rsplit('.',1)[-1]
                        z.writestr(path,data);file_status='Included'
                        manifest.append({'WP_Index':w.idx,'Archive_Path':path,'SHA256':hash_value})
                else:
                    file_status='Missing source file';warnings.append(f'{w.idx}: missing file')
            unique_reviewers = {}
            for a in approvals.get((w.id,w.version),[]):
                unique_reviewers[(a.level,a.user_id)] = f'{users[a.user_id].initials if a.user_id in users else a.user_id} (L{a.level})'
            reviewers=', '.join(unique_reviewers.values()) or '—'
            index.append({'Index':w.idx,'Title':w.title,'Folder':folder_path(w.folder_id),'Preparer':users[w.preparer_id].initials if w.preparer_id in users else '—','Approved by (current version)':reviewers,'Assigned reviewers':assigned,'Status':w.status,'Review level':w.level,'Version':w.version,'File':path,'File status':file_status})
        index_buf=BytesIO()
        with pd.ExcelWriter(index_buf,engine='openpyxl') as writer:
            pd.DataFrame(index,columns=['Index','Title','Folder','Preparer','Approved by (current version)','Assigned reviewers','Status','Review level','Version','File','File status']).to_excel(writer,index=False,sheet_name='Working Paper Index')
            pd.DataFrame(manifest,columns=['WP_Index','Archive_Path','SHA256']).to_excel(writer,index=False,sheet_name='File Hashes')
        z.writestr('Working_Paper_Index.xlsx',index_buf.getvalue())
        review_rows=[]
        wp_map={w.id:w for w in papers}
        for a in signoffs:
            review_rows.append({'Index':wp_map[a.wp_id].idx,'Version':a.version,'Level':a.level,'Action':a.action,'User':users[a.user_id].initials if a.user_id in users else a.user_id,'At':str(a.at)})
        for n in notes:
            review_rows.append({'Index':wp_map[n.wp_id].idx,'Version':n.version,'Level':n.level,'Action':'Observation ('+str(n.status)+')','User':users[n.reviewer_id].initials if n.reviewer_id in users else n.reviewer_id,'At':str(n.at),'Observation':n.body})
        output=BytesIO();columns=['Index','Version','Level','Action','User','At','Observation']
        with __import__('io').TextIOWrapper(output,encoding='utf-8-sig',newline='',write_through=True) as wrapper:
            writer=csv.DictWriter(wrapper,fieldnames=columns);writer.writeheader();writer.writerows(review_rows)
            wrapper.flush();review_csv=output.getvalue()
        z.writestr('Review_History.csv',review_csv)
        client=s.get(Client,eng.client_id)
        summary={'client':client.name if client else eng.client_id,'engagement_id':eng.id,'type':eng.kind,'financial_year':eng.fy,'start':eng.start,'end':eng.end,'status':eng.status,'exported_at':datetime.now().astimezone().isoformat(),'export_type':'Finalised' if eng.status!='Open' else 'DRAFT / IN PROGRESS','warnings':warnings}
        z.writestr('Engagement_Summary.json',json.dumps(summary,indent=2,ensure_ascii=False))
        z.writestr('File_Manifest.csv',pd.DataFrame(manifest,columns=['WP_Index','Archive_Path','SHA256']).to_csv(index=False))
    return archive.getvalue(),warnings


def export_panel(s,eng):
    st.subheader('Export complete engagement file')
    st.caption('Exports the current version of each WP in indexed folders, with Excel index, approval/observation history and SHA-256 manifest. Original files and database remain unchanged.')
    if eng.status=='Open':st.warning('This engagement is not finalised. The export will be marked DRAFT / IN PROGRESS.')
    if st.button('Prepare engagement ZIP',key=f'phase1_prepare_export_{eng.id}'):
        with st.spinner('Preparing archive and verifying file hashes...'):
            try:
                data,warnings=export_engagement(s,eng)
                st.session_state[f'phase1_export_{eng.id}']=data
                st.session_state[f'phase1_export_warnings_{eng.id}']=warnings
            except Exception as exc:st.error(f'Export could not be prepared: {exc}')
    data=st.session_state.get(f'phase1_export_{eng.id}')
    if data:
        warnings=st.session_state.get(f'phase1_export_warnings_{eng.id}',[])
        if warnings:st.warning('Some files could not be included: '+ '; '.join(warnings))
        st.download_button('Download engagement ZIP',data,file_name=f'AuditFile_Engagement_{eng.id}_{"Finalised" if eng.status!="Open" else "Draft"}.zip',mime='application/zip',key=f'phase1_download_{eng.id}')
        st.caption('If any working papers are changed after preparing the ZIP, click Prepare engagement ZIP again.')
