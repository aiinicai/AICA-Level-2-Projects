// Google access for Edge Functions. Two supported modes (set as Edge Function secrets):
//  A) OAuth refresh token of the CA firm's Google account (works with free Gmail Drive):
//     GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
//  B) Service account (Google Workspace): GOOGLE_SA_EMAIL, GOOGLE_SA_PRIVATE_KEY, GOOGLE_SHARED_DRIVE_ID
//     Service accounts have no Drive storage of their own, so files must live in a Shared Drive.
// Scopes: drive.file is enough (the app only touches files/folders it created) + spreadsheets.

const SCOPES = 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/spreadsheets';
let cached: { token: string; exp: number } | undefined;

const b64url = (data: ArrayBuffer | string) =>
  btoa(typeof data === 'string' ? data : String.fromCharCode(...new Uint8Array(data))).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');

async function serviceAccountToken(email: string, pem: string): Promise<{ token: string; exp: number }> {
  const now = Math.floor(Date.now() / 1000);
  const header = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claims = b64url(JSON.stringify({ iss: email, scope: SCOPES, aud: 'https://oauth2.googleapis.com/token', iat: now, exp: now + 3600 }));
  const der = Uint8Array.from(atob(pem.replace(/-----[^-]+-----|\s|\\n/g, '')), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey('pkcs8', der, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key, new TextEncoder().encode(`${header}.${claims}`));
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: `${header}.${claims}.${b64url(sig)}` })
  });
  const j = await res.json();
  if (!res.ok) throw new Error(`Google token error: ${JSON.stringify(j)}`);
  return { token: j.access_token, exp: now + j.expires_in - 60 };
}

async function refreshTokenToken(id: string, secret: string, refresh: string): Promise<{ token: string; exp: number }> {
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'refresh_token', client_id: id, client_secret: secret, refresh_token: refresh })
  });
  const j = await res.json();
  if (!res.ok) throw new Error(`Google token error: ${JSON.stringify(j)}`);
  return { token: j.access_token, exp: Math.floor(Date.now() / 1000) + j.expires_in - 60 };
}

export async function googleToken(): Promise<string> {
  if (cached && cached.exp > Date.now() / 1000) return cached.token;
  const env = (k: string) => Deno.env.get(k);
  if (env('GOOGLE_REFRESH_TOKEN')) cached = await refreshTokenToken(env('GOOGLE_CLIENT_ID')!, env('GOOGLE_CLIENT_SECRET')!, env('GOOGLE_REFRESH_TOKEN')!);
  else if (env('GOOGLE_SA_EMAIL')) cached = await serviceAccountToken(env('GOOGLE_SA_EMAIL')!, env('GOOGLE_SA_PRIVATE_KEY')!);
  else throw new Error('Google credentials are not configured');
  return cached.token;
}

const sharedDrive = () => Deno.env.get('GOOGLE_SHARED_DRIVE_ID');
const driveParams = () => (sharedDrive() ? '&supportsAllDrives=true&includeItemsFromAllDrives=true' : '');

export async function gfetch(url: string, init: RequestInit = {}): Promise<Response> {
  const token = await googleToken();
  for (let attempt = 0; attempt < 4; attempt++) {
    const res = await fetch(url, { ...init, headers: { ...(init.headers ?? {}), Authorization: `Bearer ${token}` } });
    // back off on rate limits / transient errors (Drive & Sheets quotas)
    if (res.status === 429 || res.status >= 500) { await new Promise((r) => setTimeout(r, 500 * 2 ** attempt)); continue; }
    return res;
  }
  throw new Error(`Google API kept failing: ${url}`);
}

/** Finds or creates each folder of "a/b/c" and returns the last folder id. */
export async function ensureFolderPath(path: string): Promise<string> {
  let parent = sharedDrive() ?? 'root';
  for (const name of path.split('/').filter(Boolean)) {
    const q = encodeURIComponent(`name='${name.replace(/'/g, "\\'")}' and '${parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false`);
    const list = await (await gfetch(`https://www.googleapis.com/drive/v3/files?q=${q}&fields=files(id)${driveParams()}${sharedDrive() ? `&corpora=drive&driveId=${sharedDrive()}` : ''}`)).json();
    if (list.files?.[0]?.id) { parent = list.files[0].id; continue; }
    const created = await (await gfetch(`https://www.googleapis.com/drive/v3/files?fields=id${driveParams()}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, mimeType: 'application/vnd.google-apps.folder', parents: [parent] })
    })).json();
    parent = created.id;
  }
  return parent;
}

export async function uploadFile(folderId: string, name: string, file: Blob): Promise<{ id: string; webViewLink: string }> {
  const meta = new Blob([JSON.stringify({ name, parents: [folderId] })], { type: 'application/json' });
  const body = new FormData();
  body.append('metadata', meta);
  body.append('file', file);
  const res = await gfetch(`https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink${driveParams()}`, { method: 'POST', body });
  const j = await res.json();
  if (!res.ok) throw new Error(`Drive upload failed: ${JSON.stringify(j)}`);
  return j;
}
