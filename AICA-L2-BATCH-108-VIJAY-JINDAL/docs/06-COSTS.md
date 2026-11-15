# 6. Costs in simple words (check current prices before launch)

| Item | How it is charged | Notes |
|---|---|---|
| Firebase Hosting, Firestore, Storage, Functions | Pay per use on the Blaze plan; small free allowances each month | A pilot with a few hundred users usually costs little; nationwide traffic needs monitoring. |
| **Phone OTP SMS** | Google's official price for India: **US$0.07 per SMS sent**; first 10/day free; each resend is billed | Largest early cost. Controls: India-only SMS region, test numbers for staff, 60s resend delay, daily cap, App Check. Base Firebase Auth also has a daily SMS limit. |
| Gemini AI (optional) | Per request/token | Off by default. Daily total and per-candidate caps in admin settings. |
| Email for contact form | Free with existing company mailbox, or provider pricing | Decision D6. |
| Domain | Yearly registrar fee | Decision D4. |

Set budget alerts (Part C of owner steps) **before** turning on SMS or AI. Budgets warn; they do not stop spending.
