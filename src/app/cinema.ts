// The stage the screens between levels and at an episode's end play on (storyScreens.ts,
// episodeEnd.ts): one interface-framework screen (src/ui) that fills the window at any aspect
// ratio. The C drew all of them on the 320x200 VGA screen; here that screen is split into layers:
//
// - the picture: a canvas STAGE_SCALE times 320x200 (1920x1200, the remastered pictures' size)
//   that the pictures, pans and the ending animation are drawn on, letterboxed in the window and
//   cropped by up to a fifth on screens wider or taller than 16:10, over a blurred copy of itself
//   that fills the rest (so a phone held upright still sees a picture, not black bars);
// - the text: JE_displayText's lines on a translucent framework panel in the interface's type,
//   each character glowing in as JE_outCharGlow made it (glowLook), the prompt a key hint;
// - the warning bars along the top and bottom edges, in the palette colour JE_updateWarning picks;
// - a layer for the screens that aren't pictures (the credits, the next episode's title);
// - the palette fades: a black or white layer over all of it (fade.ts), as the C's palette faded
//   the whole screen, text included.
//
// Input comes from the framework's navigation (src/ui/nav.ts) instead of the screens' own key and
// pad listeners: any key, pad button, click or tap is the C's key press (getInput), Escape / B (or
// the Skip button, for touch) is also ESCPressed, which the story screens use to skip a scene.
// Consecutive screens share the stage, so nothing flashes between them; it closes once nothing
// has used it for a moment (the item screen or the level is next).

import "./cinema.css";
import { button, h, keyGlyphs, keyIntent, reveal, showScreen, ui, type BackdropMood, type Screen } from "../ui";
import { BLACK, FadeLayer, FrameClock, levelFade } from "./fade";

/** The picture canvas is this many times 320x200. */
export const STAGE_SCALE = 6;
export const STAGE_W = 320 * STAGE_SCALE;
export const STAGE_H = 200 * STAGE_SCALE;

/** An 8-bit RGB palette, 256 × [r, g, b]: `colors` in the C. */
export type Colors = Uint8Array;

/** The CSS colour of palette entry `i`. */
export const cssColor = (c: Colors, i: number) => `rgb(${c[i * 3]} ${c[i * 3 + 1]} ${c[i * 3 + 2]})`;

/**
 * How a character looks at JE_outCharGlow's glow value (blit_sprite_hv's brightness offset): it
 * starts at -8, nearly black, brightens one step at a time to 10, well over its normal shade, and
 * settles back to 0. Below 0 it's dimmer (opacity); above 0 it runs hot (heat 0..1: lighter, with
 * a glow). Pure, for tests.
 */
export function glowLook(value: number): { opacity: number; heat: number } {
  const opacity = value >= 0 ? 1 : Math.max(0, Math.min(1, (value + 9) / 9));
  const heat = Math.max(0, Math.min(1, value / 10));
  return { opacity: Math.round(opacity * 1000) / 1000, heat: Math.round(heat * 1000) / 1000 };
}

/**
 * The text colour for colour bank `bank` of `colors`, as JE_outCharGlow draws it: its normal shade
 * (the glyphs' bright pixels, shade 12) lightened a quarter toward white so it reads on the panel,
 * and its brightest (15) for the glow and the `~` highlights. Pure, for tests.
 */
export function bankTint(colors: Colors, bank: number): { ink: string; hot: string } {
  const at = (shade: number, lift: number) => {
    const i = (((bank & 0xf) << 4) | shade) * 3;
    const c = [0, 1, 2].map((k) => Math.round(colors[i + k] + (255 - colors[i + k]) * lift));
    return `rgb(${c[0]} ${c[1]} ${c[2]})`;
  };
  return { ink: at(12, 0.25), hot: at(15, 0.15) };
}

/** One line of story text, split for display: centred (it was indented to the middle), and its characters. */
export interface StoryLine {
  centered: boolean;
  /** Each character with its index in the original string (JE_outCharGlow's z) and whether it's in `~highlight~`. */
  chars: { z: number; ch: string; highlight: boolean }[];
}

/**
 * Split a line of the episode script's text. `~` toggles highlighting (JE_outText's +4 brightness)
 * and isn't shown. A line indented by 8 spaces or more was centred by hand in the original's
 * fixed layout (`"                     MICROSOL!"`), so it's centred and its indent dropped. Pure.
 */
export function parseStoryLine(s: string): StoryLine {
  const indent = s.length - s.trimStart().length;
  const centered = indent >= 8 && s.trim() !== "";
  const chars: StoryLine["chars"] = [];
  let highlight = false;
  for (let z = centered ? indent : 0; z < s.length; z++) {
    if (s[z] === "~") highlight = !highlight;
    else chars.push({ z, ch: s[z], highlight });
  }
  if (centered) while (chars.length && chars[chars.length - 1].ch === " ") chars.pop();
  return { centered, chars };
}

