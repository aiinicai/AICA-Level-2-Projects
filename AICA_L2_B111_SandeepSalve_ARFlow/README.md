# ARFlow

**Accounts Receivable Automation for Small Businesses**
ARFlow Labs - Capstone Project by CA Sandeep Salve, Membership No. 154909
Submitted to ICAI under the AICA Level 2 Capstone programme.

## What it does
ARFlow automates the accounts receivable cycle, from the moment an invoice is raised to the moment cash is collected. It is an offline Windows desktop application.

| Stage | What ARFlow does |
|---|---|
| Invoice | Creates GST invoices; suggests the place of supply from the customer's GSTIN so the right tax (CGST and SGST, or IGST) is applied; assigns the invoice number on issue; produces the PDF |
| Payment | Records full, partial and multi-invoice payments and advances and allocates them against invoices |
| Ledger and ageing | Customer ledger and receivables ageing (not due, 1-30, 31-60, 61-90, above 90 days), exportable to Excel and PDF |
| Dashboard | Collection rate, overdue, outstanding, ageing and top customers, drawn natively and animated |
| Reminders | Email and WhatsApp screens show a preview of the invoice and payment-reminder message |
| Control | Audit log of every change; backup and restore; credit notes and cancellations with reasons |

## Design
- Every figure is calculated with exact Decimal arithmetic.
- Data is stored locally; the program works fully offline and sends nothing out.
- Issued invoices are never edited silently: amend, credit note or cancel, each with a reason and an audit-log entry.

## Technology
Python 3, PyQt6, OpenPyXL, ReportLab, local JSON storage with an append-only audit log.

## How to run
1. Download and unzip `ARFlow.zip`.
2. Double-click `ARFlow.exe` (Windows). No installation or Python is needed.
3. The program opens with fictitious demo company settings and an empty database. Start with **Customer Master** (or **Excel Master Import**), **Product/Service Master** and **Create Invoice**.
4. Use only test data. All data in the demonstration video is fictitious.

## Video
Project explanation video: https://drive.google.com/file/d/1pCirLPLWrIlVw58MhCaZW3651q5EBGZa/view?usp=drive_link
