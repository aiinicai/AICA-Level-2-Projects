# Tables to add per phase

All money `Numeric(18,2)`, rates `Numeric(6,3)`. Every business table has `id`,
`company_id`, `fy_id`, `created_at`, `updated_at`. Add via Alembic migrations.

| Phase | Table | Key columns | Notes |
| --- | --- | --- | --- |
| 2A | documents | original_filename, stored_path, sha256, pages, mime, status, error | unique-ish (company_id, sha256) → duplicate warning |
| 2A | extraction_results | document_id, method (pdf_text/ocr/ai), provider, raw_text_path, raw_json, field_confidence_json, duration_ms | one row per attempt |
| 2B | suppliers | name, gstin, pan, address, state_code, tally_ledger_name | (company_id, gstin) |
| 2B | invoices | document_id, supplier_id, doc_type, invoice_no, invoice_no_normalized, invoice_date, buyer_gstin, place_of_supply, reverse_charge, currency, exchange_rate, taxable_total, cgst, sgst, igst, cess, freight, packing, other_charges, round_off, tds, tcs, invoice_total, irn, ack_no, eway_bill_no, po_no, original_invoice_ref, amount_in_words, status | status: extracted, needs_review, validated, approved, rejected, mapped, voucher_ready, imported, import_failed |
| 2B | invoice_items | invoice_id, line_no, description, hsn_sac, qty, unit, rate, discount, taxable_value, gst_rate, cgst, sgst, igst, cess, total, stock_item_name, purchase_ledger_name, godown, cost_centre | |
| 2B | invoice_charges | invoice_id, kind, amount, gst_rate, ledger_name | |
| 2C | validation_results | invoice_id, check_code, severity, message, expected, found | |
| 2C | gst_rate_master | hsn_prefix, rate, cess_rate, effective_from, effective_to, notification_ref | not company-scoped |
| 3A | tally_masters | master_type, name, parent, guid, gstin, hsn, gst_rate, alter_id, raw_json, synced_at | (company_id, master_type, name) |
| 3B | mapping_rules | entity, source_key, tally_name, times_used, approved_by | (company_id, entity, source_key) |
| 3C | vouchers | invoice_id, mode, voucher_type, voucher_date, dr_total, cr_total, xml_path, status | |
| 3C | tally_imports | voucher_id, attempt_no, request_xml_path, response_xml, created, altered, errors, line_errors, tally_vch_id, status, imported_at | append-only |
| 4A | gstr2b_uploads | period, file_name, file_sha256, source_format, is_current, uploaded_at | |
| 4A | gstr2b_records | upload_id, section, supplier_gstin, supplier_name, doc_type, doc_no, doc_no_normalized, doc_date, original_doc_no, original_doc_date, pos, reverse_charge, taxable_value, igst, cgst, sgst, cess, itc_available, itc_reason | |
| 4B | purchase_register_uploads / records / rejects, pr_templates | voucher_no, voucher_date, voucher_type, party_name, supplier_gstin, supplier_invoice_no, invoice_no_normalized, supplier_invoice_date, purchase_ledger, taxable_value, cgst, sgst, igst, cess, gst_rate, hsn, invoice_total, narration | |
| 4C | recon_settings, recon_runs, recon_rows | rows: ipt_invoice_id, pr_record_id, gstr2b_record_id, status, match_stage, confidence, reasons_json, differences_json, is_manual, action_status, remarks | |
| 4D | itc_analysis | recon_row_id, itc_in_books, itc_in_2b, difference, eligibility, reason, remarks, action_taken, reviewed_by | |
| 6 | backups | path, kind, size, sha256, verified, created_at | |
