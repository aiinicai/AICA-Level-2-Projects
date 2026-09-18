import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
from utils import reconcile_transactions, generate_brs

st.set_page_config(page_title="Bank Reconciliation", layout="wide")
st.title("📊 Bank Reconciliation App")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Bank Statement")
    bank_file = st.file_uploader("Bank Statement (CSV)", type=['csv'], key='bank')
    
with col2:
    st.subheader("2. Upload GL Register")
    gl_file = st.file_uploader("GL Register (CSV)", type=['csv'], key='gl')

if bank_file and gl_file:
    try:
        # Load files
        bank_df = pd.read_csv(bank_file)
        gl_df = pd.read_csv(gl_file)
        
        # Rename columns to standard format
        bank_df.columns = ['Date', 'Reference', 'Amount', 'Balance']
        gl_df.columns = ['Date', 'Reference', 'Amount', 'Description']
        
        # Convert dates to datetime
        bank_df['Date'] = pd.to_datetime(bank_df['Date'], format='%d-%m-%Y')
        gl_df['Date'] = pd.to_datetime(gl_df['Date'], format='%d-%m-%Y')
        
        # Convert amounts to float
        bank_df['Amount'] = pd.to_numeric(bank_df['Amount'], errors='coerce')
        gl_df['Amount'] = pd.to_numeric(gl_df['Amount'], errors='coerce')
        
        # Reconcile
        matched, bank_only, gl_only, mismatch, duplicates = reconcile_transactions(
            bank_df, gl_df, date_tolerance=3, amount_tolerance=0
        )
        
        # Metrics
        st.divider()
        st.subheader("📈 Reconciliation Summary")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Bank Transactions", len(bank_df))
        with col2:
            st.metric("GL Transactions", len(gl_df))
        with col3:
            st.metric("✓ Matched", len(matched))
        with col4:
            st.metric("✗ Unmatched", len(bank_only) + len(gl_only))
        with col5:
            total = len(bank_df) + len(gl_df)
            matched_pct = (len(matched) / max(total/2, 1)) * 100
            st.metric("Match %", f"{matched_pct:.1f}%")
        
        # Detailed Results
        st.divider()
        st.subheader("🔍 Reconciliation Details")
        
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "✓ Matched", 
            "🏦 Bank Only", 
            "📘 GL Only", 
            "⚠️ Mismatch", 
            "🔁 Duplicates",
            "BRS Summary"
        ])
        
        with tab1:
            if len(matched) > 0:
                st.dataframe(matched, use_container_width=True, hide_index=True)
                st.success(f"✓ {len(matched)} transactions matched")
            else:
                st.info("No matched transactions found")
        
        with tab2:
            if len(bank_only) > 0:
                st.dataframe(bank_only[['Date', 'Reference', 'Amount']], use_container_width=True, hide_index=True)
                st.warning(f"⚠️ {len(bank_only)} transactions in Bank Statement only")
            else:
                st.info("No bank-only transactions")
        
        with tab3:
            if len(gl_only) > 0:
                st.dataframe(gl_only[['Date', 'Reference', 'Amount', 'Description']], use_container_width=True, hide_index=True)
                st.warning(f"⚠️ {len(gl_only)} transactions in GL Register only")
            else:
                st.info("No GL-only transactions")
        
        with tab4:
            if len(mismatch) > 0:
                st.dataframe(mismatch, use_container_width=True, hide_index=True)
                st.warning(f"⚠️ {len(mismatch)} transactions with amount/date mismatch")
            else:
                st.info("No mismatches found")
        
        with tab5:
            if len(duplicates) > 0:
                st.dataframe(duplicates[['Date', 'Reference', 'Amount', 'Type']], use_container_width=True, hide_index=True)
                st.error(f"🔁 {len(duplicates)} duplicate transactions found")
            else:
                st.info("No duplicates found")
        
        with tab6:
            brs_data = generate_brs(bank_df, matched, bank_only, gl_only, mismatch)
            st.dataframe(brs_data, use_container_width=True, hide_index=True)
        
        # Export
        st.divider()
        st.subheader("💾 Export Results")
        
        # Create Excel export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            matched.to_excel(writer, sheet_name='Matched', index=False)
            bank_only.to_excel(writer, sheet_name='Bank Only', index=False)
            gl_only.to_excel(writer, sheet_name='GL Only', index=False)
            mismatch.to_excel(writer, sheet_name='Mismatch', index=False)
            duplicates.to_excel(writer, sheet_name='Duplicates', index=False)
            brs_data.to_excel(writer, sheet_name='BRS Summary', index=False)
        
        output.seek(0)
        st.download_button(
            label="📥 Download Excel Report",
            data=output,
            file_name=f"Bank_Reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"Error processing files: {str(e)}")

else:
    st.info("👈 Upload both files to begin reconciliation")
    
    # Show sample instructions
    with st.expander("ℹ️ Expected Format"):
        st.code("""
Bank Statement CSV (with headers):
Date,Reference,Amount,Balance
01-01-2024,CHQ001,5000,10000
02-01-2024,DEP002,15000,25000

GL Register CSV (with headers):
Date,Reference,Amount,Description
01-01-2024,CHQ001,5000,Payment
02-01-2024,DEP002,15000,Deposit
        """)
