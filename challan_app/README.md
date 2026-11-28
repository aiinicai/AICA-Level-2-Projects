# Manual Challan Register

Standalone multi-user web app for manual delivery challans (returnable MRC / non-returnable MNRC) under Indian GST.

* Quick start (developer): `pip install -r requirements.txt`, then `set FLASK_APP=app:create_app`, `flask init-db`, `python run_server.py`
* Demo data: `flask seed-demo` (users requester1 / approver1, password `Demo@1234`)
* Tests: `python -m pytest tests`
* Docs: `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, `docs/DEPLOYMENT.md` (for IT), `docs/USER_GUIDE.md`
* Samples: `samples/` (Excel templates + importable sample vendors and historical challans; regenerate with `python make_samples.py`)
