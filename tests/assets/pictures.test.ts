// public/art/pictures.json: the new artwork for each tyrian.pic picture (assets/art/README.md).
// Code that shows a picture looks its number up there (0 is tshp2.pcx, which the episode script
// shows as `]P 000`), so every entry must name a real file of the pictures' size, and every
// picture must have one.
import { existsSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";

const PUBLIC = join(__dirname, "../../public");
const pictures = JSON.parse(readFileSync(join(PUBLIC, "art/pictures.json"), "utf8")) as Record<string, string>;

/** Width and height from a WebP's header (VP8, VP8L or VP8X chunk). */
function webpSize(b: Buffer): [number, number] {
  expect(b.toString("ascii", 0, 4)).toBe("RIFF");
  expect(b.toString("ascii", 8, 12)).toBe("WEBP");
  const chunk = b.toString("ascii", 12, 16);
  if (chunk === "VP8X") return [1 + b.readUIntLE(24, 3), 1 + b.readUIntLE(27, 3)];
  if (chunk === "VP8L") {
    const bits = b.readUInt32LE(21);
    return [1 + (bits & 0x3fff), 1 + ((bits >> 14) & 0x3fff)];
  }
  return [b.readUInt16LE(26) & 0x3fff, b.readUInt16LE(28) & 0x3fff];
}

describe("pictures.json", () => {
  test("has a picture for each of tyrian.pic's 13 (PCX_NUM) and for tshp2.pcx (0)", () => {
    expect(Object.keys(pictures).map(Number).sort((a, b) => a - b)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]);
  });

  test.each(Object.entries(pictures))("picture %s (%s) is a 1920x1200 WebP under 600 KB", (_, path) => {
    const file = join(PUBLIC, path);
    expect(existsSync(file)).toBe(true);
    expect(statSync(file).size).toBeLessThanOrEqual(600 * 1024);
    expect(webpSize(readFileSync(file))).toEqual([1920, 1200]);
  });
});
