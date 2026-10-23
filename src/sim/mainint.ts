// Port of the gameplay parts of OpenTyrian src/mainint.c: new-game player data, the per-tick
// player movement/firing/drawing (JE_playerMovement), JE_mainGamePlayerFunctions, player-vs-enemy
// collisions and pick-ups (JE_playerCollide), the message bar (JE_drawTextWindow), and item values
// (JE_getCost, JE_getValue, JE_totalScore) with the end-of-level bookkeeping (JE_endLevelAni).
//
// Not ported (menus, UI, or out of scope): JE_outCharGlow, JE_helpSystem, the high-score, setup,
// save/load and in-game menu screens, JE_endLevelAni's drawing, JE_playCredits, JE_mainKeyboardInput (cheats
// and debug keys; pause/menu are the host's job), JE_pauseGame, network play, demo playback and
// recording, chat. The HUD is HTML, so the C's HUD drawing (VGAScreenSeg: armor/shield/power bars,
// sidekick ammo gauges, port-config buttons) is left out; the state it reads is maintained.
//
// Draw keys (drawState.key) for the player's sprites, per player index p (0 or 1):
//   PLAYER_KEY_BASE + 100 * p + ...
//   0 ship (or left half of the two-sprite ship), 1 right half, 2/3 shadow halves, 4/5 superWild
//   shadows, 6 Nortship side spark sprite, 7 dragonwing charge indicator, 10..29 end-of-level warp
//   trail, 40/41 left/right sidekick.

import { fmul } from "./cfloat";
import { idiv, s16, s8, u16, u32, u8 } from "./cint";
import {
  blit_sprite2,
  blit_sprite2x2,
  blit_sprite2x2_blend,
  blit_sprite2x2_darken,
  drawGroup,
  drawState,
  type Sprite2Sheet,
} from "./draw";
import { simInput } from "./input";
import { mt_rand } from "./mtrand";
import { calc_purple_balls_needed, copyPlayerItems, handle_got_purple_ball, point_lives_at_weapon_power, power_up_weapon } from "./player";
import {
  cosf,
  player_shot_create,
  player_shot_set_direction,
  roundf,
  sinf,
  SHOT_FRONT,
  SHOT_LEFT_SIDEKICK,
  SHOT_MISC,
  SHOT_NORTSPARKS,
  SHOT_P1_SUPERBOMB,
  SHOT_P2_CHARGE,
  SHOT_REAR,
  SHOT_RIGHT_SIDEKICK,
  SHOT_SPECIAL,
  SHOT_SPECIAL2,
} from "./shots";
import {
  S_CLINK,
  S_ENEMY_HIT,
  S_EXPLOSION_11,
  S_EXPLOSION_4,
  S_EXPLOSION_9,
  S_ITEM,
  S_POWERUP,
  S_WEAPON_26,
  V_DATA_CUBE,
} from "./sndmast";
import {
  all_players_dead,
  DIFFICULTY_EASY,
  DIFFICULTY_IMPOSSIBLE,
  DIFFICULTY_INSANITY,
  DIFFICULTY_MANIACAL,
  DIFFICULTY_NORMAL,
  DIFFICULTY_NORTANEOUS,
  DIFFICULTY_SUICIDE,
  DIFFICULTY_ZINGLON,
  FRONT_WEAPON,
  g,
  LEFT_SIDEKICK,
  type Player,
  REAR_WEAPON,
  RIGHT_SIDEKICK,
  SA_NONE,
  SA_NORTSHIPZ,
} from "./state";
import {
  chargeGunWeapons,
  JE_doSpecialShot,
  JE_drawArmor,
  JE_drawOptions,
  JE_drawShield,
  JE_playerDamage,
  JE_portConfigs,
  JE_setupExplosion,
  JE_setupExplosionLarge,
  JE_wipeShieldArmorBars,
  keyboardCombos,
  linkGunWeapons,
  optionSelect,
  SASpecialWeapon,
  SASpecialWeaponB,
  SAWeapon,
  shadowYDist,
  shipCombos,
  shipCombosB,
  specialArcadeWeapon,
} from "./varz";
import { SPECIAL_NUM } from "../data";

/** config.h DIFFICULTY_HARD */
const DIFFICULTY_HARD = DIFFICULTY_NORMAL + 1;
/** episodes.h FIRST_LEVEL */
const FIRST_LEVEL = 1;
/** varz.h CURRENT_KEY_SPEED: keyboard/joystick movement rate */
const CURRENT_KEY_SPEED = 1;

const M_PI = Math.PI;
const M_PI_2 = Math.PI / 2;

/** Draw keys for the player's sprites (see the header comment). */
export const PLAYER_KEY_BASE = 10000;
const playerKey = (playerNum_: number, part: number): number => PLAYER_KEY_BASE + 100 * (playerNum_ - 1) + part;

/** network.c moveOk (a global; persists between calls). */
let moveOk = false;

/** mainint.c L76-83: shows a message in the bottom text window. The host's HUD shows g.messageText while g.textErase > 0. */
export function JE_drawTextWindow(text: string): void {
  // if (textErase > 0) erase current text: blit_sprite(VGAScreenSeg, 16, 189, OPTION_SHAPES, 36);
  g.textErase = 100;
  g.messageText = text; // JE_outText(VGAScreenSeg, 20, 190, text, 0, 4);
}

/** mainint.c L1014-1061: new game items and data. */
export function JE_initPlayerData(): void {
  const player = g.player;

  /* JE: New Game Items/Data */

  player[0].items.ship = 1; // USP Talon
  player[0].items.weapon[FRONT_WEAPON].id = 1; // Pulse Cannon
  player[0].items.weapon[REAR_WEAPON].id = 0; // None
  player[0].items.shield = 4; // Gencore High Energy Shield
  player[0].items.generator = 2; // Advanced MR-12
  for (let i = 0; i < player[0].items.sidekick.length; ++i) player[0].items.sidekick[i] = 0; // None
  player[0].items.special = 0; // None

  player[0].last_items = copyPlayerItems(player[0].items);

  player[1].items = copyPlayerItems(player[0].items);
  player[1].items.weapon[REAR_WEAPON].id = 15; // Vulcan Cannon
  player[1].items.sidekick_level = 101; // 101, 102, 103
  player[1].items.sidekick_series = 0; // None

  g.gameHasRepeated = false;
  g.onePlayerAction = false;
  g.superArcadeMode = SA_NONE;
  g.superTyrian = false;
  g.twoPlayerMode = false;

  g.secretHint = (mt_rand() % 3) + 1;

  for (let p = 0; p < player.length; ++p) {
    for (let i = 0; i < player[p].items.weapon.length; ++i) {
      player[p].items.weapon[i].power = 1;
    }

    player[p].weapon_mode = 1;
    player[p].armor = g.res.items.ships[player[p].items.ship].dmg;

    player[p].is_dragonwing = p === 1;
    point_lives_at_weapon_power(player[p], p); // player[p].lives = &player[p].items.weapon[p].power;
  }

  g.mainLevel = FIRST_LEVEL;
  g.saveLevel = FIRST_LEVEL;

  g.lastLevelName = g.miscText[19];
}

/** mainint.c L2228-2315: "Street-Fighter" twiddle codes. */
export function JE_SFCodes(playerNum_: number, PX_: number, PY_: number, mouseX_: number, mouseY_: number): void {
  PX_ = s16(PX_);
  PY_ = s16(PY_);
  mouseX_ = s16(mouseX_);
  mouseY_ = s16(mouseY_);
  let temp: number, temp2: number, temp4: number, temp5: number; // JE_byte

  let ship = g.player[playerNum_ - 1].items.ship;

  /*Get direction*/
  if (playerNum_ === 2 && ship < 15) {
    ship = 0;
  }

  if (ship < 15) {
    const b = (v: boolean) => (v ? 1 : 0);
    temp2 =
      b(mouseY_ > PY_) /*UP*/ +
      b(mouseY_ < PY_) /*DOWN*/ +
      b(PX_ < mouseX_) /*LEFT*/ +
      b(PX_ > mouseX_); /*RIGHT*/
    temp =
      b(mouseY_ > PY_) * 1 /*UP*/ +
      b(mouseY_ < PY_) * 2 /*DOWN*/ +
      b(PX_ < mouseX_) * 3 /*LEFT*/ +
      b(PX_ > mouseX_) * 4; /*RIGHT*/

    if (temp === 0) {
      // no direction being pressed
      if (!g.button[0]) {
        // if fire button is released
        temp = 9;
        temp2 = 1;
      } else {
        temp2 = 0;
        temp = 99;
      }
    }

    if (temp2 === 1) {
      // if exactly one direction pressed or fire button is released
      temp = u8(temp + b(g.button[0]) * 4);

      const temp3 = g.superTyrian ? 21 : 3;
      const code = g.SFCurrentCode[playerNum_ - 1];
      for (temp2 = 0; temp2 < temp3; temp2++) {
        /*Use SuperTyrian ShipCombos or not?*/
        temp5 = g.superTyrian ? shipCombosB[temp2] : shipCombos[ship][temp2];

        // temp5 == selected combo in ship
        if (temp5 === 0) {
          /* combo doesn't exists */
          // mark twiddles as cancelled/finished
          code[temp2] = 0;
        } else {
          // get next combo key
          temp4 = keyboardCombos[temp5 - 1][code[temp2]];

          // correct key
          if (temp4 === temp) {
            code[temp2] = u8(code[temp2] + 1);

            temp4 = keyboardCombos[temp5 - 1][code[temp2]];
            if (temp4 > 100 && temp4 <= 100 + SPECIAL_NUM) {
              code[temp2] = 0;
              g.SFExecuted[playerNum_ - 1] = temp4 - 100;
            }
          } else {
            if (
              temp !== 9 &&
              (temp4 - 1) % 4 !== (temp - 1) % 4 &&
              (code[temp2] === 0 || keyboardCombos[temp5 - 1][code[temp2] - 1] !== temp)
            ) {
              code[temp2] = 0;
            }
          }
        }
      }
    }
  }
}

