import json
import os
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client as WebClient
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Firm, User
from billing.models import Invoice, TimeEntry
from crm.models import Client
from documents.models import Document
from tests.helpers import PW, make_world
from workflow.models import RecurringRule, Task


class SignupAndLoginTests(TestCase):
    def setUp(self):
        cache.clear()

    def signup(self, **over):
        data = {"name": "Anil Sharma", "email": "Anil@Sharma.test", "password": PW, "firm_name": "Sharma & Co", "firm_type": "PARTNERSHIP",
                "firm_size": "SMALL", "subdomain": "sharma"}
        return WebClient(), {**data, **over}

    def test_signup_creates_firm_and_admin_and_logs_in(self):
        web, data = self.signup()
        r = web.post("/signup/", data)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "sharma.practiceos.app")
        firm = Firm.objects.get(subdomain="sharma")
        user = User.objects.get(firm=firm)
        self.assertEqual((user.role, user.email), ("ADMIN", "anil@sharma.test"))
        self.assertEqual(web.get("/dashboard/").status_code, 200)

    def test_signup_validation(self):
        make_world("taken")
        for field, value in [("subdomain", "taken"), ("subdomain", "admin"), ("subdomain", "x"), ("subdomain", "Has Space"), ("password", "short"), ("password", "password"), ("email", "nope")]:
            web, data = self.signup(**{field: value})
            r = web.post("/signup/", data)
            self.assertEqual(r.status_code, 200, (field, value))
            self.assertTrue(r.context["form"].errors.get(field), (field, value))
        self.assertFalse(Firm.objects.filter(subdomain="sharma").exists())

    def test_subdomain_check(self):
        make_world("taken")
        web = WebClient()
        self.assertEqual(web.get("/signup/subdomain-check/?name=Sharma%20and%20Co").json(), {"subdomain": "sharma-and-co", "available": True})
        self.assertFalse(web.get("/signup/subdomain-check/?name=Taken").json()["available"])
        self.assertFalse(web.get("/signup/subdomain-check/?name=admin").json()["available"])

    def test_login_errors_are_generic_and_repeated_failures_lock_out(self):
        w = make_world("lock")
        web = WebClient()
        for creds in [("nowhere", w.admin.email, PW), ("lock", "ghost@lock.test", PW), ("lock", w.admin.email, "wrong-pass")]:
            r = web.post("/login/", dict(zip(("workspace", "email", "password"), creds)))
            self.assertContains(r, "Invalid workspace, email or password.")
        for _ in range(8):
            web.post("/login/", {"workspace": "lock", "email": w.admin.email, "password": "bad"})
        r = web.post("/login/", {"workspace": "lock", "email": w.admin.email, "password": PW})  # even the right password is blocked now
        self.assertContains(r, "Too many failed attempts")

    def test_login_logout_roundtrip(self):
        w = make_world("round")
        web = WebClient()
        self.assertEqual(web.post("/login/", {"workspace": "ROUND", "email": w.admin.email.upper(), "password": PW}).status_code, 302)
        self.assertEqual(web.get("/dashboard/").status_code, 200)
        web.post("/logout/")
        self.assertEqual(web.get("/dashboard/").status_code, 302)


