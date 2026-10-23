import streamlit as st
import pandas as pd
import io

# --- Page Setup ---
st.set_page_config(
    page_title="Investor Transfer & Name Change Identification Tool",
    layout="wide"
)

st.title("Investor Transfer and Name Change Identification Tool")
st.markdown("Automated quarterly reconciliation for private equity & investment funds.")

# --- File Upload Section ---
st.sidebar.header("1. Upload Quarterly Data")
uploaded_files = {
    "PY": st.sidebar.file_uploader("Upload PY File", type=["xlsx", "xls"], key="py"),
    "Q1": st.sidebar.file_uploader("Upload Q1 File", type=["xlsx", "xls"], key="q1"),
    "Q2": st.sidebar.file_uploader("Upload Q2 File", type=["xlsx", "xls"], key="q2"),
    "Q3": st.sidebar.file_uploader("Upload Q3 File", type=["xlsx", "xls"], key="q3"),
    "Q4": st.sidebar.file_uploader("Upload Q4 File", type=["xlsx", "xls"], key="q4"),
}

# --- Period Selection Section ---
st.sidebar.header("2. Comparison Period")
preset_options = ["PY to Q1", "Q1 to Q2", "Q2 to Q3", "Q3 to Q4", "Custom Range"]
selected_preset = st.sidebar.selectbox("Select Comparison Scope", preset_options)

periods = ["PY", "Q1", "Q2", "Q3", "Q4"]

if selected_preset == "Custom Range":
    base_period = st.sidebar.selectbox("Base Period (From)", periods, index=0)
    target_period = st.sidebar.selectbox("Target Period (To)", periods, index=1)
else:
    mapping = {
        "PY to Q1": ("PY", "Q1"),
        "Q1 to Q2": ("Q1", "Q2"),
        "Q2 to Q3": ("Q2", "Q3"),
        "Q3 to Q4": ("Q3", "Q4")
    }
    base_period, target_period = mapping[selected_preset]

# --- Helper Functions ---
REQUIRED_COLUMNS = ["Fund name", "Vehicle name", "Investor name", "Investor ID", "Investor commitment"]

