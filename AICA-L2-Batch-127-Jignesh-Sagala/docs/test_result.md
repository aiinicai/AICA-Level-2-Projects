# Test result

Run: 27 Nov 2026 08:57. Python 3.13.18 on Linux.

| Test file | What it checks | Result |
|---|---|---|
| `test_cdsl.py` | Fund and demat statement reader (CAS) | **PASS** |
| `test_zcn.py` | Broker contract note reader | **PASS** |
| `test_bank.py` | Bank statement readers (two layouts) | **PASS** |
| `test_zledger.py` | Broker funds ledger reader | **PASS** |
| `test_samples.py` | Made-up sample statements (samples/): locked, holder BusyMe, readers pass, wrong password refused | **PASS** |
| `test_open_position.py` | Opening-cost back-solve (average-cost rule) | **PASS** |
| `test_prices_fetch.py` | Price script: parsers, plan, safe append (offline) | **PASS** |
| `test_dashboard_numbers.py` | Dashboard engine (JavaScript) = Python engine, plus hand cases | **PASS** |
| `test_life.py` | Calendar, premiums, SIP and rent (JavaScript) = Python, plus hand cases | **PASS** |
| `test_excel_check.py` | Excel formulas (separate method) = dashboard value of funds and shares, 12 dates | **PASS** |
| `test_dashboard_ui.py` | Dashboard on screen: displayed numbers = Python engine, filters, CSV export, SIP, property, insurance, calendar, DTAA tab, phone width | **PASS** |
