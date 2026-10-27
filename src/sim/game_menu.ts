// Port of the rules of OpenTyrian src/game_menu.c: JE_itemScreen, the screen the episode script
// shows between levels (`]I[`), where the player buys and sells gear and picks the next level.
//
// JE_itemScreen is one loop that redraws, waits for input and handles it. Here it's split so a
// host can drive it from its own UI without blocking:
//   JE_itemScreen_init()      everything before the loop (merge last_items into the lists, sort)
//   JE_itemScreen_update()    the state half of the loop's top (the item under the cursor in an
//                             upgrade submenu, power-level arrows, ...). Call after init and after
//                             each input, unless JE_itemScreen_done().
//   JE_itemScreen_key(k)      the keyboard handler (arrows, Enter/Space, Escape, '/')
//   JE_itemScreen_mouse(sel)  the mouse handler for a click on menu row `sel` (C's selection
//                             numbers: 2 is the first row)
//   JE_itemScreen_done()      the loop's exit test: quit || gameLoaded || jumpSection
// The host reads `menu` and the view helpers below to draw, plays menu.sounds, answers
// menu.quitRequest (JE_quitRequest is a dialog) and shows ship specs when menu.shipSpecsRequest.
//
// Ported: the full-game menu, Upgrade Ship and its submenus (prices, trade-in, weapon power
// up/downgrades, the rear weapon's firing mode), Play Next Level (the navigation choices and
// JE_computeDots), Quit, and the arcade/Super Tyrian menus' "play next level" and quit.
// Not ported (no-ops): Data Cubes, Options (load/save, keyboard and joystick setup, volume),
// network play, and drawing. The weapon simulator (JE_initWeaponView/JE_weaponSimUpdate) is in
// weaponSim.ts, which the host runs beside this state (src/app/weaponPreview.ts).

import { u8 } from "./cint";
import { JE_getCost } from "./mainint";
import { copyPlayerItems } from "./player";
import { S_CLICK, S_CLINK, S_CURSOR, S_ITEM, S_SPRING } from "./sndmast";
import { g, newPlayerItems, REAR_WEAPON, type PlayerItems } from "./state";
import { JE_getShipInfo } from "./varz";

export const MENU_FULL_GAME = 0;
export const MENU_UPGRADES = 1;
export const MENU_OPTIONS = 2;
export const MENU_PLAY_NEXT_LEVEL = 3;
export const MENU_UPGRADE_SUB = 4;
export const MENU_KEYBOARD_CONFIG = 5;
export const MENU_LOAD_SAVE = 6;
export const MENU_DATA_CUBES = 7;
export const MENU_DATA_CUBE_SUB = 8;
export const MENU_2_PLAYER_ARCADE = 9;
export const MENU_1_PLAYER_ARCADE = 10; // Also networked games.
export const MENU_LIMITED_OPTIONS = 11; // Hides save/load menus.
export const MENU_JOYSTICK_CONFIG = 12;
export const MENU_SUPER_TYRIAN = 13;
const MENU_MAX = 14;

/** config.h SAVE_FILES_NUM */
const SAVE_FILES_NUM = 11 * 2;

const menuChoicesDefault = [7, 9, 8, 0, 0, 11, SAVE_FILES_NUM / 2 + 2, 0, 0, 6, 4, 6, 7, 5];
const menuEsc = [0, 1, 1, 1, 2, 3, 3, 1, 8, 0, 0, 11, 3, 0];
/** Which itemAvail row (1-based) each Upgrade Ship choice (curSel[MENU_UPGRADES] - 2) sells from. */
export const itemAvailMap = [1, 2, 3, 9, 4, 6, 7];
/** Planet positions on the navigation map, [1..21]. */
export const planetX = [200, 150, 240, 300, 270, 280, 320, 260, 220, 150, 160, 210, 80, 240, 220, 180, 310, 330, 150, 240, 200];
export const planetY = [40, 90, 90, 80, 170, 30, 50, 130, 120, 150, 220, 200, 80, 50, 160, 10, 55, 55, 90, 90, 40];
/** varz.c PGR[21]: each planet's sprite in the planet table (1-based), and PAni: whether it animates (15 frames). */
export const PGR = [4, 1, 2, 3, 41 - 21, 57 - 21, 73 - 21, 89 - 21, 105 - 21, 121 - 21, 137 - 21, 153 - 21, 151, 151, 151, 151, 73 - 21, 73 - 21, 1, 2, 4];
export const PAni = [1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1];

