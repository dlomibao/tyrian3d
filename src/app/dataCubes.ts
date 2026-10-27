// The item screen's Data Cubes menus as HTML: the list of cubes found in the last level
// (MENU_DATA_CUBES) and the reader (MENU_DATA_CUBE_SUB). The rules are the C's, in
// src/sim/game_menu.ts (which menu, which row, Enter/Escape) and src/sim/cubes.ts (which cubes,
// their wrapped text, the reader's scrolling); this file draws them for src/app/shop.ts.
//
// What the C draws (JE_itemScreen, game_menu.c L672-783 and L811-866), and what it becomes here:
//   - the portrait area (OPTION_SHAPES 20) with the cube's face (FACE_SHAPES, in its own palette,
//     facepal) and the cube's header under it: the left pane, in place of the loadout;
//   - a cube icon (JE_drawCube: OPTION_SHAPES 25 tinted, which flashes on the chosen row) and the
//     title per cube, then "Exit to Game Menu"; with no cubes, "No Data is available at this time.";
//   - the reader: nine lines of the wrapped text scrolled by yLoc, "Read: n%" and EXIT.
//   - On the main menu, an icon per cube collected beside the Data Cubes row (L317-324).
// The reader's text column keeps the C's line breaks (load_cube wraps to the tiny font), so the
// text can't reflow; it scrolls with the C's keys and also with the wheel or a drag.
//
// Cubes the player hasn't opened yet are marked NEW; the C has no such mark (see DECISIONS.md).

import "./dataCubes.css";
import { decodeTableSprite, type DecodedSprite, type Palette, vga6To8 } from "../data";
import {
  cube,
  CUBE_LINE_HEIGHT,
  CUBE_READER_LINES,
  cubeReader,
  cubeReader_end,
  cubeReader_frame,
  cubeReader_home,
  cubeReader_percent,
  facepal,
  load_cubes,
  type CubeReaderInput,
} from "../sim/cubes";
import { MENU_DATA_CUBE_SUB, MENU_DATA_CUBES, MENU_FULL_GAME, menu, type ItemScreenEntry } from "../sim/game_menu";
import type { TyrianFiles } from "../sim/resources";
import { g } from "../sim/state";
import { CLASSIC_TICK_MS } from "../core/timing";

/** sprite.h table numbers, and the OPTION_SHAPES sprites the cube menus use. */
const FACE_SHAPES = 4;
const OPTION_SHAPES = 5;
const PORTRAIT_BACKGROUND = 20;
const CUBE_SPRITE = 25;
const CUBE_ICON = 34;
/** The item screen's palette (JE_loadPic 1). */
const SHOP_PALETTE = 0;

export interface DataCubesHost {
  files: TyrianFiles;
  /** The shop's menu column: the reader is added to it. */
  menuColumn: HTMLElement;
  /** The reader's EXIT button (the C: a click on it goes back to the list with S_SPRING). */
  back: () => void;
}

export interface DataCubesView {
  /** Draw the current menu if it's a data cube one (portrait into `side`, rows into `list`); false otherwise. */
  render(side: HTMLElement, list: HTMLElement): boolean;
  /** Extra markup for a row of another menu: the collected-cube icons by the main menu's Data Cubes row. */
  rowExtra(e: ItemScreenEntry): string;
  destroy(): void;
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

/**
 * A line of Tyrian text: '~' toggles the highlight (JE_outTextAndDarken's `bright`), starting
 * afresh on each line as each line is drawn on its own.
 */
function tildes(s: string): string {
  let out = "";
  let bright = false;
  for (const part of s.split("~")) {
    if (part) out += bright ? `<b>${esc(part)}</b>` : esc(part);
    bright = !bright;
  }
  return out;
}

/** Cubes the player has opened this session, by episode and cube number. */
const opened = new Set<string>();
const cubeKey = (slot: number) => `${g.episodeNum}:${g.cubeList[slot]}`;

/** Paint palette-indexed sprites into a canvas; `map` recolours an index (blit_sprite_hv). */
function paint(
  w: number,
  h: number,
  parts: { sprite: DecodedSprite; x: number; y: number; map?: (c: number) => number }[],
  palette: Palette,
): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;
  const img = ctx.createImageData(w, h);
  for (const { sprite, x: ox, y: oy, map } of parts) {
    for (let y = 0; y < sprite.height; y++) {
      for (let x = 0; x < sprite.width; x++) {
        let c = sprite.pixels[y * sprite.width + x];
        const px = ox + x;
        const py = oy + y;
        if (c < 0 || px < 0 || py < 0 || px >= w || py >= h) continue;
        if (map) c = map(c);
        const o = (py * w + px) * 4;
        img.data[o] = vga6To8(palette[c * 3]);
        img.data[o + 1] = vga6To8(palette[c * 3 + 1]);
        img.data[o + 2] = vga6To8(palette[c * 3 + 2]);
        img.data[o + 3] = 255;
      }
    }
  }
  ctx.putImageData(img, 0, 0);
  return canvas;
}

