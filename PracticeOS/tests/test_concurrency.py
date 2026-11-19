import threading
from datetime import date
from decimal import Decimal
from unittest import skipUnless

from django.db import connection, connections
from django.test import TransactionTestCase

from billing.models import Invoice
from billing.services import create_invoice
from tests.helpers import make_world


@skipUnless(connection.vendor == "postgresql", "needs real row locking (PostgreSQL)")
class InvoiceNumberingUnderLoadTests(TransactionTestCase):
    def test_parallel_requests_get_unique_gap_free_numbers(self):
        w = make_world("load")
        errors, start = [], threading.Barrier(8)

        def worker():
            try:
                start.wait()  # release all threads at once, with no counter row existing yet
                create_invoice(firm=w.firm, client=w.client, issue_date=date(2026, 11, 2),
                               items=[{"description": "x", "quantity": Decimal(1), "rate": Decimal(100), "tax_rate": Decimal(18)}])
            except Exception as e:  # noqa: BLE001
                errors.append(repr(e))
            finally:
                connections.close_all()

        threads = [threading.Thread(target=worker) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]

        self.assertEqual(errors, [])
        numbers = sorted(Invoice.objects.filter(firm=w.firm).values_list("number", flat=True))
        self.assertEqual(numbers, [f"INV/2026-27/{i:04d}" for i in range(1, 9)])
