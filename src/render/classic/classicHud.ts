// The original HUD for the side-by-side comparison (D158), drawn from the game's state each tick:
// the in-game frame (picture 3) with what the C draws on VGAScreenSeg (JE_drawShield, JE_drawArmor,
// the weapon power pips and power bar of JE_main, JE_drawPortConfigButtons, JE_drawOptions,
// JE_drawTextWindow), and what JE_main draws on game_screen after the draw list (the secret-level
// banner, draw_boss_bar, JE_inGameDisplays). The C draws these incrementally; here they're redrawn
// whole from the state, which looks the same.

import { FONT_SHAPES, fontMap, TINY_FONT } from "../../sim/fonthand";
import { g } from "../../sim/state";
import { Pass, type Sprite2Sheet } from "../../sim/draw";
import { drawOne, Surface, hvOp, tableSprite } from "./classicRenderer";

const OPTION_SHAPES = 5;
/** varz.h hud_sidekick_y, one-player HUD. */
const HUD_SIDEKICK_Y = [64, 82];

const DARK = (_s: number, d: number) => (d & 0xf0) | ((d & 0x0f) >> 1);

/** JE_outText (fonthand.c): TINY_FONT, hue `bank`, value `brightness` (< 0: black). */
function outText(s: Surface, x: number, y: number, text: string, bank: number, brightness: number, font = TINY_FONT): void {
  const table = g.res.spriteTables[font];
  let bright = 0;
  for (const ch of text) {
    if (ch === " ") {
      x += 6;
      continue;
    }
    if (ch === "~") {
      bright = bright === 0 ? 4 : 0;
      continue;
    }
    const id = fontMap[ch.charCodeAt(0) & 0xff];
    const spr = id >= 0 ? tableSprite(table, id) : null;
    if (!spr) continue;
    s.blit(spr, x, y, brightness >= 0 ? hvOp(bank, brightness + bright) : () => 0);
    x += spr.width + 1;
  }
}

/** JE_textShade FULL_SHADE: a black outline, then the text. */
function textShade(s: Surface, x: number, y: number, text: string, bank: number, brightness: number): void {
  for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) outText(s, x + dx, y + dy, text, 0, -1);
  outText(s, x, y, text, bank, brightness);
}

/** JE_outTextAndDarken (fonthand.c L227-256): a dark shadow at (+1, +1), then the text. */
function outTextAndDarken(s: Surface, x: number, y: number, text: string, bank: number, brightness: number, font: number): void {
  const table = g.res.spriteTables[font];
  for (const ch of text) {
    if (ch === " ") {
      x += 6;
      continue;
    }
    const id = fontMap[ch.charCodeAt(0) & 0xff];
    const spr = id >= 0 ? tableSprite(table, id) : null;
    if (!spr) continue;
    s.blit(spr, x + 1, y + 1, DARK);
    s.blit(spr, x, y, hvOp(bank, brightness));
    x += spr.width + 1;
  }
}

/** JE_dBar3 (nortvars.c): a bar of 2-pixel rows from y up, the colour stepping every two rows. */
function dBar3(s: Surface, x: number, y: number, num: number, col: number): void {
  col += 2;
  let wait = 2;
  for (let z = 0; z <= num; z++) {
    s.fill(x, y - 1, x + 8, y, col);
    if (wait > 0) wait--;
    else {
      col++;
      wait = 1;
    }
    y -= 2;
  }
}

/** draw_segmented_gauge (vga256d.c). */
function segmentedGauge(s: Surface, x: number, y: number, color: number, w: number, h: number, segValue: number, value: number): void {
  const segs = Math.floor(value / segValue);
  const part = value % segValue;
  for (let i = 0; i < segs; i++, x += w + 1) s.fill(x, y, x + w - 1, y + h - 1, color + 12);
  if (part > 0) s.fill(x, y, x + w - 1, y + h - 1, color + Math.floor((12 * part) / segValue));
}

/**
 * VGAScreenSeg: picture 3 and the sidebar's readouts. `frame` is picture 3's pixels (JE_loadPic 3);
 * the playfield's corner is drawn over it afterwards (ClassicRenderer.render).
 */
