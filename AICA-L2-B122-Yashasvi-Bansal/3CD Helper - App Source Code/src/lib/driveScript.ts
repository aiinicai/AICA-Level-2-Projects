// Client data straight to the firm's own Google Drive, through a small Google Apps Script that the firm
// puts in its own Google account (script.google.com – free, no Cloud Console). The script checks every
// upload against the live client link (client_link_info) before saving it, so only valid links can write,
// and only into "<root>/<client>/AY <year>". The firm's other Drive files are never visible to anyone.
import { zipDeflate } from "./import/bundle";

export const DRIVE_ROOT = "3CD Helper – Client data";
/** Apps Script accepts about 50 MB per request; the data goes base64-encoded (4/3 larger). */
export const DRIVE_MAX_MB = 35;

/**
 * Manifest (appsscript.json) for the script: it limits the script to the files it creates itself
 * (drive.file) and to calling this app's database (external_request). Google then asks only for these two.
 */
export const DRIVE_MANIFEST = JSON.stringify({
  timeZone: "Asia/Kolkata",
  dependencies: {},
  exceptionLogging: "STACKDRIVER",
  runtimeVersion: "V8",
  oauthScopes: ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/script.external_request"],
  webapp: { executeAs: "USER_DEPLOYING", access: "ANYONE_ANONYMOUS" },
}, null, 2);

