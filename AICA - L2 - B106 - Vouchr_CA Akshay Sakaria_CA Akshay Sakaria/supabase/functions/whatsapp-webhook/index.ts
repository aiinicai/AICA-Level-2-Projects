// Supabase Edge Function (Deno): WhatsApp Business Cloud API webhook → bills become drafts in the Vouchr Inbox.
// Per Meta's docs (checked 2 Nov 2026): GET verification with hub.verify_token / hub.challenge; POST bodies signed with
// X-Hub-Signature-256 = HMAC-SHA256(raw body, app secret); media fetched via GET /{media-id} then the returned URL (expires
// in 5 min) with the access token; retries for up to 7 days → de-duplicated by message id (wamid).
// Rules: only numbers registered to an active user with a valid DPDP consent; unknown senders are refused and nothing they
// sent is stored. Optional AI reading follows the same consent + paid-tier rules as the app.
import { createClient } from 'npm:@supabase/supabase-js@2.46.1';
import { ensureFolderPath, uploadFile } from '../_shared/google.ts';
import { DEFAULT_MODELS, runTask } from '../_shared/ai/tasks.ts';
import { checkCode, parseVerifyText } from '../_shared/waVerify.ts';

const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
const VERIFY = Deno.env.get('WHATSAPP_VERIFY_TOKEN') ?? '';
const SECRET = Deno.env.get('WHATSAPP_APP_SECRET') ?? '';
const TOKEN = Deno.env.get('WHATSAPP_TOKEN') ?? '';
const GRAPH = `https://graph.facebook.com/${Deno.env.get('WHATSAPP_GRAPH_VERSION') ?? 'v26.0'}`;
const MAX = 15 * 1024 * 1024; // same limit as Drive filing in the app
const OK_TYPES = /^(image\/(jpeg|png)|application\/pdf)$/;

const MSG = {
  en: {
    saved: '✅ Bill received — it is in your Vouchr Inbox as a draft. Open the app to check and submit it.',
    dup: 'ℹ️ This bill was already received earlier — not added again.',
    unknown: 'This number is not registered with Vouchr. Please ask your company admin to add your WhatsApp number.',
    consent: 'Please open the Vouchr app and accept the privacy notice first, then send the bill again.',
    type: 'Please send the bill as a photo (JPG/PNG) or a PDF.',
    big: 'This file is larger than 15 MB. Please send a smaller photo or PDF.',
    help: 'Send a photo or PDF of a bill here and it will be added to your Vouchr Inbox.',
    fail: 'Sorry, the bill could not be saved right now. Please try again in a few minutes.',
    verified: '✅ Number confirmed. You can now send bills here.',
    badCode: 'That code is wrong or has expired. Open the Vouchr app (Privacy & consent) and get a new code.'
  },
  hi: {
    saved: '✅ बिल मिल गया — यह आपके Vouchr इनबॉक्स में ड्राफ़्ट के रूप में है। जाँचने और जमा करने के लिए ऐप खोलें।',
    dup: 'ℹ️ यह बिल पहले ही मिल चुका है — दोबारा नहीं जोड़ा गया।',
    unknown: 'यह नंबर Vouchr में रजिस्टर्ड नहीं है। कृपया अपनी कंपनी के एडमिन से अपना WhatsApp नंबर जुड़वाएँ।',
    consent: 'कृपया पहले Vouchr ऐप खोलकर गोपनीयता सूचना स्वीकार करें, फिर बिल दोबारा भेजें।',
    type: 'कृपया बिल फोटो (JPG/PNG) या PDF के रूप में भेजें।',
    big: 'यह फ़ाइल 15 MB से बड़ी है। कृपया छोटी फोटो या PDF भेजें।',
    help: 'बिल की फोटो या PDF यहाँ भेजें, वह आपके Vouchr इनबॉक्स में जुड़ जाएगा।',
    fail: 'माफ़ कीजिए, अभी बिल सेव नहीं हो सका। कृपया कुछ मिनट बाद फिर भेजें।',
    verified: '✅ नंबर की पुष्टि हो गई। अब आप यहाँ बिल भेज सकते हैं।',
    badCode: 'यह कोड गलत है या उसकी अवधि खत्म हो गई है। Vouchr ऐप (गोपनीयता और सहमति) खोलकर नया कोड लें।'
  }
} as const;

const hex = (buf: ArrayBuffer) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
async function hmac(raw: string): Promise<string> {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return hex(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(raw)));
}
function sameText(a: string, b: string) { // constant-time compare
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
const b64 = (buf: ArrayBuffer) => { let s = ''; const u = new Uint8Array(buf); for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000)); return btoa(s); };
const istToday = () => new Date(Date.now() + 5.5 * 3600 * 1000).toISOString().slice(0, 10);
const fyOf = (d: string) => { const y = Number(d.slice(0, 4)), m = Number(d.slice(5, 7)); const s = m >= 4 ? y : y - 1; return `${s}-${String(s + 1).slice(2)}`; };
const safe = (s: string) => s.normalize('NFKD').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-').slice(0, 40) || 'file';

