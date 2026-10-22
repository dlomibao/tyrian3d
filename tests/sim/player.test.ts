import { beforeEach, describe, expect, test } from "vitest";
import { type SpriteDraw } from "../../src/sim/draw";
import { simInput } from "../../src/sim/input";
import { JE_playerCollide, PLAYER_KEY_BASE } from "../../src/sim/mainint";
import { calc_purple_balls_needed } from "../../src/sim/player";
import { SHOT_FRONT } from "../../src/sim/shots";
import { S_POWERUP } from "../../src/sim/sndmast";
import { DIFFICULTY_NORMAL, FRONT_WEAPON, g, REAR_WEAPON } from "../../src/sim/state";
import { drawList, freshGame, havePlayerData, tick } from "./playerHarness";

const sprite2Draws = () => drawList.items.filter((d): d is SpriteDraw => d.kind === "sprite2");
const activeShots = () => g.shotAvail.flatMap((v, i) => (v !== 0 ? [i] : []));

describe.skipIf(!havePlayerData())("new game", () => {
  beforeEach(() => freshGame());

  test("starting loadout matches JE_initPlayerData and newGame (1 player, episode 1)", () => {
    const { items } = g.res;
    const p = g.player[0];
    expect(items.ships[p.items.ship].name.trim()).toBe("USP Talon   Light Fighter");
    expect(items.weaponPorts[p.items.weapon[FRONT_WEAPON].id].name.trim()).toBe("Pulse-Cannon");
    expect(p.items.weapon[FRONT_WEAPON].power).toBe(1);
    expect(p.items.weapon[REAR_WEAPON].id).toBe(0);
    expect(items.shields[p.items.shield].name.trim()).toBe("Gencore High Energy Shield");
    expect(items.powerSys[p.items.generator].name.trim()).toBe("Advanced MR-12");
    expect(p.items.sidekick).toEqual([0, 0]);
    expect(p.items.special).toBe(0);
    expect(p.cash).toBe(10000);
    expect(p.weapon_mode).toBe(1);
    expect(g.difficultyLevel).toBe(DIFFICULTY_NORMAL);
    expect(g.initialDifficulty).toBe(DIFFICULTY_NORMAL);
    expect(g.onePlayerAction).toBe(false);
    expect(g.twoPlayerMode).toBe(false);
    expect(g.mainLevel).toBe(1);
    expect(g.lastLevelName).toBe("NEW GAME");
    // Player 2's (unused) loadout: same, plus a Vulcan Cannon rear weapon.
    expect(g.player[1].items.weapon[REAR_WEAPON].id).toBe(15);
    expect(g.player[1].items.sidekick_level).toBe(101);
  });

  test("lives alias the weapon power, as the C pointer does", () => {
    const p = g.player[0];
    expect(p.lives.value).toBe(1);
    p.items.weapon[FRONT_WEAPON].power = 3;
    expect(p.lives.value).toBe(3);
    expect(g.player[1].lives.value).toBe(g.player[1].items.weapon[REAR_WEAPON].power);
  });

  test("level start sets up the ship, shield and generator from the item data", () => {
    const { items } = g.res;
    const p = g.player[0];
    expect([p.x, p.y]).toEqual([100, 180]);
    expect(g.shipGr).toBe(items.ships[1].shipGraphic);
    expect(g.shipGr).toBe(233);
    expect(g.shipGrPtr).toBe(g.res.spriteSheet9);
    expect(p.armor).toBe(items.ships[1].dmg);
    expect(p.initial_armor).toBe(p.armor);
    expect(p.shield).toBe(items.shields[4].mpwr);
    expect(p.shield_max).toBe(items.shields[4].mpwr * 2);
    expect(g.shieldT).toBe((items.shields[4].tpwr * 20) & 0xff);
    expect(g.powerAdd).toBe(items.powerSys[2].power);
    expect(p.invulnerable_ticks).toBe(100);
    expect(p.purple_balls_needed).toBe(1);
    expect(g.shotRepeat.every((v) => v === 1)).toBe(true);
    expect(g.messageText).toBe("Good luck...");
    expect(g.textErase).toBe(100);
  });
});

