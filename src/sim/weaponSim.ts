// Port of the item screen's weapon simulator (OpenTyrian src/game_menu.c): the little window that
// shows the ship firing its weapons while the player browses an Upgrade Ship submenu.
//
// In the C it runs on the game's globals: JE_initWeaponView parks the ship at (72, 110) and resets
// the shot slots and the generator's power, and each JE_weaponSimUpdate fires and moves the shots
// with the same player_shot_create the game uses, plus shots.c's simulate_player_shots. The port
// does the same, on `g`, but borrows the globals only for the length of each call: weaponSim_run
// swaps the preview's copy of everything it touches in, runs, and swaps the game's back. So the
// game after the item screen is exactly what it would be without the preview, however long the
// player watched it (in the C, opening a submenu also advances mt_rand by initialize_starfield;
// see DECISIONS.md "The weapon preview borrows the sim's globals").
//
// Drawing goes to the draw list (draw.ts) like the game's, so the game's renderer shows the
// preview: a black window (8, 8)-(143, 182) of the 320x200 screen, the starfield, the shots and
// the ship. The text and bars the C draws over it (power level, upgrade costs, the generator's
// power bar) are HTML in src/app/weaponPreview.ts and shop.ts.
//
// Host API (src/app/weaponPreview.ts):
//   weaponSim_sync()        after each item screen input: starts the preview when a submenu
//                           opens (JE_menuFunction's JE_initWeaponView) and applies the loop top's
//                           "Reset player weapons"; returns whether the C runs the sim now
//   weaponSim_frame()       one JE_weaponSimUpdate (the C runs one every 3 timer frames, ~23 Hz);
//                           returns the frame's draw list
//   weaponSimPower()        the preview's generator power (0..900), for the C's power bar

import { initialize_starfield, starfield_restore, starfield_save, update_and_draw_starfield, type StarfieldStar } from "./backgrnd";
import { beginDrawList, blit_sprite2x2, drawGroup, drawList, drawState, fill_rectangle_xy, Pass, type DrawList } from "./draw";
import { MENU_UPGRADE_SUB, MENU_UPGRADES, menu } from "./game_menu";
import { mt_restore, mt_save } from "./mtrand";
import { playerShotKey, player_shot_create, simulate_player_shots } from "./shots";
import { g, LEFT_SIDEKICK, REAR_WEAPON, RIGHT_SIDEKICK, SHOT_LEFT_SIDEKICK, SHOT_RIGHT_SIDEKICK, type PlayerShotData } from "./state";
import { JE_SGr, type SheetRef } from "./varz";

/** The C runs JE_weaponSimUpdate after setFrameCount(3): three timer periods, 1.5 game ticks. */
export const WEAPON_SIM_FRAME_TICKS = 3 / 2;

/** The item screen's palette (JE_loadPic 1 → palettes[0]), which the preview is drawn in. */
const ITEM_SCREEN_PALETTE = 0;

/** Draw key of the ship in the preview (not in the C; it never moves). */
const SHIP_KEY = 9_999;

/** Everything JE_initWeaponView and JE_weaponSimUpdate write, or read back from a previous call. */
interface WeaponSimState {
  // player[0]
  x: number;
  y: number;
  mouseX: number;
  mouseY: number;
  delta_x_shot_move: number;
  delta_y_shot_move: number;
  last_x_explosion_follow: number;
  last_y_explosion_follow: number;
  sidekickXY: number[];
  // config.h
  power: number;
  lastPower: number;
  shotRepeat: number[];
  shotMultiPos: number[];
  // shots.h
  shotAvail: number[];
  playerShotData: PlayerShotData[];
  playerShotKey: number[];
  // player_shot_create queues weapon sounds; the item screen never plays the queue.
  soundQueue: number[];
  // backgrnd.c's stars; initialize_starfield also draws from mt_rand.
  stars: StarfieldStar[];
}

function capture(): WeaponSimState {
  const p = g.player[0];
  return {
    x: p.x,
    y: p.y,
    mouseX: p.mouseX,
    mouseY: p.mouseY,
    delta_x_shot_move: p.delta_x_shot_move,
    delta_y_shot_move: p.delta_y_shot_move,
    last_x_explosion_follow: p.last_x_explosion_follow,
    last_y_explosion_follow: p.last_y_explosion_follow,
    sidekickXY: p.sidekick.flatMap((s) => [s.x, s.y]),
    power: g.power,
    lastPower: g.lastPower,
    shotRepeat: [...g.shotRepeat],
    shotMultiPos: [...g.shotMultiPos],
    shotAvail: [...g.shotAvail],
    playerShotData: g.playerShotData.map((s) => ({ ...s })),
    playerShotKey: [...playerShotKey],
    soundQueue: [...g.soundQueue],
    stars: starfield_save(),
  };
}

