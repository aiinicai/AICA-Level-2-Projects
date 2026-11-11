# Family Vault — Development Progress Log

A running record of what was built, what was tested, what passed and what failed.
Newest entry first. Statuses are **NOT STARTED · IN PROGRESS · COMPLETED ·
TESTING · BLOCKED**.

The rule applied throughout: a feature is COMPLETED only when its code exists and
tests covering it pass in CI. A screen that renders is not a completed feature.

---

## Stage summary

| Stage | Deliverable | Status |
|---|---|---|
| 1 | Flutter scaffold and GitHub Actions build pipeline | **COMPLETED** — green on all jobs, run 42612638343 |
| 2 | Cryptographic core: Argon2id, authenticated encryption, vault format, tests | **COMPLETED** — green on all jobs, run 42625696754 |
| 3 | Vault interface: folders, logins, notes, cards, identities, generator, search, lock screen, trash | **COMPLETED** — v0.3.0, run 42652258834 |
| 4 | TOTP authenticator and password-health reporting | **COMPLETED** — RFC vectors asserted |
| 5 | Android autofill integration | NOT STARTED |
| 6 | Encrypted cloud-drive synchronisation and Phase 2 integrations | **IN PROGRESS** — backup, restore, a tested per-item merge and shared-folder sync are done; a background or scheduled sync is not |

---

## 2026-11-10 — Shared-folder sync, with no provider in sight

**Status: two devices keep each other in step.** CI run `42800987845`: analyser
clean, **371 tests pass**, up from 319.

A folder both devices can reach, and nothing else. No account, no sign-in, no
API key, no SDK, no paid tier — and nothing in this codebase can tell whether
the folder is Google Drive, OneDrive, Dropbox, Syncthing, a network share or a
USB stick. That is also the strongest available statement about what the
provider learns: it moves opaque files.

Each device writes one file holding its own copy of the vault. A sync reads
every **other** device's file, merges them all in through `VaultMerge`, then
writes its own file back carrying the merged result — so a third device picks
up the first through the second without the two ever meeting directly.

### The problem that shaped the design

The session deliberately never keeps the master password. A Dart `String`
cannot be wiped, so the password is used once and discarded, leaving only a key
derived with **this vault file's own salt**. Another device's file has a
different salt, so that key cannot open it, and nothing else in memory can.

| Option | Rejected because |
|---|---|
| Prompt for the master password at every sync | Defeats the purpose, and trains the user to type their master password at a prompt that appears on a schedule |
| Require both devices to share a master password | A restriction the rest of the design does not impose, and it fails silently the moment one device's password changes |
| **Chosen: a sync secret inside the encrypted payload** | 32 bytes of randomness, held as hex so it is used wherever a password is expected — the existing vetted `seal`/`open` path, no new format, no new primitive |

The secret reaches the second device through the one manual backup-and-import
that sets sharing up, and never through the shared folder. It is not a second
way into the vault: the vault file is still sealed with a key from the master
password. Recorded as D-013; the provider-free folder choice as D-014.

### Three faults the tests exist to prevent

Each would be quiet damage rather than a visible error, which is what makes
them worth tests rather than care:

| Fault | What it would do |
|---|---|
| A device reads **its own** file back | Merges with a stale copy of itself: reports changes that never happened, and resurrects anything deleted since that file was written |
| One bad file stops the whole sync | A sync client caught mid-upload is the normal case, so sync would fail most of the time. An unreadable file is reported by name and the rest merge anyway |
| The merged vault is sealed with the **sync secret** | Locks the user out of their own vault with a 64-character string they have never seen. A test locks and re-unlocks with both, asserting the secret fails and the master password works |

Device names are slugged into file names, with tests that `***`,
`../../etc/passwd` and `..\..\windows` cannot produce an empty name or a path
that escapes the folder.

### Where each setting lives, and why

| Setting | Where | Why not the other place |
|---|---|---|
| Sync secret | Inside the encrypted payload | Must travel with the vault, and must never be written in the clear |
| Folder path, device name | A small plaintext `device.json` beside the vault | A path is meaningless on the other device, and a device name exists precisely to tell the two apart — in the vault, each device would overwrite the other's at every merge |

