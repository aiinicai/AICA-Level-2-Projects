# User guide

## Which challan do I need?
* **Returnable (MRC)** - goods will come back (calibration, rework, returnable packing/pallets). Use only when the ERP cannot issue it (usually the receiver isn't an ERP vendor yet). Extra mandatory fields: reason and goods category (corrective action, owner, target date and expected return date are optional).
* **Non-returnable (MNRC)** - e.g. returning customer material after rework, returning a sister entity's laptop. Needs a reason / business justification.

## Create a challan
1. **+ New** -> Returnable or Non-returnable.
2. Choose the plant, date, then **type in the vendor box**. Pick from the list. If the vendor isn't there, choose *"…add as a new vendor"*, confirm the warning, fill the details (GSTIN is checked; state must match its first two digits). Duplicates by GSTIN are refused; similar names ask you to confirm.
3. Place of supply defaults to the vendor's state. The screen shows **Intra-state (CGST+SGST)** or **Inter-state (IGST)** automatically.
4. Enter purpose, reason, transport, reference document (e.g. customer's challan no./date for returns after rework), and the line items (part no., description, HSN 4/6/8 digits, qty, UoM, rate, GST %). Tax is computed by the system.
5. **Save as draft** (no number yet) or **Save & issue**, which assigns the number (e.g. `MRC/26-27/0007`).
6. If a returnable challan to an ERP-registered vendor is refused, create it in the ERP instead (only Admin can override).

## After issuing
* **Print / PDF**: opens 3 copies (Original for Consignee, Duplicate for Transporter, Triplicate for Consignor). Press Ctrl+P and pick a printer or *Save as PDF*.
* **E-way bill**: generate it on the government portal using the challan number, then enter number, date and valid-up-to on the challan. Until then it shows in **Pending E-way bill** (also the amber badge at the top).
* **Goods received back (returnable)**: enter date, our GRN/receiving reference and quantity per line; partial receipts are fine. Status moves Open -> Partially Received -> Closed.
* **Cancel** (Approver): give a reason. The number stays, the challan is marked CANCELLED and prints with a watermark. If an e-way bill exists, cancel it on the portal too (within 24 h). A challan with goods already received can't be cancelled.
* **Editing**: drafts are freely editable. Once issued, only Admin can edit (everything is logged).

## When the vendor gets created in the ERP
Open the vendor (Vendors menu) -> enter the **ERP vendor number** -> Save. From then on new *returnable* manual challans to that vendor are blocked; non-returnable are still allowed.

## Find things
**Challans** page filters: number/vendor/e-way no., part number, type, status, e-way status, return status, dates.

## Reports (all have Export to Excel)
Monthly register · Date-range register · GSTR-1 Table 13 (documents issued: first/last, total, cancelled, net, cancelled numbers, gaps) · Pending e-way bill · Open/overdue returnables (with statutory 1-year/3-year limit) · Vendor master export.

## Dashboard
Monthly trend (returnable vs non-returnable), reasons, top vendors, vendors not yet in ERP, pending e-way bills, open returnables. Filter by period, type, plant. The goal: push the "not in ERP" list and returnable count down.

## Excel upload
**Excel upload** menu -> download template -> fill -> upload. You get a full error report (row-by-row, downloadable) and **nothing is saved until the file is error-free and you click Commit**. Historical challans keep their numbers, and new numbers continue after the highest uploaded one. Vendors must exist before challans reference them. Upload historical challans in numeric order of preparation if possible, and note: blank e-way bill numbers will show as Pending.

## Admin
Users and roles · Plants/GSTINs · Numbering format (max 16 characters enforced) · Audit log.
