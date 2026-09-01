\# GST Harmony – GST Annual Return Reconciliation



\## AICA Level 2 Capstone Project



\*\*Submitted by:\*\* Abhay Bhagat

\*\*Batch:\*\* AICA Level 2 – Batch 104

\*\*Project type:\*\* Web-based GST reconciliation application

\*\*Live application:\*\* https://return-match.lovable.app

\*\*GitHub repository:\*\* https://github.com/arbhagat-wq/gst-harmony



\---



\## 1. Project Overview



GST Harmony is an offline-first GST Annual Return Reconciliation application developed for Chartered Accountants and accounting professionals.



The application compares data extracted from Tally with GST-return information and identifies differences in turnover, tax liability, input tax credit and invoice-level reporting.



The working papers and imported client data are stored locally in the user’s browser. The application does not directly file GST returns.



\---



\## 2. Problem Statement



GST annual-return preparation requires reconciliation of large volumes of information from multiple sources, including:



\* Tally sales register

\* Tally purchase register

\* GST ledger summary

\* GSTR-1

\* GSTR-3B

\* GSTR-2B

\* GSTR-9 draft data

\* Previous-year reconciliation adjustments



Manual reconciliation through multiple spreadsheets is time-consuming and may result in missed invoices, incorrect tax values, timing differences and incomplete explanations.



GST Harmony provides a structured workflow for importing, mapping, comparing, reviewing and exporting this information.



\---



\## 3. Main Features



\* Creation of client-wise GST reconciliation working papers

\* Excel and CSV data import

\* Automatic and manual column mapping

\* Tally sales versus GSTR-1 reconciliation

\* Tally tax liability versus GSTR-3B reconciliation

\* Purchase register versus GSTR-2B reconciliation

\* GSTR-9 draft annual-summary review

\* Previous-year adjustment tracking

\* Invoice-level reconciliation

\* Dashboard and annual summaries

\* Transaction-level review and remarks

\* Final review of books, returns and differences

\* Audit trail of imports and changes

\* Detailed Excel export

\* Client PDF summary

\* One-click fictitious demo dataset

\* Local browser-based data storage



\---



\## 4. Reconciliation Classifications



Transactions are classified into the following categories:



\* Matched

\* Missing in Tally

\* Missing in GST Return

\* Value Mismatch

\* Tax Mismatch

\* GSTIN Mismatch

\* Invoice Number Mismatch

\* Timing Difference

\* Requires Manual Review



The user can review exceptions, record remarks and document the proposed treatment.



\---



\## 5. Supported Input Files



The application supports the following input templates:



1\. Tally Sales Register

2\. Tally Purchase Register

3\. Tally GST Ledger Summary

4\. GSTR-1 Data

5\. GSTR-3B Data

6\. GSTR-2B Data

7\. GSTR-9 Draft Annual Summary

8\. Previous-Year Reconciliation Adjustments



Sample files are included in the `sample-data` folder.



All names, GSTINs and transactions included in the sample files are fictitious and intended only for demonstration and testing.



\---



\## 6. Demo Instructions



A complete demonstration can be run without manually uploading the sample files.



1\. Open https://return-match.lovable.app.

2\. Click \*\*Load Demo Data\*\*.

3\. Open \*\*Harmony Demo Solutions Pvt Ltd\*\*.

4\. Review the dashboard and annual summaries.

5\. Open the transaction reconciliation.

6\. Review matched transactions and controlled mismatches.

7\. Add remarks against an exception.

8\. Review the final annual figures.

9\. Open the audit trail.

10\. Export the Excel reconciliation and Client PDF Summary.



The demonstration includes intentional differences such as missing invoices, value mismatches and invoice-number mismatches.



\---



\## 7. Installation and Local Execution



\### Prerequisites



Install the following:



\* Node.js

\* npm

\* Google Chrome or Microsoft Edge



\### Installation



Open PowerShell or Command Prompt inside the project folder and run:



```powershell

npm install

```



Start the development server:



```powershell

npm run dev

```



Open the localhost address displayed by Vite. It will generally be:



