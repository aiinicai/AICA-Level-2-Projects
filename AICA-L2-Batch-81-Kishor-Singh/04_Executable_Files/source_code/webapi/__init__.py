"""CA DocuFlow AI -- Team Deployment web/API layer.

This is the "Team deployment" mode described in the project README: an
authenticated, multi-user service with real separation of duties
(maker-checker), a relational database, and a REST API a browser or the
desktop app can talk to. It is architecturally and physically separate
from the single-user desktop application (``core/``, ``ui/``) -- the two
share no in-process state, and this package can be deployed independently.

Local development and the automated test suite use SQLite (see
``webapi/database.py``); production deployment should point
``DATABASE_URL`` at PostgreSQL (see README "Team Deployment").

Nothing in this package is wired into the desktop app's default run path
(``app.py``) -- it is started separately via ``uvicorn webapi.app:app``.
"""
