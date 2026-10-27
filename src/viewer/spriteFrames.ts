// The sprite frames a model replaces, as the game draws them, for the model viewer.

import { decodeSprite2 } from "../data/sprites";
import type { SpriteModelEntry } from "../render/spriteModels";

/** One frame of a model's sprite: what to fetch and how big the composed picture is. */
export interface SpriteFrame {
  sheet: string;
  /** Sprite index of the top-left tile. */
  index: number;
  /** 1 = one 12x14 tile, 2 = a 2x2 block (index, +1, +19, +20). */
  size: 1 | 2;
  /** Composed picture size in sprite px. */
  width: number;
  height: number;
  /** Shown under the frame, e.g. "#153" or "bank -2". */
  label: string;
  /** A second 2x2 block drawn to the right (the Nort ship's right half). */
  rightHalf?: number;
}

/**
 * Every frame a model replaces: each listed frame, and for a player ship its banking frames
 * (frames[0] + n * step, n = -max..max). The Nort ship (tyrian.shp#8 sprite 220, no banking) is
 * drawn as two halves, 220 and 222 (blitShipHalves), so its frame is 48 px wide.
 */
export function entryFrames(entry: SpriteModelEntry): SpriteFrame[] {
  const out: SpriteFrame[] = [];
  for (const ref of entry.sprites) {
    const w = ref.size * 12, h = ref.size * 14;
    if (ref.bank) {
      for (let n = -ref.bank.max; n <= ref.bank.max; n++) {
        out.push({ sheet: ref.sheet, index: ref.frames[0] + n * ref.bank.step, size: ref.size, width: w, height: h, label: n === 0 ? "level" : `bank ${n}` });
      }
      continue;
    }
    for (const index of ref.frames) {
      if (ref.sheet === "tyrian.shp#8" && index === 220) {
        out.push({ sheet: ref.sheet, index, size: 2, width: 48, height: 28, label: "#220 + #222", rightHalf: 222 });
      } else {
        out.push({ sheet: ref.sheet, index, size: ref.size, width: w, height: h, label: `#${index}` });
      }
    }
  }
  return out;
}

/** The frame's picture as palette indices, -1 = transparent, row by row. */
export function composeFrame(sheetData: Uint8Array, frame: SpriteFrame): Int16Array {
  const pic = new Int16Array(frame.width * frame.height).fill(-1);
  const blit = (index: number, ox: number, oy: number) => {
    const s = decodeSprite2(sheetData, index);
    for (let y = 0; y < Math.min(14, s.height); y++)
      for (let x = 0; x < 12; x++) {
        const c = s.pixels[y * 12 + x];
        if (c >= 0) pic[(oy + y) * frame.width + ox + x] = c;
      }
  };
  const block = (index: number, ox: number) => {
    if (frame.size === 1) return blit(index, ox, 0);
    blit(index, ox, 0);
    blit(index + 1, ox + 12, 0);
    blit(index + 19, ox, 14);
    blit(index + 20, ox + 12, 14);
  };
  block(frame.index, 0);
  if (frame.rightHalf !== undefined) block(frame.rightHalf, 24);
  return pic;
}
