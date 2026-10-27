// Destruct, Tyrian's hidden two-player artillery game: a close transliteration of OpenTyrian's
// src/destruct.c (the game itself, without its drawing, menus and timing, which live in
// src/destruct/app.ts and src/destruct/renderer.ts).
//
// It keeps the C's names, its globals (as fields of DestructGame), its float/unsigned arithmetic
// and its use of the shared Mersenne Twister (src/sim/mtrand.ts), so a seed plays out exactly as
// in OpenTyrian. tools/destruct-trace runs the real C on the same seed and
// tests/destruct/trace.test.ts compares the two tick by tick.
//
// The terrain is the C's: destructTempScreen, a 320x200 byte "screen" whose brown pixels
// (PIXEL_DIRT) are what shots and units collide with and explosions burn away. Drawing that the C
// does onto VGAScreen each tick (units, walls, shot pixels, crosshairs) is recorded in `draws`
// instead, for the renderer.

import { roundf } from "../sim/cfloat";
import { mt_rand, mt_rand_lt1 } from "../sim/mtrand";
import {
  S_EXPLOSION_22,
  S_EXPLOSION_9,
  S_NONE,
  S_SELECT,
  S_WEAPON_1,
  S_WEAPON_10,
  S_WEAPON_13,
  S_WEAPON_14,
  S_WEAPON_15,
  S_WEAPON_2,
  S_WEAPON_26,
  S_WEAPON_5,
  S_WEAPON_7,
  V_CLEARED_PLATFORM,
} from "../sim/sndmast";

// --- C float helpers ---------------------------------------------------------------------------

/** A C float: every float variable and float-only expression is rounded to 32 bits. */
const f = Math.fround;
const sinf = (x: number): number => f(Math.sin(f(x)));
const cosf = (x: number): number => f(Math.cos(f(x)));
/** roundf of a float expression (the argument is converted to float first, as in C). */
const roundff = (x: number): number => roundf(f(x));
const floorf = (x: number): number => Math.floor(f(x));
/** unsigned int arithmetic (mod 2^32). */
const u32 = (x: number): number => x >>> 0;
/**
 * A float converted to unsigned int. In range it truncates; a negative value is undefined
 * behaviour in C, where arm64 builds saturate to 0 (x86-64 ones wrap). This follows arm64.
 */
const f2u = (x: number): number => (x <= 0 ? 0 : Math.trunc(x));
/** A float converted to int. */
const f2i = (x: number): number => Math.trunc(x);
/** `mt_rand() % n` with n converted to unsigned long; n == 0 crashes the C, here it's 0. */
const mt_rand_mod = (n: number): number => {
  const r = mt_rand();
  return n === 0 ? 0 : n < 0 ? r : r % n;
};

const M_PI = Math.PI;
const M_PI_2 = Math.PI / 2;
const M_PI_4 = Math.PI / 4;

/*** Defines ***/
export const UNIT_HEIGHT = 12;
export const MAX_KEY_OPTIONS = 4;
export const SCREEN_W = 320;
export const SCREEN_H = 200;

/*** Enums ***/
export const enum de_state_t {
  STATE_INIT,
  STATE_RELOAD,
  STATE_CONTINUE,
}

export const PLAYER_LEFT = 0;
export const PLAYER_RIGHT = 1;
export const MAX_PLAYERS = 2;

export const MODE_5CARDWAR = 0;
export const MODE_TRADITIONAL = 1;
export const MODE_HELIASSAULT = 2;
export const MODE_HELIDEFENSE = 3;
export const MODE_OUTGUNNED = 4;
export const MODE_CUSTOM = 5;
export const MODE_FIRST = MODE_5CARDWAR;
export const MODE_LAST = MODE_CUSTOM;
export const MAX_MODES = 6;
export const MODE_NONE = -1;
/** helptext.h DESTRUCT_MODES: the modes named in the data (all but Custom). */
export const DESTRUCT_MODES = 5;

export const UNIT_TANK = 0;
export const UNIT_NUKE = 1;
export const UNIT_DIRT = 2;
export const UNIT_SATELLITE = 3;
export const UNIT_MAGNET = 4;
export const UNIT_LASER = 5;
export const UNIT_JUMPER = 6;
export const UNIT_HELI = 7;
export const MAX_UNITS = 8;

export const SHOT_TRACER = 0;
export const SHOT_SMALL = 1;
export const SHOT_LARGE = 2;
export const SHOT_MICRO = 3;
export const SHOT_SUPER = 4;
export const SHOT_DEMO = 5;
export const SHOT_SMALLNUKE = 6;
export const SHOT_LARGENUKE = 7;
export const SHOT_SMALLDIRT = 8;
export const SHOT_LARGEDIRT = 9;
export const SHOT_MAGNET = 10;
export const SHOT_MINILASER = 11;
export const SHOT_MEGALASER = 12;
export const SHOT_LASERTRACER = 13;
export const SHOT_MEGABLAST = 14;
export const SHOT_MINI = 15;
export const SHOT_BOMB = 16;
export const SHOT_FIRST = SHOT_TRACER;
export const SHOT_LAST = SHOT_BOMB;
export const MAX_SHOT_TYPES = 17;
export const SHOT_INVALID = -1;

export const EXPL_NONE = 0;
export const EXPL_MAGNET = 1;
export const EXPL_DIRT = 2;
export const EXPL_NORMAL = 3;

const TRAILS_NONE = 0;
const TRAILS_NORMAL = 1;
const TRAILS_FULL = 2;

export const PIXEL_BLACK = 0;
export const PIXEL_DIRT = 25;

export const MAP_NORMAL = 0x00;
export const MAP_WALLS = 0x01;
export const MAP_RINGS = 0x02;
export const MAP_HOLES = 0x04;
export const MAP_FUZZY = 0x08;
export const MAP_TALL = 0x10;

/* keys and moves should line up. */
export const KEY_LEFT = 0;
export const KEY_RIGHT = 1;
export const KEY_UP = 2;
export const KEY_DOWN = 3;
export const KEY_CHANGE = 4;
export const KEY_FIRE = 5;
export const KEY_CYUP = 6;
export const KEY_CYDN = 7;
export const MAX_KEY = 8;

export const MOVE_LEFT = 0;
export const MOVE_RIGHT = 1;
export const MOVE_UP = 2;
export const MOVE_DOWN = 3;
export const MOVE_CHANGE = 4;
export const MOVE_FIRE = 5;
export const MOVE_CYUP = 6;
export const MOVE_CYDN = 7;
export const MAX_MOVE = 8;

/*** Structs ***/
export interface destruct_config_s {
  max_shots: number;
  min_walls: number;
  max_walls: number;
  max_explosions: number;
  max_installations: number;
  allow_custom: boolean;
  alwaysalias: boolean;
  jumper_straight: [boolean, boolean];
  ai: [boolean, boolean];
}

export interface destruct_unit_s {
  /* Positioning/movement */
  unitX: number; /* yep, one's an int and the other is a real */
  unitY: number;
  unitYMov: number;
  isYInAir: boolean;
  /* What it is and what it fires */
  unitType: number;
  shotType: number;
  /* What it's pointed */
  angle: number;
  power: number;
  /* Misc */
  lastMove: number;
  ani_frame: number;
  health: number;
}

export interface destruct_shot_s {
  isAvailable: boolean;
  x: number;
  y: number;
  xmov: number;
  ymov: number;
  gravity: boolean;
  shottype: number;
  trailx: number[];
  traily: number[];
  trailc: number[];
}

export interface destruct_explo_s {
  isAvailable: boolean;
  x: number;
  y: number;
  explowidth: number;
  explomax: number;
  explofill: number;
  exploType: number;
}

export interface destruct_ai_s {
  c_Angle: number;
  c_Power: number;
  c_Fire: number;
  c_noDown: number;
}

export interface destruct_player_s {
  is_cpu: boolean;
  aiMemory: destruct_ai_s;
  unit: destruct_unit_s[];
  /** destruct_moves_s.actions */
  moves: boolean[];
  /** destruct_keys_s.Config[MAX_KEY][MAX_KEY_OPTIONS]: KeyboardEvent.code values, "" for none. */
  keys: string[][];
  team: number;
  unitsRemaining: number;
  unitSelected: number;
  shotDelay: number;
  score: number;
}

export interface destruct_wall_s {
  wallExist: boolean;
  wallX: number;
  wallY: number;
}

export interface destruct_world_s {
  /** baseMap[320], plus the one entry past its end that DE_generateWalls reaches (see there). */
  baseMap: number[];
  mapWalls: destruct_wall_s[];
  destructMode: number;
  mapFlags: number;
}

