// The debug console's shop lists (D110): which items the item screen sells, per Upgrade Ship
// category, so the shop can be seen with any selection. `shop all` sells everything the real game
// sells somewhere (the union of every item screen's lists in episodes 1-4, read from the episode
// scripts as the sim reads an `]I[`); `shop set|add|remove|clear` edit one category. The lists live
// in the sim's override layer (setConsoleShopList in src/sim/game_menu.ts), never in the level's own
// itemAvail rows, and only for this page: never saved, never in a saved game. They stay on through
// level changes and new games until `shop reset` (or `shop all off`).

import { parseEpisodeScript } from "../../data/episodeScript";
import { OPTION_NUM, PORT_NUM, POWER_NUM, SHIELD_NUM, SHIP_NUM } from "../../data/items";
import { consoleShopList, itemAvailMap, JE_itemScreen_listsChanged, merchantOrder, setConsoleShopList, shopListShown } from "../../sim/game_menu";
import type { TyrianFiles } from "../../sim/resources";
import { g } from "../../sim/state";
import { itemAvailLine } from "../../sim/tyrian2";

export type ShopCategoryKey = "ships" | "front" | "rear" | "shields" | "generators" | "left" | "right";

/** One Upgrade Ship category: its list in the shop and the items that can go in it. */
export interface ShopCategory {
  key: ShopCategoryKey;
  /** The Upgrade Ship choice (curSel[MENU_UPGRADES]): 2 ship .. 8 right sidekick. */
  sel: number;
  /** The itemAvail row (0-based) the shop sells this category from (itemAvailMap). */
  row: number;
  /** Other words for it (any case; spaces, dashes and a final "s" don't matter). */
  aliases: readonly string[];
  /** The shop's own name when the data isn't loaded. */
  fallback: string;
  /** The item ids that can be fitted here: the item table's range (0 = None where the game sells None). */
  min: number;
  max: number;
}

const cat = (key: ShopCategoryKey, sel: number, aliases: string[], fallback: string, min: number, max: number): ShopCategory => ({
  key,
  sel,
  row: itemAvailMap[sel - 2] - 1,
  aliases,
  fallback,
  min,
  max,
});

/** The categories in the shop's order (Upgrade Ship's rows). */
export const SHOP_CATEGORIES: readonly ShopCategory[] = [
  cat("ships", 2, ["ship", "shiptype", "hull"], "Ship Type", 1, SHIP_NUM),
  cat("front", 3, ["f", "frontgun", "frontweapon", "fg"], "Front Gun", 1, PORT_NUM),
  cat("rear", 4, ["rg", "reargun", "rearweapon", "back"], "Rear Gun", 0, PORT_NUM),
  cat("shields", 5, ["shield", "sh"], "Shield", 1, SHIELD_NUM),
  cat("generators", 6, ["generator", "gen", "power", "powersystem"], "Generator", 1, POWER_NUM),
  cat("left", 7, ["l", "ls", "leftsidekick", "sidekickleft", "leftoption"], "Left Sidekick", 0, OPTION_NUM),
  cat("right", 8, ["r", "rs", "rightsidekick", "sidekickright", "rightoption"], "Right Sidekick", 0, OPTION_NUM),
];

/** A word for matching: lower case, letters and digits only. */
const key = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");

/** The category a word names (its key, an alias, either with a final "s"), or undefined. */
export function findCategory(word: string): ShopCategory | undefined {
  const k = key(word);
  if (!k) return undefined;
  const names = (c: ShopCategory) => [c.key, ...c.aliases].map(key);
  return SHOP_CATEGORIES.find((c) => names(c).some((n) => n === k || `${n}s` === k || n === `${k}s`));
}

/** The shop's name for a category ("Front Gun"), from the help text the shop draws. */
export function categoryLabel(c: ShopCategory): string {
  return (g.menuInt?.[2]?.[c.sel - 1] ?? "").trim() || c.fallback;
}

/** The item table for a category, as the shop names and prices from it (itemName, JE_getCost). */
function table(c: ShopCategory): readonly { name: string; cost: number }[] {
  const it = g.res?.items;
  if (!it) return [];
  switch (c.sel) {
    case 2: return it.ships;
    case 3:
    case 4: return it.weaponPorts;
    case 5: return it.shields;
    case 6: return it.powerSys;
    default: return it.options;
  }
}

/** An item's name in a category ("Pulse-Cannon"; spaces in the data squeezed). */
export function itemLabel(c: ShopCategory, id: number): string {
  const name = table(c)[id]?.name.replace(/\s+/g, " ").trim();
  return name || (id === 0 ? "None" : `#${id}`);
}

/** An item's price before weapon power (the item data's cost; JE_getCost adds the power's upgrades). */
export function itemCost(c: ShopCategory, id: number): number {
  return table(c)[id]?.cost ?? 0;
}

/** An item's name as one completable word (`pulse-cannon`, `megamissile-ammo-5`). */
export const itemSlug = (c: ShopCategory, id: number) =>
  itemLabel(c, id)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

