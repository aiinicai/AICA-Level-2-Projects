"""
Stage B of the pipeline: daily folder scan -> parse -> Tally voucher -> post.

Unchanged from the version already delivered to the client, except the
sys.path bootstrap below (kept, so this file still runs standalone too).

Idempotent: every file it successfully posts is recorded in
`<watch_folder>/.processed_log.json`, so re-running the same day (or
after a crash) never double-posts a contract note.
"""
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "parsers"))
sys.path.insert(0, str(Path(__file__).parent.parent / "accounting_engine"))
from broker_parsers import parse_contract_note, detect_broker_from_text  # noqa: E402
from accounting_engine import build_voucher  # noqa: E402

TALLY_GATEWAY_URL = "http://localhost:9000"  # TallyPrime XML/HTTP gateway, same machine
TALLY_COMPANY = ""  # set to the exact company name shown in TallyPrime, or leave blank for the active company

# Every fresh TallyPrime company ships with exactly one built-in godown
# ("Main Location") and treats every non-batch-tracked stock item as
# belonging to one implicit default batch ("Primary Batch") -- confirmed
# against the client's real company via Tally's own godown collection. A
# Purchase/Sales voucher's inventory entry needs an explicit godown/batch
# allocation for TallyPrime to actually attribute the entry's amount to the
# accounting side at all: without one, the voucher was accepted with HTTP
# 200 but silently rejected internally ("Voucher totals do not match", the
# Dr side reading as if the inventory entry had never been sent).
GODOWN_NAME = "Main Location"
BATCH_NAME = "Primary Batch"

# Broker contract-note PDFs are routinely password-protected (Zerodha and
# others default to the client's own PAN as the PDF open password). Set
# this to a list of candidate passwords -- typically every client's PAN
# this practice files for -- and each PDF is tried against all of them in
# turn until one opens it. app.py populates this from the dashboard's
# "PDF password(s) / Client PAN(s)" setting before calling run().
PDF_PASSWORDS: list[str] = []


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".pdf":
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError("pdfplumber not installed -- run: pip install pdfplumber")

        # Try unprotected first, then every configured password in order.
        # Broker PDFs commonly aren't actually encrypted with a *real*
        # password on the pdfplumber/pdfminer side even when a PAN is
        # printed as the "password" on the note -- but when they are, this
        # is the only way to get past it without a person typing it in
        # for every single file, every single day.
        candidates = [None] + list(PDF_PASSWORDS)
        last_error = None
        for pw in candidates:
            try:
                kwargs = {"password": pw} if pw else {}
                with pdfplumber.open(path, **kwargs) as pdf:
                    return "\n".join(page.extract_text() or "" for page in pdf.pages)
            except Exception as e:
                last_error = e
                continue
        tried = "no password" if not PDF_PASSWORDS else f"no password and {len(PDF_PASSWORDS)} configured password(s)"
        raise RuntimeError(
            f"Could not open {path.name} -- it looks password-protected and none of the "
            f"configured passwords worked (tried {tried}). Add the correct client PAN / "
            f"password in the dashboard's Settings, under 'PDF password(s) / Client PAN(s)'. "
            f"(underlying error: {last_error})"
        )
    raise ValueError(f"Unsupported file type: {path.suffix}")


def build_ledger_create_xml(name: str, parent: str) -> str:
    """One <TALLYMESSAGE> that creates a ledger master under an existing
    Tally group (Stock-in-Hand, Indirect Incomes, etc -- all built into
    every fresh TallyPrime company by default, so no group setup is
    needed either). Sent in the SAME request as the voucher, ahead of it
    ("masters before vouchers"), so a ledger this app needs is created the
    first time it's referenced -- no manual pre-creation in Tally required
    for a hands-off pipeline. Tally's ACTION="Create" is a safe no-op
    against a ledger that already exists (unlike ACTION="Alter", it does
    not overwrite an existing master's settings), so this is sent every
    run rather than trying to track what's already there."""
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        f'        <LEDGER NAME="{esc(name)}" ACTION="Create">\n'
        f"          <NAME>{esc(name)}</NAME>\n"
        f"          <PARENT>{esc(parent)}</PARENT>\n"
        "        </LEDGER>\n"
        "      </TALLYMESSAGE>"
    )


