// OpenTyrian's reads past the ends of its item and pickup tables, reproduced the way its reference
// build lays out memory (D75).
//
// In galaga mode (ALE, SQUADRON) JE_searchFor doubles the value of every enemy it finds
// (tyrian2.c L4148-4160), and value is a JE_integer (Sint16), so it wraps: 15 becomes 30720 after
// eleven doublings, 375 becomes 30464, 250 becomes 32000. Touching such an enemy, JE_playerCollide
// (mainint.c L4487-4670) takes it for a pickup and reads weaponPort[value - 30000 or - 31000],
// options[value - 32000] and special[value - 32100] (a name for the text window, and the record the
// id it gives the player then selects), specialArcadeWeapon[value - 30001], optionSelect[series]
// and SAWeapon[mode][value - 30001], all past their ends. That is undefined behaviour in C; what
// OpenTyrian does is read whatever lies there. On the reference build (tools/opentyrian-bot/run.sh:
// Apple clang -O1, arm64 macOS, the build every bot fixture comes from):
// - The item tables are back to back, in this order: options, powerSys, shields, ships, special,
//   weaponPort, weapons (71,820 bytes; mutable game globals follow). itemMemory() rebuilds that
//   block from the item data (JE_loadItemDat's fields at the structs' offsets, padding zero), and
//   extendItemTables() appends to weaponPorts, specials and options every record a Uint8 id can
//   reach (up to 255), decoded from it, so the weapon, special and sidekick code reads what the C
//   reads.
// - SAWeapon, specialArcadeWeapon and optionSelect (varz.c L45-92) are followed by the rest of
//   OpenTyrian's read-only data; CONST_FROM_SAWEAPON is those 2,562 bytes as that build compiled
//   them (from SAWeapon to the end of the last OpenTyrian object's constants).
// Past both blocks the C reads its own mutable globals (weaponPort names for value - 30000 or
// - 31000 from 805) or code-dependent unwind tables (SAWeapon past ~1,250); this reads zeros there,
// "" for a name. The names only feed the text window, and SAWeapon is only read in a Super Arcade
// game, which never reaches a galaga level's wrapped values in practice.

import { latin1, type ItemDat, type Option, type Special, type WeaponPort } from "../data";
import { OPTION_NUM, PORT_NUM, POWER_NUM, SHIELD_NUM, SHIP_NUM, SPECIAL_NUM, WEAP_NUM } from "../data";

// Struct sizes (episodes.h) and where each table starts in the block.
const OPTION_SIZE = 88;
const POWER_SIZE = 38;
const SHIELD_SIZE = 38;
const SHIP_SIZE = 44;
const SPECIAL_SIZE = 38;
const PORT_SIZE = 82;
const WEAPON_SIZE = 80;
const OPTIONS_AT = 0;
const POWERSYS_AT = OPTIONS_AT + (OPTION_NUM + 1) * OPTION_SIZE;
const SHIELDS_AT = POWERSYS_AT + (POWER_NUM + 1) * POWER_SIZE;
const SHIPS_AT = SHIELDS_AT + (SHIELD_NUM + 1) * SHIELD_SIZE;
const SPECIAL_AT = SHIPS_AT + (SHIP_NUM + 1) * SHIP_SIZE;
const PORTS_AT = SPECIAL_AT + (SPECIAL_NUM + 1) * SPECIAL_SIZE;
const WEAPONS_AT = PORTS_AT + (PORT_NUM + 1) * PORT_SIZE;
/** Bytes from options[0] to the end of weapons[WEAP_NUM]. */
export const ITEM_MEMORY_SIZE = WEAPONS_AT + (WEAP_NUM + 1) * WEAPON_SIZE;

/**
 * The tables in item-data file order (JE_loadItemDat, episodes.c L101-206): record count, record size
 * in the file, where the structs start, struct size, whether it starts with a name, and the fields
 * after the name as [file offset, struct offset, bytes]. A name is a length byte and 30 chars in
 * the file, char[31] in the struct (name[min(len, 30)] = '\0'; name[30] is never read in, so 0).
 */
