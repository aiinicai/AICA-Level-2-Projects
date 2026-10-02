# 5-Minute Presentation Script: BRMCo Accounting Hub
*(Written for a non-technical audience. Words in italics are stage directions, not to be read aloud.)*

## 1. The problem (45 seconds)
Good morning, everyone.

In every CA office, a large part of the day goes on data entry. A client sends us an Excel sheet of 200 sales bills, or a bank statement with 300 transactions, and someone types each one into Tally, line by line.

This has three problems. **It takes time**: hours that could go on advisory work go on typing. **Mistakes happen**: a wrong GST amount, a wrong party name, an entry typed twice. And **it is boring work**, and tired people make more mistakes.

So I asked: why should a person retype data that is already sitting in Excel?

## 2. What the application is (45 seconds)
My project is called **BRMCo Accounting Hub**. In simple words, it is an **Excel-to-Tally accounting automation tool**.

Think of it as a **careful assistant** between Excel and Tally. It takes the data from Excel and checks every entry the way a senior accountant would. Only when everything is correct does it post the entries into Tally automatically.

In this first phase it handles the five most common entries: **Sales, Purchase, Journal, Bank Receipt and Bank Payment**.

## 3. How it works (1 minute 30 seconds)
*(Show the screen here if possible.)*

1. **Download the template.** A ready Excel format, with drop-down lists of ledger names taken from Tally.
2. **Fill in the data.**
3. **Upload the file.**
4. **The app checks everything**, which is the heart of the project:
   - Is the date within the financial year?
   - Does this ledger exist in Tally?
   - Is the GST number valid?
   - CGST plus SGST for a local sale, IGST for an outside-state sale?
   - Is 18% really the tax written?
   - Do debits equal credits?
   - Was this invoice already entered?

   If anything is wrong, it shows **exactly which row and column**, in plain English. If a ledger is missing, it can even create it in Tally, but only after I review and approve it.
5. **Preview.** It shows the full debit and credit entry, like a paper voucher. Nothing is posted until a person clicks **"Confirm."**
6. **Post to Tally.** One click. The app shows Tally's own reply for every voucher.

Everything is recorded in an **Import History** and an **Audit Log**, so we always know what was uploaded, when, and what Tally said.

## 4. A real example (30 seconds)
While testing, Tally kept rejecting my entries with the message "voucher date is missing", although the date was clearly there. We found that the Tally copy was running in **Educational mode**, which only accepts dates on the 1st, 2nd and 31st. Now the app **detects this itself** and explains it simply. That is the idea: **catch problems before they reach the books, and explain them clearly.**

## 5. How I prepared it (1 minute)
**First, I wrote the requirements as a Chartered Accountant**: GST rules, debit-credit balance, duplicate checks, and human approval before posting.

**Second, I used AI to build it**, which is where my AICA learning came in. I gave the AI a detailed, structured prompt. It wrote the software in Python. I acted as the project leader: I tested with real Tally, reported problems with screenshots, and directed the corrections.

**Third, I designed it for safety.** It runs **on the office computer**, so client data does not go to the internet. It has a **Demo Mode** for practice. And it **never changes Tally without a person's approval.** There is also a small **server part**, ready for future features like AI reading of purchase bills.

## 6. Benefits and future plans (30 seconds)
**Benefits:** hours of typing reduced to minutes, far fewer errors, a full audit trail, and staff time freed for review and advisory work.

**Future plans:** AI reading of purchase bills from photos or PDFs, GST return preparation, and support for many clients from one system.

## 7. Closing (15 seconds)
To sum up: **BRMCo Accounting Hub turns client Excel data into checked, approved Tally entries, quickly, accurately and with a full record.** It shows how a CA can use AI not to replace professional judgement, but to remove the boring work so we can focus on the thinking work. Thank you.
