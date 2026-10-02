# Capstone video script (about 7 minutes)

**ICAI requirement:** your face and the technical content must both be on screen. Upload to YouTube as *unlisted* (or Google Drive with "anyone with the link"), then check the link in a private browser window.

**Setup:** a screen recorder with a webcam overlay in a corner: Clipchamp (built into Windows 11: *Record & create → Screen and camera*) or OBS Studio.
Open these beforehand:
1. The app: run `Start_LookThrough.bat` and sign in (it also shows values at latest prices); `app/LookThrough.html` works offline too
2. Claude Desktop with the lookthrough connector
3. The n8n workflow page
4. `examples/monitor_alert_email.html`
5. A terminal in the project folder

---

**0:00 Introduction (camera, 30 s)**
"I'm <name>, AICA Level 2, batch <no>. I work in a family office, and a question our investment committee keeps asking is: *what do we really own?* My capstone, LookThrough, answers that with verified numbers, lets Claude answer questions through MCP, and monitors our investment policy every month with n8n. The family is fictitious; all the market data is real."

**0:30 The problem (app dashboard, 45 s)**
Show the dashboard. "Five entities: two individuals, an HUF, an LLP and a son. Direct shares plus twelve mutual funds. The problem: the same stock sits in our direct book and inside several funds, so no statement shows the true exposure."

**1:15 Look-through (app → Look-through exposure, 60 s)**
"LookThrough reads each AMC's monthly portfolio disclosure, the SEBI-mandated Excel file, and looks through the funds. HDFC Bank is 12.56% of our equity: Rs 3.84 crore direct, and Rs 1.87 crore through funds that no single statement shows."
Open *Concentration & limits*: "Two policy breaches: single stock, and Financial Services at 33.39%. Three warnings: our two large-cap funds and the Nifty 50 index fund overlap 54% to 64% with each other, meaning we pay several expense ratios for largely the same stocks."

**2:15 Claude through MCP (Claude Desktop, 2 min)** *The key part for Module 10.*
Show the connectors icon → lookthrough → the 11 tools, all read-only.
Type: *"Use the ic_note prompt: is the family over-exposed to HDFC Bank?"*
While it runs: "Claude cannot use its own numbers. It calls my tools, which use a calculation engine reconciled against the app on 4,664 values. It tags every line as fact, calculation, assumption or its own view, and it gives options, not a recommendation."
When it calls **verify_note**: "This is the quality gate. Code, not another AI, checks that every figure in the note came from a tool. Each figure must be bound to the field it came from: the same value, the same unit, the tool it cites, and words that name that field. A wrong number, a coincidence or a figure attached to the wrong field is rejected, with the reason."

**4:15 n8n monthly monitor (n8n + email, 75 s)** *Module 9.*
Show the workflow canvas. "Once a month the PC refreshes the data and sends the verified results here. n8n validates them, compares with last month, logs the run and emails the committee only when a limit is breached or a breach clears. n8n never recalculates a figure, and the alert address cannot be changed by the incoming data."
Show `examples/monitor_alert_email.html`: "Two breaches and three overlap warnings this month; the committee sees each test, its limit and what changed since last month."
Optional: show the failed test execution where malformed data was rejected.

**5:30 Why you can trust it (terminal, 60 s)**
Run `.venv\Scripts\python.exe verify\mcp_check.py` → "42 of 42". Show `verify/reconciliation_result.txt` → "4,664 values agree between two independent engines." Then: "Agreement is not enough: an independent review found errors both engines shared, for example Infosys reporting in dollars, and the ELSS lock-in. They are fixed, and oracle tests now guard them."
"While building it I found real-data problems: AMFI changed its file format and silently dropped all twelve funds; a name match picked a US fund instead of an Indian large-cap fund; a benchmark labelled Smallcap was really the Nifty 500. The tests caught each one, and each is fixed and documented."

**6:30 Close (camera, 30 s)**
"Limitations: some data is secondary, from Yahoo Finance; fund holdings are published monthly, so early in a month they lag the prices, and the app says so on every screen; and tax is indicative. All of this is documented. LookThrough is decision support: the committee decides. Thank you."
