# Changes limited to the submission copy

- Selected only required source/templates and the synthetic PDF generator. Excluded private_data, original settings, backup Python files, real documents, test document binaries, databases, logs, venv and generated static assets.
- Replaced personal email literals in selected files with finance@example.com.
- Wrote new isolated localhost settings, with a fresh local secret on first use, a fixed local_demo data directory and no old hosts, tunnel/proxy settings or real mail service.
- Added pinned requirements for Waitress, WhiteNoise and Axes (missing from the old requirements), along with recorded dependency versions.
- Generated an initial schema migration; the source folder had no billing migrations. Added seven synthetic-data regression tests.
- Rewrote setup/start/admin batch scripts for the isolated copy on loopback port 8002.
- Moved generated synthetic PDFs to excluded local_demo storage, updated email-location wording, and removed one unreachable duplicated ExtractError handler without changing the first handler.
- Added README, sample environment reference, demo/security/validation documentation and optional presentation materials.

The live folder was read only. No source, configuration, database, server, tunnel or environment in C:\VendorPortalWebTest was modified. No GitHub publishing, account action or PR creation was performed.
