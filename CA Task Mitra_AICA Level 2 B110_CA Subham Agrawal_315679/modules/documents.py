from core.framework import Router
MANIFEST = dict(key="documents", name="Document Management", core=False, status="planned", requires=["work"],
    desc="Client-wise digital filing, versions and OCR. (Plugs in here later.)",
    subs=[("filing", "Client / year-wise folders", "planned"), ("versions", "Version history", "planned"),
          ("ocr", "OCR & classification", "planned"), ("expiry", "Expiry alerts", "planned")])
R = Router()
SCHEMA = ""
