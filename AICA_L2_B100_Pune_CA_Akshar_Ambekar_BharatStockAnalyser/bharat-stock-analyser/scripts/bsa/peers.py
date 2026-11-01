"""Curated NSE peer groups, sector indices and common-name aliases.

Symbols were checked against Yahoo Finance on 1 November 2026. Symbols change after
mergers and demergers, so the pipeline drops any peer that returns no data.
"""

from __future__ import annotations

# group name -> (sector index ticker or None, sector index label or None, NSE symbols)
PEER_GROUPS: dict[str, tuple[str | None, str | None, list[str]]] = {
    "IT Services": ("^CNXIT", "Nifty IT",
                    ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "PERSISTENT", "COFORGE", "MPHASIS"]),
    "Private Banks": ("^NSEBANK", "Nifty Bank",
                      ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "IDFCFIRSTB", "FEDERALBNK"]),
    "PSU Banks": ("^CNXPSUBANK", "Nifty PSU Bank",
                  ["SBIN", "BANKBARODA", "PNB", "CANBK", "UNIONBANK", "INDIANB"]),
    "NBFC and Lenders": ("NIFTY_FIN_SERVICE.NS", "Nifty Financial Services",
                         ["BAJFINANCE", "BAJAJFINSV", "SHRIRAMFIN", "CHOLAFIN", "MUTHOOTFIN", "LICHSGFIN",
                          "PFC", "RECLTD"]),
    "Insurance": ("NIFTY_FIN_SERVICE.NS", "Nifty Financial Services",
                  ["SBILIFE", "HDFCLIFE", "ICICIPRULI", "LICI", "ICICIGI"]),
    "Capital Markets": ("NIFTY_FIN_SERVICE.NS", "Nifty Financial Services",
                        ["BSE", "MCX", "CDSL", "ANGELONE", "HDFCAMC", "CAMS"]),
    "Metals and Mining": ("^CNXMETAL", "Nifty Metal",
                          ["TATASTEEL", "JSWSTEEL", "JINDALSTEL", "SAIL", "HINDALCO", "VEDL", "NMDC",
                           "NATIONALUM", "COALINDIA"]),
    "Automobiles": ("^CNXAUTO", "Nifty Auto",
                    ["MARUTI", "M&M", "TMPV", "TMCV", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO", "TVSMOTOR",
                     "ASHOKLEY"]),
    "FMCG": ("^CNXFMCG", "Nifty FMCG",
             ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR", "GODREJCP", "MARICO", "TATACONSUM",
              "COLPAL"]),
    "Pharmaceuticals": ("^CNXPHARMA", "Nifty Pharma",
                        ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN", "AUROPHARMA", "TORNTPHARM",
                         "ZYDUSLIFE", "MANKIND"]),
    "Hospitals": ("^CNXPHARMA", "Nifty Pharma", ["APOLLOHOSP", "MAXHEALTH", "FORTIS"]),
    "Cement": ("^CNXINFRA", "Nifty Infrastructure",
               ["ULTRACEMCO", "AMBUJACEM", "SHREECEM", "ACC", "DALBHARAT", "JKCEMENT"]),
    "Oil and Gas": ("^CNXENERGY", "Nifty Energy",
                    ["RELIANCE", "ONGC", "BPCL", "IOC", "HINDPETRO", "GAIL", "OIL"]),
    "Power and Utilities": ("^CNXENERGY", "Nifty Energy",
                            ["NTPC", "POWERGRID", "TATAPOWER", "ADANIPOWER", "JSWENERGY", "NHPC", "ADANIGREEN"]),
    "Telecom": ("^CNXINFRA", "Nifty Infrastructure", ["BHARTIARTL", "INDUSTOWER", "IDEA"]),
    "Capital Goods and Defence": ("^CNXINFRA", "Nifty Infrastructure",
                                  ["LT", "SIEMENS", "ABB", "BEL", "HAL", "BHEL", "CGPOWER", "CUMMINSIND"]),
    "Consumer Durables and Paints": ("^CNXCONSUM", "Nifty India Consumption",
                                     ["ASIANPAINT", "BERGEPAINT", "PIDILITIND", "TITAN", "HAVELLS", "VOLTAS"]),
    # Contract electronics makers. There is no Nifty sector index for this group.
    "Electronics Manufacturing Services": (None, None,
                                           ["DIXON", "KAYNES", "SYRMA", "AMBER", "PGEL", "AVALON", "CYIENTDLM"]),
    "Retail and Internet": ("^CNXCONSUM", "Nifty India Consumption",
                            ["DMART", "TRENT", "ETERNAL", "SWIGGY", "NYKAA", "PAYTM", "NAUKRI", "POLICYBZR"]),
    "Real Estate": ("^CNXREALTY", "Nifty Realty",
                    ["DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "LODHA"]),
    "Ports and Logistics": ("^CNXINFRA", "Nifty Infrastructure", ["ADANIPORTS", "CONCOR", "ADANIENT"]),
    "Chemicals and Agro": ("^CNXCONSUM", "Nifty India Consumption",
                           ["SRF", "DEEPAKNTR", "PIIND", "UPL"]),
}

# Yahoo 'industry' text -> peer group, used when a stock is not in any curated group.
INDUSTRY_TO_GROUP: dict[str, str] = {
    "Information Technology Services": "IT Services",
    "Software - Application": "IT Services",
    "Software - Infrastructure": "IT Services",
    "Banks - Regional": "Private Banks",
    "Banks - Diversified": "Private Banks",
    "Credit Services": "NBFC and Lenders",
    "Mortgage Finance": "NBFC and Lenders",
    "Financial Conglomerates": "NBFC and Lenders",
    "Insurance - Life": "Insurance",
    "Insurance - Diversified": "Insurance",
    "Insurance - Property & Casualty": "Insurance",
    "Capital Markets": "Capital Markets",
    "Asset Management": "Capital Markets",
    "Financial Data & Stock Exchanges": "Capital Markets",
    "Steel": "Metals and Mining",
    "Aluminum": "Metals and Mining",
    "Copper": "Metals and Mining",
    "Other Industrial Metals & Mining": "Metals and Mining",
    "Thermal Coal": "Metals and Mining",
    "Auto Manufacturers": "Automobiles",
    "Auto Parts": "Automobiles",
    "Farm & Heavy Construction Machinery": "Automobiles",
    "Household & Personal Products": "FMCG",
    "Packaged Foods": "FMCG",
    "Tobacco": "FMCG",
    "Beverages - Non-Alcoholic": "FMCG",
    "Confectioners": "FMCG",
    "Drug Manufacturers - Specialty & Generic": "Pharmaceuticals",
    "Drug Manufacturers - General": "Pharmaceuticals",
    "Biotechnology": "Pharmaceuticals",
    "Medical Care Facilities": "Hospitals",
    "Building Materials": "Cement",
    "Oil & Gas Refining & Marketing": "Oil and Gas",
    "Oil & Gas Integrated": "Oil and Gas",
    "Oil & Gas E&P": "Oil and Gas",
    "Utilities - Regulated Gas": "Oil and Gas",
    "Utilities - Independent Power Producers": "Power and Utilities",
    "Utilities - Regulated Electric": "Power and Utilities",
    "Utilities - Renewable": "Power and Utilities",
    "Utilities - Diversified": "Power and Utilities",
    "Telecom Services": "Telecom",
    "Engineering & Construction": "Capital Goods and Defence",
    "Specialty Industrial Machinery": "Capital Goods and Defence",
    "Aerospace & Defense": "Capital Goods and Defence",
    "Electrical Equipment & Parts": "Capital Goods and Defence",
    "Specialty Chemicals": "Chemicals and Agro",
    "Agricultural Inputs": "Chemicals and Agro",
    "Chemicals": "Chemicals and Agro",
    "Furnishings, Fixtures & Appliances": "Consumer Durables and Paints",
    "Luxury Goods": "Consumer Durables and Paints",
    "Consumer Electronics": "Consumer Durables and Paints",
    "Electronic Components": "Electronics Manufacturing Services",
    "Contract Manufacturers": "Electronics Manufacturing Services",
    "Internet Retail": "Retail and Internet",
    "Specialty Retail": "Retail and Internet",
    "Department Stores": "Retail and Internet",
    "Grocery Stores": "Retail and Internet",
    "Internet Content & Information": "Retail and Internet",
    "Real Estate - Development": "Real Estate",
    "Real Estate - Diversified": "Real Estate",
    "Marine Shipping": "Ports and Logistics",
    "Integrated Freight & Logistics": "Ports and Logistics",
    "Conglomerates": "Ports and Logistics",
}

# Common names and old names that Yahoo search does not resolve well.
ALIASES: dict[str, str] = {
    "sbi": "SBIN", "state bank": "SBIN", "state bank of india": "SBIN",
    "l&t": "LT", "larsen": "LT", "larsen and toubro": "LT", "larsen & toubro": "LT",
    "m&m": "M&M", "mahindra": "M&M", "mahindra and mahindra": "M&M",
    "hul": "HINDUNILVR", "hindustan unilever": "HINDUNILVR",
    "airtel": "BHARTIARTL", "bharti airtel": "BHARTIARTL",
    "zomato": "ETERNAL", "eternal": "ETERNAL",
    "tata motors": "TMPV", "tata motors pv": "TMPV", "tata motors cv": "TMCV",
    "maruti": "MARUTI", "maruti suzuki": "MARUTI",
    "kotak": "KOTAKBANK", "kotak bank": "KOTAKBANK", "kotak mahindra bank": "KOTAKBANK",
    "icici": "ICICIBANK", "icici bank": "ICICIBANK", "axis": "AXISBANK", "axis bank": "AXISBANK",
    "hdfc": "HDFCBANK", "hdfc bank": "HDFCBANK", "indusind": "INDUSINDBK",
    "asian paints": "ASIANPAINT", "sun pharma": "SUNPHARMA", "dr reddy": "DRREDDY", "dr reddys": "DRREDDY",
    "hcl": "HCLTECH", "hcl tech": "HCLTECH", "tech mahindra": "TECHM",
    "ultratech": "ULTRACEMCO", "ultratech cement": "ULTRACEMCO", "power grid": "POWERGRID",
    "adani ports": "ADANIPORTS", "adani enterprises": "ADANIENT", "bajaj auto": "BAJAJ-AUTO",
    "hero": "HEROMOTOCO", "hero motocorp": "HEROMOTOCO", "nestle": "NESTLEIND", "nestle india": "NESTLEIND",
    "jsw steel": "JSWSTEEL", "coal india": "COALINDIA", "ioc": "IOC", "indian oil": "IOC",
    "dmart": "DMART", "avenue supermarts": "DMART", "naukri": "NAUKRI", "info edge": "NAUKRI",
    "paytm": "PAYTM", "policybazaar": "POLICYBZR", "lic": "LICI", "hal": "HAL", "bel": "BEL",
    "tcs": "TCS", "infosys": "INFY", "wipro": "WIPRO", "itc": "ITC", "reliance": "RELIANCE",
    "tata steel": "TATASTEEL", "tata power": "TATAPOWER", "tata consumer": "TATACONSUM",
    "bajaj finance": "BAJFINANCE", "bajaj finserv": "BAJAJFINSV", "titan": "TITAN",
}

BENCHMARK = ("^NSEI", "Nifty 50")
SENSEX = ("^BSESN", "Sensex")


def group_for(symbol_base: str, industry: str | None) -> str | None:
    """Return the peer group for an NSE base symbol (without .NS)."""
    for name, (_, _, members) in PEER_GROUPS.items():
        if symbol_base in members:
            return name
    if industry and industry in INDUSTRY_TO_GROUP:
        return INDUSTRY_TO_GROUP[industry]
    return None


def peers_for(symbol_base: str, group: str | None, limit: int = 6) -> list[str]:
    if not group or group not in PEER_GROUPS:
        return []
    return [s for s in PEER_GROUPS[group][2] if s != symbol_base][:limit]


def sector_index_for(group: str | None) -> tuple[str, str] | None:
    if not group or group not in PEER_GROUPS:
        return None
    ticker, label, _ = PEER_GROUPS[group]
    return (ticker, label) if ticker else None
