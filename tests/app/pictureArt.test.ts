// pictureArt.ts: the story screens find each picture's remastered image through
// public/art/pictures.json, and fall back to the original when a picture isn't listed.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "vitest";
import { pictureUrl, type PictureManifest } from "../../src/app/pictureArt";

const manifest = JSON.parse(readFileSync(join(__dirname, "../../public/art/pictures.json"), "utf8")) as PictureManifest;

test("the pictures the episode scripts show have remastered images, under the site root", () => {
  // tshp2.pcx is 0; 5, 7, 8, 9 and 13 are the story pictures (assets/art/README.md).
  expect(pictureUrl(manifest, 5, "./")).toBe("./art/story_planet.webp");
  expect(pictureUrl(manifest, 0, "/tyrian/")).toBe("/tyrian/art/story_engage.webp");
  for (const pic of [7, 8, 9, 13]) expect(pictureUrl(manifest, pic, "./")).toMatch(/^\.\/art\/story_\w+\.webp$/);
});

test("a picture missing from the manifest (or an empty one) uses the original", () => {
  expect(pictureUrl(manifest, 14, "./")).toBeUndefined();
  expect(pictureUrl({}, 5, "./")).toBeUndefined();
  expect(pictureUrl({ "5": "" }, 5, "./")).toBeUndefined();
  // Not inherited properties either.
  expect(pictureUrl({}, "toString" as unknown as number, "./")).toBeUndefined();
});
