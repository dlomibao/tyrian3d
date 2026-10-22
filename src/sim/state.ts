// Shared game state for the OpenTyrian port: the C globals from varz.h, backgrnd.h, config.h,
// mainint.h, tyrian2.h, player.h and shots.h, with their C names.
//
// Conventions for ported code (DECISIONS.md D1):
// - Globals live on `g` (or on the structs below) so any module can assign them.
// - Arrays keep their C indexing. Where the C comment says [1..N] but the code indexes from 0,
//   follow the code.
// - Narrow integer types are noted per field. Wrap on assignment with src/sim/cint.ts wherever the
//   value can overflow; that matters for Tyrian's logic.
// - Statics private to one C file belong in that file's module, not here.

import type { EnemyDat, ItemDat, Level, LevelEvent, Palette } from "../data";
import type { Sprite2Sheet, SpriteTable } from "./draw";

// --- Constants (varz.h, shots.h, episodes.h, opentyr.h) ---

export const ENEMY_SHOT_MAX = 60;
export const MAX_EXPLOSIONS = 200;
export const MAX_REPEATING_EXPLOSIONS = 20;
export const MAX_SUPERPIXELS = 101;
export const MAX_PWEAPON = 81;
export const FRONT_WEAPON = 0;
export const REAR_WEAPON = 1;
export const LEFT_SIDEKICK = 0;
export const RIGHT_SIDEKICK = 1;
export const SA_NONE = 0;
export const DIFFICULTY_EASY = 1;
export const DIFFICULTY_NORMAL = 2;

// --- Structs ---

/** struct JE_SingleEnemyType (varz.h). */
export interface Enemy {
  fillbyte: number;
  /** JE_integer: position */
  ex: number;
  ey: number;
  /** JE_shortint: current speed */
  exc: number;
  eyc: number;
  /** JE_shortint: random acceleration */
  exca: number;
  eyca: number;
  /** JE_shortint: fixed acceleration wait time */
  excc: number;
  eycc: number;
  exccw: number;
  eyccw: number;
  /** JE_byte */
  armorleft: number;
  /** JE_byte[3] */
  eshotwait: number[];
  eshotmultipos: number[];
  /** JE_byte */
  enemycycle: number;
  ani: number;
  /** JE_word[20] */
  egr: number[];
  size: number;
  linknum: number;
  aniactive: number;
  animax: number;
  aniwhenfire: number;
  /** Sprite2_array* */
  sprite2s: Sprite2Sheet | null;
  /** JE_shortint */
  exrev: number;
  eyrev: number;
  /** JE_integer */
  exccadd: number;
  eyccadd: number;
  /** JE_byte */
  exccwmax: number;
  eyccwmax: number;
  /** void* enemydatofs: the EnemyDat this enemy was made from. */
  enemydatofs: EnemyDat | null;
  edamaged: boolean;
  /** JE_word */
  enemytype: number;
  animin: number;
  edgr: number;
  /** JE_shortint */
  edlevel: number;
  edani: number;
  fill1: number;
  /** JE_byte */
  filter: number;
  /** JE_integer */
  evalue: number;
  fixedmovey: number;
  /** JE_byte[3] */
  freq: number[];
  launchwait: number;
  /** JE_word */
  launchtype: number;
  launchfreq: number;
  xaccel: number;
  yaccel: number;
  /** JE_byte[3] */
  tur: number[];
  /** JE_word: enemy created when this one dies */
  enemydie: number;
  enemyground: boolean;
  explonum: number;
  /** JE_word */
  mapoffset: number;
  scoreitem: boolean;
  special: boolean;
  flagnum: number;
  setto: boolean;
  /** JE_byte: duration */
  iced: number;
  launchspecial: number;
  /** JE_integer */
  xminbounce: number;
  xmaxbounce: number;
  yminbounce: number;
  ymaxbounce: number;
}