def load_and_standardize(file):
    """Loads Excel, validates required columns, and cleans data."""
    try:
        df = pd.read_excel(file)
        # Strip whitespace from headers
        df.columns = df.columns.str.strip()
        
        # Validate schema
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns: {', '.join(missing_cols)}")
            return None
        
        # Clean string fields and numerical fields
        df["Fund name"] = df["Fund name"].astype(str).str.strip()
        df["Vehicle name"] = df["Vehicle name"].astype(str).str.strip()
        df["Investor name"] = df["Investor name"].astype(str).str.strip()
        df["Investor ID"] = df["Investor ID"].astype(str).str.strip()
        df["Investor commitment"] = pd.to_numeric(df["Investor commitment"], errors='coerce').fillna(0.0)
        
        return df[REQUIRED_COLUMNS]
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def process_reconciliation(df_base, df_target, base_lbl, target_lbl):
    """Core logic to identify Transfers, Name Changes, Sub-closes, and Unchanged commitments."""
    
    # Aggregate to prevent duplicate keys within same period/vehicle/investor
    df_base_agg = df_base.groupby(
        ["Fund name", "Vehicle name", "Investor ID", "Investor name"], as_index=False
    )["Investor commitment"].sum()

    df_target_agg = df_target.groupby(
        ["Fund name", "Vehicle name", "Investor ID", "Investor name"], as_index=False
    )["Investor commitment"].sum()

    # Outer join to match by Vehicle and Investor ID
    merged = pd.merge(
        df_base_agg,
        df_target_agg,
        on=["Vehicle name", "Investor ID"],
        how="outer",
        suffixes=(f"_{base_lbl}", f"_{target_lbl}")
    )

    merged[f"Investor commitment_{base_lbl}"] = merged[f"Investor commitment_{base_lbl}"].fillna(0.0)
    merged[f"Investor commitment_{target_lbl}"] = merged[f"Investor commitment_{target_lbl}"].fillna(0.0)
    
    # 1. Flag Name Changes: Same Vehicle, Same Investor ID, Different Name
    name_change_mask = (
        merged[f"Investor name_{base_lbl}"].notna() &
        merged[f"Investor name_{target_lbl}"].notna() &
        (merged[f"Investor name_{base_lbl}"] != merged[f"Investor name_{target_lbl}"])
    )

    # 2. Flag Disposals (potential transferors) and Additions (potential transferees)
    # Exited / Reduced commitments
    reduced_mask = (
        (merged[f"Investor commitment_{base_lbl}"] > merged[f"Investor commitment_{target_lbl}"]) & 
        ~name_change_mask
    )
    # New / Increased commitments
    increased_mask = (
        (merged[f"Investor commitment_{target_lbl}"] > merged[f"Investor commitment_{base_lbl}"]) & 
        ~name_change_mask
    )

    # Pool for transfer detection
    transferors = []
    for idx, row in merged[reduced_mask].iterrows():
        reduction = row[f"Investor commitment_{base_lbl}"] - row[f"Investor commitment_{target_lbl}"]
        transferors.append({
            "Vehicle name": row["Vehicle name"],
            "Name of transferor": row[f"Investor name_{base_lbl}"],
            "Investor ID of transferor": row["Investor ID"],
            "Original Commitment": row[f"Investor commitment_{base_lbl}"],
            "Amount reduced": reduction,
            "Matched": False
        })
    df_transferors = pd.DataFrame(transferors)

    transferees = []
    for idx, row in merged[increased_mask].iterrows():
        addition = row[f"Investor commitment_{target_lbl}"] - row[f"Investor commitment_{base_lbl}"]
        transferees.append({
            "Vehicle name": row["Vehicle name"],
            "Name of Transferee": row[f"Investor name_{target_lbl}"],
            "Investor ID of transferee": row["Investor ID"],
            "Amount added": addition,
            "Matched": False
        })
    df_transferees = pd.DataFrame(transferees)

    # Transfer matching: Different Investor ID, Different Investor Name, matching exact transfer amounts
    transfers_list = []
    if not df_transferors.empty and not df_transferees.empty:
        for t_idx, t_row in df_transferors.iterrows():
            # Exact match condition: Same or different vehicle, matching transfer reduction to addition
            match = df_transferees[
                (~df_transferees["Matched"]) &
                (df_transferees["Investor ID of transferee"] != t_row["Investor ID of transferor"]) &
                (abs(df_transferees["Amount added"] - t_row["Amount reduced"]) < 0.01)
            ]
            if not match.empty:
                m_idx = match.index[0]
                df_transferees.at[m_idx, "Matched"] = True
                df_transferors.at[t_idx, "Matched"] = True

                pct = (t_row["Amount reduced"] / t_row["Original Commitment"] * 100) if t_row["Original Commitment"] > 0 else 100.0
                transfers_list.append({
                    "Vehicle name": t_row["Vehicle name"],
                    "Name of transferor": t_row["Name of transferor"],
                    "Investor ID of transferor": t_row["Investor ID of transferor"],
                    "Name of Transferee": df_transferees.at[m_idx, "Name of Transferee"],
                    "Investor ID of transferee": df_transferees.at[m_idx, "Investor ID of transferee"],
                    "Amount transferred": t_row["Amount reduced"],
                    "Percentage of transfer": round(pct, 2)
                })

    df_transfers = pd.DataFrame(transfers_list)

    # 3. Categorize Full Check Sheet
    transferred_ids = set()
    if not df_transfers.empty:
        transferred_ids = set(df_transfers["Investor ID of transferor"]).union(set(df_transfers["Investor ID of transferee"]))

    status_col = []
    for idx, row in merged.iterrows():
        inv_id = row["Investor ID"]
        c_base = row[f"Investor commitment_{base_lbl}"]
        c_target = row[f"Investor commitment_{target_lbl}"]
        name_b = row[f"Investor name_{base_lbl}"]
        name_t = row[f"Investor name_{target_lbl}"]

        if pd.notna(name_b) and pd.notna(name_t) and (name_b != name_t):
            status_col.append("Name change")
        elif inv_id in transferred_ids:
            status_col.append("Transfer")
        elif c_base == c_target and pd.notna(name_b) and pd.notna(name_t):
            status_col.append("No change")
        else:
            status_col.append("Sub close")

    merged["Category"] = status_col

    # Format Full Check Tab
    df_full_check = pd.DataFrame({
        "Fund name": merged[f"Fund name_{target_lbl}"].combine_first(merged[f"Fund name_{base_lbl}"]),
        "Vehicle name": merged["Vehicle name"],
        f"Investor Name ({base_lbl})": merged[f"Investor name_{base_lbl}"],
        f"Investor Name ({target_lbl})": merged[f"Investor name_{target_lbl}"],
        "Investor ID": merged["Investor ID"],
        f"Commitment ({base_lbl})": merged[f"Investor commitment_{base_lbl}"],
        f"Commitment ({target_lbl})": merged[f"Investor commitment_{target_lbl}"],
        "Variance": merged[f"Investor commitment_{target_lbl}"] - merged[f"Investor commitment_{base_lbl}"],
        "Notes": merged["Category"]
    })

    # 4. Name Change Tab
    name_change_records = merged[merged["Category"] == "Name change"]
    df_name_change = pd.DataFrame({
        "Vehicle name": name_change_records["Vehicle name"],
        "Investor ID": name_change_records["Investor ID"],
        "Former name": name_change_records[f"Investor name_{base_lbl}"],
        "New name": name_change_records[f"Investor name_{target_lbl}"],
        "Commitment": name_change_records[f"Investor commitment_{target_lbl}"]
    })

    # 5. Subclose Tab
    subclose_records = merged[merged["Category"] == "Sub close"]
    df_subclose = pd.DataFrame({
        "Fund name": subclose_records[f"Fund name_{target_lbl}"].combine_first(subclose_records[f"Fund name_{base_lbl}"]),
        "Vehicle name": subclose_records["Vehicle name"],
        "Investor name": subclose_records[f"Investor name_{target_lbl}"].combine_first(subclose_records[f"Investor name_{base_lbl}"]),
        "Investor ID": subclose_records["Investor ID"],
        f"Commitment ({base_lbl})": subclose_records[f"Investor commitment_{base_lbl}"],
        f"Commitment ({target_lbl})": subclose_records[f"Investor commitment_{target_lbl}"],
        "Commitment Change": subclose_records[f"Investor commitment_{target_lbl}"] - subclose_records[f"Investor commitment_{base_lbl}"]
    })

    return df_full_check, df_transfers, df_name_change, df_subclose

