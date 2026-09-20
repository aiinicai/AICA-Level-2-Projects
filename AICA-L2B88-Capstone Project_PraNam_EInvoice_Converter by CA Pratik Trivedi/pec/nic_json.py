"""GST e-Invoice JSON (Schema Version 1.1) writer.

Important: optional fields with no value are omitted, never emitted as JSON null.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from .util import to_decimal


def _num(v, default=None):
    d = to_decimal(v) if v not in (None, "") else None
    if d is None:
        return default
    return int(d) if d == d.to_integral_value() else float(d)


def _s(v):
    v = "" if v is None else str(v).strip()
    return v if v else None


def _compact(obj):
    """Recursively remove absent optional values and empty optional objects."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            v = _compact(v)
            if v is None:
                continue
            if isinstance(v, dict) and not v:
                continue
            if isinstance(v, list) and not v:
                continue
            out[k] = v
        return out
    if isinstance(obj, list):
        return [_compact(x) for x in obj]
    return obj


def build_json(res, supplier, masters) -> list[dict]:
    H = res.header
    opt = res.options
    yn = lambda v: {"YES": "Y", "NO": "N", "Y": "Y", "N": "N"}.get(str(v or "").strip().upper())
    state = lambda name: masters.states.get(str(name or "").strip().upper()) if name else None
    unit = lambda desc: masters.unit_code(desc) or None

    domestic_recipient = opt.supply_type in {"B2B", "SEZWP", "SEZWOP", "DEXP"}
    export_supply = opt.supply_type in {"EXPWP", "EXPWOP"}
    buyer_state = state(H.get("colBState")) or ("96" if export_supply else None)

    ship = None
    if any(H.get(k) for k in ("colSgstin", "colSLegalname", "colSaddr1", "colSLoc", "colSPin", "colSState")):
        ship_state = state(H.get("colSState")) or ("96" if H.get("colSState") == "OTHER COUNTRIES" else None)
        ship = {
            "Gstin": _s(H.get("colSgstin")),
            "LglNm": _s(H.get("colSLegalname")),
            "TrdNm": _s(H.get("colSTradname")),
            "Addr1": _s(H.get("colSaddr1")),
            "Addr2": _s(H.get("colSaddr2")),
            "Loc": _s(H.get("colSLoc")),
            "Pin": _num(H.get("colSPin")),
            "Stcd": ship_state,
        }

    tran = {
        "TaxSch": "GST",
        "SupTyp": H.get("colSupType"),
        "IgstOnIntra": yn(H.get("colIgstIntra")),
        "RegRev": yn(H.get("colRevCharge")),
        "EcmGstin": _s(H.get("colEcomGstin")),
    }
    doc = {
        "Typ": masters.doc_type_codes.get(H.get("colDoctype")),
        "No": _s(H.get("colDocno")),
        "Dt": _s((H.get("colDocdate") or "").replace("-", "/")),
    }
    seller = {
        "Gstin": _s(supplier.gstin),
        "LglNm": _s(supplier.legal_name),
        "TrdNm": _s(supplier.trade_name),
        "Addr1": _s(supplier.address1),
        "Addr2": _s(supplier.address2),
        "Loc": _s(supplier.location),
        "Pin": _num(supplier.pin),
        "Stcd": state(supplier.state) or _s(supplier.state_code),
        "Ph": _s(supplier.phone),
        "Em": _s(supplier.email),
    }
    buyer = {
        "Gstin": _s(H.get("colBgstin")),
        "LglNm": _s(H.get("colBLegalname")),
        "TrdNm": _s(H.get("colBTradname")),
        "Pos": buyer_state,
        "Addr1": _s(H.get("colBaddr1")),
        "Addr2": _s(H.get("colBaddr2")),
        "Loc": _s(H.get("colBLoc")),
        "Pin": _num(H.get("colBPin")),
        "Stcd": buyer_state,
        "Ph": _s(H.get("colBPhno")),
        "Em": _s(H.get("colBEmail")),
    }
    vals = {
        "AssVal": _num(H.get("colTotTaxval"), 0),
        "IgstVal": _num(H.get("colTigstval"), 0),
        "CgstVal": _num(H.get("colTcgstval"), 0),
        "SgstVal": _num(H.get("colTsgstval"), 0),
        "CesVal": _num(H.get("colTcessval"), 0),
        "StCesVal": _num(H.get("colTstcessval"), 0),
        "Discount": _num(H.get("colTDiscount"), 0),
        "OthChrg": _num(H.get("colTOthChrgs"), 0),
        "RndOffAmt": _num(H.get("colRoundOff"), 0),
        "TotInvVal": _num(H.get("colTinvoiceval"), 0),
    }

    root = {
        "Version": "1.1",
        "TranDtls": tran,
        "DocDtls": doc,
        "SellerDtls": seller,
        "BuyerDtls": buyer,
        "ValDtls": vals,
        "ItemList": [],
    }

    # Export-only block. Do not send an empty ExpDtls object on domestic invoices.
    if export_supply:
        root["ExpDtls"] = {
            "ShipBNo": _s(H.get("colShipBilNo")),
            "ShipBDt": _s((H.get("colShipBilDt") or "").replace("-", "/")),
            "Port": _s(H.get("colPort")),
            "RefClm": yn(H.get("colSupRefund")),
            "ForCur": _s(H.get("colForCur")),
            "CntCode": _s(H.get("colCntryCode")),
            "ExpDuty": _num(H.get("colExpDty")),
        }

    for r in res.items:
        is_service = str(r.get("colProdservice") or "").strip().upper() in {"YES", "Y"}
        item = {
            "SlNo": _s(r.get("colProdSlno")),
            "PrdDesc": _s(r.get("colProddesc")),
            "IsServc": yn(r.get("colProdservice")),
            "HsnCd": _s(r.get("colHsn")),
            # Quantity/UQC are not mandatory for service supplies.
            "Qty": None if is_service else _num(r.get("colQuantity")),
            "FreeQty": None if is_service else _num(r.get("colFreeQuanty")),
            "Unit": None if is_service else unit(r.get("colUnit")),
            "UnitPrice": _num(r.get("colUnitPrice"), 0),
            "TotAmt": _num(r.get("colTotal"), 0),
            "Discount": _num(r.get("colDiscount")),
            "PreTaxVal": _num(r.get("colPreTaxVal")),
            "AssAmt": _num(r.get("colAssValue"), 0),
            "GstRt": _num(r.get("colGstrate"), 0),
            "IgstAmt": _num(r.get("colIgst")),
            "CgstAmt": _num(r.get("colCgst")),
            "SgstAmt": _num(r.get("colSgst")),
            "CesRt": _num(r.get("colCessrate")),
            "CesAmt": _num(r.get("colCessadval")),
            "CesNonAdvlAmt": _num(r.get("colCessnonad")),
            "StateCesRt": _num(r.get("colStCessrate")),
            "StateCesAmt": _num(r.get("colStCessadval")),
            "StateCesNonAdvlAmt": _num(r.get("colStCessnonad")),
            "OthChrg": _num(r.get("colOthChrgs")),
            "TotItemVal": _num(r.get("colTolitemval"), 0),
        }
        root["ItemList"].append(item)

    return [_compact(root)]


def write_json(path: Path, data) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