describe.skipIf(!havePlayerData())("movement", () => {
  beforeEach(() => freshGame());

  test("first tick clamps the start position into bounds", () => {
    tick();
    expect([g.player[0].x, g.player[0].y]).toEqual([100, 160]);
  });

  test("holding right accelerates per the C velocity/friction rules", () => {
    tick();
    simInput.right = true;
    const xs: number[] = [];
    const vs: number[] = [];
    for (let i = 0; i < 8; i++) {
      tick();
      xs.push(g.player[0].x);
      vs.push(g.player[0].x_velocity);
    }
    // Each tick: the key moves the ship 1 px and adds 1 to the velocity; x friction takes 1 off
    // every other tick; the velocity is capped at 4.
    // (After the first tick, x_friction_ticks is 1, so friction applies on even ticks here.)
    expect(vs).toEqual([1, 1, 2, 2, 3, 3, 4, 4]);
    expect(xs).toEqual([102, 104, 107, 110, 114, 118, 123, 128]);
  });

  test("releasing the key lets friction stop the ship", () => {
    tick();
    simInput.right = true;
    for (let i = 0; i < 10; i++) tick();
    simInput.right = false;
    for (let i = 0; i < 20; i++) tick();
    expect(g.player[0].x_velocity).toBe(0);
    const x = g.player[0].x;
    tick();
    expect(g.player[0].x).toBe(x);
  });

  test("respects the play-area bounds (40..256, 10..160)", () => {
    simInput.left = true;
    simInput.up = true;
    for (let i = 0; i < 100; i++) tick();
    expect([g.player[0].x, g.player[0].y]).toEqual([40, 10]);
    simInput.left = simInput.up = false;
    simInput.right = simInput.down = true;
    for (let i = 0; i < 100; i++) tick();
    expect([g.player[0].x, g.player[0].y]).toEqual([256, 160]);
  });

  test("draws the ship from shipGrPtr at (x - 5, y - 7), banking with velocity", () => {
    tick();
    let ship = sprite2Draws().find((d) => d.key === PLAYER_KEY_BASE);
    expect(ship).toMatchObject({ sheet: g.res.spriteSheet9, index: 233, x: 95, y: 153, size: 2, effect: "blend" });
    simInput.right = true;
    for (let i = 0; i < 6; i++) tick();
    ship = sprite2Draws().find((d) => d.key === PLAYER_KEY_BASE);
    // ship_banking = x_velocity / 2 + (x - mouseX) / 6, clamped to -2..2
    const p = g.player[0];
    const banking = Math.max(-2, Math.min(2, Math.trunc(p.x_velocity / 2) + Math.trunc((p.x - p.mouseX) / 6)));
    expect(banking).toBeGreaterThan(0);
    expect(ship).toMatchObject({ index: 233 + banking * 2, x: p.x - 5, y: p.y - 7 });
  });

  test("the ship stops blending once invulnerability runs out, and casts a shadow", () => {
    for (let i = 0; i < 101; i++) tick();
    const draws = sprite2Draws();
    expect(draws.find((d) => d.key === PLAYER_KEY_BASE)?.effect).toBe("none");
    const shadow = draws.find((d) => d.key === PLAYER_KEY_BASE + 2);
    expect(shadow).toMatchObject({ effect: "darken", y: g.player[0].y - 7 + 10 });
  });
});

describe.skipIf(!havePlayerData())("firing the Pulse-Cannon", () => {
  beforeEach(() => freshGame());

  test("holding fire with full power fires every shotrepeat + 1 ticks", () => {
    const weapon = g.res.items.weapons[g.res.items.weaponPorts[1].op[0][0]];
    expect(weapon.shotRepeat).toBe(3);
    simInput.fire = true;
    const fired: number[] = [];
    let last = 0;
    for (let t = 1; t <= 20; t++) {
      tick(900);
      const n = activeShots().length;
      if (n > last) fired.push(t);
      last = n;
    }
    // shotRepeat starts at 1 (memset), so the first shot comes on tick 2, then every 4 ticks.
    expect(fired).toEqual([2, 6, 10, 14, 18]);
  });

  test("power from the generator limits the first shot (power 14/tick, cost 30)", () => {
    simInput.fire = true;
    const fired: number[] = [];
    let created = 0;
    for (let t = 1; t <= 20; t++) {
      const before = g.shotRepeat[SHOT_FRONT];
      tick();
      if (g.shotRepeat[SHOT_FRONT] === 3 && before === 0) fired.push(t);
      created = activeShots().length;
    }
    expect(fired).toEqual([3, 7, 11, 15, 19]);
    expect(created).toBe(5);
  });

  test("shots carry the weapon's damage, sprite and speed, and move up 10 px a tick", () => {
    simInput.fire = true;
    tick(900);
    tick(900);
    simInput.fire = false;
    const [id] = activeShots();
    const shot = g.playerShotData[id];
    const p = g.player[0];
    expect(shot).toMatchObject({ shotDmg: 2, shotGr: 59, shotYM: -10, shotXM: 0, shotX: p.x, shotY: p.y, playerNumber: 1 });
    expect(g.shotAvail[id]).toBe(255);
    expect(g.soundQueue[0]).toBe(25);
    const y0 = shot.shotY;
    tick(900);
    expect(shot.shotY).toBe(y0 - 10);
    const draw = sprite2Draws().find((d) => d.sheet === g.res.spriteSheet8 && d.index === 59 && d.effect === "none");
    const shadow = sprite2Draws().find((d) => d.sheet === g.res.spriteSheet8 && d.index === 59 && d.effect === "darken");
    expect(shadow).toMatchObject({ x: shot.shotX + 1, y: shot.shotY + 10, key: (draw?.key ?? 0) + 1 });
    expect(draw).toMatchObject({ x: shot.shotX + 1, y: shot.shotY });
    // Off the top of the screen (y < -15) the shot is freed.
    for (let i = 0; i < 20; i++) tick(900);
    expect(g.shotAvail[id]).toBe(0);
  });
});

