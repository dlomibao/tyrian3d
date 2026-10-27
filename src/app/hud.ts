// In-game HUD as HTML over the 3D view: crisp at any resolution. It reads the simulation's state
// (the C draws these on the sidebar in JE_inGameDisplays, JE_drawShield, JE_drawArmor) and only
// touches the DOM when a value changes.

import "./overlay.css";
import { g } from "../sim/state";
import { hudLives } from "./arcade"; // [arcade]

export class Hud {
  private readonly root = document.createElement("div");
  private readonly el: Record<string, HTMLElement> = {};
  private readonly last = new Map<string, string>();

  constructor() {
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
      <div class="weapon"><div data-k="front"></div><div data-k="rear"></div></div>`;
    for (const node of this.root.querySelectorAll<HTMLElement>("[data-k]")) this.el[node.dataset.k!] = node;
    this.root.hidden = true;
    document.body.appendChild(this.root);
  }

  set visible(v: boolean) {
    this.root.hidden = !v;
  }

  update(): void {
    const p = g.player[0];
    const items = g.res?.items;
    this.text("score", String(p.cash));
    this.text("level", g.levelName.trim().toUpperCase());
    this.text("lives", hudLives()); // [arcade]
    this.text("message", g.textErase > 0 ? g.messageText : "");
    this.width("armor", p.initial_armor ? p.armor / p.initial_armor : 0);
    this.width("shield", p.shield_max ? p.shield / p.shield_max : 0);
    this.width("power", g.power / 900);
    this.hidden("warning", !(p.is_alive && p.armor < 6));

    // Boss bars (draw_boss_bar): the most damaged linked enemy's armor, out of 254; `color` > 0
    // flashes the bar after a hit.
    const bars = g.boss_bar.filter((b) => b.link_num !== 0);
    this.hidden("boss", bars.length === 0);
    this.hidden("bossSlot1", bars.length < 2);
    bars.forEach((b, i) => {
      this.width(`boss${i}`, b.armor / 254);
      this.flag(`boss${i}`, "hit", b.color > 0);
    });
    if (items) {
      this.text("front", this.weapon(items.weaponPorts[p.items.weapon[0].id]?.name, p.items.weapon[0].power));
      this.text("rear", this.weapon(items.weaponPorts[p.items.weapon[1].id]?.name, p.items.weapon[1].power));
    }
  }

  private weapon(name: string | undefined, power: number): string {
    const n = name?.trim();
    return n && n !== "None" ? `${n} · ${power}` : "";
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
