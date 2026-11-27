# Demo video script: Hisaab Kitaab

Length target: under 10 minutes. About 9 minutes 30 seconds at a calm pace. All data on screen is dummy data (owner BusyMe, PAN ABCDE1234F).

**Order:** problem, inputs, process (Claude, Python, Lovable), output demo, bonus (NRI treaty page), boundaries, close.

## Before recording

- Open only `dashboard/HisaabKitaab_Dashboard.html` in a browser. Window about 1440 pixels wide. Light theme. Date set to 25 Nov 2026.
- Close every other tab and window. Never show a folder, file name or mailbox that belongs to the real data. Show the project folder only.
- Steps 1 to 3 of the process are described in words. Do not open the real mailbox or the real statements on screen.
- Practise once with a timer. Cut words, not the demo.

## Timing at a glance

| Part | Start | Length |
|---|---|---|
| 1. Introduction | 0:00 | 0:35 |
| 2. Problem | 0:35 | 1:20 |
| 3. Inputs | 1:55 | 1:25 |
| 4. Process | 3:20 | 2:30 |
| 5. Output demo | 5:50 | 2:50 |
| 6. Bonus: NRI treaty page | 8:40 | 0:35 |
| 7. Boundaries and close | 9:15 | 0:40 |

---

## 1. Introduction (0:00 to 0:35)

**Show:** Project folder name on screen, then the Overview page of the dashboard.

**Say:**
Hello. My name is Jignesh Sagala, from AICA Level 2, Batch 127. This is my capstone project. It is called Hisaab Kitaab, which means accounts and records. It is one dashboard that shows everything an investor in India owns, on any date. I will show the problem, the inputs, how I built it with Claude, Python and Lovable, and then the dashboard itself. All data you see today is dummy data.

## 2. Problem (0:35 to 1:55)

**Show:** Slide-free. Stay on the Overview, or show the README problem section in the project folder.

**Say:**
An investor in India holds money in many places. Mutual funds with several fund houses. Shares with a broker. Savings accounts. Term deposits. A rented house. Insurance policies.

Every institution sends its own statement, in its own layout. Most are locked PDFs that arrive by email each month. To know what everything is worth today, the investor must collect each statement, remember each password, and add the numbers by hand. That takes time, and the investor is busy.

The numbers are also not simple. A fund bought through a monthly SIP changes its units and its average cost every month. A share bought in several lots has an average cost that must include brokerage. Value on a past date needs the price of that date, not today's price. And money going out, such as SIPs, premiums and house tax, is easy to forget.

So the investor wants one answer. What is everything worth, what did it cost, where does it sit, and what needs attention. That is the problem I solved. It fits any investor in India. For a non-resident Indian there is a bonus, which I will show at the end.

## 3. Inputs (1:55 to 3:20)

**Show:** The `db_dummy` folder with the eleven CSV files, or the table in the README. Then the `samples` folder with the six made-up PDFs.

**Say:**
The dashboard reads a small database of eleven CSV tables. Instruments, transactions, prices, bank balances, term deposits, broker cash, SIP plan, owner, properties, rent receipts and insurance. A CSV file is a plain table that opens in Excel.

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