```text

http://localhost:8080

```



Keep the PowerShell window open while using the local application.



\### Production Build



To test the production build, run:



```powershell

npm run build

```



\---



\## 8. Technology Used



\* React

\* TypeScript

\* Vite

\* HTML

\* CSS

\* JavaScript

\* Node.js and npm for development and build

\* Browser-based local storage

\* Excel and PDF export functionality

\* Lovable for application development and hosting

\* GitHub for source-code management



\---



\## 9. Application Workflow



1\. Create or select a client.

2\. Enter GSTIN, financial year, state and registration type.

3\. Upload the required Tally and GST files.

4\. Review automatic column mapping.

5\. Correct mappings if necessary.

6\. Validate and import the information.

7\. Run the reconciliation.

8\. Review matched and unmatched transactions.

9\. Enter remarks and proposed treatment.

10\. Complete the final annual review.

11\. Export the detailed Excel working papers.

12\. Generate the Client PDF Summary.



\---



\## 10. Data Privacy



GST Harmony is designed as an offline-first working-paper application.



\* Imported data stays in the user’s browser.

\* One user cannot see another user’s locally stored information.

\* Data entered on localhost does not automatically transfer to the published website.

\* Data is not automatically shared between computers or browser profiles.

\* Incognito data is deleted when the Incognito window is closed.

\* Users should export Excel and PDF reports regularly as backups.

\* Real client data should be used only after independently verifying the organisation’s privacy and security requirements.



\---



\## 11. Project Folder Structure



```text

AICA-L2-Batch-(104)-Abhay-Bhagat/

├── .lovable/

├── output-samples/

├── public/

├── sample-data/

├── screenshots/

├── src/

├── .gitignore

├── bun.lock

├── package.json

├── package-lock.json

├── README.md

├── vite.config.ts

└── other configuration files

```



\---



\## 12. Screenshots



\### Published Application



!\[Published Application](screenshots/01-Published-Application.png)



\### Dashboard and Annual Summary



!\[Dashboard Summary](screenshots/02-Dashboard-Summary.png)



\### Imports and Column Mapping



!\[Imports and Column Mapping](screenshots/03-Imports-Column-Mapping.png)



\### Transaction Reconciliation



!\[Transaction Reconciliation](screenshots/04-Transaction-Reconciliation.png)



\### Transaction Review



!\[Transaction Review](screenshots/05-Transaction-Review.png)



\### Final Review



!\[Final Review](screenshots/06-Final-Review.png)



\### Audit Trail



!\[Audit Trail](screenshots/07-Audit-Trail.png)



\### Exported Report



!\[Exported Report](screenshots/08-Exported-Report.png)



\---



\## 13. Output Samples



The `output-samples` folder contains representative outputs generated using fictitious demo data:



\* Detailed GST reconciliation Excel report

\* Client PDF summary



These files are provided solely for evaluation and demonstration.



\---



\## 14. Known Limitations



\* Data is stored locally and is not automatically synchronised between devices.

\* Clearing browser storage may remove saved working papers.

\* The application does not directly connect to Tally.

\* The application does not download information directly from the GST portal.

\* The application does not directly file GSTR-9 or GSTR-9C.

\* Uploaded files must follow the supported templates or be correctly mapped.

\* Reconciliation results require professional review before use in an actual GST return.



\---



\## 15. Future Improvements



Potential future enhancements include:



\* Direct Tally integration

\* GST portal API integration, where legally and technically permitted

\* Secure user authentication

\* Encrypted cloud backup

\* Multi-user access and role management

\* Automated GSTR-9 table mapping

\* Expanded GSTR-9C reconciliation

\* Configurable materiality thresholds

\* Digital review and approval workflow

\* Windows desktop `.exe` distribution



\---



\## 16. Disclaimer



This project is an educational capstone project.



The sample data is entirely fictitious. The application does not provide legal or tax advice and is not a substitute for professional judgement. All reconciliation results must be independently verified before preparing or filing any GST return.



\---



\*\*Developed by Abhay Bhagat\*\*

\*\*AICA Level 2 – Batch 104\*\*