`device.json` is the only file this application writes in the clear, so a test
states what it may contain: those three values and nothing resembling a
password, a key or the sync secret.

### Build failures, and what each turned out to be

| Run | Failure | Cause |
|---|---|---|
| 42799506133 | Formatter, 8 files | Diff applied from the `if: failure()` step |
| 42800239492 | `prefer_initializing_formals` on `VaultSync._codec` and `_folder` | The same unsatisfiable lint as `Folder._updatedAt` before it: a named parameter may not begin with an underscore. Fields made public, with the note `VaultSession.repository` already carries |
| 42800239492 | `unnecessary_import` of `dart:typed_data` | `package:flutter/foundation.dart` exports `Uint8List`; `material.dart` does not, which is why `backup_view.dart` legitimately imports it and `vault_sync.dart` must not |

And one self-inflicted: a blanket replace of `_codec.` with `codec.` also
rewrote `import 'vault_codec.dart'` into `import 'vaultcodec.dart'`. The second
time that exact trap has caught me in this project. The structural check
(import resolution plus delimiter balance) caught it before the push, which is
the only reason it cost nothing.

### Not built, and not claimed

- **Nothing runs in the background.** A sync happens when the button is
  pressed. A folder-watching or scheduled sync would change *when* a merge
  runs, not what one does.
- No conflict history. The merge keeps the more recent edit and reports how
  many entries that applied to; the older version is gone.
- Still outstanding from before: biometric unlock, Android screenshot
  blocking, device-keystore key wrapping, Android autofill, CSV import,
  Windows installer.

---

## 2026-11-10 — Backup, restore, and a merge that converges

**Status: the vault can leave the device it was made on, and come back.**
CI run `42797277075`: analyser clean, **319 tests pass**, up from 264.

Until this point a lost phone was a lost vault. Three things were built, in
this order and deliberately not the other one.

### 1. Schema 2: tombstones and change stamps

Sync needs two things the old schema could not carry.

| Added | Why the merge cannot work without it |
|---|---|
| `Tombstone` (id + `purgedAt`), kept 182 days | A device that still holds a purged entry re-adds it at the next merge. Without tombstones, "delete for good" would be temporary. |
| `Folder.updatedAt` | Two renames of the same folder are otherwise indistinguishable, so a merge would have to guess which came later. |
| `VaultData.settingsUpdatedAt` | Settings otherwise follow whichever file happened to be read second. |

Schema 1 files still open: both new fields read as absent, and a folder with
no stamp gets its creation time, which correctly loses to any later rename.

### 2. `VaultMerge`: last-write-wins per entry

Pure Dart, no file, network or platform dependency — which is why it could be
written and tested before any of the plumbing existed.

| Rule | Reasoning |
|---|---|
| Newer `updatedAt` wins | The only clock available without a server. |
| A tie breaks on the encoded JSON, compared lexicographically | Arbitrary, but **symmetric**: both devices pick the same side. A "sensible" rule each device applies to its own side leaves them disagreeing for ever. |
| A tombstone wins unless the entry was edited after the purge | Editing a password on one device while the other purges it keeps the edit. The safer direction to fail. |
| An item whose folder did not survive is unfiled, not dropped | Losing the folder must not lose the password inside it. |
| Output sorted by id | The encoded payload is then byte-identical on both devices. |

Two properties are asserted, on hand-built cases and on 100 seeded random
vault pairs each:

- **convergence** — `merge(a, b)` encodes identically to `merge(b, a)`
- **idempotence** — merging the result with either input changes nothing

### 3. Backup, restore and import screens

Export writes the same encrypted format as the live vault, so an unencrypted
copy never exists, not even briefly in a temporary file. It takes either the
vault's master password or one of its own; when it takes the master password,
the password is **checked against the file on disk first**, because a key
derived from a typo produces a backup nobody can open and the user would not
find out until the day they needed it.

Import is read → describe → apply. The file is decrypted and decoded, the user
is shown what is in it and what applying it would do, and only then is
anything written. It merges; it does not overwrite.

