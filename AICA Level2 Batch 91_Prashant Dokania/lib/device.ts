/**
 * Anonymous device identity.
 *
 * A random device id plus a random device secret is minted the first time the
 * app is opened, before any profile, payment or permission screen. It carries
 * no personal information whatsoever. The secret is what stops someone else
 * from claiming your device id and reading your balance or sessions.
 */

const ID_KEY = "mirror.device.id.v1";
const SECRET_KEY = "mirror.device.secret.v1";
const LAST_KEY = "mirror.device.last.v1";
const IDENTITY_ASKED_KEY = "mirror.identity.asked.v1";

export type DeviceCredentials = { deviceId: string; deviceSecret: string };

function randomToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Mints the device identity on first call. Browser only. */
export function getDevice(): DeviceCredentials {
  if (typeof window === "undefined") return { deviceId: "", deviceSecret: "" };
  let deviceId = window.localStorage.getItem(ID_KEY);
  let deviceSecret = window.localStorage.getItem(SECRET_KEY);
  if (!deviceId || !deviceSecret) {
    deviceId = crypto.randomUUID();
    deviceSecret = randomToken();
    window.localStorage.setItem(ID_KEY, deviceId);
    window.localStorage.setItem(SECRET_KEY, deviceSecret);
  }
  return { deviceId, deviceSecret };
}

/**
 * The single "your last reflection" callback kept for anonymous users. No
 * scrollable history is ever stored or shown while anonymous, so the next
 * person on a shared device cannot browse someone else's sessions.
 */
export type LastReflection = {
  summary: string;
  sessionType: string;
  createdAt: string;
};

export function getLastReflection(): LastReflection | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(LAST_KEY);
    return raw ? (JSON.parse(raw) as LastReflection) : null;
  } catch {
    return null;
  }
}

export function setLastReflection(value: LastReflection) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LAST_KEY, JSON.stringify(value));
}

export function clearLocalTrace() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LAST_KEY);
  window.localStorage.removeItem(IDENTITY_ASKED_KEY);
}

export const identityAsked = () =>
  typeof window !== "undefined" && window.localStorage.getItem(IDENTITY_ASKED_KEY) === "1";

export function markIdentityAsked() {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(IDENTITY_ASKED_KEY, "1");
}