/*** Weapon configurations ***/
export const demolish: readonly boolean[] = [false, false, false, false, false, true, true, true, false, false, false, false, true, false, true, false, true];
const shotTrail = [TRAILS_NONE, TRAILS_NONE, TRAILS_NONE, TRAILS_NORMAL, TRAILS_NORMAL, TRAILS_NORMAL, TRAILS_FULL, TRAILS_FULL, TRAILS_NONE, TRAILS_NONE, TRAILS_NONE, TRAILS_NORMAL, TRAILS_FULL, TRAILS_NORMAL, TRAILS_FULL, TRAILS_NORMAL, TRAILS_NONE];
export const shotDelay = [10, 30, 80, 20, 60, 100, 140, 200, 20, 60, 5, 15, 50, 5, 80, 16, 0];
const shotSound = [S_SELECT, S_WEAPON_2, S_WEAPON_1, S_WEAPON_7, S_WEAPON_7, S_EXPLOSION_9, S_EXPLOSION_22, S_EXPLOSION_22, S_WEAPON_5, S_WEAPON_13, S_WEAPON_10, S_WEAPON_15, S_WEAPON_15, S_WEAPON_26, S_WEAPON_14, S_WEAPON_7, S_WEAPON_7];
export const exploSize = [4, 20, 30, 14, 22, 16, 40, 60, 10, 30, 0, 5, 10, 3, 15, 7, 0];
const shotBounce = [false, false, false, false, false, false, false, false, false, false, false, true, true, true, true, false, true];
const exploDensity = [2, 5, 10, 15, 20, 15, 25, 30, 40, 80, 0, 30, 30, 4, 30, 5, 0];
export const shotDirt = [EXPL_NORMAL, EXPL_NORMAL, EXPL_NORMAL, EXPL_NORMAL, EXPL_NORMAL, EXPL_NORMAL, EXPL_NORMAL, EXPL_NORMAL, EXPL_DIRT, EXPL_DIRT, EXPL_MAGNET, EXPL_NORMAL, EXPL_NORMAL, EXPL_NORMAL, EXPL_NORMAL, EXPL_NORMAL, EXPL_NONE];
export const shotColor = [16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 10, 10, 10, 10, 16, 0];

export const defaultWeapon = [SHOT_SMALL, SHOT_MICRO, SHOT_SMALLDIRT, SHOT_INVALID, SHOT_MAGNET, SHOT_MINILASER, SHOT_MICRO, SHOT_MINI];
const defaultCpuWeapon = [SHOT_SMALL, SHOT_MICRO, SHOT_DEMO, SHOT_INVALID, SHOT_MAGNET, SHOT_MINILASER, SHOT_MICRO, SHOT_MINI];
const defaultCpuWeaponB = [SHOT_DEMO, SHOT_SMALLNUKE, SHOT_DEMO, SHOT_INVALID, SHOT_MAGNET, SHOT_MEGALASER, SHOT_MICRO, SHOT_MINI];
export const systemAngle = [true, true, true, false, false, true, false, false];
export const baseDamage = [200, 120, 400, 300, 80, 150, 600, 40];
const systemAni = [false, false, false, true, false, false, false, true];

/** weaponSystems[unit][shot]: which shots each unit can cycle to. */
export const weaponSystems: readonly (readonly number[])[] = [
  [1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // normal
  [0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], // nuke
  [0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0], // dirt
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // worthless
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0], // magnet
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0], // laser
  [1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0], // jumper
  [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0], // helicopter
];

/* Music that destruct will play.  You can check out musmast.c to see what is what. */
export const goodsel = [1, 2, 6, 12, 13, 14, 17, 23, 24, 26, 28, 29, 32, 33];

/* Unit creation. [0] is amount of units */
export const basetypes: readonly (readonly number[])[] = [
  [5, UNIT_TANK, UNIT_TANK, UNIT_NUKE, UNIT_DIRT, UNIT_DIRT, UNIT_SATELLITE, UNIT_MAGNET, UNIT_LASER, UNIT_JUMPER, UNIT_HELI], /*Normal*/
  [1, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_TANK], /*Traditional*/
  [4, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI], /*Weak   Heli attack fleet*/
  [8, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_NUKE, UNIT_NUKE, UNIT_NUKE, UNIT_DIRT, UNIT_MAGNET, UNIT_LASER, UNIT_JUMPER], /*Strong Heli defense fleet*/
  [8, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI, UNIT_HELI], /*Strong Heli attack fleet*/
  [4, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_TANK, UNIT_NUKE, UNIT_NUKE, UNIT_DIRT, UNIT_MAGNET, UNIT_JUMPER, UNIT_JUMPER], /*Weak   Heli defense fleet*/
  [8, UNIT_TANK, UNIT_NUKE, UNIT_DIRT, UNIT_SATELLITE, UNIT_MAGNET, UNIT_LASER, UNIT_JUMPER, UNIT_HELI, UNIT_TANK, UNIT_NUKE], /*Overpowering fleet*/
  [4, UNIT_TANK, UNIT_TANK, UNIT_NUKE, UNIT_DIRT, UNIT_TANK, UNIT_LASER, UNIT_JUMPER, UNIT_HELI, UNIT_NUKE, UNIT_JUMPER], /*Weak fleet*/
  [5, UNIT_TANK, UNIT_TANK, UNIT_NUKE, UNIT_DIRT, UNIT_DIRT, UNIT_SATELLITE, UNIT_MAGNET, UNIT_LASER, UNIT_JUMPER, UNIT_HELI], /*Left custom*/
  [5, UNIT_TANK, UNIT_TANK, UNIT_NUKE, UNIT_DIRT, UNIT_DIRT, UNIT_SATELLITE, UNIT_MAGNET, UNIT_LASER, UNIT_JUMPER, UNIT_HELI], /*Right custom*/
];
export const baseLookup = [
  [0, 1, 3, 4, 6, 8],
  [0, 1, 2, 5, 7, 9],
];

/** First sprite (1-based, in newsh~.shp) of each unit type, per player. */
export const GraphicBase = [
  [1, 6, 11, 58, 63, 68, 96, 153],
  [20, 25, 30, 77, 82, 87, 115, 172],
];
/** The wall's sprite and the first of the HUD's weapon icons (191 + shotType). */
export const WALL_SPRITE = 42;
export const WEAPON_ICON_BASE = 191;

const ModeScore = [
  [1, 0, 0, 5, 0, 1],
  [1, 0, 5, 0, 1, 1],
];

/**
 * defaultKeyConfig, as KeyboardEvent.code values (SDL scancodes in the C). Insert and the keypad
 * are kept for keyboards that have them.
 */
export const defaultKeyConfig: readonly (readonly string[])[][] = [
  [["KeyC"], ["KeyV"], ["KeyA"], ["KeyZ"], ["AltLeft"], ["KeyX", "ShiftLeft"], ["ControlLeft"], ["Space"]],
  [
    ["ArrowLeft", "Numpad4"],
    ["ArrowRight", "Numpad6"],
    ["ArrowUp", "Numpad8"],
    ["ArrowDown", "Numpad2"],
    ["Backslash", "Numpad5"],
    ["Insert", "Enter", "Numpad0", "NumpadEnter"],
    ["PageUp", "Numpad9"],
    ["PageDown", "Numpad3"],
  ],
];

/** keysactive: which keys are held. The game clears some after reading them (one press, one action). */
export interface KeysActive {
  isDown(code: string): boolean;
  /** keysactive[key] = false */
  release(code: string): void;
}

/** What the C draws onto VGAScreen during a tick, for the renderer (it never touches the terrain). */
export interface DestructDraws {
  /** DE_GravityDrawUnit: blit_sprite2(x, y, destructSpriteSheet, sprite). */
  units: { player: number; index: number; sprite: number; x: number; y: number }[];
  /** DE_RunTickDrawWalls: sprite 42 at each wall. */
  walls: { x: number; y: number }[];
  /** JE_pixCool: a shot or trail pixel and its four neighbours (colour c - 2). */
  pixels: { x: number; y: number; c: number; trail: boolean; shot: number }[];
  /** DE_RunTickDrawCrosshairs, before clipping against the HUD. */
  crosshairs: { x: number; y: number }[];
}

const newUnit = (): destruct_unit_s => ({
  unitX: 0,
  unitY: 0,
  unitYMov: 0,
  isYInAir: false,
  unitType: UNIT_TANK,
  shotType: SHOT_TRACER,
  angle: 0,
  power: 0,
  lastMove: 0,
  ani_frame: 0,
  health: 0,
});

/** Half-open bounds check of a linear screen offset (C writes past the end are dropped). */
const inScreen = (i: number): boolean => i >= 0 && i < SCREEN_W * SCREEN_H;

export class DestructGame {
  readonly config: destruct_config_s = {
    max_shots: 40,
    min_walls: 20,
    max_walls: 20,
    max_explosions: 40,
    max_installations: 10,
    allow_custom: false,
    alwaysalias: false,
    jumper_straight: [true, false],
    ai: [true, false],
  };
  readonly destruct_player: destruct_player_s[];
  readonly world: destruct_world_s;
  readonly shotRec: destruct_shot_s[];
  readonly exploRec: destruct_explo_s[];
  /** destructTempScreen: the terrain and the explosions burning in it, 320x200 palette indices. */
  readonly tempScreen = new Uint8Array(SCREEN_W * SCREEN_H);
  /** soundQueue[8] */
  readonly soundQueue: number[] = new Array(8).fill(S_NONE);
  /** The song play_song was last asked for (0-based), or -1. */
  song = -1;
  destructFirstTime = true;
  /** DE_RunTick's static endDelay. */
  endDelay = 0;
  /** JE_eSound's static exploSoundChannel. */
  private exploSoundChannel = 0;
  /** This tick's VGAScreen drawing. */
  readonly draws: DestructDraws = { units: [], walls: [], pixels: [], crosshairs: [] };
  /** Set when DE_RunTick sees P or F1: the caller shows JE_pauseScreen / JE_helpScreen. */
  pauseRequested = false;
  helpRequested = false;

