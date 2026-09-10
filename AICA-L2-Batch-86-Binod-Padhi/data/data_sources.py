"""
data/data_sources.py

Registry describing the market-data sources this application is designed
to work with, and how data actually gets in.

DESIGN DECISION: This application does NOT implement automated scraping
of MagicBricks, Housing.com, 99acres or similar portals. Those sites
generally restrict automated access in their Terms of Service and/or use
CAPTCHA/anti-bot protections. Bypassing such protections is out of scope
and against this project's policy (see spec: "Do not bypass CAPTCHA,
login restrictions, anti-bot systems, paywalls").

Instead:
  1. If a source publishes an official, documented REST API or a bulk
     data/report download (e.g. NHB RESIDEX publishes periodic index
     reports; Numbeo has a documented paid API), a fetcher can be added
     under this module using `requests` against that *documented* endpoint.
  2. For everything else, the supported path is manual export from the
     portal (most portals let a logged-in user download/view their own
     search results) followed by CSV/Excel/JSON import via
     data/importer.py.

Each SOURCE_REGISTRY entry documents what kind of access is used, so the
GUI's "Update Market Data" screen can show the user why a given source is
"Manual import only" versus "API available".
"""

SOURCE_REGISTRY = {
    "MagicBricks": {
        "url": "https://www.magicbricks.com",
        "access_method": "manual_import",
        "notes": "No public bulk API; use MagicBricks' own search/export and import via CSV.",
    },
    "Housing.com": {
        "url": "https://housing.com",
        "access_method": "manual_import",
        "notes": "No public bulk API; import listings manually.",
    },
    "99acres": {
        "url": "https://www.99acres.com",
        "access_method": "manual_import",
        "notes": "No public bulk API; import listings manually.",
    },
    "NHB RESIDEX": {
        "url": "https://www.nhbresidex.org.in",
        "access_method": "manual_report_download",
        "notes": "Publishes periodic city-level House Price Index reports (PDF/Excel) — "
                 "download the published report and import the relevant table.",
    },
    "Numbeo": {
        "url": "https://www.numbeo.com",
        "access_method": "api_documented_paid",
        "notes": "Numbeo offers a documented API under a paid plan. If the user has an API "
                 "key, a fetcher can be added here calling Numbeo's documented endpoints. "
                 "No key is bundled with this application.",
    },
}


def get_access_method(source_name: str) -> str:
    entry = SOURCE_REGISTRY.get(source_name)
    return entry["access_method"] if entry else "manual_import"


def list_sources():
    return [{"name": k, **v} for k, v in SOURCE_REGISTRY.items()]


def fetch_numbeo(api_key: str, city: str):
    """
    Placeholder for a documented, ToS-compliant Numbeo API call.
    Not implemented by default (requires the user's own paid API key).
    Raises NotImplementedError until an API key + endpoint are configured
    by the user in Settings, at which point `requests` can be used here
    against Numbeo's documented REST endpoint.
    """
    raise NotImplementedError(
        "Numbeo API integration requires a user-supplied API key configured in "
        "Settings. Once configured, implement the documented REST call here."
    )
