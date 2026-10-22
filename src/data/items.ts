// Item data: weapons, weapon ports, specials, generators, ships, sidekicks, shields, then the
// enemy table. Port of JE_loadItemDat and the item structs (OpenTyrian src/episodes.c/.h).
//
// Episodes 1-3 read it from tyrian.hdt at the offset stored in the file's first u32;
// episode 4 reads it from tyrian4.lvl at lvlPos[lvlNum - 1].
//
// Units are raw: pixels, and logic frames for anything timed. Fields that are per-frame
// quantities are marked "/frame". Index 0 of every table is the "None" entry.

import { type EnemyDat, ENEMY_NUM, readEnemyDat } from "./enemies";
import { readLevelPositions } from "./levels";
import { BinaryReader, type Bytes } from "./reader";

// Table sizes from src/lvlmast.h; each table holds NUM + 1 entries ([0..num]).
export const WEAP_NUM = 780;
export const PORT_NUM = 42;
export const POWER_NUM = 6;
export const SHIP_NUM = 13;
export const OPTION_NUM = 30;
export const SHIELD_NUM = 10;
export const SPECIAL_NUM = 46;

/** Item names are Pascal string[30]. */
const NAME_LEN = 30;

/** One shot pattern (JE_WeaponType). Arrays are per shot in the pattern, [1..8]. */
export interface Weapon {
  /** drain */
  drain: number;
  /** shotrepeat: frames before the bay can fire again. */
  shotRepeat: number;
  /** multi: shots spawned per trigger. */
  multi: number;
  /** weapani: extra animation frames for the shot sprite. */
  weapAni: number;
  /** max: shots in the pattern before it wraps (≤ 8). */
  max: number;
  /** tx, ty */
  tx: number;
  ty: number;
  /** aim: > 5 makes a guided shot, re-aiming every (aim - 5) frames. */
  aim: number;
  /** attack[8]: damage; 100..249 means chain reaction (attack - 100) with damage 1. */
  attack: number[];
  /** del[8]: shot lifetime in frames, with magic values 98-121 (see player_shot_create). */
  del: number[];
  /** sx[8], sy[8]: velocity, px/frame (sy is negated: positive moves up); values > 100 and sy 98 are special. */
  sx: number[];
  sy: number[];
  /** bx[8], by[8]: spawn offset from the ship, px. */
  bx: number[];
  by: number[];
  /** sg[8]: shot sprite index; 0 = no shot. */
  sg: number[];
  /** acceleration: vertical, px/frame² (applied negated, as shotYC). */
  acceleration: number;
  /** accelerationx: horizontal, px/frame². */
  accelerationX: number;
  /** circlesize: circular motion size; > 19 encodes x = n % 20, y = n / 20. */
  circleSize: number;
  /** sound: sound effect id; 0 = silent. */
  sound: number;
  /** trail */
  trail: number;
  /** shipblastfilter */
  shipBlastFilter: number;
}

/** A buyable front/rear weapon (JE_WeaponPortType). */
export interface WeaponPort {
  name: string;
  /** opnum: number of firing modes. */
  opNum: number;
  /** op[2][11]: weapon index per mode and power level (0..10). */
  op: [number[], number[]];
  cost: number;
  itemGraphic: number;
  /** poweruse: generator power used per shot. */
  powerUse: number;
}

/** Special weapon (JE_SpecialType). */
export interface Special {
  name: string;
  itemGraphic: number;
  /** pwr: cost or repeat interval depending on stype (see JE_specialComplete). */
  pwr: number;
  /** stype: special behaviour id. */
  sType: number;
  /** wpn: weapon or sidekick index used by the special. */
  wpn: number;
}

/** Generator (JE_PowerType, powerSys). */
export interface PowerSys {
  name: string;
  itemGraphic: number;
  power: number;
  speed: number;
  cost: number;
}

/** Player ship (JE_ShipType). */
export interface Ship {
  name: string;
  shipGraphic: number;
  itemGraphic: number;
  ani: number;
  /** spd */
  spd: number;
  /** dmg: starting armor. */
  dmg: number;
  cost: number;
  bigShipGraphic: number;
}

/** Sidekick (JE_OptionType). */
export interface Option {
  name: string;
  pwr: number;
  itemGraphic: number;
  cost: number;
  /** tr */
  tr: number;
  /** option */
  option: number;
  /** opspd */
  opSpd: number;
  ani: number;
  /** gr[20]: sprite per animation frame. */
  gr: number[];
  /** wport: weapon port the sidekick fires; 0 = none. */
  wPort: number;
  /** wpnum: weapon index it fires. */
  wpNum: number;
  ammo: number;
  stop: boolean;
  /** icongr */
  iconGr: number;
}

/** Shield (JE_ShieldType). */
export interface Shield {
  name: string;
  /** tpwr: recharge cost; the game charges tpwr * 20 power per shield point. */
  tpwr: number;
  /** mpwr: maximum shield. */
  mpwr: number;
  itemGraphic: number;
  cost: number;
}

