# Family Vault

A secure, offline-first, zero-knowledge password manager for **Android** and
**Windows**, built with a single Flutter codebase.

Your passwords are encrypted on your own device with a key derived from your
master password. There is no server, no account to create, and nothing that any
third party — including the people who built this — can decrypt.

> **Project status: Phase 1 working — v0.5.0.** The encrypted vault is built and
> usable on Android and Windows. **371 tests pass**, including security tests
> against real libsodium. You can create a vault, save logins, notes, cards and
> identities, organise them in folders, search, generate passwords, hold
> two-factor codes, check password health, take an encrypted backup, and keep
> two devices in step through any folder they both see — merged entry by entry,
> with convergence and idempotence asserted on random vault pairs.
>
> **No cloud account of any kind.** Sync is a folder: point both devices at your
> own Drive, OneDrive or Dropbox folder, a network share or a USB stick. This
> code has no integration with any provider and cannot tell which one is in use.
>
> **Not yet built:** sync runs when you press the button — nothing watches the
> folder and nothing runs on a schedule. Also Android autofill, importing from
> another password manager, a recovery sheet, and fingerprint unlock. See
> [`docs/known-limitations.md`](docs/known-limitations.md).
>
> New here? [Installing](docs/installing.md) · [How to use it](docs/user-guide.md)

---

## What it does

| | |
|---|---|
| **Encrypts locally** | Argon2id turns your master password into a key; the vault is sealed with authenticated encryption. Titles, URLs, usernames, notes and folder names are all inside the encrypted payload. |
| **Stores four kinds of thing** | Logins, secure notes, payment cards and identities, organised into folders. |
| **Generates passwords** | Configurable passwords and passphrases from a cryptographically secure source. |
| **Checks your passwords** | Finds weak, reused and ageing passwords — entirely on your device, never by sending anything anywhere. |
| **Holds your 2FA codes** | A built-in RFC 6238 authenticator for your *other* accounts. |
| **Fills logins on Android** | Integrates with the Android Autofill Framework. |
| **Works offline** | The vault is a file on your device. A network is never required. |

Optional second-factor protection for opening the vault is **off by default**.
You turn it on only if you want it. See
[Optional extra protection](#optional-extra-protection) for why it works the way
it does.

## What it deliberately does not do

No server. No account. No telemetry. No password escrow. No administrative
override. No subscription. Each family member keeps their own vault file.

---

## Documentation

| Document | What it covers |
|---|---|
| [Installing](docs/installing.md) | Step-by-step for Android and Windows, written for non-programmers |
| [User guide](docs/user-guide.md) | How to use it, and its honest limits |
| [Requirements checklist](docs/requirements-checklist.md) | Every requirement, its source and its real status |
| [Architecture](docs/architecture.md) | Layers, unlock sequence, vault format, diagrams |
| [Decisions and risks](docs/decisions-and-risks.md) | Every significant decision, with reasoning, and the risk register |
| [Progress log](docs/progress-log.md) | Stage-by-stage record of what was built and tested |
| [Known limitations](docs/known-limitations.md) | What is missing, partial or imperfect, stated plainly |

---

## Security design in brief

Your master password is never stored, not even hashed. It is correct if, and only
if, it successfully decrypts the vault. That is the whole mechanism.

```
master password ──Argon2id(salt, cost)──▶ 256-bit key ──AEAD──▶ vault file
                                                │
                                         never written to disk
```

The file's header holds the format version, the Argon2id parameters, the salt,
the cipher identifier and the nonce. It has to be readable, because it is what
tells the app how to derive the key — but it is covered by the authentication
tag, so tampering with it (for instance, lowering the Argon2id cost to make
guessing cheaper) invalidates the file instead of weakening it.

Cryptographic primitives are never hand-written here. The project uses vetted
libraries only.

### Optional extra protection

With no server, a one-time code typed into the app cannot really protect a
vault: the check would be enforced by code an attacker controls, on a file they
already hold. Anyone who copied the file could bypass it, while the user felt
protected.

So Family Vault's optional second factor is **key material**, not a code — a key
file or a FIDO2 hardware key, mixed into key derivation. Without it, the key
cannot be derived at all. This is a Phase 2 feature.

The built-in authenticator for your other accounts is a separate thing entirely,
and is a Phase 1 feature.

### A limit worth stating

If a device is already compromised while the vault is unlocked, malware on it can
read the decrypted contents from memory. No password manager solves that, and
this one does not claim to.

**This project has not had an independent security audit.** No such claim is made
anywhere in it.

---

## Installing

Builds are published on the [Releases](../../releases) page once Stage 1 has run.

**Android.** Download `FamilyVault-Android.apk` and open it. Android will warn
that the developer is unknown, because the build is signed with a development key
rather than a store key; allow the install when prompted.

**Windows.** Download `FamilyVault-Windows.zip`, unzip it anywhere, and run
`family_vault.exe`. Keep the folder together — the program needs the files beside
it.

**Web demonstration.** A browser version for assessment is published from
[`web-demo.yml`](.github/workflows/web-demo.yml). It uses sample data only, says
so on screen, and cannot open a real vault.

---

## Building it yourself

Requires the [Flutter SDK](https://docs.flutter.dev/get-started/install) on the
stable channel, and JDK 17 for Android.

```bash
git clone https://github.com/Samby28/family-vault.git
cd family-vault

flutter pub get
flutter analyze
flutter test

flutter build apk --release        # Android
flutter build windows --release    # Windows
```

### How this project is built

The environment that authors this code has no Flutter or Android SDK and cannot
reach `pub.dev`, so **GitHub Actions is the compiler**. Every push is a real
first compilation, which shapes two things:

- The pipeline analyses and tests before it builds, so mistakes appear as
  readable analyser output rather than build crashes.
- Dependencies are added one per commit and confirmed green before the next.
  Stage 1 therefore has **no third-party runtime dependencies at all**.

Builds are pinned to Flutter **3.47.9**, the version Stage 1 is verified
against.

| Workflow | Does |
|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | Analyse, test, then build the APK and the Windows app |
| [`web-demo.yml`](.github/workflows/web-demo.yml) | Build and publish the demonstration |
| [`release.yml`](.github/workflows/release.yml) | On a `v*` tag, publish installable builds to Releases |

---

## Repository layout

```
lib/src/
  app/         app shell, theme, navigation plan
  core/        shared utilities and failure types
  crypto/      Argon2id, authenticated encryption, secure random
  vault/       file format, codec, repository, session
  domain/      models, password generator, health rules, TOTP
  features/    one folder per screen area
  platform/    Keystore, biometrics, autofill, clipboard guards
  io/          import, export, sync
test/          unit, security and widget tests
docs/          all project documentation
tool/          build and bootstrap scripts
```

---

## A note on this repository being public

It is public so that capstone assessors can read the code. It therefore contains
**no real credentials, vault files, keys or family data**, and never will.
Everything used for testing or demonstration is synthetic. `.gitignore` blocks
vault, keystore and key extensions as a first line of defence.

---

## Licence and status

Built as a capstone project by CA Gurpreet Singh Samby, for family use and
academic assessment. Not a commercial product.
