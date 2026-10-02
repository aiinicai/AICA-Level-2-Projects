"""/api/v1/ai — AI invoice extraction proxy (Phase 4).

The Local Host uploads a purchase invoice PDF/image here; the server calls the AI
provider with its own key (never shared with Local Hosts) and returns structured
invoice data for human review. Planned endpoints:
    POST /api/v1/ai/invoices/extract     -> job id
    GET  /api/v1/ai/invoices/{job_id}    -> status + structured invoice
"""
from app.api._placeholder import placeholder_router

router = placeholder_router("ai", 4, "Server-side AI invoice extraction. Provider keys live only on the server.")
