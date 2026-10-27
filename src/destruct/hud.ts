// DE_RunTickDrawHUD as HTML over the field: each side's weapon (its icon, sprite 191 + shotType,
// and weaponNames), the selected unit's damage left and the side's points, plus who's playing it.
// It touches the DOM only when a value changes.

import { decodeSprite2, vga6To8, type Palette } from "../data";
import { h } from "../ui";
import { MAX_PLAYERS, PLAYER_LEFT, type DestructGame, WEAPON_ICON_BASE } from "./sim";

export class DestructHud {
  readonly root: HTMLDivElement;
  private readonly sides: { icon: HTMLImageElement; weapon: HTMLElement; dmg: HTMLElement; pts: HTMLElement; who: HTMLElement }[] = [];
  private readonly last = new Map<HTMLElement, string>();
  private readonly icons = new Map<number, string>();

  constructor(
    private readonly sheet: Uint8Array,
    private readonly palette: Palette,
    private readonly weaponNames: string[],
  ) {
    this.root = h("div", { class: "destruct-hud", attrs: { "aria-hidden": "true" } });
    for (let i = 0; i < MAX_PLAYERS; i++) {
      const side = {
        icon: h("img", { class: "destruct-hud__icon", attrs: { alt: "" } }),
        weapon: h("span", { class: "destruct-hud__weapon" }),
        dmg: h("span", { class: "destruct-hud__stat" }),
        pts: h("span", { class: "destruct-hud__stat destruct-hud__pts" }),
        who: h("span", { class: "destruct-hud__who" }),
      };
      this.sides.push(side);
      this.root.append(
        h(
          "div",
          { class: `destruct-hud__side destruct-hud__side--${i === PLAYER_LEFT ? "left" : "right"}` },
          side.icon,
          h("span", { class: "destruct-hud__text" }, side.weapon, side.who),
          side.dmg,
          side.pts,
        ),
      );
    }
    this.root.hidden = true;
    document.body.appendChild(this.root);
  }

  set visible(v: boolean) {
    this.root.hidden = !v;
  }

  update(game: DestructGame): void {
    game.destruct_player.forEach((p, i) => {
      const unit = p.unit[p.unitSelected];
      const side = this.sides[i];
      const icon = this.icon(unit.shotType);
      if (side.icon.getAttribute("src") !== icon) side.icon.src = icon;
      this.text(side.weapon, this.weaponNames[unit.shotType] ?? "");
      this.text(side.dmg, `dmg ${unit.health}`);
      this.text(side.pts, `pts ${p.score}`);
      this.text(side.who, p.is_cpu ? "Computer" : "Human");
    });
  }

  dispose(): void {
    this.root.remove();
  }

  private text(el: HTMLElement, value: string): void {
    if (this.last.get(el) === value) return;
    this.last.set(el, value);
    el.textContent = value;
  }

  /** The weapon's icon from newsh~.shp, as an image URL (cached). */
  private icon(shotType: number): string {
    let url = this.icons.get(shotType);
    if (url !== undefined) return url;
    url = "";
    const sprite = decodeSprite2(this.sheet, WEAPON_ICON_BASE + shotType);
    if (sprite.height > 0 && typeof document !== "undefined") {
      const canvas = document.createElement("canvas");
      canvas.width = sprite.width;
      canvas.height = sprite.height;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        const img = ctx.createImageData(sprite.width, sprite.height);
        sprite.pixels.forEach((c, k) => {
          if (c < 0) return;
          img.data.set([vga6To8(this.palette[c * 3]), vga6To8(this.palette[c * 3 + 1]), vga6To8(this.palette[c * 3 + 2]), 255], k * 4);
        });
        ctx.putImageData(img, 0, 0);
        url = canvas.toDataURL();
      }
    }
    this.icons.set(shotType, url);
    return url;
  }
}