/**
 * mainint.c L2848-2917. Everything it does is HUD drawing (cash, special icon, lives, superbombs,
 * "Cheaters always prosper."), which the HTML HUD reads straight from g.player[*] (cash,
 * items.special, lives.value, superbombs) and g.youAreCheating. It maintains no state.
 */
export function JE_inGameDisplays(): void {}

/** JE_drawPortConfigButtons (mainint.c): HUD only. */
export function JE_drawPortConfigButtons(): void {}

/** mainint.c L4465-4473 (network names aren't ported). */
export function JE_getName(pnum: number): string {
  return g.miscText[47 + pnum];
}

/**
 * The two 24x28 halves of a two-sprite ship (shipGraphic 0, and 1 = the Nort ship), left at x - 17
 * and right at x + 7, recorded as one object so a model can replace both (DECISIONS.md D15). The
 * group key is the left half's sprite; the centre is (x + 7, y + 7).
 */
function blitShipHalves(x: number, y: number, sheet: Sprite2Sheet, left: number, right: number, blend: boolean, leftKey: number, rightKey: number): void {
  const blit = blend ? blit_sprite2x2_blend : blit_sprite2x2;
  drawGroup.index = left;
  drawGroup.size = 2;
  drawGroup.dy = 14;
  drawGroup.dx = 24;
  drawGroup.first = true;
  drawState.key = leftKey;
  blit(x - 17, y - 7, sheet, left);
  drawGroup.dx = 0;
  drawGroup.first = false;
  drawState.key = rightKey;
  blit(x + 7, y - 7, sheet, right);
  drawGroup.index = -1;
}

/**
 * mainint.c L3270-4403: input, movement, firing, sidekicks and drawing for one player.
 * `mouseX_`/`mouseY_` in the C always point at this_player->mouseX/mouseY, so the port uses
 * those fields directly. Input comes from simInput (src/sim/input.ts).
 */
