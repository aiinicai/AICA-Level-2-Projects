import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import nodemailer from 'nodemailer';
import { ImapFlow } from 'imapflow';
import { simpleParser } from 'mailparser';

const app = express();
app.use(cors());
app.use(express.json({ limit: '2mb' }));

const PORT = process.env.API_PORT || 5174;

// DEMO_EMAIL_MODE=true (the default) never talks to a real SMTP server -
// it just logs what *would* have been sent and reports back "SIMULATED",
// exactly like the old in-browser simulation did.
// Set DEMO_EMAIL_MODE=false once SMTP_HOST / SMTP_USER / SMTP_PASS are filled
// in to actually dispatch mail through Nodemailer.
const DEMO_MODE = String(process.env.DEMO_EMAIL_MODE ?? 'true').toLowerCase() !== 'false';

let transporter = null;

function getTransporter() {
  if (transporter) return transporter;
  const port = Number(process.env.SMTP_PORT) || 587;
  transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port,
    secure: port === 465, // true for port 465 (SSL), false for 587/others (STARTTLS)
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  });
  return transporter;
}

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, demoMode: DEMO_MODE });
});

// Real mail dispatch for the Quarterly Billing & Invoice Automation workflow.
// The frontend (src/lib/services/systemService.ts) posts confirmation and
// invoice emails here instead of only recording them to the local Email
// Outbox. Kept intentionally generic (to/subject/body) so it serves both the
// confirmation-request email and the invoice-dispatch email.
// Turns the plain-text body into a simple, clean HTML version. Sending a
// text-only email with no matching HTML part is one of the more common
// spam signals mail providers look at, so every real send goes out as a
// proper multipart (text + html) message instead.
function textToHtml(body, companyName) {
  const escaped = body
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return `<!doctype html>
<html>
  <body style="margin:0;padding:24px;background:#f8fafc;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
    <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:24px;">
      <p style="white-space:pre-line;line-height:1.6;font-size:14px;margin:0;">${escaped}</p>
      <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;" />
      <p style="font-size:11px;color:#94a3b8;margin:0;">
        This is a transactional billing notice from ${companyName || 'our Finance Team'}. If you weren't expecting
        this, you can safely ignore it.
      </p>
    </div>
  </body>
</html>`;
}

app.post('/api/send-email', async (req, res) => {
  const { to, subject, body, companyName, attachment } = req.body || {};

  if (!to || !subject || !body) {
    return res.status(400).json({ success: false, status: 'FAILED', error: 'Missing to/subject/body in request body.' });
  }

  if (DEMO_MODE) {
    console.log(`[DEMO MODE] Simulated email to ${to} — "${subject}"`);
    return res.json({ success: true, status: 'SIMULATED' });
  }

  if (!process.env.SMTP_HOST || !process.env.SMTP_USER || !process.env.SMTP_PASS) {
    return res.status(500).json({
      success: false,
      status: 'FAILED',
      error: 'SMTP is not configured. Set SMTP_HOST, SMTP_USER and SMTP_PASS in .env, or set DEMO_EMAIL_MODE=true to keep simulating.',
    });
  }

  const senderAddress = process.env.SMTP_SENDER || process.env.SMTP_USER;

  try {
    const info = await getTransporter().sendMail({
      // A display name + an address that matches the authenticated SMTP
      // account (rather than an unrelated "from") is one of the biggest
      // factors in avoiding spam folder placement.
      from: `"${companyName || 'Finance Team'}" <${senderAddress}>`,
      replyTo: senderAddress,
      to,
      subject,
      text: body,
      html: textToHtml(body, companyName),
      attachments:
        attachment && attachment.filename && attachment.content
          ? [{ filename: attachment.filename, content: Buffer.from(attachment.content, 'base64') }]
          : undefined,
    });
    console.log(`Email sent to ${to} — messageId ${info.messageId}`);
    return res.json({ success: true, status: 'SENT', messageId: info.messageId });
  } catch (err) {
    console.error('Failed to send email:', err.message);
    return res.status(500).json({ success: false, status: 'FAILED', error: err.message });
  }
});

