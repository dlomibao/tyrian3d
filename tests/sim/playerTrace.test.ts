// Cross-check against the real OpenTyrian C code: fixtures/player-trace.c.txt was produced by
// compiling OpenTyrian's sources (with Homebrew SDL2) with a driver that runs the same scripted input
// (fixtures/player-trace*.script) through the same player parts of JE_main's tick as
// tests/sim/playerHarness.ts, printing this trace format. Positions, velocities, power, shield,
// cash, weapon power, twiddle state, map offsets and every live player shot must match per tick.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";
import { simInput } from "../../src/sim/input";
import { calc_purple_balls_needed } from "../../src/sim/player";
import { roundf } from "../../src/sim/shots";
import { JE_drawOptions } from "../../src/sim/varz";
import { g, MAX_PWEAPON, newEnemy } from "../../src/sim/state";
import { freshGame, havePlayerData, tick } from "./playerHarness";

const fixture = (name: string) => readFileSync(join(__dirname, "fixtures", name), "utf8");

function placeEnemy(evalue: number, scoreitem: boolean, armorleft: number, type: number): void {
  const e = newEnemy();
  e.ex = g.player[0].x;
  e.ey = g.player[0].y;
  e.evalue = evalue;
  e.scoreitem = scoreitem;
  e.armorleft = armorleft;
  e.enemytype = type;
  g.enemy[0] = e;
  g.enemyAvail[0] = 0;
}

function traceLine(t: number): string {
  const p = g.player[0];
  const sf = g.SFCurrentCode[0];
  let s =
    `${t} p ${p.x} ${p.y} ${p.x_velocity} ${p.y_velocity} ${p.mouseX} ${p.mouseY} pw ${g.power} sh ${p.shield} ar ${p.armor}` +
    ` cash ${p.cash} wp ${p.items.weapon[0].power} pb ${p.purple_balls_needed} sf ${sf[0]} ${sf[1]} ${sf[2]} ${g.SFExecuted[0]}` +
    ` rep ${g.shotRepeat[0]} te ${g.textErase} map ${g.mapXOfs} ${g.mapX2Ofs} ${g.mapX3Ofs} inv ${p.invulnerable_ticks}` +
    ` mode ${p.weapon_mode} sound ${g.soundQueue[0]} ${g.soundQueue[7]}` +
    ` alive ${p.is_alive ? 1 : 0} ex ${p.exploding_ticks} le ${g.levelEnd} fx ${g.levelEndFxWait} rel ${g.reallyEndLevel ? 1 : 0} warp ${g.levelEndWarp}`;
  p.sidekick.forEach((k, i) => {
    s += ` sk${i} ${k.x} ${k.y} ${k.ammo} ${k.ammo_refill_ticks} ${k.animation_frame} ${k.animation_enabled ? 1 : 0} ${k.charge} ${k.charge_ticks}`;
  });
  s +=
    ` rot ${roundf(g.optionSatelliteRotate * 1000)} att ${g.optionAttachmentMove} ${g.optionAttachmentLinked ? 1 : 0}` +
    ` ${g.optionAttachmentReturn ? 1 : 0} rep ${g.shotRepeat[1]} ${g.shotRepeat[2]} ${g.shotRepeat[3]} shots`;
  for (let z = 0; z < MAX_PWEAPON; z++) {
    if (g.shotAvail[z] !== 0) {
      const d = g.playerShotData[z];
      s += ` ${z}:${d.shotX}:${d.shotY}:${d.shotXM}:${d.shotYM}:${g.shotAvail[z]}:${d.shotGr}:${d.shotDmg}:${d.shotAni}:${d.aimAtEnemy}`;
    }
  }
  return s;
}

describe.skipIf(!havePlayerData())("player trace vs OpenTyrian C", () => {
  test.each([
    ["player-trace.script", "player-trace.c.txt"],
    ["player-trace-2.script", "player-trace-2.c.txt"],
  ])("%s matches the C trace tick for tick", (script, golden) => {
    freshGame(1);
    const airEnemy = g.res.enemyDat.findIndex((d, i) => i > 0 && (d.explosionType & 1) === 0);

    const lines: string[] = [];
    let t = 0;
    for (const raw of fixture(script).split("\n")) {
      if (raw.startsWith("#") || raw.trim() === "") continue;
      if (raw.startsWith("!loadout")) {
        const [f, r, l, rt, pw] = raw.trim().split(/\s+/).slice(1).map(Number);
        const p = g.player[0];
        p.items.weapon[0].id = f;
        p.items.weapon[1].id = r;
        p.items.sidekick[0] = l;
        p.items.sidekick[1] = rt;
        p.items.weapon[0].power = pw;
        p.items.weapon[1].power = pw;
        calc_purple_balls_needed(p);
        JE_drawOptions();
        continue;
      }
      const [countStr, keys, event = ""] = raw.trim().split(/\s+/);
      for (let n = 0; n < Number(countStr); n++) {
        simInput.up = keys.includes("U");
        simInput.down = keys.includes("D");
        simInput.left = keys.includes("L");
        simInput.right = keys.includes("R");
        simInput.fire = keys.includes("F");
        simInput.changeFire = keys.includes("C");
        simInput.leftSidekick = keys.includes("l");
        simInput.rightSidekick = keys.includes("r");
        if (n === 0) {
          if (event === "P") placeEnemy(-1, true, 0, 1);
          else if (event === "B") placeEnemy(30000, false, 0, 1);
          else if (event === "$") placeEnemy(100, true, 0, 1);
          else if (event === "E") placeEnemy(0, false, 10, airEnemy);
          else if (event === "X") {
            g.player[0].shield = 0;
            g.player[0].armor = 1;
            g.player[0].invulnerable_ticks = 0;
            placeEnemy(0, false, 10, airEnemy);
          } else if (event === "T") {
            placeEnemy(0, false, 50, airEnemy);
            g.enemy[0].ex = 150;
            g.enemy[0].ey = 30;
          } else if (event === "W") {
            g.endLevel = true;
            g.levelEnd = 40;
          }
        }
        tick();
        lines.push(traceLine(++t));
      }
    }

    const expected = fixture(golden).trimEnd().split("\n");
    expect(lines.length).toBe(expected.length);
    for (let i = 0; i < expected.length; i++) expect(lines[i]).toBe(expected[i]);
  });
});
