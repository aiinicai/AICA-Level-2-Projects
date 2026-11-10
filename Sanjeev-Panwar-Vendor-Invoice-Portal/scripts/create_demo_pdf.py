"""Create fictional PDF invoices/PO using installed PyMuPDF; no real vendor data."""
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parent.parent
out=ROOT/'local_demo'/'demo_documents';out.mkdir(parents=True,exist_ok=True)
def make(name,lines):
    d=fitz.open();page=d.new_page(width=595,height=842)
    y=70
    for line in lines:
        page.insert_text((45,y),line,fontsize=12,fontname='helv');y+=28
    d.save(str(out/name));d.close()
make('demo_invoice.pdf',['INVOICE','From: Demo Vendor Supplies Ltd','Vendor PIN: P987654321Z','Bill To: Demo Group Company 01 Ltd','Recipient KRA PIN: A000000001B','Invoice No: INV-DEMO-0001','Invoice Date: 2026-11-05','PO Number: PO-DEMO-101','Currency: KES','Net Amount: 1000.00','VAT: 160.00','Grand Total: 1160.00'])
make('demo_purchase_order.pdf',['PURCHASE ORDER','Customer: Demo Group Company 01 Ltd','Supplier: Demo Vendor Supplies Ltd','PO Number: PO-DEMO-101','Currency: KES','Total: 1160.00'])
make('demo_invalid_pin_invoice.pdf',['INVOICE','From: Demo Vendor Supplies Ltd','Vendor PIN: P987654321Z','Bill To: Demo Group Company 01 Ltd','Recipient KRA PIN: A999999999B','Invoice No: INV-BAD-0001','Invoice Date: 2026-11-05','Currency: KES','Grand Total: 1160.00'])
print('Demo documents created in:',out)