export function newEnemy(): Enemy {
  return {
    fillbyte: 0, ex: 0, ey: 0, exc: 0, eyc: 0, exca: 0, eyca: 0, excc: 0, eycc: 0, exccw: 0, eyccw: 0,
    armorleft: 0, eshotwait: [0, 0, 0], eshotmultipos: [0, 0, 0], enemycycle: 0, ani: 0,
    egr: new Array(20).fill(0), size: 0, linknum: 0, aniactive: 0, animax: 0, aniwhenfire: 0,
    sprite2s: null, exrev: 0, eyrev: 0, exccadd: 0, eyccadd: 0, exccwmax: 0, eyccwmax: 0,
    enemydatofs: null, edamaged: false, enemytype: 0, animin: 0, edgr: 0, edlevel: 0, edani: 0,
    fill1: 0, filter: 0, evalue: 0, fixedmovey: 0, freq: [0, 0, 0], launchwait: 0, launchtype: 0,
    launchfreq: 0, xaccel: 0, yaccel: 0, tur: [0, 0, 0], enemydie: 0, enemyground: false,
    explonum: 0, mapoffset: 0, scoreitem: false, special: false, flagnum: 0, setto: false, iced: 0,
    launchspecial: 0, xminbounce: 0, xmaxbounce: 0, yminbounce: 0, ymaxbounce: 0,
  };
}

/** EnemyShotType (varz.h). */
export interface EnemyShot {
  /** JE_integer */
  sx: number;
  sy: number;
  sxm: number;
  sym: number;
  /** JE_shortint */
  sxc: number;
  syc: number;
  /** JE_byte */
  tx: number;
  ty: number;
  /** JE_word */
  sgr: number;
  /** JE_byte */
  sdmg: number;
  duration: number;
  /** JE_word */
  animate: number;
  animax: number;
}

export const newEnemyShot = (): EnemyShot => ({
  sx: 0, sy: 0, sxm: 0, sym: 0, sxc: 0, syc: 0, tx: 0, ty: 0, sgr: 0, sdmg: 0, duration: 0, animate: 0, animax: 0,
});

/** Explosion (varz.h). */
export interface Explosion {
  /** JE_byte */
  ttl: number;
  /** JE_integer */
  x: number;
  y: number;
  /** JE_word */
  sprite: number;
  followPlayer: boolean;
  fixedPosition: boolean;
  /** JE_integer */
  deltaY: number;
}

export const newExplosion = (): Explosion => ({ ttl: 0, x: 0, y: 0, sprite: 0, followPlayer: false, fixedPosition: false, deltaY: 0 });

/** rep_explosion_type (varz.h); all unsigned int. */
export interface RepExplosion {
  delay: number;
  ttl: number;
  x: number;
  y: number;
  big: boolean;
}

export const newRepExplosion = (): RepExplosion => ({ delay: 0, ttl: 0, x: 0, y: 0, big: false });

/** superpixel_type (varz.h). */
export interface Superpixel {
  x: number;
  y: number;
  z: number;
  delta_x: number;
  delta_y: number;
  color: number;
}

export const newSuperpixel = (): Superpixel => ({ x: 0, y: 0, z: 0, delta_x: 0, delta_y: 0, color: 0 });

/** PlayerItems (player.h); all Uint8. */
export interface PlayerItems {
  ship: number;
  generator: number;
  shield: number;
  weapon: { id: number; power: number }[];
  sidekick: number[];
  special: number;
  sidekick_series: number;
  sidekick_level: number;
  super_arcade_mode: number;
}

export const newPlayerItems = (): PlayerItems => ({
  ship: 0, generator: 0, shield: 0, weapon: [{ id: 0, power: 0 }, { id: 0, power: 0 }], sidekick: [0, 0],
  special: 0, sidekick_series: 0, sidekick_level: 0, super_arcade_mode: 0,
});

export interface Sidekick {
  ammo_max: number;
  ammo_refill_ticks_max: number;
  /** affects movement and size */
  style: number;
  x: number;
  y: number;
  ammo: number;
  ammo_refill_ticks: number;
  animation_enabled: boolean;
  animation_frame: number;
  charge: number;
  charge_ticks: number;
}

