// The remastered HUD frame (DECISIONS.md D61, the approved design "A — Faithful bronze"): the
// original's sidebar and message bar (JE_loadPic 3, picture 3 in public/art/hud.webp) redrawn in
// SVG on its 320x200 grid, so it's sharp at any size and pixel ratio. Geometry is in hudLayout.ts.
//
// Two SVG layers, each its own compositing layer: the frame (plates, rods, screens, labels,
// rivets), built once per layout, with the expensive filters (brushed metal, drop shadows); and the
// live layer on top (gauges, pips, lamps, sidekicks, score, text), whose elements are changed only
// when their value does. The opening is left empty for the 3D view, except for a recessed bezel
// where the tilted camera's playfield (narrower at the far edge) doesn't reach.

import { ammoSegments, GAUGE_ROWS, type HudLayout, MAX_PIPS, POWER_ROWS } from "./hudLayout";

const SVG_NS = "http://www.w3.org/2000/svg";
const f = (n: number) => +n.toFixed(3);

/** What the live layer shows. */
export interface FrameValues {
  powerRows: number;
  powerText: string;
  shieldRows: number;
  /** The shield's maximum, in rows; null hides the marker (the C draws it only below full). */
  shieldMaxRows: number | null;
  shieldText: string;
  armorRows: number;
  armorText: string;
  frontPips: number;
  rearPips: number;
  frontName: string;
  rearName: string;
  /** 0: no lamp lit (no rear weapon); 1 or 2: the rear weapon's firing mode (JE_drawPortConfigButtons). */
  mode: number;
  sidekicks: readonly (SidekickView | null)[];
  score: string;
  message: string;
  level: string;
}

export interface SidekickView {
  /** A data URL of the sidekick's HUD icon (OPTION_SHAPES), or null for the placeholder drone. */
  icon: string | null;
  iconW: number;
  iconH: number;
  ammo: number;
  ammoMax: number;
}

const DEFS = `
<defs>
  <linearGradient id="hudf-bronzeV" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#5a3c20"/><stop offset=".18" stop-color="#9a7444"/>
    <stop offset=".45" stop-color="#c79d63"/><stop offset=".62" stop-color="#a27a48"/>
    <stop offset=".85" stop-color="#7a5630"/><stop offset="1" stop-color="#4a301a"/>
  </linearGradient>
  <linearGradient id="hudf-bronzeH" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#5a3c20"/><stop offset=".2" stop-color="#a47c4a"/>
    <stop offset=".45" stop-color="#cfa66b"/><stop offset=".7" stop-color="#94703f"/>
    <stop offset="1" stop-color="#4a301a"/>
  </linearGradient>
  <linearGradient id="hudf-plate" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#8e6a40"/><stop offset=".35" stop-color="#7a5833"/>
    <stop offset=".7" stop-color="#6a4b2a"/><stop offset="1" stop-color="#553a20"/>
  </linearGradient>
  <linearGradient id="hudf-wing" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#4a3420"/><stop offset=".5" stop-color="#3a2816"/><stop offset="1" stop-color="#2c1e10"/>
  </linearGradient>
  <linearGradient id="hudf-rodV" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#3a2614"/><stop offset=".35" stop-color="#e2c08a"/>
    <stop offset=".6" stop-color="#a47b46"/><stop offset="1" stop-color="#3a2614"/>
  </linearGradient>
  <linearGradient id="hudf-rodH" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#3a2614"/><stop offset=".35" stop-color="#e2c08a"/>
    <stop offset=".6" stop-color="#a47b46"/><stop offset="1" stop-color="#3a2614"/>
  </linearGradient>
  <linearGradient id="hudf-glass" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#1b140b"/><stop offset=".5" stop-color="#0e0a05"/><stop offset="1" stop-color="#140f08"/>
  </linearGradient>
  <linearGradient id="hudf-glare" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity=".07"/><stop offset=".4" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="hudf-bezel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#20160c"/><stop offset=".55" stop-color="#140d06"/><stop offset="1" stop-color="#0c0804"/>
  </linearGradient>
  <linearGradient id="hudf-shieldG" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#103c8c"/><stop offset=".35" stop-color="#5aa8ff"/>
    <stop offset=".55" stop-color="#b8e0ff"/><stop offset=".8" stop-color="#3b84e0"/><stop offset="1" stop-color="#0c2e70"/>
  </linearGradient>
  <linearGradient id="hudf-armorG" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#6a5010"/><stop offset=".35" stop-color="#d9c070"/>
    <stop offset=".55" stop-color="#fff0b8"/><stop offset=".8" stop-color="#c09a3a"/><stop offset="1" stop-color="#5a420c"/>
  </linearGradient>
  <linearGradient id="hudf-armorEmpty" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#1c2638"/><stop offset="1" stop-color="#2c3c58"/>
  </linearGradient>
  <linearGradient id="hudf-powerG" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="#b8200c"/><stop offset=".45" stop-color="#e86a1c"/>
    <stop offset=".8" stop-color="#ffb030"/><stop offset="1" stop-color="#ffe070"/>
  </linearGradient>
  <linearGradient id="hudf-pipG" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff9a6a"/><stop offset=".5" stop-color="#f0402a"/><stop offset="1" stop-color="#9a1408"/>
  </linearGradient>
  <radialGradient id="hudf-lamp" cx=".4" cy=".35" r=".7">
    <stop offset="0" stop-color="#ffd0b0"/><stop offset=".35" stop-color="#ff5a30"/><stop offset="1" stop-color="#7a1404"/>
  </radialGradient>
  <radialGradient id="hudf-rivet" cx=".35" cy=".3" r=".75">
    <stop offset="0" stop-color="#f2d8a8"/><stop offset=".5" stop-color="#9a7444"/><stop offset="1" stop-color="#3a2614"/>
  </radialGradient>
  <linearGradient id="hudf-vignL" x1="1" y1="0" x2="0" y2="0">
    <stop offset="0" stop-color="#000" stop-opacity=".55"/><stop offset="1" stop-color="#000" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="hudf-vignB" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="#000" stop-opacity=".55"/><stop offset="1" stop-color="#000" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="hudf-vignT" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#000" stop-opacity=".45"/><stop offset="1" stop-color="#000" stop-opacity="0"/>
  </linearGradient>
  <filter id="hudf-brushed" x="0" y="0" width="1" height="1">
    <feTurbulence type="fractalNoise" baseFrequency="2.2 0.06" numOctaves="2" seed="7" result="n"/>
    <feColorMatrix in="n" type="matrix" values="0 0 0 0 .5  0 0 0 0 .38  0 0 0 0 .22  .9 0 0 0 -.25" result="g"/>
    <feComposite in="g" in2="SourceGraphic" operator="in" result="m"/>
    <feBlend in="m" in2="SourceGraphic" mode="overlay"/>
  </filter>
  <filter id="hudf-phos" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur in="SourceGraphic" stdDeviation=".45" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="hudf-hot" x="-60%" y="-10%" width="220%" height="120%">
    <feGaussianBlur in="SourceGraphic" stdDeviation=".9" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="hudf-drop" x="-10%" y="-10%" width="130%" height="130%">
    <feDropShadow dx=".35" dy=".45" stdDeviation=".35" flood-color="#000" flood-opacity=".7"/>
  </filter>
</defs>`;

