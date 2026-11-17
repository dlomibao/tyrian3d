// creditsArt.ts (D218): the end credits' painted pictures come from public/art/credits/manifest.json,
// one WebP per estsc.shp picture at its size times the scale; the ship's banking frames from
// public/art/credits/ships/ (the shop icons' format), which with D210's level frames cover every
// frame the credits' ships show. Anything missing or malformed draws as the original.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "vitest";
import { parseCreditsArtManifest, SHIP_BANKS, SHIP_SHEET } from "../../src/app/creditsArt";
import { parseShopIconManifest, shopIconKey } from "../../src/app/shopIcons";

const dir = join(__dirname, "../../public/art/credits");
const json = (path: string) => JSON.parse(readFileSync(path, "utf8")) as unknown;

/** A WebP's canvas size (VP8X, VP8 or VP8L header). */
function webpSize(buf: Buffer): { w: number; h: number } {
  const kind = buf.toString("ascii", 12, 16);
  if (kind === "VP8X") return { w: 1 + buf.readUIntLE(24, 3), h: 1 + buf.readUIntLE(27, 3) };
  if (kind === "VP8L") {
    const b = buf.readUInt32LE(21);
    return { w: 1 + (b & 0x3fff), h: 1 + ((b >> 14) & 0x3fff) };
  }
  return { w: buf.readUInt16LE(26) & 0x3fff, h: buf.readUInt16LE(28) & 0x3fff };
}

// estsc.shp's nine pictures (load_sprites_file(EXTRA_SHAPES)): width x height.
const PICTURES = [[140, 160], [113, 170], [116, 159], [100, 148], [92, 151], [85, 161], [101, 156], [53, 156], [135, 138]];

test("every credits picture is painted, at its size times the scale, in a WebP of that size", () => {
  const m = parseCreditsArtManifest(json(join(dir, "manifest.json")), (msg) => expect.fail(msg))!;
  expect(m).not.toBeNull();
  expect([...m.pictures.keys()]).toEqual(PICTURES.map((_, i) => i));
  for (const [n, p] of m.pictures) {
    expect([p.w, p.h]).toEqual([PICTURES[n][0] * m.scale, PICTURES[n][1] * m.scale]);
    expect(webpSize(readFileSync(join(dir, p.image)))).toEqual({ w: p.w, h: p.h });
  }
});

test("with D210's level frames, every frame of every credits ship is painted", () => {
  const shop = parseShopIconManifest(json(join(dir, "../shop/manifest.json")))!;
  const banks = parseShopIconManifest(json(join(dir, "ships/manifest.json")), (msg) => expect.fail(msg))!;
  const { w, h } = webpSize(readFileSync(join(dir, "ships", banks.image)));
  for (const f of banks.icons.values()) {
    expect([f.w, f.h]).toEqual([24 * banks.scale, 28 * banks.scale]);
    expect(f.x + f.w).toBeLessThanOrEqual(w);
    expect(f.y + f.h).toBeLessThanOrEqual(h);
  }
  // ships[1..11].shipGraphic in the item data: Talon/Fang, SuperCarrot, Phoenix/Maelstrom, Stalkers, U-Ship, Silver Ship.
  for (const g of [233, 119, 157, 195, 271, 81]) {
    for (const d of SHIP_BANKS) {
      const key = shopIconKey(SHIP_SHEET, g + d);
      expect(shop.icons.has(key) || banks.icons.has(key), key).toBe(true);
    }
  }
});

test("a malformed manifest gives no art; a malformed picture is dropped (it stays original)", () => {
  expect(parseCreditsArtManifest(null)).toBeNull();
  expect(parseCreditsArtManifest({ pictures: {} })).toBeNull();
  expect(parseCreditsArtManifest({ scale: 0, pictures: {} })).toBeNull();
  const warnings: string[] = [];
  const m = parseCreditsArtManifest(
    { scale: 5, pictures: { "0": { image: "p.webp", w: 700, h: 800 }, "1": { image: "", w: 1, h: 1 }, x: { image: "q.webp", w: 1, h: 1 } } },
    (msg) => warnings.push(msg),
  )!;
  expect([...m.pictures.keys()]).toEqual([0]);
  expect(warnings).toHaveLength(2);
});
