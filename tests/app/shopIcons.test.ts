// shopIcons.ts (D210): the item screen's remastered icons come from public/art/shop/manifest.json,
// keyed by sheet and first sprite; anything missing or malformed draws as the original pixels, and
// the look follows D42's switch (?sprites=, else ?vfx=).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "vitest";
import { parseShopIconManifest, shopIconKey, shopIconMode } from "../../src/app/shopIcons";

const dir = join(__dirname, "../../public/art/shop");
const raw = JSON.parse(readFileSync(join(dir, "manifest.json"), "utf8")) as unknown;

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

test("the committed atlas has every shop icon (61 across episodes 1-4) at 24x28 times its scale, inside the image", () => {
  const m = parseShopIconManifest(raw, (msg) => expect.fail(msg))!;
  expect(m).not.toBeNull();
  expect(m.icons.size).toBe(61);
  const { w, h } = webpSize(readFileSync(join(dir, m.image)));
  for (const [key, f] of m.icons) {
    expect(key).toMatch(/^(newsh1\.shp|tyrian\.shp#8):\d+$/);
    expect([f.w, f.h]).toEqual([24 * m.scale, 28 * m.scale]);
    expect(f.x + f.w).toBeLessThanOrEqual(w);
    expect(f.y + f.h).toBeLessThanOrEqual(h);
  }
  // The Pulse-Cannon (itemGraphic 7) and the USP Talon (shipGraphic 233).
  expect(m.icons.has(shopIconKey("newsh1.shp", 7))).toBe(true);
  expect(m.icons.has(shopIconKey("tyrian.shp#8", 233))).toBe(true);
});

test("a malformed manifest gives no art; a malformed frame is dropped (that icon stays original)", () => {
  expect(parseShopIconManifest(null)).toBeNull();
  expect(parseShopIconManifest({ scale: 6, icons: {} })).toBeNull();
  expect(parseShopIconManifest({ scale: 0, image: "a.webp", icons: {} })).toBeNull();
  const warnings: string[] = [];
  const m = parseShopIconManifest(
    { scale: 6, image: "a.webp", icons: { "newsh1.shp:7": { x: 0, y: 0, w: 144, h: 168 }, "newsh1.shp:9": { x: 0, y: 0, w: 0, h: 168 }, bad: { x: 0, y: 0, w: 1, h: 1 } } },
    (msg) => warnings.push(msg),
  )!;
  expect([...m.icons.keys()]).toEqual(["newsh1.shp:7"]);
  expect(warnings).toHaveLength(2);
});

test("the icons follow the sprite art's look: ?sprites= first, else the effects look", () => {
  expect(shopIconMode("")).toBe("remastered");
  expect(shopIconMode("?sprites=original")).toBe("original");
  expect(shopIconMode("?vfx=original")).toBe("original");
  expect(shopIconMode("?vfx=original&sprites=remastered")).toBe("remastered");
});
