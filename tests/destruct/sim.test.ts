// Destruct's rules (src/destruct/sim.ts): terrain damage, the per-side turn logic (fire delays,
// changing units and weapons, the end of a round) and how it draws on the shared RNG. The whole
// game is also checked tick by tick against the C in trace.test.ts.
import { beforeEach, describe, expect, test, vi } from "vitest";
import {
  de_state_t,
  DE_CycleWeaponDown,
  DE_CycleWeaponUp,
  DestructGame,
  EXPL_NORMAL,
  goodsel,
  type KeysActive,
  MAP_FUZZY,
  MAP_HOLES,
  MAP_RINGS,
  MAP_TALL,
  MAP_WALLS,
  MODE_5CARDWAR,
  MODE_TRADITIONAL,
  PIXEL_DIRT,
  PLAYER_LEFT,
  PLAYER_RIGHT,
  SCREEN_W,
  SHOT_DEMO,
  SHOT_INVALID,
  SHOT_LARGE,
  SHOT_LARGEDIRT,
  SHOT_SMALL,
  shotDelay,
  UNIT_HELI,
  UNIT_SATELLITE,
  UNIT_TANK,
  weaponSystems,
} from "../../src/destruct/sim";
import { mt_rand, mt_srand } from "../../src/sim/mtrand";

/** keysactive for tests: the codes held, with the game's releases recorded. */
function keys(...held: string[]): KeysActive & { held: Set<string> } {
  const set = new Set(held);
  return { held: set, isDown: (c) => set.has(c), release: (c) => void set.delete(c) };
}
const NONE = keys();

/** A game with a round set up for two humans (the computer off, so the RNG stays put). */
function humanRound(seed: number, mode = MODE_5CARDWAR): DestructGame {
  mt_srand(seed);
  const game = new DestructGame();
  game.startSession();
  game.destruct_player.forEach((p) => (p.is_cpu = false));
  game.startRound(mode);
  return game;
}

const at = (x: number, y: number) => y * SCREEN_W + x;
const countDirt = (g: DestructGame, x0: number, y0: number, x1: number, y1: number) => {
  let n = 0;
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (g.tempScreen[at(x, y)] === PIXEL_DIRT) n++;
  return n;
};

describe("terrain", () => {
  let game: DestructGame;
  beforeEach(() => {
    game = new DestructGame();
    game.tempScreen.fill(0);
    // A solid block of dirt from row 100 down, and no units in the way.
    for (let y = 100; y < 200; y++) for (let x = 0; x < SCREEN_W; x++) game.tempScreen[at(x, y)] = PIXEL_DIRT;
    game.DE_ResetUnits();
    game.DE_ResetWeapons();
    mt_srand(7);
  });

  test("a normal explosion burns the dirt away, and the fire fades to black", () => {
    game.JE_makeExplosion(160, 130, SHOT_LARGE);
    expect(game.exploRec[0]).toMatchObject({ isAvailable: false, x: 160, y: 130, explowidth: 2, explomax: 30, exploType: EXPL_NORMAL });
    for (let t = 0; t < 30; t++) {
      game.JE_tempScreenChecking();
      game.DE_RunTickExplosions();
    }
    expect(game.exploRec[0].isAvailable).toBe(true); // it ends when its width reaches explomax
    // Its middle is fire (241-255), no longer dirt...
    expect(countDirt(game, 155, 125, 165, 135)).toBeLessThan(20);
    expect(game.tempScreen[at(160, 130)]).toBeGreaterThanOrEqual(241);
    // ...which fades a step a tick to PIXEL_BLACK, leaving a crater.
    for (let t = 0; t < 20; t++) game.JE_tempScreenChecking();
    expect(game.tempScreen[at(160, 130)]).toBe(0);
    // Far away, the dirt is untouched.
    expect(countDirt(game, 0, 150, 40, 199)).toBe(41 * 50);
  });

  test("a dirt shot's explosion piles dirt up instead", () => {
    const before = countDirt(game, 120, 40, 200, 99);
    expect(before).toBe(0);
    game.JE_makeExplosion(160, 80, SHOT_LARGEDIRT);
    for (let t = 0; t < 40; t++) game.DE_RunTickExplosions();
    expect(countDirt(game, 120, 40, 200, 99)).toBeGreaterThan(200);
  });

  test("explosions hurt the units they reach, and destroying one scores for the other side", () => {
    const right = game.destruct_player[PLAYER_RIGHT];
    const unit = right.unit[0];
    Object.assign(unit, { unitX: 150, unitY: 100, unitType: UNIT_TANK, health: 5 });
    right.unitsRemaining = 1;
    game.JE_makeExplosion(156, 95, SHOT_LARGE);
    for (let t = 0; t < 10 && unit.health > 0; t++) game.DE_RunTickExplosions();
    expect(unit.health).toBeLessThanOrEqual(0);
    expect(right.unitsRemaining).toBe(0);
    expect(game.destruct_player[PLAYER_LEFT].score).toBe(1);
  });

  test("units stand on 10 of the 12 dirt pixels under them, and fall when it's gone", () => {
    const unit = game.destruct_player[PLAYER_LEFT].unit[0];
    Object.assign(unit, { unitX: 50, unitY: 100, unitType: UNIT_TANK, health: 200 });
    expect(game.JE_stabilityCheck(50, 100)).toBe(false); // solid
    for (let x = 49; x < 52; x++) game.tempScreen[at(x, 100)] = 0; // 3 of 12 gone
    expect(game.JE_stabilityCheck(50, 100)).toBe(true);
    for (let y = 100; y < 110; y++) for (let x = 40; x < 70; x++) game.tempScreen[at(x, y)] = 0;
    for (let t = 0; t < 12; t++) game.DE_GravityLowerUnit(unit);
    expect(unit.unitY).toBe(110); // one pixel a tick, down to the dirt
  });

  test("generation: dirt from each column's height down, units on flattened ground, walls when flagged", () => {
    const g = humanRound(3);
    const m = g.world.baseMap;
    for (let x = 1; x <= 318; x++) {
      expect(m[x]).toBeGreaterThanOrEqual(40);
      expect(m[x]).toBeLessThanOrEqual(195);
    }
    for (const p of g.destruct_player) {
      for (const u of p.unit.filter((u) => u.health > 0 && u.unitType !== UNIT_SATELLITE)) {
        // JE_placementPosition levels the 14 columns under each unit to its ground height (a later
        // unit or wall placed over them can only dig them deeper).
        for (let x = u.unitX - 1; x < u.unitX + 13; x++) expect(m[x]).toBeGreaterThanOrEqual(u.unitY);
        expect(g.tempScreen[at(u.unitX + 5, u.unitY)]).toBe(PIXEL_DIRT);
      }
    }
    expect(g.world.mapWalls.some((w) => w.wallExist)).toBe((g.world.mapFlags & MAP_WALLS) !== 0);
  });
});