const LAYOUT: readonly [number, number, number, number, boolean, readonly (readonly [number, number, number])[]][] = [
  [WEAP_NUM + 1, 80, WEAPONS_AT, WEAPON_SIZE, false, [[0, 0, 80]]],
  [PORT_NUM + 1, 82, PORTS_AT, PORT_SIZE, true, [[31, 31, 51]]],
  [SPECIAL_NUM + 1, 37, SPECIAL_AT, SPECIAL_SIZE, true, [[31, 32, 6]]],
  [POWER_NUM + 1, 37, POWERSYS_AT, POWER_SIZE, true, [[31, 32, 6]]],
  [SHIP_NUM + 1, 41, SHIPS_AT, SHIP_SIZE, true, [[31, 32, 7], [38, 40, 2], [40, 42, 1]]],
  [OPTION_NUM + 1, 86, OPTIONS_AT, OPTION_SIZE, true, [[31, 31, 50], [81, 82, 2], [83, 84, 3]]],
  [SHIELD_NUM + 1, 37, SHIELDS_AT, SHIELD_SIZE, true, [[31, 31, 2], [33, 34, 4]]],
];

const memories = new WeakMap<ItemDat, Uint8Array>();

/** The item tables as the reference build holds them in memory: options[0] .. weapons[WEAP_NUM]. */
export function itemMemory(items: ItemDat): Uint8Array {
  let m = memories.get(items);
  if (m) return m;
  m = new Uint8Array(ITEM_MEMORY_SIZE);
  const raw = items.raw;
  let src = 14; // the 7 u16 counts
  for (const [count, fileSize, at, size, named, fields] of LAYOUT) {
    for (let i = 0; i < count; i++, src += fileSize) {
      const dst = at + i * size;
      if (named) {
        m.set(raw.subarray(src + 1, src + 31), dst);
        m[dst + Math.min(raw[src], 30)] = 0;
      }
      for (const [from, to, n] of fields) m.set(raw.subarray(src + from, src + from + n), dst + to);
      if (at === OPTIONS_AT) m[dst + 85] = m[dst + 85] !== 0 ? 1 : 0; // stop: fileReadBool
    }
  }
  memories.set(items, m);
  return m;
}

const u16At = (m: Uint8Array, at: number) => m[at] | (m[at + 1] << 8);
const u16sAt = (m: Uint8Array, at: number, n: number) => Array.from({ length: n }, (_, i) => u16At(m, at + 2 * i));
const s8At = (m: Uint8Array, at: number) => (m[at] << 24) >> 24;

/** The C string at `at` (as %s reads it: up to the first NUL), "" past the block. */
function cString(m: Uint8Array, at: number): string {
  if (at >= m.length) return "";
  let end = at;
  while (end < m.length && m[end] !== 0) end++;
  return latin1(m.subarray(at, end));
}

function portAt(m: Uint8Array, at: number): WeaponPort {
  return {
    name: cString(m, at),
    opNum: m[at + 31],
    op: [u16sAt(m, at + 32, 11), u16sAt(m, at + 54, 11)],
    cost: u16At(m, at + 76),
    itemGraphic: u16At(m, at + 78),
    powerUse: u16At(m, at + 80),
  };
}

function specialAt(m: Uint8Array, at: number): Special {
  return { name: cString(m, at), itemGraphic: u16At(m, at + 32), pwr: m[at + 34], sType: m[at + 35], wpn: u16At(m, at + 36) };
}

function optionAt(m: Uint8Array, at: number): Option {
  return {
    name: cString(m, at),
    pwr: m[at + 31],
    itemGraphic: u16At(m, at + 32),
    cost: u16At(m, at + 34),
    tr: m[at + 36],
    option: m[at + 37],
    opSpd: s8At(m, at + 38),
    ani: m[at + 39],
    gr: u16sAt(m, at + 40, 20),
    wPort: m[at + 80],
    wpNum: u16At(m, at + 82),
    ammo: m[at + 84],
    stop: m[at + 85] !== 0,
    iconGr: m[at + 86],
  };
}