export function JE_playerMovement(
  this_player: Player,
  inputDevice: number,
  playerNum_: number,
  shipGr_: number,
  shipGrPtr_: Sprite2Sheet | null,
): void {
  const items = g.res.items;
  const button = g.button;
  const savedKey = drawState.key;
  const sheet = shipGrPtr_ as Sprite2Sheet;

  let mouseXC: number, mouseYC: number; // JE_integer
  let accelXC: number, accelYC: number;

  if (playerNum_ === 2 || !g.twoPlayerMode) {
    const tempW = items.weaponPorts[this_player.items.weapon[REAR_WEAPON].id].opNum;

    if (this_player.weapon_mode > tempW) this_player.weapon_mode = 1;
  }

  // (network state packet prep: not ported)

  let link_gun_analog = false;
  let link_gun_angle = 0;

  // redo: (the C jumps back here after a respawn)
  for (;;) {
    if (g.isNetworkGame) {
      inputDevice = 0;
    }

    mouseXC = 0;
    mouseYC = 0;
    accelXC = 0;
    accelYC = 0;

    link_gun_analog = false;
    link_gun_angle = 0;

    /* Draw Player */
    if (!this_player.is_alive) {
      if (this_player.exploding_ticks > 0) {
        --this_player.exploding_ticks;

        if (g.levelEndFxWait > 0) {
          g.levelEndFxWait--;
        } else {
          g.levelEndFxWait = (mt_rand() % 6) + 3;
          if (mt_rand() % 3 === 1) g.soundQueue[6] = S_EXPLOSION_9;
          else g.soundQueue[5] = S_EXPLOSION_11;
        }

        const explosion_x = this_player.x + (mt_rand() % 32) - 16;
        const explosion_y = this_player.y + (mt_rand() % 32) - 16;
        JE_setupExplosionLarge(false, 0, explosion_x, explosion_y + 7);
        JE_setupExplosionLarge(false, 0, this_player.x, this_player.y + 7);

        if (g.levelEnd > 0) g.levelEnd--;
      } else {
        if (g.twoPlayerMode || g.onePlayerAction) {
          // if arcade mode
          if (this_player.lives.value > 1) {
            // respawn if any extra lives
            --this_player.lives.value;

            g.reallyEndLevel = false;
            g.shotMultiPos[playerNum_ - 1] = 0;
            calc_purple_balls_needed(this_player);
            g.twoPlayerLinked = false;
            if (g.galagaMode) g.twoPlayerMode = false;
            this_player.y = 160;
            this_player.invulnerable_ticks = 100;
            this_player.is_alive = true;
            g.endLevel = false;

            if (g.galagaMode || g.episodeNum === 4) this_player.armor = this_player.initial_armor;
            else this_player.armor = idiv(this_player.initial_armor, 2);

            if (g.galagaMode) this_player.shield = 0;
            else this_player.shield = idiv(this_player.shield_max, 2);

            JE_drawArmor();
            JE_drawShield();
            continue; // goto redo;
          } else {
            if (g.galagaMode) g.twoPlayerMode = false;
            if (g.allPlayersGone && g.isNetworkGame) g.reallyEndLevel = true;
          }
        }
      }
    } else if (g.constantDie) {
      // finished exploding?  start dying again
      if (this_player.exploding_ticks === 0) {
        this_player.shield = 0;

        if (this_player.armor > 0) {
          --this_player.armor;
        } else {
          this_player.is_alive = false;
          this_player.exploding_ticks = 60;
          g.levelEnd = 40;
        }

        JE_wipeShieldArmorBars();
        JE_drawArmor();

        // as if instant death weren't enough, player also gets infinite lives in order to enjoy an infinite number of deaths -_-
        if (g.player[0].lives.value < 11) ++g.player[0].lives.value;
      }
    }
    break;
  }

  if (!this_player.is_alive) {
    g.explosionFollowAmountX = g.explosionFollowAmountY = 0;
    return;
  }

  if (!g.endLevel) {
    this_player.mouseX = u16(this_player.x);
    this_player.mouseY = u16(this_player.y);
    button[1 - 1] = false;
    button[2 - 1] = false;
    button[3 - 1] = false;
    button[4 - 1] = false;

    /* --- Movement Routine Beginning --- */

    if (!g.isNetworkGame /* || playerNum_ == thisPlayerNum */) {
      if (g.endLevel) {
        this_player.y -= 2;
      } else {
        if (g.playDemo || g.recordDemo) inputDevice = 1; // keyboard is required device for demo recording

        // demo playback input: not ported (playDemoKeys)

        /* joystick input */
        // The host folds a gamepad's d-pad and buttons into simInput's keys (the C's digital
        // joystick moves exactly like the keyboard), and its analog stick into analogX/Y.
        if (inputDevice === 0 || inputDevice >= 3) {
          mouseXC += simInput.analogX;
          mouseYC += simInput.analogY;
        }

        /* mouse input */
        if (inputDevice === 0 || inputDevice === 2) {
          button[0] ||= simInput.mouseLeft;
          button[1] ||= simInput.mouseRight;
          button[2] ||= simInput.mouseMiddle;

          mouseXC += simInput.mouseXR;
          mouseYC += simInput.mouseYR;
        }

        /* keyboard input */
        if ((inputDevice === 0 || inputDevice === 1) && !g.playDemo) {
          if (simInput.up) this_player.y -= CURRENT_KEY_SPEED;
          if (simInput.down) this_player.y += CURRENT_KEY_SPEED;

          if (simInput.left) this_player.x -= CURRENT_KEY_SPEED;
          if (simInput.right) this_player.x += CURRENT_KEY_SPEED;

          button[0] ||= simInput.fire;
          button[3] ||= simInput.changeFire;
          button[1] ||= simInput.leftSidekick;
          button[2] ||= simInput.rightSidekick;

          if (g.constantPlay) {
            for (let i = 0; i < 4; i++) button[i] = true;

            ++this_player.y;
            this_player.x += g.constantLastX;
          }

          // if (recordDemo) recordDemoKeys(); (not ported)
        }

        if (g.smoothies[9 - 1]) {
          this_player.mouseY = u16(this_player.y - (this_player.mouseY - this_player.y));
          mouseYC = -mouseYC;
        }

        accelXC += this_player.x - this_player.mouseX;
        accelYC += this_player.y - this_player.mouseY;

        if (mouseXC > 30) mouseXC = 30;
        else if (mouseXC < -30) mouseXC = -30;
        if (mouseYC > 30) mouseYC = 30;
        else if (mouseYC < -30) mouseYC = -30;

        if (mouseXC > 0) this_player.x += idiv(mouseXC + 3, 4);
        else if (mouseXC < 0) this_player.x += idiv(mouseXC - 3, 4);
        if (mouseYC > 0) this_player.y += idiv(mouseYC + 3, 4);
        else if (mouseYC < 0) this_player.y += idiv(mouseYC - 3, 4);

        if (mouseXC > 3) accelXC++;
        else if (mouseXC < -2) accelXC--;
        if (mouseYC > 2) accelYC++;
        else if (mouseYC < -2) accelYC--;
      } /*endLevel*/

      // (network: send state; not ported)
    } /*isNetworkGame*/

    /* --- Movement Routine Ending --- */

    moveOk = true;

    // (network: apply remote state; not ported)

    /*Street-Fighter codes*/
    JE_SFCodes(playerNum_, this_player.x, this_player.y, this_player.mouseX, this_player.mouseY);

    if (moveOk) {
      /* END OF MOVEMENT ROUTINES */

      /*Linking Routines*/

      if (
        g.twoPlayerMode && !g.twoPlayerLinked && this_player.x === this_player.mouseX && this_player.y === this_player.mouseY &&
        Math.abs(g.player[0].x - g.player[1].x) < 8 && Math.abs(g.player[0].y - g.player[1].y) < 8 &&
        g.player[0].is_alive && g.player[1].is_alive && !g.galagaMode
      ) {
        g.twoPlayerLinked = true;
      }

      if (playerNum_ === 1 && (button[3 - 1] || button[2 - 1]) && !g.galagaMode) g.twoPlayerLinked = false;

      if (
        g.twoPlayerMode && g.twoPlayerLinked && playerNum_ === 2 &&
        (this_player.x !== this_player.mouseX || this_player.y !== this_player.mouseY)
      ) {
        if (button[0]) {
          if (link_gun_analog) {
            g.linkGunDirec = Math.fround(link_gun_angle);
          } else {
            let tempR: number; // JE_real

            if (Math.abs(this_player.x - this_player.mouseX) > Math.abs(this_player.y - this_player.mouseY))
              tempR = this_player.x - this_player.mouseX > 0 ? M_PI_2 : M_PI + M_PI_2;
            else tempR = this_player.y - this_player.mouseY > 0 ? 0 : M_PI;
            tempR = Math.fround(tempR);

            if (Math.abs(Math.fround(g.linkGunDirec - tempR)) < Math.fround(0.3)) g.linkGunDirec = tempR;
            else if (g.linkGunDirec < tempR && Math.fround(g.linkGunDirec - tempR) > Math.fround(-3.24))
              g.linkGunDirec = Math.fround(g.linkGunDirec + Math.fround(0.2));
            else if (Math.fround(g.linkGunDirec - tempR) < M_PI) g.linkGunDirec = Math.fround(g.linkGunDirec - Math.fround(0.2));
            else g.linkGunDirec = Math.fround(g.linkGunDirec + Math.fround(0.2));
          }

          if (g.linkGunDirec >= 2 * M_PI) g.linkGunDirec = Math.fround(g.linkGunDirec - 2 * M_PI);
          else if (g.linkGunDirec < 0) g.linkGunDirec = Math.fround(g.linkGunDirec + 2 * M_PI);
        } else if (!g.galagaMode) {
          g.twoPlayerLinked = false;
        }
      }
    }
  }

  if (g.levelEnd > 0 && all_players_dead()) g.reallyEndLevel = true;

  /* End Level Fade-Out */
  if (this_player.is_alive && g.endLevel) {
    if (g.levelEnd === 0) {
      g.reallyEndLevel = true;
    } else {
      this_player.y -= g.levelEndWarp;
      if (this_player.y < -200) g.reallyEndLevel = true;

      let trail_spacing = 1;
      let trail_y = this_player.y;
      let num_trails = Math.abs(41 - g.levelEnd);
      if (num_trails > 20) num_trails = 20;

      for (let i = 0; i < num_trails; i++) {
        trail_y += trail_spacing;
        trail_spacing++;
      }

      for (let i = 1; i < num_trails; i++) {
        trail_y -= trail_spacing;
        trail_spacing--;

        if (trail_y > 0 && trail_y < 170) {
          drawState.key = playerKey(playerNum_, 10 + i);
          if (shipGr_ === 0) {
            blitShipHalves(this_player.x, trail_y, sheet, 13, 51, false, drawState.key, drawState.key);
          } else if (shipGr_ === 1) {
            blitShipHalves(this_player.x, trail_y, sheet, 220, 222, false, drawState.key, drawState.key);
          } else {
            blit_sprite2x2(this_player.x - 5, trail_y - 7, sheet, shipGr_);
          }
        }
      }
    }
  }

  // if (playDemo) JE_dString(VGAScreen, 115, 10, miscText[7], SMALL_FONT_SHAPES); // insert coin

  if (this_player.is_alive && !g.endLevel) {
    if (!g.twoPlayerLinked || playerNum_ < 2) {
      if (!g.twoPlayerMode || g.shipGr2 !== 0) {
        // if not dragonwing
        if (this_player.sidekick[LEFT_SIDEKICK].style === 0) {
          this_player.sidekick[LEFT_SIDEKICK].x = this_player.mouseX - 14;
          this_player.sidekick[LEFT_SIDEKICK].y = this_player.mouseY;
        }

        if (this_player.sidekick[RIGHT_SIDEKICK].style === 0) {
          this_player.sidekick[RIGHT_SIDEKICK].x = this_player.mouseX + 16;
          this_player.sidekick[RIGHT_SIDEKICK].y = this_player.mouseY;
        }
      }

      if (this_player.x_friction_ticks > 0) {
        --this_player.x_friction_ticks;
      } else {
        this_player.x_friction_ticks = 1;

        if (this_player.x_velocity < 0) ++this_player.x_velocity;
        else if (this_player.x_velocity > 0) --this_player.x_velocity;
      }

      if (this_player.y_friction_ticks > 0) {
        --this_player.y_friction_ticks;
      } else {
        this_player.y_friction_ticks = 2;

        if (this_player.y_velocity < 0) ++this_player.y_velocity;
        else if (this_player.y_velocity > 0) --this_player.y_velocity;
      }

      this_player.x_velocity += accelXC;
      this_player.y_velocity += accelYC;

      this_player.x_velocity = Math.min(Math.max(-4, this_player.x_velocity), 4);
      this_player.y_velocity = Math.min(Math.max(-4, this_player.y_velocity), 4);

      this_player.x += this_player.x_velocity;
      this_player.y += this_player.y_velocity;

      // if player moved, add new ship x, y history entry
      if (this_player.x - this_player.mouseX !== 0 || this_player.y - this_player.mouseY !== 0) {
        const n = this_player.old_x.length;
        for (let i = 1; i < n; ++i) {
          this_player.old_x[i - 1] = this_player.old_x[i];
          this_player.old_y[i - 1] = this_player.old_y[i];
        }
        this_player.old_x[n - 1] = this_player.x;
        this_player.old_y[n - 1] = this_player.y;
      }
    } /*twoPlayerLinked*/ else {
      if (shipGr_ === 0) this_player.x = g.player[0].x - 1;
      else this_player.x = g.player[0].x;
      this_player.y = g.player[0].y + 8;

      this_player.x_velocity = g.player[0].x_velocity;
      this_player.y_velocity = 4;

      // turret direction marker/shield
      const d = g.linkGunDirec;
      const d_plus = Math.fround(d + Math.fround(0.2));
      const d_minus = Math.fround(d - Math.fround(0.2));
      g.shotMultiPos[SHOT_MISC] = 0;
      player_shot_create(0, SHOT_MISC, this_player.x + 1 + roundf(sinf(d_plus) * 26), this_player.y + roundf(cosf(d_plus) * 26), this_player.mouseX, this_player.mouseY, 148, playerNum_);
      g.shotMultiPos[SHOT_MISC] = 0;
      player_shot_create(0, SHOT_MISC, this_player.x + 1 + roundf(sinf(d_minus) * 26), this_player.y + roundf(cosf(d_minus) * 26), this_player.mouseX, this_player.mouseY, 148, playerNum_);
      g.shotMultiPos[SHOT_MISC] = 0;
      player_shot_create(0, SHOT_MISC, this_player.x + 1 + roundf(sinf(d) * 26), this_player.y + roundf(cosf(d) * 26), this_player.mouseX, this_player.mouseY, 147, playerNum_);

      if (g.shotRepeat[SHOT_REAR] > 0) {
        --g.shotRepeat[SHOT_REAR];
      } else if (button[1 - 1]) {
        g.shotMultiPos[SHOT_REAR] = 0;
        const b = player_shot_create(0, SHOT_REAR, this_player.x + 1 + roundf(sinf(d) * 20), this_player.y + roundf(cosf(d) * 20), this_player.mouseX, this_player.mouseY, linkGunWeapons[this_player.items.weapon[REAR_WEAPON].id - 1], playerNum_);
        player_shot_set_direction(b, this_player.items.weapon[REAR_WEAPON].id, g.linkGunDirec);
      }
    }
  }

  let ship_banking = 0;

  if (!g.endLevel) {
    if (this_player.x > 256) {
      this_player.x = 256;
      g.constantLastX = s8(-g.constantLastX);
    }
    if (this_player.x < 40) {
      this_player.x = 40;
      g.constantLastX = s8(-g.constantLastX);
    }

    if (g.isNetworkGame && playerNum_ === 1) {
      if (this_player.y > 154) this_player.y = 154;
    } else {
      if (this_player.y > 160) this_player.y = 160;
    }

    if (this_player.y < 10) this_player.y = 10;

    // Determines the ship banking sprite to display, depending on horizontal velocity and acceleration
    ship_banking = idiv(this_player.x_velocity, 2) + idiv(this_player.x - this_player.mouseX, 6);
    ship_banking = Math.max(-2, Math.min(ship_banking, 2));

    const ship_sprite = ship_banking * 2 + shipGr_;

    g.explosionFollowAmountX = s16(this_player.x - this_player.last_x_explosion_follow);
    g.explosionFollowAmountY = s16(this_player.y - this_player.last_y_explosion_follow);

    if (g.explosionFollowAmountY < 0) g.explosionFollowAmountY = 0;

    this_player.last_x_explosion_follow = this_player.x;
    this_player.last_y_explosion_follow = this_player.y;

    const shadow_x = this_player.x - g.mapX2Ofs + 30;
    const shadow_y = this_player.y - 7 + shadowYDist;
    if (shipGr_ === 0) {
      if (g.background2) {
        drawState.key = playerKey(playerNum_, 2);
        blit_sprite2x2_darken(shadow_x - 17, shadow_y, sheet, ship_sprite + 13);
        drawState.key = playerKey(playerNum_, 3);
        blit_sprite2x2_darken(shadow_x + 7, shadow_y, sheet, ship_sprite + 51);
        if (g.superWild) {
          drawState.key = playerKey(playerNum_, 4);
          blit_sprite2x2_darken(shadow_x - 16, shadow_y, sheet, ship_sprite + 13);
          drawState.key = playerKey(playerNum_, 5);
          blit_sprite2x2_darken(shadow_x + 6, shadow_y, sheet, ship_sprite + 51);
        }
      }
    } else if (shipGr_ === 1) {
      if (g.background2) {
        drawState.key = playerKey(playerNum_, 2);
        blit_sprite2x2_darken(shadow_x - 17, shadow_y, sheet, 220);
        drawState.key = playerKey(playerNum_, 3);
        blit_sprite2x2_darken(shadow_x + 7, shadow_y, sheet, 222);
      }
    } else {
      if (g.background2) {
        drawState.key = playerKey(playerNum_, 2);
        blit_sprite2x2_darken(shadow_x - 5, shadow_y, sheet, ship_sprite);
        if (g.superWild) {
          drawState.key = playerKey(playerNum_, 4);
          blit_sprite2x2_darken(shadow_x - 4, shadow_y, sheet, ship_sprite);
        }
      }
    }

    if (this_player.invulnerable_ticks > 0) {
      --this_player.invulnerable_ticks;

      if (shipGr_ === 0) {
        blitShipHalves(this_player.x, this_player.y, sheet, ship_sprite + 13, ship_sprite + 51, true, playerKey(playerNum_, 0), playerKey(playerNum_, 1));
      } else if (shipGr_ === 1) {
        blitShipHalves(this_player.x, this_player.y, sheet, 220, 222, true, playerKey(playerNum_, 0), playerKey(playerNum_, 1));
      } else {
        drawState.key = playerKey(playerNum_, 0);
        blit_sprite2x2_blend(this_player.x - 5, this_player.y - 7, sheet, ship_sprite);
      }
    } else {
      if (shipGr_ === 0) {
        blitShipHalves(this_player.x, this_player.y, sheet, ship_sprite + 13, ship_sprite + 51, false, playerKey(playerNum_, 0), playerKey(playerNum_, 1));
      } else if (shipGr_ === 1) {
        blitShipHalves(this_player.x, this_player.y, sheet, 220, 222, false, playerKey(playerNum_, 0), playerKey(playerNum_, 1));

        // (the C shadows ship_banking here with a new local)
        let nort_banking = 0;
        let tempW = 0; // JE_word
        drawState.key = playerKey(playerNum_, 6);
        switch (ship_sprite) {
          case 5:
            blit_sprite2(this_player.x - 17, this_player.y + 7, sheet, 40);
            tempW = u16(this_player.x - 7);
            nort_banking = -2;
            break;
          case 3:
            blit_sprite2(this_player.x - 17, this_player.y + 7, sheet, 39);
            tempW = u16(this_player.x - 7);
            nort_banking = -1;
            break;
          case 1:
            nort_banking = 0;
            break;
          case -1:
            blit_sprite2(this_player.x + 19, this_player.y + 7, sheet, 58);
            tempW = u16(this_player.x + 9);
            nort_banking = 1;
            break;
          case -3:
            blit_sprite2(this_player.x + 19, this_player.y + 7, sheet, 59);
            tempW = u16(this_player.x + 9);
            nort_banking = 2;
            break;
        }
        if (nort_banking !== 0) {
          // NortSparks
          if (g.shotRepeat[SHOT_NORTSPARKS] > 0) {
            --g.shotRepeat[SHOT_NORTSPARKS];
          } else {
            // C leaves argument evaluation order unspecified; this takes the x roll first.
            const spark_x = tempW + (mt_rand() % 8) - 4;
            const spark_y = this_player.y + (mt_rand() % 8) - 4;
            player_shot_create(0, SHOT_NORTSPARKS, spark_x, spark_y, this_player.mouseX, this_player.mouseY, 671, 1);
            g.shotRepeat[SHOT_NORTSPARKS] = Math.abs(nort_banking) - 1;
          }
        }
      } else {
        drawState.key = playerKey(playerNum_, 0);
        blit_sprite2x2(this_player.x - 5, this_player.y - 7, sheet, ship_sprite);
      }
    }

    /*Options Location*/
    if (playerNum_ === 2 && shipGr_ === 0) {
      // if dragonwing
      if (this_player.sidekick[LEFT_SIDEKICK].style === 0) {
        this_player.sidekick[LEFT_SIDEKICK].x = this_player.x - 14 + ship_banking * 2;
        this_player.sidekick[LEFT_SIDEKICK].y = this_player.y;
      }

      if (this_player.sidekick[RIGHT_SIDEKICK].style === 0) {
        this_player.sidekick[RIGHT_SIDEKICK].x = this_player.x + 17 + ship_banking * 2;
        this_player.sidekick[RIGHT_SIDEKICK].y = this_player.y;
      }
    }
  } // !endLevel

  if (moveOk) {
    if (this_player.is_alive) {
      if (!g.endLevel) {
        this_player.delta_x_shot_move = this_player.x - this_player.last_x_shot_move;
        this_player.delta_y_shot_move = this_player.y - this_player.last_y_shot_move;

        /* PLAYER SHOT Change */
        if (button[4 - 1]) {
          g.portConfigChange = true;
          if (g.portConfigDone) {
            g.shotMultiPos[SHOT_REAR] = 0;

            if (g.superArcadeMode !== SA_NONE && g.superArcadeMode <= SA_NORTSHIPZ) {
              g.shotMultiPos[SHOT_SPECIAL] = 0;
              g.shotMultiPos[SHOT_SPECIAL2] = 0;
              if (g.player[0].items.special === SASpecialWeapon[g.superArcadeMode - 1]) {
                g.player[0].items.special = SASpecialWeaponB[g.superArcadeMode - 1];
                this_player.weapon_mode = 2;
              } else {
                g.player[0].items.special = SASpecialWeapon[g.superArcadeMode - 1];
                this_player.weapon_mode = 1;
              }
            } else if (++this_player.weapon_mode > JE_portConfigs()) this_player.weapon_mode = 1;

            JE_drawPortConfigButtons();
            g.portConfigDone = false;
          }
        }

        /* PLAYER SHOT Creation */

        /*SpecialShot*/
        if (!g.galagaMode) JE_doSpecialShot(playerNum_, this_player); // C: &this_player->armor, &this_player->shield

        /*Normal Main Weapons*/
        if (!(g.twoPlayerLinked && playerNum_ === 2)) {
          let min: number, max: number;

          if (!g.twoPlayerMode) (min = 1), (max = 2);
          else min = max = playerNum_;

          for (let temp = min - 1; temp < max; temp++) {
            const item = this_player.items.weapon[temp].id;

            if (item > 0) {
              if (g.shotRepeat[temp] > 0) {
                --g.shotRepeat[temp];
              } else if (button[1 - 1]) {
                const item_power = g.galagaMode ? 0 : this_player.items.weapon[temp].power - 1,
                  item_mode = temp === REAR_WEAPON ? this_player.weapon_mode - 1 : 0;

                player_shot_create(item, temp, this_player.x, this_player.y, this_player.mouseX, this_player.mouseY, items.weaponPorts[item].op[item_mode][item_power], playerNum_);
              }
            }
          }
        }

        /*Super Charge Weapons*/
        if (playerNum_ === 2) {
          if (!g.twoPlayerLinked) {
            drawState.key = playerKey(playerNum_, 7);
            blit_sprite2(this_player.x + (shipGr_ === 0 ? 1 : 0) + 1, this_player.y - 13, g.res.spriteSheet10, 77 + g.chargeLevel + g.chargeGr * 19);
          }

          if (g.chargeGrWait > 0) {
            g.chargeGrWait--;
          } else {
            g.chargeGr++;
            if (g.chargeGr === 4) g.chargeGr = 0;
            g.chargeGrWait = 3;
          }

          // if (chargeLevel > 0) fill_rectangle_xy(VGAScreenSeg, ...) (HUD)

          if (g.chargeWait > 0) {
            g.chargeWait--;
          } else {
            if (g.chargeLevel < g.chargeMax) g.chargeLevel++;

            g.chargeWait = u8(28 - this_player.items.weapon[REAR_WEAPON].power * 2);
            if (g.difficultyLevel > DIFFICULTY_HARD) g.chargeWait = u8(g.chargeWait - 5);
          }

          // if (chargeLevel > 0) fill_rectangle_xy(VGAScreenSeg, ...) (HUD)

          if (g.shotRepeat[SHOT_P2_CHARGE] > 0) {
            --g.shotRepeat[SHOT_P2_CHARGE];
          } else if (button[1 - 1] && (!g.twoPlayerLinked || g.chargeLevel > 0)) {
            g.shotMultiPos[SHOT_P2_CHARGE] = 0;
            player_shot_create(16, SHOT_P2_CHARGE, this_player.x, this_player.y, this_player.mouseX, this_player.mouseY, chargeGunWeapons[g.player[1].items.weapon[REAR_WEAPON].id - 1] + g.chargeLevel, playerNum_);

            // if (chargeLevel > 0) fill_rectangle_xy(VGAScreenSeg, ...) (HUD)

            g.chargeLevel = 0;
            g.chargeWait = u8(30 - this_player.items.weapon[REAR_WEAPON].power * 2);
          }
        }

        /*SUPER BOMB*/
        let temp = playerNum_;
        if (temp === 0) temp = 1; /*Get whether player 1 or 2*/

        if (g.player[temp - 1].superbombs > 0) {
          if (g.shotRepeat[SHOT_P1_SUPERBOMB + temp - 1] > 0) {
            --g.shotRepeat[SHOT_P1_SUPERBOMB + temp - 1];
          } else if (button[3 - 1] || button[2 - 1]) {
            --g.player[temp - 1].superbombs;
            g.shotMultiPos[SHOT_P1_SUPERBOMB + temp - 1] = 0;
            player_shot_create(16, SHOT_P1_SUPERBOMB + temp - 1, this_player.x, this_player.y, this_player.mouseX, this_player.mouseY, 535, playerNum_);
          }
        }

        // sidekicks

        const left = this_player.sidekick[LEFT_SIDEKICK];
        const right = this_player.sidekick[RIGHT_SIDEKICK];

        if (left.style === 4 && right.style === 4) g.optionSatelliteRotate = Math.fround(g.optionSatelliteRotate + Math.fround(0.2));
        else if (left.style === 4 || right.style === 4) g.optionSatelliteRotate = Math.fround(g.optionSatelliteRotate + Math.fround(0.15));

        const old_n = this_player.old_x.length;
        switch (left.style) {
          case 1: // trailing
          case 3:
            left.x = this_player.old_x[old_n / 2 - 1];
            left.y = this_player.old_y[old_n / 2 - 1];
            break;
          case 2: // front-mounted
            left.x = this_player.x;
            left.y = Math.max(10, this_player.y - 20);
            break;
          case 4: // orbiting
            left.x = this_player.x + roundf(sinf(g.optionSatelliteRotate) * 20);
            left.y = this_player.y + roundf(cosf(g.optionSatelliteRotate) * 20);
            break;
        }

        switch (right.style) {
          case 4: // orbiting
            right.x = this_player.x - roundf(sinf(g.optionSatelliteRotate) * 20);
            right.y = this_player.y - roundf(cosf(g.optionSatelliteRotate) * 20);
            break;
          case 1: // trailing
          case 3:
            right.x = this_player.old_x[0];
            right.y = this_player.old_y[0];
            break;
          case 2: // front-mounted
            if (!g.optionAttachmentLinked) {
              right.y += idiv(g.optionAttachmentMove, 2);
              if (g.optionAttachmentMove >= -2) {
                const ret = g.optionAttachmentReturn ? 1 : 0;
                let temp: number; // JE_byte
                if (g.optionAttachmentReturn) temp = 2;
                else temp = 0;

                if (right.y > this_player.y - 20 + 5) {
                  temp = 2;
                  g.optionAttachmentMove = s16(g.optionAttachmentMove - (1 + ret));
                } else if (right.y > this_player.y - 20 - 0) {
                  temp = 3;
                  if (g.optionAttachmentMove > 0) g.optionAttachmentMove--;
                  else g.optionAttachmentMove++;
                } else if (right.y > this_player.y - 20 - 5) {
                  temp = 2;
                  g.optionAttachmentMove++;
                } else if (g.optionAttachmentMove < 2 + ret * 4) {
                  g.optionAttachmentMove = s16(g.optionAttachmentMove + 1 + ret);
                }

                if (g.optionAttachmentReturn) temp = u8(temp * 2);
                if (Math.abs(right.x - this_player.x) < temp) temp = 1;

                if (right.x > this_player.x) right.x -= temp;
                else if (right.x < this_player.x) right.x += temp;

                if (Math.abs(right.y - (this_player.y - 20)) + Math.abs(right.x - this_player.x) < 8) {
                  g.optionAttachmentLinked = true;
                  g.soundQueue[2] = S_CLINK;
                }

                if (button[3 - 1]) g.optionAttachmentReturn = true;
              } // sidekick needs to catch up to player
              else {
                g.optionAttachmentMove = s16(g.optionAttachmentMove + 1 + (g.optionAttachmentReturn ? 1 : 0));
                JE_setupExplosion(right.x + 1, right.y + 10, 0, 0, false, false);
              }
            } else {
              right.x = this_player.x;
              right.y = this_player.y - 20;
              if (button[3 - 1]) {
                g.optionAttachmentLinked = false;
                g.optionAttachmentReturn = false;
                g.optionAttachmentMove = -20;
                g.soundQueue[3] = S_WEAPON_26;
              }
            }

            if (right.y < 10) right.y = 10;
            break;
        }

        if (playerNum_ === 2 || !g.twoPlayerMode) {
          // if player has sidekicks
          for (let i = 0; i < this_player.items.sidekick.length; ++i) {
            const shot_i = i === 0 ? SHOT_LEFT_SIDEKICK : SHOT_RIGHT_SIDEKICK;

            const this_option = items.options[this_player.items.sidekick[i]];
            const sk = this_player.sidekick[i];

            // fire/refill sidekick
            if (this_option.wPort > 0) {
              if (g.shotRepeat[shot_i] > 0) {
                --g.shotRepeat[shot_i];
              } else {
                const ammo_max = sk.ammo_max;

                if (ammo_max > 0) {
                  // sidekick has limited ammo
                  if (sk.ammo_refill_ticks > 0) {
                    --sk.ammo_refill_ticks;
                  } // refill one ammo
                  else {
                    sk.ammo_refill_ticks = sk.ammo_refill_ticks_max;

                    if (sk.ammo < ammo_max) ++sk.ammo;

                    // draw sidekick refill ammo gauge (HUD)
                  }

                  if (button[1 + i] && sk.ammo > 0) {
                    player_shot_create(this_option.wPort, shot_i, sk.x, sk.y, this_player.mouseX, this_player.mouseY, this_option.wpNum + sk.charge, playerNum_);

                    --sk.ammo;
                    if (sk.charge > 0) {
                      g.shotMultiPos[shot_i] = 0;
                      sk.charge = 0;
                    }
                    sk.charge_ticks = 20;
                    sk.animation_enabled = true;

                    // draw sidekick discharge ammo gauge (HUD)
                  }
                } // has infinite ammo
                else {
                  if (button[0] || button[1 + i]) {
                    player_shot_create(this_option.wPort, shot_i, sk.x, sk.y, this_player.mouseX, this_player.mouseY, this_option.wpNum + sk.charge, playerNum_);

                    if (sk.charge > 0) {
                      g.shotMultiPos[shot_i] = 0;
                      sk.charge = 0;
                    }
                    sk.charge_ticks = 20;
                    sk.animation_enabled = true;
                  }
                }
              }
            }
          }
        } // end of if player has sidekicks
      } // !endLevel
    } // this_player->is_alive
  } // moveOK

  // draw sidekicks
  if ((playerNum_ === 2 || !g.twoPlayerMode) && !g.endLevel) {
    for (let i = 0; i < this_player.sidekick.length; ++i) {
      const this_option = items.options[this_player.items.sidekick[i]];
      const sk = this_player.sidekick[i];

      if (this_option.option > 0) {
        if (sk.animation_enabled) {
          if (++sk.animation_frame >= this_option.ani) {
            sk.animation_frame = 0;
            sk.animation_enabled = this_option.option === 1;
          }
        }

        const x = sk.x,
          y = sk.y;
        const sprite = u32(this_option.gr[sk.animation_frame] + sk.charge);

        drawState.key = playerKey(playerNum_, 40 + i);
        if (sk.style === 1 || sk.style === 2) blit_sprite2x2(x - 6, y, g.res.spriteSheet10, sprite);
        else blit_sprite2(x, y, g.res.spriteSheet9, sprite);
      }

      sk.charge_ticks = u32(sk.charge_ticks - 1);
      if (sk.charge_ticks === 0) {
        if (sk.charge < this_option.pwr) ++sk.charge;
        sk.charge_ticks = 20;
      }
    }
  }

  drawState.key = savedKey;
}

