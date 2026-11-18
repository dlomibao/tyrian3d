// IP -> country, from an offline DB-IP "IP to Country Lite" table (CC BY 4.0, "IP geolocation by
// DB-IP", https://db-ip.com), loaded by tools/load-geo.mjs. Only the 2-letter code is ever stored;
// the address is discarded after the lookup.
import { isIPv4, isIPv6 } from "node:net";
import { transaction } from "./db.mjs";

export const UNKNOWN_COUNTRY = "ZZ";

/**
 * The 16-byte form of an IPv4 or IPv6 address (IPv4 as ::ffff:a.b.c.d), so BLOB order (memcmp) is
 * address order. null if `ip` isn't an address.
 */
export function ipToBytes(ip) {
  let s = String(ip ?? "").trim();
  const zone = s.indexOf("%");
  if (zone >= 0) s = s.slice(0, zone);
  const out = Buffer.alloc(16);
  if (isIPv4(s)) {
    out[10] = 0xff;
    out[11] = 0xff;
    s.split(".").forEach((p, i) => (out[12 + i] = Number(p)));
    return out;
  }
  if (!isIPv6(s)) return null;
  // An embedded IPv4 tail (::ffff:1.2.3.4) becomes two hex groups.
  const lastColon = s.lastIndexOf(":");
  if (s.indexOf(".", lastColon) >= 0) {
    const p = s.slice(lastColon + 1).split(".").map(Number);
    s = `${s.slice(0, lastColon + 1)}${((p[0] << 8) | p[1]).toString(16)}:${((p[2] << 8) | p[3]).toString(16)}`;
  }
  const halves = s.split("::");
  const head = halves[0] ? halves[0].split(":") : [];
  const tail = halves.length > 1 && halves[1] ? halves[1].split(":") : [];
  const fill = halves.length > 1 ? 8 - head.length - tail.length : 0;
  const groups = [...head, ...Array(fill).fill("0"), ...tail];
  if (groups.length !== 8) return null;
  groups.forEach((g, i) => out.writeUInt16BE(parseInt(g, 16), i * 2));
  return out;
}

/** Whether a 16-byte address is IPv4-mapped (::ffff:a.b.c.d). */
export function isMappedV4(bytes) {
  for (let i = 0; i < 10; i++) if (bytes[i] !== 0) return false;
  return bytes[10] === 0xff && bytes[11] === 0xff;
}

const lookups = new WeakMap();

/** The 2-letter country of `ip`, or 'ZZ' (no table, no match, not an address). */
export function lookupCountry(db, ip) {
  const bytes = ipToBytes(ip);
  if (!bytes) return UNKNOWN_COUNTRY;
  let stmt = lookups.get(db);
  if (!stmt) {
    stmt = db.prepare("SELECT end, country FROM geo WHERE start <= ? ORDER BY start DESC LIMIT 1");
    lookups.set(db, stmt);
  }
  const row = stmt.get(bytes);
  if (!row || Buffer.compare(bytes, Buffer.from(row.end)) > 0) return UNKNOWN_COUNTRY;
  return /^[A-Z]{2}$/.test(row.country) ? row.country : UNKNOWN_COUNTRY;
}

/** One CSV line `ip_start,ip_end,country` (quotes allowed) -> {start, end, country} or null. */
export function parseGeoLine(line) {
  const f = line.split(",").map((s) => s.trim().replace(/^"|"$/g, ""));
  if (f.length < 3) return null;
  const start = ipToBytes(f[0]);
  const end = ipToBytes(f[1]);
  const country = f[2].toUpperCase();
  if (!start || !end || !/^[A-Z]{2}$/.test(country)) return null;
  if (isMappedV4(start) !== isMappedV4(end) || Buffer.compare(start, end) > 0) return null;
  return { start, end, country };
}

/**
 * Replace the geo table with the ranges in `lines` (an iterable of CSV lines). Fills a new table in
 * chunks (so the running server's writes aren't blocked for long), then swaps it in in one short
 * transaction. Returns {rows, skipped}.
 */
export function loadGeo(db, lines, chunk = 20000) {
  db.exec("DROP TABLE IF EXISTS geo_new");
  db.exec("CREATE TABLE geo_new (start BLOB PRIMARY KEY, end BLOB NOT NULL, country TEXT NOT NULL) WITHOUT ROWID");
  const insert = db.prepare("INSERT OR REPLACE INTO geo_new (start, end, country) VALUES (?, ?, ?)");
  let rows = 0;
  let skipped = 0;
  let batch = [];
  const flush = () => {
    transaction(db, () => {
      for (const r of batch) insert.run(r.start, r.end, r.country);
    });
    rows += batch.length;
    batch = [];
  };
  for (const line of lines) {
    if (!line.trim()) continue;
    const r = parseGeoLine(line);
    if (!r) {
      skipped++;
      continue;
    }
    batch.push(r);
    if (batch.length >= chunk) flush();
  }
  if (batch.length) flush();
  transaction(db, () => {
    db.exec("DROP TABLE geo");
    db.exec("ALTER TABLE geo_new RENAME TO geo");
  });
  return { rows, skipped };
}
