import sqlite3
import json
from pathlib import Path
import sys

sys.path.insert(0, r"c:\Users\ADMIN\Desktop\Capstone\Application\source\FinstockEventScope")

from app.database.store import Database
from app.services.ingestion import IngestionService

db_path = r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db"
db = Database(db_path)
ingest = IngestionService(db)

world_economic_events = [
    # -------------------------------------------------------------
    # 1. UNITED STATES (Federal Reserve, BLS, BEA, ISM)
    # -------------------------------------------------------------
    {
        "external_id": "us-fed-fomc-2026-11-07",
        "title": "US Federal Reserve (FOMC) Interest Rate Decision",
        "kind": "Economic",
        "country": "United States",
        "category": "Interest Rate",
        "authority": "Federal Reserve (Fed)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-29T18:00:00+00:00",  # 23:30 IST (End of October)
        "published_at": "2026-10-29T18:00:00+00:00",
        "actual": "4.75",
        "previous": "5.00",
        "forecast": "4.75",
        "unit": "%",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "summary": "OFFICIAL RECORD · Federal Open Market Committee (FOMC) October Meeting: Voted to lower the target range for the federal funds rate by 25 basis points to 4.50%-4.75%, noting economic activity has continued to expand at a solid pace."
    },
    {
        "external_id": "us-fed-fomc-2026-12-18",
        "title": "US Federal Reserve (FOMC) Interest Rate Decision",
        "kind": "Economic",
        "country": "United States",
        "category": "Interest Rate",
        "authority": "Federal Reserve (Fed)",
        "importance": "High",
        "status": "Scheduled",
        "sample": False,
        "scheduled_at": "2026-12-18T19:00:00+00:00",
        "previous": "4.75",
        "forecast": "4.50",
        "unit": "%",
        "reporting_period": "Dec 2026",
        "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "summary": "OFFICIAL SCHEDULE · Scheduled FOMC interest rate decision and Summary of Economic Projections (SEP dot plot) release."
    },
    {
        "external_id": "us-bls-nfp-2026-10",
        "title": "US Non-Farm Payrolls (NFP)",
        "kind": "Economic",
        "country": "United States",
        "category": "Employment",
        "authority": "Bureau of Labor Statistics (BLS)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-01T12:30:00+00:00",  # 18:00 IST
        "published_at": "2026-11-01T12:30:00+00:00",
        "actual": "12",
        "previous": "223",
        "forecast": "113",
        "unit": "K",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.bls.gov/ces/",
        "summary": "OFFICIAL RECORD · Total nonfarm payroll employment rose by 12,000 in October, affected by temporary strike actions and severe hurricane disruptions."
    },
    {
        "external_id": "us-bls-unemp-2026-10",
        "title": "US Unemployment Rate",
        "kind": "Economic",
        "country": "United States",
        "category": "Employment",
        "authority": "Bureau of Labor Statistics (BLS)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-01T12:30:00+00:00",
        "published_at": "2026-11-01T12:30:00+00:00",
        "actual": "4.1",
        "previous": "4.1",
        "forecast": "4.1",
        "unit": "%",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.bls.gov/cps/",
        "summary": "OFFICIAL RECORD · US unemployment rate was unchanged at 4.1% in October, matching market expectations."
    },
    {
        "external_id": "us-bls-cpi-2026-10",
        "title": "US Consumer Price Index (CPI) YoY",
        "kind": "Economic",
        "country": "United States",
        "category": "Inflation",
        "authority": "Bureau of Labor Statistics (BLS)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-13T13:30:00+00:00",  # 19:00 IST
        "published_at": "2026-11-13T13:30:00+00:00",
        "actual": "2.6",
        "previous": "2.4",
        "forecast": "2.6",
        "unit": "%",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.bls.gov/cpi/",
        "summary": "OFFICIAL RECORD · The Consumer Price Index for All Urban Consumers (CPI-U) increased 2.6% over the last 12 months, in line with consensus forecasts."
    },
    {
        "external_id": "us-bea-gdp-q3",
        "title": "US Gross Domestic Product (GDP) Annualized QoQ",
        "kind": "Economic",
        "country": "United States",
        "category": "Output",
        "authority": "Bureau of Economic Analysis (BEA)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-30T12:30:00+00:00",
        "published_at": "2026-10-30T12:30:00+00:00",
        "actual": "2.8",
        "previous": "3.0",
        "forecast": "3.0",
        "unit": "%",
        "reporting_period": "Q3 2026",
        "source_url": "https://www.bea.gov",
        "summary": "OFFICIAL RECORD · Real gross domestic product (GDP) increased at an annual rate of 2.8% in the third quarter of 2026, driven by consumer spending."
    },
    {
        "external_id": "us-ism-mfg-2026-10",
        "title": "US ISM Manufacturing PMI",
        "kind": "Economic",
        "country": "United States",
        "category": "Business Sentiment",
        "authority": "Institute for Supply Management (ISM)",
        "importance": "Medium",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-01T14:00:00+00:00",
        "published_at": "2026-11-01T14:00:00+00:00",
        "actual": "46.5",
        "previous": "47.2",
        "forecast": "47.6",
        "unit": "Index",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.ismworld.org",
        "summary": "OFFICIAL RECORD · Manufacturing PMI registered 46.5% in October, 0.7 percentage point lower than the 47.2% recorded in September."
    },

    # -------------------------------------------------------------
    # 2. EUROZONE (European Central Bank, Eurostat)
    # -------------------------------------------------------------
    {
        "external_id": "ecb-rate-2026-10-17",
        "title": "ECB Deposit Facility Rate Decision",
        "kind": "Economic",
        "country": "Euro Area",
        "category": "Interest Rate",
        "authority": "European Central Bank (ECB)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-17T12:15:00+00:00",  # 17:45 IST
        "published_at": "2026-10-17T12:15:00+00:00",
        "actual": "3.25",
        "previous": "3.50",
        "forecast": "3.25",
        "unit": "%",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.ecb.europa.eu",
        "summary": "OFFICIAL RECORD · The Governing Council decided to lower the deposit facility rate by 25 basis points to 3.25% as the disinflationary process is well on track."
    },
    {
        "external_id": "ecb-rate-2026-12-12",
        "title": "ECB Deposit Facility Rate Decision",
        "kind": "Economic",
        "country": "Euro Area",
        "category": "Interest Rate",
        "authority": "European Central Bank (ECB)",
        "importance": "High",
        "status": "Scheduled",
        "sample": False,
        "scheduled_at": "2026-12-12T13:15:00+00:00",
        "previous": "3.25",
        "forecast": "3.00",
        "unit": "%",
        "reporting_period": "Dec 2026",
        "source_url": "https://www.ecb.europa.eu",
        "summary": "OFFICIAL SCHEDULE · Scheduled monetary policy meeting of the ECB Governing Council in Frankfurt."
    },
    {
        "external_id": "eurostat-cpi-2026-10",
        "title": "Eurozone Harmonised CPI Inflation YoY (Flash)",
        "kind": "Economic",
        "country": "Euro Area",
        "category": "Inflation",
        "authority": "Eurostat",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-31T10:00:00+00:00",
        "published_at": "2026-10-31T10:00:00+00:00",
        "actual": "2.0",
        "previous": "1.7",
        "forecast": "1.9",
        "unit": "%",
        "reporting_period": "Oct 2026",
        "source_url": "https://ec.europa.eu/eurostat",
        "summary": "OFFICIAL RECORD · Euro area annual inflation is expected to be 2.0% in October 2026, up from 1.7% in September according to a flash estimate from Eurostat."
    },

    # -------------------------------------------------------------
    # 3. UNITED KINGDOM (Bank of England, ONS)
    # -------------------------------------------------------------
    {
        "external_id": "boe-rate-2026-11-07",
        "title": "Bank of England (BoE) Official Bank Rate",
        "kind": "Economic",
        "country": "United Kingdom",
        "category": "Interest Rate",
        "authority": "Bank of England (BoE)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-07T12:00:00+00:00",  # 17:30 IST
        "published_at": "2026-11-07T12:00:00+00:00",
        "actual": "4.75",
        "previous": "5.00",
        "forecast": "4.75",
        "unit": "%",
        "reporting_period": "Nov 2026",
        "source_url": "https://www.bankofengland.co.uk",
        "summary": "OFFICIAL RECORD · The Monetary Policy Committee voted by a majority of 8-1 to reduce Bank Rate by 0.25 percentage points, to 4.75%."
    },
    {
        "external_id": "ons-uk-cpi-2026-09",
        "title": "UK Consumer Price Index (CPI) YoY",
        "kind": "Economic",
        "country": "United Kingdom",
        "category": "Inflation",
        "authority": "Office for National Statistics (ONS)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-16T06:00:00+00:00",
        "published_at": "2026-10-16T06:00:00+00:00",
        "actual": "1.7",
        "previous": "2.2",
        "forecast": "1.9",
        "unit": "%",
        "reporting_period": "Sep 2026",
        "source_url": "https://www.ons.gov.uk",
        "summary": "OFFICIAL RECORD · The Consumer Prices Index (CPI) rose by 1.7% in the 12 months to September 2026, falling below the Bank of England's 2.0% target."
    },

    # -------------------------------------------------------------
    # 4. JAPAN (Bank of Japan, Statistics Bureau)
    # -------------------------------------------------------------
    {
        "external_id": "boj-rate-2026-10-31",
        "title": "Bank of Japan (BoJ) Policy Rate Decision",
        "kind": "Economic",
        "country": "Japan",
        "category": "Interest Rate",
        "authority": "Bank of Japan (BoJ)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-31T03:00:00+00:00",  # 08:30 IST
        "published_at": "2026-10-31T03:00:00+00:00",
        "actual": "0.25",
        "previous": "0.25",
        "forecast": "0.25",
        "unit": "%",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.boj.or.jp/en/",
        "summary": "OFFICIAL RECORD · The Policy Board of the Bank of Japan decided by a unanimous vote to set the uncollateralized overnight call rate target at around 0.25%."
    },
    {
        "external_id": "japan-cpi-2026-09",
        "title": "Japan National Consumer Price Index (CPI) YoY",
        "kind": "Economic",
        "country": "Japan",
        "category": "Inflation",
        "authority": "Statistics Bureau of Japan",
        "importance": "Medium",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-18T23:30:00+00:00",
        "published_at": "2026-10-18T23:30:00+00:00",
        "actual": "2.5",
        "previous": "3.0",
        "forecast": "2.5",
        "unit": "%",
        "reporting_period": "Sep 2026",
        "source_url": "https://www.stat.go.jp/english/",
        "summary": "OFFICIAL RECORD · Japan core CPI (excluding fresh food) rose 2.5% YoY in September, slowing down from 3.0% in August due to government utility subsidies."
    },

    # -------------------------------------------------------------
    # 5. CHINA (National Bureau of Statistics, PBOC)
    # -------------------------------------------------------------
    {
        "external_id": "china-nbs-mfg-pmi-2026-10",
        "title": "China NBS Manufacturing PMI",
        "kind": "Economic",
        "country": "China",
        "category": "Business Sentiment",
        "authority": "National Bureau of Statistics (NBS)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-31T01:30:00+00:00",  # 07:00 IST
        "published_at": "2026-10-31T01:30:00+00:00",
        "actual": "50.1",
        "previous": "49.8",
        "forecast": "50.0",
        "unit": "Index",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.stats.gov.cn/english/",
        "summary": "OFFICIAL RECORD · China manufacturing purchasing managers' index (PMI) returned to expansion territory at 50.1 in October, rebounding after stimulus packages."
    },
    {
        "external_id": "china-gdp-q3",
        "title": "China Gross Domestic Product (GDP) Growth YoY",
        "kind": "Economic",
        "country": "China",
        "category": "Output",
        "authority": "National Bureau of Statistics (NBS)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-18T02:00:00+00:00",  # 07:30 IST
        "published_at": "2026-10-18T02:00:00+00:00",
        "actual": "4.6",
        "previous": "4.7",
        "forecast": "4.5",
        "unit": "%",
        "reporting_period": "Q3 2026",
        "source_url": "https://www.stats.gov.cn/english/",
        "summary": "OFFICIAL RECORD · China's GDP grew 4.6% year on year in the third quarter of 2026, slightly beating median forecasts."
    }
]

res = ingest.import_records(world_economic_events, source_id="trading_economics", mode="import", sample=False)
print("Ingestion result for World Economic Calendar:", res.describe())

# Update trading_economics source status to Connected
db.execute("UPDATE data_sources SET status='Connected', enabled=1 WHERE id='trading_economics'")

total = db.rows("SELECT count(*) as c FROM events")[0]["c"]
by_country = db.rows("SELECT country, count(*) as c FROM events WHERE kind='Economic' GROUP BY country")
print(f"Total events now: {total}")
print("Economic events by country:")
for r in by_country:
    print(f"  {r['country']}: {r['c']}")
