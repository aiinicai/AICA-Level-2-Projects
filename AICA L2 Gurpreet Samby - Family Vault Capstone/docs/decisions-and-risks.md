# Family Vault — Design Decisions and Risk Register

**Version:** 1.0 · **Date:** 9 November 2026

Every decision here was taken without consulting the project owner, as the engagement
directs. Each records what was chosen, what was rejected, and why. Where a decision
deviates from a literal reading of the source documents, the deviation is stated plainly.

---

## Part 1 — Design decisions

### D-001 · CI is the build and compile environment

**Decision.** All compilation, analysis, testing and packaging happens in GitHub Actions.
No build is attempted in the authoring environment.

**Why.** The authoring environment has no Flutter or Android SDK and its network policy
refuses `pub.dev`, `dl.google.com`, `maven.google.com` and `services.gradle.org`. This was
verified by direct connection attempts, not assumed.

**Consequence.** Turnaround on a compile error is one CI run rather than one second. The
pipeline is therefore ordered to fail fast and cheap: format, then analyze, then test,
then build.

---

### D-002 · Phase 1 ships with no third-party runtime dependencies

**Decision.** The Stage 1 scaffold depends only on the Flutter SDK itself. Third-party
packages are introduced one per commit from Stage 2 onward, each confirmed green in CI
before the next is added.

**Why.** A package version cannot be resolved or verified here. Declaring several unknown
dependencies at once would make the first build fail for reasons that are hard to
separate. Starting at zero makes the first build near-certain, which establishes the
pipeline as a reliable signal before it is relied upon.

**Rejected.** Declaring the full Stage 2 dependency set now and fixing fallout. Faster if
it works, considerably slower if it does not, and it would delay the first installable
APK, which the build route document makes an early priority.

---

### D-003 · XChaCha20-Poly1305 and Argon2id, both from libsodium

**Decided 9 November 2026**, on evidence from three CI probe runs rather than
on preference.

**Decision.** The cipher is XChaCha20-Poly1305 (IETF construction) and the key
derivation is Argon2id, both from libsodium through `package:sodium` 4.1.2+1.

**How the alternative was ruled out.** `package:cryptography` was the only
serious pure-Dart candidate. Its own listing records that the repository moved
"due to lack of maintenance", and it carries discontinued dependencies. D-003
named active maintenance as the deciding factor, so it was out on that ground
alone. The deeper problem was Argon2id: it is memory-hard by design, so a
pure-Dart implementation would make unlocking slow on a phone, and lowering the
cost to compensate is exactly the wrong trade for a password manager.

**Why XChaCha20-Poly1305 over AES-256-GCM.** Its nonce is 192 bits. At that
size a nonce can be drawn at random for every single write with no realistic
chance of a repeat, which removes nonce management — and with it the
counter-handling mistake that breaks AES-GCM catastrophically. AES-GCM's
96-bit nonce is too short for that to be safe, so it would need a counter
persisted across writes and devices, which is precisely the kind of state that
goes wrong during a cloud sync conflict. Hardware-accelerated AES would have
been faster, but the payload here is a vault file of kilobytes, so throughput
is irrelevant and safety is not.

**What the probes established.**

| Probe | Run | Finding |
|---|---|---|
| 1 | 42618366937 | `sodium` resolves; an Android APK and a Windows application both still build with libsodium added; libsodium 1.0.18 installs on the Linux runner |
| 1 | 42618366937 | No `pwhash.dart` in the base API — Argon2id is in the "sumo" interface, not the default one |
| 2 | 42619562544 | `SodiumSumoInit.init()` uses a bundled libsodium, so no dynamic-library loader is needed; `Aead.encrypt`/`decrypt` accept `additionalData`, which is what lets the header be authenticated; `sodium_libs` is **deprecated**, with everything moved into `sodium` |
| 3 | 42620302996 | `CryptoPwhashAlgorithm.argon2id13` is the explicit Argon2id value; `sodium` alone builds on both platforms without the deprecated wrapper |
| 4 | 42624506031 | Correction to probe 2: `SodiumSumoInit.init()` returns `FutureOr<SodiumSumo>`, not `SodiumSumo`. The signature probe 2 read was the FFI-specific one; the conditional export resolves to a declaration that may be asynchronous, because the web build has to load a WebAssembly module first. Initialisation is therefore awaited, which covers both targets from one call site |

