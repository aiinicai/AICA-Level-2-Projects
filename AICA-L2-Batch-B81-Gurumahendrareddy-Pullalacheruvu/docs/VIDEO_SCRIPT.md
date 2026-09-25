# Video script — Cash Runway

**Target: 10 minutes. Spoken narration over a screen recording.**

Everything in `>` blockquotes is said aloud, written to be spoken rather than
read. Everything in *(brackets)* is what is on screen while you say it.

Word count is about 1,600, which is close to eleven minutes at a normal
speaking pace — so it has no slack. Read it once with a timer before recording.
If you run long, section 4 is where to cut — drop Scenarios and Capital & Debt
before you touch sections 1, 2 or 5.

**Audience:** the ICAI examiner, but also LinkedIn and colleagues. So the
first fifteen seconds have to earn attention from someone who is not a CA,
and terms like DSO get half a sentence of explanation the first time. It is
framed throughout as something you built to learn — never as a product anyone
should buy or adopt.

---

## 1 · The problem (0:00 – 1:00)

*(Start on a black slide or the login screen. Do not start on a spreadsheet.)*

> Profit is a view about timing. Cash is a fact about Friday.

*(Beat.)*

> A company can close a profitable quarter and be unable to make payroll six
> weeks later. Both are true at once, and neither is an accounting error.
> Revenue is recognised when the work is done; cash arrives when the customer
> decides to pay — sixty or ninety days later, if they pay on time at all.
>
> So the P&L looks fine right up until it stops mattering.
>
> Most finance teams handle this in a spreadsheet. It works, until someone asks
> where a number came from — and last month's version says something different.
>
> So the gap isn't "show me my cash". Every bank app does that. It's: *how long
> have I got, what changes it, and can I defend the answer when somebody pushes
> back on it?*

---

## 2 · What I set out to build (1:00 – 2:00)