class KanbanAndTaskTests(TestCase):
    def setUp(self):
        self.w = make_world("kan")
        self.web = WebClient()
        self.web.force_login(self.w.member)
        self.task = Task.objects.create(firm=self.w.firm, title="File GSTR-3B", created_by=self.w.admin)

    def move(self, status):
        return self.web.post(f"/tasks/{self.task.pk}/status/", json.dumps({"status": status}), content_type="application/json")

    def test_drag_and_drop_updates_status_and_completion_time(self):
        self.assertEqual(self.move("REVIEW").status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual((self.task.status, self.task.completed_at), ("REVIEW", None))
        self.move("COMPLETED")
        self.task.refresh_from_db()
        self.assertIsNotNone(self.task.completed_at)
        self.move("TODO")
        self.task.refresh_from_db()
        self.assertIsNone(self.task.completed_at)  # reopening clears it

    def test_bad_input_is_rejected(self):
        self.assertEqual(self.move("DONE").status_code, 400)
        self.assertEqual(self.web.post(f"/tasks/{self.task.pk}/status/", "not json", content_type="application/json").status_code, 400)
        self.assertEqual(self.web.get(f"/tasks/{self.task.pk}/status/").status_code, 405)

    def test_board_groups_tasks_and_flags_overdue(self):
        Task.objects.create(firm=self.w.firm, title="Late", created_by=self.w.admin, due_date=timezone.localdate() - timedelta(days=2))
        r = self.web.get("/tasks/")
        cols = {value: items for value, _, items in r.context["columns"]}
        self.assertEqual({t.title for t in cols["TODO"]}, {"File GSTR-3B", "Late"})
        self.assertContains(r, "Overdue")

    def test_create_edit_delete_task_via_forms(self):
        r = self.web.post("/tasks/new/", {"title": "New one", "client": self.w.client.pk, "assignee": self.w.member.pk, "status": "TODO", "priority": "HIGH", "due_date": "2026-12-01"})
        self.assertEqual(r.status_code, 302)
        t = Task.objects.get(title="New one")
        self.assertEqual((t.firm, t.created_by, t.assignee), (self.w.firm, self.w.member, self.w.member))
        self.web.post(f"/tasks/{t.pk}/edit/", {"title": "Renamed", "status": "IN_PROGRESS", "priority": "LOW"})
        t.refresh_from_db()
        self.assertEqual((t.title, t.status), ("Renamed", "IN_PROGRESS"))
        self.web.post(f"/tasks/{t.pk}/delete/")
        self.assertFalse(Task.objects.filter(pk=t.pk).exists())

    def test_creating_a_recurring_rule_releases_tasks_immediately(self):
        due = timezone.localdate() + timedelta(days=2)
        r = self.web.post("/tasks/recurring/new/", {"title": "GSTR-3B", "client": self.w.client.pk, "priority": "HIGH", "frequency": "MONTHLY", "day_of_month": due.day, "lead_days": 7})
        self.assertEqual(r.status_code, 302)
        rule = RecurringRule.objects.get(firm=self.w.firm)
        self.assertTrue(Task.objects.filter(recurring_rule=rule).exists())


class ClientTests(TestCase):
    def setUp(self):
        self.w = make_world("crm")
        self.web = WebClient()
        self.web.force_login(self.w.admin)

    def test_pan_validation_normalisation_and_uniqueness(self):
        bad = self.web.post("/clients/new/", {"name": "Bad PAN", "type": "INDIVIDUAL", "pan": "12345"})
        self.assertTrue(bad.context["form"].errors.get("pan"))
        ok = self.web.post("/clients/new/", {"name": "Acme", "type": "COMPANY", "pan": "aaaca1234f", "gstin": "", "phone": ""})
        self.assertEqual(ok.status_code, 302)
        acme = Client.objects.get(name="Acme")
        self.assertEqual((acme.pan, acme.gstin), ("AAACA1234F", None))
        dup = self.web.post("/clients/new/", {"name": "Acme 2", "type": "COMPANY", "pan": "AAACA1234F"})
        self.assertIn("already have a client", str(dup.context["form"].errors["pan"]))
        # the same PAN is fine in a different firm
        other = make_world("crm2")
        web2 = WebClient()
        web2.force_login(other.admin)
        self.assertEqual(web2.post("/clients/new/", {"name": "Acme", "type": "COMPANY", "pan": "AAACA1234F"}).status_code, 302)

    def test_clearing_optional_fields_on_edit(self):
        c = Client.objects.create(firm=self.w.firm, name="Edit me", pan="BCDPR5678K", phone="999")
        self.web.post(f"/clients/{c.pk}/edit/", {"name": "Edit me", "type": "INDIVIDUAL", "pan": "", "phone": ""})
        c.refresh_from_db()
        self.assertEqual((c.pan, c.phone), (None, ""))

    def test_archive_restore_and_search(self):
        c = Client.objects.create(firm=self.w.firm, name="Zeta Traders", pan="ZZZZZ9999Z")
        listed = lambda url: [x.name for x in self.web.get(url).context["clients"]]  # the list itself, not flash messages
        self.assertEqual(listed("/clients/?q=zzzzz"), ["Zeta Traders"])
        self.assertEqual(listed("/clients/?q=nothing-matches"), [])
        self.web.post(f"/clients/{c.pk}/archive/")
        self.assertNotIn("Zeta Traders", listed("/clients/"))
        self.assertEqual(listed("/clients/?archived=1"), ["Zeta Traders"])
        self.web.post(f"/clients/{c.pk}/restore/")
        self.assertIn("Zeta Traders", listed("/clients/"))

    def test_service_lifecycle(self):
        self.web.post(f"/clients/{self.w.client.pk}/services/new/", {"name": "GST Returns", "fee": "4000", "billing_frequency": "MONTHLY", "is_active": "on"})
        s = self.w.client.services.get()
        self.assertEqual((s.firm, s.fee), (self.w.firm, Decimal("4000")))
        self.assertContains(self.web.get(f"/clients/{self.w.client.pk}/"), "GST Returns")
        self.web.post(f"/clients/{self.w.client.pk}/services/{s.pk}/delete/")
        self.assertFalse(self.w.client.services.exists())


@override_settings(MAX_UPLOAD_BYTES=1024)
class DocumentTests(TestCase):
    def setUp(self):
        self.w = make_world("docs")
        self.other_client = Client.objects.create(firm=self.w.firm, name="Someone else")
        self.other_portal = User.objects.create_user(self.w.firm, "other@docs.test", "Other", PW, role="CLIENT", client=self.other_client)
        self.admin = WebClient()
        self.admin.force_login(self.w.admin)

    def upload(self, name="FY26-ITR.pdf", content=b"%PDF-1.4 test", **over):
        data = {"type": "UPLOAD", "client": self.w.client.pk, "file": SimpleUploadedFile(name, content, content_type="application/pdf"), **over}
        return self.admin.post("/documents/new/", data)

    def test_upload_store_privately_and_download(self):
        self.assertEqual(self.upload(financial_year="2025-26", category="ITR").status_code, 302)
        doc = Document.objects.get()
        self.assertEqual((doc.name, doc.size_bytes, doc.firm), ("FY26-ITR.pdf", 13, self.w.firm))
        self.assertTrue(doc.file.name.startswith(f"{self.w.firm.pk}/") and "FY26" not in doc.file.name)  # random name, per-tenant folder
        r = self.admin.get(f"/documents/{doc.pk}/download/")
        self.assertEqual((r.status_code, b"".join(r.streaming_content)), (200, b"%PDF-1.4 test"))
        self.assertIn("attachment", r["Content-Disposition"])
        member = WebClient()
        member.force_login(self.w.member)
        self.assertEqual(member.get(f"/documents/{doc.pk}/download/").status_code, 200)

    def test_client_portal_access_requires_sharing_and_ownership(self):
        self.upload()
        doc = Document.objects.get()
        mine, other = WebClient(), WebClient()
        mine.force_login(self.w.portal)
        other.force_login(self.other_portal)
        self.assertEqual(mine.get(f"/documents/{doc.pk}/download/").status_code, 404)  # not shared yet
        self.admin.post(f"/documents/{doc.pk}/share/")
        self.assertEqual(mine.get(f"/documents/{doc.pk}/download/").status_code, 200)
        self.assertEqual(other.get(f"/documents/{doc.pk}/download/").status_code, 404)  # shared, but belongs to another client
        self.assertContains(mine.get("/portal/"), "FY26-ITR.pdf")
        self.assertNotContains(other.get("/portal/"), "FY26-ITR.pdf")

    def test_upload_restrictions(self):
        bad_ext = self.upload(name="run.exe")
        self.assertTrue(bad_ext.context["form"].errors.get("file"))
        too_big = self.upload(content=b"x" * 2048)
        self.assertIn("larger than 20 MB", str(too_big.context["form"].errors["file"]))
        self.assertEqual(Document.objects.count(), 0)

    def test_link_and_physical_records_need_their_details(self):
        self.assertTrue(self.admin.post("/documents/new/", {"type": "LINK", "client": self.w.client.pk, "name": "Books"}).context["form"].errors.get("url"))
        self.assertTrue(self.admin.post("/documents/new/", {"type": "PHYSICAL", "client": self.w.client.pk, "name": "Deed"}).context["form"].errors.get("physical_location"))
        self.admin.post("/documents/new/", {"type": "LINK", "client": self.w.client.pk, "name": "Books", "url": "https://drive.example.com/x"})
        self.admin.post("/documents/new/", {"type": "PHYSICAL", "client": self.w.client.pk, "name": "Deed", "physical_location": "Cabinet B / Shelf 3 / Box 12"})
        self.assertEqual(sorted(Document.objects.values_list("type", flat=True)), ["LINK", "PHYSICAL"])
        self.assertContains(self.admin.get("/documents/"), "Cabinet B / Shelf 3 / Box 12")

    def test_delete_removes_the_stored_file(self):
        self.upload()
        doc = Document.objects.get()
        path = doc.file.path
        self.assertTrue(os.path.exists(path))
        self.admin.post(f"/documents/{doc.pk}/delete/")
        self.assertFalse(os.path.exists(path))


class BillingWebTests(TestCase):
    def setUp(self):
        self.w = make_world("web")
        self.web = WebClient()
        self.web.force_login(self.w.admin)

    def test_create_invoice_from_form_computes_on_the_server(self):
        r = self.web.post("/invoices/new/", {"client": self.w.client.pk, "issue_date": "2026-11-02", "due_date": "", "notes": "Thanks",
                                             "items-TOTAL_FORMS": 3, "items-INITIAL_FORMS": 0, "items-MIN_NUM_FORMS": 1, "items-MAX_NUM_FORMS": 1000,
                                             "items-0-description": "GSTR-3B filing", "items-0-quantity": "1", "items-0-rate": "4000", "items-0-tax_rate": "18",
                                             "items-1-description": "Advisory", "items-1-quantity": "2.5", "items-1-rate": "1200.50", "items-1-tax_rate": "18",
                                             "items-2-description": "", "items-2-quantity": "1", "items-2-rate": "", "items-2-tax_rate": "18"})
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["formset"].errors)
        inv = Invoice.objects.get()
        self.assertEqual((inv.number, inv.total, inv.items.count()), ("INV/2026-27/0001", Decimal("8261.48"), 2))  # blank third row ignored
        self.assertEqual(inv.due_date.isoformat(), "2026-11-17")

    def test_invoice_needs_at_least_one_valid_line(self):
        r = self.web.post("/invoices/new/", {"client": self.w.client.pk, "issue_date": "2026-11-02", "items-TOTAL_FORMS": 1, "items-INITIAL_FORMS": 0,
                                             "items-MIN_NUM_FORMS": 1, "items-MAX_NUM_FORMS": 1000, "items-0-description": "", "items-0-quantity": "1", "items-0-rate": "", "items-0-tax_rate": "18"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_payment_flow_and_overpayment_error(self):
        from billing.services import create_invoice
        inv = create_invoice(firm=self.w.firm, client=self.w.client, items=[{"description": "x", "quantity": 1, "rate": 1000, "tax_rate": 18}])
        bad = self.web.post(f"/invoices/{inv.pk}/pay/", {"amount": "2000", "paid_on": "2026-11-02", "method": "UPI"})
        self.assertTrue(bad.context["form"].errors.get("amount"))
        self.web.post(f"/invoices/{inv.pk}/pay/", {"amount": "180", "paid_on": "2026-11-02", "method": "UPI", "reference": "UTR1"})
        self.web.post(f"/invoices/{inv.pk}/pay/", {"amount": "1000", "paid_on": "2026-11-02", "method": "NEFT / RTGS"})
        inv.refresh_from_db()
        self.assertEqual(inv.status, "PAID")
        self.assertContains(self.web.get(f"/invoices/{inv.pk}/"), "UTR1")
        self.assertEqual(self.web.get(f"/invoices/{inv.pk}/pay/").status_code, 302)  # nothing left to pay

    def test_bill_logged_time_end_to_end(self):
        e = TimeEntry.objects.create(firm=self.w.firm, user=self.w.member, client=self.w.client, work_date=timezone.localdate(), minutes=90, description="Recon")
        page = self.web.get(f"/invoices/from-time/?client={self.w.client.pk}")
        self.assertContains(page, "Recon")
        r = self.web.post(f"/invoices/from-time/?client={self.w.client.pk}", {"entries": [e.pk], "default_rate": "500", "tax_rate": "18", "due_date": ""})
        self.assertEqual(r.status_code, 302)
        inv = Invoice.objects.get()
        self.assertEqual(inv.subtotal, Decimal("1500.00"))  # 1.5 h × member's ₹1000/h
        e.refresh_from_db()
        self.assertEqual(e.invoice_id, inv.pk)
        self.assertEqual(self.web.get(f"/time/{e.pk}/edit/", follow=True).redirect_chain[0][0], "/time/")  # invoiced time is locked
        self.assertNotContains(self.web.get(f"/invoices/from-time/?client={self.w.client.pk}"), "Recon")

    def test_time_entry_validation(self):
        base = {"client": self.w.client.pk, "work_date": timezone.localdate().isoformat(), "hours": 1, "mins": 30, "billable": "on"}
        self.assertEqual(self.web.post("/time/new/", base).status_code, 302)
        self.assertEqual(TimeEntry.objects.get().minutes, 90)
        self.assertTrue(self.web.post("/time/new/", {**base, "hours": 0, "mins": 0}).context["form"].errors.get("hours"))
        future = (timezone.localdate() + timedelta(days=3)).isoformat()
        self.assertTrue(self.web.post("/time/new/", {**base, "work_date": future}).context["form"].errors.get("work_date"))


class SeedAndPageSmokeTests(TestCase):
    """Run the real demo seed, then render every page the way a user would see it."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_every_page_renders_for_staff(self):
        firm = Firm.objects.get(subdomain="demo")
        web = WebClient()
        web.force_login(User.objects.get(firm=firm, email="admin@demo.com"))
        client, invoice, task = Client.objects.filter(firm=firm).first(), Invoice.objects.filter(firm=firm).first(), Task.objects.filter(firm=firm).first()
        urls = ["/", "/dashboard/", "/clients/", "/clients/?archived=1", "/clients/new/", f"/clients/{client.pk}/", f"/clients/{client.pk}/edit/",
                f"/clients/{client.pk}/services/new/", "/tasks/", "/tasks/?mine=1", "/tasks/new/", f"/tasks/{task.pk}/edit/", "/tasks/recurring/",
                "/tasks/recurring/new/", "/documents/", "/documents/new/", "/time/", "/time/new/", "/invoices/", "/invoices/?status=PAID", "/invoices/new/",
                "/invoices/from-time/", f"/invoices/from-time/?client={client.pk}", f"/invoices/{invoice.pk}/", "/team/", "/team/invite/"]
        for url in urls:
            r = web.get(url, follow=True)
            self.assertEqual(r.status_code, 200, url)

    def test_seeded_data_drives_the_dashboard(self):
        firm = Firm.objects.get(subdomain="demo")
        web = WebClient()
        web.force_login(User.objects.get(firm=firm, email="admin@demo.com"))
        s = web.get("/dashboard/").context["s"]
        self.assertEqual(s["clients"], 3)
        self.assertEqual(s["outstanding"], Decimal("4720.00"))  # the pending ₹4,000 + 18% GST invoice; the other is paid
        self.assertEqual(s["unbilled_hours"], 4.75)             # 150 + 90 + 45 minutes
        self.assertGreaterEqual(s["overdue"], 1)
        self.assertEqual(s["received_month"] > 0, True)
        self.assertTrue(Task.objects.filter(firm=firm, recurring_rule__isnull=False).exists())  # engine ran during seeding

    def test_demo_client_portal(self):
        firm = Firm.objects.get(subdomain="demo")
        web = WebClient()
        self.assertEqual(web.post("/login/", {"workspace": "demo", "email": "rao@client.demo", "password": "Password@123"}).status_code, 302)
        r = web.get("/portal/", follow=True)
        self.assertContains(r, "INV/")
        invoices = list(r.context["invoices"])
        self.assertEqual({i.client.name for i in invoices}, {"Dr. S. Rao"})  # only their own invoices
        self.assertContains(r, "Paid")