def build_stock_group_create_xml(name: str) -> str:
    """A top-level Stock Group (parent omitted -- Tally defaults a new
    stock group to the root "Primary" group). Same safe, idempotent
    ACTION="Create" pattern as build_ledger_create_xml."""
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        f'        <STOCKGROUP NAME="{esc(name)}" ACTION="Create">\n'
        f"          <NAME>{esc(name)}</NAME>\n"
        "        </STOCKGROUP>\n"
        "      </TALLYMESSAGE>"
    )


def build_unit_create_xml(name: str) -> str:
    """A simple Unit of Measure (e.g. "Shares") -- TallyPrime ships with
    no units pre-created at all, so one must exist before any stock item
    can use it."""
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        f'        <UNIT NAME="{esc(name)}" ACTION="Create">\n'
        f"          <NAME>{esc(name)}</NAME>\n"
        "          <ISSIMPLEUNIT>Yes</ISSIMPLEUNIT>\n"
        f"          <SYMBOL>{esc(name)}</SYMBOL>\n"
        f"          <FORMALNAME>{esc(name)}</FORMALNAME>\n"
        "          <DECIMALPLACES>0</DECIMALPLACES>\n"
        "        </UNIT>\n"
        "      </TALLYMESSAGE>"
    )


def build_stock_item_create_xml(name: str, group: str, uom: str) -> str:
    """One stock item (e.g. a scrip symbol like "TCS"), under the given
    Stock Group and Unit of Measure. Deliberately carries no GST/HSN tags
    at all -- see the accounting_engine module docstring on why equity
    shares must never be tagged for GST."""
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        f'        <STOCKITEM NAME="{esc(name)}" ACTION="Create">\n'
        f"          <NAME>{esc(name)}</NAME>\n"
        f"          <PARENT>{esc(group)}</PARENT>\n"
        f"          <BASEUNITS>{esc(uom)}</BASEUNITS>\n"
        "        </STOCKITEM>\n"
        "      </TALLYMESSAGE>"
    )


def get_existing_names(collection_id: str, tag: str, gateway_url: str = TALLY_GATEWAY_URL, company: str = "") -> set[str]:
    """Fetches every master name of one type (ledgers, stock items, stock
    groups, units, ...) that already exists in the given TallyPrime
    company, via one of Tally's built-in collection exports over the same
    XML/HTTP gateway (`collection_id` e.g. "List of Ledgers", "List of
    Stock Items"; `tag` the XML element each entry uses, e.g. "LEDGER",
    "STOCKITEM"). Used so this app only ever *creates* a master that's
    genuinely missing, and never re-sends a Create for one that already
    exists -- Tally treats Create against an existing master as an
    attempted Alter, and refuses certain changes outright (e.g. "Improper
    change of Group Name" the moment the parent group differs from what's
    already there), which otherwise blocks the whole voucher import even
    though the master itself is perfectly usable as-is. Returns an empty
    set (meaning "assume nothing exists yet, try to create everything") if
    the lookup itself fails for any reason -- the normal post-and-check-
    the-response flow still catches a genuine problem from there."""
    import re as _re
    import html
    import requests
    request_xml = f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>EXPORT</TALLYREQUEST>
    <TYPE>COLLECTION</TYPE>
    <ID>{collection_id}</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""
    try:
        resp = requests.post(gateway_url, data=request_xml.encode("utf-8"),
                              headers={"Content-Type": "text/xml"}, timeout=30)
        resp.raise_for_status()
        # Regex, not a strict XML parser: Tally's own collection export is
        # occasionally not perfectly well-formed (e.g. a stray unescaped
        # "&" inside a name), and all that's needed here is the NAME
        # attribute off each matching element.
        names = _re.findall(rf'<{tag}[^>]*\bNAME="([^"]*)"', resp.text)
        return {html.unescape(n) for n in names}
    except Exception:
        return set()


def get_existing_ledgers(gateway_url: str = TALLY_GATEWAY_URL, company: str = "") -> set[str]:
    return get_existing_names("List of Ledgers", "LEDGER", gateway_url, company)


def get_existing_stock_items(gateway_url: str = TALLY_GATEWAY_URL, company: str = "") -> set[str]:
    return get_existing_names("List of Stock Items", "STOCKITEM", gateway_url, company)


