DIGITAL ITR CONSULTANCY — EXECUTABLE WORKFLOW FILES (UPDATED)
=====================================================
Batch: AICA-L2B85, Chandigarh Branch

These five files are real n8n workflow exports (JSON), directly importable
into any n8n instance (n8n.cloud or self-hosted) via:

  n8n editor -> "..." menu (top right) -> Import from File

Import them in this order:

  1. 01_Intake_and_Dummy_Payment.json
  2. 02_Document_Intake_via_Email.json
  3. 04_ITR_Knowledge_Base_Ingestion.json
  4. 05_Tax_Knowledge_Base_Live_Search_Cache_Writer.json
  5. 03_Report_Generation_and_Approval.json

(03 is imported last because it references the workflow ID of 05 in its
"Cache Tax Info in Knowledge Base" tool node.)

WHAT'S NEW SINCE THE FIRST SUBMISSION
----------------------------
  - Two new workflows: an ITR Knowledge Base — Ingestion workflow (04) that
    embeds tax-law PDFs into a Supabase vector table, and a Live Search
    Cache Writer (05) that lets the AI Agent save content it verifies via
    live web search back into that same table — so the knowledge base
    grows on its own instead of staying a static, manually-curated library.
  - Workflow 03's AI Agent now has three tools instead of zero: a Knowledge
    Base search tool, a live web-search tool (Tavily, restricted to
    incometaxindia.gov.in / egazette.gov.in), and the cache-write tool
    above — used in that order before the agent states any numeric tax
    figure, with an explicit "UNVERIFIED: ..." flag if neither lookup
    confirms a figure.
  - The report is now split into two versions: a full, tabular version
    with all verification flags for the CA's review, and a shorter,
    flag-free plain-language version for the client.
  - Workflows 01 and 02 now collect and pass through PAN, Assessment
    Year, Financial Year, and six deduction amounts (80C, 80D,
    80TTA/80TTB, HRA, Section 24(b), 80CCD(1B)) so the AI can cross-check
    the client's declared figures against the actual uploaded document.
  - The AI Agent is capped at 6 reasoning iterations and instructed to
    make at most one combined tool call per source (rather than one call
    per tax figure), which cut a several-minute, 8-LLM-call report run
    down to a small, predictable number of calls and materially reduced
    token cost.

BUG FIXES SINCE THE PREVIOUS SUBMISSION
----------------------------
Found and fixed while re-testing the full pipeline live end-to-end:
  - Workflow 01's "Classify ITR Type" node now lowercases the client's
    email before writing it to the CRM. Previously, whatever casing the
    client typed was stored as-is, but workflow 02 always looks up the
    CRM row using a lowercased sender address -- a client who typed their
    email in mixed/upper case would silently get zero CRM matches, so
    their reply and attachments never reached the report-generation step
    at all, with no error anywhere in the chain.
  - Workflow 02's "Trigger Report Generation" node and workflow 03's
    "Cache Tax Info in Knowledge Base" node had both drifted to point at
    stale, non-existent workflow IDs from an earlier import (a common
    failure mode any time 02/03/05 are re-imported or re-linked) --
    re-pointed to the correct sub-workflows. If you ever see either of
    these calls fail with "workflow not found," re-copy the ID exactly as
    described in the SETUP section below.
  - Removed a leftover, invalid empty "builtInTools" parameter on
    workflow 03's OpenAI Chat Model node.
  - The "Build Agent Prompt" node's extracted-text cap was raised to
    40,000 characters (from 10,000) so longer, multi-document uploads
    aren't cut off before the AI Agent sees the later pages -- see
    Prompt_File.docx Section 6 for detail.

UPDATES FROM LIVE PRODUCTION TESTING (LATEST REVISION)
----------------------------
Found and fixed while running the full pipeline against a real client
reply and real uploaded documents (not test/pinned data):
  - Workflow 03's AI Agent now runs on Anthropic Claude Sonnet 5 instead
    of OpenAI GPT-5-mini. A new "Anthropic Chat Model" node feeds the
    "ITR Analysis Agent" node, configured with adaptive thinking mode,
    "low" effort, and a 12,000-token cap. It runs on n8n's own Gateway
    credits by default, so no separate Anthropic API key is required to
    import and run this workflow -- see SETUP below if you'd rather
    connect your own Anthropic API credential instead. The Knowledge
    Base's embedding step ("Tax KB Embeddings") is unchanged and still
    uses an OpenAI embedding model (Claude has no embeddings API); this
    is expected and needs no setup change.
  - Added a CRM-authoritative reconciliation step to workflow 03: three
    new nodes -- "Lookup Client in CRM," "Pick Most Recent CRM Match,"
    and "Reconcile Client Info with CRM" -- run immediately after the
    document is received and before the AI Agent prompt is built. They
    re-fetch the client's row from the CRM sheet and use it as the
    source of truth for name, PAN, DOB, and all six deduction amounts,
    overriding anything stale or mismatched that may have arrived in the
    hand-off payload from workflow 02. This is what fixed an issue where
    a generated report reflected an earlier or wrong client's details
    instead of the documents actually just submitted. Workflow 03 is now
    30 nodes (up from 27).
  - Reliability hardening: added automatic retry (2-3 attempts, with a
    short delay between attempts) to roughly 16 nodes across workflows
    02 and 03 -- every Gmail send, Google Sheets log, Google Drive
    upload/export, and AI Agent tool call (Knowledge Base search, Tavily
    live search, cache-write). A brief Google Drive rate-limit or network
    blip now retries automatically instead of failing the whole run.
  - Workflow 03's CA-facing email nodes ("CA Approval (Send and Wait)",
    "Notify Self — Needs Revision", "Send Editable Report to CA") now
    correctly use the YOUR_EMAIL@example.com placeholder described below
    -- they had drifted to a hardcoded address in the previous export.
  - IMPORTANT -- publish after every edit: n8n saves a change to a
    workflow's "draft" first; it does NOT take effect for real, trigger-
    based runs until you click Publish (top-right of the workflow editor)
    to make that draft the active version. After reconnecting credentials
    or changing any node below, publish workflows 02, 03, 04, and 05
    again before testing live.

