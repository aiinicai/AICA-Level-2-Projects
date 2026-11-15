# 2. Essential decisions for the owner (only what blocks work)

Please reply with the decision number and your choice (e.g. "D1: A"). My recommendation is marked ★.

| # | Decision | Choice / Status | Needed before |
|---|---|---|---|
| D1 | **OTP SMS budget.** Google's official price for a Firebase OTP SMS to India is **US$0.07 (~₹6) per SMS**. | **CONFIRMED: Option A** - Use Firebase OTP for the pilot with hard daily SMS cap and billing alerts; switch to DLT-registered Indian provider before national launch. | Phase 2 (Resolved) |
| D2 | **Monthly budget alert amounts.** | **CONFIRMED: ₹2,000 / month** | Phase 2 (Resolved) |
| D3 | **Final age rule.** | **CONFIRMED: Option A** - Simple "I confirm I am 18 years or older" attestation checkbox. | Phase 2 (Resolved) |
| D4 | **Domain name** (e.g. careers.vrscorporate.in) – must be registered in the company's name. | Your domain | Phase 9 (staging can use the free *.web.app address) |
| D5 | **Mandatory-certification vacancies:** what happens when a non-certified candidate applies? | A ★ Accept but clearly mark "DRA not established" for recruiters. B: Block the application with a friendly message. | Phase 5 |
| D6 | **Contact-form email sender.** | A ★ Company Google Workspace / Microsoft 365 mailbox via SMTP app password stored in Secret Manager. B: Transactional email service (e.g. SendGrid/Brevo/Amazon SES). | Phase 7 |
| D7 | **Legal reviewer** for DPDP privacy notice, consent text, retention periods, grievance officer, processors and cross-border data. | Name of lawyer/firm | Before pilot (Phase 8) |
| D8 | **Data retention**: how long to keep inactive profiles / closed accounts / audit logs. | ★ Proposal: inactive profiles reminded at 12 months, deleted at 24 months; closed accounts deleted within 30 days except legally required records; audit logs 3 years – **subject to legal review** | Phase 8 |
| D9 | **Malware scanning of uploads.** | A ★ Pilot: strict type/size/magic-byte checks + staff open files only via signed links; add ClamAV on Cloud Run before national launch. B: ClamAV from day one (more cost/complexity). | Phase 3 |

Nothing else is blocking. All other details (wording, colours, course content) can be changed later in the admin screens.
