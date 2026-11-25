# Synthetic data (no real company data)

Every name, amount and reference in this folder is made up. Rebuild it with:

```
python scripts/make_synthetic.py --as-of 2026-11-24 --months 3 --seed 26
```

The same seed always produces the same files.

| Folder | What it is |
|---|---|
| `day1_<date>/` | A full daily upload: ERP exports, the bank's bill discount / LC file, the templates, bank balances and facility, the category list and the payment history. |
| `day2_<date+1>/` | The next day's re-upload. Cleared cheques and paid invoices drop out, a few new rows appear, and the keys stay the same. Used to prove that overrides survive a re-upload. |
| `acceptance/` | `pdc_month_2026_12.xlsx` has exactly 70 PDCs in December 2026, including cheques on every lot boundary. Its "Hand check" sheet and the `_expected.csv` file give the lot totals worked out independently of the app. |

## Test cases planted on purpose (also listed in each folder's `_manifest.txt`)
- **ERP layout**: report title rows above the header and a `Total` row at the bottom of the receivables and PDC exports.
- **Header spellings**: ERP headers such as `Doc No`, `Party Name`, `Chq Date`, `Deal Type` and `Value Date` are recognised as aliases.
- **Unknown headers and categories**: `Visa Renewal Fees` (wide layout) should be matched to *Visa & labour fees* through its alias. `Marketing campaign` (long layout) has no good match and is offered as a new category.
- **Category missing**: a row with a blank category takes the source's default category.
- **Duplicate**: one PDC row appears twice.
- **Overlap**: a payment-plan invoice has the same vendor and amount as a PDC, one day apart, so it may be paid twice.
- **Bill discounted**: a receivable financed by discount proceeds must not be collected again.
- **Overdue**: unpaid items dated before the as-of date go into the current lot.
- **Risk-adjusted**: three receivables are flagged, for the Risk-adjusted scenario.
- **Non-OMR bank account**: a USD account with a manual rate of 0.3845.
- **Payment history**: about 400 paid invoices, where each customer has its own typical delay, for the advisory delay model.
