// In-game HUD as HTML and SVG over the 3D view: crisp at any resolution. It reads the simulation's
// state (the C draws these on the sidebar in JE_inGameDisplays, JE_drawShield, JE_drawArmor,
// JE_drawPortConfigButtons, JE_drawOptions, JE_drawTextWindow and tyrian2.c's weapon and power
// bars) and only touches the DOM when a value changes.
//
// Two looks (Options → Interface, `?interface=`, DECISIONS.md D61):
//   frame    the remastered bronze frame (hudFrame.ts): the original's sidebar and message bar
//            around the playfield, which the 3D view is fitted into (View.setViewport). The boss
//            bars, WARNING, arcade lives and the cheating line stay HTML, over the opening.
//   minimal  the light HUD over the full-window view (score, level, lives, bars, weapons, message).
// [two-player] Two-player games keep the minimal look, beside their own HUD (twoPlayerHud.ts).

import "./overlay.css";
import { cameraStyle, interfaceStyle, type CameraStyle } from "../core/displayStyle";
import { CAMERA_TILT, CAMERA_TILT_GENTLE, CAMERA_TILT_OVERHEAD, playfieldScreenAspect, type ScreenRect } from "../render/view";
import { g } from "../sim/state";
import { hudLives } from "./arcade"; // [arcade]
import { paint, tableSprite } from "./dataCubes";
import type { TouchAction } from "./controls";
import { HudFrame, type FrameValues, type HudTargetId, type SidekickView } from "./hudFrame";
import { touchHudParam, touchHudWanted } from "./touchHud";
import { gaugeRows, hudLayout, type Insets, pipCount, powerPercent, powerRows, toFrameUnits } from "./hudLayout";

/** The camera's tilt for a Camera choice. */
export const cameraTilt = (style: CameraStyle): number => (style === "overhead" ? CAMERA_TILT_OVERHEAD : style === "steep" ? CAMERA_TILT : CAMERA_TILT_GENTLE);

/** What the HUD needs of the game's view: where to fit the playfield, and where it landed. */
export interface HudView {
  setTilt(tilt: number): void;
  setViewport(rect: ScreenRect | null): void;
  playfieldCorners(): readonly { x: number; y: number }[];
}

/** sprite.h's OPTION_SHAPES table, and the in-level palette (JE_loadPic 3 → pcxpal[2]). */
const OPTION_SHAPES = 5;
const LEVEL_PALETTE = 5;

export class Hud {
  private readonly root = document.createElement("div");
  private readonly frame = new HudFrame();
  private readonly el: Record<string, HTMLElement> = {};
  private readonly last = new Map<string, string>();
  private readonly aspects = new Map<CameraStyle, number>();
  private readonly icons = new Map<number, SidekickView | null>();
  private readonly insetProbe = document.createElement("div");
  private shown = false;
  private framed = false;

  constructor(private readonly view: HudView | null = null) {
    this.root.className = "hud";
    this.root.innerHTML = `
      <div class="top"><span class="score" data-k="score"></span><span class="level" data-k="level"></span><span class="lives" data-k="lives"></span></div>
      <div class="boss" data-k="boss" hidden>
        <span class="bar"><i data-k="boss0"></i></span><span class="bar" data-k="bossSlot1"><i data-k="boss1"></i></span>
      </div>
      <div class="warning" data-k="warning" hidden>WARNING</div>
      <div class="message" data-k="message"></div>
      <div class="bars">
        <span>Armor</span><span class="bar armor"><i data-k="armor"></i></span>
        <span>Shield</span><span class="bar shield"><i data-k="shield"></i></span>
        <span>Power</span><span class="bar power"><i data-k="power"></i></span>
      </div>
      <div class="weapon"><div data-k="front"></div><div data-k="rear"></div></div>
      <div class="cheating" data-k="cheating" hidden>Cheaters always prosper.</div>`;
    for (const node of this.root.querySelectorAll<HTMLElement>("[data-k]")) this.el[node.dataset.k!] = node;
    this.root.hidden = true;
    this.frame.root.hidden = true;
    this.insetProbe.className = "hud-inset-probe";
    document.body.append(this.insetProbe, this.frame.root, this.root);
    window.addEventListener("resize", () => this.framed && this.layout());
    interfaceStyle.listen(() => this.sync());
    cameraStyle.listen(() => this.framed && this.layout());
  }

