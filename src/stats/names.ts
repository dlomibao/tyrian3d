// The names the stats page shows for the summary's ids, read from the game's own data the way the
// game labels them: level names from the episode scripts' `]L[` lines (levelsN.dat), episode and
// difficulty names from tyrian.hdt's menu texts, item names from its item data. Episode 4's item
// data (in tyrian4.lvl, 800 KB) has the same names for every id as tyrian.hdt's, so the page only
// fetches tyrian.hdt (150 KB) and the four scripts (32 KB). Without the data every name falls back to
// a plain label ("Level 9", "Ship 3").

import { episodeLevels, parseEpisodeScript } from "../data/episodeScript";
import { hdtItemDatOffset, parseItemDat } from "../data/items";
import { parseMenuText } from "../sim/helptext";
import { DIFFICULTIES } from "../../server/scores/lib/plausibility.mjs";

export const EPISODES = [1, 2, 3, 4] as const;

/** Item kinds by shop slot. */
export type ItemKind = "ship" | "weapon" | "shield" | "generator" | "sidekick";

export interface GameNames {
  /** True when the names came from the game data. */
  fromData: boolean;
  /** "Escape", "Treachery", ... (without the "Episode n:" part). */
  episode(ep: number): string;
  difficulty(level: number): string;
  /** The level's name in the episode, e.g. "SAVARA". */
  level(ep: number, lvl: number): string;
  /** The levels in the order the episode script first plays them (for tables). */
  levelOrder(ep: number): number[];
  /** Some of the episode's levels share a name (the later ones are shown with "(2)"). */
  sharedNames(ep: number): boolean;
  item(kind: ItemKind, id: number): string;
}

const tidy = (s: string | undefined) => (s ?? "").replace(/\s+/g, " ").trim();

const FALLBACK_DIFFICULTY: Record<number, string> = { 1: "Easy", 2: "Normal", 3: "Hard", 4: "Impossible", 6: "Suicide", 8: "Lord of Game" };
const KIND_LABEL: Record<ItemKind, string> = { ship: "Ship", weapon: "Weapon", shield: "Shield", generator: "Generator", sidekick: "Sidekick" };

/** Names from the files (null where one is missing), else the fallbacks. */
export function gameNames(hdt: Uint8Array | null, scripts: (Uint8Array | null)[]): GameNames {
  let episodeNames: string[] = [];
  let difficultyNames: string[] = [];
  const items: Record<ItemKind, string[]> = { ship: [], weapon: [], shield: [], generator: [], sidekick: [] };
  if (hdt) {
    try {
      const menu = parseMenuText(hdt);
      episodeNames = menu.episodeName.map((s) => tidy(s.replace(/^Episode\s*\d+\s*:\s*/i, "")));
      // difficulty_name[i + 1] is the i-th selectable difficulty (cheats.ts difficultyNamesByLevel).
      DIFFICULTIES.forEach((level, i) => (difficultyNames[level] = tidy(menu.difficultyName[i + 1])));
      const dat = parseItemDat(hdt, hdtItemDatOffset(hdt));
      items.ship = dat.ships.map((s) => tidy(s.name));
      items.weapon = dat.weaponPorts.map((s) => tidy(s.name));
      items.shield = dat.shields.map((s) => tidy(s.name));
      items.generator = dat.powerSys.map((s) => tidy(s.name));
      items.sidekick = dat.options.map((s) => tidy(s.name));
    } catch (err) {
      console.warn("tyrian.hdt didn't read", err);
    }
  }
  const levels = new Map<number, Map<number, string[]>>();
  const order = new Map<number, number[]>();
  const dupes = new Set<number>();
  scripts.forEach((data, i) => {
    if (!data) return;
    const ep = i + 1;
    try {
      const byLvl = new Map<number, string[]>();
      for (const ref of episodeLevels(parseEpisodeScript(data))) {
        const name = tidy(ref.levelName);
        const names = byLvl.get(ref.lvlFileNum) ?? [];
        if (name && !names.includes(name)) names.push(name);
        byLvl.set(ref.lvlFileNum, names);
      }
      // Two levels of one name (episode 1's TYRIAN, 9 and its hard twin 15; its two SAVARAs): the
      // later ones, in script order, get "(2)", "(3)" so tables and routes tell them apart.
      const seen = new Map<string, number>();
      for (const [lvl, names] of byLvl) {
        const key = names.join(" / ");
        const n = (seen.get(key) ?? 0) + 1;
        seen.set(key, n);
        if (n > 1) byLvl.set(lvl, [`${key} (${n})`]);
        if (n > 1) dupes.add(ep);
      }
      levels.set(ep, byLvl);
      order.set(ep, [...byLvl.keys()]);
    } catch (err) {
      console.warn(`levels${ep}.dat didn't read`, err);
    }
  });
  return {
    fromData: !!hdt && scripts.every((s) => s),
    episode: (ep) => episodeNames[ep] || `Episode ${ep}`,
    difficulty: (d) => difficultyNames[d] || FALLBACK_DIFFICULTY[d] || `Difficulty ${d}`,
    level: (ep, lvl) => levels.get(ep)?.get(lvl)?.join(" / ") || `Level ${lvl}`,
    levelOrder: (ep) => order.get(ep) ?? [],
    sharedNames: (ep) => dupes.has(ep),
    item: (kind, id) => (id === 0 ? "None" : items[kind][id] || `${KIND_LABEL[kind]} ${id}`),
  };
}

/** Fetch the files from the game's data folder (`dir`, e.g. "../tyrian-data/") and read the names. */
export async function loadGameNames(dir: string, fetcher: typeof fetch = fetch): Promise<GameNames> {
  const get = (name: string): Promise<Uint8Array | null> =>
    fetcher(`${dir}${name}`)
      .then((r) => (r.ok && !(r.headers.get("content-type") ?? "").includes("text/html") ? r.arrayBuffer() : null))
      .then((b) => (b && b.byteLength > 0 ? new Uint8Array(b) : null))
      .catch(() => null);
  const [hdt, ...scripts] = await Promise.all([get("tyrian.hdt"), ...EPISODES.map((ep) => get(`levels${ep}.dat`))]);
  return gameNames(hdt, scripts);
}
