# GST Reconciliation Assistant

**ICAI Level 2 AI Course — Capstone Project**
**Submitted by:** Avleen Kaur
**Live App:** https://gst-reconciliation-assistant.lovable.app

---

## Problem Statement

Reconciling GSTR-2B (auto-populated ITC data from the GST portal) against a client's Purchase Register is one of the most repetitive and error-prone tasks in GST compliance work. Practicing Chartered Accountants routinely have to manually cross-check hundreds of invoices to identify:

- Invoices where the supplier hasn't filed their return (ITC at risk)
- Invoices recorded in books but missing from GSTR-2B
- Invoices present in GSTR-2B but not recorded in the client's books
- Amount or tax mismatches between the two sources
- Invoices marked ITC-ineligible (e.g., blocked credit under Section 17(5))

Doing this manually in Excel is slow, and small errors (like duplicate entries or invoice number formatting differences) are easy to miss — leading to incorrect ITC claims or missed follow-ups with non-compliant suppliers.

## Solution

This tool is a web-based GST Reconciliation Assistant that lets a user upload two files — a GSTR-2B export and a Purchase Register — and automatically:

1. Matches invoices using GSTIN + Invoice Number, with normalization to handle formatting differences (spacing, case, leading zeros)
2. Categorizes every invoice into: Matched, Amount Mismatch, Missing in 2B, Missing in Books, ITC Ineligible, Duplicate in Books, or Duplicate in 2B
3. Displays a summary dashboard (total invoices compared, % matched, total ITC at risk)
4. Provides a searchable, filterable detailed table with an Excel export option
5. Generates an AI-written plain-English summary of key risk areas and suggested follow-up actions

## Key Design Decisions

- **File upload only, no GST portal login integration.** The GST portal does not offer open API access for individual applications — programmatic access is only available through licensed GSPs (GST Suvidha Providers) under a formal agreement with GSTN. Asking users to enter GST portal credentials into a third-party app would be a security and compliance risk. Instead, users export their GSTR-2B directly from the portal and upload it here. A production version could integrate via a licensed GSP/ASP API for direct auto-fetch.
- **Duplicate detection.** Testing uncovered that duplicate invoice entries in the Purchase Register (a common real-world data entry error) could otherwise be double-matched against a single GSTR-2B invoice, causing duplicate ITC claims. The tool now detects and separately flags duplicate entries before matching.

## Tech Stack

Built using Lovable (AI-assisted no-code development platform), with client-side file parsing and matching logic, and an LLM-powered summary generation feature.

## How to Use

1. Open the live app link above
2. Upload your GSTR-2B export (Excel/CSV) and Purchase Register (Excel/CSV)
3. Review the reconciliation dashboard and detailed table
4. Export the report to Excel, or generate an AI summary note

## Future Scope

- Direct GSP/ASP API integration for automated GSTR-2B fetch
- Multi-period/multi-GSTIN reconciliation for firms handling multiple clients
- Automated email follow-up drafts to non-compliant suppliers
- Historical trend tracking of supplier filing compliance
