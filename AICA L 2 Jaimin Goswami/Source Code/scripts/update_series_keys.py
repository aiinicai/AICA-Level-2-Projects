import sqlite3
from pathlib import Path

SERIES_MAP = {
    "ed7ddd36-e4d0-54b3-8684-9d6d8b54e055": "IN:POLICY_REPO_RATE:%",
    "6196b714-1311-58ca-ad2c-932530030783": "IN:CPI_INFLATION:%",
    "f984cc7f-7549-5709-b6cf-6c83e0aa332f": "IN:IIP_GROWTH:%",
    "bfd88c87-9693-501e-b5cb-d95e89fa0736": "IN:FOREX_RESERVES:USD",
    "a95a75d9-6eac-5f47-8630-4420245fab1f": "IN:FISCAL_DEFICIT:%BE",
    "9d060595-58fe-5bf9-8b51-7754c515b73f": "US:FED_FUNDS_RATE:%",
    "9bc87a5f-046a-5014-97c2-9278b976b8c2": "US:NONFARM_PAYROLLS:K",
    "931dd0f3-8ef1-52bd-82e3-52d3ee80ea02": "US:UNEMPLOYMENT_RATE:%",
    "5daa972d-4660-512b-a2b1-b81e9294adb6": "US:CPI_INFLATION:%",
    "35757dad-13b2-5dcb-89ac-1d4d89eb1b3a": "US:GDP_GROWTH:%",
    "77e61d0f-571e-5894-81b4-fd71872696b8": "US:ISM_MANUFACTURING_PMI:INDEX",
    "c58e8bc2-224f-5116-8eee-9badefd6e802": "EU:ECB_DEPOSIT_RATE:%",
    "4683bdcd-b5bd-54df-94b3-416b22d6e3f8": "EU:HICP_INFLATION:%",
    "87dcc747-5f91-567a-b08c-71733d893eec": "UK:BOE_BANK_RATE:%",
    "167481cd-42df-507e-843a-6f884bc51512": "UK:CPI_INFLATION:%",
    "28b937e4-a273-53fc-8fd4-c4caca7758d4": "JP:BOJ_POLICY_RATE:%",
    "1b5a0683-be78-5fc8-ad8a-e7af9d12189f": "JP:CPI_INFLATION:%",
    "b4c4f487-d796-5f24-ad75-4e6a5476b216": "CN:NBS_MANUFACTURING_PMI:INDEX",
    "0b4b3d30-015f-5e1b-9c37-b58df01ba4d3": "CN:GDP_GROWTH:%"
}

TITLE_TO_KEY = [
    ("Repo Rate", "IN:POLICY_REPO_RATE:%"),
    ("India Consumer Price Index", "IN:CPI_INFLATION:%"),
    ("India Wholesale Price Index", "IN:WPI_INFLATION:%"),
    ("India Index of Industrial Production", "IN:IIP_GROWTH:%"),
    ("India Gross Domestic Product", "IN:GDP_GROWTH:%"),
    ("India Central Government Fiscal Deficit", "IN:FISCAL_DEFICIT:%BE"),
    ("India Foreign Exchange Reserves", "IN:FOREX_RESERVES:USD"),
    ("US Federal Reserve (FOMC) Interest Rate", "US:FED_FUNDS_RATE:%"),
    ("US Non-Farm Payrolls", "US:NONFARM_PAYROLLS:K"),
    ("US Unemployment Rate", "US:UNEMPLOYMENT_RATE:%"),
    ("US Consumer Price Index", "US:CPI_INFLATION:%"),
    ("US Gross Domestic Product", "US:GDP_GROWTH:%"),
    ("US ISM Manufacturing PMI", "US:ISM_MANUFACTURING_PMI:INDEX"),
    ("ECB Deposit Facility Rate", "EU:ECB_DEPOSIT_RATE:%"),
    ("Eurozone Harmonised CPI", "EU:HICP_INFLATION:%"),
    ("Bank of England (BoE) Official Bank Rate", "UK:BOE_BANK_RATE:%"),
    ("UK Consumer Price Index", "UK:CPI_INFLATION:%"),
    ("Bank of Japan (BoJ) Policy Rate", "JP:BOJ_POLICY_RATE:%"),
    ("Japan National Consumer Price Index", "JP:CPI_INFLATION:%"),
    ("China NBS Manufacturing PMI", "CN:NBS_MANUFACTURING_PMI:INDEX"),
    ("China Gross Domestic Product", "CN:GDP_GROWTH:%")
]

def update_series_keys(db_path):
    print(f"Updating series keys in {db_path}...", flush=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Update economic_indicators
    for ind_id, sk in SERIES_MAP.items():
        cur.execute("UPDATE economic_indicators SET series_key = ? WHERE id = ?", (sk, ind_id))

    # 2. Update events table
    for title_sub, sk in TITLE_TO_KEY:
        cur.execute("UPDATE events SET series_key = ? WHERE LOWER(kind) = 'economic' AND title LIKE ?", (sk, f"%{title_sub}%"))

    # 3. Update economic_observations table
    cur.execute("""
        UPDATE economic_observations
        SET series_key = (SELECT series_key FROM events WHERE events.id = economic_observations.event_id)
    """)

    conn.commit()
    
    cur.execute("SELECT count(*) FROM economic_observations WHERE series_key != ''")
    obs_cnt = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM events WHERE LOWER(kind) = 'economic' AND series_key != ''")
    ev_cnt = cur.fetchone()[0]
    conn.close()
    print(f"Done {db_path}: {ev_cnt}/31 economic events and {obs_cnt}/155 observations now have series keys.", flush=True)

if __name__ == "__main__":
    for db in [
        r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db",
        r"C:\Users\ADMIN\Desktop\Capstone\Github\FinstockEventScope\data\eventscope.db"
    ]:
        if Path(db).exists():
            update_series_keys(db)