SETUP REQUIRED AFTER IMPORT
----------------------------
Credentials and account-specific IDs are NOT included (for security) and are
marked with placeholder values you must replace after import:

  - REPLACE_WITH_YOUR_CREDENTIAL_ID  -> reconnect each Gmail / Google Sheets /
    Google Drive / OpenAI / Supabase / Tavily node to your own n8n
    credentials. (Tavily uses n8n's native "Tavily MCP OAuth2" credential
    type; Supabase uses the standard Supabase API credential with the
    project URL and service role key.)
  - The "Anthropic Chat Model" node (workflow 03) and the "Tax KB
    Embeddings" node have no credential of their own by default -- they
    run on n8n's shared Gateway credits automatically. This is fine for
    testing, but Gateway credits reset monthly and cannot be topped up,
    so for real production use, add your own Anthropic API credential
    (from console.anthropic.com) to the "Anthropic Chat Model" node once
    you're ready to rely on it long-term.
  - REPLACE_WITH_YOUR_PARENT_FOLDER_ID -> the Google Drive folder ID you want
    to use as the shared "ITR Client Uploads" parent folder.
  - REPLACE_WITH_YOUR_TAX_LAW_FOLDER_ID -> the Google Drive folder ID you
    want the Ingestion workflow (04) to watch for new tax-law PDFs.
  - REPLACE_WITH_YOUR_CRM_SHEET_ID -> the Google Sheet ID you're using as the
    CRM (must have a tab named INTAKE with columns: name, email, phone,
    itr_type, price_inr, classified_at, payment_status, paid_at,
    report_status, date_of_birth, submission_id, pan_number,
    assessment_year, financial_year, deduction_80c, deduction_80d,
    deduction_80tta_ttb, hra_amount, home_loan_interest_24b,
    deduction_80ccd_1b).
  - REPLACE_WITH_WORKFLOW_3_ID_AFTER_IMPORT (in workflow 02's "Trigger Report
    Generation" node) -> after importing workflow 03, copy its workflow ID
    from the browser URL and paste it here so workflow 02 can call it.
  - REPLACE_WITH_WORKFLOW_5_ID_AFTER_IMPORT (in workflow 03's "Cache Tax
    Info in Knowledge Base" node) -> after importing workflow 05, copy its
    workflow ID from the browser URL and paste it here.
  - YOUR_EMAIL@example.com -> replace with the CA's own inbox address in the
    approval / notification nodes.

You will also need a Supabase project with a pgvector-enabled
"tax_knowledge_base" table and a matching "match_documents" SQL function
(the standard n8n Supabase Vector Store setup) before running 03, 04, or 05.

WORKFLOW ROLES
----------------------------
  01 - Client-facing intake form + dummy payment simulation. Classifies
       ITR type (1-4) and emails the document checklist, now driven by
       the client's declared deduction amounts as well as their profile.
  02 - Watches the CA's inbox for client replies with attachments, files
       them into a per-client Drive folder, and hands off to workflow 03
       together with the client's declared PAN/AY/FY/deduction data.
  03 - Downloads the document, extracts text (with password fallback),
       reconciles client identity/deduction data against the CRM record,
       runs it through the AI Agent (Anthropic Claude Sonnet 5) with
       mandatory Knowledge-Base + live-search verification of tax
       figures, builds two report versions (CA-facing tabular,
       client-facing concise) in HTML + Word + PDF, and routes it
       through CA approval before emailing the client and logging
       status to the CRM.
  04 - Ingestion: watches (or backfills) a Google Drive folder of tax-law
       PDFs and embeds them into the Supabase knowledge base used by 03.
  05 - Cache Writer: a small sub-workflow the AI Agent in 03 calls to save
       newly live-searched, verified tax content back into the same
       knowledge base, so the same lookup is never needed twice.

Once credentials are reconnected and IDs replaced, activate workflows 02,
03, 04, and 05 (workflow 01 runs via its own Form trigger URL, shareable
with clients).