// --- Real Inbox Reply Detection ---
// Checks the actual mailbox (via IMAP) for unseen replies from specific
// clients and looks for a confirming / rejecting reply, so the "client
// confirmed by email" step can be driven by a real, naturally-worded reply
// instead of requiring the literal word "CONFIRMED" and instead of only
// the manual "Simulate Client Confirmation" button.
//
// This is intentionally narrow: for each pending billing record the
// frontend sends us, we search ONLY for unseen mail FROM that exact client
// address - never a broad inbox scan - so nothing else in the mailbox is
// touched or marked read.
//
// Matching is phrase-based rather than a single fixed keyword, so a real
// reply like "Hi Finance team, We confirm the count and amount therein"
// is recognised as a confirmation. Negated confirmation language ("we do
// not confirm", "unable to approve") and explicit rejection wording are
// checked FIRST so a reply isn't misread as a confirmation just because it
// contains the word "confirm" inside a denial.
const NEGATED_CONFIRM_PATTERN =
  /\b(?:do\s+not|don't|does\s+not|doesn't|did\s+not|didn't|cannot|can't|will\s+not|won't|unable\s+to|not\s+able\s+to)\s+(?:confirm|agree|accept|approve)\b/i;

const REJECT_PATTERN =
  /\b(?:reject(?:ed|ing)?|disagree(?:d|ing)?|dispute(?:d|ing)?|discrepanc(?:y|ies)|incorrect|mismatch(?:ed)?|not\s+correct|does\s+not\s+match|do\s+not\s+agree)\b/i;

const CONFIRM_PATTERN =
  /\b(?:confirm(?:ed|ing|s)?|agree(?:d|s)?|approve(?:d|s)?|accept(?:ed|s)?|looks?\s+good|no\s+discrepanc(?:y|ies)|ok(?:ay)?\s+to\s+proceed)\b/i;

async function getImapClient() {
  const host = process.env.IMAP_HOST || 'imap.gmail.com';
  const port = Number(process.env.IMAP_PORT) || 993;
  const client = new ImapFlow({
    host,
    port,
    secure: true,
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
    logger: false,
  });
  await client.connect();
  return client;
}

app.post('/api/check-confirmations', async (req, res) => {
  const { pending } = req.body || {};

  if (DEMO_MODE) {
    return res.json({ checked: false, reason: 'Demo Mode is on - inbox is not checked.', confirmed: [], rejected: [] });
  }

  if (!process.env.SMTP_HOST || !process.env.SMTP_USER || !process.env.SMTP_PASS) {
    return res.json({
      checked: false,
      reason: 'SMTP/IMAP credentials are not configured in .env.',
      confirmed: [],
      rejected: [],
    });
  }

  if (!Array.isArray(pending) || pending.length === 0) {
    return res.json({ checked: true, confirmed: [], rejected: [] });
  }

  let client;
  const confirmed = [];
  const rejected = [];

  try {
    client = await getImapClient();
    const lock = await client.getMailboxLock('INBOX');
    try {
      for (const item of pending) {
        if (!item?.billingId || !item?.clientEmail) continue;

        // "since" is IMAP's SINCE search criterion, which most servers
        // (including Gmail) only compare at DAY granularity - it narrows the
        // search but is not enough on its own to exclude an old message from
        // earlier the same day. We use it purely to keep the search cheap,
        // then do the real, precise cutoff below with the message's actual
        // parsed Date header, so a stale unseen email from BEFORE this
        // specific confirmation-request was sent can never be picked up as
        // its reply, no matter how many hours old it is.
        const sinceDate = item.since ? new Date(item.since) : null;
        const searchQuery = { from: item.clientEmail, seen: false };
        if (sinceDate && !Number.isNaN(sinceDate.getTime())) {
          searchQuery.since = sinceDate;
        }

        const uids = await client.search(searchQuery, { uid: true });
        if (!uids || uids.length === 0) continue;

        for (const uid of uids) {
          const message = await client.fetchOne(uid, { source: true }, { uid: true });
          if (!message?.source) continue;

          const parsed = await simpleParser(message.source);

          // Precise cutoff: skip anything that isn't actually AFTER the
          // confirmation-request email was sent, regardless of what the
          // coarse IMAP "since" day-level filter let through.
          if (sinceDate && parsed.date && parsed.date.getTime() < sinceDate.getTime()) {
            continue;
          }

          const text = (parsed.text || parsed.html || '').toString();

          // Check negation/rejection wording BEFORE the confirm wording, so
          // "we do not confirm the count" isn't misread as a confirmation
          // just because it contains "confirm".
          const isRejection = NEGATED_CONFIRM_PATTERN.test(text) || REJECT_PATTERN.test(text);
          const isConfirmation = !isRejection && CONFIRM_PATTERN.test(text);

          if (isConfirmation) {
            confirmed.push(item.billingId);
            await client.messageFlagsAdd(uid, ['\\Seen'], { uid: true });
            break; // one confirming reply is enough for this billing record
          } else if (isRejection) {
            rejected.push({ billingId: item.billingId, reason: text.trim().slice(0, 300) || 'Client rejected via email reply.' });
            await client.messageFlagsAdd(uid, ['\\Seen'], { uid: true });
            break;
          }
          // Anything else from that address is left unseen/untouched - it
          // isn't a confirmation or rejection reply, so we don't guess.
        }
      }
    } finally {
      lock.release();
    }
    await client.logout();
  } catch (err) {
    console.error('IMAP check-confirmations failed:', err.message);
    if (client) {
      try { await client.logout(); } catch { /* ignore */ }
    }
    return res.status(500).json({ checked: false, reason: err.message, confirmed: [], rejected: [] });
  }

  return res.json({ checked: true, confirmed, rejected });
});

app.listen(PORT, () => {
  console.log(`Mail server listening on http://localhost:${PORT} (DEMO_EMAIL_MODE=${DEMO_MODE})`);
});
