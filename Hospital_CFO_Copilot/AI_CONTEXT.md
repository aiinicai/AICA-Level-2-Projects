# AI_CONTEXT.md
## Context for AI Agent — Hospital CFO Copilot

**Project:** Hospital CFO Copilot  
**Hardened Version:** V1.1  
**Firebase Project:** `central-sanctuary-32ts5`

---

## CRITICAL MANDATORY RULES

> [!CAUTION]
> These rules are absolute. Violating them breaks institutional security or financial integrity.

1. **DO NOT rebuild, simplify, or refactor the application.** The architecture is production-quality.
2. **DO NOT change `src/engine/controlEngine.ts` financial logic.** C01–C08 are deterministic and audited.
3. **DO NOT let AI calculate, invent, or modify financial values.** AI provides commentary and synthesis only.
4. **DO NOT introduce synthetic/demo/seed data** into production. `syntheticDataset.ts is a development/UAT fixture only and is not automatically loaded into production.`
5. **DO NOT add dashboards, features, or modules** unless explicitly requested.
6. **DO NOT remove or simplify the multi-agent orchestration** in `cfoFinancialReviewAgent.ts`.
7. **DO NOT reintroduce `Rajesh Menon`, `Sunita Rao`**, or any fabricated user identities.
8. **DO NOT use misleading terminology implying clinical or patient-release authority.** Do NOT use: Gate Pass, Financial Discharge Gate, Patient Release Control, Discharge Without Clearance. The application is a financial-control and revenue intelligence layer only. Describe departmental review as financial review and billing completeness associated with discharged encounters, not patient-release control.
9. **RBAC POLICY:** `Authenticated Google users without an authorised Firestore user profile are denied access.` Never default an unknown user to CFO or any privileged role. Roles come strictly from the Firestore user profile.
10. **DO NOT store financial data in `localStorage`.** Firestore is the authoritative store.

---

## Authentication & Authorization Model

```
Google Authentication (Firebase Auth)
        ↓
Firestore user profile lookup (/users/{uid} or /users/{email})
        ↓
Profile exists and authorized?
   YES → Load assigned role + department from Firestore profile
   NO  → ACCESS DENIED (Immediate signout + error message)
```

- **Bootstrap Account:** `rukminigopakumar@gmail.com` serves as the initial bootstrap administrative account when the application runs on a domain not yet added to Firebase Authorized Domains. Its privileges are governed by its Firestore profile.
- **Frontend Role Selection:** The application does NOT allow frontend users to self-assign or escalate roles.

---

## Financial Controls (C01–C08)

All financial metrics are computed strictly by deterministic engines:
- **C01** — Unbilled Service: Services delivered without corresponding billing lines
- **C02** — Qty Mismatch: Quantity mismatch between services and billing
- **C03** — Amount Mismatch: Billed amount deviates from contracted tariff
- **C04** — Post-Billing Svc: Service entered after initial bill generation
- **C05** — Missing Final Bill: Discharged encounters with unfinalized or provisional bills
- **C06** — TPA Shortfall: Insurance disallowances and adjudication shortfalls
- **C07** — Overdue Receivables: Outstanding receivables exceeding settlement terms
- **C08** — Unusual Discount: Concession or discount above authorised limits

---

## Multi-Agent Orchestrator
**File:** `src/services/cfoFinancialReviewAgent.ts`

10 specialist review stages:
1. `CONTROL_POSITION` — Overall control posture & C01–C08 summary
2. `REVENUE_REVIEW` — Billing completeness & capture rate
3. `EXCEPTION_REVIEW` — Material open financial exceptions
4. `RECEIVABLES_REVIEW` — AR ageing schedule & overdue exposure
5. `TPA_REVIEW` — Insurance claims adjudication & disallowances
6. `DEPARTMENT_REVIEW` — Departmental billing completeness review
7. `TARIFF_REVIEW` — Contracted tariff compliance & deviations
8. `BUDGET_REVIEW` — Budget vs actual operating variance
9. `FINANCIAL_SYNTHESIS` — Cross-stage evidence correlation & deduplication
10. `CFO_BRIEFING` — Executive markdown briefing with strict taxonomy

**Output Taxonomy:** `[FACT]` | `[CALCULATED METRIC]` | `[AI OBSERVATION]` | `[SUGGESTED ACTION]`
