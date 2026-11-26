# 3CD Helper – Tally Connector (Chrome / Edge extension)

Brings loan data from TallyPrime on this computer into the Clause 31 screen of 3CD Helper.
It only **reads** from Tally (fixed export requests) and talks only to Tally on `localhost`.

## Install (one time)
1. Unzip `tally-connector.zip`.
2. Open `chrome://extensions` (Edge: `edge://extensions`), turn on **Developer mode**.
3. Click **Load unpacked** and choose the unzipped `3cd-tally-connector` folder.
4. TallyPrime: **F1 Help → Settings → Connectivity → TallyPrime acts as: Server** (or Both), **Port 9000**. Keep the client's company open.
5. Open 3CD Helper → client → year → Clause 31 → Upload → **Tally से लाएँ**.

## Choices
- **Day Book – all loan groups**: all vouchers of the period come; you tick the loan ledgers in the app.
- **Only loan groups**: you tick the groups (by default *Loans (Liability)* with all its sub-groups such as Secured and Unsecured Loans). Only ledgers under those groups, the vouchers that touch them and the masters of their other side (bank, cash, interest) leave Tally.

The extension works on `clause44-3cd-helper.lovable.app` and its preview only.
