import mimetypes

import streamlit as st

from core import auth, db, duedates, ui
from core.constants import DOC_CATEGORIES

from . import common

MAX_MB = 10


def render():
    u = common.me()
    ui.header("Documents", "Client documents stored securely in the firm's database, by client and financial year")
    cm = common.clients()
    if not cm:
        common.no_clients_yet()
        return
    stats = db.one("SELECT COUNT(*) AS n, COALESCE(SUM(size_bytes),0) AS sz FROM documents")
    fy0 = duedates.current_fy_start()
    years = [duedates.fy_label(y) for y in range(fy0 + 1, fy0 - 6, -1)]

    with st.expander("Upload documents", expanded=stats["n"] == 0, icon=":material/upload:"):
        with st.form("upload", clear_on_submit=True):
            a, b, c = st.columns(3)
            cid = a.selectbox("Client", list(cm), format_func=lambda i: cm[i])
            cat = b.selectbox("Category", DOC_CATEGORIES)
            fy = c.selectbox("Financial year", years, index=1)
            files = st.file_uploader(f"Files (max {MAX_MB} MB each)", accept_multiple_files=True)
            if st.form_submit_button("Upload", type="primary") and files:
                saved = 0
                for f in files:
                    data = f.getvalue()
                    if len(data) > MAX_MB * 1024 * 1024:
                        st.warning(f"{f.name} is larger than {MAX_MB} MB and was skipped."); continue
                    db.execute("INSERT INTO documents(client_id,category,fin_year,filename,mime,size_bytes,content,"
                               "uploaded_by,uploaded_on) VALUES (:c,:cat,:fy,:fn,:m,:s,:b,:u,:at)",
                               c=cid, cat=cat, fy=fy, fn=f.name, m=f.type or mimetypes.guess_type(f.name)[0],
                               s=len(data), b=data, u=u["id"], at=db.now())
                    saved += 1
                st.success(f"{saved} file(s) uploaded.")

    f1, f2, f3, f4 = st.columns([1.4, 1, 1, 1.6])
    fc = f1.selectbox("Client", [0] + list(cm), format_func=lambda i: "All clients" if i == 0 else cm[i])
    fcat = f2.selectbox("Category", ["All"] + DOC_CATEGORIES)
    ffy = f3.selectbox("Year", ["All"] + years)
    q = f4.text_input("File name", placeholder="Search file name…")
    sql = ("SELECT d.id, d.client_id, d.filename, d.mime, d.category, d.fin_year, d.size_bytes, d.uploaded_on, d.uploaded_by, "
           "c.name AS client, u.name AS uploader FROM documents d JOIN clients c ON c.id=d.client_id "
           "LEFT JOIN users u ON u.id=d.uploaded_by WHERE 1=1")
    p = {}
    if fc:
        sql += " AND d.client_id=:c"; p["c"] = fc
    if fcat != "All":
        sql += " AND d.category=:cat"; p["cat"] = fcat
    if ffy != "All":
        sql += " AND d.fin_year=:fy"; p["fy"] = ffy
    docs = db.query(sql + " ORDER BY d.uploaded_on DESC LIMIT 200", **p)
    if q:
        docs = [d for d in docs if q.lower() in d["filename"].lower()]
    st.caption(f"{stats['n']} documents · {stats['sz'] / 1024 / 1024:.1f} MB stored")
    if not docs:
        st.markdown(ui.empty("No documents match"), unsafe_allow_html=True)
        return
    icons = {"pdf": "📕", "xlsx": "📗", "xls": "📗", "csv": "📗", "docx": "📘", "doc": "📘", "jpg": "🖼️", "jpeg": "🖼️",
             "png": "🖼️", "zip": "🗜️", "json": "🧩"}
    for d in docs:
        ext = d["filename"].rsplit(".", 1)[-1].lower() if "." in d["filename"] else ""
        with st.container(border=True, key=f"doc-{d['id']}"):
            c1, c2, c3 = st.columns([5, 1.1, 0.6], vertical_alignment="center")
            c1.markdown(f"<div style='display:flex;gap:12px;align-items:center'><span style='font-size:1.6rem'>"
                        f"{icons.get(ext, '📄')}</span><div><b>{ui.esc(d['filename'])}</b><br/>"
                        f"<span style='color:#64748B;font-size:0.8rem'>{ui.esc(d['client'])} · {ui.esc(d['category'])} · "
                        f"FY {ui.esc(d['fin_year'])} · {(d['size_bytes'] or 0) / 1024:.0f} KB · "
                        f"{ui.esc(d['uploader'] or '')} · {ui.ago(d['uploaded_on'])}</span></div></div>",
                        unsafe_allow_html=True)
            with c2:
                st.download_button("Download", lambda i=d["id"]: bytes(db.scalar("SELECT content FROM documents WHERE id=:i", i=i)),
                                   d["filename"], mime=d["mime"] or "application/octet-stream", key=f"dl{d['id']}",
                                   icon=":material/download:", width="stretch")
            can_delete = auth.sees_all_work(u) or d["uploaded_by"] == u["id"]
            if can_delete and c3.button("", key=f"rm{d['id']}", icon=":material/delete:", help="Delete"):
                db.execute("DELETE FROM documents WHERE id=:i", i=d["id"])
                st.rerun()
