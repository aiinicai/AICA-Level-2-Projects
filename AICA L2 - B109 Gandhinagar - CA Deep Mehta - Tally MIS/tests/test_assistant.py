"""Phase 7: the assistant never calculates, stays on the company's data by default, and only talks to this PC."""
import json
import sys
from pathlib import Path

import httpx
import pytest

from app.assistant import facts as F
from app.assistant import lmstudio as L
from app.assistant.service import GENERAL_LABEL, REFUSAL, Assistant
from app.engine import reports as R
from app.model.store import Store
from app.sync import Runs, import_files

DATA = Path(__file__).parent / "data"


@pytest.fixture(scope="module")
def filters():
    store = Store()
    cid = store.ensure_company("Demo")
    runs = Runs()
    for n in ("masters.xml", "daybook-2024-04.xml", "daybook-2024-05.xml"):
        assert import_files(store, runs.new(company_id=cid, mode="file"), cid, [str(DATA / n)]).status == "succeeded"
    yield R.make_filters(store, cid, "2024-04-01", "2024-05-31", "none")
    store.wipe()


def fake_lm(replies, seen=None, models=("google/gemma-4-e2b",)):
    """A pretend LM Studio. `replies` is a list of answers returned in order for chat calls."""
    it = iter(replies)

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": m} for m in models]})
        body = json.loads(req.content)
        if seen is not None:
            seen.append(body)
        return httpx.Response(200, json={"choices": [{"message": {"content": next(it)}}]})
    return httpx.Client(transport=httpx.MockTransport(handler))


def make(replies, **kw):
    seen = kw.pop("seen", None)
    return Assistant(client=fake_lm(replies, seen), persist=False)


def revenue_text(f):
    return next(x for x in F.build_facts(f) if x.startswith("Revenue from operations"))


def test_indian_grouping():
    assert F.inr(18127955.66) == "₹1,81,27,955.66" and F.inr(-1234.5) == "-₹1,234.50" and F.inr(0) == "₹0.00"


def test_facts_come_from_the_engine(filters):
    facts = F.build_facts(filters, "who owes the most")
    assert any("Net profit" in x for x in facts) and any(x.startswith("Customer owes us —") for x in facts)
    assert facts[1].startswith("Period: 2024-04-01 to 2024-05-31")


def test_reply_with_only_known_numbers_is_shown(filters):
    rev = revenue_text(filters).split(": ")[1].split(" (")[0]
    a = make([f"Revenue was {rev} for the period."])
    r = a.chat("What is the revenue?", filters)
    assert r["kind"] == "company" and rev in r["answer"] and r["facts"]


def test_invented_number_is_withheld(filters):
    a = make(["Revenue grew by 17.3% to ₹9,99,999.00 this period."])
    r = a.chat("What is the revenue?", filters)
    assert r["kind"] == "warning" and "17.3" in r["unmatched"] and "Revenue grew" not in r["answer"] and r["facts"]


def test_the_model_is_given_the_figures_and_told_not_to_calculate(filters):
    seen = []
    a = make(["I don't have that in the open company's data."], seen=seen)
    a.chat("What is the gross margin?", filters)
    sys_msg, user = seen[0]["messages"][0]["content"], seen[0]["messages"][1]["content"]
    assert "Never calculate" in sys_msg and "FACTS:" in user and "Gross margin" in user
    assert seen[0]["temperature"] == 0
    assert seen[0]["reasoning_effort"] == "none"  # no minutes-long "thinking" before the answer


def test_company_only_by_default(filters):
    a = make(["NO"])  # no finance word in the question, so the model is asked "is this about the company?"
    r = a.chat("Who won the football world cup?", filters)
    assert r["kind"] == "refused" and r["answer"] == REFUSAL


def test_general_questions_are_labelled_when_allowed(filters):
    a = make(["NO", "France won in 2018."])
    a.update({"allowGeneral": True})
    r = a.chat("Who won the football world cup?", filters)
    assert r["kind"] == "general" and r["label"] == GENERAL_LABEL and "France" in r["answer"] and not r["facts"]


def test_finance_words_skip_the_classifier(filters):
    seen = []
    a = make(["ok"], seen=seen)
    a.chat("Explain the net profit", filters)
    assert len(seen) == 1  # only the answer call, no yes/no call


def test_lm_studio_not_running_is_explained():
    def boom(req):
        raise httpx.ConnectError("refused")
    c = httpx.Client(transport=httpx.MockTransport(boom))
    s = L.status(L.DEFAULT_URL, L.DEFAULT_MODEL, c)
    assert not s.online and "LM Studio is not running" in s.message
    a = Assistant(client=c, persist=False)
    store = Store()
    cid = store.ensure_company("x")
    r = a.chat("Explain the net profit", R.make_filters(store, cid))
    assert r["kind"] == "offline" and "not running" in r["answer"]
    store.wipe()


def test_missing_model_is_explained():
    s = L.status(L.DEFAULT_URL, "google/gemma-4-e2b", fake_lm([], models=("other/model",)))
    assert s.online and not s.model_loaded and "other/model" in s.message


@pytest.mark.parametrize("url", ["http://example.com/v1", "http://192.168.1.5:1234/v1", "https://api.openai.com/v1", "ftp://localhost/v1"])
def test_only_this_pc_can_be_contacted(url):
    with pytest.raises(L.AssistantError):
        L.check_local(url)
    with pytest.raises(L.AssistantError):
        Assistant(persist=False).update({"baseUrl": url})


def test_local_addresses_are_accepted():
    for u in ("http://localhost:1234/v1", "http://127.0.0.1:1234/v1/", "http://[::1]:1234/v1"):
        assert L.check_local(u).startswith("http")


def test_number_checker_ignores_list_markers_but_not_numbers():
    facts = ["Revenue: ₹1,000.00 (actual)"]
    assert F.unmatched_numbers("1. Revenue ₹1,000.00\n2. Costs fell", facts, "") == []
    assert F.unmatched_numbers("Revenue ₹1,200.00", facts, "") == ["1200.00"]


def test_thinking_blocks_are_removed_and_empty_replies_explained(filters):
    a = make(["<think>hmm</think>Net profit is fine."])
    assert a.chat("Explain the net profit", filters)["answer"] == "Net profit is fine."
    r = make([""]).chat("Explain the net profit", filters)
    assert r["kind"] == "offline" and "thinking" in r["answer"]
