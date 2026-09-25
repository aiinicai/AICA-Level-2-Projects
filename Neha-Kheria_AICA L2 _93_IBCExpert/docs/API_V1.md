# IBC Expert Local API v1 Contract

The API is intentionally local (`127.0.0.1`) and is designed for the desktop UI and future trusted local integrations. It is not exposed as a LAN/cloud API.

Authentication uses the same opaque local session as the UI. Write operations require `X-CSRF-Token`. All normal-use endpoints enforce current trial/licence status. JSON errors use `{ "error": "..." }`.

Internet/database updating is not an API capability in this version. `/api/v1/status` reports `offline_only: true` and `internet_updates_enabled: false` so integrations can fail closed rather than assume network functionality.
