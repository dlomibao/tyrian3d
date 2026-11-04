// Dynamic resolution (DECISIONS.md D91): when the GPU can't hold 60 fps, draw fewer pixels.
//
// The view reports each frame's start time and how long its own work took on the main thread. The
// scaler watches the frame intervals over a window: if many frames come later than 60 fps allows
// while the main thread's share is small (so it's the GPU, or the compositor, that's late), it lowers
// the render scale a step; after a long spell without late frames it raises it again, waiting longer
// each time a raise has to be undone. At 60 fps (or faster: a 120 Hz screen alternating 8 and 17 ms
// frames is fine) it never moves, so the picture is the full-resolution one whenever the GPU keeps up.

/** A frame later than this (ms) missed 60 fps: one and a quarter 60 Hz frames. */
export const LATE_MS = 1000 / 60 * 1.25;
/** Frames per decision window. */
export const WINDOW = 60;
/** Share of late frames in a window that lowers the scale. */
export const LATE_SHARE = 0.25;
/** The main thread's median work per frame must stay under this (ms) for a lowering. */
export const CPU_LIMIT_MS = 10;
/** Each step multiplies the scale by this. */
export const STEP = 0.8;
/** The lowest scale (of the device pixel ratio, itself capped by Settings.maxPixelRatio). */
export const MIN_SCALE = 0.5;
/** Seconds without late frames before a raise; doubled each time a raise is undone, up to MAX_HOLD_S. */
export const HOLD_S = 5;
export const MAX_HOLD_S = 80;
/** A lowering this soon (s) after a raise undoes it: the next raise waits twice as long. */
const UNDO_S = 4;
/** Intervals longer than this (ms) are pauses (a hidden tab, a loading screen): the window restarts. */
const PAUSE_MS = 250;

export class ResolutionScaler {
  /** The render scale, MIN_SCALE..1. */
  scale = 1;
  /** Off: always 1 (Options → Resolution: Full). */
  enabled = true;
  private last = -1;
  private readonly intervals: number[] = [];
  private readonly cpu: number[] = [];
  /** Seconds since the last late window, and since the last raise. */
  private calm = 0;
  private sinceRaise = Infinity;
  private hold = HOLD_S;

  /** Back to full scale, the history forgotten; true if the scale changed. */
  reset(): boolean {
    const changed = this.scale !== 1;
    this.scale = 1;
    this.last = -1;
    this.intervals.length = 0;
    this.cpu.length = 0;
    this.calm = 0;
    this.hold = HOLD_S;
    this.sinceRaise = Infinity;
    return changed;
  }

  /**
   * One frame: `now` its start (ms), `cpuMs` the main thread's work in it. Returns true when the
   * scale changed (the caller resizes its drawing buffer).
   */
  frame(now: number, cpuMs: number): boolean {
    if (!this.enabled) {
      const changed = this.scale !== 1;
      this.scale = 1;
      this.last = now;
      return changed;
    }
    const dt = this.last < 0 ? 0 : now - this.last;
    this.last = now;
    if (dt <= 0 || dt > PAUSE_MS) {
      this.intervals.length = 0;
      this.cpu.length = 0;
      return false;
    }
    this.intervals.push(dt);
    this.cpu.push(cpuMs);
    this.calm += dt / 1000;
    this.sinceRaise += dt / 1000;
    if (this.intervals.length < WINDOW) return false;
    const late = this.intervals.filter((t) => t > LATE_MS).length / this.intervals.length;
    const cpu = median(this.cpu);
    this.intervals.length = 0;
    this.cpu.length = 0;
    if (late >= LATE_SHARE && cpu < CPU_LIMIT_MS) {
      this.calm = 0;
      if (this.scale <= MIN_SCALE) return false;
      if (this.sinceRaise < UNDO_S) this.hold = Math.min(MAX_HOLD_S, this.hold * 2);
      this.scale = Math.max(MIN_SCALE, this.scale * STEP);
      return true;
    }
    if (late > 0.05) this.calm = 0;
    if (this.scale < 1 && this.calm >= this.hold) {
      this.scale = Math.min(1, this.scale / STEP);
      if (this.scale > 0.999) this.scale = 1;
      this.calm = 0;
      this.sinceRaise = 0;
      return true;
    }
    return false;
  }
}

function median(a: number[]): number {
  const s = [...a].sort((x, y) => x - y);
  return s[Math.floor(s.length / 2)] ?? 0;
}