*(Sign in. Land on Today, but don't start explaining screens yet.)*

> Cash Runway is a twelve-screen application, and each screen answers exactly
> one question. If the question can't be said in a sentence, it isn't a screen.
>
> Four rules run through the whole thing, and they're really the design.
>
> **First — no number without its basis.** "Burn is fifty-four lakh" is
> useless. "Net burn, three-month average, one-off items removed, as on the
> thirty-first of August" is a number I can say out loud in a board meeting.
>
> **Second — every number is traceable.** Click any figure and you get the
> ledger entries underneath it. A number you can't trace is a number you can't
> quote.
>
> **Third — colour means one thing.** Red is act this week. Amber is watch.
> Grey means the data is incomplete, don't rely on this. Never decorative.
>
> **Fourth, and this is the one I care most about — the tool has to be honest
> about itself.** When it doesn't know something, it says so, instead of
> showing you a confident zero.

---

## 3 · How it's built (2:00 – 3:15)

*(Optional: a simple architecture slide, or just keep the app on screen.)*

> The back end is Python — FastAPI, with SQLAlchemy over SQLite. Ninety-seven
> API endpoints across forty-six tables.
>
> SQLite gets raised as a limitation, so let me take it first. It's a single
> file — no database server, no connection string. For one finance team on one
> machine that's the right trade, and it means the whole thing starts with one
> command and no internet.
>
> The front end is React with Vite and Tailwind, charts in Recharts.
>
> Two integrations. **Tally Prime** — it speaks XML over HTTP on port nine
> thousand, so the app reads the day book and the ledger balances directly.
> Tally can't push, so the app polls, and it's blunt about how old the data is
> when a poll was missed. And **Twilio** for SMS alerts.
>
> The commentary on some screens — "Reading of the Position" — is written by
> the application itself, not by a language model. Conditional logic assembling
> sentences from figures already computed. Same inputs, same sentence, every
> time, and nothing leaves the machine.
>
> That's deliberate. In a finance tool reproducible beats eloquent — commentary
> you can't reproduce is commentary you can't defend. And it cannot invent a
> figure, because it never produces one; it only places numbers the calculation
> already worked out.
>
> It also knows when to stop. If confidence in the data is low it suppresses
> itself and lists the gaps instead. Silence beats confident narration on bad
> data.

*(Optional 20-second beat, only if you want it — this is an AI certification,
and how you built it is fair to mention:)*

> I built this with an AI assistant as a pair — I made the accounting and
> design decisions, and it wrote a lot of the code. Where that went wrong is
> in the limitations at the end.

---

## 4 · Walkthrough (3:15 – 8:45)

### 4a · What you need, and setting it up (3:15 – 4:30)

> Prerequisites are thin: Python, nothing else. No internet, no Node, no
> database to install.

*(Show `run.bat`, then the first-run screen.)*

> The first thing it asks is which data to load, because the two people who
> open this want opposite things. Load the demonstration company and every
> screen is populated. Or start empty and bring in your own.

*(Click into the set-up path briefly, then back.)*

> Set-up is staged, not one long form. Stage one is bank balances and three
> months of movement — and that alone gives a defensible runway number. You
> don't have to finish everything before the tool is useful.

*(Setup › Import data.)*

> You can type it or upload it. Upload a filled-in file and you get a row-by-row
> report — every rejected row, its row number, and what's wrong with it. Nothing
> is written until you accept that report.

*(Setup › Tally, show the four steps quickly, land on step 3.)*

> Or connect Tally. Four steps, and only the third one is interesting.

*(Point at the mapping table.)*

> This is where the numbers are decided. Every ledger arrives with the app's
> guess, and you confirm or change it. A confirmed row is never overwritten by
> a later sync. Real charts of accounts contain ledgers called "PROJ-B ADJ" —
> no classifier should be trusted to guess that, so the app asks.

### 4b · The screens (4:30 – 7:45)

*(Today.)*

> Today has to answer "am I fine" in five seconds without scrolling. Cash runs
> out on the twenty-second of April. Four point one seven crore available —
> and *available* is doing work there, because forty-five lakh of the balance
> is lien-marked against a bank guarantee. Burning fifty-four lakh a month.
> Seven point seven months of runway.

*(Point at the amber banner and a grey dot.)*

> And here's rule four in practice. Books and bank disagree by three point two
> lakh, so there's a banner, and every headline number carries a grey dot until
> that's explained. It would be easy to hide that. It's more useful not to.

*(Click "Cash Available" to open the drawer.)*

> Every figure opens to what's behind it — the accounts, the lien, and why it's
> restricted.

*(Runway & Burn.)*

> Burn, split into what's structural and what isn't. A one-off legal fee on a
> funding round isn't your run rate — leave it in and your runway looks shorter
> than it is. Both are shown, because which one you want depends on the question.

*(Money Coming In.)*

> What's owed to you, aged and weighted by whether it will actually arrive.
> DSO — days sales outstanding, the average time customers take to pay — is
> seventy-two days, and forty-two percent of the book is overdue. One client is
> thirty-six percent of it, which is a risk whether or not they pay on time.

*(Cash Calendar.)*

> Thirteen weeks forward, week by week. A monthly view hides the problem: money
> arrives on the twentieth and leaves on the fifth, so the month nets positive
> while week two is a hole.

*(Plan vs Actual, then Alerts.)*

> Plan against actual, with variance explained rather than just coloured.
>
> And alerts. Ten rules — runway below a floor, statutory dues unfunded, a
> client going quiet. They go out by SMS, with quiet hours, a cooldown, and
> escalation if nobody acknowledges.

*(Alerts tab — point at delivery status.)*

> Every attempt is recorded, including the failures. A tool that quietly stops
> alerting is worse than one that never alerted.

*(Board Pack.)*

> And the board pack. Ten minutes before a meeting it produces the cash story —
> and freezes it. When someone asks in March what you told the board in
> December, you open the December pack instead of reconstructing it.

### 4c · What it's actually for (7:45 – 8:45)

> So what does this buy you.
>
> A runway number you can defend line by line. The week you have a problem in,
> not the month. Alerts before it's a crisis. A board pack that doesn't take an
> afternoon.
>
> And the honest summary: a spreadsheet can do all of that. What it can't do is
> stay consistent across twelve views, tell you when it's stale, and show its
> working every time without you remembering to build that in.

---

## 5 · Limitations (8:45 – 9:45)

*(Back on Today, or a plain slide. Slow down here. Don't rush this section —
it's the one that shows judgement.)*

> Five things it doesn't do, or doesn't do yet.
>
> **One — the Tally connection.** It reads Tally properly, but I don't have a
> licensed one. Educational mode only accepts vouchers dated the first, second
> or thirty-first of a month, so most of my seventeen months of test data won't
> import. What you saw is a local stand-in speaking the same XML on the same
> port. The connector can't tell the difference — but I haven't tested against a
> production Tally, and I'm not going to claim I have.
>
> **Two — SMS in India needs registration I don't have.** The domestic route
> requires DLT registration with the operators — entity, sender ID, and every
> template approved in advance — and unregistered messages are dropped at the
> network with no error returned. The code is production-shaped. The account
> isn't production-registered.
>
> **Three — the app knows a message was accepted, not that it was read.**
> That needs a delivery webhook I haven't built, so it says "accepted" rather
> than "delivered". A small distinction that matters when you're relying on it.
>
> **Four — it isn't deployed anywhere.** It's a proper web application — four
> roles, sign-in, and the board account genuinely sees a different, filtered
> view of the same data. Several people can use it at once from their own
> devices over the office network. What it doesn't have is a server: no
> hosting, no domain, no HTTPS, and it only runs while someone has started it.
> A board member sitting at home can't reach it. That's a deployment job, not a
> rewrite — but it isn't done.
>
> **Five — and this is the one worth saying out loud.** I built this with AI
> assistance, and three bugs got all the way through that would only ever have
> shown in production. Tally's sign convention is backwards from the intuitive
> one, and it had been read the wrong way — every receipt would have been
> recorded as a payment. A save button called an API method that didn't exist,
> so the board visibility settings silently never saved. And the WhatsApp
> integration could never have worked, because Meta doesn't allow
> business-initiated messages without a pre-approved template.
>
> All three passed the tests. All three worked in demo mode. What caught them
> was building a fake Tally that behaved like the real one, and then reading
> what came back.
>
> That's the thing I'd take into any finance system: the test that matters is
> the one that fails the way production fails.

*(Beat.)*

> Twelve screens, one question each. Every number carries its basis, every
> number is traceable, and it tells you when not to trust it.
>
> That's Cash Runway. Thank you.

---

## Before you record

- [ ] **Load the demonstration company, not a Tally-synced entity.** The
      figures quoted in section 4b — ₹ 4.17 Cr, ₹ 54 L, 7.7 months, DSO 72 —
      are the seeded eighteen-month dataset. A Tally sync produces different
      numbers and the narration will not match what's on screen.
- [ ] `CR_ALERT_CHANNEL=console` unless the Twilio number is live
- [ ] Server up on http://localhost:8000, browser zoom at 100%
- [ ] Record at 1680×1050 or wider, or the top strip is cramped
- [ ] Signed in as the CFO account, not the board account
- [ ] Bookmarks bar hidden, no other tabs, notifications off
- [ ] Do the statutory earmark early so the activity log has something in it
- [ ] Read section 5 aloud once before recording — it's the densest minute

## Things not to say

- Don't call it production-ready. It runs, it's tested, it isn't deployed.
- Don't compare it to a tool your employer uses. This is a certification
  project you built to learn, and framing it as a replacement for anything
  in use at work invites a conversation you don't want.
- Don't quote a statistic about how many businesses fail from cash flow. The
  commonly cited ones don't survive checking, and one shaky number undermines
  a section built on defensible ones.