/** mainint.c L4405-4463: moves and draws the player(s), then sets the parallax map offsets. */
export function JE_mainGamePlayerFunctions(): void {
  /*PLAYER MOVEMENT/MOUSE ROUTINES*/

  if (g.endLevel && g.levelEnd > 0) {
    g.levelEnd--;
    g.levelEndWarp = s8(g.levelEndWarp + 1);
  }

  /*Reset Street-Fighter commands*/
  g.SFExecuted.fill(0);

  g.portConfigChange = false;

  if (g.twoPlayerMode) {
    JE_playerMovement(g.player[0], !g.galagaMode ? g.inputDevice[0] : 0, 1, g.shipGr, g.shipGrPtr);
    JE_playerMovement(g.player[1], !g.galagaMode ? g.inputDevice[1] : 0, 2, g.shipGr2, g.shipGr2ptr);
  } else {
    JE_playerMovement(g.player[0], 0, 1, g.shipGr, g.shipGrPtr);
  }

  /* == Parallax Map Scrolling == */
  let tempX: number; // JE_word
  if (g.twoPlayerMode) tempX = u16(idiv(g.player[0].x + g.player[1].x, 2));
  else tempX = u16(g.player[0].x);

  const f = Math.fround;
  const tempW = u16(Math.floor(f(f(f(260 - (tempX - 36)) / (260 - 36)) * (24 * 3)) - 1));
  g.mapX3Ofs = tempW;
  g.mapX3Pos = g.mapX3Ofs % 24;
  g.mapX3bpPos = 1 - idiv(g.mapX3Ofs, 24);

  g.mapX2Ofs = idiv(tempW * 2, 3);
  g.mapX2Pos = g.mapX2Ofs % 24;
  g.mapX2bpPos = 1 - idiv(g.mapX2Ofs, 24);

  g.oldMapXOfs = g.mapXOfs;
  g.mapXOfs = idiv(g.mapX2Ofs, 2);
  g.mapXPos = g.mapXOfs % 24;
  g.mapXbpPos = 1 - idiv(g.mapXOfs, 24);

  if (g.background3x1) {
    g.mapX3Ofs = g.mapXOfs;
    g.mapX3Pos = g.mapXPos;
    g.mapX3bpPos = g.mapXbpPos - 1;
  }
}