def get_existing_stock_groups(gateway_url: str = TALLY_GATEWAY_URL, company: str = "") -> set[str]:
    return get_existing_names("List of Stock Groups", "STOCKGROUP", gateway_url, company)


def get_existing_units(gateway_url: str = TALLY_GATEWAY_URL, company: str = "") -> set[str]:
    """NOT USED by run() -- kept only for reference/manual use. "List of
    Units" is NOT a real built-in TallyPrime collection (unlike the three
    above); sending this exact request against a real TallyPrime instance
    produced 'Error in TDL. 'Collection:List of Units' Could not find
    description!' and made Tally itself unstable. Do not wire this back
    into run()'s existing-master lookups without first confirming a
    genuinely valid collection ID for Units against a real Tally instance."""
    return get_existing_names("List of Units", "UNIT", gateway_url, company)


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ledger_entry_xml(ledger: str, dr_cr: str, amount: float, indent: str = "      ",
                       bill_ref: str | None = None, invert_sign: bool = False,
                       list_tag: str = "ALLLEDGERENTRIES.LIST", is_party: bool = False) -> str:
    """One ledger-entry block. TWO different, both TallyPrime-confirmed sign
    conventions coexist depending on voucher type:

      - Journal (and any other non-invoice voucher; invert_sign=False, the
        default): Dr -> ISDEEMEDPOSITIVE Yes with a POSITIVE amount, Cr ->
        No with a NEGATIVE amount. This is the convention already proven
        working live for this project's Journal vouchers.
      - A Purchase/Sales voucher in "Invoice Voucher View" (ISINVOICE=Yes):
        confirmed against TallyPrime's own official sample XML
        (help.tallysolutions.com/sample-xml/, "Sales Transaction - As
        Invoice" -- a fully self-balancing sample) that the sign is the
        OPPOSITE: Dr -> ISDEEMEDPOSITIVE Yes with a NEGATIVE amount, Cr ->
        No with a POSITIVE amount. _purchase_or_sales_voucher_xml passes
        invert_sign=True for every entry in that voucher to match.

    list_tag lets a Purchase/Sales (invoice-mode) voucher use
    <LEDGERENTRIES.LIST> for its party entry, matching that same official
    sample, instead of the <ALLLEDGERENTRIES.LIST> Journal vouchers use.

    is_party adds <ISPARTYLEDGER> and <ISLASTDEEMEDPOSITIVE> -- present on
    the party entry in that same official sample, absent elsewhere.

    bill_ref, when given, attaches a <BILLALLOCATIONS.LIST> ("New Ref",
    same signed amount) -- required for a bill-wise ledger (Tally's default
    "Sundry Creditors" group has bill-wise tracking on), otherwise Tally
    rejects the whole voucher with "Voucher totals do not match" even
    though the entry itself was sent with the right amount -- confirmed
    live: a Purchase voucher's broker entry was silently not counted into
    the Dr/Cr total at all without one."""
    is_debit = dr_cr == "Dr"
    base_signed = amount if is_debit else -amount
    signed = -base_signed if invert_sign else base_signed
    bill_block = ""
    if bill_ref:
        bill_block = (
            f"\n{indent}  <BILLALLOCATIONS.LIST>\n"
            f"{indent}    <NAME>{_esc(bill_ref)}</NAME>\n"
            f"{indent}    <BILLTYPE>New Ref</BILLTYPE>\n"
            f"{indent}    <AMOUNT>{signed:.2f}</AMOUNT>\n"
            f"{indent}  </BILLALLOCATIONS.LIST>"
        )
    party_tags = ""
    if is_party:
        party_tags = (
            f"\n{indent}  <ISPARTYLEDGER>Yes</ISPARTYLEDGER>"
            f"\n{indent}  <ISLASTDEEMEDPOSITIVE>{'Yes' if is_debit else 'No'}</ISLASTDEEMEDPOSITIVE>"
        )
    return (
        f"{indent}<{list_tag}>\n"
        f"{indent}  <LEDGERNAME>{_esc(ledger)}</LEDGERNAME>\n"
        f"{indent}  <ISDEEMEDPOSITIVE>{'Yes' if is_debit else 'No'}</ISDEEMEDPOSITIVE>{party_tags}\n"
        f"{indent}  <AMOUNT>{signed:.2f}</AMOUNT>{bill_block}\n"
        f"{indent}</{list_tag}>"
    )


