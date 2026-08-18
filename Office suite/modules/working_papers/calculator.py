from datetime import datetime, date
import math
import logging

logger = logging.getLogger("FDCalculator")

class FDCalculator:
    def __init__(self, financial_year: str = "2024-25"):
        self.financial_year = financial_year
        self.fy_start_date, self.reporting_date = self._get_fy_dates(financial_year)

    def _get_fy_dates(self, fy_str: str):
        """
        Calculates start date (April 1st) and reporting date (March 31st) for given Financial Year string.
        Example: "2024-25" -> (2024-04-01, 2025-03-31)
        """
        try:
            parts = fy_str.strip().replace('/', '-').split('-')
            start_yr = int(parts[0])
            if len(parts[1]) == 2:
                end_yr = (start_yr // 100) * 100 + int(parts[1])
            else:
                end_yr = int(parts[1])
            
            return date(start_yr, 4, 1), date(end_yr, 3, 31)
        except Exception:
            return date(2024, 4, 1), date(2025, 3, 31)

    @staticmethod
    def get_prior_fy(fy_str: str) -> str:
        """Returns the prior financial year string. Example: '2025-26' -> '2024-25'."""
        try:
            parts = fy_str.strip().replace('/', '-').split('-')
            start_yr = int(parts[0]) - 1
            end_yr_val = int(parts[1]) - 1
            if len(parts[1]) == 2:
                return f"{start_yr}-{end_yr_val:02d}"
            else:
                return f"{start_yr}-{end_yr_val}"
        except Exception:
            return "2023-24"

    @staticmethod
    def parse_date(date_val) -> date:
        """Parses various date formats into datetime.date object with fallback safety."""
        if isinstance(date_val, date) and not isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, datetime):
            return date_val.date()
        
        d_str = str(date_val).strip().split('T')[0].split(' ')[0]
        
        for fmt in [
            "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y",
            "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y",
            "%b %d, %Y", "%B %d, %Y"
        ]:
            try:
                dt = datetime.strptime(d_str, fmt).date()
                if 1990 <= dt.year <= 2050:
                    return dt
            except ValueError:
                pass
        
        logger.warning(f"Unable to parse date string '{date_val}', defaulting to 2024-01-15.")
        return date(2024, 1, 15)

    def process_fd(
        self,
        bank_name: str,
        fd_account_number: str,
        principal_amount: float,
        date_of_issue,
        date_of_maturity,
        interest_rate: float,
        compounding_frequency: str = "Quarterly",
        opening_accrued_interest: float = 0.0,
        tds_deducted: float = 0.0,
        status: str = "Active",
        is_roll_forward: bool = False,
        opening_principal_override: float = None
    ) -> dict:
        """
        Processes an FD record, computes Interest Income, Movement Schedule, Closing Balances, and Statutory Classification.
        """
        issue_d = self.parse_date(date_of_issue)
        maturity_d = self.parse_date(date_of_maturity)

        # 1. Maturity Days Calculations
        original_maturity_days = max(0, (maturity_d - issue_d).days)
        remaining_maturity_days = max(0, (maturity_d - self.reporting_date).days) if maturity_d > self.reporting_date else 0

        # 2. Movement Schedule Logic (Opening, Created, Matured, Closing Principal)
        principal_amount = round(principal_amount or 0.0, 2)
        status_clean = status.capitalize() if status else "Active"

        if is_roll_forward or opening_principal_override is not None:
            opening_principal = round(opening_principal_override if opening_principal_override is not None else principal_amount, 2)
            created_principal = 0.0
        elif issue_d <= self.fy_start_date:
            opening_principal = principal_amount
            created_principal = 0.0
        else:
            opening_principal = 0.0
            created_principal = principal_amount

        if maturity_d <= self.reporting_date and status_clean == "Matured":
            matured_principal = max(opening_principal, principal_amount)
        else:
            matured_principal = 0.0

        closing_principal = round(opening_principal + created_principal - matured_principal, 2)

        # 3. Interest Calculation for Current Financial Year (Actual/365)
        effective_start = max(issue_d, self.fy_start_date)
        effective_end = min(maturity_d, self.reporting_date)
        days_in_fy = max(0, (effective_end - effective_start).days)
        
        r = (interest_rate or 0.0) / 100.0
        freq_str = (compounding_frequency or "Quarterly").strip().capitalize()

        if days_in_fy <= 0 or r <= 0:
            interest_income = 0.0
        elif freq_str == "Simple":
            interest_income = max(opening_principal, principal_amount) * r * (days_in_fy / 365.0)
        else:
            n_map = {"Monthly": 12, "Quarterly": 4, "Half-yearly": 2, "Half-year": 2, "Annual": 1, "Yearly": 1}
            n = n_map.get(freq_str, 4)
            t_years = days_in_fy / 365.0
            base_amount = max(opening_principal, principal_amount) + (opening_accrued_interest or 0.0)
            interest_income = base_amount * (math.pow(1 + (r / n), n * t_years) - 1)

        interest_income = round(interest_income, 2)
        opening_accrued_interest = round(opening_accrued_interest or 0.0, 2)
        tds_deducted = round(tds_deducted or 0.0, 2)

        # 4. Accrued Interest Movement & Closing
        if matured_principal > 0:
            settled_accrued_interest = round(opening_accrued_interest + interest_income - tds_deducted, 2)
            closing_accrued_interest = 0.0
        else:
            settled_accrued_interest = 0.0
            closing_accrued_interest = round(opening_accrued_interest + interest_income - tds_deducted, 2)

        closing_total_balance = round(closing_principal + closing_accrued_interest, 2)

        # 5. Statutory Classification Logic
        if original_maturity_days <= 90:
            classification_class = "Class 1"
            classification_label = "Cash & Cash Equivalents"
        elif remaining_maturity_days <= 365:
            classification_class = "Class 2"
            classification_label = "Other Current Bank Balances"
        else:
            classification_class = "Class 3"
            classification_label = "Non-Current Assets"

        return {
            "bank_name": bank_name.strip() if bank_name else "Unknown Bank",
            "fd_account_number": str(fd_account_number).strip(),
            "principal_amount": principal_amount,
            "date_of_issue": issue_d.strftime("%Y-%m-%d"),
            "date_of_maturity": maturity_d.strftime("%Y-%m-%d"),
            "interest_rate": round(interest_rate or 0.0, 2),
            "compounding_frequency": freq_str,
            "opening_accrued_interest": opening_accrued_interest,
            "tds_deducted": tds_deducted,
            "status": status_clean,
            "opening_principal": opening_principal,
            "created_principal": created_principal,
            "matured_principal": matured_principal,
            "settled_accrued_interest": settled_accrued_interest,
            "original_maturity_days": original_maturity_days,
            "remaining_maturity_days": remaining_maturity_days,
            "interest_income": interest_income,
            "closing_accrued_interest": closing_accrued_interest,
            "closing_principal": closing_principal,
            "closing_total_balance": closing_total_balance,
            "classification_class": classification_class,
            "classification_label": classification_label,
            "reporting_date": self.reporting_date.strftime("%Y-%m-%d")
        }