/** A gauge's place, for the live updates: fills from the bottom in `rows` rows. */
interface GaugeGeo {
  x: number;
  y: number;
  w: number;
  h: number;
  rows: number;
}

interface SidekickGeo {
  /** The box. */
  x: number;
  y: number;
  w: number;
  h: number;
}

/** The SVG markup of one layout, and where the live parts went. */
interface Built {
  frame: string;
  live: string;
  power: GaugeGeo;
  shield: GaugeGeo;
  armor: GaugeGeo;
  sidekicks: SidekickGeo[];
  /** The message: left edge, baseline, font size, and the bar's inside (for its backing). */
  message: { x: number; y: number; size: number; barX: number; barY: number; barW: number; barH: number };
  /** The widest a weapon name may be. */
  nameW: number;
}

/** Builds markup into two lists: the frame's and the live layer's. */
class Painter {
  readonly frame: string[] = [];
  readonly live: string[] = [];
  private out = this.frame;

  /** Draw into the live layer while `fn` runs. */
  liveLayer(fn: () => void): void {
    this.out = this.live;
    fn();
    this.out = this.frame;
  }

  add(s: string): void {
    this.out.push(s);
  }

  plate(x: number, y: number, w: number, h: number, grad = "plate"): void {
    this.add(`<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}" fill="url(#hudf-${grad})"/>`);
    this.add(`<path d="M${f(x)} ${f(y + h)} V${f(y)} H${f(x + w)}" fill="none" stroke="#e9c993" stroke-opacity=".55" stroke-width=".5"/>`);
    this.add(`<path d="M${f(x)} ${f(y + h)} H${f(x + w)} V${f(y)}" fill="none" stroke="#1c1108" stroke-opacity=".8" stroke-width=".5"/>`);
  }

  rodH(x: number, y: number, w: number, t = 1.6): void {
    this.add(`<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(t)}" rx="${f(t / 2)}" fill="url(#hudf-rodH)" filter="url(#hudf-drop)"/>`);
  }

  rodV(x: number, y: number, h: number, t = 1.6): void {
    this.add(`<rect x="${f(x)}" y="${f(y)}" width="${f(t)}" height="${f(h)}" rx="${f(t / 2)}" fill="url(#hudf-rodV)" filter="url(#hudf-drop)"/>`);
  }

  /** A recessed screen with a raised bronze rim (the original's tube-framed boxes). */
  screen(x: number, y: number, w: number, h: number, opts: { rim?: number; fill?: string } = {}): void {
    const r = opts.rim ?? 1.6;
    this.add(`<rect x="${f(x - r)}" y="${f(y - r)}" width="${f(w + 2 * r)}" height="${f(h + 2 * r)}" rx="${f(r * 0.7)}" fill="url(#hudf-bronzeH)" filter="url(#hudf-drop)"/>`);
    this.add(`<rect x="${f(x - r + 0.25)}" y="${f(y - r + 0.25)}" width="${f(w + 2 * r - 0.5)}" height="${f(h + 2 * r - 0.5)}" rx="${f(r * 0.6)}" fill="none" stroke="#f3d7a2" stroke-opacity=".45" stroke-width=".3"/>`);
    this.add(`<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}" fill="${opts.fill ?? "url(#hudf-glass)"}"/>`);
    this.add(`<path d="M${f(x)} ${f(y + h)} V${f(y)} H${f(x + w)}" fill="none" stroke="#000" stroke-opacity=".85" stroke-width=".9"/>`);
    this.add(`<path d="M${f(x + 0.4)} ${f(y + h)} H${f(x + w)} V${f(y + 0.4)}" fill="none" stroke="#6a4b2a" stroke-opacity=".55" stroke-width=".35"/>`);
  }

