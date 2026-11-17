import { expect, test } from "vitest";
import { ANIM_VIDEO, animArtMode } from "../../src/app/animArt";

test("the ending animation's look follows D42's switch: ?sprites=, else ?vfx=", () => {
  expect(animArtMode("")).toBe("remastered");
  expect(animArtMode("?sprites=original")).toBe("original");
  expect(animArtMode("?vfx=original")).toBe("original");
  expect(animArtMode("?vfx=original&sprites=remastered")).toBe("remastered");
});

test("the video is a WebM under public/art", () => {
  expect(ANIM_VIDEO).toMatch(/^art\/cutscenes\/[\w-]+\.webm$/);
});
