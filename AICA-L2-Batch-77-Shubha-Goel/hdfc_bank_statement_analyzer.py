import io
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Bank Statement Analyzer - HDFC", page_icon="🏦", layout="wide")

st.title("🏦 Bank Statement Analyzer")
st.caption("HDFC Bank statement analyzer for CA / audit / financial review")

# ============================================================
# HDFC STATEMENT READER
# ============================================================
def read_hdfc_statement(uploaded_file):
    """
    Reads the HDFC .xls/.xlsx statement format supplied for this project.

    HDFC format observed:
    Date | Narration | Chq./Ref.No. | Value Dt |
    Withdrawal Amt. | Deposit Amt. | Closing Balance
    """
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        raw = pd.read_csv(uploaded_file, header=None)
    else:
        # xlrd is required for old .xls files.
        raw = pd.read_excel(uploaded_file, header=None)

    header_row = None
    for i in range(min(len(raw), 100)):
        row = " | ".join(str(x).strip() for x in raw.iloc[i].tolist() if pd.notna(x))
        if "Date" in row and "Narration" in row and "Closing Balance" in row:
            header_row = i
            break

    if header_row is None:
        raise ValueError(
            "HDFC transaction header was not found. Expected columns such as "
            "'Date', 'Narration', 'Withdrawal Amt.', 'Deposit Amt.' and 'Closing Balance'."
        )

    data = raw.iloc[header_row + 1:].copy()
    data = data.iloc[:, :7]
    data.columns = [
        "Date", "Narration", "Chq_Ref_No", "Value_Dt",
        "Withdrawal_Amt", "Deposit_Amt", "Closing_Balance"
    ]

    data["Date"] = pd.to_datetime(
        data["Date"].astype(str).str.strip(),
        format="%d/%m/%y",
        errors="coerce"
    )

    # Some HDFC exports contain footer/summary rows. Keep only real dates.
    data = data[data["Date"].notna()].copy()

    for col in ["Withdrawal_Amt", "Deposit_Amt", "Closing_Balance"]:
        data[col] = (
            data[col].astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("₹", "", regex=False)
            .str.strip()
        )
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0.0)

    data["Narration"] = data["Narration"].fillna("").astype(str).str.strip()
    data["Chq_Ref_No"] = data["Chq_Ref_No"].fillna("").astype(str).str.strip()
    data["Value_Dt"] = data["Value_Dt"].fillna("").astype(str).str.strip()

    data["Type"] = "Debit"
    data.loc[data["Deposit_Amt"] > 0, "Type"] = "Credit"

    data["Amount"] = data["Withdrawal_Amt"].where(
        data["Withdrawal_Amt"] > 0, data["Deposit_Amt"]
    )

    data["Month"] = data["Date"].dt.to_period("M").astype(str)

    return data.reset_index(drop=True)


# ============================================================
# CLASSIFICATION
# ============================================================
def classify_hdfc(row):
    text = str(row["Narration"]).upper()
    amount = float(row["Amount"])
    txn_type = row["Type"]

    # Most specific rules first.
    if "INTEREST PAID" in text or "QUARTERLY INTEREST CREDIT" in text:
        return "Interest"

    if "SALARY" in text:
        return "Salary"

    if "ITDTAX REFUND" in text or "INCOME TAX REFUND" in text:
        return "Income Tax Refund"

    if "CASH DEPOSIT" in text or "CASH DEP" in text:
        return "Cash Deposit"

    if "CASH WITHDRAW" in text or "CASH WD" in text or "CASH WDL" in text:
        return "Cash Withdrawal"

    if "ATM" in text and txn_type == "Debit":
        return "Cash Withdrawal"

    if any(x in text for x in [
        "BANK CHARGE", "SERVICE CHARGE", "CHARGES", "ANNUAL FEE",
        "SMS CHARGE", "PROCESSING FEE", "COMMISSION", "DEBIT CARD FEE"
    ]):
        return "Bank Charges"

    if "ZERODHA" in text or "BROKING" in text or "BROKER" in text:
        return "Investment / Brokerage"

    if any(x in text for x in [
        "MUTUAL FUND", "MOTILAL OSWAL", "SIP", "MF PURCHASE",
        "MF REDEMPTION", "REDEMPTION"
    ]):
        return "Investment / Mutual Fund"

    if any(x in text for x in [
        "LOAN", "EMI", "BAJAJ", "HDFC CREDILA", "PRADHAN JI"
    ]):
        return "Loan / Personal Transfer"

    if "GIFT" in text:
        return "Gift / Personal Transfer"

    # Self-transfer detection based on common HDFC narration.
    if "-SELF" in text or "SELF TRANSFER" in text:
        return "Self Transfer"

    # Electronic transfer channels.
    if text.startswith("NEFT"):
        return "NEFT Transfer"

    if text.startswith("RTGS"):
        return "RTGS Transfer"

    if text.startswith("IMPS"):
        return "IMPS Transfer"

    if text.startswith("UPI"):
        return "UPI Transaction"

    if "NACH" in text or "ECS" in text:
        return "NACH / ECS"

    if "TPT" in text:
        return "Transfer"

    if txn_type == "Credit":
        return "Other Credit"

    return "Other Debit"


