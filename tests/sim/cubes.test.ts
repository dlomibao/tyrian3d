// Data cubes (src/sim/cubes.ts, a port of OpenTyrian's load_cube and the reader's scrolling) and
// their item screen menus (MENU_DATA_CUBES / MENU_DATA_CUBE_SUB in src/sim/game_menu.ts).
//
// The first suite is a cross-check against the real C code: fixtures/cube-digest.c.txt was
// produced by tools/opentyrian-cubes/build.sh, which compiles OpenTyrian with a driver that runs
// load_cube on every cube of every episode and prints hashes of its title, header and wrapped text
// (hashes, so the fixture holds none of the game's text). The port must print the same lines.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { beforeEach, describe, expect, test } from "vitest";
import { atoi, parseEpisodeScript } from "../../src/data";
import {
  cube,
  cubeCount,
  cubeFilename,
  cubeReader,
  cubeReader_end,
  cubeReader_frame,
  cubeReader_home,
  cubeReader_percent,
  load_cube,
  load_cubes,
  type cube_struct,
} from "../../src/sim/cubes";
import {
  itemScreenEntries,
  JE_itemScreen_init,
  JE_itemScreen_key,
  JE_itemScreen_mouse,
  JE_itemScreen_update,
  JE_mainMenuHelpText,
  JE_menuHeader,
  MENU_DATA_CUBE_SUB,
  MENU_DATA_CUBES,
  MENU_FULL_GAME,
  menu,
  type ItemScreenKey,
} from "../../src/sim/game_menu";
import { loadHelpText } from "../../src/sim/helptext";
import { buildResources } from "../../src/sim/resources";
import { S_SPRING } from "../../src/sim/sndmast";
import { g } from "../../src/sim/state";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const CUBE_FILES = [1, 2, 3, 4].map((e) => cubeFilename(e));
const HAVE = hasData("tyrian.shp", "tyrian.hdt", "palette.dat", ...CUBE_FILES);

/** The driver's fnv(): FNV-1a over a string's bytes, continuing from h. */
function fnv(s: string, h = 2166136261): number {
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ (s.charCodeAt(i) & 0xff), 16777619) >>> 0;
  return h;
}
const hex = (n: number) => n.toString(16).padStart(8, "0");

function digest(episode: number, index: number, c: cube_struct): string {
  let text = 2166136261;
  for (const line of c.text) text = fnv("\n", fnv(line, text));
  return `C episode=${episode} cube=${index} face=${c.face_sprite} last_line=${c.last_line} title=${hex(fnv(c.title))} header=${hex(fnv(c.header))} text=${hex(text)}`;
}

function setup(): void {
  if (!g.res || g.episodeNum !== 1) g.res = buildResources(files, 1);
  g.episodeNum = 1;
  loadHelpText(readData("tyrian.hdt"));
}

describe.skipIf(!HAVE)("load_cube matches OpenTyrian's", () => {
  beforeEach(setup);

  test("every cube of every episode", () => {
    const expected = readFileSync(join(__dirname, "fixtures", "cube-digest.c.txt"), "utf8").trimEnd().split("\n");
    const got: string[] = [];
    for (let episode = 1; episode <= 4; episode++) {
      const data = readData(cubeFilename(episode));
      const count = cubeCount(data);
      got.push(`N episode=${episode} cubes=${count}`);
      // One slot, loaded in order, like the driver.
      for (let index = 1; index <= count; index++) {
        cube[0].text.fill("");
        load_cube(data, 0, index);
        got.push(digest(episode, index, cube[0]));
      }
    }
    expect(got).toEqual(expected);
  });

  test("wrapped lines fit the reader's column", () => {
    for (let episode = 1; episode <= 4; episode++) {
      const data = readData(cubeFilename(episode));
      for (let index = 1; index <= cubeCount(data); index++) {
        cube[0].text.fill("");
        load_cube(data, 0, index);
        expect(cube[0].header.length).toBeLessThanOrEqual(12);
        expect(cube[0].title.length).toBeLessThanOrEqual(80);
        for (const line of cube[0].text) expect(line.length).toBeLessThanOrEqual(35);
      }
    }
  });

  test("every cube an episode script lists (`]?[`) is in its cubetxt file", () => {
    for (let episode = 1; episode <= 4; episode++) {
      const count = cubeCount(readData(cubeFilename(episode)));
      const script = parseEpisodeScript(readData(`levels${episode}.dat`));
      let lists = 0;
      for (const s of script.lines) {
        if (!s.startsWith("]?[")) continue;
        lists++;
        // JE_loadMap's '?' (tyrian2.c L2391-2399): temp = atoi(s + 4), cubeList[i] = atoi(s + 3 + (i + 1) * 4).
        const n = Math.min(atoi(s.slice(4)), 4);
        for (let i = 0; i < n; i++) {
          const index = atoi(s.slice(3 + (i + 1) * 4));
          expect(index, `${s} (episode ${episode})`).toBeGreaterThanOrEqual(1);
          expect(index, `${s} (episode ${episode})`).toBeLessThanOrEqual(count);
        }
      }
      expect(lists).toBeGreaterThan(0);
    }
  });
});

