"""Tally master creation (ledgers).

Ledgers are created ONLY when the user explicitly reviews and confirms them on
the Create Ledgers screen — never automatically from an Excel upload.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from pydantic import BaseModel, field_validator, model_validator

from app.accounting.gst import gstin_error, normalise_state, state_from_gstin

GST_DUTY_HEADS = ("Central Tax", "State Tax", "Integrated Tax", "Cess")
GST_REGISTRATION_TYPES = ("Regular", "Composition", "Unregistered", "Consumer", "Unknown")


class NewLedger(BaseModel):
    name: str
    parent: str
    gst_registration_type: str | None = None
    gstin: str | None = None
    state: str | None = None
    gst_duty_head: str | None = None
    bill_wise: bool = False

    @field_validator("name", "parent")
    @classmethod
    def _required(cls, v: str) -> str:
        v = " ".join((v or "").split())
        if not v:
            raise ValueError("is required")
        if len(v) > 100:
            raise ValueError("is longer than 100 characters")
        return v

    @field_validator("gstin", "gst_registration_type", "state", "gst_duty_head", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return None if v is None or not str(v).strip() else str(v).strip()

    @model_validator(mode="after")
    def _gst(self) -> "NewLedger":
        if self.gstin:
            self.gstin = self.gstin.upper().replace(" ", "")
            problem = gstin_error(self.gstin)
            if problem:
                raise ValueError(problem)
            gst_state = state_from_gstin(self.gstin)
            if self.state and normalise_state(self.state) != gst_state:
                raise ValueError(f'State "{self.state}" does not match GSTIN state "{gst_state}"')
            self.state = gst_state
            self.gst_registration_type = self.gst_registration_type or "Regular"
        if self.state:
            canonical = normalise_state(self.state)
            if not canonical:
                raise ValueError(f'"{self.state}" is not a recognised state')
            self.state = canonical
        if self.gst_registration_type and self.gst_registration_type not in GST_REGISTRATION_TYPES:
            raise ValueError(f"GST registration type must be one of {', '.join(GST_REGISTRATION_TYPES)}")
        if self.gst_duty_head and self.gst_duty_head not in GST_DUTY_HEADS:
            raise ValueError(f"GST duty head must be one of {', '.join(GST_DUTY_HEADS)}")
        return self


def _sub(parent: ET.Element, tag: str, text: str) -> None:
    ET.SubElement(parent, tag).text = text


def ledger_element(ledger: NewLedger) -> ET.Element:
    el = ET.Element("LEDGER", {"NAME": ledger.name, "ACTION": "Create"})
    names = ET.SubElement(el, "NAME.LIST", {"TYPE": "String"})
    _sub(names, "NAME", ledger.name)
    _sub(el, "PARENT", ledger.parent)
    _sub(el, "ISBILLWISEON", "Yes" if ledger.bill_wise else "No")
    _sub(el, "AFFECTSSTOCK", "No")
    if ledger.gst_duty_head:
        _sub(el, "TAXTYPE", "GST")
        _sub(el, "GSTDUTYHEAD", ledger.gst_duty_head)
    if ledger.gst_registration_type:
        _sub(el, "GSTREGISTRATIONTYPE", ledger.gst_registration_type)
    if ledger.gstin:
        _sub(el, "PARTYGSTIN", ledger.gstin)
    if ledger.state:
        _sub(el, "LEDSTATENAME", ledger.state)
        _sub(el, "COUNTRYNAME", "India")
    return el


def ledger_import_envelope(ledgers: list[NewLedger], company: str = "") -> bytes:
    env = ET.Element("ENVELOPE")
    _sub(ET.SubElement(env, "HEADER"), "TALLYREQUEST", "Import Data")
    imp = ET.SubElement(ET.SubElement(env, "BODY"), "IMPORTDATA")
    desc = ET.SubElement(imp, "REQUESTDESC")
    _sub(desc, "REPORTNAME", "All Masters")
    if company:
        _sub(ET.SubElement(desc, "STATICVARIABLES"), "SVCURRENTCOMPANY", company)
    data = ET.SubElement(imp, "REQUESTDATA")
    for ledger in ledgers:
        msg = ET.SubElement(data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        msg.append(ledger_element(ledger))
    ET.indent(env, space=" ")
    return ET.tostring(env, encoding="utf-8")
