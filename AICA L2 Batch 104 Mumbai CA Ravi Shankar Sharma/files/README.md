# Bank Reconciliation App

A simple Streamlit-based bank reconciliation application for CA and finance professionals. Upload bank statements and GL registers, automatically reconcile transactions, and generate reports.

## Features

- **Automatic Reconciliation**: Match transactions using date (±3 days tolerance), amount, and reference
- **Dashboard**: View matched/unmatched transactions and match percentage
- **Detailed Reports**: 
  - Matched transactions
  - Bank-only transactions
  - GL-only transactions
  - Amount/date mismatches
  - Duplicate detection
  - Bank Reconciliation Statement (BRS) summary
- **Excel Export**: Download reconciliation results as Excel workbook
- **Unit Tests**: Pytest tests for matching, unmatched, mismatch, and duplicate scenarios

## Project Structure

```
bank-reconciliation-app/
├── app.py                          # Main Streamlit app
├── utils.py                        # Reconciliation logic
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── sample_data/
│   ├── sample_bank_statement.csv   # Sample bank data (50 transactions)
│   └── sample_gl_register.csv      # Sample GL data (50+ transactions)
└── tests/
    ├── __init__.py
    └── test_reconciliation.py      # Unit tests
```

## Installation

1. Clone or download the project:
```bash
cd bank-reconciliation-app
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Run the App

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

### Using Sample Data

1. Click "Upload Bank Statement" → select `sample_data/sample_bank_statement.csv`
2. Click "Upload GL Register" → select `sample_data/sample_gl_register.csv`
3. View reconciliation results in tabs:
   - **Matched**: Successfully reconciled transactions
   - **Bank Only**: Transactions in bank statement but not in GL
   - **GL Only**: Transactions in GL but not in bank statement
   - **Mismatch**: Same reference but different amounts/dates
   - **Duplicates**: Duplicate entries detected
   - **BRS Summary**: Bank Reconciliation Statement

4. Download results as Excel workbook

### Input File Format

**Bank Statement CSV** (with headers):
```
Date,Reference,Amount,Balance
01-09-2024,CHQ001,5000,10000
02-09-2024,DEP001,15000,25000
```

**GL Register CSV** (with headers):
```
Date,Reference,Amount,Description
01-09-2024,CHQ001,5000,Rent Payment
02-09-2024,DEP001,15000,Sales Revenue
```

Dates must be in DD-MM-YYYY format.

## Run Tests

```bash
pytest tests/ -v
```

### Test Coverage

- `test_basic_matching`: Verify transaction matching logic
- `test_unmatched_bank_only`: Identify bank-only transactions
- `test_unmatched_gl_only`: Identify GL-only transactions
- `test_date_tolerance`: Test date tolerance matching (±3 days)
- `test_amount_mismatch_detection`: Detect amount mismatches
- `test_duplicate_detection`: Identify duplicate transactions
- `test_brs_generation`: Verify BRS summary generation
- `test_empty_dataframes`: Handle empty input
- `test_perfect_match`: Test perfect matching scenario

## Reconciliation Logic

### Matching Rules

Transactions are matched if:
1. **Amount** matches exactly
2. **Date** is within ±3 days
3. **Reference** matches (or weighted match if missing)

### Match Scoring

- Exact date match: +2 points
- Reference match: +1 point
- Minimum score to match: 0 (amount + date tolerance sufficient)

### Categories

| Category | Meaning |
|----------|---------|
| **Matched** | Found in both bank & GL with matching date/amount/reference |
| **Bank Only** | In bank statement but not in GL (e.g., cheques in transit) |
| **GL Only** | In GL but not in bank statement (e.g., accruals) |
| **Mismatch** | Same reference but different amounts or dates |
| **Duplicates** | Repeated entries within same dataset |

## Sample Data

The `sample_data/` folder contains realistic reconciliation scenarios:

- ✓ 40+ matched transactions
- 🏦 5 bank-only transactions (timing/in-transit items)
- 📘 10 GL-only transactions (accruals, reversals)
- ⚠️ 1 amount mismatch
- 🔁 1 duplicate
- ⏱️ 2 timing differences (±1-2 days)

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | 1.28.1 | Web app framework |
| pandas | 2.0.3 | Data processing |
| openpyxl | 3.1.2 | Excel export |
| pytest | 7.4.2 | Unit testing |

## Troubleshooting

**"Date parsing error"**: Ensure dates are in DD-MM-YYYY format

**"No transactions matched"**: 
- Check that Amount column contains numbers (no ₹ or other symbols)
- Verify date format matches DD-MM-YYYY
- Increase date tolerance if needed (edit `date_tolerance=3` in app.py)

**"Import error"**: Make sure all requirements are installed:
```bash
pip install --upgrade -r requirements.txt
```

## Future Enhancements

- Multi-tolerance settings (configurable date/amount tolerance)
- Batch file processing
- Integration with accounting software (Tally, SAP)
- Machine learning-based fuzzy matching
- Email report delivery
- API for external integration

## License

Open source - free to use and modify for your organization.

## Support

For issues or feature requests, check the test suite for expected behavior or review the reconciliation logic in `utils.py`.
