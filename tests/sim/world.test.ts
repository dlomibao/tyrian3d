import { beforeEach, describe, expect, test } from "vitest";
import { parseLevelFile, parseShapes } from "../../src/data";
import { BG_KEY_LAYER, draw_background_1, JE_filterScreen } from "../../src/sim/backgrnd";
import { beginDrawList, drawList, Pass, type SpriteDraw, type TileDraw } from "../../src/sim/draw";
import { mt_srand } from "../../src/sim/mtrand";
import type { TyrianFiles } from "../../src/sim/resources";
import { DIFFICULTY_HARD, DIFFICULTY_NORMAL, g, newPlayer } from "../../src/sim/state";
import {
  ENEMY_KEY_BASE,
  initLevelWorld,
  JE_eventJump,
  JE_eventSystem,
  JE_makeEnemy,
  JE_newEnemy,
  JE_searchFor,
  loadLevel,
} from "../../src/sim/tyrian2";
import { JE_doSP, JE_drawSP, JE_playerDamage, JE_setupExplosion, JE_setupExplosionLarge } from "../../src/sim/varz";
import { hasData, readData } from "../data/dataDir";
import { worldTick } from "./worldDriver";

const NEEDED = ["levels1.dat", "tyrian1.lvl", "shapesz.dat", "tyrian.hdt", "tyrian.shp", "palette.dat", "newsh6.shp"];

const cache = new Map<string, Uint8Array | undefined>();
const files: TyrianFiles = {
  get(name) {
    if (!cache.has(name)) cache.set(name, hasData(name) ? readData(name) : undefined);
    return cache.get(name);
  },
};

function resetPlayers(): void {
  g.player = [newPlayer(), newPlayer()];
  g.twoPlayerMode = false;
  g.difficultyLevel = DIFFICULTY_NORMAL;
  g.initialDifficulty = DIFFICULTY_NORMAL;
}

describe.skipIf(!hasData(...NEEDED))("loadLevel (JE_loadMap)", () => {
  beforeEach(resetPlayers);

  test("episode 1 starts at TYRIAN: section 1 jumps to 2, whose shop falls into section 3's ]L[", () => {
    loadLevel(files, 1, 1);
    // levels1.dat section 3: `]h[` then `]L[ 9999 004 TYRIAN   18 09`.
    expect(g.levelName).toBe("TYRIAN   ");
    expect(g.lvlFileNum).toBe(9);
    expect(g.levelSong).toBe(18);
    expect(g.nextLevel).toBe(4);
    expect(g.mainLevel).toBe(2); // ]J 002[; execution then falls through into section 3
    expect(g.bonusLevelCurrent).toBe(false);
    expect(g.normalBonusLevelCurrent).toBe(false);
    // Section 2's ]?[ 04 001 002 023 005, ]![ 04, ]G[ 01 1 01 003 and the ]I[ lists.
    expect(g.cubeList).toEqual([1, 2, 23, 5]);
    expect(g.cubeMax).toBe(4);
    expect(g.mapPNum).toBe(1);
    expect(g.mapPlanet[0]).toBe(1);
    expect(g.mapSection[0]).toBe(3);
    expect(g.itemAvail[1].slice(0, g.itemAvailMax[1])).toEqual([13, 2, 7]); // WeapF 13 2 7
    expect(g.itemAvailMax).toEqual([1, 3, 4, 3, 1, 4, 4, 3, 3]);
  });

  test("the level comes from tyrian1.lvl level 9 with its shapes file and the 65500 sentinel", () => {
    loadLevel(files, 1, 1);
    const level = parseLevelFile(readData("tyrian1.lvl")).levels[9 - 1];
    expect(g.lvl.level.start).toBe(level.start);
    expect(g.maxEvent).toBe(level.events.length);
    expect(g.lvl.eventRec).toHaveLength(level.events.length + 1);
    expect(g.lvl.eventRec.at(-1)!.eventTime).toBe(65500);
    expect(g.lvl.eventRec.slice(0, -1)).toEqual(level.events);
    expect(g.lvl.eventRec[0]).not.toBe(level.events[0]); // copies: events modify eventRec
    expect(g.lvl.shapesFile).toBe(`shapes${level.shapeFile.toLowerCase()}.dat`);
    expect(g.levelEnemy.slice(0, g.levelEnemyMax)).toEqual(level.levelEnemy);
    expect([g.mapX, g.mapX2, g.mapX3]).toEqual([level.mapX, level.mapX2, level.mapX3]);
    // First events: scroll speed, then the enemy shape banks (newsh2, newsh4, newshe, newshp).
    expect(g.lvl.eventRec[0]).toMatchObject({ eventTime: 0, eventType: 2, eventDat: 1, eventDat2: 2 });
    expect(g.lvl.eventRec[1]).toMatchObject({ eventTime: 0, eventType: 5, eventDat: 1, eventDat2: 2, eventDat3: 9, eventDat4: 20 });
    // Tiles: layer 0 maps blank shapes to empty tiles, so every matched byte has pixels.
    const shapes = parseShapes(readData(g.lvl.shapesFile));
    const sh = level.mapSh[0][level.maps[0][0]] - 1;
    expect(g.lvl.tiles[0][level.maps[0][0]]).toEqual(shapes[sh] ?? new Uint8Array(24 * 28));
  });

  test("]h[ skips the normal-difficulty line on hard", () => {
    g.initialDifficulty = DIFFICULTY_HARD;
    loadLevel(files, 1, 1);
    expect(g.lvlFileNum).toBe(15); // ]L[ 9999 004 TYRIAN   18 15
  });

  test("event texts come from tyrian.hdt", () => {
    loadLevel(files, 1, 1);
    expect(g.miscText[20]).toBe("Good luck...");
    expect(g.outputs[0]).toBe("Enemy approaching from behind.");
  });
});