  glare(x: number, y: number, w: number, h: number): void {
    this.add(`<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}" fill="url(#hudf-glare)"/>`);
  }

  text(x: number, y: number, s: string, size: number, opts: { anchor?: string; ls?: number; fill?: string; key?: string; cls?: string } = {}): void {
    const attrs = [
      `class="hudf-lbl${opts.cls ? ` ${opts.cls}` : ""}"`,
      `x="${f(x)}"`,
      `y="${f(y)}"`,
      `font-size="${f(size)}"`,
      opts.anchor ? `text-anchor="${opts.anchor}"` : "",
      opts.ls ? `letter-spacing="${opts.ls}"` : "",
      opts.fill ? `style="fill:${opts.fill}"` : "",
      opts.key ? `data-k="${opts.key}"` : "",
    ];
    this.add(`<text ${attrs.filter(Boolean).join(" ")}>${s}</text>`);
  }

  /** Upright letters stacked down a column (SHIELD, ARMOR). */
  vtext(cx: number, y0: number, y1: number, s: string, size: number): void {
    const step = (y1 - y0) / s.length;
    [...s].forEach((c, i) => this.text(cx, y0 + step * (i + 0.82), c, size, { anchor: "middle" }));
  }

  rivet(x: number, y: number, r = 0.7): void {
    this.add(`<circle cx="${f(x)}" cy="${f(y)}" r="${f(r)}" fill="url(#hudf-rivet)"/>`);
  }

  greeble(x: number, y: number, w: number, h: number): void {
    this.add(`<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}" rx=".3" fill="url(#hudf-plate)" stroke="#2a1a0c" stroke-width=".3" filter="url(#hudf-drop)"/>`);
    this.add(`<path d="M${f(x + 0.2)} ${f(y + h - 0.2)} V${f(y + 0.2)} H${f(x + w - 0.2)}" fill="none" stroke="#e9c993" stroke-opacity=".5" stroke-width=".25"/>`);
  }

  /** Weapon power pips: MAX_PIPS dim slots, each with a lit pip over it (shown per the power). */
  pips(x: number, y: number, w: number, h: number, key: string): void {
    const gap = 0.45;
    const pw = (w - gap * (MAX_PIPS - 1)) / MAX_PIPS;
    for (let i = 0; i < MAX_PIPS; i++) {
      const px = x + i * (pw + gap);
      this.add(`<rect x="${f(px)}" y="${f(y)}" width="${f(pw)}" height="${f(h)}" rx=".2" fill="#2a120c" stroke="#3e1a10" stroke-width=".2"/>`);
    }
    this.liveLayer(() => {
      // One group with the hot glow, so a power change re-filters one small area.
      this.add(`<g filter="url(#hudf-hot)">`);
      for (let i = 0; i < MAX_PIPS; i++) {
        const px = x + i * (pw + gap);
        this.add(`<rect data-k="${key}${i}" visibility="hidden" x="${f(px)}" y="${f(y)}" width="${f(pw)}" height="${f(h)}" rx=".2" fill="url(#hudf-pipG)"/>`);
      }
      this.add(`</g>`);
    });
  }

  /**
   * A vertical gauge filling from the bottom: the fill (live), its row lines and top cap, and an
   * optional max marker (live). Returns its geometry.
   */
  vgauge(x: number, y: number, w: number, h: number, rows: number, grad: string, key: string, opts: { hot?: boolean; marker?: boolean; lines?: number } = {}): GaugeGeo {
    this.liveLayer(() => {
      this.add(`<rect data-k="${key}" x="${f(x + 0.5)}" y="${f(y + h)}" width="${f(w - 1)}" height="0" fill="url(#hudf-${grad})"${opts.hot ? ` filter="url(#hudf-hot)"` : ""}/>`);
      this.add(`<rect data-k="${key}Cap" x="${f(x + 0.5)}" y="${f(y + h)}" width="${f(w - 1)}" height=".5" fill="#fff" opacity="0"/>`);
      // Row lines, like JE_dBar3's 2-pixel rows.
      const lines = opts.lines ?? rows;
      const row = h / lines;
      let d = "";
      for (let i = 1; i < lines; i++) d += `M${f(x)} ${f(y + h - i * row)}H${f(x + w)}`;
      this.add(`<path d="${d}" stroke="#000" stroke-opacity=".55" stroke-width=".35"/>`);
      if (opts.marker) {
        this.add(`<path data-k="${key}Max" visibility="hidden" d="M${f(x - 0.3)} 0H${f(x + w + 0.3)}" stroke="#7fd0ff" stroke-width=".45" stroke-dasharray=".8 .5" opacity=".9"/>`);
      }
      // The read-out at the top (the design's tweak 2).
      this.text(x + w / 2, y + 3.4, "", 2.9, { anchor: "middle", key: `${key}Num`, cls: "hudf-num" });
      this.glare(x, y, w, h);
    });
    return { x, y, w, h, rows };
  }

  /** Two rear-mode lamps (JE_drawPortConfigButtons): `key`1 and `key`2. */
  modeLamp(x: number, y: number, w: number, h: number, key: string): void {
    this.liveLayer(() => this.add(`<rect data-k="${key}" x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}" rx="${f(h / 2)}" fill="#16311a"/>`));
  }

