"""V3 — query splitting: numbered queries win over an 'issues identified' summary; closing matter is cut."""
from noticemate.services.notice_parser import split_queries

NOTICE = """The issues identified are:
(a) Large cash deposits during the year; (b) Unsecured loans and other credits.
You are requested to furnish the following information:
1. Please explain the source of cash deposits aggregating Rs. 18,00,000 made in your bank
account during FY 2025-26, and furnish the cash book.
2. Please furnish details of capital introduced by partners in cash aggregating Rs. 3,00,000
and the source of such capital.
In case of failure to comply with this notice, the case may be proceeded under section 144.
Assessment Unit, Income Tax Department"""


def test_numbered_queries_only_and_footer_removed():
    q = split_queries(NOTICE)
    assert [x["label"] for x in q] == ["1", "2"]
    assert q[-1]["text"].endswith("source of such capital.")
    assert "In case of failure" not in q[-1]["text"]


def test_lettered_queries_still_work_alone():
    q = split_queries("(a) Please explain the source of the cash deposits in the bank account.\n"
                      "(b) Please furnish confirmations from the lenders of unsecured loans.")
    assert [x["label"] for x in q] == ["a", "b"]