/** Player (player.h). `uint` fields are unsigned 32-bit. */
export interface Player {
  cash: number;
  items: PlayerItems;
  last_items: PlayerItems;
  is_dragonwing: boolean;
  /** Uint8 *lives: points at a shared lives counter; a one-element box here. */
  lives: { value: number };
  shield_max: number;
  initial_armor: number;
  shot_hit_area_x: number;
  shot_hit_area_y: number;
  is_alive: boolean;
  invulnerable_ticks: number;
  exploding_ticks: number;
  shield: number;
  armor: number;
  weapon_mode: number;
  superbombs: number;
  purple_balls_needed: number;
  /** Uint16 */
  mouseX: number;
  mouseY: number;
  x: number;
  y: number;
  old_x: number[];
  old_y: number[];
  x_velocity: number;
  y_velocity: number;
  x_friction_ticks: number;
  y_friction_ticks: number;
  delta_x_shot_move: number;
  delta_y_shot_move: number;
  last_x_shot_move: number;
  last_y_shot_move: number;
  last_x_explosion_follow: number;
  last_y_explosion_follow: number;
  sidekick: Sidekick[];
}

const newSidekick = (): Sidekick => ({
  ammo_max: 0, ammo_refill_ticks_max: 0, style: 0, x: 0, y: 0, ammo: 0, ammo_refill_ticks: 0,
  animation_enabled: false, animation_frame: 0, charge: 0, charge_ticks: 0,
});

export const newPlayer = (): Player => ({
  cash: 0, items: newPlayerItems(), last_items: newPlayerItems(), is_dragonwing: false, lives: { value: 0 },
  shield_max: 0, initial_armor: 0, shot_hit_area_x: 0, shot_hit_area_y: 0, is_alive: false,
  invulnerable_ticks: 0, exploding_ticks: 0, shield: 0, armor: 0, weapon_mode: 0, superbombs: 0,
  purple_balls_needed: 0, mouseX: 0, mouseY: 0, x: 0, y: 0, old_x: new Array(20).fill(0),
  old_y: new Array(20).fill(0), x_velocity: 0, y_velocity: 0, x_friction_ticks: 0, y_friction_ticks: 0,
  delta_x_shot_move: 0, delta_y_shot_move: 0, last_x_shot_move: 0, last_y_shot_move: 0,
  last_x_explosion_follow: 0, last_y_explosion_follow: 0, sidekick: [newSidekick(), newSidekick()],
});

/** PlayerShotDataType (shots.h). */
export interface PlayerShotData {
  /** JE_integer */
  shotX: number;
  shotY: number;
  shotXM: number;
  shotYM: number;
  shotXC: number;
  shotYC: number;
  shotComplicated: boolean;
  shotDevX: number;
  shotDirX: number;
  shotDevY: number;
  shotDirY: number;
  shotCirSizeX: number;
  shotCirSizeY: number;
  /** JE_byte */
  shotTrail: number;
  /** JE_word */
  shotGr: number;
  shotAni: number;
  shotAniMax: number;
  /** Uint8 */
  shotDmg: number;
  /** JE_byte */
  shotBlastFilter: number;
  chainReaction: number;
  playerNumber: number;
  aimAtEnemy: number;
  aimDelay: number;
  aimDelayMax: number;
}

export const newPlayerShotData = (): PlayerShotData => ({
  shotX: 0, shotY: 0, shotXM: 0, shotYM: 0, shotXC: 0, shotYC: 0, shotComplicated: false, shotDevX: 0,
  shotDirX: 0, shotDevY: 0, shotDirY: 0, shotCirSizeX: 0, shotCirSizeY: 0, shotTrail: 0, shotGr: 0,
  shotAni: 0, shotAniMax: 0, shotDmg: 0, shotBlastFilter: 0, chainReaction: 0, playerNumber: 0,
  aimAtEnemy: 0, aimDelay: 0, aimDelayMax: 0,
});