Restore sits on the **setup screen**, not in Settings: a replaced or wiped
device reaches that screen and nowhere else, and it is the one moment when a
vault can be rebuilt from a file with no risk of overwriting a live one —
`createFromBackup` refuses outright if a vault already exists.

### The platform difference is handled, not papered over

`file_selector_android` implements `openFile` and `getDirectoryPath` but
**not** `getSaveLocation`. This was established by resolving the package in CI
(run `42790776305`) and reading it, not from memory:

```
file_selector_android-0.5.2+11/lib/src/file_selector_android.dart:51:
  Future<String?> getDirectoryPath({...})
```

Android's system chooser returns a `content://` URI rather than a path, so
there is no save dialog to offer. Saving on Android therefore goes through the
share sheet and the button reads "Share a copy" instead of "Save a copy".
Opening a file is the same call on both platforms. The same run confirmed both
packages build on Android and Windows before a line of code depended on them.

### Two real faults the tests caught

**The merge did not converge.** When neither side had ever stamped its
settings — two pre-schema-2 files, or two users who never changed a setting —
the rule was "keep mine", which reads as harmless and is not: each device
keeps its own settings, every merge reports a change, and the two never agree.
Caught on **round 1 of 100** random pairs. It now falls through to the same
symmetric tiebreak used for an exact timestamp tie. This is the entire reason
the convergence property was written before the sync plumbing.

**The password dialog used a disposed controller.** Disposing the
`TextEditingController` when the dialog's future completed disposed it while
the dialog was still animating out, so the field rebuilt once more against a
disposed controller and threw. Replaced with `PasswordPrompt`, a
`StatefulWidget` that owns its controller, so its life is tied to the dialog's
own, closing animation included.

### A test that was wrong about its own subject

One test demanded the unlock failure message **not** contain the word
"password", reasoning that naming the password tells an attacker the file is
intact. The real message — "The master password may be wrong, or the file may
have been changed or damaged" — names both causes and commits to neither,
which is the property actually wanted. The code was right and the test was
wrong; the test was corrected to assert that both halves are present. Worth
recording, because the tempting move in that moment is to "fix" working code
to satisfy a confused assertion.

### Build failures, and what each turned out to be

| Run | Failure | Cause |
|---|---|---|
| 42792067695 | Formatter | Two files; diff applied from the `if: failure()` step |
| 42793420378 | Formatter | Four files — and the step also produced the resolved `pubspec.lock` for 25 new transitive packages and the Windows plugin registration, neither of which this environment can generate |
| 42793932243 | `Undefined class 'Uint8List'` | `package:flutter/material.dart` does not export it; only `services.dart` does, which is why `vault_session.dart` never needed the import |
| 42793932243 | `prefer_initializing_formals` on `Folder._updatedAt` | Unsatisfiable as written: a named parameter may not begin with an underscore. Resolved by making `updatedAt` required and non-nullable and moving the fallback into `fromJson` |
| 42794629158 | `Binding has not yet been initialized` | `VaultSession.dispose` unregisters a `WidgetsBindingObserver`; needs a binding even with no widgets |
| 42794629158 | Section not found in the tree | The test created the vault by calling the session, then started the app — whose startup calls `initialise`, which sets the status from whether a file exists, so the vault came back **locked** and every test landed on the unlock screen |
| 42795423782 | Merge divergence, disposed controller | The two real faults above |

### Not yet built, and not claimed

- No automatic sync. Keeping two devices in step means exporting on one and
  importing on the other, both ways. The merge makes that safe and repeatable;
  nothing watches a folder yet.
- No replace-wholesale import. Merge only, on purpose: a wholesale replace can
  silently drop an entry the other side never had.
- Still outstanding from before: biometric unlock, Android screenshot
  blocking, device-keystore key wrapping, Android autofill, CSV import,
  Windows installer.

---

## 2026-11-09 — Stages 3 and 4: a working password manager, v0.3.0

