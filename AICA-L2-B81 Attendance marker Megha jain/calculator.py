"""
Attendance cum Salary Calculator Logic Engine
Based on CA Firm Employment Offer Letter Rules
Supports multiple employees and custom parameters
"""

from datetime import date, datetime, timedelta
import calendar
import sys
from typing import Dict, List, Optional, Tuple

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class AttendanceSalaryCalculator:
    def __init__(
        self,
        basic_salary: float = 20000.0,
        joining_date: date = date(2026, 4, 13),
        retainership_bonus: float = 60000.0,
        retainership_target_date: date = date(2027, 12, 31),
        standard_daily_hours: float = 9.0, # 9:30 AM to 7:00 PM minus 30 min lunch = 9 hours
        weekly_target_hours: float = 50.0, # 5.5 days (5 days * 9h + 1 half day * 5h = 50h)
    ):
        self.basic_salary = basic_salary
        self.joining_date = joining_date
        self.retainership_bonus = retainership_bonus
        self.retainership_target_date = retainership_target_date
        self.standard_daily_hours = standard_daily_hours
        self.weekly_target_hours = weekly_target_hours

    def get_month_days(self, year: int, month: int) -> int:
        return calendar.monthrange(year, month)[1]

    def calculate_daily_rate(self, year: int, month: int, calculation_basis: str = "calendar_days") -> float:
        """
        calculation_basis: 'calendar_days' (e.g. 30/31 days) or 'standard_26' (26 working days)
        """
        if calculation_basis == "standard_26":
            return self.basic_salary / 26.0
        else:
            days_in_month = self.get_month_days(year, month)
            return self.basic_salary / float(days_in_month)

    def calculate_hours_worked(self, in_time_str: Optional[str], out_time_str: Optional[str], break_minutes: int = 30) -> float:
        """
        Calculates net working hours from HH:MM string in 24-hr or 12-hr format.
        """
        if not in_time_str or not out_time_str:
            return 0.0
        try:
            fmt = "%H:%M" if len(in_time_str.split(':')) == 2 else "%H:%M:%S"
            t1 = datetime.strptime(in_time_str, fmt)
            t2 = datetime.strptime(out_time_str, fmt)
            diff_mins = (t2 - t1).total_seconds() / 60.0
            net_mins = max(0.0, diff_mins - break_minutes)
            return round(net_mins / 60.0, 2)
        except Exception:
            return 0.0

    def evaluate_late_status(self, in_time_str: Optional[str]) -> Tuple[bool, bool]:
        """
        Returns (is_late, is_late_beyond_10am)
        Clause 4 & 6:
        - Normal start: 09:30 AM
        - Late if in_time > 09:30 AM
        - Severe Late if in_time > 10:00 AM (may be treated as half-day leave)
        """
        if not in_time_str:
            return (False, False)
        try:
            fmt = "%H:%M" if len(in_time_str.split(':')) == 2 else "%H:%M:%S"
            t = datetime.strptime(in_time_str, fmt).time()
            cutoff_start = datetime.strptime("09:30", "%H:%M").time()
            cutoff_10am = datetime.strptime("10:00", "%H:%M").time()

            is_late = t > cutoff_start
            is_severe_late = t > cutoff_10am
            return (is_late, is_severe_late)
        except Exception:
            return (False, False)

    def compute_month_payroll(
        self,
        year: int,
        month: int,
        daily_records: List[Dict],
        opening_leave_balance: float = 0.0,
        reimbursements: float = 0.0,
        tds_deduction: float = 0.0,
        other_deductions: float = 0.0,
        calculation_basis: str = "calendar_days"
    ) -> Dict:
        """
        daily_records: list of dicts for each day of the month:
        {
           'day': 1..31,
           'status': 'P' (Present), 'HD' (Half Day), 'WFH' (Work from Home),
                     'PL' (Paid Leave), 'UL' (Unpaid Leave/LOP), 'ML' (Medical Leave),
                     'EL' (Exam Leave), 'OFF' (Weekly Off), 'HOL' (Declared Holiday),
           'in_time': '09:30', # optional
           'out_time': '19:00', # optional
           'wfh_productive': True/False,
           'medical_cert_provided': True/False,
           'custom_note': ''
        }
        """
        days_in_month = self.get_month_days(year, month)
        daily_rate = self.calculate_daily_rate(year, month, calculation_basis)

        # Joining date pro-rata factor
        month_start_date = date(year, month, 1)
        month_end_date = date(year, month, days_in_month)

        if self.joining_date > month_end_date:
            return {
                'status': 'Not Joined',
                'net_salary': 0.0,
                'remarks': f"Employee joins on {self.joining_date.strftime('%d-%b-%Y')}"
            }

        eligible_calendar_days = days_in_month
        if self.joining_date > month_start_date:
            eligible_calendar_days = (month_end_date - self.joining_date).days + 1
            pro_rata_basic = (self.basic_salary / days_in_month) * eligible_calendar_days
        else:
            pro_rata_basic = self.basic_salary

        # Process attendance records
        total_present_days = 0.0
        total_half_days = 0.0
        total_wfh_days = 0.0
        total_weekly_offs = 0.0
        total_holidays = 0.0
        total_medical_leaves = 0.0
        total_exam_leaves = 0.0
        total_leaves_requested = 0.0
        unpaid_leaves_explicit = 0.0
        total_hours_worked = 0.0

        late_count_total = 0
        late_after_10am_count = 0
        medical_leaves_consecutive = 0
        missing_medical_cert_days = 0

        record_map = {r.get('day'): r for r in daily_records}

        for d in range(1, days_in_month + 1):
            curr_date = date(year, month, d)
            if curr_date < self.joining_date:
                continue

            rec = record_map.get(d, {})
            status = rec.get('status', 'P')
            in_time = rec.get('in_time', '09:30' if status in ['P', 'WFH'] else None)
            out_time = rec.get('out_time', '19:00' if status in ['P', 'WFH'] else None)
            wfh_productive = rec.get('wfh_productive', True)
            has_med_cert = rec.get('medical_cert_provided', False)

            # Working hours calculation
            if status in ['P', 'HD', 'WFH']:
                hrs = self.calculate_hours_worked(in_time, out_time)
                if hrs == 0 and status == 'P':
                    hrs = self.standard_daily_hours
                elif hrs == 0 and status == 'HD':
                    hrs = self.standard_daily_hours / 2.0
                total_hours_worked += hrs

            # Late analysis
            if in_time:
                is_late, is_late_10 = self.evaluate_late_status(in_time)
                if is_late:
                    late_count_total += 1
                if is_late_10:
                    late_after_10am_count += 1

            # Status processing
            if status == 'P':
                total_present_days += 1.0
                medical_leaves_consecutive = 0
            elif status == 'HD':
                total_half_days += 1.0
                medical_leaves_consecutive = 0
            elif status == 'WFH':
                if wfh_productive:
                    total_wfh_days += 1.0
                else:
                    total_leaves_requested += 1.0
                medical_leaves_consecutive = 0
            elif status == 'OFF':
                total_weekly_offs += 1.0
                medical_leaves_consecutive = 0
            elif status == 'HOL':
                total_holidays += 1.0
                medical_leaves_consecutive = 0
            elif status == 'PL':
                total_leaves_requested += 1.0
                medical_leaves_consecutive = 0
            elif status == 'UL':
                unpaid_leaves_explicit += 1.0
                medical_leaves_consecutive = 0
            elif status == 'ML':
                total_medical_leaves += 1.0
                total_leaves_requested += 1.0
                medical_leaves_consecutive += 1
                if medical_leaves_consecutive > 2 and not has_med_cert:
                    missing_medical_cert_days += 1
            elif status == 'EL':
                total_exam_leaves += 1.0
                total_leaves_requested += 1.0
                medical_leaves_consecutive = 0

        # Monthly holiday/leave credit
        monthly_credited_leave = 1.0
        available_leave_pool = opening_leave_balance + monthly_credited_leave

        if total_leaves_requested <= available_leave_pool:
            paid_leaves_granted = total_leaves_requested
            excess_unpaid_leaves = 0.0
            closing_leave_balance = available_leave_pool - total_leaves_requested
        else:
            paid_leaves_granted = available_leave_pool
            excess_unpaid_leaves = total_leaves_requested - available_leave_pool
            closing_leave_balance = 0.0

        total_unpaid_leave_days = excess_unpaid_leaves + unpaid_leaves_explicit

        # Late deductions
        late_half_day_deductions = 0.0
        if late_after_10am_count > 0:
            late_half_day_deductions += (late_after_10am_count * 0.5)

        if late_count_total > 2:
            repeated_delays = late_count_total - 2
            unpenalized_delays = max(0, repeated_delays - late_after_10am_count)
            late_half_day_deductions += (unpenalized_delays * 0.5)

        lop_deduction = total_unpaid_leave_days * daily_rate
        late_penalty_deduction = late_half_day_deductions * daily_rate

        gross_salary = pro_rata_basic + reimbursements
        total_deductions = (
            lop_deduction +
            late_penalty_deduction +
            tds_deduction +
            other_deductions
        )

        net_salary = max(0.0, gross_salary - total_deductions)

        total_service_days_target = (self.retainership_target_date - self.joining_date).days
        completed_service_days = max(0, (min(month_end_date, self.retainership_target_date) - self.joining_date).days)
        bonus_completion_pct = min(100.0, round((completed_service_days / total_service_days_target) * 100, 1))

        leave_encashment_value = round(closing_leave_balance * daily_rate, 2)

        return {
            'month_year': f"{calendar.month_name[month]} {year}",
            'year': year,
            'month': month,
            'days_in_month': days_in_month,
            'eligible_calendar_days': eligible_calendar_days,
            'daily_rate': round(daily_rate, 2),
            'pro_rata_basic': round(pro_rata_basic, 2),
            'total_present_days': total_present_days,
            'total_half_days': total_half_days,
            'total_wfh_days': total_wfh_days,
            'total_weekly_offs': total_weekly_offs,
            'total_holidays': total_holidays,
            'total_medical_leaves': total_medical_leaves,
            'total_exam_leaves': total_exam_leaves,
            'total_hours_worked': round(total_hours_worked, 1),
            'late_count_total': late_count_total,
            'late_after_10am_count': late_after_10am_count,
            'missing_medical_cert_days': missing_medical_cert_days,
            'opening_leave_balance': opening_leave_balance,
            'monthly_credited_leave': monthly_credited_leave,
            'total_leaves_requested': total_leaves_requested,
            'paid_leaves_granted': paid_leaves_granted,
            'unpaid_leaves_explicit': unpaid_leaves_explicit,
            'excess_unpaid_leaves': excess_unpaid_leaves,
            'total_unpaid_leave_days': total_unpaid_leave_days,
            'closing_leave_balance': round(closing_leave_balance, 2),
            'leave_encashment_value': leave_encashment_value,
            'lop_deduction': round(lop_deduction, 2),
            'late_penalty_deduction': round(late_penalty_deduction, 2),
            'tds_deduction': round(tds_deduction, 2),
            'other_deductions': round(other_deductions, 2),
            'reimbursements': round(reimbursements, 2),
            'total_deductions': round(total_deductions, 2),
            'gross_salary': round(gross_salary, 2),
            'net_salary': round(net_salary, 2),
            'retainership_bonus_target': self.retainership_bonus,
            'bonus_completion_pct': bonus_completion_pct,
            'days_to_retainership_bonus': max(0, (self.retainership_target_date - month_end_date).days),
        }

if __name__ == "__main__":
    calc = AttendanceSalaryCalculator()
    print("Testing April 2026 (Joined 13th April 2026):")
    sample_records_apr = []
    for d in range(13, 31):
        sample_records_apr.append({
            'day': d,
            'status': 'OFF' if d in [19, 26] else 'P',
            'in_time': '09:30',
            'out_time': '19:00'
        })
    res_apr = calc.compute_month_payroll(2026, 4, sample_records_apr, opening_leave_balance=0)
    print(f"Pro-rata Basic: ₹{res_apr['pro_rata_basic']}")
    print(f"Net Salary: ₹{res_apr['net_salary']}")
    print(f"Closing Leave Balance: {res_apr['closing_leave_balance']}")