  set visible(v: boolean) {
    this.shown = v;
    this.root.hidden = !v;
    this.sync();
    this.syncTouch();
  }

  /**
   * Touch play (D100): the rear gun's box and MODE lamps change its mode, the sidekick boxes fire
   * them while held. `press` is Controls.pressButton; targets work in the framed HUD, on a touch
   * device (a coarse pointer, or a finger just used), or when `?touchhud=1` says so.
   */
  attachTouch(press: (action: TouchAction, down: boolean) => void): void {
    const action: Record<HudTargetId, TouchAction> = { rearMode: "changeFire", sk0: "leftSidekick", sk1: "rightSidekick" };
    this.frame.onTarget = (id, down) => press(action[id], down);
    const coarse = window.matchMedia?.("(pointer: coarse)");
    const param = touchHudParam(location.search);
    this.touchWanted = () => touchHudWanted(param, coarse?.matches ?? false, document.documentElement.dataset.input);
    coarse?.addEventListener?.("change", () => this.syncTouch());
    new MutationObserver(() => this.syncTouch()).observe(document.documentElement, { attributes: true, attributeFilter: ["data-input"] });
  }

  private touchWanted: () => boolean = () => false;

  private syncTouch(): void {
    this.frame.touchEnabled = this.shown && this.framed && this.touchWanted();
  }

  update(): void {
    this.sync();
    const p = g.player[0];
    const items = g.res?.items;
    this.text("lives", hudLives()); // [arcade]
    this.hidden("warning", !(p.is_alive && p.armor < 6));
    this.hidden("cheating", !g.youAreCheating); // [cheats] JE_inGameDisplays (mainint.c L2913-2916)

    // Boss bars (draw_boss_bar): the most damaged linked enemy's armor, out of 254; `color` > 0
    // flashes the bar after a hit.
    const bars = g.boss_bar.filter((b) => b.link_num !== 0);
    this.hidden("boss", bars.length === 0);
    this.hidden("bossSlot1", bars.length < 2);
    bars.forEach((b, i) => {
      this.width(`boss${i}`, b.armor / 254);
      this.flag(`boss${i}`, "hit", b.color > 0);
    });

    const front = items?.weaponPorts[p.items.weapon[0].id]?.name.trim() ?? "";
    const rear = items?.weaponPorts[p.items.weapon[1].id]?.name.trim() ?? "";
    const fitted = (n: string) => n !== "" && n !== "None";
    const message = g.textErase > 0 ? g.messageText : "";
    const level = g.levelName.trim().toUpperCase();

    if (this.framed) {
      const v: FrameValues = {
        powerRows: powerRows(g.power),
        powerText: String(powerPercent(g.power)),
        shieldRows: gaugeRows(p.shield),
        shieldMaxRows: p.shield !== p.shield_max ? gaugeRows(p.shield_max) : null,
        shieldText: String(Math.max(0, p.shield)),
        armorRows: gaugeRows(p.armor),
        armorText: String(Math.max(0, p.armor)),
        frontPips: pipCount(p.items.weapon[0].power, fitted(front)),
        rearPips: pipCount(p.items.weapon[1].power, fitted(rear)),
        frontName: fitted(front) ? front.toUpperCase() : "",
        rearName: fitted(rear) ? rear.toUpperCase() : "",
        mode: fitted(rear) ? p.weapon_mode : 0,
        sidekicks: [0, 1].map((i) => this.sidekick(i)),
        score: p.cash.toLocaleString("en-US"),
        message,
        level,
      };
      this.frame.update(v);
      return;
    }

    this.text("score", String(p.cash));
    this.text("level", level);
    this.text("message", message);
    this.width("armor", p.initial_armor ? p.armor / p.initial_armor : 0);
    this.width("shield", p.shield_max ? p.shield / p.shield_max : 0);
    this.width("power", g.power / 900);
    this.text("front", fitted(front) ? `${front} · ${p.items.weapon[0].power}` : "");
    this.text("rear", fitted(rear) ? `${rear} · ${p.items.weapon[1].power}` : "");
  }

