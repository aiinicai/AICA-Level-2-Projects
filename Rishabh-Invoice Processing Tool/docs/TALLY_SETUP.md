# Tally setup for IPT (TallyPrime)

Tested with TallyPrime (Silver) on the user's PC, companies "Manakpur Lime Product" (live books) and
"Majisa Lime Product" (test company).

1. **Enable the connection** – in TallyPrime: F1 Help → Settings → Connectivity → Client/Server configuration:
   - TallyPrime acts as: *Both*  · Enable ODBC: *Yes*  · Port: *9000*. Restart TallyPrime.
2. **Open the company** in Tally. IPT only talks to companies that are open.
3. In IPT **Company Settings** set *Tally company name* exactly as Tally shows it.
4. IPT → **Tally Integration** → *Test connection* → *Sync masters*.
5. GST ledgers: input tax ledgers must be under *Duties & Taxes* with GST duty head (Central Tax / State Tax /
   Integrated Tax). IPT can create missing ones (Tally Integration → Create GST ledgers…, after you confirm).
6. Purchase vouchers are created as **Item Invoice** vouchers like your own entries: party first, then GST
   ledgers and round off; supplier invoice no. goes into Reference / Supplier Invoice No.

## Safety rules IPT follows
- Every write to Tally (voucher, ledger) needs your confirmation in IPT.
- An import is "success" only if Tally answers CREATED ≥ 1 with no errors **and** IPT finds the voucher again.
- Fetching the purchase register is read-only.
- Test new mappings in a test company first (as was done with Majisa Lime Product).

## Known limits
- Credit notes / debit notes and reverse-charge invoices are not imported into Tally by IPT yet (they are read,
  reconciled and reported).
- The purchase-register fetch reads the Day Book month by month; very large months may take a few seconds each.