/** The item screen's statics (game_menu.c L79-104), plus what the host needs to answer. */
export const menu = {
  curMenu: MENU_FULL_GAME,
  /** JE_byte curSel[MENU_MAX]: the cursor per menu; 2 is the first choice. */
  curSel: new Array<number>(MENU_MAX).fill(2),
  /** The last choice's number per menu (the cursor wraps from it to 2). */
  menuChoices: [...menuChoicesDefault],
  lastDirection: 0,
  lastCurSel: 0,
  /** In a weapon submenu: whether the power can go down / up, and whether the player can afford up. */
  leftPower: false,
  rightPower: false,
  rightPowerAfford: false,
  /** The loadout when the submenu opened (or at the last JE_menuFunction): Escape restores it. */
  old_items: newPlayerItems(),
  /**
   * JE_itemScreen's temp_weapon_power[7]: the power each weapon in the submenu shows, then "Done".
   * (The C array assumes at most 6 weapons per list; this one has room for a full row.)
   */
  temp_weapon_power: new Array<number>(12).fill(0),
  /** JE_computeDots: route dots from mapOrigin to each destination. */
  planetDots: new Array<number>(5).fill(0),
  planetDotX: Array.from({ length: 5 }, () => new Array<number>(10).fill(0)),
  planetDotY: Array.from({ length: 5 }, () => new Array<number>(10).fill(0)),
  /** menuInt[4]: the Next Level menu: title, planet names, then "back" (set by JE_menuFunction). */
  menuInt4: [] as string[],
  /** The host should show the quit dialog (JE_quitRequest) and call JE_itemScreen_quitAnswer. */
  quitRequest: false,
  /** The host should show Ship Specs (JE_doShipSpecs) for the current ship until a key is pressed. */
  shipSpecsRequest: false,
  /** JE_playSampleNum calls since the host last drained this. */
  sounds: [] as number[],
};

/** JE_playSampleNum: queued for the host. */
function JE_playSampleNum(samplenum: number): void {
  menu.sounds.push(samplenum);
}

/** playeritem_map (game_menu.c L117-131): items field i: ship, front, rear, shield, generator, left/right sidekick. */
export function playeritem_get(items: PlayerItems, i: number): number {
  switch (i) {
    case 0: return items.ship;
    case 1: return items.weapon[0].id;
    case 2: return items.weapon[1].id;
    case 3: return items.shield;
    case 4: return items.generator;
    case 5: return items.sidekick[0];
    case 6: return items.sidekick[1];
  }
  throw new Error(`playeritem_map: index ${i}`); // assert(i < COUNTOF(map))
}

function playeritem_set(items: PlayerItems, i: number, v: number): void {
  v = u8(v);
  switch (i) {
    case 0: items.ship = v; return;
    case 1: items.weapon[0].id = v; return;
    case 2: items.weapon[1].id = v; return;
    case 3: items.shield = v; return;
    case 4: items.generator = v; return;
    case 5: items.sidekick[0] = v; return;
    case 6: items.sidekick[1] = v; return;
  }
  throw new Error(`playeritem_map: index ${i}`);
}

/** The itemAvail row (0-based) the Upgrade Ship choice `sel` (2..8) sells from. */
const availRow = (sel: number): number => itemAvailMap[sel - 2] - 1;

/**
 * JE_cashLeft (game_menu.c L133-155): cash after paying for the item in the current Upgrade Ship
 * category and its power upgrades. The upgrades are summed in tempW, a JE_word, so they wrap.
 */
export function JE_cashLeft(): number {
  const { curSel } = menu;
  let tempL = g.player[0].cash;
  const itemNum = playeritem_get(g.player[0].items, curSel[MENU_UPGRADES] - 2);

  tempL -= JE_getCost(curSel[MENU_UPGRADES], itemNum);

  let tempW = 0;

  switch (curSel[MENU_UPGRADES]) {
    case 3:
    case 4:
      for (let i = 1; i < g.player[0].items.weapon[curSel[MENU_UPGRADES] - 3].power; ++i) {
        tempW = (tempW + g.res.items.weaponPorts[itemNum].cost * i) & 0xffff;
        tempL -= tempW;
      }
      break;
  }

  return tempL | 0; // JE_longint
}

