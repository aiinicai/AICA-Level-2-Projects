from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from billing.models import Invoice, TimeEntry
from billing.services import cancel_invoice, compute_totals, create_invoice, items_from_time, record_payment
from tests.helpers import make_world

D = Decimal


def line(desc="Work", qty="1", rate="1000", tax="18"):
    return {"description": desc, "quantity": D(qty), "rate": D(rate), "tax_rate": D(tax)}


class TotalsTests(TestCase):
    def test_gst_totals_round_half_up_per_line(self):
        _, sub, tax, total = compute_totals([line(rate="4000"), line(qty="2.5", rate="1200.50")])
        self.assertEqual((sub, tax, total), (D("7001.25"), D("1260.23"), D("8261.48")))  # 720.00 + 540.225→540.23

    def test_zero_rated_line(self):
        _, sub, tax, total = compute_totals([line(rate="500", tax="0")])
        self.assertEqual((sub, tax, total), (D("500.00"), D("0.00"), D("500.00")))


class InvoiceTests(TestCase):
    def setUp(self):
        self.w = make_world("bill")

    def make(self, issue=None, **kw):
        return create_invoice(firm=self.w.firm, client=self.w.client, items=[line(rate="1000")], issue_date=issue, **kw)

    def test_numbers_are_sequential_per_firm_and_financial_year(self):
        a, b = self.make(date(2026, 11, 2)), self.make(date(2027, 3, 31))
        c = self.make(date(2027, 4, 1))  # new Indian FY starts 1 April
        self.assertEqual([a.number, b.number, c.number], ["INV/2026-27/0001", "INV/2026-27/0002", "INV/2027-28/0001"])
        other = make_world("bill2")
        o = create_invoice(firm=other.firm, client=other.client, items=[line()], issue_date=date(2026, 11, 2))
        self.assertEqual(o.number, "INV/2026-27/0001")  # each firm has its own series

    def test_due_date_defaults_to_15_days(self):
        inv = self.make(date(2026, 11, 2))
        self.assertEqual(inv.due_date, date(2026, 11, 17))
        self.assertEqual((inv.subtotal, inv.tax_amount, inv.total), (D("1000.00"), D("180.00"), D("1180.00")))

    def test_empty_invoice_rejected(self):
        with self.assertRaises(ValidationError):
            create_invoice(firm=self.w.firm, client=self.w.client, items=[])

    def test_part_payment_then_full_settlement(self):
        inv = self.make()
        record_payment(inv, amount=D("500"), method="UPI")
        inv.refresh_from_db()
        self.assertEqual(inv.status, "PENDING")
        self.assertEqual(Invoice.objects.prefetch_related("payments").get(pk=inv.pk).balance, D("680.00"))
        record_payment(inv, amount=D("680"))
        inv.refresh_from_db()
        self.assertEqual(inv.status, "PAID")

    def test_overpayment_zero_and_cancelled_are_rejected(self):
        inv = self.make()
        with self.assertRaises(ValidationError):
            record_payment(inv, amount=D("1180.01"))
        with self.assertRaises(ValidationError):
            record_payment(inv, amount=D("0"))
        cancel_invoice(inv)
        with self.assertRaises(ValidationError):
            record_payment(inv, amount=D("10"))

    def test_cannot_cancel_after_payment(self):
        inv = self.make()
        record_payment(inv, amount=D("100"))
        with self.assertRaises(ValidationError):
            cancel_invoice(inv)

    def test_overdue_flag(self):
        past = timezone.localdate() - timedelta(days=30)
        inv = self.make(issue=past, due_date=past + timedelta(days=5))
        self.assertTrue(inv.is_overdue)
        self.assertEqual(inv.status_label, "Overdue")
        record_payment(inv, amount=inv.total)
        inv.refresh_from_db()
        self.assertFalse(inv.is_overdue)


class BillingTimeTests(TestCase):
    def setUp(self):
        self.w = make_world("time")

    def entry(self, user, minutes, rate=None, billable=True):
        return TimeEntry.objects.create(firm=self.w.firm, user=user, client=self.w.client, work_date=timezone.localdate(),
                                        minutes=minutes, hourly_rate=rate, billable=billable, description="Reconciliation")

    def test_rate_precedence_entry_then_user_then_fallback(self):
        e1 = self.entry(self.w.member, 150, rate=D("2000"))   # entry rate wins
        e2 = self.entry(self.w.member, 60)                    # member's rate (1000)
        e3 = self.entry(self.w.admin, 30)                     # admin has no rate → fallback
        items = items_from_time(TimeEntry.objects.filter(pk__in=[e1.pk, e2.pk, e3.pk]).order_by("pk"), default_rate=D("1500"))
        self.assertEqual([(i["quantity"], i["rate"]) for i in items], [(D("2.50"), D("2000.00")), (D("1.00"), D("1000.00")), (D("0.50"), D("1500"))])

    def test_billing_time_links_entries_and_cancelling_releases_them(self):
        e = self.entry(self.w.member, 120)
        inv = create_invoice(firm=self.w.firm, client=self.w.client, items=items_from_time(TimeEntry.objects.filter(pk=e.pk)), time_entries=[e])
        e.refresh_from_db()
        self.assertEqual(e.invoice_id, inv.pk)
        self.assertEqual(inv.subtotal, D("2000.00"))
        cancel_invoice(inv)
        e.refresh_from_db()
        self.assertIsNone(e.invoice_id)  # available for re-billing
