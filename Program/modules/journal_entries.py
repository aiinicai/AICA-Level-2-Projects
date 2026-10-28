"""
Journal Entries Generator for Ind AS 116 Lease Accounting
Generates debits, credits, account heads, dates, and narrative vouchers for:
- Initial recognition at commencement
- Periodic interest accrual & lease payments
- Periodic ROU asset depreciation
- Short-term & low-value exempt leases
- Final derecognition & closure entries
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import pandas as pd
from modules.financial_engine import FinancialSummary
from modules.ind_as_116_engine import IndAS116Assessment

@dataclass
class JournalEntryLine:
    entry_id: str
    date: str
    period: str
    account_head: str
    account_category: str  # "Asset", "Liability", "Equity", "Revenue", "Expense"
    debit_amount: float
    credit_amount: float
    narration: str


class JournalEntryEngine:
    def __init__(self, currency: str = "INR"):
        self.currency = currency

    def generate_all_entries(
        self,
        assessment: IndAS116Assessment,
        summary: Optional[FinancialSummary],
        schedule_df: Optional[pd.DataFrame],
        commencement_date: str,
        asset_description: str
    ) -> List[JournalEntryLine]:
        """
        Builds chronological journal entries based on assessment and schedule.
        """
        entries: List[JournalEntryLine] = []
        entry_counter = 1

        # Case 1: Short-Term or Low-Value Exemption Elected
        if assessment.accounting_classification in ["SHORT_TERM_EXEMPT", "LOW_VALUE_EXEMPT"]:
            # Generate straight-line rent expense entries
            term_months = assessment.effective_lease_term_months
            monthly_rent = assessment.lease_component_amount
            total_rent = monthly_rent * term_months

            # Entry 1: Monthly or periodic rent payment
            entries.append(JournalEntryLine(
                entry_id=f"JE-{entry_counter:04d}",
                date=commencement_date,
                period="Period 1",
                account_head="Rent / Lease Expense (P&L)",
                account_category="Expense",
                debit_amount=monthly_rent,
                credit_amount=0.0,
                narration=(
                    f"Being lease rental recognized on straight-line basis for exempt lease "
                    f"({assessment.accounting_classification}) under Ind AS 116 para 6 for {asset_description}."
                )
            ))
            entries.append(JournalEntryLine(
                entry_id=f"JE-{entry_counter:04d}",
                date=commencement_date,
                period="Period 1",
                account_head="Bank / Cash Account",
                account_category="Asset",
                debit_amount=0.0,
                credit_amount=monthly_rent,
                narration="Being payment of exempt lease rental."
            ))
            entry_counter += 1

            entries.append(JournalEntryLine(
                entry_id=f"JE-{entry_counter:04d}",
                date="Subsequent Periods",
                period="Periods 2 to End",
                account_head="Rent / Lease Expense (P&L)",
                account_category="Expense",
                debit_amount=total_rent - monthly_rent,
                credit_amount=0.0,
                narration="Being recurring lease expense recognized over remaining term of exempt lease."
            ))
            entries.append(JournalEntryLine(
                entry_id=f"JE-{entry_counter:04d}",
                date="Subsequent Periods",
                period="Periods 2 to End",
                account_head="Bank / Cash Account",
                account_category="Asset",
                debit_amount=0.0,
                credit_amount=total_rent - monthly_rent,
                narration="Being recurring lease rental payments."
            ))
            return entries

        # Case 2: Full Ind AS 116 On-Balance Sheet Accounting
        if not summary or schedule_df is None or schedule_df.empty:
            return entries

        # ---------------- 1. Initial Recognition Entry ----------------
        entries.append(JournalEntryLine(
            entry_id=f"JE-{entry_counter:04d}",
            date=commencement_date,
            period="Commencement",
            account_head="Right-of-Use Asset (Gross Block)",
            account_category="Asset",
            debit_amount=summary.initial_rou_asset,
            credit_amount=0.0,
            narration=(
                f"Being initial recognition of Right-of-Use Asset for {asset_description} "
                f"at PV of lease payments plus initial direct costs/restoration obligations under Ind AS 116.24."
            )
        ))
        
        entries.append(JournalEntryLine(
            entry_id=f"JE-{entry_counter:04d}",
            date=commencement_date,
            period="Commencement",
            account_head="Lease Liability Account",
            account_category="Liability",
            debit_amount=0.0,
            credit_amount=summary.initial_liability,
            narration=f"Being initial measurement of lease liability at present value of lease payments discounted at {summary.annual_discount_rate}% p.a."
        ))

        if assessment.initial_direct_costs > 0:
            entries.append(JournalEntryLine(
                entry_id=f"JE-{entry_counter:04d}",
                date=commencement_date,
                period="Commencement",
                account_head="Bank / Cash (Initial Direct Costs)",
                account_category="Asset",
                debit_amount=0.0,
                credit_amount=assessment.initial_direct_costs,
                narration="Being initial direct costs (legal, brokerage, stamp duty) capitalized into ROU Asset."
            ))

        if assessment.restoration_provision > 0:
            entries.append(JournalEntryLine(
                entry_id=f"JE-{entry_counter:04d}",
                date=commencement_date,
                period="Commencement",
                account_head="Provision for Decommissioning / Site Restoration",
                account_category="Liability",
                debit_amount=0.0,
                credit_amount=assessment.restoration_provision,
                narration="Being provision for dismantling and restoration obligation recognized under Ind AS 37."
            ))

        if assessment.lease_incentives > 0:
            entries.append(JournalEntryLine(
                entry_id=f"JE-{entry_counter:04d}",
                date=commencement_date,
                period="Commencement",
                account_head="Bank / Cash (Lease Incentive Received)",
                account_category="Asset",
                debit_amount=assessment.lease_incentives,
                credit_amount=0.0,
                narration="Being lease incentive received from Lessor deducted from ROU Asset cost."
            ))

        entry_counter += 1

        # ---------------- 2. Periodic Payment & Interest Accrual Entries ----------------
        for _, row in schedule_df.iterrows():
            p_idx = int(row["period_idx"])
            p_date = str(row["payment_date"])
            pmt = float(row["gross_payment"])
            interest = float(row["interest_expense"])
            principal = float(row["principal_repayment"])
            depr = float(row["depreciation_expense"])

            # A. Payment Entry
            if pmt > 0:
                entries.append(JournalEntryLine(
                    entry_id=f"JE-{entry_counter:04d}",
                    date=p_date,
                    period=f"Period {p_idx}",
                    account_head="Lease Liability Account",
                    account_category="Liability",
                    debit_amount=principal,
                    credit_amount=0.0,
                    narration=f"Being principal portion of lease payment for Period {p_idx}."
                ))
                
                if interest > 0:
                    entries.append(JournalEntryLine(
                        entry_id=f"JE-{entry_counter:04d}",
                        date=p_date,
                        period=f"Period {p_idx}",
                        account_head="Finance Cost - Interest on Lease Liability (P&L)",
                        account_category="Expense",
                        debit_amount=interest,
                        credit_amount=0.0,
                        narration=f"Being interest expense on lease liability recognized using effective interest method for Period {p_idx}."
                    ))

                entries.append(JournalEntryLine(
                    entry_id=f"JE-{entry_counter:04d}",
                    date=p_date,
                    period=f"Period {p_idx}",
                    account_head="Bank / Cash Account",
                    account_category="Asset",
                    debit_amount=0.0,
                    credit_amount=pmt,
                    narration=f"Being periodic lease rental payment made to Lessor for Period {p_idx}."
                ))
                entry_counter += 1

            # B. Depreciation Entry
            if depr > 0:
                entries.append(JournalEntryLine(
                    entry_id=f"JE-{entry_counter:04d}",
                    date=str(row["end_date"]),
                    period=f"Period {p_idx}",
                    account_head="Depreciation Expense - Right-of-Use Asset (P&L)",
                    account_category="Expense",
                    debit_amount=depr,
                    credit_amount=0.0,
                    narration=f"Being straight-line depreciation of ROU Asset over lease term for Period {p_idx}."
                ))
                entries.append(JournalEntryLine(
                    entry_id=f"JE-{entry_counter:04d}",
                    date=str(row["end_date"]),
                    period=f"Period {p_idx}",
                    account_head="Accumulated Depreciation - ROU Asset",
                    account_category="Asset",
                    debit_amount=0.0,
                    credit_amount=depr,
                    narration=f"Being accumulated depreciation recorded against ROU Asset for Period {p_idx}."
                ))
                entry_counter += 1

        # ---------------- 3. Final Period Derecognition Entry ----------------
        last_row = schedule_df.iloc[-1]
        final_date = str(last_row["end_date"])
        entries.append(JournalEntryLine(
            entry_id=f"JE-{entry_counter:04d}",
            date=final_date,
            period="Lease Expiry",
            account_head="Accumulated Depreciation - ROU Asset",
            account_category="Asset",
            debit_amount=summary.initial_rou_asset,
            credit_amount=0.0,
            narration="Being reversal and derecognition of accumulated depreciation upon expiry/closure of lease contract."
        ))
        entries.append(JournalEntryLine(
            entry_id=f"JE-{entry_counter:04d}",
            date=final_date,
            period="Lease Expiry",
            account_head="Right-of-Use Asset (Gross Block)",
            account_category="Asset",
            debit_amount=0.0,
            credit_amount=summary.initial_rou_asset,
            narration="Being derecognition of gross block of Right-of-Use Asset upon expiry of lease term."
        ))

        return entries

    def to_dataframe(self, entries: List[JournalEntryLine]) -> pd.DataFrame:
        """Converts journal entries to formatted DataFrame."""
        return pd.DataFrame([asdict(e) for e in entries])
