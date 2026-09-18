import streamlit as st
import os
import database as db

def render_documents(all_assignments, current_user_name):
    st.subheader("📁 Centralized Document & Working Paper Repository")
    st.markdown("Upload and archive appointment letters, bank sanction data, stock sheets, physical verification photos, and signed audit reports.")
    
    if not all_assignments:
        st.warning("Please create an assignment before uploading documents.")
        return
        
    doc_assign_map = {a["id"]: f"#{a['id']} - {a['borrower_name']} ({a['bank_name']})" for a in all_assignments}
    doc_assign_id = st.selectbox("Select Audit Assignment:", list(doc_assign_map.keys()), format_func=lambda x: doc_assign_map[x])
    
    d_col1, d_col2 = st.columns([1, 1])
    with d_col1:
        st.markdown("#### 📤 Upload New Document")
        selected_cat = st.selectbox("Document Category *", db.DOC_CATEGORIES)
        uploaded_file = st.file_uploader("Choose File (PDF, Excel, Word, Images, Zip)", type=["pdf", "xlsx", "xls", "docx", "doc", "jpg", "jpeg", "png", "zip"])
        
        if st.button("Upload Document", type="primary"):
            if uploaded_file is not None:
                success = db.save_document(
                    assignment_id=doc_assign_id,
                    doc_category=selected_cat,
                    file_name=uploaded_file.name,
                    file_bytes=uploaded_file.getvalue(),
                    uploaded_by=current_user_name
                )
                if success:
                    st.success(f"✅ '{uploaded_file.name}' uploaded successfully under '{selected_cat}'!")
                    st.rerun()
                else:
                    st.error("Failed to save document.")
            else:
                st.error("Please select a file to upload.")
                
    with d_col2:
        st.markdown("#### 📂 Attached Documents for this Assignment")
        docs = db.get_assignment_documents(doc_assign_id)
        if docs:
            for doc in docs:
                with st.container(border=True):
                    st.markdown(f"📄 **{doc['file_name']}**")
                    st.caption(f"Category: **{doc['doc_category']}** | Size: {round((doc['file_size'] or 0)/1024, 1)} KB | Uploaded by: {doc['uploaded_by']} on {doc['uploaded_at'][:16]}")
                    
                    if os.path.exists(doc["file_path"]):
                        with open(doc["file_path"], "rb") as f:
                            st.download_button(
                                label="⬇️ Download File",
                                data=f.read(),
                                file_name=doc["file_name"],
                                key=f"dl_doc_{doc['id']}"
                            )
                    else:
                        st.warning("File not found on local disk.")
        else:
            st.info("No documents uploaded yet for this assignment.")
