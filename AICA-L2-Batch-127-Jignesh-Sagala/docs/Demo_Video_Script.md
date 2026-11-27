# Demo video script: Hisaab Kitaab

Length target: under 10 minutes. About 9 minutes 30 seconds at a calm pace. All data on screen is dummy data (owner BusyMe, PAN ABCDE1234F).

**Order:** problem, inputs, process (Claude, Python, Lovable), output demo, bonus (NRI treaty page), boundaries, close.

## Before recording

- Open these before you press record, in this order, as browser tabs: (1) the dashboard, `dashboard/HisaabKitaab_Dashboard.html` from your project folder, light theme, date 25 Nov 2026; (2) the README from your GitHub fork, top of the page; (3) the same README with `#7-how-it-runs` added to the link, which opens the eleven-step table; (4) `docs/Lovable_Build_Log.md` in your fork; (5) `docs/test_result.md` in your fork. The fork link starts: `github.com/jigneshsagala-creator/AICA-Level-2-Projects/blob/main/AICA-L2-Batch-127-Jignesh-Sagala/`. Also open File Explorer on the project folder only, showing `db_dummy` and `samples`. Switch with Ctrl+Tab or Alt+Tab. Open nothing new while recording.
- Close every other tab and window. Never show a folder, file name or mailbox that belongs to the real data. Do not open Python files or a database. Show the project folder only.
- Steps 1 to 3 of the process are described in words. Do not open the real mailbox or the real statements on screen.
- The submission form requires a video that shows your face and the technical content. Keep your camera on for the whole recording. Zoom shows your face in a small corner while you share the screen.
- Host the video on YouTube (unlisted) or Google Drive, set so anyone with the link can view. The link goes only into the form, not into GitHub. Only dummy data appears in it, so a public link is safe.
- Practise once with a timer. Cut words, not the demo.

## Timing at a glance

| Part | Start | Length |
|---|---|---|
| 1. Introduction | 0:00 | 0:55 |
| 2. Problem | 0:55 | 1:00 |
| 3. Inputs | 1:55 | 1:25 |
| 4. Process | 3:20 | 2:30 |
| 5. Output demo | 5:50 | 2:50 |
| 6. Bonus: NRI treaty page | 8:40 | 0:35 |
| 7. Boundaries and close | 9:15 | 0:40 |

---

## 1. Introduction (0:00 to 0:55)

**Show:** Your face on camera, then the Overview page of the dashboard.

**Say:**
I thank the President and the Vice-President of ICAI, and all the faculty of AICA Level 1 and Level 2.

My name is Jignesh Sagala, AICA Level 2, Batch 127. My project is about all of us. We work in practice, business or industry. Work and family keep us so busy that we, as CAs, rarely track our own investments. So I built an investment tracker dashboard. I named it Hisaab Kitaab, which means accounts and records. We will see it through the eyes of BusyMe. BusyMe could be any one of us. All data you see is dummy data.

## 2. Problem (0:55 to 1:55)

**Show:** Slide-free. Stay on the Overview, or show the top of the README tab.

**Say:**
BusyMe holds money in many places. Mutual funds. Shares with a broker. Savings accounts. Term deposits. A rented house. Insurance policies.

Every institution sends its own statement, in its own layout. Most are locked PDFs that arrive by email each month. To track investments and cash flows, and to know what everything is worth, BusyMe must collect each statement, remember each password, and add the numbers by hand. That takes time, and BusyMe is busy.

The numbers are not simple either. A fund bought through a monthly SIP changes its units and average cost every month. Shares bought in lots need an average cost with brokerage. Value on a past date needs that date's price. Money going out, such as SIPs, premiums and house tax, is easy to forget.

So BusyMe wants one answer. What is everything worth, what did it cost, where does it sit, and what needs attention. It fits any investor in India. For a non-resident Indian there is a bonus, which I will show at the end.

## 3. Inputs (1:55 to 3:20)

**Show:** The `db_dummy` folder (eleven CSV tables and one small helper file, `price_sources.csv`), or the table in the README. Then the `samples` folder with the six made-up PDFs.

**Say:**
The dashboard reads a small database of eleven CSV tables. Instruments, transactions, prices, bank balances, term deposits, broker cash, SIP plan, owner, properties, rent receipts and insurance. A CSV file is a plain table that opens in Excel. A twelfth small file, price sources, only says where each price comes from.

In real life, the data starts as locked PDF statements. A consolidated fund and demat statement. Broker contract notes. A broker funds ledger. Bank statements. Prices come from public sources: fund prices from AMFI, share prices from Yahoo, and the dollar rate.

Real statements hold real names and passwords, so they never leave my laptop. For this public project I made six made-up locked statements for BusyMe. The password of each sample is in the README. Four Python readers open them and turn them into the CSV tables. The tables you see here are dummy data.

## 4. Process (3:20 to 5:50)

**Show:** The eleven-step table in README section 7. Then the Lovable build log table. Then `docs/test_result.md`.

**Say:**
Eleven steps take a statement email to the dashboard. Claude, Python and I each have a part.

Step one. Claude collects the statement emails through the Gmail connector, on the 10th of each month, and saves the attachments. This step runs only on my laptop, so it is not in the public upload. Steps two and three. I sort the files, and I type each password once, hidden. It is kept in the Windows Credential Manager, never in a file and never in chat.

