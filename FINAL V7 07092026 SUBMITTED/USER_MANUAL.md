# FAMILY INVESTMENT MATRIX V7 — USER MANUAL

## A layman-friendly step-by-step guide

This manual is written so that a family member who is not a programmer can operate the application safely.

---

# 1. What the application does

Family Investment Matrix is a local family portfolio application. It combines investments belonging to different family members and different brokers into one place.

It can be used to record and analyse:

- equity/share investments;
- mutual-fund investments;
- purchases and sales;
- SIP transactions;
- dividends;
- bonus/split-related entries supported by the transaction engine;
- member-wise holdings;
- broker/platform-wise holdings;
- invested amount;
- current market value;
- realised and unrealised gains;
- portfolio allocation;
- portfolio-related news;
- cached/live market prices.

The application is a **tracker and analytical dashboard**, not an online broker.

---

# 2. Important files

The two most important files are:

```text
family_investment_matrix_v7.py
family_investments.db
```

The `.py` file is the program.

The `.db` file contains the family investment records.

If the database is accidentally deleted, the application can open as an empty system. Therefore, back up the database regularly.

---

# 3. Starting the application

### Method A — recommended

Open Command Prompt inside the project folder and run:

```bash
python family_investment_matrix_v7.py
```

The program checks the Streamlit environment and, when necessary, relaunches through Streamlit.

### Method B

```bash
streamlit run family_investment_matrix_v7.py
```

The application should open in your normal web browser.

---

# 4. First login

The first user is the administrator.

On first setup/login:

1. Enter the administrator details required by the setup screen.
2. Use the initial password configured in the application.
3. The application forces the first user to change the password.
4. Create a strong private password.
5. Do not share the password or broker/API credentials casually.

---

# 5. Main menu

The application includes pages/functions such as:

- Dashboard
- Member View
- All Transactions
- Query Explorer
- News Board
- Add Family Member
- Upload Investments
- Instrument Master
- Settings
- Logout

The exact sidebar ordering may change slightly as the UI evolves.

---

# 6. Add family members

Open **Add Family Member**.

Enter the person's details.

Typical fields include:

- name;
- relation;
- mobile number;
- date of birth, PAN and email where useful.

Only record sensitive personal details when they are actually required.

After saving a family member, investments can be linked to that person.

---

# 7. Add brokers and platforms

The application keeps a broker/platform master.

Examples:

- HDFC Securities
- ICICI Direct
- Zerodha
- Upstox
- SBI Securities
- CAMS
- KFintech
- other brokers/platforms

If a platform is not already available, use Settings to add it where the V7 interface permits.

---

# 8. Understanding the Instrument Master

The Instrument Master is one of the major V7 improvements.

The same share can have different identifiers at different market-data providers.

For example, the investment may be known to the family as:

```text
RELIANCE
```

but providers can require:

- an exchange;
- an instrument token;
- an ISIN;
- a broker-specific code;
- an Upstox instrument key;
- a Yahoo symbol.

The Instrument Master stores those mappings once so the user does not have to repeatedly remember them.

Typical mapping fields include:

- common portfolio symbol;
- company/instrument name;
- exchange;
- segment;
- ISIN;
- HDFC token/code;
- ICICI Breeze stock code;
- Zerodha/trading symbol;
- Upstox instrument key;
- Yahoo symbol.

### Good practice

When adding a new share:

1. create/check the portfolio identifier;
2. confirm the NSE/BSE exchange;
3. populate the provider mapping that you actually use;
4. test the market-price connection;
5. check that the returned price belongs to the correct security.

---

# 9. Manual investment entry

Use **Upload Investments → Manual Entry**.

Typical fields:

| Field | Meaning |
|---|---|
| Family Member | Who owns the investment |
| Broker / Platform | Where the investment is held |
| Asset Type | Equity or Mutual Fund |
| Instrument Name | Name of the company/fund |
| Identifier | Symbol/scheme code used for matching |
| Transaction Type | BUY, SELL, SIP, DIVIDEND, BONUS, SPLIT etc. |
| Transaction Date | Actual transaction date |
| Quantity / Units | Number of shares/units |
| Price per Unit | Transaction price |
| Charges | Brokerage/taxes/charges |
| Folio / Remarks | Optional reference |