  /** JE_destructGame's one-time setup (the mallocs; malloc'd units start zeroed here). */
  constructor() {
    const c = this.config;
    //Malloc enough structures to cover all of this session's possible needs.
    for (let i = 0; i < 10; i++) c.max_installations = Math.max(c.max_installations, basetypes[i][0]);
    this.shotRec = Array.from({ length: c.max_shots }, () => ({
      isAvailable: true,
      x: 0,
      y: 0,
      xmov: 0,
      ymov: 0,
      gravity: false,
      shottype: 0,
      trailx: [0, 0, 0, 0],
      traily: [0, 0, 0, 0],
      trailc: [0, 0, 0, 0],
    }));
    this.exploRec = Array.from({ length: c.max_explosions }, () => ({
      isAvailable: true,
      x: 0,
      y: 0,
      explowidth: 0,
      explomax: 0,
      explofill: 0,
      exploType: EXPL_NONE,
    }));
    this.world = {
      baseMap: new Array(321).fill(0),
      mapWalls: Array.from({ length: c.max_walls }, () => ({ wallExist: false, wallX: 0, wallY: 0 })),
      destructMode: MODE_5CARDWAR,
      mapFlags: MAP_NORMAL,
    };
    this.destruct_player = [0, 1].map((team) => ({
      is_cpu: false,
      aiMemory: { c_Angle: 0, c_Power: 0, c_Fire: 0, c_noDown: 0 },
      unit: Array.from({ length: c.max_installations }, newUnit),
      moves: new Array(MAX_MOVE).fill(false),
      keys: [],
      team,
      unitsRemaining: 0,
      unitSelected: 0,
      shotDelay: 0,
      score: 0,
    }));
    this.DE_ResetPlayers();
  }

  /** The start of JE_destructMain: players reset, the computer playing where config.ai says. */
  startSession(): void {
    this.DE_ResetPlayers();
    this.destruct_player[PLAYER_LEFT].is_cpu = this.config.ai[PLAYER_LEFT];
    this.destruct_player[PLAYER_RIGHT].is_cpu = this.config.ai[PLAYER_RIGHT];
  }

  /**
   * JE_destructMain's round setup: destructFirstTime, JE_loadPic(VGAScreen, 11) (its pixels, or a
   * black screen), DE_ResetUnits, DE_ResetLevel.
   */
  startRound(mode: number, picture?: Uint8Array): void {
    this.world.destructMode = mode;
    this.destructFirstTime = true;
    if (picture) this.tempScreen.set(picture.subarray(0, SCREEN_W * SCREEN_H));
    else this.tempScreen.fill(0);
    this.DE_ResetUnits();
    this.DE_ResetLevel();
  }

  // --- level generating functions ---

  JE_generateTerrain(): void {
    /* The unique modifiers:
        Altered generation (really tall)
        Fuzzy hills
        Rings of dirt

       The non-unique ones;:
        Rings of not dirt (holes)
        Walls
    */
    const world = this.world;
    world.mapFlags = MAP_NORMAL;

    if (mt_rand() % 2 === 0) world.mapFlags |= MAP_WALLS;
    if (mt_rand() % 4 === 0) world.mapFlags |= MAP_HOLES;
    switch (mt_rand() % 4) {
      case 0:
        world.mapFlags |= MAP_FUZZY;
        break;
      case 1:
        world.mapFlags |= MAP_TALL;
        break;
      case 2:
        world.mapFlags |= MAP_RINGS;
        break;
    }

    this.song = goodsel[mt_rand() % 14] - 1; // play_song

    this.DE_generateBaseTerrain(world.mapFlags, world.baseMap);
    this.DE_generateUnits(world.baseMap);
    this.DE_generateWalls(world);
    this.DE_drawBaseTerrain(world.baseMap);

    if (world.mapFlags & MAP_RINGS) this.DE_generateRings(this.tempScreen, PIXEL_DIRT);
    if (world.mapFlags & MAP_HOLES) this.DE_generateRings(this.tempScreen, PIXEL_BLACK);

    this.JE_aliasDirt(this.tempScreen);
    // (The C draws all this on VGAScreen and copies it to destructTempScreen; here it's drawn there.)
  }

  DE_generateBaseTerrain(mapFlags: number, baseWorld: number[]): void {
    /* The ranges here are between .01 and roughly 0.07283...*/
    let sinewave = f((mt_rand_lt1() * M_PI) / 50 + f(0.01));
    let sinewave2 = f((mt_rand_lt1() * M_PI) / 50 + f(0.01));
    const cosinewave = f((mt_rand_lt1() * M_PI) / 50 + f(0.01));
    const cosinewave2 = f((mt_rand_lt1() * M_PI) / 50 + f(0.01));
    let HeightMul = 20;

    /* This block just exists to mix things up. */
    if (mapFlags & MAP_FUZZY) {
      sinewave = f(M_PI - f(mt_rand_lt1() * f(0.3)));
      sinewave2 = f(M_PI - f(mt_rand_lt1() * f(0.3)));
    }
    if (mapFlags & MAP_TALL) HeightMul = 100;

    /* Now compute a height for each of our lines. */
    for (let i = 1; i <= 318; i++) {
      const sum = f(
        f(f(f(sinf(f(sinewave * i)) * HeightMul) + f(sinf(f(sinewave2 * i)) * 15)) + f(cosf(f(cosinewave * i)) * 10)) +
          f(sinf(f(cosinewave2 * i)) * 15),
      );
      let newheight = f2u(f(roundf(sum) + 130));

      /* Bind it; we have mins and maxs */
      if (newheight < 40) newheight = 40;
      else if (newheight > 195) newheight = 195;
      baseWorld[i] = newheight;
    }
  }

  DE_drawBaseTerrain(baseWorld: number[]): void {
    // JE_rectangle(VGAScreen, i, baseWorld[i], i, 199, PIXEL_DIRT): a column down to the bottom.
    for (let i = 1; i <= 318; i++) {
      for (let y = baseWorld[i]; y <= 199; y++) this.tempScreen[y * SCREEN_W + i] = PIXEL_DIRT;
    }
  }

  DE_generateUnits(baseWorld: number[]): void {
    const mode = this.world.destructMode;
    for (let i = 0; i < MAX_PLAYERS; i++) {
      const player = this.destruct_player[i];
      const types = basetypes[baseLookup[i][mode]];
      let numSatellites = 0;
      player.unitsRemaining = 0;

      for (let j = 0; j < types[0]; j++) {
        const unit = player.unit[j];
        /* Not everything is the same between players */
        if (i === PLAYER_LEFT) unit.unitX = (mt_rand() % 120) + 10;
        else unit.unitX = 320 - ((mt_rand() % 120) + 22);

        unit.unitY = this.JE_placementPosition(unit.unitX - 1, 14, baseWorld);
        unit.unitType = types[(mt_rand() % 10) + 1];

        /* Sats are special cases since they are useless.  They don't count
         * as active units and we can't have a team of all sats */
        if (unit.unitType === UNIT_SATELLITE) {
          if (numSatellites === types[0]) {
            unit.unitType = UNIT_TANK;
            player.unitsRemaining++;
          } else {
            /* Place the satellite. It can be generated in hills and there is a clearing underneath it. */
            unit.unitY = 30 + (mt_rand() % 40);
            numSatellites++;
          }
        } else {
          player.unitsRemaining++;
        }

        /* Now just fill in the rest of the unit's values. */
        unit.lastMove = 0;
        unit.unitYMov = 0;
        unit.isYInAir = false;
        unit.angle = 0;
        unit.power = unit.unitType === UNIT_LASER ? 6 : 3;
        unit.shotType = defaultWeapon[unit.unitType];
        unit.health = baseDamage[unit.unitType];
        unit.ani_frame = 0;
      }
    }
  }

