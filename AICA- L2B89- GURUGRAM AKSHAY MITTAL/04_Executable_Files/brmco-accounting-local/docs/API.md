# Local Host API (http://127.0.0.1:8000)

Interactive docs are at **http://127.0.0.1:8000/docs** while the app is running.

Errors always come back as `{"detail": "<message for the user>"}`:
- 400: ordinary problems, such as posting an invalid file.
- 404: unknown batch or history entry.
- 422: malformed request.
- 500: unexpected problems, with a reference number that appears in `data/logs/errors.log`.

## Vouchers

`{base}` is `/api/sales`, `/api/purchase`, `/api/journal`, `/api/bank/receipt` or `/api/bank/payment`.

| Method | Path | Description |
|---|---|---|
| GET | `{base}/template` | Blank .xlsx template with dropdowns from the synced masters |
| GET | `{base}/sample` | Filled sample matching the demo masters |
| POST | `{base}/upload` | multipart `file=<xlsx>`. Validates and returns a **batch** (below) |

Batch response:

```json
{
  "id": "6f95250fff50", "kind": "sales", "kind_label": "Sales", "file_name": "sales_sept.xlsx",
  "status": "validated", "row_count": 3, "voucher_count": 2, "errors": 0, "warnings": 0,
  "issues": [{"severity": "error", "row": 7, "column": "Customer Ledger", "voucher": "INV-1025",
              "message": "Ledger \"ABC Traders\" does not exist in Tally master data.", "code": "master.ledger"}],
  "vouchers": [{"voucher_type": "Sales", "label": "INV-1025", "date": "2026-09-25", "party": "ABC Traders",
                "taxable_value": "100000.00", "cgst": "9000.00", "sgst": "9000.00", "total": "118000.00",
                "balanced": true, "entries": [{"ledger": "ABC Traders", "side": "Dr", "amount": "118000.00"}]}],
  "totals": {"debit": "135110.00", "credit": "135110.00"},
  "can_post": true, "demo_mode": true, "stale": null
}
```

## Batches

| Method | Path | Description |
|---|---|---|
| GET | `/api/batches/{id}` | Batch as above |
| GET | `/api/batches/{id}/xml` | Download Tally XML. Returns 400 if the batch has errors |
| POST | `/api/batches/{id}/post` | Confirm & post. Returns 400 if the batch has errors, was already posted, or settings changed since validation |

Post response:

```json
{"status": "SUCCESS", "demo_mode": false, "message": "2 of 2 voucher(s) accepted by Tally.",
 "created": 2, "altered": 0, "ignored": 0, "errors": 0, "history_id": 14, "xml_file": "sales_….xml",
 "results": [{"voucher": "INV-1025", "status": "SUCCESS", "message": "1 voucher created successfully.",
              "created": 1, "line_errors": [], "last_voucher_id": "4567"}]}
```

Per-voucher `status` is one of `SUCCESS`, `PARTIAL`, `FAILED`, `SKIPPED` (already posted) or `NOT_ATTEMPTED` (Tally went offline).

## Tally

| Method | Path | Description |
|---|---|---|
| GET | `/api/tally/status` | `{connected, message, url, companies[], demo_mode, warning}` |
| POST | `/api/tally/masters/sync` | body `{"types": ["ledger", …]}` (optional). Returns results per type and counts |
| GET | `/api/tally/masters` | Cached counts per type |
| GET | `/api/tally/masters/{type}?q=` | Search the cache. `type` is `ledger`, `group`, `stock_item`, `unit` or `voucher_type` |

## History & audit

| Method | Path | Description |
|---|---|---|
| GET | `/api/history?q=&kind=&status=&date_from=&date_to=` | Search posting attempts |
| GET | `/api/history/{id}` | One attempt with per-voucher results |
| GET | `/api/audit?q=&action=` | Audit log |

## App, settings, server

| Method | Path | Description |
|---|---|---|
| GET | `/api/app` | Name, version, demo flag, company |
| GET | `/api/dashboard` | Counts, recent imports |
| GET | `/api/settings` | Current settings and the list of states |
| PUT | `/api/settings` | Partial update. The whole result is validated before anything is saved |
| GET | `/api/server/status` | Result of Server Host `/health` + `/version` |

The Server Host API is documented in `brmco-accounting-server/README.md`.
