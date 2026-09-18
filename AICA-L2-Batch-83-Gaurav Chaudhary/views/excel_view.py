import streamlit as st
import reports

def render_excel_module(current_user_name):
    st.subheader("📤 Excel Import & Migration Engine")
    st.markdown("Migrate your existing Excel stock audit tracking sheet into the application in seconds.")
    
    col_imp1, col_imp2 = st.columns([1, 1])
    with col_imp1:
        st.markdown("#### 1. Download Pre-Formatted Excel Template")
        tpl_bytes = reports.generate_sample_excel_template()
        st.download_button(
            label="📥 Download Sample Excel Template (.xlsx)",
            data=tpl_bytes,
            file_name="Stock_Audit_Import_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary",
            use_container_width=True
        )
        st.markdown("**Includes all 16 standardized audit fields** with built-in format validations.")

    with col_imp2:
        st.markdown("#### 2. Upload Completed Excel Tracker")
        excel_upload = st.file_uploader("Upload Excel File (.xlsx / .xls)", type=["xlsx", "xls"])
        
        if excel_upload is not None:
            if st.button("🚀 Process & Import Excel Data", type="primary", use_container_width=True):
                with st.spinner("Parsing and importing records..."):
                    imported, skipped, errs = reports.parse_and_import_excel(
                        file_bytes=excel_upload.getvalue(),
                        user_name=current_user_name
                    )
                    if imported > 0:
                        st.success(f"🎉 Successfully imported {imported} audit assignments into the database!")
                    if skipped > 0:
                        st.warning(f"Skipped {skipped} rows (empty or invalid).")
                    if errs:
                        with st.expander("View Error Details"):
                            for e in errs:
                                st.write(f"- {e}")
                    if imported > 0:
                        st.rerun()
