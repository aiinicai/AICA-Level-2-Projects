# AuditVault GitHub Release Checklist

1. Change all default passwords before any real deployment.
2. Never commit `.env`, `.streamlit/secrets.toml`, `auditvault.db`, or `AuditVault_Data/`.
3. Run `git status` and inspect every staged file before committing.
4. Confirm sample files contain fictional data only.
5. Keep the repository private if the source must remain confidential.
6. For a public academic demonstration, retain the included all-rights-reserved license and do not include client information.
7. Test a clean installation in a separate folder:
   - Create a virtual environment.
   - Install `requirements.txt`.
   - Run `streamlit run app.py`.
   - Confirm that the database initializes automatically.
8. For production, replace SQLite with PostgreSQL, serve behind HTTPS, configure centralized identity, move evidence to encrypted object storage, and arrange security testing and backups.

## Important technical reality

Python source uploaded to a public repository cannot be encrypted while remaining directly runnable from that repository. Obfuscation can slow casual inspection but does not prevent extraction. Device binding stored only on a user's computer can also be reset by a technically capable user. Strong enforcement requires a server-controlled license service or a hosted application whose source is never distributed.
