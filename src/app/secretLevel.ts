// The "Secret Level!" banner (tyrian2.c L1993-2000): while displayTime runs (150 frames from picking
// up a secret-level warp, mainint.c L4697-4706), JE_main draws miscText[59] with
//   JE_outTextAndDarken(VGAScreen, 90, 10, miscText[59], 15, (JE_byte)flash - 8, FONT_SHAPES)
// i.e. in the big font at screen (90, 10), colour bank 15 (the level palette's fire ramp), each glyph
// shade darkened by 8 - flash, flash bouncing 0..5 (the pulse), over a dark drop shadow at (+1, +1).
// The sim keeps displayTime and flash (game.ts); this turns them into what the HUD shows: the text,
// where it sits on the playfield, and its colour this frame. Pure, so it can be tested without a DOM.

import { vga6To8 } from "../data/palette";
import { FONT_SHAPES, fontMap, JE_textWidth } from "../sim/fonthand";
import { g } from "../sim/state";

/** The banner's screen position and colour bank in the C. */
export const SECRET_X = 90;
export const SECRET_Y = 10;
export const SECRET_BANK = 15;
/** miscText[59]: "Secret Level!" in tyrian.hdt. */
export const SECRET_TEXT_INDEX = 59;
/** The playfield on the 320x200 screen: x 24..288, y 0..184. */
const PLAY_LEFT = 24;
const PLAY_W = 264;
const PLAY_H = 184;
/** The in-level palette (JE_loadPic 3 → pcxpal[2]), as the HUD uses. */
const LEVEL_PALETTE = 5;
/** The glyph shade the colour is taken at (the font's bright body; 14 and 15 of the bank are black and white). */
const BODY_SHADE = 14;

export interface SecretLevelBanner {
  text: string;
  /** The text's centre and top, and the glyphs' height, as fractions of the playfield. */
  centerX: number;
  top: number;
  height: number;
  /** blit_sprite_hv_unsafe's colour for the body shade this frame: bank 15, shade + flash - 8. */
  color: string;
  /** The drop shadow's colour (blit_sprite_dark), the bank's darkest step. */
  shadow: string;
}

function rgb(index: number): string {
  const pal = g.res?.palettes?.[LEVEL_PALETTE];
  if (!pal) return "#ffffff";
  return `rgb(${vga6To8(pal[index * 3])}, ${vga6To8(pal[index * 3 + 1])}, ${vga6To8(pal[index * 3 + 2])})`;
}

/** The banner to show this frame, or null while displayTime is 0. */
export function secretLevelBanner(): SecretLevelBanner | null {
  if (g.displayTime <= 0) return null;
  const text = g.miscText[SECRET_TEXT_INDEX] ?? "";
  if (!text) return null;
  const sprites = g.res?.spriteTables?.[FONT_SHAPES]?.sprites;
  const width = sprites ? JE_textWidth(text, FONT_SHAPES) : text.length * 11;
  const glyph = sprites?.[fontMap["S".charCodeAt(0)]];
  const height = glyph?.height ?? 14;
  // (JE_byte)flash - 8 read back as the Sint8 `value`: -8 .. -3.
  const shade = Math.max(0, Math.min(15, BODY_SHADE + g.flash - 8));
  return {
    text,
    centerX: (SECRET_X + width / 2 - PLAY_LEFT) / PLAY_W,
    top: SECRET_Y / PLAY_H,
    height: height / PLAY_H,
    color: rgb(SECRET_BANK * 16 + shade),
    shadow: rgb(SECRET_BANK * 16),
  };
}