  /** The bottom message bar's slotted grille. */
  grille(x: number, y: number, w: number, h: number): void {
    this.screen(x, y, w, h, { rim: 1.4 });
    let d = "";
    for (let xx = x + 1.6; xx < x + w - 1; xx += 1.75) d += `M${f(xx)} ${f(y + 1.2)}V${f(y + h - 1.2)}`;
    this.add(`<path d="${d}" stroke="#3a2a18" stroke-width=".75" stroke-linecap="round"/>`);
    this.add(`<path d="${d}" stroke="#000" stroke-width=".35" stroke-linecap="round" transform="translate(.15 .15)"/>`);
  }

  /** Bronze plate filling the window around the block (wide or tall screens). */
  wings(layout: HudLayout): void {
    const v = layout.viewBox;
    const right = v.x + v.w;
    const bottom = v.y + v.h;
    const W = layout.blockW;
    const H = layout.blockH;
    const add = (x: number, y: number, w: number, h: number) => {
      if (w > 0.05 && h > 0.05) this.add(`<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}" fill="url(#hudf-wing)"/>`);
    };
    this.add(`<g filter="url(#hudf-brushed)">`);
    add(v.x, v.y, -v.x, v.h); // left
    add(W, v.y, right - W, v.h); // right
    add(0, v.y, W, -v.y); // top
    add(0, H, W, bottom - H); // bottom
    this.add(`</g>`);
    if (-v.x > 0.5) {
      this.rodV(-1.6, v.y, v.h, 1.6);
      for (let y = 6; y < v.y + v.h; y += 40) this.rivet(-v.x > 6 ? -4 : -v.x / 2 - 0.8, y);
    }
    if (right - W > 0.5) {
      this.rodV(W, v.y, v.h, 1.6);
      for (let y = 6; y < v.y + v.h; y += 40) this.rivet(right - W > 6 ? W + 4 : W + (right - W) / 2 + 0.8, y);
    }
    if (-v.y > 0.5) this.rodH(0, -1.6, W, 1.6);
    if (bottom - H > 0.5) this.rodH(0, H, W, 1.6);
  }

  /**
   * The bezel where the opening shows no playfield: the opening minus the playfield's on-screen
   * outline (`corners`, frame units), dark and recessed, with a lit lip along the outline.
   */
  bezel(ow: number, oh: number, corners: readonly { x: number; y: number }[]): void {
    if (corners.length !== 4) return;
    const poly = corners.map((c, i) => `${i ? "L" : "M"}${f(c.x)} ${f(c.y)}`).join("") + "Z";
    this.add(`<path d="M0 0H${f(ow)}V${f(oh)}H0Z${poly}" fill="url(#hudf-bezel)" fill-rule="evenodd"/>`);
    // Faint ribs across the recess, so it reads as part of the machine rather than a hole.
    let ribs = "";
    for (let y = 3; y < oh - 2; y += 3) ribs += `M0 ${f(y)}H${f(ow)}`;
    this.add(`<clipPath id="hudf-recess"><path d="M0 0H${f(ow)}V${f(oh)}H0Z${poly}" clip-rule="evenodd"/></clipPath>`);
    this.add(`<path d="${ribs}" stroke="#2c1f12" stroke-width=".5" opacity=".55" clip-path="url(#hudf-recess)"/>`);
    // The opening's own rim casts a shadow into the recess.
    this.add(`<rect x="0" y="0" width="${f(ow)}" height="6" fill="url(#hudf-vignT)" clip-path="url(#hudf-recess)"/>`);
    // The playfield's raised lip: a shadow just outside each edge but the near one (it meets the
    // bar), and a lit bronze line on it.
    const [fl, fr, nr, nl] = corners;
    const edges: [typeof fl, typeof fl, number, number][] = [
      [fl, fr, 0, -1],
      [fl, nl, -1, 0],
      [fr, nr, 1, 0],
    ];
    for (const [a, b, dx, dy] of edges) {
      const len = Math.hypot(b.x - a.x, b.y - a.y);
      // Skip edges on the opening's border: nothing outside them to shade.
      const onBorder = (dy < 0 && a.y < 0.3) || (dx < 0 && Math.max(a.x, b.x) < 0.3) || (dx > 0 && Math.min(a.x, b.x) > ow - 0.3);
      if (len < 0.5 || onBorder) continue;
      this.add(`<path d="M${f(a.x + dx * 1.1)} ${f(a.y + dy * 1.1)}L${f(b.x + dx * 1.1)} ${f(b.y + dy * 1.1)}" stroke="#000" stroke-opacity=".55" stroke-width="2.2" stroke-linecap="round"/>`);
      this.add(`<path d="M${f(a.x + dx * 0.35)} ${f(a.y + dy * 0.35)}L${f(b.x + dx * 0.35)} ${f(b.y + dy * 0.35)}" stroke="url(#hudf-rodH)" stroke-width=".9" stroke-linecap="round"/>`);
    }
  }
}