function apply(s: WeaponSimState): void {
  const p = g.player[0];
  p.x = s.x;
  p.y = s.y;
  p.mouseX = s.mouseX;
  p.mouseY = s.mouseY;
  p.delta_x_shot_move = s.delta_x_shot_move;
  p.delta_y_shot_move = s.delta_y_shot_move;
  p.last_x_explosion_follow = s.last_x_explosion_follow;
  p.last_y_explosion_follow = s.last_y_explosion_follow;
  p.sidekick.forEach((sk, i) => {
    sk.x = s.sidekickXY[i * 2];
    sk.y = s.sidekickXY[i * 2 + 1];
  });
  g.power = s.power;
  g.lastPower = s.lastPower;
  copyInto(g.shotRepeat, s.shotRepeat);
  copyInto(g.shotMultiPos, s.shotMultiPos);
  copyInto(g.shotAvail, s.shotAvail);
  s.playerShotData.forEach((shot, i) => Object.assign(g.playerShotData[i], shot));
  copyInto(playerShotKey, s.playerShotKey);
  copyInto(g.soundQueue, s.soundQueue);
  starfield_restore(s.stars);
}

const copyInto = (dst: number[], src: readonly number[]) => {
  for (let i = 0; i < dst.length; i++) dst[i] = src[i];
};

/** The preview's copy of the globals while the game has them; null before the first submenu. */
let preview: WeaponSimState | null = null;
/** menu.curMenu at the last weaponSim_sync, to see a submenu open. */
let lastMenu = -1;

/**
 * Run `fn` on the globals with the preview's values swapped in, then swap the game's back. The
 * draw list and mt_rand are only borrowed: the preview keeps neither.
 */
function weaponSim_run<T>(fn: () => T): T {
  const game = capture();
  const rng = mt_save();
  const list = { ...drawList };
  const state = { ...drawState };
  const group = { ...drawGroup };
  if (preview) apply(preview);
  try {
    return fn();
  } finally {
    preview = capture();
    apply(game);
    mt_restore(rng);
    Object.assign(drawList, list);
    Object.assign(drawState, state);
    Object.assign(drawGroup, group);
  }
}

/** Forget the preview (a new item screen starts it afresh, as the C does on each submenu). */
export function weaponSim_reset(): void {
  preview = null;
  lastMenu = -1;
}

/**
 * Call after JE_itemScreen_init and after each input's JE_itemScreen_update. Mirrors what the C's
 * item screen does to the simulator's globals outside JE_weaponSimUpdate:
 * - JE_menuFunction runs JE_initWeaponView when Upgrade Ship opens a submenu (game_menu.c L2608);
 * - the loop top's "Reset player weapons" zeroes shotMultiPos (game_menu.c L770-ish, ported in
 *   JE_itemScreen_update for the game's copy).
 * Returns whether the C runs the simulator in the current menu (game_menu.c L895-899): in the
 * front and rear gun, generator and sidekick submenus.
 */
export function weaponSim_sync(): boolean {
  const { curMenu } = menu;
  if (curMenu === MENU_UPGRADE_SUB && lastMenu !== MENU_UPGRADE_SUB) weaponSim_run(JE_initWeaponView);
  lastMenu = curMenu;
  if (preview) preview.shotMultiPos.fill(0);
  return weaponSim_active();
}

/** IF (curmenu = 5) AND (cursel [2] IN [3, 4, 6, 7, 8]) (game_menu.c L894-899). */
export function weaponSim_active(): boolean {
  const { curMenu, curSel } = menu;
  return (
    preview !== null &&
    curMenu === MENU_UPGRADE_SUB &&
    (curSel[MENU_UPGRADES] === 3 || curSel[MENU_UPGRADES] === 4 || (curSel[MENU_UPGRADES] >= 6 && curSel[MENU_UPGRADES] <= 8))
  );
}

/** One frame of the simulator (JE_weaponSimUpdate), as a draw list the caller may keep. */
export function weaponSim_frame(): DrawList {
  return weaponSim_run(() => {
    JE_weaponSimUpdate();
    return { ...drawList };
  });
}

/** The preview's generator power, 0..900 (the C's power bar shows power / 10 pixels). */
export function weaponSimPower(): number {
  return preview?.power ?? 0;
}

/** JE_initWeaponView (game_menu.c L2233-2257) */
export function JE_initWeaponView(): void {
  const p = g.player[0];

  // fill_rectangle_xy(VGAScreen, 8, 8, 144, 177, 0): JE_weaponViewFrame clears it every frame.

  p.sidekick[LEFT_SIDEKICK].x = 72 - 15;
  p.sidekick[LEFT_SIDEKICK].y = 120;
  p.sidekick[RIGHT_SIDEKICK].x = 72 + 15;
  p.sidekick[RIGHT_SIDEKICK].y = 120;

  p.x = 72;
  p.y = 110;
  p.delta_x_shot_move = 0;
  p.delta_y_shot_move = 0;
  p.last_x_explosion_follow = 72;
  p.last_y_explosion_follow = 110;
  g.power = 500;
  g.lastPower = 500;

  g.shotAvail.fill(0);

  g.shotRepeat.fill(1);
  g.shotMultiPos.fill(0);

  initialize_starfield();
}

