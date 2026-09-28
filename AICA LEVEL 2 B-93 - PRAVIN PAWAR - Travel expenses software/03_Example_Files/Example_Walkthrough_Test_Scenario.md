# Example Walkthrough – One Complete Trip

Use this script to demonstrate or train users on a **fresh** installation (`Start_ABC_Travel_App.bat`).
Screenshots of every step are in `Example_Screenshots/`.

| # | Who logs in | What to do | Result |
|---|---|---|---|
| 1 | – | Open http://localhost:8080 → **Sign Up**: Anita Admin, admin@abc.com, password `Admin@123` | First user becomes **Admin** |
| 2 | – | Try Sign Up with random@gmail.com | Refused – email not added by Admin (logged) |
| 3 | Admin | **Employees → Add employee** (or Import CSV `Sample_Employee_Import.csv`): Business Head, Managing Director, Travel Assistant, HR Head, Accountant, Sales Executive (reporting to the Business Head) | Employees show "Awaiting sign up" |
| 4 | Each employee | **Sign Up** with the email id added by Admin and own password | Status changes to "Signed up" |
| 5 | Sales Executive | **New Travel Request**: Mumbai → Delhi, 20 days ahead, 3 days, purpose, *Auto-fill from policy*, advance ₹3,000 → **Submit for approval** | Ref TR-YYYY-0001, *Pending Business Head*; lead-time shows "On time" |
| 6 | Sales Executive | (Optional) **Edit request** while still pending | Allowed until the Business Head acts |
| 7 | Business Head | **Pending Approvals** → open → revise budget to ₹25,000, comment → **Approve** | *Pending Managing Director* |
| 8 | Managing Director | Open → **Approve** | *Pending Travel Booking* |
| 9 | Accountant | Open → **Record advance paid** ₹3,000 | Advance recorded |
| 10 | Travel Assistant | **Booking Desk** → IndiGo 6E 2134, PNR, ₹8,200; Lemon Tree 3 Star, 2 nights @ ₹3,800; attach `Sample_Airline_E_Ticket.pdf` → **Confirm booking** | *Booked*; employee notified. Choosing 5 Star forces a justification and raises an exception |
| 11 | Sales Executive | After travel: add expenses – Taxi ₹850 + `Sample_Bill_Taxi_Receipt.pdf`, Client lunch ₹2,400 + `Sample_Bill_Restaurant.pdf`, Dinner ₹450 → **Submit expense statement** | *Claim Pending Business Head* |
| 12 | Business Head | Reduce taxi line to ₹800 with note → **Approve** | *Claim Pending HR Head* |
| 13 | HR Head | **Approve** (or Send back to test correction loop) | *Pending Accounting & Payment* |
| 14 | Accountant | **Accounts Desk** → voucher JV/TR/2026/001, NEFT, UTR, date → **Post voucher & mark paid** | Net payable = approved ₹3,650 − advance ₹3,000 = ₹650; *Paid & Closed* |
| 15 | Admin | **Analytics Dashboard**, **All Requests** (Export CSV), **Sign-in / Sign-up Log**, **Backup database** | Company-wide view |

### Demo database
`Example_Demo_Database_abc_travel_demo.db` holds 15 employees and 46 trips across all stages
(with exceptions such as late booking, 5 Star above grade, missing bills, over-DA food, late claim).
Easiest way to use it: double-click **Start_Demo_Mode.bat** (creates the same data automatically) and
log in with `admin@abc-demo.com` / `Demo@1234`. Other demo users: md@, bh.west@, bh.north@, hr@,
accounts@, travel@, arjun@, deepa@, rahul@, sneha@, imran@, pooja@, manoj@ `abc-demo.com` – all `Demo@1234`.

### Sample bills
Files in `Sample_Bills/` are generated test documents for fictional vendors, clearly marked
"SAMPLE BILL – FOR TESTING ONLY".