async function reply(phoneNumberId: string, to: string, body: string) {
  // text reply inside the 24-hour customer-service window opened by the user's own message
  await fetch(`${GRAPH}/${phoneNumberId}/messages`, {
    method: 'POST', headers: { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ messaging_product: 'whatsapp', to, type: 'text', text: { body } })
  }).catch(() => undefined);
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  if (req.method === 'GET') {
    const ok = url.searchParams.get('hub.mode') === 'subscribe' && VERIFY && url.searchParams.get('hub.verify_token') === VERIFY;
    return ok ? new Response(url.searchParams.get('hub.challenge') ?? '', { status: 200 }) : new Response('forbidden', { status: 403 });
  }
  if (req.method !== 'POST') return new Response('method', { status: 405 });

  const raw = await req.text();
  const sig = (req.headers.get('x-hub-signature-256') ?? '').replace(/^sha256=/, '');
  if (!SECRET || !sameText(sig, await hmac(raw))) return new Response('bad signature', { status: 401 });

  let payload: any; // deno-lint-ignore no-explicit-any
  try { payload = JSON.parse(raw); } catch { return new Response('bad json', { status: 400 }); }

  for (const entry of payload.entry ?? []) for (const change of entry.changes ?? []) {
    const v = change.value ?? {};
    const phoneNumberId: string = v.metadata?.phone_number_id;
    for (const m of v.messages ?? []) {
      // Meta retries for 7 days — a message id already seen is ignored
      const { data: seen } = await db.from('whatsapp_messages').select('wamid').eq('wamid', m.id).maybeSingle();
      if (seen) continue;
      const from = String(m.from ?? '').replace(/\D/g, '');
      const log = (row: Record<string, unknown>) => db.from('whatsapp_messages').insert({ wamid: m.id, kind: m.type ?? 'other', ...row });

      const { data: user } = await db.from('profiles').select('id, client_id, language, active, whatsapp_verified_at, whatsapp_code_hash, whatsapp_code_expires, whatsapp_code_tries').eq('whatsapp_number', from).maybeSingle();

      // number check: "VERIFY 123456" sent FROM the registered number proves it belongs to that person
      const code = m.type === 'text' ? parseVerifyText(String(m.text?.body ?? '')) : undefined;
      if (code && user?.active && !user.whatsapp_verified_at) {
        const tv = MSG[(user.language as 'en' | 'hi') ?? 'en'] ?? MSG.en;
        const outcome = await checkCode(code, { hash: user.whatsapp_code_hash ?? undefined, expires: user.whatsapp_code_expires ?? undefined, tries: user.whatsapp_code_tries ?? 0 });
        if (outcome === 'verified') {
          await db.from('profiles').update({ whatsapp_verified_at: new Date().toISOString(), whatsapp_code_hash: null, whatsapp_code_expires: null, whatsapp_code_tries: 0 }).eq('id', user.id);
        } else if (outcome === 'wrong') {
          await db.from('profiles').update({ whatsapp_code_tries: (user.whatsapp_code_tries ?? 0) + 1 }).eq('id', user.id);
        }
        await log({ user_id: user.id, client_id: user.client_id, status: outcome === 'verified' ? 'number_verified' : 'verify_failed', detail: outcome });
        await reply(phoneNumberId, from, outcome === 'verified' ? tv.verified : tv.badCode);
        continue;
      }
      if (!user || !user.active || !user.whatsapp_verified_at || !user.client_id) {
        await log({ status: 'unknown_sender' }); // nothing from an unknown sender is stored
        await reply(phoneNumberId, from, MSG.en.unknown);
        continue;
      }
      const t = MSG[(user.language as 'en' | 'hi') ?? 'en'] ?? MSG.en;
      const today = istToday();
      const { data: uc } = await db.from('consents').select('purposes, withdrawn_at, valid_until').eq('scope', 'user').eq('user_id', user.id).order('accepted_at', { ascending: false }).limit(1).maybeSingle();
      const { data: cc } = await db.from('consents').select('purposes, withdrawn_at, valid_until').eq('scope', 'client').eq('client_id', user.client_id).order('accepted_at', { ascending: false }).limit(1).maybeSingle();
      const live = (c: { withdrawn_at?: string; valid_until?: string } | null) => !!c && !c.withdrawn_at && (!c.valid_until || c.valid_until >= today);
      if (!live(uc) || (cc && !live(cc))) { await log({ user_id: user.id, client_id: user.client_id, status: 'no_consent' }); await reply(phoneNumberId, from, t.consent); continue; }

      const media = m.type === 'image' ? m.image : m.type === 'document' ? m.document : undefined;
      if (!media) { await log({ user_id: user.id, client_id: user.client_id, status: 'unsupported' }); await reply(phoneNumberId, from, m.type === 'text' ? t.help : t.type); continue; }
      if (!OK_TYPES.test(media.mime_type ?? '')) { await log({ user_id: user.id, client_id: user.client_id, status: 'unsupported', detail: media.mime_type }); await reply(phoneNumberId, from, t.type); continue; }

      try {
        // 1) media id → short-lived URL → file
        const meta = await (await fetch(`${GRAPH}/${media.id}?phone_number_id=${phoneNumberId}`, { headers: { Authorization: `Bearer ${TOKEN}` } })).json();
        if (meta.file_size && meta.file_size > MAX) { await log({ user_id: user.id, client_id: user.client_id, status: 'too_large' }); await reply(phoneNumberId, from, t.big); continue; }
        const file = await fetch(meta.url, { headers: { Authorization: `Bearer ${TOKEN}` } });
        if (!file.ok) throw new Error(`media download HTTP ${file.status}`);
        const buf = await file.arrayBuffer();
        if (buf.byteLength > MAX) { await log({ user_id: user.id, client_id: user.client_id, status: 'too_large' }); await reply(phoneNumberId, from, t.big); continue; }
        const sha = hex(await crypto.subtle.digest('SHA-256', buf));

        // 2) same file already recorded for this client?
        const { data: dup } = await db.from('expenses').select('id').eq('client_id', user.client_id).eq('image_sha256', sha).neq('status', 'rejected').limit(1).maybeSingle();
        if (dup) { await log({ user_id: user.id, client_id: user.client_id, status: 'duplicate', expense_id: dup.id }); await reply(phoneNumberId, from, t.dup); continue; }

        // 3) optional AI reading — only on the paid tier and only with user + company consent for AI
        let ai: Record<string, { value: unknown; certainty: string }> | undefined;
        if (Deno.env.get('GEMINI_API_KEY') && Deno.env.get('GEMINI_TIER') === 'paid' && (uc as any)?.purposes?.ai && (!cc || (cc as any).purposes?.ai)) {
          try {
            const r = await runTask(Deno.env.get('GEMINI_API_KEY')!, { heavy: Deno.env.get('GEMINI_MODEL') ?? DEFAULT_MODELS.heavy, fast: Deno.env.get('GEMINI_MODEL_FAST') ?? DEFAULT_MODELS.fast },
              'read_bill', {}, [{ mime: media.mime_type, data: b64(buf) }], today);
            ai = r.result as typeof ai;
          } catch { /* AI is optional — the draft is still created */ }
        }
        const sure = (k: string) => (ai?.[k]?.certainty === 'certain' ? ai[k].value : undefined);
        const date = (sure('invoice_date') as string | undefined) ?? today;

        // 4) file in Drive: Vouchr/<Client>/FY …/Bills/  (originals kept as received)
        const { data: client } = await db.from('clients').select('name').eq('id', user.client_id).single();
        const ext = media.mime_type === 'application/pdf' ? 'pdf' : media.mime_type === 'image/png' ? 'png' : 'jpg';
        const folderId = await ensureFolderPath(`Vouchr/${safe(client!.name)}/FY ${fyOf(date)}/Bills`);
        const up = await uploadFile(folderId, `${date}_whatsapp_${safe(String(sure('vendor_name') ?? 'bill'))}.${ext}`, new Blob([buf], { type: media.mime_type }));

        // 5) draft in the Inbox — a person completes and submits it
        const { data: exp } = await db.from('expenses').insert({
          client_id: user.client_id, fy_label: fyOf(date), invoice_date: date, invoice_no: sure('invoice_no') ?? null, entry_source: 'whatsapp',
          drive_file_id: up.id, image_sha256: sha, total_amount: sure('total') ?? 0, taxable_value: sure('taxable_value') ?? 0,
          cgst: sure('cgst') ?? 0, sgst: sure('sgst') ?? 0, igst: sure('igst') ?? 0, status: 'draft', created_by: user.id
        }).select('id').single();
        await log({ user_id: user.id, client_id: user.client_id, status: 'draft_created', expense_id: exp?.id, detail: media.caption ?? media.filename ?? null });
        await reply(phoneNumberId, from, t.saved);
      } catch (err) {
        await log({ user_id: user.id, client_id: user.client_id, status: 'error', detail: String(err).slice(0, 300) });
        await db.from('system_events').insert({ level: 'error', component: 'whatsapp', client_id: user.client_id, message: String(err).slice(0, 500) });
        await reply(phoneNumberId, from, t.fail);
      }
    }
  }
  return new Response('ok', { status: 200 }); // always 200 once signature is valid, so Meta does not retry handled messages
});
