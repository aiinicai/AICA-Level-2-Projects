# FOLDER LOCK — Two-Factor Folder Encryption

**AICA Level 2 Capstone Project**

| | |
|---|---|
| **Candidate** | Sanjeev Kar |
| **Batch** | 80 |
| **Project** | FOLDER LOCK — Two-Factor Folder Encryption |
| **Flow** | Face Recognition → Password → Unlock |
| **Platform** | Windows 10 / 11 (64-bit, NTFS) |
| **Language** | Python 3.12+ |
| **Interface** | tkinter |

---

## 1. Overview

FOLDER LOCK converts an ordinary folder on a professional's computer into an encrypted vault.
Access requires successful authentication using **two independently validated factors**, in a
fixed order that the interface enforces structurally:

```
   Factor 1                  Factor 2
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│    Face      │  ───►  │   Password   │  ───►  │    UNLOCK    │
│ Recognition  │        │ Verification │        │  (decrypt)   │
└──────────────┘        └──────────────┘        └──────────────┘
  (something              (something               AES-256-GCM
   you are)                you know)               streaming
```

Failure at either stage aborts the process and the folder remains encrypted. Neither factor alone
is sufficient. Credentials are held **per folder**, so folder A's password is rejected by folder B.

### Why this matters for a Chartered Accountant

A practising CA's laptop typically carries, in plain unencrypted form, client-wise income tax
folders (PAN, Aadhaar, Form 16, Form 26AS, capital gains and bank statements), GST working
folders, audit folders with trial balances and working papers, bank and stock audit folders with
borrower data, and payroll/TDS folders with employee salary and bank details.

These are ordinarily protected by nothing more than the Windows login password. Anyone who obtains
the machine, boots it from external media, removes the hard disk, or simply sits at an unlocked
desk during lunch hour has complete access to every client file.

| Existing option | What it does | Where it fails |
|---|---|---|
| Windows login password | Prevents interactive login | Files stay unencrypted on disk; a live USB or removed disk exposes everything |
| ZIP / RAR password | Encrypts an archive | Single factor; no audit trail; the archive must be re-zipped after every edit |
| Office file passwords | Protects one Excel or Word file | One file at a time; routinely shared over WhatsApp; ignores PDFs, scans and Tally exports |
| BitLocker / full-disk | Encrypts the drive at rest | Once Windows boots, every folder is readable; no separation between clients; unavailable on Windows Home |

FOLDER LOCK encrypts the file contents themselves, folder by folder, behind two factors, and
produces a tamper-evident audit trail suitable for internal quality review.

---

## 2. Features

- **Two-factor authentication** — face recognition, then password; the order is enforced by the UI
- **Per-folder credentials** — each folder has its own password and enrolled face; credentials do
  not travel with a folder between machines
- **AES-256-GCM streaming encryption** — chunked container format with per-chunk authentication,
  so tampering is detected and no partial plaintext is ever written
- **Argon2id key derivation** — the encryption key is derived from the password; the password
  itself is never stored
- **HKDF-SHA256 key separation** — an independent key per file, so no key/nonce pair is reused
- **NTFS access restriction** — a locked folder refuses to open in Windows Explorer
- **Liveness check** — a coarse blink test to deter a single static photograph
- **Face re-enrolment and password change** — both behind full two-factor authentication
- **Automatic dependency installation** — dependencies are detected and installed on first run,
  with the installation log shown in a window rather than hidden
- **Professional tkinter interface** — ttk widgets, resizable window, live camera preview,
  progress feedback; long operations run off the UI thread so the interface never freezes
- **Audit logging** — event types and timestamps only; never passwords, face images or key material
- **Safe swap on write** — originals are deleted only after the verified replacement succeeds

---

## 3. Requirements

| Item | Requirement |
|---|---|
| Operating system | Windows 10 or 11, 64-bit |
| Filesystem | NTFS (access restriction is unavailable on FAT32/exFAT; encryption still applies) |
| Python | 3.12 or later, with "Add Python to PATH" ticked |
| Hardware | A working webcam |
| Internet | Required only on the first run, to download dependencies |

### External libraries

Every dependency below is detected and installed automatically on first execution. **No manual
`pip install` is required.**

