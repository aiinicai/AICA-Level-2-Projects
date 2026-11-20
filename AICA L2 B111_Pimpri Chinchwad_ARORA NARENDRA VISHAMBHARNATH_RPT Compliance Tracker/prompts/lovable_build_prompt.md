Build a web app called "RPT Compliance Tracker" (subtitle: "Related party transactions: Companies Act and SEBI checks, from a Tally export to Board-ready disclosures"). Audience: CFOs, company secretaries, audit committee members and auditors (Chartered Accountants) in India. Show a slim banner on every page when sample data is loaded: "Demonstration data: Sahyadri Precision Components Ltd (fictitious)".

## 1. Architecture (keep it simple)
- No database, no login, no Lovable Cloud tables. Everything runs in the browser and the uploaded file is never stored. Say on the upload screen: "Your file is processed in your browser and is not stored."
- Use the `xlsx` (SheetJS) package to read and write Excel files (read with cellDates: true).
- Put all logic in pure TypeScript modules so it can be audited:
  - src/lib/rules.ts: limits and settings (section 4) with legal source text.
  - src/lib/parse.ts: read and validate the workbook into typed rows.
  - src/lib/rpt.ts: the checks and outputs (pure functions, no React).
  - src/lib/acceptance.ts: acceptance test against expected results (section 7).
  - src/data/sampleData.ts: exact content given at the end of this message.
- The only server code is one backend function that calls Lovable AI for the audit committee summary (section 6, screen 6).

## 2. Input workbook (four sheets; match headers after trimming, case-insensitive)
- Company: columns Field, Value. Read by field-name prefix: "Company name", "Financial year under review", "FY start", "FY end", "Standalone turnover" (Rs), "Net worth" (Rs), "Consolidated turnover" (Rs).
- Transactions (Tally day book, detailed): Date, Particulars, Vch Type, Vch No., Item, Quantity, Unit, Rate, Debit Amount, Credit Amount, Nature. Amount = Debit Amount if present, else Credit Amount. Direction = "Dr" if Debit Amount is present (sale side), else "Cr" (purchase or expense side). Nature values: Sale of goods, Purchase of goods, Availing of services, Rendering of services, Leasing of property, Sale of property, Purchase of property, Office or place of profit.
- Related_Parties: Party, Relationship, Recognised under, Ind AS 24 category, Interested director or KMP, Closing balance 31-Mar-2026 (Rs), Balance nature. "Recognised under" is either "SEBI only" or another value meaning Companies Act and SEBI. Match the closing balance column by the prefix "Closing balance".
- Approvals: Approval ID, Party, Nature, Approving body (Audit Committee | Board | Shareholders), Approval type, Approval date, Valid from, Valid to, Limit (Rs), Interested director(s), Interested director stayed out (Yes | No | Not applicable), Reference.
- Dates may arrive as Excel dates or text "YYYY-MM-DD"; normalise to ISO date strings and compare as dates.
- Validation: if a sheet or column is missing, show a clear message naming it and offer the sample file download.

## 3. Upload screen (home page)
- Buttons: "Upload Excel file", "Load sample data" and "Download sample file" (build the xlsx in the browser from sampleData.ts with the exact sheet names and headers above).
- "Load sample data" must build the workbook in memory from sampleData.ts and pass it through the same parser as an uploaded file.
- A choice "Company type: Unlisted public company | Listed company" (default Unlisted). Also put a mode toggle at the top of every results page; results recalculate instantly.
- After loading, show a strip "Unlisted: N exceptions | Listed: M exceptions" (compute both modes) so the user sees the difference.

## 4. Rules and limits (src/lib/rules.ts); show all of this on a "Rules and limits" page
- ORDINARY_COURSE natures = Sale of goods, Purchase of goods, Availing of services, Rendering of services. All other natures are treated as outside the ordinary course of business.
- MARKET_TOLERANCE = 10% (screening parameter, not a legal limit).
- RULE15_PCT = 10%: goods, services and leasing are compared with standalone turnover of the preceding year; sale or purchase of property with net worth. Source: Rule 15(3), Companies (Meetings of Board and its Powers) Rules, 2014, as amended in 2019.
- RULE15_OFFICE_MONTHLY = Rs 2,50,000 monthly remuneration (Rule 15(3)(f)).
- SEBI material threshold (Schedule XII to SEBI LODR, effective 19 December 2025), on consolidated turnover T in rupees: if T ≤ 20,000 crore then 10% of T; else if T ≤ 40,000 crore then 2,000 crore + 5% of (T − 20,000 crore); else min(3,000 crore + 2.5% of (T − 40,000 crore), 5,000 crore).
- Show a table: Limit | Basis | Value for this company | Legal source | Status. Status for each: "To be verified against the current text" (I will update it later).
- List the simplifications: (1) Tally does not tag transactions by legal nature, so the file carries a Nature column; (2) the market price test is a screening test, not the legal definition of arm's length; (3) wholly owned subsidiary and private company exemptions are not modelled; (4) this is a demonstration MVP.

