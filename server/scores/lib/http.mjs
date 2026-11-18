// Small HTTP helpers: body reading with a size limit, JSON replies, the client's address.
import { isIP } from "node:net";

export const MAX_BODY = 32 * 1024;

export class HttpError extends Error {
  constructor(status, body) {
    super(body?.reason ?? String(status));
    this.status = status;
    this.body = body;
  }
}

/** The request body as text, at most `limit` bytes (413 beyond). */
export function readBody(req, limit = MAX_BODY) {
  return new Promise((resolve, reject) => {
    const declared = Number(req.headers["content-length"] ?? 0);
    if (declared > limit) {
      req.resume();
      return reject(new HttpError(413, { ok: false, reason: "too-large" }));
    }
    const chunks = [];
    let size = 0;
    req.on("data", (c) => {
      size += c.length;
      if (size > limit) {
        req.removeAllListeners("data");
        req.resume();
        reject(new HttpError(413, { ok: false, reason: "too-large" }));
      } else chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

/**
 * The body parsed as JSON whatever its Content-Type (sendBeacon sends text/plain). 400 if it
 * isn't JSON.
 */
export async function readJson(req, limit = MAX_BODY) {
  const text = await readBody(req, limit);
  try {
    return JSON.parse(text);
  } catch {
    throw new HttpError(400, { ok: false, reason: "invalid", error: "json" });
  }
}

export function sendJson(res, status, body, headers = {}) {
  const text = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(text),
    "Cache-Control": "no-store",
    ...headers,
  });
  res.end(text);
}

export function sendEmpty(res, status, headers = {}) {
  res.writeHead(status, { "Cache-Control": "no-store", ...headers });
  res.end();
}

/**
 * The client's address: the socket peer, or, when the peer is a trusted proxy (nginx on this host),
 * X-Real-IP, else the last X-Forwarded-For entry (the one nginx appended; earlier ones are the
 * client's own claims).
 */
export function clientIp(req, trustProxy) {
  const peer = req.socket.remoteAddress ?? "";
  if (!trustProxy.includes(peer)) return peer;
  const real = String(req.headers["x-real-ip"] ?? "").trim();
  if (isIP(real)) return real;
  const xff = String(req.headers["x-forwarded-for"] ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  const last = xff.at(-1) ?? "";
  return isIP(last) ? last : peer;
}