/** mainint.c L4475-4852: player vs enemies — pick-ups, and collision damage. */
export function JE_playerCollide(this_player: Player, playerNum_: number): void {
  const player = g.player;
  const enemy = g.enemy;
  const enemyAvail = g.enemyAvail;
  const items = g.res.items;
  const enemyDat = g.res.enemyDat;
  const miscText = g.miscText;
  let tempStr: string;

  for (let z = 0; z < 100; z++) {
    if (enemyAvail[z] !== 1) {
      const enemy_screen_x = enemy[z].ex + enemy[z].mapoffset;

      if (Math.abs(this_player.x - enemy_screen_x) < 12 && Math.abs(this_player.y - enemy[z].ey) < 14) {
        /*Collide*/
        const evalue = enemy[z].evalue;
        if (evalue > 29999) {
          if (evalue === 30000) {
            // spawn dragonwing in galaga mode, otherwise just a purple ball
            this_player.cash += 100;

            if (!g.galagaMode) {
              handle_got_purple_ball(this_player);
            } else {
              // spawn the dragonwing?
              if (g.twoPlayerMode) this_player.cash += 2400;
              g.twoPlayerMode = true;
              g.twoPlayerLinked = true;
              player[1].items.weapon[REAR_WEAPON].power = 1;
              player[1].armor = 10;
              player[1].is_alive = true;
            }
            enemyAvail[z] = 1;
            g.soundQueue[7] = S_POWERUP;
          } else if (g.superArcadeMode !== SA_NONE && evalue > 30000) {
            g.shotMultiPos[SHOT_FRONT] = 0;
            g.shotRepeat[SHOT_FRONT] = 10;

            const tempW = SAWeapon[g.superArcadeMode - 1][evalue - 30000 - 1];

            // if picked up already-owned weapon, power weapon up
            if (tempW === player[0].items.weapon[FRONT_WEAPON].id) {
              this_player.cash += 1000;
              power_up_weapon(this_player, FRONT_WEAPON);
            }
            // else weapon also gives purple ball
            else {
              handle_got_purple_ball(this_player);
            }

            player[0].items.weapon[FRONT_WEAPON].id = tempW;
            this_player.cash += 200;
            g.soundQueue[7] = S_POWERUP;
            enemyAvail[z] = 1;
          } else if (evalue > 32100) {
            if (playerNum_ === 1) {
              this_player.cash += 250;
              player[0].items.special = evalue - 32100;
              g.shotMultiPos[SHOT_SPECIAL] = 0;
              g.shotRepeat[SHOT_SPECIAL] = 10;
              g.shotMultiPos[SHOT_SPECIAL2] = 0;
              g.shotRepeat[SHOT_SPECIAL2] = 0;

              if (g.isNetworkGame) tempStr = `${JE_getName(1)} ${g.miscTextB[4 - 1]} ${items.specials[evalue - 32100].name}`;
              else if (g.twoPlayerMode) tempStr = `${miscText[43 - 1]} ${items.specials[evalue - 32100].name}`;
              else tempStr = `${miscText[64 - 1]} ${items.specials[evalue - 32100].name}`;
              JE_drawTextWindow(tempStr);
              g.soundQueue[7] = S_POWERUP;
              enemyAvail[z] = 1;
            }
          } else if (evalue > 32000) {
            if (playerNum_ === 2) {
              enemyAvail[z] = 1;
              if (g.isNetworkGame) tempStr = `${JE_getName(2)} ${g.miscTextB[4 - 1]} ${items.options[evalue - 32000].name}`;
              else tempStr = `${miscText[44 - 1]} ${items.options[evalue - 32000].name}`;
              JE_drawTextWindow(tempStr);

              // if picked up a different sidekick than player already has, then reset sidekicks to least powerful, else power them up
              if (evalue - 32000 !== player[1].items.sidekick_series) {
                player[1].items.sidekick_series = u8(evalue - 32000);
                player[1].items.sidekick_level = 101;
              } else if (player[1].items.sidekick_level < 103) {
                ++player[1].items.sidekick_level;
              }

              const temp = player[1].items.sidekick_level - 100 - 1;
              for (let i = 0; i < player[1].items.sidekick.length; ++i)
                player[1].items.sidekick[i] = optionSelect[player[1].items.sidekick_series][temp][i];

              g.shotMultiPos[SHOT_LEFT_SIDEKICK] = 0;
              g.shotMultiPos[SHOT_RIGHT_SIDEKICK] = 0;
              JE_drawOptions();
              g.soundQueue[7] = S_POWERUP;
            } else if (g.onePlayerAction) {
              enemyAvail[z] = 1;
              tempStr = `${miscText[64 - 1]} ${items.options[evalue - 32000].name}`;
              JE_drawTextWindow(tempStr);

              for (let i = 0; i < player[0].items.sidekick.length; ++i) player[0].items.sidekick[i] = u8(evalue - 32000);
              g.shotMultiPos[SHOT_LEFT_SIDEKICK] = 0;
              g.shotMultiPos[SHOT_RIGHT_SIDEKICK] = 0;

              JE_drawOptions();
              g.soundQueue[7] = S_POWERUP;
            }
            if (enemyAvail[z] === 1) this_player.cash += 250;
          } else if (evalue > 31000) {
            this_player.cash += 250;
            if (playerNum_ === 2) {
              if (g.isNetworkGame) tempStr = `${JE_getName(2)} ${g.miscTextB[4 - 1]} ${items.weaponPorts[evalue - 31000].name}`;
              else tempStr = `${miscText[44 - 1]} ${items.weaponPorts[evalue - 31000].name}`;
              JE_drawTextWindow(tempStr);
              player[1].items.weapon[REAR_WEAPON].id = u8(evalue - 31000);
              g.shotMultiPos[SHOT_REAR] = 0;
              enemyAvail[z] = 1;
              g.soundQueue[7] = S_POWERUP;
            } else if (g.onePlayerAction) {
              tempStr = `${miscText[64 - 1]} ${items.weaponPorts[evalue - 31000].name}`;
              JE_drawTextWindow(tempStr);
              player[0].items.weapon[REAR_WEAPON].id = u8(evalue - 31000);
              g.shotMultiPos[SHOT_REAR] = 0;
              enemyAvail[z] = 1;
              g.soundQueue[7] = S_POWERUP;

              if (player[0].items.weapon[REAR_WEAPON].power === 0)
                // does this ever happen?
                player[0].items.weapon[REAR_WEAPON].power = 1;
            }
          } else if (evalue > 30000) {
            if (playerNum_ === 1 && g.twoPlayerMode) {
              if (g.isNetworkGame) tempStr = `${JE_getName(1)} ${g.miscTextB[4 - 1]} ${items.weaponPorts[evalue - 30000].name}`;
              else tempStr = `${miscText[43 - 1]} ${items.weaponPorts[evalue - 30000].name}`;
              JE_drawTextWindow(tempStr);
              player[0].items.weapon[FRONT_WEAPON].id = u8(evalue - 30000);
              g.shotMultiPos[SHOT_FRONT] = 0;
              enemyAvail[z] = 1;
              g.soundQueue[7] = S_POWERUP;
            } else if (g.onePlayerAction) {
              tempStr = `${miscText[64 - 1]} ${items.weaponPorts[evalue - 30000].name}`;
              JE_drawTextWindow(tempStr);
              player[0].items.weapon[FRONT_WEAPON].id = u8(evalue - 30000);
              g.shotMultiPos[SHOT_FRONT] = 0;
              enemyAvail[z] = 1;
              g.soundQueue[7] = S_POWERUP;
            }

            if (enemyAvail[z] === 1) {
              player[0].items.special = specialArcadeWeapon[evalue - 30000 - 1];
              if (player[0].items.special > 0) {
                g.shotMultiPos[SHOT_SPECIAL] = 0;
                g.shotRepeat[SHOT_SPECIAL] = 0;
                g.shotMultiPos[SHOT_SPECIAL2] = 0;
                g.shotRepeat[SHOT_SPECIAL2] = 0;
              }
              this_player.cash += 250;
            }
          }
        } else if (evalue > 20000) {
          if (g.twoPlayerLinked) {
            // share the armor evenly between linked players
            for (let i = 0; i < player.length; ++i) {
              player[i].armor += idiv(evalue - 20000, player.length);
              if (player[i].armor > 28) player[i].armor = 28;
            }
          } else {
            this_player.armor += evalue - 20000;
            if (this_player.armor > 28) this_player.armor = 28;
          }
          enemyAvail[z] = 1;
          JE_drawArmor();
          g.soundQueue[7] = S_POWERUP;
        } else if (evalue > 10000 && enemyAvail[z] === 2) {
          if (!g.bonusLevel) {
            // play_song(30); /*Zanac*/ (music isn't driven by the sim)
            g.bonusLevel = true;
            g.nextLevel = evalue - 10000;
            enemyAvail[z] = 1;
            g.displayTime = 150;
          }
        } else if (enemy[z].scoreitem) {
          enemyAvail[z] = 1;
          g.soundQueue[7] = S_ITEM;
          if (evalue === 1) {
            g.cubeMax++;
            g.soundQueue[3] = V_DATA_CUBE;
          } else if (evalue === -1) {
            // got front weapon powerup
            if (g.isNetworkGame) tempStr = `${JE_getName(1)} ${g.miscTextB[4 - 1]} ${miscText[45 - 1]}`;
            else if (g.twoPlayerMode) tempStr = `${miscText[43 - 1]} ${miscText[45 - 1]}`;
            else tempStr = miscText[45 - 1];
            JE_drawTextWindow(tempStr);

            power_up_weapon(player[0], FRONT_WEAPON);
            g.soundQueue[7] = S_POWERUP;
          } else if (evalue === -2) {
            // got rear weapon powerup
            if (g.isNetworkGame) tempStr = `${JE_getName(2)} ${g.miscTextB[4 - 1]} ${miscText[46 - 1]}`;
            else if (g.twoPlayerMode) tempStr = `${miscText[44 - 1]} ${miscText[46 - 1]}`;
            else tempStr = miscText[46 - 1];
            JE_drawTextWindow(tempStr);

            power_up_weapon(g.twoPlayerMode ? player[1] : player[0], REAR_WEAPON);
            g.soundQueue[7] = S_POWERUP;
          } else if (evalue === -3) {
            // picked up orbiting asteroid killer
            g.shotMultiPos[SHOT_MISC] = 0;
            player_shot_create(0, SHOT_MISC, this_player.x, this_player.y, player[0].mouseX, player[0].mouseY, 104, playerNum_);
            g.shotAvail[z] = 0; // (sic: indexes shotAvail by the enemy slot)
          } else if (evalue === -4) {
            if (player[playerNum_ - 1].superbombs < 10) ++player[playerNum_ - 1].superbombs;
          } else if (evalue === -5) {
            player[0].items.weapon[FRONT_WEAPON].id = 25; // HOT DOG!
            player[0].items.weapon[REAR_WEAPON].id = 26;
            player[1].items.weapon[REAR_WEAPON].id = 26;

            player[0].last_items = copyPlayerItems(player[0].items);

            for (let i = 0; i < player.length; ++i) player[i].weapon_mode = 1;

            g.shotMultiPos.fill(0);
          } else if (g.twoPlayerLinked) {
            // players get equal share of pick-up cash when linked
            for (let i = 0; i < player.length; ++i) player[i].cash += idiv(evalue, player.length);
          } else {
            this_player.cash += evalue;
          }
          JE_setupExplosion(enemy_screen_x, enemy[z].ey, 0, enemyDat[enemy[z].enemytype].explosionType, true, false);
        } else if (
          this_player.invulnerable_ticks === 0 && enemyAvail[z] === 0 &&
          (enemyDat[enemy[z].enemytype].explosionType & 1) === 0 // explosiontype & 1 == 0: not ground enemy
        ) {
          let armorleft = enemy[z].armorleft;
          if (armorleft > g.damageRate) armorleft = g.damageRate;

          JE_playerDamage(armorleft, this_player);

          // player ship gets push-back from collision
          if (enemy[z].armorleft > 0) {
            this_player.x_velocity += idiv(enemy[z].exc * enemy[z].armorleft, 2);
            this_player.y_velocity += idiv(enemy[z].eyc * enemy[z].armorleft, 2);
          }

          let armorleft2 = enemy[z].armorleft;
          if (armorleft2 === 255) armorleft2 = 30000;

          let temp = enemy[z].linknum; // JE_byte
          if (temp === 0) temp = 255;

          const b = z;

          if (armorleft2 > armorleft) {
            // damage enemy
            if (enemy[z].armorleft !== 255) enemy[z].armorleft = u8(enemy[z].armorleft - armorleft);
            g.soundQueue[5] = S_ENEMY_HIT;
          } else {
            // kill enemy
            for (let temp2 = 0; temp2 < 100; temp2++) {
              if (enemyAvail[temp2] !== 1) {
                const temp3 = enemy[temp2].linknum;
                if (
                  temp2 === b ||
                  (temp !== 255 &&
                    (temp === temp3 || temp - 100 === temp3 ||
                      (temp3 > 40 && idiv(temp3, 20) === idiv(temp, 20) && temp3 <= temp)))
                ) {
                  const enemy_screen_x = enemy[temp2].ex + enemy[temp2].mapoffset;

                  enemy[temp2].linknum = 0;

                  enemyAvail[temp2] = 1;

                  if (enemyDat[enemy[temp2].enemytype].eSize === 1) {
                    JE_setupExplosionLarge(enemy[temp2].enemyground, enemy[temp2].explonum, enemy_screen_x, enemy[temp2].ey);
                    g.soundQueue[6] = S_EXPLOSION_9;
                  } else {
                    JE_setupExplosion(enemy_screen_x, enemy[temp2].ey, 0, 1, false, false);
                    g.soundQueue[5] = S_EXPLOSION_4;
                  }
                }
              }
            }
            enemyAvail[z] = 1;
          }
        }
      }
    }
  }
}

