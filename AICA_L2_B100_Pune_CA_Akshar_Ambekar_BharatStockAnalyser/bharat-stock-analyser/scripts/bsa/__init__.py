"""Bharat Stock Analyser: equity research engine for NSE and BSE listed stocks.

Modules:
    fmt           Indian number formatting (lakh and crore grouping)
    data          Symbol resolution and data download (Yahoo Finance)
    exchange      NSE and BSE filings: quarterly results XBRL, results meetings, shareholding
    indicators    Technical indicators (pure pandas, no network)
    fundamentals  Annual and quarterly tables, ratios, historical multiples
    peers         Curated NSE peer groups and sector indices
    valuation     Target price: relative multiple, DCF or justified P/B, consensus
    scoring       Six-pillar scorecard and the Buy / Hold / Sell rule
    narrative     Data-backed positives, concerns and summary text
    charts        Matplotlib exhibits saved as PNG
    report        Self-contained HTML research note and optional PDF
    pipeline      Orchestration used by scripts/analyse.py
"""

__version__ = "1.2.0"
