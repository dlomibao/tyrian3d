// The sprite frames a model replaces, as the game draws them, for the model viewer.

import { decodeSprite2 } from "../data/sprites";
import type { SpriteModelEntry } from "../render/spriteModels";

/** One sprite object drawn as part of a frame: a 12x14 tile or a 2x2 block (index, +1, +19, +20). */
export interface FramePart {
  sheet: string;
  size: 1 | 2;
  index: number;
  /** Top-left within the frame, sprite px. */
  x: number;
  y: number;
}

/** One frame of a model's sprite (or of a whole assembly): its parts and its size in sprite px. */
export interface SpriteFrame {
  parts: FramePart[];
  width: number;
  height: number;
  /** Shown under the frame, e.g. "#153" or "bank -2". */
  label: string;
}

const single = (sheet: string, size: 1 | 2, index: number, label: string): SpriteFrame => ({
  parts: [{ sheet, size, index, x: 0, y: 0 }],
  width: size * 12,
  height: size * 14,
  label,
});

/**
 * Every frame a model replaces: each listed frame, and for a player ship its banking frames
 * (frames[0] + n * step, n = -max..max). The Nort ship (tyrian.shp#8 sprite 220, no banking) is
 * drawn as two halves, 220 and 222 (blitShipHalves), so its frame is 48 px wide.
 */
export function entryFrames(entry: SpriteModelEntry): SpriteFrame[] {
  const out: SpriteFrame[] = [];
  for (const ref of entry.sprites) {
    if (ref.bank) {
      for (let n = -ref.bank.max; n <= ref.bank.max; n++) {
        out.push(single(ref.sheet, ref.size, ref.frames[0] + n * ref.bank.step, n === 0 ? "level" : `bank ${n}`));
      }
      continue;
    }
    for (const index of ref.frames) {
      if (ref.sheet === "tyrian.shp#8" && index === 220) {
        out.push({
          parts: [{ sheet: ref.sheet, size: 2, index: 220, x: 0, y: 0 }, { sheet: ref.sheet, size: 2, index: 222, x: 24, y: 0 }],
          width: 48,
          height: 28,
          label: "#220 + #222",
        });
      } else {
        out.push(single(ref.sheet, ref.size, index, `#${index}`));
      }
    }
  }
  return out;
}

/** A multi-piece object (src/viewer/assemblies.json): each piece's centre relative to the whole's. */
export interface AssemblyLayout {
  name: string;
  pieces: { sheet: string; size: number; index: number; x: number; y: number }[];
}

/** An assembly as one frame: every piece at its place, the frame's centre on the object's centre. */
export function assemblyFrame(layout: AssemblyLayout): SpriteFrame {
  const half = (p: AssemblyLayout["pieces"][number]) => [p.size * 6, p.size * 7];
  const left = Math.min(...layout.pieces.map((p) => p.x - half(p)[0]));
  const right = Math.max(...layout.pieces.map((p) => p.x + half(p)[0]));
  const top = Math.min(...layout.pieces.map((p) => p.y - half(p)[1]));
  const bottom = Math.max(...layout.pieces.map((p) => p.y + half(p)[1]));
  // Keep the object's centre in the middle of the frame (the layout is centred on it).
  const w = 2 * Math.max(right, -left), h = 2 * Math.max(bottom, -top);
  return {
    parts: layout.pieces.map((p) => ({
      sheet: p.sheet,
      size: p.size === 1 ? 1 : 2,
      index: p.index,
      x: w / 2 + p.x - half(p)[0],
      y: h / 2 + p.y - half(p)[1],
    })),
    width: w,
    height: h,
    label: `${layout.pieces.length} pieces`,
  };
}

/**
 * The frame's picture as palette indices, -1 = transparent, row by row. `sheetData` returns a
 * sheet's bytes by id; null if one is missing.
 */
export function composeFrame(sheetData: (sheet: string) => Uint8Array | null, frame: SpriteFrame): Int16Array | null {
  const pic = new Int16Array(frame.width * frame.height).fill(-1);
  for (const part of frame.parts) {
    const data = sheetData(part.sheet);
    if (!data) return null;
    const tiles = part.size === 1 ? [[0, 0, 0]] : [[0, 0, 0], [1, 12, 0], [19, 0, 14], [20, 12, 14]];
    for (const [offset, tx, ty] of tiles) {
      const s = decodeSprite2(data, part.index + offset);
      for (let y = 0; y < Math.min(14, s.height); y++)
        for (let x = 0; x < 12; x++) {
          const c = s.pixels[y * 12 + x];
          const px = part.x + tx + x, py = part.y + ty + y;
          if (c >= 0 && px >= 0 && px < frame.width && py >= 0 && py < frame.height) pic[py * frame.width + px] = c;
        }
    }
  }
  return pic;
}
