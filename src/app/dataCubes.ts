// The item screen's Data Cubes menus, drawn as a data terminal of the interface framework
// (src/ui/README.md): the list of cubes found in the last level (MENU_DATA_CUBES) and the reader
// (MENU_DATA_CUBE_SUB). The rules are the C's, in src/sim/game_menu.ts (which menu, which row,
// Enter/Escape) and src/sim/cubes.ts (which cubes, their wrapped text, the reader's scrolling);
// this file draws them for src/app/shop.ts and turns the framework's input into the reader's.
//
// What the C draws (JE_itemScreen, game_menu.c L672-783 and L811-866), and what it becomes here:
//   - the portrait area (OPTION_SHAPES 20) with the cube's face (FACE_SHAPES, in its own palette,
//     facepal) and the cube's header under it: the left pane, in place of the loadout;
//   - a cube icon (JE_drawCube: OPTION_SHAPES 25 tinted, which flashes on the chosen row) and the
//     title per cube, then "Exit to Game Menu"; with no cubes, "No Data is available at this time.":
//     rows in the framework's menu markup, as the item screen's other menus;
//   - the reader: nine lines of the wrapped text scrolled by yLoc, "Read: n%" and EXIT: a scroll
//     box under the cube's title, a stat bar and a back button.
//   - On the main menu, an icon per cube collected beside the Data Cubes row (L317-324).
// The reader's text column keeps the C's line breaks (load_cube wraps to the tiny font), so the
// text can't reflow. It scrolls by the C's rules with the framework's up/down (keys, d-pad,
// stick), Page Up/Down, Home/End and a click on its upper or lower half, a pad's shoulder buttons
// page (cubeReaderControl.ts), and the wheel or a finger move it directly.
//
// Cubes the player hasn't opened yet are marked NEW; the C has no such mark (see DECISIONS.md).

import "./dataCubes.css";
import { decodeTableSprite, type DecodedSprite, type Palette, vga6To8 } from "../data";
import { cube, CUBE_LINE_HEIGHT, CUBE_READER_LINES, cubeReader, cubeReader_end, cubeReader_home, cubeReader_percent, facepal, load_cubes } from "../sim/cubes";
import { MENU_DATA_CUBE_SUB, MENU_DATA_CUBES, MENU_FULL_GAME, menu, type ItemScreenEntry } from "../sim/game_menu";
import type { TyrianFiles } from "../sim/resources";
import { g } from "../sim/state";
import { button, h, type Intent, type KeyHint, statBar } from "../ui";
import { CubeReaderControl } from "./cubeReaderControl";

/** sprite.h table numbers, and the OPTION_SHAPES sprites the cube menus use. */
const FACE_SHAPES = 4;
const OPTION_SHAPES = 5;
const PORTRAIT_BACKGROUND = 20;
const CUBE_SPRITE = 25;
const CUBE_ICON = 34;
/** The item screen's palette (JE_loadPic 1). */
const SHOP_PALETTE = 0;

/** Standard-mapping pad buttons that page the reader: LB up, RB down. */
const PAD_PAGE_UP = 4;
const PAD_PAGE_DOWN = 5;

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
  /**
   * An intent the item screen got. In the reader, up/down scroll the text; the item screen still
   * hands every intent to the C's keys too, as the C reads both.
   */
  intent(intent: Intent): void;
  /** A raw key (the item screen's onKey): the reader's Page Up/Down, Home and End. True if used. */
  key(e: KeyboardEvent): boolean;
  /** A pad button that isn't an intent (the item screen's onPadButton): LB/RB page the reader. */
  padButton(index: number): void;
  /** The key hints while the reader is open, or null for the item screen's own. */
  hints(): KeyHint[] | null;
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

/** The "n / max" of a cube slot, for the labels. */
const cubeOf = (slot: number) => `Data cube ${slot + 1} / ${g.cubeMax}`;

