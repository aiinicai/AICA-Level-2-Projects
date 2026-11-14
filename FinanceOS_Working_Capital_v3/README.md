# FinanceOS Working Capital Intelligence — Online Peer Benchmark Edition

## Install (macOS)
```bash
cd FinanceOS_Working_Capital
python3.13 -m venv .venv  # or python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Online peer benchmarking
1. Import debtor/creditor Excel or CSV aging reports.
2. Enter own-company sales, purchases and opening/closing receivable/payable figures in Turnover & Ratios.
3. In Peer Benchmarks, type your reporting company name (optional) and select the industry from the dropdown. Automatic detection only works for known names or when the Excel workbook includes a `Metadata` sheet with `Company Name` in column A and its value in B.
4. Press **Fetch online peer financials**. The app downloads available annual income statements and balance sheets from Yahoo Finance through yfinance for a predefined candidate ticker list, or a user-specified comma-separated list of `.NS` symbols.
5. Review DSO/DPO values and original annual reports before using the output professionally. Some peers will have missing data or provider outages. The application will show N/A and failure reasons rather than invent figures.

**Benchmark methodology:** DSO = 365 × average receivables / annual total revenue. DPO = 365 × average payables / annual cost of revenue. These are **proxies**, not the credit-only ratios used for own-company calculations. The online provider may change its field names and may not supply all data. Benchmarks may therefore be incomplete and not directly comparable. Banking and insurance are intentionally excluded.

No aging records are sent to Yahoo Finance. Ticker queries are sent online. The application is offline-first except for the peer retrieval function.

## Collection letters
In Collection Letters, select an as-of date in Aging Analysis, review the 180-day default threshold, and generate Word drafts to a chosen folder. The application never sends email.

## Build standalone macOS app
```bash
bash build_mac.sh
```
Output: `dist/FinanceOS Working Capital.app`. For distribution to other Macs, Apple signing and notarization may be required.
## Project Presentation & Video Demonstration

A recorded walkthrough explaining how FinanceOS Working Capital Intelligence V3 was developed using natural-language prompts in ChatGPT and Python.

The demonstration covers debtor and creditor turnover ratios, DSO/DPO calculations, industry peer benchmarking using online financial data, overdue invoice identification, and automated collection reminder letters.

🎥 [Click here to watch the FinanceOS project presentation](https://drive.google.com/file/d/1VVMaIs0sDH2X2avwfEziF3L_-JqN12l5/view?usp=sharing)
