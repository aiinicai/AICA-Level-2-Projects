from core.framework import Router
MANIFEST = dict(key="portal", name="Client Portal", core=False, status="planned", requires=["work"],
    desc="Client login, document upload, work tracking and online fee payment. (Plugs in here later.)",
    subs=[("client_login", "Client login", "planned"), ("doc_upload", "Document submission", "planned"),
          ("status_tracking", "Work status tracking", "planned"), ("online_payment", "Online fee payment", "planned")])
R = Router()
SCHEMA = ""