/** boss_bar_t (tyrian2.h). */
export interface BossBar {
  link_num: number;
  armor: number;
  color: number;
}

// --- Loaded data the simulation reads (set up by the level loader) ---

export interface Resources {
  palettes: Palette[];
  items: ItemDat;
  /** enemyDat[ENEMY_NUM + 1], indexed by enemy type (index 0 unused). */
  enemyDat: EnemyDat[];
  /** spriteSheet8..12 and the explosion sheet (newsh6.shp). */
  spriteSheet8: Sprite2Sheet;
  spriteSheet9: Sprite2Sheet;
  spriteSheet10: Sprite2Sheet;
  spriteSheet11: Sprite2Sheet;
  spriteSheet12: Sprite2Sheet;
  explosionSpriteSheet: Sprite2Sheet;
  /** sprite_table[0..6] (fonts, interface, option shapes) from tyrian.shp. */
  spriteTables: SpriteTable[];
  /** Loads newsh<c>.shp (JE_loadCompShapes) for the enemy sprite sheets. */
  loadCompShapes(c: string): Sprite2Sheet;
}

/** The level being played: what JE_loadMap reads. */
export interface LevelData {
  level: Level;
  /** eventRec[], including the 65500 sentinel JE_loadMap appends. */
  eventRec: LevelEvent[];
  /** megaData1..3 shapes: per layer, tile pixels by tile number (0-based), null if absent. */
  tiles: [(Uint8Array | null)[], (Uint8Array | null)[], (Uint8Array | null)[]];
  /** Name of the shapes file, for tile cache ids. */
  shapesFile: string;
}

// --- Globals ---

