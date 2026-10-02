'use strict';
/* Google Calendar API sync plus Google Drive access for the desktop app.
   OAuth 2.0 for installed apps: loopback redirect plus PKCE. The refresh token is
   encrypted with the operating system keychain (Electron safeStorage) before it is stored.
   Drive is used by the tracker's Drive sync (journal files in one shared folder). */
const http = require('http');
const crypto = require('crypto');
const { shell, safeStorage } = require('electron');

const SCOPES = 'https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/drive openid email';
const DRIVE_SCOPE = /(^|\s)https:\/\/www\.googleapis\.com\/auth\/drive(\s|$)/;
const GOOGLE_HOSTS = ['www.googleapis.com', 'openidconnect.googleapis.com'];
const b64url = b => b.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const enc = s => safeStorage.isEncryptionAvailable() ? 'enc:' + safeStorage.encryptString(s).toString('base64') : 'raw:' + s;
const dec = s => !s ? null : s.startsWith('enc:') ? safeStorage.decryptString(Buffer.from(s.slice(4), 'base64')) : s.slice(4);

function create(db) {
  let access = null, accessExp = 0;

  function status() {
    return { connected: !!db.getSetting('gcal_refresh'), email: db.getSetting('gcal_email'), clientId: db.getSetting('gcal_client_id'), synced: db.gcalCount(),
      drive: DRIVE_SCOPE.test(db.getSetting('gcal_scope') || '') };
  }

  function connect({ clientId, clientSecret }) {
    return new Promise((resolve, reject) => {
      const verifier = b64url(crypto.randomBytes(32));
      const challenge = b64url(crypto.createHash('sha256').update(verifier).digest());
      const state = b64url(crypto.randomBytes(12));
      const server = http.createServer(async (req, res) => {
        const u = new URL(req.url, 'http://127.0.0.1');
        if (u.pathname !== '/') { res.writeHead(404); res.end(); return; }
        const done = (ok, msg) => { res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); res.end(`<html><body style="font-family:Georgia,serif;padding:40px;color:#0B1F3A"><h2>${ok ? 'Google Calendar connected' : 'Sign in did not complete'}</h2><p>${msg}</p><p>You can close this tab and return to the Sample Advisory tracker.</p></body></html>`); server.close(); };
        try {
          if (u.searchParams.get('state') !== state) throw new Error('State mismatch');
          if (u.searchParams.get('error')) throw new Error(u.searchParams.get('error'));
          const code = u.searchParams.get('code');
          const redirect = `http://127.0.0.1:${server.address().port}`;
          const tok = await tokenRequest({ client_id: clientId, client_secret: clientSecret || '', code, code_verifier: verifier, grant_type: 'authorization_code', redirect_uri: redirect });
          if (!tok.refresh_token) throw new Error('Google did not return a refresh token');
          db.setSetting('gcal_client_id', clientId);
          db.setSetting('gcal_client_secret', enc(clientSecret || ''));
          db.setSetting('gcal_refresh', enc(tok.refresh_token));
          db.setSetting('gcal_scope', tok.scope || '');
          access = tok.access_token; accessExp = Date.now() + (tok.expires_in - 60) * 1000;
          try { const info = await api('GET', 'https://openidconnect.googleapis.com/v1/userinfo'); db.setSetting('gcal_email', info.email || ''); } catch (e) { /* email is optional */ }
          done(true, 'Meetings can now be synced from the tracker.');
          resolve(status());
        } catch (e) { done(false, String(e.message)); reject(e); }
      });
      server.listen(0, '127.0.0.1', () => {
        const redirect = `http://127.0.0.1:${server.address().port}`;
        const p = new URLSearchParams({ client_id: clientId, redirect_uri: redirect, response_type: 'code', scope: SCOPES, access_type: 'offline', prompt: 'consent', code_challenge: challenge, code_challenge_method: 'S256', state });
        shell.openExternal('https://accounts.google.com/o/oauth2/v2/auth?' + p);
      });
      setTimeout(() => { try { server.close(); } catch (e) {} reject(new Error('Timed out waiting for Google sign in')); }, 5 * 60 * 1000);
    });
  }

  async function tokenRequest(params) {
    const r = await fetch('https://oauth2.googleapis.com/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(params) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error_description || j.error || ('HTTP ' + r.status));
    return j;
  }

  async function token() {
    if (access && Date.now() < accessExp) return access;
    const refresh = dec(db.getSetting('gcal_refresh'));
    if (!refresh) throw new Error('Google Calendar is not connected');
    const j = await tokenRequest({ client_id: db.getSetting('gcal_client_id'), client_secret: dec(db.getSetting('gcal_client_secret')) || '', refresh_token: refresh, grant_type: 'refresh_token' });
    access = j.access_token; accessExp = Date.now() + (j.expires_in - 60) * 1000;
    return access;
  }

  async function api(method, url, body) {
    const r = await fetch(url, { method, headers: { Authorization: 'Bearer ' + await token(), 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
    if (r.status === 204) return {};
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { const e = new Error((j.error && j.error.message) || ('HTTP ' + r.status)); e.status = r.status; throw e; }
    return j;
  }

  function toGoogle(ev) {
    const addDay = d => { const x = new Date(d + 'T00:00:00Z'); x.setUTCDate(x.getUTCDate() + 1); return x.toISOString().slice(0, 10); };
    let start, end;
    if (ev.allDay || !ev.time) { start = { date: ev.date }; end = { date: addDay(ev.date) }; }
    else {
      const [h, m] = ev.time.split(':').map(Number);
      const mins = h * 60 + m + (ev.duration || 60);
      const endDate = mins >= 1440 ? addDay(ev.date) : ev.date;
      const eh = String(Math.floor((mins % 1440) / 60)).padStart(2, '0'), em = String(mins % 60).padStart(2, '0');
      start = { dateTime: `${ev.date}T${ev.time}:00`, timeZone: 'Asia/Kolkata' };
      end = { dateTime: `${endDate}T${eh}:${em}:00`, timeZone: 'Asia/Kolkata' };
    }
    return { summary: ev.summary, description: ev.description, location: ev.location || undefined, start, end,
      attendees: (ev.attendees || []).map(email => ({ email })),
      status: ev.status === 'Cancelled' ? 'cancelled' : ev.status === 'Requested' ? 'tentative' : 'confirmed',
      extendedProperties: { private: { dealflowKey: ev.key } },
      reminders: { useDefault: true } };
  }

  async function sync({ events, sendInvites }) {
    const res = { created: 0, updated: 0, failed: 0, errors: [] };
    const q = sendInvites ? '?sendUpdates=all' : '?sendUpdates=none';
    const base = 'https://www.googleapis.com/calendar/v3/calendars/primary/events';
    for (const ev of events) {
      try {
        const body = toGoogle(ev);
        const existing = db.gcalMap(ev.key);
        if (existing) {
          try { await api('PATCH', `${base}/${encodeURIComponent(existing)}${q}`, body); res.updated++; continue; }
          catch (e) { if (e.status !== 404 && e.status !== 410) throw e; }
        }
        const made = await api('POST', base + q, body);
        db.setGcalMap(ev.key, made.id); res.created++;
      } catch (e) { res.failed++; res.errors.push(`${ev.summary}: ${e.message}`); }
    }
    db.flush();
    return res;
  }

  // Raw authorised request for the page's Drive sync; the page never sees the token.
  async function googleFetch({ method, url, headers, body }) {
    const host = new URL(url).hostname;
    if (!GOOGLE_HOSTS.includes(host)) throw new Error('Only Google API addresses are allowed');
    let t;
    try { t = await token(); } catch (e) { return { status: 401, text: '' }; }
    const r = await fetch(url, { method, headers: Object.assign({}, headers, { Authorization: 'Bearer ' + t }), body });
    if (r.status === 401) { access = null; accessExp = 0; }
    return { status: r.status, text: await r.text() };
  }

  function disconnect() {
    ['gcal_refresh', 'gcal_email', 'gcal_client_secret', 'gcal_scope'].forEach(k => db.setSetting(k, null));
    access = null; accessExp = 0;
    return status();
  }

  return { status, connect, sync, disconnect, googleFetch };
}
module.exports = { create };