Steps four and five. Python probes each PDF and keeps only the layout, with digits masked. Claude saw layout only, never real numbers. Then four Python readers read the statements by position on the page. Each reader checks its own work. Units must add up. Running balances must match. Totals must tie. If one check fails, that file is not used.

Steps six to nine. Python works out the opening cost, fetches prices, assembles the eleven tables, and builds one HTML file. Step ten is testing. One command runs eleven tests. The readers have two hundred and nine checks, including errors planted on purpose. Two separate calculation engines, one in JavaScript and one in Python, agree on one hundred and eight questions. A third method, plain Excel formulas, differs by zero rupees. Step eleven is mine. I review the dashboard against my own books.

The screen design was made with a third tool, Lovable. Lovable builds web pages from written instructions. Claude wrote eight messages for it. The key rule in every message was: do not touch the two tested calculation files, and show only numbers that come from them. I then checked the result against Python. The totals matched. I rebuilt it as one offline file. The full list of messages is in the Lovable build log.

## 5. Output demo (5:50 to 8:40)

**Show:** The dashboard, page by page, as marked. Move slowly. Pause on each number.

**Say:**
This is the dashboard. One file. I double-click it and it opens in any browser. No login, no internet.

*Overview.* On twenty-fifth November 2026, everything is worth 20 crore 59 lakh 65 thousand rupees. Cost was 18 crore 4 lakh. That is a gain of 14.14 per cent. The yearly return on the funds, called XIRR, is 13.92 per cent. The split is 24.9 per cent mutual funds, 30.6 per cent shares, 11.7 per cent bank balances, and 32.7 per cent term deposits. The summary says the total is up 66 lakh 54 thousand since thirty-first October.

*Date selector.* Now I change the date to thirty-first March 2026. The total is 15 crore 59 lakh. On thirtieth June 2026 it is 18 crore 45 lakh. Every number moves, because every number uses the price of that date.

*Mutual Funds.* Funds are worth 5 crore 12 lakh against a cost of just over 4 crore. The chart shows money added by SIP each month. The table shows units, average cost, price, value and gain for each fund. I click one fund and its ledger opens.

*Equity shares.* I filter by sector, Banking. The table and the charts change together. Share cost includes brokerage.

*Bank and Deposits.* Balances by account, including NRE, NRO and a dollar account shown in rupees at the rate of the day. Term deposits show interest so far, maturity dates and days left. The next maturity is on tenth December 2026.

*Property, Insurance.* The rented house with its rent receipts. Three insurance policies, with cover of 12 crore in total. Neither is added to the total on the Overview, and the page says so.

*Cash Calendar.* The next twelve months commit 31 lakh 40 thousand rupees. That is SIP of 24 lakh, premiums of 6 lakh and house tax of 1 lakh 40 thousand. The next payment is on fifth December, forty thousand rupees to HDFC Flexi Cap Fund.

*Data checks.* All checks pass, and the rules behind every number are written here in plain words. Last, a quick look at the dark theme, and the Excel export. One click saves the page as a spreadsheet.

## 6. Bonus: NRI treaty page (8:40 to 9:15)

**Show:** The NRI DTAA tab. Scroll once through the page.

**Say:**
The bonus is for a non-resident Indian. Bank balances in dollars use the dollar to rupee rate of the day, in the same pages. The last tab, NRI DTAA, is a worked example of treaty relief on a fund redemption. All names and numbers on it are fictional, and it is marked as a sample page.

## 7. Boundaries and close (9:15 to 9:55)

**Show:** Overview again, or the README boundaries section.

**Say:**
Three boundaries. First, no real data is in the public project. The real dashboard stays on my laptop. Second, this is read-only. Nothing is ever ordered or changed at a bank or broker. Third, this is not tax advice or investment advice.

What I learned. A tool is a good partner only when it has clear rules and its output is checked. Claude wrote and tested the code. Python did the exact work on my laptop. Lovable gave the screen its design. The numbers were never left to a tool that could not be tested.

Thank you. The code, the tests and the build log are in my project folder.

---

## Facts used in this script (all checked)

| Item | Value | Source |
|---|---|---|
| Total value, 25 Nov 2026 | INR 20,59,65,739 | Python build and Lovable page |
| Cost | INR 18,04,49,856 | Python build |
| Gain on cost | 14.14% | Python build |
| Fund return per year (XIRR) | 13.92% | Python build and Lovable page |
| Mix | 24.9 / 30.6 / 11.7 / 32.7 per cent | Overview summary |
| Total on 31 Mar 2026, 30 Jun 2026 | INR 15,59,77,517 and INR 18,45,77,457 | Python and Lovable page |
| Up since 31 Oct 2026 | INR 66.54 L (3.34%) | Overview summary |
| Next 12 months | INR 31,40,000 = SIP 24,00,000 + premiums 6,00,000 + house tax and maintenance 1,40,000 | Cash Calendar page |
| Next commitment | 5 Dec 2026, HDFC Flexi Cap Fund, INR 40,000 | Cash Calendar page |
| Insurance cover | INR 12 Cr (term 10 Cr, medical 2 Cr) | README |
| Funds value and cost | INR 5.12 Cr and INR 4.01 Cr | Mutual Funds page |
| Next deposit maturity | 10 Dec 2026, INR 1,13,90,822 | Bank and Deposits page |
| Tests | 11 tests, 209 reader checks, 108 engine questions, Excel difference INR 0 | README section 6 |
| Lovable messages | 8 | docs/Lovable_Build_Log.md |