// --- Item values and the end-of-level bookkeeping (added by the shop port) ---

/** mainint.c L570-582: cost to upgrade a weapon to `power` from power - 1 (power 0 = unupgraded). */
export function weapon_upgrade_cost(base_cost: number, power: number): number {
  if (power > 11) throw new Error(`weapon_upgrade_cost: power ${power} > 11`); // assert(power <= 11)

  let temp = 0;

  // 0 1 3 6 10 15 21 29 ...
  for (; power > 0; power--) temp += power;

  return base_cost * temp;
}

/**
 * JE_getCost (mainint.c L584-618): an item's price. itemType is the upgrade menu's selection: 2
 * ship, 3 front weapon, 4 rear weapon, 5 shield, 6 generator, 7/8 left/right sidekick. For weapons it
 * also sets g.upgradeCost and g.downgradeCost (JE_word) for the player's current power level.
 */
export function JE_getCost(itemType: number, itemNum: number): number {
  const { items } = g.res;
  let cost = 0;

  switch (itemType) {
    case 2:
      cost = itemNum > 90 ? 100 : items.ships[itemNum].cost;
      break;
    case 3:
    case 4: {
      cost = items.weaponPorts[itemNum].cost;

      const port = itemType - 3,
        item_power = g.player[0].items.weapon[port].power - 1;

      g.downgradeCost = u16(weapon_upgrade_cost(cost, item_power));
      g.upgradeCost = u16(weapon_upgrade_cost(cost, item_power + 1));
      break;
    }
    case 5:
      cost = items.shields[itemNum].cost;
      break;
    case 6:
      cost = items.powerSys[itemNum].cost;
      break;
    case 7:
    case 8:
      cost = items.options[itemNum].cost;
      break;
  }

  return cost;
}

