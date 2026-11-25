"""Executes the whole V3 Streamlit UI (Home, every workflow step, legal sources, settings) against the real
services through tests/ui_harness.py. Fails on any Python error in the UI, any call to an endpoint that does
not exist, any request body the API schema rejects, or any server-side error."""
import re

from noticemate.services import auth, cases, documents, issues, notices

from .conftest import sample
from .ui_harness import CALLS, harness, run

STEPS = ["upload", "confirm", "issues", "reconcile", "research", "draft", "approve"]
PAGES = ["🏠 Home", "📋 Cases & dashboard", "📂 Case workspace", "📚 Legal sources", "🛠️ Settings"]


def _seed(users):
    ca, staff = users["ca"], users["staff"]
    c = cases.create_case(ca, case_ref="UI-SMOKE", assessee_name="PQR Traders", assessee_category="FIRM", pan="AAAFP1234Z",
                          assessment_year="2026-27", party_names=["Amit Verma"])
    cases.add_member(ca, c["id"], staff["id"])
    d = {n: documents.upload(ca, c["id"], f"ui_{n}", sample(n)) for n in
         ("notice_143_2_PQR.docx", "bank_statement_PQR.xlsx", "bank_book_PQR.xlsx", "cash_book_PQR.xlsx", "sales_ledger_PQR.xlsx",
          "ais_PQR.xlsx", "debtor_ledger_PQR.xlsx")}
    n = notices.create_from_document(ca, d["notice_143_2_PQR.docx"]["id"])
    issues.generate_from_notice(ca, n["id"])
    return c


def _no_bad_calls():
    server_errors = [c for c in CALLS if c[2] == 404 or (isinstance(c[2], int) and c[2] >= 500)]
    assert not server_errors, server_errors
    schema_errors = [c for c in CALLS if c[2] == "SCHEMA"]
    assert not schema_errors, schema_errors


