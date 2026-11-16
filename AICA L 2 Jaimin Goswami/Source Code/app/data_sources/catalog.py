import json

SOURCES = [
    dict(
        id="trading_economics",
        name="Trading Economics · licensed calendar",
        adapter="trading_economics",
        kind="Economic",
        authority="Trading Economics",
        url="https://api.tradingeconomics.com",
        terms_url="https://tradingeconomics.com/analytics/api.aspx",
        rights_note="User subscription and display/storage entitlement required. API integration must be verified with your credentials.",
        config={"countries": "india,united states,united kingdom,euro area,china,japan,australia", "days_back": 7, "days_ahead": 30}
    ),
    dict(
        id="finnhub",
        name="Finnhub · free global economic calendar",
        adapter="finnhub",
        kind="Economic",
        authority="Finnhub API",
        country="Global",
        url="https://finnhub.io/api/v1/calendar/economic",
        terms_url="https://finnhub.io/terms-of-service",
        rights_note="Free tier provides real-time macroeconomic releases, consensus estimates, and previous readings (60 calls/min). Get a free API key at finnhub.io.",
        config={"days_back": 7, "days_ahead": 30}
    ),
    dict(
        id="sebi",
        name="SEBI · official RSS",
        adapter="rss",
        kind="Regulatory",
        authority="SEBI",
        country="India",
        url="https://www.sebi.gov.in/sebirss.xml",
        terms_url="https://www.sebi.gov.in/website-policy.html",
        rights_note="Official RSS for personal feed reading. SEBI reproduction/redistribution requires permission. Only feed metadata is ingested; linked documents are not copied."
    ),
    dict(
        id="rbi_press",
        name="RBI · press releases",
        adapter="rss",
        kind="Regulatory",
        authority="RBI",
        country="India",
        url="https://rbi.org.in/pressreleases_rss.xml",
        terms_url="https://www.rbi.org.in/Scripts/rss.aspx",
        rights_note="Official RSS metadata. Review applicable RBI content terms before redistribution."
    ),
    dict(
        id="rbi_notifications",
        name="RBI · notifications",
        adapter="rss",
        kind="Regulatory",
        authority="RBI",
        country="India",
        url="https://rbi.org.in/notifications_rss.xml",
        terms_url="https://www.rbi.org.in/Scripts/rss.aspx",
        rights_note="Official RSS metadata; not a complete historic or MPC schedule feed."
    ),
    dict(
        id="nse_announcements",
        name="NSE · corporate RSS",
        adapter="rss",
        kind="Corporate",
        authority="NSE",
        country="India",
        url="https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
        terms_url="https://www.nseindia.com/static/market-data/nse-data-policy",
        rights_note="Official RSS. Commercial storage/distribution needs appropriate NSE terms. RSS does not establish complete company/history coverage."
    ),
    dict(
        id="nse_circulars",
        name="NSE · exchange circulars",
        adapter="rss",
        kind="Regulatory",
        authority="NSE",
        country="India",
        url="https://nsearchives.nseindia.com/content/RSS/Circulars.xml",
        terms_url="https://www.nseindia.com/static/rss-feed",
        rights_note="Official RSS metadata. Review applicable usage/retention rights."
    ),
    dict(
        id="bse_import",
        name="BSE · authorized corporate / notice import",
        adapter="import",
        kind="Corporate",
        authority="BSE",
        country="India",
        terms_url="https://marketdata.bseindia.com/",
        rights_note="No verified accessible feed is bundled. Import authorized CSV/JSON exports. A paid delivery endpoint requires your agreement and documentation."
    ),
    dict(
        id="india_official_import",
        name="MoSPI / DPIIT / Finance · authorized import",
        adapter="import",
        kind="Economic",
        country="India",
        terms_url="https://esankhyiki.mospi.gov.in/",
        rights_note="Official downloads or authorized exports using the documented CSV/JSON schema. No unverified API endpoint is used."
    ),
    dict(
        id="manual",
        name="Authorized file imports",
        adapter="import",
        rights_note="Importer is responsible for permission and truthful source references."
    ),
    dict(
        id="demo",
        name="Synthetic demonstration library",
        adapter="import",
        rights_note="Entirely synthetic test examples. Not real financial releases or filings."
    ),
]


def seed_sources(db):
    for source in SOURCES:
        db.execute(
            "INSERT OR IGNORE INTO data_sources(id, name, adapter, url, kind, authority, country, terms_url, rights_note, config) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                source["id"],
                source["name"],
                source["adapter"],
                source.get("url", ""),
                source.get("kind", "Regulatory"),
                source.get("authority", ""),
                source.get("country", ""),
                source.get("terms_url", ""),
                source["rights_note"],
                json.dumps(source.get("config", {}))
            )
        )
