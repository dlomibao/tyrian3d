// Rate limiting, in memory only. Clients are keyed by a salted, monthly-rotating hash of their IP
// (never the IP itself) and, separately, by their player id: the two are never joined or stored.
import { createHmac } from "node:crypto";
import { ipToBytes, isMappedV4 } from "./geo.mjs";

/** 'YYYY-MM' (UTC) of `now` (ms). */
export const utcMonth = (now) => new Date(now).toISOString().slice(0, 7);
/** 'YYYY-MM-DD' (UTC) of `now` (ms). */
export const utcDay = (now) => new Date(now).toISOString().slice(0, 10);

/**
 * HMAC-SHA256(salt + "|" + UTC 'YYYY-MM', ip): the monthly key means hashes can't be linked across
 * months. The address is canonicalised to 16 bytes first; an IPv6 address is cut to its /64 (one
 * subscriber's usual allocation), so rotating within it doesn't escape the limit.
 */
export function ipHash(salt, ip, now) {
  const bytes = ipToBytes(ip) ?? Buffer.from(String(ip ?? ""));
  if (bytes.length === 16 && !isMappedV4(bytes)) bytes.fill(0, 8);
  return createHmac("sha256", `${salt}|${utcMonth(now)}`).update(bytes).digest("hex");
}

/** Fixed one-hour windows per key. */
export class RateLimiter {
  constructor(windowMs = 3600 * 1000) {
    this.windowMs = windowMs;
    this.windows = new Map();
  }

  /**
   * Count a hit for `key` against `limit` per window. Returns 0 if allowed, else the seconds until
   * the window resets (for Retry-After).
   */
  hit(key, limit, now) {
    if (this.windows.size > 100000) this.sweep(now);
    let w = this.windows.get(key);
    if (!w || now - w.start >= this.windowMs) {
      w = { start: now, count: 0 };
      this.windows.set(key, w);
    }
    if (w.count >= limit) return Math.max(1, Math.ceil((w.start + this.windowMs - now) / 1000));
    w.count++;
    return 0;
  }

  sweep(now) {
    for (const [k, w] of this.windows) if (now - w.start >= this.windowMs) this.windows.delete(k);
  }
}