/** JE_getValue (mainint.c L918-953): what an owned item is worth, including weapon power upgrades. */
export function JE_getValue(itemType: number, itemNum: number): number {
  const { items } = g.res;
  let value = 0;

  switch (itemType) {
    case 2:
      value = items.ships[itemNum].cost;
      break;
    case 3:
    case 4: {
      const base_value = items.weaponPorts[itemNum].cost;

      // if two-player, use first player's front and second player's rear weapon
      const port = itemType - 3;
      const item_power = g.player[g.twoPlayerMode ? port : 0].items.weapon[port].power - 1;

      value = base_value;
      for (let i = 1; i <= item_power; ++i) value += weapon_upgrade_cost(base_value, i);
      break;
    }
    case 5:
      value = items.shields[itemNum].cost;
      break;
    case 6:
      value = items.powerSys[itemNum].cost;
      break;
    case 7:
    case 8:
      value = items.options[itemNum].cost;
      break;
  }

  return value;
}

/** JE_totalScore (mainint.c L903-916): cash plus the value of everything the player owns. */
export function JE_totalScore(this_player: Player): number {
  let temp = this_player.cash;

  temp += JE_getValue(2, this_player.items.ship);
  temp += JE_getValue(3, this_player.items.weapon[FRONT_WEAPON].id);
  temp += JE_getValue(4, this_player.items.weapon[REAR_WEAPON].id);
  temp += JE_getValue(5, this_player.items.shield);
  temp += JE_getValue(6, this_player.items.generator);
  temp += JE_getValue(7, this_player.items.sidekick[LEFT_SIDEKICK]);
  temp += JE_getValue(8, this_player.items.sidekick[RIGHT_SIDEKICK]);

  return temp;
}