describe.skipIf(!hasData(...NEEDED))("world simulation on TYRIAN", () => {
  beforeEach(() => {
    resetPlayers();
    mt_srand(1);
    loadLevel(files, 1, 1);
    initLevelWorld();
    g.player[0].x = 100;
    g.player[0].y = 180;
    g.player[0].is_alive = true;
    g.background2 = true; // what JE_initProcessorType sets for every detail level but 386
  });

  test("background 1 draws 7 rows of 12 tiles from the bottom of the map at the start", () => {
    beginDrawList();
    draw_background_1();
    const tiles = drawList.items.filter((d): d is TileDraw => d.kind === "tile");
    expect(tiles).toHaveLength(7 * 12);
    // mapYPos = 292 * 14 - 1, map = mapYPos + mapXbpPos(0) - 12; row i = -1 is fully clipped.
    const first = 292 * 14 - 1 - 12 + 14;
    expect(tiles[0]).toMatchObject({ layer: 0, x: 0, y: 0, key: first, pass: Pass.Background1 });
    expect(tiles[13]).toMatchObject({ x: 24, y: 28, key: first + 15 });
    expect(new Set(tiles.map((t) => t.key)).size).toBe(tiles.length);
  });

  test("3000 ticks: events run, enemies spawn, move, fire and stay in bounds", () => {
    const seen = new Set<number>();
    let maxActive = 0;
    let shotsFired = 0;
    let enemyDraws = 0;
    let tileDraws = 0;

    for (let tick = 0; tick < 3000; tick++) {
      worldTick();

      expect(drawList.items.length).toBeGreaterThan(0);
      tileDraws += drawList.items.filter((d) => d.kind === "tile").length;
      const enemySprites = drawList.items.filter((d): d is SpriteDraw => d.kind === "sprite2" && d.key >= ENEMY_KEY_BASE);
      enemyDraws += enemySprites.length;
      for (const d of enemySprites) {
        expect(d.x).toBeGreaterThan(-60);
        expect(d.x).toBeLessThan(340);
        expect(d.index).toBeGreaterThan(0);
      }

      let active = 0;
      for (let i = 0; i < 100; i++) {
        if (g.enemyAvail[i] === 1) continue;
        active++;
        const e = g.enemy[i];
        seen.add(e.enemytype);
        expect(e.ex).toBeGreaterThanOrEqual(-80);
        expect(e.ex).toBeLessThanOrEqual(340);
        expect(e.ey).toBeGreaterThanOrEqual(-112);
        expect(e.ey).toBeLessThanOrEqual(200);
      }
      maxActive = Math.max(maxActive, active);
      shotsFired += g.enemyShotAvail.filter((a) => !a).length;
    }

    expect(g.curLoc).toBeGreaterThan(1000);
    expect(g.eventLoc).toBeGreaterThan(100);
    expect(g.enemySpriteSheetIds).toEqual([1, 2, 9, 20]);
    expect(g.enemySpriteSheets.map((s) => s?.id)).toEqual(["newsh2.shp", "newsh4.shp", "newshe.shp", "newshp.shp"]);
    expect(seen.size).toBeGreaterThan(5);
    expect(maxActive).toBeGreaterThan(3);
    expect(enemyDraws).toBeGreaterThan(1000);
    expect(tileDraws).toBeGreaterThan(3000 * 84);
    expect(shotsFired).toBeGreaterThan(0);
  });

  test("the run is deterministic for a seed", () => {
    const run = () => {
      mt_srand(7);
      loadLevel(files, 1, 1);
      initLevelWorld();
      g.player[0].x = 100;
      g.player[0].y = 180;
      const trace: number[] = [];
      for (let tick = 0; tick < 1500; tick++) {
        worldTick();
        for (let i = 0; i < 100; i++) if (g.enemyAvail[i] !== 1) trace.push(i, g.enemy[i].ex, g.enemy[i].ey);
      }
      return trace;
    };
    expect(run()).toEqual(run());
  });
});