**Status: COMPLETED.** CI run `42652258834` green on all three jobs.
**264 tests pass**, up from 91. Released as
[v0.3.0](https://github.com/Samby28/family-vault/releases/tag/v0.3.0) with both
installers. This is the first version that holds a real password.

### Evidence

| Check | Result |
|---|---|
| `dart format`, `flutter analyze` | PASS, both blocking |
| `flutter test` | **264 of 264 passed** |
| RFC 6238 / RFC 4226 vectors | **Asserted**, SHA-1, SHA-256 and SHA-512, all ten HOTP counters |
| RFC 4648 base32 vectors | **Asserted** |
| Android APK | **Built, 53.8 MB**, published |
| Windows application | **Built**, published |
| Argon2id, 64 MiB / 2 passes | seal 64 ms, open 68 ms on CI hardware |

### What a user can now do

Create a vault; save logins, secure notes, payment cards and identities;
organise them in folders; search; generate passwords, passphrases and
usernames; hold two-factor codes for other accounts with a live countdown; see
a password-health score with specific advice; restore from trash; change the
master password; lock by hand, on a timer, or when the app leaves the screen.

### Two real bugs the tests caught before the owner could

**Tapping Add would have crashed the app.** `SessionScope` was passed as
MaterialApp's `home`, but MaterialApp builds the Navigator, so a route pushed
onto it is a sibling of `home` rather than a descendant. Every pushed screen —
the item editor and the generator — could not find the session and threw while
building. Found only because the widget tests drive the real screens rather
than asserting that they render.

**The health check missed an obviously guessable password.** The sequence
detector required the whole password to be one unbroken run, so
`123456789012` passed because it wraps from 9 back to 0. It now flags a run of
five or more anywhere in the password.

### Test failures, and what each turned out to be

Nine runs. Worth separating the ones that found product bugs from the ones that
found mistakes in the tests, because the ratio is the point of writing them.

| Cause | Where the fault was |
|---|---|
| `SessionScope` below the Navigator | **Product** |
| Sequence check required a whole-password run | **Product** |
| `WidgetsBindingObserver` imported from `foundation.dart` instead of `widgets.dart` | **Product** (would not compile) |
| Private field as a named initializing formal — not legal Dart | **Product** |
| `isValid('not a key')` asserted false, but NOTAKEY is valid base32 | Test — the code was right |
| Taps on widgets below the fold in an 800×600 window did nothing | Test |
| Surface size set without the pixel ratio, leaving ~367 logical px | Test |
| Auto-lock timer still pending when the test ended | Test harness |
| Looked for an entry name on the dashboard, which shows counts only | Test |

Four product faults, five test faults. The two in bold would both have reached
the owner's phone.

### Decisions taken during this stage

**One item class, not four.** Common fields are typed; the parts that differ by
kind live in a map keyed by constants, and each `VaultItemType` carries its own
field list with labels and input kinds. One form renders all four kinds, and a
fifth kind needs no new screen. That is what "extensible to future item types"
comes to in practice.

**Saving never keeps the master password.** The password is used once to derive
a key; that key then lives in libsodium's locked memory, which can be wiped. A
Dart `String` cannot be wiped, so holding the password would leave it on the
heap for the life of the process. Saving re-seals with the held key.

**Writing is three steps.** Write to a temporary file and flush, move the
existing vault aside as a backup, then rename the temporary file into place. A
rename within a directory is atomic, so the real file is never half-written,
and a crash mid-save leaves the backup intact. Tested by checking the vault is
complete and current after each of ten successive writes.

**A failed write does not change what the interface shows.** Telling someone
their password was saved when it was not would be the worst available failure.

**No state-management package**, as decision D-005 anticipated: Flutter's own
`InheritedNotifier` carries the single piece of shared state here.

### The published APK was inspected, not taken on trust

| Check | Result |
|---|---|
| Archive integrity | PASS, no errors in compressed data |
| Recognised as an Android package | PASS |
| Native libraries | `arm64-v8a`, `armeabi-v7a`, `x86_64` |
| **libsodium bundled** | **Yes** — `libsodium.so` present in all three architectures, so the cryptography really ships with the app |
| Compiled Dart and Flutter engine | `libapp.so` and `libflutter.so` in all three |
| Signature | APK Signing Block present, consistent with the debug-key signing of decision D-006 |
| Size | 51.3 MB |

### Not yet verified

| Not verified | Resolved by |
|---|---|
| Argon2id timing on a real phone | 64 ms on CI says little about a mid-range Android; measuring on the owner's device |
| Daily use with real entries | The owner using it |

### Known gaps, stated rather than glossed

No syncing, so each device holds a separate vault and losing the device loses
the vault. No Android autofill, no CSV import, no biometric unlock, no
screenshot blocking, no hardware-backed device key, no recovery sheet. Encrypted
export exists in the session but has no screen. All of it is in
`docs/known-limitations.md` and in the app's own settings screen.

---

## 2026-11-09 — Stage 2: cryptographic core

**Status: COMPLETED.** CI run `42625696754` green on all three jobs.
**91 tests pass**, up from 11. Five runs were needed; every failure is below.

### Evidence

| Check | Result |
|---|---|
| `dart format` | PASS, blocking |
| `flutter analyze` | PASS, no issues |
| `flutter test` | **91 of 91 passed** |
| Security tests against real libsodium | **Ran**, not skipped — 22 cases |
| Argon2id, 64 MiB / 2 passes | seal 60 ms, open 60 ms on CI hardware |
| Android APK | Builds with libsodium |
| Windows application | Builds with libsodium |

### Decision D-003, settled on evidence

XChaCha20-Poly1305 and Argon2id, both from libsodium through
`package:sodium` 4.1.2+1. Three probe runs answered what this environment
cannot: whether a native dependency still builds on both platforms, and what
the library's real API is. `package:cryptography` was ruled out because its own
listing records that its repository moved "due to lack of maintenance", and
because a pure-Dart Argon2id would make unlocking slow on a phone. Full
reasoning, including why XChaCha20-Poly1305 rather than AES-256-GCM, is in
`docs/decisions-and-risks.md`.

### What the security tests actually assert

Not that encryption "works", but the specific properties the product rests on:

- A wrong password cannot open a vault — including one differing by a single
  character, and an empty one.
- **A bit flipped at every single byte position in the file is refused.** The
  test walks the whole file, header included, and asserts every one fails.
- Truncating at any point, appending a byte, and splicing another vault's
  sealed section or header are all refused.
- Two vaults with the same password get different salts.
- The failure for a wrong password is indistinguishable from the failure for a
  damaged file, so neither tells an attacker whether a guess was close.
- No failure message contains the password or the payload.

### Build failures, and how each was fixed

| # | Run | Failed at | Cause | Fix |
|---|---|---|---|---|
| 1 | 42622294291 | `dart format` | Two conditions wrapped that fit on one line | Applied the printed diff |
| 2 | 42623376449 | `dart format` | **The formatter had changed underneath the project.** Raising the SDK floor to 3.13.0 for `sodium` also raised the language version past 3.7, which switches `dart format` from "short" to "tall" style — so a dependency fix silently reformatted the whole codebase | Applied the full 12-file diff from the log, verified with `git apply` |
| 3 | 42624506031 | `flutter analyze` | `SodiumSumoInit.init()` returns `FutureOr<SodiumSumo>`, not `SodiumSumo`. Probe 2 had read the FFI-specific declaration; the conditional export resolves to one that may be asynchronous, because the web target loads a WebAssembly module first | `initialise()` is now an awaited static method, which covers both targets from one call site |
| 4 | 42624506031 | `flutter analyze` | A duplicated `const` left by an earlier scripted edit, and a redundant `dart:typed_data` import | Removed both |
| 5 | 42625696754 | — | — | **Green.** |

Two things are worth keeping from that list. The formatter-style change was
found only because the formatter contradicted itself between runs, asking for
opposite layouts of the same construct; the cause was a coupling between the
SDK constraint and the formatter that is easy to miss. And the diagnostic step
added in Stage 1, which prints the formatter's diff on failure, paid for itself
twice here — the layout was applied verbatim rather than guessed at, which
would have cost several runs.

The evidence table in D-003 was corrected rather than quietly edited: probe 2's
claim that initialisation was synchronous was wrong, and the record now says so
and why.

### Not yet verified

| Not verified | Resolved by |
|---|---|
| Argon2id timing on a real phone | Measuring on the owner's device; 60 ms on CI says little about a mid-range Android |
| That the vault format is right for real data | Stage 3, when items exist to store |

No vault can be created or opened from the interface yet. The core is tested
but not yet wired to a screen, so v0.1.0 remains the installable build and
still must not hold real passwords.

---

## 2026-11-09 — Stage 1 closed: pipeline green on all platforms

**Status: COMPLETED.** CI run `42612638343` on commit `83e45b6` is green on all
three jobs. Four pushes were needed; each failure, including one I misreported,
is recorded below.

### Evidence

| Check | Result |
|---|---|
| Toolchain | Flutter 3.47.9, stable, now pinned in all workflows |
| `dart format` | PASS, blocking |
| `flutter analyze` | PASS, no issues |
| `flutter test` | **11 of 11 passed** |
| Android release APK | **Built, 45.8 MB** (`app-release.apk`, 21.5 MB compressed artifact) |
| Windows release build | **Built**, `family_vault.exe` (11.3 MB compressed artifact) |
| Web demonstration | **Built**, downloadable artifact; live URL blocked on Pages |
| Coverage | Collected and uploaded |

### Build failures, and how each was fixed

Four CI runs were needed. Per MP 17, each is recorded rather than hidden.

| # | Run | Failed at | Cause | Fix |
|---|---|---|---|---|
| 1 | 42609591764 | `flutter analyze` | `dangling_library_doc_comments` in `build_info.dart` — a file-level doc comment with no `library` directive to attach to | Added `library;` |
| 2 | 42610134562 | `dart format` | **A failure I had misreported.** Run 1 showed the format step as "success", so I stated in a commit message that the hand-written source was already format-clean. It was not: the step carried `continue-on-error`, which reports a step as successful even when the command fails. Making the check blocking is what exposed it. | Corrected the record in the next commit message; added a step that prints the formatter's diff on failure, since this environment has no Dart SDK to run the formatter |
| 3 | 42610812140 | `dart format` | Two test files laid out differently from the formatter's preference | Applied the printed diff verbatim rather than guessing |
| 4 | 42611264390 | — | — | **Green.** APK and Windows build both produced |

The lesson from failure 2 is now a standing rule for this project: **`continue-on-error`
makes a step report success, so it hides exactly what CI exists to reveal.** It is
used only where a failure is genuinely acceptable, and where it is used, a
following step states plainly what failed and what to do about it. The Pages
deployment is the one remaining place it appears, and it now does that.

### Also done in this stage

- **Platform projects committed.** `android/`, `windows/` and `web/` were
  generated in CI from Flutter 3.47.9's templates and committed, along with the
  resolved `pubspec.lock`. The repository is now self-contained: a reviewer can
  clone it and run `flutter build` with no extra step. The one-time bootstrap
  workflow was removed; `tool/bootstrap_platforms.sh` stays as a no-op for a
  clean tree.
- **Product names corrected.** The generated templates carried the Dart package
  name `family_vault` into the Android launcher label, the Windows title bar and
  file properties, and the web page title. All are now "Family Vault". Identifiers
  (`applicationId`, `namespace`, Kotlin package, `BINARY_NAME`) were deliberately
  left alone, because an application identifier is a permanent identity and
  changing it later would stop an installed app upgrading in place.
- **Flutter pinned** to 3.47.9 so builds stay reproducible and the toolchain is
  raised deliberately rather than drifting with the stable channel.

### Release v0.1.0 published

Release workflow run `42613649843`, all three jobs green:
<https://github.com/Samby28/family-vault/releases/tag/v0.1.0>

| Asset | Size |
|---|---|
| `FamilyVault-Android.apk` | 43.7 MB |
| `FamilyVault-Windows.zip` | 10.8 MB |

The published APK was downloaded and inspected rather than taken on trust:

| Check | Result |
|---|---|
| Archive integrity | PASS, no errors in compressed data |
| Recognised as an Android package | PASS |
| Native libraries | `arm64-v8a`, `armeabi-v7a`, `x86_64` — covers current phones |
| Compiled Dart | `libapp.so` present in all three architectures |
| Flutter engine | `libflutter.so` present in all three |
| Bundled assets | `flutter_assets` present |
| Signature | APK Signing Block present (v2/v3 scheme), consistent with the debug-key signing recorded in decision D-006 |

A note on how the tag was created: `git push origin v0.1.0` failed twice with
`send-pack: unexpected disconnect`, which appears to be a limit of this
session's git proxy on annotated tag objects rather than anything about the
repository — branch pushes succeeded throughout. The release was therefore
created by dispatching the release workflow with its `tag` input, which the
workflow already supported. The outcome is identical; it is recorded here so
the absence of a locally pushed tag object is not a mystery later.

### Secret scan of the public repository

| Check | Result |
|---|---|
| Tracked files with vault, keystore, key or env extensions | **None** |
| Hard-coded passwords, private keys or API keys in source | **None** |
| Tracked files total | 66 |

### Blocked

**Open question 2 — GitHub Pages is not enabled**, so the web demonstration has
no public URL. The build itself succeeds and the demo is downloadable from the
`family-vault-web-demo` artifact, so nothing is lost but the shareable link.

*Owner action:* at **Settings → Pages**, set Source to **GitHub Actions**. The
next push publishes it to `https://samby28.github.io/family-vault/`.

R-001 (no write access) is **closed** — the first push succeeded.

### Owner device verification — 9 November 2026

The owner installed and ran v0.1.0 on both targets. **Both run.**

| Target | Result |
|---|---|
| Android phone | APK installs and the app runs |
| Windows laptop | Application runs |

The owner noted that no information can be entered and no sections open. That
is the expected Stage 1 behaviour, not a fault: there is no vault yet, so there
is nothing to type into, and tapping a section raises a message saying it is not
built rather than opening an empty screen.

This closes the two items that had been held at TESTING because nothing had run
outside a CI container. B9.1 and B10.1 are now COMPLETED.

### Superseded: not yet verified at the time of the entry above

| Not verified | Resolved by |
|---|---|
| The APK installs and runs on a real phone | Owner installing it from the Releases page |
| The Windows build runs on a real Windows machine | Owner unzipping and running it |
| Behaviour on a physical device of any kind | Owner testing |

Nothing has run outside a CI container. The builds exist and are green; that is
not the same as having been used.

---

## 2026-11-09 — Stage 1: scaffold and pipeline

**Status: superseded by the entry above, which closes this stage.** At the time
of writing, nothing had been compiled or executed, because the authoring
environment has no Flutter or Android SDK
and its network policy refuses `pub.dev`, `dl.google.com`, `maven.google.com`
and `services.gradle.org`. This was verified by direct connection attempts, not
assumed. The first CI run is the first compilation and the first test execution.

### Completed

**Documentation**

| File | Contents |
|---|---|
| `docs/requirements-checklist.md` | 120+ requirements consolidated from both source documents, each traced to its source and given a status |
| `docs/architecture.md` | Layered architecture, dependency rules, directory layout, unlock sequence, vault format outline, technology decisions |
| `docs/decisions-and-risks.md` | 10 design decisions with reasoning and rejected alternatives; 10-entry risk register; 3 open questions for the owner |
| `docs/known-limitations.md` | What is not implemented, what will always be limited, build and testing limitations |
| `README.md` | Product overview, security design, install and build instructions |
| `docs/progress-log.md` | This file |

**Application scaffold**

| File | Purpose |
|---|---|
| `pubspec.yaml` | Project metadata. **No third-party runtime dependencies** (decision D-002) |
| `analysis_options.yaml` | `flutter_lints` plus strict casts, strict inference, strict raw types, and `avoid_print` to keep secrets out of device logs |
| `lib/main.dart` | Entry point |
| `lib/src/app/build_info.dart` | Version, stage and the compile-time `isDemoBuild` flag |
| `lib/src/app/theme.dart` | Seeded light and dark themes |
| `lib/src/app/navigation_plan.dart` | The twelve navigation sections as public, testable data with honest status values |
| `lib/src/app/family_vault_app.dart` | Root widget, follows the platform light/dark setting |
| `lib/src/features/home/shell_screen.dart` | Stage 1 shell: responsive, states the current stage, lists planned sections, no empty screens implying features |

**Tests written** (11 cases, not yet executed)

| File | Covers |
|---|---|
| `test/navigation_plan_test.dart` | Section count, exact order, non-empty summaries, no duplicate labels, and an honesty guard asserting nothing is marked working at Stage 1 |
| `test/app_shell_test.dart` | App builds, product name shown, sections listed, stage stated, about dialog reports the version, tapping an unbuilt section says so, no demo banner in a normal build |

**Build pipeline**

| Workflow | Jobs |
|---|---|
| `ci.yml` | `quality` (resolve, format check, analyse, test, upload coverage) then `android` (universal release APK) and `windows` (release build, zipped) in parallel |
| `web-demo.yml` | Build the demo with `FAMILY_VAULT_DEMO=true`, upload a downloadable copy, deploy to Pages |
| `release.yml` | On a `v*` tag: test and build both platforms, then publish to a GitHub Release with plain-language install notes |

**Supporting**

| File | Purpose |
|---|---|
| `tool/bootstrap_platforms.sh` | Generates `android/`, `windows/` and `web/` from Flutter's templates, only when absent, in a scratch directory so app code can never be overwritten (decision D-004) |
| `.gitignore` | Security guard first: blocks `*.fvault`, `*.keystore`, `*.jks`, `*.p12`, `*.pem`, `*.key`, `key.properties`, `*.env`, `recovery-sheet*` and password CSV patterns |

### Verified locally

What could be checked without a Flutter SDK was checked:

| Check | Result |
|---|---|
| All five YAML files parse | PASS — `ci.yml` (3 jobs), `release.yml` (3 jobs), `web-demo.yml` (2 jobs), `pubspec.yaml`, `analysis_options.yaml` |
| `tool/bootstrap_platforms.sh` shell syntax | PASS — `bash -n` clean |
| Bootstrap script behaviour | PASS — correctly detects all three platform directories absent and attempts generation |
| Dart import graph | PASS — every relative import resolves to a file that exists |
| Repository contains no secret material | PASS — no vault, key, keystore or credential file present |

### Not verified

| Not verified | Why | Resolved by |
|---|---|---|
| The Dart code compiles | No Dart SDK available | First CI run |
| Tests pass | No Flutter SDK available | First CI run |
| `flutter analyze` is clean | No analyser available | First CI run |
| Dependency resolution succeeds | `pub.dev` refused | First CI run |
| The APK installs and runs | No Android SDK or device | Owner testing on a physical phone |
| The Windows build runs | No Windows machine | First CI run, then owner testing |

### Failed

Nothing has failed, because nothing has yet been executed. This is recorded
explicitly so that "no failures" is not mistaken for "tests passed".

### Blocked

**R-001 — pushes to the repository are refused.** The repository
`Samby28/family-vault` was attached successfully and can be read, but this
session reports that it lacks write access, so no commit can reach GitHub and no
build can run.

**Owner action required:** authorise the Claude GitHub App for the repository at
`https://github.com/apps/claude/installations/select_target`. If it reports the
app is already installed, reconnect GitHub from claude.ai → Settings →
Connectors.

Everything above is written and waiting locally; the push is the only thing
standing between it and the first build.

### Next

1. Owner authorises repository write access.
2. Push Stage 1; read the first CI run.
3. Fix whatever the analyser and the test run report, per MP 17 — iterate until
   green, and record each failure and its resolution here.
4. Pin the Flutter version to the first known-good release; make the format
   check blocking.
5. Commit the generated `android/`, `windows/` and `web/` directories and the
   resolved `pubspec.lock`.
6. Tag `v0.1.0` so the first installable APK reaches the Releases page.
7. Begin Stage 2: evaluate Argon2id and AEAD libraries in CI on both platforms,
   settle decision D-003, then build the crypto core test-first.
