// Palette fades as a solid layer over the screen, and the C's frame timer they run on.
//
// palette.c's fade_palette / fade_solid move every colour from the displayed palette to the target
// in `steps` frames, a 1/steps share of what's left each frame (step_fade_palette), which is a
// straight line from start to target. Blending a black (or white) layer over the picture with an
// opacity on the same line gives the same colours, without touching the renderer's palette, and
// it covers the HUD and anything else on screen too.
//
// JE_main's level fades (tyrian2.c L716 fade_palette(colors, 50) after the level loads, L639
// fade_black(10) after a death, and JE_endLevelAni's fade_black(15) after the level-end text) use
// the layer over the 3D view, levelFade(); the story screens have their own.

import "./story.css";
import { CLASSIC_TICK_MS } from "../core/timing";

/** One setFrameCount(1) period (nortsong.c framePeriod at speed 0x4300): half a game tick, ~14.4 ms. */
export const FRAME_MS = CLASSIC_TICK_MS / 2;

/** The longest sleep between checks for input while waiting (SDL_POLL_INTERVAL in the C is 5 ms). */
const POLL_MS = 5;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/**
 * nortsong.c's frame timers: setFrameCount / getFrameCountTicks / waitUntilElapsed, and the
 * second timer (setFrameCount2 / getFrameCount2Ticks) the warning bars use. Times are ms.
 */
export class FrameClock {
  private frameCountEnd = performance.now();
  private frameCount2End = performance.now();

  /** setFrameCount (nortsong.c L64-75): `frameCount` periods on from now, keeping a partial one. */
  setFrameCount(frameCount: number): void {
    this.frameCountEnd = FrameClock.advance(this.frameCountEnd, frameCount);
  }

  setFrameCount2(frameCount2: number): void {
    this.frameCount2End = FrameClock.advance(this.frameCount2End, frameCount2);
  }

  private static advance(end: number, frames: number): number {
    // Keep the partial timer period that has already elapsed.
    const now = performance.now();
    const diff = now - end;
    if (diff >= FRAME_MS) end = now - (diff % FRAME_MS);
    else if (-diff >= FRAME_MS) end = now + (-diff % FRAME_MS);
    return end + frames * FRAME_MS;
  }

  /** getFrameCountTicks() == 0 */
  elapsed(): boolean {
    return performance.now() >= this.frameCountEnd;
  }

  /** getFrameCount2Ticks() == 0 */
  elapsed2(): boolean {
    return performance.now() >= this.frameCount2End;
  }

  /** How long until the frame ends, in ms (0 if it has). */
  remaining(): number {
    return Math.max(0, this.frameCountEnd - performance.now());
  }

  /** waitUntilElapsed: returns at once if the frame is already over, so a late caller catches up. */
  async waitUntilElapsed(): Promise<void> {
    while (!this.elapsed()) await sleep(Math.min(this.remaining(), POLL_MS));
  }
}

export class FadeLayer {
  readonly el: HTMLDivElement;
  /** The layer's colour (8-bit RGB) and opacity: 0 shows the screen, 1 hides it. */
  private rgb = [0, 0, 0];
  private alpha = 0;
  /** Bumped by every set() and fade(), so an older fade stops when a newer one starts. */
  private run = 0;

  constructor(className: string) {
    this.el = document.createElement("div");
    this.el.className = className;
    this.el.setAttribute("aria-hidden", "true");
    this.apply();
  }

  /** The layer's opacity now (0: screen fully shown). */
  get opacity(): number {
    return this.alpha;
  }

  /** Show `rgb` at opacity `alpha` at once (set_palette); stops a fade in progress. */
  set(alpha: number, rgb: readonly number[] = this.rgb): void {
    this.run++;
    this.alpha = alpha;
    this.rgb = [...rgb];
    this.apply();
  }

  /**
   * One step_fade_palette: move a 1/steps share of the way to `rgb` at opacity `alpha`. A clear
   * layer shows no colour, so it takes the target's colour first (a fade from the picture to white
   * is white all the way, as the palette's would be).
   */
  step(alpha: number, rgb: readonly number[], steps: number): void {
    if (this.alpha === 0) this.rgb = [...rgb];
    this.alpha += (alpha - this.alpha) / steps;
    this.rgb = this.rgb.map((c, i) => c + (rgb[i] - c) / steps);
    this.apply();
  }

  /**
   * fade_palette / fade_solid (palette.c L146-190): `steps` frames, one step each, on `clock`.
   * Resolves when done, or early if a later set() or fade() takes over.
   */
  async fade(alpha: number, steps: number, rgb: readonly number[] = this.rgb, clock = new FrameClock()): Promise<void> {
    const run = ++this.run;
    for (; steps > 0; steps--) {
      clock.setFrameCount(1);
      this.step(alpha, rgb, steps);
      await clock.waitUntilElapsed();
      if (run !== this.run) return;
    }
  }

  private apply(): void {
    const [r, g, b] = this.rgb.map(Math.round);
    this.el.style.background = `rgb(${r} ${g} ${b})`;
    this.el.style.opacity = String(this.alpha);
    this.el.hidden = this.alpha <= 0;
  }
}

export const BLACK = [0, 0, 0] as const;
export const WHITE = [255, 255, 255] as const;

let level: FadeLayer | null = null;

/** The fade layer over the 3D view and HUD, created on first use (so later overlays are above it). */
export function levelFade(): FadeLayer {
  if (!level) {
    level = new FadeLayer("level-fade");
    document.body.appendChild(level.el);
  }
  return level;
}
