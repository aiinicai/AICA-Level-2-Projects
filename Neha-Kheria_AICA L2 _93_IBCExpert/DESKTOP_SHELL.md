# IBC Expert Desktop Shell

Build 04 introduces the production-oriented desktop execution path.

- `launch_desktop.py` starts the PyWebView shell.
- A TCP socket is bound to `127.0.0.1:0` first, obtaining an OS-assigned free port.
- That already-bound socket is handed to Uvicorn, avoiding a reserve-then-release port race.
- The desktop window is pointed only at the loopback URL.
- Closing the window requests Uvicorn shutdown, clears in-memory sessions during FastAPI shutdown, closes the database, and closes the listening socket.
- No external interface such as `0.0.0.0` is used.

## Trial and activation shell policy

The 30-day trial starts from the existing protected TrialService. The application displays trial status and exact expiry. After expiry or a clock anomaly, authenticated users are routed to the activation screen and normal UI/API operations are blocked. Existing local data is not deleted or damaged.

Offline activation uses the existing Ed25519 signed entitlement design. Customer builds contain only the owner public verification key (`licence_public_key.hex`). The owner private signing key must remain outside the customer package.

## TOTP

The Security screen can start, verify, enable and disable RFC 6238 TOTP. Setup secrets are held only in process memory until verification; enabled secrets are encrypted under the authenticated user's master key.