  DE_generateWalls(gameWorld: destruct_world_s): void {
    const config = this.config;
    if ((this.world.mapFlags & MAP_WALLS) === 0) {
      /* Just clear them out */
      for (let i = 0; i < config.max_walls; i++) gameWorld.mapWalls[i].wallExist = false;
      return;
    }

    // rand() % (max_walls - min_walls + 1) + min_walls: the C's libc rand(), not mt_rand. With the
    // default config (20 and 20) that is always 20, so libc's generator never matters.
    let remainWalls = config.min_walls;

    do {
      /* Create a wall.  Decide how tall the wall will be */
      let wallHeight = (mt_rand() % 5) + 1;
      if (wallHeight > remainWalls) wallHeight = remainWalls;

      /* Now find a good place to put the wall. */
      let tries = 0;
      let isGood: boolean;
      let wallX: number;
      do {
        isGood = true;
        wallX = (mt_rand() % 300) + 10;

        /* Is this X already occupied?  Check every unit (including ones left from earlier rounds),
         * but only try plotting an unobstructed X five times. */
        outer: for (let i = 0; i < MAX_PLAYERS; i++) {
          for (let j = 0; j < config.max_installations; j++) {
            const ux = this.destruct_player[i].unit[j].unitX;
            if (wallX > u32(ux - 12) && wallX < u32(ux + 13)) {
              isGood = false;
              break outer; /* I do feel that outer breaking is a legitimate goto use. */
            }
          }
        }
        tries++;
      } while (isGood === false && tries < 5);

      /* We now have a valid X.  Create the wall. */
      for (let i = 1; i <= wallHeight; i++) {
        const wall = gameWorld.mapWalls[remainWalls - i];
        wall.wallExist = true;
        wall.wallX = wallX;
        // JE_placementPosition(wallX, 12, ...) reaches baseMap[320] for wallX 309, one past the end.
        wall.wallY = u32(this.JE_placementPosition(wallX, 12, gameWorld.baseMap) - 14 * i);
      }

      remainWalls -= wallHeight;
    } while (remainWalls !== 0);
  }

  DE_generateRings(screen: Uint8Array, pixel: number): void {
    const rings = (mt_rand() % 6) + 1;
    for (let i = 1; i <= rings; i++) {
      const tempPosX1 = mt_rand() % 320;
      const tempPosY1 = (mt_rand() % 160) + 20;
      const tempSize = (mt_rand() % 40) + 10; /*Size*/

      for (let j = 1; j <= tempSize * tempSize * 2; j++) {
        const tempRadian = f(mt_rand_lt1() * (2 * M_PI));
        const tempPosY2 = f2i(f(tempPosY1 + roundff(f(cosf(tempRadian) * f(f(mt_rand_lt1() * f(0.1)) + f(0.9))) * tempSize)));
        const tempPosX2 = f2i(f(tempPosX1 + roundff(f(sinf(tempRadian) * f(f(mt_rand_lt1() * f(0.1)) + f(0.9))) * tempSize)));
        if (tempPosY2 > 12 && tempPosY2 < 200 && tempPosX2 > 0 && tempPosX2 < 319) {
          screen[tempPosX2 + tempPosY2 * SCREEN_W] = pixel;
        }
      }
    }
  }

  JE_aliasDirt(screen: Uint8Array): void {
    /* Goes through the whole screen looking for brown pixels which just happen to be next to
     * non-brown pixels.  It's an aliaser, just like it says. */
    for (let y = 12; y < SCREEN_H; y++) {
      for (let x = 0; x < SCREEN_W; x++) {
        const s = y * SCREEN_W + x;
        if (screen[s] === PIXEL_BLACK) screen[s] = aliasDirtPixel(screen, x, y, s);
      }
    }
  }

  JE_placementPosition(passed_x: number, width: number, world: number[]): number {
    /* This is the function responsible for carving out chunks of land.  Areas can be carved out
     * for units that are aerial or in mountains.  This can result in huge caverns. */
    let new_y = 0;
    for (let i = passed_x; i <= passed_x + width - 1; i++) {
      if (new_y < world[i]) new_y = world[i];
    }
    for (let i = passed_x; i <= passed_x + width - 1; i++) world[i] = new_y;
    return new_y;
  }

  JE_stabilityCheck(x: number, y: number): boolean {
    let numDirtPixels = 0;
    let s = x + y * SCREEN_W - 1;

    /* Check the 12 pixels on the bottom border of our object */
    for (let i = 0; i < 12; i++) {
      if (this.tempScreen[s] === PIXEL_DIRT) numDirtPixels++;
      s++;
    }

    /* If there are fewer than 10 brown pixels we don't consider it a solid base */
    return numDirtPixels < 10;
  }

  JE_tempScreenChecking(): void {
    /*and copy to vgascreen*/
    const temps = this.tempScreen;
    for (let i = 12 * SCREEN_W; i < SCREEN_W * SCREEN_H; i++) {
      // This block is what fades out explosions. The palette from 241 to 255 fades from a very
      // dark red to a very bright yellow.
      if (temps[i] >= 241) {
        if (temps[i] === 241) temps[i] = PIXEL_BLACK;
        else temps[i]--;
      }
      // This block is for aliasing dirt.
      if (this.config.alwaysalias === true && temps[i] === PIXEL_BLACK) {
        temps[i] = aliasDirtPixel(temps, i % SCREEN_W, Math.floor(i / SCREEN_W), i);
      }
    }
  }

  JE_makeExplosion(tempPosX: number, tempPosY: number, shottype: number): void {
    const exploRec = this.exploRec;
    /* First find an open explosion. If we can't find one, return.*/
    let i: number;
    for (i = 0; i < this.config.max_explosions; i++) if (exploRec[i].isAvailable === true) break;
    if (i === this.config.max_explosions) return; /* No empty slots */

    const e = exploRec[i];
    e.isAvailable = false;
    e.x = tempPosX;
    e.y = tempPosY;
    e.explowidth = 2;

    if (shottype !== SHOT_INVALID) {
      const tempExploSize = exploSize[shottype];
      if (tempExploSize < 5) this.JE_eSound(3);
      else if (tempExploSize < 15) this.JE_eSound(4);
      else if (tempExploSize < 20) this.JE_eSound(12);
      else if (tempExploSize < 40) this.JE_eSound(11);
      else {
        this.JE_eSound(12);
        this.JE_eSound(11);
      }

      e.explomax = tempExploSize;
      e.explofill = exploDensity[shottype];
      e.exploType = shotDirt[shottype];
    } else {
      this.JE_eSound(4);
      e.explomax = (mt_rand() % 40) + 10;
      e.explofill = (mt_rand() % 60) + 20;
      e.exploType = EXPL_NORMAL;
    }
  }

  JE_eSound(sound: number): void {
    if (++this.exploSoundChannel > 5) this.exploSoundChannel = 1;
    this.soundQueue[this.exploSoundChannel] = sound;
  }

  JE_superPixel(tempPosX: number, tempPosY: number): void {
    const maxX = SCREEN_W;
    const maxY = SCREEN_H;
    const rowLen = SCREEN_W;
    const t = this.tempScreen;
    let s = rowLen * (tempPosY - 2) + (tempPosX - 2);

    for (let y = 0; y < 5; y++, s += rowLen - 5) {
      if (tempPosY + y - 2 < 0 /* would be out of bounds */ || tempPosY + y - 2 >= maxY) continue;

      for (let x = 0; x < 5; x++, s++) {
        if (tempPosX + x - 2 < 0 || tempPosX + x - 2 >= maxX) continue;
        const pattern = starPattern[y][x];
        if (pattern === 0) continue; /* this is just to speed it up */

        /* at this point *s is our pixel.  Our constant arrays tell us what to do with it. */
        if (t[s] < pattern) t[s] = pattern;
        else if (t[s] + starIntensity[y][x] > 255) t[s] = 255;
        else t[s] += starIntensity[y][x];
      }
    }
  }

  // --- DE_ResetX: the reset functions clear the state of whatever they are assigned to ---

  DE_ResetUnits(): void {
    for (let p = 0; p < MAX_PLAYERS; ++p) for (let u = 0; u < this.config.max_installations; ++u) this.destruct_player[p].unit[u].health = 0;
  }

  DE_ResetPlayers(): void {
    for (let i = 0; i < MAX_PLAYERS; ++i) {
      const p = this.destruct_player[i];
      p.is_cpu = false;
      p.unitSelected = 0;
      p.shotDelay = 0;
      p.score = 0;
      p.aiMemory.c_Angle = 0;
      p.aiMemory.c_Power = 0;
      p.aiMemory.c_Fire = 0;
      p.aiMemory.c_noDown = 0;
      p.keys = defaultKeyConfig[i].map((codes) => Array.from({ length: MAX_KEY_OPTIONS }, (_, k) => codes[k] ?? ""));
    }
  }

  DE_ResetWeapons(): void {
    for (let i = 0; i < this.config.max_shots; i++) this.shotRec[i].isAvailable = true;
    for (let i = 0; i < this.config.max_explosions; i++) this.exploRec[i].isAvailable = true;
  }

  DE_ResetLevel(): void {
    /* Okay, let's prep the arena */
    this.DE_ResetWeapons();
    this.JE_generateTerrain();
    this.DE_ResetAI();
  }

