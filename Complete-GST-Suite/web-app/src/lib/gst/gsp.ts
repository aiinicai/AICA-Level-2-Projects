import type { Client } from "./demo";

/**
 * GST Suvidha Provider (GSP) access. Portal access works only through a GSP: the client enables
 * "Manage API Access" on gst.gov.in and the firm enters the OTP the client receives.
 * No portal password is ever asked for or stored.
 *
 * All endpoint paths live in this one object so any GSP can be configured (Settings › GSP).
 */
export const DEFAULT_GSP_ENDPOINTS = {
  authenticate: { path: "/taxpayerapi/v2.0/authenticate", actions: { otp: "OTPREQUEST", token: "AUTHTOKEN", refresh: "REFRESHTOKEN" } },
  gstr1: { path: "/taxpayerapi/v3.0/returns/gstr1", actions: ["B2B", "B2CS", "CDNR"] },
  gstr2b: { path: "/taxpayerapi/v1.0/returns/gstr2b", actions: ["GET2B"] },
  gstr3b: { path: "/taxpayerapi/v1.0/returns/gstr3b", actions: ["RETSUM"] },
  notices: { path: "/taxpayerapi/v1.0/notices", actions: ["NOTICES"] },
};
export type GspEndpoints = typeof DEFAULT_GSP_ENDPOINTS;

export const DEMO_OTP = "123456";
export const SESSION_HOURS = 6;
/** refresh the token when less than this many minutes are left */
export const REFRESH_BEFORE_MIN = 10;

export interface GspSession {
  /** only an opaque, non-secret session reference and its expiry are kept in the browser */
  ref: string;
  connectedAt: string;
  expiry: string;
}

export type SessionStatus = "Connected" | "Expired" | "Not connected";

export function sessionStatus(s: GspSession | undefined, now = new Date()): SessionStatus {
  if (!s) return "Not connected";
  return new Date(s.expiry).getTime() > now.getTime() ? "Connected" : "Expired";
}

export function needsRefresh(s: GspSession | undefined, now = new Date()): boolean {
  if (!s || sessionStatus(s, now) !== "Connected") return false;
  return new Date(s.expiry).getTime() - now.getTime() < REFRESH_BEFORE_MIN * 60000;
}

export class GspError extends Error {}

export function requestOtp(client: Client): string {
  if (!client.apiEnabled)
    throw new GspError("API access is not enabled for this client. Ask the client to enable 'Manage API Access' on gst.gov.in, then tick 'API access enabled' in the client master.");
  return `OTP sent to the client's registered mobile ending ${client.mobile4 || "XXXX"}. (Demo GSP: use OTP ${DEMO_OTP})`;
}

export function verifyOtp(otp: string, now = new Date()): GspSession {
  if (!/^\d{6}$/.test(otp.trim())) throw new GspError("Enter the 6-digit OTP the client received.");
  if (otp.trim() !== DEMO_OTP) throw new GspError(`That OTP is not correct. (Demo GSP accepts ${DEMO_OTP}.)`);
  return newSession(now);
}

export function newSession(now = new Date(), hours = SESSION_HOURS): GspSession {
  return { ref: `S-${Math.random().toString(36).slice(2, 8).toUpperCase()}`, connectedAt: now.toISOString(), expiry: new Date(now.getTime() + hours * 3600000).toISOString() };
}

export function refreshSession(s: GspSession | undefined, now = new Date()): GspSession {
  if (sessionStatus(s, now) !== "Connected") throw new GspError("The GSP session has expired — click Request OTP.");
  return { ...newSession(now), connectedAt: s!.connectedAt };
}

export type Route = "GSP API" | "Downloaded files";

/**
 * Data Source decides where portal data comes from:
 * - Auto: GSP API if the GSTIN is connected, otherwise uploaded files.
 * - GSP API: always the API; an expired session stops this client with "Request OTP".
 * - Downloaded files: never call the API.
 */
export function decideRoute(client: Client, status: SessionStatus): { route: Route; reason: string; error?: string | undefined } {
  if (client.dataSource === "Downloaded files") return { route: "Downloaded files", reason: "Data source is 'Downloaded files'" };
  if (client.dataSource === "GSP API") {
    if (status === "Connected") return { route: "GSP API", reason: "Data source is 'GSP API' (session connected)" };
    return { route: "GSP API", reason: "Data source is 'GSP API'", error: status === "Expired" ? "GSP session expired — click Request OTP for this client." : "GSP not connected — click Request OTP for this client." };
  }
  return status === "Connected"
    ? { route: "GSP API", reason: "Auto: GSTIN is connected to the GSP" }
    : { route: "Downloaded files", reason: "Auto: not connected, using uploaded files" };
}
