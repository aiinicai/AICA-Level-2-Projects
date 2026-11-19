"""Demo data:  python manage.py seed_demo
Workspace `demo` | admin@demo.com / Password@123 | staff: priya@demo.com / Password@123 | client portal: rao@client.demo / Password@123"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Firm, User
from billing.models import Invoice, Payment, TimeEntry
from billing.services import create_invoice, record_payment
from crm.models import Client, ClientService
from documents.models import Document
from workflow.models import RecurringRule, Task
from workflow.recurrence import first_due_date, generate_due_tasks

PASSWORD = "Password@123"


class Command(BaseCommand):
    help = "Create (or recreate) the demo workspace with sample clients, tasks, time and invoices."

    @transaction.atomic
    def handle(self, *args, **options):
        demo_firm = Firm.objects.filter(subdomain="demo").first()
        if demo_firm:
            Payment.objects.filter(firm=demo_firm).delete()
            Invoice.objects.filter(firm=demo_firm).delete()
            TimeEntry.objects.filter(firm=demo_firm).delete()
            Task.objects.filter(firm=demo_firm).delete()
            RecurringRule.objects.filter(firm=demo_firm).delete()
            Document.objects.filter(firm=demo_firm).delete()
            ClientService.objects.filter(firm=demo_firm).delete()
            Client.objects.filter(firm=demo_firm).delete()
            User.objects.filter(firm=demo_firm).delete()
            demo_firm.delete()
        today = timezone.localdate()
        day = lambda n: today + timedelta(days=n)

        firm = Firm.objects.create(
            name="Demo & Associates",
            type=Firm.Type.PARTNERSHIP,
            size=Firm.Size.SMALL,
            subdomain="demo",
            pan="AAAFD1234P",
            gstin="27AAAFD1234P1Z1",
            address="402, Trade Centre, Bandra-Kurla Complex\nBandra (East), Mumbai – 400051",
            phone="+91 22 2650 1234",
            email="billing@demo.example",
            bank_name="HDFC Bank",
            bank_account_name="Demo & Associates",
            bank_account_no="50200012345678",
            bank_ifsc="HDFC0000123",
            bank_branch="BKC Mumbai",
            upi_id="demoassociates@hdfcbank",
            signatory_name="CA Anil Demo",
            signatory_designation="Partner, Chartered Accountant",
        )
        admin = User.objects.create_user(firm, "admin@demo.com", "Anil Demo", PASSWORD, role=User.Role.ADMIN, hourly_rate=Decimal("2500"))
        priya = User.objects.create_user(firm, "priya@demo.com", "Priya Shah", PASSWORD, hourly_rate=Decimal("1200"))

        acme = Client.objects.create(firm=firm, name="Acme Traders Pvt Ltd", type="COMPANY", pan="AAACA1234F", gstin="27AAACA1234F1Z5", email="accounts@acme.example", phone="9820000001", contact_person="R. Mehta")
        rao = Client.objects.create(firm=firm, name="Dr. S. Rao", type="INDIVIDUAL", pan="BCDPR5678K", email="rao@example.com", phone="9820000002")
        sun = Client.objects.create(firm=firm, name="Sunrise Enterprises LLP", type="LLP", pan="AAJFS9876L", gstin="27AAJFS9876L1Z2", email="info@sunrise.example")
        User.objects.create_user(firm, "rao@client.demo", "Dr. S. Rao", PASSWORD, role=User.Role.CLIENT, client=rao)

        for client, name, fee, freq in [(acme, "GST Returns", 4000, "MONTHLY"), (acme, "Statutory & Tax Audit", 85000, "ANNUAL"),
                                        (rao, "Income Tax Return", 6000, "ANNUAL"), (sun, "Bookkeeping & GST", 7500, "MONTHLY")]:
            ClientService.objects.create(firm=firm, client=client, name=name, fee=fee, billing_frequency=freq)

        for client, title, freq, dom, month in [(acme, "GSTR-3B filing", "MONTHLY", 20, None), (acme, "GSTR-1 filing", "MONTHLY", 11, None),
                                                (sun, "GSTR-3B filing", "MONTHLY", 20, None), (rao, "ITR filing (non-audit)", "ANNUAL", 31, 7)]:
            RecurringRule.objects.create(firm=firm, client=client, title=title, frequency=freq, day_of_month=dom, assignee=priya,
                                         priority="HIGH", lead_days=21, next_due_date=first_due_date(freq, dom, month))
        self.stdout.write(f"Recurring engine: {generate_due_tasks(firm)}")

        for client, assignee, title, status, prio, due in [
            (acme, priya, "Prepare tax audit working papers", "IN_PROGRESS", "HIGH", day(12)),
            (rao, admin, "Review Form 26AS / AIS mismatch", "REVIEW", "MEDIUM", day(3)),
            (sun, priya, "Collect bank statements for Q2", "TODO", "MEDIUM", day(-2)),
            (acme, priya, "File TDS return (Q1)", "COMPLETED", "MEDIUM", day(-15))]:
            Task.objects.create(firm=firm, client=client, assignee=assignee, created_by=admin, title=title, status=status, priority=prio, due_date=due)

        Document.objects.create(firm=firm, client=acme, uploaded_by=admin, type="LINK", name="FY 2025-26 Books (Tally backup)", url="https://drive.google.com/", financial_year="2025-26", category="Accounts")
        Document.objects.create(firm=firm, client=rao, uploaded_by=admin, type="PHYSICAL", name="Original investment proofs", physical_location="Cabinet B / Shelf 3 / Box 12", financial_year="2025-26", category="ITR", shared_with_client=True)

        for user, client, minutes, text, off in [(priya, acme, 150, "GST reconciliation", -1), (priya, acme, 90, "Audit vouching", -2), (admin, rao, 45, "AIS review call", -3)]:
            TimeEntry.objects.create(firm=firm, user=user, client=client, minutes=minutes, description=text, work_date=day(off))

        inv = create_invoice(firm=firm, client=acme, issue_date=day(-5), due_date=day(10),
                             items=[{"description": "GST compliance – monthly retainer", "quantity": Decimal(1), "rate": Decimal(4000), "tax_rate": Decimal(18)}])
        paid = create_invoice(firm=firm, client=rao, issue_date=day(-20), due_date=day(-5),
                              items=[{"description": "ITR filing FY 2025-26", "quantity": Decimal(1), "rate": Decimal(6000), "tax_rate": Decimal(18)}])
        record_payment(paid, amount=paid.total, paid_on=today, method="UPI", reference="UTR123456")
        self.stdout.write(self.style.SUCCESS(f"Seeded workspace 'demo'. Login: admin@demo.com / {PASSWORD}  (pending invoice {inv.number})"))