**Consequences recorded elsewhere.** Argon2id is named explicitly at the call
site rather than left to the library default, because the same call also offers
Argon2i and a password manager should not infer which function protects the
vault. `sodium_libs` is not used. The header reserves an algorithm identifier
for both the KDF and the cipher, so a future third option needs no format
break.

### D-004 · Platform projects are generated, then committed

**Decision.** The `android/`, `windows/` and `web/` directories are generated by
`flutter create` in CI on the first run via `tool/bootstrap_platforms.sh`, and will then
be committed to the repository so the project is self-contained for a reviewer.

**Why.** Hand-writing a Gradle and CMake project blind is a large, needless risk; Flutter's
own templates are correct by construction. The script copies a platform directory only if
it is absent, so once the real files are committed it never overwrites them.

**Consequence for assessment.** A reviewer who clones the repository after Stage 1 gets a
complete, buildable project. Between now and that commit, the script closes the gap.

---

### D-005 · No state-management library in Stage 1

**Decision.** The Stage 1 shell uses Flutter's own `StatefulWidget`. A state-management
library is chosen in Stage 3, when there is real state to manage.

**Why.** Picking Riverpod, Bloc or Provider now would mean an unverifiable dependency in
the first build for no present benefit, contradicting D-002. The layered architecture
already isolates the presentation layer, so introducing a library later touches only that
layer.

---

### D-006 · Release APK is debug-signed in Phase 1

**Decision.** The Android release APK is signed with Flutter's default debug key until a
release keystore exists.

**Why.** A real signing key must be generated by the owner and held as a repository
secret; it cannot be created here, and committing one to a public repository would be a
serious error. A debug-signed APK installs and runs correctly for family use and faculty
assessment.

**Stated limitation.** A debug-signed APK is not suitable for Play Store distribution and
shows an "unknown developer" warning on install. Recorded in `docs/known-limitations.md`.

---

### D-007 · The web demo is a separate, data-isolated build

**Decision.** The web demonstration is built from the same codebase behind a compile-time
demo flag. It is seeded with synthetic data, labelled as a demonstration in the interface,
and has no access to a real vault file.

**Why.** Browser storage is not a safe place for a real vault, and the demo exists for
assessment rather than use. A compile-time flag, rather than a runtime setting, means the
demo build physically cannot open a real vault file.

---

### D-008 · Vault header is plaintext but authenticated

**Decision.** The format version, KDF parameters, salt, cipher identifier and nonce are
stored unencrypted, and are covered by the AEAD authentication tag as associated data.

**Why.** They are required *in order to* derive the key, so they cannot be encrypted under
it. Authenticating them means tampering invalidates the file instead of silently weakening
it — for instance, an attacker lowering the Argon2id cost to make a brute-force cheaper.

**Accepted exposure.** An attacker holding the file learns that it is a Family Vault file,
its format version and its KDF cost. None of these reveal anything about the contents.

---

### D-009 · Argon2id parameters validated against bounds before use

**Decision.** Parameters read from a vault header are checked against a permitted range
before any memory is allocated.

**Why.** The parameters come from a file, and a file can be hostile. A header claiming
16 GB of memory cost would otherwise crash or hang the app on open — a denial-of-service
triggered by a file the user merely received. This is required by MP 5.3 and is a security
test case, not a nicety.

---

### D-010 · No TOTP gate on vault opening

**Decision.** Optional second-factor protection is implemented as key-file or FIDO2
hardware-key material mixed into key derivation. A TOTP code check is not offered for
opening a vault.

**Why.** With no server, an in-app code check is enforced by code the attacker controls,
on a file they already hold. It could be bypassed by patching the app or reading the file
directly, while giving the user a false sense of protection. A key file or hardware key
genuinely changes the decryption key and cannot be bypassed.

**This matches the source documents** and was the subject of the owner's explicit
instruction that vault 2FA be optional. The built-in TOTP authenticator for the user's
*other* accounts is unaffected and is a Phase 1 feature.

---

### D-011 · Import merges per entry; it never replaces a vault wholesale

**Decision.** Importing a backup compares the two vaults entry by entry and keeps
whichever side changed each entry more recently. There is no "replace my vault with
this file" option in the interface. Rebuilding from a file is offered only on the setup
screen, where there is no vault to replace.

