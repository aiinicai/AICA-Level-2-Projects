import streamlit as st
import pandas as pd
import os
import json
import time
import io
import fitz

from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Smart Invoice Analyzer",
    page_icon="🧾",
    layout="wide"
)

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")


# --------------------------------------------------
# SESSION STORAGE
# --------------------------------------------------

if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = []


# --------------------------------------------------
# CONVERT PDF PAGES TO IMAGES
# --------------------------------------------------

def convert_pdf_to_images(uploaded_file):

    pdf_bytes = uploaded_file.getvalue()

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []

    for page_number in range(len(document)):

        page = document.load_page(page_number)

        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            alpha=False
        )

        image_bytes = pix.tobytes("png")

        pages.append(
            {
                "name": (
                    f"{uploaded_file.name} "
                    f"- Page {page_number + 1}"
                ),
                "bytes": image_bytes,
                "mime_type": "image/png"
            }
        )

    document.close()

    return pages


# --------------------------------------------------
# PREPARE UPLOADED FILES
# --------------------------------------------------

def prepare_invoice_files(uploaded_files):

    prepared_files = []

    for uploaded_file in uploaded_files:

        if uploaded_file.type == "application/pdf":

            pdf_pages = convert_pdf_to_images(
                uploaded_file
            )

            prepared_files.extend(pdf_pages)

        else:

            prepared_files.append(
                {
                    "name": uploaded_file.name,
                    "bytes": uploaded_file.getvalue(),
                    "mime_type": uploaded_file.type
                }
            )

    return prepared_files


# --------------------------------------------------
# AI EXTRACTION FUNCTION
# --------------------------------------------------

def extract_invoice_data(file_name, file_bytes, mime_type):

    if not api_key:
        raise ValueError(
            "Gemini API key was not found."
        )

    client = genai.Client(api_key=api_key)

    prompt = """
You are an invoice data extraction assistant.

Carefully read the attached invoice.

Extract ONLY information that is visible or clearly supported
by the invoice.

Do not invent information.

Return ONLY one valid JSON object.

Use exactly these fields:

{
  "Vendor Name": "",
  "Invoice Number": "",
  "Invoice Date": "",
  "GSTIN": "",
  "Expense Category": "",
  "Taxable Amount": null,
  "CGST": null,
  "SGST": null,
  "IGST": null,
  "Total Amount": null
}

IMPORTANT RULES:

1. If a text field cannot be found, return an empty string.

2. If an amount cannot be found, return null.
   Do NOT automatically return zero for a missing amount.

3. Return 0 only when the invoice itself clearly indicates
   that the relevant amount is zero.

4. Do not guess GSTIN, invoice number, invoice date,
   taxable value or tax amounts.

5. "Vendor Name" means the supplier/seller issuing the invoice,
   not the customer/buyer.

6. GSTIN should be the supplier/vendor GSTIN where identifiable.

7. Expense Category is an AI-suggested category based on the
   goods or services shown on the invoice. Examples include:
   Office Supplies, Professional Fees, Software, Travel,
   Advertising, Repairs, Utilities and Other.

8. Taxable Amount means the amount before GST/tax where
   clearly identifiable.

9. CGST, SGST and IGST should be extracted separately.

10. Total Amount means the final invoice total payable,
    including applicable taxes.

11. Numeric fields must contain only a number or null.
    Do not include currency symbols, commas or words.

12. Do not include markdown.

13. Do not include ```json.

14. Return one JSON object only.
"""

    response = None

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=[
                    types.Part.from_bytes(
                        data=file_bytes,
                        mime_type=mime_type
                    ),
                    prompt
                ]
            )

            break

        except Exception as e:

            if attempt < 2:
                time.sleep(5)
            else:
                raise e

    if response is None:
        raise ValueError(
            "No response received from Gemini."
        )

    result_text = response.text.strip()

    result_text = result_text.replace(
        "```json",
        ""
    )

    result_text = result_text.replace(
        "```",
        ""
    )

    result_text = result_text.strip()

    result = json.loads(result_text)

    result["Source File"] = file_name

    return result


# --------------------------------------------------
# DATA CLEANING
# --------------------------------------------------

def create_dataframe():

    if not st.session_state.invoice_data:
        return pd.DataFrame()

    data = pd.DataFrame(
        st.session_state.invoice_data
    )

    numeric_columns = [
        "Taxable Amount",
        "CGST",
        "SGST",
        "IGST",
        "Total Amount"
    ]

    for column in numeric_columns:

        if column in data.columns:

            data[column] = pd.to_numeric(
                data[column],
                errors="coerce"
            )

    return data


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title(
    "🧾 AI-Powered Invoice Data Extraction & Expense Dashboard"
)

st.write(
    "Upload PDF or image invoices, extract structured "
    "information using AI, review the extracted data and "
    "analyse expenses through an interactive dashboard."
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.title(
    "🧾 Smart Invoice Analyzer"
)

st.sidebar.write(
    "AI-Powered Invoice Processing"
)

menu = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard",
        "🧾 Process Invoices",
        "📋 Invoice Data",
        "📥 Export Data"
    ]
)

st.sidebar.divider()

st.sidebar.info(
    "Capstone Project\n\n"
    "AI-Powered Invoice Data Extraction & Expense Dashboard"
)

st.sidebar.caption(
    "AI-extracted information should be reviewed "
    "before accounting or reporting use."
)


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

