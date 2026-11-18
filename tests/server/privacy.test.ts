// Geo lookup, the salted IP hash, that no address is ever stored, and the service as a process.
import { afterAll, describe, expect, test } from "vitest";
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { openDb } from "../../server/scores/lib/db.mjs";
import { ipToBytes, loadGeo, lookupCountry } from "../../server/scores/lib/geo.mjs";
import { ipHash } from "../../server/scores/lib/ratelimit.mjs";
import { GEO_FIXTURE, HOUR, SALT, SECRET, from, newRun, report, startApi, submit, validRun } from "./helpers";

const tmp = mkdtempSync(join(tmpdir(), "tyrian-scores-geo-"));
afterAll(() => rmSync(tmp, { recursive: true, force: true }));

describe("geo", () => {
  test("address bytes", () => {
    expect(ipToBytes("1.2.3.4")?.toString("hex")).toBe("00000000000000000000ffff01020304");
    expect(ipToBytes("::ffff:1.2.3.4")?.toString("hex")).toBe("00000000000000000000ffff01020304");
    expect(ipToBytes("::")?.toString("hex")).toBe("0".repeat(32));
    expect(ipToBytes("2001:db8::1")?.toString("hex")).toBe("20010db8000000000000000000000001");
    expect(ipToBytes("fe80::1%en0")?.toString("hex")).toBe("fe800000000000000000000000000001");
    expect(ipToBytes("1:2:3:4:5:6:7:8")?.toString("hex")).toBe("00010002000300040005000600070008");
    expect(ipToBytes("nope")).toBeNull();
    expect(ipToBytes("1.2.3.256")).toBeNull();
  });

  test("lookups: IPv4, IPv6, unknown, empty table", () => {
    const db = openDb(join(tmp, "geo.db"));
    expect(lookupCountry(db, "192.0.2.10")).toBe("ZZ"); // empty table
    const { rows, skipped } = loadGeo(db, readFileSync(GEO_FIXTURE, "utf8").split("\n"));
    expect(rows).toBe(6);
    expect(skipped).toBe(0);
    expect(lookupCountry(db, "192.0.2.10")).toBe("AU");
    expect(lookupCountry(db, "192.0.2.255")).toBe("AU");
    expect(lookupCountry(db, "::ffff:192.0.2.0")).toBe("AU");
    expect(lookupCountry(db, "192.0.3.0")).toBe("ZZ");
    expect(lookupCountry(db, "198.51.100.127")).toBe("US");
    expect(lookupCountry(db, "198.51.100.128")).toBe("ZZ"); // past the range's end
    expect(lookupCountry(db, "203.0.113.200")).toBe("JP"); // quoted CSV fields
    expect(lookupCountry(db, "2001:db8::1")).toBe("NZ");
    expect(lookupCountry(db, "2001:db8:ffff:ffff:ffff:ffff:ffff:ffff")).toBe("NZ");
    expect(lookupCountry(db, "2001:db9::1")).toBe("DE");
    expect(lookupCountry(db, "2001:db9::1:0")).toBe("ZZ");
    expect(lookupCountry(db, "2001:dba::1")).toBe("ZZ");
    expect(lookupCountry(db, "8.8.8.8")).toBe("ZZ");
    expect(lookupCountry(db, "garbage")).toBe("ZZ");
    // A reload replaces the table.
    loadGeo(db, ["10.0.0.0,10.255.255.255,FR", "ip_start,ip_end,country", "bad,row,XX"]);
    expect(lookupCountry(db, "192.0.2.10")).toBe("ZZ");
    expect(lookupCountry(db, "10.1.2.3")).toBe("FR");
    db.close();
  });

  test("tools/load-geo.mjs", () => {
    const dbPath = join(tmp, "cli.db");
    for (let i = 0; i < 2; i++) {
      const r = spawnSync(process.execPath, ["--disable-warning=ExperimentalWarning", "server/scores/tools/load-geo.mjs", GEO_FIXTURE, dbPath], { encoding: "utf8" });
      expect(r.status, r.stderr).toBe(0);
      expect(JSON.parse(r.stdout)).toEqual({ rows: 6, skipped: 0 });
    }
    const db = openDb(dbPath);
    expect(db.prepare("SELECT count(*) AS n FROM geo").get()).toEqual({ n: 6 });
    db.close();
  });
});