/** Every id that can go in a category's list. */
export function validIds(c: ShopCategory): number[] {
  return Array.from({ length: c.max - c.min + 1 }, (_, i) => c.min + i);
}

/** The episodes `shop all` reads: Tyrian 2.1's four. */
export const SHOP_EPISODES = [1, 2, 3, 4] as const;

/** Every item screen's 9 itemAvail rows in an episode script, read as the sim reads `]I[` (itemAvailLine). */
export function itemScreenLists(data: Uint8Array): number[][][] {
  const { lines } = parseEpisodeScript(data);
  const out: number[][][] = [];
  lines.forEach((line, i) => {
    if (line.startsWith("]I[")) out.push(Array.from({ length: 9 }, (_, r) => itemAvailLine(lines[i + 1 + r] ?? "")));
  });
  return out;
}

export interface SoldEverywhere {
  /** Per category key: every id some item screen sells, in the merchant's order. */
  lists: Record<ShopCategoryKey, number[]>;
  /** The episodes read. */
  episodes: number[];
  /** Item screens read. */
  screens: number;
  /** Ids a list gave that the category can't take (none in Tyrian 2.1's data), dropped. */
  dropped: { key: ShopCategoryKey; id: number }[];
}

/**
 * `shop all`'s lists: per category, the union of every item screen's list in the episodes there is
 * data for (1-4). Only what the real game sells somewhere: items no shop lists (the Stalker,
 * U-Ship, Silver and Nort ships, the joke and Nort guns, Quicksilver, the HXS Class C shield, ...)
 * stay out, and an id outside the category's item table would be dropped.
 */
export function soldEverywhere(files: TyrianFiles): SoldEverywhere {
  const sets = Object.fromEntries(SHOP_CATEGORIES.map((c) => [c.key, new Set<number>()])) as Record<ShopCategoryKey, Set<number>>;
  const dropped: SoldEverywhere["dropped"] = [];
  const episodes: number[] = [];
  let screens = 0;
  for (const ep of SHOP_EPISODES) {
    const data = files.get(`levels${ep}.dat`);
    if (!data) continue;
    episodes.push(ep);
    for (const rows of itemScreenLists(data)) {
      screens++;
      for (const c of SHOP_CATEGORIES) {
        for (const id of rows[c.row]) {
          if (id < c.min || id > c.max) dropped.push({ key: c.key, id });
          else sets[c.key].add(id);
        }
      }
    }
  }
  const lists = Object.fromEntries(SHOP_CATEGORIES.map((c) => [c.key, merchantOrder(sets[c.key])])) as Record<ShopCategoryKey, number[]>;
  return { lists, episodes, screens, dropped };
}

// --- the console's state: `shop all`, and the categories edited ---

let allOn = false;
let soldCache: { files: TyrianFiles; sold: SoldEverywhere } | null = null;

export function sold(files: TyrianFiles): SoldEverywhere {
  if (soldCache?.files !== files) soldCache = { files, sold: soldEverywhere(files) };
  return soldCache.sold;
}

/** Whether `shop all` is on. */
export const shopAllOn = () => allOn;

/** The categories whose list the console has set (by `shop all` or an edit). */
export const overridden = () => SHOP_CATEGORIES.filter((c) => consoleShopList(c.row) !== null);

/** Categories edited since `shop all` (or set without it). */
const edited = new Set<ShopCategoryKey>();
export const editedCategories = () => SHOP_CATEGORIES.filter((c) => edited.has(c.key));

/** After a change: the shop on screen takes the new lists at once. */
function changed(inShop: boolean): void {
  if (inShop) JE_itemScreen_listsChanged();
}

/** `shop all on`: every category sells the union. Earlier edits go. */
export function setShopAll(files: TyrianFiles, inShop: boolean): SoldEverywhere {
  const s = sold(files);
  allOn = true;
  edited.clear();
  for (const c of SHOP_CATEGORIES) setConsoleShopList(c.row, s.lists[c.key]);
  changed(inShop);
  return s;
}

/** `shop reset [category]` (and `shop all off`): the level's own lists back; with no category, everything and `shop all` off. */
export function resetShopLists(inShop: boolean, only?: ShopCategory): void {
  for (const c of only ? [only] : SHOP_CATEGORIES) {
    setConsoleShopList(c.row, null);
    edited.delete(c.key);
  }
  if (!only || overridden().length === 0) allOn = false;
  changed(inShop);
}

/** The console's list for a category, or null when the level's is sold. */
export const consoleList = (c: ShopCategory): readonly number[] | null => consoleShopList(c.row);

/**
 * What a category offers now: the console's list (with what the player has, as the shop lists it),
 * or the level's (the last item screen's, outside the shop).
 */
export const offered = (c: ShopCategory): number[] => shopListShown(c.row);

/** Replace a category's list (deduplicated, in the merchant's order, as the shop sorts it). */
export function setCategoryList(c: ShopCategory, ids: readonly number[], inShop: boolean): number[] {
  const list = merchantOrder(ids);
  setConsoleShopList(c.row, list);
  edited.add(c.key);
  changed(inShop);
  return list;
}
