// The deployed data's loader (DECISIONS.md D234): the boot files from one deflated zip when the
// site has it, one by one when it doesn't (the dev server, older deploys) or when it doesn't read,
// never the files the game doesn't read, and tyrend.anm only when asked for.
import { deflateRawSync } from "node:zlib";
import { readdirSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { DATA_ZIP, isBootFile, isGameFile, loadDataFolder, ON_DEMAND_FILES, type Fetcher } from "../../src/assets/files";
import { DATA_DIR, hasData } from "../data/dataDir";

/** A zip of these files (deflated), as the deploy script's zipfile writes one. */
function makeZip(files: Record<string, Uint8Array>): Uint8Array {
  const local: Buffer[] = [];
  const central: Buffer[] = [];
  let offset = 0;
  for (const [name, data] of Object.entries(files)) {
    const packed = deflateRawSync(data);
    const n = Buffer.from(name, "latin1");
    const head = Buffer.alloc(30);
    head.writeUInt32LE(0x04034b50, 0);
    head.writeUInt16LE(8, 8);
    head.writeUInt32LE(packed.length, 18);
    head.writeUInt32LE(data.length, 22);
    head.writeUInt16LE(n.length, 26);
    local.push(head, n, packed);
    const dir = Buffer.alloc(46);
    dir.writeUInt32LE(0x02014b50, 0);
    dir.writeUInt16LE(8, 10);
    dir.writeUInt32LE(packed.length, 20);
    dir.writeUInt32LE(data.length, 24);
    dir.writeUInt16LE(n.length, 28);
    dir.writeUInt32LE(offset, 42);
    central.push(dir, n);
    offset += 30 + n.length + packed.length;
  }
  const cd = Buffer.concat(central);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(Object.keys(files).length, 8);
  end.writeUInt16LE(Object.keys(files).length, 10);
  end.writeUInt32LE(cd.length, 12);
  end.writeUInt32LE(offset, 16);
  return new Uint8Array(Buffer.concat([...local, cd, end]));
}

const bytes = (s: string) => new TextEncoder().encode(s);

/** A served folder: `files` by name, logging every URL asked for. */
function server(files: Record<string, Uint8Array>): { get: Fetcher; asked: string[] } {
  const asked: string[] = [];
  return {
    asked,
    get: async (url) => {
      asked.push(url);
      return files[decodeURIComponent(url.replace(/^tyrian-data\//, ""))];
    },
  };
}

const DATA = {
  "tyrian.shp": bytes("ships"),
  "tyrian1.lvl": bytes("levels"),
  "shapes).dat": bytes("tiles"),
  "tyrend.anm": bytes("the ending"),
  "tyrianc.shp": bytes("unused"),
  "netarena.pcx": bytes("unused"),
  "tyrian.exe": bytes("dos"),
};
const index = (names: string[]) => bytes(JSON.stringify(names));
const NAMES = Object.keys(DATA);

describe("which files load", () => {
  test("the DOS programs, the files the game never reads and zips aren't game files; tyrend.anm waits", () => {
    for (const n of ["tyrian.exe", "tyrianc.shp", "voicesc.snd", "netarena.pcx", "NETFONT1.PCX", "tyrset.pcx", "shipedit.pcx", "loudness.awe", "user1.shp", "user2.shp", "exitmsg.bin", DATA_ZIP])
      expect(isGameFile(n), n).toBe(false);
    for (const n of ["tyrian.shp", "voices.snd", "tshp2.pcx", "newsh~.shp", "shapes).dat", "demo.1", "tyrend.anm"]) expect(isGameFile(n), n).toBe(true);
    expect(isBootFile("tyrend.anm")).toBe(false);
    expect([...ON_DEMAND_FILES]).toEqual(["tyrend.anm"]);
  });

  test.skipIf(!hasData("tyrian.shp"))("the 2.1 data: 66 boot files, tyrend.anm on demand", () => {
    const names = readdirSync(DATA_DIR);
    expect(names.filter(isBootFile)).toHaveLength(66);
    expect(names.filter((n) => isGameFile(n) && !isBootFile(n))).toEqual(["tyrend.anm"]);
  });
});

describe("loadDataFolder", () => {
  test("with the zip: one request for the boot files besides the list, unread zip entries dropped", async () => {
    const zip = makeZip({ "tyrian.shp": DATA["tyrian.shp"], "tyrian1.lvl": DATA["tyrian1.lvl"], "shapes).dat": DATA["shapes).dat"], "tyrianc.shp": DATA["tyrianc.shp"] });
    const s = server({ ...DATA, "index.json": index(NAMES), [DATA_ZIP]: zip });
    const files = (await loadDataFolder("tyrian-data/", s.get))!;
    expect(new Set(s.asked)).toEqual(new Set(["tyrian-data/index.json", `tyrian-data/${DATA_ZIP}`]));
    expect(files.get("TYRIAN.SHP")).toEqual(DATA["tyrian.shp"]);
    expect(files.get("shapes).dat")).toEqual(DATA["shapes).dat"]);
    expect(files.get("tyrianc.shp")).toBeUndefined();
    expect(files.size).toBe(3);
  });

  test("without the zip (a dev server, an older deploy): the boot files one by one, never the unread ones", async () => {
    const s = server({ ...DATA, "index.json": index(NAMES) });
    const files = (await loadDataFolder("tyrian-data/", s.get))!;
    expect(new Set(s.asked)).toEqual(new Set(["tyrian-data/index.json", `tyrian-data/${DATA_ZIP}`, "tyrian-data/tyrian.shp", "tyrian-data/tyrian1.lvl", "tyrian-data/shapes).dat"]));
    expect(files.get("tyrian1.lvl")).toEqual(DATA["tyrian1.lvl"]);
    expect(files.get("tyrend.anm")).toBeUndefined();
  });

  test("a zip that doesn't read, or lacks a file the list names: those files one by one", async () => {
    const broken = server({ ...DATA, "index.json": index(NAMES), [DATA_ZIP]: bytes("<!doctype html>") });
    const a = (await loadDataFolder("tyrian-data/", broken.get))!;
    expect(a.get("tyrian.shp")).toEqual(DATA["tyrian.shp"]);
    expect(a.size).toBe(3);
    const short = server({ ...DATA, "index.json": index(NAMES), [DATA_ZIP]: makeZip({ "tyrian.shp": DATA["tyrian.shp"] }) });
    const b = (await loadDataFolder("tyrian-data/", short.get))!;
    expect(short.asked.filter((u) => !/index\.json|\.zip$/.test(u)).sort()).toEqual(["tyrian-data/shapes).dat", "tyrian-data/tyrian1.lvl"]);
    expect(b.get("shapes).dat")).toEqual(DATA["shapes).dat"]);
  });

  test("tyrend.anm is fetched when first asked for, once", async () => {
    const s = server({ ...DATA, "index.json": index(NAMES), [DATA_ZIP]: makeZip({ "tyrian.shp": DATA["tyrian.shp"], "tyrian1.lvl": DATA["tyrian1.lvl"], "shapes).dat": DATA["shapes).dat"] }) });
    const files = (await loadDataFolder("tyrian-data/", s.get))!;
    expect(s.asked).not.toContain("tyrian-data/tyrend.anm");
    expect(files.get("tyrend.anm")).toBeUndefined();
    const [x, y] = await Promise.all([files.load("tyrend.anm"), files.load("TYREND.ANM")]);
    expect(x).toEqual(DATA["tyrend.anm"]);
    expect(y).toBe(x);
    expect(files.get("tyrend.anm")).toBe(x);
    await files.load("tyrend.anm");
    expect(s.asked.filter((u) => u.endsWith("tyrend.anm"))).toHaveLength(1);
    // A file the list doesn't name, or a boot file, is what get() says.
    expect(await files.load("nothing.dat")).toBeUndefined();
    expect(await files.load("tyrian.shp")).toBe(files.get("tyrian.shp"));
  });

  test("no list (no data served, or a fallback page): null", async () => {
    expect(await loadDataFolder("tyrian-data/", server({}).get)).toBeNull();
    expect(await loadDataFolder("tyrian-data/", server({ "index.json": bytes("<!doctype html>") }).get)).toBeNull();
    expect(await loadDataFolder("tyrian-data/", server({ "index.json": index([]) }).get)).toBeNull();
  });
});