### Automatic value

The V7 application calculates the ordinary transaction amount from:

```text
Quantity × Price per Unit
```

Example:

```text
100 shares × ₹2,450 = ₹2,45,000
```

This reduces manual arithmetic errors.

---

# 10. Transaction types

### BUY

Adds quantity and investment cost.

### SIP

Used for periodic acquisition, particularly mutual funds. It is treated like an acquisition in the holdings calculation.

### SELL

Reduces quantity. The holdings engine proportionately removes cost and calculates a realised result based on the implemented average-cost logic.

### DIVIDEND

Records income without normally increasing the number of shares.

### BONUS / SPLIT

Used to adjust quantity for supported corporate-action entries.

Because corporate actions can be complex, reconcile the resulting quantity with the broker statement.

---

# 11. Excel bulk import

Use Excel when entering many historical transactions.

Recommended workflow:

1. Use the application's template.
2. Enter one transaction per row.
3. Use correct family member names.
4. Use correct broker/platform.
5. Use actual transaction dates.
6. Keep identifiers as clean text where possible.
7. Upload.
8. Preview and validate.
9. Review duplicates.
10. Save only after checking the data.

The application contains duplicate-detection logic to reduce accidental duplicate imports.

---

# 12. PDF extraction

The PDF extraction feature uses `pdfplumber`.

It is an **import assistant**, not guaranteed automatic accounting.

PDF statement formats vary between brokers.

Always:

1. upload the statement;
2. inspect extracted tables;
3. map columns;
4. compare with the original PDF;
5. verify date, quantity, price, amount and security;
6. only then save.

---

# 13. Dashboard

The Dashboard is the family-level summary.

Important figures include:

### Total Invested

The remaining investment cost derived from the transaction ledger.

### Current Value

Current quantity × latest cached/current market price or NAV.

### Gain / Loss

Difference between current value and invested cost for open holdings, together with realised/dividend information where the relevant report exposes it.

### Members

Number of family members represented.

### Charts

The dashboard can compare:

- invested value vs current value;
- member-wise value;
- asset allocation;
- broker/platform concentration;
- security-wise holdings.

Hovering over Plotly charts can reveal exact values.

---

# 14. Member View

Use Member View when you want to analyse only one family member.

Steps:

1. Open Member View.
2. Select the family member.
3. Review invested amount.
4. Review current value.
5. Review gain/loss.
6. Check the instrument-wise table.
7. Compare quantities with actual broker statements.

---

# 15. Market-price providers in V7

V7 includes multiple provider paths.

The application can use:

1. HDFC Securities InvestRight
2. ICICI Direct Breeze
3. Zerodha Kite Connect
4. Upstox
5. Yahoo/yfinance fallback
6. Manual price override

The provider order is configurable.

---

# 16. Preferred price provider

Open **Settings**.

Choose the preferred provider.

If `AUTO` is selected, the application follows its standard provider order.

When a specific provider is selected, V7 attempts that provider first and can move to other configured providers if required by the implemented fallback path.

---

# 17. HDFC Securities connection

V7 contains a dedicated HDFC LTP integration path.

You must enter valid credentials/tokens according to the HDFC developer account/API requirements.

Because authentication rules can change, always use the current credentials generated through your own HDFC Securities API access.

Use the built-in connection test where available before refreshing all portfolio prices.

---

# 18. ICICI Direct Breeze connection

V7 contains an ICICI Breeze quote path.

Breeze normally requires credentials/session information from the ICICI Breeze developer setup.

Sessions/tokens can expire.

If the connection worked yesterday but fails today:

1. obtain a current valid session/token;
2. re-enter it;
3. run the connection test;
4. then refresh the portfolio.

---

# 19. Zerodha

Zerodha Kite Connect can be used as an official quote provider when valid API credentials and access token are configured.

Typical issues:

- expired access token;
- wrong trading symbol;
- wrong exchange;
- invalid API key/token;
- no network connection.

---

# 20. Upstox

Upstox often works best when the Instrument Master contains the correct provider instrument key/ISIN mapping.