# ============================================================
# EXCEPTION / AUDIT RULES
# ============================================================
def apply_audit_rules(df, high_value, large_cash, round_value):
    result = df.copy()

    # Duplicate reference number.
    ref = result["Chq_Ref_No"].astype(str).str.strip()
    result["Duplicate Reference"] = (
        ref.ne("") &
        ref.ne("nan") &
        ref.duplicated(keep=False)
    )

    # Repeated exact narration.
    narration_key = result["Narration"].str.upper().str.replace(r"\s+", " ", regex=True).str.strip()
    result["Repeated Narration"] = narration_key.duplicated(keep=False)

    # Round amount.
    result["Round Value"] = (
        result["Amount"].ge(round_value) &
        (result["Amount"] % 1000 == 0)
    )

    # High-value.
    result["High Value"] = result["Amount"] >= high_value

    # Large cash.
    result["Large Cash"] = (
        result["Amount"].ge(large_cash) &
        result["Category"].isin(["Cash Deposit", "Cash Withdrawal"])
    )

    def build_reason(row):
        reasons = []

        if row["High Value"]:
            reasons.append(f"High value >= ₹{high_value:,.0f}")

        if row["Large Cash"]:
            reasons.append(f"Large cash >= ₹{large_cash:,.0f}")

        if row["Duplicate Reference"]:
            reasons.append("Duplicate cheque/reference number")

        if row["Repeated Narration"]:
            reasons.append("Repeated narration")

        if row["Round Value"]:
            reasons.append("Round-value transaction")

        text = str(row["Narration"]).upper()

        if any(k in text for k in [
            "MANUAL", "ADJUSTMENT", "UNKNOWN", "UNIDENTIFIED"
        ]):
            reasons.append("Unusual narration")

        return "; ".join(reasons)

    result["Exception Reason"] = result.apply(build_reason, axis=1)
    result["Audit Exception"] = result["Exception Reason"].ne("")

    return result


