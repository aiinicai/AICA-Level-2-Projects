"""TallyPrime connector (local XML over HTTP).

Safety rules implemented here:
* Nothing is sent unless post_journal()/validate_*() is called by an explicit user action (confirmed=True is required for posting).
* HTTP 200 is NOT success. A voucher is recorded as posted only when Tally's response reports it created (CREATED >= 1, no
  LINEERROR, ERRORS/EXCEPTIONS = 0). Ambiguous replies are stored as 'unconfirmed' and block re-posting until the user resolves them.
* Idempotency: stable voucher number / REMOTEID = journal reference; journals already 'posted' or 'unconfirmed' are refused locally.
* The connector only writes to posting_log / journals.posting_state. It never changes calculations or journal amounts.

Items NOT verified against Tally documentation (see docs/ASSUMPTIONS.md): REMOTEID semantics, CREATED/ERRORS/LASTVCHID response tags in every
TallyPrime release, and the TDL ledger-collection request used by validate_ledgers().
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from xml.sax.saxutils import escape

from .money import dec, ZERO


class TallyUnavailable(Exception):
    """Tally cannot be reached (not running, wrong port, timeout). Entries stay pending."""


class TallyConfigError(ValueError):
    """Configuration problem detected before any request is sent."""


@dataclass
class TallyConfig:
    host: str = 'localhost'
    port: int = 9000
    company: str = ''
    voucher_type: str = 'Journal'
    timeout: int = 15
    use_json: bool = False
    narration_prefix: str = 'IFRS16'

    @property
    def url(self):
        return f'http://{self.host}:{self.port}'

    @staticmethod
    def from_dict(d):
        c = TallyConfig()
        for k in c.__dict__:
            if k in d:
                setattr(c, k, type(getattr(c, k))(d[k]) if k not in ('use_json',) else bool(d[k]))
        return c


def _amt(x: Decimal) -> str:
    return f'{x:.2f}'


def voucher_message(journal: dict, cfg: TallyConfig, account_map: dict) -> str:
    """One <TALLYMESSAGE> for a stored journal dict (as returned by Store.journal)."""
    if not cfg.company.strip():
        raise TallyConfigError('Enter the Tally company name in the connector settings.')
    lines = journal['lines']
    dr = sum(dec(l['debit']) for l in lines)
    cr = sum(dec(l['credit']) for l in lines)
    if dr != cr or dr == 0:
        raise TallyConfigError(f"Journal {journal['ref']} is not balanced (Dr {dr} / Cr {cr}).")
    entries = []
    for l in lines:
        m = account_map.get(l['account'])
        if not m or not str(m.get('ledger', '')).strip():
            raise TallyConfigError(f"No Tally ledger is mapped for account '{l['account']}'. Complete the ledger mapping first.")
        led = escape(m['ledger'])
        d, c = dec(l['debit']), dec(l['credit'])
        if d:
            entries.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{led}</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-{_amt(d)}</AMOUNT></ALLLEDGERENTRIES.LIST>")
        if c:
            entries.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{led}</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>{_amt(c)}</AMOUNT></ALLLEDGERENTRIES.LIST>")
    date = journal['jdate'].replace('-', '')
    narr = escape(f"{cfg.narration_prefix} | {journal['ref']} | {journal['narration']}")
    ref = escape(journal['ref'])
    vt = escape(cfg.voucher_type)
    return (f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER REMOTEID="{ref}" VCHTYPE="{vt}" ACTION="Create" OBJVIEW="Accounting Voucher View">'
            f'<DATE>{date}</DATE><VOUCHERTYPENAME>{vt}</VOUCHERTYPENAME><VOUCHERNUMBER>{ref}</VOUCHERNUMBER>'
            f'<REFERENCE>{ref}</REFERENCE><NARRATION>{narr}</NARRATION>{"".join(entries)}</VOUCHER></TALLYMESSAGE>')


def envelope(messages: list[str], cfg: TallyConfig) -> str:
    return ('<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Import</TALLYREQUEST><TYPE>Data</TYPE><ID>Vouchers</ID></HEADER>'
            f'<BODY><DESC><STATICVARIABLES><SVCURRENTCOMPANY>{escape(cfg.company)}</SVCURRENTCOMPANY></STATICVARIABLES></DESC>'
            f'<DATA>{"".join(messages)}</DATA></BODY></ENVELOPE>')


def build_voucher_xml(journal: dict, cfg: TallyConfig, account_map: dict) -> str:
    return envelope([voucher_message(journal, cfg, account_map)], cfg)


def export_xml_file(journals: list[dict], cfg: TallyConfig, account_map: dict, path: str) -> int:
    """Fallback: write a single Tally import file (Gateway of Tally > Import > Vouchers) – works with Tally offline."""
    msgs = [voucher_message(j, cfg, account_map) for j in journals]
    if not msgs:
        raise TallyConfigError('There are no journals to export.')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + envelope(msgs, cfg))
    return len(msgs)


# ---------------------------------------------------------------- transport
def send(xml: str, cfg: TallyConfig) -> tuple[int, str]:
    req = urllib.request.Request(cfg.url, data=xml.encode('utf-8'), headers={'Content-Type': 'text/xml; charset=utf-8'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        raise TallyUnavailable(f'Cannot reach TallyPrime at {cfg.url}: {getattr(e, "reason", e)}. Start TallyPrime, open the company and enable the HTTP server (F1 Help > Settings > Connectivity), or use the XML export fallback.') from e


def _tag(text, name):
    m = re.findall(rf'<{name}>\s*([^<]*?)\s*</{name}>', text, flags=re.I)
    return m


def classify_response(status: int, text: str) -> dict:
    """Return {'outcome': success|failed|unconfirmed, 'voucher_id', 'reason'}. Success requires an explicit creation report."""
    if status != 200:
        return {'outcome': 'failed', 'voucher_id': '', 'reason': f'HTTP status {status} from Tally.'}
    body = text or ''
    if not body.strip():
        return {'outcome': 'unconfirmed', 'voucher_id': '', 'reason': 'Tally returned an empty response, so creation could not be confirmed.'}
    errs = [e for e in _tag(body, 'LINEERROR') if e]
    if errs:
        return {'outcome': 'failed', 'voucher_id': '', 'reason': '; '.join(errs)}
    def num(n):
        v = _tag(body, n)
        try:
            return int(float(v[0])) if v else None
        except ValueError:
            return None
    created, errors, exc, status_tag = num('CREATED'), num('ERRORS'), num('EXCEPTIONS'), num('STATUS')
    if (errors or 0) > 0 or (exc or 0) > 0:
        return {'outcome': 'failed', 'voucher_id': '', 'reason': f'Tally reported ERRORS={errors}, EXCEPTIONS={exc}.'}
    if status_tag == 0 and not created:
        return {'outcome': 'failed', 'voucher_id': '', 'reason': 'Tally returned STATUS 0 (request not processed). Check the company name is open and the voucher type exists.'}
    last = _tag(body, 'LASTVCHID')
    if (created or 0) >= 1 and (errors in (0, None)):
        return {'outcome': 'success', 'voucher_id': (last[0] if last else ''), 'reason': ''}
    if re.search(r'unknown request', body, re.I):
        return {'outcome': 'failed', 'voucher_id': '', 'reason': 'Tally did not accept the request.'}
    return {'outcome': 'unconfirmed', 'voucher_id': (last[0] if last else ''), 'reason': 'Tally replied but did not report a voucher as created. Check Day Book in Tally, then resolve the status manually.'}


# ---------------------------------------------------------------- user actions
def test_connection(cfg: TallyConfig) -> dict:
    """Connectivity check: a GET/POST to the Tally port answers with a short 'TallyPrime Server is Running' banner."""
    try:
        req = urllib.request.Request(cfg.url, method='GET')
        with urllib.request.urlopen(req, timeout=cfg.timeout) as r:
            body = r.read().decode('utf-8', 'replace')
            ok = r.status == 200
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        return {'ok': False, 'message': f'Cannot reach {cfg.url}: {getattr(e, "reason", e)}'}
    running = 'tally' in body.lower()
    return {'ok': ok and running, 'message': (body.strip()[:200] or 'Empty response') + ('' if running else ' – response does not look like TallyPrime.')}


def ledger_list_request(cfg: TallyConfig) -> str:
    """TDL collection export for ledger names (UNVERIFIED on official docs – falls back to a user-visible warning)."""
    return ('<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>IFRS16LedgerList</ID></HEADER>'
            f'<BODY><DESC><STATICVARIABLES><SVCURRENTCOMPANY>{escape(cfg.company)}</SVCURRENTCOMPANY><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>'
            '<TDL><TDLMESSAGE><COLLECTION NAME="IFRS16LedgerList" ISMODIFY="No"><TYPE>Ledger</TYPE><FETCH>NAME</FETCH></COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>')


def validate_ledgers(cfg: TallyConfig, account_map: dict) -> dict:
    """Return {'ok', 'missing': [...], 'found': n, 'message'}. Never raises on Tally being down."""
    if not cfg.company.strip():
        return {'ok': False, 'missing': [], 'found': 0, 'message': 'Enter the Tally company name first.'}
    try:
        status, text = send(ledger_list_request(cfg), cfg)
    except TallyUnavailable as e:
        return {'ok': False, 'missing': [], 'found': 0, 'message': str(e)}
    if status != 200:
        return {'ok': False, 'missing': [], 'found': 0, 'message': f'HTTP {status} from Tally.'}
    names = set(re.findall(r'<LEDGER[^>]*\sNAME="([^"]+)"', text)) | set(x for x in _tag(text, 'NAME'))
    names = {n.replace('&amp;', '&').strip().lower() for n in names}
    if not names:
        return {'ok': False, 'missing': [], 'found': 0, 'message': 'Tally returned no ledgers. Check the company name is loaded in Tally. (The ledger-list request is not verified for every TallyPrime release.)'}
    missing = [m['ledger'] for m in account_map.values() if m['ledger'].strip().lower() not in names]
    return {'ok': not missing, 'missing': missing, 'found': len(names), 'message': 'All mapped ledgers exist.' if not missing else f'{len(missing)} mapped ledger(s) not found in Tally: ' + ', '.join(missing)}


def preview(store, ref, cfg: TallyConfig) -> str:
    j = store.journal(ref)
    return build_voucher_xml(j, cfg, store.get_setting('account_map'))


def post_journal(store, ref, cfg: TallyConfig, confirmed: bool = False) -> dict:
    """Post one APPROVED journal. Requires confirmed=True (an explicit user action). Returns the classified outcome."""
    if not confirmed:
        raise TallyConfigError('Posting to Tally requires explicit confirmation.')
    j = store.journal(ref)
    if j['status'] == 'superseded':
        raise TallyConfigError('This journal has been superseded by a later version and must not be posted.')
    if j['status'] not in ('approved', 'posted'):
        raise TallyConfigError('Only approved journals can be posted. Approve the journal first.')
    if j['posting_state'] == 'posted':
        raise TallyConfigError(f"Journal {ref} is already posted (voucher {j['voucher_id'] or 'recorded'}). Duplicate posting prevented.")
    if j['posting_state'] == 'unconfirmed':
        raise TallyConfigError(f'Journal {ref} has an unconfirmed earlier attempt. Check Day Book in Tally, then use "Resolve" to record whether the voucher exists, to avoid a duplicate.')
    xml = build_voucher_xml(j, cfg, store.get_setting('account_map'))
    try:
        status, text = send(xml, cfg)
    except TallyUnavailable as e:
        store.log_posting(ref, 'post', xml, '', 0, 'unavailable', '', str(e))
        return {'outcome': 'unavailable', 'voucher_id': '', 'reason': str(e)}
    res = classify_response(status, text)
    store.log_posting(ref, 'post', xml, text, status, res['outcome'], res['voucher_id'] or (ref if res['outcome'] == 'success' else ''), res['reason'])
    return res
