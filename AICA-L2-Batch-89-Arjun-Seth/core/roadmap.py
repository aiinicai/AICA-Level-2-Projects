# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""The Future Roadmap: enhancements and developments that are planned or deliberately deferred.

Pure data - this is a write-up only; nothing listed here is built in the current version. ``today`` (optional) states,
factually, what the current build already does in that area, so the roadmap never overstates what is missing.
"""

ROADMAP_TITLE = "Future Enhancements and Developments"
ROADMAP_INTRO = (
    "The items below are the future roadmap of LeaseIQ Pro. They are planned or deliberately deferred, and none of them is "
    "built in the current version."
)

ROADMAP = [
    {
        "title": "OCR / Scanned Document Support",
        "summary": "Handling scanned, image-based lease agreements.",
        "note": "The current build only supports clean, text-based PDF and Word documents.",
        "today": None,
    },
    {
        "title": "Multi-Currency Support",
        "summary": "FX translation and remeasurement for leases denominated in a foreign currency.",
        "note": "Moved from the Enhanced Feature Set and deferred given the added complexity and the dependency on a paid FX-rate API.",
        "today": "Each lease already carries its own currency, and reports and the dashboard are produced one currency at a time. Amounts are never converted from one currency to another.",
    },
    {
        "title": "AI Chatbot / Q&A on the Lease (RAG-based)",
        "summary": "Conversational question-and-answer over the uploaded agreement, using embeddings and a vector store.",
        "note": "Moved from the Enhanced Feature Set and deferred: it needs a vector store and adds meaningful build complexity beyond the free-API, 10-day scope.",
        "today": None,
    },
    {
        "title": "IFRS 16 as a fully separate parallel engine",
        "summary": "A dedicated IFRS 16 calculation and reporting engine running alongside the others.",
        "note": "Documented as an extension, given the convergence of IFRS 16 with Ind AS 116.",
        "today": None,
    },
    {
        "title": "Lease impairment, sub-leases, and sale-and-leaseback accounting",
        "summary": "Accounting for impairment of right-of-use assets, sub-leases, and sale-and-leaseback transactions.",
        "note": None,
        "today": None,
    },
    {
        "title": "Multi-lease portfolio management and consolidation dashboards",
        "summary": "Managing many leases as a portfolio, with consolidation dashboards.",
        "note": None,
        "today": "The dashboard and the disclosure reports already summarise a portfolio of leases for one currency at a time.",
    },
    {
        "title": "Multi-tenant SaaS deployment, billing, and enterprise SSO",
        "summary": "Running LeaseIQ Pro as a multi-tenant hosted service, with billing and enterprise single sign-on.",
        "note": None,
        "today": None,
    },
    {
        "title": "ERP integration (SAP / Oracle / Tally) for automatic GL posting",
        "summary": "Posting the lease journal entries to the general ledger automatically.",
        "note": None,
        "today": None,
    },
    {
        "title": "Mobile application",
        "summary": "A native mobile app for LeaseIQ Pro.",
        "note": None,
        "today": None,
    },
    {
        "title": "Comparison mode (Ind AS 116 vs ASC 842)",
        "summary": "A side-by-side view of one lease under Ind AS 116 and ASC 842 - classification, lease liability, right-of-use asset and expense - with an explanation of where the two frameworks differ and why.",
        "note": None,
        "today": "Each lease's results screen already shows the schedules and journal entries of both frameworks, and the disclosure reports cover one framework at a time.",
    },
    {
        "title": "Lease amendments and version tracking",
        "summary": "Re-measuring a lease when its terms change (for example a modification, extension or termination), keeping the original untouched and linked to each new version, with a version history.",
        "note": "The data model already reserves a place for linking an amended lease to its original.",
        "today": "A rejected lease can be corrected and resubmitted; changing the terms of an approved lease and re-measuring it is not supported yet.",
    },
]
