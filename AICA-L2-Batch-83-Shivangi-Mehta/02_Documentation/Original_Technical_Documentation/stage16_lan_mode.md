# Stage 16 — LAN / Same Network Access

Status: **Complete.** Architecture reconnaissance first, then only the additions the governing instruction asked for, then verification. No schema change was made or required. No Accounting/Audit/Tax/Unified Review/Query business logic, no Working Paper workflow, and no CSRF protection was weakened.

---

## 1. What LAN mode is

FinSight can now run on one computer (the **host**) and be opened, over the local network only, from other computers (**clients**) through a normal web browser — no Python, no install, no copy of the database, on the client side. The database and all client files stay on the host at all times. This is not internet access: FinSight still makes no outbound call to the public internet, in LAN mode or otherwise (Section 17; Stage 15's own offline findings are unchanged and still apply).

---

## 2. Host computer requirements

Python and FinSight's installed dependencies (as today), and a computer that stays on and connected to the local network for as long as other people need to reach it. The host serves the application; nothing else is required beyond what standalone/local mode already needs.

## 3. Client computer requirements

Only a modern web browser and network access to the host computer. No Python, no FinSight install, no local copy of any data.

---

## 4. How to start FINsight on the host

```
python wsgi_lan.py
```

This is the same `wsgi_lan.py` launcher referenced throughout the project's Blueprint (Section 26) — Stage 16 completes it rather than replacing it. It refuses to start if `SECRET_KEY` is still the development fallback (pre-existing guard, unchanged):

```
export FINSIGHT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
python wsgi_lan.py
```

On startup it prints:

```
FinSight LAN Server Started

Local:
  http://127.0.0.1:8877

LAN:
  http://<detected-LAN-IP>:8877

Open the LAN address from another computer connected to the same network.
LAN users must be on the same trusted network — this is not internet-facing.
```

The port (`8877`) is the existing `LAN_MODE_PORT` default from `config.py`, unchanged by Stage 16; override with `FINSIGHT_LAN_PORT=<port>` if needed.

## 5. How to find/access the LAN URL

The startup banner above prints it automatically, detected via a local-only OS route lookup (Section 15) — no external service is contacted to do this. If detection fails for any reason, the banner says so and startup is **not** blocked; check your OS's network settings for this computer's local IPv4 address (usually starting `192.168.` or `10.`) and combine it with the port shown.

## 6. How to connect from another computer

On a client computer, open a browser and go to the LAN address shown on the host (e.g. `http://192.168.1.23:8877`). Both computers must be on the same local network (same Wi-Fi/LAN).

## 7. First-run password setup

The first time LAN mode is started and no access password has been configured yet, every screen redirects to a setup page:

```
FINsight LAN Setup
Create an access password.
Password: [        ]
Confirm password: [        ]
[Set Password]
```

The password must be at least 8 characters and match its confirmation. Once set, the device that set it is immediately signed in; every other device that opens the LAN URL sees the normal login gate.

## 8. How to sign out

**Sign Out** appears in the top bar whenever LAN mode is active and the current browser is signed in. Signing out clears this browser's authenticated state; the next request to any protected page redirects back to the login gate.

## 9. How to change the password

**Settings → Security → Change LAN Access Password** (only shown when LAN mode is active). Requires the current password, a new password, and its confirmation. Changing the password **signs out every other already-connected device automatically** — the next request from any other browser is redirected to the login gate, not silently left signed in under the old password.

There is no password-reset flow (Section 29 explicitly rules this out — FinSight is offline-first, so there is no email to recover through). If the password is forgotten, it must be reset locally on the host computer: stop FinSight, open `database/finsight.db` with any SQLite tool, and delete the single row where `setting_key = 'lan_access_password_hash'` from the `application_settings` table. The next LAN startup will show the first-run setup screen again. (No convenience script for this was built in Stage 16 — it was judged unnecessary complexity for a rare, host-administrator-only action; document this procedure for yourself before you need it.)

## 10. Firewall guidance

If another computer cannot connect, the host computer's firewall may be blocking the configured port. Allow that port through the host's firewall for the **Private/Trusted** network profile only — never for Public networks. FinSight does not modify your firewall automatically (Section 16); this is a manual step you take on the host if needed.

## 11. Trusted-network warning

LAN access is intended for a **trusted private network only** (e.g. a home or office Wi-Fi you control), never a public or shared network, and never port-forwarded to the internet. FinSight V1 LAN mode does not provide HTTPS, enterprise identity management, individual user accounts, role-based permissions, or multi-tenant access control (Section 30). Anyone who has the shared access password and can reach the host on the network can use FinSight as if they were the host user.

## 12. Data location

Unchanged from every prior stage — all on the host computer:

```
FinSight/
    database/finsight.db
    data/input/, data/processed/, data/output/
    logs/
```

No client computer ever receives a copy of the database (Section 18) — there is no synchronization and no download route for it (verified, Section "Static File / Database Exposure" below).

## 13. Backup guidance

Unchanged from Stage 15: back up the `database/`, `data/`, and `logs/` directories together before moving FinSight to a new computer or upgrading. LAN mode does not add or change what needs backing up — the access password hash lives in the same `finsight.db` file as everything else.

## 14. Known limitations

- **No multi-user accounts.** One shared password protects the whole instance; there is no way to tell which person on the network performed a given action. This is the explicit V1 design (Section 4), not an oversight.
- **No database-at-rest encryption.** `finsight.db` remains plaintext on the host's disk, unchanged from Stage 15.
- **Plain HTTP, not HTTPS.** LAN traffic (including the login password submission) is not encrypted in transit. This is a real, disclosed limitation of a trusted-local-network tool with no certificate infrastructure — see Security Limitations in the completion report below.
- **Brute-force lockout state is in-memory only,** per source IP, and resets if the LAN server process restarts (Section 11). This is a conscious simplicity trade-off, not a persistence bug — see `app/security/lan_auth.py`.
- **No password-reset flow** (Section 29) — see Section 9 above for the manual local procedure.
- **SQLite concurrency was verified with stdlib `sqlite3` directly, not through FinSight's own SQLAlchemy stack**, because real SQLAlchemy is not installed in this sandbox (only its pytest-time verification shim is) — see the completion report's SQLite Concurrency Observations section for the full, honest explanation of what was and wasn't tested.
- **No live network/browser-rendered visual QA this stage** — the browser automation bridge used for Stage 14's Playwright pass was not connected in this session. Verification instead used the pytest suite plus a real, live end-to-end HTTP walkthrough (via `curl`, against an actually-running Flask process) of setup → dashboard → sign out → wrong password → correct password → Settings password change. This is disclosed here rather than described as equivalent to a rendered-screenshot pass.

## 15. Troubleshooting

- **"Could not automatically detect this computer's LAN IPv4 address"** on startup: use your OS's network settings to find your local IPv4 address (Windows: `ipconfig`; macOS/Linux: `ifconfig` or `ip addr`) and combine it with the printed port.
- **A client computer can't reach the LAN URL:** confirm both computers are on the same network, and check the host firewall (Section 10 above).
- **"Too many incorrect attempts"** on login: wait for the lockout window to pass (5 minutes by default, `FINSIGHT_LAN_LOCKOUT_SECONDS`), then try again with the correct password.
- **A previously-signed-in device suddenly asks to log in again:** expected if the password was changed in Settings on another device (Section 9), or if the host's LAN server process was restarted.
- **"FinSight LAN mode refused to start: SECRET_KEY is still the development fallback"**: set `FINSIGHT_SECRET_KEY` as shown in Section 4 before starting `wsgi_lan.py`.