def _journal_voucher_xml(v: dict, date_tally: str, broker_ledger: str | None = None, bill_ref_base: str | None = None) -> str:
    entries = "\n".join(
        _ledger_entry_xml(
            l["ledger"], l["dr_cr"], l["amount"],
            bill_ref=f"{bill_ref_base}-Journal" if (broker_ledger and bill_ref_base and l["ledger"] == broker_ledger) else None,
        )
        for l in v["lines"]
    )
    return (
        '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        f'        <VOUCHER VCHTYPE="Journal" ACTION="Create">\n'
        f"          <DATE>{date_tally}</DATE>\n"
        "          <VOUCHERTYPENAME>Journal</VOUCHERTYPENAME>\n"
        f"          <NARRATION>{_esc(v['narration'])}</NARRATION>\n"
        f"{entries}\n"
        "        </VOUCHER>\n"
        "      </TALLYMESSAGE>"
    )


def _purchase_or_sales_voucher_xml(v: dict, date_tally: str, uom: str, bill_ref_base: str | None = None) -> str:
    """A Purchase (buy legs) or Sales (sell legs) voucher with per-scrip
    stock-item inventory allocations, so TallyPrime actually tracks
    quantity-wise inventory for each symbol -- a plain Journal voucher has
    no concept of inventory at all.

    Built as a genuine "Invoice Voucher View" (VOUCHER ACTION="Create"
    OBJVIEW="Invoice Voucher View", plus <ISINVOICE>Yes</ISINVOICE> and
    <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>) -- this was the
    actual root cause of the long-standing "Voucher totals do not match"
    rejection: without these three, TallyPrime doesn't treat the voucher as
    an item invoice at all, so the ACCOUNTINGALLOCATIONS.LIST amounts
    nested inside ALLINVENTORYENTRIES.LIST were never being folded into the
    voucher's Dr/Cr total no matter what else was tried. Confirmed against
    TallyPrime's own official sample XML (help.tallysolutions.com/
    sample-xml/, "Sales Transaction - As Invoice", a fully self-balancing
    example) which uses exactly this structure. That same sample also
    revealed that Invoice-mode Purchase/Sales vouchers use the OPPOSITE
    amount-sign convention from a Journal voucher: Dr -> ISDEEMEDPOSITIVE
    Yes with a NEGATIVE amount, Cr -> No with a POSITIVE amount (every
    entry below is built with invert_sign=True for this reason). The
    party ledger line uses <LEDGERENTRIES.LIST> (not ALLLEDGERENTRIES.LIST)
    with <ISPARTYLEDGER>/<ISLASTDEEMEDPOSITIVE>, matching that same sample;
    there is no separate top-level entry for the Purchase/Sales ledger
    itself -- only the nested ACCOUNTINGALLOCATIONS.LIST, again exactly as
    in Tally's own sample, since with ISINVOICE=Yes that nested amount is
    now correctly counted.

    Sign convention (before inversion): for a Purchase, the stock item side
    is Dr (stock increasing) and the broker/party side is Cr (money paid
    out); for a Sales voucher it's the mirror image."""
    vtype = v["voucher_type"]  # "Purchase" or "Sales"
    is_purchase = vtype == "Purchase"
    item_side = "Dr" if is_purchase else "Cr"       # stock item: Dr on a Purchase, Cr on a Sale
    party_side = "Cr" if is_purchase else "Dr"       # broker: Cr on a Purchase (money out), Dr on a Sale (money in)
    is_item_debit = item_side == "Dr"
    item_sign = -1 if is_item_debit else 1          # inverted vs. Journal -- see docstring

    inv_blocks = []
    for il in v["inventory_lines"]:
        amount = il["amount"] * item_sign
        qty_str = f"{il['quantity']:g} {_esc(uom)}"
        rate = il.get("rate")
        rate_tag = f"        <RATE>{rate:.2f}/{_esc(uom)}</RATE>\n" if rate else ""
        inv_blocks.append(
            "      <ALLINVENTORYENTRIES.LIST>\n"
            f"        <STOCKITEMNAME>{_esc(il['stock_item'])}</STOCKITEMNAME>\n"
            f"        <ISDEEMEDPOSITIVE>{'Yes' if is_item_debit else 'No'}</ISDEEMEDPOSITIVE>\n"
            f"{rate_tag}"
            f"        <AMOUNT>{amount:.2f}</AMOUNT>\n"
            f"        <ACTUALQTY>{qty_str}</ACTUALQTY>\n"
            f"        <BILLEDQTY>{qty_str}</BILLEDQTY>\n"
            "        <BATCHALLOCATIONS.LIST>\n"
            f"          <GODOWNNAME>{_esc(GODOWN_NAME)}</GODOWNNAME>\n"
            f"          <BATCHNAME>{_esc(BATCH_NAME)}</BATCHNAME>\n"
            f"          <AMOUNT>{amount:.2f}</AMOUNT>\n"
            f"          <ACTUALQTY>{qty_str}</ACTUALQTY>\n"
            f"          <BILLEDQTY>{qty_str}</BILLEDQTY>\n"
            "        </BATCHALLOCATIONS.LIST>\n"
            "        <ACCOUNTINGALLOCATIONS.LIST>\n"
            f"          <LEDGERNAME>{_esc(v['inventory_ledger'])}</LEDGERNAME>\n"
            f"          <ISDEEMEDPOSITIVE>{'Yes' if is_item_debit else 'No'}</ISDEEMEDPOSITIVE>\n"
            f"          <AMOUNT>{amount:.2f}</AMOUNT>\n"
            "        </ACCOUNTINGALLOCATIONS.LIST>\n"
            "      </ALLINVENTORYENTRIES.LIST>"
        )

    bill_ref = f"{bill_ref_base}-{vtype}" if bill_ref_base else None
    party_entry = _ledger_entry_xml(
        v["party_ledger"], party_side, v["party_amount"],
        bill_ref=bill_ref, invert_sign=True, list_tag="LEDGERENTRIES.LIST", is_party=True,
    )

    return (
        '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        f'        <VOUCHER VCHTYPE="{vtype}" ACTION="Create" OBJVIEW="Invoice Voucher View">\n'
        f"          <DATE>{date_tally}</DATE>\n"
        f"          <VOUCHERTYPENAME>{vtype}</VOUCHERTYPENAME>\n"
        "          <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>\n"
        "          <ISINVOICE>Yes</ISINVOICE>\n"
        f"          <NARRATION>{_esc(v['narration'])}</NARRATION>\n"
        f"          <PARTYLEDGERNAME>{_esc(v['party_ledger'])}</PARTYLEDGERNAME>\n"
        f"{party_entry}\n"
        f"{chr(10).join(inv_blocks)}\n"
        "        </VOUCHER>\n"
        "      </TALLYMESSAGE>"
    )