describe.skipIf(!HAVE)("the item screen's data cube menus", () => {
  beforeEach(() => {
    setup();
    g.player[0].cash = 0;
    g.cubeList = [1, 2, 23, 5]; // episode 1's first `]?[`
    g.cubeMax = 3;
    g.jumpSection = false;
    g.gameLoaded = false;
    g.constantPlay = false;
    g.twoPlayerMode = g.onePlayerAction = g.isNetworkGame = g.superTyrian = false;
    JE_itemScreen_init();
    load_cubes(files);
    JE_itemScreen_update();
    menu.sounds.length = 0;
  });

  const key = (k: ItemScreenKey) => {
    JE_itemScreen_key(k);
    JE_itemScreen_update();
  };

  test("load_cubes loads the cubes cubeList names, in order", () => {
    const data = readData(cubeFilename(1));
    const expected = [1, 2, 23].map((index) => {
      cube[3].text.fill("");
      load_cube(data, 3, index);
      return cube[3].title;
    });
    load_cubes(files);
    expect(cube.slice(0, 3).map((c) => c.title)).toEqual(expected);
  });

  test("Data Cubes lists the cubes found, then Exit to Game Menu", () => {
    expect(itemScreenEntries().find((e) => e.sel === 2)?.unavailable).toBeFalsy();
    key("enter"); // Data Cubes is the first choice
    expect(menu.curMenu).toBe(MENU_DATA_CUBES);
    expect(JE_menuHeader()).toBe(g.menuInt[1][1]);
    const rows = itemScreenEntries();
    expect(rows.map((e) => e.sel)).toEqual([2, 3, 4, 5]);
    expect(rows.slice(0, 3).map((e) => e.label)).toEqual(cube.slice(0, 3).map((c) => c.title));
    expect(rows[3]).toMatchObject({ label: g.miscText[5], done: true });
    expect(menu.menuChoices[MENU_DATA_CUBES]).toBe(5);
    // help: the cube rows (mainMenuHelp[17 + 7 - 3]), then the exit row (mainMenuHelp[12 - 1])
    expect(JE_mainMenuHelpText()).toBe(g.mainMenuHelp[21]);
    key("up");
    expect(menu.curSel[MENU_DATA_CUBES]).toBe(5);
    expect(JE_mainMenuHelpText()).toBe(g.mainMenuHelp[11]);
    key("enter");
    expect(menu.curMenu).toBe(MENU_FULL_GAME);
  });

  test("Enter opens the reader on the chosen cube; Enter or Escape goes back", () => {
    key("enter");
    key("down");
    key("enter");
    expect(menu.curMenu).toBe(MENU_DATA_CUBE_SUB);
    expect(menu.currentCube).toBe(1);
    expect(JE_menuHeader()).toBe(cube[1].header);
    expect(itemScreenEntries()).toEqual([]);
    key("enter");
    expect(menu.curMenu).toBe(MENU_DATA_CUBES);
    expect(menu.curSel[MENU_DATA_CUBES]).toBe(3);
    key("enter");
    key("esc");
    expect(menu.curMenu).toBe(MENU_DATA_CUBES);
    key("esc");
    expect(menu.curMenu).toBe(MENU_FULL_GAME);
  });

  test("with no cubes, the list only offers the way back, and a click takes it", () => {
    g.cubeMax = 0;
    key("enter");
    expect(itemScreenEntries()).toMatchObject([{ sel: 2, done: true }]);
    expect(JE_mainMenuHelpText()).toBe(g.mainMenuHelp[11]);
    menu.sounds.length = 0;
    JE_itemScreen_mouse(2);
    expect(menu.curMenu).toBe(MENU_FULL_GAME);
    expect(menu.sounds).toEqual([S_SPRING]);
  });
});

describe("the data cube reader's scrolling", () => {
  const c: cube_struct = { title: "", header: "", face_sprite: -1, text: [], last_line: 30 };
  beforeEach(() => {
    cubeReader.yLoc = 0;
    cubeReader.yChg = 0;
  });

  test("a tap scrolls one line, a pixel a frame", () => {
    cubeReader_frame(c, { down: true });
    let frames = 0;
    while (cubeReader.yChg !== 0) cubeReader_frame(c, {}), frames++;
    expect(frames).toBe(12);
    expect(cubeReader.yLoc).toBe(12);
    expect(cubeReader_percent(c)).toBe(Math.trunc((12 * 100) / (21 * 12)));
  });

  test("Page Down scrolls two pixels a frame; up stops at the top", () => {
    cubeReader_frame(c, { pageDown: true });
    for (let i = 0; i < 6; i++) cubeReader_frame(c, {});
    expect(cubeReader.yLoc).toBe(12);
    expect(cubeReader.yChg).toBe(0);
    for (let i = 0; i < 40; i++) cubeReader_frame(c, { up: true });
    expect(cubeReader.yLoc).toBe(0);
    expect(cubeReader.yChg).toBe(0);
  });

  test("holding down stops with the last line at the bottom", () => {
    for (let i = 0; i < 1000; i++) cubeReader_frame(c, { down: true });
    expect(cubeReader.yLoc).toBe((30 - 9) * 12);
    expect(cubeReader_percent(c)).toBe(100);
    cubeReader_home();
    expect(cubeReader.yLoc).toBe(0);
    cubeReader_end(c);
    expect(cubeReader.yLoc).toBe((30 - 9) * 12);
  });

  test("a short cube doesn't scroll", () => {
    const short = { ...c, last_line: 5 };
    for (let i = 0; i < 50; i++) cubeReader_frame(short, { down: true });
    expect(cubeReader.yLoc).toBe(0);
    cubeReader_end(short);
    expect(cubeReader.yLoc).toBe(0);
    expect(cubeReader_percent(short)).toBe(100);
  });
});