/** The script the firm pastes into script.google.com (with this app's database address filled in). */
export function driveScript(supabaseUrl: string, publishableKey: string, readKey = ""): string {
  return `// 3CD Helper – client data to your Google Drive.
// Access: ONLY the files and folders this script creates itself (Google calls it "drive.file").
// It cannot see, change or delete any other file in your Drive.
// 1. Project Settings → tick "Show appsscript.json manifest file in editor"; replace that file with the manifest from 3CD Helper.
// 2. Choose "setup" next to the Run button and press Run once; allow access (Advanced → Go to … → Allow).
// 3. Deploy → New deployment → Web app → Execute as: Me → Who has access: Anyone → Deploy.
// 4. Copy the Web app URL into 3CD Helper → Settings → Google Drive.
const SUPABASE_URL = ${JSON.stringify(supabaseUrl.replace(/\/+$/, ""))};
const SUPABASE_KEY = ${JSON.stringify(publishableKey)};
const ROOT = ${JSON.stringify(DRIVE_ROOT)};
const API = "https://www.googleapis.com/drive/v3/files";
// Only 3CD Helper (signed in to your firm) knows this key; without it nobody can list or read the files.
const READ_KEY = ${JSON.stringify(readKey)};

/** Run this once from the editor: Google then asks to allow the two limited permissions. */
function setup() {
  const id = folder_(ROOT, "root");
  UrlFetchApp.fetch(SUPABASE_URL + "/rest/v1/", { muteHttpExceptions: true, headers: { apikey: SUPABASE_KEY } });
  Logger.log("Ready. Data will be saved in the folder: " + ROOT + " (" + id + ")");
}

function doGet() {
  // tells 3CD Helper whether access has been allowed
  let drive = true;
  try { folder_(ROOT, "root"); } catch (e) { drive = false; }
  return out_({ ok: true, app: "3CD Helper Drive", drive: drive, reader: !!READ_KEY });
}

function doPost(e) {
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    if (body.action) return read_(body);
    const token = String(body.token || "");
    if (!/^[0-9a-f]{40,80}$/.test(token)) throw new Error("This link is not valid");
    const res = UrlFetchApp.fetch(SUPABASE_URL + "/rest/v1/rpc/client_link_info", {
      method: "post", contentType: "application/json", muteHttpExceptions: true,
      headers: { apikey: SUPABASE_KEY, Authorization: "Bearer " + SUPABASE_KEY },
      payload: JSON.stringify({ p_token: token }),
    });
    const info = res.getResponseCode() === 200 ? JSON.parse(res.getContentText() || "null") : null;
    if (!info || info.deliver_to !== "drive") throw new Error("This link has expired or does not send to Google Drive");
    const bytes = Utilities.base64Decode(String(body.data || ""));
    if (!bytes.length) throw new Error("No data");
    if (bytes.length > ${DRIVE_MAX_MB} * 1024 * 1024) throw new Error("The file is too large");
    const client = folder_(clean_(info.client), folder_(ROOT, "root"));
    const year = folder_("AY " + clean_(info.ay), client);
    const stamp = Utilities.formatDate(new Date(), "Asia/Kolkata", "yyyy-MM-dd HH.mm");
    const name = stamp + " " + clean_(String(body.fileName || "Tally data.zip")).slice(0, 150);
    upload_(name, String(body.mime || "application/zip"), bytes, year, { eng: String(info.engagement_id || ""), ay: String(info.ay || "") });
    return out_({ ok: true, name: name, folder: ROOT + " / " + info.client + " / AY " + info.ay });
  } catch (err) {
    const m = String((err && err.message) || err);
    return out_({ ok: false, error: /permission|authori|insufficient|scope|401|403/i.test(m) ? "NO_DRIVE_PERMISSION" : m });
  }
}

/** For 3CD Helper itself: the list of a year's files, or one file's data. Needs the firm's key. */
function read_(body) {
  if (!READ_KEY || body.key !== READ_KEY) throw new Error("BAD_KEY");
  if (body.action === "list") {
    const eng = String(body.eng || "");
    if (!/^[0-9a-f-]{36}$/.test(eng)) throw new Error("Bad request");
    const fields = "&fields=files(id,name,size,createdTime,appProperties)&orderBy=createdTime desc&pageSize=100";
    const seen = {}; const files = [];
    const add = (list) => (list || []).forEach(function (f) {
      if (seen[f.id] || (f.appProperties && f.appProperties.eng && f.appProperties.eng !== eng)) return;
      seen[f.id] = 1; files.push({ id: f.id, name: f.name, size: Number(f.size || 0), at: f.createdTime });
    });
    add(call_(API + "?q=" + encodeURIComponent("appProperties has { key='eng' and value='" + eng + "' } and trashed = false") + fields).files);
    // files sent before tagging: found by the folder <client> / AY <year>
    const root = find_(ROOT, "root"); const client = root && find_(clean_(body.client), root); const year = client && find_("AY " + clean_(body.ay), client);
    if (year) add(call_(API + "?q=" + encodeURIComponent("'" + year + "' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'") + fields).files);
    files.sort(function (a, b) { return a.at < b.at ? 1 : -1; });
    return out_({ ok: true, files: files });
  }
  if (body.action === "get") {
    const id = String(body.id || "");
    if (!/^[\\w-]{10,}$/.test(id)) throw new Error("Bad request");
    const meta = call_(API + "/" + id + "?fields=name,size");
    const r = UrlFetchApp.fetch(API + "/" + id + "?alt=media", { muteHttpExceptions: true, headers: auth_() });
    if (r.getResponseCode() >= 300) throw new Error("Drive " + r.getResponseCode());
    return out_({ ok: true, name: meta.name, data: Utilities.base64Encode(r.getBlob().getBytes()) });
  }
  throw new Error("Bad request");
}
function find_(name, parentId) {
  const q = "name = '" + name.replace(/\\\\/g, "\\\\\\\\").replace(/'/g, "\\\\'") + "' and mimeType = 'application/vnd.google-apps.folder' and '" + parentId + "' in parents and trashed = false";
  const f = call_(API + "?fields=files(id)&q=" + encodeURIComponent(q)).files;
  return f && f.length ? f[0].id : null;
}
function auth_() { return { Authorization: "Bearer " + ScriptApp.getOAuthToken() }; }
function call_(url, opt) {
  const r = UrlFetchApp.fetch(url, Object.assign({ muteHttpExceptions: true, headers: auth_() }, opt || {}));
  if (r.getResponseCode() >= 300) throw new Error("Drive " + r.getResponseCode() + ": " + r.getContentText().slice(0, 200));
  return JSON.parse(r.getContentText() || "{}");
}
/** A folder this script made (kept by id; found again by name inside its parent; made if missing). */
function folder_(name, parentId) {
  const props = PropertiesService.getScriptProperties();
  const key = "f:" + parentId + ":" + name;
  const known = props.getProperty(key);
  if (known) {
    try { const f = call_(API + "/" + known + "?fields=id,trashed"); if (!f.trashed) return f.id; } catch (e) { /* gone – make again */ }
  }
  const q = "name = '" + name.replace(/\\\\/g, "\\\\\\\\").replace(/'/g, "\\\\'") + "' and mimeType = 'application/vnd.google-apps.folder' and '" + parentId + "' in parents and trashed = false";
  const found = call_(API + "?fields=files(id)&q=" + encodeURIComponent(q));
  const id = found.files && found.files.length ? found.files[0].id
    : call_(API + "?fields=id", { method: "post", contentType: "application/json", payload: JSON.stringify({ name: name, mimeType: "application/vnd.google-apps.folder", parents: [parentId] }) }).id;
  props.setProperty(key, id);
  return id;
}
function upload_(name, mime, bytes, parentId, props) {
  const boundary = "3cd" + Date.now();
  const head = "--" + boundary + "\\r\\nContent-Type: application/json; charset=UTF-8\\r\\n\\r\\n" + JSON.stringify({ name: name, parents: [parentId], appProperties: props || {} }) +
    "\\r\\n--" + boundary + "\\r\\nContent-Type: " + mime + "\\r\\n\\r\\n";
  const tail = "\\r\\n--" + boundary + "--";
  const payload = Utilities.newBlob(head).getBytes().concat(bytes).concat(Utilities.newBlob(tail).getBytes());
  return call_("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id", { method: "post", contentType: "multipart/related; boundary=" + boundary, payload: payload });
}
function clean_(s) { return String(s || "").replace(/[\\\\/:*?"<>|]+/g, "_").trim() || "_"; }
function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
`;
}

