# Family Vault — Known Limitations

**Version:** 1.0 · **Date:** 9 November 2026 · **Applies to:** Stage 1 (v0.1.0)

This document exists so that nothing about this project is overstated. It is
updated at every stage. Anything described as working here has code behind it
and tests that pass.

---

## 1. Not yet implemented

The encrypted vault works and can be used for real passwords, and as of 10 Nov
2026 it can be backed up and moved between devices. What is still missing:

| Area | State |
|---|---|
| Encrypted vault, Argon2id, authenticated encryption | **Working** |
| Logins, notes, cards, identities | **Working** |
| Folders, search, favourites, trash | **Working** |
| Password generator and passphrases | **Working** |
| TOTP authenticator for other accounts | **Working** |
| Password-health report | **Working** |
| Auto-lock, clipboard clearing, lock when hidden | **Working** |
| Change master password | **Working** |
| Encrypted backup and restore | **Working** — Backup & Transfer screen |
| Importing another device's vault | **Working** — merges per entry, never overwrites |
| Biometric unlock | Not implemented |
| Screenshot blocking on Android | Not implemented |
| Android Keystore / Windows Hello device key | Not implemented |
| Android autofill | Not implemented |
| CSV import from Chrome, Bitwarden, KeePass | Not implemented |
| Sync through a shared folder | **Working** — point both devices at the same folder and press Sync now |
| Sync that runs on its own | Not implemented: nothing watches the folder and nothing runs on a schedule |
| Optional key file or hardware key | Not implemented — Phase 2 |
| Printable recovery sheet | Not implemented — Phase 2 |
| Item history, custom fields, attachments | Not implemented — Phase 2 |
| Breach checking | Not implemented — Phase 2 |
| Passkeys, sharing, emergency access, browser extension | Not implemented — Phase 3 |

Two consequences the user needs to know, both stated in the app and in the
release notes:

**Syncing happens when you press the button.** Point both devices at one shared
folder and press Sync now on each. The merge keeps whichever side changed an
entry more recently, so pressing it on both leaves both devices holding the same
thing, and pressing it again changes nothing. But nothing watches the folder and
nothing runs on a schedule: if nobody presses Sync now, nothing moves.

**Setting sync up needs one manual transfer.** The second device can only read
the first device's files if it was set up from the first device's vault — make a
backup there, import it on the second device, then choose the shared folder on
both. This is not an arbitrary step: the key that protects the shared files lives
inside the encrypted vault, so the only way to pass it across is to pass the
vault across. See `docs/decisions-and-risks.md`, D-013.

**The shared folder is a folder, nothing more.** The app has no account with
Google, Microsoft or Dropbox and talks to none of them. It reads and writes files
in a folder you choose; whatever already keeps that folder in step does the
moving, and it only ever sees encrypted files.

**Take a backup.** The app cannot recover a vault from a lost device on its own.
A backup file on a cloud drive or a USB stick is the only thing standing between
a broken phone and a lost vault. The backup is encrypted, so where it is kept
matters much less than whether it exists — but its password cannot be recovered
either.

**An import cannot be undone.** The merge is designed so it cannot lose an entry
either side still holds, and it is tested for that on 100 random vault pairs. But
once a backup from another device is merged in, there is no "undo last import".
The dialog shows what the file contains before anything is applied; read it.

**There is no fingerprint unlock**, so the master password is typed every time.

## 2. Limitations that will remain

These are consequences of the design, not gaps to be closed later. They are
stated because a user deserves to know them.

### A lost master password means a lost vault

There is no recovery, no reset and no back door. This is the direct cost of the
guarantee that nobody else can read the vault — if a recovery mechanism existed,
it would be a second way in, and whoever held it could use it. Phase 2 adds a
printable recovery sheet, but a sheet records information; it cannot recreate a
forgotten password.

### A compromised device defeats the design

While a vault is unlocked, its contents are decrypted in memory. Malware with
access to the device at that moment can read them. No password manager prevents
this.

### File size reveals a rough item count

Anyone holding the vault file learns roughly how much is in it from its size, and
learns the format version and the Argon2id cost from the header. Nothing about
the contents is revealed. Padding the payload to fixed blocks would hide the
size; this was judged not worth the complexity for a family tool, and is recorded
rather than hidden.

### No independent security audit

The design follows published guidance and uses vetted cryptographic libraries,
and the security-critical paths are covered by tests. **No external security firm
has reviewed this project.** No claim to the contrary is made anywhere in it.

---

## 3. Build and distribution limitations

### The release APK is signed with a development key

Android will warn that the app comes from an unknown developer. The app is
unaffected, but the APK is not suitable for Play Store distribution. A proper
release key must be generated by the project owner and held as a repository
secret; it cannot be created by the build agent, and committing one to a public
repository would be a serious error. See decision D-006.

### The Android APK is universal rather than per-architecture

One file covers all devices, which makes installation simple for a non-technical
family member, at the cost of a larger download than a per-architecture build.

### No installer for Windows

Distribution is a zip folder that is unzipped and run. A proper MSIX or
Installer package is Phase 2 work.

### The app identifier keeps Flutter's generated form

The Android `applicationId` is `com.casamby.family_vault`. It is deliberately
left as generated: an application identifier is a permanent identity, and
changing it later would make an installed app unable to upgrade in place. Only
the names a user actually reads were changed.

### The Flutter version is pinned to one release

CI builds against Flutter **3.47.9** only. This is deliberate: a pinned
toolchain makes builds reproducible, and the version is raised explicitly rather
than drifting with the stable channel. The cost is that a newer Flutter is not
picked up automatically.

---

## 4. Testing limitations

| Limitation | Detail |
|---|---|
| No test has ever run | Stage 1 tests are written but have not executed, because the authoring environment cannot run Flutter. The first CI run is their first execution. |
| No device testing yet | Nothing has run on a physical Android phone or a real Windows machine. |
| No integration tests yet | Only unit and widget tests exist. Integration tests arrive with the features they cover. |
| Coverage is not yet measured | CI collects coverage from the first run onward; no target is set until there is meaningful code to cover. |

---

## 5. How to report a problem

Open an issue on the repository. Please do **not** include a real password, a
vault file, a recovery sheet or a screenshot containing real credentials in an
issue — the repository is public.