A plain symbol may not always be sufficient for an Upstox quote request.

---

# 21. Yahoo fallback

Yahoo/yfinance is retained as a convenient fallback.

It should not be treated as guaranteed exchange-grade market infrastructure.

If it fails, use another configured provider or manual price override.

---

# 22. Manual price/NAV override

Manual override is the last-resort safety mechanism.

Use it when:

- a provider is temporarily down;
- authentication fails;
- an instrument is unsupported;
- a symbol mapping needs correction;
- a mutual-fund NAV lookup fails.

Enter the correct current value/price and save.

Later, a successful live refresh can replace the cached manual value.

---

# 23. Mutual-fund NAVs

For mutual funds, use the correct scheme identifier/scheme code expected by the NAV function.

Do not rely only on a nickname such as:

```text
Bluechip Fund
```

when the NAV source requires an official numeric scheme code.

---

# 24. Identifier rule

Correct identifiers are essential.

Examples:

```text
RELIANCE
TCS
INFY
HDFCBANK
SBIN
```

Excel sometimes converts numeric scheme codes such as:

```text
125497
```

into:

```text
125497.0
```

V5/V6/V7 contain identifier-normalization logic to prevent this from creating float-vs-string merge errors.

---

# 25. All Transactions

When a dashboard figure looks wrong, open **All Transactions first**.

Check:

- wrong BUY/SELL selection;
- wrong quantity;
- wrong date;
- duplicate transaction;
- missed historical purchase;
- missed sale;
- bonus/split entry;
- wrong family member;
- wrong broker;
- wrong identifier.

The transaction ledger is the source from which holdings are derived.

---

# 26. Query Explorer

Query Explorer provides alternate analytical views.

Examples of questions it can help answer:

- Which family member owns a particular security?
- In which broker is a share held?
- Which platform has the highest value?
- Is the same company held by multiple family members?

---

# 27. News Board

The application can fetch and cache portfolio-related news.

News should be treated as information only.

The news module is not a substitute for professional investment research or advice.

---

# 28. Backup

The database is the most important family record.

Recommended procedure:

1. Close the application or avoid saving a transaction during copying.
2. Copy:

```text
family_investments.db
```

3. Rename the copy:

```text
family_investments_2026-09-07.db
```

4. Store at least one additional copy on a trusted device/drive.

---

# 29. Restore

If the active database becomes damaged:

1. stop Streamlit;
2. rename the current database rather than immediately deleting it;
3. copy a known-good backup into the application folder;
4. rename the backup exactly:

```text
family_investments.db
```

5. restart the application;
6. verify members and transactions.

---

# 30. Troubleshooting

### Application does not open

Run:

```bash
python family_investment_matrix_v7.py
```

from Command Prompt and read the displayed error.

### Missing module

Run:

```bash
pip install -r requirements.txt
```

### Dashboard values are wrong

Check All Transactions and identifiers.

### Live price does not update

Check:

1. internet;
2. preferred provider;
3. credentials;
4. access token/session expiry;
5. Instrument Master mapping;
6. symbol/exchange;
7. fallback provider;
8. manual override.

### Excel import looks wrong

Check date format, numeric fields and identifiers before saving.

---

# 31. Recommended monthly routine

1. Enter all purchases/sales/SIPs.
2. Enter dividends/corporate actions where applicable.
3. Reconcile quantities with broker statements.
4. Check Instrument Master for new securities.
5. Refresh prices.
6. Review failed quotes.
7. Review member-wise values.
8. Review family allocation.
9. Check unusual concentration.
10. Back up the database.

---

# 32. Security recommendations

- Keep the application on a trusted computer.
- Do not hard-code API secrets in the source.
- Prefer session/environment-variable credentials.
- Use strong login passwords.
- Back up the database.
- Do not expose Streamlit publicly without adding proper deployment security.
- Do not add trading/order functions casually.
- Keep API access read-only for this portfolio-tracking use case wherever practical.

---

# 33. Remember

**Transactions are the accounting source.  
Instrument Master controls symbol/provider mapping.  
Price cache controls valuation.  
Dashboard is the calculated presentation.**

If a result is wrong, check those layers in that order.
