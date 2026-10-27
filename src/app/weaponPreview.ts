// The item screen's weapon preview: the C's weapon simulator (src/sim/weaponSim.ts) drawn by the
// game's own renderer into a small view in the shop panel, so its shots look exactly as they do in
// a level, models included. It takes the place of the loadout column while a submenu shows it, in a
// framed "simulator" panel stacked in the same grid cell as the loadout (shop.css .shop-side), so
// the layout doesn't move when it shows or hides.
//
// One View (one WebGL context) is made the first time a preview shows and reused by every later
// item screen; its canvas moves into each new shop panel.

import "./weaponPreview.css";
import { CLASSIC_TICK_MS } from "../core/timing";
import { loadSettings } from "../core/settings";
import { loadModel } from "../render/models";
import { spriteModels } from "../render/spriteModels";
import { View } from "../render/view";
import { g } from "../sim/state";
import { WEAPON_SIM_FRAME_TICKS, weaponSim_frame, weaponSim_reset, weaponSim_sync, weaponSimPower } from "../sim/weaponSim";

/** JE_weaponSimUpdate's pace: one frame per setFrameCount(3), ~43 ms. */
const FRAME_MS = CLASSIC_TICK_MS * WEAPON_SIM_FRAME_TICKS;
/** Catch-up cap after a stall, as in run.ts. */
const MAX_FRAMES_PER_RENDER = 8;
/** The simulator's window on the 320x200 screen: fill_rectangle_xy(8, 8, 143, 182) in JE_weaponViewFrame. */
const WINDOW = { x: 8, y: 8, w: 136, h: 175 };
/** The C's power bar is power / 10 pixels of the generator's 900. */
const POWER_MAX = 900;

let shared: { view: View; host: HTMLElement } | null = null;

function sharedView(): { view: View; host: HTMLElement } {
  if (!shared) {
    const host = document.createElement("div");
    host.className = "weapon-preview-view";
    const view = new View(host, loadSettings(), { frame: WINDOW, fitContainer: true });
    view.draws.setSpriteModels(spriteModels(), loadModel);
    shared = { view, host };
  }
  return shared;
}

export class WeaponPreview {
  /** Put this in the shop panel; it hides itself when the current menu has no preview. */
  readonly element = document.createElement("div");
  private readonly power: HTMLElement;
  /** The framed screen the shared view's canvas goes in. */
  private readonly screen: HTMLElement;
  private active = false;
  private acc = 0;
  private last = 0;

  constructor() {
    this.element.className = "weapon-preview";
    this.element.hidden = true;
    this.element.setAttribute("aria-label", "Weapon simulator");
    this.element.innerHTML = `
      <div class="weapon-preview-head"><span>Simulator</span><span class="weapon-preview-pwr">Power</span></div>
      <div class="weapon-preview-body">
        <div class="weapon-preview-screen"></div>
        <div class="weapon-preview-power" title="Generator power"><i></i></div>
      </div>`;
    this.power = this.element.querySelector(".weapon-preview-power i")!;
    this.screen = this.element.querySelector(".weapon-preview-screen")!;
    weaponSim_reset();
  }

  /**
   * Call after each item screen input (once its update has run): starts the simulator when a
   * submenu opens and shows or hides the preview. Returns whether it's showing.
   */
  sync(): boolean {
    const active = weaponSim_sync();
    if (active && !this.active) this.start();
    this.active = active;
    this.element.hidden = !active;
    return active;
  }

  /** Call every display frame: runs the simulator at the C's pace and draws it. */
  frame(now: number): void {
    if (!this.active || !shared) return;
    this.acc += now - this.last;
    this.last = now;
    let steps = Math.floor(this.acc / FRAME_MS);
    if (steps > MAX_FRAMES_PER_RENDER) {
      steps = MAX_FRAMES_PER_RENDER;
      this.acc = 0;
    } else {
      this.acc -= steps * FRAME_MS;
    }
    for (let i = 0; i < steps; i++) shared.view.setDrawList(weaponSim_frame());
    if (steps > 0) this.power.style.height = `${(Math.min(POWER_MAX, weaponSimPower()) / POWER_MAX) * 100}%`;
    shared.view.render(null, this.acc / FRAME_MS);
  }

  /** The item screen is closing. The shared view stays, detached, for the next one. */
  close(): void {
    this.active = false;
    shared?.host.remove();
  }

  private start(): void {
    const { view, host } = sharedView();
    if (host.parentElement !== this.screen) this.screen.append(host);
    view.setPalettes(g.res.palettes); // each episode has its own
    view.draws.resetInterpolation();
    view.setDrawList(weaponSim_frame());
    this.acc = 0;
    this.last = performance.now();
  }
}