**Why.** A wholesale replace silently discards every entry the other side never had —
the password added on the phone this morning, if the laptop's backup is the one
imported. The user cannot see what they lost, because the thing that would have told
them is the thing that was overwritten. A per-entry merge cannot lose an entry that
either side still holds.

**The cost.** The merge needs a clock per entry and a record of deliberate deletions,
which is what schema 2 adds (`Tombstone`, `Folder.updatedAt`,
`VaultData.settingsUpdatedAt`). Without tombstones, "delete for good" would be
temporary: any device still holding the entry would re-add it at the next merge.

**Ties are broken symmetrically, not sensibly.** When two devices changed the same
entry at the same recorded time, the winner is chosen by comparing the encoded JSON
lexicographically. That is arbitrary, and arbitrariness is the point: both devices
compute the same answer. A rule that sounds better — "keep what is on this device" —
leaves the two devices disagreeing for ever. The convergence property test caught
exactly this fault in the settings path.

---

### D-012 · Saving on Android goes through the share sheet, not a save dialog

**Decision.** Export uses a native save dialog on Windows, macOS and Linux, and the
system share sheet on Android. Opening a file uses the same call everywhere.

**Why.** `file_selector_android` does not implement `getSaveLocation`. Established by
resolving the package in CI run `42790776305` and reading it, rather than from memory:

| Platform package | `openFile` | `getDirectoryPath` | `getSaveLocation` |
|---|---|---|---|
| `file_selector_windows-0.9.3+6` | yes | yes | yes |
| `file_selector_android-0.5.2+11` | yes | yes | **no** |

Android's system chooser hands back a `content://` URI rather than a filesystem path,
so there is nothing for the application to write to. The share sheet is the platform's
own answer to "give this file to something else", and it reaches Drive, Files, email
and messaging apps without this project needing a credential for any of them.

**Consequence the user sees.** The button reads "Share a copy" on Android and "Save a
copy" on Windows, and after a share the application cannot report where the file went,
so it does not pretend to.

**Why handing an encrypted vault to an arbitrary app is acceptable.** The file is
sealed before it reaches the transfer layer. The share target receives ciphertext and a
header; without the password it is useless, which is the same reason it is safe on a
cloud drive.

---

### D-013 · The vault carries a sync secret; exchange files are not sealed with the master password

**Decision.** Each vault holds a `syncSecret`: 32 bytes from the cryptographic random
generator, stored inside the encrypted payload as 64 hexadecimal characters. The files
devices place in a shared folder are sealed with it. The vault file itself is still
sealed with a key derived from the master password; the secret is not a second way in.

**Why not the master password.** The session deliberately never keeps it (see the class
comment on `VaultSession`): a Dart `String` cannot be wiped, so the password is used once
and discarded, leaving only a key derived with **this vault file's own salt**. Another
device's file has a different salt, so that key cannot open it, and nothing else in
memory can either. Two ways out of that, both rejected:

| Rejected | Why |
|---|---|
| Prompt for the master password at every sync | Defeats the purpose of sync, and trains the user to type their master password in response to a prompt that appears on a schedule |
| Require both devices to share a master password | A constraint the rest of the design does not impose — two devices are otherwise fully independent — and it fails silently and confusingly the moment one device's password is changed |

**Why a hex string rather than a raw key.** Using the secret wherever a password is
expected means `seal` and `open` are the existing, vetted calls, with no new file format,
no key-wrapping scheme and no primitive written here. Running Argon2id over 256 bits of
randomness is wasted work, but it is work done twice per sync on a user action, and it
buys an unchanged crypto path — see MP's instruction never to implement cryptographic
primitives.

**How the second device gets it.** Through the one manual backup-and-import that sets
sharing up: the secret is inside the payload, so it travels with the vault. It is never
written to the shared folder in the clear and never leaves the device any other way.
This is why the interface states plainly that the other device must be set up from this
one — a consequence worth naming rather than leaving to be discovered as a mysterious
"could not open" message.

**The failure mode, and why it is reported as two possibilities.** A file sealed with a
different secret and a file half-written by the sync client are indistinguishable: both
fail authentication. The report offers both explanations rather than accusing the user of
a setup mistake that may not have happened.

---

### D-014 · The shared folder is a folder, and the app knows nothing about the provider