/**
 * JE_weaponSimUpdate (game_menu.c L3085-3145): a frame of the simulator, then the ship. The power
 * level, its arrows and costs, which the C draws here, are the shop's HTML (shop.ts renderPower).
 */
export function JE_weaponSimUpdate(): void {
  JE_weaponViewFrame();

  const p = g.player[0];
  drawState.pass = Pass.Player;
  drawState.key = SHIP_KEY;
  JE_drawItem1(p.items.ship, p.x - 5, p.y - 7);
  drawState.key = -1;
}

/** JE_drawItem(1, itemNum, x, y) (game_menu.c L1855-1890): the ship picture. */
function JE_drawItem1(itemNum: number, x: number, y: number): void {
  if (itemNum > 0) {
    if (itemNum > 90) {
      const shipGrPtr: SheetRef = { value: g.res.spriteSheet9 };
      const shipGr = JE_SGr(itemNum - 90, shipGrPtr);
      if (shipGrPtr.value) blit_sprite2x2(x, y, shipGrPtr.value, shipGr); // (extraShapes: null when no custom ships are loaded)
    } else {
      blit_sprite2x2(x, y, g.res.spriteSheet9, g.res.items.ships[itemNum].shipGraphic);
    }
  }
}

/** JE_weaponViewFrame (game_menu.c L3147-3263), without the power bar's pixels (see weaponSimPower). */
export function JE_weaponViewFrame(): void {
  const { items } = g.res;
  const p = g.player[0];

  beginDrawList();
  drawList.palette = ITEM_SCREEN_PALETTE;
  drawList.filter = -99;
  drawList.brightness = 0;
  drawList.screen = null;

  drawState.pass = Pass.Background1;
  fill_rectangle_xy(8, 8, 143, 182, 0);

  /* JE: (* Port Configuration Display *)
  (*    drawportconfigbuttons;*/

  drawState.pass = Pass.Starfield;
  update_and_draw_starfield(1);

  p.mouseX = p.x;
  p.mouseY = p.y;

  drawState.pass = Pass.PlayerShots;

  // create shots in weapon simulator
  for (let i = 0; i < 2; ++i) {
    if (g.shotRepeat[i] > 0) {
      --g.shotRepeat[i];
    } else {
      const item = p.items.weapon[i].id,
        item_power = p.items.weapon[i].power - 1,
        item_mode = i === REAR_WEAPON ? p.weapon_mode - 1 : 0;

      // (A power of 0 makes the C's uint item_power wrap and read past op[]; nothing fires here.)
      player_shot_create(item, i, p.x, p.y, p.mouseX, p.mouseY, items.weaponPorts[item].op[item_mode]?.[item_power] ?? 0, 1);
    }
  }

  if (items.options[p.items.sidekick[LEFT_SIDEKICK]].wPort > 0) {
    if (g.shotRepeat[SHOT_LEFT_SIDEKICK] > 0) {
      --g.shotRepeat[SHOT_LEFT_SIDEKICK];
    } else {
      const item = p.items.sidekick[LEFT_SIDEKICK];
      const x = p.sidekick[LEFT_SIDEKICK].x,
        y = p.sidekick[LEFT_SIDEKICK].y;

      player_shot_create(items.options[item].wPort, SHOT_LEFT_SIDEKICK, x, y, p.mouseX, p.mouseY, items.options[item].wpNum, 1);
    }
  }

  if (items.options[p.items.sidekick[RIGHT_SIDEKICK]].tr === 2) {
    p.sidekick[RIGHT_SIDEKICK].x = p.x;
    p.sidekick[RIGHT_SIDEKICK].y = Math.max(10, p.y - 20);
  } else {
    p.sidekick[RIGHT_SIDEKICK].x = 72 + 15;
    p.sidekick[RIGHT_SIDEKICK].y = 120;
  }

  if (items.options[p.items.sidekick[RIGHT_SIDEKICK]].wPort > 0) {
    if (g.shotRepeat[SHOT_RIGHT_SIDEKICK] > 0) {
      --g.shotRepeat[SHOT_RIGHT_SIDEKICK];
    } else {
      const item = p.items.sidekick[RIGHT_SIDEKICK];
      const x = p.sidekick[RIGHT_SIDEKICK].x,
        y = p.sidekick[RIGHT_SIDEKICK].y;

      player_shot_create(items.options[item].wPort, SHOT_RIGHT_SIDEKICK, x, y, p.mouseX, p.mouseY, items.options[item].wpNum, 1);
    }
  }

  simulate_player_shots();

  // blit_sprite(VGAScreenSeg, 0, 0, OPTION_SHAPES, 12); // upgrade interface: the shop's HTML

  /*========================Power Bar=========================*/

  g.power = (g.power + g.powerAdd) >>> 0; // uint
  if (g.power > 900) g.power = 900;

  // The bar's pixels are the host's (weaponSimPower); the C ends with lastPower = its top row.
  g.lastPower = 147 - Math.trunc(g.power / 10);
}

