// Hardware-linked license verification for CMA Pro Builder server (Chronoflow-style).
//
// HARDWARE ID (shown on the activation screen):  XXXX-XXXX-XXXX-XXXX
//   5 hex chars from SHA256(CPU ID) + 5 from SHA256(motherboard serial)
//   + 5 from SHA256(primary MAC) + 1 checksum char.
//
// LICENSE KEY (produced by the vendor keygen):  CMA-XXXX-XXXX-XXXX-XXXX
//   char 0     : key type — 'A' = Annual (expires Dec 31 of year), 'M' = Master (perpetual)
//   chars 1-4  : year (e.g. 2027) or 0000 for Master
//   chars 5-15 : first 11 hex chars of HMAC-SHA256(secret, "CMA1|<hardwareId16>|<type><year>")
//
// The secret is derived from the vendor's private key file; only the derived
// value ships inside the exe (same security model as Chronoflow).
//
// TOLERANCE: at activation the presented Hardware ID is stored with the key.
//   Later checks accept the machine if >= 2 of the 3 hardware segments still
//   match (empty/unreadable components never count as a match).
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');

const SIG_PREFIX_LEN = 11;

function sha256(s) {
  return crypto.createHash('sha256').update(String(s || '')).digest('hex');
}
function hmac(secret, s) {
  return crypto.createHmac('sha256', secret).update(String(s)).digest('hex');
}

function psQuery(cmd) {
  const shells = [
    'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe',
    'powershell.exe',
    'pwsh.exe',
  ];
  for (const sh of shells) {
    try {
      return execSync(`"${sh}" -NoProfile -Command "${cmd}"`, { encoding: 'utf8', timeout: 10000, windowsHide: true }).trim();
    } catch { /* try next */ }
  }
  return '';
}

function wmicQuery(cmd) {
  try {
    const out = execSync(`C:\\Windows\\System32\\wbem\\WMIC.exe ${cmd}`, { encoding: 'utf8', timeout: 10000, windowsHide: true });
    const lines = out.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    return lines.length > 1 ? lines[1] : '';
  } catch {
    return '';
  }
}

function getCpuId() {
  return psQuery('(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty ProcessorId)')
    || wmicQuery('cpu get processorid');
}
function getBoardSerial() {
  return psQuery('(Get-CimInstance Win32_BaseBoard | Select-Object -First 1 -ExpandProperty SerialNumber)')
    || wmicQuery('baseboard get serialnumber');
}
function getPrimaryMac() {
  const ifs = os.networkInterfaces();
  for (const list of Object.values(ifs)) {
    for (const ni of list || []) {
      if (!ni.internal && ni.mac && ni.mac !== '00:00:00:00:00:00') return ni.mac;
    }
  }
  return '';
}

/** Segment = 5 uppercase hex chars, or '' when the component is unreadable */
function seg(raw) {
  return raw ? sha256(raw).slice(0, 5).toUpperCase() : '';
}

/** Live hardware segments {cpu, board, mac} (each may be '') */
function liveSegments() {
  return { cpu: seg(getCpuId()), board: seg(getBoardSerial()), mac: seg(getPrimaryMac()) };
}

function idChecksum(cpu5, board5, mac5) {
  return sha256(cpu5 + board5 + mac5).slice(0, 1).toUpperCase();
}

/** The short Hardware ID for display / key minting.
 *  Cached after first computation — hardware queries (PowerShell/CIM) can take
 *  several seconds, and /api/health must answer fast or the frontend's
 *  license check times out and could open the app without activation. */
let cachedShortId = null;
function machineShortId() {
  if (cachedShortId) return cachedShortId;
  const s = liveSegments();
  const cpu5 = s.cpu || '00000';
  const board5 = s.board || '00000';
  const mac5 = s.mac || '00000';
  const raw16 = cpu5 + board5 + mac5 + idChecksum(cpu5, board5, mac5);
  cachedShortId = { id: raw16.replace(/(.{4})(?=.)/g, '$1-'), raw16, segments: s };
  return cachedShortId;
}

/** Validate + normalize a Hardware ID typed/pasted by a human → raw16 or null */
function parseHardwareId(text) {
  const raw = String(text || '').toUpperCase().replace(/[^0-9A-F]/g, '');
  if (raw.length !== 16) return null;
  if (idChecksum(raw.slice(0, 5), raw.slice(5, 10), raw.slice(10, 15)) !== raw[15]) return null;
  return raw;
}

/** Parse a license key → {type, year, sigPrefix, normalized} or null. Accepts CMA- prefix, dashes, spaces. */
function parseKey(keyText) {
  const raw = String(keyText || '').toUpperCase().replace(/^CMA-/, '').replace(/[^0-9A-Z]/g, '');
  if (raw.length !== 16) return null;
  const type = raw[0];
  if (type !== 'A' && type !== 'M') return null;
  const year = raw.slice(1, 5);
  if (!/^\d{4}$/.test(year)) return null;
  if (type === 'M' && year !== '0000') return null;
  if (type === 'A' && year === '0000') return null;
  const sigPrefix = raw.slice(5);
  if (!/^[0-9A-F]{11}$/.test(sigPrefix)) return null;
  return { type, year, sigPrefix, normalized: `CMA-${raw.replace(/(.{4})(?=.)/g, '$1-')}` };
}

