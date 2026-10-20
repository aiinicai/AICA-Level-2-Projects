"""Data model: lease terms, payments, events and (de)serialisation helpers."""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field, fields
from decimal import Decimal
from typing import Any

from .money import D, ZERO, RoundingPolicy, dec, parse_date


def to_jsonable(o: Any):
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    if isinstance(o, dict):
        return {k: to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [to_jsonable(v) for v in o]
    if hasattr(o, 'to_dict'):
        return to_jsonable(o.to_dict())
    return o


def dumps(o) -> str:
    return json.dumps(to_jsonable(o), ensure_ascii=False, sort_keys=True)


@dataclass
class Payment:
    date: dt.date
    amount: Decimal
    kind: str = 'lease'   # lease | rvg (residual value guarantee) | purchase_option | termination_penalty
    note: str = ''
    edited: bool = False

    def to_dict(self):
        return {'date': self.date.isoformat(), 'amount': str(self.amount), 'kind': self.kind, 'note': self.note, 'edited': self.edited}

    @staticmethod
    def from_dict(d):
        return Payment(parse_date(d['date']), dec(d['amount']), d.get('kind', 'lease'), d.get('note', ''), bool(d.get('edited', False)))


@dataclass
class LeaseTerms:
    # --- identification
    ref: str = ''
    lessor: str = ''
    asset: str = ''
    signing_date: dt.date | None = None
    commencement: dt.date | None = None
    end_date: dt.date | None = None                 # last day of the lease term (inclusive)
    # --- currency
    functional_currency: str = 'AED'
    currency: str = 'AED'
    fx_rate: Decimal = D(1)                        # lease currency -> functional currency, fixed (see limitations)
    # --- payments
    payment_amount: Decimal = ZERO                 # regular payment, in lease currency
    frequency: str = 'monthly'                     # monthly | quarterly | semi-annual | annual
    timing: str = 'arrears'                        # advance | arrears
    payments: list[Payment] = field(default_factory=list)   # explicit schedule (functional currency); generated if empty
    # --- discounting
    discount_rate: Decimal = D('0.05')             # annual rate as a fraction
    rate_basis: str = 'IBR'                        # IBR | implicit
    day_count: str = 'ACT/365'
    compounding: str = 'annual'
    # --- ROU asset
    depreciation_method: str = 'straight_line'     # straight_line | declining_balance
    db_rate: Decimal = ZERO                        # annual rate for declining_balance (0 = 2 / useful life)
    useful_life_years: Decimal = ZERO
    ownership_transfers: bool = False
    # --- other components (lease currency)
    incentives_received: Decimal = ZERO
    prepaid_before_commencement: Decimal = ZERO
    initial_direct_costs: Decimal = ZERO
    restoration_obligation: Decimal = ZERO        # present value of the estimated restoration cost (IAS 37 measurement, entered by user)
    rvg_expected: Decimal = ZERO                   # amount expected payable under residual value guarantee
    purchase_option_price: Decimal = ZERO
    purchase_option_certain: bool = False         # reasonably certain to exercise (IFRS 16.27(d))
    termination_penalty: Decimal = ZERO
    termination_penalty_included: bool = False    # lease term reflects exercise of a termination option (IFRS 16.27(g))
    index_linked: bool = False
    floating_rate_linked: bool = False
    # --- exemptions
    exemption: str = 'none'                        # none | short_term | low_value
    exemption_elected: bool = False
    asset_value_new: Decimal = ZERO                # value of the asset when new, for the low-value test
    low_value_threshold: Decimal = D(5000)
    # --- policy
    posting_granularity: str = 'monthly'           # monthly | per_payment
    rounding: RoundingPolicy = field(default_factory=RoundingPolicy)
    notes: str = ''

    def fx(self, amount) -> Decimal:
        return self.rounding.q(dec(amount) * self.fx_rate)

    def to_dict(self):
        d = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if f.name == 'payments':
                d[f.name] = [p.to_dict() for p in v]
            elif f.name == 'rounding':
                d[f.name] = v.to_dict()
            else:
                d[f.name] = to_jsonable(v)
        return d

    @staticmethod
    def from_dict(d):
        t = LeaseTerms()
        dates = {'signing_date', 'commencement', 'end_date'}
        decs = {'fx_rate', 'payment_amount', 'discount_rate', 'db_rate', 'useful_life_years', 'incentives_received', 'prepaid_before_commencement',
                'initial_direct_costs', 'restoration_obligation', 'rvg_expected', 'purchase_option_price', 'termination_penalty', 'asset_value_new',
                'low_value_threshold'}
        for f in fields(t):
            if f.name not in d:
                continue
            v = d[f.name]
            if f.name in dates:
                v = parse_date(v) if v else None
            elif f.name in decs:
                v = dec(v)
            elif f.name == 'payments':
                v = [Payment.from_dict(p) for p in v]
            elif f.name == 'rounding':
                v = RoundingPolicy.from_dict(v)
            setattr(t, f.name, v)
        return t


EVENT_TYPES = {
    'term_reassessment': 'Reassessment – lease term / purchase option (revised discount rate)',
    'index_change': 'Reassessment – index / rate-linked payments change',
    'rvg_change': 'Reassessment – residual value guarantee amount',
    'modification': 'Lease modification (negotiated)',
    'termination': 'Termination – full or partial',
}


@dataclass
class Event:
    type: str
    effective_date: dt.date
    params: dict = field(default_factory=dict)
    label: str = ''

    def to_dict(self):
        return {'type': self.type, 'effective_date': self.effective_date.isoformat(), 'params': to_jsonable(self.params), 'label': self.label}

    @staticmethod
    def from_dict(d):
        return Event(d['type'], parse_date(d['effective_date']), dict(d.get('params', {})), d.get('label', ''))