/**
 * Whether the break after `line` only wrapped a paragraph to the original's 300-pixel width (so a
 * narrow screen may join it to the next line) rather than ending it. Pure.
 */
export function isSoftBreak(line: string, next: string | undefined): boolean {
  if (next === undefined || line.trim() === "" || next.trim() === "") return false;
  if (parseStoryLine(line).centered || parseStoryLine(next).centered) return false;
  return line.trimEnd().length >= 40;
}

/** JE_outCharGlow's view of a line: light character z at a glow value, or show it all at once. */
export interface GlowLine {
  /** blit_sprite_hv of character z (its index in the line) at glow `value`. */
  glow(z: number, value: number): void;
  /** JE_textShade: the whole line, settled. */
  shade(): void;
}

export interface TextOptions {
  lines: string[];
  /** The palette and colour bank the C drew the text in. */
  colors: Colors;
  bank: number;
  /** warningRed: the text sits at the top (the C drew it from y 2). */
  top?: boolean;
  /** The C's prompt ("Press a key"): shown as a key hint, glowing in over as many steps as its text did. */
  prompt: string;
}

export interface TextHandle {
  lines: GlowLine[];
  /** The prompt: a key hint that glows in as the C's prompt text did. */
  prompt: GlowLine;
}

/** What the stage shows behind its content: a picture (opaque black) or a framework backdrop mood. */
export type StageMode = "picture" | Exclude<BackdropMood, "none">;

/** What the corner button and its keys do: skip a scene (story), skip (anim, credits), or nothing. */
export type SkipKind = "scene" | "skip" | "none";

export class Cinema {
  readonly screen: Screen;
  /** The picture: 1920x1200, standing for the 320x200 screen. */
  readonly canvas: HTMLCanvasElement;
  readonly ctx: CanvasRenderingContext2D;
  readonly fade = new FadeLayer("cinema-fade");
  readonly clock = new FrameClock();
  /** For screens that aren't pictures (credits, titles). Cleared by clearOverlay(). */
  readonly layer: HTMLDivElement;
  /** Something has been drawn on the picture since the stage opened or was blanked. */
  showing = false;
  /** What's behind the content (setMode). */
  mode: StageMode = "picture";
  /** ESCPressed: Escape, pad B or the Skip button since the story last cleared it. */
  escape = false;

  private readonly ambient: CanvasRenderingContext2D;
  private readonly bars: HTMLDivElement[];
  private readonly skipButton: HTMLButtonElement;
  private pending = false;
  /** Bumped whenever the panel's content changes, so a fading text isn't cleared after new text came. */
  private textGeneration = 0;

  constructor() {
    this.screen = showScreen({
      id: "cinema",
      backdrop: "none",
      scrim: false,
      label: "Story",
      onKey: (e) => this.onKey(e),
      onIntent: (intent) => {
        // Any intent is a key press (a direction too: the C took any key); back is also Esc.
        if (intent === "back") this.escape = true;
        this.pending = true;
        return true;
      },
      onPadButton: () => (this.pending = true),
    });
    const root = this.screen.root;
    root.classList.add("is-picture");

    this.canvas = h("canvas", { class: "cinema-picture", attrs: { width: String(STAGE_W), height: String(STAGE_H), "aria-hidden": "true" } });
    this.ctx = this.canvas.getContext("2d")!;
    // A tiny copy of the picture, scaled up and blurred by CSS behind the letterboxed one.
    const ambient = h("canvas", { class: "cinema-ambient", attrs: { width: "48", height: "30", "aria-hidden": "true" } });
    this.ambient = ambient.getContext("2d")!;
    this.bars = [h("div", { class: "cinema-bar cinema-bar--top" }), h("div", { class: "cinema-bar cinema-bar--bottom" })];
    this.layer = h("div", { class: "cinema-layer" });
    this.skipButton = button({
      label: "Skip",
      variant: "ghost",
      class: "cinema-skip",
      hint: { key: "Esc", pad: "B" },
      onPress: () => {
        this.escape = true;
        this.pending = true;
      },
    });
    // The button acts on its click; the stage's own tap would count as a key press first.
    this.skipButton.addEventListener("pointerdown", (e) => e.stopPropagation());
    this.screen.panel.classList.add("cinema-text");
    this.screen.panel.hidden = true;
    root.prepend(ambient, h("div", { class: "cinema-frame" }, this.canvas));
    root.append(...this.bars, this.layer, this.fade.el, this.skipButton);
    root.addEventListener("pointerdown", () => (this.pending = true));

    this.blank();
    this.setSkip("none");
  }

