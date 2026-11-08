# FinanceOS v3 changes

- Financial statements requested through both yfinance annual getter and property interfaces.
- Broader row-name support, period-aligned income statements and consecutive-year balance-sheet averages.
- Per-ticker detailed retrieval diagnostics, including unavailable financial fields.
- Successful results cached locally at `~/.financeos_peer_cache.json`; cached results marked with retrieval date.
- Source URL and financial statement field names displayed for audit review.

**Limitations:** The public Yahoo Finance provider may not supply financial statements for Indian equities. If no source values exist, the app will not invent DSO/DPO. Cached data is not live. This release does not implement a guaranteed secondary filings provider. Review peer methodology and source filings before professional use.