## 5. The checks (src/lib/rpt.ts); implement exactly
Definitions:
- FY = Company FY start to FY end. Only transactions inside the FY count.
- Related parties in scope: Unlisted mode = rows where "Recognised under" is not "SEBI only". Listed mode = all rows.
- Related party transaction (RPT) = a transaction whose Particulars matches (trim, case-insensitive) a related party in scope.
- An approval "covers" transaction t for body B when: same party, same nature, Approving body = B, Approval date ≤ t.date, and Valid from ≤ t.date ≤ Valid to.
Each check produces exception rows: check code, check name, party, nature, amount (Rs), finding, law.
- C1 Identify RPTs (no exception row; feeds the summaries).
- C2 Audit committee approval: group RPTs by (party, nature). If any transaction in the group is not covered by an Audit Committee approval, create one exception. Amount = sum of uncovered amounts. Finding: "No audit committee approval on record" if the party has no Audit Committee approval at all, otherwise "Audit committee approval had lapsed for these transactions", followed by "(n vouchers, first date to last date)". Law: "Sec 177(4)(iv) Companies Act", and in Listed mode append "; Reg 23(2) SEBI LODR".
- C3 Approved limit: for each Audit Committee approval, used = sum of RPTs with the same party and nature dated within Valid from to Valid to. If used > Limit, exception. Amount = used − Limit. Finding: "Transactions of Rs X against approved limit of Rs Y (Approval ID)". Law: "Sec 177(4)(iv), Rule 6A".
- C4 Market price: for each (related party, item) in scope, comparables = FY transactions with the same item and same direction whose party is NOT in the full related party list (all rows, including SEBI only). No comparables means "No comparable" (not tested). RP rate = sum of RP amounts ÷ sum of RP quantities; market rate = same for the comparables; deviation = RP rate ÷ market rate − 1. Flag when direction is Cr and deviation > +10%, or direction is Dr and deviation < −10%. Amount = Math.round(|RP rate − market rate| × RP quantity). Finding: "<item>: average rate Rs a vs Rs b with unrelated parties (+x.x%); estimated excess cost shown". Law: "Sec 188(1) arm's length test (screening at 10%)".
- C5 Board approval (Section 188): group RPTs by (party, nature). Section 188 applies if the nature is outside the ordinary course OR any item in the group is flagged in C4. If it applies and any transaction in the group is not covered by a Board approval, exception. Amount = group total. Finding: "Section 188 applies (not in the ordinary course of business | not at arm's length (C4)); no board approval on record". Law: "Sec 188(1) Companies Act".
- C6 Shareholder approval (Rule 15): only for groups where Section 188 applies. The group crosses the limit if: Office or place of profit, largest single transaction (monthly remuneration) > 2,50,000; Sale or Purchase of property, group total ≥ 10% of net worth; otherwise group total ≥ 10% of turnover. If it crosses and any transaction is not covered by a Shareholders approval, exception. Amount = group total. Finding states the limit crossed and "no resolution on record". Law: "Sec 188(1), Rule 15(3)".
- C7 Interested director: for each Board approval with "Interested director stayed out" = "No", if RPTs exist for that party and nature, exception. Amount = sum of those RPTs. Finding: "<Interested director(s)> did not stay out of the board decision (<Reference>)". Law: "Sec 184(2) Companies Act".
- L1 (Listed mode only): the wider SEBI definition. Parties marked "SEBI only" (promoter group, holders of 10% or more) come into scope; no separate exception row, C2 and C3 then apply to them. On the Exceptions page show a note listing the parties added in Listed mode.
- L2 Material transaction (Listed mode only): for each party, total of its RPTs in the FY (all natures). If total > SEBI threshold and any of its transactions is not covered by a Shareholders approval for that party (any nature; approval date ≤ t.date and within validity), exception. Amount = total. Finding: "Material transaction: Rs X with this party exceeds Rs Y (10% of consolidated turnover); no prior shareholder approval". Law: "Reg 23(4) and Schedule XII, SEBI LODR".
Sort exceptions by check (C2, C3, C4, C5, C6, C7, L2), then party.

## 6. Screens (left sidebar on desktop; on phones a menu button with a slide-out menu; every table scrolls horizontally on phones)
1. Upload (section 3).
2. Overview: KPI cards: Related party transactions (Rs crore), Related parties transacted with, Exceptions, Parties with exceptions. Mode badge. Bar chart of exceptions by check. The Unlisted vs Listed strip.
3. Exceptions: table with check code and plain-English check name, party, nature, amount, finding, law; filter chips by check; a one-line "What this check means" for each check.
4. Transactions: RPTs by party and nature (relationship, total, number of vouchers) with drill-down to vouchers; below it the market price test table (party, item, RP rate, market rate, deviation, result).
5. Disclosures: (a) Ind AS 24 summary for parties whose Ind AS 24 category is not "Not a related party under Ind AS 24": category, party, nature, FY amount, closing balance and its nature. (b) Form AOC-2. Part 1 "Contracts not at arm's length" = each (party, item) flagged in C4: party, relationship, nature, duration (the FY), value, board approval date ("Not obtained" if none), shareholder approval "Not applicable". Part 2 "Material contracts at arm's length" = among non-"SEBI only" parties, each (party, nature) not flagged in C4 that crosses the Rule 15 limits (same test as C6, regardless of ordinary course): party, relationship, nature, duration, value, board approval date (earliest; "Not applicable (ordinary course, arm's length)" if none), shareholder approval date (earliest; "Not obtained" if none). Note under it: "Materiality for Part 2 uses the Rule 15(3) limits in this demonstration." (c) Button "Download results (Excel)" exporting Exceptions, RPT summary, Market price test, Ind AS 24 summary and AOC-2 sheets.
6. Audit committee summary: button "Draft audit committee summary". Use Lovable AI through a backend function. Send ONLY a JSON payload of computed results: company name, FY, mode, totals, the exception list and the limits, with every amount pre-formatted in the payload (for example "Rs 7.20 crore", "Rs 36.00 lakh"). System prompt: "You are a company secretary drafting a note for the audit committee of an Indian company. Use only the figures and findings in the JSON. Never calculate, derive or invent any figure, section or fact. Cite only the law references given. Write in plain, formal Indian English, without jargon and without em dashes." Output in markdown: (1) Overview in two sentences; (2) Matters for the committee's attention, one bullet per exception; (3) Points for the committee to consider, three to five bullets phrased as considerations, not legal conclusions. Render with react-markdown and remark-gfm. Label: "Draft for review: figures from the calculation engine". Copy button. Friendly error if AI is unavailable.
7. Rules and limits (section 4) plus the acceptance test panel (section 7).

## 7. Acceptance test (src/lib/acceptance.ts)
A panel on the Rules and limits page, and a small status chip on the Overview: "Run acceptance test on sample data". It builds the sample through the same parser, runs both modes and compares with these expected results (amount tolerance ±1 rupee). Show each test as a row with pass or fail and a total "x of 24 passed".
- Limits (4 tests): Rule 15 turnover limit 48,00,00,000; Rule 15 net worth limit 22,00,00,000; office or place of profit 2,50,000; SEBI material threshold 52,00,00,000.
- Unlisted (9 tests): RPT total 1,05,56,18,816; parties transacted with 6; exception count 6; and each exception (check, party, nature, amount):
  C2, Pune Precision Gears Pvt Ltd, Sale of goods, 6,00,09,000
  C3, Deccan Tooling LLP, Purchase of goods, 1,19,99,352
  C4, Deccan Tooling LLP, Purchase of goods, 1,08,94,662
  C5, Deccan Tooling LLP, Purchase of goods, 7,19,99,352
  C6, Kavya Joshi, Office or place of profit, 36,00,000
  C7, Westghat Realty Pvt Ltd, Leasing of property, 4,80,00,000
- Listed (11 tests): RPT total 1,15,76,18,720; parties transacted with 8; exception count 8; each of the six exceptions above plus:
  C2, Konkan Logistics Ltd, Availing of services, 8,99,99,904
  L2, Sahyadri Castings Pvt Ltd, Purchase of goods, 55,20,01,464
The app must show 24 of 24 passed. Run the test yourself after building and fix the engine (not the expected values) until it passes.

