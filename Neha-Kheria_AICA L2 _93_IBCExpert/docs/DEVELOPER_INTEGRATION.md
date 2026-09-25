# IBC Expert — Developer and Integration Guide

## Architecture contract
IBC Expert uses service-layer business logic with a local FastAPI/Jinja2 UI/API displayed by PyWebView. The web service binds only to `127.0.0.1`. SQLite is the local system of record. UI/API handlers must orchestrate services rather than duplicate business rules.

## Local API v1
The stable integration prefix is `/api/v1`. It requires an authenticated local session. Mutating requests additionally require the current CSRF token in `X-CSRF-Token`. OpenAPI/Swagger endpoints are intentionally disabled in the customer runtime.

Primary contracts include:
- `GET /api/v1/status`
- `GET /api/v1/dashboard`
- `GET /api/v1/licence`
- `GET|POST /api/v1/clients`
- `GET|PUT /api/v1/clients/{id}`
- `POST /api/v1/clients/{id}/status/{action}`
- `GET /api/v1/documents`, detail/download, upload, ZIP import, OCR and metadata routes
- legal search/statute/provision/judgment read contracts
- workflow instance/stage read and deadline recalculation contracts
- recommendation generation
- forms/form-version read contracts
- backup list/create contracts
- review queue read/resolve/reject contracts
- plugin list contract

The API is localhost-only and is not an authorization bypass: normal trial/licence gating applies.

## Events/plugins
`EventBus` persists local event-outbox records and dispatches in-process subscribers. `PluginManager` requires declared permissions and keeps plugins disabled by default. `future.network_update` is reserved but rejected in this release.

## Future internet downloader/updater boundary
Do not add direct web requests to existing legal/import services. A future internet update subsystem must be separate, explicit, disabled by default, permission-controlled, source-authenticated, integrity-checked, staged to the review queue, auditable and capable of rollback. It must never silently overwrite verified legal content or transmit confidential client information.

## Database migrations
Schema changes must be introduced through the migration system with checksums and forward migration testing. Never patch a user's production SQLite schema manually.

## Release gates
Run `python -m pytest -q` with pinned dependencies, the customer-package verifier, Windows PyInstaller build, Inno Setup build, and the clean-Windows acceptance sequence before declaring a release complete.
