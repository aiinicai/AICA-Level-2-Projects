"""
Unit Test Suite for Attendance cum Salary Calculator
Verifying all clauses of M/s J Megha & Co. Offer Letter
"""

import unittest
from datetime import date
from calculator import AttendanceSalaryCalculator

class TestAttendanceSalaryCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = AttendanceSalaryCalculator(
            basic_salary=20000.0,
            joining_date=date(2026, 4, 13),
            retainership_bonus=60000.0,
            retainership_target_date=date(2027, 12, 31)
        )

    def test_pro_rata_joining_month(self):
        """April 2026: Employee joined on 13th April. Eligible days = 18 (13th to 30th). Pro-rata Basic = 18/30 * 20000 = 12000"""
        records = [{'day': d, 'status': 'P', 'in_time': '09:30', 'out_time': '19:00'} for d in range(13, 31)]
        res = self.calc.compute_month_payroll(2026, 4, records, opening_leave_balance=0.0)
        self.assertEqual(res['pro_rata_basic'], 12000.0)
        self.assertEqual(res['net_salary'], 12000.0)
        self.assertEqual(res['closing_leave_balance'], 1.0) # 1 leave earned, 0 taken

    def test_leave_accumulation_and_overflow(self):
        """
        Month 1 (May): 0 leaves taken -> closing balance = 0 + 1 = 1.0
        Month 2 (June): 2 leaves taken -> pool = 1.0 + 1.0 = 2.0 -> 0 LOP, closing = 0.0
        Month 3 (July): 2 leaves taken -> pool = 0.0 + 1.0 = 1.0 -> 1 paid, 1 LOP deduction
        """
        # May 2026
        rec_may = [{'day': d, 'status': 'P', 'in_time': '09:30', 'out_time': '19:00'} for d in range(1, 32)]
        res_may = self.calc.compute_month_payroll(2026, 5, rec_may, opening_leave_balance=1.0) # 1.0 from April
        self.assertEqual(res_may['closing_leave_balance'], 2.0)
        self.assertEqual(res_may['lop_deduction'], 0.0)

        # June 2026 (2 leaves taken)
        rec_june = [{'day': d, 'status': 'PL' if d in [5, 6] else 'P', 'in_time': '09:30', 'out_time': '19:00'} for d in range(1, 31)]
        res_june = self.calc.compute_month_payroll(2026, 6, rec_june, opening_leave_balance=2.0) # pool = 2 + 1 = 3
        self.assertEqual(res_june['closing_leave_balance'], 1.0)
        self.assertEqual(res_june['lop_deduction'], 0.0)

        # July 2026 (3 leaves taken, pool = 1 + 1 = 2 -> 1 excess LOP)
        rec_july = [{'day': d, 'status': 'PL' if d in [1, 2, 3] else 'P', 'in_time': '09:30', 'out_time': '19:00'} for d in range(1, 32)]
        res_july = self.calc.compute_month_payroll(2026, 7, rec_july, opening_leave_balance=1.0)
        self.assertEqual(res_july['closing_leave_balance'], 0.0)
        daily_rate_july = 20000.0 / 31.0
        self.assertAlmostEqual(res_july['lop_deduction'], round(1.0 * daily_rate_july, 2))

    def test_late_arrival_penalties(self):
        """
        Clause 6:
        - Late after 10:00 AM treated as half-day deduction.
        - Delays > 2 times attract deduction.
        Scenario: 1 day after 10:00 AM (10:15) + 2 days after 9:30 AM (9:45) = 3 late days total.
        1 day > 10 AM (0.5 day deduction). Total late = 3 (> 2). Remaining repeated = 1 - 1 = 0.
        Total late deduction = 0.5 day.
        """
        records = []
        for d in range(1, 31):
            in_t = '09:30'
            if d == 1: in_t = '10:15' # severe late (>10 AM)
            elif d in [2, 3]: in_t = '09:40' # mild late (9:30-10:00)
            records.append({'day': d, 'status': 'P', 'in_time': in_t, 'out_time': '19:00'})

        res = self.calc.compute_month_payroll(2026, 6, records, opening_leave_balance=0.0)
        daily_rate_june = 20000.0 / 30.0
        expected_deduction = round(0.5 * daily_rate_june, 2)
        self.assertEqual(res['late_after_10am_count'], 1)
        self.assertEqual(res['late_count_total'], 3)
        self.assertEqual(res['late_penalty_deduction'], expected_deduction)

    def test_reimbursements_and_tds(self):
        """Reimbursements add to gross, TDS deducts from net"""
        records = [{'day': d, 'status': 'P', 'in_time': '09:30', 'out_time': '19:00'} for d in range(1, 31)]
        res = self.calc.compute_month_payroll(
            2026, 6, records,
            opening_leave_balance=0.0,
            reimbursements=1500.0,
            tds_deduction=500.0
        )
        self.assertEqual(res['gross_salary'], 21500.0)
        self.assertEqual(res['net_salary'], 21000.0)

if __name__ == '__main__':
    unittest.main()
