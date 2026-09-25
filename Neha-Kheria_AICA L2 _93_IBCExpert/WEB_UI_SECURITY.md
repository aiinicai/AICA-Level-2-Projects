# Local Web/UI Security Contract

- IBC Expert local web traffic binds only to `127.0.0.1`; source launcher uses port 8765.
- Host validation accepts only `127.0.0.1`, `localhost`, and the in-process test host.
- Authentication uses an opaque, high-entropy `ibc_session` cookie. The master key never enters HTML, JavaScript, cookies, or persistent session storage.
- The session cookie is `HttpOnly` and `SameSite=Strict`.
- Every state-changing HTML form and JSON API request requires a CSRF token. JSON clients submit it using `X-CSRF-Token`.
- A separate random `ibc_csrf` SameSite cookie supports double-submit validation.
- Content Security Policy permits only locally bundled scripts/styles and blocks framing, plugins/objects, remote connections, and remote form targets.
- OpenAPI/Swagger/ReDoc endpoints are disabled in the desktop application.
- Responses use `no-store`, `X-Frame-Options: DENY`, `nosniff`, a no-referrer policy, and restrictive browser permissions.
- The UI includes no CDN, remote font, analytics, telemetry, or cloud dependency.
