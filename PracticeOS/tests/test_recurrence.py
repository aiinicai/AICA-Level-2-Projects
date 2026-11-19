from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from tests.helpers import make_world
from workflow.models import RecurringRule, Task
from workflow.recurrence import add_period, first_due_date, generate_due_tasks, period_label


class DateMathTests(TestCase):
    def test_day_of_month_clamps_to_short_months(self):
        self.assertEqual(add_period(date(2027, 1, 31), "MONTHLY", 31), date(2027, 2, 28))
        self.assertEqual(add_period(date(2027, 2, 28), "MONTHLY", 31), date(2027, 3, 31))
        self.assertEqual(add_period(date(2028, 1, 31), "MONTHLY", 31), date(2028, 2, 29))  # leap year

    def test_year_rollover_and_other_frequencies(self):
        self.assertEqual(add_period(date(2026, 12, 20), "MONTHLY", 20), date(2027, 1, 20))
        self.assertEqual(add_period(date(2026, 12, 15), "QUARTERLY", 15), date(2027, 3, 15))
        self.assertEqual(add_period(date(2026, 7, 31), "ANNUAL", 31), date(2027, 7, 31))
        self.assertEqual(add_period(date(2026, 9, 30), "HALF_YEARLY", 30), date(2027, 3, 30))

    def test_first_due_date(self):
        today = date(2026, 11, 2)
        self.assertEqual(first_due_date("MONTHLY", 20, today=today), date(2026, 11, 20))
        self.assertEqual(first_due_date("MONTHLY", 1, today=today), date(2026, 12, 1))  # already passed this month
        self.assertEqual(first_due_date("ANNUAL", 31, 7, today=today), date(2027, 7, 31))
        self.assertEqual(first_due_date("ANNUAL", 31, 12, today=today), date(2026, 12, 31))
        self.assertEqual(first_due_date("QUARTERLY", 15, 6, today=today), date(2026, 12, 15))  # Jun/Sep/Dec/Mar

    def test_period_labels(self):
        self.assertEqual(period_label("MONTHLY", date(2026, 11, 20)), "Oct 2026")  # GSTR-3B due 20 Nov is for October
        self.assertEqual(period_label("MONTHLY", date(2027, 1, 11)), "Dec 2026")
        self.assertEqual(period_label("ANNUAL", date(2027, 7, 31)), "FY 2026-27")  # ITR due Jul 2027
        self.assertEqual(period_label("ANNUAL", date(2026, 12, 31)), "FY 2025-26")  # GSTR-9 due Dec 2026
        self.assertEqual(period_label("QUARTERLY", date(2026, 12, 15)), "Due Dec 2026")


class GenerationTests(TestCase):
    def setUp(self):
        self.w = make_world("rec")
        self.today = timezone.localdate()

    def rule(self, due, lead=7, **kw):
        return RecurringRule.objects.create(firm=self.w.firm, client=self.w.client, title="GSTR-3B", frequency="MONTHLY",
                                            day_of_month=due.day, next_due_date=due, lead_days=lead, assignee=self.w.member, **kw)

    def test_creates_task_inside_lead_window_and_is_idempotent(self):
        rule = self.rule(self.today + timedelta(days=3))
        first = generate_due_tasks(self.w.firm)
        self.assertEqual(first["tasks_created"], 1)
        task = Task.objects.get(recurring_rule=rule)
        self.assertEqual((task.client, task.assignee, task.created_by), (self.w.client, self.w.member, self.w.admin))
        rule.refresh_from_db()
        self.assertGreater(rule.next_due_date, self.today + timedelta(days=3))  # advanced to the next period
        self.assertEqual(generate_due_tasks(self.w.firm)["tasks_created"], 0)  # running again changes nothing
        self.assertEqual(Task.objects.filter(recurring_rule=rule).count(), 1)

    def test_not_created_before_lead_window_opens(self):
        self.rule(self.today + timedelta(days=30), lead=7)
        self.assertEqual(generate_due_tasks(self.w.firm)["tasks_created"], 0)

    def test_catches_up_on_missed_periods(self):
        self.rule(self.today - timedelta(days=65))
        self.assertGreaterEqual(generate_due_tasks(self.w.firm)["tasks_created"], 3)

    def test_paused_rules_are_skipped(self):
        self.rule(self.today + timedelta(days=1), is_active=False)
        self.assertEqual(generate_due_tasks(self.w.firm)["tasks_created"], 0)

    def test_only_the_requested_firm_is_processed(self):
        other = make_world("rec2")
        RecurringRule.objects.create(firm=other.firm, title="x", frequency="MONTHLY", day_of_month=1, next_due_date=self.today, lead_days=7)
        self.rule(self.today + timedelta(days=1))
        generate_due_tasks(self.w.firm)
        self.assertFalse(Task.objects.filter(firm=other.firm).exists())
        self.assertEqual(generate_due_tasks()["tasks_created"], 1)  # the scheduled all-firms run picks the other one up
