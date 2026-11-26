# Clause44 3cd Helper

/skill:migrate-external-project Source: code archive. Migrate the attached project into Lovable.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/91f452ce-dbc9-4bb3-8511-12c6d09e2db0).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Clause 31 – loans (269SS / 269T)

Open an assessment year and choose the **Clause 31** chip.

- **Upload:** Tally XML – the full Day Book, or Group Vouchers of only "Unsecured Loans" (export with "Include dependent masters = Yes") – or an Excel / CSV loan register. Large files can be uploaded as a ZIP (up to 200 MB).
- **Ledger choice:** "Day Book – all loan groups" or "Only Unsecured Loans". You can tick or untick single ledgers, and the choice is remembered for the client.
- **Running balance:** each entry is only a debit or a credit. Loan taken, repayment, loan given and repayment received are worked out from the running balance, and an entry that crosses zero is split.
- **Report:** 31(a)–(e) in the Form 3CD layout with a **Review** mark on accounts to check: a reportable entry not through an a/c payee cheque / draft / bank, or the balance changing side. Same-day order can be chosen, and the report exports to Excel.

- **Tally से लाएँ** (also in Clause 44 upload, Day Book only): with the free **Tally Connector** Chrome / Edge extension (folder `tally-connector/`, downloadable from the app as `/tally-connector.zip`, installed with "Load unpacked") data comes straight from TallyPrime on the same computer (port 9000) – either the full Day Book or only the Unsecured Loans ledgers. The extension only reads from Tally and works only on this app's pages.
- **Report choices:** lender names drop "Loan" from the ledger name (editable in Parties), Note 1 codes as notified, an a/c payee dropdown for cheque / draft rows, and an optional "Combine similar entries" switch.

## Sharing on WhatsApp

Clause 44 and Clause 31 reports have a **WhatsApp** button: the report is saved privately, a link valid for 7 days is made, and WhatsApp Desktop / Web / phone opens on the client's number with the message filled in – the user presses Send. No WhatsApp API or cost.

## Client upload link

In the Upload tab of Clause 44 and Clause 31 the firm can make a **7-day link** and send it on WhatsApp. The client opens `/u/<token>`, uploads files without an account, and the files appear under "Files from the client" (with **Use this file**) and in the uploads list. Links stop when they expire, are stopped, or the year is made Final. Needs the one-time database change in `docs/database/client_upload_links.sql` (applied through Lovable); until then the panel says the update is pending.

Clients can be deleted by an Owner or Partner (not when a year is Final). Taking a backup before deleting is optional.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