  DE_ResetAI(): void {
    for (let i = PLAYER_LEFT; i < MAX_PLAYERS; i++) {
      if (this.destruct_player[i].is_cpu === false) continue;
      for (const ptr of this.destruct_player[i].unit) {
        if (DE_isValidUnit(ptr) === false) continue;

        if (systemAngle[ptr.unitType] || ptr.unitType === UNIT_HELI) ptr.angle = f(M_PI_4);
        else ptr.angle = 0;

        ptr.power = ptr.unitType === UNIT_LASER ? 6 : 4;

        if (this.world.mapFlags & MAP_WALLS) ptr.shotType = defaultCpuWeaponB[ptr.unitType];
        else ptr.shotType = defaultCpuWeapon[ptr.unitType];
      }
    }
  }

  DE_ResetActions(): void {
    for (const p of this.destruct_player) p.moves.fill(false);
  }

  /**
   * DE_RunTick: one tick of physics, explosions, shots, the computer players and input. Returns
   * STATE_CONTINUE while the round runs, STATE_RELOAD for a new map and STATE_INIT to go back to
   * the mode select. The C's timing, palette fade and screen copies are the caller's; P and F1
   * set pauseRequested and helpRequested, for the caller to show those screens.
   */
  DE_RunTick(keys: KeysActive): de_state_t {
    this.soundQueue.fill(S_NONE);
    this.draws.units.length = 0;
    this.draws.walls.length = 0;
    this.draws.pixels.length = 0;
    this.draws.crosshairs.length = 0;
    this.JE_tempScreenChecking();

    this.DE_ResetActions();
    this.DE_RunTickCycleDeadUnits();

    this.DE_RunTickGravity();
    this.DE_RunTickAnimate();
    this.DE_RunTickDrawWalls();
    this.DE_RunTickExplosions();
    this.DE_RunTickShots();
    this.DE_RunTickAI();
    this.DE_RunTickDrawCrosshairs();

    if (this.destructFirstTime) {
      // fade_palette(colors, 25, 0, 255)
      this.destructFirstTime = false;
      this.endDelay = 0;
    }

    this.DE_RunTickGetInput(keys);
    this.DE_ProcessInput();

    if (this.endDelay > 0) {
      if (--this.endDelay === 0) return de_state_t.STATE_RELOAD;
    } else if (this.DE_RunTickCheckEndgame() === true) {
      this.endDelay = 80;
    }

    // DE_RunTickPlaySounds and delayUntilElapsed are the caller's.

    const once = (code: string): boolean => {
      if (!keys.isDown(code)) return false;
      keys.release(code);
      return true;
    };
    if (once("F10")) this.destruct_player[PLAYER_LEFT].is_cpu = !this.destruct_player[PLAYER_LEFT].is_cpu;
    if (once("F11")) this.destruct_player[PLAYER_RIGHT].is_cpu = !this.destruct_player[PLAYER_RIGHT].is_cpu;
    if (once("KeyP")) this.pauseRequested = true;
    if (once("F1")) this.helpRequested = true;
    if (once("Escape")) return de_state_t.STATE_INIT; /* STATE_INIT drops us to the mode select */
    if (once("Backspace")) return de_state_t.STATE_RELOAD; /* STATE_RELOAD creates a new map */

    return de_state_t.STATE_CONTINUE;
  }

  /* DE_RunTickX: handles something that we do once per tick, such as track ammo and move explosions. */

  DE_RunTickCycleDeadUnits(): void {
    /* This code automatically switches the active unit if it is destroyed
     * and skips over the useless satellite */
    for (let i = 0; i < MAX_PLAYERS; i++) {
      const player = this.destruct_player[i];
      if (player.unitsRemaining === 0) continue;

      let unit = player.unit[player.unitSelected];
      while (DE_isValidUnit(unit) === false || unit.shotType === SHOT_INVALID) {
        player.unitSelected++;
        if (player.unitSelected >= this.config.max_installations) player.unitSelected = 0;
        unit = player.unit[player.unitSelected];
      }
    }
  }

  DE_RunTickGravity(): void {
    for (let i = 0; i < MAX_PLAYERS; i++) {
      const units = this.destruct_player[i].unit;
      for (let j = 0; j < this.config.max_installations; j++) {
        const unit = units[j];
        if (DE_isValidUnit(unit) === false) continue; /* invalid unit */

        switch (unit.unitType) {
          case UNIT_SATELLITE: /* satellites don't fall down */
            break;
          case UNIT_HELI:
          case UNIT_JUMPER:
            if (unit.isYInAir === true) {
              /* unit is falling down, at least in theory */
              this.DE_GravityFlyUnit(unit);
            } else {
              /* else treat as a normal unit */
              this.DE_GravityLowerUnit(unit);
            }
            break;
          default:
            this.DE_GravityLowerUnit(unit);
        }

        /* Draw the unit. */
        this.DE_GravityDrawUnit(i, unit, j);
      }
    }
  }

  DE_GravityDrawUnit(team: number, unit: destruct_unit_s, index: number): void {
    let anim_index = GraphicBase[team][unit.unitType] + unit.ani_frame;
    if (unit.unitType === UNIT_HELI) {
      /* Adjust animation index if we are traveling right or left. */
      if (unit.lastMove < -2) anim_index += 5;
      else if (unit.lastMove > 2) anim_index += 10;
    } else {
      /* This handles our cannons and the like */
      anim_index += floorf(f(unit.angle * f(9.99)) / M_PI);
    }

    this.draws.units.push({ player: team, index, sprite: anim_index, x: unit.unitX, y: roundff(unit.unitY) - 13 });
  }

  DE_GravityLowerUnit(unit: destruct_unit_s): void {
    /* units fall at a constant speed.  The chopper is given a slight downward acceleration
     * (simulating a 'rocky' takeoff), and it is lowered like a regular unit, but not as quickly. */
    if (unit.unitY < 199) {
      /* checking takes time, don't check if it's at the bottom */
      if (this.JE_stabilityCheck(unit.unitX, roundff(unit.unitY))) {
        switch (unit.unitType) {
          case UNIT_HELI:
            unit.unitYMov = f(1.5);
            unit.unitY = f(unit.unitY + f(0.2));
            break;
          default:
            unit.unitY = f(unit.unitY + 1);
        }

        if (unit.unitY > 199) unit.unitY = 199; /* could be possible */
      }
    }
  }

  DE_GravityFlyUnit(unit: destruct_unit_s): void {
    if (f(unit.unitY + unit.unitYMov) > 199) {
      /* would hit bottom of screen */
      unit.unitY = 199;
      unit.unitYMov = 0;
      unit.isYInAir = false;
      return;
    }

    /* move the unit and alter acceleration */
    unit.unitY = f(unit.unitY + unit.unitYMov);
    if (unit.unitY < 24) {
      /* This stops units from going above the screen */
      unit.unitYMov = 0;
      unit.unitY = 24;
    }

    if (unit.unitType === UNIT_HELI) unit.unitYMov = f(unit.unitYMov + f(0.0001)); /* helicopters fall more slowly */
    else unit.unitYMov = f(unit.unitYMov + f(0.03));

    if (!this.JE_stabilityCheck(unit.unitX, roundff(unit.unitY))) {
      unit.unitYMov = 0;
      unit.isYInAir = false;
    }
  }

  DE_RunTickAnimate(): void {
    for (let p = 0; p < MAX_PLAYERS; ++p) {
      for (const ptr of this.destruct_player[p].unit) {
        /* Don't mess with any unit that is unallocated or doesn't animate and is set to frame 0 */
        if (DE_isValidUnit(ptr) === false) continue;
        if (systemAni[ptr.unitType] === false && ptr.ani_frame === 0) continue;
        if (++ptr.ani_frame > 3) ptr.ani_frame = 0;
      }
    }
  }

  DE_RunTickDrawWalls(): void {
    for (const wall of this.world.mapWalls) if (wall.wallExist) this.draws.walls.push({ x: wall.wallX, y: wall.wallY });
  }

  DE_RunTickExplosions(): void {
    /* Run through all open explosions.  They are not sorted in any way */
    for (const e of this.exploRec) {
      if (e.isAvailable === true) continue; /* Nothing to do */

      for (let j = 0; j < e.explofill; j++) {
        /* An explosion is comprised of multiple 'flares' that fan out.
           Calculate where this 'flare' will end up */
        const tempRadian = f(mt_rand_lt1() * (2 * M_PI));
        const tempPosY = f2i(f(e.y + roundff(f(f(cosf(tempRadian) * mt_rand_lt1()) * e.explowidth))));
        let tempPosX = f2i(f(e.x + roundff(f(f(sinf(tempRadian) * mt_rand_lt1()) * e.explowidth))));

        /* Our game allows explosions to wrap around.  This looks to have originally been a bug
         * that was left in as being fun. */
        while (tempPosX < 0) tempPosX += 320;
        while (tempPosX > 320) tempPosX -= 320;

        /* We don't draw our explosion if it's out of bounds vertically */
        if (tempPosY >= 200 || tempPosY <= 15) continue;

        /* Dirt simply draws a brown pixel; flares explode and have a star formation. */
        switch (e.exploType) {
          case EXPL_DIRT: {
            const at = tempPosX + tempPosY * SCREEN_W;
            if (inScreen(at)) this.tempScreen[at] = PIXEL_DIRT;
            break;
          }
          case EXPL_NORMAL:
            this.JE_superPixel(tempPosX, tempPosY);
            this.DE_TestExplosionCollision(tempPosX, tempPosY);
            break;
          default:
            throw new Error(`destruct: explosion type ${e.exploType}`); // assert(false)
        }
      }

      /* Widen the explosion and delete it if necessary. */
      e.explowidth++;
      if (e.explowidth === e.explomax) e.isAvailable = true;
    }
  }