export const isDriveUrl = (u: string) => /^https:\/\/script\.google\.com\/macros\/s\/[\w-]+\/exec$/.test(u.trim());

/** Does the script answer, and has Drive access been allowed? ("no-drive" = run setup once in the editor; "old" = script without the read key). */
export async function testDrive(url: string): Promise<"ok" | "no-drive" | "no" | "old"> {
  try {
    const r = await fetch(`${url}?t=${Date.now()}`, { method: "GET", cache: "no-store" }); const j = await r.json();
    if (!j?.ok || j.app !== "3CD Helper Drive") return "no";
    return j.drive === false ? "no-drive" : j.reader ? "ok" : "old";
  } catch { return "no"; }
}
const PERMISSION_TEXT = "Your CA's Google Drive has not allowed access yet. Please tell your CA: open the script at script.google.com, run \"setup\" once and allow access, then deploy a new version.";

const toBase64 = (b: Uint8Array) => {
  let s = ""; const step = 0x8000;
  for (let i = 0; i < b.length; i += step) s += String.fromCharCode(...b.subarray(i, i + step));
  return btoa(s);
};

/** Sends files (one ZIP) to the firm's Drive through the script; returns the saved name and folder. */
export async function sendToDrive(url: string, token: string, files: File[], baseName: string): Promise<{ name: string; folder: string; bytes: number }> {
  const items = await Promise.all(files.map(async (f) => ({ name: f.name, data: new Uint8Array(await f.arrayBuffer()) })));
  const single = items.length === 1 && /\.zip$/i.test(items[0].name);
  const zip = single ? items[0].data : await zipDeflate(items);
  if (zip.length > DRIVE_MAX_MB * 1048576) throw new Error(`The data is larger than ${DRIVE_MAX_MB} MB even after ZIP. Send a shorter period, or files one at a time.`);
  // a plain text body: no browser pre-check, which Apps Script does not answer
  const r = await fetch(url, { method: "POST", body: JSON.stringify({ token, fileName: single ? items[0].name : `${baseName}.zip`, mime: "application/zip", data: toBase64(zip) }) });
  let j: any = null;
  try { j = await r.json(); } catch { /* not JSON */ }
  if (!j?.ok) throw new Error(j?.error === "NO_DRIVE_PERMISSION" || /permission|authori/i.test(j?.error ?? "") ? PERMISSION_TEXT : j?.error || "Google Drive did not accept the data. Ask your CA to check the Drive setting.");
  return { name: j.name, folder: j.folder, bytes: zip.length };
}

/** A new random key for reading the firm's Drive files (kept in firms.settings.drive_key and in the script). */
export function newDriveKey() {
  const b = crypto.getRandomValues(new Uint8Array(24));
  return Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
}
export interface DriveFile { id: string; name: string; size: number; at: string }
export const OLD_SCRIPT_TEXT = "The Google Drive script is older than this app. Settings → Google Drive → copy the script again, paste it in script.google.com, save, then Deploy → Manage deployments → Edit → New version.";

async function read(url: string, body: object) {
  let j: any = null;
  try { const r = await fetch(url, { method: "POST", body: JSON.stringify(body) }); j = await r.json(); } catch { /* not JSON */ }
  if (!j?.ok) throw new Error(j?.error === "BAD_KEY" ? OLD_SCRIPT_TEXT : j?.error === "NO_DRIVE_PERMISSION" ? "Drive access is not allowed: run \"setup\" once in the script editor and allow access." : j?.error || "Google Drive did not answer. Check Settings → Google Drive.");
  return j;
}
/** Files clients sent for one assessment year (newest first). */
export async function listDrive(url: string, key: string, q: { eng: string; client: string; ay: string }): Promise<DriveFile[]> {
  return (await read(url, { action: "list", key, ...q })).files ?? [];
}
/** One file from the firm's Drive, as a File ready for import. */
export async function getDrive(url: string, key: string, f: DriveFile): Promise<File> {
  const j = await read(url, { action: "get", key, id: f.id });
  const bin = atob(j.data); const b = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) b[i] = bin.charCodeAt(i);
  return new File([b], j.name || f.name, { type: /\.zip$/i.test(j.name || f.name) ? "application/zip" : "application/octet-stream" });
}