function tableSprite(table: number, index: number): DecodedSprite | null {
  const raw = g.res.spriteTables[table]?.sprites[index];
  return raw ? decodeTableSprite(raw) : null;
}

/** blit_sprite_hv's colour: the hue's palette row, the pixel's brightness plus value, clamped (sprite.c L304-366). */
const hv = (hue: number, value: number) => (c: number) => {
  let v = (c & 0x0f) + value;
  if (v > 0xf) v = v >= 0x1f ? 0 : 0xf;
  return (hue << 4) | v;
};

const urlCache = new Map<string, string>();
function cached(key: string, make: () => HTMLCanvasElement | null): string {
  let url = urlCache.get(key);
  if (url === undefined) {
    url = make()?.toDataURL() ?? "";
    urlCache.set(key, url);
  }
  return url;
}

/** JE_drawCube's cube (filter 13, brightness 0); the shadows are CSS. */
const cubeImage = () =>
  cached("cube", () => {
    const s = tableSprite(OPTION_SHAPES, CUBE_SPRITE);
    return s && paint(s.width, s.height, [{ sprite: s, x: 0, y: 0, map: hv(13, 0) }], g.res.palettes[SHOP_PALETTE]);
  });

/** The main menu's cube icon (OPTION_SHAPES 34). */
const cubeIconImage = () =>
  cached("icon", () => {
    const s = tableSprite(OPTION_SHAPES, CUBE_ICON);
    return s && paint(s.width, s.height, [{ sprite: s, x: 0, y: 0 }], g.res.palettes[SHOP_PALETTE]);
  });

/**
 * The portrait area (game_menu.c L679, L720-738): OPTION_SHAPES 20 at (1, 1) and the face centred
 * on (77, 92). The C swaps palette colours 1..207 for the face's palette (facepal), the area
 * included; the rest keeps the item screen's.
 */
function portraitImage(face: number): string {
  return cached(`portrait:${face}`, () => {
    const bg = tableSprite(OPTION_SHAPES, PORTRAIT_BACKGROUND);
    if (!bg) return null;
    const parts: { sprite: DecodedSprite; x: number; y: number }[] = [{ sprite: bg, x: 0, y: 0 }];
    let palette = g.res.palettes[SHOP_PALETTE];
    const f = face !== -1 ? tableSprite(FACE_SHAPES, face) : null;
    if (f) {
      parts.push({ sprite: f, x: 77 - Math.trunc(f.width / 2) - 1, y: 92 - Math.trunc(f.height / 2) - 1 });
      const facePalette = g.res.palettes[facepal[face]];
      if (facePalette) {
        palette = palette.slice();
        palette.set(facePalette.subarray(3, (255 - 3 * 16 + 1) * 3), 3); // colors[1 .. 255 - 3*16]
      }
    }
    return paint(bg.width, bg.height, parts, palette);
  });
}

