from datetime import date, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.db import locks
from app.db.models import (AuditLog, Company, MappingRule, MasterCache, Outbox, VoucherHistory,
                           utcnow)
from app.db.session import local_sessionmaker, make_local_engine, make_remote_engine
from app.db.sync import sync
from app.tally import parsers, xml_requests as rq
from app.tally.client import TallyClient, TallyError
from app.tally.sync_masters import sync_company
from tests import fake_tally


@pytest.fixture(scope="module")
def tally():
    srv, port = fake_tally.start()
    yield TallyClient("127.0.0.1", port, timeout=5)
    srv.shutdown()


def _local(tmp_path, name="local.db", actor="op1@pc1"):
    eng = make_local_engine(f"sqlite:///{tmp_path / name}")
    return local_sessionmaker(eng, actor)()


# ---------------------------------------------------------------- Tally
def test_ping_and_companies(tally):
    assert tally.ping()
    comps = tally.companies()
    assert comps == [{"name": "Demo Traders Pvt Ltd", "guid": "abc-123-guid", "formal_name": "",
                      "books_from": "20250401", "state": "Gujarat", "gstin": "24AAACD1234F1Z5", "pan": ""}]


def test_ledgers_cleaned_and_gstin(tally):
    leds = {l["name"]: l for l in tally.masters("ledger", "Demo Traders Pvt Ltd")}
    assert "ABC Stationers" in leds                     # &#4; stripped
    assert leds["ABC Stationers"]["data"]["_gstin"] == "24ABCPS1234K1Z2"
    assert leds["Input CGST"]["parent"] == "Duties & Taxes"


def test_stock_hsn(tally):
    items = tally.masters("stock_item", "Demo Traders Pvt Ltd")
    assert items[0]["data"]["_hsn"] == "4802"


def test_voucher_dr_cr(tally):
    v = tally.vouchers("Demo Traders Pvt Ltd", "20251101", "20261111", ["journal"])[0]
    dr = [e for e in v["entries"] if e["dr"]]
    cr = [e for e in v["entries"] if not e["dr"]]
    assert [e["ledger"] for e in dr] == ["Office Rent"]
    assert sum(float(e["amount"]) for e in dr) == sum(float(e["amount"]) for e in cr) == 60000


def test_voucher_request_has_filters_and_dates():
    x = rq.vouchers_request("Demo", "20251101", "20261111", ["purchase", "journal"])
    assert '<SVFROMDATE TYPE="Date">1-Nov-2025</SVFROMDATE>' in x and "$$IsPurchase:$VoucherTypeName" in x
    assert "NOT $IsCancelled" in x


def test_import_response(tally):
    r = tally.import_vouchers("Demo", ["<VOUCHER/>"])
    assert r["created"] == 1 and r["errors"] == 0 and r["last_vch_id"] == "457"


def test_amount_parsing():
    assert parsers.amount("1,180.00 Dr") == -1180
    assert parsers.amount("-500") == -500
    assert parsers.amount("") == 0


def test_udf_namespace_prefixes_parse():
    raw = (b'<ENVELOPE><BODY><DATA><COLLECTION><LEDGER NAME="Rent" RESERVEDNAME="">'
           b'<GUID>x</GUID><UDF:VATDEALERNATURE.LIST DESC="`VATDealerNature`" ISLIST="YES" TYPE="String" INDEX="10">'
           b'<UDF:VATDEALERNATURE DESC="`VATDealerNature`">Regular</UDF:VATDEALERNATURE>'
           b'</UDF:VATDEALERNATURE.LIST></LEDGER></COLLECTION></DATA></BODY></ENVELOPE>')
    recs = parsers.parse_masters(raw, "ledger")
    assert recs[0]["name"] == "Rent" and recs[0]["guid"] == "x"


def test_malformed_voucher_reply_is_repaired_or_salvaged():
    raw = (b"<ENVELOPE><BODY><DATA><COLLECTION>"
           b"<VOUCHER><GUID>a</GUID><DATE>20261001</DATE><NARRATION>Paid to R & S Traders <urgent></NARRATION>"
           b"</VOUCHER><VOUCHER><GUID>b</GUID><DATE>20261002</DATE><NARRATION>ok</NARRATION></VOUCHER>"
           b"</COLLECTION></DATA></BODY></ENVELOPE>")
    vs = parsers.parse_vouchers(raw)
    assert [v["guid"] for v in vs] in (["a", "b"], ["b"])
    assert any(v["narration"] == "ok" for v in vs)
    amp = parsers.parse_vouchers(raw.replace(b" <urgent>", b""))
    assert amp[0]["narration"] == "Paid to R & S Traders"


def test_cp1252_bytes_in_reply():
    raw = b"<ENVELOPE><VOUCHER><GUID>c</GUID><NARRATION>Rent Oct\x96Nov\xa0paid</NARRATION></VOUCHER></ENVELOPE>"
    assert parsers.parse_vouchers(raw)[0]["narration"].startswith("Rent Oct")


def test_gstin_checksum():
    assert parsers.gstin_valid("24AAACL1234F1Z5")
    assert not parsers.gstin_valid("24AAACL1234F1Z6")       # wrong check digit
    assert not parsers.gstin_valid("24AAACL1234F1X5")       # 14th char must be Z