describe("turns", () => {
  test("each side fires, then waits out its weapon's shotDelay", () => {
    const game = humanRound(11, MODE_TRADITIONAL);
    const right = game.destruct_player[PLAYER_RIGHT];
    const unit = right.unit[right.unitSelected];
    expect(unit.shotType).toBe(SHOT_SMALL);
    const fire = keys("Enter");
    game.DE_RunTick(fire);
    expect(game.shotRec.filter((s) => !s.isAvailable)).toHaveLength(1);
    expect(right.shotDelay).toBe(shotDelay[SHOT_SMALL]);
    // Holding fire does nothing until the delay has run out.
    for (let t = 0; t < shotDelay[SHOT_SMALL] - 1; t++) game.DE_RunTick(fire);
    expect(right.shotDelay).toBe(1);
    game.DE_RunTick(fire);
    expect(right.shotDelay).toBe(shotDelay[SHOT_SMALL]); // fired again
  });

  test("the two sides share the keyboard: each reads only its own keys", () => {
    const game = humanRound(12, MODE_TRADITIONAL);
    const [left, right] = game.destruct_player;
    const la = left.unit[left.unitSelected].power;
    const ra = right.unit[right.unitSelected].power;
    game.DE_RunTick(keys("KeyA")); // left: more power
    expect(left.unit[left.unitSelected].power).toBeGreaterThan(la);
    expect(right.unit[right.unitSelected].power).toBe(ra);
    game.DE_RunTick(keys("ArrowUp")); // right: more power
    expect(right.unit[right.unitSelected].power).toBeGreaterThan(ra);
  });

  test("change and weapon keys act once per press; held keys repeat", () => {
    const game = humanRound(5);
    const left = game.destruct_player[PLAYER_LEFT];
    const k = keys("AltLeft", "ControlLeft");
    const before = left.unitSelected;
    game.DE_RunTick(k);
    expect(k.held.size).toBe(0); // DE_RunTickGetInput let go of both
    expect(left.unitSelected).not.toBe(before);
  });

  test("changing unit skips destroyed units and satellites", () => {
    const game = humanRound(5);
    const left = game.destruct_player[PLAYER_LEFT];
    left.unit[1].health = 0;
    left.unit[2].unitType = UNIT_SATELLITE;
    left.unit[2].shotType = SHOT_INVALID;
    left.unitSelected = 1;
    game.DE_RunTickCycleDeadUnits();
    expect(left.unitSelected).toBe(3);
  });

  test("weapons cycle through what the unit carries", () => {
    const unit = new DestructGame().destruct_player[0].unit[0];
    Object.assign(unit, { unitType: UNIT_HELI, shotType: 0 });
    const seen: number[] = [];
    for (let i = 0; i < 4; i++) {
      DE_CycleWeaponUp(unit);
      seen.push(unit.shotType);
    }
    expect(seen.every((s) => weaponSystems[UNIT_HELI][s] === 1)).toBe(true);
    DE_CycleWeaponDown(unit);
    expect(unit.shotType).toBe(seen[2]);
  });

  test("a round ends 80 ticks after a side has nothing left, with the mode's bonus", () => {
    const game = humanRound(9, MODE_TRADITIONAL);
    const left = game.destruct_player[PLAYER_LEFT];
    for (const u of left.unit) u.health = 0;
    left.unitsRemaining = 0;
    expect(game.DE_RunTick(NONE)).toBe(de_state_t.STATE_CONTINUE);
    expect(game.soundQueue[7]).toBe(30); // V_CLEARED_PLATFORM
    expect(game.endDelay).toBe(80);
    expect(game.destruct_player[PLAYER_RIGHT].score).toBe(0); // ModeScore: no bonus in Traditional
    let state = de_state_t.STATE_CONTINUE;
    let ticks = 1;
    while (state === de_state_t.STATE_CONTINUE) {
      state = game.DE_RunTick(NONE);
      ticks++;
    }
    expect(state).toBe(de_state_t.STATE_RELOAD);
    expect(ticks).toBe(81);
  });

  test("Escape goes back to the mode select, Backspace makes a new map, F10/F11 swap computer and human", () => {
    const game = humanRound(1);
    expect(game.DE_RunTick(keys("Escape"))).toBe(de_state_t.STATE_INIT);
    expect(game.DE_RunTick(keys("Backspace"))).toBe(de_state_t.STATE_RELOAD);
    game.DE_RunTick(keys("F10"));
    expect(game.destruct_player[PLAYER_LEFT].is_cpu).toBe(true);
    game.DE_RunTick(keys("F11"));
    expect(game.destruct_player[PLAYER_RIGHT].is_cpu).toBe(true);
  });
});

