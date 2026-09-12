# SMS alerts — Twilio

Alerts go out as SMS through Twilio. This is what to set up, and what to know
before promising anyone it will work in production.

---

## Why SMS and not WhatsApp

The first build used Meta's WhatsApp Cloud API. It could not have worked.

Meta accepts a free-form WhatsApp message only inside a **24-hour customer
service window**, and that window opens when *the recipient* messages the
business first. It closes 24 hours after their last reply. Outside it, only a
pre-approved template may be sent.

An alert is business-initiated by definition. It fires at 08:00 because runway
crossed nine months — nobody wrote in. So the window is always shut, and every
alert would have needed a template approved by Meta in advance.

That was fixable, but SMS is the better fit for this application: no window, no
per-message approval, and it reaches a phone with no app installed — which for
a CFO who wants to know about a payroll shortfall is the point.

---

## What SMS does not escape, in India

**DLT registration is mandatory on the domestic route.** To send transactional
SMS to Indian numbers through Indian operators you need, registered with a
TRAI-approved DLT platform:

| | |
|---|---|
| Principal Entity (PE) ID | your company, registered once |
| Sender header | a 6-character alphanumeric ID, approved |
| Content template | every message must match one, approved in advance |

There is no exemption for low volume or testing, and **unregistered messages
are dropped at the network with no error returned** — the API reports success
and nothing arrives. That is worth knowing before you trust a green tick.

**The international route does not need DLT.** Messages from a foreign
long code reach Indian handsets without registration, from an unbranded
number, subject to operator filtering. This is the route a Twilio trial
account uses, and it is what a demonstration runs on.

So the honest position for this project: **the code is production-shaped, the
account is not production-registered.** Say that rather than implying a
deployment-ready SMS pipeline.

---

## 1 · Twilio account

1. Sign up at twilio.com. A trial account is enough.
2. From the Console dashboard, copy the **Account SID** and **Auth Token**.
3. Get a phone number — trial accounts include one. Note it in E.164
   (`+15551234567`).

**A trial account only sends to verified numbers.** Console › Phone Numbers ›
Verified Caller IDs — add your own number and confirm the code. Without this,
every send returns Twilio error **21608**, which the app shows verbatim.

---

## 2 · Point the app at it

Set these before starting the server. On Windows, in the same terminal:

```
set CR_ALERT_CHANNEL=twilio
set CR_TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
set CR_TWILIO_AUTH_TOKEN=your_auth_token
set CR_TWILIO_FROM=+15551234567
```

macOS or Linux: `export` instead of `set`.

| Variable | Notes |
|---|---|
| `CR_ALERT_CHANNEL` | `twilio`, `console` or `n8n`. Default `twilio`. |
| `CR_TWILIO_ACCOUNT_SID` | starts `AC` |
| `CR_TWILIO_AUTH_TOKEN` | keep it out of screenshots |
| `CR_TWILIO_FROM` | your Twilio number, E.164 |
| `CR_TWILIO_MESSAGING_SERVICE_SID` | optional, starts `MG`. Wins over `FROM` when set — it is what carries a sender pool and compliance registration. |

---

## 3 · Prove it

**Setup › Alert rules › Send a test message.** Channel SMS, your verified
number in E.164, Send.

The result reports the transport, the character count and **how many SMS
segments** the message costs. A demonstration that hides the cost of its own
channel is not much of a demonstration.

What "delivered" means here: Twilio *accepted* the message. Delivery to a
handset is asynchronous, and without a status webhook the app cannot honestly
claim more. It does not pretend to.

---

## 4 · Demonstrating without an account

```
set CR_ALERT_CHANNEL=console
```

Every alert prints to the server terminal exactly as it would be sent, with
its segment count. Nothing is stubbed — the same `compose_sms()` builds the
same body; only the transport changes. This is the safe setting for recording
if the Twilio account is not ready.

---

## Message shape, and why it is plain

One SMS segment is 160 characters of the GSM-7 alphabet. **A single character
outside it — the rupee sign, an emoji, a typographic dash — switches the whole
message to UCS-2 and the segment drops to 70 characters.** A four-line alert
then costs six segments instead of two, and pays six times.

So the SMS body is transliterated before sending: `₹` becomes `Rs`, the
severity emoji are dropped, em-dashes become hyphens. The email body keeps all
of it — email has no such tax.

A typical alert:

```
Cash Runway - Northwind Robotics Pvt Ltd
RED: Runway below 9 months
Runway is 7.8 months against a 9.0 month floor.
At stake: Rs 4.17 Cr
As on 31-Aug-26.
```

203 characters, 2 segments.

The deep link is deliberately absent. It points at `localhost:8000`, which is
useless on a phone, and it would cost a segment to say so. The email carries
it instead.

---

## When it does not work

| Twilio error | What it means |
|---|---|
| **21608** | Trial account, unverified recipient. Add the number under Verified Caller IDs. |
| **21606** / **21659** | The `From` number cannot send SMS, or is not yours. Check `CR_TWILIO_FROM`. |
| **20003** | Authentication failed. Wrong Account SID or Auth Token. |
| **21211** | The `To` number is not valid E.164. It needs the `+` and country code. |
| **30007** | Carrier filtering — the likeliest symptom of the DLT position above when sending to India. |
| `SMS is not configured` | The app's own message: the SID or token is unset. |

The app shows Twilio's own sentence rather than a status code, because
Twilio's message names the unverified number or the unreachable region
outright.

---

## Recipients

Alert rules take a comma-separated list. Phone numbers in E.164 go to SMS,
addresses containing `@` go to email, and a rule may carry both. Escalation
recipients work the same way and are used only when nobody acknowledges within
the rule's window.

Rules written before this change say `whatsapp`. They are read as SMS, and
renamed once on the next start — nothing is lost.
