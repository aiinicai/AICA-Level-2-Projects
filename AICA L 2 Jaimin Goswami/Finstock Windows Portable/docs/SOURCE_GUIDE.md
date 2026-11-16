# Source configuration and evidence

Reviewed and locally tested on 13 November 2026. See source-probe.json and live-source-test-report.json for actual HTTP/adapter outcomes. These are dated observations, not future availability guarantees. No access controls, CAPTCHA or private website endpoints are bypassed.

## Official RSS adapters

| Source | Documented endpoint | Role / limits |
|---|---|---|
| SEBI | https://www.sebi.gov.in/sebirss.xml | Recent press releases, circulars, orders/rulings. Date-only publication strings observed. |
| RBI press | https://rbi.org.in/pressreleases_rss.xml | Recent press releases; observed timestamps omit offset. |
| RBI notifications | https://rbi.org.in/notifications_rss.xml | Recent notifications; observed timestamps omit offset. |
| NSE announcements | https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml | Issuer in title, filing subject in description; some entries omit filing URL. Exact timezone not established by the observed raw timestamps. |
| NSE circulars | https://nsearchives.nseindia.com/content/RSS/Circulars.xml | Recent circulars; observed timestamps use midnight placeholders. |

Official directories: https://www.sebi.gov.in/rss.html ; https://www.rbi.org.in/Scripts/rss.aspx ; https://www.nseindia.com/static/rss-feed .

Enable each feed in Sources & Settings after reviewing your usage rights. The default interval is 15 minutes and can be changed. No published numeric RSS quota or complete-history SLA was verified. Conditional HTTP requests are used when ETag/Last-Modified is supplied. Failed checks retain old data and last success; retries use bounded backoff and respect Retry-After. Initial synchronization suppresses publication alerts.

Only RSS metadata is ingested. RBI body HTML is not treated as structured facts or copied into explanatory articles. NSE's explicitly supplied filing subject is preserved. Unknown importance remains Unknown. Categories are application rules, identified as such.

For missing offsets, EventScope retains the raw source timestamp and shows a date-only value. It does not assume IST from the publisher's location. For a missing individual filing URL, the source reference points to the actual feed and is explicitly labelled “filing link unavailable.” No fictional document link is created.

RSS windows are finite: prolonged offline periods may produce unrecoverable gaps. Comprehensive coverage, low-latency commitments and historic backfill require a licensed delivery product or authorized export.

## Trading Economics

API documentation: https://docs.tradingeconomics.com/economic_calendar/country/ . Pricing/access: https://tradingeconomics.com/analytics/api.aspx . Limits: https://docs.tradingeconomics.com/get_started/rate-limits/ .

The adapter uses the documented country/date-range calendar endpoint. Enter the provider credential in the application (Windows Credential Manager), or set TRADING_ECONOMICS_API_KEY in the process environment. Nothing is embedded in the executable. Configure country names and a rolling past/future range. Changing range/countries resets the initial-sync checkpoint to avoid historical alert flooding.

Current implementation partitions capped results into date windows and refuses a single day that still reaches the provider's 1,000-row cap. Country calls are spaced. HTTP 401/403 becomes Restricted; missing credentials stays Not Configured. A changed entitlement can limit data even when an HTTP request succeeds: inspect coverage and the provider's agreement.

The calendar adapter is covered by deterministic tests. No authenticated Trading Economics call has been made because credentials were not supplied. Subscription price, rights to cache observations/consensus, commercial display, derived summaries and redistribution require the user's agreement. Provider LastUpdate is retained as an update timestamp, never fabricated as actual publication time. Forecast and TEForecast remain separate.

## BSE and Indian economic/fiscal sources

BSE's official corporate-data product is documented at https://marketdata.bseindia.com/ and https://www.bseindia.com/downloads1/Information_Products_Pricing_Sheet.pdf . No verified accessible production feed is bundled; use the BSE authorized-import source for corporate disclosures and regulatory notices. A future contracted adapter needs the supplier's actual delivery specification and rights. No reverse-engineered BSE endpoint is used.

MoSPI/eSankhyiki: https://esankhyiki.mospi.gov.in/ ; release schedule: https://mospi.gov.in/advance-release-calendar . DPIIT/OEA: https://eaindustry.nic.in/ . India Budget: https://www.indiabudget.gov.in/ . These are source/reference locations, not automatically configured APIs. Import authorized exports using IMPORT_FORMAT.md. Preserve publisher, period, unit/base year and date precision.

## Rights and retention

NSE: https://www.nseindia.com/static/market-data/nse-data-policy . SEBI: https://www.sebi.gov.in/website-policy.html . India Budget: https://www.indiabudget.gov.in/website-policies.php . PIB: https://www.pib.gov.in/content/102_2_Copyright-Policy.aspx?lang=1&reg=30 .

Public website access is not a blanket commercial storage or redistribution licence. SEBI reproduction needs permission under its stated policy. The India Budget site has its own permission requirements. PIB's reuse conditions have attribution and third-party exceptions. Check the particular RBI/MoSPI/OEA dataset/document terms. Disabling a source stops fetching; it does not automatically erase the user's history. Retention compliance remains the operator's responsibility.

No other channel, paid provider subscription, cloud service or public redistribution is implied by this application.