/** weaponPort[i], special[i] and options[i] read from itemMemory(), for any i whose record fits in it. */
export const weaponPortAt = (items: ItemDat, i: number): WeaponPort => portAt(itemMemory(items), PORTS_AT + i * PORT_SIZE);
export const specialRecordAt = (items: ItemDat, i: number): Special => specialAt(itemMemory(items), SPECIAL_AT + i * SPECIAL_SIZE);
export const optionRecordAt = (items: ItemDat, i: number): Option => optionAt(itemMemory(items), OPTIONS_AT + i * OPTION_SIZE);

/**
 * Append to weaponPorts, specials and options the records past their ends that a Uint8 id
 * (weapon[].id, items.special, sidekick[]) can select, read from itemMemory() as the C reads them.
 */
export function extendItemTables(items: ItemDat): void {
  for (let i = items.weaponPorts.length; i < 256; i++) items.weaponPorts.push(weaponPortAt(items, i));
  for (let i = items.specials.length; i < 256; i++) items.specials.push(specialRecordAt(items, i));
  for (let i = items.options.length; i < 256; i++) items.options.push(optionRecordAt(items, i));
}

/** weaponPort[i].name, special[i].name or options[i].name as the C's %s reads it, for any i >= 0. */
export function itemName(items: ItemDat, table: "weaponPort" | "special" | "options", i: number): string {
  const [at, size] =
    table === "weaponPort" ? [PORTS_AT, PORT_SIZE] : table === "special" ? [SPECIAL_AT, SPECIAL_SIZE] : [OPTIONS_AT, OPTION_SIZE];
  return cString(itemMemory(items), at + i * size);
}

/**
 * The reference build's read-only data from SAWeapon (const JE_word[7][5]) on: specialArcadeWeapon
 * (JE_byte[42]) at 70, optionSelect (JE_byte[16][3][2]) at 112, then the rest of varz.c's and the
 * later objects' constants. Compiled from OpenTyrian's sources (GPL-2.0-or-later, as this repo).
 */