/** JE_itemScreen (game_menu.c L157-268): set up the screen, before its loop. */
export function JE_itemScreen_init(): void {
  menu.menuChoices = [...menuChoicesDefault];

  // play_song(songBuy), JE_loadPic, palettes: the host's.

  g.gameLoaded = false;

  menu.curSel.fill(2);

  menu.curMenu = MENU_FULL_GAME;

  menu.quitRequest = false;
  menu.shipSpecsRequest = false;

  /* JE: (* Check for where Pitems and Select match up - if no match then add to the itemavail list *) */
  for (let i = 0; i < 7; i++) {
    const item = playeritem_get(g.player[0].last_items, i);
    const row = itemAvailMap[i] - 1;

    let slot = 0;

    for (; slot < g.itemAvailMax[row]; ++slot) {
      if (g.itemAvail[row][slot] === item) break;
    }

    if (slot === g.itemAvailMax[row]) {
      g.itemAvail[row][slot] = item;
      g.itemAvailMax[row]++;
    }
  }

  /* JE: Sort items in merchant inventory */
  for (let x = 0; x < 9; x++) {
    const a = g.itemAvail[x];
    if (g.itemAvailMax[x] > 1) {
      for (let temp = 0; temp < g.itemAvailMax[x] - 1; temp++) {
        for (let temp2 = temp; temp2 < g.itemAvailMax[x]; temp2++) {
          if (a[temp] === 0 || (a[temp] > a[temp2] && a[temp2] !== 0)) {
            const temp3 = a[temp];
            a[temp] = a[temp2];
            a[temp2] = temp3;
          }
        }
      }
    }
  }
}

/** JE_itemScreen's loop condition: the screen is done (a destination was chosen, or the player quit). */
export function JE_itemScreen_done(): boolean {
  return g.gameLoaded || g.jumpSection;
}

/** The state half of the top of JE_itemScreen's loop (game_menu.c L270-302, L524-614, L776-783). */
export function JE_itemScreen_update(): void {
  const { curSel, menuChoices } = menu;
  const player = g.player;

  JE_getShipInfo();

  if (menu.curMenu === MENU_FULL_GAME) {
    if (g.twoPlayerMode) menu.curMenu = MENU_2_PLAYER_ARCADE;

    if (g.isNetworkGame || g.onePlayerAction) menu.curMenu = MENU_1_PLAYER_ARCADE;

    if (g.superTyrian) menu.curMenu = MENU_SUPER_TYRIAN;
  }

  menu.leftPower = false;
  menu.rightPower = false;

  if (menu.curMenu === MENU_UPGRADES && (curSel[menu.curMenu] === 3 || curSel[menu.curMenu] === 4)) {
    // reset temp_weapon_power[] every time we select upgrading front or back
    const item = player[0].items.weapon[curSel[MENU_UPGRADES] - 3].id,
      item_power = player[0].items.weapon[curSel[MENU_UPGRADES] - 3].power,
      row = availRow(curSel[MENU_UPGRADES]);

    // set power level of owned weapon
    for (let slot = 0; slot < g.itemAvailMax[row]; ++slot) {
      if (g.itemAvail[row][slot] === item) menu.temp_weapon_power[slot] = item_power;
      else menu.temp_weapon_power[slot] = 1;
    }

    // set power level for "Done"
    menu.temp_weapon_power[g.itemAvailMax[row]] = item_power;
  }

  // MENU_PLAY_NEXT_LEVEL: the navigation map's animation (JE_updateNavScreen) is the host's.

  if (menu.curMenu === MENU_UPGRADE_SUB) {
    const sel = curSel[MENU_UPGRADES];
    const row = availRow(sel);
    const avail = g.itemAvail[row];

    /* Move cursor until we hit either "Done" or a weapon the player can afford */
    while (curSel[MENU_UPGRADE_SUB] < menuChoices[MENU_UPGRADE_SUB] && JE_getCost(sel, avail[curSel[MENU_UPGRADE_SUB] - 2]) > player[0].cash) {
      curSel[MENU_UPGRADE_SUB] = u8(curSel[MENU_UPGRADE_SUB] + menu.lastDirection);
      if (curSel[MENU_UPGRADE_SUB] < 2) curSel[MENU_UPGRADE_SUB] = menuChoices[MENU_UPGRADE_SUB];
      else if (curSel[MENU_UPGRADE_SUB] > menuChoices[MENU_UPGRADE_SUB]) curSel[MENU_UPGRADE_SUB] = 2;
    }

    if (curSel[MENU_UPGRADE_SUB] === menuChoices[MENU_UPGRADE_SUB]) {
      /* If cursor on "Done", use previous weapon */
      playeritem_set(player[0].items, sel - 2, playeritem_get(menu.old_items, sel - 2));
    } else {
      /* Otherwise display the selected weapon */
      playeritem_set(player[0].items, sel - 2, avail[curSel[MENU_UPGRADE_SUB] - 2]);
    }

    /* Get power level info for front and rear weapons */
    if (
      (sel === 3 || sel === 4) && // front or rear weapon
      curSel[MENU_UPGRADE_SUB] < menuChoices[MENU_UPGRADE_SUB] && // not "Done"
      avail[curSel[MENU_UPGRADE_SUB] - 2] !== 0 // not "None"
    ) {
      const port = sel - 3, // 0 or 1 (front or back)
        item_level = player[0].items.weapon[port].power;

      // calculate upgradeCost
      JE_getCost(sel, avail[curSel[MENU_UPGRADE_SUB] - 2]);

      menu.leftPower = item_level > 1; // can downgrade
      menu.rightPower = item_level < 11; // can upgrade

      if (menu.rightPower) menu.rightPowerAfford = JE_cashLeft() >= g.upgradeCost; // can afford upgrade
    } else {
      /* Nothing else can be upgraded / downgraded */
      menu.leftPower = false;
      menu.rightPower = false;
    }
  }

  /* JE: {Reset player weapons} */
  g.shotMultiPos.fill(0);

  if (g.constantPlay) {
    g.mainLevel = u8(g.mapSection[g.mapPNum - 1]);
    g.jumpSection = true;
  }
}

