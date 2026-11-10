# Demonstration with fictional data

After setup, use a normal browser window for Finance and a separate private window for the vendor. Accounts/passwords are created locally and are not included in the submission.

1. Open http://127.0.0.1:8002 and sign in with the Finance account you created.
2. In the vendor window register Demo Vendor Supplies Ltd with fictional PIN P987654321Z and an example.com email address. Choose a new local password.
3. Confirm upload is blocked while approval is pending.
4. In Finance, open Vendors and approve the new vendor.
5. Return as vendor, open Upload and select Demo Group Company 01 Ltd (CO01).
6. Attach local_demo/demo_documents/demo_invoice.pdf and demo_purchase_order.pdf. These are freshly generated synthetic documents, not copied from the working project. Submit and note the reference.
7. Confirm parsed invoice INV-DEMO-0001, PO-DEMO-101, KES net 1000.00, VAT 160.00, total 1160.00. Finance must verify these values even when automatically populated.
8. In Finance, review/correct and approve the invoice, then download the ERP staging CSV. The invoice becomes exported and is locked in the Finance review workflow.
9. Attempt a repeated submission; the duplicate should be rejected. Submit demo_invalid_pin_invoice.pdf with the valid PO; recipient PIN validation should reject it without a new invoice.
10. Log out. Do not include generated databases, PDFs, test-email files or exports in GitHub uploads.

For optional recording: 4-5 minutes, fictional records only. Hide notifications, browser suggestions, password entry and unrelated windows. Record only the local app; no public tunnel is needed. Review the entire recording before sharing. A video is not required by the upload guide.

See VALIDATION.md for automated evidence; do not claim an actual screen recording or human walkthrough was completed by this preparation.
