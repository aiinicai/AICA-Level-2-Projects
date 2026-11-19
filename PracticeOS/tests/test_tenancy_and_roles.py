import json

from django.core.cache import cache
from django.test import Client as WebClient
from django.test import TestCase

from accounts.models import User
from billing.models import Invoice, TimeEntry
from billing.services import create_invoice
from crm.models import Client
from documents.models import Document
from tests.helpers import PW, make_world
from workflow.models import Task


class TenantIsolationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.a, self.b = make_world("alpha"), make_world("beta")
        self.web = WebClient()
        self.web.force_login(self.a.admin)
        self.b_task = Task.objects.create(firm=self.b.firm, title="B secret", created_by=self.b.admin)
        self.b_invoice = create_invoice(firm=self.b.firm, client=self.b.client, items=[{"description": "x", "quantity": 1, "rate": 100, "tax_rate": 18}])
        self.b_doc = Document.objects.create(firm=self.b.firm, client=self.b.client, type="LINK", name="B doc", url="https://example.com")

    def test_other_firms_records_return_404(self):
        for url in [f"/clients/{self.b.client.pk}/", f"/clients/{self.b.client.pk}/edit/", f"/tasks/{self.b_task.pk}/edit/",
                    f"/invoices/{self.b_invoice.pk}/", f"/invoices/{self.b_invoice.pk}/pay/"]:
            self.assertEqual(self.web.get(url).status_code, 404, url)
        for url in [f"/clients/{self.b.client.pk}/archive/", f"/tasks/{self.b_task.pk}/delete/", f"/invoices/{self.b_invoice.pk}/cancel/",
                    f"/documents/{self.b_doc.pk}/delete/", f"/documents/{self.b_doc.pk}/share/", f"/team/{self.b.member.pk}/toggle-active/"]:
            self.assertEqual(self.web.post(url).status_code, 404, url)
        self.b.client.refresh_from_db(), self.b_invoice.refresh_from_db()
        self.assertTrue(self.b.client.is_active)
        self.assertEqual(self.b_invoice.status, "PENDING")
        self.assertTrue(Task.objects.filter(pk=self.b_task.pk).exists() and Document.objects.filter(pk=self.b_doc.pk).exists())

    def test_lists_only_show_own_firm(self):
        self.assertNotContains(self.web.get("/clients/"), self.b.client.name)
        self.assertNotContains(self.web.get("/tasks/"), "B secret")
        self.assertNotContains(self.web.get("/documents/"), "B doc")
        self.assertEqual(self.web.get("/invoices/").context["invoices"], [])  # B has an invoice; A must not see it

    def test_forged_foreign_keys_are_rejected(self):
        before = Task.objects.count()
        r = self.web.post("/tasks/new/", {"title": "Sneaky", "client": self.b.client.pk, "status": "TODO", "priority": "MEDIUM"})
        self.assertEqual(r.status_code, 200)  # form re-rendered with an error
        self.assertTrue(r.context["form"].errors.get("client"))
        r = self.web.post("/tasks/new/", {"title": "Sneaky", "assignee": self.b.member.pk, "status": "TODO", "priority": "MEDIUM"})
        self.assertTrue(r.context["form"].errors.get("assignee"))
        r = self.web.post("/invoices/new/", {"client": self.b.client.pk, "issue_date": "2026-11-02", "items-TOTAL_FORMS": 1, "items-INITIAL_FORMS": 0,
                                             "items-0-description": "x", "items-0-quantity": 1, "items-0-rate": 10, "items-0-tax_rate": 18})
        self.assertTrue(r.context["form"].errors.get("client"))
        self.assertEqual(Task.objects.count(), before)
        self.assertEqual(Invoice.objects.filter(firm=self.a.firm).count(), 0)

    def test_foreign_document_download_is_404(self):
        self.assertEqual(self.web.get(f"/documents/{self.b_doc.pk}/download/").status_code, 404)

    def test_same_email_can_exist_in_two_workspaces(self):
        User.objects.create_user(self.a.firm, "shared@x.test", "Shared A", "Passw0rd-AAA!")
        User.objects.create_user(self.b.firm, "shared@x.test", "Shared B", "Passw0rd-BBB!")
        web = WebClient()
        self.assertEqual(web.post("/login/", {"workspace": "alpha", "email": "shared@x.test", "password": "Passw0rd-AAA!"}).status_code, 302)
        web = WebClient()
        self.assertEqual(web.post("/login/", {"workspace": "beta", "email": "shared@x.test", "password": "Passw0rd-AAA!"}).status_code, 200)  # wrong workspace's password
        self.assertEqual(web.post("/login/", {"workspace": "beta", "email": "shared@x.test", "password": "Passw0rd-BBB!"}).status_code, 302)
        self.assertEqual(web.get("/dashboard/").wsgi_request.user.name, "Shared B")


class RoleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.w = make_world("roles")

    def web_as(self, user):
        web = WebClient()
        web.force_login(user)
        return web

    def test_anonymous_goes_to_login(self):
        for url in ["/", "/dashboard/", "/clients/", "/tasks/", "/invoices/", "/time/", "/documents/", "/team/"]:
            r = WebClient().get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/login/", r["Location"])

    def test_client_login_is_confined_to_the_portal(self):
        web = self.web_as(self.w.portal)
        for url in ["/dashboard/", "/clients/", "/tasks/", "/time/", "/invoices/", "/documents/", "/team/", "/invoices/new/"]:
            r = web.get(url)
            self.assertEqual((r.status_code, r["Location"]), (302, "/portal/"), url)
        self.assertEqual(web.post("/tasks/new/", {"title": "x"}).status_code, 302)
        self.assertEqual(web.get("/portal/").status_code, 200)
        self.assertEqual(web.get("/", follow=False)["Location"], "/portal/")

    def test_team_member_cannot_reach_admin_pages(self):
        web = self.web_as(self.w.member)
        self.assertEqual(web.get("/team/").status_code, 403)
        self.assertEqual(web.get("/team/invite/").status_code, 403)
        self.assertEqual(web.post(f"/team/{self.w.admin.pk}/toggle-active/").status_code, 403)
        self.assertEqual(web.get("/clients/").status_code, 200)
        self.assertEqual(web.get("/dashboard/").status_code, 200)

    def test_staff_cannot_use_portal_page(self):
        self.assertEqual(self.web_as(self.w.admin).get("/portal/")["Location"], "/dashboard/")

    def test_members_only_see_and_edit_their_own_time(self):
        mine = TimeEntry.objects.create(firm=self.w.firm, user=self.w.member, client=self.w.client, work_date="2026-11-01", minutes=60, description="mine")
        theirs = TimeEntry.objects.create(firm=self.w.firm, user=self.w.admin, client=self.w.client, work_date="2026-11-01", minutes=90, description="admins")
        member = self.web_as(self.w.member)
        r = member.get("/time/?from=2026-11-01&to=2026-11-30")
        self.assertEqual([e.pk for e in r.context["entries"]], [mine.pk])
        self.assertEqual(member.get(f"/time/{theirs.pk}/edit/").status_code, 403)
        self.assertEqual(member.post(f"/time/{theirs.pk}/delete/").status_code, 403)
        admin = self.web_as(self.w.admin).get("/time/?from=2026-11-01&to=2026-11-30")
        self.assertEqual({e.pk for e in admin.context["entries"]}, {mine.pk, theirs.pk})

    def test_last_admin_cannot_be_removed_or_demoted(self):
        web = self.web_as(self.w.admin)
        web.post(f"/team/{self.w.admin.pk}/toggle-active/")  # can't disable yourself
        web.post(f"/team/{self.w.admin.pk}/toggle-role/")
        self.w.admin.refresh_from_db()
        self.assertTrue(self.w.admin.is_active and self.w.admin.role == "ADMIN")
        self.w.member.role = "ADMIN"
        self.w.member.save()
        web.post(f"/team/{self.w.member.pk}/toggle-role/")  # another admin may be demoted while one remains
        self.w.member.refresh_from_db()
        self.assertEqual(self.w.member.role, "TEAM_MEMBER")

    def test_admin_invites_login_and_it_works(self):
        web = self.web_as(self.w.admin)
        r = web.post("/team/invite/", {"name": "New Hire", "email": "NEW@roles.test", "role": "TEAM_MEMBER", "hourly_rate": "800"})
        self.assertEqual(r.status_code, 200)
        temp = r.context["temp_password"]
        user = User.objects.get(firm=self.w.firm, email="new@roles.test")
        self.assertTrue(user.check_password(temp))
        self.assertEqual(WebClient().post("/login/", {"workspace": "roles", "email": "new@roles.test", "password": temp}).status_code, 302)
        # duplicate email in the same workspace, and a client login without a linked client, are rejected
        self.assertTrue(web.post("/team/invite/", {"name": "Dup", "email": "new@roles.test", "role": "TEAM_MEMBER"}).context["form"].errors.get("email"))
        self.assertTrue(web.post("/team/invite/", {"name": "C", "email": "c@roles.test", "role": "CLIENT"}).context["form"].errors.get("client"))

    def test_disabled_user_is_locked_out_immediately(self):
        web = self.web_as(self.w.member)
        self.assertEqual(web.get("/clients/").status_code, 200)
        self.w.member.is_active = False
        self.w.member.save()
        self.assertEqual(web.get("/clients/").status_code, 302)  # existing session no longer valid
        self.assertEqual(WebClient().post("/login/", {"workspace": "roles", "email": self.w.member.email, "password": PW}).status_code, 200)


class CsrfTests(TestCase):
    def test_state_changing_requests_require_csrf_token(self):
        w = make_world("csrf")
        web = WebClient(enforce_csrf_checks=True)
        web.force_login(w.admin)
        self.assertEqual(web.post(f"/clients/{w.client.pk}/archive/").status_code, 403)
        t = Task.objects.create(firm=w.firm, title="t", created_by=w.admin)
        self.assertEqual(web.post(f"/tasks/{t.pk}/status/", json.dumps({"status": "REVIEW"}), content_type="application/json").status_code, 403)
        self.assertEqual(web.get("/logout/").status_code, 405)  # logout is POST-only
