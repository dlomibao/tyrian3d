import { beforeEach, describe, expect, test } from "vitest";
import type { TyrianFiles } from "../../src/sim/resources";
import { DIFFICULTY_NORMAL, g, newPlayer } from "../../src/sim/state";
import { clearStorySteps, takeStorySteps, type StoryStep } from "../../src/sim/story";
import { JE_loadMapSteps, loadLevel, loadLevelUntilPause } from "../../src/sim/tyrian2";
import { hasData, readData } from "../data/dataDir";

const NEEDED = ["levels1.dat", "tyrian1.lvl", "levels3.dat", "tyrian3.lvl", "tyrian.hdt", "tyrian.shp", "palette.dat"];

const cache = new Map<string, Uint8Array | undefined>();
const files: TyrianFiles = {
  get(name) {
    if (!cache.has(name)) cache.set(name, hasData(name) ? readData(name) : undefined);
    return cache.get(name);
  },
};

/** The ops alone, with each step's main argument, for compact expectations. */
function ops(steps: StoryStep[]): string[] {
  return steps.map((s) => {
    switch (s.op) {
      case "loadPic":
        return `loadPic ${s.pic}/${s.palette}`;
      case "setColors":
        return `setColors ${s.palette}`;
      case "fadePalette":
      case "fadeBlack":
      case "fadeWhite":
        return `${s.op} ${s.steps}`;
      case "pan":
        return `pan ${s.dir} ${s.pic}/${s.palette} ${s.frames}`;
      case "text":
        return `text ${s.lines.length}`;
      case "song":
        return `song ${s.song}`;
      default:
        return s.op;
    }
  });
}

describe.skipIf(!hasData(...NEEDED))("JE_loadMap's screens between levels", () => {
  beforeEach(() => {
    g.player = [newPlayer(), newPlayer()];
    g.twoPlayerMode = false;
    g.constantPlay = false;
    g.useLastBank = false;
    g.difficultyLevel = DIFFICULTY_NORMAL;
    g.initialDifficulty = DIFFICULTY_NORMAL;
    clearStorySteps();
  });

  test("episode 1 section 39 (after SAVARA V): two text screens over picture 5, then the item screen", () => {
    // levels1.dat section 39: ]M 009[ ]P 005[ ]Wn 03[ (10 lines) ... # ]M 005[ ]P 005[ ]Wn 03[
    // (6 lines) ... # ]J 035[; section 35 is ]I[ before ASSASSIN.
    loadLevel(files, 1, 1); // loads the episode's resources and help text
    g.mainLevel = 39;
    const steps = JE_loadMapSteps(files);
    expect(steps.next()).toEqual({ value: "itemScreen", done: false });
    const before = takeStorySteps();
    expect(ops(before)).toEqual([
      "song 8",
      "loadPic 5/10", // pcxpal[5 - 1]
      "fadePalette 10",
      "text 10",
      "song 4",
      "loadPic 5/10",
      "fadePalette 10",
      "text 6",
    ]);
    expect(before[3]).toEqual({
      op: "text",
      lines: [
        "Now that you've saved the crisis on Savara and earned the",
        "help of Transon Lohk, you head back to Tyrian to find out",
        "more about this new power.",
        "",
        "How could such an innocent pile of rocks be used to",
        "devastate planets?",
        "",
        "You must locate a sample of this new energy.  If nothing",
        "else, perhaps it could be harnessed back against Microsol's",
        "new device.",
      ],
      prompt: "Press a key", // miscText[4]
      frameCountMax: 3,
      warningRed: false,
      warningDisplay: false,
      useLastBank: false,
    });
    // g.levelWarningText keeps the last text, as the C's levelWarningText does.
    expect(g.levelWarningText).toEqual((before[7] as { lines: string[] }).lines);

    g.mapSection[0] = 36; // the item screen's choice
    g.mainLevel = 36;
    g.jumpSection = true;
    expect(steps.next()).toEqual({ value: true, done: true });
    expect(g.levelName).toBe("ASSASSIN ");
    // fade_black(50) before the level.
    expect(ops(takeStorySteps())).toEqual(["fadeBlack 50"]);
  });

  test("episode 1 section 11 (before MINES): the warning text with flashers", () => {
    loadLevel(files, 1, 11);
    const steps = takeStorySteps();
    expect(ops(steps)).toEqual(["song 15", "loadPic 5/10", "fadePalette 10", "text 6", "fadeBlack 50"]);
    // ]Wy 01[: warning bars, one frame per character.
    expect(steps[3]).toMatchObject({ warningDisplay: true, frameCountMax: 1, warningRed: false });
    expect((steps[3] as { lines: string[] }).lines[0]).toBe("Warning:");
  });

  test("episode 1 section 42 (after the ALE bonus): ]U pans up to picture 8, ]n ends the scene, ]F flashes", () => {
    expect(loadLevelUntilPause(files, 1, 42)).not.toBeNull(); // its item screen leads to section 26, on to the episode's end
    expect(ops(takeStorySteps()).slice(0, 12)).toEqual([
      "song 7",
      "loadPic 9/19",
      "fadePalette 10",
      "text 10",
      "song 21",
      "pan up 8/19 200",
      "text 1",
      "endScene", // ]2 026[ jumps only in two-player or arcade games
      "fadeWhite 100",
      "fadeBlack 30",
      "clear",
      "song 37",
    ]);
  });

  test("episode 3 section 13 (the ending): ]P 907[ clears to palette 18, ]C[ fades and resets to palette 7", () => {
    // ]A[ ]F[ ]P 907[ ]Wn 03[ ]C[ ]P 907[ ]Wn 03[ ]C[ ]P 907[ ]Wn 03[ ]F[ ]P 005[ ]Q[
    expect(loadLevelUntilPause(files, 3, 13, ["displayText"])).toBe("displayText"); // ]Q['s hint, after ]A[
    const clear907 = ["setColors 18", "clear", "fadePalette 1"]; // pcxpal[907 - 1 - 900]
    const resetC = ["fadeBlack 10", "clear", "setColors 7", "setPalette"];
    const flash = ["fadeWhite 100", "fadeBlack 30", "clear"];
    expect(ops(takeStorySteps())).toEqual([
      "song 8",
      ...flash,
      ...clear907,
      "text 7",
      ...resetC,
      ...clear907,
      "text 5",
      ...resetC,
      ...clear907,
      "text 8",
      ...flash,
      "loadPic 5/10",
      "fadePalette 10",
      // ]Q[ pauses for its screens before fade_black(50); the steps wait for the host.
    ]);
  });

  test("constantPlay skips the pictures and text but not the fades", () => {
    g.constantPlay = true;
    // constantPlay skips ]Q['s hint too, so loading carries on into the next episode: check the start.
    loadLevelUntilPause(files, 3, 13, ["displayText"]);
    expect(ops(takeStorySteps()).slice(0, 15)).toEqual([
      "song 8",
      "fadeWhite 100",
      "fadeBlack 30",
      "clear",
      "fadeBlack 10",
      "clear",
      "setColors 7",
      "setPalette",
      "fadeBlack 10",
      "clear",
      "setColors 7",
      "setPalette",
      "fadeWhite 100",
      "fadeBlack 30",
      "clear",
    ]);
  });

  test("JE_loadMap starts with an empty queue", () => {
    loadLevel(files, 1, 11);
    loadLevel(files, 1, 1);
    expect(ops(takeStorySteps())).toEqual(["fadeBlack 50"]);
  });
});
