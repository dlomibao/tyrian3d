import { expect, test } from "vitest";
import { pictureArtUrl } from "../../src/app/pictureArt";

test("no remastered pictures yet: every picture comes from the game data", () => {
  // tshp2.pcx is 0, tyrian.pic's pictures 1..13.
  for (let pic = 0; pic <= 13; pic++) expect(pictureArtUrl(pic)).toBeUndefined();
});