describe("RNG", () => {
  test("a map is drawn from mt_rand in the C's order: walls, holes, the shape, then the song", () => {
    mt_srand(42);
    const r = [mt_rand(), mt_rand(), mt_rand(), mt_rand()];
    let flags = 0;
    if (r[0] % 2 === 0) flags |= MAP_WALLS;
    if (r[1] % 4 === 0) flags |= MAP_HOLES;
    flags |= [MAP_FUZZY, MAP_TALL, MAP_RINGS, 0][r[2] % 4];
    const game = humanRound(42);
    expect(game.world.mapFlags).toBe(flags);
    expect(game.song).toBe(goodsel[r[3] % 14] - 1);
  });

  test("the same seed makes the same battlefield; another seed doesn't", () => {
    const a = humanRound(2024);
    const b = humanRound(2024);
    const c = humanRound(2025);
    expect(Buffer.from(a.tempScreen).equals(Buffer.from(b.tempScreen))).toBe(true);
    expect(a.destruct_player.map((p) => p.unit.map((u) => [u.unitX, u.unitY, u.unitType]))).toEqual(b.destruct_player.map((p) => p.unit.map((u) => [u.unitX, u.unitY, u.unitType])));
    expect(Buffer.from(a.tempScreen).equals(Buffer.from(c.tempScreen))).toBe(false);
  });

  test("only the shared mt_rand: never Math.random", () => {
    const spy = vi.spyOn(Math, "random");
    const game = humanRound(77);
    game.destruct_player.forEach((p) => (p.is_cpu = true));
    for (let t = 0; t < 500; t++) game.DE_RunTick(NONE);
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  test("two humans with nothing happening use no random numbers; the computer draws every tick", () => {
    const game = humanRound(8);
    mt_srand(1);
    for (let t = 0; t < 50; t++) game.DE_RunTick(NONE);
    const after = mt_rand();
    mt_srand(1);
    expect(after).toBe(mt_rand());

    game.destruct_player[PLAYER_LEFT].is_cpu = true;
    mt_srand(1);
    game.DE_RunTick(NONE);
    const next = mt_rand();
    mt_srand(1);
    expect(next).not.toBe(mt_rand());
  });

  test("walls: a demolisher knocks one down; other shots bounce off (no RNG involved)", () => {
    const game = new DestructGame();
    game.tempScreen.fill(0);
    game.DE_ResetUnits();
    game.DE_ResetWeapons();
    game.world.mapWalls[0] = { wallExist: true, wallX: 100, wallY: 100 };
    const shoot = (type: number) => Object.assign(game.shotRec[0], { isAvailable: false, x: 98, y: 105, xmov: 3, ymov: 0, shottype: type, trailc: [0, 0, 0, 0] });
    shoot(SHOT_SMALL);
    game.DE_RunTickShots();
    expect(game.world.mapWalls[0].wallExist).toBe(true);
    expect(game.shotRec[0].xmov).toBeLessThan(0);
    shoot(SHOT_DEMO);
    game.DE_RunTickShots();
    expect(game.world.mapWalls[0].wallExist).toBe(false);
    expect(game.shotRec[0].isAvailable).toBe(true);
  });
});
