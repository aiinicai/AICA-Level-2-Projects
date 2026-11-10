# Isolated demonstration configuration

`portal.settings` and the compatibility name `portal.settings_web` now both use the sanitized local settings. The original settings and backups were not copied. `DJANGO_SETTINGS_MODULE` is explicitly set in the provided batch scripts.

- Data is fixed to this copy's `local_demo/`; the original VIP_DATA_DIR environment override is deliberately ignored. Database: local_demo/demo.sqlite3. Documents: local_demo/documents. Test emails: local_demo/test_emails. Synthetic PDFs: local_demo/demo_documents. Collected static files: local_demo/staticfiles.
- A random secret is generated once in local_demo/.secret_key on first run. The optional DJANGO_SECRET_KEY environment override must contain at least 50 characters and must stay local. No secret is shipped. .env.example documents this optional variable; there is no dotenv loader.
- DEBUG=False, localhost-only ALLOWED_HOSTS, no trusted proxies, no tunnel settings, and no real email service or API credentials. Secure-only cookie flags are false for HTTP localhost; these settings must not be used for a public service.
- Waitress binds explicitly to 127.0.0.1:8002. Do not change to 0.0.0.0 for this demo. WhiteNoise serves collected static assets; uploaded documents are served by authorized Django views, not static storage.
- Axes is configured for five failed attempts and a one-hour cooldown with username and IP lockout parameters. Tests cover successful login, not full rate-limit behavior. Registration uses the explicit Django authentication backend to avoid the historical multiple-backend error.
- No dependency installation, settings command or test needs access to the original private_data folder.

Run only from a new extracted folder. Never point this copy at the original database or copy the original .env/secret files into it. Generated local_demo files stay local even when fictional.