/** The landscape frame: the original's sidebar to the right of the opening and the bar below it. */
function buildLandscape(layout: HudLayout, corners: readonly { x: number; y: number }[]): Built {
  const P = new Painter();
  const ow = layout.openingW;
  /** The design's sidebar x (from 259) at this opening's width. */
  const X = (x: number) => x - 259 + ow;
  P.wings(layout);
  P.bezel(ow, 184, corners);
  // The frame's shadow on the playfield.
  P.add(`<rect x="${f(ow - 8)}" y="0" width="8" height="184" fill="url(#hudf-vignL)"/>`);
  P.add(`<rect x="0" y="176" width="${f(ow)}" height="8" fill="url(#hudf-vignB)"/>`);

  P.add(`<g filter="url(#hudf-brushed)">`);
  P.plate(X(259), 0, 61, 200, "bronzeV");
  P.plate(0, 184, ow, 16, "bronzeH");
  P.add(`</g>`);
  P.rodV(X(258.6), 0, 200, 1.8);
  P.rodV(X(262.5), 9, 99, 1.1);
  P.rodH(0, 183.4, ow, 1.8);
  P.rodH(X(260), 109.5, 60, 1.2);
  P.rodH(X(260), 129.5, 60, 1.2);

  // The red lamp over the generator's power column.
  P.screen(X(267), 2.2, 12.5, 5.4, { rim: 1 });
  P.add(`<ellipse cx="${f(X(273.2))}" cy="4.9" rx="4" ry="1.9" fill="url(#hudf-lamp)" filter="url(#hudf-hot)"/>`);
  P.screen(X(268.2), 11, 10.5, 95);
  const power = P.vgauge(X(268.2), 11, 10.5, 95, POWER_ROWS, "powerG", "power", { hot: true, lines: 50 });

  // FRONT GUN and REAR GUN, each with its weapon's name (tweak 1) and power pips.
  const nameW = 26.4;
  P.screen(X(284), 2.4, 30.5, 18.5);
  P.text(X(286.2), 8.1, "FRONT", 6.4);
  P.text(X(286.2), 13.9, "GUN", 6.4);
  P.liveLayer(() => P.text(X(286.2), 17.1, "", 2.7, { key: "frontName", cls: "hudf-name" }));
  P.pips(X(286.2), 18.1, nameW, 1.9, "front");
  P.liveLayer(() => P.glare(X(284), 2.4, 30.5, 18.5));
  P.screen(X(284), 24.6, 30.5, 17.3);
  P.text(X(286.2), 30.0, "REAR", 6.4);
  P.text(X(286.2), 35.6, "GUN", 6.4);
  P.liveLayer(() => P.text(X(286.2), 38.6, "", 2.7, { key: "rearName", cls: "hudf-name" }));
  P.pips(X(286.2), 39.5, nameW, 1.8, "rear");
  P.liveLayer(() => P.glare(X(284), 24.6, 30.5, 17.3));
  // The rear weapon's mode lamps, and MODE.
  for (const [x, m] of [[285.2, 1], [301.6, 2]] as const) {
    P.screen(X(x), 45, 12.6, 4.4, { rim: 1 });
    P.modeLamp(X(x) + 1.2, 46, 10.2, 2.4, `mode${m}`);
  }
  P.screen(X(284), 53.2, 30.5, 6.6, { rim: 1.2 });
  P.text(X(286.2), 58.9, "MODE", 6.4);
  // Sidekicks.
  const sidekicks: SidekickGeo[] = [];
  for (const y of [63.6, 82.6]) {
    P.screen(X(284), y, 30.5, 16.4);
    sidekicks.push({ x: X(284), y, w: 30.5, h: 16.4 });
  }
  P.liveLayer(() => {
    sidekicks.forEach((_, i) => P.add(`<g data-k="sk${i}"></g>`));
    for (const s of sidekicks) P.glare(s.x, s.y, s.w, s.h);
  });
  for (const [x, y, w, h] of [[286, 101.5, 4.5, 3], [291, 102.5, 4.5, 5], [296.5, 101.2, 6, 3.4], [302.5, 103, 3, 5], [306.5, 102, 4, 4.5], [312, 101, 2.2, 6.5]]) P.greeble(X(x), y, w, h);
  P.rivet(X(264), 3);
  P.rivet(X(316.5), 3);
  P.rivet(X(264), 106);
  P.rivet(X(316.5), 106.5);

  // The score, in the wide box (tweak 3: the C prints it on the playfield).
  P.screen(X(265), 113.4, 52.5, 12.6);
  P.text(X(267.3), 117.6, "CREDITS", 3.1, { ls: 0.3, fill: "#2f9a38" });
  P.liveLayer(() => {
    P.text(X(315.6), 124, "", 8.6, { anchor: "end", ls: 0.2, key: "score" });
    P.glare(X(265), 113.4, 52.5, 12.6);
  });

  // SHIELD | labels | ARMOR.
  P.screen(X(268.2), 134, 10.5, 62.6);
  const shield = P.vgauge(X(268.2), 134, 10.5, 62.6, GAUGE_ROWS, "shieldG", "shield", { marker: true });
  P.screen(X(283), 134.5, 9.2, 43.6, { rim: 1.1 });
  P.vtext(X(287.6), 135.5, 177, "SHIELD", 6.4);
  P.screen(X(293.6), 134.5, 9.2, 43.6, { rim: 1.1 });
  P.vtext(X(298.2), 135.5, 168, "ARMOR", 6.4);
  P.screen(X(305.4), 134, 10.5, 62.6, { fill: "url(#hudf-armorEmpty)" });
  const armor = P.vgauge(X(305.4), 134, 10.5, 62.6, GAUGE_ROWS, "armorG", "armor");
  P.greeble(X(284), 182, 5, 4.5);
  P.greeble(X(289.5), 184.5, 6, 4);
  P.greeble(X(296.5), 186, 4, 3);
  P.add(`<path d="M${f(X(290))} 200a7 4.5 0 0 1 14 0z" fill="url(#hudf-plate)" stroke="#2a1a0c" stroke-width=".3"/>`);
  P.rivet(X(264), 132);
  P.rivet(X(264), 197.5);
  P.rivet(X(318), 132);
  P.rivet(X(318), 197.5);

  // The message bar.
  const barW = ow - 13;
  P.grille(5, 187.2, barW, 9.6);
  P.screen(ow - 6, 187.2, 3.4, 9.6, { rim: 0.8 });
  P.rivet(2.4, 192);
  P.rivet(ow - 1.7, 185);
  const message = { x: 8, y: 187.2 + 4.8 + 5.2 * 0.36, size: 5.2, barX: 6, barY: 188.2, barW: barW - 2, barH: 7.6 };
  liveMessage(P, message, 5 + barW - 3, 3.4);
  P.liveLayer(() => P.glare(5, 187.2, barW, 9.6));
  return { frame: P.frame.join(""), live: P.live.join(""), power, shield, armor, sidekicks, message, nameW };
}

