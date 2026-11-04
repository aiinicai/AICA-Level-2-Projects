# Vouchr — AI (Gemini): what's built, how truth is enforced, what's pending

Status 2 Nov 2026: everything below is built and unit-tested. **None of it has run against the real Gemini API yet**, because there is no key. Connect one with [GEMINI-SETUP.md](GEMINI-SETUP.md); the engagement-letter wording is in [ENGAGEMENT-AI-CLAUSE.md](ENGAGEMENT-AI-CLAUSE.md).

## The truth rules (non-negotiable) — enforced by code, not by trusting the AI
Code: `supabase/functions/_shared/ai/truth.ts`, tested in `src/lib/ai-truth.test.ts`.

1. Every value comes back as a fact: **value + certainty (certain / uncertain / not found) + the exact quote it was read from**.
2. The prompt carries strict rules: use only the input; no guessing, rounding or "correcting"; any doubt is marked; no judging anyone by name, community, region, language, gender or size.
3. Code then re-checks every answer and **downgrades** anything that fails to "uncertain", with the reason. It never upgrades. Checks include:
   - GSTIN check digit, PAN format, real dates, valid amounts;
   - taxable + GST = total;
   - the quote must really appear in the bill text, transcript, narration or notice;
   - heads, TDS codes, vendors and projects must come from *our* lists;
   - any number in AI-written text must exist in our data.
4. Screens fill a field only from facts that passed everything. Anything doubtful shows in amber with the reason and a **Use** button — a person decides.
5. Figures (TDS thresholds, Ask-your-data answers, MIS numbers) are **calculated by the app**, never by AI.
6. Every call is logged with tokens used, and there is a daily cap per client.

## Built (A–J plus the original three)
| # | Feature | Where | Key safeguard |
|---|---|---|---|
| A | Read any bill, incl. handwritten / Hindi | Add expense → **Read with AI** | Fills only checked facts; GSTIN check digit; totals must add up; buyer's own GSTIN rejected |
| B | Hindi / English voice entry | Add expense → **Speak the expense** | Shows the transcript; every fact must be quoted from it; "kal" (yesterday/tomorrow) is always marked unsure |
| C | GSTR-2B mismatch → supplier message | GST reco → **Ask supplier** | The app computes the difference; numbers not in our records are flagged; you send it yourself |
| D | Bank narration → vendor | Bank statement → **Suggest vendors with AI** | Only our vendors; the quote must be in that narration; never matched on amount; rows stay unticked |
| E | Tally narration | Review → **Write narration** | Rejected if it contains any number not on the bill |
| F | HSN/SAC + GST rate | Review → **Suggest HSN** | A code not printed on the bill is always "suggestion — verify"; rate must be valid for the bill date (GST 2.0) |
| G | Ask your data | **Ask your data** page | AI only maps the question to fixed queries; filters shown and editable; the answer is calculated by the app |
| H | MIS notes for the owner | MIS → **Write with AI** | AI may only write `{figure}` placeholders; any digit it writes drops the point |
| I | Tax notice reader | Compliance → **Read a tax notice** | Every action needs a quote; quotes checked against the PDF text; "not legal advice" |
| J | Duplicate / look-alike bills | Bill risk check → **Possible duplicate bills** | Free on-device photo fingerprint first; AI "same bill" accepted only with two quoted matches and no difference |
| — | Invoice analysis (CA review) | Review → **AI check** | Head and TDS only from our masters; the app computes mismatches with what staff typed |
| — | Rule-change scan | Compliance → **AI scan for rule changes** | Marked unless a government site, notification number and effective date are all present; filed for CA review, masters untouched |
| — | Bill risk check (11 rules, no AI) | Bill risk check | Works offline, free |

## Facts behind the setup (from Google's pages, 31 Oct–2 Nov 2026)
- **Gemini Pro subscription ≠ API.** API calls need a billing-enabled project.
- **Use the paid tier only.** Google says free-tier content is used to improve its products; paid-tier content is not.
- **Default model:** `gemini-3.8-flash`. Paid price $0.75 in / $3.75 out per 1M tokens until 31 Dec 2026, then $1.50 / $7.50.
- **Search grounding** (rule-change scan): 5,000 queries/month free, then $14 per 1,000.
- **Cost per bill: not measured yet.** It will be read from `ai-dev-log.jsonl` after testing with your key.

## Live test on your free-tier key (2 Nov 2026, dummy data only)
| Task | Result |
|---|---|
| Model speed | `gemini-3.8-flash`: 35–60 s, often "high demand" or time-outs. `gemini-3.5-flash-lite`: 1–5 s. Both models are now set to flash-lite in `.env.local`. |
| A Read bill (image) | All 11 fields correct, 3 s, about 1,500 input + 600 output tokens |
| Altered bill (total changed) | The AI said "certain"; **the app's arithmetic check downgraded it** ("differs by ₹220") ✓ |
| J Same bill twice / different bill | "same" with 4 quoted points ✓ / "different", quoting SH/1182 vs SH/1190 ✓ |
| CA review | Head ✓, SAC ✓, the app caught the typo total 2,630 vs 2,360 ✓ |
| I Tax notice | Ref, date, section, due date and action ✓. The amount was cut off in the test image; **AI said "cut off, shows only Rs. 4" instead of guessing** ✓ |
| C, D, E, H | Correct. Hindi and wording fixes applied after the first run |
| F HSN | First run looked like the AI put 4802 on the wrong line. It was my 0/1 numbering, not the AI: both models counted lines from 1. Fixed with an explicit line number; a skipped line is now reported |
| G Ask your data | First run gave Jul–Sep for "this quarter" (wrong). Now the AI only names the period and **the app supplies the dates** ✓ |
| Rule-change scan (search) | **Not available on the free tier** — Google answered 429 "quota exceeded". Needs billing |
| B Voice | Not tested here (needs a microphone). Try "Speak the expense" on the Add expense screen |

## Known limits
- AI notes written by Gemini itself, e.g. why a value is unsure, come in English; the app's own reasons are bilingual.
- A fresh photo of the same bill taken from another angle may not be caught by the photo fingerprint.
- The Search-grounding response fields and the structured-output field names follow Google's generateContent reference. They must be confirmed with the first real call.

## Compression and n8n
Unchanged from v0.5:
- **Compression:** photos are compressed after reading, PDFs are never re-saved.
- **n8n:** not needed — Supabase cron + Edge Functions cover it.
