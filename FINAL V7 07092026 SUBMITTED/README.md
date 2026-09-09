# FAMILY INVESTMENT MATRIX — V7

## Project Submission Package

**Family Investment Matrix V7** is a local Python + Streamlit family investment tracking application designed to consolidate investments belonging to multiple family members across different brokers and platforms.

The application maintains a transaction-ledger-based portfolio, calculates member-wise and consolidated holdings, displays dashboards and charts, supports manual/Excel/PDF-assisted imports, and can retrieve current market prices through a multi-provider engine.

### Main V7 market-data providers

1. HDFC Securities InvestRight API
2. ICICI Direct Breeze API
3. Zerodha Kite Connect
4. Upstox Market Quote API
5. Yahoo Finance / yfinance fallback
6. Manual price/NAV override

V7 also contains an **Instrument Master** so one investment can be mapped to different broker/provider identifiers and a **Settings** screen for choosing the preferred price provider.

---

## Important project principle

The application is primarily a **portfolio tracking and valuation system**. It is not intended to place buy/sell orders. Broker/API credentials are used for market-data retrieval only.

---

## Folder contents

| File | Purpose |
|---|---|
| `family_investment_matrix_v7.py` | Final V7 application |
| `README.md` | Project overview, installation and submission notes |
| `USER_MANUAL.md` | Detailed layman-friendly operating manual |
| `ROADMAP.md` | Development roadmap from the initial version through future phases |
| `DEVELOPMENT_HISTORY_AND_ARCHITECTURE_PROMPT.txt` | Full development history, architecture record and reusable master prompt |
| `TEST_REPORT.md` | Validation performed before packaging |
| `requirements.txt` | Python dependencies |
| `sample_environment_variables.txt` | Optional environment-variable names for API credentials |

---

## Technology stack

- Python
- Streamlit
- SQLite
- Pandas
- Plotly Express
- Requests
- yfinance
- OpenPyXL
- pdfplumber
- feedparser
- hashlib / password hashing utilities

---

## Installation

### 1. Install Python

Recommended: a modern supported 64-bit Python installation.

Confirm:

```bash
python --version
```

### 2. Put the project in a permanent folder

Example:

```text
C:\Family Investment Matrix\
```

Keep the Python file and the database created by the application in the same application folder.

### 3. Install dependencies

From Command Prompt in the project folder:

```bash
pip install -r requirements.txt
```

The program also contains dependency-check logic, but installing from `requirements.txt` is recommended for a project submission.

### 4. Start the application

```bash
python family_investment_matrix_v7.py
```

The launcher is designed to restart itself through Streamlit when required.

Alternative:

```bash
streamlit run family_investment_matrix_v7.py
```

### 5. Open the browser

Streamlit normally opens the application automatically. The usual local address is similar to:

```text
http://localhost:8501
```

---

## First-use workflow

1. Start the application.
2. Complete the initial administrator setup/login.
3. Change the initial password when requested.
4. Add family members.
5. Add/confirm brokers and platforms.
6. Open the Instrument Master and map securities.
7. Enter investments manually or import them.
8. Configure a preferred market-data provider under Settings.
9. Test the provider connection.
10. Refresh prices from the Dashboard.
11. Review family and member-level holdings.
12. Back up `family_investments.db`.

---

## Data files

The local SQLite database is:

```text
family_investments.db
```

It stores the family/member master, users, broker/platform master, transaction ledger, cached prices, news cache, Instrument Master mappings and application settings.

**Do not delete this file unless you intentionally want to start with an empty database.**

---

## Market-data credentials

API credentials should not be permanently hard-coded into the source.

Where supported, V7 reads credentials from Streamlit session state and/or local environment variables.

See `sample_environment_variables.txt`.

Access tokens can expire. A connection that worked previously may need a fresh token depending on the broker/provider's authentication rules.

---

## Backup

The most important file to back up is:

```text
family_investments.db
```

Recommended backup name:

```text
family_investments_YYYY-MM-DD.db
```

Keep at least one additional copy on a trusted external drive or encrypted backup location.

---

## Testing status

Before packaging, the submitted V7 source was:

- compiled using Python `py_compile`;
- parsed through the Python AST parser;
- scanned for duplicate literal Streamlit widget keys;
- checked for required V7 functions;
- tested with a synthetic holdings calculation;
- tested for identifier normalization.

Authenticated live calls to HDFC Securities, ICICI Breeze, Zerodha or Upstox require the user's own valid credentials and therefore are tested from the application's Settings screen on the user's machine.

See `TEST_REPORT.md`.

---

## Project name

The final project name is:

# FAMILY INVESTMENT MATRIX

Previous references to “Family Fortune Tracker” belong to the earlier development history only and are not the current project branding.

---

## Version

**V7 — Multi-provider market-data architecture with Instrument Master and preferred-provider Settings.**
