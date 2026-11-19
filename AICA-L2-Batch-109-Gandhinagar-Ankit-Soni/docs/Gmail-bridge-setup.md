# Gmail bridge — set-up guide

**Purpose.** The desktop application produces and sends the confirmations. The
bridge is the other half: a small script that lives in *your* Google account
and keeps collecting the replies while your computer is switched off. When you
next open the application it reads what the bridge has gathered and updates the
reconciliation and the reports.

Two files make up the bridge:

| File | What it is |
|---|---|
| `balance-confirmation-bridge.gs` | the script itself |
| `appsscript.json` | the permissions it is allowed to ask for |

---

## 1. Before you begin

You will need the Google account that **receives** the confirmation replies —
the mailbox the letters were sent from. Everything below happens inside that
account. Nothing is installed on your computer and no password is typed
anywhere.

Set aside about ten minutes. It is done once per mailbox, not once per
engagement.

---

## 2. Create the script project

| Step | What to do |
|---|---|
| 2.1 | Sign in to the mailbox, then open **https://script.google.com** |
| 2.2 | Click **New project** |
| 2.3 | Click the project name (top left, "Untitled project") and rename it `Balance confirmation bridge` |
| 2.4 | In the editor, select everything in `Code.gs` and delete it |
| 2.5 | Open `balance-confirmation-bridge.gs`, copy the whole file, and paste it in |
| 2.6 | Click the save icon (or Ctrl+S / Cmd+S) |

### Put the permissions file in place

| Step | What to do |
|---|---|
| 2.7 | Click the gear (**Project Settings**) in the left bar |
| 2.8 | Tick **Show "appsscript.json" manifest file in editor** |
| 2.9 | Go back to the **Editor** and open `appsscript.json` |
| 2.10 | Replace its contents with the supplied `appsscript.json` and save |

If your firm does not work to Indian Standard Time, change `"timeZone"` in that
file to your own zone before saving — it is what dates the rows.

### Switch on the Drive service

| Step | What to do |
|---|---|
| 2.11 | In the left bar, next to **Services**, click **+** |
| 2.12 | Choose **Drive API**, leave the identifier as `Drive` and the version as `v3`, then click **Add** |

This is what lets the script read a PDF or Word attachment, and read a scanned
or photographed slip through Google's text recognition.

---

## 3. Authorise and start it

| Step | What to do |
|---|---|
| 3.1 | In the function list at the top, select **setUp** |
| 3.2 | Click **Run** |
| 3.3 | Google will ask for authorisation. Choose the mailbox account |
| 3.4 | You will see "Google hasn't verified this app". This is normal for a script you wrote yourself. Click **Advanced**, then **Go to Balance confirmation bridge (unsafe)** |
| 3.5 | Read the permissions and click **Allow** |

`setUp` creates three things: a spreadsheet called **Balance confirmation
replies**, two Gmail labels (`BCG/Processed` and `BCG/Needs review`), and a
timer that runs every ten minutes. Open **Execution log** at the bottom of the
editor to see the spreadsheet address.

### What you are agreeing to

| Permission | Why it is needed | What it does **not** allow |
|---|---|---|
| Gmail — *modify* | read a reply, apply a label, mark it read | it is not full-mailbox access, and it cannot delete mail |
| Sheets | write the replies into the spreadsheet | — |
| Docs and Drive | convert each attachment to text, in a temporary file deleted straight after | — |
| Script | create the ten-minute timer | — |

The script makes no connection to anything outside your own Google account.
There is no server of ours and nothing is sent to one.

---

## 4. Publish the feed

This is the address the desktop application reads.

| Step | What to do |
|---|---|
| 4.1 | Click **Deploy** (top right) > **New deployment** |
| 4.2 | Click the gear next to "Select type" and choose **Web app** |
| 4.3 | Description: `feed v1` |
| 4.4 | **Execute as:** `Me` |
| 4.5 | **Who has access:** `Anyone with the link` |
| 4.6 | Click **Deploy**, then **Done** |
| 4.7 | In the function list select **feedUrl**, click **Run**, and open the **Execution log** |
| 4.8 | Copy the whole address it prints. **Check that it ends in `/exec?key=...`** |

If the log says the address is private, or prints no address at all, build it
yourself — this takes a moment and is not a fault:

1. **Deploy** › **Manage deployments**, and copy the **Web app URL**. It ends
   in `/exec`.
2. Add `?key=` and the ACCESS KEY from the log to the end, so that it reads
   `https://script.google.com/macros/s/AKfycb....../exec?key=<40 characters>`.

An address ending in `/dev` is the private testing one. It always demands a
browser sign-in and can never be read by the application.

> **The address is a password.** "Anyone with the link" is what allows the
> application to read the feed without a browser sign-in. The confirmations are
> protected by the 40-character key at the end of the address, which only you
> hold. Do not paste it into an e-mail, a chat message or a shared document. If
> it is ever disclosed, run **resetAccessKey** — the old address stops working
> immediately — and paste the new one into the application.

### If your administrator blocks "Anyone with the link"