if menu == "📊 Dashboard":

    st.header(
        "📊 Expense Dashboard"
    )

    data = create_dataframe()

    if not data.empty:

        total_invoices = len(data)

        total_expenses = data[
            "Total Amount"
        ].fillna(0).sum()

        total_gst = (
            data["CGST"].fillna(0).sum()
            + data["SGST"].fillna(0).sum()
            + data["IGST"].fillna(0).sum()
        )

        total_vendors = (
            data["Vendor Name"]
            .replace("", pd.NA)
            .dropna()
            .nunique()
        )

    else:

        total_invoices = 0
        total_expenses = 0
        total_gst = 0
        total_vendors = 0

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Invoices",
        total_invoices
    )

    col2.metric(
        "Total Expenses",
        f"₹{total_expenses:,.2f}"
    )

    col3.metric(
        "Total GST",
        f"₹{total_gst:,.2f}"
    )

    col4.metric(
        "Total Vendors",
        total_vendors
    )

    st.divider()

    st.subheader(
        "📈 Expense Analysis"
    )

    if data.empty:

        st.info(
            "Dashboard charts will appear after "
            "invoices have been processed."
        )

    else:

        chart_data = data.copy()

        chart_data["Expense Category"] = (
            chart_data["Expense Category"]
            .replace("", "Uncategorised")
            .fillna("Uncategorised")
        )

        category_data = (
            chart_data
            .groupby(
                "Expense Category",
                as_index=False
            )["Total Amount"]
            .sum()
        )

        st.bar_chart(
            category_data,
            x="Expense Category",
            y="Total Amount"
        )


# --------------------------------------------------
# PROCESS INVOICES
# --------------------------------------------------

elif menu == "🧾 Process Invoices":

    st.header(
        "🧾 Process Invoices"
    )

    st.write(
        "Upload one or more PDF, PNG, JPG or JPEG invoices."
    )

    st.info(
        "For PDF files, each page is processed as a "
        "separate invoice."
    )

    uploaded_files = st.file_uploader(
        "Upload Invoice Files",
        type=[
            "pdf",
            "png",
            "jpg",
            "jpeg"
        ],
        accept_multiple_files=True
    )

    if uploaded_files:

        st.success(
            f"{len(uploaded_files)} file(s) uploaded successfully."
        )

        st.subheader(
            "Uploaded Files"
        )

        for uploaded_file in uploaded_files:

            st.write(
                "📄",
                uploaded_file.name
            )

        st.divider()

        if st.button(
            "🤖 Extract Invoice Data",
            type="primary",
            use_container_width=True
        ):

            try:

                prepared_files = (
                    prepare_invoice_files(
                        uploaded_files
                    )
                )

            except Exception as e:

                st.error(
                    f"Could not prepare uploaded files: {e}"
                )

                prepared_files = []

            if prepared_files:

                st.write(
                    f"Processing {len(prepared_files)} "
                    f"invoice page(s)..."
                )

                progress = st.progress(0)

                new_results = []

                for index, invoice_file in enumerate(
                    prepared_files
                ):

                    try:

                        with st.spinner(
                            "AI is reading "
                            f"{invoice_file['name']}..."
                        ):

                            result = extract_invoice_data(
                                invoice_file["name"],
                                invoice_file["bytes"],
                                invoice_file["mime_type"]
                            )

                            new_results.append(
                                result
                            )

                    except Exception as e:

                        st.error(
                            "Could not process "
                            f"{invoice_file['name']}: {e}"
                        )

                    progress.progress(
                        (index + 1)
                        / len(prepared_files)
                    )

                if new_results:

                    st.session_state.invoice_data.extend(
                        new_results
                    )

                    st.success(
                        "🎉 Invoice data extracted successfully!"
                    )

                    st.dataframe(
                        pd.DataFrame(
                            new_results
                        ),
                        use_container_width=True,
                        hide_index=True
                    )

                    st.warning(
                        "Please review AI-extracted values "
                        "before using them for accounting, "
                        "tax or reporting purposes."
                    )


# --------------------------------------------------
# INVOICE DATA
# --------------------------------------------------

elif menu == "📋 Invoice Data":

    st.header(
        "📋 Extracted Invoice Data"
    )

    if st.session_state.invoice_data:

        data = create_dataframe()

        st.write(
            "Review and correct the AI-extracted information "
            "where necessary."
        )

        edited_data = st.data_editor(
            data,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "💾 Save Edited Data",
                type="primary",
                use_container_width=True
            ):

                st.session_state.invoice_data = (
                    edited_data
                    .where(
                        pd.notnull(edited_data),
                        None
                    )
                    .to_dict("records")
                )

                st.success(
                    "Changes saved successfully."
                )

        with col2:

            if st.button(
                "🗑️ Clear All Invoice Data",
                use_container_width=True
            ):

                st.session_state.invoice_data = []

                st.rerun()

    else:

        st.info(
            "No invoices have been processed yet."
        )


# --------------------------------------------------
# EXPORT DATA
# --------------------------------------------------

elif menu == "📥 Export Data":

    st.header(
        "📥 Export Invoice Data"
    )

    if st.session_state.invoice_data:

        data = create_dataframe()

        csv_data = data.to_csv(
            index=False
        ).encode("utf-8-sig")

        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl"
        ) as writer:

            data.to_excel(
                writer,
                index=False,
                sheet_name="Invoice Data"
            )

        excel_data = excel_buffer.getvalue()

        col1, col2 = st.columns(2)

        with col1:

            st.download_button(
                "📗 Download Excel",
                data=excel_data,
                file_name=(
                    "smart_invoice_data.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True
            )

        with col2:

            st.download_button(
                "📄 Download CSV",
                data=csv_data,
                file_name=(
                    "smart_invoice_data.csv"
                ),
                mime="text/csv",
                use_container_width=True
            )

        st.success(
            f"{len(data)} invoice record(s) ready for export."
        )

    else:

        st.info(
            "Process at least one invoice before exporting data."
        )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "AI-Powered Invoice Data Extraction & Expense Dashboard "
    "| Capstone Project"
)