  get open(): boolean {
    return this.screen.open;
  }

  // --- input (keyboard.c's newkey / mousedown / joystick; ESCPressed) ---

  /** Raw keys: any key that isn't an intent is a press too (the C took any key). */
  private onKey(e: KeyboardEvent): boolean {
    if (e.ctrlKey || e.metaKey || e.altKey) return false;
    if (["Shift", "Control", "Alt", "Meta", "CapsLock"].includes(e.key)) return true;
    if (e.repeat) return true; // a held key is one press
    if (keyIntent(e.code, e.key)) return false; // an intent: onIntent
    this.pending = true;
    // Function keys still count, but keep their browser actions (reload, dev tools).
    return !/^F\d+$/.test(e.key);
  }

  /** getInput (keyboard.c): a key, click, tap or pad button pressed since the last call. */
  getInput(): boolean {
    const pressed = this.pending;
    this.pending = false;
    return pressed;
  }

  /** keyboardClearInput / mouseClearInput */
  clearInput(): void {
    this.pending = false;
  }

  /** waitUntilGetInputOrElapsed (keyboard.c L451-469): true if input came before the frame ended. */
  async waitUntilGetInputOrElapsed(): Promise<boolean> {
    for (;;) {
      if (this.getInput()) return true;
      if (this.clock.elapsed()) return false;
      await sleep(Math.min(this.clock.remaining(), 5));
    }
  }

  /** waitUntilGetInput (keyboard.c L438-449) */
  async waitUntilGetInput(): Promise<void> {
    while (!this.getInput()) await sleep(10);
  }

  // --- look ---

  /** A picture on black (the story) or text over a framework backdrop (titles, codes). */
  setMode(mode: StageMode): void {
    this.mode = mode;
    const root = this.screen.root;
    root.classList.toggle("is-picture", mode === "picture");
    const mood: BackdropMood = mode === "picture" ? "none" : mode;
    this.screen.opts.backdrop = mood;
    ui.backdrop?.setMood(mood);
    // The backdrop draws in the game's canvas, under the level fade.
    if (mode !== "picture") levelFade().set(0);
  }

  /** The corner Skip button: Esc skips the scene (story), any key skips (anim, credits), or none. */
  setSkip(kind: SkipKind): void {
    this.skipButton.hidden = kind === "none";
    this.skipButton.querySelector("span")!.textContent = kind === "scene" ? "Skip scene" : "Skip";
  }

  // --- the picture ---

  /** Copy the picture to the blurred fill behind it. Call after drawing on `ctx`. */
  present(): void {
    this.ambient.drawImage(this.canvas, 0, 0, this.ambient.canvas.width, this.ambient.canvas.height);
    this.showing = true;
  }

  /** A fresh stage: black, faded out, nothing over it (the C's palette after the item screen or a level). */
  blank(): void {
    this.ctx.fillStyle = "#000";
    this.ctx.fillRect(0, 0, STAGE_W, STAGE_H);
    this.present();
    this.fade.set(1, BLACK);
    this.clearOverlay();
    this.setMode("picture");
    this.showing = false;
  }

  /**
   * Take the text, warning bars and layer content off (a new picture replaces the screen). With
   * `fadeOut` the text fades away instead (a pan carries it off with the old picture).
   */
  clearOverlay(fadeOut = false): void {
    const panel = this.screen.panel;
    const gen = ++this.textGeneration;
    if (fadeOut && !panel.hidden) {
      panel.classList.add("is-fading");
      setTimeout(() => gen === this.textGeneration && this.clearText(), 600);
    } else {
      this.clearText();
    }
    this.setBars(null);
    this.layer.replaceChildren();
  }

  private clearText(): void {
    const panel = this.screen.panel;
    panel.hidden = true;
    panel.classList.remove("is-fading");
    panel.replaceChildren();
  }

  /** The warning bars in this colour, or hidden. */
  setBars(color: string | null): void {
    for (const bar of this.bars) {
      bar.hidden = color === null;
      if (color) bar.style.setProperty("--bar", color);
    }
  }

  /** fade_palette / fade_solid: one step per frame; input during a fade is discarded. */
  async fadeTo(alpha: number, rgb: readonly number[], steps: number): Promise<void> {
    for (; steps > 0; steps--) {
      this.clock.setFrameCount(1);
      this.fade.step(alpha, rgb, steps);
      await this.clock.waitUntilElapsed();
    }
    this.clearInput();
  }

  // --- text ---

