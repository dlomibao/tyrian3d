// Two display choices of the in-game screen (DECISIONS.md D61), kept like the terrain look (D57):
//   interface  "frame": the remastered bronze frame, the original's sidebar and message bar drawn
//              around the playfield (src/app/hudFrame.ts); "minimal": the light HUD over a
//              full-window view (the HUD before D61).
//   camera     "overhead": straight down, so the playfield is a rectangle like the original's;
//              "tilted": leaning 15° from straight down, the default (src/render/view.ts);
//              "steep": 32°, the look before D61. A stored "tilted" from before the gentle
//              tilt meant 32°; it now gets the new default, as the user decided.
// Options → Graphics sets them and the prefs keep them (app/prefs.ts); `?interface=frame|minimal`
// and `?camera=overhead|tilted|steep` override them for the page. Listeners hear every change.

/** One persisted choice among a few values: the URL's, else the stored one, else the default. */
export class DisplayChoice<T extends string> {
  private stored: T | undefined;
  private override: T | undefined;
  private readonly listeners = new Set<(value: T) => void>();

  constructor(
    /** The URL parameter that overrides it. */
    readonly param: string,
    /** Offered in Options, in this order. */
    readonly values: readonly T[],
    readonly fallback: T,
    search: string | undefined = typeof location === "undefined" ? undefined : location.search,
  ) {
    this.override = this.fromSearch(search);
  }

  is(v: unknown): v is T {
    return (this.values as readonly unknown[]).includes(v);
  }

  /** The URL's choice, or undefined. */
  fromSearch(search: string | undefined): T | undefined {
    const v = search === undefined ? null : new URLSearchParams(search).get(this.param);
    return this.is(v) ? v : undefined;
  }

  /** The choice in effect. */
  get(): T {
    return this.override ?? this.stored ?? this.fallback;
  }

  /** The stored choice (prefs), undefined if the player never chose. */
  storedValue(): T | undefined {
    return this.stored;
  }

  /** Set from the prefs at start-up; the URL's choice still wins. */
  load(v: unknown): void {
    const before = this.get();
    this.stored = this.is(v) ? v : undefined;
    if (this.get() !== before) this.notify();
  }

  /** The player's choice (Options): kept, and it replaces the URL's for the rest of the page. */
  set(v: T): void {
    const before = this.get();
    this.stored = v;
    this.override = undefined;
    if (this.get() !== before) this.notify();
  }

  /** For tests: forget the stored choice and set the URL's. */
  reset(urlValue?: T): void {
    this.stored = undefined;
    this.override = urlValue;
  }

  /** Call `fn` whenever the choice changes; returns the unsubscribe. */
  listen(fn: (value: T) => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private notify(): void {
    const v = this.get();
    for (const fn of this.listeners) fn(v);
  }
}

export type InterfaceStyle = "frame" | "minimal";
/** "auto": dynamic resolution, fewer pixels only while the GPU can't hold 60 fps (D91); "full": never. */
export type ResolutionStyle = "auto" | "full";
export type CameraStyle = "overhead" | "tilted" | "steep";

/** The in-game interface: the remastered frame unless the player says otherwise. */
export const interfaceStyle = new DisplayChoice<InterfaceStyle>("interface", ["frame", "minimal"], "frame");

/** The game camera: the gentle tilt unless the player says otherwise. */
export const cameraStyle = new DisplayChoice<CameraStyle>("camera", ["overhead", "tilted", "steep"], "tilted");

/** The render resolution: dynamic (D91) unless the player says otherwise. */
export const resolutionStyle = new DisplayChoice<ResolutionStyle>("resolution", ["auto", "full"], "auto");
