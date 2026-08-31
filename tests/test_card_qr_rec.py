import io
from datetime import date

import openpyxl
from app.seed import seed_database
from app.models.card_qr_rec import CardQrReconciliation
from app.models.bank_transaction import BankTransaction
from app.models.branch import Branch
from app.services.matching_engine import run_card_qr_auto_matching
from app.services.import_service import process_bank_statement_import
from app.services.card_qr_service import get_card_qr_settlement_matrix


def test_card_qr_auto_matching(db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()

    rec = CardQrReconciliation(
        branch_id=branch.id,
        sale_date=date(2026, 4, 1),
        card_qr_sales_amount=50000.0,
        received_amount=0.0,
        difference=50000.0,
        status="PENDING"
    )
    db_session.add(rec)

    bank_tx = BankTransaction(
        bank_account="HDFC Main Account",
        tx_date=date(2026, 4, 2),
        reference_no="POS-50000",
        credit_amount=50000.0,
        is_matched=False
    )
    db_session.add(bank_tx)
    db_session.commit()

    res = run_card_qr_auto_matching(db_session, date_tolerance_days=3)
    assert res["matched_count"] >= 1

    db_session.refresh(rec)
    db_session.refresh(bank_tx)
    assert rec.status == "MATCHED"
    assert bank_tx.is_matched is True


def test_card_qr_matches_gateway_charges_with_lag(db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()

    rec = CardQrReconciliation(
        branch_id=branch.id,
        sale_date=date(2026, 4, 1),
        card_qr_sales_amount=18699.0,
        received_amount=0.0,
        difference=18699.0,
        status="PENDING"
    )
    db_session.add(rec)
    db_session.add(BankTransaction(
        bank_account="Kotak Mahindra Bank",
        tx_date=date(2026, 4, 2),
        reference_no="",
        credit_amount=18574.08,
        is_matched=False
    ))
    db_session.commit()

    res = run_card_qr_auto_matching(db_session, date_tolerance_days=3)
    assert res["matched_count"] == 1
    db_session.refresh(rec)
    assert rec.status == "MATCHED"
    assert rec.received_amount == 18574.08
    assert rec.difference == 124.92
    assert rec.match_method == "CHARGES_WINDOW"


def test_tally_ledger_imports_only_bank_receipts(db_session):
    seed_database(db=db_session)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "Account : Credit Card/Wallet/UPI/Paytm"
    ws.append([])
    ws.append(["Date", "Type", "Vch/Bill No", "Account", "Debit(Rs.)", "Credit(Rs.)", "Balance(Rs.)"])
    ws.append([date(2026, 4, 1), "Rcpt", "", "Kotak Mahindra Bank", "", 3278.00, 3278.00])
    ws.append([date(2026, 4, 1), "Rcpt", "", "Axis Bank", "", 6499.00, 9777.00])
    ws.append([date(2026, 4, 1), "Jrnl", "", "Service Charges", 19760.00, "", 0])
    ws.append([date(2026, 4, 1), "Jrnl", "", "Sales", 5704.00, "", 0])
    buf = io.BytesIO()
    wb.save(buf)

    batch = process_bank_statement_import(
        db_session, buf.getvalue(), "card_ledger.xlsx", "Credit Card Ledger"
    )
    assert batch.success_rows == 2
    assert getattr(batch, "_skipped_rows", 0) >= 2
    txs = db_session.query(BankTransaction).all()
    assert len(txs) == 2
    names = {t.bank_account for t in txs}
    assert names == {"Kotak Mahindra Bank", "Axis Bank"}
    assert all(t.credit_amount > 0 for t in txs)


def test_tally_ledger_pdf_imports_only_bank_receipts(db_session):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table

    seed_database(db=db_session)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    data = [
        ["Account : Credit Card/Wallet/UPI/Paytm", "", "", "", "", "", ""],
        ["Date", "Type", "Vch/Bill No", "Account", "Debit(Rs.)", "Credit(Rs.)", "Balance(Rs.)"],
        ["01-04-2026", "Rcpt", "", "Kotak Mahindra Bank", "", "3,278.00", "3,278.00"],
        ["01-04-2026", "Rcpt", "", "Axis Bank", "", "6,499.00", "9,777.00"],
        ["01-04-2026", "Jrnl", "", "Service Charges", "19,760.00", "", ""],
        ["01-04-2026", "Jrnl", "", "Sales", "5,704.00", "", ""],
    ]
    doc.build([Table(data)])
    batch = process_bank_statement_import(
        db_session, buf.getvalue(), "card_ledger.pdf", "Credit Card Ledger"
    )
    assert batch.success_rows == 2
    txs = db_session.query(BankTransaction).all()
    assert {t.bank_account for t in txs} == {"Kotak Mahindra Bank", "Axis Bank"}
    assert {round(t.credit_amount, 2) for t in txs} == {3278.00, 6499.00}


def test_settlement_matrix_is_date_by_branch(db_session):
    seed_database(db=db_session)
    noida = db_session.query(Branch).filter(Branch.code == "NOIDA01").first()
    rdc = db_session.query(Branch).filter(Branch.code == "RDC01").first()
    db_session.add(CardQrReconciliation(
        branch_id=noida.id, sale_date=date(2026, 4, 1),
        card_qr_sales_amount=1000, received_amount=990, difference=10, status="MATCHED"
    ))
    db_session.add(CardQrReconciliation(
        branch_id=rdc.id, sale_date=date(2026, 4, 1),
        card_qr_sales_amount=2000, received_amount=1980, difference=20, status="MATCHED"
    ))
    db_session.commit()

    matrix = get_card_qr_settlement_matrix(db_session, start_date=date(2026, 4, 1), end_date=date(2026, 4, 30))
    assert "2026-04-01" in matrix["dates"]
    assert len(matrix["branches"]) >= 2
    day = matrix["cells"]["2026-04-01"]
    assert day[str(noida.id)]["sales"] == 1000
    assert day[str(rdc.id)]["received"] == 1980
