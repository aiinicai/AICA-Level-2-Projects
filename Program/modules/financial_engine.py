"""
Financial Engine for Ind AS 116 Lease Accounting
Calculates present value of lease flows, initial liability & ROU asset,
amortisation schedules, effective interest, depreciation, and current/non-current splits.
"""
from dataclasses import dataclass
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

@dataclass
class PeriodScheduleRow:
    period_idx: int
    start_date: str
    end_date: str
    payment_date: str
    opening_liability: float
    gross_payment: float
    interest_expense: float
    principal_repayment: float
    closing_liability: float
    current_liability_portion: float
    non_current_liability_portion: float
    opening_rou_asset: float
    depreciation_expense: float
    closing_rou_asset: float
    total_pl_charge: float
    net_cash_outflow: float


@dataclass
class FinancialSummary:
    initial_liability: float
    initial_rou_asset: float
    total_lease_payments: float
    total_interest_expense: float
    total_depreciation_expense: float
    total_pl_cost: float
    effective_periodic_rate: float
    annual_discount_rate: float
    payment_frequency: str
    total_periods: int
    currency: str


class FinancialEngine:
    def __init__(self, currency: str = "INR"):
        self.currency = currency

    def generate_schedule(
        self,
        commencement_date_str: str,
        term_months: int,
        base_rent_per_period: float,
        annual_discount_rate: float,
        frequency: str = "Monthly",
        payment_timing: str = "In Advance",  # "In Advance" or "In Arrears"
        rent_free_months: int = 0,
        escalation_pct: float = 0.0,
        escalation_interval_months: int = 12,
        initial_direct_costs: float = 0.0,
        lease_incentives: float = 0.0,
        restoration_obligation: float = 0.0,
        prepaid_rent: float = 0.0,
        purchase_option_price: float = 0.0,
        residual_value_guarantee: float = 0.0,
        compounding_method: str = "nominal"  # "nominal" or "effective"
    ) -> Tuple[pd.DataFrame, FinancialSummary]:
        """
        Builds the complete period-by-period Ind AS 116 schedule.
        """
        # Parse commencement date
        try:
            start_dt = datetime.strptime(commencement_date_str, "%Y-%m-%d").date()
        except Exception:
            start_dt = date(2024, 4, 1)

        # Map frequency to periods per year and step in months
        freq_map = {
            "Monthly": (12, 1),
            "Quarterly": (4, 3),
            "Half-Yearly": (2, 6),
            "Annual": (1, 12)
        }
        periods_per_year, month_step = freq_map.get(frequency, (12, 1))

        # Calculate total periods
        total_periods = max(1, int(np.ceil(term_months / month_step)))

        # Periodic discount rate
        r_annual = annual_discount_rate / 100.0
        if compounding_method == "effective":
            # Compound interest: (1 + r)^(1/n) - 1
            periodic_rate = ((1.0 + r_annual) ** (1.0 / periods_per_year)) - 1.0
        else:
            # Nominal convention: r / n (ICAI standard convention)
            periodic_rate = r_annual / periods_per_year

        # Step 1: Build payment timeline and calculate cash outflows
        raw_periods = []
        cur_date = start_dt
        rent_free_periods_count = int(np.ceil(rent_free_months / month_step))

        for i in range(total_periods):
            p_idx = i + 1
            p_start = cur_date
            p_end = p_start + relativedelta(months=month_step) - relativedelta(days=1)
            p_pay_date = p_start if payment_timing == "In Advance" else p_end

            # Months elapsed from commencement to this period's start
            months_elapsed = i * month_step

            # Escalation calculation
            escalation_count = 0
            if escalation_pct > 0 and escalation_interval_months > 0:
                escalation_count = months_elapsed // escalation_interval_months

            current_rent = base_rent_per_period * ((1.0 + (escalation_pct / 100.0)) ** escalation_count)

            # Apply rent-free period
            if i < rent_free_periods_count:
                payment_amt = 0.0
            else:
                payment_amt = current_rent

            # If last period and purchase option or RVG exists
            if i == total_periods - 1:
                payment_amt += purchase_option_price + residual_value_guarantee

            raw_periods.append({
                "period_idx": p_idx,
                "start_date": p_start.strftime("%Y-%m-%d"),
                "end_date": p_end.strftime("%Y-%m-%d"),
                "payment_date": p_pay_date.strftime("%Y-%m-%d"),
                "payment_amount": payment_amt
            })

            cur_date = p_start + relativedelta(months=month_step)

        # Step 2: Calculate Present Value (Initial Lease Liability)
        # For payments: PV = Payment / (1 + periodic_rate)^t
        # If In Advance: period 1 payment is at t=0, period 2 is at t=1, etc.
        # If In Arrears: period 1 payment is at t=1, period 2 is at t=2, etc.
        pv_liability = 0.0
        for i, row in enumerate(raw_periods):
            t = i if payment_timing == "In Advance" else (i + 1)
            disc_factor = 1.0 / ((1.0 + periodic_rate) ** t)
            pv_liability += row["payment_amount"] * disc_factor

        initial_liability = float(np.round(pv_liability, 2))

        # Step 3: Calculate Initial ROU Asset (Ind AS 116.24)
        # ROU = Lease Liability + Initial Direct Costs + Restoration Provision + Prepaid Rent - Lease Incentives
        initial_rou = initial_liability + initial_direct_costs + restoration_obligation + prepaid_rent - lease_incentives
        initial_rou = float(np.round(initial_rou, 2))

        # Step 4: Build Amortisation & Depreciation Schedule
        depreciation_per_period = float(np.round(initial_rou / total_periods, 2))
        
        schedule_rows: List[PeriodScheduleRow] = []
        op_liability = initial_liability
        op_rou = initial_rou
        accum_depr = 0.0

        for i, row in enumerate(raw_periods):
            p_idx = row["period_idx"]
            pmt = row["payment_amount"]

            if payment_timing == "In Advance":
                # Advance payment occurs immediately at start of period:
                # Interest is charged on (Opening Liability - Payment)
                net_liability_for_interest = max(0.0, op_liability - pmt)
                interest = net_liability_for_interest * periodic_rate
                cl_liability = net_liability_for_interest + interest
                principal = pmt - (op_liability - (cl_liability - interest))  # net reduction in principal
            else:
                # Arrears payment occurs at end of period:
                interest = op_liability * periodic_rate
                cl_liability = op_liability + interest - pmt
                principal = pmt - interest

            # Adjust for rounding on final period
            if i == total_periods - 1:
                cl_liability = 0.0
                interest = max(0.0, pmt - (op_liability if payment_timing == "In Arrears" else 0.0))
                principal = op_liability if payment_timing == "In Arrears" else pmt

            # Depreciation
            if i == total_periods - 1:
                depr = max(0.0, initial_rou - accum_depr)
                cl_rou = 0.0
            else:
                depr = depreciation_per_period
                cl_rou = max(0.0, op_rou - depr)
            
            accum_depr += depr

            total_pl = interest + depr

            schedule_rows.append(PeriodScheduleRow(
                period_idx=p_idx,
                start_date=row["start_date"],
                end_date=row["end_date"],
                payment_date=row["payment_date"],
                opening_liability=float(np.round(op_liability, 2)),
                gross_payment=float(np.round(pmt, 2)),
                interest_expense=float(np.round(interest, 2)),
                principal_repayment=float(np.round(pmt - interest if pmt >= interest else 0.0, 2)),
                closing_liability=float(np.round(max(0.0, cl_liability), 2)),
                current_liability_portion=0.0,      # will compute in secondary pass
                non_current_liability_portion=0.0,  # will compute in secondary pass
                opening_rou_asset=float(np.round(op_rou, 2)),
                depreciation_expense=float(np.round(depr, 2)),
                closing_rou_asset=float(np.round(max(0.0, cl_rou), 2)),
                total_pl_charge=float(np.round(total_pl, 2)),
                net_cash_outflow=float(np.round(pmt, 2))
            ))

            op_liability = cl_liability
            op_rou = cl_rou

        # Step 5: Secondary Pass to calculate Current vs Non-Current Liability Split
        # For each period, current portion is principal payable in the next 12 months (or next `periods_per_year` periods)
        for i in range(len(schedule_rows)):
            cur_cl = schedule_rows[i].closing_liability
            if cur_cl <= 0:
                schedule_rows[i].current_liability_portion = 0.0
                schedule_rows[i].non_current_liability_portion = 0.0
                continue

            # Look ahead up to periods_per_year
            lookahead_end_idx = min(len(schedule_rows) - 1, i + periods_per_year)
            lookahead_cl = schedule_rows[lookahead_end_idx].closing_liability
            
            # Principal expected to be paid over the next 12 months
            current_portion = max(0.0, cur_cl - lookahead_cl)
            non_current_portion = max(0.0, lookahead_cl)

            schedule_rows[i].current_liability_portion = float(np.round(current_portion, 2))
            schedule_rows[i].non_current_liability_portion = float(np.round(non_current_portion, 2))

        # Convert to DataFrame
        df = pd.DataFrame([vars(r) for r in schedule_rows])
        
        # Build summary
        total_payments = float(df["gross_payment"].sum())
        total_interest = float(df["interest_expense"].sum())
        total_depr = float(df["depreciation_expense"].sum())
        total_pl = total_interest + total_depr

        summary = FinancialSummary(
            initial_liability=initial_liability,
            initial_rou_asset=initial_rou,
            total_lease_payments=float(np.round(total_payments, 2)),
            total_interest_expense=float(np.round(total_interest, 2)),
            total_depreciation_expense=float(np.round(total_depr, 2)),
            total_pl_cost=float(np.round(total_pl, 2)),
            effective_periodic_rate=float(np.round(periodic_rate * 100, 4)),
            annual_discount_rate=annual_discount_rate,
            payment_frequency=frequency,
            total_periods=total_periods,
            currency=self.currency
        )

        return df, summary
