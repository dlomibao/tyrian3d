// Where the Tyrian data comes from in the browser (DECISIONS.md D3).

import type { TyrianFiles } from "../sim/resources";

export class FileMap implements TyrianFiles {
  private readonly pending = new Map<string, Promise<Uint8Array | undefined>>();

  /**
   * `later`: how to fetch a file the boot left out (ON_DEMAND_FILES); undefined if it can't be
   * had. Each is fetched when load() first asks for it, and kept.
   */
  constructor(
    private readonly files: Map<string, Uint8Array>,
    private readonly later?: (name: string) => Promise<Uint8Array | undefined>,
  ) {}

  get(name: string): Uint8Array | undefined {
    return this.files.get(name.toLowerCase());
  }

  /** The file, fetched first if it's one the boot left for later (tyrend.anm). */
  load(name: string): Promise<Uint8Array | undefined> {
    const key = name.toLowerCase();
    const have = this.files.get(key);
    if (have || !this.later) return Promise.resolve(have);
    let p = this.pending.get(key);
    if (!p) {
      p = this.later(key)
        .catch((err) => (console.warn(`couldn't fetch ${key}`, err), undefined))
        .then((data) => {
          if (data) this.files.set(key, data);
          this.pending.delete(key); // kept in files, or tried again next time
          return data;
        });
      this.pending.set(key, p);
    }
    return p;
  }

  get size(): number {
    return this.files.size;
  }
}

/**
 * Files in the 2.1 data the port never reads (each name grepped in src/, D234): tyrianc.shp and
 * voicesc.snd (OpenTyrian's Christmas mode, opentyr.c L813-821, not ported), user1/2.shp,
 * tyrset.pcx, shipedit.pcx, net*.pcx, loudness.awe and exitmsg.bin (not read by OpenTyrian either).
 */
const UNUSED = /^(tyrianc\.shp|voicesc\.snd|user[12]\.shp|tyrset\.pcx|shipedit\.pcx|net[^/]*\.pcx|loudness\.awe|exitmsg\.bin)$/i;

/** Game files worth loading (skips the DOS executables, docs and zips, and the files the game never reads). */
export const isGameFile = (name: string): boolean => !/\.(exe|doc|ovl|diz|com|bat|txt|ini|int|box|tfp|ico|zip)$/i.test(name) && !UNUSED.test(name);

/**
 * Game files fetched only when asked for (FileMap.load), not at boot (D234): tyrend.anm (3.3 MB),
 * which only episode 3's ending reads, and then only when the remastered video (D219) isn't played.
 */
export const ON_DEMAND_FILES: ReadonlySet<string> = new Set(["tyrend.anm"]);

/** Game files a boot fetches: what the deployed data zip (DATA_ZIP) holds. */
export const isBootFile = (name: string): boolean => isGameFile(name) && !ON_DEMAND_FILES.has(name.toLowerCase());

/**
 * The boot files as one deflated zip beside the files, made by the site's deploy (D234); the dev
 * server and older deploys have none, and the files are fetched one by one.
 */
export const DATA_ZIP = "boot.zip";

/** Fetches `url`'s bytes: undefined if it isn't there (a 404, or no network). */
export type Fetcher = (url: string) => Promise<Uint8Array | undefined>;

const fetchBytes: Fetcher = (url) =>
  fetch(url)
    .then((r) => (r.ok ? r.arrayBuffer() : undefined))
    .then((b) => (b ? new Uint8Array(b) : undefined))
    .catch(() => undefined);

/**
 * Load the boot files from `dir`, which index.json lists (D234): from DATA_ZIP, fetched alongside
 * the list, and any boot file the list names that the zip lacks (all of them without a zip, or with
 * one that doesn't read) one by one. Null without a list. ON_DEMAND_FILES are left for FileMap.load.
 */
export async function loadDataFolder(dir: string, get: Fetcher = fetchBytes): Promise<FileMap | null> {
  const [listBytes, zip] = await Promise.all([get(`${dir}index.json`), get(`${dir}${DATA_ZIP}`)]);
  let list: unknown = null;
  try {
    if (listBytes) list = JSON.parse(new TextDecoder().decode(listBytes));
  } catch {
    // A dev server's fallback page: no data here.
  }
  if (!Array.isArray(list)) return null;
  const names = list.filter((n): n is string => typeof n === "string");
  if (names.length === 0) return null;
  const map = new Map<string, Uint8Array>();
  if (zip) {
    try {
      const { readZip } = await import("./zip");
      for (const entry of await readZip(zip)) {
        const name = entry.name.split("/").pop()!.toLowerCase();
        if (isBootFile(name)) map.set(name, entry.data);
      }
    } catch (err) {
      console.warn(`${dir}${DATA_ZIP} didn't read; fetching the data files one by one`, err);
      map.clear();
    }
  }
  const missing = names.filter((n) => isBootFile(n) && !map.has(n.toLowerCase()));
  const fetched = await Promise.all(missing.map(async (n) => [n.toLowerCase(), await get(`${dir}${encodeURIComponent(n)}`)] as const));
  for (const [name, data] of fetched) if (data) map.set(name, data);
  const later = new Map(names.filter((n) => ON_DEMAND_FILES.has(n.toLowerCase())).map((n) => [n.toLowerCase(), n]));
  return new FileMap(map, async (name) => {
    const n = later.get(name);
    return n === undefined ? undefined : get(`${dir}${encodeURIComponent(n)}`);
  });
}

/**
 * Dev server or local build (`npm run play:local`, and the deployed site): load the data from
 * /tyrian-data/ (served from the local data/ folder by vite.config.ts). The public build never asks.
 */
export async function loadDevFiles(): Promise<FileMap | null> {
  if (!import.meta.env.DEV && import.meta.env.VITE_LOCAL_DATA !== "1") return null;
  return loadDataFolder("tyrian-data/");
}

/** Build the game's file map from tyrian21.zip (or any zip holding the data, nested or not). */
export async function filesFromZip(zip: Uint8Array): Promise<FileMap> {
  const { readZip } = await import("./zip");
  const map = new Map<string, Uint8Array>();
  for (const entry of await readZip(zip)) {
    const name = entry.name.split("/").pop()!.toLowerCase();
    if (isGameFile(name)) map.set(name, entry.data);
  }
  if (!map.has("tyrian1.lvl") || !map.has("tyrian.shp")) throw new Error("that zip doesn't contain the Tyrian 2.1 data");
  return new FileMap(map);
}
