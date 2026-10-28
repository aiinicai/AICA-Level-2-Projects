"""
Synthetic Demo Data Generator for MarketMatch.
Produces exact real-world formatted files:
1. demo_mtr.csv: MTR sales with 60 B2C orders across 2 months (March & April 2026).
2. demo_gst_rtf.xlsx: GST Ready-to-File Excel with B2CS, B2CL, CDNUR, and HSN Summary sheets.
3. demo_payments.csv: Unified Payments CSV with preamble, released and deferred transactions.

Planted Issues:
- 45 clean orders (including 1 B2CL > 1,00,000 with a CDNUR refund)
- 3 not paid (order older than 10 days, 0 payment rows)
- 2 short paid (fees higher by 50 and 120)
- 1 duplicate payout (2 released payout rows for same order)
- 2 refunds without credit note (return rows missing credit note no)
- 2 sales missing from GST data (in MTR, omitted from GST RTF)
- 1 B2C Small state/rate group discrepancy (state 27, 18% slab)
- 1 HSN tax-column gap (tax columns sum 291.94 lower than taxable x rate)
- 1 TCS at double statutory amount (1.0% instead of 0.5%)
- 2 deferred payouts (Transaction Status = Deferred, classified as Timing)
- 2 month-end timing differences (sale in March, payout in April)
- 1 invoice reported in wrong GST month (March sale reported in April GST)
- 1 payout row with no order ID
"""
import os
import random
from decimal import Decimal
import pandas as pd
import openpyxl

SEED = 42

DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demo")