  /** Frame or minimal: the frame while shown, chosen, and not a two-player game. */
  private sync(): void {
    const framed = this.shown && this.view !== null && interfaceStyle.get() === "frame" && !g.twoPlayerMode;
    if (framed === this.framed) return;
    this.framed = framed;
    this.syncTouch();
    this.root.classList.toggle("is-framed", framed);
    this.frame.root.hidden = !framed;
    this.last.clear();
    if (framed) this.layout();
    else {
      this.view?.setViewport(null);
      for (const k of ["left", "top", "width", "height"]) this.root.style.removeProperty(k);
      const s = document.documentElement.style;
      s.removeProperty("--hud-pause-top");
      s.removeProperty("--hud-pause-right");
    }
    if (this.shown) this.update();
  }

  /** Lay the frame out for the window, fit the view into its opening, and draw it. */
  private layout(): void {
    const view = this.view;
    if (!view) return;
    const style = cameraStyle.get();
    const tilt = cameraTilt(style);
    let aspect = this.aspects.get(style);
    if (aspect === undefined) this.aspects.set(style, (aspect = playfieldScreenAspect(tilt)));
    const W = window.innerWidth;
    const H = window.innerHeight;
    const layout = hudLayout(W, H, aspect, this.insets());
    view.setTilt(tilt);
    view.setViewport(layout.playfield);
    this.frame.build(
      layout,
      view.playfieldCorners().map((c) => toFrameUnits(layout, c)),
    );
    // The HTML parts (boss bars, WARNING, lives, cheating) over the opening.
    const o = layout.opening;
    Object.assign(this.root.style, { left: `${o.x}px`, top: `${o.y}px`, width: `${o.w}px`, height: `${o.h}px` });
    this.root.style.setProperty("--hud-unit", `${layout.scale}px`);
    // The touch pause button at the opening's top right, off the instruments.
    const s = document.documentElement.style;
    s.setProperty("--hud-pause-top", `${Math.round(o.y + 8)}px`);
    s.setProperty("--hud-pause-right", `${Math.round(W - (o.x + o.w) + 8)}px`);
  }

  /** The safe area's insets (notches), read from a probe padded with env(safe-area-inset-*). */
  private insets(): Insets {
    const cs = getComputedStyle(this.insetProbe);
    const px = (v: string) => parseFloat(v) || 0;
    return { top: px(cs.paddingTop), right: px(cs.paddingRight), bottom: px(cs.paddingBottom), left: px(cs.paddingLeft) };
  }

  /**
   * A sidekick's box (JE_drawOptions): its HUD icon, OPTION_SHAPES iconGr - 1 in the in-level
   * palette, and its ammo (draw_segmented_gauge, for sidekicks that run out).
   */
  private sidekick(i: number): SidekickView | null {
    const p = g.player[0];
    const id = p.items.sidekick[i];
    const option = id > 0 ? g.res?.items.options[id] : undefined;
    if (!option) return null;
    let art = this.icons.get(option.iconGr);
    if (art === undefined) {
      const sprite = option.iconGr > 0 ? tableSprite(OPTION_SHAPES, option.iconGr - 1) : null;
      const palette = g.res.palettes[LEVEL_PALETTE];
      art = sprite && palette ? { icon: paint(sprite.width, sprite.height, [{ sprite, x: 0, y: 0 }], palette).toDataURL(), iconW: sprite.width, iconH: sprite.height, ammo: 0, ammoMax: 0 } : null;
      this.icons.set(option.iconGr, art);
    }
    const sk = p.sidekick[i];
    return { icon: art?.icon ?? null, iconW: art?.iconW ?? 0, iconH: art?.iconH ?? 0, ammo: sk.ammo, ammoMax: sk.ammo_max };
  }

  private text(k: string, v: string): void {
    if (this.last.get(k) === v) return;
    this.last.set(k, v);
    this.el[k].textContent = v;
  }

  private width(k: string, fraction: number): void {
    this.style(k, `${Math.round(Math.max(0, Math.min(1, fraction)) * 100)}%`);
  }

  private style(k: string, width: string): void {
    if (this.last.get(k) === width) return;
    this.last.set(k, width);
    this.el[k].style.width = width;
  }

  private flag(k: string, cls: string, on: boolean): void {
    const key = `${k}.${cls}`;
    const v = String(on);
    if (this.last.get(key) === v) return;
    this.last.set(key, v);
    this.el[k].classList.toggle(cls, on);
  }

  private hidden(k: string, hidden: boolean): void {
    const v = String(hidden);
    if (this.last.get(k) === v) return;
    this.last.set(k, v);
    this.el[k].hidden = hidden;
  }
}