/** The message's backing and text, and the level's name at the bar's right (live). */
function liveMessage(P: Painter, m: Built["message"], levelRight: number, levelSize: number): void {
  P.liveLayer(() => {
    P.add(`<rect data-k="msgBack" x="${f(m.barX)}" y="${f(m.barY)}" width="0" height="${f(m.barH)}" fill="#0c0905" opacity=".88"/>`);
    P.text(m.x, m.y, "", m.size, { ls: 0.15, key: "message" });
    P.text(levelRight, m.y - (m.size - levelSize) * 0.36, "", levelSize, { anchor: "end", ls: 0.4, key: "level", cls: "hudf-dim" });
  });
}

/** The phone layout: the playfield over a console with the same instruments (the design's portrait). */
function buildPortrait(layout: HudLayout, corners: readonly { x: number; y: number }[]): Built {
  const P = new Painter();
  const vw = layout.blockW;
  const cy = layout.openingH;
  const cH = layout.blockH - cy;
  const vh = cy + cH;
  P.wings(layout);
  P.bezel(vw, cy, corners);
  P.add(`<rect x="0" y="${f(cy - 6)}" width="${f(vw)}" height="6" fill="url(#hudf-vignB)"/>`);
  P.add(`<g filter="url(#hudf-brushed)">`);
  P.plate(0, cy, vw, cH, "bronzeH");
  P.add(`</g>`);
  P.rodH(0, cy - 0.6, vw, 1.8);
  P.rodH(0, vh - 1.2, vw, 1.6);

  const top = cy + 4.5;
  const gh = cH - 25;
  // Lamp and power column (left).
  P.screen(4.5, top - 0.8, 11, 3.6, { rim: 0.8 });
  P.add(`<ellipse cx="10" cy="${f(top + 1)}" rx="3.6" ry="1.3" fill="url(#hudf-lamp)" filter="url(#hudf-hot)"/>`);
  P.screen(5, top + 5.5, 10, gh - 1);
  const power = P.vgauge(5, top + 5.5, 10, gh - 1, POWER_ROWS, "powerG", "power", { hot: true, lines: 26 });
  P.rodV(18, top - 2, gh + 8, 1);

  // Guns.
  const gx = 22;
  const gw = 46;
  const g2 = gx + gw + 5;
  const nameW = gw - 4;
  for (const [x, label, key] of [[gx, "FRONT GUN", "front"], [g2, "REAR GUN", "rear"]] as const) {
    P.screen(x, top, gw, 14.5);
    P.text(x + 2, top + 5.6, label, 5);
    P.liveLayer(() => P.text(x + 2, top + 9.6, "", 3, { key: `${key}Name`, cls: "hudf-name" }));
    P.pips(x + 2, top + 10.9, nameW, 2, key);
    P.liveLayer(() => P.glare(x, top, gw, 14.5));
  }
  // Mode: the label and the two lamps.
  const my = top + 19;
  P.screen(gx, my, 20, 7, { rim: 1.1 });
  P.text(gx + 1.8, my + 5.6, "MODE", 5.4);
  for (const [x, m] of [[gx + 24, 1], [gx + 36, 2]] as const) {
    P.screen(x, my, 10, 7, { rim: 1 });
    P.modeLamp(x + 1.2, my + 2.3, 7.6, 2.4, `mode${m}`);
  }
  // Sidekicks.
  const sw = (gw - 4) / 2;
  const sidekicks: SidekickGeo[] = [];
  for (const x of [g2, g2 + sw + 4]) {
    P.screen(x, my, sw, 17);
    sidekicks.push({ x, y: my, w: sw, h: 17 });
  }
  P.liveLayer(() => {
    sidekicks.forEach((_, i) => P.add(`<g data-k="sk${i}"></g>`));
    for (const s of sidekicks) P.glare(s.x, s.y, s.w, s.h);
  });
  // Score.
  const sy = my + 11.5;
  P.screen(gx, sy, gw, 16);
  P.text(gx + 1.8, sy + 4.4, "CREDITS", 3, { ls: 0.3, fill: "#2f9a38" });
  P.liveLayer(() => {
    P.text(gx + gw - 1.8, sy + 13.2, "", 9.4, { anchor: "end", ls: 0.2, key: "score" });
    P.glare(gx, sy, gw, 16);
  });
  for (const [x, y, w, h] of [[1, 21, 5, 4], [7, 20.5, 7, 6], [15.5, 22, 4.5, 3.5], [21.5, 20.5, 6, 5.5], [29, 21.5, 4, 4], [34.5, 20.5, 2.6, 6.5], [39, 22, 6, 3.6]]) P.greeble(g2 + x, my + y, w, h);

  // SHIELD | labels | ARMOR, laid out like the original's lower block.
  const rx = 125;
  P.screen(rx, top, 11, gh + 4.5);
  const shield = P.vgauge(rx, top, 11, gh + 4.5, GAUGE_ROWS, "shieldG", "shield", { marker: true });
  P.screen(rx + 14.2, top, 6.4, gh * 0.82, { rim: 1 });
  P.vtext(rx + 17.4, top + 0.5, top + gh * 0.82 - 0.5, "SHIELD", 5.6);
  P.screen(rx + 23, top, 6.4, gh * 0.72, { rim: 1 });
  P.vtext(rx + 26.2, top + 0.5, top + gh * 0.72 - 0.5, "ARMOR", 5.6);
  P.screen(rx + 32.6, top, 11, gh + 4.5, { fill: "url(#hudf-armorEmpty)" });
  const armor = P.vgauge(rx + 32.6, top, 11, gh + 4.5, GAUGE_ROWS, "armorG", "armor");
  P.greeble(rx + 14.5, top + gh * 0.82 + 3.5, 5, 4);
  P.greeble(rx + 21, top + gh * 0.82 + 5, 6, 3.5);
  P.rivet(2.4, cy + 2.6);
  P.rivet(vw - 2.4, cy + 2.6);
  P.rivet(2.4, vh - 2.4);
  P.rivet(vw - 2.4, vh - 2.4);

  // The message bar.
  const barY = vh - 12.6;
  const barW = vw - 10;
  P.grille(5, barY, barW, 8.6);
  const message = { x: 8, y: barY + 4.3 + 4.8 * 0.36, size: 4.8, barX: 6, barY: barY + 1, barW: barW - 2, barH: 6.6 };
  liveMessage(P, message, 5 + barW - 3, 3.2);
  P.liveLayer(() => P.glare(5, barY, barW, 8.6));
  return { frame: P.frame.join(""), live: P.live.join(""), power, shield, armor, sidekicks, message, nameW };
}