/** Keyboard keys JE_itemScreen handles (SDL scancodes in the C). */
export type ItemScreenKey = "up" | "down" | "left" | "right" | "enter" | "esc" | "slash";

/** JE_itemScreen's keyboard handler (game_menu.c L1150-1585), for the menus this port has. */
export function JE_itemScreen_key(key: ItemScreenKey): void {
  const { curSel, menuChoices } = menu;
  const player = g.player;
  const curMenu = menu.curMenu;
  const weaponSub = curMenu === MENU_UPGRADE_SUB && (curSel[MENU_UPGRADES] === 3 || curSel[MENU_UPGRADES] === 4);

  switch (key) {
    case "slash":
      // if in rear weapon upgrade screen
      if (curMenu === MENU_UPGRADE_SUB && curSel[MENU_UPGRADES] === 4) {
        // cycle weapon modes
        player[0].weapon_mode = u8(player[0].weapon_mode + 1);
        if (player[0].weapon_mode > g.res.items.weaponPorts[player[0].items.weapon[REAR_WEAPON].id].opNum) player[0].weapon_mode = 1;
      }
      break;

    case "enter":
      // if front or rear weapon, update "Done" power level
      if (weaponSub)
        menu.temp_weapon_power[g.itemAvailMax[availRow(curSel[MENU_UPGRADES])]] = player[0].items.weapon[curSel[MENU_UPGRADES] - 3].power;

      JE_menuFunction(curSel[curMenu]);
      break;

    case "esc":
      JE_playSampleNum(S_SPRING);
      if (menuEsc[curMenu] === 0) {
        menu.quitRequest = true; // JE_quitRequest(): the host asks, then calls JE_itemScreen_quitAnswer
      } else {
        if (curMenu === MENU_UPGRADE_SUB) {
          // leaving upgrade menu without buying
          player[0].items = copyPlayerItems(menu.old_items);
          curSel[MENU_UPGRADE_SUB] = menu.lastCurSel;
          player[0].cash = JE_cashLeft();
        }

        menu.curMenu = menuEsc[curMenu] - 1;
      }
      break;

    case "up":
      menu.lastDirection = -1;

      if (curMenu !== MENU_DATA_CUBE_SUB) JE_playSampleNum(S_CURSOR);

      curSel[curMenu] = u8(curSel[curMenu] - 1);
      if (curSel[curMenu] < 2) curSel[curMenu] = menuChoices[curMenu];

      // if in front or rear weapon upgrade screen
      if (weaponSub) {
        player[0].items.weapon[curSel[MENU_UPGRADES] - 3].power = menu.temp_weapon_power[curSel[MENU_UPGRADE_SUB] - 2];
        if (curSel[MENU_UPGRADES] === 4) player[0].weapon_mode = 1;
      }
      break;

    case "down":
      menu.lastDirection = 1;

      if (curMenu !== MENU_DATA_CUBE_SUB) JE_playSampleNum(S_CURSOR);

      curSel[curMenu] = u8(curSel[curMenu] + 1);
      if (curSel[curMenu] > menuChoices[curMenu]) curSel[curMenu] = 2;

      // if in front or rear weapon upgrade screen
      if (weaponSub) {
        player[0].items.weapon[curSel[MENU_UPGRADES] - 3].power = menu.temp_weapon_power[curSel[MENU_UPGRADE_SUB] - 2];
        if (curSel[MENU_UPGRADES] === 4) player[0].weapon_mode = 1;
      }
      break;

    case "left":
      if (curMenu === MENU_UPGRADE_SUB) JE_playSampleNum(S_CURSOR);
      if (curMenu === MENU_UPGRADE_SUB) powerDown();
      break;

    case "right":
      if (curMenu === MENU_UPGRADE_SUB) JE_playSampleNum(S_CURSOR);
      if (curMenu === MENU_UPGRADE_SUB) powerUp();
      break;
  }
}