// License HMAC secret: embedded at bundle time (exe build) via license-secret.cjs.
let EMBEDDED_SECRET = '';
try { EMBEDDED_SECRET = require('./license-secret.cjs') || ''; } catch { /* dev mode: file fallback */ }

function loadSecret(dataDir) {
  if (EMBEDDED_SECRET) return EMBEDDED_SECRET;
  const candidates = [
    path.join(dataDir, '..', 'server', 'license-secret.txt'),
    path.join(__dirname, 'license-secret.txt'),
    path.join(__dirname, '..', 'server', 'license-secret.txt'),
  ];
  for (const p of candidates) {
    try { if (fs.existsSync(p)) return fs.readFileSync(p, 'utf8').trim(); } catch { /* next */ }
  }
  return null;
}

function isExpired(type, year) {
  if (type === 'M') return false;
  return new Date() > new Date(`${year}-12-31T23:59:59`);
}

/** Verify a license key against a hardware ID (raw16). Returns {ok, reason, key} */
function verifyKeyForId(keyText, raw16, dataDir) {
  const secret = loadSecret(dataDir);
  if (!secret) return { ok: false, reason: 'no-secret' };
  const k = parseKey(keyText);
  if (!k) return { ok: false, reason: 'malformed' };
  const expect = hmac(secret, `CMA1|${raw16}|${k.type}${k.year}`).slice(0, SIG_PREFIX_LEN).toUpperCase();
  if (expect !== k.sigPrefix) return { ok: false, reason: 'machine-mismatch' };
  if (isExpired(k.type, k.year)) return { ok: false, reason: 'expired', key: k };
  return { ok: true, key: k };
}

/** 2-of-3 segment match between live hardware and the ID stored at activation */
function segmentsMatch(live, storedRaw16) {
  const stored = { cpu: storedRaw16.slice(0, 5), board: storedRaw16.slice(5, 10), mac: storedRaw16.slice(10, 15) };
  let matches = 0;
  for (const comp of ['cpu', 'board', 'mac']) {
    // Empty (unreadable) live component or all-zero stored segment NEVER counts
    if (live[comp] && stored[comp] !== '00000' && live[comp] === stored[comp]) matches++;
  }
  return matches >= 2;
}

function keyInfo(k) {
  return {
    keyType: k.type === 'M' ? 'Master' : 'Annual',
    year: k.type === 'M' ? null : k.year,
    expiry: k.type === 'M' ? null : `${k.year}-12-31`,
  };
}

/** Load the stored license (hardwareId + key) and verify against live hardware. */
// ─────────────────────────────────────────────────────────────────────────────
// EVALUATION BUILD (AICA Level 2 Capstone submission):
// Licensing is DISABLED in this copy so the examiner can run the app on any PC
// without an activation key. The production build (vendor copy) enforces the
// hardware-locked short-key system implemented below — all functions remain
// intact and unit-testable (see test/ and tools/keygen-interactive.cjs).
const EVALUATION_MODE = true;
// ─────────────────────────────────────────────────────────────────────────────
function licenseStatus(dataDir) {
  const id = machineShortId();
  const base = { hardwareId: id.id, machineCode: id.id };
  if (EVALUATION_MODE) return { licensed: true, keyType: 'Evaluation', year: null, expiry: null, ...base };
  const keyPath = path.join(dataDir, 'license.key');
  let fileText = '';
  try { if (fs.existsSync(keyPath)) fileText = fs.readFileSync(keyPath, 'utf8'); } catch { /* none */ }
  if (!fileText.trim()) return { licensed: false, reason: 'no-key', ...base };

  const lines = fileText.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const storedRaw16 = parseHardwareId(lines[0] || '');
  const keyText = lines[1] || lines[0]; // tolerate single-line legacy files
  if (!storedRaw16) return { licensed: false, reason: 'bad-license-file', ...base };

  if (!segmentsMatch(id.segments, storedRaw16)) return { licensed: false, reason: 'machine-mismatch', ...base };

  const v = verifyKeyForId(keyText, storedRaw16, dataDir);
  return {
    licensed: v.ok,
    reason: v.ok ? undefined : v.reason,
    ...(v.key ? keyInfo(v.key) : {}),
    ...base,
  };
}

/** Activate: verify the key against the LIVE hardware ID, then store id+key. */
function activate(keyText, dataDir) {
  if (EVALUATION_MODE) return { ok: true, keyType: 'Evaluation', year: null, expiry: null };
  const id = machineShortId();
  const v = verifyKeyForId(keyText, id.raw16, dataDir);
  if (!v.ok) return { ok: false, reason: v.reason };
  fs.mkdirSync(dataDir, { recursive: true });
  fs.writeFileSync(keyPath(dataDir), `${id.raw16}\n${v.key.normalized}\n`, 'utf8');
  return { ok: true, ...keyInfo(v.key) };
}
function keyPath(dataDir) { return path.join(dataDir, 'license.key'); }

module.exports = { machineShortId, parseHardwareId, parseKey, licenseStatus, activate, verifyKeyForId };