def build_tally_xml(
    voucher: dict,
    company: str = "",
    existing_ledgers: set[str] | None = None,
    existing_stock_items: set[str] | None = None,
    existing_stock_groups: set[str] | None = None,
    existing_units: set[str] | None = None,
) -> str:
    """Builds ONE combined XML request containing every master this
    contract note needs that doesn't already exist (ledgers, the stock
    group, the unit of measure, per-scrip stock items -- masters before
    vouchers), followed by every voucher this note produces (Purchase for
    delivery buys, Sales for delivery sells, Journal for everything else
    -- see accounting_engine.build_voucher). Each *_masters set defaults
    to empty (meaning "create everything"), matching build_ledger_create_
    xml's existing "safe to always send Create, but prefer checking first"
    contract."""
    date_tally = voucher["date"].replace("-", "")
    existing_ledgers = existing_ledgers or set()
    existing_stock_items = existing_stock_items or set()
    existing_stock_groups = existing_stock_groups or set()
    existing_units = existing_units or set()

    masters = []
    if voucher.get("stock_items"):
        uom = voucher["stock_uom"]
        group = voucher["stock_group"]
        if uom not in existing_units:
            masters.append(build_unit_create_xml(uom))
        if group not in existing_stock_groups:
            masters.append(build_stock_group_create_xml(group))
        for item_name, item_group in voucher["stock_items"].items():
            if item_name not in existing_stock_items:
                masters.append(build_stock_item_create_xml(item_name, item_group, uom))
    for name, parent in voucher.get("ledger_groups", {}).items():
        if name not in existing_ledgers:
            masters.append(build_ledger_create_xml(name, parent))

    broker_ledger = voucher.get("broker_ledger")
    bill_ref_base = voucher.get("contract_note_no")
    voucher_blocks = []
    for v in voucher["vouchers"]:
        if v["voucher_type"] == "Journal":
            voucher_blocks.append(_journal_voucher_xml(v, date_tally, broker_ledger, bill_ref_base))
        else:
            voucher_blocks.append(_purchase_or_sales_voucher_xml(v, date_tally, voucher["stock_uom"], bill_ref_base))

    data_body = "\n".join(masters + voucher_blocks)

    return f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Import</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Vouchers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVCURRENTCOMPANY>{_esc(company)}</SVCURRENTCOMPANY>
      </STATICVARIABLES>
    </DESC>
    <DATA>
{data_body}
    </DATA>
  </BODY>
