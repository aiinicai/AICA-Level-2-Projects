"""Offline workflow examples; no fabricated legal research or client evidence."""
from services.case_models import DocumentNeed, DocumentPlan, Research, Strategy, IssueStrategy


def demo_plan(analysis):
    return DocumentPlan(
        documents=[DocumentNeed(name=d.text, issue="Relevant notice issue", purpose="Reconcile the notice with the underlying client records.", origin="Notice requested") for d in analysis.documents_requested] + [
            DocumentNeed(name="Filed return and relevant ledger extracts", issue="Interest income and deduction", purpose="Compare what was filed with the books; do not assume the difference is an omission.", origin="AI suggested")],
        public_research_topics=[
            "Indian income tax: evidentiary requirements for reconciling third-party interest information with a filed return; AY 2025-26. Find provisions and judgments both favorable and adverse to taxpayers.",
            "Indian income tax: burden of supporting a deduction when responding to a notice under section 142(1); AY 2025-26. Check the applicable law and factual distinctions; deduction type and jurisdiction remain unknown.",
        ],
    )


def demo_research():
    return Research(authorities=[], gaps=["Offline demonstration: no web searches were performed and no authorities are supplied.", "Favorable and adverse case law, applicable instruments and subsequent judicial treatment remain to be researched."], search_summary="Offline workflow preview only; not legal research.")


def demo_strategy(analysis, case):
    return Strategy(
        issues=[IssueStrategy(issue=i.title, established_facts=["The department's allegation is recorded in the notice; the taxpayer's explanation is not yet established."], evidence_references=[], missing_facts=["Verified client explanation and source records are required."], primary_position="Reconcile the allegation to verified records before asserting a factual position.", alternative_position="If records remain unavailable, consider a factually supported request for time; confirm portal procedure and deadline.", adverse_arguments_and_response="An unsupported assertion may not discharge the evidentiary burden. Obtain underlying records and address any discrepancy openly.", authorities_to_use=[]) for i in analysis.issues],
        procedural_checks=["Verify service, actual reply deadline, issuing authority, portal and applicable jurisdiction."],
        contradictions=["No taxpayer records have been reviewed in the offline example."],
        pre_filing_actions=["Complete placeholders; verify all amounts; research applicable law and both sides of case law; check final attachments."],
        overall_approach="Offline illustration: build a documentary reconciliation for each issue, identify unanswered facts, then settle the legal position. No legal authorities have been verified.",
    )
