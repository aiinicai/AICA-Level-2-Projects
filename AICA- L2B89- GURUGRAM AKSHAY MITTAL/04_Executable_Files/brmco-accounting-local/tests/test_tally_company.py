"""Company period / Educational-mode checks before posting."""
from datetime import date

from app.accounting.models import Voucher, VoucherKind
from app.config.settings import AppConfig, EnvSettings
from app.services.tally_service import TallyService
from app.tally.client import CompanyInfo, parse_company_info

# Trimmed from a real TallyPrime reply (Educational mode).
REPLY = """<ENVELOPE><HEADER><VERSION>1</VERSION><STATUS>1</STATUS></HEADER><BODY><DESC><CMPINFO>
<COMPANY>1</COMPANY><LEDGER>16</LEDGER></CMPINFO></DESC><DATA><COLLECTION>
<COMPANY NAME="B R Maheswari &amp; Co LLP" RESERVEDNAME=""><STARTINGFROM TYPE="Date">20260401</STARTINGFROM>
<BOOKSFROM TYPE="Date">20260401</BOOKSFROM><NAME TYPE="String">B R Maheswari &amp; Co LLP</NAME>
<LICMODE TYPE="Logical">Yes</LICMODE></COMPANY></COLLECTION></DATA></BODY></ENVELOPE>"""


class FakeClient:
    def __init__(self, info):
        self.info = info

    def company_info(self):
        return self.info


def voucher(d: date, label="INV-1") -> Voucher:
    return Voucher(kind=VoucherKind.SALES, date=d, voucher_number=label)


def service() -> TallyService:
    return TallyService(EnvSettings(_env_file=None), masters=None, audit=None)  # type: ignore[arg-type]


def test_parse_company_info_skips_counter_element():
    [c] = parse_company_info(REPLY)
    assert c.name == "B R Maheswari & Co LLP"
    assert c.books_from == date(2026, 4, 1)
    assert c.educational_mode is True


def test_educational_mode_blocks_other_dates():
    client = FakeClient([CompanyInfo("X", date(2026, 4, 1), True)])
    cfg = AppConfig(demo_mode=False)
    msg = service().posting_problem(cfg, client, [voucher(date(2026, 9, 26), "INV-1026"), voucher(date(2026, 9, 1))])
    assert "Educational mode" in msg and "INV-1026 (26-09-2026)" in msg and "INV-1 " not in msg
    assert service().posting_problem(cfg, client, [voucher(date(2026, 8, 31)), voucher(date(2026, 9, 2))]) is None


def test_licensed_mode_and_books_from():
    client = FakeClient([CompanyInfo("X", date(2026, 4, 1), False)])
    cfg = AppConfig(demo_mode=False)
    assert service().posting_problem(cfg, client, [voucher(date(2026, 9, 26))]) is None
    msg = service().posting_problem(cfg, client, [voucher(date(2026, 3, 31))])
    assert "books begin on 01-04-2026" in msg
