# Prompt File 1 — Gemini Invoice Extraction Prompt (used inside the app)

**Where it lives:** `app/extract/gemini.py` (functions `_prompt`, `extract`, constant `SCHEMA`).
**When it is used:** only for supplier invoices / bills that the offline reader (text, OCR, QR, learned layout) could not read with confidence, and only if the user has added a Gemini API key.
**Never used for:** bank or credit-card statements. `assert_not_banking()` refuses any call from banking code, and automated tests enforce it.

## 1. Model settings (Google AI Studio / Gemini API concepts from Module 3)

| Parameter | Value | Why |
| --- | --- | --- |
| Model | Newest stable *gemini-flash-lite*, escalating to *gemini-flash* only if validation fails | Cheapest model first |
| temperature | 0 | Same document, same answer — no creativity in accounting data |
| responseMimeType | application/json | Machine-readable output only |
| responseSchema | See section 4 | Forces exact field names and types |
| Input | Up to 3 masked page images + the masked text layer / OCR text | PAN, Aadhaar, bank a/c, IFSC, UPI blacked out before upload |

## 2. Main prompt (as sent; buyer name and GSTIN are filled in per company — demo company shown)

```text
You are reading an Indian purchase/expense document received by Aarohan Infotech Private Limited (GSTIN 24AAHCA4821K1ZR). Extract exactly what is printed.
Rules:
- supplier = the party issuing the document (usually top of page, near 'Tax Invoice'); the buyer is the company named above. Never swap them.
- invoice_no exactly as printed (keep / - and leading zeros). In Tally-printed invoices the value sits in the box BELOW the label 'Invoice No.' / 'Dated'.
- Amounts: plain numbers, no commas, Indian grouping like 2,36,140.00 means 236140.00. Ignore phone, account, PIN, HSN and invoice numbers when looking for amounts.
- taxable_total is the value before GST; use the HSN/SAC tax summary table if present. tax_summary has one row per GST rate (gst_rate = total rate, e.g. 18 for CGST 9% + SGST 9%).
- grand_total is the final invoice amount (after round-off and TCS), not 'amount after due date'.
- round_off negative if shown as (-) or less.
- For utility bills/receipts without GST, put the net payable in grand_total and taxable_total.
- Text shown as [REDACTED] or black boxes was hidden on purpose; ignore it.
- Use 0 or empty string for anything not printed; say what was unclear in notes.
```

After the page images, a second text part is sent:

```text
TEXT LAYER / OCR OF THE SAME DOCUMENT (may contain reading errors; the image wins if they disagree):
<masked text of the invoice, max 30,000 characters>
```

## 3. Self-check (re-check) prompt

The answer is validated locally (taxable + GST = total to Rs 1, GSTIN checksum, GST rate, place of supply, duplicate). If it fails, Gemini is asked **once** to look again:

```text
Your previous answer was:
<previous JSON>
It fails these checks:
- <each failed check, e.g. "taxable 25,000.00 + GST 4,500.00 != grand total 29,700.00">
Look at the document again and return corrected values. If the document itself is inconsistent, keep the printed values and explain in notes.
```

The corrected answer is kept only if it fails fewer checks. Gemini never posts anything; every result goes to the human review screen.

## 4. Response schema

```json
{
  "type": "OBJECT",
  "properties": {
    "document_type": {
      "type": "STRING",
      "enum": [
        "tax_invoice",
        "bill_of_supply",
        "credit_note",
        "debit_note",
        "utility_bill",
        "receipt",
        "proforma",
        "other"
      ]
    },
    "supplier_name": {
      "type": "STRING"
    },
    "supplier_gstin": {
      "type": "STRING"
    },
    "buyer_name": {
      "type": "STRING"
    },
    "buyer_gstin": {
      "type": "STRING"
    },
    "invoice_no": {
      "type": "STRING",
      "description": "invoice / credit note / debit note number"
    },
    "invoice_date": {
      "type": "STRING",
      "description": "DD-MM-YYYY"
    },
    "original_invoice_no": {
      "type": "STRING",
      "description": "credit/debit note only: the invoice number it is issued against"
    },
    "place_of_supply_state_code": {
      "type": "STRING",
      "description": "2-digit GST state code"
    },
    "reverse_charge": {
      "type": "BOOLEAN"
    },
    "tax_summary": {
      "type": "ARRAY",
      "description": "one row per GST rate",
      "items": {
        "type": "OBJECT",
        "properties": {
          "gst_rate": {
            "type": "NUMBER"
          },
          "taxable": {
            "type": "NUMBER"
          },
          "igst": {
            "type": "NUMBER"
          },
          "cgst": {
            "type": "NUMBER"
          },
          "sgst": {
            "type": "NUMBER"
          },
          "cess": {
            "type": "NUMBER"
          }
        },
        "required": [
          "gst_rate",
          "taxable"
        ]
      }
    },
    "taxable_total": {
      "type": "NUMBER"
    },
    "igst_total": {
      "type": "NUMBER"
    },
    "cgst_total": {
      "type": "NUMBER"
    },
    "sgst_total": {
      "type": "NUMBER"
    },
    "cess_total": {
      "type": "NUMBER"
    },
    "tcs": {
      "type": "NUMBER"
    },
    "round_off": {
      "type": "NUMBER",
      "description": "negative if deducted"
    },
    "grand_total": {
      "type": "NUMBER",
      "description": "final amount payable on this invoice"
    },
    "lines": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "description": {
            "type": "STRING"
          },
          "hsn": {
            "type": "STRING"
          },
          "qty": {
            "type": "NUMBER"
          },
          "uom": {
            "type": "STRING"
          },
          "rate": {
            "type": "NUMBER"
          },
          "taxable": {
            "type": "NUMBER"
          },
          "gst_rate": {
            "type": "NUMBER"
          }
        }
      }
    },
    "notes": {
      "type": "STRING",
      "description": "anything unclear or illegible"
    }
  },
  "required": [
    "document_type",
    "supplier_gstin",
    "invoice_no",
    "invoice_date",
    "taxable_total",
    "grand_total"
  ]
}
```

## 5. Prompt-engineering techniques used

- **Role and context:** "Indian purchase/expense document received by <buyer> (GSTIN …)" — fixes who is buyer and who is supplier.
- **Explicit rules** for the commonest errors seen in testing: swapped supplier/buyer, Tally-printed invoice-number boxes, Indian digit grouping (2,36,140.00), phone/PIN/HSN numbers mistaken for amounts, "amount after due date", negative round-off.
- **Negative instructions:** what to ignore (redacted areas, non-amount numbers).
- **Structured output** via schema instead of free text; "0 or empty string" for missing fields so nothing is invented.
- **Uncertainty channel:** the `notes` field asks the model to say what was unclear rather than guess.
- **Verification loop:** deterministic checks + one targeted re-ask (self-correction), then human review.
