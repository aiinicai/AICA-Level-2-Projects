import pytest
from datetime import date
from app.seed import seed_database
from app.models.aggregator import Aggregator
from app.models.branch import Branch
from app.services.aggregator_service import create_or_update_settlement_batch, get_aggregator_payout_matrix

def test_aggregator_settlement_payout_breakup(db_session):
    seed_database(db=db_session)
    agg = db_session.query(Aggregator).filter(Aggregator.code == "ZOMATO").first()
    branch = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()

    batch = create_or_update_settlement_batch(
        db=db_session,
        batch_no="SETTLE-ZOMATO-TEST",
        aggregator_id=agg.id,
        branch_id=branch.id,
        period_start_date=date(2026, 4, 1),
        period_end_date=date(2026, 4, 5),
        gross_sales=100000.0,
        payout=80000.0,
        deductions_data=[
            {"deduction_type": "COMMISSION", "amount": 15000.0},
            {"deduction_type": "PROMOTION", "amount": 3000.0},
            {"deduction_type": "TCS", "amount": 1000.0},
            {"deduction_type": "TDS", "amount": 1000.0}
        ]
    )

    # Gross Sales = 100,000, Payout = 80,000 => Actual Diff = 20,000
    # Total Deductions = 15000 + 3000 + 1000 + 1000 = 20,000
    # Difference Adjustment = 20,000 - 20,000 = 0 => Reconciled
    assert batch.actual_difference == 20000.0
    assert batch.total_deductions == 20000.0
    assert batch.difference_adjustment == 0.0
    assert batch.status == "RECONCILED"

    matrix = get_aggregator_payout_matrix(db_session, aggregator_id=agg.id)
    assert len(matrix["columns"]) >= 1
    assert matrix["branch_groups"]
    assert matrix["branch_groups"][0]["branch_name"] == branch.name

def test_swiggy_parser_rules():
    import pandas as pd
    from app.services.import_service import _parse_swiggy_settlement

    data = [
        ["A Total Customer Paid [1+2-3-4+5]", 71694.63, 0, 71694.58],
        ["1 Item Total", 76281.0, 0, 76281.0],
        ["2 Packaging Charges", 2219.0, 0, 2219.0],
        ["3 Restaurant Discounts (Coupon based)", -6590.35, 0, -6590.4],
        ["4 Restaurant Discounts (Trade Discounts)", -3629.26, 0, -3629.26],
        ["5 GST Collected", 3414.24, 0, 3414.24],
        ["B Swiggy Fees [6+7+8+9+10+11+12+13+14+15]", -17527.7, -17.21, -17544.91],
        ["19 GST on Service Fee @18%", -3155.04, -3.1, -3158.14],
        ["C Customer Complaints", -205.0, 0, -205.0],
        ["D Growth Investment In Ads", 0, 0, -1803.63],
        ["E Other Charges and Refunds", 0, 0, -37.0],
        ["18 GST Deduction (paid by Swiggy)", -3414.08, 0, -3414.08],
        ["20 TCS", 0, 0, 0.0],
        ["21 TDS", -68.29, 0, -68.29],
        ["G Net Payout [A+B+C+D+E+F]", 47324.43, -20.31, 45463.49]
    ]
    df = pd.DataFrame(data, columns=["Particulars", "Delivered", "Cancelled", "Total"])

    gross, payout, deductions = _parse_swiggy_settlement(df)

    # Reconciling sale = Customer Paid − GST Collected
    assert gross == pytest.approx(71694.58 - 3414.24, 0.01)
    assert payout == 45463.49
    # B fees + GST on service (item 19, outside B). C complaints are miscellaneous.
    assert deductions["COMMISSION"] == pytest.approx(17544.91 + 3158.14, 0.01)
    assert deductions["PROMOTION"] == pytest.approx(1803.63, 0.01)
    assert deductions["TDS"] == pytest.approx(68.29, 0.01)
    assert deductions["GST_9_5"] == pytest.approx(3414.08, 0.01)
    assert deductions["PACKING_CHARGES"] == pytest.approx(2219.00, 0.01)
    assert deductions["MISC"] == pytest.approx(205.00 + 37.00, 0.01)


def test_swiggy_parser_client_mapping_sheet():
    import pandas as pd
    from app.services.import_service import _parse_swiggy_settlement

    data = [
        ["A Total Customer Paid [1+2-3+4]", 100000.0],
        ["1 Item Total", 90000.0],
        ["2 Packaging Charges", 2000.0],
        ["3 Discount Share", -5000.0],
        ["4 GST Collected", 3000.0],
        ["B Swiggy Fees", -15000.0],
        ["6 Commission", -8000.0],
        ["7 Long Distance Charges", -500.0],
        ["8 Payment Collection Charges", -400.0],
        ["9 Pocket Hero Fees", -300.0],
        ["10 Swiggy One Fees", -700.0],
        ["11 Restaurant Cancellation Charges", -200.0],
        ["12 Call Center Charges", -100.0],
        ["13 Delivery Fee sponsored by Restaurant", -250.0],
        ["14 Bolt Fees", -150.0],
        ["15 GST on Service Fee @18%", -2400.0],
        ["C Customer Complaints & Cancellation", -500.0],
        ["16 Merchant Share Of Cancelled Orders", -200.0],
        ["17 Refund For Customer Complaints", -300.0],
        ["D Other Charges and Refunds", 0.0],
        ["Top Picks - Ads", -1000.0],
        ["Cost Per Click - Ads", -400.0],
        ["E Total Taxes [18+19+20]", -3300.0],
        ["18 GST Deduction (paid by Swiggy on behalf of the restaurant)", -3000.0],
        ["19 TCS", -100.0],
        ["20 TDS", -200.0],
        ["F Net Payout [A+B+C+D+E]", 81100.0],
    ]
    df = pd.DataFrame(data, columns=["Particulars", "Total"])

    gross, payout, deductions = _parse_swiggy_settlement(df)

    assert gross == pytest.approx(97000.0, 0.01)
    assert payout == pytest.approx(81100.0, 0.01)
    assert deductions["COMMISSION"] == pytest.approx(15000.0, 0.01)
    assert deductions["PROMOTION"] == pytest.approx(1400.0, 0.01)
    assert deductions["TCS"] == pytest.approx(100.0, 0.01)
    assert deductions["TDS"] == pytest.approx(200.0, 0.01)
    assert deductions["GST_9_5"] == pytest.approx(3000.0, 0.01)
    assert deductions["PACKING_CHARGES"] == pytest.approx(2000.0, 0.01)
    assert deductions["MISC"] == pytest.approx(500.0, 0.01)


def test_swiggy_parser_live_payout_sheet():
    import pandas as pd
    from app.services.import_service import _parse_swiggy_settlement

    data = [
        ["Orders", "", 72],
        ["A Total Customer Paid [1+2-3+4]", "", 47782.00],
        ["1 Item Total", "Commissionable Value = A1-A4 i.e Item Total - GST Collected i.e 46548-2275.58=44272.42", 46548.00],
        ["2 Packaging Charges", "", 1393.0],
        ["3 Discount Share", "", -2434.58],
        ["4 GST Collected", "", 2275.58],
        ["B Swiggy Fees", "", -13747.58],
        ["6 Commission", "Online Platform Charges", -11467.58],
        ["7 Long Distance Charges", "Online Platform Charges", 0],
        ["10 Swiggy One Fees", "Online Platform Charges", -183],
        ["15 GST on Service Fee @18%", "Online Platform Charges", -2097.0],
        ["C Customer Complaints & Cancellation", "", -385.00],
        ["16 Merchant Share Of Cancelled Orders", "Miscellaneous", 0.0],
        ["17 Refund For Customer Complaints", "Miscellaneous", -385.0],
        ["D Other Charges and Refunds", "", -2313.68],
        ["Top Picks - Ads", "Ads means business promotion", -313.58],
        ["Cost Per Click - Ads", "Ads means business promotion", -2000.1],
        ["E Total Taxes [18+19+20]", "", -2320.86],
        ["18 GST Deduction (paid by Swiggy on behalf of the restaurant)", "GST paid by Zomato/Swiggy under section 9(5)", -2275.34],
        ["19 TCS", "TCS", 0.0],
        ["20 TDS", "TDS Receivable", -45.52],
        ["F Net Payout [A+B+C+D+E]", "", 29014.37],
    ]
    df = pd.DataFrame(data, columns=["Particulars", "Rules", "Total"])

    gross, payout, deductions = _parse_swiggy_settlement(df)

    assert gross == pytest.approx(47782.00 - 2275.58, 0.01)
    assert payout == pytest.approx(29014.37, 0.01)
    assert deductions["COMMISSION"] == pytest.approx(13747.58, 0.01)
    assert deductions["PROMOTION"] == pytest.approx(2313.68, 0.01)
    assert deductions["MISC"] == pytest.approx(385.00, 0.01)
    assert deductions["TDS"] == pytest.approx(45.52, 0.01)
    assert deductions["TCS"] == pytest.approx(0.0, 0.01)
    assert deductions["GST_9_5"] == pytest.approx(2275.34, 0.01)
    assert deductions["PACKING_CHARGES"] == pytest.approx(1393.00, 0.01)

    actual_diff = round(gross - payout, 2)
    calc_deds = round(
        deductions["COMMISSION"] + deductions["PROMOTION"] + deductions["MISC"]
        + deductions["TCS"] + deductions["TDS"],
        2,
    )
    assert abs(actual_diff - calc_deds) < 1.0


def test_swiggy_picks_summary_sheet_not_empty_sheet2():
    import io
    import pandas as pd
    from app.services.import_service import _load_best_payout_df, _parse_swiggy_settlement

    summary = pd.DataFrame([
        ["Title", "Swiggy payout", ""],
        ["Particulars", "Rules", "Total"],
        ["A Total Customer Paid [1+2-3+4]", "", 47782.00],
        ["1 Item Total", "Commissionable Value = A1-A4", 46548.00],
        ["4 GST Collected", "", 2275.58],
        ["B Swiggy Fees", "", -13747.58],
        ["C Customer Complaints & Cancellation", "", -385.00],
        ["Top Picks - Ads", "Ads means business promotion", -313.58],
        ["Cost Per Click - Ads", "Ads means business promotion", -2000.1],
        ["18 GST Deduction (paid by Swiggy on behalf of the restaurant)", "", -2275.34],
        ["20 TDS", "TDS Receivable", -45.52],
        ["F Net Payout [A+B+C+D+E]", "", 29014.37],
    ])
    noise = pd.DataFrame([["Order Id", "Amount"], [1, 10], [2, 20]])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        noise.to_excel(writer, sheet_name="Cover", index=False)
        summary.to_excel(writer, sheet_name="Payout", header=False, index=False)
    buf.seek(0)
    xls = pd.ExcelFile(buf)
    df = _load_best_payout_df(xls)
    gross, payout, deductions = _parse_swiggy_settlement(df)
    assert payout == pytest.approx(29014.37, 0.01)
    assert gross == pytest.approx(47782.00 - 2275.58, 0.01)
    assert deductions["COMMISSION"] == pytest.approx(13747.58, 0.01)


def test_zomato_parser_client_mapping_sheet():
    import pandas as pd
    from app.services.import_service import _parse_zomato_settlement

    # I = A - B - C - D - E - F - G + H
    # A=142887.06, B=20000, C=14715.13, E=18981.48, I=89190.45
    data = [
        ["S.No.", "Particular", "MAPPING RULES", "Delivered Orders", "Cancelled/Rejected Orders", "Total"],
        ["", "A. Net order value (1+2+3-4-5+6-7+8)", "", 142887.06, 0, 142887.06],
        ["1", "Subtotal (items total)", "", 140000.00, 0, 140000.00],
        ["2", "Packaging charge", "", 2500.00, 0, 2500.00],
        ["8", "Total GST collected from customers", "", 7673.92, 0, 7673.92],
        ["9", "Commissionable value (excludes customer GST)", "Total Sale", 135213.14, 0, 135213.14],
        ["", "B. Service fees & payment mechanism fees", "Online Platform Charges", 20000.00, 0, 20000.00],
        ["10", "Base service fee", "Online Platform Charges", 16000.00, 0, 16000.00],
        ["11", "Fulfilment fee", "Online Platform Charges", 2500.00, 0, 2500.00],
        ["", "Payment mechanism fee", "Online Platform Charges", 1500.00, 0, 1500.00],
        ["", "C. Government charges", "", 14715.13, 0, 14715.13],
        ["12", "Taxes on service & payment mechanism fees", "Online Platform Charges", 6887.72, 0, 6887.72],
        ["13", "Tax collected at source + TCS IGST amount", "TCS", 0.00, 0, 0.00],
        ["14", "TDS 194O amount", "TDS Receivable", 153.49, 0, 153.49],
        ["15", "GST paid by Zomato on behalf of restaurant - under section 9(5)", "GST Paid by Zomato / Swiggy under Sec", 7673.92, 0, 7673.92],
        ["", "D. Other order level deductions", "Miscellaneous", 0.00, 0, 0.00],
        ["16", "Other Order level deductions", "Miscellaneous", 0.00, 0, 0.00],
        ["", "Customer Compensation/Recoupment", "Miscellaneous", 0.00, 0, 0.00],
        ["", "Rejection Penalty", "Miscellaneous", 0.00, 0, 0.00],
        ["17", "Amount received in cash (on self delivery orders)", "Miscellaneous", 0.00, 0, 0.00],
        ["18", "Adjustments from previous weeks", "Miscellaneous", 0.00, 0, 0.00],
        ["", "E. Investment in growth services", "Business Promotion", 18981.48, 0, 18981.48],
        ["19", "Total Ads (inc. 18% GST)", "Business Promotion", 18981.48, 0, 18981.48],
        ["20", "Total Dining Ads (inc. 18% GST)", "Business Promotion", 0.00, 0, 0.00],
        ["21", "Miscellaneous services", "Business Promotion", 0.00, 0, 0.00],
        ["", "F. Investment in Hyperpure", "", 0.00, 0, 0.00],
        ["", "G. Other Deductions", "", 0.00, 0, 0.00],
        ["", "H. Total Additions", "Miscellaneous", 0.00, 0, 0.00],
        ["24", "Cancellation refund for cancelled Orders", "Miscellaneous", 0.00, 0, 0.00],
        ["25", "Tip for Kitchen Staff for delivered Orders", "Miscellaneous", 0.00, 0, 0.00],
        ["26", "TDS 194 H and other Res id level Additions", "Miscellaneous", 0.00, 0, 0.00],
        ["27", "Restaurant-level service fees rebate", "Miscellaneous", 0.00, 0, 0.00],
        ["", "I. Net Payout (A-B-C-D-E-F-G+H)", "", 89190.45, 0, 89190.45],
        ["", "Amount Settled", "", 0.00, 0, 0.00],
        ["", "Pending Amount (Will be credited on next pay-out day)", "Payout", 89190.45, 0, 89190.45],
    ]
    df = pd.DataFrame(data[1:], columns=data[0])

    gross, payout, deductions = _parse_zomato_settlement(df)

    assert payout == pytest.approx(89190.45, 0.01)
    assert gross == pytest.approx(142887.06 - 7673.92, 0.01)
    assert deductions["COMMISSION"] == pytest.approx(20000.00 + 6887.72, 0.01)
    assert deductions["PROMOTION"] == pytest.approx(18981.48, 0.01)
    assert deductions["TCS"] == pytest.approx(0.0, 0.01)
    assert deductions["TDS"] == pytest.approx(153.49, 0.01)
    assert deductions["GST_9_5"] == pytest.approx(7673.92, 0.01)
    assert deductions["PACKING_CHARGES"] == pytest.approx(2500.00, 0.01)
    assert deductions["MISC"] == pytest.approx(0.0, 0.01)

    actual_diff = round(gross - payout, 2)
    calc_deds = round(
        deductions["COMMISSION"] + deductions["PROMOTION"] + deductions["MISC"]
        + deductions["TCS"] + deductions["TDS"],
        2,
    )
    assert abs(actual_diff - calc_deds) < 1.0


def test_zomato_parser_additions_and_no_double_count():
    import pandas as pd
    from app.services.import_service import _parse_zomato_settlement

    data = [
        ["A. Net order value", 100000.0],
        ["Commissionable value (excludes customer GST)", 95000.0],
        ["B. Service fees & payment mechanism fees", 10000.0],
        ["Base service fee", 8000.0],
        ["Payment mechanism fee", 2000.0],
        ["Taxes on service & payment mechanism fees", 1800.0],
        ["Tax collected at source + TCS IGST amount", 100.0],
        ["TDS 194O amount", 200.0],
        ["GST paid by Zomato on behalf of restaurant - under section 9(5)", 5000.0],
        ["Customer Compensation/Recoupment", 300.0],
        ["Total Ads (inc. 18% GST)", 4000.0],
        ["Cancellation refund for cancelled Orders", 150.0],
        ["TDS 194 H and other Res id level Additions", 50.0],
        ["Restaurant-level service fees rebate", 25.0],
        ["I. Net Payout (A-B-C-D-E-F-G+H)", 78825.0],
    ]
    df = pd.DataFrame(data, columns=["Particular", "Total"])

    gross, payout, deductions = _parse_zomato_settlement(df)

    assert payout == pytest.approx(78825.0, 0.01)
    assert gross == pytest.approx(100000.0 - 5000.0, 0.01)
    assert deductions["COMMISSION"] == pytest.approx(11800.0, 0.01)
    assert deductions["PROMOTION"] == pytest.approx(4000.0, 0.01)
    assert deductions["TCS"] == pytest.approx(100.0, 0.01)
    assert deductions["TDS"] == pytest.approx(200.0, 0.01)
    assert deductions["GST_9_5"] == pytest.approx(5000.0, 0.01)
    assert deductions["MISC"] == pytest.approx(300.0 - 150.0 - 50.0 - 25.0, 0.01)


def test_zomato_parser_real_sno_column_layout():
    import pandas as pd
    from app.services.import_service import _parse_zomato_settlement

    # Live Zomato layout: letter/number in S.No., wording in Particular.
    df = pd.DataFrame([
        ["A", "Net order value \n( 1 + 2 + 3 - 4 - 5 + 6 - 7 + 8 )", "", 161152.32],
        ["2", "Packaging charge", "Packaging Charges", 4284.0],
        ["8", "Total GST collected from customers", "", 7673.92],
        ["9", "Commissionable value (excludes customer GST)", "Commissionable Value / Total Sale", 153478.4],
        ["B", "Service fees & payment mechanism fees\n( 10 + 11 )", "", 38265.2625],
        ["10", "Service fee", "Online Platform Charges", 35300.032],
        ["11", "Payment mechanism fee", "Online Platform Charges", 2965.2305],
        ["C", "Government charges\n( 12 + 13 + 14 + 15 )", "", 14715.1307],
        ["12", "Taxes on service & payment mechanism fees", "Online Platform Charges", 6887.7203],
        ["13", "Tax collected at source + TCS IGST amount", "TCS", 0.0],
        ["14", "TDS 194O amount", "TDS Receivable", 153.4904],
        ["15", "GST paid by Zomato on behalf of restaurant - under section 9(5)", "GST Paid by Zomato / Swiggy under Section 9(5)", 7673.92],
        ["E", "Investment in growth services\n( 19 + 20 + 21 )", "", 18981.48],
        ["19", "Total Ads (inc. 18% GST)", "Business Promotion", 18981.48],
        ["I", "Net Payout \n( A - B - C - D - E  - F - G + H )", "", 89190.4468],
        ["", "Pending Amount (Will be credited on next pay-out day)", "Payout", 89190.4468],
    ], columns=["S.No.", "Particular", "MAPPING RULES", "Total"])

    gross, payout, deductions = _parse_zomato_settlement(df)

    assert payout == pytest.approx(89190.45, 0.01)
    assert gross == pytest.approx(161152.32 - 7673.92, 0.01)
    assert deductions["COMMISSION"] == pytest.approx(38265.26 + 6887.72, 0.01)
    assert deductions["PROMOTION"] == pytest.approx(18981.48, 0.01)
    assert deductions["TDS"] == pytest.approx(153.49, 0.01)
    assert deductions["GST_9_5"] == pytest.approx(7673.92, 0.01)
    assert deductions["PACKING_CHARGES"] == pytest.approx(4284.00, 0.01)

    actual_diff = round(gross - payout, 2)
    calc_deds = round(
        deductions["COMMISSION"] + deductions["PROMOTION"] + deductions["MISC"]
        + deductions["TCS"] + deductions["TDS"],
        2,
    )
    assert abs(actual_diff - calc_deds) < 1.0
