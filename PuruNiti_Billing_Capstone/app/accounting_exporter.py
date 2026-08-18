import os
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom

def format_date_tally(date_str):
    """Converts yyyy-mm-dd to Tally's yyyymmdd format."""
    if not date_str:
        return ""
    return date_str.replace("-", "").replace("/", "")

def generate_tally_xml(invoices, output_path):
    """Generates Tally XML files for both Masters and Vouchers to ensure smooth import."""
    company_name = "My Company"
    if invoices:
        company_name = invoices[0].get("seller", {}).get("trade_name", "My Company")

    # 1. ACCUMULATE LEDGERS
    used_ledgers = set()
    customer_names = set()
    for inv in invoices:
        cust = inv.get("customer", {})
        cust_name = cust.get("name", "Unknown Customer").strip()
        if cust_name:
            customer_names.add(cust_name)
        summary = inv.get("summary", {})
        is_service = (inv.get("invoice_type") == "Services")
        is_rcm = inv.get("rcm", False)
        
        if is_service:
            used_ledgers.add(("Services Sales Account", "Sales Accounts"))
        else:
            used_ledgers.add(("Goods Sales Account", "Sales Accounts"))
            
        if not is_rcm:
            if float(summary.get("cgst_total", 0.0)) > 0:
                used_ledgers.add(("Output CGST", "Duties & Taxes"))
            if float(summary.get("sgst_total", 0.0)) > 0:
                used_ledgers.add(("Output SGST", "Duties & Taxes"))
            if float(summary.get("igst_total", 0.0)) > 0:
                used_ledgers.add(("Output IGST", "Duties & Taxes"))
        if float(summary.get("cess_total", 0.0)) > 0:
            used_ledgers.add(("Output GST Cess", "Duties & Taxes"))
        if float(summary.get("round_off", 0.0)) != 0:
            used_ledgers.add(("Round Off Account", "Indirect Expenses"))

    # Determine master & voucher paths
    base, ext = os.path.splitext(output_path)
    masters_path = f"{base}_Masters.xml"
    vouchers_path = f"{base}_Vouchers.xml"

    # --- 2. GENERATE MASTERS XML ---
    env_m = ET.Element("ENVELOPE")
    hdr_m = ET.SubElement(env_m, "HEADER")
    ET.SubElement(hdr_m, "VERSION").text = "1"
    ET.SubElement(hdr_m, "TALLYREQUEST").text = "Import"
    ET.SubElement(hdr_m, "TYPE").text = "Data"
    ET.SubElement(hdr_m, "ID").text = "All Masters"
    
    body_m = ET.SubElement(env_m, "BODY")
    desc_m = ET.SubElement(body_m, "DESC")
    sv_m = ET.SubElement(desc_m, "STATICVARIABLES")
    ET.SubElement(sv_m, "SVCURRENTCOMPANY").text = company_name
    data_m = ET.SubElement(body_m, "DATA")

    # Standard Ledgers
    for name, parent in sorted(used_ledgers):
        msg = ET.SubElement(data_m, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        ledger = ET.SubElement(msg, "LEDGER", {"NAME": name, "ACTION": "Create"})
        ET.SubElement(ledger, "NAME").text = name
        ET.SubElement(ledger, "PARENT").text = parent
        ET.SubElement(ledger, "AFFECTSSTOCK").text = "No"

    # Customer Ledgers
    for cust_name in sorted(customer_names):
        msg = ET.SubElement(data_m, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        ledger = ET.SubElement(msg, "LEDGER", {"NAME": cust_name, "ACTION": "Create"})
        ET.SubElement(ledger, "NAME").text = cust_name
        ET.SubElement(ledger, "PARENT").text = "Sundry Debtors"
        ET.SubElement(ledger, "ISBILLWISEON").text = "Yes"
        ET.SubElement(ledger, "AFFECTSSTOCK").text = "No"

    raw_m = ET.tostring(env_m, 'utf-8')
    parsed_m = minidom.parseString(raw_m)
    pretty_m = parsed_m.toprettyxml(indent="  ")
    with open(masters_path, "w", encoding="utf-8") as f:
        f.write(pretty_m)

    # --- 3. GENERATE VOUCHERS XML ---
    env_v = ET.Element("ENVELOPE")
    hdr_v = ET.SubElement(env_v, "HEADER")
    ET.SubElement(hdr_v, "VERSION").text = "1"
    ET.SubElement(hdr_v, "TALLYREQUEST").text = "Import"
    ET.SubElement(hdr_v, "TYPE").text = "Data"
    ET.SubElement(hdr_v, "ID").text = "Vouchers"
    
    body_v = ET.SubElement(env_v, "BODY")
    desc_v = ET.SubElement(body_v, "DESC")
    sv_v = ET.SubElement(desc_v, "STATICVARIABLES")
    ET.SubElement(sv_v, "SVCURRENTCOMPANY").text = company_name
    data_v = ET.SubElement(body_v, "DATA")

    for inv in invoices:
        tally_msg = ET.SubElement(data_v, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        
        # Voucher Attributes
        voucher = ET.SubElement(tally_msg, "VOUCHER", {
            "VCHTYPE": "Sales",
            "ACTION": "Create",
            "OBJTYPE": "Voucher"
        })
        
        inv_no = inv.get("invoice_number", "")
        date_raw = inv.get("date", "")
        date_tally = format_date_tally(date_raw)
        customer = inv.get("customer", {})
        cust_name = customer.get("name", "Unknown Customer")
        place_of_supply = inv.get("place_of_supply", "")
        if "(" in place_of_supply:
            place_of_supply = place_of_supply.split("(")[0].strip()
        
        summary = inv.get("summary", {})
        grand_total = float(summary.get("grand_total", 0.0))
        subtotal = float(summary.get("subtotal", 0.0))
        cgst = float(summary.get("cgst_total", 0.0))
        sgst = float(summary.get("sgst_total", 0.0))
        igst = float(summary.get("igst_total", 0.0))
        cess = float(summary.get("cess_total", 0.0))
        round_off = float(summary.get("round_off", 0.0))
        is_rcm = inv.get("rcm", False)
        
        # Basic Voucher details
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = "Sales"
        ET.SubElement(voucher, "DATE").text = date_tally
        ET.SubElement(voucher, "VOUCHERNUMBER").text = inv_no
        ET.SubElement(voucher, "REFERENCE").text = inv_no
        ET.SubElement(voucher, "PARTYLEDGERNAME").text = cust_name
        ET.SubElement(voucher, "EFFECTIVEDATE").text = date_tally
        ET.SubElement(voucher, "PERSISTEDVIEW").text = "Accounting Voucher View"
        ET.SubElement(voucher, "PLACEOFSUPPLY").text = place_of_supply
        
        # Narration
        item_names = [f"{item.get('name', '')} (Qty: {item.get('qty', 0)})" for item in inv.get("items", [])]
        narration_text = f"Being sales of: {', '.join(item_names)}"
        ET.SubElement(voucher, "NARRATION").text = narration_text
        
        # Add RCM flag if yes
        if is_rcm:
            ET.SubElement(voucher, "ISREVERSECHARGEAPPLICABLE").text = "Yes"
            
        # Ledgers Listing
        # 1. Debit Party Ledger (Negative in Tally Sales)
        debit_amt = grand_total
        
        party_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
        ET.SubElement(party_entry, "LEDGERNAME").text = cust_name
        ET.SubElement(party_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(party_entry, "AMOUNT").text = f"-{debit_amt:.2f}"
        
        # 2. Credit Sales Ledger (Positive in Tally Sales)
        sales_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
        is_service = (inv.get("invoice_type") == "Services")
        sales_ledger = "Services Sales Account" if is_service else "Goods Sales Account"
        ET.SubElement(sales_entry, "LEDGERNAME").text = sales_ledger
        ET.SubElement(sales_entry, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(sales_entry, "AMOUNT").text = f"{subtotal:.2f}"
        
        # 3. Credit CGST Ledger (if positive and NOT RCM)
        if cgst > 0 and not is_rcm:
            cgst_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
            cgst_ledger = "Output CGST"
            ET.SubElement(cgst_entry, "LEDGERNAME").text = cgst_ledger
            ET.SubElement(cgst_entry, "ISDEEMEDPOSITIVE").text = "No"
            ET.SubElement(cgst_entry, "AMOUNT").text = f"{cgst:.2f}"
            
        # 4. Credit SGST Ledger (if positive and NOT RCM)
        if sgst > 0 and not is_rcm:
            sgst_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
            sgst_ledger = "Output SGST"
            ET.SubElement(sgst_entry, "LEDGERNAME").text = sgst_ledger
            ET.SubElement(sgst_entry, "ISDEEMEDPOSITIVE").text = "No"
            ET.SubElement(sgst_entry, "AMOUNT").text = f"{sgst:.2f}"
            
        # 5. Credit IGST Ledger (if positive and NOT RCM)
        if igst > 0 and not is_rcm:
            igst_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
            igst_ledger = "Output IGST"
            ET.SubElement(igst_entry, "LEDGERNAME").text = igst_ledger
            ET.SubElement(igst_entry, "ISDEEMEDPOSITIVE").text = "No"
            ET.SubElement(igst_entry, "AMOUNT").text = f"{igst:.2f}"
            
        # 6. Credit Cess Ledger (if positive)
        if cess > 0:
            cess_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
            ET.SubElement(cess_entry, "LEDGERNAME").text = "Output GST Cess"
            ET.SubElement(cess_entry, "ISDEEMEDPOSITIVE").text = "No"
            ET.SubElement(cess_entry, "AMOUNT").text = f"{cess:.2f}"
            
        # 7. Round off Ledger (if present)
        if round_off != 0:
            ro_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
            ET.SubElement(ro_entry, "LEDGERNAME").text = "Round Off Account"
            ET.SubElement(ro_entry, "ISDEEMEDPOSITIVE").text = "Yes" if round_off < 0 else "No"
            ET.SubElement(ro_entry, "AMOUNT").text = f"{round_off:.2f}"

    raw_v = ET.tostring(env_v, 'utf-8')
    parsed_v = minidom.parseString(raw_v)
    pretty_v = parsed_v.toprettyxml(indent="  ")
    with open(vouchers_path, "w", encoding="utf-8") as f:
        f.write(pretty_v)

    return True

def generate_accounting_csv(invoices, output_path):
    """Generates a standard CSV import file compatible with Zoho Books/QuickBooks."""
    headers = [
        "Invoice Number", "Date", "Invoice Type", "GST Treatment", "Reverse Charge (RCM)", 
        "Place of Supply", "Customer Name", "Customer Mobile", "Customer GSTIN", 
        "Taxable Value", "CGST Amount", "SGST Amount", "IGST Amount", "Cess Amount", "Round Off", "Grand Total"
    ]
    
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for inv in invoices:
                customer = inv.get("customer", {})
                summary = inv.get("summary", {})
                
                writer.writerow([
                    inv.get("invoice_number", ""),
                    inv.get("date", ""),
                    inv.get("invoice_type", "Goods"),
                    inv.get("gst_treatment", "CGST_SGST"),
                    "Yes" if inv.get("rcm", False) else "No",
                    inv.get("place_of_supply", ""),
                    customer.get("name", ""),
                    customer.get("mobile", ""),
                    customer.get("gstin", ""),
                    f"{summary.get('subtotal', 0.0):.2f}",
                    f"{summary.get('cgst_total', 0.0):.2f}",
                    f"{summary.get('sgst_total', 0.0):.2f}",
                    f"{summary.get('igst_total', 0.0):.2f}",
                    f"{summary.get('cess_total', 0.0):.2f}",
                    f"{summary.get('round_off', 0.0):+.2f}",
                    f"{summary.get('grand_total', 0.0):.2f}"
                ])
        return True
    except Exception as e:
        print(f"Error exporting CSV: {e}")
        return False
