# Capital Gains Summariser (CG Tool)

**AICA Level 2 Project – Piyushi Kataria (Piyushi Kataria & Co, Chartered Accountants)**

## What it does
An offline tool for CA practice work. Upload the capital gain / P&L reports downloaded from any Indian broker or RTA (CAMS, KFintech) and the tool produces one consolidated Excel workbook.

| Output sheet | Contents |
|---|---|
| Summary | Equity & Mutual Fund gains – sale value, cost, gross gain, charges, net gain, STCG / LTCG, split by sale before / on-after 23-07-2024 |
| Workings | Transaction-wise computation, including grandfathering (FMV 31-01-2018) |
| F&O / Intraday | Business income, broker-wise – turnover, favourable / unfavourable, gross profit, expenses (brokerage, STT, exchange and other charges) |
| Exceptions | Anything doubtful – nothing is silently dropped or guessed |
| Reconciliation | Each file reconciled to the broker's own Total / Sub-total rows |
| Parse log | What was read from each file |
| KDK Template (optional) | Tick / untick option to export data in the KDK tax-software import format |

## Key features
| Feature | Detail |
|---|---|
| Format-proof reading | Headers recognised by meaning, not column position; handles two-row headers, multiple tables per sheet, HTML ".xls" files |
| Tax rules in a CONFIG block | 12-month holding for listed equity / equity MF, grandfathering, rate change from 23-07-2024; STT never deducted |
| Brokers tested | Tradesmart Fintech (Tax P&L Report), Angel One (F&O P&L), CAMS / KFintech statements |
| Privacy | Fully offline – no network calls; runs on 127.0.0.1 only |

## How to run
```
pip install -r requirements.txt
python capgain_tool.py
```
Command line: `python capgain_tool.py a.xlsx b.xls --out summary.xlsx`

Build the Windows .exe: `pyinstaller CGToolnew4.spec` (output: `dist\CGToolnew4.exe`)

> Tax rates are indicative – verify against the Act in force before filing.
