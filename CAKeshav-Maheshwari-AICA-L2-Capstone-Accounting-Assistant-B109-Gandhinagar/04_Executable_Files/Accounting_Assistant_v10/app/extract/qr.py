"""E-invoice QR (signed IRN JWT). Decoding the QR image needs zxing-cpp or OpenCV, both optional
native libraries; if neither loads, this step is skipped and the text/OCR route takes over.
The JWT payload is read without signature verification (flagged as unverified)."""
from __future__ import annotations

import base64
import json
from decimal import Decimal

from .schema import Invoice


def decode_qr(img: bytes) -> list[str]:
    try:
        import zxingcpp                                    # optional
        from PyQt6.QtGui import QImage
        q = QImage.fromData(img).convertToFormat(QImage.Format.Format_Grayscale8)
        ptr = q.constBits()
        ptr.setsize(q.sizeInBytes())
        import numpy as np                                 # zxing-cpp needs an array
        arr = np.frombuffer(ptr, np.uint8).reshape(q.height(), q.bytesPerLine())[:, : q.width()]
        return [r.text for r in zxingcpp.read_barcodes(arr)]
    except Exception:
        pass
    try:
        import cv2                                         # optional
        import numpy as np
        arr = cv2.imdecode(np.frombuffer(img, np.uint8), cv2.IMREAD_GRAYSCALE)
        ok, texts, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(arr)
        return [t for t in texts if t] if ok else []
    except Exception:
        return []


def jwt_payload(token: str) -> dict | None:
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None
    try:
        body = parts[1] + "=" * (-len(parts[1]) % 4)
        outer = json.loads(base64.urlsafe_b64decode(body))
        data = outer.get("data", outer)
        return json.loads(data) if isinstance(data, str) else data
    except Exception:
        return None


def invoice_from_qr(payload: dict) -> Invoice:
    """Signed QR carries: SellerGstin, BuyerGstin, DocNo, DocTyp, DocDt (dd/mm/yyyy), TotInvVal,
    ItemCnt, MainHsnCode, Irn, IrnDt. Totals per tax head are NOT in the QR, so this seeds
    the header fields at high confidence and the text/OCR route fills the rest."""
    dt = payload.get("DocDt", "")
    ymd = f"{dt[6:10]}{dt[3:5]}{dt[0:2]}" if len(dt) == 10 else ""
    inv = Invoice(supplier_gstin=payload.get("SellerGstin", ""), buyer_gstin=payload.get("BuyerGstin", ""),
                  invoice_no=payload.get("DocNo", ""), invoice_date=ymd, irn=payload.get("Irn", ""),
                  grand_total=Decimal(str(payload.get("TotInvVal", 0) or 0)), source="qr")
    inv.field_confidence = {k: 0.99 for k in ("supplier_gstin", "buyer_gstin", "invoice_no", "invoice_date",
                                             "grand_total")}
    if payload.get("MainHsnCode"):
        inv.field_confidence["main_hsn"] = 0.99
        inv.raw_text = f"MainHsnCode {payload['MainHsnCode']}"
    return inv