describe("IP hash", () => {
  const nov = Date.UTC(2026, 10, 30, 23, 30);
  const dec = Date.UTC(2026, 11, 1, 0, 10);
  test("salted, rotating monthly", () => {
    const h = ipHash(SALT, "203.0.113.77", nov);
    expect(h).toMatch(/^[0-9a-f]{64}$/);
    expect(ipHash(SALT, "203.0.113.77", Date.UTC(2026, 10, 1))).toBe(h);
    expect(ipHash(SALT, "::ffff:203.0.113.77", nov)).toBe(h);
    expect(ipHash(SALT, "203.0.113.77", dec)).not.toBe(h);
    expect(ipHash(SALT + "x", "203.0.113.77", nov)).not.toBe(h);
    expect(ipHash(SALT, "203.0.113.78", nov)).not.toBe(h);
    // IPv6: one /64.
    expect(ipHash(SALT, "2001:db8:1:2::1", nov)).toBe(ipHash(SALT, "2001:db8:1:2:ffff::9", nov));
    expect(ipHash(SALT, "2001:db8:1:2::1", nov)).not.toBe(ipHash(SALT, "2001:db8:1:3::1", nov));
  });

  test("a new month is a new hash, so a new limit window", async () => {
    const api = await startApi({}, nov);
    try {
      for (let i = 0; i < 30; i++) await newRun(api, {}, from("203.0.113.77"));
      expect((await api.call("POST", "/api/runs", { episode: 1, difficulty: 2, mode: "story", build: "t" }, from("203.0.113.77"))).status).toBe(429);
      api.clock.t = dec; // 40 minutes later: the hour isn't over, but the month is
      await newRun(api, {}, from("203.0.113.77"));
    } finally {
      await api.close();
    }
  });
});

describe("no address is stored", () => {
  test("the database holds neither the text nor the bytes of a client address", async () => {
    const api = await startApi({ limits: { runs: 1000, scores: 1000 } });
    try {
      loadGeo(api.app.db, readFileSync(GEO_FIXTURE, "utf8").split("\n"));
      const ips = ["203.0.113.77", "192.0.2.10", "2001:db8::4242:77"];
      const player = crypto.randomUUID();
      const tokens: string[] = [];
      for (const ip of ips) tokens.push(await newRun(api, { playerId: player }, from(ip)));
      api.clock.t += HOUR;
      for (const [i, ip] of ips.entries()) {
        expect((await submit(api, validRun(tokens[i]), `Player ${i}`, {}, from(ip))).status).toBe(200);
        expect((await submit(api, validRun(tokens[i]), `Player ${i}`, {}, from(ip))).status).toBe(422); // a rejected row too
        expect((await api.call("POST", "/api/levels/report", report(tokens[i], player), from(ip))).status).toBe(204);
      }
      const countries = api.app.db.prepare("SELECT DISTINCT country FROM levels ORDER BY country").all().map((r) => (r as { country: string }).country);
      expect(countries).toEqual(["AU", "NZ", "ZZ"]);

      const files = [api.dbPath, `${api.dbPath}-wal`].filter(existsSync);
      expect(files.length).toBeGreaterThan(0);
      const bytes = Buffer.concat(files.map((f) => readFileSync(f)));
      for (const ip of ips) {
        const raw = ipToBytes(ip)!;
        const needles = [Buffer.from(ip), Buffer.from(ip.toUpperCase()), raw, raw.subarray(12), Buffer.from(raw.toString("hex")), Buffer.from(ipHash(SALT, ip, api.clock.t))];
        for (const n of needles) expect(bytes.indexOf(n), `${ip}: ${n.toString("hex")}`).toBe(-1);
      }
      // The player id is stored (stats sharing on); no hash sits next to it.
      expect(bytes.indexOf(Buffer.from(player))).toBeGreaterThan(-1);
    } finally {
      await api.close();
    }
  });
});

describe("the service as a process", () => {
  const env = (over: Record<string, string>) => ({ PATH: process.env.PATH ?? "", HOME: tmp, SCORES_DB: join(tmp, "proc.db"), PORT: "0", SCORES_HMAC_SECRET: SECRET, SCORES_IP_SALT: SALT, ...over });

  test("refuses to start without a strong secret", () => {
    const r = spawnSync(process.execPath, ["server/scores/server.mjs"], { env: env({ SCORES_HMAC_SECRET: "short" }), encoding: "utf8", timeout: 10000 });
    expect(r.status).toBe(1);
    expect(r.stderr).toContain("SCORES_HMAC_SECRET");
    const s = spawnSync(process.execPath, ["server/scores/server.mjs"], { env: env({ SCORES_IP_SALT: "" }), encoding: "utf8", timeout: 10000 });
    expect(s.status).toBe(1);
    expect(s.stderr).toContain("SCORES_IP_SALT");
  });

  test("PORT=0 prints the bound port and serves", async () => {
    const child = spawn(process.execPath, ["--disable-warning=ExperimentalWarning", "server/scores/server.mjs"], { env: env({}), stdio: ["ignore", "pipe", "pipe"] });
    try {
      const port = await new Promise<number>((resolve, reject) => {
        let out = "";
        child.stdout.on("data", (c) => {
          out += c;
          const line = out.split("\n").find((l) => l.startsWith("{"));
          if (line) resolve(JSON.parse(line).listening);
        });
        child.on("exit", (code) => reject(new Error(`exited ${code}`)));
        setTimeout(() => reject(new Error("timeout")), 10000);
      });
      expect(port).toBeGreaterThan(0);
      const r = await fetch(`http://127.0.0.1:${port}/api/health`);
      expect(await r.json()).toEqual({ ok: true, db: true });
    } finally {
      child.kill("SIGTERM");
    }
  });
});