/** Everything JE_loadItemDat reads, in file order. */
export interface ItemDat {
  /** The 7 u16 counts in the header: weapons, ports, powers, ships, options, shields, enemies. */
  counts: number[];
  weapons: Weapon[];
  weaponPorts: WeaponPort[];
  specials: Special[];
  powerSys: PowerSys[];
  ships: Ship[];
  options: Option[];
  shields: Shield[];
  enemies: EnemyDat[];
  /** Byte offset just past the last record. */
  end: number;
}

function readWeapon(r: BinaryReader): Weapon {
  return {
    drain: r.u16(),
    shotRepeat: r.u8(),
    multi: r.u8(),
    weapAni: r.u16(),
    max: r.u8(),
    tx: r.u8(),
    ty: r.u8(),
    aim: r.u8(),
    attack: r.u8Array(8),
    del: r.u8Array(8),
    sx: r.s8Array(8),
    sy: r.s8Array(8),
    bx: r.s8Array(8),
    by: r.s8Array(8),
    sg: r.u16Array(8),
    acceleration: r.s8(),
    accelerationX: r.s8(),
    circleSize: r.u8(),
    sound: r.u8(),
    trail: r.u8(),
    shipBlastFilter: r.u8(),
  };
}

function readWeaponPort(r: BinaryReader): WeaponPort {
  return {
    name: r.pascalString(NAME_LEN),
    opNum: r.u8(),
    op: [r.u16Array(11), r.u16Array(11)],
    cost: r.u16(),
    itemGraphic: r.u16(),
    powerUse: r.u16(),
  };
}

function readSpecial(r: BinaryReader): Special {
  return {
    name: r.pascalString(NAME_LEN),
    itemGraphic: r.u16(),
    pwr: r.u8(),
    sType: r.u8(),
    wpn: r.u16(),
  };
}

function readPowerSys(r: BinaryReader): PowerSys {
  return {
    name: r.pascalString(NAME_LEN),
    itemGraphic: r.u16(),
    power: r.u8(),
    speed: r.s8(),
    cost: r.u16(),
  };
}

function readShip(r: BinaryReader): Ship {
  return {
    name: r.pascalString(NAME_LEN),
    shipGraphic: r.u16(),
    itemGraphic: r.u16(),
    ani: r.u8(),
    spd: r.s8(),
    dmg: r.u8(),
    cost: r.u16(),
    bigShipGraphic: r.u8(),
  };
}

function readOption(r: BinaryReader): Option {
  return {
    name: r.pascalString(NAME_LEN),
    pwr: r.u8(),
    itemGraphic: r.u16(),
    cost: r.u16(),
    tr: r.u8(),
    option: r.u8(),
    opSpd: r.s8(),
    ani: r.u8(),
    gr: r.u16Array(20),
    wPort: r.u8(),
    wpNum: r.u16(),
    ammo: r.u8(),
    stop: r.bool(),
    iconGr: r.u8(),
  };
}

function readShield(r: BinaryReader): Shield {
  return {
    name: r.pascalString(NAME_LEN),
    tpwr: r.u8(),
    mpwr: r.u8(),
    itemGraphic: r.u16(),
    cost: r.u16(),
  };
}

function table<T>(count: number, read: () => T): T[] {
  return Array.from({ length: count }, read);
}

/**
 * Parse the item data block starting at `offset`. Like JE_loadItemDat, the table sizes are
 * the compile-time constants; the header counts must match them (the C code asserts this).
 * The special table has no header count.
 */
export function parseItemDat(data: Bytes, offset: number): ItemDat {
  const r = new BinaryReader(data, offset);
  const counts = r.u16Array(7);
  const expected = [WEAP_NUM, PORT_NUM, POWER_NUM, SHIP_NUM, OPTION_NUM, SHIELD_NUM, ENEMY_NUM];
  if (counts.some((c, i) => c !== expected[i])) {
    throw new Error(`item data counts ${counts.join(",")} != ${expected.join(",")}`);
  }
  return {
    counts,
    weapons: table(WEAP_NUM + 1, () => readWeapon(r)),
    weaponPorts: table(PORT_NUM + 1, () => readWeaponPort(r)),
    specials: table(SPECIAL_NUM + 1, () => readSpecial(r)),
    powerSys: table(POWER_NUM + 1, () => readPowerSys(r)),
    ships: table(SHIP_NUM + 1, () => readShip(r)),
    options: table(OPTION_NUM + 1, () => readOption(r)),
    shields: table(SHIELD_NUM + 1, () => readShield(r)),
    enemies: table(ENEMY_NUM + 1, () => readEnemyDat(r)),
    end: r.pos,
  };
}

/** Offset of the item data in tyrian.hdt: the file's first u32. */
export function hdtItemDatOffset(hdt: Bytes): number {
  return new BinaryReader(hdt).u32();
}

/**
 * JE_loadItemDat for an episode: episodes 1-3 use tyrian.hdt, episode 4 uses the item data
 * at the end of its level file (`lvl`, tyrian4.lvl), at lvlPos[lvlNum - 1].
 */
export function loadItemDat(episode: number, hdt: Bytes, lvl?: Bytes): ItemDat {
  if (episode <= 3) return parseItemDat(hdt, hdtItemDatOffset(hdt));
  if (!lvl) throw new Error(`episode ${episode} item data is in its level file`);
  const { lvlNum, lvlPos } = readLevelPositions(lvl);
  return parseItemDat(lvl, lvlPos[lvlNum - 1]!);
}