def export_to_excel(df_full, df_transfers, df_name_change, df_subclose):
    """Exports all reconciliation dataframes into a structured multi-tab Excel file."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_full.to_excel(writer, sheet_name="Full Check", index=False)
        df_transfers.to_excel(writer, sheet_name="Transfer", index=False)
        df_name_change.to_excel(writer, sheet_name="Name Change", index=False)
        df_subclose.to_excel(writer, sheet_name="Sub Close", index=False)
    output.seek(0)
    return output

# --- Main Execution ---
st.subheader(f"Current Comparison: `{base_period}` ➔ `{target_period}`")

if st.button("Run Identification Tool", type="primary"):
    file_base = uploaded_files.get(base_period)
    file_target = uploaded_files.get(target_period)

    if not file_base or not file_target:
        st.error(f"Please upload files for both **{base_period}** and **{target_period}** before running.")
    else:
        df_base = load_and_standardize(file_base)
        df_target = load_and_standardize(file_target)

        if df_base is not None and df_target is not None:
            df_full, df_transfers, df_name_change, df_subclose = process_reconciliation(
                df_base, df_target, base_period, target_period
            )

            st.success("Reconciliation completed successfully.")

            # Summary Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Investors Checked", len(df_full))
            c2.metric("Transfers Identified", len(df_transfers))
            c3.metric("Name Changes", len(df_name_change))
            c4.metric("Sub-closes / New Closings", len(df_subclose))

            # UI Preview Tabs
            tab1, tab2, tab3, tab4 = st.tabs(["Full Check", "Transfer", "Name Change", "Sub Close"])
            with tab1:
                st.dataframe(df_full, use_container_width=True)
            with tab2:
                st.dataframe(df_transfers, use_container_width=True)
            with tab3:
                st.dataframe(df_name_change, use_container_width=True)
            with tab4:
                st.dataframe(df_subclose, use_container_width=True)

            # Export Button
            excel_bytes = export_to_excel(df_full, df_transfers, df_name_change, df_subclose)
            st.download_button(
                label="📥 Export Report to Excel",
                data=excel_bytes,
                file_name=f"Reconciliation_{base_period}_to_{target_period}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )