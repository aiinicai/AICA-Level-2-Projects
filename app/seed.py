import os
import pandas as pd
from datetime import date, timedelta
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash, verify_password
from app.models.user import User, Role
from app.models.branch import Branch
from app.models.payment_channel import PaymentChannel, ChannelMapping
from app.models.aggregator import Aggregator
from app.models.accounting_head import AccountingHead
from app.models.setting import ApplicationSetting
from app.models.ocr_audit import OCRAuditLog
from app.models.attendance import Employee, AttendanceMark
from app.services.cash_service import create_or_update_cash_reconciliation
from app.services.aggregator_service import create_or_update_settlement_batch


def apply_admin_login(db):
    user = db.query(User).filter(User.email.in_(["admin", "admin@restaurant.com"])).first()
    if not user:
        return
    if user.email != "admin":
        clash = db.query(User).filter(User.email == "admin", User.id != user.id).first()
        if not clash:
            user.email = "admin"
    if not verify_password("admin", user.hashed_password):
        user.hashed_password = get_password_hash("admin")
    db.commit()


def apply_noida_login(db):
    user = db.query(User).filter(
        User.email.in_(["noida", "branch@restaurant.com", "noida@restaurant.com"])
    ).first()
    if not user:
        user = db.query(User).filter(User.full_name.ilike("%noida%")).first()
    if not user:
        return
    if user.email != "noida":
        clash = db.query(User).filter(User.email == "noida", User.id != user.id).first()
        if not clash:
            user.email = "noida"
    if not verify_password("noida", user.hashed_password):
        user.hashed_password = get_password_hash("noida")
    noida_branch = db.query(Branch).filter(Branch.code == "NOIDA01").first()
    if noida_branch and not user.branch_id:
        user.branch_id = noida_branch.id
    if user.is_active is False:
        user.is_active = True
    db.commit()


def seed_database(db=None, include_samples=True, include_demo_branches=None):
    if db is None:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        db_session = SessionLocal()
        close_on_exit = True
    else:
        db_session = db
        close_on_exit = False

    try:
        # 1. ROLES
        roles_data = [
            ("Administrator", "Full system administrative access"),
            ("Accounts Manager", "Access to imports, reconciliations, and reporting"),
            ("Branch User", "Can enter daily branch operational data"),
            ("Viewer", "Read-only access")
        ]
        role_objs = {}
        for r_name, r_desc in roles_data:
            role = db_session.query(Role).filter(Role.name == r_name).first()
            if not role:
                role = Role(name=r_name, description=r_desc)
                db_session.add(role)
                db_session.flush()
            role_objs[r_name] = role

        # 2. USERS
        users_data = [
            ("admin", "System Admin", "admin", "Administrator"),
            ("accounts@restaurant.com", "Accounts Lead", "accounts123", "Accounts Manager"),
            ("noida", "Noida Branch Staff", "noida", "Branch User"),
            ("viewer@restaurant.com", "Auditor Viewer", "viewer123", "Viewer")
        ]
        for email, full_name, raw_pwd, role_name in users_data:
            user = db_session.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    full_name=full_name,
                    hashed_password=get_password_hash(raw_pwd),
                    is_active=True,
                    role_id=role_objs[role_name].id
                )
                db_session.add(user)
        apply_admin_login(db_session)

        if include_demo_branches is None:
            include_demo_branches = include_samples

        # 3. BRANCHES
        branches_data = [
            ("NOIDA01", "Noida Branch", "Sector 62, Noida", 15000.0, True),
            ("RDC01", "RDC Branch", "RDC Raj Nagar, Ghaziabad", 12000.0, False)
        ] if include_demo_branches else []
        branch_objs = {}
        for code, name, addr, opening, is_base in branches_data:
            b = db_session.query(Branch).filter(Branch.code == code).first()
            if not b:
                b = Branch(
                    code=code,
                    name=name,
                    address=addr,
                    opening_cash_balance=opening,
                    is_base_kitchen=is_base,
                    is_active=True
                )
                db_session.add(b)
                db_session.flush()
            branch_objs[code] = b
        apply_noida_login(db_session)

        # 4. PAYMENT CHANNELS
        channels_data = [
            ("CASH", "Cash", "CASH", "PHYSICAL_COUNT", ["cash sale", "cash", "counter cash"]),
            ("CARD_QR", "Card / QR Code", "BANK", "BANK_STATEMENT", ["card", "credit card", "debit card", "upi", "qr", "paytm qr"]),
            ("ZOMATO", "Zomato", "AGGREGATOR", "AGGREGATOR_SETTLEMENT", ["zomato", "zomato online"]),
            ("SWIGGY", "Swiggy", "AGGREGATOR", "AGGREGATOR_SETTLEMENT", ["swiggy", "swiggy online"]),
            ("DINEOUT", "Dineout", "AGGREGATOR", "AGGREGATOR_SETTLEMENT", ["dineout", "dineout pay"])
        ]
        ch_objs = {}
        for code, name, ch_type, rec_meth, aliases in channels_data:
            ch = db_session.query(PaymentChannel).filter(PaymentChannel.code == code).first()
            if not ch:
                ch = PaymentChannel(code=code, name=name, channel_type=ch_type, reconciliation_method=rec_meth)
                db_session.add(ch)
                db_session.flush()
            ch_objs[code] = ch

            # Add Channel Mappings
            for alias in aliases:
                mapping = db_session.query(ChannelMapping).filter(ChannelMapping.alias == alias).first()
                if not mapping:
                    mapping = ChannelMapping(payment_channel_id=ch.id, alias=alias)
                    db_session.add(mapping)

        # 5. AGGREGATORS
        aggregators_data = [
            ("ZOMATO", "Zomato - Eternal Limited"),
            ("SWIGGY", "Swiggy"),
            ("DINEOUT", "Dineout")
        ]
        agg_objs = {}
        for code, name in aggregators_data:
            agg = db_session.query(Aggregator).filter(Aggregator.code == code).first()
            if not agg:
                agg = Aggregator(code=code, name=name, is_active=True)
                db_session.add(agg)
                db_session.flush()
            elif agg.name != name:
                agg.name = name
            agg_objs[code] = agg

        # 6. ACCOUNTING HEADS
        heads_data = [
            ("COMMISSION_EXP", "Online Platform Commission Charges", "EXPENSE"),
            ("PROMO_EXP", "Business Promotion & Discounts", "EXPENSE"),
            ("TCS_REC", "TCS Receivable (Section 52)", "ASSET"),
            ("TDS_REC", "TDS Receivable (Section 194O)", "ASSET"),
            ("GST_SEC_9_5", "GST Paid by Aggregator (Sec 9(5))", "TAX"),
            ("PACKING_CHARGES", "Packing Charges Collected", "REVENUE"),
            ("MISC_EXP", "Miscellaneous Aggregator Charges", "DEDUCTION")
        ]
        for code, name, h_type in heads_data:
            head = db_session.query(AccountingHead).filter(AccountingHead.code == code).first()
            if not head:
                head = AccountingHead(code=code, name=name, head_type=h_type)
                db_session.add(head)

        # 7. DEFAULT SETTINGS
        settings_data = [
            ("DEFAULT_DATE_TOLERANCE_DAYS", "3", "Bank statement date matching tolerance in days"),
            ("DEFAULT_CURRENCY", "INR", "Default currency display symbol"),
            ("DECIMAL_PRECISION", "2", "Rounding decimal places")
        ]
        for key, val, desc in settings_data:
            st = db_session.query(ApplicationSetting).filter(ApplicationSetting.key == key).first()
            if not st:
                st = ApplicationSetting(key=key, value=val, description=desc)
                db_session.add(st)

        db_session.commit()

        # Seed sample Cash Rec & Aggregator Batch
        no_branch = branch_objs.get("NOIDA01")
        rdc_branch = branch_objs.get("RDC01")
        if include_samples and no_branch and rdc_branch:
            # Seed Cash Rec for April 1, 2026
            create_or_update_cash_reconciliation(
                db=db_session,
                branch_id=no_branch.id,
                rec_date=date(2026, 4, 1),
                data={
                    "opening_balance": 15000.0,
                    "cash_sale": 42500.0,
                    "site_expenses_inv_rec": 3200.0,
                    "site_expenses_inv_not_rec": 850.0,
                    "advance_salary_1_5": 5000.0,
                    "transfer_base_kitchen": 10000.0,
                    "service_charge": 500.0,
                    "actual_closing_balance": 38950.0,
                    "remarks": "Sample April 1 Cash Rec"
                }
            )

            # Seed Zomato Settlement Batch for Noida Branch (April 1 to April 5, 2026)
            zomato_agg = agg_objs.get("ZOMATO")
            if zomato_agg:
                create_or_update_settlement_batch(
                    db=db_session,
                    batch_no="SETTLE-ZOMATO-20260401-20260405",
                    aggregator_id=zomato_agg.id,
                    branch_id=no_branch.id,
                    period_start_date=date(2026, 4, 1),
                    period_end_date=date(2026, 4, 5),
                    gross_sales=125400.0,
                    payout=104500.0,
                    settlement_date=date(2026, 4, 6),
                    deductions_data=[
                        {"deduction_type": "COMMISSION", "description": "Zomato Commission 18%", "amount": 15500.0},
                        {"deduction_type": "PROMOTION", "description": "Gold Promo Discounts", "amount": 3200.0},
                        {"deduction_type": "TCS", "description": "TCS 1%", "amount": 1254.0},
                        {"deduction_type": "TDS", "description": "TDS 1%", "amount": 946.0}
                    ]
                )

        print("Seed data successfully inserted.")

        # 8. CREATE SAMPLE DOWNLOADABLE EXCEL TEMPLATES
        os.makedirs("sample_data", exist_ok=True)
        
        # Sample Daily Sales Excel
        sales_df = pd.DataFrame([
            {"Date": "2026-04-01", "Cash Sale": 42500, "Credit Card": 38400, "Zomato": 24500, "Swiggy": 18200, "Dineout": 9800},
            {"Date": "2026-04-02", "Cash Sale": 45100, "Credit Card": 41200, "Zomato": 26800, "Swiggy": 19500, "Dineout": 10400},
            {"Date": "2026-04-03", "Cash Sale": 39800, "Credit Card": 35600, "Zomato": 22100, "Swiggy": 16900, "Dineout": 8500},
            {"Date": "2026-04-04", "Cash Sale": 51200, "Credit Card": 49800, "Zomato": 31500, "Swiggy": 24200, "Dineout": 14100},
            {"Date": "2026-04-05", "Cash Sale": 48900, "Credit Card": 46500, "Zomato": 29800, "Swiggy": 22800, "Dineout": 12900}
        ])
        sales_df.to_excel("sample_data/daily_sales_template.xlsx", index=False)

        # Sample Bank Statement Excel
        bank_df = pd.DataFrame([
            {"Transaction Date": "2026-04-01", "Description": "HDFC POS Card Settlement Noida", "Ref No": "POS894321", "Credit": 38400, "Debit": 0},
            {"Transaction Date": "2026-04-02", "Description": "HDFC POS Card Settlement Noida", "Ref No": "POS894322", "Credit": 41200, "Debit": 0},
            {"Transaction Date": "2026-04-06", "Description": "ZOMATO MEDIA PVT LTD SETTLEMENT", "Ref No": "ZOM784321", "Credit": 104500, "Debit": 0}
        ])
        bank_df.to_excel("sample_data/bank_statement_template.xlsx", index=False)

        # Sample Zomato Settlement Excel
        zomato_df = pd.DataFrame([
            {"Order Date": "2026-04-01", "Order ID": "ZOM-1001", "Gross Sales": 24500, "Payout": 20400, "Commission": 3000, "Promo": 600, "TCS": 245, "TDS": 255},
            {"Order Date": "2026-04-02", "Order ID": "ZOM-1002", "Gross Sales": 26800, "Payout": 22300, "Commission": 3300, "Promo": 700, "TCS": 268, "TDS": 232}
        ])
        zomato_df.to_excel("sample_data/zomato_settlement_template.xlsx", index=False)

        print("Sample Excel templates generated in 'sample_data/' directory.")

    finally:
        if close_on_exit:
            db_session.close()

if __name__ == "__main__":
    seed_database()
