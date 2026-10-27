// The screens around the Options menu, as HTML overlays:
//   showOptions      the settings screen: music and sound volume, music style, the keyboard
//                    bindings and a gamepad button check. The title's Options button opens it, and
//                    so do the item screen's Joystick and Keyboard rows (the C's MENU_JOYSTICK_CONFIG
//                    and MENU_KEYBOARD_CONFIG, game_menu.c L386-440, L2668-2745).
//   showLoadScreen   JE_loadScreen (mainint.c L619-901): the title's list of saved games.
//   promptSaveName   JE_operation's save dialog (mainint.c L2729-2843): the name for a save slot.
//   itemScreenOptionsRow  how the item screen (shop.ts) draws the Options menu's volume rows and the
//                    load/save menu's slots.
// The rules are elsewhere: volumes in src/sim/volume.ts, bindings in bindings.ts, saves in
// src/sim/savegame.ts. Everything here takes keys, gamepad buttons, clicks and taps.

import "./options.css";
import type { MusicPlayer } from "../audio/remaster";
import type { SoundEffects } from "../audio/sfx";
import type { ItemScreenEntry } from "../sim/game_menu";
import { saveNameChar, saveSlotViews, type SaveSlotView } from "../sim/savegame";
import { S_CLICK, S_CLINK, S_CURSOR, S_SELECT, S_SPRING } from "../sim/sndmast";
import { g } from "../sim/state";
import { JE_changeVolume, set_volume, volume, volumeFromBarCells, VOLUME_STEP } from "../sim/volume";
import { ACTIONS, BINDING_SLOTS, bindKey, clearKey, keyName, keys, resetKeys, type Action } from "./bindings";
import { savePrefs } from "./prefs";