/** A placeholder drone for a sidekick without an icon: the design's twin-pod option. */
function droneIcon(cx: number, cy: number, s: number): string {
  return `<g transform="translate(${f(cx)} ${f(cy)}) scale(${f(s)})">
    <path d="M0 -5 L2.2 -1.5 L2.2 3.5 L0 5 L-2.2 3.5 L-2.2 -1.5 Z" fill="#9aa8b8" stroke="#2a3340" stroke-width=".4"/>
    <path d="M0 -5 L2.2 -1.5 L0 -0.5 Z" fill="#dfe8f2"/>
    <rect x="-5.2" y="-1" width="2.6" height="5" rx="1" fill="#6f8296" stroke="#2a3340" stroke-width=".35"/>
    <rect x="2.6" y="-1" width="2.6" height="5" rx="1" fill="#6f8296" stroke="#2a3340" stroke-width=".35"/>
    <circle cx="0" cy="1.2" r="1.05" fill="#5cd6ff"/><circle cx="-.3" cy=".9" r=".35" fill="#e6fbff"/>
  </g>`;
}

/** A sidekick box's contents: its icon and ammo gauge, or EMPTY. */
export function sidekickMarkup(geo: SidekickGeo, sk: SidekickView | null): string {
  const { x, y, w, h } = geo;
  if (!sk) return `<text class="hudf-lbl hudf-empty" x="${f(x + w / 2)}" y="${f(y + h * 0.6)}" font-size="3.1" text-anchor="middle">EMPTY</text>`;
  const ammo = ammoSegments(sk.ammo, sk.ammoMax);
  const gaugeY = y + h - 2.4;
  const iconArea = ammo.slots ? h - 3.4 : h - 1;
  let out = "";
  if (sk.icon) {
    // The C's sprite, one unit per pixel at most, kept pixel-sharp.
    const k = Math.min(1, (w - 2) / sk.iconW, iconArea / sk.iconH);
    const iw = sk.iconW * k;
    const ih = sk.iconH * k;
    out += `<image href="${sk.icon}" x="${f(x + (w - iw) / 2)}" y="${f(y + 0.6 + (iconArea - ih) / 2)}" width="${f(iw)}" height="${f(ih)}" preserveAspectRatio="none" style="image-rendering:pixelated"/>`;
  } else {
    out += droneIcon(x + w / 2, y + iconArea / 2 + 0.6, Math.min(0.95, iconArea / 11));
  }
  if (ammo.slots) {
    const gap = 0.4;
    const gw = w - 3;
    const sw = (gw - gap * (ammo.slots - 1)) / ammo.slots;
    for (let i = 0; i < ammo.slots; i++) {
      const lit = i < ammo.full;
      const part = i === ammo.full && ammo.partial > 0;
      const fill = lit ? "#4fe05a" : part ? "#2f9a38" : "#163a18";
      out += `<rect x="${f(x + 1.5 + i * (sw + gap))}" y="${f(gaugeY)}" width="${f(sw)}" height="1.1" fill="${fill}"${lit ? ` filter="url(#hudf-phos)"` : ""}/>`;
    }
  }
  return out;
}

/** The frame's two SVG layers, and the live updates. */
export class HudFrame {
  readonly root = document.createElement("div");
  private readonly frameSvg = document.createElementNS(SVG_NS, "svg");
  private readonly liveSvg = document.createElementNS(SVG_NS, "svg");
  private built: Built | null = null;
  private el: Record<string, SVGElement> = {};
  private readonly last = new Map<string, string>();

