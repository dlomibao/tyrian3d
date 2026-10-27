// The data cube reader's input and clock (src/app/dataCubes.ts draws it). The scrolling rules are
// the C's, in src/sim/cubes.ts (cubeReader_frame); this turns the interface framework's input into
// that function's per-frame input, runs it at the C's frame rate, and says where to draw the text
// between two frames so the scroll moves smoothly at any display rate.
//
// The C reads keysactive every frame, so a held key keeps scrolling. The framework hands a screen
// presses instead (src/ui/nav.ts: the keyboard's own repeat, a pad direction repeating every 110 ms
// after 380 ms), so a press counts as the key being down for HOLD_FRAMES frames. That is shorter
// than a line takes (12 frames at a pixel a frame, 6 at Page Down's two), so a tap still moves
// exactly one line as in the C; and longer than the gap between repeats, so a held key or direction
// keeps the text moving through the line ends. Only the first line of a hold can pause briefly, until
// the repeats start. A click is the C's "new click": one frame.
// Pads have no Page keys; a shoulder button pages by holding the C's Page Down for one page's worth
// of frames.

import { CLASSIC_TICK_MS } from "../core/timing";
import { CUBE_LINE_HEIGHT, CUBE_READER_LINES, cubeReader, cubeReader_frame, type cube_struct, type CubeReaderInput } from "../sim/cubes";

/** A press: the keys and mouse halves cubeReader_frame reads. */
export type CubeReaderPress = keyof CubeReaderInput;

/** Frames a key or direction press counts as held: under a Page Down line (6), over a pad repeat (~4). */
export const HOLD_FRAMES = 6;

/** Frames of Page Down (2 pixels a frame) that scroll one page of the reader's lines. */
export const PAGE_FRAMES = (CUBE_READER_LINES * CUBE_LINE_HEIGHT) / 2;

type HeldKey = "up" | "down" | "pageUp" | "pageDown";
const OPPOSITE: Record<HeldKey, HeldKey> = { up: "down", down: "up", pageUp: "pageDown", pageDown: "pageUp" };

/** Longest catch-up after a stall (a background tab, a slow frame), so the text doesn't race. */
const MAX_CATCH_UP_MS = 250;

export class CubeReaderControl {
  /** Frames each key is still down for. */
  private held = new Map<HeldKey, number>();
  /** Clicks since the last frame: down for the next frame only. */
  private clicks: CubeReaderInput = {};
  /** A pad page: frames of Page Up/Down still to hold, and which. */
  private pageFrames = 0;
  private pageDown = true;
  /** Time not yet run as frames (ms). */
  private carry = 0;
  /** yLoc before and after the last frame, to draw between them. */
  private from = 0;
  private to = 0;

  /** A key or pad direction (down for the next HOLD_FRAMES frames), or a click (the next frame). */
  press(p: CubeReaderPress): void {
    if (p === "clickUp" || p === "clickDown") return void (this.clicks[p] = true);
    // A press lets go of the opposite key, as a player turning round would (the C lets down win
    // when both are down).
    this.held.delete(OPPOSITE[p]);
    this.held.set(p, HOLD_FRAMES);
  }

  /** A pad shoulder: one page down (or up). */
  page(down: boolean): void {
    this.pageDown = down;
    this.pageFrames = PAGE_FRAMES;
  }

  /** yLoc was set from outside (opening a cube, Home/End, the wheel or a drag): draw it as it is. */
  sync(): void {
    this.held.clear();
    this.clicks = {};
    this.pageFrames = 0;
    this.carry = 0;
    this.from = this.to = cubeReader.yLoc;
  }

  /** One of the C's frames. */
  frame(c: cube_struct): void {
    const input = this.clicks;
    this.clicks = {};
    for (const [k, n] of this.held) {
      input[k] = true;
      if (n > 1) this.held.set(k, n - 1);
      else this.held.delete(k);
    }
    if (this.pageFrames > 0) {
      this.pageFrames--;
      if (this.pageDown) input.pageDown = true;
      else input.pageUp = true;
    }
    this.from = cubeReader.yLoc;
    cubeReader_frame(c, input);
    this.to = cubeReader.yLoc;
    // At the top or the bottom the C stops the page; so does the pad's.
    if (cubeReader.yChg === 0 && this.from === this.to) this.pageFrames = 0;
  }

  /**
   * Let `ms` pass: run the frames that fall in it, and return the yLoc to draw now, in C pixels
   * (between the last two frames' positions, by how far into the next frame we are).
   */
  advance(c: cube_struct, ms: number): number {
    this.carry = Math.min(this.carry + Math.max(0, ms), MAX_CATCH_UP_MS);
    while (this.carry >= CLASSIC_TICK_MS) {
      this.carry -= CLASSIC_TICK_MS;
      this.frame(c);
    }
    return this.from + (this.to - this.from) * (this.carry / CLASSIC_TICK_MS);
  }
}
