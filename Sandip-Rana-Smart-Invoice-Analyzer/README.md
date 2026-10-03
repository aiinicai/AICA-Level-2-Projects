\# AI-Powered Invoice Data Extraction \& Expense Dashboard



\## Capstone Project



This project is an AI-powered invoice processing application developed using Python and Streamlit. It extracts structured information from PDF and image invoices using the Google Gemini API and provides an interactive expense dashboard.



\## Features



\- Upload PDF, JPG, JPEG and PNG invoices

\- Process multiple invoices

\- AI-powered invoice data extraction

\- Extract Vendor Name

\- Extract Invoice Number

\- Extract Invoice Date

\- Extract GSTIN where available

\- AI-based Expense Category classification

\- Extract Taxable Amount

\- Extract CGST, SGST and IGST where available

\- Extract Total Invoice Amount

\- Review and edit extracted invoice data

\- Interactive expense dashboard

\- Category-wise expense analysis

\- Vendor-wise expense analysis

\- Export invoice data to Excel

\- Export invoice data to CSV



\## Technology Used



\- Python

\- Streamlit

\- Google Gemini API

\- Pandas

\- Plotly

\- PyMuPDF

\- OpenPyXL

\- Pillow

\- python-dotenv



\## Installation



Install the required Python packages:



pip install -r requirements.txt



\## API Key Setup



Create a `.env` file in the project directory and add your Google Gemini API key:



GEMINI\_API\_KEY=your\_api\_key\_here



For security, the `.env` file must not be uploaded to GitHub.



\## Run the Application



Run the following command from the project directory:



streamlit run app.py



The application will open in your web browser.



\## Application Workflow



1\. Open the Process Invoices page.

2\. Upload one or more invoice files.

3\. Click Extract Invoice Data.

4\. AI extracts structured invoice information.

5\. Review and edit the extracted information in Invoice Data.

6\. View expense analysis on the Dashboard.

7\. Export the reviewed data to Excel or CSV.



\## Important Note



AI-generated information may contain extraction or classification errors. Users should review the extracted invoice data before using it for accounting, taxation, audit or reporting purposes.



\## Project Purpose



The purpose of this capstone project is to demonstrate the practical application of Generative AI in invoice processing, structured data extraction, expense classification, data analysis and reporting.



\## Disclaimer



This application is developed for educational and demonstration purposes. It should not be treated as a substitute for professional accounting, taxation or audit review.