  DE_TestExplosionCollision(PosX: number, PosY: number): void {
    for (let i = PLAYER_LEFT; i < MAX_PLAYERS; i++) {
      for (const unit of this.destruct_player[i].unit) {
        if (DE_isValidUnit(unit) === true && PosX > unit.unitX && PosX < unit.unitX + 11 && PosY < unit.unitY && PosY > f(unit.unitY - 11)) {
          unit.health--;
          if (unit.health <= 0) this.DE_DestroyUnit(i, unit);
        }
      }
    }
  }

  DE_DestroyUnit(playerID: number, unit: destruct_unit_s): void {
    /* Helicopters explode like small shots do.  Invalids are their own special case. */
    this.JE_makeExplosion(unit.unitX + 5, f2u(f(roundff(unit.unitY) - 5)), unit.unitType === UNIT_HELI ? SHOT_SMALL : SHOT_INVALID);

    if (unit.unitType !== UNIT_SATELLITE) {
      /* increment score */
      this.destruct_player[playerID].unitsRemaining--;
      this.destruct_player[playerID === PLAYER_LEFT ? PLAYER_RIGHT : PLAYER_LEFT].score++;
    }
  }

  DE_RunTickShots(): void {
    const world = this.world;
    for (let i = 0; i < this.config.max_shots; i++) {
      const shot = this.shotRec[i];
      if (shot.isAvailable === true) continue; /* Nothing to do */

      /* Move the shot.  Simple displacement */
      shot.x = f(shot.x + shot.xmov);
      shot.y = f(shot.y + shot.ymov);

      /* If the shot can bounce off the map, bounce it */
      if (shotBounce[shot.shottype]) {
        if (shot.y > 199 || shot.y < 14) {
          shot.y = f(shot.y - shot.ymov);
          shot.ymov = f(-shot.ymov);
        }
        if (shot.x < 1 || shot.x > 318) {
          shot.x = f(shot.x - shot.xmov);
          shot.xmov = f(-shot.xmov);
        }
      } else {
        /* If it cannot, apply normal physics */
        shot.ymov = f(shot.ymov + f(0.05)); /* add gravity */

        if (shot.y > 199) {
          /* We hit the floor */
          shot.y = f(shot.y - shot.ymov);
          shot.ymov = f(f(-shot.ymov) * f(0.8)); /* bounce at reduced velocity */

          /* Don't allow a bouncing shot to bounce straight up and down */
          if (shot.xmov === 0) shot.xmov = f(shot.xmov + f(mt_rand_lt1() - f(0.5)));
        }
      }

      /* Shot has gone out of bounds. Eliminate it. */
      if (shot.x > 318 || shot.x < 1) {
        shot.isAvailable = true;
        continue;
      }

      /* Now check for collisions. */

      /* Don't bother checking for collisions above the map :) */
      if (shot.y <= 14) continue;

      let tempPosX = f2u(roundf(shot.x));
      let tempPosY = f2u(roundf(shot.y));

      /*Check building hits*/
      for (let j = 0; j < MAX_PLAYERS; j++) {
        for (const unit of this.destruct_player[j].unit) {
          if (DE_isValidUnit(unit) === false) continue;
          if (tempPosX > unit.unitX && tempPosX < unit.unitX + 11 && tempPosY < unit.unitY && tempPosY > f(unit.unitY - 13)) {
            shot.isAvailable = true;
            this.JE_makeExplosion(tempPosX, tempPosY, shot.shottype);
          }
        }
      }

      const tempTrails = u32((shotColor[shot.shottype] << 4) - 3);
      this.JE_pixCool(tempPosX, tempPosY, tempTrails, i);

      /*Draw the shot trail (if applicable) */
      switch (shotTrail[shot.shottype]) {
        case TRAILS_NONE:
          break;
        case TRAILS_NORMAL:
          this.DE_DrawTrails(shot, 2, 4, tempTrails - 3, i);
          break;
        case TRAILS_FULL:
          this.DE_DrawTrails(shot, 4, 3, tempTrails - 1, i);
          break;
      }

      /* Bounce off of or destroy walls */
      for (const wall of world.mapWalls) {
        if (wall.wallExist === true && tempPosX >= wall.wallX && tempPosX <= wall.wallX + 11 && tempPosY >= wall.wallY && tempPosY <= wall.wallY + 14) {
          if (demolish[shot.shottype]) {
            /* Blow up the wall and remove the shot. */
            wall.wallExist = false;
            shot.isAvailable = true;
            this.JE_makeExplosion(tempPosX, tempPosY, shot.shottype);
            continue;
          } else {
            /* Otherwise, bounce. */
            if (f(shot.x - shot.xmov) < wall.wallX || f(shot.x - shot.xmov) > wall.wallX + 11) {
              shot.xmov = f(-shot.xmov);
            }
            if (f(shot.y - shot.ymov) < wall.wallY || f(shot.y - shot.ymov) > wall.wallY + 14) {
              if (shot.ymov < 0) shot.ymov = f(-shot.ymov);
              else shot.ymov = f(f(-shot.ymov) * f(0.8));
            }

            tempPosX = f2u(roundf(shot.x));
            tempPosY = f2u(roundf(shot.y));
          }
        }
      }

      /* Our last collision check, at least for now.  We hit dirt. */
      if (this.tempScreen[tempPosX + tempPosY * SCREEN_W] === PIXEL_DIRT) {
        shot.isAvailable = true;
        this.JE_makeExplosion(tempPosX, tempPosY, shot.shottype);
        continue;
      }
    }
  }

  DE_DrawTrails(shot: destruct_shot_s, count: number, decay: number, startColor: number, shotIndex: number): void {
    for (let i = count - 1; i >= 0; i--) {
      /* going in reverse is important as it affects how we draw */
      if (shot.trailc[i] > 0 && shot.traily[i] > 12) {
        /* If it exists and if it's not out of bounds, draw it. */
        this.JE_pixCool(shot.trailx[i], shot.traily[i], shot.trailc[i], shotIndex, true);
      }

      if (i === 0) {
        /* The first trail we create. */
        shot.trailx[i] = f2u(roundf(shot.x));
        shot.traily[i] = f2u(roundf(shot.y));
        shot.trailc[i] = startColor;
      } else {
        /* The newer trails decay into the older trails.*/
        shot.trailx[i] = shot.trailx[i - 1];
        shot.traily[i] = shot.traily[i - 1];
        if (shot.trailc[i - 1] > 0) shot.trailc[i] = u32(shot.trailc[i - 1] - decay);
      }
    }
  }