describe.skipIf(!hasData(...NEEDED))("enemies and events", () => {
  beforeEach(() => {
    resetPlayers();
    mt_srand(1);
    loadLevel(files, 1, 1);
    initLevelWorld();
  });

  test("JE_makeEnemy seeds an enemy from enemyDat like the C", () => {
    const dat = g.res.enemyDat[10];
    const e = g.enemy[0];
    const avail = JE_makeEnemy(e, 10, 0);
    expect(avail).toBe(dat.armor > 0 ? 0 : 2);
    expect(e.enemytype).toBe(10);
    expect(e.exc).toBe(dat.xMove);
    expect(e.eyc).toBe(dat.yMove);
    expect(e.egr).toEqual(dat.eGraphic);
    expect(e.armorleft).toBe(dat.armor > 0 ? dat.armor : 255); // normal difficulty
    expect(e.enemyground).toBe((dat.explosionType & 1) === 0);
    if (dat.startXC === 0) expect(e.ex).toBe(dat.startX + 1);
    expect(g.totalEnemy).toBe(e.scoreitem ? 0 : 1);
  });

  test("JE_newEnemy fills the first free slot in its block of 25", () => {
    g.enemyAvail[25] = 0;
    expect(JE_newEnemy(25, 10, 0)).toBe(27);
    for (let i = 25; i < 50; i++) g.enemyAvail[i] = 0;
    expect(JE_newEnemy(25, 10, 0)).toBe(0);
  });

  test("JE_eventJump finds the first event at or after the new curLoc and keeps the return point", () => {
    g.curLoc = 50;
    const target = g.lvl.eventRec[20].eventTime;
    JE_eventJump(target);
    expect(g.curLoc).toBe(target);
    expect(g.returnLoc).toBe(51);
    const first = g.lvl.eventRec.findIndex((e) => e.eventTime >= target);
    expect(g.eventLoc).toBe(first); // eventLoc = tempW - 1: one before, eventSystem's ++ follows
    JE_eventJump(65535);
    expect(g.curLoc).toBe(51);
  });

  test("events 15/12 spawn event enemies at the event's position", () => {
    // Event 6: ground enemy (block 25) at eventdat2 - (mapX - 1) * 24 - 12, ey = -28 + eventdat5.
    g.lvl.eventRec[0] = { eventTime: 0, eventType: 6, eventDat: 10, eventDat2: 100, eventDat3: 2, eventDat5: 5, eventDat6: 0, eventDat4: 7 };
    g.eventLoc = 1;
    JE_eventSystem();
    expect(g.eventLoc).toBe(2);
    const e = g.enemy[25];
    expect(g.enemyAvail[25]).not.toBe(1);
    expect(e.ex).toBe(100 - (g.mapX - 1) * 24 - 12);
    expect(e.ey).toBe(-28 + 5);
    expect(e.linknum).toBe(7);
    expect(e.eyc).toBe(g.res.enemyDat[10].yMove + 2);
    expect(JE_searchFor(7)).toBe(true);
  });

  test("event 19 (global move) addresses enemies by link number", () => {
    JE_newEnemy(0, 10, 0);
    g.enemy[0].linknum = 3;
    g.lvl.eventRec[0] = { eventTime: 0, eventType: 19, eventDat: 4, eventDat2: -99, eventDat3: 0, eventDat5: 0, eventDat6: 0, eventDat4: 3 };
    g.eventLoc = 1;
    const eyc = g.enemy[0].eyc;
    JE_eventSystem();
    expect(g.enemy[0].exc).toBe(4);
    expect(g.enemy[0].eyc).toBe(eyc);
  });
});