**Decision.** Sync works through any directory both devices can reach. There is no
provider integration, no OAuth, no API key, no SDK. The user picks a folder with the
platform's own folder picker — `getDirectoryPath`, which `file_selector_android`
**does** implement, unlike `getSaveLocation` (D-012).

**Why.** It satisfies MP's ban on paid services and mandatory subscriptions by not
having a service at all, and it works with Google Drive, OneDrive, Dropbox, Syncthing, a
network share or a USB stick without a line of code per provider. Nothing in this
codebase can tell which is in use, which is also the strongest possible statement about
what the provider learns: it moves opaque files.

**The cost, stated rather than hidden.** Nothing runs in the background. A sync happens
when the button is pressed. A folder-watching or scheduled sync is a later addition; it
would change when a merge runs, not what one does.

**Each device writes the merged result, not just its own changes.** A device reads every
other file, merges them all, then writes its own file carrying the result. So a third
device picks up the first through the second without the two ever meeting — tested in
`vault_sync_test.dart` — at the cost of each file growing to hold the whole vault, which
it does anyway.

---

## Part 2 — Risk register

Likelihood and impact are rated Low, Medium or High. Risks are ordered by current
priority.

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| ~~R-001~~ | ~~Pushes to the repository are refused~~ **CLOSED 9 Nov 2026**: the first push succeeded | — | — | — | — |
| R-002 | First CI build fails on an unforeseen toolchain detail | High | Medium | Zero dependencies in Stage 1; fail-fast pipeline ordering; logs read and fixed per MP 17 | Agent |
| ~~R-003~~ | ~~No Dart Argon2id library builds cleanly on both Android and Windows~~ **CLOSED 9 Nov 2026**: libsodium builds on both; verified by CI runs 42618366937 and 42620302996 | — | — | Resolved by decision D-003 | — |
| R-004 | Owner loses a master password and the vault becomes unrecoverable | Medium | **High** — permanent data loss | Explicit warnings at creation; Phase 2 recovery sheet; no false promise of recovery | Shared |
| R-005 | Android autofill proves unreliable across OEM skins | Medium | Medium | Built last in Phase 1, after the vault is stable; documented honestly if partial | Agent |
| R-006 | A real credential is committed to the public repository | Low | **High** — irreversible exposure | `.gitignore` blocks vault and key extensions; synthetic data only; no secret ever requested in chat | Agent |
| R-007 | Flutter Windows desktop limitations block a required control | Low | Medium | Windows targeted first so problems surface early; limitations documented rather than worked around insecurely | Agent |
| R-008 | Cloud-drive sync corrupts a vault through a race between two devices | Medium | High | **Reduced 10 Nov 2026**: import merges per entry and never replaces wholesale (D-011); convergence and idempotence asserted on 100 random vault pairs each; a file that will not decrypt is rejected before anything local is touched. Remaining exposure is the automatic shared-folder watch, which is not built | Agent |
| R-009 | Scope grows beyond what one project can deliver | Medium | Medium | Three-phase roadmap treated as authoritative; Phase 1 acceptance criteria fixed in the checklist | Shared |
| R-010 | Debug-signed APK is mistaken for production-ready | Low | Low | Stated in the known-limitations document and in the release notes | Agent |

### Risks accepted without further mitigation

- **A compromised device defeats the design.** If malware has the device while the vault
  is unlocked, it can read the decrypted contents from memory. No password manager solves
  this, and Family Vault does not claim to.
- **File size leaks a rough item count.** Mitigating this would require padding the
  payload to fixed blocks. Judged not worth the complexity for a family tool; recorded
  rather than hidden.

---

## Part 3 — Open questions requiring owner input

Only items that genuinely need a decision from the owner appear here. Everything else has
been decided above.

| # | Question | Needed by | Default if no answer |
|---|---|---|---|
| 1 | Authorise the Claude GitHub App for `Samby28/family-vault` so builds can run | Immediately | None. This is a hard blocker. |
| 2 | Enable GitHub Pages for the repository so the web demo gets a public URL | Before faculty review | Web demo artifact downloadable from CI instead of a live link |
| 3 | Which cloud drive the family actually uses (Google Drive, OneDrive, something else) | Start of Phase 2 | Local file plus manual copy; sync layer built provider-independent regardless |