  DE_RunTickAI(): void {
    for (let i = 0; i < MAX_PLAYERS; i++) {
      const ptrPlayer = this.destruct_player[i];
      if (ptrPlayer.is_cpu === false) continue;

      let j = i + 1;
      if (j >= MAX_PLAYERS) j = 0;

      const ptrTarget = this.destruct_player[j];
      const ptrCurUnit = ptrPlayer.unit[ptrPlayer.unitSelected];
      const ai = ptrPlayer.aiMemory;
      const moves = ptrPlayer.moves;

      /* This is the start of the original AI.  Heh.  AI. */

      if (ai.c_noDown > 0) ai.c_noDown--;

      if (mt_rand() % 100 > 80) {
        ai.c_Angle += (mt_rand() % 3) - 1;
        if (ai.c_Angle > 1) ai.c_Angle = 1;
        else if (ai.c_Angle < -1) ai.c_Angle = -1;
      }
      if (mt_rand() % 100 > 90) {
        if (ai.c_Angle > 0 && ptrCurUnit.angle > M_PI_2 - M_PI / 9) ai.c_Angle = 0;
        else if (ai.c_Angle < 0 && ptrCurUnit.angle < M_PI / 8) ai.c_Angle = 0;
      }

      if (mt_rand() % 100 > 93) {
        ai.c_Power += (mt_rand() % 3) - 1;
        if (ai.c_Power > 1) ai.c_Power = 1;
        else if (ai.c_Power < -1) ai.c_Power = -1;
      }
      if (mt_rand() % 100 > 90) {
        if (ai.c_Power > 0 && ptrCurUnit.power > 4) ai.c_Power = 0;
        else if (ai.c_Power < 0 && ptrCurUnit.power < 3) ai.c_Power = 0;
        else if (ptrCurUnit.power < 2) ai.c_Power = 1;
      }

      // prefer helicopter
      for (let k = 0; k < this.config.max_installations; k++) {
        const ptrUnit = ptrPlayer.unit[k];
        if (DE_isValidUnit(ptrUnit) && ptrUnit.unitType === UNIT_HELI) {
          ptrPlayer.unitSelected = k;
          break;
        }
      }

      if (ptrCurUnit.unitType === UNIT_HELI) {
        if (ptrCurUnit.isYInAir === false) ai.c_Power = 1;
        if (mt_rand_mod(ptrCurUnit.unitX) > 100) ai.c_Power = 1;
        if (mt_rand() % 240 > ptrCurUnit.unitX) moves[MOVE_RIGHT] = true;
        else if ((mt_rand() % 20) + 300 < ptrCurUnit.unitX) moves[MOVE_LEFT] = true;
        else if (mt_rand() % 30 === 1) ai.c_Angle = (mt_rand() % 3) - 1;
        if (ptrCurUnit.unitX > 295 && ptrCurUnit.lastMove > 1) {
          moves[MOVE_LEFT] = true;
          moves[MOVE_RIGHT] = false;
        }
        if (ptrCurUnit.unitType !== UNIT_HELI || ptrCurUnit.lastMove > 3 || (ptrCurUnit.unitX > 160 && ptrCurUnit.lastMove > -3)) {
          if (mt_rand_mod(roundff(ptrCurUnit.unitY)) < 150 && ptrCurUnit.unitYMov < f(0.01) && (ptrCurUnit.unitX < 160 || ptrCurUnit.lastMove < 2)) moves[MOVE_FIRE] = true;
          ai.c_noDown = (5 - Math.abs(ptrCurUnit.lastMove)) * (5 - Math.abs(ptrCurUnit.lastMove)) + 3;
          ai.c_Power = 1;
        } else {
          moves[MOVE_FIRE] = false;
        }

        for (const ptrUnit of ptrTarget.unit) {
          if (Math.abs((ptrUnit.unitX | 0) - (ptrCurUnit.unitX | 0)) < 8) {
            /* I get it.  This makes helicopters hover over their enemies. */
            if (ptrUnit.unitType === UNIT_SATELLITE) {
              moves[MOVE_FIRE] = false;
            } else {
              moves[MOVE_LEFT] = false;
              moves[MOVE_RIGHT] = false;
              if (ptrCurUnit.lastMove < -1) ptrCurUnit.lastMove++;
              else if (ptrCurUnit.lastMove > 1) ptrCurUnit.lastMove--;
            }
          }
        }
      } else {
        moves[MOVE_FIRE] = true;
      }

      if (mt_rand() % 200 > 198) {
        moves[MOVE_CHANGE] = true;
        ai.c_Angle = 0;
        ai.c_Power = 0;
        ai.c_Fire = 0;
      }

      if (mt_rand() % 100 > 98 || ptrCurUnit.shotType === SHOT_TRACER) moves[MOVE_CYDN] = true;
      if (ai.c_Angle > 0) moves[MOVE_LEFT] = true;
      if (ai.c_Angle < 0) moves[MOVE_RIGHT] = true;
      if (ai.c_Power > 0) moves[MOVE_UP] = true;
      if (ai.c_Power < 0 && ai.c_noDown === 0) moves[MOVE_DOWN] = true;
      if (ai.c_Fire > 0) moves[MOVE_FIRE] = true;

      if (ptrCurUnit.unitYMov < f(-0.1) && ptrCurUnit.unitType === UNIT_HELI) moves[MOVE_FIRE] = false;

      /* This last hack was down in the processing section. */
      if (ptrCurUnit.unitType === UNIT_LASER || ptrCurUnit.isYInAir === true) ai.c_Power = 0;
    }
  }

  DE_RunTickDrawCrosshairs(): void {
    /* Most vehicles aim left or right.  Helis can aim either way and this must be accounted for. */
    for (let i = 0; i < MAX_PLAYERS; i++) {
      const direction = i === PLAYER_LEFT ? -1 : 1;
      const player = this.destruct_player[i];
      const curUnit = player.unit[player.unitSelected];
      let tempPosX: number;
      let tempPosY: number;

      if (curUnit.unitType === UNIT_HELI) {
        const cube = roundff(f(f(f(0.1) * curUnit.lastMove) * curUnit.lastMove) * curUnit.lastMove);
        tempPosX = f2i(f(f(curUnit.unitX + cube) + 5));
        tempPosY = f2i(f(roundff(curUnit.unitY) + 1));
      } else {
        const reach = f(f(curUnit.power * 8) + 7);
        tempPosX = f2i(roundff(f(curUnit.unitX + 6) - f(f(cosf(curUnit.angle) * reach) * direction)));
        tempPosY = f2i(roundff(f(f(curUnit.unitY - 7) - f(sinf(curUnit.angle) * reach))));
      }
      this.draws.crosshairs.push({ x: tempPosX, y: tempPosY });
    }
  }

  DE_RunTickGetInput(keys: KeysActive): void {
    /* destruct_player.moves and destruct_player.keys line up; rather than manually checking left
     * and right we can just loop through the indexes and set the actions as needed. */
    for (let player_index = 0; player_index < MAX_PLAYERS; player_index++) {
      const player = this.destruct_player[player_index];
      for (let key_index = 0; key_index < MAX_KEY; key_index++) {
        for (let slot_index = 0; slot_index < MAX_KEY_OPTIONS; slot_index++) {
          const key = player.keys[key_index][slot_index];
          if (key === "") break;
          if (keys.isDown(key)) {
            /* The right key was clearly pressed */
            player.moves[key_index] = true;

            /* Some keys we want to toggle afterwards */
            if (key_index === KEY_CHANGE || key_index === KEY_CYUP || key_index === KEY_CYDN) keys.release(key);
            break;
          }
        }
      }
    }
  }

  DE_ProcessInput(): void {
    for (let player_index = 0; player_index < MAX_PLAYERS; player_index++) {
      const player = this.destruct_player[player_index];
      if (player.unitsRemaining <= 0) continue;

      const direction = player_index === PLAYER_LEFT ? -1 : 1;
      const curUnit = player.unit[player.unitSelected];
      const moves = player.moves;

      if (systemAngle[curUnit.unitType] === true) {
        /* selected unit may change shot angle */
        if (moves[MOVE_LEFT] === true) {
          if (player_index === PLAYER_LEFT) DE_RaiseAngle(curUnit);
          else DE_LowerAngle(curUnit);
        }
        if (moves[MOVE_RIGHT] === true) {
          if (player_index === PLAYER_LEFT) DE_LowerAngle(curUnit);
          else DE_RaiseAngle(curUnit);
        }
      } else if (curUnit.unitType === UNIT_HELI) {
        if (moves[MOVE_LEFT] === true && curUnit.unitX > 5) {
          if (this.JE_stabilityCheck(curUnit.unitX - 5, roundff(curUnit.unitY))) {
            if (curUnit.lastMove > -5) curUnit.lastMove--;
            curUnit.unitX--;
            if (this.JE_stabilityCheck(curUnit.unitX, roundff(curUnit.unitY))) curUnit.isYInAir = true;
          }
        }
        if (moves[MOVE_RIGHT] === true && curUnit.unitX < 305) {
          if (this.JE_stabilityCheck(curUnit.unitX + 5, roundff(curUnit.unitY))) {
            if (curUnit.lastMove < 5) curUnit.lastMove++;
            curUnit.unitX++;
            if (this.JE_stabilityCheck(curUnit.unitX, roundff(curUnit.unitY))) curUnit.isYInAir = true;
          }
        }
      }

      if (curUnit.unitType !== UNIT_LASER) {
        /*increasepower*/
        if (moves[MOVE_UP] === true) {
          if (curUnit.unitType === UNIT_HELI) {
            curUnit.isYInAir = true;
            curUnit.unitYMov = f(curUnit.unitYMov - f(0.1));
          } else if (curUnit.unitType === UNIT_JUMPER && curUnit.isYInAir === false) {
            curUnit.unitYMov = -3;
            curUnit.isYInAir = true;
          } else {
            DE_RaisePower(curUnit);
          }
        }
        /*decreasepower*/
        if (moves[MOVE_DOWN] === true) {
          if (curUnit.unitType === UNIT_HELI && curUnit.isYInAir === true) curUnit.unitYMov = f(curUnit.unitYMov + f(0.1));
          else DE_LowerPower(curUnit);
        }
      }

      /*up/down weapon.  These just cycle until a valid weapon is found */
      if (moves[MOVE_CYUP] === true) DE_CycleWeaponUp(curUnit);
      if (moves[MOVE_CYDN] === true) DE_CycleWeaponDown(curUnit);

      /* Change.  Since change would change out curUnit pointer, let's just do it last.
       * Validity checking is performed at the beginning of the tick. */
      if (moves[MOVE_CHANGE] === true) {
        player.unitSelected++;
        if (player.unitSelected >= this.config.max_installations) player.unitSelected = 0;
      }

      /*Newshot*/
      if (player.shotDelay > 0) player.shotDelay--;
      if (moves[MOVE_FIRE] === true && player.shotDelay === 0) {
        player.shotDelay = shotDelay[curUnit.shotType];

        switch (shotDirt[curUnit.shotType]) {
          case EXPL_NONE:
            break;
          case EXPL_MAGNET:
            this.DE_RunMagnet(player_index, curUnit);
            break;
          case EXPL_DIRT:
          case EXPL_NORMAL:
            this.DE_MakeShot(player_index, curUnit, direction);
            break;
          default:
            throw new Error(`destruct: shot type ${curUnit.shotType}`); // assert(false)
        }
      }
    }
  }