/** case 4 of the LEFT handler: lower the weapon's power (refunds its upgrade). */
function powerDown(): void {
  const { curSel } = menu;
  switch (curSel[MENU_UPGRADES]) {
    case 3:
    case 4:
      if (menu.leftPower)
        g.player[0].items.weapon[curSel[MENU_UPGRADES] - 3].power = --menu.temp_weapon_power[curSel[MENU_UPGRADE_SUB] - 2];
      else JE_playSampleNum(S_CLINK);
      break;
  }
}

/** case 4 of the RIGHT handler: raise the weapon's power, if affordable. */
function powerUp(): void {
  const { curSel } = menu;
  switch (curSel[MENU_UPGRADES]) {
    case 3:
    case 4:
      if (menu.rightPower && menu.rightPowerAfford)
        g.player[0].items.weapon[curSel[MENU_UPGRADES] - 3].power = ++menu.temp_weapon_power[curSel[MENU_UPGRADE_SUB] - 2];
      else JE_playSampleNum(S_CLINK);
      break;
  }
}

/**
 * JE_itemScreen's mouse handler (game_menu.c L963-1147) for a click on menu row `selection` (2 is
 * the first row, as the C computes from the click's y), or on a weapon power arrow.
 */
export function JE_itemScreen_mouse(selection: number | "powerDown" | "powerUp"): void {
  const { curSel, menuChoices } = menu;
  const curMenu = menu.curMenu;

  menu.lastDirection = 1;

  if (selection === "powerDown" || selection === "powerUp") {
    if (curMenu === MENU_UPGRADE_SUB && (curSel[MENU_UPGRADES] === 3 || curSel[MENU_UPGRADES] === 4)) {
      JE_playSampleNum(S_CURSOR);
      if (selection === "powerDown") powerDown();
      else powerUp();
    }
    return;
  }

  if (selection <= menuChoices[curMenu]) {
    if (curMenu === MENU_UPGRADE_SUB && selection === menuChoices[MENU_UPGRADE_SUB]) {
      g.player[0].cash = JE_cashLeft();
      menu.curMenu = MENU_UPGRADES;
      JE_playSampleNum(S_ITEM);
    } else {
      JE_playSampleNum(S_CLICK);
      if (curSel[curMenu] === selection) {
        JE_menuFunction(curSel[curMenu]);
      } else {
        if (curMenu === MENU_UPGRADE_SUB && JE_getCost(curSel[MENU_UPGRADES], g.itemAvail[availRow(curSel[MENU_UPGRADES])][selection - 2]) > g.player[0].cash) {
          JE_playSampleNum(S_CLINK);
        } else {
          if (curSel[MENU_UPGRADES] === 4) g.player[0].weapon_mode = 1;

          curSel[curMenu] = selection;
        }

        // in front or rear weapon upgrade screen?
        if (curMenu === MENU_UPGRADE_SUB && (curSel[MENU_UPGRADES] === 3 || curSel[MENU_UPGRADES] === 4)) {
          g.player[0].items.weapon[curSel[MENU_UPGRADES] - 3].power = menu.temp_weapon_power[curSel[MENU_UPGRADE_SUB] - 2];
        }
      }
    }
  }
}

