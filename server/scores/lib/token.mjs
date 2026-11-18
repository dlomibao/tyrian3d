// Run tokens: base64url(JSON payload) + "." + base64url(HMAC-SHA256(secret, payload part)).
// The payload is {v: 1, id, iat, ep, diff, mode}; id is 16 random bytes in hex, iat ms since epoch.
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

/** Score submissions: a token lives in the save, so it lasts 30 days. */
export const TOKEN_MAX_AGE_MS = 30 * 24 * 3600 * 1000;
/** Level reports accept a token up to 60 days old. */
export const REPORT_TOKEN_MAX_AGE_MS = 60 * 24 * 3600 * 1000;
/** A token can't be issued in the future by more than this (clock steps). */
const FUTURE_SLACK_MS = 60 * 1000;

const sign = (secret, part) => createHmac("sha256", secret).update(part).digest();

/** A new token for {ep, diff, mode} issued at `now`. Returns {token, payload}. */
export function issueToken(secret, { ep, diff, mode }, now) {
  const payload = { v: 1, id: randomBytes(16).toString("hex"), iat: now, ep, diff, mode };
  const part = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return { token: `${part}.${sign(secret, part).toString("base64url")}`, payload };
}

/**
 * Check a token's signature and age. Returns {ok: true, payload} or {ok: false, reason} with reason
 * "token" (malformed or bad signature) or "expired" (then with the payload).
 */
export function verifyToken(secret, token, now, maxAgeMs = TOKEN_MAX_AGE_MS) {
  if (typeof token !== "string" || token.length > 512) return { ok: false, reason: "token" };
  const parts = token.split(".");
  if (parts.length !== 2 || !/^[A-Za-z0-9_-]+$/.test(parts[0]) || !/^[A-Za-z0-9_-]+$/.test(parts[1])) return { ok: false, reason: "token" };
  const given = Buffer.from(parts[1], "base64url");
  const expected = sign(secret, parts[0]);
  if (given.length !== expected.length || !timingSafeEqual(given, expected)) return { ok: false, reason: "token" };
  let payload;
  try {
    payload = JSON.parse(Buffer.from(parts[0], "base64url").toString("utf8"));
  } catch {
    return { ok: false, reason: "token" };
  }
  if (payload?.v !== 1 || typeof payload.id !== "string" || !/^[0-9a-f]{32}$/.test(payload.id) || !Number.isSafeInteger(payload.iat)) {
    return { ok: false, reason: "token" };
  }
  if (payload.iat > now + FUTURE_SLACK_MS) return { ok: false, reason: "token" };
  if (now - payload.iat > maxAgeMs) return { ok: false, reason: "expired", payload };
  return { ok: true, payload };
}
