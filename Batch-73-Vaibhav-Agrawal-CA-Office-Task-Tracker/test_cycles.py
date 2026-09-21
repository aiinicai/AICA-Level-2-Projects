"""
test_cycles.py - Checks that the due-date engine (cycles.py) gives correct answers.

Run with:   python -m unittest -v
"""

import unittest
from datetime import date

import cycles


class MonthlyTasks(unittest.TestCase):
    def test_due_day(self):
        task = {"frequency": "Monthly", "dueDay": 20}
        c = cycles.cycle(task, date(2026, 9, 21))
        self.assertEqual((c["key"], c["deadline"]), ("2026-09", date(2026, 9, 20)))
        self.assertEqual(cycles.info(task, date(2026, 9, 21))["state"], "overdue")
        self.assertEqual(cycles.info(task, date(2026, 9, 18))["state"], "soon")
        self.assertEqual(cycles.info(task, date(2026, 9, 5))["state"], "open")

    def test_day_31_in_a_short_month(self):
        c = cycles.cycle({"frequency": "Monthly", "dueDay": 31}, date(2027, 2, 10))
        self.assertEqual(c["deadline"], date(2027, 2, 28))

    def test_window_crossing_month_end(self):
        task = {"frequency": "Monthly", "dueFrom": 28, "dueDay": 5}
        early = cycles.cycle(task, date(2026, 10, 3))       # still September's cycle
        self.assertEqual((early["key"], early["deadline"]), ("2026-09", date(2026, 10, 5)))
        late = cycles.cycle(task, date(2026, 10, 10))       # October's cycle, not open yet
        self.assertEqual((late["key"], late["start"]), ("2026-10", date(2026, 10, 28)))
        self.assertEqual(cycles.info(task, date(2026, 10, 10))["state"], "later")

    def test_second_saturday(self):
        c = cycles.cycle({"frequency": "Monthly", "dueRule": "2nd-sat"}, date(2026, 9, 1))
        self.assertEqual(c["deadline"], date(2026, 9, 12))

    def test_done_resets_next_month(self):
        task = {"frequency": "Monthly", "dueDay": 11, "doneFor": "2026-09"}
        self.assertTrue(cycles.info(task, date(2026, 9, 30))["done"])
        self.assertFalse(cycles.info(task, date(2026, 10, 1))["done"])


class QuarterlyAndAnnualTasks(unittest.TestCase):
    def test_tds_return_due_in_month_after_quarter(self):
        task = {"frequency": "Quarterly", "dueDay": 31, "dueQOffset": 1}
        c = cycles.cycle(task, date(2026, 7, 15))           # Apr-Jun return, due 31 July
        self.assertEqual((c["key"], c["label"], c["deadline"]),
                         ("Q2026-0", "Apr–Jun 2026", date(2026, 7, 31)))
        c = cycles.cycle(task, date(2026, 8, 1))            # now the Jul-Sep quarter
        self.assertEqual((c["key"], c["deadline"]), ("Q2026-1", date(2026, 10, 31)))

    def test_jan_mar_quarter_belongs_to_same_financial_year(self):
        task = {"frequency": "Quarterly", "dueDay": 15, "dueQOffset": 0}
        c = cycles.cycle(task, date(2027, 2, 1))
        self.assertEqual((c["key"], c["label"], c["deadline"]),
                         ("Q2026-3", "Jan–Mar 2027", date(2027, 3, 15)))

    def test_advance_tax_in_last_month_of_quarter(self):
        task = {"frequency": "Quarterly", "dueDay": 15, "dueQOffset": 0}
        self.assertEqual(cycles.cycle(task, date(2026, 9, 1))["deadline"], date(2026, 9, 15))

    def test_annual_follows_financial_year(self):
        task = {"frequency": "Annual", "dueDate": "2026-09-30"}
        self.assertEqual(cycles.cycle(task, date(2027, 1, 10))["deadline"], date(2026, 9, 30))
        self.assertEqual(cycles.cycle(task, date(2027, 4, 1))["key"], "FY2027")
        january = {"frequency": "Annual", "dueDate": "2026-01-31"}
        self.assertEqual(cycles.cycle(january, date(2026, 6, 1))["deadline"], date(2027, 1, 31))

    def test_financial_year_label(self):
        self.assertEqual(cycles.fy_label(cycles.fy_start(date(2026, 3, 31))), "FY 2025-26")
        self.assertEqual(cycles.fy_label(cycles.fy_start(date(2026, 4, 1))), "FY 2026-27")


class OtherTasks(unittest.TestCase):
    def test_weekly(self):
        task = {"frequency": "Weekly", "dueWeekday": 5}                     # Friday
        c = cycles.cycle(task, date(2026, 9, 21))                           # a Monday
        self.assertEqual((c["key"], c["deadline"]), ("W2026-09-21", date(2026, 9, 25)))

    def test_daily_resets_every_day(self):
        task = {"frequency": "Daily", "doneFor": "2026-09-21"}
        self.assertTrue(cycles.info(task, date(2026, 9, 21))["done"])
        self.assertFalse(cycles.info(task, date(2026, 9, 22))["done"])

    def test_one_time(self):
        task = {"frequency": "One-time", "dueDate": "2026-09-23", "status": "open"}
        i = cycles.info(task, date(2026, 9, 21))
        self.assertEqual((i["state"], i["days"]), ("soon", 2))
        self.assertEqual(cycles.pill_text(task, i, date(2026, 9, 21)), "Due in 2d")
        task["status"] = "done"
        self.assertEqual(cycles.info(task, date(2026, 9, 30))["state"], "done")

    def test_when_free_does_not_hide_urgent_work(self):
        task = {"frequency": "One-time", "dueDate": "2026-10-30", "later": True}
        self.assertTrue(cycles.info(task, date(2026, 9, 21))["free"])
        self.assertFalse(cycles.info(task, date(2026, 10, 29))["free"])     # due soon

    def test_checked_today_lasts_one_day(self):
        task = {"frequency": "One-time", "checkedOn": "2026-09-21"}
        self.assertTrue(cycles.info(task, date(2026, 9, 21))["checked"])
        self.assertFalse(cycles.info(task, date(2026, 9, 22))["checked"])

    def test_texts(self):
        self.assertEqual([cycles.ordinal(n) for n in (1, 2, 3, 11, 12, 21, 23, 30)],
                         ["1st", "2nd", "3rd", "11th", "12th", "21st", "23rd", "30th"])
        self.assertEqual(cycles.due_text({"frequency": "Monthly", "dueFrom": 14, "dueDay": 18}), "14th–18th")
        self.assertEqual(cycles.due_text({"frequency": "Quarterly", "dueDay": 31, "dueQOffset": 1}), "31st after qtr")
        self.assertEqual(cycles.cycle_key_label("Q2026-1"), "Jul–Sep 2026")
        self.assertEqual(cycles.cycle_key_label("2026-09"), "Sep 2026")


if __name__ == "__main__":
    unittest.main()
