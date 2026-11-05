# Miles2Collect: n8n workflow source (three workflows, n8n Cloud)

The app (Miles2Collect.html) calls three n8n webhooks. Each checks a shared token first, then does one job. The token and the Gemini/Gmail credentials are NOT included here. In your own n8n, create the credentials and set a fresh token (the same string goes in the app under Demand Workflow > Letterhead and n8n connection). The webhook paths still read `slab2cash-...` because the project was renamed after they were created; the path is just a label.

Design rule for all three: AI reads and suggests. Fixed rules in the app verify every number. A person approves.

## 1. Certificate AI Reader
Status: rebuilt and published in the new n8n account (hjsaccts.app.n8n.cloud), workflow "Miles2Collect - Certificate AI Reader".

Webhook (POST) `/webhook/slab2cash-certificate-ai` -> Prepare Input (Code: token check, text check, prompt build) -> IF input valid (else respond with is_certificate=false and the reason; wrong token = HTTP 401) -> Basic LLM Chain (Anthropic Claude Sonnet 5, structured output parser, max 1500 tokens) -> Format Response (Code: sanitises types and dates) -> Respond to Webhook (JSON).

Input from the app: `action` ("extract_certificate"), `token`, `project`, `schedule` (the company payment schedule), `text` (text of the architect certificate read by pdf.js in the browser; first 15,000 characters are used).

System prompt (summary): read ONLY the certificate text; use null for anything not stated; dates YYYY-MM-DD; percentages without the % sign; stage_pct = % of agreement value for this milestone, cumulative_pct = total entitlement after it; is_certificate is true when the document is in the form of a milestone work-completion certificate (project, milestone, completion date, percentage), EVEN IF marked SAMPLE / DEMO / unsigned (such markings go in notes); false for any other document; signed only if a signature is stated; confidence = accuracy of reading, not genuineness; flag anything a reviewer should check in notes; the schedule is context only and values must not be copied from it.

Output schema: `{ is_certificate, project, milestone, milestone_name, stage_pct, cumulative_pct, completion_date, certificate_ref, architect, signed, confidence, notes }`.
The app compares this reading with its own rule-based reading and with the schedule, so a wrong or out-of-sequence certificate is still blocked by the app's checks. Confidence measures reading accuracy, not correctness.

## 2. Demand Letters Automation (demand invoices and overdue reminders)
Status: rebuilt, published and live-tested in the new n8n account as "Miles2Collect - Demand Letters Automation" (Gmail OAuth2 attached to the "Send Demand Email" node; a demand e-mail with the PDF letter was sent and received in an approved test inbox on 05-Nov-2026).

Webhook (POST) `/webhook/slab2cash-demand-letters` -> Validate and Filter (Code: token check, demo-safety filter on the recipient address) -> Respond to Webhook immediately with `{ok, batchId, received, queued[], skipped[], message}` (HTTP 401 for a wrong token; an empty `demands` list is the app's connection ping and returns ok) -> IF anything to send -> Split Out -> Convert to File (PDF from pdfBase64) -> Gmail "send message" (HTML body plus PDF attachment, sender name from the letterhead).

Input from the app: a batch of demands, each with `to`, `flat`, `subject`, `html`, `fromName`, `fileName`, `pdfBase64`.
The demo-safety filter allows only the two configured test inboxes and their +aliases. Remove or edit it to go live.

## 3. Narration Matcher (AI help for unmatched bank receipts)
Status: rebuilt and published in the new n8n account (hjsaccts.app.n8n.cloud), workflow "Miles2Collect - Bank Receipt AI Matching".

Webhook (POST) `/webhook/slab2cash-narration-ai` -> Prepare Input (Code: token check, validation, prompt build) -> IF input valid (else respond with matched=false and the reason; wrong token = HTTP 401) -> Basic LLM Chain (Anthropic Claude Sonnet 5, structured output parser, max 600 tokens) -> Format Response (Code: guards) -> Respond to Webhook (JSON).

Input from the app: `action` ("match_narration"), `token`, `project`, `narration`, `amount`, `date`, `flats` (each: `flat`, `customer`, `openDemands`). The token is read from the body; an `x-api-key` header is also accepted. The token is stored in the Prepare Input node and is not included in this ZIP.

System prompt:

> You are a receivables clerk for an Indian real-estate developer. Match ONE bank receipt narration (NEFT/RTGS/IMPS/UPI/cheque text) to exactly one flat from the supplied flat list.
> Rules:
> - Choose ONLY a flat value that appears in the supplied list, copied exactly. Never invent a flat.
> - Use flat numbers written in any form (A-101, A101, A/101, Flat 101, wing/floor/unit), the payer or customer name (allow initials, spelling variants, joint holders), and the amount if the list gives an expected demand or instalment.
> - If two or more flats are plausible and nothing separates them, return flat as an empty string with low confidence and say why.
> - If nothing supports a match, return an empty flat and confidence 0.
> - confidence is 0 to 1: 0.9+ means a flat number and name both agree; 0.6 to 0.89 means one strong signal; below 0.6 means a guess.
> - reason: one short sentence naming the evidence used.

User message: Project / Bank narration / Credit amount (INR) / Receipt date / Flats with customer names and open demands (JSON).

Output: `{ matched, flat, confidence, reason, suggestion }`. `suggestion` is the best candidate when confidence is below 0.60 (the app ignores it).
Guards: (n8n) a flat that is not in the supplied list is discarded; matched=true only at confidence 0.60 or more. (app) a flat outside the sold-flat list is discarded; below 70% confidence there is no Accept button; nothing is applied until the Accountant clicks Accept, and the acceptance is logged.

## Setup in your own n8n
1. Create credentials: Gmail OAuth2 (demand letters). The two AI workflows use Anthropic Claude (n8n gateway credits or your own Anthropic API key); no Gemini key is needed.
2. Create the three workflows with the nodes above, set the same token in each "Valid Token?" node, and publish them.
3. In the app: Demand Workflow > Letterhead and n8n connection > paste the three webhook URLs and the token. Keep "Dry run" ticked until you want real emails.
4. Rotate the token after the capstone.