describe.skipIf(!havePlayerData())("pick-ups and collisions", () => {
  beforeEach(() => {
    freshGame();
    tick();
  });

  function placeEnemy(evalue: number, scoreitem: boolean) {
    const e = g.enemy[0];
    e.ex = g.player[0].x;
    e.ey = g.player[0].y;
    e.mapoffset = 0;
    e.evalue = evalue;
    e.scoreitem = scoreitem;
    e.enemytype = 1;
    g.enemyAvail[0] = 0;
    return e;
  }

  test("a front weapon power-up (evalue -1) raises the weapon power", () => {
    placeEnemy(-1, true);
    JE_playerCollide(g.player[0], 1);
    expect(g.player[0].items.weapon[FRONT_WEAPON].power).toBe(2);
    expect(g.enemyAvail[0]).toBe(1);
    expect(g.soundQueue[7]).toBe(S_POWERUP);
    expect(g.messageText).toBe("Front Weapon Power-Up");
    // The next volley uses the power-2 pattern.
    simInput.fire = true;
    for (let i = 0; i < 5; i++) tick(900);
    const ids = activeShots();
    expect(g.playerShotData[ids[ids.length - 1]].shotGr).toBe(g.res.items.weapons[g.res.items.weaponPorts[1].op[0][1]].sg[0]);
  });

  test("a purple ball (evalue 30000) powers up once enough are collected", () => {
    placeEnemy(30000, false);
    JE_playerCollide(g.player[0], 1);
    expect(g.player[0].items.weapon[FRONT_WEAPON].power).toBe(2);
    expect(g.player[0].cash).toBe(10100);
    // Power 2 needs 2 balls for the next level.
    expect(g.player[0].purple_balls_needed).toBe(2);
    placeEnemy(30000, false);
    JE_playerCollide(g.player[0], 1);
    expect(g.player[0].items.weapon[FRONT_WEAPON].power).toBe(2);
    expect(g.player[0].purple_balls_needed).toBe(1);
  });

  test("power-ups past 11 give 1000 credits instead", () => {
    g.player[0].items.weapon[FRONT_WEAPON].power = 11;
    calc_purple_balls_needed(g.player[0]);
    placeEnemy(-1, true);
    JE_playerCollide(g.player[0], 1);
    expect(g.player[0].items.weapon[FRONT_WEAPON].power).toBe(11);
    expect(g.player[0].cash).toBe(11000);
  });

  test("coins add their value; data cubes count up", () => {
    placeEnemy(150, true);
    JE_playerCollide(g.player[0], 1);
    expect(g.player[0].cash).toBe(10150);
    placeEnemy(1, true);
    JE_playerCollide(g.player[0], 1);
    expect(g.cubeMax).toBe(1);
  });

  test("armor pick-ups (evalue > 20000) add armor, capped at 28", () => {
    placeEnemy(20005, false);
    JE_playerCollide(g.player[0], 1);
    expect(g.player[0].armor).toBe(15);
    placeEnemy(20020, false);
    JE_playerCollide(g.player[0], 1);
    expect(g.player[0].armor).toBe(28);
  });

  test("ramming an enemy costs damageRate shield once invulnerability is over", () => {
    const e = placeEnemy(0, false);
    e.armorleft = 10;
    // Find an air enemy (explosiontype even) for the collision.
    e.enemytype = g.res.enemyDat.findIndex((d, i) => i > 0 && (d.explosionType & 1) === 0);
    JE_playerCollide(g.player[0], 1);
    expect(g.player[0].shield).toBe(5); // still invulnerable
    g.player[0].invulnerable_ticks = 0;
    JE_playerCollide(g.player[0], 1);
    expect(g.player[0].shield).toBe(3);
    expect(e.armorleft).toBe(8);
  });
});