  /** Put JE_displayText's lines up, every character still dark; JE_outCharGlow lights them. */
  showText(opts: TextOptions): TextHandle {
    const panel = this.screen.panel;
    this.clearText();
    this.textGeneration++;
    const tint = bankTint(opts.colors, opts.bank);
    panel.style.setProperty("--tint", tint.ink);
    panel.style.setProperty("--tint-hot", tint.hot);
    panel.classList.toggle("is-top", !!opts.top);
    panel.classList.remove("is-card");

    const body = h("p", { class: "cinema-lines" });
    const lines = opts.lines.map((line, i) => {
      const parsed = parseStoryLine(line);
      const spans = new Map<number, HTMLElement>();
      const el = h("span", { class: parsed.centered ? "cinema-line cinema-line--center" : "cinema-line" });
      let run = "";
      const flush = () => {
        if (run) el.append(run);
        run = "";
      };
      for (const c of parsed.chars) {
        if (c.ch === " ") {
          run += " ";
          continue;
        }
        flush();
        const span = h("span", { class: c.highlight ? "cinema-char is-hl" : "cinema-char", text: c.ch });
        spans.set(c.z, span);
        el.append(span);
      }
      flush();
      body.append(el);
      if (!parsed.centered && i < opts.lines.length - 1) {
        // A soft break (a paragraph wrapped to 300 pixels) may join up on a narrow screen.
        const soft = isSoftBreak(line, opts.lines[i + 1]);
        if (soft) body.append(h("span", { class: "cinema-join", text: " " }));
        body.append(h("br", { class: soft ? "cinema-br cinema-br--soft" : "cinema-br" }));
      }
      return glowSpans(spans);
    });

    const prompt = h(
      "div",
      { class: "ui-hint cinema-prompt", attrs: { "aria-hidden": "true" } },
      keyGlyphs({ key: "Any key", pad: "A", touch: "Tap" }),
      h("span", { class: "ui-hint__label", text: "Continue" }),
    );
    panel.replaceChildren(body, prompt);
    panel.hidden = false;
    panel.scrollTop = 0;
    return { lines, prompt: glowWhole(prompt, parseStoryLine(opts.prompt).chars.filter((c) => c.ch !== " ").length) };
  }

  /** Put a title card (the next episode, the Super Arcade code) on the panel, with a continue hint. */
  showCard(...content: Node[]): void {
    const panel = this.screen.panel;
    this.clearText();
    this.textGeneration++;
    panel.classList.remove("is-top");
    panel.classList.add("is-card");
    panel.replaceChildren(
      ...content,
      h(
        "div",
        { class: "ui-hint cinema-prompt is-lit" },
        keyGlyphs({ key: "Any key", pad: "A", touch: "Tap" }),
        h("span", { class: "ui-hint__label", text: "Continue" }),
      ),
    );
    panel.hidden = false;
  }
}

/** A line's characters as a GlowLine. */
function glowSpans(spans: Map<number, HTMLElement>): GlowLine {
  const set = (span: HTMLElement, value: number) => {
    const { opacity, heat } = glowLook(value);
    span.style.setProperty("--o", String(opacity));
    span.style.setProperty("--h", String(heat));
  };
  return {
    glow(z, value) {
      const span = spans.get(z);
      if (span) set(span, value);
    },
    shade() {
      for (const span of spans.values()) set(span, 0);
    },
  };
}

/**
 * One element that lights up as a line of `count` characters would: by the share of them that
 * have appeared, glowing as hot as the hottest.
 */
function glowWhole(el: HTMLElement, count: number): GlowLine {
  const values = new Map<number, number>();
  return {
    glow(z, value) {
      // A text too long for a small screen scrolls: the prompt comes into view as it appears.
      if (values.size === 0) reveal(el);
      values.set(z, value);
      let heat = 0;
      for (const v of values.values()) heat = Math.max(heat, glowLook(v).heat);
      el.style.setProperty("--o", String(Math.min(1, values.size / Math.max(1, count))));
      el.style.setProperty("--h", String(heat));
    },
    shade() {
      reveal(el);
      el.style.setProperty("--o", "1");
      el.style.setProperty("--h", "0");
    },
  };
}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, Math.max(0, ms)));

let cinema: Cinema | null = null;
let closeTimer = 0;

/** The stage, up already (from the screen before) or opened now (black, faded out). */
export function openCinema(): Cinema {
  clearTimeout(closeTimer);
  // A screen shown since (the item screen, a message) closed ours: start a new one.
  if (!cinema?.open || ui.current !== cinema.screen) cinema = new Cinema();
  return cinema;
}

/** The stage if it's up, without opening it. */
export function currentCinema(): Cinema | null {
  return cinema?.open && ui.current === cinema.screen ? cinema : null;
}

/** Done with the stage for now: it closes unless another screen between levels takes it at once. */
export function releaseCinema(): void {
  clearTimeout(closeTimer);
  const leaving = cinema;
  closeTimer = window.setTimeout(() => {
    leaving?.screen.close();
    if (cinema === leaving) cinema = null;
  }, 150);
}
