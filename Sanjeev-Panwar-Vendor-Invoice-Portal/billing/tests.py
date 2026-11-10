"""Synthetic-data regression checks for the submission copy."""
import secrets
import tempfile
from pathlib import Path
from unittest.mock import patch

import fitz
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from .models import Company, VendorProfile, Invoice, Document, AuditEvent


class PortalWorkflowTests(TestCase):
    def setUp(self):
        self.password = secrets.token_urlsafe(28)
        self.staff = User.objects.create_user('finance@example.com', password=self.password, is_staff=True)
        self.vendor = User.objects.create_user('vendor@example.com', email='vendor@example.com', password=self.password)
        self.profile = VendorProfile.objects.create(user=self.vendor, legal_name='Fictional Vendor', kra_pin='P987654321Z')
        self.company = Company.objects.create(code='CO01', name='Demo Group Company 01 Ltd', kra_pin='A000000001B')
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = patch('billing.views.PRIVATE_DOCS', Path(directory.name))
        storage.start()
        self.addCleanup(storage.stop)

    def pdf(self, name='invoice.pdf', wrong_pin=False):
        doc = fitz.open()
        page = doc.new_page()
        pin = 'A999999999B' if wrong_pin else self.company.kra_pin
        lines = ['INVOICE', 'Bill To: Demo Group Company 01 Ltd', 'Recipient KRA PIN: ' + pin,
                 'Invoice No: INV-SYNTHETIC-01', 'Invoice Date: 2026-11-05',
                 'PO Number: PO-SYNTHETIC-01', 'Currency: KES', 'Net Amount: 1000.00',
                 'VAT: 160.00', 'Grand Total: 1160.00']
        page.insert_text((45, 70), '\n'.join(lines), fontsize=12)
        raw = doc.tobytes()
        doc.close()
        return SimpleUploadedFile(name, raw, content_type='application/pdf')

    def submit(self, wrong_pin=False):
        return self.client.post('/upload/', {'company': self.company.pk,
            'invoice': self.pdf(wrong_pin=wrong_pin), 'purchase_order': self.pdf('po.pdf')})

    def approve_profile(self):
        self.profile.approved = True
        self.profile.save()
        self.client.force_login(self.vendor)

    def test_registration_login_and_pending_access(self):
        response = self.client.post('/register/', {'legal_name': 'Synthetic New Vendor',
            'kra_pin': 'P123456789Z', 'email': 'new-vendor@example.com',
            'password1': self.password, 'password2': self.password})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(VendorProfile.objects.get(user__username='new-vendor@example.com').approved)
        self.assertEqual(self.client.get('/upload/').status_code, 302)
        self.client.post('/logout/')
        self.assertEqual(self.client.post('/login/', {'username': 'new-vendor@example.com',
            'password': self.password}).status_code, 302)

    def test_finance_approval_requires_staff_and_post(self):
        self.client.force_login(self.vendor)
        url = f'/finance/vendors/{self.profile.pk}/approve/'
        self.assertEqual(self.client.post(url).status_code, 302)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.approved)
        self.client.force_login(self.staff)
        self.client.get(url)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.approved)
        self.client.post(url)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.approved)
        self.assertTrue(AuditEvent.objects.filter(action='VENDOR_APPROVED').exists())

    def test_upload_review_export_and_lock(self):
        self.approve_profile()
        self.assertEqual(self.submit().status_code, 302)
        invoice = Invoice.objects.get()
        self.assertEqual(invoice.invoice_number, 'INV-SYNTHETIC-01')
        self.assertEqual(str(invoice.total_amount), '1160.00')
        self.assertEqual(invoice.documents.count(), 2)
        self.assertEqual(self.client.get(f'/invoice/{invoice.pk}/').status_code, 200)
        self.client.force_login(self.staff)
        response = self.client.post(f'/finance/invoice/{invoice.pk}/', {
            'invoice_number': invoice.invoice_number, 'invoice_date': '2026-11-05',
            'currency': 'KES', 'net_amount': '1000.00', 'vat_amount': '160.00',
            'total_amount': '1160.00', 'po_number': 'PO-SYNTHETIC-01',
            'finance_notes': 'Checked synthetic data', 'action': 'approve'})
        self.assertEqual(response.status_code, 302)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.APPROVED)
        response = self.client.post('/finance/export/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'INV-SYNTHETIC-01', response.content)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.EXPORTED)
        self.assertEqual(self.client.get(f'/finance/invoice/{invoice.pk}/').status_code, 302)
        self.assertEqual(self.client.post('/finance/export/').status_code, 302)

    def test_wrong_recipient_and_duplicate_rejected(self):
        self.approve_profile()
        self.assertEqual(self.submit(wrong_pin=True).status_code, 200)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(self.submit().status_code, 302)
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_cross_vendor_document_and_invoice_isolation(self):
        self.approve_profile()
        self.submit()
        invoice = Invoice.objects.get()
        document = Document.objects.first()
        response = self.client.get(f'/document/{document.pk}/')
        self.assertEqual(response.status_code, 200)
        response.close()
        other = User.objects.create_user('other@example.com', password=self.password)
        VendorProfile.objects.create(user=other, legal_name='Other Synthetic Vendor', kra_pin='P123456789Z', approved=True)
        self.client.force_login(other)
        self.assertEqual(self.client.get(f'/invoice/{invoice.pk}/').status_code, 404)
        self.assertEqual(self.client.get(f'/document/{document.pk}/').status_code, 404)
        self.assertEqual(self.client.post('/finance/export/').status_code, 302)

    def test_invalid_file_and_anonymous_access(self):
        self.assertEqual(self.client.get('/upload/').status_code, 302)
        self.approve_profile()
        response = self.client.post('/upload/', {'company': self.company.pk,
            'invoice': SimpleUploadedFile('invalid.pdf', b'NOT A PDF'), 'purchase_order': self.pdf('po.pdf')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_csrf_enforced_and_finance_pages_render(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        self.assertEqual(client.post(f'/finance/vendors/{self.profile.pk}/approve/').status_code, 403)
        for url in ['/finance/', '/finance/vendors/', '/admin/', '/password-reset/']:
            self.assertEqual(client.get(url).status_code, 200)
