# Connecting Gemini to Vouchr — step by step

Checked 2 Nov 2026 against Google's pages: API keys, billing, plans and pricing. Button names may shift slightly.

## Before you start
- **Your Gemini Pro (Google AI Pro) subscription does not pay for API calls.** Google's plans page says API use is billed separately. You need a project with **billing set up**.
- **Without billing the key is on the free tier.** There, Google may use what you send to improve its products. Never use the free tier for client bills.
- **Use a Google account the firm controls**, not a personal one.

## Steps
| # | Where | What to click / do |
|---|---|---|
| 1 | aistudio.google.com | Sign in. Accept the terms if asked. New users get a default project and key automatically. |
| 2 | Left menu → **Dashboard → Projects** | Rename the project to `vouchr-ai`, or create a new one. Use **Import projects** for an existing Google Cloud project. |
| 3 | **API Keys** page | Choose the `vouchr-ai` project → **Create API key**. If the button is greyed out, your account lacks permission (needs Project Editor). |
| 4 | Same row → **Add restrictions** | Choose **Restrict to Gemini API only** → **Restrict key**. |
| 5 | API Keys or Projects page → **Set up billing** (Billing Tier column) | Pick or create a Cloud Billing account and add a payment method. Choose Prepay (minimum $5) or Postpay. |
| 6 | **Billing** page | Confirm the project shows a paid tier. Google says this usually appears within about 10 minutes. |
| 7 | **Spend** → Monthly spend cap → **Edit spend cap** | Start low, e.g. $10/month. Google marks this experimental; it can overshoot for about 10 minutes. |
| 8 | Your computer | Copy `.env.local.example` to `.env.local` in the Vouchr folder. Open it in Notepad and paste the key after `GEMINI_API_KEY=`. Save. **Never paste the key in chat, e-mail or WhatsApp.** |
| 9 | Tell me "key added" | I restart the app and test A–J with dummy bills. Token use goes to `ai-dev-log.jsonl`, which gives the real cost per bill. |
| 10 | In Vouchr | Each user turns AI on in **Privacy & consent** (DPDP — AI is opt-in). A client admin can switch it off for the whole company. |

## Testing on the free tier first (allowed — dummy data only)
- Skip steps 5–7. In `.env.local` keep `GEMINI_TIER=free`.
- Every AI panel then shows an amber "FREE tier — dummy data only" warning.
- The live server refuses to run AI unless `GEMINI_TIER=paid`, so real client data can't go out on the free tier by mistake.
- When you commercialise: set up billing, then change it to `GEMINI_TIER=paid`.

## Live (later)
- You run `supabase secrets set GEMINI_API_KEY=…` yourself.
- The app build gets `VITE_AI_ENABLED=true`.
- The key then lives only on the server.

## If the key leaks
1. Create a new key.
2. Put it in `.env.local` (or Supabase secrets).
3. Check that AI works.
4. Delete the old key.
