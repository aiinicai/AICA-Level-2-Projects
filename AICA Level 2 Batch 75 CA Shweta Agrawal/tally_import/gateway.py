"""
Tally Prime XML/HTTP Gateway client.

Talks to Tally over the local HTTP XML interface (default port 9000).
Used for both reads (company name, ledger list, ledger vouchers for duplicate
checks) and writes (posting vouchers). Requires Gateway of Tally -> F12 ->
Advanced Configuration -> "Allow ODBC/HTTP" (or equivalent XML server) enabled.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from xml.sax.saxutils import escape

import requests
from lxml import etree

DEFAULT_URL = "http://localhost:9000"
TIMEOUT = 30


class TallyConnectionError(Exception):
    pass


class TallyGatewayError(Exception):
    pass


@dataclass
class TallyClient:
    url: str = DEFAULT_URL
    timeout: int = TIMEOUT

    # ---------- low level ----------

    def _post(self, xml_body: str) -> etree._Element:
        try:
            resp = requests.post(
                self.url,
                data=xml_body.encode("utf-8"),
                headers={"Content-Type": "text/xml"},
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectionError as e:
            raise TallyConnectionError(
                f"Could not reach Tally at {self.url}. Confirm Tally Prime is open, "
                f"a company is loaded, and Gateway of Tally -> F12 -> Advanced "
                f"Configuration has the HTTP/XML server enabled on this port."
            ) from e
        except requests.exceptions.Timeout as e:
            raise TallyConnectionError(f"Tally at {self.url} timed out.") from e

        if resp.status_code != 200:
            raise TallyGatewayError(f"Tally returned HTTP {resp.status_code}: {resp.text[:500]}")

        text = resp.text.strip()
        if not text:
            raise TallyGatewayError("Tally returned an empty response.")

        try:
            # Tally sometimes emits invalid control chars; strip them.
            cleaned = "".join(ch for ch in text if ch >= " " or ch in "\r\n\t")
            root = etree.fromstring(cleaned.encode("utf-8"), parser=etree.XMLParser(recover=True))
        except Exception as e:
            raise TallyGatewayError(f"Could not parse Tally XML response: {e}") from e

        if root is None:
            raise TallyGatewayError(f"Could not parse Tally XML response: {text[:500]}")

        return root

    # ---------- connectivity ----------

    def check_connection(self) -> tuple[bool, str]:
        """Returns (ok, message). Fetches the active company name as a probe."""
        try:
            name = self.active_company()
            if name:
                return True, f"Connected. Active company: {name}"
            return False, "Connected to Tally, but no company appears to be open."
        except (TallyConnectionError, TallyGatewayError) as e:
            return False, str(e)

    def active_company(self) -> str | None:
        """Tally has no direct 'current company name' report; instead we make a
        minimal masters export and read back the SVCURRENTCOMPANY it echoes."""
        xml = """
        <ENVELOPE>
          <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
          <BODY>
            <EXPORTDATA>
              <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                  <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                  <ACCOUNTTYPE>Currency</ACCOUNTTYPE>
                </STATICVARIABLES>
              </REQUESTDESC>
            </EXPORTDATA>
          </BODY>
        </ENVELOPE>
        """
        try:
            root = self._post(xml)
        except (TallyConnectionError, TallyGatewayError):
            return None
        name = root.findtext(".//SVCURRENTCOMPANY")
        return name.strip() if name else None

    # ---------- reads ----------

    def list_ledgers(self) -> list[dict]:
        """Returns [{'name':..., 'parent':..., 'gstin':...}, ...] for all ledgers."""
        xml = """
        <ENVELOPE>
          <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
          <BODY>
            <EXPORTDATA>
              <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                  <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                  <ACCOUNTTYPE>Ledger</ACCOUNTTYPE>
                </STATICVARIABLES>
              </REQUESTDESC>
            </EXPORTDATA>
          </BODY>
        </ENVELOPE>
        """
        root = self._post(xml)
        ledgers = []
        for led in root.findall(".//LEDGER"):
            name = led.get("NAME") or (led.findtext("NAME") or "")
            parent = led.findtext("PARENT") or ""
            gstin = led.findtext("PARTYGSTIN") or led.findtext("GSTIN") or ""
            if name:
                ledgers.append({"name": name.strip(), "parent": parent.strip(), "gstin": gstin.strip()})
        return ledgers

    def list_groups(self) -> list[dict]:
        """Returns [{'name':..., 'parent':..., 'reserved_name':...}, ...] for all account groups.
        Used to classify ledgers (Purchase Accounts / Direct Expenses / Indirect Expenses /
        Fixed Assets vs. everything else) by walking each ledger's PARENT up the group tree."""
        xml = """
        <ENVELOPE>
          <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
          <BODY>
            <EXPORTDATA>
              <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                  <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                  <ACCOUNTTYPE>Group</ACCOUNTTYPE>
                </STATICVARIABLES>
              </REQUESTDESC>
            </EXPORTDATA>
          </BODY>
        </ENVELOPE>
        """
        root = self._post(xml)
        groups = []
        for grp in root.findall(".//GROUP"):
            name = grp.get("NAME") or (grp.findtext("NAME") or "")
            reserved = grp.get("RESERVEDNAME") or ""
            parent = grp.findtext("PARENT") or ""
            if name:
                groups.append({"name": name.strip(), "parent": parent.strip(), "reserved_name": reserved.strip()})
        return groups

    def ledger_vouchers(self, ledger_name: str, from_date: dt.date, to_date: dt.date) -> list[dict]:
        """Voucher-level lines for a ledger, for duplicate detection (date+amount).

        The 'Ledger Vouchers' report (SVLEDGERNAME/SVFROMDATE/SVTODATE) reliably
        returns nothing on this Tally version even when the ledger has vouchers
        -- same class of bug as list_voucher_types(). Uses the TDL Collection
        export instead (confirmed reliable) and filters/extracts client-side."""
        xml = """
        <ENVELOPE>
          <HEADER>
            <VERSION>1</VERSION>
            <TALLYREQUEST>EXPORT</TALLYREQUEST>
            <TYPE>Collection</TYPE>
            <ID>VoucherCollection</ID>
          </HEADER>
          <BODY>
            <DESC>
              <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
              </STATICVARIABLES>
              <TDL>
                <TDLMESSAGE>
                  <COLLECTION NAME="VoucherCollection" ISMODIFY="No">
                    <TYPE>Voucher</TYPE>
                    <FETCH>DATE,VOUCHERTYPENAME,VOUCHERNUMBER,NARRATION,REFERENCE,ALLLEDGERENTRIES.LEDGERNAME,ALLLEDGERENTRIES.AMOUNT</FETCH>
                  </COLLECTION>
                </TDLMESSAGE>
              </TDL>
            </DESC>
          </BODY>
        </ENVELOPE>
        """
        root = self._post(xml)
        f = from_date.strftime("%Y%m%d")
        t = to_date.strftime("%Y%m%d")
        rows = []
        for v in root.findall(".//VOUCHER"):
            date = v.findtext("DATE") or ""
            if not (f <= date <= t):
                continue
            for entry in v.findall("./ALLLEDGERENTRIES.LIST"):
                if (entry.findtext("LEDGERNAME") or "").strip() != ledger_name.strip():
                    continue
                rows.append({
                    "date": date,
                    "voucher_type": v.findtext("VOUCHERTYPENAME") or "",
                    "voucher_number": v.findtext("VOUCHERNUMBER") or "",
                    "amount": entry.findtext("AMOUNT") or "",
                    "narration": v.findtext("NARRATION") or "",
                    "reference": v.findtext("REFERENCE") or "",
                })
        return rows

    def list_voucher_types(self) -> list[dict]:
        """Returns [{'name':..., 'parent':...}, ...] for all voucher types.

        The 'List of Accounts' / ACCOUNTTYPE=VoucherType report used for
        Ledger/Group reads does NOT work for voucher types on this Tally version
        -- it silently falls through to an unrelated response instead of erroring.
        This uses Tally's TDL Collection export instead, which reliably returns
        every voucher type including custom ones based on a reserved base type."""
        xml = """
        <ENVELOPE>
          <HEADER>
            <VERSION>1</VERSION>
            <TALLYREQUEST>EXPORT</TALLYREQUEST>
            <TYPE>Collection</TYPE>
            <ID>VoucherTypeCollection</ID>
          </HEADER>
          <BODY>
            <DESC>
              <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
              </STATICVARIABLES>
              <TDL>
                <TDLMESSAGE>
                  <COLLECTION NAME="VoucherTypeCollection" ISMODIFY="No">
                    <TYPE>VoucherType</TYPE>
                    <FETCH>NAME,PARENT</FETCH>
                  </COLLECTION>
                </TDLMESSAGE>
              </TDL>
            </DESC>
          </BODY>
        </ENVELOPE>
        """
        root = self._post(xml)
        out = []
        for vt in root.findall(".//VOUCHERTYPE"):
            name = vt.get("NAME") or (vt.findtext("NAME") or "")
            parent = vt.findtext("PARENT") or ""
            if name:
                out.append({"name": name.strip(), "parent": parent.strip()})
        return out

    # ---------- writes ----------

    def _import(self, master_xml: str) -> tuple[bool, str]:
        """POSTs a single master/voucher import envelope. Returns (success, message)."""
        envelope = f"""
        <ENVELOPE>
          <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
          <BODY>
            <IMPORTDATA>
              <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES><SVCURRENTCOMPANY>##SVCurrentCompany</SVCURRENTCOMPANY></STATICVARIABLES>
              </REQUESTDESC>
              <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                  {master_xml}
                </TALLYMESSAGE>
              </REQUESTDATA>
            </IMPORTDATA>
          </BODY>
        </ENVELOPE>
        """
        try:
            root = self._post(envelope)
        except (TallyConnectionError, TallyGatewayError) as e:
            return False, str(e)

        def _int(tag):
            v = root.findtext(f".//{tag}")
            try:
                return int((v or "0").strip())
            except ValueError:
                return 0

        line_errors = root.findall(".//LINEERROR")
        if line_errors:
            msgs = "; ".join(e.text or "" for e in line_errors if e.text)
            return False, msgs or "Tally rejected the request (LINEERROR)."

        errors = _int("ERRORS")
        exceptions = _int("EXCEPTIONS")
        created = _int("CREATED")
        altered = _int("ALTERED")

        if errors > 0:
            err_text = root.findtext(".//DESC") or root.findtext(".//ERROR") or ""
            return False, (err_text or "Tally reported an error.")
        if exceptions > 0:
            return False, (
                f"Tally raised {exceptions} exception(s) and created nothing "
                f"(CREATED={created}). This usually means a duplicate name, an "
                f"invalid parent, or something needing manual resolution inside Tally."
            )
        if created > 0 or altered > 0:
            return True, "OK."
        err_text = root.findtext(".//DESC") or root.findtext(".//ERROR")
        if err_text:
            return False, err_text
        return True, "OK (no explicit CREATED count returned)."

    def post_voucher(self, voucher_xml: str) -> tuple[bool, str]:
        """POSTs a single <VOUCHER> import envelope. Returns (success, message)."""
        return self._import(voucher_xml)

    def create_ledger(self, name: str, parent: str, gstin: str | None = None, state: str | None = None) -> tuple[bool, str]:
        """Attempts to create a ledger master live over the HTTP gateway. On this
        installation this reliably fails (CREATED=0, EXCEPTIONS=1, no further detail)
        even though voucher posting works fine -- kept for installations where it
        does work, but masters_xml.py's file-export path is the reliable option here."""
        from .masters_xml import ledger_fragment
        return self._import(ledger_fragment(name, parent, gstin, state))

    def create_voucher_type(self, name: str, parent: str = "Purchase") -> tuple[bool, str]:
        """Attempts to create a custom voucher type live over the HTTP gateway.
        See create_ledger's note -- unreliable here; prefer masters_xml.py."""
        from .masters_xml import voucher_type_fragment
        return self._import(voucher_type_fragment(name, parent))