def test_company_gstin_from_gst_registrations(tally):
    found, raws = tally.company_gstins("Aarohan", "24")
    assert found[0] == "24AAACL1234F1Z5" and "27AAACL1234F1ZZ" in found
    assert "gst_registrations" in raws


def test_months_back_same_day():
    from app.tally.sync_masters import _months_back
    assert _months_back(date(2026, 10, 27), 12) == date(2025, 10, 27)
    assert _months_back(date(2026, 3, 31), 1) == date(2026, 2, 28)


def test_sync_fills_missing_gstin_and_counts_types(tally, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    s = _local(tmp_path)
    info = {**tally.companies()[0], "gstin": ""}
    rep = sync_company(s, tally, info, today=date(2026, 11, 11))
    assert rep.gstin == "24AAACL1234F1Z5" and "2 GST registrations" in rep.gstin_note
    assert rep.period == ("20251111", "20261111")
    assert rep.vouchers_by_type == {"Journal": 1}
    assert rep.vouchers_by_month == {"202610": 1}
    # a voucher outside the requested window is dropped even if Tally sends it
    rep = sync_company(s, tally, info, today=date(2026, 10, 27))
    assert rep.vouchers == 0
    assert (tmp_path / "AccountingAssistant" / "diagnostics").exists()


def test_unreachable_tally():
    with pytest.raises(TallyError, match="not reachable"):
        TallyClient("127.0.0.1", 1, timeout=2).companies()


# ---------------------------------------------------------------- masters sync
def test_sync_company(tally, tmp_path):
    s = _local(tmp_path)
    info = tally.companies()[0]
    rep = sync_company(s, tally, info, today=date(2026, 11, 11))
    assert rep.counts["ledger"] == 3 and rep.counts["stock_item"] == 1 and rep.vouchers == 1
    comp = s.scalar(select(Company))
    assert comp.gstin == "24AAACD1234F1Z5" and comp.tally_guid == "abc-123-guid"
    assert s.scalar(select(func.count()).select_from(VoucherHistory)) == 1
    # re-sync replaces, doesn't duplicate
    sync_company(s, tally, info, today=date(2026, 11, 11))
    assert s.scalar(select(func.count()).select_from(MasterCache).where(MasterCache.kind == "ledger")) == 3


def test_orphaned_rule_flagged(tally, tmp_path):
    s = _local(tmp_path)
    info = tally.companies()[0]
    rep = sync_company(s, tally, info)
    s.add(MappingRule(company_id=rep.company_id, vendor_key="X", target_name="Deleted Ledger"))
    s.add(MappingRule(company_id=rep.company_id, vendor_key="Y", target_name="Office Rent"))
    s.commit()
    rep = sync_company(s, tally, info)
    assert rep.orphaned_rules == ["Deleted Ledger"]
    assert s.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "rule_orphaned")) == 1


# ---------------------------------------------------------------- outbox + offline sync
def test_outbox_and_two_pc_sync(tmp_path):
    remote_eng = make_remote_engine(f"sqlite:///{tmp_path / 'master.db'}")
    Remote = sessionmaker(bind=remote_eng, expire_on_commit=False)
    pc1, pc2 = _local(tmp_path, "pc1.db", "op1@pc1"), _local(tmp_path, "pc2.db", "op2@pc2")

    # PC1 works offline: creates company + a rule
    c = Company(tally_guid="g1", name="Demo")
    pc1.add(c); pc1.commit()
    pc1.add(MappingRule(company_id=c.id, vendor_key="24ABCPS1234K1Z2", target_name="Printing & Stationery"))
    pc1.commit()
    assert pc1.scalar(select(func.count()).select_from(Outbox)) == 2

    # back on LAN: push, then PC2 pulls
    r1 = sync(pc1, Remote(), "op1@pc1")
    assert r1.pushed == 2
    sync(pc2, Remote(), "op2@pc2")
    rule2 = pc2.scalar(select(MappingRule))
    assert rule2.target_name == "Printing & Stationery"

    # PC2 edits later -> wins over PC1's stale copy
    rule2.target_name = "Office Expenses"
    pc2.commit()
    sync(pc2, Remote(), "op2@pc2")
    sync(pc1, Remote(), "op1@pc1")
    assert pc1.scalar(select(MappingRule)).target_name == "Office Expenses"
    # pulled rows must not re-queue into PC1's outbox
    assert pc1.scalar(select(func.count()).select_from(Outbox).where(Outbox.pushed_at.is_(None))) == 0


# ---------------------------------------------------------------- company lock
def test_company_lock(tmp_path):
    s = _local(tmp_path)
    locks.acquire(s, "c1", "op1@pc1")
    with pytest.raises(locks.LockHeld):
        locks.acquire(s, "c1", "op2@pc2")
    assert locks.heartbeat(s, "c1", "op1@pc1")
    # stale lock can be taken over
    from app.db.models import CompanyLock
    s.get(CompanyLock, "c1").heartbeat_at = utcnow() - timedelta(minutes=10)
    s.commit()
    assert locks.acquire(s, "c1", "op2@pc2").holder == "op2@pc2"
    locks.release(s, "c1", "op2@pc2")
    assert s.get(CompanyLock, "c1") is None
