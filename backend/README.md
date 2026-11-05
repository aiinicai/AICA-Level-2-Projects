# DirhamTrack AI - Python FastAPI Backend & SQLite

## Setup Instructions

### 1. Install Dependencies
```bash
cd backend
python3 -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Initialize Database & Run Server
```bash
# Initialize SQLite schemas
python3 database.py

# Launch FastAPI development server
uvicorn main:app --reload --port 8000
```

### 3. API Endpoints
- `POST /api/v1/categorize`:
  Submits merchant name and user learned rules; returns normalized name and category.
- `POST /api/v1/parse-notification`:
  Parses incoming notification strings, detects bank, extracts amount, currency, and flags anomalies.
- `POST /api/v1/corrections`:
  Stores user-corrected merchant category rules in SQLite.
- `GET /docs`:
  Interactive Swagger UI documentation.