/** The end of JE_quitRequest (game_menu.c L2360-2462) and its callers: `quit` is the player's answer. */
export function JE_itemScreen_quitAnswer(quit: boolean): void {
  menu.quitRequest = false;
  JE_playSampleNum(quit ? S_SPRING : S_CLICK);
  if (quit) {
    g.gameLoaded = true;
    g.mainLevel = 0;
  }
}

/** JE_genItemMenu (game_menu.c L2464-2506): the submenu for Upgrade Ship choice itemNum (2..8). */
export function JE_genItemMenu(itemNum: number): void {
  const row = availRow(itemNum);
  menu.menuChoices[MENU_UPGRADE_SUB] = g.itemAvailMax[row] + 2;

  let temp3 = 2;
  const temp2 = playeritem_get(g.player[0].items, itemNum - 2);

  // (The C also copies the item names into menuInt[5]; itemScreenEntries builds them.)
  for (let tempW = 0; tempW < g.itemAvailMax[row]; tempW++) {
    if (g.itemAvail[row][tempW] === temp2) temp3 = tempW + 2;
  }

  menu.curSel[MENU_UPGRADE_SUB] = temp3;
}

/** JE_menuFunction (game_menu.c L2540-2986), for the menus this port has. */
export function JE_menuFunction(select: number): void {
  const { curSel, menuChoices } = menu;
  const player = g.player;

  JE_playSampleNum(S_CLICK);

  const curSelect = curSel[menu.curMenu];

  switch (menu.curMenu) {
    case MENU_FULL_GAME:
      switch (select) {
        case 2: // cubes
          // Data cubes: not ported.
          break;
        case 3: // shipspecs
          menu.shipSpecsRequest = true; // JE_doShipSpecs(): the host shows it
          JE_playSampleNum(S_SPRING);
          break;
        case 4: // upgradeship
          menu.curMenu = MENU_UPGRADES;
          break;
        case 5: // options
          // Options: not ported.
          break;
        case 6: {
          // nextlevel
          menu.curMenu = MENU_PLAY_NEXT_LEVEL;
          JE_computeDots();
          menuChoices[MENU_PLAY_NEXT_LEVEL] = g.mapPNum + 2;
          curSel[MENU_PLAY_NEXT_LEVEL] = 2;
          menu.menuInt4 = ["Next Level"];
          let x = 0;
          for (; x < g.mapPNum; x++) {
            const temp = g.mapPlanet[x];
            menu.menuInt4[x + 1] = g.pName[temp - 1];
          }
          menu.menuInt4[x + 1] = g.miscText[5];
          break;
        }
        case 7: // quit
          menu.quitRequest = true;
          break;
      }
      break;

    case MENU_UPGRADES:
      if (select === 9) {
        // done
        menu.curMenu = MENU_FULL_GAME;
      } else {
        // selected item to upgrade
        menu.old_items = copyPlayerItems(player[0].items);

        menu.lastDirection = 1;
        JE_genItemMenu(select);
        // JE_initWeaponView(): weaponSim_sync runs it when it sees the submenu open (weaponSim.ts).
        menu.curMenu = MENU_UPGRADE_SUB;
        menu.lastCurSel = curSel[MENU_UPGRADE_SUB];
        player[0].cash = player[0].cash * 2 - JE_cashLeft();
      }
      break;

    case MENU_PLAY_NEXT_LEVEL:
      if (select === menuChoices[MENU_PLAY_NEXT_LEVEL]) {
        // exit
        menu.curMenu = MENU_FULL_GAME;
      } else {
        g.mainLevel = u8(g.mapSection[curSelect - 2]);
        g.jumpSection = true;
      }
      break;

    case MENU_UPGRADE_SUB:
      if (curSel[MENU_UPGRADE_SUB] < menuChoices[MENU_UPGRADE_SUB]) {
        // select done
        curSel[MENU_UPGRADE_SUB] = menuChoices[MENU_UPGRADE_SUB];
      } else {
        // if done is selected
        JE_playSampleNum(S_ITEM);

        player[0].cash = JE_cashLeft();
        menu.curMenu = MENU_UPGRADES;
      }
      break;

    case MENU_2_PLAYER_ARCADE:
    case MENU_1_PLAYER_ARCADE:
    case MENU_SUPER_TYRIAN: {
      // The "play next level" and quit choices; the others (options, input devices, ship specs) aren't ported.
      const quitChoice = menu.curMenu === MENU_2_PLAYER_ARCADE ? 6 : menu.curMenu === MENU_1_PLAYER_ARCADE ? 4 : 5;
      if (curSel[menu.curMenu] === 2) {
        g.mainLevel = u8(g.mapSection[g.mapPNum - 1]);
        g.jumpSection = true;
      } else if (curSel[menu.curMenu] === quitChoice) {
        menu.quitRequest = true;
      } else if (menu.curMenu === MENU_SUPER_TYRIAN && curSel[menu.curMenu] === 3) {
        menu.shipSpecsRequest = true;
        JE_playSampleNum(S_SPRING);
      }
      break;
    }
  }

  menu.old_items = copyPlayerItems(player[0].items);
}

