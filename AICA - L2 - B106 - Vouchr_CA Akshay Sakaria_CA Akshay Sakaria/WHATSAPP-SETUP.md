# WhatsApp bill intake — how it works and how to switch it on

Checked against Meta's WhatsApp Business Platform documentation on 2 Nov 2026. Prices come from third-party trackers, so confirm them on Meta's own rate card.

## How it works
1. An admin adds a staff member's mobile number in **Settings → Team → 💬 Add WhatsApp**.
2. That person opens Vouchr and confirms in **Privacy & consent → "Yes, this is my number"**.
3. They send a bill photo (JPG/PNG) or PDF to the firm's WhatsApp Business number.
4. Vouchr checks:
   - the number belongs to an active user whose number is confirmed;
   - the person and their company have a valid DPDP consent;
   - the file isn't a duplicate (same file already recorded for the client).
5. The file is saved in Drive (`Vouchr/<Client>/FY …/Bills/`) and a **draft** appears in that person's Inbox with "💬 via WhatsApp".
6. If the firm has the paid Gemini tier, and the user and company agreed to AI, the AI fills in the details. Only checked facts are used.
7. The sender gets a reply in English or Hindi.
8. Someone opens the draft, checks it and submits it. **Nothing goes to the CA queue without a person submitting it.**

**Unknown numbers** get a polite refusal. Nothing they send is stored.

## What you need (you do these; Meta requires the business owner)
| # | Step |
|---|---|
| 1 | A Meta Business account (business.facebook.com) for the firm |
| 2 | In Meta for Developers, create an app with **WhatsApp** added. You get a test number to try things out first. |
| 3 | A phone number for the firm's WhatsApp Business line. Meta's onboarding explains the rules for numbers already on the WhatsApp app. |
| 4 | A **permanent access token** (System User in Business Settings) with WhatsApp permissions |
| 5 | Webhook URL = the Supabase function `whatsapp-webhook` (once Supabase is live). Choose a verify token. Subscribe to **messages**. |
| 6 | Server secrets (Supabase): `WHATSAPP_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, optional `WHATSAPP_GRAPH_VERSION` (default v26.0) |
| 7 | Put the firm's WhatsApp number in **Privacy & consent → Firm WhatsApp number for bills**, so staff can see where to send bills |

## Cost (verify on Meta's rate card)
- **Receiving messages is free.**
- Replies to a user's own message are "service" messages. From 1 Oct 2026 the first 1,000 per number per month are free; after that, about the utility rate (≈ ₹0.115 + GST each, per trackers).
- Vouchr sends one reply per bill, so a firm receiving under ~1,000 bills a month per number should pay ₹0 for WhatsApp.

## Built-in safeguards
- Every delivery's signature is checked (HMAC-SHA256 with the app secret).
- Meta retries for up to 7 days, so each message ID is processed once.
- File size limit is 15 MB, the same as in the app. Only JPG, PNG and PDF are accepted.
- Every message is logged (`whatsapp_messages`) for audit.

## Not done yet
- **Not tested with Meta.** It needs your Meta app and number, plus Supabase live. Only the in-app simulator was tested.
- **No one-time-code check of numbers yet.** Number confirmation is self-confirmation inside the person's own login. A WhatsApp OTP check would be stronger, but it needs an approved message template and paid messages.