def generate_all_demo_data(target_dir: str = DEMO_DIR):
    random.seed(SEED)
    os.makedirs(target_dir, exist_ok=True)

    seller_gstin = "33AAJFI0296H1ZE"
    ship_from_state = "TAMIL NADU"
    ship_from_code = "33"

    states_pool = [
        ("33", "TAMIL NADU"),
        ("29", "KARNATAKA"),
        ("27", "MAHARASHTRA"),
        ("09", "UTTAR PRADESH"),
        ("19", "WEST BENGAL"),
        ("32", "KERALA")
    ]

    hsn_catalog = [
        {"hsn": "33049990", "rate": Decimal("0.18"), "sku": "Face Glow Serum", "price": Decimal("359.00")},
        {"hsn": "33049930", "rate": Decimal("0.18"), "sku": "HYDRA COOL MOISTURIZER", "price": Decimal("360.00")},
        {"hsn": "34011110", "rate": Decimal("0.05"), "sku": "Handmade Herbal Soap", "price": Decimal("210.00")},
        {"hsn": "33051090", "rate": Decimal("0.18"), "sku": "Nourishing Hair Cleanser", "price": Decimal("450.00")}
    ]

    # Assign orders
    # Month 1: March 2026 (35 orders)
    # Month 2: April 2026 (25 orders)
    orders = []

    # Helper to pick state (interstate or intrastate)
    def pick_state(interstate_only=False):
        if interstate_only:
            sub = [s for s in states_pool if s[0] != "33"]
            return random.choice(sub)
        return random.choice(states_pool)

    # 1. 45 Clean Orders (one of which is B2CL > 1,00,000)
    for i in range(1, 46):
        oid = f"402-{1000000 + i}-000{i:04d}"
        inv_no = f"IN-2026-{100 + i}"
        m = 3 if i <= 25 else 4
        if i == 24:
            d = 30
            inv_date = "2026-03-30 18:00:00"
        elif i == 25:
            d = 31
            inv_date = "2026-03-31 19:30:00"
        else:
            d = random.randint(1, 28)
            inv_date = f"2026-{m:02d}-{d:02d} 11:20:00"

        if i == 1:
            # The B2CL Order (> 1,00,000) with refund
            item = hsn_catalog[0]
            qty = 300
            price = Decimal("360.00")
            inv_amount = Decimal("108000.00")  # > 1,00,000
            taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
            tot_tax = inv_amount - taxable
            pos_code, pos_name = ("27", "MAHARASHTRA")  # interstate
            orders.append({
                "type": "b2cl_clean",
                "order_id": oid,
                "inv_no": inv_no,
                "inv_date": inv_date,
                "month": m,
                "pos_code": pos_code,
                "pos_name": pos_name,
                "item": item,
                "qty": qty,
                "inv_amount": inv_amount,
                "taxable": taxable,
                "tax": tot_tax,
                "has_refund": True,
                "refund_amount": Decimal("18000.00"),
                "cn_no": "CN-2026-001"
            })
        else:
            item = random.choice(hsn_catalog)
            qty = random.randint(1, 2)
            inv_amount = item["price"] * qty
            taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
            tot_tax = inv_amount - taxable
            pos_code, pos_name = pick_state()
            orders.append({
                "type": "clean",
                "order_id": oid,
                "inv_no": inv_no,
                "inv_date": inv_date,
                "month": m,
                "pos_code": pos_code,
                "pos_name": pos_name,
                "item": item,
                "qty": qty,
                "inv_amount": inv_amount,
                "taxable": taxable,
                "tax": tot_tax,
                "has_refund": False
            })

    # 2. 3 Not Paid Orders (older than 10 days, in March 2026)
    for i in range(46, 49):
        oid = f"403-{1000000 + i}-000{i:04d}"
        inv_no = f"IN-2026-{100 + i}"
        item = random.choice(hsn_catalog)
        qty = 1
        inv_amount = item["price"]
        taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
        tot_tax = inv_amount - taxable
        pos_code, pos_name = pick_state()
        orders.append({
            "type": "not_paid",
            "order_id": oid,
            "inv_no": inv_no,
            "inv_date": f"2026-03-{i-40:02d} 14:10:00",
            "month": 3,
            "pos_code": pos_code,
            "pos_name": pos_name,
            "item": item,
            "qty": qty,
            "inv_amount": inv_amount,
            "taxable": taxable,
            "tax": tot_tax,
            "has_refund": False
        })

    # 3. 2 Short Paid Orders (fees short by 50 and 120)
    for idx, i in enumerate(range(49, 51)):
        oid = f"404-{1000000 + i}-000{i:04d}"
        inv_no = f"IN-2026-{100 + i}"
        item = random.choice(hsn_catalog)
        qty = 2
        inv_amount = item["price"] * qty
        taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
        tot_tax = inv_amount - taxable
        pos_code, pos_name = pick_state()
        orders.append({
            "type": "short_paid",
            "short_amount": Decimal("50.00") if idx == 0 else Decimal("120.00"),
            "order_id": oid,
            "inv_no": inv_no,
            "inv_date": f"2026-03-{15 + idx:02d} 10:00:00",
            "month": 3,
            "pos_code": pos_code,
            "pos_name": pos_name,
            "item": item,
            "qty": qty,
            "inv_amount": inv_amount,
            "taxable": taxable,
            "tax": tot_tax,
            "has_refund": False
        })

    # 4. 1 Duplicate Payout Order
    i = 51
    oid = f"405-{1000000 + i}-000{i:04d}"
    inv_no = f"IN-2026-{100 + i}"
    item = random.choice(hsn_catalog)
    qty = 1
    inv_amount = item["price"]
    taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
    orders.append({
        "type": "duplicate_payout",
        "order_id": oid,
        "inv_no": inv_no,
        "inv_date": "2026-03-18 16:00:00",
        "month": 3,
        "pos_code": "33",
        "pos_name": "TAMIL NADU",
        "item": item,
        "qty": qty,
        "inv_amount": inv_amount,
        "taxable": taxable,
        "tax": inv_amount - taxable,
        "has_refund": False
    })

    # 5. 2 Refunds Without Credit Note
    for idx, i in enumerate(range(52, 54)):
        oid = f"406-{1000000 + i}-000{i:04d}"
        inv_no = f"IN-2026-{100 + i}"
        item = random.choice(hsn_catalog)
        qty = 1
        inv_amount = item["price"]
        taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
        orders.append({
            "type": "refund_without_cn",
            "order_id": oid,
            "inv_no": inv_no,
            "inv_date": f"2026-03-{20 + idx:02d} 09:30:00",
            "month": 3,
            "pos_code": "29",
            "pos_name": "KARNATAKA",
            "item": item,
            "qty": qty,
            "inv_amount": inv_amount,
            "taxable": taxable,
            "tax": inv_amount - taxable,
            "has_refund": True,
            "refund_amount": inv_amount,
            "cn_no": ""  # Missing Credit Note Number!
        })

    # 6. 2 Sales Missing from GST Data
    for idx, i in enumerate(range(54, 56)):
        oid = f"407-{1000000 + i}-000{i:04d}"
        inv_no = f"IN-2026-{100 + i}"
        item = random.choice(hsn_catalog)
        qty = 1
        inv_amount = item["price"]
        taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
        orders.append({
            "type": "missing_in_gst",
            "order_id": oid,
            "inv_no": inv_no,
            "inv_date": f"2026-03-{22 + idx:02d} 11:45:00",
            "month": 3,
            "pos_code": "07",
            "pos_name": "DELHI",
            "item": item,
            "qty": qty,
            "inv_amount": inv_amount,
            "taxable": taxable,
            "tax": inv_amount - taxable,
            "has_refund": False
        })

    # 7. 1 B2C Small state/rate group discrepancy order
    i = 56
    oid = f"408-{1000000 + i}-000{i:04d}"
    inv_no = f"IN-2026-{100 + i}"
    item = hsn_catalog[0]  # 18%
    qty = 2
    inv_amount = item["price"] * qty
    taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
    orders.append({
        "type": "b2cs_diff",
        "order_id": oid,
        "inv_no": inv_no,
        "inv_date": "2026-03-24 15:20:00",
        "month": 3,
        "pos_code": "27",
        "pos_name": "MAHARASHTRA",
        "item": item,
        "qty": qty,
        "inv_amount": inv_amount,
        "taxable": taxable,
        "tax": inv_amount - taxable,
        "has_refund": False
    })

    # 8. 1 TCS at Double Statutory Rate (1.0% instead of 0.5%)
    i = 57
    oid = f"409-{1000000 + i}-000{i:04d}"
    inv_no = f"IN-2026-{100 + i}"
    item = random.choice(hsn_catalog)
    qty = 2
    inv_amount = item["price"] * qty
    taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
    orders.append({
        "type": "double_tcs",
        "order_id": oid,
        "inv_no": inv_no,
        "inv_date": "2026-03-25 12:10:00",
        "month": 3,
        "pos_code": "33",
        "pos_name": "TAMIL NADU",
        "item": item,
        "qty": qty,
        "inv_amount": inv_amount,
        "taxable": taxable,
        "tax": inv_amount - taxable,
        "has_refund": False
    })

    # 9. 2 Deferred Payouts (Transaction Status = Deferred)
    for idx, i in enumerate(range(58, 60)):
        oid = f"410-{1000000 + i}-000{i:04d}"
        inv_no = f"IN-2026-{100 + i}"
        item = random.choice(hsn_catalog)
        qty = 1
        inv_amount = item["price"]
        taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
        orders.append({
            "type": "deferred",
            "order_id": oid,
            "inv_no": inv_no,
            "inv_date": f"2026-04-{26 + idx:02d} 18:00:00",
            "month": 4,
            "pos_code": "33",
            "pos_name": "TAMIL NADU",
            "item": item,
            "qty": qty,
            "inv_amount": inv_amount,
            "taxable": taxable,
            "tax": inv_amount - taxable,
            "has_refund": False
        })

    # 10. 1 Invoice Reported in Wrong GST Month (Sale in March, reported in April GST)
    i = 60
    oid = f"411-{1000000 + i}-000{i:04d}"
    inv_no = f"IN-2026-{100 + i}"
    item = random.choice(hsn_catalog)
    qty = 1
    inv_amount = item["price"]
    taxable = (inv_amount / (Decimal("1.00") + item["rate"])).quantize(Decimal("0.01"))
    orders.append({
        "type": "wrong_gst_month",
        "order_id": oid,
        "inv_no": inv_no,
        "inv_date": "2026-03-29 17:30:00",  # March
        "month": 3,
        "gst_month": 4,  # April GST
        "pos_code": "36",
        "pos_name": "TELANGANA",
        "item": item,
        "qty": qty,
        "inv_amount": inv_amount,
        "taxable": taxable,
        "tax": inv_amount - taxable,
        "has_refund": False
    })

    # Note: 2 Month-End Timing Differences (Sale on 30th/31st March, Payout in April)
    # We assign order 44 and order 45 (which are clean March orders) to have settlement date in April!

    # =========================================================================
    # BUILD FILE 1: MTR CSV (demo_mtr.csv)
    # =========================================================================
    mtr_rows = []
    mtr_headers = [
        "Seller Gstin", "Invoice Number", "Invoice Date", "Transaction Type", "Order Id",
        "Shipment Id", "Shipment Date", "Order Date", "Shipment Item Id", "Quantity",
        "Item Description", "Asin", "Hsn/sac", "Sku", "Product Tax Code",
        "Bill From City", "Bill From State", "Bill From Country", "Bill From Postal Code",
        "Ship From City", "Ship From State", "Ship From Country", "Ship From Postal Code",
        "Ship To City", "Ship To State", "Ship To Country", "Ship To Postal Code",
        "Invoice Amount", "Tax Exclusive Gross", "Total Tax Amount",
        "Cgst Rate", "Sgst Rate", "Utgst Rate", "Igst Rate", "Compensatory Cess Rate",
        "Principal Amount", "Principal Amount Basis",
        "Cgst Tax", "Sgst Tax", "Igst Tax", "Utgst Tax", "Compensatory Cess Tax",
        "Shipping Amount", "Shipping Amount Basis",
        "Shipping Cgst Tax", "Shipping Sgst Tax", "Shipping Utgst Tax", "Shipping Igst Tax", "Shipping Cess Tax Amount",
        "Gift Wrap Amount", "Gift Wrap Amount Basis",
        "Gift Wrap Cgst Tax", "Gift Wrap Sgst Tax", "Gift Wrap Utgst Tax", "Gift Wrap Igst Tax", "Gift Wrap Compensatory Cess Tax",
        "Item Promo Discount", "Item Promo Discount Basis", "Item Promo Tax",
        "Shipping Promo Discount", "Shipping Promo Discount Basis", "Shipping Promo Tax",
        "Gift Wrap Promo Discount", "Gift Wrap Promo Discount Basis", "Gift Wrap Promo Tax",
        "Tcs Cgst Rate", "Tcs Cgst Amount", "Tcs Sgst Rate", "Tcs Sgst Amount",
        "Tcs Utgst Rate", "Tcs Utgst Amount", "Tcs Igst Rate", "Tcs Igst Amount",
        "Warehouse Id", "Fulfillment Channel", "Payment Method Code", "Credit Note No", "Credit Note Date"
    ]

    for ord_data in orders:
        is_interstate = (ord_data["pos_code"] != ship_from_code)
        rate = ord_data["item"]["rate"]

        cgst_rate = (rate / Decimal("2.00")) if not is_interstate else Decimal("0.00")
        sgst_rate = (rate / Decimal("2.00")) if not is_interstate else Decimal("0.00")
        igst_rate = rate if is_interstate else Decimal("0.00")

        taxable = ord_data["taxable"]
        tax = ord_data["tax"]
        cgst_tax = (tax / Decimal("2.00")).quantize(Decimal("0.01")) if not is_interstate else Decimal("0.00")
        sgst_tax = (tax - cgst_tax) if not is_interstate else Decimal("0.00")
        igst_tax = tax if is_interstate else Decimal("0.00")

        # TCS calculation (0.5% statutory, or double for double_tcs)
        tcs_mult = Decimal("0.01") if ord_data["type"] == "double_tcs" else Decimal("0.005")
        tcs_cgst_rate = (tcs_mult / Decimal("2.00")) if not is_interstate else Decimal("0.00")
        tcs_sgst_rate = (tcs_mult / Decimal("2.00")) if not is_interstate else Decimal("0.00")
        tcs_igst_rate = tcs_mult if is_interstate else Decimal("0.00")

        tcs_cgst_amt = (taxable * tcs_cgst_rate).quantize(Decimal("0.01"))
        tcs_sgst_amt = (taxable * tcs_sgst_rate).quantize(Decimal("0.01"))
        tcs_igst_amt = (taxable * tcs_igst_rate).quantize(Decimal("0.01"))

        # Sale Row
        row_sale = [
            seller_gstin, ord_data["inv_no"], ord_data["inv_date"], "Shipment", ord_data["order_id"],
            f"SHIP-{ord_data['order_id'][-6:]}", ord_data["inv_date"], ord_data["inv_date"], "ITEM-01", ord_data["qty"],
            ord_data["item"]["sku"], "B0D54FXTW9", ord_data["item"]["hsn"], ord_data["item"]["sku"], "A_GEN_STANDARD",
            "CHENNAI", ship_from_state, "IN", "600012",
            "CHENNAI", ship_from_state, "IN", "600012",
            "CITY", ord_data["pos_name"], "IN", "500001",
            float(ord_data["inv_amount"]), float(taxable), float(tax),
            float(cgst_rate), float(sgst_rate), 0.0, float(igst_rate), 0.0,
            float(ord_data["inv_amount"]), float(taxable),
            float(cgst_tax), float(sgst_tax), float(igst_tax), 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            float(tcs_cgst_rate), float(tcs_cgst_amt), float(tcs_sgst_rate), float(tcs_sgst_amt),
            0.0, 0.0, float(tcs_igst_rate), float(tcs_igst_amt),
            "WAREHOUSE-1", "MFN", "COD", "", ""
        ]
        mtr_rows.append(row_sale)

        # Refund Row if present
        if ord_data.get("has_refund"):
            ref_amt = ord_data.get("refund_amount", ord_data["inv_amount"])
            ref_taxable = (ref_amt / (Decimal("1.00") + rate)).quantize(Decimal("0.01"))
            ref_tax = ref_amt - ref_taxable
            ref_cgst = (ref_tax / Decimal("2.00")).quantize(Decimal("0.01")) if not is_interstate else Decimal("0.00")
            ref_sgst = (ref_tax - ref_cgst) if not is_interstate else Decimal("0.00")
            ref_igst = ref_tax if is_interstate else Decimal("0.00")
            cn_num = ord_data.get("cn_no", "")
            cn_dt = ord_data["inv_date"] if cn_num else ""

            row_refund = [
                seller_gstin, ord_data["inv_no"], ord_data["inv_date"], "Refund", ord_data["order_id"],
                f"SHIP-{ord_data['order_id'][-6:]}", ord_data["inv_date"], ord_data["inv_date"], "ITEM-01", -1,
                ord_data["item"]["sku"], "B0D54FXTW9", ord_data["item"]["hsn"], ord_data["item"]["sku"], "A_GEN_STANDARD",
                "CHENNAI", ship_from_state, "IN", "600012",
                "CHENNAI", ship_from_state, "IN", "600012",
                "CITY", ord_data["pos_name"], "IN", "500001",
                -float(ref_amt), -float(ref_taxable), -float(ref_tax),
                float(cgst_rate), float(sgst_rate), 0.0, float(igst_rate), 0.0,
                -float(ref_amt), -float(ref_taxable),
                -float(ref_cgst), -float(ref_sgst), -float(ref_igst), 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                float(tcs_cgst_rate), -float((ref_taxable * tcs_cgst_rate).quantize(Decimal("0.01"))),
                float(tcs_sgst_rate), -float((ref_taxable * tcs_sgst_rate).quantize(Decimal("0.01"))),
                0.0, 0.0,
                float(tcs_igst_rate), -float((ref_taxable * tcs_igst_rate).quantize(Decimal("0.01"))),
                "WAREHOUSE-1", "MFN", "COD", cn_num, cn_dt
            ]
            mtr_rows.append(row_refund)

    df_mtr = pd.DataFrame(mtr_rows, columns=mtr_headers)
    mtr_path = os.path.join(target_dir, "demo_mtr.csv")
    df_mtr.to_csv(mtr_path, index=False)

    # =========================================================================
    # BUILD FILE 2: GST READY-TO-FILE WORKBOOK (demo_gst_rtf.xlsx)
    # =========================================================================
    wb_gst = openpyxl.Workbook()
    # Sheet 1: GSTIN
    ws_gstin = wb_gst.active
    ws_gstin.title = "GSTIN"
    ws_gstin["A2"] = "Merchant GSTIN"
    ws_gstin["A3"] = seller_gstin
    ws_gstin["A5"] = "Amazon GSTR-1 Ready to file export."

    # Blank sheets
    for s_name in ["B2B", "B2B CN (cdnr)"]:
        ws = wb_gst.create_sheet(title=s_name)
        ws.cell(1, 1).value = f"Summary For {s_name}"
        ws.cell(4, 1).value = "GSTIN/UIN of Recipient"

    # Sheet: B2CL CN (cdnur)
    ws_cdnur = wb_gst.create_sheet(title="B2CL CN (cdnur)")
    ws_cdnur.cell(1, 1).value = "Summary For CDNUR"
    cdnur_headers = ["UR Type", "Note Number", "Note Date", "Note Type", "Place Of Supply", "Note Value", "Applicable % of Tax Rate", "Rate", "Taxable Value", "Cess Amount", "Invoice/Advance Receipt Number", "Invoice/Advance Receipt Date", "Reason for Issuing Document"]
    for c_i, h in enumerate(cdnur_headers, start=1):
        ws_cdnur.cell(4, c_i).value = h
    # Add B2CL refund row (Order 1)
    b2cl_ord = orders[0]
    ws_cdnur.cell(5, 1).value = "B2CL"
    ws_cdnur.cell(5, 2).value = b2cl_ord["cn_no"]
    ws_cdnur.cell(5, 3).value = "2026-03-05"
    ws_cdnur.cell(5, 4).value = "C"
    ws_cdnur.cell(5, 5).value = f"{b2cl_ord['pos_code']}-{b2cl_ord['pos_name']}"
    ws_cdnur.cell(5, 6).value = float(b2cl_ord["refund_amount"])
    ws_cdnur.cell(5, 7).value = ""
    ws_cdnur.cell(5, 8).value = float(b2cl_ord["item"]["rate"])
    ref_taxable = (b2cl_ord["refund_amount"] / (Decimal("1.00") + b2cl_ord["item"]["rate"])).quantize(Decimal("0.01"))
    ws_cdnur.cell(5, 9).value = float(ref_taxable)
    ws_cdnur.cell(5, 10).value = 0
    ws_cdnur.cell(5, 11).value = b2cl_ord["inv_no"]
    ws_cdnur.cell(5, 12).value = "2026-03-01"
    ws_cdnur.cell(5, 13).value = "Sales Return"

    # Sheet: B2C Large
    ws_b2cl = wb_gst.create_sheet(title="B2C Large")
    ws_b2cl.cell(1, 1).value = "Summary For B2CL"
    b2cl_headers = ["Invoice Number", "Invoice date", "Invoice Value", "Place Of Supply", "Applicable % of Tax Rate", "Rate", "Taxable Value", "Cess Amount", "E-Commerce GSTIN"]
    for c_i, h in enumerate(b2cl_headers, start=1):
        ws_b2cl.cell(4, c_i).value = h
    ws_b2cl.cell(5, 1).value = b2cl_ord["inv_no"]
    ws_b2cl.cell(5, 2).value = "2026-03-01"
    ws_b2cl.cell(5, 3).value = float(b2cl_ord["inv_amount"])
    ws_b2cl.cell(5, 4).value = f"{b2cl_ord['pos_code']}-{b2cl_ord['pos_name']}"
    ws_b2cl.cell(5, 5).value = ""
    ws_b2cl.cell(5, 6).value = float(b2cl_ord["item"]["rate"])
    ws_b2cl.cell(5, 7).value = float(b2cl_ord["taxable"])
    ws_b2cl.cell(5, 8).value = 0
    ws_b2cl.cell(5, 9).value = ""

    # Sheet: B2C Small
    ws_b2cs = wb_gst.create_sheet(title="B2C Small")
    ws_b2cs.cell(1, 1).value = "Summary For B2CS"
    ws_b2cs.cell(2, 5).value = "Total Taxable Value"
    b2cs_headers = ["Type", "Place Of Supply", "Applicable % of Tax Rate", "Rate", "Taxable Value", "Cess Amount", "E-Commerce GSTIN"]
    for c_i, h in enumerate(b2cs_headers, start=1):
        ws_b2cs.cell(4, c_i).value = h

    # Group sales for March (Month 3) for B2CS
    # Exclude B2CL (Order 1), Exclude Missing in GST (Orders 54, 55),
    # Exclude Wrong GST Month (Order 60) which is reported in April GST!
    b2cs_groups = {}
    for o in orders:
        if o["type"] in ("b2cl_clean", "missing_in_gst"):
            continue
        # Only include March orders (month 3), or order 60 if month 4
        if o.get("gst_month", o["month"]) != 3:
            continue

        key = (o["pos_code"], o["pos_name"], o["item"]["rate"])
        net_taxable = o["taxable"]
        if o.get("has_refund") and o["type"] != "b2cl_clean":
            ref_amt = o.get("refund_amount", o["inv_amount"])
            ref_t = (ref_amt / (Decimal("1.00") + o["item"]["rate"])).quantize(Decimal("0.01"))
            net_taxable -= ref_t

        b2cs_groups[key] = b2cs_groups.get(key, Decimal("0.00")) + net_taxable

    # Plant B2CS discrepancy in state 27 (MAHARASHTRA) 18% slab: deduct 500
    r_idx = 5
    b2cs_total_taxable_written = Decimal("0.00")
    for (pos_code, pos_name, rate), t_val in b2cs_groups.items():
        if pos_code == "27" and rate == Decimal("0.18"):
            # Planted discrepancy: reported 500 lower in GST report
            t_val = t_val - Decimal("500.00")
        
        # Add floating-point noise e.g. 11833.809999999996
        float_noise_val = float(t_val) + 0.000000000004

        ws_b2cs.cell(r_idx, 1).value = "E"
        ws_b2cs.cell(r_idx, 2).value = f"{pos_code}-{pos_name}"
        ws_b2cs.cell(r_idx, 3).value = ""
        ws_b2cs.cell(r_idx, 4).value = float(rate)
        ws_b2cs.cell(r_idx, 5).value = float_noise_val
        ws_b2cs.cell(r_idx, 6).value = 0
        ws_b2cs.cell(r_idx, 7).value = ""
        b2cs_total_taxable_written += t_val
        r_idx += 1
    ws_b2cs.cell(3, 5).value = float(b2cs_total_taxable_written)

    # Sheet: HSN Summary
    ws_hsn = wb_gst.create_sheet(title="HSN Summary")
    ws_hsn.cell(1, 1).value = "Summary for HSN"
    hsn_headers = ["HSN", "Description", "UQC", "Total Quantity", "Rate", "Total Value", "Taxable Value", "Integrated Tax Amount", "Central Tax Amount", "State/UT Tax Amount", "Cess Amount"]
    for c_i, h in enumerate(hsn_headers, start=1):
        ws_hsn.cell(4, c_i).value = h

    # Group HSN from March orders
    hsn_groups = {}
    for o in orders:
        if o["type"] in ("b2cl_clean", "missing_in_gst"):
            continue
        if o.get("gst_month", o["month"]) != 3:
            continue
        h_code = o["item"]["hsn"]
        rate = o["item"]["rate"]
        key = (h_code, rate)
        if key not in hsn_groups:
            hsn_groups[key] = {
                "qty": 0,
                "taxable": Decimal("0.00"),
                "total_val": Decimal("0.00")
            }
        net_t = o["taxable"]
        net_tot = o["inv_amount"]
        net_q = o["qty"]
        if o.get("has_refund") and o["type"] != "b2cl_clean":
            ref_amt = o.get("refund_amount", o["inv_amount"])
            ref_t = (ref_amt / (Decimal("1.00") + rate)).quantize(Decimal("0.01"))
            net_t -= ref_t
            net_tot -= ref_amt
            net_q -= 1
        hsn_groups[key]["qty"] += net_q
        hsn_groups[key]["taxable"] += net_t
        hsn_groups[key]["total_val"] += net_tot

    r_idx = 5
    # Plant HSN tax-column gap of ₹ 291.94: deduct 291.94 from integrated tax of the first HSN row!
    gap_deducted = False
    for (h_code, rate), h_vals in hsn_groups.items():
        taxable_v = h_vals["taxable"]
        tot_val = h_vals["total_val"]
        expected_tax = (taxable_v * rate).quantize(Decimal("0.01"))

        # Split tax between IGST and CGST/SGST
        igst_v = (expected_tax * Decimal("0.4")).quantize(Decimal("0.01"))
        cgst_v = ((expected_tax - igst_v) / Decimal("2.00")).quantize(Decimal("0.01"))
        sgst_v = expected_tax - igst_v - cgst_v

        if not gap_deducted and rate == Decimal("0.18"):
            # Plant exact gap of 291.94
            igst_v = igst_v - Decimal("291.94")
            gap_deducted = True

        ws_hsn.cell(r_idx, 1).value = h_code
        ws_hsn.cell(r_idx, 2).value = ""
        ws_hsn.cell(r_idx, 3).value = "PCS"
        ws_hsn.cell(r_idx, 4).value = h_vals["qty"]
        ws_hsn.cell(r_idx, 5).value = float(rate)
        ws_hsn.cell(r_idx, 6).value = float(tot_val)
        ws_hsn.cell(r_idx, 7).value = float(taxable_v) + 0.000000000003  # float noise
        ws_hsn.cell(r_idx, 8).value = float(igst_v)
        ws_hsn.cell(r_idx, 9).value = float(cgst_v)
        ws_hsn.cell(r_idx, 10).value = float(sgst_v)
        ws_hsn.cell(r_idx, 11).value = 0
        r_idx += 1

    gst_path = os.path.join(target_dir, "demo_gst_rtf.xlsx")
    wb_gst.save(gst_path)

    # =========================================================================
    # BUILD FILE 3: PAYMENTS CSV (demo_payments.csv)
    # =========================================================================
    pay_lines = [
        '"Includes Amazon Marketplace, Fulfillment by Amazon (FBA), and Amazon Webstore transactions"',
        '"All amounts in INR, unless specified"',
        '"Definitions:"',
        '"Date/Time: Posted date/time of the transaction"',
        '"Total sales tax liable:Includes GST or sales tax collected from buyers for product sales, shipping, and gift wrap."',
        '"TCS-CGST:Tax Collected at Source from Central GST"',
        '"TCS-SGST:Tax Collected at Source from State GST"',
        '"TCS-IGST:Tax Collected at Source from Integrated GST"',
        '"TDS (Section 194-O): Tax Deducted at Source under Section 194-O of Income tax Act, 1961"',
        '"Selling fees: Includes variable closing fees and referral fees."',
        '"Other transaction fees: Includes shipping chargebacks, shipping holdbacks, and sales tax collection fees."',
        '"Other: Includes non-order transaction amounts. For more details, see the ""Type"" and ""Description"" columns for each order ID."',
        '"Note: Reports with start date of 1 Jan 2025 or later are indexed by posted date, include both released and deferred transactions and have two new columns. You may need to update integrations or third-party mappings."'
    ]

    pay_headers = [
        "date/time", "settlement id", "type", "order id", "Sku", "description",
        "quantity", "marketplace", "account type", "fulfillment", "order city",
        "order state", "order postal", "product sales", "shipping credits",
        "gift wrap credits", "promotional rebates",
        "Total sales tax liable(GST before adjusting TCS)",
        "TCS-CGST", "TCS-SGST", "TCS-IGST", "TDS (Section 194-O)",
        "selling fees", "fba fees", "other transaction fees", "other",
        "total", "Transaction Status", "Transaction Release Date"
    ]

    pay_rows = []
    settlement_id_base = 28000000000

    for idx, o in enumerate(orders):
        # 1. Skip Not Paid Orders (46, 47, 48) - 0 payout rows
        if o["type"] == "not_paid":
            continue

        oid = o["order_id"]
        is_interstate = (o["pos_code"] != ship_from_code)
        rate = o["item"]["rate"]
        settle_id = str(settlement_id_base + idx)

        # Date logic: Month 1 vs Month 2
        # Orders 24 and 25 are month-end timing differences (Sale in March, payout in April)
        if idx in (23, 24):
            settle_date = "2026-04-03 10:15:00"
            release_date = "2026-04-03 10:15:00"
        else:
            settle_date = o["inv_date"]
            release_date = o["inv_date"]

        # Status
        status = "Deferred" if o["type"] == "deferred" else "Released"
        if status == "Deferred":
            release_date = "2026-05-15 09:00:00"

        prod_sales = o["inv_amount"]
        selling_fees = -(prod_sales * Decimal("0.10")).quantize(Decimal("0.01"))
        other_tx_fees = Decimal("-25.96")

        # Plant Short Paid (Order 49 and 50)
        short_deduct = Decimal("0.00")
        if o["type"] == "short_paid":
            short_deduct = o["short_amount"]

        # TCS
        tcs_mult = Decimal("0.01") if o["type"] == "double_tcs" else Decimal("0.005")
        tcs_cgst = -(o["taxable"] * tcs_mult / Decimal("2.00")).quantize(Decimal("0.01")) if not is_interstate else Decimal("0.00")
        tcs_sgst = -(o["taxable"] * tcs_mult / Decimal("2.00")).quantize(Decimal("0.01")) if not is_interstate else Decimal("0.00")
        tcs_igst = -(o["taxable"] * tcs_mult).quantize(Decimal("0.01")) if is_interstate else Decimal("0.00")

        # TDS 194-O (0.1% on gross)
        tds = -(prod_sales * Decimal("0.001")).quantize(Decimal("0.01"))

        # Sales tax liable
        sales_tax = o["tax"]
        net_payout = prod_sales + selling_fees + other_tx_fees + tcs_cgst + tcs_sgst + tcs_igst + tds - short_deduct

        row = [
            f'"{settle_date}"', f'"{settle_id}"', '"Order"', f'"{oid}"', f'"{o["item"]["sku"]}"',
            f'"{o["item"]["sku"]}"', f'"{o["qty"]}"', '"amazon.in"',
            '"Cash On Delivery Transactions and Non-Transactional Fees"', '"Merchant"',
            '"CITY"', f'"{o["pos_name"]}"', '"600001"',
            f'"{prod_sales:.2f}"', '"0.00"', '"0.00"', '"0.00"',
            f'"{sales_tax:.2f}"',
            f'"{tcs_cgst:.2f}"', f'"{tcs_sgst:.2f}"', f'"{tcs_igst:.2f}"',
            f'"{tds:.2f}"', f'"{selling_fees:.2f}"', '"0.00"',
            f'"{other_tx_fees:.2f}"', '"0.00"', f'"{net_payout:.2f}"',
            f'"{status}"', f'"{release_date}"'
        ]
        pay_rows.append(",".join(row))

        # Refund row in Payments for Order 1 (B2CL with refund)
        if o["type"] == "b2cl_clean" and o.get("has_refund"):
            ref_settle_id = str(settlement_id_base + 5555)
            ref_amt = o.get("refund_amount", Decimal("18000.00"))
            row_ref = [
                f'"{settle_date}"', f'"{ref_settle_id}"', '"Refund"', f'"{oid}"', f'"{o["item"]["sku"]}"',
                f'"{o["item"]["sku"]}"', '"-1"', '"amazon.in"',
                '"Cash On Delivery Transactions and Non-Transactional Fees"', '"Merchant"',
                '"CITY"', f'"{o["pos_name"]}"', '"600001"',
                f'"{-float(ref_amt):.2f}"', '"0.00"', '"0.00"', '"0.00"',
                '"0.00"', '"0.00"', '"0.00"', '"0.00"', '"0.00"',
                '"0.00"', '"0.00"', '"0.00"', '"0.00"',
                f'"{-float(ref_amt):.2f}"', '"Released"', f'"{release_date}"'
            ]
            pay_rows.append(",".join(row_ref))

        # Duplicate payout order: add a second identical released payout row
        if o["type"] == "duplicate_payout":
            dup_settle_id = str(settlement_id_base + 9999)
            row_dup = [
                f'"{settle_date}"', f'"{dup_settle_id}"', '"Order"', f'"{oid}"', f'"{o["item"]["sku"]}"',
                f'"{o["item"]["sku"]}"', f'"{o["qty"]}"', '"amazon.in"',
                '"Electronic Transactions (Credit Card/Net Banking/GC)"', '"Merchant"',
                '"CITY"', f'"{o["pos_name"]}"', '"600001"',
                f'"{prod_sales:.2f}"', '"0.00"', '"0.00"', '"0.00"',
                f'"{sales_tax:.2f}"',
                f'"{tcs_cgst:.2f}"', f'"{tcs_sgst:.2f}"', f'"{tcs_igst:.2f}"',
                f'"{tds:.2f}"', f'"{selling_fees:.2f}"', '"0.00"',
                f'"{other_tx_fees:.2f}"', '"0.00"', f'"{net_payout:.2f}"',
                '"Released"', f'"{release_date}"'
            ]
            pay_rows.append(",".join(row_dup))

    # Add 1 Payout Row with NO Order ID (orphaned fee/transfer)
    orphan_row = [
        '"2026-03-31 23:59:00"', f'"{settlement_id_base + 8888}"', '"Service Fee"', '""', '""',
        '"Subscription fee for Professional Selling Plan"', '""', '"amazon.in"',
        '"Cash On Delivery Transactions and Non-Transactional Fees"', '""',
        '""', '""', '""',
        '"0.00"', '"0.00"', '"0.00"', '"0.00"', '"0.00"',
        '"0.00"', '"0.00"', '"0.00"', '"0.00"',
        '"0.00"', '"0.00"', '"0.00"', '"-499.00"',
        '"-499.00"', '"Released"', '"2026-03-31 23:59:00"'
    ]
    pay_rows.append(",".join(orphan_row))

    header_csv_line = ",".join([f'"{h}"' for h in pay_headers])
    full_csv = "\n".join(pay_lines + [header_csv_line] + pay_rows)
    pay_path = os.path.join(target_dir, "demo_payments.csv")
    with open(pay_path, "w", encoding="utf-8") as f:
        f.write(full_csv)

    print(f"Demo data generated successfully in {target_dir}:")
    print(f" - MTR: {mtr_path}")
    print(f" - GST: {gst_path}")
    print(f" - Payments: {pay_path}")


if __name__ == "__main__":
    generate_all_demo_data()
