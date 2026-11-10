// The debug console's cheats (D109), as changes to the sim's own state through its own functions, so
// they act as the real game's pickups and cheats do: a new gun fires from its first shot pattern
// (shotMultiPos reset, as a pickup does), power goes through the weapon's power level (and the
// purple balls the next level needs, calc_purple_balls_needed), sidekicks are set up by
// JE_drawOptions, armour is capped by JE_drawArmor, god mode is the original's own (youAreCheating:
// F2 F3 F6), a kill is a shot's kill (destroyEnemy), a skip the original's skip-level cheat. The HUD
// reads the state each frame, so its bars follow.

import { FRONT_WEAPON, g, REAR_WEAPON, type Player } from "../../sim/state";
import { calc_purple_balls_needed } from "../../sim/player";
import { JE_drawArmor, JE_drawOptions } from "../../sim/varz";
import { JE_drawTextWindow } from "../../sim/mainint";
import { destroyEnemy } from "../../sim/game";
import { cheatSkipLevel } from "../../sim/cheats";
import { SHOT_FRONT, SHOT_LEFT_SIDEKICK, SHOT_REAR, SHOT_RIGHT_SIDEKICK } from "../../sim/shots";
import { u8 } from "../../sim/cint";
import { OPTION_NUM, PORT_NUM } from "../../data/items";

/** Thrown for a request the game can't take (out of range, no such item): the console shows it as an error. */
export class CheatError extends Error {}

/** The player the console's cheats act on: player 1 (also the one-player game's). */
const player = (): Player => g.player[0];

/** The highest armour the game keeps (JE_drawArmor's cap). */
export const ARMOR_CAP = 28;
/** Weapon power levels (power_up_weapon stops at 11). */
export const POWER_MAX = 11;

function int(v: number, what: string, min: number, max: number): number {
  if (!Number.isInteger(v) || v < min || v > max) throw new CheatError(`${what} must be a whole number from ${min} to ${max}`);
  return v;
}

/** Toggle (or set) the original's invulnerability (youAreCheating). Returns the new state. */
export function setGod(on: boolean = !g.youAreCheating): boolean {
  g.youAreCheating = on;
  return on;
}

/** Set the armour, as JE_drawArmor keeps it (at most 28). Returns the armour now. */
export function setArmor(n: number): number {
  const p = player();
  p.armor = int(n, "armor", 0, 255);
  JE_drawArmor();
  return p.armor;
}

/** Set the shield, up to the shield's maximum (shield_max, the most the generator recharges it to). */
export function setShield(n: number): number {
  const p = player();
  p.shield = Math.min(int(n, "shield", 0, 255), p.shield_max);
  return p.shield;
}

/** Full armour (the ship's, initial_armor) and shield (shield_max). */
export function heal(): { armor: number; shield: number } {
  const p = player();
  p.armor = p.initial_armor;
  JE_drawArmor();
  p.shield = p.shield_max;
  return { armor: p.armor, shield: p.shield };
}

/** Set the credits (cash). */
export function setCredits(n: number): number {
  const p = player();
  p.cash = int(n, "credits", 0, 2 ** 31 - 1);
  return p.cash;
}

/** A port's name in this episode's item data. */
export function weaponName(id: number): string {
  return g.res.items.weaponPorts[id]?.name.trim() || (id === 0 ? "None" : `#${id}`);
}

/** A sidekick's name in this episode's item data. */
export function sidekickName(id: number): string {
  return g.res.items.options[id]?.name.trim() || (id === 0 ? "None" : `#${id}`);
}

/**
 * Fit the front or rear port with weapon `id` (an item number, as in the shop's lists; 0 = none) at
 * `power` (default: keep the power). As a pickup does: the port's shot pattern restarts, and the
 * message bar says what was fitted. The rear gun's mode falls back to 1 by JE_playerMovement
 * when the new gun has fewer modes.
 */
export function setWeapon(port: "front" | "rear", id: number, power?: number): { id: number; power: number; name: string } {
  const slot = port === "front" ? FRONT_WEAPON : REAR_WEAPON;
  const w = player().items.weapon[slot];
  w.id = u8(int(id, "weapon id", 0, PORT_NUM));
  if (power !== undefined) w.power = u8(int(power, "power", 1, POWER_MAX));
  else if (w.power === 0) w.power = 1; // a port fitted without power (the C's "does this ever happen?")
  g.shotMultiPos[slot === FRONT_WEAPON ? SHOT_FRONT : SHOT_REAR] = 0;
  calc_purple_balls_needed(player());
  JE_drawTextWindow(`${g.miscText[64 - 1] ?? ""} ${weaponName(w.id)}`.trim());
  return { id: w.id, power: w.power, name: weaponName(w.id) };
}

/** Set the front weapon's power (1-11), as power_up_weapon would step it. */
export function setPower(n: number, port: "front" | "rear" = "front"): number {
  const slot = port === "front" ? FRONT_WEAPON : REAR_WEAPON;
  const w = player().items.weapon[slot];
  w.power = u8(int(n, "power", 1, POWER_MAX));
  g.shotMultiPos[slot] = 0;
  calc_purple_balls_needed(player());
  return w.power;
}

/** Fit the left or right sidekick with option `id` (0 = none); JE_drawOptions sets up its ammo and charge. */
export function setSidekick(side: "left" | "right", id: number): { id: number; name: string } {
  const i = side === "left" ? 0 : 1;
  const p = player();
  p.items.sidekick[i] = u8(int(id, "sidekick id", 0, OPTION_NUM));
  g.shotMultiPos[i === 0 ? SHOT_LEFT_SIDEKICK : SHOT_RIGHT_SIDEKICK] = 0;
  JE_drawOptions();
  JE_drawTextWindow(`${g.miscText[64 - 1] ?? ""} ${sidekickName(p.items.sidekick[i])}`.trim());
  return { id: p.items.sidekick[i], name: sidekickName(p.items.sidekick[i]) };
}

/** The playfield an enemy counts as on screen in: the sim's 320x200 screen, with a sprite's margin. */
const ON_SCREEN = { x0: -24, x1: 290, y0: -24, y1: 200 };

/**
 * Kill every enemy on screen that a shot could: not the indestructible (armour 255) and not the
 * pickups (evalue 30000 and up). Each dies as a shot kills it (destroyEnemy), linked parts, drops
 * and score included. Returns how many were killed (linked parts counted).
 */
export function killAll(): number {
  const before = g.enemyKilled;
  for (let b = 0; b < g.enemy.length; b++) {
    if (g.enemyAvail[b] !== 0) continue; // gone, or already dying
    const e = g.enemy[b];
    if (e.armorleft === 255 || e.evalue >= 30000) continue;
    const x = e.ex + e.mapoffset;
    if (x < ON_SCREEN.x0 || x > ON_SCREEN.x1 || e.ey < ON_SCREEN.y0 || e.ey > ON_SCREEN.y1) continue;
    destroyEnemy(b, e.linknum === 0 ? 255 : e.linknum, 1);
  }
  return g.enemyKilled - before;
}

/** The original's skip-level cheat: the level ends as completed 40 ticks later. */
export function skipLevel(): void {
  cheatSkipLevel();
}