export interface OptionsHost {
  sfx: SoundEffects;
  /** The music; a MusicSwitch also offers its styles (local remaster packs). */
  music: MusicPlayer & { readonly styles?: readonly string[]; readonly style?: string; setStyle?(style: string): void };
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
/** Tyrian's text toggles a highlight with '~' (JE_textShade / JE_helpBox). */
const highlight = (s: string) => esc(s).replace(/~([^~]*)~?/g, "<b>$1</b>");

// These screens read keys and pads themselves; the title and item screen open them through the
// interface framework's Screen.aside, which keeps the framework's navigation off meanwhile.

function overlay(className: string, html: string): HTMLDivElement {
  const el = document.createElement("div");
  el.className = `overlay ${className}`;
  el.innerHTML = html;
  document.body.appendChild(el);
  return el;
}

function closeOverlay(el: HTMLElement): void {
  el.remove();
}

// --- Gamepad ---

/** Standard-mapping button names, and what the game uses each for (as Controls.sample maps them). */
const PAD_BUTTONS: [name: string, use: string][] = [
  ["A", "Fire"],
  ["B", ""],
  ["X", "Change fire"],
  ["Y", ""],
  ["LB", "Left sidekick"],
  ["RB", "Right sidekick"],
  ["LT", ""],
  ["RT", "Fire"],
  ["Back", ""],
  ["Start", "Pause"],
  ["L3", ""],
  ["R3", ""],
  ["Up", "Move"],
  ["Down", "Move"],
  ["Left", "Move"],
  ["Right", "Move"],
  ["Home", ""],
];

type PadKey = "up" | "down" | "left" | "right" | "enter" | "esc";
const PAD_KEYS: [number, PadKey][] = [[12, "up"], [13, "down"], [14, "left"], [15, "right"], [0, "enter"], [1, "esc"]];

/**
 * Menu input from gamepads: edge-triggered buttons, d-pad repeat, and buttons held when the screen
 * opens are ignored until released. `frame` runs every animation frame too.
 */
function pollPad(onKey: (k: PadKey) => void, frame?: (pads: Gamepad[], now: number) => void): () => void {
  const held = new Map<number, number>();
  let armed = false;
  let raf = 0;
  let stopped = false;
  const tick = (now: number) => {
    if (stopped) return;
    const pads = (navigator.getGamepads?.() ?? []).filter((p): p is Gamepad => !!p);
    const down = (i: number) => pads.some((p) => p.buttons[i]?.pressed);
    if (!armed) armed = !PAD_KEYS.some(([i]) => down(i));
    else {
      for (const [i, k] of PAD_KEYS) {
        if (!down(i)) {
          held.delete(i);
          continue;
        }
        const since = held.get(i);
        if (since === undefined) {
          held.set(i, now);
          onKey(k);
        } else if (i >= 12 && now - since > 380) {
          held.set(i, now - 380 + 110);
          onKey(k);
        }
        if (stopped) return;
      }
    }
    frame?.(pads, now);
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => {
    stopped = true;
    cancelAnimationFrame(raf);
  };
}

const KEYS_TO_MENU: Record<string, PadKey> = {
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
  Enter: "enter",
  NumpadEnter: "enter",
  Space: "enter",
  Escape: "esc",
};

// --- Volume bars ---

/** JE_barDrawShadow's cells for a volume: tyrMusicVolume / 12, up to 21 (game_menu.c L667-668). */
const VOLUME_CELLS = Math.trunc(255 / VOLUME_STEP);

function volumeBarHtml(vol: number, row: number | string): string {
  const lit = Math.trunc(vol / VOLUME_STEP);
  const cells = Array.from({ length: VOLUME_CELLS }, (_, i) => `<i class="${i < lit ? "on" : ""}"></i>`).join("");
  return `<span class="vol-bar" data-vol-row="${row}" role="slider" aria-valuemin="0" aria-valuemax="255" aria-valuenow="${vol}">${cells}</span><span class="vol-num">${vol}</span>`;
}

/** The bar cell a click lands on, as the C counts 4-pixel cells from the bar's start; the far end is full volume. */
export function volumeBarCells(e: MouseEvent, bar: HTMLElement): number {
  const r = bar.getBoundingClientRect();
  const cells = Math.round(((e.clientX - r.left) / Math.max(1, r.width)) * VOLUME_CELLS);
  return cells >= VOLUME_CELLS ? VOLUME_CELLS + 1 : Math.max(0, cells);
}

// --- The item screen's rows ---

/**
 * The inner HTML for an item-screen row this file draws: the Options menu's Music and Sound rows
 * (their volume bars; click with JE_itemScreen_volumeClick) and the load/save menu's slots (name,
 * last level, episode: game_menu.c L328-383). Null for any other row.
 */
export function itemScreenOptionsRow(e: ItemScreenEntry): string | null {
  if (e.saveSlot) {
    const s = e.saveSlot;
    const level = s.empty ? "-----" : esc(s.levelName); /* Empty save slot */
    const ep = s.empty ? "" : `<span class="slot-ep">${esc(g.miscTextB[1 - 1] ?? "Ep")}${s.episode}</span>`;
    return `<span class="what ui-menu__label slot-name">${esc(s.name)}</span><span class="slot-level">${level}</span>${ep}`;
  }
  if (e.volume !== undefined) return `<span class="what ui-menu__label">${esc(e.label)}</span>${volumeBarHtml(e.volume, e.sel)}`;
  return null;
}

// --- The settings screen ---

type Row =
  | { kind: "volume"; which: "music" | "sound"; label: string }
  | { kind: "style"; label: string }
  | { kind: "key"; action: Action; label: string }
  | { kind: "reset"; label: string }
  | { kind: "pad"; label: string }
  | { kind: "done"; label: string };

const styleName = (s: string) => `${s[0].toUpperCase()}${s.slice(1)}`;

/**
 * The settings screen. `focus` puts the cursor on its sound, keyboard or gamepad part (the item
 * screen's Options rows); "joystick" starts the gamepad check. Changes apply and are kept at once.
 */
export function showOptions(host: OptionsHost, focus: "sound" | "keyboard" | "joystick" = "sound"): Promise<void> {
  const opt = g.menuInt[3] ?? []; // Options, Load, Save, Music, Sound, Joystick, Keyboard, Done
  const keyMenu = g.menuInt[6] ?? []; // KEY CONFIG, UP ... RIGHT SIDEKICK, Reset to Defaults, Done
  const styles = host.music.styles ?? [];
  const actionLabels = ["Up", "Down", "Left", "Right", "Fire", "Change fire", "Left sidekick", "Right sidekick"];

  const rows: Row[] = [
    { kind: "volume", which: "music", label: opt[3] || "Music" },
    { kind: "volume", which: "sound", label: opt[4] || "Sound" },
    ...(styles.length > 1 ? [{ kind: "style" as const, label: "Music style" }] : []),
    ...ACTIONS.map((action, i) => ({ kind: "key" as const, action, label: keyMenu[i + 1] || actionLabels[i] })),
    { kind: "reset", label: keyMenu[9] || "Reset to Defaults" },
    { kind: "pad", label: "Check gamepad buttons" },
    { kind: "done", label: keyMenu[10] || "Done" },
  ];
  const firstKeyRow = rows.findIndex((r) => r.kind === "key");
  const sectionOf = (r: Row) => (r.kind === "volume" || r.kind === "style" ? 0 : r.kind === "key" || r.kind === "reset" ? 1 : r.kind === "pad" ? 2 : 3);
  const sectionTitles = ["Sound", keyMenu[0] ? styleName(keyMenu[0].toLowerCase()) : "Keyboard", (g.menuInt[13] ?? [])[0] || "Gamepad", ""];

  let cur = focus === "keyboard" ? firstKeyRow : focus === "joystick" ? rows.findIndex((r) => r.kind === "pad") : 0;
  let col = 0; // the key slot on a key row
  let capturing = false;
  let checking = focus === "joystick";
  let bHeldSince = 0;

  const root = overlay(
    "options",
    `<div class="panel options-panel" role="dialog" aria-label="Options">
      <h2>${esc(opt[0] || "Options")}</h2>
      <div class="opt-list" data-k="list"></div>
      <div class="opt-padcheck" data-k="pad" hidden></div>
      <footer class="opt-help" data-k="help"></footer>
    </div>`,
  );
  const el = (k: string) => root.querySelector<HTMLElement>(`[data-k="${k}"]`)!;
  const list = el("list");
  const padEl = el("pad");

  const sound = (n: number) => host.sfx.playSampleNum(n);

  const helpText = (): string => {
    const r = rows[cur];
    if (checking) return "Press buttons and move the sticks to check them. Hold B (or press Esc) to finish.";
    if (capturing) return g.miscText[32] || "Press the key to use for this function.";
    switch (r.kind) {
      case "volume": return g.mainMenuHelp[15 - 1] ?? "";
      case "style": return "Change the music with the left/right arrow keys.";
      case "key": return `${g.mainMenuHelp[20 - 1] ?? ""} Left/right picks the first or second key; Delete clears it.`;
      case "reset": return g.mainMenuHelp[25 - 1] ?? "";
      case "pad": return "See which gamepad buttons the game reads, and what they do.";
      case "done": return g.mainMenuHelp[12 - 1] ?? "";
    }
  };

  const rowHtml = (r: Row, i: number): string => {
    const cls = ["opt-row", `opt-${r.kind}`]; // (not "key": overlay.css styles .panel .key)
    if (i === cur) cls.push("cur");
    if (r.kind === "done") cls.push("done");
    let body = `<span class="lbl">${esc(r.label)}</span>`;
    if (r.kind === "volume") body += volumeBarHtml(r.which === "music" ? volume.tyrMusicVolume : volume.fxVolume, r.which);
    if (r.kind === "style") {
      body += `<span class="opt-styles">${styles
        .map((s) => `<button type="button" data-style="${esc(s)}" class="${s === host.music.style ? "on" : ""}">${esc(styleName(s))}</button>`)
        .join("")}</span>`;
    }
    if (r.kind === "key") {
      for (let slot = 0; slot < BINDING_SLOTS; slot++) {
        const c = keys[r.action][slot];
        const sel = i === cur && slot === col;
        const wait = sel && capturing;
        body += `<button type="button" class="opt-slot${sel ? " sel" : ""}${wait ? " wait" : ""}${c ? "" : " none"}" data-slot="${slot}">${wait ? "…" : esc(keyName(c))}</button>`;
      }
    }
    return `<div class="${cls.join(" ")}" data-i="${i}">${body}</div>`;
  };

  const render = () => {
    let html = "";
    let section = -1;
    rows.forEach((r, i) => {
      const s = sectionOf(r);
      if (s !== section) {
        section = s;
        if (sectionTitles[s]) html += `<h3>${esc(sectionTitles[s])}</h3>`;
      }
      html += rowHtml(r, i);
    });
    list.innerHTML = html;
    list.hidden = checking; // the check takes the list's place
    padEl.hidden = !checking;
    el("help").innerHTML = highlight(helpText());
    list.querySelector(".cur")?.scrollIntoView({ block: "nearest" });
  };

  let stopPad: () => void = () => {};
  let resolveDone: () => void = () => {};
  const done = new Promise<void>((r) => (resolveDone = r));
  const close = () => {
    stopPad();
    window.removeEventListener("keydown", onKey, true);
    closeOverlay(root);
    resolveDone();
  };

  const changeVolume = (which: "music" | "sound", dir: number) => {
    sound(S_CURSOR);
    JE_changeVolume(which === "music" ? dir * VOLUME_STEP : 0, which === "sound" ? dir * VOLUME_STEP : 0, sound);
  };
  const changeStyle = (dir: number) => {
    const i = styles.indexOf(host.music.style ?? "original");
    host.music.setStyle?.(styles[(i + dir + styles.length) % styles.length]);
    sound(S_CURSOR);
  };

  const activate = () => {
    const r = rows[cur];
    switch (r.kind) {
      case "style":
        changeStyle(1);
        break;
      case "key":
        sound(S_CLICK);
        capturing = true;
        break;
      case "reset":
        sound(S_CLICK);
        resetKeys();
        savePrefs();
        break;
      case "pad":
        sound(S_CLICK);
        checking = true;
        bHeldSince = 0;
        break;
      case "done":
        sound(S_CLICK);
        close();
        return;
    }
    render();
  };

  const menuKey = (k: PadKey) => {
    if (checking || capturing) {
      if (k === "esc") {
        checking = capturing = false;
        sound(S_SPRING);
        render();
      }
      return;
    }
    const r = rows[cur];
    switch (k) {
      case "up":
      case "down":
        cur = (cur + (k === "up" ? -1 : 1) + rows.length) % rows.length;
        sound(S_CURSOR);
        break;
      case "left":
      case "right": {
        const dir = k === "left" ? -1 : 1;
        if (r.kind === "volume") changeVolume(r.which, dir);
        else if (r.kind === "style") changeStyle(dir);
        else if (r.kind === "key") {
          col = (col + dir + BINDING_SLOTS) % BINDING_SLOTS;
          sound(S_CURSOR);
        }
        break;
      }
      case "enter":
        activate();
        return;
      case "esc":
        sound(S_SPRING);
        close();
        return;
    }
    render();
  };

  /** The KEY CONFIG wait for a key (game_menu.c L2683-2741): Escape cancels, reserved keys clink. */
  const capture = (code: string) => {
    const r = rows[cur];
    capturing = false;
    if (code === "Escape") sound(S_SPRING);
    else if (r.kind === "key" && bindKey(r.action, col, code)) {
      sound(S_CLICK);
      savePrefs();
    } else sound(S_CLINK);
    render();
  };

  const onKey = (e: KeyboardEvent) => {
    const r = rows[cur];
    const clear = !checking && !capturing && r.kind === "key" && (e.code === "Delete" || e.code === "Backspace");
    const k = KEYS_TO_MENU[e.code];
    if (!capturing && !clear && !k) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    if (capturing) {
      if (!e.repeat) capture(e.code);
    } else if (clear && r.kind === "key") {
      clearKey(r.action, col);
      savePrefs();
      sound(S_CLICK);
      render();
    } else if (k) menuKey(k);
  };
  window.addEventListener("keydown", onKey, true);

  list.addEventListener("click", (e) => {
    const t = e.target as HTMLElement;
    const rowEl = t.closest<HTMLElement>("[data-i]");
    if (!rowEl) return;
    if (capturing || checking) {
      capturing = false; // a click cancels the wait, as in the C
      checking = false;
      render();
      return;
    }
    cur = Number(rowEl.dataset.i);
    const r = rows[cur];
    const bar = t.closest<HTMLElement>(".vol-bar");
    const styleBtn = t.closest<HTMLElement>("[data-style]");
    const slotBtn = t.closest<HTMLElement>("[data-slot]");
    if (bar && r.kind === "volume") {
      const v = volumeFromBarCells(volumeBarCells(e, bar));
      if (r.which === "music") volume.tyrMusicVolume = v;
      else volume.fxVolume = v;
      set_volume(volume.tyrMusicVolume, volume.fxVolume);
      sound(S_CURSOR);
      render();
    } else if (styleBtn && r.kind === "style") {
      host.music.setStyle?.(styleBtn.dataset.style!);
      sound(S_CURSOR);
      render();
    } else if (slotBtn && r.kind === "key") {
      col = Number(slotBtn.dataset.slot);
      activate();
    } else if (r.kind !== "volume" && r.kind !== "key") {
      activate();
    } else render();
  });

  // The gamepad check: every button and both sticks, live, with what the game does with them.
  const drawPad = (pads: Gamepad[], now: number) => {
    if (!checking) return;
    const pad = pads[0];
    if (!pad) {
      padEl.innerHTML = `<p>No gamepad found. Connect one and press a button.</p>`;
      return;
    }
    const b = (i: number) => pad.buttons[i];
    const standard = pad.mapping === "standard";
    const chips = pad.buttons
      .map((btn, i) => {
        const [name, use] = standard ? (PAD_BUTTONS[i] ?? [`${i}`, ""]) : [`${i}`, ""];
        const fill = Math.round((btn.value || (btn.pressed ? 1 : 0)) * 100);
        return `<span class="chip${btn.pressed ? " on" : ""}" style="--fill:${fill}%"><b>${esc(name)}</b>${use ? `<small>${esc(use)}</small>` : ""}</span>`;
      })
      .join("");
    const stick = (x = 0, y = 0, label: string) =>
      `<span class="stick"><i style="left:${50 + x * 40}%;top:${50 + y * 40}%"></i><small>${label}</small></span>`;
    padEl.innerHTML = `
      <p class="pad-id">${esc(pad.id)}${standard ? "" : " · non-standard layout: buttons by number, the game expects the standard one"}</p>
      <div class="sticks">${stick(pad.axes[0], pad.axes[1], "Left stick · Move")}${stick(pad.axes[2], pad.axes[3], "Right stick")}</div>
      <div class="chips">${chips}</div>
      <p class="hint">Hold B to finish</p>`;
    // Hold B (button 1) for a second to leave the check: a press alone is part of the check.
    if (b(1)?.pressed) {
      if (!bHeldSince) bHeldSince = now;
      else if (now - bHeldSince > 1000) {
        checking = false;
        bHeldSince = 0;
        sound(S_SPRING);
        render();
      }
    } else bHeldSince = 0;
  };
  padEl.addEventListener("click", () => {
    checking = false;
    render();
  });

  stopPad = pollPad((k) => {
    if (checking) return; // buttons are being checked, not used
    if (capturing && k === "esc") return menuKey("esc");
    if (!capturing) menuKey(k);
  }, drawPad);

  render();
  return done;
}

// --- JE_loadScreen ---

/**
 * JE_loadScreen (mainint.c L619-901): the one-player saved games. Resolves with the slot the
 * player picks (the caller loads it: JE_operation), or null for "Exit to Main Menu" / Escape. An
 * empty slot clinks. (The C's second page, two-player saves, isn't offered: there's no two-player
 * game to continue.)
 */
export function showLoadScreen(host: Pick<OptionsHost, "sfx">): Promise<number | null> {
  const menuItemsCount = 12;
  const slots: SaveSlotView[] = saveSlotViews(1, menuItemsCount - 1);
  let selectedIndex = 0;
  const sound = (n: number) => host.sfx.playSampleNum(n);
  const root = overlay(
    "options load-screen",
    `<div class="panel options-panel" role="dialog" aria-label="Load game">
      <h2>${esc(g.miscText[38] || "One Player Saved Games")}</h2>
      <div class="opt-list slots" data-k="list" role="listbox"></div>
      <footer class="opt-help">${esc(g.mainMenuHelp[21 - 1] ?? "")}</footer>
    </div>`,
  );
  const list = root.querySelector<HTMLElement>('[data-k="list"]')!;
  const lastLevel = g.miscTextB[3 - 1] || "Last Level";
  const episode = g.miscTextB[2 - 1] || "Episode";

  const render = () => {
    list.innerHTML =
      slots
        .map((s, i) => {
          const cls = `opt-row slot${i === selectedIndex ? " cur" : ""}${s.empty ? " empty" : ""}`;
          return `<div class="${cls}" data-i="${i}" role="option" aria-selected="${i === selectedIndex}">
            <span class="slot-name">${esc(s.name)}</span>
            <span class="slot-level">${esc(lastLevel)} ${s.empty ? "-----" : esc(s.levelName)}</span>
            <span class="slot-ep">${s.empty ? "" : `${esc(episode)} ${s.episode}`}</span></div>`;
        })
        .join("") +
      `<div class="opt-row done${selectedIndex === menuItemsCount - 1 ? " cur" : ""}" data-i="${menuItemsCount - 1}" role="option">${esc(g.miscText[33] || "Exit to Main Menu")}</div>`;
    list.querySelector(".cur")?.scrollIntoView({ block: "nearest" });
  };

  return new Promise((resolve) => {
    let stopPad: () => void = () => {};
    const finish = (slot: number | null) => {
      stopPad();
      window.removeEventListener("keydown", onKey, true);
      closeOverlay(root);
      resolve(slot);
    };
    const action = () => {
      if (selectedIndex === menuItemsCount - 1) {
        // "Exit to Main Menu"
        sound(S_SELECT);
        return finish(null);
      }
      const s = slots[selectedIndex];
      if (s.empty) sound(S_CLINK); // "EMPTY SLOT"
      else {
        sound(S_SELECT);
        finish(s.slot);
      }
    };
    const key = (k: PadKey) => {
      switch (k) {
        case "up":
          sound(S_CURSOR);
          selectedIndex = selectedIndex === 0 ? menuItemsCount - 1 : selectedIndex - 1;
          break;
        case "down":
          sound(S_CURSOR);
          selectedIndex = selectedIndex === menuItemsCount - 1 ? 0 : selectedIndex + 1;
          break;
        case "enter":
          return action();
        case "esc":
          sound(S_SPRING);
          return finish(null);
        default:
          return;
      }
      render();
    };
    const onKey = (e: KeyboardEvent) => {
      const k = KEYS_TO_MENU[e.code];
      if (!k) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      key(k);
    };
    window.addEventListener("keydown", onKey, true);
    list.addEventListener("click", (e) => {
      const row = (e.target as HTMLElement).closest<HTMLElement>("[data-i]");
      if (!row) return;
      const i = Number(row.dataset.i);
      if (i !== selectedIndex) sound(S_CURSOR);
      selectedIndex = i;
      render();
      action();
    });
    list.addEventListener("contextmenu", (e) => {
      e.preventDefault(); // the C's right click: back
      sound(S_SPRING);
      finish(null);
    });
    stopPad = pollPad(key);
    render();
  });
}

// --- JE_operation's save dialog ---

/**
 * The save-name dialog of JE_operation (mainint.c L2729-2843): "Save name:" with the slot's name to
 * edit (at most 14 characters the font has), above the last level's name. Resolves with the name
 * on Enter or OK, or null on Escape or CANCEL; JE_itemScreen_operation then saves (or not).
 */
export function promptSaveName(host: Pick<OptionsHost, "sfx">, initial: string): Promise<string | null> {
  const sound = (n: number) => host.sfx.playSampleNum(n);
  const root = overlay(
    "options save-name",
    `<div class="panel options-panel save-box" role="dialog" aria-label="Save game">
      <p>${highlight(g.miscText[1 - 1] || "Last Level Completed")}</p>
      <p class="level">${esc(g.levelName.trim())}</p>
      <label><span>${highlight(g.miscText[2 - 1] || "~Save name: ~")}</span>
        <input type="text" maxlength="14" spellcheck="false" autocomplete="off" /></label>
      <div class="choices row">
        <button type="button" data-act="ok">${esc(g.miscText[9] || "OK")}</button>
        <button type="button" data-act="cancel">${esc(g.miscText[10] || "CANCEL")}</button>
      </div>
    </div>`,
  );
  const input = root.querySelector<HTMLInputElement>("input")!;
  input.value = initial;
  let last = initial;

  return new Promise((resolve) => {
    let stopPad: () => void = () => {};
    const finish = (name: string | null) => {
      stopPad();
      window.removeEventListener("keydown", onKey, true);
      closeOverlay(root);
      resolve(name);
    };
    // Window-level keys for when the field isn't focused (and the gamepad's A/B).
    const onKey = (e: KeyboardEvent) => {
      if (e.target === input) return;
      if (e.code === "Enter" || e.code === "NumpadEnter") finish(input.value);
      else if (e.code === "Escape") finish(null);
      else {
        input.focus();
        return;
      }
      e.preventDefault();
      e.stopImmediatePropagation();
    };
    window.addEventListener("keydown", onKey, true);
    input.addEventListener("keydown", (e) => {
      // Keep the game's key handlers (which take Space, letters and Backspace) out of the typing.
      e.stopPropagation();
      if (e.code === "Enter" || e.code === "NumpadEnter") {
        e.preventDefault();
        finish(input.value);
      } else if (e.code === "Escape") {
        e.preventDefault();
        finish(null);
      }
    });
    input.addEventListener("input", () => {
      const v = [...input.value].filter(saveNameChar).join("").slice(0, 14);
      if (v !== input.value) input.value = v;
      if (v.length > last.length) sound(S_CURSOR);
      else if (v.length < last.length) sound(S_CLICK);
      last = v;
    });
    root.addEventListener("click", (e) => {
      const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]");
      if (b) finish(b.dataset.act === "ok" ? input.value : null);
    });
    stopPad = pollPad((k) => {
      if (k === "enter") finish(input.value);
      else if (k === "esc") finish(null);
    });
    input.focus();
    input.select();
  });
}