def test_ui_all_pages_and_steps(users):
    case = _seed(users)
    cid = case["id"]
    with harness() as st:
        CALLS.clear()
        run(st)  # login page
        assert any("NOTICE-MATE" in r for r in st.rendered)
        run(st, {"Username": "ca.sharma", "Password": "Ca!Passw0rd123", "Sign in": True})
        assert st.session_state.get("token"), st.errors
        for page in PAGES:
            st.session_state["nav"] = page
            run(st)
            assert not [e for e in st.errors if "not reachable" in e], st.errors

        # Home: notice-first intake with the scanned PDF
        st.session_state["nav"] = "🏠 Home"
        st.script = {}
        run(st, {"__files__": type("F", (), {"name": "scan.pdf", "getvalue": lambda self: sample("notice_143_2_PQR_scanned.pdf")})(),
                 "📨 Read the notice": True})
        assert ("POST", "/intake/notice", 200) in CALLS

        # Every workflow step on the seeded case, with the extra "more" tabs switched on
        st.session_state["nav"] = "📂 Case workspace"
        st.session_state["case_id"] = cid
        for s in STEPS:
            st.session_state[f"step_{cid}"] = s
            run(st, {f"Show more for this case — status, redaction terms, AI requests, 13-section analysis, audit history": True})
            assert not [e for e in st.errors if "not reachable" in e], (s, st.errors)

        # Reconciliation variants (step 4)
        st.session_state[f"step_{cid}"] = "reconcile"
        for kind in ["Bank statement vs bank book", "Bank book vs ledger", "Sales vs bank credits", "AIS/26AS vs books",
                     "Debtors vs receipts", "Cash book & cash availability", "Cash book vs sales ledger", "Custom transaction match",
                     "Financial statements tie-out"]:
            for k in [k for k in st.session_state if str(k).startswith("rk")]:
                st.session_state[k] = kind
            run(st, {"Run": True, "Match": True, "Compare": True, "Test chronology & availability": True})
        run(st, {"Party name": "Amit Verma", "Amount (₹)": 150000.0, "Date (YYYY-MM-DD)": "2025-12-20", "Save record": True})

        # Step 5: add a source, a proposition, link a source; record decisions; AI research note
        st.session_state[f"step_{cid}"] = "research"
        run(st, {"Title (case name, section heading, circular subject) *": "Fictional test provision (UI)",
                 "Official link (https://…gov.in / …nic.in for primary sources)": "https://incometaxindia.gov.in/fictional-ui-test",
                 "Add source": True})
        run(st, {"Proposition (one legal or factual point the reply would rely on)": "UI test proposition", "Add proposition": True})
        run(st, {"Link source": True})
        run(st, {"Link fact": True, "Fact type": "ASSUMPTION", "Basis": "ASSUMPTION", "Note": "UI assumption"})
        run(st, {"Record decision": True, "Decision": "NEEDS_CA_REVIEW"})
        run(st, {"Record proposition decision": True, "Decision": "NEEDS_CA_REVIEW"})
        run(st, {"Research question": "Which Act applies and how are cash credits examined?", "Create research note": True})

        # Steps 6–7 and the AI gate
        st.session_state[f"step_{cid}"] = "draft"
        run(st, {"✍️ Write the reply": True})
        run(st, {"📋 Generate client information request": True})
        st.session_state[f"step_{cid}"] = "approve"
        run(st, {"Section": "Q1", "Comment": "Attach the cash book.", "Add comment": True})
        run(st, {"Show changes": True})
        st.session_state[f"step_{cid}"] = "issues"
        run(st, {"Show more for this case — status, redaction terms, AI requests, 13-section analysis, audit history": True,
                 "Text to analyse (only this text — documents are never attached)": "PQR Traders received Rs 1,50,000 from Amit Verma.",
                 "🔒 Prepare & preview (nothing is sent)": True})
        run(st, {"Show more for this case — status, redaction terms, AI requests, 13-section analysis, audit history": True,
                 "I have reviewed the exact payload above and approve sending it to the AI provider.": True, "🚀 Approve & send": True})
        run(st, {"Show more for this case — status, redaction terms, AI requests, 13-section analysis, audit history": True,
                 "⚙️ Build local analysis (no AI, no network)": True})

        # Library and settings
        st.session_state["nav"] = "📚 Legal sources"
        run(st, {"Class": "PRIMARY", "Status": "UNVERIFIED"})
        st.session_state["nav"] = "🛠️ Settings"
        run(st, {"Test connection": True})
        assert any("OCR" in r for r in st.rendered)

        # STAFF view
        tok = auth.login("staff1", "Staff!Pass123")
        st.session_state["token"], st.session_state["user"] = tok["token"], tok["user"]
        st.session_state["nav"] = "📂 Case workspace"
        for s in STEPS:
            st.session_state[f"step_{cid}"] = s
            run(st)
            assert not [e for e in st.errors if "not reachable" in e], (s, st.errors)
        for page in ["🏠 Home", "📚 Legal sources", "🛠️ Settings"]:
            st.session_state["nav"] = page
            run(st)

        _no_bad_calls()
        print("domain validation responses:", sorted({c for c in CALLS if c[2] in (400, 403, 409, 422)}))
        covered = {(m, re.sub(r"/\d+", "/{id}", p)) for m, p, _ in CALLS}
        print(f"{len(covered)} distinct endpoints exercised")
        assert len(covered) >= 55, sorted(covered)
        for must in [("POST", "/intake/notice"), ("GET", "/cases/{id}/workflow"), ("GET", "/issues/{id}/trace"),
                     ("POST", "/legal-sources"), ("POST", "/cases/{id}/propositions"), ("POST", "/propositions/{id}/sources"),
                     ("POST", "/propositions/{id}/facts"), ("POST", "/propositions/{id}/decision"),
                     ("POST", "/legal-sources/{id}/decision"), ("GET", "/system/ocr-health"),
                     ("POST", "/ai/submissions/{id}/send"), ("POST", "/cases/{id}/research"), ("POST", "/cases/{id}/parties"),
                     ("POST", "/cases/{id}/analysis/local"), ("POST", "/drafts/{id}/comments"), ("POST", "/cases/{id}/recon/ais-vs-books")]:
            assert must in covered, must


def test_ui_delete_case_confirmation(users):
    ca = users["ca"]
    keep = cases.create_case(ca, case_ref="UI-KEEP", assessee_name="Fictional Keep", assessee_category="FIRM")
    gone = cases.create_case(ca, case_ref="UI-GONE", assessee_name="Fictional Gone", assessee_category="FIRM")
    with harness() as st:
        CALLS.clear()
        run(st, {"Username": "ca.sharma", "Password": "Ca!Passw0rd123", "Sign in": True})
        st.session_state["nav"] = "📋 Cases & dashboard"
        st.session_state["case_id"] = keep["id"]  # the active case differs from the one being deleted
        st.session_state["case_delete_pending"] = {"id": gone["id"], "ref": "UI-GONE", "name": "Fictional Gone"}
        run(st)
        assert any("Permanently delete case" in r and "UI-GONE" in r for r in st.rendered)
        run(st, {"I understand that case UI-GONE will be deleted permanently": True, "Delete UI-GONE permanently": True})
        assert ("POST", f"/cases/{gone['id']}/delete", 200) in CALLS
        _no_bad_calls()
        assert st.session_state.get("case_id") == keep["id"]
    ids = [c["id"] for c in cases.list_cases(ca)]
    assert gone["id"] not in ids and keep["id"] in ids
