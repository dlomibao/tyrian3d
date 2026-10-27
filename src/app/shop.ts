// The item screen between levels, as an HTML overlay. All the rules (what's for sale, prices,
// trade-ins, weapon power, where Play Next Level goes) are the C's, in src/sim/game_menu.ts; this
// file only draws that state and turns keys, pad buttons, clicks and taps into the C's inputs.
//
// It is a screen of the interface framework (src/ui/README.md): its intents become the C's keys.
// Keys: arrows (or WASD) move and change weapon power, Enter/Space select, Escape/Backspace back,
// '/' changes the rear gun's firing mode. Pad: d-pad or stick, A select, B back, X firing mode.
// Mouse and touch use the C's mouse rules: the first click on a row moves the cursor there, a
// second click on the same row selects it. Behind it the backdrop turns the player's ship.

import "./shop.css";
import { decodeSprite2, decodeTableSprite, type DecodedSprite, type Palette, vga6To8 } from "../data";
import type { MusicPlayer } from "../audio/remaster";
import type { SoundEffects } from "../audio/sfx";
import {
  itemName,
  itemScreenCash,
  itemScreenEntries,
  JE_itemScreen_done,
  JE_itemScreen_init,
  JE_itemScreen_key,
  JE_itemScreen_mouse,
  JE_itemScreen_quitAnswer,
  JE_itemScreen_update,
  JE_mainMenuHelpText,
  JE_menuHeader,
  MENU_PLAY_NEXT_LEVEL,
  MENU_UPGRADE_SUB,
  MENU_UPGRADES,
  menu,
  PAni,
  PGR,
  planetX,
  planetY,
  type ItemScreenEntry,
  type ItemScreenKey,
} from "../sim/game_menu";
import type { TyrianFiles } from "../sim/resources";
import { g, REAR_WEAPON } from "../sim/state";
import { sectionLevelName } from "../sim/tyrian2";
import { backButton, keyHints, reveal, showScreen, ui, type Intent } from "../ui";

export interface ItemScreenHost {
  files: TyrianFiles;
  sfx: SoundEffects;
  music: MusicPlayer;
}

/** sprite_table index of PLANET_SHAPES (sprite.h). */
const PLANET_SHAPES = 3;
/** The navigation screen's palette (newPal = 18) and the item screen's (JE_loadPic 1 → pcxpal[0]). */
const NAV_PALETTE = 17;
const SHOP_PALETTE = 0;

/** The framework's intents (src/ui/nav.ts: the keys and pad buttons above) as the C's keys. */
const INTENT_KEYS: Record<Intent, ItemScreenKey> = {
  up: "up",
  down: "down",
  left: "left",
  right: "right",
  accept: "enter",
  start: "enter",
  back: "esc",
  alt: "slash",
};

/** The navigation map's canvas is drawn at this multiple of the C's 220x160 pixels, for crisp lines and labels. */
const NAV_SCALE = 3;

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

/** Tyrian's help text toggles a highlight colour with '~' (JE_helpBox). */
const highlight = (s: string) => esc(s).replace(/~([^~]*)~?/g, "<b>$1</b>");