/** Set up the cube menus for one item screen visit; JE_itemScreen's load_cubes() (game_menu.c L164). */
export function createDataCubes(host: DataCubesHost): DataCubesView {
  load_cubes(host.files);

  // The reader, in the menu's place: the cube's title, the text in a scroll box, "Read: n%" and EXIT.
  const titleEl = h("span");
  const linesEl = h("div", { class: "cube-lines" });
  const textEl = h("div", { class: "ui-scroll cube-text", attrs: { role: "document" } }, linesEl);
  const read = statBar("", "cyan");
  const exit = button({ label: g.miscText[12] ?? "EXIT", class: "cube-exit", hint: { key: "Esc", pad: "B" }, onPress: () => host.back() });
  const reader = h(
    "div",
    { class: "cube-reader" },
    // The portrait's caption beside it already says which cube this is.
    h("h3", { class: "ui-title cube-reader__title" }, titleEl),
    h("div", { class: "cube-screen" }, textEl),
    h("div", { class: "cube-foot" }, read.el, exit),
  );
  reader.hidden = true;
  // The box shows the C's nine lines; its height comes from this in dataCubes.css.
  textEl.style.setProperty("--cube-lines", String(CUBE_READER_LINES));
  const readLabel = read.el.querySelector<HTMLElement>(".ui-stat__label")!;
  host.menuColumn.appendChild(reader);

  /** The cube the reader has open (-1: none), so a redraw keeps its scroll position. */
  let shown = -1;
  const reading = () => menu.curMenu === MENU_DATA_CUBE_SUB && shown >= 0;
  const control = new CubeReaderControl();
  /** CSS pixels per C pixel of yLoc (one text line is CUBE_LINE_HEIGHT C pixels). */
  let scale = 1;
  /** The scrollTop the frame loop last set, to tell its own scroll events from the player's. */
  let setTop = -1;
  /** The yLoc (C pixels, fractional between frames) last drawn. */
  let drawnY = -1;
  let percentFor = -1;

  const measure = () => {
    const line = linesEl.firstElementChild?.getBoundingClientRect().height;
    if (line) scale = line / CUBE_LINE_HEIGHT;
    drawnY = -1; // redraw at the new scale
  };
  const resize = new ResizeObserver(measure);
  resize.observe(textEl);

  function draw(y: number): void {
    if (y !== drawnY) {
      drawnY = y;
      textEl.scrollTop = y * scale;
      setTop = textEl.scrollTop;
    }
    if (cubeReader.yLoc !== percentFor) {
      percentFor = cubeReader.yLoc;
      const pct = cubeReader_percent(cube[shown]);
      readLabel.textContent = `${g.miscText[11] ?? "Read:"} ${pct}%`;
      read.set(pct / 100);
    }
  }

  // A click on the upper or lower half of the text scrolls a line up or down (game_menu.c L813-820, L969-978).
  textEl.addEventListener("click", (e) => {
    if (!reading()) return;
    const r = textEl.getBoundingClientRect();
    control.press(e.clientY < r.top + r.height / 2 ? "clickUp" : "clickDown");
  });
  // The wheel, a finger or the scrollbar move the text directly; the C's scrolling carries on from there.
  textEl.addEventListener("scroll", () => {
    if (!reading() || Math.abs(textEl.scrollTop - setTop) < 1) return;
    cubeReader.yLoc = Math.max(0, Math.round(textEl.scrollTop / scale));
    cubeReader.yChg = 0;
    control.sync();
    drawnY = cubeReader.yLoc;
    setTop = textEl.scrollTop;
    draw(drawnY);
  });

  function openReader(slot: number): void {
    shown = slot;
    opened.add(cubeKey(slot));
    const c = cube[slot];
    titleEl.innerHTML = tildes(c.title);
    const lines = c.text.slice(0, Math.max(c.last_line, 0));
    linesEl.innerHTML = lines.map((l) => `<div>${tildes(l) || "&nbsp;"}</div>`).join("");
    reader.hidden = false;
    measure();
    control.sync();
    percentFor = -1;
    draw(cubeReader.yLoc);
  }

  // The reader's frame loop: the C's frames at the C's rate (cubeReaderControl.ts), drawn every
  // display frame.
  let raf = 0;
  let last = 0;
  const frame = (now: number) => {
    raf = requestAnimationFrame(frame);
    const dt = last ? now - last : 0;
    last = now;
    if (!reading()) return;
    draw(control.advance(cube[shown], dt));
  };
  raf = requestAnimationFrame(frame);

  function renderPortrait(side: HTMLElement): void {
    const sel = menu.curSel[MENU_DATA_CUBES];
    const onCube = sel < menu.menuChoices[MENU_DATA_CUBES] && g.cubeMax > 0;
    const slot = onCube ? sel - 2 : -1;
    const c = onCube ? cube[slot] : null;
    const url = portraitImage(c ? c.face_sprite : -1);
    side.innerHTML = `
      <figure class="cube-portrait${c ? "" : " is-idle"}">
        <span class="cube-portrait__frame">${url ? `<img src="${url}" alt="">` : ""}</span>
        <figcaption>
          <small>${c ? esc(cubeOf(slot)) : "Data cubes"}</small>
          <b>${c ? esc(c.header) : "&nbsp;"}</b>
        </figcaption>
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
      const c = cube[x - 1];
      // The rows in the interface framework's menu markup (src/ui/components.css), as shop.ts's.
      html += `<li class="ui-menu__item shop-row cube-row${cur ? " is-focused" : ""}${isNew ? " is-new" : ""}" data-sel="${x + 1}" role="option" aria-selected="${cur}">
        <span class="ui-menu__icon cube-ico">${img ? `<img src="${img}" alt="">` : ""}</span>
        <span class="ui-menu__text"><span class="ui-menu__label cube-title">${tildes(c.title)}</span><small class="ui-menu__detail">${esc(c.header)}</small></span>
        ${isNew ? `<span class="ui-badge cube-new" title="Not read yet">NEW</span>` : ""}
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

    intent(intent) {
      if (!reading()) return;
      if (intent === "up" || intent === "down") control.press(intent);
    },

    key(e) {
      if (!reading() || e.altKey || e.ctrlKey || e.metaKey) return false;
      switch (e.code) {
        case "PageUp":
          control.press("pageUp");
          return true;
        case "PageDown":
          control.press("pageDown");
          return true;
        case "Home":
        case "End":
          // game_menu.c L1337-1345: a jump, not a scroll.
          if (e.code === "Home") cubeReader_home();
          else cubeReader_end(cube[shown]);
          cubeReader.yChg = 0;
          control.sync();
          draw(cubeReader.yLoc);
          return true;
      }
      return false;
    },

    padButton(index) {
      if (!reading()) return;
      if (index === PAD_PAGE_UP || index === PAD_PAGE_DOWN) control.page(index === PAD_PAGE_DOWN);
    },

    hints() {
      if (menu.curMenu !== MENU_DATA_CUBE_SUB) return null;
      return [
        { key: "↑↓", pad: "✛", touch: "Drag", label: "Scroll" },
        { key: "PgUp PgDn", pad: "LB RB", label: "Page" },
        { key: "Esc", pad: "B", label: "Back" },
      ];
    },

    destroy() {
      cancelAnimationFrame(raf);
      resize.disconnect();
      reader.remove();
    },
  };
}
