# Family Vault — how to use it

Written for everyone in the family, not for programmers. If something here does
not match what you see on screen, trust the screen and say so.

Installing it first: [`installing.md`](installing.md).

---

## The idea in one paragraph

You remember **one** password. Family Vault remembers all the others, locked in
a file on your own device that nobody can read without that one password — not
a website, not a company, not whoever built this. The point is that every
account you have can then have a different, long, unguessable password, which
is the single biggest thing you can do to stay safe online.

---

## Setting up, once

1. Open the app. It asks you to choose a **master password**.
2. The meter underneath tells you how it looks. Longer beats complicated: four
   or five unrelated words are easier to remember *and* harder to guess than a
   short jumble of symbols. Tap **Suggest a passphrase** if you want one made
   for you.
3. Type it again to confirm.
4. Tick the box. It says there is no reset, and that is true.
5. Tap **Create my vault**.

That is the only time you do this. From then on the app just asks for the
password.

---

## Saving your first login

1. Tap **Add** (the button at the bottom right).
2. Leave the kind as **Login**.
3. **Name** — whatever you will recognise it by. "Barclays", not
   "banking portal v2".
4. **Username** or **Email** — whichever you sign in with.
5. **Password** — tap the dice icon to have a strong one made for you, or type
   the one you already use.
6. **Website** — optional, but it helps you find the right entry later.
7. Tap **Save**.

### Changing a password you already have

If you are replacing a weak password on a real website, do it in this order:

1. Change it on the website first.
2. Then update it here.

The other way round leaves you with a password saved that does not work.

---

## Finding things again

- **Search** at the top of any list. It looks at names, usernames, email
  addresses, websites, notes and folder names.
- **Folders** group things — Banking, Shopping, Work. Create them under
  Folders; the app suggests common ones.
- **Favourites** — tap the star on an entry. The handful you use daily end up
  one tap away.

Search deliberately does **not** look inside passwords. If it did, anyone with
your unlocked phone could confirm a guessed password just by typing it in.

---

## Using a saved password

1. Open the entry.
2. The password is hidden. Tap the **eye** to see it, or the **copy** icon to
   copy it without looking.
3. Paste it into the website.

The clipboard clears itself after 30 seconds by default, so a copied password
is not left lying around for the next app that looks. You can change that under
Settings, including turning it off.

---

## The four kinds of entry

| Kind | For | Holds |
|---|---|---|
| **Login** | Websites and apps | Username, email, password, website, authenticator key |
| **Secure Note** | Anything written down | Free text |
| **Payment Card** | Bank and credit cards | Name on card, number, expiry, security code |
| **Identity** | Details you type into forms often | Name, address, email, phone, date of birth |

Card numbers and security codes are hidden until you tap to reveal them, the
same as passwords.

---

## Two-factor codes

Many websites offer a second step at sign-in: a six-digit code that changes
every 30 seconds. This is well worth turning on, and Family Vault can hold
those codes for you.

When a website shows you a QR code and a long **setup key**:

1. Copy the setup key, or the whole `otpauth://` link if it offers one.
2. Open that website's entry here and tap the pencil to edit it.
3. Paste it into **Authenticator key**. If you pasted a link, the app pulls the
   key out of it for you.
4. Save.

The six-digit code now appears on that entry and under **Authenticator**, with
a ring showing how long before it changes. Tap it to copy.

> **Keep the website's own backup codes somewhere else.** If you lose this
> device and the codes only existed here, you are locked out of that account.
> The usual advice applies: print them and keep them with your master password
> note.

### One thing worth understanding

Those codes protect your *other* accounts. They do not protect this vault. A
code checked inside this app could be bypassed by anyone who took a copy of the
vault file, so offering it would be false comfort. Real extra protection for
the vault itself — a key file or a hardware key, which actually change the
encryption — is planned, not built. For now the vault's protection is your
master password, which is why its length matters.

---

## Password Health

Tap **Password Health** for a score out of 100 and a list, worst first.

| It says | It means | Do this |
|---|---|---|
| **Weak password** | Short, or an obvious pattern | Use the dice icon to replace it |
| **Reused password** | The same password on more than one entry | Give each its own. One breached site otherwise exposes all of them |
| **Old password** | Unchanged in over a year | Worth changing, not urgent |
| **Two-factor available** | No authenticator key saved | If the site offers it, turn it on — the biggest single improvement |

This runs on your device. No password, and no scrambled version of one, is sent
anywhere.

Length counts for more than punctuation here, deliberately.
`correcthorsebatterystaple` passes; `Ab1!` does not.

---

## Locking

| How | When |
|---|---|
| **Lock button** (padlock, top right) | Whenever you walk away |
| **By itself after inactivity** | 5 minutes by default; change under Settings |
| **When the app leaves the screen** | On by default |

Locking wipes the decrypted contents from memory. Reopening needs the master
password again — fingerprint unlock is planned, not built.

---

## Deleting and restoring

Deleting an entry moves it to **Trash**, still encrypted. You can restore it
from there. **Empty trash** removes those entries for good.

Deleting a *folder* never deletes what is in it. Its entries stay, simply
without a folder.

---

## Settings worth knowing

| Setting | Default | Why change it |
|---|---|---|
| Lock after inactivity | 5 minutes | Shorter on a phone you carry; longer on a desktop at home |
| Lock when the app is hidden | On | Leave it on, especially on a phone |
| Clear copied passwords | 30 seconds | Turn off only if it gets in your way |
| Change master password | — | Re-encrypts the whole vault. Write the new one down **first** |
| Delete this vault | — | Permanent. Asks twice and makes you type DELETE |

