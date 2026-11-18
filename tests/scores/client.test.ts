// The game's side of the shared high-score list (src/scores/, src/sim/runRecord.ts): every taint
// source taints and blocks the submission, the taint survives a save and a load, the stats id and
// its toggle, and the play reports (none when the toggle is off).
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const DATA = hasData("tyrian1.lvl", "tyrian.hdt", "tyrian.shp");

/** A Web Storage stand-in. */
function memoryStorage() {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), m };
}

/** Fresh modules with the shared list on (VITE_SCORES_API) or off. */
async function load(api: string | null) {
  vi.resetModules();
  if (api) vi.stubEnv("VITE_SCORES_API", api);
  else vi.stubEnv("VITE_SCORES_API", "");
  const listeners: Record<string, ((e: unknown) => void)[]> = {};
  vi.stubGlobal("window", { addEventListener: (t: string, f: (e: unknown) => void) => (listeners[t] ??= []).push(f) });
  vi.stubGlobal("localStorage", memoryStorage());
  const calls: { url: string; body: unknown }[] = [];
  vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
    calls.push({ url, body: init?.body ? JSON.parse(String(init.body)) : null });
    if (url.endsWith("/runs")) return new Response(JSON.stringify({ token: "tok.sig", issuedAt: Date.now() - 3_600_000 }));
    if (url.endsWith("/scores")) return new Response(JSON.stringify({ ok: true, rank: 1, total: 1 }));
    return new Response("{}");
  });
  const beacons: unknown[] = [];
  vi.stubGlobal("navigator", { sendBeacon: (_u: string, b: Blob) => (void b.text().then((t) => beacons.push(JSON.parse(t))), true) });
  const state = await import("../../src/sim/state");
  const resources = await import("../../src/sim/resources");
  const newgame = await import("../../src/sim/newgame");
  const helptext = await import("../../src/sim/helptext");
  const rec = await import("../../src/sim/runRecord");
  const session = await import("../../src/scores/session");
  const statsId = await import("../../src/scores/statsId");
  const savegame = await import("../../src/sim/savegame");
  const cheatKeys = await import("../../src/app/cheatKeys");
  const bridge = await import("../../src/app/consoleBridge");
  statsId.setStatsStorage(memoryStorage());
  savegame.setSaveStorage(memoryStorage());
  if (DATA) {
    state.g.res = resources.buildResources(files, 1);
    helptext.loadHelpText(readData("tyrian.hdt"));
  }
  newgame.newOnePlayerGame(1, 2);
  return { g: state.g, rec, session, statsId, savegame, cheatKeys, bridge, calls, beacons, listeners };
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe.skipIf(!DATA)("taint", { timeout: 30000 }, () => {
  let m: Awaited<ReturnType<typeof load>>;
  beforeEach(async () => {
    m = await load("/api");
  }, 30000);

  /** Start a run, let the token arrive, taint it with `how`, then try to submit. */
  async function taintedSubmission(how: () => void | Promise<void>) {
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "story");
    expect(m.rec.runRecord.current?.token).toBe("tok.sig");
    m.rec.runRecord.current!.levels.push({ lvl: 9, ticks: 3000, score: 25000, done: true });
    expect(m.session.ineligibleReason(1)).toBeNull();
    await how();
    expect(m.rec.runRecord.current?.tainted).toBe(true);
    expect(m.session.ineligibleReason(1)).toMatch(/Cheats or debug tools/);
    const before = m.calls.length;
    expect(await m.session.submitHighScore("ACE", 30000, 1, "quit")).toBeNull();
    expect(m.calls.slice(before).filter((c) => c.url.endsWith("/scores"))).toEqual([]);
  }

  test("a clean run submits", async () => {
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "story");
    expect(m.session.ineligibleReason(1)).toMatch(/Play a level/);
    m.rec.runRecord.current!.levels.push({ lvl: 9, ticks: 3000, score: 25000, done: true });
    const r = await m.session.submitHighScore("ACE", 25000, 1, "quit");
    expect(r).toEqual({ ok: true, rank: 1, total: 1 });
    const body = m.calls.find((c) => c.url === "/api/scores")!.body as Record<string, unknown>;
    expect(body).toMatchObject({ token: "tok.sig", episode: 1, difficulty: 2, mode: "story", name: "ACE", score: 25000, levels: [{ lvl: 9, ticks: 3000, score: 25000, done: true }] });
    expect(body.hash).toMatch(/^[0-9a-f]{64}$/);
  });

  test("the debug console (opened, or run from devtools)", async () => {
    await taintedSubmission(async () => {
      m.bridge.installDebugConsole();
      const tc = (window as unknown as { tyrianConsole: { run(l: string): Promise<unknown> } }).tyrianConsole;
      await tc.run("help").catch(() => {});
    });
    // and it lasts for the page session: the next run starts tainted
    await m.session.startRun(1, 2, "story");
    expect(m.rec.runRecord.current?.taints).toEqual(["console"]);
  });

  test("the debug console screen", async () => {
    await taintedSubmission(() => void m.bridge.showDebugConsole().catch(() => {}));
  });

  test("the cheat chords in flight", async () => {
    const chords = [
      ["F2", "F4", "F6", "F7", "F9", "Backslash", "Slash"], // Nort ship
      ["F2", "F3", "F6"], // invulnerability
      ["F2", "F3", "F4"], // self-destruct
      ["F2", "F6", "F7"], // skip level
    ];
    for (const c of chords) expect(m.cheatKeys.isCheatChord(new Set(c))).toBe(true);
    expect(m.cheatKeys.isCheatChord(new Set(["F2", "F6", "F7", "F9"]))).toBe(false);
    expect(m.cheatKeys.isCheatChord(new Set(["ArrowLeft", "Space"]))).toBe(false);
    await taintedSubmission(() => {
      const keys = new m.cheatKeys.CheatKeys(() => true);
      for (const code of ["F2", "F3", "F6"]) for (const f of m.listeners.keydown) f({ code, repeat: false, preventDefault() {} });
      keys.poll();
    });
    expect(m.rec.runRecord.current?.taints).toEqual(["cheat-keys"]);
  });

  test.each([["?loot"], ["?seed=5"], ["?debug=play&episode=1"]])("the URL %s", async (search) => {
    m.session.initScoresSession(search);
    await m.session.startRun(1, 2, "story");
    expect(m.rec.runRecord.current?.tainted).toBe(true);
    expect(await m.session.submitHighScore("ACE", 30000, 1, "quit")).toBeNull();
    expect(m.calls.filter((c) => c.url.endsWith("/scores"))).toEqual([]);
  });

  test("look parameters don't taint", () => {
    expect(m.session.urlTaints("?bg=original&vfx=original&terrain=hd&compare=1&camera=steep")).toEqual([]);
  });

  test("not eligible without a taint: arcade and two-player, another episode, no token", async () => {
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "arcade");
    expect(m.session.ineligibleReason(1)).toMatch(/one-player full games/);
    await m.session.startRun(1, 2, "story");
    expect(m.session.ineligibleReason(2)).toMatch(/episode the game started on/);
    m.rec.runRecord.current!.token = null;
    expect(m.session.ineligibleReason(1)).toMatch(/couldn't be reached/);
  });

  test("the taint survives a save and a load, and a reload of the page", async () => {
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "story");
    m.rec.taintRun("cheat-keys");
    m.g.saveLevel = 3;
    m.savegame.JE_saveGame(1, "TAINTED");
    const stored = m.savegame.serializeSaves();
    expect(JSON.parse(stored).slots[0].run).toMatchObject({ tainted: true, taints: ["cheat-keys"], token: "tok.sig" });

    // A new page: nothing in memory, the slots from storage.
    const n = await load("/api");
    n.session.initScoresSession("");
    const storage = memoryStorage();
    storage.setItem(n.savegame.SAVE_STORAGE_KEY, stored);
    n.savegame.setSaveStorage(storage);
    n.savegame.loadSaves();
    expect(n.rec.runRecord.current).toBeNull();
    n.savegame.JE_loadGame(1, files);
    expect(n.rec.runRecord.current).toMatchObject({ tainted: true, token: "tok.sig" });
    expect(await n.session.submitHighScore("ACE", 30000, 1, "quit")).toBeNull();
  });

  test("the retry backup can't wash out a taint", async () => {
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "story");
    m.savegame.JE_saveGame(11, "LAST LEVEL    "); // clean backup, before the level
    m.rec.taintRun("cheat-keys"); // a cheat, then the ship is lost
    m.savegame.JE_loadGame(11, files);
    expect(m.rec.runRecord.current?.tainted).toBe(true);
  });

  test("without the shared list, saves are as before (no run field)", async () => {
    const n = await load(null);
    n.session.initScoresSession("?loot");
    await n.session.startRun(1, 2, "story");
    n.savegame.JE_saveGame(1, "PLAIN");
    expect(JSON.parse(n.savegame.serializeSaves()).slots[0]).not.toHaveProperty("run");
    expect(n.calls).toEqual([]);
    expect(await n.session.submitHighScore("ACE", 30000, 1, "quit")).toBeNull();
    expect(n.calls).toEqual([]);
  });
});

