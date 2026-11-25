"""Manual entry of bank balances and facilities (the screen). Same rules as the bulk upload."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import round_money, to_decimal
from app.models import BankAccount, BankBalance, BankFacility
from app.services.audit import audit
from app.services.settings_service import get_business_settings


class EntryError(ValueError):
    pass


def _amount(v, label: str, allow_negative: bool = True) -> Decimal:
    try:
        d = round_money(to_decimal(v))
    except ValueError:
        raise EntryError(f"{label}: '{v}' is not an amount")
    if not allow_negative and d < 0:
        raise EntryError(f"{label} cannot be negative")
    return d


def set_balance(db: Session, *, bank: str, account: str, currency: str, as_of: date, balance, rate=None,
                user_id: int | None = None) -> BankBalance:
    s = get_business_settings(db)
    bank, account, ccy = bank.strip(), account.strip(), (currency or s.base_currency).strip().upper()
    if not bank or not account:
        raise EntryError("bank and account are required")
    if len(ccy) != 3 or not ccy.isalpha():
        raise EntryError(f"'{currency}' is not a currency code")
    bal_amt = _amount(balance, "Balance")
    if ccy == s.base_currency:
        fx = Decimal(1)
        if rate not in (None, "") and to_decimal(rate) != 1:
            raise EntryError(f"{ccy} accounts have rate 1")
    else:
        if rate in (None, ""):
            raise EntryError(f"enter the manual rate to {s.base_currency} for this {ccy} account")
        try:
            fx = to_decimal(rate)
        except ValueError:
            raise EntryError(f"'{rate}' is not a rate")
        if fx <= 0:
            raise EntryError("rate must be greater than 0")
    acct = db.scalar(select(BankAccount).where(BankAccount.bank_name == bank, BankAccount.account_name == account))
    if acct is None:
        if ccy == s.base_currency:
            n = len(db.scalars(select(BankAccount).where(BankAccount.is_active,
                                                         BankAccount.currency == s.base_currency)).all())
            if n >= s.max_bank_accounts_base_currency:
                raise EntryError(f"already {n} {ccy} accounts; the limit is {s.max_bank_accounts_base_currency}")
        acct = BankAccount(bank_name=bank, account_name=account, currency=ccy)
        db.add(acct)
        db.flush()
    elif acct.currency != ccy:
        raise EntryError(f"account is set up as {acct.currency}")
    row = db.scalar(select(BankBalance).where(BankBalance.account_id == acct.id, BankBalance.as_of_date == as_of))
    before = {"balance": row.balance, "rate": row.fx_rate_to_base} if row else None
    if row is None:
        row = BankBalance(account_id=acct.id, as_of_date=as_of)
        db.add(row)
    row.balance, row.fx_rate_to_base, row.entered_by_id = bal_amt, fx, user_id
    db.flush()
    audit(db, "balance.set", "bank_balance", f"{bank} {account} {as_of}", before=before,
          after={"balance": bal_amt, "rate": fx, "currency": ccy}, user_id=user_id)
    return row


def set_facility(db: Session, *, bank: str, facility_type: str, as_of: date, available, limit=None, utilised=None,
                 user_id: int | None = None) -> BankFacility:
    bank, ftype = bank.strip(), (facility_type or "Overdraft / working capital").strip()
    if not bank:
        raise EntryError("bank is required")
    lim = None if limit in (None, "") else _amount(limit, "Limit", False)
    used = None if utilised in (None, "") else _amount(utilised, "Utilised", False)
    if available in (None, "") and lim is not None and used is not None:
        avail = lim - used
    else:
        avail = _amount(available, "Available", False)
    f = db.scalar(select(BankFacility).where(BankFacility.bank_name == bank, BankFacility.facility_type == ftype,
                                             BankFacility.as_of_date == as_of))
    before = {"available": f.available_amount} if f else None
    if f is None:
        f = BankFacility(bank_name=bank, facility_type=ftype, as_of_date=as_of)
        db.add(f)
    f.limit_amount, f.utilised_amount, f.available_amount, f.entered_by_id = lim, used, avail, user_id
    db.flush()
    audit(db, "facility.set", "bank_facility", f"{bank} {ftype} {as_of}", before=before,
          after={"limit": lim, "utilised": used, "available": avail}, user_id=user_id)
    return f