---

## Backing up, and using two devices

Open **Backup & Transfer** in the list on the left.

### Making a backup

Press **Save a copy** (on Windows) or **Share a copy** (on Android), and choose
where it goes. What gets written is encrypted — the same as your vault file — so
it is safe on a cloud drive, in email to yourself, or on a USB stick. Anyone who
finds it sees nothing without the password.

By default the backup uses your master password. If you would rather it had its
own, turn on **Protect the backup with a separate password** and type that one
twice. A backup password cannot be recovered any more than a master password
can, so write it somewhere that is not inside the vault.

**Do this.** The app cannot get your vault back from a broken phone by itself. A
backup file is the only thing that can.

### Moving entries between your phone and your laptop

There is no automatic syncing in this version. You move entries yourself:

1. On the **phone**, make a backup and send it somewhere the laptop can reach —
   a cloud drive folder works well.
2. On the **laptop**, open Backup & Transfer, press **Choose a backup file**,
   pick that file and type its password.
3. You will see how many entries the file holds **before anything changes**.
   Press **Merge**.
4. Then do the same in the other direction: back up on the laptop, import on the
   phone.

After both directions, the two devices hold the same thing.

### What "merge" actually does

It does **not** replace your vault with the file. It goes through entry by entry:

| Situation | What happens |
|---|---|
| The entry is only in the file | It is added here |
| The entry is only here | It stays, untouched |
| The same entry is in both, unchanged | Nothing happens |
| The same entry was edited on both devices | The **more recent** edit is kept, and the screen tells you how many entries that applied to |
| You deleted the entry for good on the other device | It is deleted here too |

So importing the same file twice is harmless — the second time it will simply
say **Already up to date**. And nothing you still have on this device can be
lost by importing.

The one thing to be careful of: there is no "undo last import". Read the box
that appears before you press Merge.

### Keeping two devices in step through a shared folder

Rather than carrying a file back and forth every time, you can point both
devices at one folder and press a button.

**The folder can be anything both devices can see** — your Google Drive,
OneDrive or Dropbox folder *on the device*, a folder on a network share, even a
USB stick you move between two machines. The app has no account with any of
those services and never talks to them. It writes an encrypted file into the
folder; whatever already keeps that folder in step does the moving, and only
ever sees a file it cannot read.

**Set it up in this order.** It matters.

1. On the device that **already holds your passwords**, open Backup & Transfer,
   press **Choose a shared folder**, pick the folder and give the device a name
   like "laptop". Press **Sync now**.
2. On the **same** device, make a backup (above) and get it to the other device.
3. On the **other** device, import that backup.
4. Now on the other device, choose the **same folder** and name it something
   else, like "phone". Press **Sync now**.

From then on, pressing **Sync now** on either device is enough.

**Why step 2 and 3 cannot be skipped.** The key that protects the files in the
shared folder lives *inside* your encrypted vault. The only way to get it onto
the second device is to get your vault onto the second device — which is what
that one import does. Without it, the second device will say it cannot open the
first one's file, and it will be right.

**What you will see.** After a sync: how many devices it found and what changed,
for example *"Synced with 1 device: 3 added, 1 updated."* If a file could not be
used, it is named and the rest are merged anyway — the usual cause is that your
cloud app was still uploading it, and it will work next time.

**It only runs when you press the button.** Nothing happens in the background,
and nothing runs on a schedule. If neither of you presses Sync now, nothing
moves.

**Stop sharing on this device** unhooks that one device. Your vault there is
untouched, and the files already in the folder are left alone, because your
other device may still be using them.

---

### Setting up a new or replaced phone

On a fresh device, the first screen offers **Restore from a backup file
instead**, underneath the setup form. Choose it, pick your backup, and type the
password that protects it. The restored vault keeps that password; you can
change it afterwards in Settings.

That option disappears once a vault exists on the device, so a restore can never
wipe a vault you are already using. If you want to bring a backup into a vault
you already have, use **Import** on the Backup & Transfer screen instead.

---

## Honest limits

Things this version does **not** do, so nobody is caught out:

- **No automatic syncing.** Sync runs when you press Sync now. Nothing watches
  the folder and nothing runs on a schedule.
- **No autofill on Android.** Copy and paste for now.
- **No importing** from Chrome, Bitwarden or anywhere else. Entries are typed
  in by hand.
- **No recovery sheet** yet, and **no password reset ever**.
- **No fingerprint unlock** yet.

And one that will never change: if someone has already taken over your device
while the vault is unlocked, they can read what is on screen. No password
manager solves that.

This project has not been reviewed by an outside security firm.

---

## If something goes wrong

| Problem | What it means |
|---|---|
| "The master password may be wrong, or the file may have been changed" | Usually a typo. The app cannot tell a wrong password from a damaged file apart on purpose, because saying which would help someone guessing. |
| "Some entries could not be read and were left out" | The file was damaged. The rest opened normally. Tell whoever maintains this. |
| "Family Vault could not start" | Nothing has happened to your vault. Close the app and open it again. |

Forgotten master password: there is nothing anyone can do. The only way forward
is **Settings → Delete this vault** and starting again. That is the cost of the
guarantee that nobody else can read it.
