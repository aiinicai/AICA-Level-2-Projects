# Lordship Africa Payroll (Kenya)

A desktop payroll app for Kenya written in Python. It uses only the standard library (Tkinter and SQLite), so there's nothing to install.

## Run
Double-click `Run_Payroll.bat`, or run `python app.py`. The first time it opens, it asks you to create the Admin login.

Run the tests with `python -m unittest test_payroll -v`.

## Statutory deductions (defaults as of Oct 2026, editable in Settings > Statutory Rates)
| Item | Rule |
|---|---|
| PAYE | Monthly bands: 10% up to 24,000; 25% up to 32,333; 30% up to 500,000; 32.5% up to 800,000; 35% above. Personal relief 2,400 |
| NSSF | 6% from the employee and 6% from the employer. Tier I goes up to the LEL and Tier II runs from the LEL to the UEL. Limits are applied by date: Feb 2026 onwards is 9,000 / 108,000 (max 6,480 each side) |
| SHIF | 2.75% of gross, minimum 300. Deductible before PAYE |
| Housing Levy | 1.5% from the employee and 1.5% from the employer. The employee's share is deductible before PAYE |
| Allowable deductions | Pension up to 30,000, mortgage interest up to 30,000, post-retirement medical fund up to 15,000, disability exemption 150,000 |
| Reliefs | Insurance relief at 15% of premiums, capped at 5,000 |
| Benefits | Non-cash benefits of 5,000 or less are exempt. Car and housing benefits are always taxable |
| Other | Secondary employment is taxed at a flat 35% with no relief. Consultants pay 5% WHT. NITA is 50 per employee |
| Employment Act | Overtime at 1.5x and 2x. The app warns if deductions exceed 2/3 of wages or pay is below the minimum wage |

## Features
- Employee master record with KRA PIN validation, CSV import and export, and pay for joiners and leavers pro-rated by days worked
- Loans that count down and stop when paid off, plus recurring SACCO, HELB, welfare and union deductions
- Monthly inputs: overtime, bonus, arrears, leave pay, absence and leave days, entered on screen or by CSV import
- Payroll runs as a draft first, then the period is closed and locked (Admin only). Closing reduces loan balances and reopening restores them
- Reports: payslips with year-to-date totals (HTML, print to PDF), payroll register, KRA P10, NSSF, SHIF and Housing Levy returns, a bank and M-Pesa payment file, the GL journal, a statutory summary with due dates (the 9th), and the P9A card
- PAYE calculator that works both ways: from gross to net, and from a target net back to the gross needed
- User accounts with roles, PBKDF2-hashed passwords, a full audit trail and database backup

## Notes
- Paste the P10 CSV into KRA's official iTax P10 Excel template and validate it there before uploading.
- Check the rates whenever a new Finance Act or Legal Notice comes out. Changing a rate only affects payrolls you run after the change.
- `payroll.db` holds confidential salary data, so keep it in a secure location and back it up regularly.