/** JE_computeDots (game_menu.c L2259-2288): the dotted routes from mapOrigin to each destination. */
export function JE_computeDots(): void {
  const { planetDots, planetDotX, planetDotY } = menu;
  for (let x = 0; x < g.mapPNum; x++) {
    const distX = planetX[g.mapPlanet[x] - 1] - planetX[g.mapOrigin - 1];
    const distY = planetY[g.mapPlanet[x] - 1] - planetY[g.mapOrigin - 1];
    const tempX = Math.abs(distX) + Math.abs(distY);

    if (tempX !== 0) planetDots[x] = u8(roundfC(Math.fround(Math.sqrt(Math.fround(Math.sqrt(distX * distX + distY * distY))))) - 1);
    else planetDots[x] = 0;

    if (planetDots[x] > 10) planetDots[x] = 10;

    for (let y = 0; y < planetDots[x]; y++) {
      planetDotX[x][y] = JE_partWay(planetX[g.mapOrigin - 1], planetX[g.mapPlanet[x] - 1], planetDots[x], y);
      planetDotY[x][y] = JE_partWay(planetY[g.mapOrigin - 1], planetY[g.mapPlanet[x] - 1], planetDots[x], y);
    }
  }
}

/** C roundf (half away from zero). */
function roundfC(v: number): number {
  const r = Math.floor(Math.abs(v) + 0.5);
  return v < 0 ? -r : r;
}

/** JE_partWay (game_menu.c L2290-2293), in C integer arithmetic. */
export function JE_partWay(start: number, finish: number, dots: number, dist: number): number {
  return Math.trunc((finish - start) / (dots + 2)) * (dist + 1) + start;
}

/** JE_drawMainMenuHelpText (game_menu.c L2321-2358): the help line for the cursor's choice. */
export function JE_mainMenuHelpText(): string {
  const { curSel, menuChoices, curMenu } = menu;
  const temp = curSel[curMenu] - 2;

  if (curMenu < MENU_PLAY_NEXT_LEVEL || curMenu === MENU_2_PLAYER_ARCADE || curMenu > MENU_1_PLAYER_ARCADE) {
    return g.mainMenuHelp[menuHelp[curMenu][temp] - 1] ?? "";
  } else if (menu.leftPower || menu.rightPower) {
    return g.mainMenuHelp[24 - 1];
  } else if (temp === menuChoices[curMenu] - 2 || (curMenu === MENU_DATA_CUBES && g.cubeMax === 0)) {
    return g.mainMenuHelp[12 - 1];
  } else {
    return g.mainMenuHelp[17 + curMenu - 3];
  }
}

