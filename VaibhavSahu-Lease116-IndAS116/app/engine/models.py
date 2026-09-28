"""Engine data model (inputs and outputs).

These are plain dataclasses with no dependency on the database or the UI, so the
accounting engine can be unit-tested and reproduced from a stored input snapshot.
All monetary values are Decimal in the lease currency unless stated otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from .decimal_utils import ZERO
from .rates import DayCount, RateConvention


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class Framework(str, Enum):
    IND_AS_116 = "IND_AS_116"
    IFRS_16 = "IFRS_16"


class PaymentCategory(str, Enum):
    FIXED = "FIXED"
    IN_SUBSTANCE_FIXED = "IN_SUBSTANCE_FIXED"
    INDEX_LINKED = "INDEX_LINKED"          # e.g. CPI (para 27(b), 28)
    RATE_LINKED = "RATE_LINKED"            # benchmark interest rate (para 27(b), 28, 43)
    VARIABLE = "VARIABLE"                  # sales/usage based — excluded (para 38(b))
    RVG = "RVG"                            # residual value guarantee expected payable (27(c))
    PURCHASE_OPTION = "PURCHASE_OPTION"    # exercise price (27(d))
    TERMINATION_PENALTY = "TERMINATION_PENALTY"  # (27(e))
    INCENTIVE = "INCENTIVE"                # lease incentive receivable (negative, 27(a))
    NON_LEASE = "NON_LEASE"                # service/CAM only line


class OptionKind(str, Enum):
    EXTENSION = "EXTENSION"
    TERMINATION = "TERMINATION"
    PURCHASE = "PURCHASE"


class OptionHolder(str, Enum):
    LESSEE = "LESSEE"
    LESSOR = "LESSOR"
    BOTH = "BOTH"


class Timing(str, Enum):
    ADVANCE = "ADVANCE"
    ARREARS = "ARREARS"


class EventType(str, Enum):
    MODIFICATION = "MODIFICATION"
    REASSESSMENT = "REASSESSMENT"
    TERMINATION = "TERMINATION"
    IMPAIRMENT = "IMPAIRMENT"
    RESTORATION_REVISION = "RESTORATION_REVISION"
    ROU_DERECOGNITION = "ROU_DERECOGNITION"      # e.g. portion of ROU subleased under a finance sublease (B58)


class ReassessmentKind(str, Enum):
    LEASE_TERM = "LEASE_TERM"            # para 40(a) — revised rate
    PURCHASE_OPTION = "PURCHASE_OPTION"  # para 40(b) — revised rate
    RVG = "RVG"                          # para 42(a) — unchanged rate
    INDEX_RATE = "INDEX_RATE"            # para 42(b) — unchanged rate
    FLOATING_RATE = "FLOATING_RATE"      # para 43 — revised rate reflecting interest-rate change


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# ---------------------------------------------------------------------------
# Policies and flags
# ---------------------------------------------------------------------------
@dataclass
class Policy:
    """Entity accounting policies / calculation conventions (spec section 2, 32)."""

    framework: Framework = Framework.IND_AS_116
    daycount: DayCount = DayCount.ACT_365F
    rate_convention: RateConvention = RateConvention.EFFECTIVE_ANNUAL
    commencement_payment_paid: bool = True          # A2
    depreciation_method: str = "DAILY"               # DAILY | MONTHLY_EQUAL
    current_split_method: str = "PRINCIPAL_12M"      # PRINCIPAL_12M | PV_12M
    rounding_method: str = "BALANCE"                 # BALANCE | INTEREST_TRUEUP
    currency_decimals: int = 2
    fy_start_month: int = 4
    maturity_buckets: tuple = (1, 2, 3, 4, 5)        # years; > last = "more than"
    truep_tolerance: Decimal = Decimal("1.00")       # rounding true-up above this is an exception
    lessor_income_method: str = "MONTHLY_EQUAL"      # lessor operating-lease straight-line basis: MONTHLY_EQUAL | DAILY


@dataclass
class JudgmentFlag:
    code: str
    title: str
    detail: str
    reference: str = ""
    severity: str = "REVIEW"     # REVIEW | INFO
    assumptions: list[str] = field(default_factory=list)


@dataclass
class Issue:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    field: str = ""
    reference: str = ""


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
@dataclass
class PaymentLine:
    date: date
    lease_amount: Decimal
    non_lease_amount: Decimal = ZERO
    category: PaymentCategory = PaymentCategory.FIXED
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    description: str = ""
    line_no: int = 0
    include_override: Optional[bool] = None
    override_reason: str = ""
    source: str = "GENERATED"
    # determined by the engine
    included: bool = False
    inclusion_reason: str = ""


@dataclass
class LeaseOption:
    kind: OptionKind
    holder: OptionHolder = OptionHolder.LESSEE
    exercise_date: Optional[date] = None        # termination/purchase effective date; extension start
    extension_end_date: Optional[date] = None   # end of the extended period (inclusive)
    price: Decimal = ZERO                       # purchase price / termination penalty
    reasonably_certain: bool = False
    # EXTENSION / PURCHASE: reasonably certain TO exercise
    # TERMINATION: reasonably certain NOT to exercise (period after the option is then included)
    rationale: str = ""
    description: str = ""


@dataclass
class LeaseTermInput:
    commencement: date
    contract_end: date                          # last day of the contractual (non-extended) term
    options: list[LeaseOption] = field(default_factory=list)
    enforceable_end: Optional[date] = None      # B34 cap (both parties may terminate) — judgment
    enforceable_rationale: str = ""


@dataclass
class CostItem:
    date: date
    amount: Decimal
    description: str = ""


@dataclass
class DepositInput:
    amount: Decimal
    payment_date: date
    refund_date: date
    interest_bearing: bool = False
    contractual_rate_pct: Decimal = ZERO      # coupon if interest-bearing (simple annual, paid at refund)
    market_rate_pct: Optional[Decimal] = None  # rate for fair value (Ind AS 109) — required if not at market
    treat_difference_as_prepaid_rent: bool = True  # policy (A7)
    description: str = "Refundable security deposit"


@dataclass
class RestorationInput:
    estimated_cost: Decimal                    # amount expected to be spent at settlement date
    settlement_date: date
    discount_rate_pct: Decimal                 # pre-tax rate (Ind AS 37.47)
    recognition_date: Optional[date] = None    # default commencement
    cost_is_current_price: bool = False        # if True, inflate with inflation_pct to settlement
    inflation_pct: Decimal = ZERO
    description: str = "Restoration / reinstatement obligation"


@dataclass
class FxInput:
    functional_currency: str
    rates: dict                                # {date: Decimal} functional units per 1 lease-currency unit (spot/closing)
    average_rates: dict = field(default_factory=dict)  # {period_end: Decimal}


@dataclass
class OpeningBalance:
    """Cut-over / migration: continue from given balances instead of recomputing history."""

    cutover_date: date                          # balances are as at the START of this date
    liability: Decimal
    rou_cost: Decimal
    rou_acc_dep: Decimal = ZERO
    rou_acc_imp: Decimal = ZERO
    use_implied_rate: bool = True               # solve the rate that amortises the given liability


@dataclass
class ModificationInput:
    effective_date: date
    description: str = ""
    new_payments: list[PaymentLine] = field(default_factory=list)  # replaces all payments on/after effective date
    revised_rate_pct: Optional[Decimal] = None
    new_term_end: Optional[date] = None
    scope_decrease_fraction: Decimal = ZERO     # area / units reduction (0..1) — partial termination
    additional_rou: bool = False                # adds right to use one or more underlying assets
    commensurate_standalone_price: bool = False  # para 44(b)
    new_useful_life_end: Optional[date] = None
    purchase_option_rc: Optional[bool] = None


@dataclass
class ReassessmentInput:
    effective_date: date
    kind: ReassessmentKind
    description: str = ""
    new_payments: list[PaymentLine] = field(default_factory=list)
    revised_rate_pct: Optional[Decimal] = None
    new_term_end: Optional[date] = None
    purchase_option_rc: Optional[bool] = None
    new_useful_life_end: Optional[date] = None


@dataclass
class TerminationInput:
    effective_date: date
    penalty: Decimal = ZERO
    description: str = ""


@dataclass
class ImpairmentInput:
    effective_date: date
    impairment_amount: Optional[Decimal] = None     # positive = loss; negative = reversal
    recoverable_amount: Optional[Decimal] = None    # alternative input
    cgu: str = ""
    rationale: str = ""


@dataclass
class RestorationRevisionInput:
    effective_date: date
    new_estimated_cost: Optional[Decimal] = None
    new_discount_rate_pct: Optional[Decimal] = None
    new_settlement_date: Optional[date] = None
    description: str = ""


@dataclass
class RouDerecognitionInput:
    effective_date: date
    fraction: Decimal                            # portion of the ROU asset derecognised (0..1)
    description: str = ""
    clearing_role: str = "SUBLEASE_CLEARING"


@dataclass
class LeaseEvent:
    type: EventType
    effective_date: date
    ref: str = ""
    apply_after_payments: bool = False     # process after payments dated on the effective date (default: before)
    modification: Optional[ModificationInput] = None
    reassessment: Optional[ReassessmentInput] = None
    termination: Optional[TerminationInput] = None
    impairment: Optional[ImpairmentInput] = None
    restoration_revision: Optional[RestorationRevisionInput] = None
    rou_derecognition: Optional[RouDerecognitionInput] = None


@dataclass
class LesseeLeaseInput:
    lease_id: str
    commencement: date
    term: LeaseTermInput
    payments: list[PaymentLine]
    discount_rate_pct: Decimal
    currency: str = "INR"
    rate_basis: str = "IBR"                    # IBR | IMPLICIT
    policy: Policy = field(default_factory=Policy)
    asset_class: str = "Buildings"
    description: str = ""
    idc: list[CostItem] = field(default_factory=list)
    incentives_received: list[CostItem] = field(default_factory=list)
    prepaid_before_commencement: list[CostItem] = field(default_factory=list)
    other_rou_adjustments: list[CostItem] = field(default_factory=list)
    deposit: Optional[DepositInput] = None
    restoration: Optional[RestorationInput] = None
    useful_life_end: Optional[date] = None     # of the underlying asset (para 32)
    ownership_transfers: bool = False
    non_lease_expedient: bool = False          # para 15 elected for the class
    events: list[LeaseEvent] = field(default_factory=list)
    fx: Optional[FxInput] = None
    opening: Optional[OpeningBalance] = None
    schedule_end: Optional[date] = None        # optional horizon for period rows


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
@dataclass
class TermResult:
    commencement: date
    contract_end: date
    noncancellable_end: date
    term_end: date
    max_possible_end: date
    term_days: int
    term_months: Decimal
    purchase_option_rc: bool
    explanation: list[str] = field(default_factory=list)
    flags: list[JudgmentFlag] = field(default_factory=list)
    termination_reflected: bool = False


@dataclass
class PVLine:
    date: date
    amount: Decimal
    years: Decimal
    discount_factor: Decimal
    present_value: Decimal
    category: str
    description: str = ""


@dataclass
class ExcludedLine:
    date: date
    amount: Decimal
    category: str
    reason: str
    description: str = ""


@dataclass
class InitialMeasurement:
    measurement_date: date
    rate_pct: Decimal
    effective_annual_rate: Decimal
    daycount: str
    convention: str
    liability_exact: Decimal
    liability: Decimal
    pv_lines: list[PVLine]
    excluded: list[ExcludedLine]
    undiscounted_total: Decimal
    rou_components: list[tuple[str, Decimal, str]]   # (label, amount, reference)
    rou: Decimal
    depreciation_end: date


@dataclass
class PeriodRow:
    period_start: date
    period_end: date
    # lease liability
    liab_open: Decimal = ZERO
    liab_additions: Decimal = ZERO
    interest: Decimal = ZERO
    payments: Decimal = ZERO
    liab_remeasurement: Decimal = ZERO
    liab_modification: Decimal = ZERO
    liab_derecognised: Decimal = ZERO
    liab_fx: Decimal = ZERO                # exchange differences (functional-currency view only)
    liab_close: Decimal = ZERO
    liab_current: Decimal = ZERO
    liab_noncurrent: Decimal = ZERO
    rounding_trueup: Decimal = ZERO
    # ROU asset (net carrying amount and components)
    rou_open: Decimal = ZERO
    rou_additions: Decimal = ZERO
    depreciation: Decimal = ZERO
    impairment: Decimal = ZERO             # loss (+) / reversal (−)
    rou_remeasurement: Decimal = ZERO
    rou_modification: Decimal = ZERO
    rou_derecognised: Decimal = ZERO
    rou_close: Decimal = ZERO
    rou_cost_close: Decimal = ZERO
    rou_accdep_close: Decimal = ZERO
    rou_accimp_close: Decimal = ZERO
    # P&L and cash
    gain_loss: Decimal = ZERO              # + gain / − loss from events
    remeasurement_pl: Decimal = ZERO       # para 39 excess taken to P&L (+ gain)
    variable_expense: Decimal = ZERO
    non_lease_expense: Decimal = ZERO
    cash_outflow: Decimal = ZERO           # lease payments incl. excluded variable/non-lease
    # restoration provision
    prov_open: Decimal = ZERO
    prov_additions: Decimal = ZERO
    prov_unwinding: Decimal = ZERO
    prov_revision: Decimal = ZERO
    prov_settled: Decimal = ZERO
    prov_close: Decimal = ZERO
    # security deposit
    dep_open: Decimal = ZERO
    dep_additions: Decimal = ZERO
    dep_interest: Decimal = ZERO
    dep_refund: Decimal = ZERO
    dep_close: Decimal = ZERO
    # maturity (undiscounted remaining included payments) by bucket at period end
    maturity: dict = field(default_factory=dict)
    status: str = "ACTIVE"
    rate_pct: Decimal = ZERO
    detail: dict = field(default_factory=dict)   # explainability: interest sub-intervals, depreciation segments


@dataclass
class PaymentRow:
    no: int
    date: date
    opening: Decimal
    interest: Decimal
    payment: Decimal
    adjustment: Decimal
    principal: Decimal
    closing: Decimal
    note: str = ""


@dataclass
class Posting:
    """Accounting posting produced by the engine; resolved to GL accounts later."""

    date: date
    event: str                     # COMMENCEMENT | INTEREST | PAYMENT | DEPRECIATION | ...
    narration: str
    lines: list[tuple[str, Decimal, Decimal]]   # (gl_role, debit, credit)
    period_end: Optional[date] = None
    ref: str = ""


@dataclass
class EventResult:
    type: str
    effective_date: date
    ref: str
    description: str
    steps: list[tuple[str, Decimal, str]]        # (label, amount, explanation)
    liability_before: Decimal
    liability_after: Decimal
    rou_before: Decimal
    rou_after: Decimal
    gain_loss: Decimal
    rate_before_pct: Decimal
    rate_after_pct: Decimal
    term_end_before: Optional[date] = None
    term_end_after: Optional[date] = None
    separate_lease: bool = False
    flags: list[JudgmentFlag] = field(default_factory=list)
    reference: str = ""


@dataclass
class LesseeResult:
    lease_id: str
    currency: str
    term: TermResult
    initial: InitialMeasurement
    periods: list[PeriodRow]
    payment_rows: list[PaymentRow]
    events: list[EventResult]
    postings: list[Posting]
    payments: list[PaymentLine]
    flags: list[JudgmentFlag]
    issues: list[Issue]
    deposit: Optional[dict] = None
    restoration: Optional[dict] = None
    fx_periods: Optional[list] = None
    totals: dict = field(default_factory=dict)
    engine_version: str = ""