Some Workspace domains do not permit it. In that case use the offline route:
deploy to your domain instead, and whenever you want the replies, run
**exportFeedToDrive** in the script, download the
`balance-confirmation-replies.json` file it writes to your Drive, and load it
with **Import replies (JSON)** on the Confirmations received page. Everything
else works the same way.

---

## 5. Connect the application

| Step | What to do |
|---|---|
| 5.1 | Open the Balance Confirmation Generator |
| 5.2 | Go to **10 Settings**, scroll to **Gmail bridge** |
| 5.3 | Paste the address into **Feed address** |
| 5.4 | Leave **Sync automatically when the application starts** ticked |
| 5.5 | Click **Sync now** |

The status line beside the card will report how many replies came across. From
then on the application reads the bridge each time it opens, and you can read
it at any time from **08 Confirmations received > Sync Gmail bridge**.

---

## 5a. Updating the script later

When you are sent a newer `balance-confirmation-bridge.gs`, the address, the
key, the spreadsheet and the labels all stay as they are:

| Step | What to do |
|---|---|
| 1 | Open the project, click `Code.gs`, select everything, paste the new file over it, and save |
| 2 | **Deploy** › **Manage deployments** |
| 3 | Click the pencil icon on the existing web app |
| 4 | Under **Version**, choose **New version**, then click **Deploy** |

Step 4 matters: a web app keeps serving the version it was deployed with until
a new version is published. Saving the code alone changes nothing for the
application. Do **not** create a second deployment, which would have a new
address.

---

## 6. How it behaves day to day

Every ten minutes the script searches the mailbox for

```
is:unread subject:"balance confirmation" newer_than:180d
```

For each message it finds, it:

1. reads the body, and the text of every attachment (PDF, Word, and scans or
   photographs through text recognition);
2. looks for the reference code `BCG-XXXXXX` that the letter carried, in the
   subject, the body and the attachment;
3. reads the confirmed figure out of the signed slip — the sentence beginning
   *"We hereby confirm that the amount ... is ..."*;
4. decides whether the party has agreed or reported a difference;
5. writes one row into the spreadsheet;
6. labels the message.

| Outcome | Label applied | Marked read | Row status |
|---|---|---|---|
| figure read from a signed slip, or a clear bounce | `BCG/Processed` | yes | `recorded` |
| no figure found | `BCG/Needs review` | **no** | `needs review` |
| figure found, but only weakly | `BCG/Needs review` | **no** | `needs review` |
| an attachment could not be read | `BCG/Needs review` | **no** | `needs review` |

A message is only ever marked read when the script is satisfied with it, so
anything in `BCG/Needs review` stays unread and visible in your inbox until you
look at it. The `note` column says why. Nothing is ever deleted, and no message
is recorded twice however often the script runs.

The **Audit trail** sheet logs every message the script touched, which is worth
keeping with the working papers.

---

## 7. Checking and changing it

| Want to | Run this function |
|---|---|
| See what one message would produce, changing nothing | `dryRun` |
| Get the feed address again | `feedUrl` |
| Issue a new key and kill the old address | `resetAccessKey` |
| Write the replies to a Drive file | `exportFeedToDrive` |
| Stop collecting | `tearDown` |
| Start collecting again | `setUp` |

To change what it searches for, edit `CONFIG.QUERY` at the top of the script.
To change how often it runs, edit `CONFIG.TRIGGER_MINUTES` and run `setUp`
again. To make it stricter about the figures it will accept without review,
raise `CONFIG.MIN_CONFIDENCE` (it is `0.70`; a signed slip scores `0.95` and a
figure read loosely out of the body scores `0.75`).

---

## 8. If something is not working

| What you see | What it means |
|---|---|
| The application says *"the bridge returned a page rather than data"* | Google served a sign-in page instead of the feed. Either the address ends in `/dev` (the private testing one — take the `/exec` address from Deploy › Manage deployments instead), or the deployment's **Who has access** is not set to **Anyone with the link**. |
| The application says *"HTTP 403"* | the deployment was removed or replaced. Deploy again and run `feedUrl`. |
| *"not authorised"* in the browser when you open the address | the key is wrong or absent — use the address `feedUrl` prints, unedited. |
| Replies are arriving in Gmail but no rows appear | check the subject line carries the words "balance confirmation"; the covering e-mail the application sends does, so this usually means the party started a fresh message. Widen `CONFIG.QUERY` if your parties reply with their own subject lines. |
| Everything lands in `BCG/Needs review` | the parties are not returning the signed slip, or they are sending images the text recognition cannot read. Open the rows and record those figures by hand. |
| Nothing has run for a while | open the project, click **Executions** in the left bar, and look for a failure. Google also e-mails you when a timed script fails. |

---

## 9. What this does not do

The bridge collects and reads. It does not judge. Every figure it records is
still yours to vouch: the reference code tells you which letter a reply belongs
to, the spreadsheet keeps the message link so you can open the original, and
the `needs review` rows are the ones that need your eye before they go into the
file. A reply matched only on the sender's address or on a similar party name
is shown as such in the register, and an auditor should satisfy themselves of
the sender's authority before treating it as evidence.