  constructor() {
    this.root.className = "hudf";
    this.frameSvg.setAttribute("class", "hudf-layer hudf-frame");
    this.liveSvg.setAttribute("class", "hudf-layer hudf-live");
    for (const svg of [this.frameSvg, this.liveSvg]) {
      svg.setAttribute("preserveAspectRatio", "none");
      svg.setAttribute("aria-hidden", "true");
      this.root.appendChild(svg);
    }
  }

  /** Rebuild both layers for `layout`; `corners` is the playfield's outline in frame units. */
  build(layout: HudLayout, corners: readonly { x: number; y: number }[]): void {
    const b = layout.mode === "portrait" ? buildPortrait(layout, corners) : buildLandscape(layout, corners);
    this.built = b;
    const v = layout.viewBox;
    const viewBox = `${f(v.x)} ${f(v.y)} ${f(v.w)} ${f(v.h)}`;
    this.frameSvg.setAttribute("viewBox", viewBox);
    this.liveSvg.setAttribute("viewBox", viewBox);
    this.frameSvg.innerHTML = DEFS + b.frame;
    this.liveSvg.innerHTML = b.live;
    this.el = {};
    for (const node of this.liveSvg.querySelectorAll<SVGElement>("[data-k]")) this.el[node.dataset.k!] = node;
    this.last.clear();
  }

  /** Show `v`, touching only what changed. */
  update(v: FrameValues): void {
    const b = this.built;
    if (!b) return;
    this.gauge("power", b.power, v.powerRows, v.powerText);
    this.gauge("shield", b.shield, v.shieldRows, v.shieldText);
    this.gauge("armor", b.armor, v.armorRows, v.armorText);
    this.set("shieldMax", v.shieldMaxRows === null ? "" : String(v.shieldMaxRows), () => {
      const m = this.el.shieldMax;
      if (v.shieldMaxRows === null) m.setAttribute("visibility", "hidden");
      else {
        const g = b.shield;
        m.setAttribute("transform", `translate(0 ${f(g.y + g.h - (Math.min(v.shieldMaxRows, g.rows) * g.h) / g.rows)})`);
        m.setAttribute("visibility", "visible");
      }
    });
    this.pips("front", v.frontPips);
    this.pips("rear", v.rearPips);
    this.name("frontName", v.frontName, b.nameW);
    this.name("rearName", v.rearName, b.nameW);
    for (const m of [1, 2]) this.set(`mode${m}`, String(v.mode === m), () => {
      const lit = v.mode === m;
      this.el[`mode${m}`].setAttribute("fill", lit ? "#4fe05a" : "#16311a");
      if (lit) this.el[`mode${m}`].setAttribute("filter", "url(#hudf-hot)");
      else this.el[`mode${m}`].removeAttribute("filter");
    });
    b.sidekicks.forEach((geo, i) => {
      const sk = v.sidekicks[i] ?? null;
      const key = sk ? `${sk.icon?.length ?? 0}:${sk.icon?.slice(-24)}:${sk.ammoMax}:${JSON.stringify(ammoSegments(sk.ammo, sk.ammoMax))}` : "empty";
      this.set(`sk${i}`, key, () => (this.el[`sk${i}`].innerHTML = sidekickMarkup(geo, sk)));
    });
    this.set("score", v.score, () => (this.el.score.textContent = v.score));
    this.set("level", v.level, () => (this.el.level.textContent = v.level));
    this.set("message", v.message, () => {
      this.el.message.textContent = v.message;
      const m = b.message;
      const textW = v.message ? (this.el.message as SVGTextElement).getComputedTextLength() : 0;
      this.el.msgBack.setAttribute("width", v.message ? String(f(Math.min(m.barW, textW + (m.x - m.barX) * 2))) : "0");
    });
  }

  private gauge(key: string, g: GaugeGeo, rows: number, text: string): void {
    this.set(key, String(rows), () => {
      const h = (Math.min(rows, g.rows) * g.h) / g.rows;
      const fill = this.el[key];
      fill.setAttribute("y", String(f(g.y + g.h - h)));
      fill.setAttribute("height", String(f(h)));
      const cap = this.el[`${key}Cap`];
      cap.setAttribute("y", String(f(g.y + g.h - h)));
      cap.setAttribute("opacity", rows > 0 ? ".7" : "0");
    });
    this.set(`${key}Num`, text, () => (this.el[`${key}Num`].textContent = text));
  }

  private pips(key: string, n: number): void {
    this.set(key, String(n), () => {
      for (let i = 0; i < MAX_PIPS; i++) this.el[`${key}${i}`].setAttribute("visibility", i < n ? "visible" : "hidden");
    });
  }

  /** A weapon's name, squeezed to fit its box when it's long. */
  private name(key: string, text: string, maxW: number): void {
    this.set(key, text, () => {
      const t = this.el[key] as SVGTextElement;
      t.removeAttribute("textLength");
      t.removeAttribute("lengthAdjust");
      t.textContent = text;
      if (text && t.getComputedTextLength() > maxW) {
        t.setAttribute("textLength", String(maxW));
        t.setAttribute("lengthAdjust", "spacingAndGlyphs");
      }
    });
  }

  private set(key: string, value: string, apply: () => void): void {
    if (this.last.get(key) === value) return;
    this.last.set(key, value);
    apply();
  }
}
