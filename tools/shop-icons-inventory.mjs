// Every distinct shop icon (JE_drawItem's 24x28 picture) across episodes 1-4, for tools/shop_icons.py
// (DECISIONS.md D210).
//
//   NODE_OPTIONS= node tools/shop-icons-inventory.mjs [out.json]
//
// An icon is a (sheet, first sprite) pair: the four 12x14 sprites index, +1, +19, +20 of newsh1.shp
// (weapons, shields, generators, sidekicks: itemGraphic) or of tyrian.shp's ship sheet (spriteSheet9,
// tyrian.shp#8: shipGraphic), as src/app/shop.ts itemIcon draws them. Each lists the items that
// show it, with their names and the episodes whose item data has them. The output is derived from
// the game data (D3): keep it in a scratch folder.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const out = process.argv[2] ?? "shop-icons-inventory.json";
const { createServer } = await import("vite");
const server = await createServer({ root: ROOT, configFile: false, logLevel: "error", server: { middlewareMode: true }, appType: "custom" });
try {
  const items = await server.ssrLoadModule("/src/data/items.ts");
  const data = process.env.TYRIAN_DATA ?? join(ROOT, "data");
  const hdt = readFileSync(join(data, "tyrian.hdt"));
  const lvl4 = readFileSync(join(data, "tyrian4.lvl"));
  const icons = new Map();
  const add = (sheet, index, kind, id, raw, ep) => {
    if (index <= 0) return;
    const name = raw.replace(/\s+/g, " ").trim();
    const key = `${sheet}:${index}`;
    let e = icons.get(key);
    if (!e) icons.set(key, (e = { key, sheet, index, uses: [] }));
    const use = e.uses.find((u) => u.kind === kind && u.id === id && u.name === name);
    if (use) {
      if (!use.episodes.includes(ep)) use.episodes.push(ep);
    } else e.uses.push({ kind, id, name, episodes: [ep] });
  };
  for (const ep of [1, 2, 3, 4]) {
    const d = items.loadItemDat(ep, hdt, ep === 4 ? lvl4 : undefined);
    // itemIcon draws ids 1..90 (the C's custom ships above 90 aren't in the data).
    d.ships.forEach((s, id) => id > 0 && id <= 90 && add("tyrian.shp#8", s.shipGraphic, "ship", id, s.name, ep));
    d.weaponPorts.forEach((w, id) => id > 0 && add("newsh1.shp", w.itemGraphic, "weapon", id, w.name, ep));
    d.shields.forEach((w, id) => id > 0 && add("newsh1.shp", w.itemGraphic, "shield", id, w.name, ep));
    d.powerSys.forEach((w, id) => id > 0 && add("newsh1.shp", w.itemGraphic, "generator", id, w.name, ep));
    d.options.forEach((w, id) => id > 0 && add("newsh1.shp", w.itemGraphic, "sidekick", id, w.name, ep));
  }
  const list = [...icons.values()].sort((a, b) => a.sheet.localeCompare(b.sheet) || a.index - b.index);
  writeFileSync(out, JSON.stringify(list, null, 1));
  console.log(`${list.length} icons (${list.filter((e) => e.sheet === "newsh1.shp").length} on newsh1.shp, ${list.filter((e) => e.sheet !== "newsh1.shp").length} ships) -> ${out}`);
} finally {
  await server.close();
}