| Library | Purpose | Why the standard library is not sufficient |
|---|---|---|
| `cryptography` | AES-256-GCM, HKDF-SHA256, CSPRNG, key wrapping | `hashlib` hashes but does not encrypt; hand-rolling a cipher would be unsafe |
| `argon2-cffi` | Argon2id password-based key derivation | The memory-hard KDF recommended for password hashing has no stdlib equivalent |
| `opencv-contrib-python` | Camera capture, Haar cascade face detection, LBPH recognition | Python has no built-in camera or image-processing capability; LBPH lives in the `contrib` build |

> **Important:** it must be `opencv-contrib-python`, not plain `opencv-python` — the base package
> does not include `cv2.face`. The two conflict, so uninstall the base package first if present:
> `pip uninstall opencv-python -y`

| `numpy` | Image array handling | Required by OpenCV |
| `Pillow` | Bridges OpenCV frames to tkinter images for the live preview | tkinter cannot display OpenCV frames directly |

Everything else — `tkinter`, `pathlib`, `logging`, `configparser`, `threading`, `subprocess`,
`importlib`, `secrets`, `hashlib` and `json` — is from the Python standard library.

`pyinstaller` is required only to build the executable, not to run from source.

---

## 4. Installation

1. Install **Python 3.12 or later** from [python.org](https://www.python.org/downloads/), ticking
   **"Add Python to PATH"**.
2. Download or clone this project folder.
3. Open Command Prompt in the folder and run:

   ```
   python main.py
   ```

On the first run, `bootstrap.py` checks for each required package and installs any that are
missing, with the installation log displayed in a window. If a C-extension package such as OpenCV
was freshly installed, the application restarts itself cleanly so the new interpreter can see it.
Subsequent runs start immediately.

The bootstrap module has **no third-party imports of its own** (standard library only), so it can
run before any dependency exists, and it is skipped entirely when running from the frozen
executable.

```python
import sys
import subprocess
import importlib


def install(package: str) -> None:
    """Install a package using the interpreter running this script."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def ensure_package(import_name: str, pip_name: str | None = None) -> None:
    """Import a package, installing it first if it is not present."""
    try:
        importlib.import_module(import_name)
    except ImportError:
        install(pip_name or import_name)
```

### Building the executable (optional)

```
pip install -r requirements.txt
pip install pyinstaller
python build_exe.py
```

Output: `dist/FolderLock/FolderLock.exe`. The `.exe` depends on the `_internal` folder beside it
and will not start alone. The build is not code-signed, so SmartScreen shows a warning
(**More info → Run anyway**), and some antivirus products flag it because "encrypts folders and
uses the webcam" matches ransomware heuristics.

---

## 5. Usage

### First-time setup for a folder

1. Run `python main.py`.
2. Select the folder to protect.
3. Enrol your face at the camera prompt.
4. Set the password for that folder. Policy requires upper case, lower case, digits and symbols.

### Locking

Select the folder → **Lock**. Every file is encrypted in place using the streaming AES-256-GCM
container, a manifest is written, and NTFS access restriction is applied.

### Unlocking

Select the folder → **Unlock** → **Factor 1**: the camera verifies your face against *that
folder's* enrolled template → **Factor 2**: enter *that folder's* password. On success the folder
is decrypted and access restored. On failure the attempt is logged and the folder stays encrypted.

### Recovery

If the application is lost or uninstalled while a folder is locked, access restriction can be
removed with:

```
icacls "C:\path\to\folder" /remove:d "%USERNAME%"
```

This restores *access* only — the contents remain encrypted and still require the password.

> **There is no password recovery.** A forgotten password means that folder's data is
> unrecoverable, by design. Back up anything irreplaceable before locking it for the first time.

---

## 6. Folder structure

```
AICA-L2-Batch-(080)-Sanjeev-Kar/
│
├── main.py                 Entry point: dependency bootstrap, audit logging, GUI launch
├── bootstrap.py            First-run dependency installer with a visible log; inert when frozen
├── config.py               Paths, defaults, settings persistence, per-folder profile helpers
├── security.py             Argon2id, HKDF, AES-GCM, CSPRNG, key wrapping, memory zeroing
├── password_auth.py        Password policy and the per-folder vault wrapping each master key
├── face_auth.py            Camera lifecycle, Haar detection, LBPH enrol/verify, liveness
├── access_control.py       Windows NTFS deny/restore so a locked folder refuses to open
├── encryption.py           Streaming chunked AES-256-GCM container with per-chunk authentication
├── folder_manager.py       Recursive lock/unlock, manifest, registry, credential profiles
├── ui.py                   All screens; enforces the face-then-password order structurally
├── build_exe.py            PyInstaller build script
│
├── requirements.txt
├── README.md               This file
│
├── _selftest.py            Password policy and Argon2id key derivation
├── _selftest_multi.py      Per-folder credential independence
├── _selftest_face.py       Haar cascade loading, LBPH train → encrypt → verify
├── _selftest_access.py     A locked folder genuinely refuses to open
├── _selftest_ui.py         Every dialog constructs against a real Tk root
│
├── resources/
│   ├── haarcascade_frontalface_default.xml
│   └── haarcascade_eye.xml
│
└── docs/
    ├── FolderLock-Documentation-v2.pdf   Requirements, architecture, development log, source
    └── Steps.pdf                          Problem statement and design rationale
```

---

## 7. Testing

Run the self-test suite from the project folder:

```
python _selftest.py
python _selftest_multi.py
python _selftest_face.py
python _selftest_access.py
python _selftest_ui.py
```

| Test | Expected result |
|---|---|
| Password without upper case / digits / symbols | Rejected by policy |
| Folder A's password used on folder B | Rejected — credentials are per folder |
| Bit-flipped encrypted file | `TamperDetectedError`; no partial plaintext written |
| Missing webcam | `CameraError` with an actionable message |
| Interrupted encryption | Originals deleted only after the verified swap succeeds |
| Locked folder opened in Explorer | Access refused; lock state detectable |
| Every dialog against a real Tk root | Constructs without error; preview holds its pixel size |

End-to-end operation was additionally verified on real hardware with a real camera, including the
rejection path, and a complete lock/unlock cycle on a real folder with the contents restored
intact.

---

## 8. Security limitations

Stated honestly, because a security tool that overstates itself is worse than none.

- **Face recognition is a gate, not a secret.** Templates are protected at rest by a locally stored
  device key, not by the password, because verification must occur before the password is entered.
- **Liveness detection is a coarse blink check.** It deters a single static photograph. It does not
  reliably stop a video replay, a printed cut-out or a mask. This is not certified anti-spoofing,
  which requires depth or infrared hardware.
- **LBPH is less accurate than a modern deep embedding model**, particularly in poor lighting or at
  extreme pose. The match threshold is adjustable in Security Settings.
- **Access restriction is a deterrent.** The folder's owner can always restore access through the
  Windows Security tab, and an administrator can override it. No user-space application can do
  better without a kernel-mode filesystem driver.
- **Encryption is the real protection.** Every file is AES-256-GCM ciphertext; even with access
  fully restored, the contents are unreadable without the password.
- **Filenames remain visible** even though contents are encrypted.
- **Python cannot guarantee secrets are erased from memory.** Garbage collection, paging and core
  dumps all evade best-effort zeroing.
- **Non-NTFS volumes** cannot carry the access restriction; encryption still applies and the
  application warns clearly.

This is not "unhackable" or "military-grade". It composes standard, well-reviewed primitives
correctly, with tamper detection and safe-ordering file operations. That is a strong baseline, not
a guarantee against every adversary.

---

## 9. Possible future enhancements

- Depth or infrared liveness detection to replace the blink check
- A modern deep face embedding model in place of LBPH, with LBPH retained as a CPU-only fallback
- Audit trail export to Excel via `openpyxl`, for internal-audit and IS-audit evidence
- Optional OTP as a third factor for highly sensitive vaults
- Multi-user enrolment with role-based access for a firm with several partners
- Scheduled automatic re-locking after a defined period of inactivity
- Code signing to remove the SmartScreen warning

---

## 10. Disclaimer

Developed as an academic capstone project for the ICAI AICA Level 2 programme. It demonstrates the
two-factor authentication and encryption concepts covered in the course. It has not undergone
independent security certification and should be evaluated accordingly before any use involving
live client data.
