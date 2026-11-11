# Validation record - 10 November 2026

The existing application's virtual-environment launcher could not execute in this session. No changes were made to repair it or the working portal. Testing instead used bundled CPython 3.12.14 with a separate local-only library directory, reusing the installed pure-Python packages and PyMuPDF abi3 distribution. Pillow was the runtime's 13.0.0; the existing project's 12.3.0 wheel targets Python 3.13 and could not be loaded by 3.12.

Pinned requirements record the versions observed in the existing environment, including Python-3.13-era Pillow 12.3.0. A fresh pip install of that exact environment has NOT been run. Package availability, vulnerability status and course requirements were not checked online. The setup batch scripts target Python 3.13 and still need a first run in that exact environment.

Completed checks:
- Django system check: no issues (0 silenced).
- Generated the missing billing initial schema migration from the copied models; this contains schema only, no data.
- Seven synthetic-data regression tests: all passed (23.055 seconds on the first run). Tests use an isolated test database and temporary document storage.
- Fresh database migration, demo seeding, static collection and synthetic PDF generation: see the final preparation status file for completion evidence.

The seven tests cover registration/login and pending status; staff approval and POST behavior; invoice extraction/review/export/locking; wrong-recipient/duplicate rejection; cross-vendor invoice/document isolation; malformed input and anonymous access; and CSRF plus Finance/admin page rendering.

Not established: exact Python 3.13 dependency installation, batch-script execution through Windows Explorer, human browser walkthrough, Tesseract image/scanned-PDF OCR, public deployment, production security or concurrency guarantees. A loopback Waitress HTTP/static smoke check is recorded separately when completed. No real data was used.