/** adjust_difficulty (mainint.c L2158-2225): raise the difficulty as the player's score grows. */
export function adjust_difficulty(): void {
  const score_multiplier = [
    0, // Wimp  (doesn't exist)
    0.4, // Easy
    0.8, // Normal
    1.3, // Hard
    1.6, // Impossible
    2, // Insanity
    2, // Suicide
    3, // Maniacal
    3, // Zinglon
    3, // Nortaneous
  ];

  // assert(initialDifficulty > 0 && initialDifficulty < 10)
  if (!(g.initialDifficulty > 0 && g.initialDifficulty < 10)) throw new Error(`adjust_difficulty: initialDifficulty ${g.initialDifficulty}`);

  // ulong * float is a float multiply.
  const score = g.twoPlayerMode ? g.player[0].cash + g.player[1].cash : JE_totalScore(g.player[0]),
    adjusted_score = roundf(fmul(score, score_multiplier[g.initialDifficulty]));

  let new_difficulty = 0;

  if (g.twoPlayerMode) {
    if (adjusted_score < 10000) new_difficulty = DIFFICULTY_EASY;
    else if (adjusted_score < 20000) new_difficulty = DIFFICULTY_NORMAL;
    else if (adjusted_score < 50000) new_difficulty = DIFFICULTY_HARD;
    else if (adjusted_score < 80000) new_difficulty = DIFFICULTY_IMPOSSIBLE;
    else if (adjusted_score < 125000) new_difficulty = DIFFICULTY_INSANITY;
    else if (adjusted_score < 200000) new_difficulty = DIFFICULTY_SUICIDE;
    else if (adjusted_score < 400000) new_difficulty = DIFFICULTY_MANIACAL;
    else if (adjusted_score < 600000) new_difficulty = DIFFICULTY_ZINGLON;
    else new_difficulty = DIFFICULTY_NORTANEOUS;
  } else {
    if (adjusted_score < 40000) new_difficulty = DIFFICULTY_EASY;
    else if (adjusted_score < 70000) new_difficulty = DIFFICULTY_NORMAL;
    else if (adjusted_score < 150000) new_difficulty = DIFFICULTY_HARD;
    else if (adjusted_score < 300000) new_difficulty = DIFFICULTY_IMPOSSIBLE;
    else if (adjusted_score < 600000) new_difficulty = DIFFICULTY_INSANITY;
    else if (adjusted_score < 1000000) new_difficulty = DIFFICULTY_SUICIDE;
    else if (adjusted_score < 2000000) new_difficulty = DIFFICULTY_MANIACAL;
    else if (adjusted_score < 3000000) new_difficulty = DIFFICULTY_ZINGLON;
    else new_difficulty = DIFFICULTY_NORTANEOUS;
  }

  // MAX((unsigned)difficultyLevel, new_difficulty)
  g.difficultyLevel = Math.max(u32(g.difficultyLevel), new_difficulty);
}

/**
 * JE_endLevelAni (mainint.c L2521-2676), its state changes only: the difficulty adjustment, the
 * loadout the next item screen adds to its lists (last_items), and lastLevelName. The "Completed"
 * summary is the host's screen; ShipEdit privileges (editorItemAvail) and editorLevel aren't ported.
 */
export function JE_endLevelAni(): void {
  adjust_difficulty();

  g.player[0].last_items = copyPlayerItems(g.player[0].items);
  g.lastLevelName = g.levelName;
}