  DE_MakeShot(curPlayer: number, curUnit: destruct_unit_s, direction: number): void {
    /* First, find an empty shot struct we can use */
    let shotIndex = -1;
    for (let i = 0; ; i++) {
      if (i >= this.config.max_shots) return; /* no empty slots.  Do nothing. */
      if (this.shotRec[i].isAvailable) {
        shotIndex = i;
        break;
      }
    }

    /* Helis can't fire when they are on the ground. */
    if (curUnit.unitType === UNIT_HELI && curUnit.isYInAir === false) return;

    /* Play the firing sound */
    this.soundQueue[curPlayer] = shotSound[curUnit.shotType];

    const shot = this.shotRec[shotIndex];
    /* Create our shot.  Some units have differing logic here */
    switch (curUnit.unitType) {
      case UNIT_HELI:
        shot.x = f(u32(curUnit.unitX + curUnit.lastMove * 2 + 5));
        shot.xmov = f(f(f(f(0.02) * curUnit.lastMove) * curUnit.lastMove) * curUnit.lastMove);

        /* If we are trying in vain to move up off the screen, act differently.*/
        if (this.destruct_player[curPlayer].moves[MOVE_UP] && curUnit.unitY < 30) {
          shot.y = curUnit.unitY;
          shot.ymov = f(0.1);

          if (shot.xmov < 0) shot.xmov = f(shot.xmov + f(0.1));
          else if (shot.xmov > 0) shot.xmov = f(shot.xmov - f(0.1));
        } else {
          shot.y = f(curUnit.unitY + 1);
          shot.ymov = f(f(0.5) + f(curUnit.unitYMov * f(0.1)));
        }
        break;

      case UNIT_JUMPER: /* Jumpers are normally only special for the left hand player.  Bug?  Or feature? */
        if (this.config.jumper_straight[curPlayer]) {
          /* This is identical to the default case. */
          this.aimShot(shot, curUnit, direction);
        } else {
          /* This is not identical to the default case. */
          shot.x = f(curUnit.unitX + 2);
          shot.xmov = f(f(f(-cosf(curUnit.angle)) * curUnit.power) * direction);

          if (curUnit.isYInAir === true) {
            shot.ymov = 1;
            shot.y = f(curUnit.unitY + 2);
          } else {
            shot.ymov = -2;
            shot.y = f(curUnit.unitY - 12);
          }
        }
        break;

      default:
        this.aimShot(shot, curUnit, direction);
        break;
    }

    /* Now set/clear out a few last details. */
    shot.isAvailable = false;
    shot.shottype = curUnit.shotType;
    shot.trailc[0] = 0;
    shot.trailc[1] = 0;
    shot.trailc[2] = 0;
    shot.trailc[3] = 0;
  }

  /** DE_MakeShot's default case: out of the barrel along the unit's angle. */
  private aimShot(shot: destruct_shot_s, curUnit: destruct_unit_s, direction: number): void {
    shot.x = f(f(curUnit.unitX + 6) - f(f(cosf(curUnit.angle) * 10) * direction));
    shot.y = f(f(curUnit.unitY - 7) - f(sinf(curUnit.angle) * 10));
    shot.xmov = f(f(f(-cosf(curUnit.angle)) * curUnit.power) * direction);
    shot.ymov = f(f(-sinf(curUnit.angle)) * curUnit.power);
  }

  DE_RunMagnet(curPlayer: number, magnet: destruct_unit_s): void {
    const curEnemy = curPlayer === PLAYER_LEFT ? PLAYER_RIGHT : PLAYER_LEFT;
    const direction = curPlayer === PLAYER_LEFT ? -1 : 1;

    /* Push all shots that are in front of the magnet */
    for (const shot of this.shotRec) {
      if (shot.isAvailable === false) {
        if ((curPlayer === PLAYER_LEFT && shot.x > magnet.unitX) || (curPlayer === PLAYER_RIGHT && shot.x < magnet.unitX)) {
          shot.xmov = f(shot.xmov + f(f(magnet.power * f(0.1)) * -direction));
        }
      }
    }

    const enemy = this.destruct_player[curEnemy];
    for (const enemyUnit of enemy.unit) {
      /* magnets push coptors */
      if (DE_isValidUnit(enemyUnit) && enemyUnit.unitType === UNIT_HELI && enemyUnit.isYInAir === true) {
        if ((curEnemy === PLAYER_RIGHT && enemyUnit.unitX + 11 < 318) || (curEnemy === PLAYER_LEFT && enemyUnit.unitX > 1)) {
          enemyUnit.unitX = u32(enemyUnit.unitX - 2 * direction);
        }
      }
    }
    magnet.ani_frame = 1;
  }

  DE_RunTickCheckEndgame(): boolean {
    const mode = this.world.destructMode;
    if (this.destruct_player[PLAYER_LEFT].unitsRemaining === 0) {
      this.destruct_player[PLAYER_RIGHT].score += ModeScore[PLAYER_LEFT][mode];
      this.soundQueue[7] = V_CLEARED_PLATFORM;
      return true;
    }
    if (this.destruct_player[PLAYER_RIGHT].unitsRemaining === 0) {
      this.destruct_player[PLAYER_LEFT].score += ModeScore[PLAYER_RIGHT][mode];
      this.soundQueue[7] = V_CLEARED_PLATFORM;
      return true;
    }
    return false;
  }

  /** JE_pix(x, y, c) and its four neighbours in c - 2, on VGAScreen; `shot` is whose (or its trail). */
  JE_pixCool(x: number, y: number, c: number, shot: number, trail = false): void {
    this.draws.pixels.push({ x, y, c: c & 0xff, trail, shot });
  }
}

/** JE_superPixel's star: the colour each pixel rises to at least, and how much brighter it gets. */
const starPattern = [
  [0, 0, 246, 0, 0],
  [0, 247, 249, 247, 0],
  [246, 249, 252, 249, 246],
  [0, 247, 249, 247, 0],
  [0, 0, 246, 0, 0],
];
const starIntensity = [
  [0, 0, 1, 0, 0],
  [0, 1, 2, 1, 0],
  [1, 2, 4, 2, 1],
  [0, 1, 2, 1, 0],
  [0, 0, 1, 0, 0],
];

/** A helper used when aliasing dirt: a shade of brown by how much dirt surrounds pixel s. */
export function aliasDirtPixel(screen: Uint8Array, x: number, y: number, s: number): number {
  let newColor = PIXEL_BLACK;
  if (y > 0 && screen[s - SCREEN_W] === PIXEL_DIRT) newColor += 1; // look up
  if (y < SCREEN_H - 1 && screen[s + SCREEN_W] === PIXEL_DIRT) newColor += 3; // look down
  if (x > 0 && screen[s - 1] === PIXEL_DIRT) newColor += 2; // look left
  if (x < SCREEN_W - 1 && screen[s + 1] === PIXEL_DIRT) newColor += 2; // look right
  if (newColor !== PIXEL_BLACK) return newColor + 16; // 16 must be the start of the brown pixels.
  return PIXEL_BLACK;
}

/* Unit functions */

export function DE_CycleWeaponUp(unit: destruct_unit_s): void {
  do {
    unit.shotType++;
    if (unit.shotType > SHOT_LAST) unit.shotType = SHOT_FIRST;
  } while (weaponSystems[unit.unitType][unit.shotType] === 0);
}

export function DE_CycleWeaponDown(unit: destruct_unit_s): void {
  do {
    unit.shotType--;
    if (unit.shotType < SHOT_FIRST) unit.shotType = SHOT_LAST;
  } while (weaponSystems[unit.unitType][unit.shotType] === 0);
}

export function DE_RaiseAngle(unit: destruct_unit_s): void {
  unit.angle = f(unit.angle + f(0.01));
  if (unit.angle > M_PI_2 - f(0.01)) unit.angle = f(M_PI_2 - f(0.01));
}

export function DE_LowerAngle(unit: destruct_unit_s): void {
  unit.angle = f(unit.angle - f(0.01));
  if (unit.angle < 0) unit.angle = 0;
}

export function DE_RaisePower(unit: destruct_unit_s): void {
  unit.power = f(unit.power + f(0.05));
  if (unit.power > 5) unit.power = 5;
}

export function DE_LowerPower(unit: destruct_unit_s): void {
  unit.power = f(unit.power - f(0.05));
  if (unit.power < 1) unit.power = 1;
}

/** Returns true if the unit's health is above 0 (health doubles as "this slot is in use"). */
export function DE_isValidUnit(unit: destruct_unit_s): boolean {
  return unit.health > 0;
}
