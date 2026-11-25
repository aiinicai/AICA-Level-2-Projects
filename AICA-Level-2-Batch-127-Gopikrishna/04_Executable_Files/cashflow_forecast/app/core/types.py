"""Custom SQLAlchemy column types.

* ``Money``  - Decimal in Python, INTEGER minor units in SQLite (3 dp -> 1 OMR = 1000).
               Every currency is stored at 3 dp so one column type fits all accounts.
* ``ExactDecimal`` - Decimal in Python, TEXT in SQLite (used for FX rates, no float drift).
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, String
from sqlalchemy.types import TypeDecorator

from app.core.money import DEFAULT_DECIMALS, from_minor, to_decimal, to_minor


class Money(TypeDecorator):
    impl = BigInteger
    cache_ok = True

    def __init__(self, decimals: int = DEFAULT_DECIMALS):
        super().__init__()
        self.decimals = decimals

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return to_minor(value, self.decimals)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return from_minor(value, self.decimals)


class ExactDecimal(TypeDecorator):
    impl = String(40)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return format(to_decimal(value).normalize(), "f")

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)