export function drawSidebar(s: Surface, frame: Uint8Array | null): void {
  if (frame) s.px.set(frame.subarray(0, s.px.length));
  else s.px.fill(0);
  const p = g.player[0];
  const opt = g.res.spriteTables[OPTION_SHAPES];

  // JE_drawShield, JE_drawArmor
  dBar3(s, 270, 194, Math.max(0, p.shield), 144);
  if (p.shield !== p.shield_max) {
    const y = 193 - p.shield_max * 2;
    s.fill(270, y, 278, y, 68);
  }
  dBar3(s, 307, 194, Math.max(0, Math.min(28, p.armor)), 224);

  // Weapon power pips (tyrian2.c L1089-1108)
  for (let i = 0; i < 2; i++) {
    let x = 289;
    const y = i === 0 ? 17 : 38;
    s.fill(x, y, x + 1 + 20, y + 2, 0);
    for (let j = 1; j <= p.items.weapon[i].power; j++, x += 2) s.fill(x, y, x + 1, y + 2, 115 + j);
  }

  // Power bar (tyrian2.c L1111-1132): drawn a row at a time as it fills, each in its level's colour.
  const power = Math.floor(g.power / 10);
  for (let t = 1; t <= power; t++) s.fill(269, 113 - 11 - t, 276, 113 - 11 - t, 113 + Math.floor(t / 7));

  // JE_drawPortConfigButtons
  const lit = tableSprite(opt, 18);
  const unlit = tableSprite(opt, 19);
  const [a, b] = p.weapon_mode === 1 ? [lit, unlit] : [unlit, lit];
  if (a) s.blit(a, 285, 44, (c) => c);
  if (b) s.blit(b, 302, 44, (c) => c);

  // JE_drawOptions: the sidekick boxes
  for (let i = 0; i < 2; i++) {
    const y = HUD_SIDEKICK_Y[i];
    s.fill(284, y, 284 + 28, y + 15, 0);
    const o = g.res.items.options[p.items.sidekick[i]];
    if (o && o.iconGr > 0) {
      const icon = tableSprite(opt, o.iconGr - 1);
      if (icon) s.blit(icon, 284, y, (c) => c);
    }
    const sk = p.sidekick[i];
    segmentedGauge(s, 284, y + 13, 112, 2, 2, Math.max(1, Math.floor(sk.ammo_max / 10)), sk.ammo);
  }

  // JE_drawTextWindow: the message area, and the message while it lasts
  const area = tableSprite(opt, 36);
  if (area) s.blit(area, 16, 189, (c) => c);
  if (g.textErase > 0) outText(s, 20, 190, g.messageText, 0, 4);
}

/** game_screen, before JE_filterScreen: the "Secret Level!" banner (tyrian2.c L1993-2000). */
export function drawBeforeFilter(gs: Surface): void {
  if (g.displayTime > 0) outTextAndDarken(gs, 90, 10, g.miscText[59] ?? "", 15, g.flash - 8, FONT_SHAPES);
}

/** JE_barX (tyrian2.c L5110-5115). */
function barX(s: Surface, x1: number, y1: number, x2: number, y2: number, col: number): void {
  s.fill(x1, y1, x2, y1, col + 1);
  s.fill(x1, y1 + 1, x2, y2 - 1, col);
  s.fill(x1, y2, x2, y2, col - 1);
}

/** game_screen, after JE_filterScreen: draw_boss_bar and JE_inGameDisplays (one player). */
export function drawAfterFilter(gs: Surface): void {
  const bars = g.boss_bar.filter((b) => b.link_num !== 0);
  bars.forEach((b, i) => {
    const x = bars.length === 2 ? (i === 0 ? 125 : 185) : g.levelTimer ? 250 : 155;
    barX(gs, x - 25, 7, x + 25, 12, 115);
    barX(gs, x - Math.floor(b.armor / 10), 7, x + Math.floor((b.armor + 5) / 10), 12, 118 + b.color);
  });

  const p = g.player[0];
  textShade(gs, 30, 175, String(p.cash), 2, 4);
  const sprite2 = (sheet: Sprite2Sheet, index: number, x: number, y: number, size: 1 | 2) =>
    drawOne(gs, {
      kind: "sprite2", sheet, index, x, y, size, pass: Pass.Effects, key: -1, effect: "none", filter: 0, value: 0,
      groupIndex: -1, groupSize: 1, groupDx: 0, groupDy: 0, groupFirst: false,
    });
  const special = p.items.special > 0 ? g.res.items.specials[p.items.special] : undefined;
  if (special) sprite2(g.res.spriteSheet10, special.itemGraphic, 25, 1, 2);
  for (let j = 0; j < p.superbombs; j++) sprite2(g.res.spriteSheet9, 304, 30 + 12 * j, 160, 1);
  if (g.youAreCheating) outText(gs, 90, 170, "Cheaters always prosper.", 3, 4);
}
