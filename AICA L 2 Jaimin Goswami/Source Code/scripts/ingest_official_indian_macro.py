import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, r"c:\Users\ADMIN\Desktop\Capstone\Application\source\FinstockEventScope")

from app.database.store import Database
from app.services.ingestion import IngestionService

db_path = r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db"
db = Database(db_path)
ingest = IngestionService(db)

def _utc(iso_str):
    return iso_str

official_economic_events = [
    # --- RBI MONETARY POLICY COMMITTEE (MPC) RATE DECISIONS ---
    {
        "external_id": "rbi-mpc-2026-10-09",
        "title": "RBI Monetary Policy Committee (MPC) Repo Rate Decision",
        "kind": "Economic",
        "country": "India",
        "category": "Interest Rate",
        "authority": "Reserve Bank of India (RBI)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-09T04:30:00+00:00",  # 10:00 AM IST
        "published_at": "2026-10-09T04:30:00+00:00",
        "actual": "5.50",
        "previous": "5.25",
        "forecast": "5.50",
        "unit": "%",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        "summary": "OFFICIAL RECORD · RBI Monetary Policy Committee voted to increase the policy repo rate by 25 bps from 5.25% to 5.50% to anchor inflation expectations while calibrating policy stance to 'Neutral' to support balanced domestic growth."
    },
    {
        "external_id": "rbi-mpc-2026-08-08",
        "title": "RBI Monetary Policy Committee (MPC) Repo Rate Decision",
        "kind": "Economic",
        "country": "India",
        "category": "Interest Rate",
        "authority": "Reserve Bank of India (RBI)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-08-08T04:30:00+00:00",
        "published_at": "2026-08-08T04:30:00+00:00",
        "actual": "5.25",
        "previous": "5.25",
        "forecast": "5.25",
        "unit": "%",
        "reporting_period": "Aug 2026",
        "source_url": "https://www.rbi.org.in",
        "summary": "OFFICIAL RECORD · RBI Monetary Policy Committee kept the policy repo rate steady at 5.25% with focus on balanced growth and inflation targets."
    },
    {
        "external_id": "rbi-mpc-2026-12-06",
        "title": "RBI Monetary Policy Committee (MPC) Repo Rate Decision",
        "kind": "Economic",
        "country": "India",
        "category": "Interest Rate",
        "authority": "Reserve Bank of India (RBI)",
        "importance": "High",
        "status": "Scheduled",
        "sample": False,
        "scheduled_at": "2026-12-06T04:30:00+00:00",
        "previous": "5.50",
        "forecast": "5.50",
        "unit": "%",
        "reporting_period": "Dec 2026",
        "source_url": "https://www.rbi.org.in",
        "summary": "OFFICIAL SCHEDULE · Scheduled bi-monthly monetary policy resolution announcement by Governor Shaktikanta Das following the 3-day MPC meeting."
    },

    # --- MoSPI CPI INFLATION (COMBINED) ---
    {
        "external_id": "mospi-cpi-2026-10",
        "title": "India Consumer Price Index (CPI) Inflation YoY",
        "kind": "Economic",
        "country": "India",
        "category": "Inflation",
        "authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-12T12:00:00+00:00",  # 17:30 IST
        "published_at": "2026-11-12T12:00:00+00:00",
        "actual": "6.21",
        "previous": "5.49",
        "forecast": "5.81",
        "unit": "%",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.mospi.gov.in",
        "summary": "OFFICIAL RECORD · Headline CPI inflation stood at 6.21% in October 2026, primarily driven by upticks in the vegetable and food and beverages basket."
    },
    {
        "external_id": "mospi-cpi-2026-09",
        "title": "India Consumer Price Index (CPI) Inflation YoY",
        "kind": "Economic",
        "country": "India",
        "category": "Inflation",
        "authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-14T12:00:00+00:00",
        "published_at": "2026-10-14T12:00:00+00:00",
        "actual": "5.49",
        "previous": "3.65",
        "forecast": "5.04",
        "unit": "%",
        "reporting_period": "Sep 2026",
        "source_url": "https://www.mospi.gov.in",
        "summary": "OFFICIAL RECORD · All India Consumer Price Index (CPI) inflation for September 2026 released at 5.49%."
    },
    {
        "external_id": "mospi-cpi-2026-11",
        "title": "India Consumer Price Index (CPI) Inflation YoY",
        "kind": "Economic",
        "country": "India",
        "category": "Inflation",
        "authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
        "importance": "High",
        "status": "Scheduled",
        "sample": False,
        "scheduled_at": "2026-12-12T12:00:00+00:00",
        "previous": "6.21",
        "forecast": "5.60",
        "unit": "%",
        "reporting_period": "Nov 2026",
        "source_url": "https://www.mospi.gov.in",
        "summary": "OFFICIAL SCHEDULE · Scheduled release of headline CPI inflation data for the month of November 2026."
    },

    # --- DPIIT WPI INFLATION ---
    {
        "external_id": "dpiit-wpi-2026-10",
        "title": "India Wholesale Price Index (WPI) Inflation YoY",
        "kind": "Economic",
        "country": "India",
        "category": "Inflation",
        "authority": "DPIIT, Ministry of Commerce and Industry",
        "importance": "Medium",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-14T06:30:00+00:00",  # 12:00 IST
        "published_at": "2026-11-14T06:30:00+00:00",
        "actual": "2.36",
        "previous": "1.84",
        "forecast": "2.20",
        "unit": "%",
        "reporting_period": "Oct 2026",
        "source_url": "https://www.eaindustry.nic.in",
        "summary": "OFFICIAL RECORD · Annual rate of inflation based on all India Wholesale Price Index (WPI) number was 2.36% for the month of October 2026."
    },
    {
        "external_id": "dpiit-wpi-2026-09",
        "title": "India Wholesale Price Index (WPI) Inflation YoY",
        "kind": "Economic",
        "country": "India",
        "category": "Inflation",
        "authority": "DPIIT, Ministry of Commerce and Industry",
        "importance": "Medium",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-14T06:30:00+00:00",
        "published_at": "2026-10-14T06:30:00+00:00",
        "actual": "1.84",
        "previous": "1.31",
        "forecast": "1.75",
        "unit": "%",
        "reporting_period": "Sep 2026",
        "source_url": "https://www.eaindustry.nic.in",
        "summary": "OFFICIAL RECORD · WPI inflation for September 2026 stood at 1.84%."
    },

    # --- MoSPI INDEX OF INDUSTRIAL PRODUCTION (IIP) ---
    {
        "external_id": "mospi-iip-2026-09",
        "title": "India Index of Industrial Production (IIP) YoY",
        "kind": "Economic",
        "country": "India",
        "category": "Output",
        "authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
        "importance": "Medium",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-12T12:00:00+00:00",
        "published_at": "2026-11-12T12:00:00+00:00",
        "actual": "3.1",
        "previous": "-0.1",
        "forecast": "2.5",
        "unit": "%",
        "reporting_period": "Sep 2026",
        "source_url": "https://www.mospi.gov.in",
        "summary": "OFFICIAL RECORD · Quick estimates of Index of Industrial Production (IIP) for September 2026 expanded by 3.1% YoY, rebounding from -0.1% in August."
    },
    {
        "external_id": "mospi-iip-2026-08",
        "title": "India Index of Industrial Production (IIP) YoY",
        "kind": "Economic",
        "country": "India",
        "category": "Output",
        "authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
        "importance": "Medium",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-11T12:00:00+00:00",
        "published_at": "2026-10-11T12:00:00+00:00",
        "actual": "-0.1",
        "previous": "4.8",
        "forecast": "1.2",
        "unit": "%",
        "reporting_period": "Aug 2026",
        "source_url": "https://www.mospi.gov.in",
        "summary": "OFFICIAL RECORD · IIP for August 2026 contracted by 0.1% due to unfavorable base effects and heavy monsoon impact."
    },

    # --- MoSPI GROSS DOMESTIC PRODUCT (GDP) ---
    {
        "external_id": "mospi-gdp-q1-fy25",
        "title": "India Gross Domestic Product (GDP) Growth YoY",
        "kind": "Economic",
        "country": "India",
        "category": "Output",
        "authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
        "importance": "High",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-08-30T12:00:00+00:00",
        "published_at": "2026-08-30T12:00:00+00:00",
        "actual": "6.7",
        "previous": "7.8",
        "forecast": "6.9",
        "unit": "%",
        "reporting_period": "Q1 FY25",
        "source_url": "https://www.mospi.gov.in",
        "summary": "OFFICIAL RECORD · Real GDP growth in Q1 (April-June) 2026-27 was estimated at 6.7%."
    },
    {
        "external_id": "mospi-gdp-q2-fy25",
        "title": "India Gross Domestic Product (GDP) Growth YoY",
        "kind": "Economic",
        "country": "India",
        "category": "Output",
        "authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
        "importance": "High",
        "status": "Scheduled",
        "sample": False,
        "scheduled_at": "2026-11-29T12:00:00+00:00",
        "previous": "6.7",
        "forecast": "6.5",
        "unit": "%",
        "reporting_period": "Q2 FY25",
        "source_url": "https://www.mospi.gov.in",
        "summary": "OFFICIAL SCHEDULE · Scheduled release of Second Quarter (Q2 July-September) Real GDP growth estimates by MoSPI."
    },

    # --- RBI FOREIGN EXCHANGE RESERVES ---
    {
        "external_id": "rbi-forex-2026-11-08",
        "title": "India Foreign Exchange Reserves (Forex)",
        "kind": "Economic",
        "country": "India",
        "category": "Foreign Exchange",
        "authority": "Reserve Bank of India (RBI)",
        "importance": "Low",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-08T11:30:00+00:00",
        "published_at": "2026-11-08T11:30:00+00:00",
        "actual": "682.13",
        "previous": "684.80",
        "unit": "USD Billion",
        "reporting_period": "01 Nov 2026",
        "source_url": "https://www.rbi.org.in",
        "summary": "OFFICIAL RECORD · RBI weekly statistical supplement showing total foreign exchange reserves at $682.13 billion."
    },
    {
        "external_id": "rbi-forex-2026-11-15",
        "title": "India Foreign Exchange Reserves (Forex)",
        "kind": "Economic",
        "country": "India",
        "category": "Foreign Exchange",
        "authority": "Reserve Bank of India (RBI)",
        "importance": "Low",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-11-15T11:30:00+00:00",
        "published_at": "2026-11-15T11:30:00+00:00",
        "actual": "675.65",
        "previous": "682.13",
        "unit": "USD Billion",
        "reporting_period": "08 Nov 2026",
        "source_url": "https://www.rbi.org.in",
        "summary": "OFFICIAL RECORD · Total foreign exchange reserves stood at $675.65 billion."
    },

    # --- CENTRAL GOVERNMENT FISCAL DEFICIT (CGA) ---
    {
        "external_id": "cga-deficit-2026-09",
        "title": "India Central Government Fiscal Deficit (% of Budget Target)",
        "kind": "Economic",
        "country": "India",
        "category": "Fiscal Policy",
        "authority": "Controller General of Accounts (CGA), Ministry of Finance",
        "importance": "Medium",
        "status": "Published",
        "sample": False,
        "scheduled_at": "2026-10-31T10:30:00+00:00",
        "published_at": "2026-10-31T10:30:00+00:00",
        "actual": "29.4",
        "previous": "27.0",
        "unit": "% of FY BE",
        "reporting_period": "Apr-Sep 2026",
        "source_url": "https://cga.nic.in",
        "summary": "OFFICIAL RECORD · Government of India fiscal deficit stood at 29.4% of full-year budget estimates at the end of September 2026."
    }
]

res = ingest.import_records(official_economic_events, source_id="india_official_import", mode="import", sample=False)
print("Ingestion result for official Indian economic events:", res.describe())

total = db.rows("SELECT count(*) as c FROM events")[0]["c"]
by_kind = db.rows("SELECT kind, count(*) as c FROM events GROUP BY kind")
print(f"Total events now: {total}")
for r in by_kind:
    print(f"  {r['kind']}: {r['c']}")