export const g = {
  // Loaded data (set before a level starts).
  res: null as unknown as Resources,
  lvl: null as unknown as LevelData,

  // player.h / shots.h
  player: [newPlayer(), newPlayer()],
  playerShotData: Array.from({ length: MAX_PWEAPON + 1 }, newPlayerShotData),
  /** JE_byte[MAX_PWEAPON] */
  shotAvail: new Array<number>(MAX_PWEAPON).fill(0),

  // varz.h
  SFCurrentCode: [new Array(21).fill(0), new Array(21).fill(0)],
  SFExecuted: [0, 0],
  lvlFileNum: 0,
  /** JE_word */
  maxEvent: 0,
  eventLoc: 0,
  tempBackMove: 0,
  explodeMove: 0,
  /** JE_byte */
  levelEnd: 0,
  levelEndFxWait: 0,
  /** JE_shortint */
  levelEndWarp: 0,
  endLevel: false,
  reallyEndLevel: false,
  waitToEndLevel: false,
  playerEndLevel: false,
  normalBonusLevelCurrent: false,
  bonusLevelCurrent: false,
  smallEnemyAdjust: false,
  readyToEndLevel: false,
  quitRequested: false,
  newPL: new Array(10).fill(0),
  returnLoc: 0,
  returnActive: false,
  galagaShotFreq: 0,
  galagaLife: 0,
  debug: false,
  /** JE_word */
  curLoc: 0,
  firstGameOver: false,
  gameLoaded: false,
  enemyStillExploding: false,
  totalEnemy: 0,
  enemyKilled: 0,
  flash: 0,
  flashChange: 0,
  displayTime: 0,
  /** JE_byte[8]: sound effect ids to play this tick, by channel. */
  soundQueue: new Array<number>(8).fill(0),
  enemyContinualDamage: false,
  enemiesActive: false,
  forceEvents: false,
  stopBackgrounds: false,
  stopBackgroundNum: 0,
  damageRate: 0,
  background3x1: false,
  background3x1b: false,
  levelTimer: false,
  levelTimerCountdown: 0,
  levelTimerJumpTo: 0,
  randomExplosions: false,
  editShip1: false,
  editShip2: false,
  globalFlags: new Array<boolean>(10).fill(false),
  levelSong: 0,
  loadDestruct: false,
  mapOrigin: 0,
  mapPNum: 0,
  mapPlanet: new Array(5).fill(0),
  mapSection: new Array(5).fill(0),
  moveTyrianLogoUp: false,
  skipStarShowVGA: false,
  enemy: Array.from({ length: 100 }, newEnemy),
  /** JE_byte[100]: 1 = free, 0 = active, 2 = active but dying (see the collision code). */
  enemyAvail: new Array<number>(100).fill(1),
  enemyOffset: 0,
  enemyOnScreen: 0,
  superEnemy254Jump: 0,
  explosions: Array.from({ length: MAX_EXPLOSIONS }, newExplosion),
  explosionFollowAmountX: 0,
  explosionFollowAmountY: 0,
  fireButtonHeld: false,
  enemyShotAvail: new Array<boolean>(ENEMY_SHOT_MAX).fill(true),
  enemyShot: Array.from({ length: ENEMY_SHOT_MAX }, newEnemyShot),
  zinglonDuration: 0,
  astralDuration: 0,
  flareDuration: 0,
  flareStart: false,
  flareColChg: 0,
  specialWait: 0,
  nextSpecialWait: 0,
  spraySpecial: false,
  doIced: 0,
  infiniteShot: false,
  allPlayersGone: false,
  optionSatelliteRotate: 0,
  optionAttachmentMove: 0,
  optionAttachmentLinked: false,
  optionAttachmentReturn: false,
  chargeWait: 0,
  chargeLevel: 0,
  chargeMax: 0,
  chargeGr: 0,
  chargeGrWait: 0,
  neat: 0,
  rep_explosions: Array.from({ length: MAX_REPEATING_EXPLOSIONS }, newRepExplosion),
  superpixels: Array.from({ length: MAX_SUPERPIXELS }, newSuperpixel),
  last_superpixel: 0,
  doNotSaveBackup: false,
  specialWeaponFilter: 0,
  specialWeaponFreq: 0,
  specialWeaponWpn: 0,
  linkToPlayer: false,
  shipGr: 0,
  shipGr2: 0,
  shipGrPtr: null as Sprite2Sheet | null,
  shipGr2ptr: null as Sprite2Sheet | null,
  /** Enemy sprite sheets loaded by level events (enemySpriteSheets[4] in OpenTyrian). */
  enemySpriteSheets: [null, null, null, null] as (Sprite2Sheet | null)[],
  /** enemySpriteSheetIds[4]: which newsh file each sheet holds. */
  enemySpriteSheetIds: [0, 0, 0, 0],

  // backgrnd.h
  backPos: 0,
  backPos2: 0,
  backPos3: 0,
  backMove: 0,
  backMove2: 0,
  backMove3: 0,
  mapX: 0,
  mapY: 0,
  mapX2: 0,
  mapX3: 0,
  mapY2: 0,
  mapY3: 0,
  /** JE_byte **mapYPos etc.: pointers into the maps, as indices into Level.maps[layer]. */
  mapYPos: 0,
  mapY2Pos: 0,
  mapY3Pos: 0,
  mapXPos: 0,
  oldMapXOfs: 0,
  mapXOfs: 0,
  mapX2Ofs: 0,
  mapX2Pos: 0,
  mapX3Pos: 0,
  oldMapX3Ofs: 0,
  mapX3Ofs: 0,
  tempMapXOfs: 0,
  mapXbpPos: 0,
  mapX2bpPos: 0,
  mapX3bpPos: 0,
  map1YDelay: 0,
  map1YDelayMax: 0,
  map2YDelay: 0,
  map2YDelayMax: 0,
  /** BKwrap1..3 / BKwrap1to..3to: wrap pointers, as indices into Level.maps[layer]. */
  BKwrap1: 0,
  BKwrap2: 0,
  BKwrap3: 0,
  BKwrap1to: 0,
  BKwrap2to: 0,
  BKwrap3to: 0,
  anySmoothies: false,
  smoothie_data: new Array(9).fill(0),
  starfield_speed: 0,

  // config.h
  smoothies: new Array<boolean>(9).fill(false),
  starShowVGASpecialCode: 0,
  lastCubeMax: 0,
  cubeMax: 0,
  cubeList: [0, 0, 0, 0],
  gameHasRepeated: false,
  difficultyLevel: DIFFICULTY_NORMAL,
  oldDifficultyLevel: DIFFICULTY_NORMAL,
  initialDifficulty: DIFFICULTY_NORMAL,
  /** uint */
  power: 0,
  lastPower: 0,
  powerAdd: 0,
  shieldWait: 0,
  shieldT: 0,
  /** JE_byte[11] */
  shotRepeat: new Array<number>(11).fill(0),
  shotMultiPos: new Array<number>(11).fill(0),
  portConfigChange: false,
  portConfigDone: false,
  lastLevelName: "",
  levelName: "",
  mainLevel: 0,
  nextLevel: 0,
  saveLevel: 0,
  /** JE_shortint */
  levelFilter: -99,
  levelFilterNew: 0,
  levelBrightness: 0,
  levelBrightnessChg: 0,
  filtrationAvail: false,
  filterActive: false,
  filterFade: false,
  filterFadeStart: false,
  gameJustLoaded: false,
  galagaMode: false,
  extraGame: false,
  twoPlayerMode: false,
  twoPlayerLinked: false,
  onePlayerAction: false,
  superTyrian: false,
  trentWin: false,
  superArcadeMode: SA_NONE,
  superArcadePowerUp: 0,
  linkGunDirec: 0,
  inputDevice: [1, 2],
  secretHint: 0,
  background3over: 0,
  background2over: 1,
  gammaCorrection: 0,
  superPause: false,
  explosionTransparent: true,
  youAreCheating: false,
  displayScore: false,
  background2: false,
  smoothScroll: true,
  wild: false,
  superWild: false,
  starActive: false,
  topEnemyOver: false,
  skyEnemyOverAll: false,
  background2notTransparent: false,
  fastPlay: 0,
  pentiumMode: false,
  gameSpeed: 0,
  processorType: 4,

  // episodes.h
  episodeNum: 1,
  bonusLevel: false,
  jumpBackToEpisode1: false,

  // mainint.h
  /** fire, left fire, right fire, mode swap */
  button: [false, false, false, false],
  constantLastX: 0,
  textErase: 0,
  upgradeCost: 0,
  downgradeCost: 0,
  performSave: false,
  jumpSection: false,
  useLastBank: false,
  pause_pressed: false,
  ingamemenu_pressed: false,

  // tyrian2.h
  boss_bar: [{ link_num: 0, armor: 0, color: 0 }, { link_num: 0, armor: 0, color: 0 }] as BossBar[],
  /** levelEnemy[40] and levelEnemyMax, levelEnemyFrequency (tyrian2.c) */
  levelEnemy: new Array<number>(40).fill(0),
  levelEnemyMax: 0,
  levelEnemyFrequency: 0,

  // nortsong.h
  frameCountMax: 2,

  // tyrian2.c JE_main locals that survive across ticks
  /** Text shown in the message bar (JE_drawTextWindow), and the ticks until it's erased. */
  messageText: "",
  isNetworkGame: false,
  playDemo: false,
  constantPlay: false,
  constantDie: false,

  // --- added by player port ---
  /** helptext.h miscText[68] / miscTextB[5] (0-based like the C arrays), loaded from tyrian.hdt by loadHelpText. */
  miscText: new Array<string>(68).fill(""),
  miscTextB: new Array<string>(5).fill(""),
  /** params.h richMode: start a full game with 1,000,000 credits. */
  richMode: false,
  /** demo.h recordDemo (demo recording isn't ported; always false). */
  recordDemo: false,
};

export type Globals = typeof g;

/** all_players_dead (player.h) */
export const all_players_dead = (): boolean => !g.player[0].is_alive && (!g.twoPlayerMode || !g.player[1].is_alive);

/** all_players_alive (player.h) */
export const all_players_alive = (): boolean => g.player[0].is_alive && (!g.twoPlayerMode || g.player[1].is_alive);
