# Database design

Defined in `app/models.py` (created automatically by `flask init-db`).

```
users ─┐ (username stored as text in audit/created_by fields)
plants ──< challans >── vendors
              │
              ├──< challan_lines ──< receipts (goods received back, per line)
              └── consignor_json / consignee_json (snapshots taken at issue)
counters        key 'VENDOR' or 'MRC|2026-27' -> last_no
series_config   one row per challan type: prefix, FY style, separator, digits
audit_log       who / when / what for every change
upload_batches  parsed Excel uploads awaiting commit
```

| Table | Key columns |
|---|---|
| `users` | username (unique), role (requester/approver/admin), password_hash, active, must_change_password |
| `plants` | code (unique), company_name, address, state_code, pin, **gstin**, signatory - one per GSTIN/plant |
| `series_config` | ctype (MRC/MNRC), prefix, fy_style (short/long), separator, pad |
| `counters` | key (PK), last_no - incremented inside the saving transaction |
| `vendors` | vendor_no (MV-0001, unique), name, name_norm, address, state_code, pin, gstin (unique, NULL if unregistered), pan (derived), contact_person, phone, email, **erp_code**, erp_code_updated_at/by, active |
| `challans` | ctype, status (DRAFT/FINAL/CANCELLED), **number (unique, ≤16)**, fy, seq_no, challan_date, plant_id, vendor_id, place_of_supply, interstate, purpose, purpose_text, reason; returnable-only: corrective_action/owner/target_date/status/done_date, expected_return_date, goods_category, return_status; transport_mode, vehicle_no, transporter_name/id; ref_doc_no/date; ewb_status/no/date/valid_upto; totals (taxable, cgst, sgst, igst, cess, grand); printed_at/print_count; cancel_reason/by/at; created/updated/finalized by+at; is_historical |
| `challan_lines` | challan_id, line_no, part_no, description, hsn, qty, uom, rate, taxable_value, tax_rate, cess_rate, cgst, sgst, igst, cess, qty_received |
| `receipts` | challan_id, line_id, received_date, qty, doc_ref, remarks, created_by |
| `audit_log` | ts, username, entity, entity_id, ref, action, details |
| `upload_batches` | kind, filename, payload (JSON), errors, warnings, status |

Indexes: challan number (unique), type, status, date, vendor, ewb_status, FY; line part_no (for part search); vendor GSTIN (unique) and normalised name.
Cancelled challans keep their row and number; numbers are never reused or deleted. Drafts have no number, so deleting a draft never creates a gap.