describe.skipIf(!DATA)("stats id and play reports", { timeout: 30000 }, () => {
  test("the id is made only while sharing is on; reset makes a new one", async () => {
    const m = await load("/api");
    expect(m.statsId.storedStatsPlayerId()).toBeNull();
    m.statsId.setStatsSharing(false);
    expect(m.statsId.statsPlayerId()).toBeNull();
    expect(m.statsId.storedStatsPlayerId()).toBeNull();
    m.statsId.setStatsSharing(true);
    const id = m.statsId.statsPlayerId()!;
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(m.statsId.statsPlayerId()).toBe(id);
    const fresh = m.statsId.resetStatsPlayerId();
    expect(fresh).not.toBe(id);
    expect(m.statsId.statsPlayerId()).toBe(fresh);
  });

  /** Play a "level" through the session hooks. */
  async function playOne(m: Awaited<ReturnType<typeof load>>, outcome: "completed" | "died" | "quit") {
    m.g.lvlFileNum = 9;
    m.g.levelName = "TYRIAN   ";
    m.session.levelStart();
    for (let i = 0; i < 30; i++) m.session.levelTick();
    m.g.player[0].cash += 1234;
    m.session.levelEnd(outcome);
    await new Promise((r) => setTimeout(r, 10));
  }

  test("a report per level with the id; the run token carries it too", async () => {
    const m = await load("/api");
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "story");
    const id = m.statsId.storedStatsPlayerId();
    expect(m.calls[0].body).toMatchObject({ episode: 1, difficulty: 2, mode: "story", playerId: id });
    await playOne(m, "completed");
    await playOne(m, "died");
    expect(m.beacons).toHaveLength(2);
    expect(m.beacons[0]).toMatchObject({
      v: 1,
      token: "tok.sig",
      playerId: id,
      tainted: false,
      run: { episode: 1, difficulty: 2, mode: "story" },
      level: { lvl: 9, name: "TYRIAN", index: 0, prev: null, via: "start" },
      outcome: { result: "finished", ticks: 30, scoreGained: 1234 },
    });
    expect(m.beacons[1]).toMatchObject({ level: { index: 1, prev: 9, via: "story" }, outcome: { result: "died" } });
    expect(m.rec.runRecord.current?.levels).toEqual([{ lvl: 9, ticks: 30, score: expect.any(Number), done: true }]);
  });

  test("cheated runs are reported, flagged", async () => {
    const m = await load("/api");
    m.session.initScoresSession("?seed=3");
    await m.session.startRun(1, 2, "story");
    await playOne(m, "completed");
    expect(m.beacons[0]).toMatchObject({ tainted: true });
  });

  test("sharing off: no id on the run token, no reports; scores still go", async () => {
    const m = await load("/api");
    m.statsId.setStatsSharing(false);
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "story");
    expect(m.calls[0].body).not.toHaveProperty("playerId");
    await playOne(m, "completed");
    await playOne(m, "quit");
    expect(m.beacons).toEqual([]);
    expect(m.statsId.storedStatsPlayerId()).toBeNull();
    expect(await m.session.submitHighScore("ACE", 30000, 1, "quit")).toMatchObject({ ok: true });
  });

  test("a quit level goes into the submission unfinished", async () => {
    const m = await load("/api");
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "story");
    await playOne(m, "quit");
    await m.session.submitHighScore("ACE", 20734, 1, "quit");
    const body = m.calls.find((c) => c.url === "/api/scores")!.body as { levels: unknown[] };
    expect(body.levels).toEqual([{ lvl: 9, ticks: 30, score: expect.any(Number), done: false }]);
  });

  test("going on into the next episode: a new run for its reports, taints kept", async () => {
    const m = await load("/api");
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "story");
    const first = m.rec.runRecord.current!;
    m.rec.taintRun("cheat-keys");
    await playOne(m, "completed");
    m.g.episodeNum = 2;
    await playOne(m, "completed");
    const second = m.rec.runRecord.current!;
    expect(second.runId).not.toBe(first.runId);
    expect(second).toMatchObject({ episode: 2, tainted: true, taints: ["cheat-keys"] });
    expect(m.calls.filter((c) => c.url === "/api/runs").map((c) => (c.body as { episode: number }).episode)).toEqual([1, 2]);
  });

  test("the item screen's trades go with the next report", async () => {
    const m = await load("/api");
    m.session.initScoresSession("");
    await m.session.startRun(1, 2, "story");
    m.session.shopStart();
    m.g.player[0].items.weapon[0].power += 1;
    m.g.player[0].items.shield = 2;
    m.session.shopEnd();
    await playOne(m, "completed");
    const shop = (m.beacons[0] as { shop: { kind: string; slot: string }[] }).shop;
    expect(shop.map((t) => `${t.kind} ${t.slot}`)).toEqual(["upgrade front", "sell shield", "buy shield"]);
  });
});
