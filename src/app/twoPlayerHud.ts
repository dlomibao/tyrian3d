// [two-player] The in-game HUD's two-player part, as HTML over the 3D view beside the one-player
// HUD (hud.ts). In two-player mode the C draws a different sidebar (JE_loadPic 6, tyrian2.c L708):
// each player's armor and shield, score, extra lives and weapon power (the lives are that power:
// point_lives_at_weapon_power). Here each player gets a panel in a bottom corner, and the
// one-player HUD's own bars, weapons, score and warning are hidden (twoPlayer.css) while this one
// shows. It reads the simulation's state and only touches the DOM when a value changes.

import "./twoPlayer.css";
import { FRONT_WEAPON, g, REAR_WEAPON } from "../sim/state";

/** Each player's weapon in a two-player game: player 1 fires the front gun, player 2 the rear. */
const PLAYER_WEAPON = [FRONT_WEAPON, REAR_WEAPON] as const;

export class TwoPlayerHud {
  private readonly root = document.createElement("div");
  private readonly el: Record<string, HTMLElement> = {};
  private readonly last = new Map<string, string>();
  private shown = false;

  constructor() {
    this.root.className = "hud2";
    const panel = (i: number) => `
      <div class="hud2-player hud2-player--${i + 1}" data-k="p${i}">
        <div class="hud2-head"><b data-k="name${i}"></b><span class="hud2-score" data-k="score${i}"></span></div>
        <div class="hud2-bars">
          <span>Armor</span><span class="bar armor"><i data-k="armor${i}"></i></span>
          <span>Shield</span><span class="bar shield"><i data-k="shield${i}"></i></span>
        </div>
        <div class="hud2-foot"><span class="hud2-lives" data-k="lives${i}"></span><span class="hud2-weapon" data-k="weapon${i}"></span></div>
        <div class="hud2-state" data-k="state${i}" hidden></div>
      </div>`;
    this.root.innerHTML = `${panel(0)}${panel(1)}<div class="hud2-warning" data-k="warning" hidden>WARNING</div>`;
    for (const node of this.root.querySelectorAll<HTMLElement>("[data-k]")) this.el[node.dataset.k!] = node;
    this.root.hidden = true;
    document.body.appendChild(this.root);
  }

  /** Shown while a level is played; it hides itself (and gives the one-player HUD back) outside two-player games. */
  set visible(v: boolean) {
    this.shown = v;
    this.sync();
  }

  private sync(): void {
    const on = this.shown && g.twoPlayerMode;
    this.root.hidden = !on;
    if (on) document.documentElement.dataset.players = "2";
    else delete document.documentElement.dataset.players;
  }

  update(): void {
    this.sync();
    if (this.root.hidden) return;
    const items = g.res?.items;
    let warning = false;
    for (let i = 0; i < 2; i++) {
      const p = g.player[i];
      this.text(`name${i}`, g.miscText[48 + i]?.trim() || `Player ${i + 1}`);
      this.text(`score${i}`, String(p.cash));
      this.width(`armor${i}`, p.initial_armor ? p.armor / p.initial_armor : 0);
      this.width(`shield${i}`, p.shield_max ? p.shield / p.shield_max : 0);
      // The extra lives, past the one in play (JE_inGameDisplays, mainint.c L2864-2890): an icon
      // each, or one icon and the count from 5 on.
      const extra = Math.max(0, p.lives.value - 1);
      this.text(`lives${i}`, extra >= 5 ? `▲ ${extra}` : "▲".repeat(extra));
      const port = PLAYER_WEAPON[i];
      const weapon = p.items.weapon[port];
      const name = items?.weaponPorts[weapon.id]?.name?.trim();
      this.text(`weapon${i}`, name && name !== "None" ? `${name} · ${weapon.power}` : "");
      const out = !p.is_alive && p.exploding_ticks === 0 && p.lives.value <= 1;
      const state = out ? "Out" : i === 1 && g.twoPlayerLinked ? "Linked" : "";
      this.text(`state${i}`, state);
      this.hidden(`state${i}`, state === "");
      this.flag(`p${i}`, "is-out", out);
      if (p.is_alive && p.armor < 6) warning = true;
    }
    this.hidden("warning", !warning);
  }

  private text(k: string, v: string): void {
    if (this.last.get(k) === v) return;
    this.last.set(k, v);
    this.el[k].textContent = v;
  }

  private width(k: string, fraction: number): void {
    const v = `${Math.round(Math.max(0, Math.min(1, fraction)) * 100)}%`;
    if (this.last.get(k) === v) return;
    this.last.set(k, v);
    this.el[k].style.width = v;
  }

  private flag(k: string, cls: string, on: boolean): void {
    const key = `${k}.${cls}`;
    const v = String(on);
    if (this.last.get(key) === v) return;
    this.last.set(key, v);
    this.el[k].classList.toggle(cls, on);
  }

  private hidden(k: string, hidden: boolean): void {
    const key = `${k}.hidden`;
    const v = String(hidden);
    if (this.last.get(key) === v) return;
    this.last.set(key, v);
    this.el[k].hidden = hidden;
  }
}
