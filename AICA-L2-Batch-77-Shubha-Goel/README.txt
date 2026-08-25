HDFC BANK STATEMENT ANALYZER
=============================

This version is customized specifically for the HDFC Bank statement format supplied for the project.

Expected HDFC columns:
Date
Narration
Chq./Ref.No.
Value Dt
Withdrawal Amt.
Deposit Amt.
Closing Balance

INSTALLATION
------------
1. Keep all files in the same folder.
2. Double-click install_dependencies.bat
3. Wait until installation completes.
4. Double-click run_application.bat
5. The application opens in your browser.

IMPORTANT FOR OLD .XLS FILES
----------------------------
The supplied statement is an old Microsoft Excel .XLS file.
The project therefore requires xlrd>=2.0.1 in addition to pandas.

CLASSIFICATIONS
---------------
The application specifically recognizes:
- Interest
- Salary
- Income Tax Refund
- Cash Deposit
- Cash Withdrawal
- Bank Charges
- Investment / Brokerage
- Investment / Mutual Fund
- Loan / Personal Transfer
- Gift / Personal Transfer
- Self Transfer
- NEFT Transfer
- RTGS Transfer
- IMPS Transfer
- UPI Transaction
- NACH / ECS
- Other Credit
- Other Debit

AUDIT EXCEPTIONS
----------------
The application flags:
- High-value transactions
- Large cash transactions
- Duplicate reference numbers
- Repeated narrations
- Round-value transactions
- Unusual/manual/adjustment/unknown narrations

REPORT
------
The Excel export contains:
1. Analyzed Transactions
2. Monthly Summary
3. Category Summary
4. Audit Exceptions
5. Cash Transactions
6. Investments

NOTE
----
The supplied statement is treated as a transaction-analysis source only.
The rules are transparent and editable in the Python file.
Final accounting/tax/audit conclusions should be reviewed by the CA.