/** Paint a decoded sprite into a canvas (transparent where the sprite has no pixel). */
function spriteCanvas(parts: { sprite: DecodedSprite; x: number; y: number }[], w: number, h: number, palette: Palette): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;
  const img = ctx.createImageData(w, h);
  for (const { sprite, x: ox, y: oy } of parts) {
    for (let y = 0; y < sprite.height; y++) {
      for (let x = 0; x < sprite.width; x++) {
        const c = sprite.pixels[y * sprite.width + x];
        const px = ox + x;
        const py = oy + y;
        if (c < 0 || px < 0 || py < 0 || px >= w || py >= h) continue;
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

const iconCache = new Map<string, string>();

/**
 * JE_drawItem: the item's 24x28 shop picture (blit_sprite2x2 from newsh1.shp, or the ship sheet),
 * as a data URL. itemType is the Upgrade Ship choice (2..8).
 */
function itemIcon(itemType: number, id: number): string | null {
  if (id <= 0 || id > 90) return null;
  const key = `${itemType}:${id}`;
  const hit = iconCache.get(key);
  if (hit !== undefined) return hit || null;
  const { items } = g.res;
  let sheet: Uint8Array;
  let index = 0;
  switch (itemType) {
    case 2:
      sheet = g.res.spriteSheet9.data;
      index = items.ships[id].shipGraphic;
      break;
    default:
      sheet = g.res.loadCompShapes("1").data;
      index =
        itemType === 3 || itemType === 4 ? items.weaponPorts[id].itemGraphic
        : itemType === 5 ? items.shields[id].itemGraphic
        : itemType === 6 ? items.powerSys[id].itemGraphic
        : items.options[id].itemGraphic;
  }
  let url = "";
  if (index > 0) {
    const parts = [
      { sprite: decodeSprite2(sheet, index), x: 0, y: 0 },
      { sprite: decodeSprite2(sheet, index + 1), x: 12, y: 0 },
      { sprite: decodeSprite2(sheet, index + 19), x: 0, y: 14 },
      { sprite: decodeSprite2(sheet, index + 20), x: 12, y: 14 },
    ];
    url = spriteCanvas(parts, 24, 28, g.res.palettes[SHOP_PALETTE]).toDataURL();
  }
  iconCache.set(key, url);
  return url || null;
}

const planetCache = new Map<number, HTMLCanvasElement>();

function planetSprite(index: number): HTMLCanvasElement | null {
  const hit = planetCache.get(index);
  if (hit) return hit;
  const raw = g.res.spriteTables[PLANET_SHAPES]?.sprites[index];
  if (!raw) return null;
  const sprite = decodeTableSprite(raw);
  const canvas = spriteCanvas([{ sprite, x: 0, y: 0 }], sprite.width, sprite.height, g.res.palettes[NAV_PALETTE]);
  planetCache.set(index, canvas);
  return canvas;
}

/** Run the item screen until the player picks a destination or quits. */
export function runItemScreen(host: ItemScreenHost): Promise<void> {
  JE_itemScreen_init();
  JE_itemScreen_update();
  host.music.play(g.songBuy);

  const screen = showScreen({
    id: "shop",
    backdrop: "hangar",
    layout: "wide",
    label: "Item screen",
    onIntent: (intent) => {
      key(INTENT_KEYS[intent]);
      return true;
    },
  });
  const root = screen.panel;
  root.innerHTML = `
      <header class="shop-header">
        <h2 class="ui-title"><small class="ui-title__kicker">Item screen</small><span data-k="title"></span></h2>
        <div class="shop-cash"><span>Credits</span><b data-k="cash"></b></div>
      </header>
      <div class="shop-body">
        <aside class="shop-ship" data-k="ship"></aside>
        <section class="shop-menu">
          <canvas class="shop-nav" data-k="nav" width="${220 * NAV_SCALE}" height="${160 * NAV_SCALE}" hidden></canvas>
          <ul class="ui-menu shop-list" data-k="list" role="listbox"></ul>
          <div class="shop-power" data-k="power" hidden></div>
        </section>
      </div>
      <footer class="shop-help"><p data-k="help"></p><div data-k="hints"></div></footer>
      <div class="ui-modal is-shown shop-dialog" data-k="dialog" hidden></div>`;
  root.querySelector("header")!.append(backButton(() => key("esc")));
  const el = (k: string) => root.querySelector<HTMLElement>(`[data-k="${k}"]`)!;
  const list = el("list");
  const navCanvas = el("nav") as HTMLCanvasElement;
  // The quit question and ship specs cover the whole screen, not just the (scrollable) panel.
  const dialogEl = el("dialog");
  screen.root.append(dialogEl);

  let quitYes = false;
  let finished = false;
  let resolveDone: () => void = () => {};
  const done = new Promise<void>((r) => (resolveDone = r));

  const drainSounds = () => {
    for (const id of menu.sounds) host.sfx.playSampleNum(id);
    menu.sounds.length = 0;
  };

  /** After any input: the loop's exit test, then the next iteration's update, then redraw. */
  const step = () => {
    drainSounds();
    if (JE_itemScreen_done()) {
      finish();
      return;
    }
    JE_itemScreen_update();
    drainSounds();
    render();
  };

  const key = (k: ItemScreenKey) => {
    if (menu.quitRequest) {
      // JE_quitRequest: left/right toggle, Enter/Space confirm, Escape = no.
      if (k === "left" || k === "right" || k === "up" || k === "down") {
        quitYes = !quitYes;
        host.sfx.playSampleNum(28); // S_CURSOR
        render();
      } else if (k === "enter") JE_itemScreen_quitAnswer(quitYes), step();
      else if (k === "esc") JE_itemScreen_quitAnswer(false), step();
      return;
    }
    if (menu.shipSpecsRequest) {
      menu.shipSpecsRequest = false; // JE_doShipSpecs: waitUntilGetInput
      render();
      return;
    }
    JE_itemScreen_key(k);
    if (menu.quitRequest) quitYes = true; // JE_quitRequest starts on "yes"
    step();
  };

  const click = (sel: number | "powerDown" | "powerUp") => {
    if (menu.quitRequest || menu.shipSpecsRequest) return;
    JE_itemScreen_mouse(sel);
    if (menu.quitRequest) quitYes = true;
    step();
  };

  list.addEventListener("click", (e) => {
    const row = (e.target as HTMLElement).closest<HTMLElement>("[data-sel]");
    if (row) click(Number(row.dataset.sel));
  });
  el("power").addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]");
    if (!b) return;
    const act = b.dataset.act!;
    if (act === "slash") key("slash");
    else click(act as "powerDown" | "powerUp");
  });
  dialogEl.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]");
    if (menu.shipSpecsRequest) {
      menu.shipSpecsRequest = false;
      render();
    } else if (b && menu.quitRequest) {
      JE_itemScreen_quitAnswer(b.dataset.act === "yes");
      step();
    }
  });

  // The map's animation (keys and pad buttons come through the framework's navigation).
  let raf = 0;
  let navT = 0;
  const frame = (now: number) => {
    if (menu.curMenu === MENU_PLAY_NEXT_LEVEL && now - navT > 1000 / 18) {
      navT = now;
      drawNav();
    }
    raf = requestAnimationFrame(frame);
  };
  raf = requestAnimationFrame(frame);

  function finish(): void {
    if (finished) return;
    finished = true;
    cancelAnimationFrame(raf);
    screen.close();
    resolveDone();
  }

  // --- drawing ---

  const navState = {
    x: 0,
    y: 0,
    ani: 0,
    aniWait: 3,
    dots: 0,
    dotWait: 8,
    lastSel: -1,
  };

  function navTarget(): [number, number] {
    const sel = menu.curSel[MENU_PLAY_NEXT_LEVEL];
    const o = g.mapOrigin - 1;
    if (sel >= menu.menuChoices[MENU_PLAY_NEXT_LEVEL]) return [navState.x, navState.y];
    const d = g.mapPlanet[sel - 2] - 1;
    return [(planetX[o] + planetX[d]) / 2, (planetY[o] + planetY[d]) / 2];
  }

  /** JE_updateNavScreen's map: planets, the dotted routes, and the view easing toward the chosen route. */
  function drawNav(): void {
    const ctx = navCanvas.getContext("2d")!;
    // Drawn in the C's 220x160 pixels, scaled up so lines and labels stay crisp.
    ctx.setTransform(NAV_SCALE, 0, 0, NAV_SCALE, 0, 0);
    ctx.imageSmoothingEnabled = false;
    const W = navCanvas.width / NAV_SCALE;
    const H = navCanvas.height / NAV_SCALE;
    const sel = menu.curSel[MENU_PLAY_NEXT_LEVEL];
    if (sel !== navState.lastSel) {
      navState.lastSel = sel;
      navState.dots = 0;
      navState.dotWait = 8;
    }
    const [tx, ty] = navTarget();
    navState.x += (tx - navState.x) / 2;
    navState.y += (ty - navState.y) / 2;
    if (Math.abs(tx - navState.x) < 1) navState.x = tx;
    if (Math.abs(ty - navState.y) < 1) navState.y = ty;
    if (navState.aniWait > 0) navState.aniWait--;
    else {
      navState.ani = navState.ani >= 14 ? 0 : navState.ani + 1;
      navState.aniWait = 3;
    }
    if (navState.dotWait > 0) navState.dotWait--;
    else {
      if (sel - 2 < g.mapPNum && navState.dots < menu.planetDots[sel - 2]) navState.dots++;
      navState.dotWait = 5;
    }

    const ox = W / 2 - navState.x;
    const oy = H / 2 - navState.y;
    const bg = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, W * 0.7);
    bg.addColorStop(0, "#0b1a2c");
    bg.addColorStop(1, "#04080f");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(92, 214, 255, 0.12)";
    ctx.lineWidth = 1 / NAV_SCALE;
    for (let gx = ((ox % 15) + 15) % 15; gx < W; gx += 15) ctx.strokeRect(gx, -1, 0, H + 2);
    for (let gy = ((oy % 15) + 15) % 15; gy < H; gy += 15) ctx.strokeRect(-1, gy, W + 2, 0);

    // JE_drawDots: the chosen route's dots light up one by one.
    for (let x = 0; x < g.mapPNum; x++) {
      for (let y = 0; y < menu.planetDots[x]; y++) {
        const lit = x === sel - 2 && y < navState.dots;
        ctx.fillStyle = lit ? "#ffd75a" : "rgba(160, 190, 220, 0.45)";
        ctx.beginPath();
        ctx.arc(menu.planetDotX[x][y] + ox, menu.planetDotY[x][y] + oy, lit ? 1.4 : 0.9, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // JE_drawPlanet: the first 11 planets, then any destinations and the origin past them.
    const drawn = new Set<number>();
    const planet = (n: number) => {
      if (drawn.has(n)) return;
      drawn.add(n);
      let z = PGR[n] - 1;
      if (PAni[n]) z += navState.ani;
      const s = planetSprite(z) ?? planetSprite(PGR[n] - 1);
      if (!s) return;
      const px = Math.round(planetX[n] + ox - s.width / 2);
      const py = Math.round(planetY[n] + oy - s.height / 2);
      ctx.globalAlpha = 0.35;
      ctx.filter = "brightness(0)";
      ctx.drawImage(s, px + 3, py + 3);
      ctx.filter = "none";
      ctx.globalAlpha = 1;
      ctx.drawImage(s, px, py);
    };
    for (let n = 0; n < 11; n++) planet(n);
    for (let x = 0; x < g.mapPNum; x++) planet(g.mapPlanet[x] - 1);
    planet(g.mapOrigin - 1);

    // Labels: where you are and the chosen destination.
    ctx.font = "600 8px 'Exo 2', 'Trebuchet MS', sans-serif";
    ctx.textAlign = "center";
    const label = (n: number, text: string, color: string) => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
      ctx.fillText(text, planetX[n] + ox + 0.5, planetY[n] + oy + 20.5);
      ctx.fillStyle = color;
      ctx.fillText(text, planetX[n] + ox, planetY[n] + oy + 20);
    };
    label(g.mapOrigin - 1, g.pName[g.mapOrigin - 1] ?? "", "#a3b3c4");
    if (sel - 2 < g.mapPNum && sel >= 2) label(g.mapPlanet[sel - 2] - 1, g.pName[g.mapPlanet[sel - 2] - 1] ?? "", "#ffd75a");
  }

  function renderShip(): string {
    const p = g.player[0];
    const it = p.items;
    const { items } = g.res;
    const icon = (type: number, id: number) => {
      const url = itemIcon(type, id);
      return `<span class="ui-menu__icon">${url ? `<img src="${url}" alt="">` : ""}</span>`;
    };
    const row = (type: number, label: string, id: number, extra = "") =>
      `<li>${icon(type, id)}<span class="ui-menu__text"><small class="ui-menu__detail">${esc(label)}</small><span class="ui-menu__label">${esc(itemName(type, id))}${extra}</span></span></li>`;
    const labels = g.menuInt[2] ?? [];
    const power = (port: number) => (it.weapon[port].id ? ` <em>· ${it.weapon[port].power}</em>` : "");
    const mode = items.weaponPorts[it.weapon[REAR_WEAPON].id]?.opNum > 1 ? ` <em>· mode ${p.weapon_mode}</em>` : "";
    const shieldMax = items.shields[it.shield]?.mpwr ?? 0;
    const bar = (label: string, tone: string, pct: number) =>
      `<div class="ui-stat ui-stat--${tone}"><span class="ui-stat__label">${label}</span><span class="ui-stat__bar"><i style="width:${Math.min(100, pct)}%"></i></span></div>`;
    return `
      <div class="shop-bars">
        ${bar("Armor", "armor", (p.armor / 28) * 100)}
        ${bar("Shield", "shield", ((shieldMax * 2) / 28) * 100)}
      </div>
      <ul class="loadout">
        ${row(2, labels[1] ?? "Ship", it.ship)}
        ${row(3, labels[2] ?? "Front Gun", it.weapon[0].id, power(0))}
        ${row(4, labels[3] ?? "Rear Gun", it.weapon[1].id, power(1) + mode)}
        ${row(5, labels[4] ?? "Shield", it.shield)}
        ${row(6, labels[5] ?? "Generator", it.generator)}
        ${row(7, labels[6] ?? "Left Sidekick", it.sidekick[0])}
        ${row(8, labels[7] ?? "Right Sidekick", it.sidekick[1])}
      </ul>`;
  }

  /** One row of the current menu, in the framework's menu list markup (components.css). */
  function renderRow(e: ItemScreenEntry, cur: boolean): string {
    const cls = ["ui-menu__item", "shop-row"];
    if (cur) cls.push("is-focused");
    if (e.unaffordable) cls.push("dim");
    if (e.unavailable) cls.push("off");
    if (e.done) cls.push("done");
    const text = (label: string, detail = "") =>
      `<span class="ui-menu__text"><span class="ui-menu__label">${esc(label)}</span>${detail ? `<small class="ui-menu__detail">${detail}</small>` : ""}</span>`;
    let inner = "";
    if (menu.curMenu === MENU_UPGRADE_SUB && !e.done) {
      const icon = itemIcon(menu.curSel[MENU_UPGRADES], e.item ?? 0);
      inner = `<span class="ui-menu__icon">${icon ? `<img src="${icon}" alt="">` : ""}</span>
        ${text(e.label, `Cost: ${e.cost}`)}
        ${e.owned ? `<span class="ui-badge" title="Owned">OWNED</span>` : ""}`;
    } else if (menu.curMenu === MENU_PLAY_NEXT_LEVEL && !e.done) {
      const level = sectionLevelName(host.files, g.episodeNum, g.mapSection[e.sel - 2]);
      inner = text(e.label, level ? esc(level) : "");
    } else if (menu.curMenu === MENU_UPGRADES && !e.done) {
      const id = playerItem(e.sel);
      inner = text(e.label, esc(itemName(e.sel, id)));
    } else {
      inner = text(e.label, e.unavailable ? "not available" : "");
    }
    return `<li class="${cls.join(" ")}" data-sel="${e.sel}" role="option" aria-selected="${cur}">${inner}</li>`;
  }

  function playerItem(sel: number): number {
    const it = g.player[0].items;
    return [it.ship, it.weapon[0].id, it.weapon[1].id, it.shield, it.generator, it.sidekick[0], it.sidekick[1]][sel - 2] ?? 0;
  }

  function renderPower(): string {
    const sel = menu.curSel[MENU_UPGRADES];
    const p = g.player[0];
    const weapon = menu.curMenu === MENU_UPGRADE_SUB && (sel === 3 || sel === 4);
    if (!weapon) return "";
    const it = p.items.weapon[sel - 3];
    const onWeapon = menu.leftPower || menu.rightPower;
    let html = "";
    if (onWeapon) {
      const segs = Array.from({ length: 11 }, (_, i) => `<i class="${i < it.power ? "on" : ""}"></i>`).join("");
      html += `
        <button class="ui-button" tabindex="-1" data-act="powerDown" ${menu.leftPower ? "" : "disabled"} aria-label="Lower power">◀<small>${menu.leftPower ? g.downgradeCost : ""}</small></button>
        <span class="meter"><b>Power ${it.power}</b><span class="segs">${segs}</span></span>
        <button class="ui-button" tabindex="-1" data-act="powerUp" ${menu.rightPower && menu.rightPowerAfford ? "" : "disabled"} aria-label="Raise power">▶<small>${menu.rightPower ? g.upgradeCost : ""}</small></button>`;
    }
    const opNum = g.res.items.weaponPorts[p.items.weapon[REAR_WEAPON].id]?.opNum ?? 1;
    if (sel === 4 && opNum > 1) {
      html += `<button class="ui-button mode" tabindex="-1" data-act="slash">Firing mode ${p.weapon_mode} / ${opNum}
        <span class="ui-glyphs"><kbd class="ui-key" data-dev="keys">/</kbd><kbd class="ui-key ui-key--pad" data-dev="pad">X</kbd></span></button>`;
    }
    return html;
  }

  /** JE_quitRequest and JE_doShipSpecs, drawn as the framework's modal (components.css .ui-modal). */
  function renderDialog(): string {
    if (menu.quitRequest) {
      return `<div class="ui-panel ui-panel--narrow ui-modal__box"><p>${esc(g.miscText[28] ?? "Quit the game?")}</p>
        <ul class="ui-menu ui-menu--row ui-modal__actions">
          <li class="ui-menu__item ${quitYes ? "is-focused" : ""}" data-act="yes">${esc(g.miscText[9] ?? "Yes")}</li>
          <li class="ui-menu__item ${quitYes ? "" : "is-focused"}" data-act="no">${esc(g.miscText[10] ?? "No")}</li></ul></div>`;
    }
    if (menu.shipSpecsRequest) {
      const info = g.shipInfo[g.player[0].items.ship - 1];
      const name = g.res.items.ships[g.player[0].items.ship]?.name ?? "";
      return `<div class="ui-panel ui-panel--center ui-modal__box specs"><h3 class="ui-title"><small class="ui-title__kicker">Ship specs</small><span>${esc(name)}</span></h3>
        <div class="ui-scroll">${info ? info.map((s) => `<p>${highlight(s)}</p>`).join("") : ""}</div>
        <div class="ui-hints"><span class="ui-hint"><span class="ui-hint__label">Press any key or tap to continue</span></span></div></div>`;
    }
    return "";
  }

  let hintsFor = "";

  /** The key hints under the help text, for the current menu. */
  function renderHints(): void {
    const weapon = menu.curMenu === MENU_UPGRADE_SUB && (menu.curSel[MENU_UPGRADES] === 3 || menu.curSel[MENU_UPGRADES] === 4);
    const id = `${weapon}`;
    if (id === hintsFor) return;
    hintsFor = id;
    el("hints").replaceChildren(
      keyHints([
        { key: "↑↓", pad: "✛", label: "Move" },
        ...(weapon ? [{ key: "←→", pad: "✛", label: "Power" }] : []),
        { key: "Enter", pad: "A", touch: "Tap twice", label: "Select" },
        { key: "Esc", pad: "B", label: "Back" },
      ]),
    );
  }

  function render(): void {
    const entries = itemScreenEntries();
    el("title").textContent = JE_menuHeader();
    el("cash").textContent = String(itemScreenCash());
    el("ship").innerHTML = renderShip();
    list.innerHTML = entries.map((e) => renderRow(e, e.sel === menu.curSel[menu.curMenu])).join("");
    reveal(list.querySelector(".is-focused"));
    const power = renderPower();
    el("power").innerHTML = power;
    el("power").hidden = !power;
    const isNav = menu.curMenu === MENU_PLAY_NEXT_LEVEL;
    if (isNav && navCanvas.hidden) {
      const [tx, ty] = navTarget();
      navState.x = planetX[g.mapOrigin - 1] ?? tx;
      navState.y = planetY[g.mapOrigin - 1] ?? ty;
      navState.lastSel = -1;
    }
    navCanvas.hidden = !isNav;
    if (isNav) drawNav();
    el("help").textContent = JE_mainMenuHelpText();
    renderHints();
    const dialog = renderDialog();
    dialogEl.innerHTML = dialog;
    dialogEl.hidden = !dialog;
    // The backdrop shows the ship being bought or flown (src/ui/backdrop.ts).
    ui.backdrop?.setShipGraphic?.(g.res.items.ships[g.player[0].items.ship]?.shipGraphic ?? -1);
  }

  render();
  return done;
}
