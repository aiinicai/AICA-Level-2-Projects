"""Tests. Run from the project folder:   python -m unittest discover -s tests -v

The LLM is replaced by a scripted fake, so these tests need NO API key and verify
the tool-calling loop logic (tool schemas, tool execution, fallback behaviour).
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd

import app as M

ENABLED = [f.__name__ for f in M.ALL_TESTS]


def tool_call_msg(calls):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": f"call_{i}", "type": "function",
         "function": {"name": n, "arguments": json.dumps(a)}} for i, (n, a) in enumerate(calls)]}


class FakeGrok:
    """Scripted stand-in for the LLM: list -> inspect -> record -> DONE."""
    def __init__(self):
        self.round, self.ids, self.tool_results = 0, [], []

    def chat(self, messages, tools=None):
        self.round += 1
        if self.round == 1:
            return tool_call_msg([("list_flagged_journals", {"limit": 10})])
        if self.round == 2:
            self.ids = [j["JE_ID"] for j in json.loads(messages[-1]["content"])]
            return tool_call_msg(
                [("get_journal_lines", {"je_id": i}) for i in self.ids[:3]]
                + [("get_user_activity", {"user": "admin"}),
                   ("get_account_variance", {"account_code": "5200"}),
                   ("no_such_tool", {})])
        if self.round == 3:
            self.tool_results = [m["content"] for m in messages if m.get("role") == "tool"]
            return tool_call_msg([("record_finding", {
                "je_id": i, "risk_level": "CRITICAL", "procedures": ["Vouch to support"],
                "assessment": f"LLM assessment for {i}"}) for i in self.ids])
        return {"role": "assistant", "content": "DONE"}


class TestDetectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = M.load_and_clean(M.generate_sample_ledger())
        cls.flags = M.run_all_detectors(cls.df)

    def n(self, test):
        return self.flags[self.flags["Test"] == test]["JE_ID"].nunique()

    def test_planted_anomalies_found(self):
        self.assertEqual(self.n("Weekend posting"), 4)
        self.assertEqual(self.n("Duplicate entry"), 5)
        self.assertEqual(self.n("Just below approval limit"), 4)
        self.assertGreaterEqual(self.n("Round-number amount"), 7)

    def test_control_tests_find_planted_failures(self):
        self.assertGreaterEqual(self.n("Override without approval / self-approval"), 8)
        self.assertGreaterEqual(self.n("After-hours posting"), 5)
        self.assertEqual(self.n("Back-dated / future-dated entry"), 2)
        self.assertEqual(self.n("Debit-credit imbalance"), 1)
        self.assertEqual(self.n("Rare user large entry"), 1)

    def test_control_tests_skipped_without_optional_columns(self):
        raw = M.generate_sample_ledger().drop(columns=["Posting_Time", "Approved_By", "Override", "Entry_Date"])
        flags = M.run_all_detectors(M.load_and_clean(raw))
        tests = set(flags["Test"])
        for t in ("Override without approval / self-approval", "After-hours posting", "Back-dated / future-dated entry"):
            self.assertNotIn(t, tests)
        self.assertIn("Weekend posting", tests)

    def test_variance_flags_known_spikes(self):
        v = M.monthly_variance(self.df)
        flagged = set(zip(v[v.Flag]["Account_Name"], v[v.Flag]["Month"]))
        self.assertIn(("Rent Expense", "2025-01"), flagged)
        self.assertIn(("Salaries & Wages", "2025-02"), flagged)

    def test_missing_column_rejected(self):
        with self.assertRaises(ValueError):
            M.load_and_clean(pd.DataFrame({"JE_ID": [1]}))


class TestAgents(unittest.TestCase):
    def setUp(self):
        self.df = M.load_and_clean(M.generate_sample_ledger())
        self._orig = (M.is_enabled, M.supports_tools, M.chat, M.ask)

    def tearDown(self):
        (M.is_enabled, M.supports_tools, M.chat, M.ask) = self._orig

    def test_offline_mode(self):
        M.is_enabled = lambda: False
        M.supports_tools = lambda: False
        res = M.run_pipeline(self.df, ENABLED, {}, "Co", "FY25", "Auditor")
        self.assertEqual(len(res["findings"]), len(res["detector"]["scores"]))
        self.assertTrue((res["findings"]["Analysed_By"] == "Rules").all())
        self.assertEqual(res["letter"]["source"], "Template")

    def test_llm_tool_calling_loop(self):
        fake = FakeGrok()
        M.is_enabled = lambda: True
        M.supports_tools = lambda: True
        M.chat = fake.chat
        M.ask = lambda *a, **k: "Dear Board, " + "x" * 300
        res = M.run_pipeline(self.df, ENABLED, {}, "Co", "FY25", "Auditor")
        f = res["findings"]
        self.assertEqual((f["Analysed_By"] == "LLM tool-calling").sum(), 10)
        self.assertEqual((f["Analysed_By"] == "Rules").sum(), len(f) - 10)     # rest by rules
        self.assertIn("LLM assessment for", f.iloc[0]["Narrative"])
        self.assertEqual(res["letter"]["source"], "LLM")
        self.assertTrue(any("unknown tool" in r for r in fake.tool_results))  # bad tool handled
        self.assertTrue(any("tool calls" in a for a in res["log"]["Action"]))

    def test_llm_failure_falls_back(self):
        M.is_enabled = lambda: True
        M.supports_tools = lambda: True
        M.chat = lambda *a, **k: None          # API down / bad key
        M.ask = lambda *a, **k: None
        res = M.run_pipeline(self.df, ENABLED, {}, "Co", "FY25", "Auditor")
        self.assertEqual(len(res["findings"]), len(res["detector"]["scores"]))
        self.assertTrue((res["findings"]["Analysed_By"] == "Rules").all())
        self.assertEqual(res["letter"]["source"], "Template")


class TestRetry(unittest.TestCase):
    """chat() must survive a malformed-tool-call 400 and a rate limit, then succeed."""

    def test_retry_then_success(self):
        import requests
        os.environ.update(LLM_PROVIDER="groq", GROQ_API_KEY="x")
        calls = {"n": 0}

        class Resp:
            def __init__(self, code): self.status_code, self.text = code, '{"error":"tool_use_failed"}'
            def raise_for_status(self):
                if self.status_code != 200: raise requests.HTTPError("err", response=self)
            def json(self): return {"choices": [{"message": {"role": "assistant", "content": "fine"}}]}

        def post(*a, **k):
            calls["n"] += 1
            return Resp([400, 429, 200][calls["n"] - 1])

        orig = (M.requests.post, M.time.sleep)
        M.requests.post, M.time.sleep = post, lambda s: None
        try:
            msg = M.chat([{"role": "user", "content": "hi"}], M.TOOL_SCHEMAS)
        finally:
            M.requests.post, M.time.sleep = orig
            os.environ.pop("LLM_PROVIDER"); os.environ.pop("GROQ_API_KEY")
        self.assertEqual(calls["n"], 3)
        self.assertEqual(msg["content"], "fine")


class TestRateLimitEndToEnd(unittest.TestCase):
    """Fake Groq over HTTP: rate-limits (429 with a 'try again in' hint), then tool calls, then a letter."""

    def test_pipeline_through_http_with_rate_limits(self):
        import requests
        os.environ.update(LLM_PROVIDER="groq", GROQ_API_KEY="x")
        sleeps, state = [], {"post": 0, "round": 0, "ids": []}

        class Resp:
            def __init__(self, code, body=None, text=""):
                self.status_code, self._b, self.text = code, body, text
            def raise_for_status(self):
                if self.status_code != 200: raise requests.HTTPError("err", response=self)
            def json(self): return self._b

        def msg(m): return Resp(200, {"choices": [{"message": m}]})

        def post(url, headers=None, json=None, timeout=None):
            state["post"] += 1
            if state["post"] in (1, 4):                       # two rate limits during the run
                return Resp(429, text='{"error":{"message":"Rate limit reached. Please try again in 2.5s."}}')
            if not json.get("tools"):                          # the letter request (no tools)
                return msg({"role": "assistant", "content": "Dear Board, " + "findings " * 60})
            state["round"] += 1
            if state["round"] == 1:
                return msg({"role": "assistant", "content": None, "tool_calls": [
                    {"id": "a", "type": "function", "function": {"name": "list_flagged_journals", "arguments": "{\"limit\": 4}"}}]})
            if state["round"] == 2:
                import json as J
                state["ids"] = [j["JE_ID"] for j in J.loads(json["messages"][-1]["content"])]
                return msg({"role": "assistant", "content": None, "tool_calls": [
                    {"id": f"r{i}", "type": "function", "function": {"name": "record_finding", "arguments":
                     J.dumps({"je_id": i, "risk_level": "CRITICAL", "assessment": f"LLM view {i}", "procedures": ["Vouch"]})}}
                    for i in state["ids"]]})
            return msg({"role": "assistant", "content": "DONE"})

        orig = (M.requests.post, M.time.sleep)
        M.requests.post, M.time.sleep = post, lambda s: sleeps.append(s)
        try:
            df = M.load_and_clean(M.generate_sample_ledger())
            res = M.run_pipeline(df, ENABLED, {}, "Co", "FY25", "Auditor", 4)
        finally:
            M.requests.post, M.time.sleep = orig
            os.environ.pop("LLM_PROVIDER"); os.environ.pop("GROQ_API_KEY")
        self.assertIn(3.5, sleeps)                             # waited the provider's 2.5s hint + 1s
        self.assertEqual((res["findings"]["Analysed_By"] == "LLM tool-calling").sum(), 4)
        self.assertEqual(res["letter"]["source"], "LLM")
        self.assertTrue(any("4 findings recorded" in a for a in res["log"]["Action"]))

    def test_wait_hint_parsing(self):
        class E:  # minimal stand-in for requests' HTTPError with a response
            def __init__(self, text): self.response = type("R", (), {"text": text})()
        self.assertAlmostEqual(M._retry_wait(E("try again in 10.59s"), 0), 11.59)
        self.assertAlmostEqual(M._retry_wait(E("try again in 1m2.5s"), 0), 63.5 if 63.5 < 45 else 45.0)
        self.assertEqual(M._retry_wait(E("no hint"), 1), 4.0)


class TestParseFailure(unittest.TestCase):
    """Groq 'output_parse_failed' (malformed tool call) -> retry with one tool call at a time."""

    def test_parallel_calls_switched_off_after_parse_failure(self):
        import requests
        os.environ.update(LLM_PROVIDER="groq", GROQ_API_KEY="x")
        seen = []

        class Resp:
            def __init__(self, code, text=""): self.status_code, self.text = code, text
            def raise_for_status(self):
                if self.status_code != 200: raise requests.HTTPError("err", response=self)
            def json(self): return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}

        def post(url, headers=None, json=None, timeout=None):
            seen.append(dict(json))
            return Resp(400, '{"error":{"code":"output_parse_failed"}}') if len(seen) == 1 else Resp(200)

        orig = (M.requests.post, M.time.sleep)
        M.requests.post, M.time.sleep = post, lambda s: None
        try:
            msg = M.chat([{"role": "user", "content": "x"}], M.TOOL_SCHEMAS)
        finally:
            M.requests.post, M.time.sleep = orig
            os.environ.pop("LLM_PROVIDER"); os.environ.pop("GROQ_API_KEY")
        self.assertEqual(msg["content"], "ok")
        self.assertNotIn("parallel_tool_calls", seen[0])
        self.assertIs(seen[1]["parallel_tool_calls"], False)


if __name__ == "__main__":
    unittest.main()