## 8. Formatting and design
- Indian digit grouping everywhere (en-IN), for example 1,05,56,18,816. KPI cards in Rs crore with two decimals. Dates as 15-Dec-2025. Percentages to one decimal.
- Clean, board-ready look: white background, deep navy (#1F3864) headings, one amber accent (#C8862A) for exceptions, right-aligned numbers, tabular figures. Must read well on an iPhone (Overview, Exceptions, Rules pages especially).
- Footer on every page: "Demonstration MVP for the ICAI AICA Level 2 capstone. Not legal advice; verify limits against the current law."

## 9. Sample data
Create src/data/sampleData.ts with EXACTLY the content below (do not change any value). In parse.ts add a function that expands it into the four sheets:
- Company: the SAMPLE_COMPANY pairs.
- Transactions: for each row [d, p, vchType, vchNo, i, q, r, side, amount] of SAMPLE_TX_COMPACT: Date = d, Particulars = SAMPLE_PARTIES[p], Vch Type = vchType, Vch No. = vchNo, Item = SAMPLE_ITEMS[i][0], Quantity = q, Unit = SAMPLE_ITEMS[i][1], Rate = r, Debit Amount = amount if side is "D" else empty, Credit Amount = amount if side is "C" else empty, Nature = SAMPLE_ITEMS[i][2].
- Related_Parties and Approvals: the header arrays and rows given.

```ts
// Sample data: Sahyadri Precision Components Ltd (fictitious). Generated by gen_rpt.py. Do not edit.
export const SAMPLE_COMPANY: [string, string | number][] = [["Company name","Sahyadri Precision Components Ltd"],["Company type","Public company with an audit committee (listing status chosen at upload)"],["Financial year under review","2025-26"],["FY start","2025-04-01"],["FY end","2026-03-31"],["Standalone turnover, FY 2024-25 (Rs)",4800000000],["Net worth at 31-Mar-2025 (Rs)",2200000000],["Consolidated turnover, FY 2024-25 (Rs)",5200000000],["Paid-up share capital (Rs)",250000000]];
export const SAMPLE_RP_HEADERS = ["Party","Relationship","Recognised under","Ind AS 24 category","Interested director or KMP","Closing balance 31-Mar-2026 (Rs)","Balance nature"];
export const SAMPLE_RP: (string | number)[][] = [["Sahyadri Holdings Pvt Ltd","Holding company (holds 52%)","Companies Act, SEBI and Ind AS 24","Holding company","Mr Vikram Joshi (MD, common director)",60000000,"Receivable"],["Sahyadri Castings Pvt Ltd","Subsidiary (74% held)","Companies Act, SEBI and Ind AS 24","Subsidiary","",92000000,"Payable"],["Pune Precision Gears Pvt Ltd","Associate (30% held)","Companies Act, SEBI and Ind AS 24","Associate","",21000000,"Receivable"],["Deccan Tooling LLP","LLP in which the MD is a partner","Companies Act, SEBI and Ind AS 24","Entity controlled by KMP","Mr Vikram Joshi (MD)",12500000,"Payable"],["Westghat Realty Pvt Ltd","Private company in which a director is a director and member","Companies Act, SEBI and Ind AS 24","Entity in which a director has significant influence","Ms Anita Rao (Non-executive director)",4000000,"Payable"],["Kavya Joshi","Daughter of the MD (relative)","Companies Act, SEBI and Ind AS 24","Close member of the family of KMP","Mr Vikram Joshi (MD)",300000,"Payable"],["Konkan Logistics Ltd","Promoter group entity","SEBI only","Not a related party under Ind AS 24","",7500000,"Payable"],["Nilgiri Capital Advisors LLP","Shareholder holding 12%","SEBI only","Not a related party under Ind AS 24","",1000000,"Payable"]];
export const SAMPLE_AP_HEADERS = ["Approval ID","Party","Nature","Approving body","Approval type","Approval date","Valid from","Valid to","Limit (Rs)","Interested director(s)","Interested director stayed out","Reference"];
export const SAMPLE_AP: (string | number)[][] = [["A01","Sahyadri Castings Pvt Ltd","Purchase of goods","Audit Committee","Omnibus","2025-03-27","2025-04-01","2026-03-31",600000000,"","Not applicable","AC/2024-25/14"],["A02","Deccan Tooling LLP","Purchase of goods","Audit Committee","Omnibus","2025-03-27","2025-04-01","2026-03-31",60000000,"Mr Vikram Joshi","Not applicable","AC/2024-25/15"],["A03","Pune Precision Gears Pvt Ltd","Sale of goods","Audit Committee","Omnibus","2025-03-27","2025-04-01","2025-09-30",150000000,"","Not applicable","AC/2024-25/16"],["A04","Westghat Realty Pvt Ltd","Leasing of property","Audit Committee","Specific","2025-03-27","2025-04-01","2026-03-31",48000000,"Ms Anita Rao","Not applicable","AC/2024-25/17"],["A05","Westghat Realty Pvt Ltd","Leasing of property","Board","Specific","2025-03-28","2025-04-01","2026-03-31",48000000,"Ms Anita Rao","No","BM/2024-25/22"],["A06","Kavya Joshi","Office or place of profit","Audit Committee","Specific","2025-03-27","2025-04-01","2026-03-31",3600000,"Mr Vikram Joshi","Not applicable","AC/2024-25/18"],["A07","Kavya Joshi","Office or place of profit","Board","Specific","2025-03-28","2025-04-01","2026-03-31",3600000,"Mr Vikram Joshi","Yes","BM/2024-25/23"],["A08","Sahyadri Holdings Pvt Ltd","Sale of property","Audit Committee","Specific","2025-10-20","2025-10-20","2026-03-31",260000000,"Mr Vikram Joshi","Not applicable","AC/2025-26/09"],["A09","Sahyadri Holdings Pvt Ltd","Sale of property","Board","Specific","2025-10-22","2025-10-22","2026-03-31",260000000,"Mr Vikram Joshi","Yes","BM/2025-26/11"],["A10","Sahyadri Holdings Pvt Ltd","Sale of property","Shareholders","Specific","2025-11-25","2025-11-25","2026-03-31",260000000,"Related parties did not vote","Yes","EGM/2025-26/01"],["A11","Nilgiri Capital Advisors LLP","Availing of services","Audit Committee","Specific","2025-03-27","2025-04-01","2026-03-31",15000000,"","Not applicable","AC/2024-25/19"]];
export const SAMPLE_TX_HEADERS = ["Date","Particulars","Vch Type","Vch No.","Item","Quantity","Unit","Rate","Debit Amount","Credit Amount","Nature"];
export const SAMPLE_PARTIES = ["Westghat Realty Pvt Ltd","Sahyadri Castings Pvt Ltd","Bharat Foundry Works","Malwa Castings Ltd","Deccan Tooling LLP","Precision Tools India","Toolcraft Engineers","Pune Precision Gears Pvt Ltd","Ashoka Motors Ltd","Narmada Tractors Ltd","Coromandel Auto Parts Ltd","Satpura Engineering Ltd","Indus Earthmovers Ltd","Kavya Joshi","Konkan Logistics Ltd","Shree Ganesh Roadways","Western Cargo Movers","Nilgiri Capital Advisors LLP","Sahyadri Holdings Pvt Ltd"];
export const SAMPLE_ITEMS: [string, string, string][] = [["Office rent","month","Leasing of property"],["MS castings","kg","Purchase of goods"],["Carbide inserts","pcs","Purchase of goods"],["Gear assembly GA-200","nos","Sale of goods"],["Salary","month","Office or place of profit"],["Freight","trips","Availing of services"],["Advisory retainer","month","Availing of services"],["Land at Chakan, Plot 14","plot","Sale of property"]];
// [date, party index, Vch Type, Vch No., item index, quantity, rate, D or C, amount]
export const SAMPLE_TX_COMPACT: [string, number, string, string, number, number, number, "D" | "C", number][] = [
["2025-04-01",0,"Journal","JO/0001",0,1,4000000,"C",4000000],
["2025-04-08",1,"Purchase","PU/0001",1,156463,147,"C",23000061],
["2025-04-08",2,"Purchase","PU/0002",1,46288,146.9,"C",6799707],
["2025-04-08",3,"Purchase","PU/0003",1,52009,147.67,"C",7680169],
["2025-04-08",4,"Purchase","PU/0007",2,2991,1003,"C",2999973],
["2025-04-08",5,"Purchase","PU/0008",2,2383,832.09,"C",1982870],
["2025-04-08",6,"Purchase","PU/0009",2,2324,844.78,"C",1963269],
["2025-04-08",7,"Sales","SA/0001",3,1205,4150,"D",5000750],
["2025-04-08",8,"Sales","SA/0002",3,6318,4288.71,"D",27096070],
["2025-04-08",9,"Sales","SA/0003",3,3549,4248.71,"D",15078672],
["2025-04-08",10,"Sales","SA/0004",3,6864,4269.58,"D",29306397],
["2025-04-08",11,"Sales","SA/0005",3,6663,4239.15,"D",28245456],
["2025-04-08",12,"Sales","SA/0006",3,6157,4238.65,"D",26097368],
["2025-04-22",1,"Purchase","PU/0004",1,156463,147,"C",23000061],
["2025-04-22",2,"Purchase","PU/0005",1,50083,146.22,"C",7323136],
["2025-04-22",3,"Purchase","PU/0006",1,49180,148.4,"C",7298312],
["2025-04-22",4,"Purchase","PU/0010",2,2991,1003,"C",2999973],
["2025-04-22",5,"Purchase","PU/0011",2,2180,864.35,"C",1884283],
["2025-04-22",6,"Purchase","PU/0012",2,2175,860.17,"C",1870870],
["2025-04-22",7,"Sales","SA/0007",3,1205,4150,"D",5000750],
["2025-04-22",8,"Sales","SA/0008",3,6151,4286.45,"D",26365954],
["2025-04-22",9,"Sales","SA/0009",3,6849,4127.06,"D",28266234],
["2025-04-22",10,"Sales","SA/0010",3,3821,4263.59,"D",16291177],
["2025-04-22",11,"Sales","SA/0011",3,5839,4205.65,"D",24556790],
["2025-04-22",12,"Sales","SA/0012",3,4461,4315.03,"D",19249349],
["2025-04-28",13,"Journal","JO/0002",4,1,300000,"C",300000],
["2025-04-28",14,"Purchase","PU/0013",5,195,38461.5,"C",7499992],
["2025-04-28",15,"Purchase","PU/0014",5,102,37472,"C",3822144],
["2025-04-28",16,"Purchase","PU/0015",5,94,39120,"C",3677280],
["2025-04-28",17,"Purchase","PU/0016",6,1,1000000,"C",1000000],
["2025-05-01",0,"Journal","JO/0003",0,1,4000000,"C",4000000],
["2025-05-08",1,"Purchase","PU/0017",1,156463,147,"C",23000061],
["2025-05-08",2,"Purchase","PU/0018",1,52779,145.04,"C",7655066],
["2025-05-08",3,"Purchase","PU/0019",1,56458,148.56,"C",8387400],
["2025-05-08",4,"Purchase","PU/0023",2,2991,1003,"C",2999973],
["2025-05-08",5,"Purchase","PU/0024",2,2518,852.87,"C",2147527],
["2025-05-08",6,"Purchase","PU/0025",2,2397,858.29,"C",2057321],
["2025-05-08",7,"Sales","SA/0013",3,1205,4150,"D",5000750],
["2025-05-08",8,"Sales","SA/0014",3,4502,4302.8,"D",19371206],
["2025-05-08",9,"Sales","SA/0015",3,3627,4218.23,"D",15299520],
["2025-05-08",10,"Sales","SA/0016",3,5089,4116.44,"D",20948563],
["2025-05-08",11,"Sales","SA/0017",3,4926,4280.55,"D",21085989],
["2025-05-08",12,"Sales","SA/0018",3,4948,4281.85,"D",21186594],
["2025-05-22",1,"Purchase","PU/0020",1,156463,147,"C",23000061],
["2025-05-22",2,"Purchase","PU/0021",1,47365,144.15,"C",6827665],
["2025-05-22",3,"Purchase","PU/0022",1,46796,141.51,"C",6622102],
["2025-05-22",4,"Purchase","PU/0026",2,2991,1003,"C",2999973],
["2025-05-22",5,"Purchase","PU/0027",2,2479,869.56,"C",2155639],
["2025-05-22",6,"Purchase","PU/0028",2,2287,860.88,"C",1968833],
["2025-05-22",7,"Sales","SA/0019",3,1205,4150,"D",5000750],
["2025-05-22",8,"Sales","SA/0020",3,5893,4141.37,"D",24405093],
["2025-05-22",9,"Sales","SA/0021",3,4604,4165.49,"D",19177916],
["2025-05-22",10,"Sales","SA/0022",3,4374,4301.15,"D",18813230],
["2025-05-22",11,"Sales","SA/0023",3,6590,4157.66,"D",27398979],
["2025-05-22",12,"Sales","SA/0024",3,7111,4094.66,"D",29117127],
["2025-05-28",13,"Journal","JO/0004",4,1,300000,"C",300000],
["2025-05-28",14,"Purchase","PU/0029",5,195,38461.5,"C",7499992],
["2025-05-28",15,"Purchase","PU/0030",5,110,38164,"C",4198040],
["2025-05-28",16,"Purchase","PU/0031",5,90,38292,"C",3446280],
["2025-05-28",17,"Purchase","PU/0032",6,1,1000000,"C",1000000],
["2025-06-01",0,"Journal","JO/0005",0,1,4000000,"C",4000000],
["2025-06-08",1,"Purchase","PU/0033",1,156463,147,"C",23000061],
["2025-06-08",2,"Purchase","PU/0034",1,49428,148.62,"C",7345989],
["2025-06-08",3,"Purchase","PU/0035",1,54934,142.53,"C",7829743],
["2025-06-08",4,"Purchase","PU/0039",2,2991,1003,"C",2999973],
["2025-06-08",5,"Purchase","PU/0040",2,2278,849.96,"C",1936209],
["2025-06-08",6,"Purchase","PU/0041",2,2268,834.53,"C",1892714],
["2025-06-08",7,"Sales","SA/0025",3,1205,4150,"D",5000750],
["2025-06-08",8,"Sales","SA/0026",3,3659,4288.91,"D",15693122],
["2025-06-08",9,"Sales","SA/0027",3,6338,4160.33,"D",26368172],
["2025-06-08",10,"Sales","SA/0028",3,6563,4189.91,"D",27498379],
["2025-06-08",11,"Sales","SA/0029",3,6150,4184.84,"D",25736766],
["2025-06-08",12,"Sales","SA/0030",3,5073,4273.52,"D",21679567],
["2025-06-22",1,"Purchase","PU/0036",1,156463,147,"C",23000061],
["2025-06-22",2,"Purchase","PU/0037",1,53693,144.01,"C",7732329],
["2025-06-22",3,"Purchase","PU/0038",1,46413,141.13,"C",6550267],
["2025-06-22",4,"Purchase","PU/0042",2,2991,1003,"C",2999973],
["2025-06-22",5,"Purchase","PU/0043",2,2435,852.01,"C",2074644],
["2025-06-22",6,"Purchase","PU/0044",2,2319,861.51,"C",1997842],
["2025-06-22",7,"Sales","SA/0031",3,1205,4150,"D",5000750],
["2025-06-22",8,"Sales","SA/0032",3,6341,4203.85,"D",26656613],
["2025-06-22",9,"Sales","SA/0033",3,3588,4253.59,"D",15261881],
["2025-06-22",10,"Sales","SA/0034",3,6748,4279.72,"D",28879551],
["2025-06-22",11,"Sales","SA/0035",3,4997,4264.45,"D",21309457],
["2025-06-22",12,"Sales","SA/0036",3,6080,4300.77,"D",26148682],
["2025-06-28",13,"Journal","JO/0006",4,1,300000,"C",300000],
["2025-06-28",14,"Purchase","PU/0045",5,195,38461.5,"C",7499992],
["2025-06-28",15,"Purchase","PU/0046",5,89,37019,"C",3294691],
["2025-06-28",16,"Purchase","PU/0047",5,91,38559,"C",3508869],
["2025-06-28",17,"Purchase","PU/0048",6,1,1000000,"C",1000000],
["2025-07-01",0,"Journal","JO/0007",0,1,4000000,"C",4000000],
["2025-07-08",1,"Purchase","PU/0049",1,156463,147,"C",23000061],
["2025-07-08",2,"Purchase","PU/0050",1,47879,143.95,"C",6892182],
["2025-07-08",3,"Purchase","PU/0051",1,51521,148.98,"C",7675599],
["2025-07-08",4,"Purchase","PU/0055",2,2991,1003,"C",2999973],
["2025-07-08",5,"Purchase","PU/0056",2,2419,867.75,"C",2099087],
["2025-07-08",6,"Purchase","PU/0057",2,2179,832.21,"C",1813386],
["2025-07-08",7,"Sales","SA/0037",3,1205,4150,"D",5000750],
["2025-07-08",8,"Sales","SA/0038",3,4719,4092.51,"D",19312555],
["2025-07-08",9,"Sales","SA/0039",3,5009,4194.75,"D",21011503],
["2025-07-08",10,"Sales","SA/0040",3,6184,4160.93,"D",25731191],
["2025-07-08",11,"Sales","SA/0041",3,4383,4298.6,"D",18840764],
["2025-07-08",12,"Sales","SA/0042",3,5654,4246.5,"D",24009711],
["2025-07-22",1,"Purchase","PU/0052",1,156463,147,"C",23000061],
["2025-07-22",2,"Purchase","PU/0053",1,49810,144.08,"C",7176625],
["2025-07-22",3,"Purchase","PU/0054",1,56484,143.79,"C",8121834],
["2025-07-22",4,"Purchase","PU/0058",2,2991,1003,"C",2999973],
["2025-07-22",5,"Purchase","PU/0059",2,2340,835.79,"C",1955749],
["2025-07-22",6,"Purchase","PU/0060",2,2082,867.04,"C",1805177],
["2025-07-22",7,"Sales","SA/0043",3,1205,4150,"D",5000750],
["2025-07-22",8,"Sales","SA/0044",3,5241,4207.9,"D",22053604],
["2025-07-22",9,"Sales","SA/0045",3,5053,4176.53,"D",21104006],
["2025-07-22",10,"Sales","SA/0046",3,3731,4182.09,"D",15603378],
["2025-07-22",11,"Sales","SA/0047",3,3847,4172.71,"D",16052415],
["2025-07-22",12,"Sales","SA/0048",3,7064,4218.91,"D",29802380],
["2025-07-28",13,"Journal","JO/0008",4,1,300000,"C",300000],
["2025-07-28",14,"Purchase","PU/0061",5,195,38461.5,"C",7499992],
["2025-07-28",15,"Purchase","PU/0062",5,98,37388,"C",3664024],
["2025-07-28",16,"Purchase","PU/0063",5,95,38572,"C",3664340],
["2025-07-28",17,"Purchase","PU/0064",6,1,1000000,"C",1000000],
["2025-08-01",0,"Journal","JO/0009",0,1,4000000,"C",4000000],
["2025-08-08",1,"Purchase","PU/0065",1,156463,147,"C",23000061],
["2025-08-08",2,"Purchase","PU/0066",1,44512,147.04,"C",6545044],
["2025-08-08",3,"Purchase","PU/0067",1,45373,145.13,"C",6584983],
["2025-08-08",4,"Purchase","PU/0071",2,2991,1003,"C",2999973],
["2025-08-08",5,"Purchase","PU/0072",2,2445,838.01,"C",2048934],
["2025-08-08",6,"Purchase","PU/0073",2,2418,853.52,"C",2063811],
["2025-08-08",7,"Sales","SA/0049",3,1205,4150,"D",5000750],
["2025-08-08",8,"Sales","SA/0050",3,5959,4282.53,"D",25519596],
["2025-08-08",9,"Sales","SA/0051",3,3994,4132.68,"D",16505924],
["2025-08-08",10,"Sales","SA/0052",3,5884,4146.06,"D",24395417],
["2025-08-08",11,"Sales","SA/0053",3,5725,4236.6,"D",24254535],
["2025-08-08",12,"Sales","SA/0054",3,7018,4118.63,"D",28904545],
["2025-08-22",1,"Purchase","PU/0068",1,156463,147,"C",23000061],
["2025-08-22",2,"Purchase","PU/0069",1,47988,143.99,"C",6909792],
["2025-08-22",3,"Purchase","PU/0070",1,51264,147.82,"C",7577844],
["2025-08-22",4,"Purchase","PU/0074",2,2991,1003,"C",2999973],
["2025-08-22",5,"Purchase","PU/0075",2,2274,840.77,"C",1911911],
["2025-08-22",6,"Purchase","PU/0076",2,2269,845.09,"C",1917509],
["2025-08-22",7,"Sales","SA/0055",3,1205,4150,"D",5000750],
["2025-08-22",8,"Sales","SA/0056",3,3735,4272.74,"D",15958684],
["2025-08-22",9,"Sales","SA/0057",3,4793,4304.85,"D",20633146],
["2025-08-22",10,"Sales","SA/0058",3,4354,4085.31,"D",17787440],
["2025-08-22",11,"Sales","SA/0059",3,6660,4206.48,"D",28015157],
["2025-08-22",12,"Sales","SA/0060",3,3994,4182.62,"D",16705384],
["2025-08-28",13,"Journal","JO/0010",4,1,300000,"C",300000],
["2025-08-28",14,"Purchase","PU/0077",5,195,38461.5,"C",7499992],
["2025-08-28",15,"Purchase","PU/0078",5,120,38320,"C",4598400],
["2025-08-28",16,"Purchase","PU/0079",5,106,38777,"C",4110362],
["2025-08-28",17,"Purchase","PU/0080",6,1,1000000,"C",1000000],
["2025-09-01",0,"Journal","JO/0011",0,1,4000000,"C",4000000],
["2025-09-08",1,"Purchase","PU/0081",1,156463,147,"C",23000061],
["2025-09-08",2,"Purchase","PU/0082",1,56214,142.89,"C",8032418],
["2025-09-08",3,"Purchase","PU/0083",1,45227,148.06,"C",6696310],
["2025-09-08",4,"Purchase","PU/0087",2,2991,1003,"C",2999973],
["2025-09-08",5,"Purchase","PU/0088",2,2243,833.12,"C",1868688],
["2025-09-08",6,"Purchase","PU/0089",2,2556,846.81,"C",2164446],
["2025-09-08",7,"Sales","SA/0061",3,1205,4150,"D",5000750],
["2025-09-08",8,"Sales","SA/0062",3,6245,4280.75,"D",26733284],
["2025-09-08",9,"Sales","SA/0063",3,6009,4290.64,"D",25782456],
["2025-09-08",10,"Sales","SA/0064",3,6078,4148.98,"D",25217500],
["2025-09-08",11,"Sales","SA/0065",3,4285,4272.39,"D",18307191],
["2025-09-08",12,"Sales","SA/0066",3,4695,4275.56,"D",20073754],
["2025-09-22",1,"Purchase","PU/0084",1,156463,147,"C",23000061],
["2025-09-22",2,"Purchase","PU/0085",1,58548,143.15,"C",8381146],
["2025-09-22",3,"Purchase","PU/0086",1,49803,145.27,"C",7234882],
["2025-09-22",4,"Purchase","PU/0090",2,2991,1003,"C",2999973],
["2025-09-22",5,"Purchase","PU/0091",2,2489,832.74,"C",2072690],
["2025-09-22",6,"Purchase","PU/0092",2,2384,831.61,"C",1982558],
["2025-09-22",7,"Sales","SA/0067",3,1205,4150,"D",5000750],
["2025-09-22",8,"Sales","SA/0068",3,4109,4268.1,"D",17537623],
["2025-09-22",9,"Sales","SA/0069",3,6118,4263.71,"D",26085378],
["2025-09-22",10,"Sales","SA/0070",3,5728,4130.55,"D",23659790],
["2025-09-22",11,"Sales","SA/0071",3,7225,4101.84,"D",29635794],
["2025-09-22",12,"Sales","SA/0072",3,6227,4243.84,"D",26426392],
["2025-09-28",13,"Journal","JO/0012",4,1,300000,"C",300000],
["2025-09-28",14,"Purchase","PU/0093",5,195,38461.5,"C",7499992],
["2025-09-28",15,"Purchase","PU/0094",5,118,37629,"C",4440222],
["2025-09-28",16,"Purchase","PU/0095",5,111,38753,"C",4301583],
["2025-09-28",17,"Purchase","PU/0096",6,1,1000000,"C",1000000],
["2025-10-01",0,"Journal","JO/0013",0,1,4000000,"C",4000000],
["2025-10-08",1,"Purchase","PU/0097",1,156463,147,"C",23000061],
["2025-10-08",2,"Purchase","PU/0098",1,57045,147.54,"C",8416419],
["2025-10-08",3,"Purchase","PU/0099",1,48183,141.09,"C",6798139],
["2025-10-08",4,"Purchase","PU/0103",2,2991,1003,"C",2999973],
["2025-10-08",5,"Purchase","PU/0104",2,2564,847.14,"C",2172067],
["2025-10-08",6,"Purchase","PU/0105",2,2320,845.12,"C",1960678],
["2025-10-08",7,"Sales","SA/0073",3,1205,4150,"D",5000750],
["2025-10-08",8,"Sales","SA/0074",3,5129,4303.81,"D",22074241],
["2025-10-08",9,"Sales","SA/0075",3,5212,4165.67,"D",21711472],
["2025-10-08",10,"Sales","SA/0076",3,3996,4291.07,"D",17147116],
["2025-10-08",11,"Sales","SA/0077",3,5438,4255.26,"D",23140104],
["2025-10-08",12,"Sales","SA/0078",3,6886,4250.11,"D",29266257],
["2025-10-22",1,"Purchase","PU/0100",1,156463,147,"C",23000061],
["2025-10-22",2,"Purchase","PU/0101",1,51439,147.87,"C",7606285],
["2025-10-22",3,"Purchase","PU/0102",1,46952,143.48,"C",6736673],
["2025-10-22",4,"Purchase","PU/0106",2,2991,1003,"C",2999973],
["2025-10-22",5,"Purchase","PU/0107",2,2551,861.66,"C",2198095],
["2025-10-22",6,"Purchase","PU/0108",2,2269,836.25,"C",1897451],
["2025-10-22",7,"Sales","SA/0079",3,1205,4150,"D",5000750],
["2025-10-22",8,"Sales","SA/0080",3,6469,4097.76,"D",26508409],
["2025-10-22",9,"Sales","SA/0081",3,4509,4112.2,"D",18541910],
["2025-10-22",10,"Sales","SA/0082",3,6545,4175.48,"D",27328517],
["2025-10-22",11,"Sales","SA/0083",3,6083,4172.37,"D",25380527],
["2025-10-22",12,"Sales","SA/0084",3,4263,4167.33,"D",17765328],
["2025-10-28",13,"Journal","JO/0014",4,1,300000,"C",300000],
["2025-10-28",14,"Purchase","PU/0109",5,195,38461.5,"C",7499992],
["2025-10-28",15,"Purchase","PU/0110",5,88,39436,"C",3470368],
["2025-10-28",16,"Purchase","PU/0111",5,117,39234,"C",4590378],
["2025-10-28",17,"Purchase","PU/0112",6,1,1000000,"C",1000000],
["2025-11-01",0,"Journal","JO/0015",0,1,4000000,"C",4000000],
["2025-11-08",1,"Purchase","PU/0113",1,156463,147,"C",23000061],
["2025-11-08",2,"Purchase","PU/0114",1,55839,142.38,"C",7950357],
["2025-11-08",3,"Purchase","PU/0115",1,45980,148.4,"C",6823432],
["2025-11-08",4,"Purchase","PU/0119",2,2991,1003,"C",2999973],
["2025-11-08",5,"Purchase","PU/0120",2,2442,832.93,"C",2034015],
["2025-11-08",6,"Purchase","PU/0121",2,2158,860.29,"C",1856506],
["2025-11-08",7,"Sales","SA/0085",3,1205,4150,"D",5000750],
["2025-11-08",8,"Sales","SA/0086",3,5368,4290.68,"D",23032370],
["2025-11-08",9,"Sales","SA/0087",3,3758,4262.92,"D",16020053],
["2025-11-08",10,"Sales","SA/0088",3,4781,4253.29,"D",20334979],
["2025-11-08",11,"Sales","SA/0089",3,6927,4296.51,"D",29761925],
["2025-11-08",12,"Sales","SA/0090",3,3708,4241.73,"D",15728335],
["2025-11-22",1,"Purchase","PU/0116",1,156463,147,"C",23000061],
["2025-11-22",2,"Purchase","PU/0117",1,45811,148.38,"C",6797436],
["2025-11-22",3,"Purchase","PU/0118",1,46531,143.4,"C",6672545],
["2025-11-22",4,"Purchase","PU/0122",2,2991,1003,"C",2999973],
["2025-11-22",5,"Purchase","PU/0123",2,2093,867.46,"C",1815594],
["2025-11-22",6,"Purchase","PU/0124",2,2356,844.64,"C",1989972],
["2025-11-22",7,"Sales","SA/0091",3,1205,4150,"D",5000750],
["2025-11-22",8,"Sales","SA/0092",3,6846,4296.2,"D",29411785],
["2025-11-22",9,"Sales","SA/0093",3,5184,4314.49,"D",22366316],
["2025-11-22",10,"Sales","SA/0094",3,6420,4221.39,"D",27101324],
["2025-11-22",11,"Sales","SA/0095",3,5438,4298.24,"D",23373829],
["2025-11-22",12,"Sales","SA/0096",3,6922,4240.7,"D",29354125],
["2025-11-28",13,"Journal","JO/0016",4,1,300000,"C",300000],
["2025-11-28",14,"Purchase","PU/0125",5,195,38461.5,"C",7499992],
["2025-11-28",15,"Purchase","PU/0126",5,109,38878,"C",4237702],
["2025-11-28",16,"Purchase","PU/0127",5,97,39386,"C",3820442],
["2025-11-28",17,"Purchase","PU/0128",6,1,1000000,"C",1000000],
["2025-12-01",0,"Journal","JO/0017",0,1,4000000,"C",4000000],
["2025-12-08",1,"Purchase","PU/0129",1,156463,147,"C",23000061],
["2025-12-08",2,"Purchase","PU/0130",1,57551,144.14,"C",8295401],
["2025-12-08",3,"Purchase","PU/0131",1,59270,143.06,"C",8479166],
["2025-12-08",4,"Purchase","PU/0135",2,2991,1003,"C",2999973],
["2025-12-08",5,"Purchase","PU/0136",2,2527,841.81,"C",2127254],
["2025-12-08",6,"Purchase","PU/0137",2,2162,840.46,"C",1817075],
["2025-12-08",7,"Sales","SA/0097",3,1205,4150,"D",5000750],
["2025-12-08",8,"Sales","SA/0098",3,5693,4201.69,"D",23920221],
["2025-12-08",9,"Sales","SA/0099",3,4809,4291.35,"D",20637102],
["2025-12-08",10,"Sales","SA/0100",3,6809,4145.78,"D",28228616],
["2025-12-08",11,"Sales","SA/0101",3,6245,4160.22,"D",25980574],
["2025-12-08",12,"Sales","SA/0102",3,4998,4112.43,"D",20553925],
["2025-12-15",18,"Journal","JO/0025",7,1,260000000,"D",260000000],
["2025-12-22",1,"Purchase","PU/0132",1,156463,147,"C",23000061],
["2025-12-22",2,"Purchase","PU/0133",1,52515,142.6,"C",7488639],
["2025-12-22",3,"Purchase","PU/0134",1,45139,148.41,"C",6699079],
["2025-12-22",4,"Purchase","PU/0138",2,2991,1003,"C",2999973],
["2025-12-22",5,"Purchase","PU/0139",2,2349,854.99,"C",2008372],
["2025-12-22",6,"Purchase","PU/0140",2,2537,863.14,"C",2189786],
["2025-12-22",7,"Sales","SA/0103",3,1205,4150,"D",5000750],
["2025-12-22",8,"Sales","SA/0104",3,4485,4319.95,"D",19374976],
["2025-12-22",9,"Sales","SA/0105",3,5536,4147.42,"D",22960117],
["2025-12-22",10,"Sales","SA/0106",3,3925,4271.21,"D",16764499],
["2025-12-22",11,"Sales","SA/0107",3,5331,4305.05,"D",22950222],
["2025-12-22",12,"Sales","SA/0108",3,4324,4314.15,"D",18654385],
["2025-12-28",13,"Journal","JO/0018",4,1,300000,"C",300000],
["2025-12-28",14,"Purchase","PU/0141",5,195,38461.5,"C",7499992],
["2025-12-28",15,"Purchase","PU/0142",5,109,37804,"C",4120636],
["2025-12-28",16,"Purchase","PU/0143",5,114,39369,"C",4488066],
["2025-12-28",17,"Purchase","PU/0144",6,1,1000000,"C",1000000],
["2026-01-01",0,"Journal","JO/0019",0,1,4000000,"C",4000000],
["2026-01-08",1,"Purchase","PU/0145",1,156463,147,"C",23000061],
["2026-01-08",2,"Purchase","PU/0146",1,45158,146.34,"C",6608422],
["2026-01-08",3,"Purchase","PU/0147",1,46774,141.02,"C",6596069],
["2026-01-08",4,"Purchase","PU/0151",2,2991,1003,"C",2999973],
["2026-01-08",5,"Purchase","PU/0152",2,2307,850.06,"C",1961088],
["2026-01-08",6,"Purchase","PU/0153",2,2457,863.63,"C",2121939],
["2026-01-08",7,"Sales","SA/0109",3,1205,4150,"D",5000750],
["2026-01-08",8,"Sales","SA/0110",3,4008,4108.83,"D",16468191],
["2026-01-08",9,"Sales","SA/0111",3,5865,4162.9,"D",24415408],
["2026-01-08",10,"Sales","SA/0112",3,6947,4316.51,"D",29986795],
["2026-01-08",11,"Sales","SA/0113",3,5749,4277.08,"D",24588933],
["2026-01-08",12,"Sales","SA/0114",3,4350,4167.82,"D",18130017],
["2026-01-22",1,"Purchase","PU/0148",1,156463,147,"C",23000061],
["2026-01-22",2,"Purchase","PU/0149",1,54724,141.66,"C",7752202],
["2026-01-22",3,"Purchase","PU/0150",1,55978,141.63,"C",7928164],
["2026-01-22",4,"Purchase","PU/0154",2,2991,1003,"C",2999973],
["2026-01-22",5,"Purchase","PU/0155",2,2515,869.76,"C",2187446],
["2026-01-22",6,"Purchase","PU/0156",2,2504,865.2,"C",2166461],
["2026-01-22",7,"Sales","SA/0115",3,1205,4150,"D",5000750],
["2026-01-22",8,"Sales","SA/0116",3,4196,4295.56,"D",18024170],
["2026-01-22",9,"Sales","SA/0117",3,3917,4190.93,"D",16415873],
["2026-01-22",10,"Sales","SA/0118",3,6681,4105.4,"D",27428177],
["2026-01-22",11,"Sales","SA/0119",3,5256,4314.49,"D",22676959],
["2026-01-22",12,"Sales","SA/0120",3,4706,4084.25,"D",19220480],
["2026-01-28",13,"Journal","JO/0020",4,1,300000,"C",300000],
["2026-01-28",14,"Purchase","PU/0157",5,195,38461.5,"C",7499992],
["2026-01-28",15,"Purchase","PU/0158",5,85,37841,"C",3216485],
["2026-01-28",16,"Purchase","PU/0159",5,100,38052,"C",3805200],
["2026-01-28",17,"Purchase","PU/0160",6,1,1000000,"C",1000000],
["2026-02-01",0,"Journal","JO/0021",0,1,4000000,"C",4000000],
["2026-02-08",1,"Purchase","PU/0161",1,156463,147,"C",23000061],
["2026-02-08",2,"Purchase","PU/0162",1,54616,141.73,"C",7740726],
["2026-02-08",3,"Purchase","PU/0163",1,51685,144.44,"C",7465381],
["2026-02-08",4,"Purchase","PU/0167",2,2991,1003,"C",2999973],
["2026-02-08",5,"Purchase","PU/0168",2,2147,865.84,"C",1858958],
["2026-02-08",6,"Purchase","PU/0169",2,2270,864.55,"C",1962528],
["2026-02-08",7,"Sales","SA/0121",3,1205,4150,"D",5000750],
["2026-02-08",8,"Sales","SA/0122",3,5768,4124.82,"D",23791962],
["2026-02-08",9,"Sales","SA/0123",3,6460,4226.89,"D",27305709],
["2026-02-08",10,"Sales","SA/0124",3,4788,4307.49,"D",20624262],
["2026-02-08",11,"Sales","SA/0125",3,5829,4234.72,"D",24684183],
["2026-02-08",12,"Sales","SA/0126",3,4235,4237.1,"D",17944118],
["2026-02-22",1,"Purchase","PU/0164",1,156463,147,"C",23000061],
["2026-02-22",2,"Purchase","PU/0165",1,58300,145.27,"C",8469241],
["2026-02-22",3,"Purchase","PU/0166",1,48160,144.49,"C",6958638],
["2026-02-22",4,"Purchase","PU/0170",2,2991,1003,"C",2999973],
["2026-02-22",5,"Purchase","PU/0171",2,2247,846.75,"C",1902647],
["2026-02-22",6,"Purchase","PU/0172",2,2272,865.29,"C",1965939],
["2026-02-22",7,"Sales","SA/0127",3,1205,4150,"D",5000750],
["2026-02-22",8,"Sales","SA/0128",3,5430,4299.08,"D",23344004],
["2026-02-22",9,"Sales","SA/0129",3,6846,4258.65,"D",29154718],
["2026-02-22",10,"Sales","SA/0130",3,4199,4269.9,"D",17929310],
["2026-02-22",11,"Sales","SA/0131",3,5573,4182.21,"D",23307456],
["2026-02-22",12,"Sales","SA/0132",3,5668,4198.82,"D",23798912],
["2026-02-27",13,"Journal","JO/0022",4,1,300000,"C",300000],
["2026-02-28",14,"Purchase","PU/0173",5,195,38461.5,"C",7499992],
["2026-02-28",15,"Purchase","PU/0174",5,83,37881,"C",3144123],
["2026-02-28",16,"Purchase","PU/0175",5,81,38859,"C",3147579],
["2026-02-28",17,"Purchase","PU/0176",6,1,1000000,"C",1000000],
["2026-03-01",0,"Journal","JO/0023",0,1,4000000,"C",4000000],
["2026-03-08",1,"Purchase","PU/0177",1,156463,147,"C",23000061],
["2026-03-08",2,"Purchase","PU/0178",1,53069,146.9,"C",7795836],
["2026-03-08",3,"Purchase","PU/0179",1,47968,145.73,"C",6990377],
["2026-03-08",4,"Purchase","PU/0183",2,2991,1003,"C",2999973],
["2026-03-08",5,"Purchase","PU/0184",2,2487,858.75,"C",2135711],
["2026-03-08",6,"Purchase","PU/0185",2,2497,855.61,"C",2136458],
["2026-03-08",7,"Sales","SA/0133",3,1205,4150,"D",5000750],
["2026-03-08",8,"Sales","SA/0134",3,7031,4096,"D",28798976],
["2026-03-08",9,"Sales","SA/0135",3,6326,4115.67,"D",26035728],
["2026-03-08",10,"Sales","SA/0136",3,5947,4238.3,"D",25205170],
["2026-03-08",11,"Sales","SA/0137",3,5391,4100.57,"D",22106173],
["2026-03-08",12,"Sales","SA/0138",3,6693,4286.56,"D",28689946],
["2026-03-22",1,"Purchase","PU/0180",1,156463,147,"C",23000061],
["2026-03-22",2,"Purchase","PU/0181",1,50488,146.24,"C",7383365],
["2026-03-22",3,"Purchase","PU/0182",1,52202,142.81,"C",7454968],
["2026-03-22",4,"Purchase","PU/0186",2,2991,1003,"C",2999973],
["2026-03-22",5,"Purchase","PU/0187",2,2360,857.19,"C",2022968],
["2026-03-22",6,"Purchase","PU/0188",2,2236,834.76,"C",1866523],
["2026-03-22",7,"Sales","SA/0139",3,1205,4150,"D",5000750],
["2026-03-22",8,"Sales","SA/0140",3,3543,4244.6,"D",15038618],
["2026-03-22",9,"Sales","SA/0141",3,4126,4264.47,"D",17595203],
["2026-03-22",10,"Sales","SA/0142",3,6321,4132.49,"D",26121469],
["2026-03-22",11,"Sales","SA/0143",3,4111,4235.8,"D",17413374],
["2026-03-22",12,"Sales","SA/0144",3,5410,4155.35,"D",22480444],
["2026-03-28",13,"Journal","JO/0024",4,1,300000,"C",300000],
["2026-03-28",14,"Purchase","PU/0189",5,195,38461.5,"C",7499992],
["2026-03-28",15,"Purchase","PU/0190",5,81,38225,"C",3096225],
["2026-03-28",16,"Purchase","PU/0191",5,104,37292,"C",3878368],
["2026-03-28",17,"Purchase","PU/0192",6,1,1000000,"C",1000000]
];
```