describe.skipIf(!hasData(...NEEDED))("varz", () => {
  beforeEach(() => {
    resetPlayers();
    loadLevel(files, 1, 1);
    initLevelWorld();
  });

  test("JE_setupExplosion takes the first free slot and offsets type 6", () => {
    JE_setupExplosion(10, 20, 0, 6, false, false);
    expect(g.explosions[0]).toMatchObject({ x: 12, y: 32, sprite: 133, ttl: 7 });
    JE_setupExplosion(10, 200, 0, 1, false, false); // off screen: ignored
    expect(g.explosions[1].ttl).toBe(0);
  });

  test("JE_setupExplosionLarge queues a repeating explosion", () => {
    JE_setupExplosionLarge(true, 13, -5, 50);
    expect(g.explosions.filter((e) => e.ttl > 0)).toHaveLength(4);
    expect(g.rep_explosions[0]).toMatchObject({ ttl: 3, delay: 2, big: true, y: 50 });
    expect(g.rep_explosions[0].x).toBe(2 ** 32 - 5); // unsigned int, as in the C
  });

  test("JE_playerDamage drains shield, then armor, then kills", () => {
    const p = g.player[0];
    p.is_alive = true;
    p.shield = 5;
    p.armor = 10;
    expect(JE_playerDamage(3, p)).toBe(0);
    expect(p.shield).toBe(2);
    expect(JE_playerDamage(6, p)).toBe(6);
    expect([p.shield, p.armor]).toEqual([0, 6]);
    JE_playerDamage(20, p);
    expect(p.armor).toBe(0);
    expect(p.is_alive).toBe(false);
    expect(p.exploding_ticks).toBe(60);
  });

  test("JE_doSP spawns superpixels that JE_drawSP fades over 15 ticks", () => {
    JE_doSP(100, 100, 5, 3, 0x40);
    expect(g.superpixels.filter((s) => s.z === 15)).toHaveLength(5);
    for (let i = 0; i < 15; i++) JE_drawSP();
    expect(g.superpixels.every((s) => s.z === 0)).toBe(true);
  });

  test("JE_filterScreen records the filter for the renderer and runs the fade", () => {
    g.filtrationAvail = true;
    g.levelBrightness = -14;
    g.levelBrightnessChg = 1;
    g.filterFade = true;
    JE_filterScreen(3, -14);
    expect(drawList.filter).toBe(3);
    expect(drawList.brightness).toBe(-14);
    expect(g.levelBrightness).toBe(-13);
  });
});

test("BG_KEY_LAYER leaves room for every map cell", () => {
  expect(BG_KEY_LAYER).toBeGreaterThan(600 * 15);
});