/** helptext.c menuHelp[MENU_MAX][11]: mainMenuHelp entries (1-based) per menu choice. */
const menuHelp = [
  [1, 34, 2, 3, 4, 5, 0, 0, 0, 0, 0],
  [6, 7, 8, 9, 10, 11, 11, 12, 0, 0, 0],
  [13, 14, 15, 15, 16, 17, 12, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [4, 30, 30, 3, 5, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [16, 17, 15, 15, 12, 0, 0, 0, 0, 0, 0],
  [31, 31, 31, 31, 32, 12, 0, 0, 0, 0, 0],
  [4, 34, 3, 5, 0, 0, 0, 0, 0, 0, 0],
];

// --- View helpers: what JE_itemScreen draws, as data ---

/** One row of the current menu. */
export interface ItemScreenEntry {
  /** C selection number (2 = first row). */
  sel: number;
  label: string;
  /** Upgrade submenus: the item id (0 = None), its "Cost:" and whether it's shown dimmed (cost > cash). */
  item?: number;
  cost?: number;
  unaffordable?: boolean;
  /** The item-owned marker: the item the player had when the submenu opened (not None). */
  owned?: boolean;
  /** The row is the menu's "Done"/"back" choice. */
  done?: boolean;
  /** A choice this port doesn't implement (Data Cubes, Options, ...). */
  unavailable?: boolean;
}

/** An item's name as the submenu shows it (game_menu.c L640-662). itemType is the Upgrade Ship choice (2..8). */
export function itemName(itemType: number, id: number): string {
  const { items } = g.res;
  switch (itemType) {
    case 2: return id > 90 ? `Custom Ship ${id - 90}` : items.ships[id].name;
    case 3:
    case 4: return items.weaponPorts[id].name;
    case 5: return items.shields[id].name;
    case 6: return items.powerSys[id].name;
    case 7:
    case 8: return items.options[id].name;
  }
  return "";
}

/** The current menu's title (JE_drawMenuHeader, and the submenu title). */
export function JE_menuHeader(): string {
  const { curMenu, curSel } = menu;
  if (curMenu === MENU_UPGRADE_SUB) return g.menuInt[2][curSel[MENU_UPGRADES] - 1] ?? "";
  if (curMenu === MENU_PLAY_NEXT_LEVEL) return menu.menuInt4[0] ?? "";
  return g.menuInt[curMenu + 1]?.[0] ?? "";
}

/** The current menu's rows (JE_drawMenuChoices, and the submenu list at game_menu.c L616-701). */
export function itemScreenEntries(): ItemScreenEntry[] {
  const { curMenu, curSel, menuChoices } = menu;
  const out: ItemScreenEntry[] = [];

  if (curMenu === MENU_UPGRADE_SUB) {
    const sel = curSel[MENU_UPGRADES];
    const row = availRow(sel);
    for (let tempW = 1; tempW < menuChoices[curMenu]; tempW++) {
      if (tempW === menuChoices[curMenu] - 1) {
        out.push({ sel: tempW + 1, label: g.miscText[13], done: true });
        continue;
      }
      const temp = g.itemAvail[row][tempW - 1]; /* Item ID */
      const temp_cost = JE_getCost(sel, temp);
      out.push({
        sel: tempW + 1,
        label: itemName(sel, temp),
        item: temp,
        cost: temp_cost,
        unaffordable: temp_cost > g.player[0].cash,
        owned: temp === playeritem_get(menu.old_items, sel - 2) && temp !== 0,
      });
    }
    // JE_drawScore runs JE_cashLeft after the list, so upgradeCost/downgradeCost (which the
    // JE_getCost calls above overwrote) describe the item on display again.
    JE_cashLeft();
    return out;
  }

  const labels = curMenu === MENU_PLAY_NEXT_LEVEL ? menu.menuInt4 : (g.menuInt[curMenu + 1] ?? []);
  for (let x = 2; x <= menuChoices[curMenu]; x++) {
    const entry: ItemScreenEntry = { sel: x, label: labels[x - 1] ?? "" };
    if (curMenu === MENU_FULL_GAME && (x === 2 || x === 5)) entry.unavailable = true;
    if (curMenu === MENU_UPGRADES && x === 9) entry.done = true;
    if (curMenu === MENU_PLAY_NEXT_LEVEL && x === menuChoices[curMenu]) entry.done = true;
    if (curMenu === MENU_1_PLAYER_ARCADE && x === 3) entry.unavailable = true;
    if (curMenu === MENU_2_PLAYER_ARCADE && (x === 3 || x === 4 || x === 5)) entry.unavailable = true;
    if (curMenu === MENU_SUPER_TYRIAN && x === 4) entry.unavailable = true;
    out.push(entry);
  }
  return out;
}

/** The cash figure the screen shows: JE_cashLeft() in a submenu (JE_drawScore), else the player's cash. */
export function itemScreenCash(): number {
  return menu.curMenu === MENU_UPGRADE_SUB ? JE_cashLeft() : g.player[0].cash;
}

/**
 * Non-interactive item screen: what JE_itemScreen does when nobody is choosing (the C's
 * constantPlay branch): set up, then go to the last destination the script lists. loadLevel
 * uses it by default so tests and tools can play through an episode.
 */
export function JE_itemScreenNonInteractive(): void {
  JE_itemScreen_init();
  JE_itemScreen_update();
  if (!JE_itemScreen_done()) {
    if (g.mapPNum < 1) throw new Error("item screen without navigation choices (]G[)");
    g.mainLevel = u8(g.mapSection[g.mapPNum - 1]);
    g.jumpSection = true;
  }
}