/** Set up the cube menus for one item screen visit; JE_itemScreen's load_cubes() (game_menu.c L164). */
export function createDataCubes(host: DataCubesHost): DataCubesView {
  load_cubes(host.files);

  const reader = document.createElement("div");
  reader.className = "cube-reader";
  reader.hidden = true;
  reader.innerHTML = `
    <div class="cube-text" data-k="text" tabindex="-1"></div>
    <div class="cube-foot">
      <span data-k="read"></span>
      <button type="button" class="ui-button ui-button--ghost" tabindex="-1" data-k="exit"></button>
    </div>`;
  const textEl = reader.querySelector<HTMLElement>('[data-k="text"]')!;
  const readEl = reader.querySelector<HTMLElement>('[data-k="read"]')!;
  const exitEl = reader.querySelector<HTMLButtonElement>('[data-k="exit"]')!;
  host.menuColumn.appendChild(reader);
  exitEl.addEventListener("click", () => host.back());

  /** The cube the reader has open (-1: none), so a redraw keeps its scroll position. */
  let shown = -1;
  /** CSS pixels per C pixel of yLoc (one text line is CUBE_LINE_HEIGHT C pixels). */
  let scale = 1;
  /** The scrollTop the frame loop last set, to tell its own scroll events from the player's. */
  let setTop = -1;

  // The reader's keys, read every frame as the C reads keysactive (so a held key keeps scrolling).
  // A key also counts as down for the first frame after it's pressed, so a quick tap isn't missed.
  const held = new Set<string>();
  const tapped = new Set<string>();
  let clicks: CubeReaderInput = {};
  const onKeyDown = (e: KeyboardEvent) => {
    if (menu.curMenu !== MENU_DATA_CUBE_SUB) return;
    held.add(e.code);
    tapped.add(e.code);
    const c = cube[menu.currentCube];
    if (e.code === "Home" || e.code === "End") {
      e.preventDefault();
      if (e.code === "Home") cubeReader_home();
      else cubeReader_end(c);
      cubeReader.yChg = 0;
      scrollToYLoc();
    } else if (e.code === "PageUp" || e.code === "PageDown") {
      e.preventDefault();
    }
  };
  const onKeyUp = (e: KeyboardEvent) => held.delete(e.code);
  const onBlur = () => (held.clear(), tapped.clear());
  window.addEventListener("keydown", onKeyDown, true);
  window.addEventListener("keyup", onKeyUp, true);
  window.addEventListener("blur", onBlur);

  // A click on the upper or lower half of the text scrolls a line up or down (game_menu.c L813-820, L969-978).
  textEl.addEventListener("click", (e) => {
    const r = textEl.getBoundingClientRect();
    if (e.clientY < r.top + r.height / 2) clicks = { clickUp: true };
    else clicks = { clickDown: true };
  });
  // The wheel, a drag or the scrollbar move the text directly; the C's scrolling carries on from there.
  textEl.addEventListener("scroll", () => {
    if (Math.abs(textEl.scrollTop - setTop) < 1) return;
    cubeReader.yLoc = Math.max(0, Math.round(textEl.scrollTop / scale));
    cubeReader.yChg = 0;
    updatePercent();
  });

  function scrollToYLoc(): void {
    setTop = cubeReader.yLoc * scale;
    textEl.scrollTop = setTop;
    setTop = textEl.scrollTop;
    updatePercent();
  }

  function updatePercent(): void {
    if (shown < 0) return;
    readEl.textContent = `${g.miscText[11] ?? "Read:"} ${cubeReader_percent(cube[shown])}%`;
  }

  function openReader(slot: number): void {
    shown = slot;
    opened.add(cubeKey(slot));
    const c = cube[slot];
    const lines = c.text.slice(0, Math.max(c.last_line, 0));
    textEl.innerHTML = lines.map((l) => `<div>${tildes(l) || "&nbsp;"}</div>`).join("");
    exitEl.textContent = g.miscText[12] ?? "EXIT";
    reader.hidden = false;
    const lineHeight = textEl.firstElementChild?.getBoundingClientRect().height || 20;
    scale = lineHeight / CUBE_LINE_HEIGHT;
    textEl.style.height = `${CUBE_READER_LINES * lineHeight}px`;
    scrollToYLoc();
    textEl.focus({ preventScroll: true });
  }

  // The reader's frame loop: setFrameCount(1), one classic tick per frame.
  let raf = 0;
  let last = 0;
  const frame = (now: number) => {
    raf = requestAnimationFrame(frame);
    if (menu.curMenu !== MENU_DATA_CUBE_SUB || shown < 0) return;
    if (now - last < CLASSIC_TICK_MS) return;
    last = now - ((now - last) % CLASSIC_TICK_MS);
    const pads = (navigator.getGamepads?.() ?? []).filter((p): p is Gamepad => !!p);
    const pad = (i: number) => pads.some((p) => p.buttons[i]?.pressed);
    const down = (code: string) => held.has(code) || tapped.has(code);
    const input: CubeReaderInput = {
      ...clicks,
      up: down("ArrowUp") || down("KeyW") || pad(12),
      down: down("ArrowDown") || down("KeyS") || pad(13),
      pageUp: down("PageUp"),
      pageDown: down("PageDown"),
    };
    clicks = {};
    tapped.clear();
    const before = cubeReader.yLoc;
    cubeReader_frame(cube[shown], input);
    if (cubeReader.yLoc !== before) scrollToYLoc();
  };
  raf = requestAnimationFrame(frame);

  function renderPortrait(side: HTMLElement): void {
    const sel = menu.curSel[MENU_DATA_CUBES];
    const onCube = sel < menu.menuChoices[MENU_DATA_CUBES] && g.cubeMax > 0;
    const c = onCube ? cube[sel - 2] : null;
    const url = portraitImage(c ? c.face_sprite : -1);
    side.innerHTML = `
      <figure class="cube-portrait">
        ${url ? `<img src="${url}" alt="">` : ""}
        <figcaption>${c ? esc(c.header) : ""}</figcaption>
      </figure>`;
  }

  function renderList(list: HTMLElement): void {
    const sel = menu.curSel[MENU_DATA_CUBES];
    const img = cubeImage();
    let html = "";
    if (g.cubeMax === 0) html += `<li class="cube-none">${esc(g.miscText[16 - 1] ?? "")}</li>`;
    for (let x = 1; x <= g.cubeMax; x++) {
      const cur = x + 1 === sel;
      const isNew = !opened.has(cubeKey(x - 1));
      // The rows in the interface framework's menu markup (src/ui/components.css), as shop.ts's.
      html += `<li class="ui-menu__item shop-row cube-row${cur ? " is-focused" : ""}" data-sel="${x + 1}" role="option" aria-selected="${cur}">
        <span class="cube-ico">${img ? `<img src="${img}" alt="">` : ""}</span>
        <span class="ui-menu__text"><span class="ui-menu__label what">${tildes(cube[x - 1].title)}</span></span>
        ${isNew ? `<span class="cube-new" title="Not read yet">NEW</span>` : ""}
      </li>`;
    }
    const exitSel = g.cubeMax + 2;
    const cur = exitSel === sel;
    html += `<li class="ui-menu__item shop-row done${cur ? " is-focused" : ""}" data-sel="${exitSel}" role="option" aria-selected="${cur}">
      <span class="ui-menu__text"><span class="ui-menu__label">${esc(g.miscText[6 - 1] ?? "")}</span></span></li>`;
    list.innerHTML = html;
  }

  return {
    render(side, list) {
      const m = menu.curMenu;
      if (m !== MENU_DATA_CUBES && m !== MENU_DATA_CUBE_SUB) {
        reader.hidden = true;
        list.hidden = false;
        shown = -1;
        return false;
      }
      renderPortrait(side);
      list.hidden = m === MENU_DATA_CUBE_SUB;
      if (m === MENU_DATA_CUBES) {
        reader.hidden = true;
        shown = -1;
        renderList(list);
      } else {
        list.innerHTML = "";
        if (shown !== menu.currentCube) openReader(menu.currentCube);
      }
      return true;
    },

    rowExtra(e) {
      if (menu.curMenu !== MENU_FULL_GAME || e.sel !== 2 || g.cubeMax === 0) return "";
      const img = cubeIconImage();
      const icons = Array.from({ length: Math.min(g.cubeMax, cube.length) }, () => (img ? `<img src="${img}" alt="">` : "")).join("");
      return `<span class="cube-count" title="${esc(g.miscText[4 - 1] ?? "")} ${g.cubeMax}">${icons}</span>`;
    },

    destroy() {
      cancelAnimationFrame(raf);
      window.removeEventListener("keydown", onKeyDown, true);
      window.removeEventListener("keyup", onKeyUp, true);
      window.removeEventListener("blur", onBlur);
      reader.remove();
    },
  };
}