# ============================================================
# REPORTS
# ============================================================
def monthly_summary(df):
    s = (
        df.groupby(["Month", "Type"])["Amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    if "Credit" not in s.columns:
        s["Credit"] = 0.0
    if "Debit" not in s.columns:
        s["Debit"] = 0.0

    s["Net Flow"] = s["Credit"] - s["Debit"]
    return s.sort_values("Month")


def category_summary(df):
    return (
        df.groupby(["Category", "Type"])["Amount"]
        .agg(Transactions="count", Total_Amount="sum")
        .reset_index()
        .sort_values("Total_Amount", ascending=False)
    )


def create_excel_report(df):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Analyzed Transactions")
        monthly_summary(df).to_excel(writer, index=False, sheet_name="Monthly Summary")
        category_summary(df).to_excel(writer, index=False, sheet_name="Category Summary")

        exceptions = df[df["Audit Exception"]].copy()
        exceptions.to_excel(writer, index=False, sheet_name="Audit Exceptions")

        cash = df[df["Category"].isin(["Cash Deposit", "Cash Withdrawal"])]
        cash.to_excel(writer, index=False, sheet_name="Cash Transactions")

        investments = df[
            df["Category"].isin([
                "Investment / Brokerage", "Investment / Mutual Fund"
            ])
        ]
        investments.to_excel(writer, index=False, sheet_name="Investments")

    output.seek(0)
    return output


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.header("⚙ Analysis Rules")

    high_value = st.number_input(
        "High-value transaction threshold",
        min_value=0.0,
        value=500000.0,
        step=50000.0
    )

    large_cash = st.number_input(
        "Large cash threshold",
        min_value=0.0,
        value=100000.0,
        step=10000.0
    )

    round_value = st.number_input(
        "Round-value threshold",
        min_value=0.0,
        value=10000.0,
        step=1000.0
    )

    st.markdown("---")
    st.write("**Statement format:** HDFC Bank Excel statement")
    st.write("**Period:** Automatically read from transactions")


# ============================================================
# UPLOAD
# ============================================================
uploaded = st.file_uploader(
    "Upload HDFC Bank Statement",
    type=["xls", "xlsx", "csv"]
)

if not uploaded:
    st.info("Upload the HDFC statement to start.")
    st.stop()

try:
    df = read_hdfc_statement(uploaded)
    df["Category"] = df.apply(classify_hdfc, axis=1)
    df = apply_audit_rules(df, high_value, large_cash, round_value)

except Exception as e:
    st.error(f"Unable to process the HDFC statement: {e}")
    st.stop()


# ============================================================
# KPI
# ============================================================
credits = df.loc[df["Type"] == "Credit", "Amount"].sum()
debits = df.loc[df["Type"] == "Debit", "Amount"].sum()
cash_deposit = df.loc[df["Category"] == "Cash Deposit", "Amount"].sum()
cash_withdrawal = df.loc[df["Category"] == "Cash Withdrawal", "Amount"].sum()
interest = df.loc[df["Category"] == "Interest", "Amount"].sum()
exceptions = int(df["Audit Exception"].sum())

c = st.columns(6)
c[0].metric("Transactions", f"{len(df):,}")
c[1].metric("Total Credits", f"₹{credits:,.2f}")
c[2].metric("Total Debits", f"₹{debits:,.2f}")
c[3].metric("Cash Deposits", f"₹{cash_deposit:,.2f}")
c[4].metric("Cash Withdrawals", f"₹{cash_withdrawal:,.2f}")
c[5].metric("Audit Exceptions", f"{exceptions:,}")


# ============================================================
# DASHBOARD
# ============================================================
st.markdown("---")
left, right = st.columns(2)

with left:
    cat = (
        df.groupby("Category")["Amount"]
        .sum()
        .reset_index()
        .sort_values("Amount", ascending=False)
    )
    fig = px.bar(
        cat,
        x="Category",
        y="Amount",
        title="Amount by Classification"
    )
    fig.update_layout(xaxis_tickangle=-40)
    st.plotly_chart(fig, use_container_width=True)

with right:
    ms = monthly_summary(df)
    fig2 = px.bar(
        ms,
        x="Month",
        y=["Credit", "Debit"],
        barmode="group",
        title="Monthly Credit vs Debit"
    )
    st.plotly_chart(fig2, use_container_width=True)


# ============================================================
# MONTHLY SUMMARY
# ============================================================
st.subheader("📅 Monthly Summary")
st.dataframe(
    monthly_summary(df),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# CLASSIFICATION SUMMARY
# ============================================================
st.subheader("📊 Classification Summary")
st.dataframe(
    category_summary(df),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# CA-RELEVANT REVIEW SECTIONS
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🚨 Audit Exceptions",
    "💵 Cash",
    "📈 Investments",
    "🔎 Full Statement"
])

with tab1:
    exceptions = df[df["Audit Exception"]].copy()

    if exceptions.empty:
        st.success("No transactions matched the configured audit rules.")
    else:
        st.warning(f"{len(exceptions):,} transaction(s) require review.")
        st.dataframe(
            exceptions[
                [
                    "Date", "Narration", "Chq_Ref_No", "Type",
                    "Amount", "Category", "Exception Reason"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

with tab2:
    cash = df[
        df["Category"].isin(["Cash Deposit", "Cash Withdrawal"])
    ].copy()

    if cash.empty:
        st.info("No cash transactions were identified.")
    else:
        st.write(
            f"Cash deposits: ₹{cash[cash['Category']=='Cash Deposit']['Amount'].sum():,.2f}"
        )
        st.write(
            f"Cash withdrawals: ₹{cash[cash['Category']=='Cash Withdrawal']['Amount'].sum():,.2f}"
        )
        st.dataframe(
            cash[
                ["Date", "Narration", "Type", "Amount", "Category", "Closing_Balance"]
            ],
            use_container_width=True,
            hide_index=True
        )

with tab3:
    investments = df[
        df["Category"].isin([
            "Investment / Brokerage", "Investment / Mutual Fund"
        ])
    ].copy()

    if investments.empty:
        st.info("No investment-related transactions were identified.")
    else:
        st.dataframe(
            investments[
                ["Date", "Narration", "Type", "Amount", "Category", "Closing_Balance"]
            ],
            use_container_width=True,
            hide_index=True
        )

with tab4:
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# EXPORT
# ============================================================
st.markdown("---")
st.subheader("⬇️ Export CA Review Report")

report = create_excel_report(df)

st.download_button(
    "Download Excel Analysis Report",
    data=report,
    file_name=f"HDFC_Bank_Analysis_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.caption(
    "This application provides rule-based analytical support. "
    "Transactions and exceptions should be reviewed by the CA/user before final reliance."
)