</ENVELOPE>"""


def post_to_tally(xml: str, gateway_url: str = TALLY_GATEWAY_URL) -> str:
    """Posts the voucher XML to TallyPrime's XML/HTTP gateway.

    IMPORTANT Tally-specific gotcha: the gateway always answers with HTTP
    200 -- even when it rejects the voucher outright (an unknown ledger
    name, a company-name mismatch, a disabled voucher type, etc). The real
    outcome is only inside the response body's <IMPORTRESULT> block
    (<CREATED>/<ERRORS>/<LINEERROR>), so resp.raise_for_status() alone is
    not enough to know whether anything was actually posted -- it must be
    parsed, or a rejected voucher gets silently marked "posted" here while
    never actually appearing in Tally."""
    import re as _re
    import requests
    resp = requests.post(gateway_url, data=xml.encode("utf-8"),
                          headers={"Content-Type": "text/xml"}, timeout=30)
    resp.raise_for_status()
    body = resp.text

    created = _re.search(r"<CREATED>\s*(\d+)\s*</CREATED>", body)
    errors = _re.search(r"<ERRORS>\s*(\d+)\s*</ERRORS>", body)
    line_error = _re.search(r"<LINEERROR>(.*?)</LINEERROR>", body, _re.DOTALL)

    if created is None and errors is None:
        raise RuntimeError(
            "Tally's response didn't look like a voucher-import result at all -- is "
            f"TallyPrime's XML/HTTP gateway actually listening at {gateway_url} (and not "
            f"some other service on that port)? Raw response (first 300 chars): {body[:300]!r}"
        )

    accepted = created is not None and created.group(1) != "0" and (errors is None or errors.group(1) == "0")
    if not accepted:
        reason = line_error.group(1).strip() if (line_error and line_error.group(1).strip()) else None
        raise RuntimeError(
            "Tally received the request but did NOT create the voucher"
            + (f" -- {reason}" if reason else ".")
            + " Most common causes: one of the ledger names in the voucher (see the Tally "
              "Accounting step for the exact names) doesn't exist yet in TallyPrime under the "
              "company set in Settings, the company name in Settings doesn't match the one in "
              "Tally exactly, or the 'Journal' voucher type isn't enabled for that company."
        )
    return body


def load_processed_log(watch_folder: Path) -> dict:
    log_path = watch_folder / ".processed_log.json"
    if log_path.exists():
        return json.loads(log_path.read_text())
    return {}


def save_processed_log(watch_folder: Path, log: dict) -> None:
    (watch_folder / ".processed_log.json").write_text(json.dumps(log, indent=2))


def run(watch_folder: str, dry_run: bool = False) -> dict:
    watch_folder = Path(watch_folder)
    processed_dir = watch_folder / "processed"
    error_dir = watch_folder / "errors"
    processed_dir.mkdir(exist_ok=True)
    error_dir.mkdir(exist_ok=True)

    log = load_processed_log(watch_folder)
    results = {"posted": [], "skipped": [], "errors": [], "details": []}

    candidates = [p for p in watch_folder.iterdir()
                  if p.is_file() and p.suffix.lower() in (".pdf", ".txt")]

    # Fetched once per run (not once per file) to save round-trips, then
    # kept up to date in memory as masters get created below -- so if this
    # run posts several notes that all need the same new ledger/stock item,
    # it's only actually created once, on the first one. Dry runs never
    # touch Tally at all (they stay fully offline by design), so this is
    # skipped then.
    existing_ledgers: set[str] = get_existing_ledgers(TALLY_GATEWAY_URL, TALLY_COMPANY) if not dry_run else set()
    existing_stock_items: set[str] = get_existing_stock_items(TALLY_GATEWAY_URL, TALLY_COMPANY) if not dry_run else set()
    existing_stock_groups: set[str] = get_existing_stock_groups(TALLY_GATEWAY_URL, TALLY_COMPANY) if not dry_run else set()
    # NOT fetched via get_existing_units() -- unlike "List of Ledgers" /
    # "List of Stock Items" / "List of Stock Groups" (all genuine built-in
    # Tally collections), "List of Units" is NOT a collection TallyPrime
    # actually ships -- sending that request produced a TDL error ("Error
    # in TDL. 'Collection:List of Units' Could not find description!") that
    # made Tally itself unstable. So the Unit master (just "Shares" --
    # ISSIMPLEUNIT/SYMBOL/FORMALNAME/DECIMALPLACES, always identical) is
    # simply always sent as ACTION="Create" every run instead, the same
    # safe-idempotent-Create pattern ledgers relied on before the
    # existing-ledger check was added -- since its fields never change
    # between runs, Create against an already-existing Unit is a no-op, not
    # a rejection.
    existing_units: set[str] = set()

    for path in sorted(candidates):
        file_key = f"{path.name}:{path.stat().st_mtime_ns}"
        # A file already actually posted (or already run live and failed --
        # that one's been moved out of here into errors/ anyway) is skipped.
        # A file that was only ever *dry-run* is NOT skipped here even
        # though it has a log entry -- a dry run never posts to Tally or
        # moves the file, so without this check, testing a file with "Dry
        # run" first (the normal, sensible way to try a new note) would
        # permanently poison it: the very next "Post to Tally" click would
        # see the same file_key already in the log and silently skip it
        # forever, with the file never posting and never moving anywhere,
        # which looks exactly like nothing is happening at all.
        if file_key in log and not (log[file_key].get("dry_run") and not dry_run):
            results["skipped"].append(path.name)
            continue
        try:
            text = extract_text(path)
            broker = detect_broker_from_text(text)
            normalized = parse_contract_note(broker, text)
            voucher = build_voucher(normalized)
            xml = build_tally_xml(
                voucher, company=TALLY_COMPANY,
                existing_ledgers=existing_ledgers,
                existing_stock_items=existing_stock_items,
                existing_stock_groups=existing_stock_groups,
                existing_units=existing_units,
            )

            if not dry_run:
                # Pass TALLY_GATEWAY_URL explicitly (rather than relying on
                # post_to_tally's default parameter) -- a default value is
                # bound once at module-load time, so it would otherwise
                # keep using whatever URL was hardcoded when this module
                # was first imported, silently ignoring any different
                # gateway URL app.py sets from Settings afterwards.
                post_to_tally(xml, TALLY_GATEWAY_URL)
                existing_ledgers |= set(voucher.get("ledger_groups", {}).keys())
                if voucher.get("stock_items"):
                    existing_stock_items |= set(voucher["stock_items"].keys())
                    existing_stock_groups |= {voucher["stock_group"]}
                    existing_units |= {voucher["stock_uom"]}
                shutil.move(str(path), str(processed_dir / path.name))
            log[file_key] = {
                "file": path.name, "broker": broker,
                "contract_note_no": normalized["contract_note_no"],
                "account_code": normalized["account_code"],
                "trade_date": normalized["trade_date"],
                "posted_at": datetime.now().isoformat(),
                "dry_run": dry_run,
            }
            results["posted"].append(path.name)
            results["details"].append({
                "file": path.name, "broker": broker,
                "normalized": normalized, "voucher": voucher,
            })
        except Exception as e:
            if not dry_run:
                shutil.move(str(path), str(error_dir / path.name))
            results["errors"].append({"file": path.name, "error": str(e)})

    save_processed_log(watch_folder, log)
    return results


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Daily contract-note folder scan -> Tally posting")
    ap.add_argument("watch_folder", help="Folder to scan for new contract note files")
    ap.add_argument("--dry-run", action="store_true",
                     help="Parse and build vouchers but do not post to Tally or move files")
    args = ap.parse_args()

    result = run(args.watch_folder, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    print(f"\nPosted: {len(result['posted'])}, Skipped (already processed): {len(result['skipped'])}, "
          f"Errors: {len(result['errors'])}")