const CONST_FROM_SAWEAPON_BASE64 =
  "CQAfACAAIQAiABMACAAWACkAIgAbAAUAFAAqAB8ADwADABwAFgAMABcAIwAZAA4ABgACAAUAFQAEAAcAKAAmACUAKQAkABEREgAA" +
  "AAoAAAAAACwACgATAAAAAAAAAAAAAAAAAC0AAAAAAAAAAAAAAAAAAAAAAAEBEBAeHgICHR0dFAMDFRUMAAQEEhIQFwAAAAAAAAYG" +
  "HRAAFgcHExMTHAAAAAAAAAAAAAAAAAoKFRUVGwAAAAAAAAAAAAAAAA0NERENGgAAAAAAAA8PDxAPEAQAAQACAAMAFAAkADQARABU" +
  "AGQAdACEAJcAlwCXAJcANAA0AAEAAgAEAAEAAAABAQEBAQEBAQAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAvAG9Ab4BvwEAAMAB" +
  "wQEAAAAAAAAAAAAAwgHDAQAA+gEAADQCvQG+Ab8BwAHBAb0BvgG/AcABwQHCAcMBAAAAAAAAAAAAAAAAAAAAANwBygHQAeIBAADo" +
  "AdYBAAAAAAAAAAAAAO4B9AEAABACAAAuAsoBygHKAcoBygHKAcoBygHKAcoBygHKAQ0GGgIBAgWJAAAABAMCBYoAAAADBAaLAAAA" +
  "AAIFjgAAAAAABgIGjwAAAAAGBwUIBgcFcAcIZQAAAAAAAQcGkgAAAAAIBgcBeAAAAAMGCAV5AAAAAQIHCHcAAAADBAMGewAAAAYH" +
  "BQh8AAAAAQZ9AAAAAAAJBX4AAAAAAAEHfwAAAAAAAQiAAAAAAAAJB4EAAAAAAAkIggAAAAAABAIDBYMAAAADAQIIhAAAAAIEBYUA" +
  "AAAAAwQCCIYAAAABBAaHAAAAAAEDBokAAAAAAQQDBAeIAAAPEBESExQVFhcYBwgFGQ4EBgMJAhoBAgQFBQQHAQIADgQABAUABgUA" +
  "BwgABwkACgMFBQgJAQMABxARAgsMAwgKAAAACgAAAOkAnQDDAA8BUQAAAHcABQArAFEAdwCdAMMA6QAPAQAAQAAAAFIAAABsAAAA" +
  "fgAAAJAABwB4AAwAvgAMANEADACYAAwAqwAMAIUABwABAAwAFAAMACcADAA6AAwAbgADAEwABwBbAAMA4wADAOYAAwDpAAMA/AAD" +
  "APYAAwD5AAMACQEDAAwBAwAPAQMA7AADAO8AAwDyAAMABQEDABIBAwAVAQMAGAEDACsBAwAcAQMAHwEDACIBAwAlAQMApQAIALgA" +
  "CADLAAgA3gAIAKgACAC7AAgAzgAIAOEACgCpAAoAvAAKAM8AFADiAA4AqgAOAL0ADgDQAA4A9gAOAOMADgAJAQ4AAAAAAHYAOgAA" +
  "AAAAbAArAFMAiAAgAu0CUwCIAJoAzQMJAAkAlgEBBD4APgAgBOcDAQ9XBLQADA9KD9EE8Am0AAAAAAB2ADoAAAAAAGwAKwAvABQA" +
  "ygCpAy8AFADIAooCCQAJAJYBAQQ+AD4AIATnA9YEkgX/BEEEdw9WD1sP6w4ZABkAowQ1BRkAGQCdBQ0O/wHkAHIDqAT/AeQAUg5x" +
  "DKACoAKMAyUPDwEPAeAEmAw4AZwOcgRcBG0HOAixC40IYwBjAMUEQwhjAGMAdgUgDAMDLQO3BXIDAwMtA1kG6gtRA1ED2wTmBQYB" +
  "BgFWBUYNZg2nBakNHQ6RDvYJNg5ABQAAAAB2ADoAAAAAAGwAKwBTAIgAIALtAlMAiACaAM0DWABYAE4CQwEiACIAsQFyAQgGMAVv" +
  "DXsFGgpUBhYN2QwAAAAAdgA6AAAAAABsACsALwAUAMoAqQMvABQAyAKKAlgAWABOAkMBIgAiALEBcgHDBvUNzQbCBUYKSwi9CFEK" +
  "RwBHAOELTAZHAEcAhwxtDAwDjQHVB3IHDAONARMGswx+An4CogWgC9gB2AGMA4ULNgyyBV8GMQaQBkUH5gofCZEAkQDIBl4MkQBQ" +
  "CFkILQxnATkCTQt9CmcBOQL+BlwJzQHNAV4IjQdCAkICAgvzCDgBwgojCh0I5wiBCHYJrAkAAAAAxgBWAAAAAAC8AEMAmwDsAG4D" +
  "bASbAOwA/QC7BREAEQCZAgUGWABYACYG6wUuFY8GFwE9Fa8VJQecDRcBAAAAAMYAVgAAAAAAvABDAEUAIABNAYYFRQAgAFMEAAQR" +
  "ABEAmQIFBlgAWAAmBusFKAdHCFcHWQb6Fc0V0BUBFSMAIwD9Bo8HIwAjAFYIghM5A2cBTgUABzkDZwENFHoRFgQWBGkFXxWcAZwB" +
  "LgfJEccByRTIBpIGVwpfC0AQwAurAKsAIgduC6sAqwAiCLUQjgTaBGwITgWOBNoEMAmJEBcFFwUrB6kIjQGNAdMHhhKyElwI9hKo" +
  "E1cUwg3mE5kHAAAAAMYAVgAAAAAAvABDAJsA7ABuA2wEmwDsAP0AuwWeAJ4AqwMZAjQANAC0AmsC3AiMB8ESJQj8DS0JSBIWEgAA" +
  "AADGAFYAAAAAALwAQwBFACAATQGGBUUAIABTBAAEngCeAKsDGQI0ADQAtAJrArAJUBO2CXcIdA54C/oLgw6KAIoAfhArCYoAigCb" +
  "EXgRnwSIArsKWgqfBIgC6wj1EfQD9ANZCCwQ9AL0AmkF5A/fEGkISQkJCXwJIQotD4QMeQB5ALMJVhF5AHkAewvWEE8CiAObD7EO" +
  "TwKIA+cJvgzMAswCfgt8CpkDmQNPD2QMxwH4Dh4OAAsyDK4L2AxKDWYBZgE/CPMEZgFmAcMH7gPRBhsJXxEQFtEGGwnMCQcaJgIm" +
  "ArAOhBo9BT0F5RpFGq9KpxssChJLckzKHdc0LApmAWYBPwjzBGYBZgHDB+4DPwSmAmgKOBk/BKYCLRUvFCYCJgKwDoQaPQU9BeUa" +
  "RRogHsQhXh9DG+NNPU2TTXNK9gL2AtUcKCD2AvYCRCJtRpUQrAqjGB0dlRCsCvVHMkBtFG0U2hhhS5oLmgvrHmhBLwxoSWYcAhyp" +
  "K0wuzTswMQAAAACCHdAuAAAAAD4hMD1sFqUXniOjGGwWpReAJ6s87BfsF3YesSQVCxUL4CDTQm1D2yK7RFZHwkgnNaVHpCBmAWYB" +
  "PwjzBGYBZgHDB+4D0QYbCV8REBbRBhsJzAkHGhsHGwe0En8MagNqAyUPgg3EJc0f0EONIdE1KidvQi9CZgFmAT8I8wRmAWYBwwfu" +
  "Az8EpgJoCjgZPwSmAi0VLxQbBxsHtBJ/DGoDagMlD4INHyloRb0pCiT3NjwvoTF3N10GXQYxPOAmXQZdBnBA4T/bFjsOKC37K9sW" +
  "Ow4nJshByRPJE5MiSDvDD8MP2hjoOiw+QyPOJ6kmVSj3Kig5TzPpBekFdSn9PukF6QWSL649Aw26EUE6tzcDDboRLCqPM10PXQ/h" +
  "L1csLxIvEng57zIvDFw4UTYVLm4yqzDtM2o0AAD/AAD/AAD/AAAAAAAwAAAHAAAGAAAACQAAABAnAAAAAAAAmDoAAAAAAAAgTgAA" +
  "AAAAADB1AAAAAAAA";
const CONST_FROM_SAWEAPON = Uint8Array.from(atob(CONST_FROM_SAWEAPON_BASE64), (c) => c.charCodeAt(0));
const SPECIAL_ARCADE_WEAPON_AT = 70;
const OPTION_SELECT_AT = 112;

const constByte = (at: number) => (at < CONST_FROM_SAWEAPON.length ? CONST_FROM_SAWEAPON[at] : 0);

/** SAWeapon[mode][i] for any i >= 0 (mode 0..6). */
export function SAWeaponAt(mode: number, i: number): number {
  const at = (mode * 5 + i) * 2;
  return constByte(at) | (constByte(at + 1) << 8);
}

/** specialArcadeWeapon[i] for any i >= 0. */
export function specialArcadeWeaponAt(i: number): number {
  return constByte(SPECIAL_ARCADE_WEAPON_AT + i);
}

/** optionSelect[series][level][side] for any series >= 0. */
export function optionSelectAt(series: number, level: number, side: number): number {
  return constByte(OPTION_SELECT_AT + series * 6 + level * 2 + side);
}

/** The block's bytes (tests check them against the tables they start with). */
export const constFromSAWeapon = (): Uint8Array => CONST_FROM_SAWEAPON.slice();
