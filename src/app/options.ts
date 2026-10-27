// The screens around the Options menu, on the interface framework (src/ui/README.md):
//   showOptions      the settings screen: music and sound volume, music style, the keyboard
//                    bindings and a gamepad button check. The title's Options entry opens it, and
//                    so do the item screen's Joystick and Keyboard rows (the C's MENU_JOYSTICK_CONFIG
//                    and MENU_KEYBOARD_CONFIG, game_menu.c L386-440, L2668-2745).
//   showLoadScreen   JE_loadScreen (mainint.c L619-901): the title's list of saved games.
//   promptSaveName   JE_operation's save dialog (mainint.c L2729-2843): the name for a save slot.
//   itemScreenOptionsRow  how the item screen (shop.ts) draws the Options menu's volume rows and the
//                    load/save menu's slots.
// Each is a screen shown over the one that opened it (ScreenOptions.over), so the title or the item
// screen waits underneath and gets the input back when it closes. The rules are elsewhere: volumes
// in src/sim/volume.ts, bindings in bindings.ts, saves in src/sim/savegame.ts. The settings
// screen's own rules (which row does what with which input) are SettingsMenu, apart from the page.

import "./options.css";
import type { MusicPlayer } from "../audio/remaster";
import type { SoundEffects } from "../audio/sfx";
import type { ItemScreenEntry } from "../sim/game_menu";
import { saveNameChar, saveSlotViews, type SaveSlotView } from "../sim/savegame";
import { S_CLICK, S_CLINK, S_CURSOR, S_SELECT, S_SPRING } from "../sim/sndmast";
import { g } from "../sim/state";
import { JE_changeVolume, set_volume, volume, volumeFromBarCells, VOLUME_STEP } from "../sim/volume";
import { backButton, button, h, keyHints, MenuList, moveFocus, reveal, showScreen, title, type InputDevice, type Intent, type KeyHint } from "../ui";
import { ACTIONS, BINDING_SLOTS, bindKey, clearKey, keyName, playerKeys, resetKeys, type Action, type PlayerIndex } from "./bindings";
import { savePrefs } from "./prefs";

export interface OptionsHost {
  sfx: SoundEffects;
  /** The music; a MusicSwitch also offers its styles (local remaster packs). */
  music: MusicPlayer & { readonly styles?: readonly string[]; readonly style?: string; setStyle?(style: string): void };
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
/** Tyrian's text toggles a highlight with '~' (JE_textShade / JE_helpBox). */
const highlight = (s: string) => esc(s).replace(/~([^~]*)~?/g, "<b>$1</b>");

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

/** How long B must be held to leave the gamepad check (a press alone is part of the check). */
export const PAD_CHECK_HOLD_MS = 1000;

// --- Volume sliders ---

/** JE_barDrawShadow's cells for a volume: tyrMusicVolume / 12, up to 21 (game_menu.c L667-668). */
export const VOLUME_CELLS = Math.trunc(255 / VOLUME_STEP);

/** How full a volume's bar is drawn: the C's lit cells out of VOLUME_CELLS. */
export function volumeFill(vol: number): number {
  return Math.min(VOLUME_CELLS, Math.max(0, Math.trunc(vol / VOLUME_STEP))) / VOLUME_CELLS;
}

/**
 * The bar cell a point `fraction` of the way along the bar lands on, as the C counts 4-pixel cells
 * from the bar's start (game_menu.c L1047-1080); the far end is full volume.
 */
export function volumeCellsAt(fraction: number): number {
  const cells = Math.round(fraction * VOLUME_CELLS);
  return cells >= VOLUME_CELLS ? VOLUME_CELLS + 1 : Math.max(0, cells);
}

/** The bar cell a click or drag at `e` lands on (volumeCellsAt). */
export function volumeBarCells(e: { clientX: number }, bar: HTMLElement): number {
  const r = bar.getBoundingClientRect();
  return volumeCellsAt((e.clientX - r.left) / Math.max(1, r.width));
}

/**
 * A volume slider: a stat bar cut into the C's 21 cells, and the value. `row` goes in
 * data-vol-row (the item screen's row number, or the settings screen's "music" / "sound"); the
 * element carrying it is the bar a tap or drag measures.
 */
function volumeSliderHtml(vol: number, row: number | string, label: string): string {
  return (
    `<span class="opt-vol ui-stat--gold" data-vol-row="${row}" role="slider" aria-label="${esc(label)}" aria-valuemin="0" aria-valuemax="255" aria-valuenow="${vol}">` +
    `<span class="ui-stat__bar"><i style="width:${(volumeFill(vol) * 100).toFixed(2)}%"></i></span></span>` +
    `<span class="opt-vol__num">${vol}</span>`
  );
}

/** Show `vol` on a slider made by volumeSliderHtml (the bar's element and its number after it). */
function setVolumeSlider(bar: HTMLElement, vol: number): void {
  bar.querySelector<HTMLElement>("i")!.style.width = `${(volumeFill(vol) * 100).toFixed(2)}%`;
  bar.setAttribute("aria-valuenow", String(vol));
  const num = bar.nextElementSibling;
  if (num) num.textContent = String(vol);
}

// --- The item screen's rows ---

/**
 * The inner HTML for an item-screen row this file draws: the Options menu's Music and Sound rows
 * (their volume sliders; a tap goes to JE_itemScreen_volumeClick) and the load/save menu's slots
 * (name, last level, episode: game_menu.c L328-383). Null for any other row.
 */
export function itemScreenOptionsRow(e: ItemScreenEntry): string | null {
  if (e.saveSlot) {
    const s = e.saveSlot;
    const level = s.empty ? "-----" : esc(s.levelName); /* Empty save slot */
    const ep = s.empty ? "" : `<span class="slot-ep">${esc(g.miscTextB[1 - 1] ?? "Ep")}${s.episode}</span>`;
    return `<span class="what ui-menu__label slot-name">${esc(s.name)}</span><span class="slot-level">${level}</span>${ep}`;
  }
  if (e.volume !== undefined) return `<span class="what ui-menu__label">${esc(e.label)}</span>${volumeSliderHtml(e.volume, e.sel, e.label)}`;
  return null;
}

// --- The settings screen's rules ---

export type OptionsRow =
  | { kind: "volume"; which: "music" | "sound"; label: string }
  | { kind: "style"; label: string }
  | { kind: "key"; action: Action; label: string; player: PlayerIndex }
  | { kind: "reset"; label: string; player: PlayerIndex }
  | { kind: "pad"; label: string }
  | { kind: "done"; label: string };

export type OptionsFocus = "sound" | "keyboard" | "joystick";

const styleName = (s: string) => `${s[0].toUpperCase()}${s.slice(1)}`;

/** The settings screen's rows, labelled from the game's menu text where it has them. */
export function optionsRows(styles: readonly string[]): OptionsRow[] {
  const opt = g.menuInt[3] ?? []; // Options, Load, Save, Music, Sound, Joystick, Keyboard, Done
  const keyMenu = g.menuInt[6] ?? []; // KEY CONFIG, UP ... RIGHT SIDEKICK, Reset to Defaults, Done
  const actionLabels = ["Up", "Down", "Left", "Right", "Fire", "Change fire", "Left sidekick", "Right sidekick"];
  return [
    { kind: "volume", which: "music", label: opt[3] || "Music" },
    { kind: "volume", which: "sound", label: opt[4] || "Sound" },
    ...(styles.length > 1 ? [{ kind: "style" as const, label: "Music style" }] : []),
    // [two-player] player 1's (and the one-player game's) keys, then player 2's
    ...([0, 1] as const).flatMap((player) => [
      ...ACTIONS.map((action, i) => ({ kind: "key" as const, action, label: keyMenu[i + 1] || actionLabels[i], player })),
      { kind: "reset" as const, label: keyMenu[9] || "Reset to Defaults", player },
    ]),
    { kind: "pad", label: "Check gamepad buttons" },
    { kind: "done", label: keyMenu[10] || "Done" },
  ];
}

/** What the settings rules act on besides the volumes and bindings (the screen, or a test). */
export interface SettingsHost {
  sound(sample: number): void;
  /** The music styles to choose from (local remaster packs), and the one playing. */
  styles: readonly string[];
  style(): string | undefined;
  setStyle(style: string): void;
  /** Leave the settings screen. */
  close(): void;
}

/**
 * The settings screen's state and what each input does to it, apart from the page (so it's tested
 * without a browser). Changes apply and are kept at once: volumes through JE_changeVolume and
 * set_volume (the host saves them), bindings with savePrefs.
 */
export class SettingsMenu {
  /** The focused row. */
  cur: number;
  /** The key slot on a key row. */
  col = 0;
  /** Waiting for the key to bind (KEY CONFIG's wait, game_menu.c L2683-2741). */
  capturing = false;
  /** The gamepad check is up instead of the list. */
  checking: boolean;
  private bHeldSince = 0;

  constructor(
    readonly rows: OptionsRow[],
    focus: OptionsFocus,
    private readonly host: SettingsHost,
  ) {
    this.cur = focus === "keyboard" ? rows.findIndex((r) => r.kind === "key") : focus === "joystick" ? rows.findIndex((r) => r.kind === "pad") : 0;
    this.checking = focus === "joystick";
  }

  get row(): OptionsRow {
    return this.rows[this.cur];
  }

  /**
   * An intent from the framework (keys, pad). While a key is awaited the keyboard goes to key();
   * the pad's B cancels. During the gamepad check the pad's buttons are being checked, not used:
   * only the keyboard's Escape (or holding B, padHold) ends it.
   */
  intent(intent: Intent, device: InputDevice): void {
    const sound = this.host.sound;
    if (this.checking || this.capturing) {
      if (intent === "back" && (this.capturing || device !== "pad")) {
        this.checking = this.capturing = false;
        sound(S_SPRING);
      }
      return;
    }
    const r = this.row;
    switch (intent) {
      case "up":
      case "down":
        this.cur = moveFocus(this.rows.length, this.cur, intent === "up" ? -1 : 1);
        sound(S_CURSOR);
        break;
      case "left":
      case "right": {
        const dir = intent === "left" ? -1 : 1;
        if (r.kind === "volume") this.changeVolume(r.which, dir);
        else if (r.kind === "style") this.changeStyle(dir);
        else if (r.kind === "key") {
          this.col = (this.col + dir + BINDING_SLOTS) % BINDING_SLOTS;
          sound(S_CURSOR);
        }
        break;
      }
      case "accept":
        this.activate();
        break;
      case "back":
        sound(S_SPRING);
        this.host.close();
        break;
    }
  }

  /**
   * A raw key, before it becomes an intent. While a key is awaited every key is taken (Escape
   * cancels, reserved keys clink); on a key row Delete or Backspace clears the slot. True if used.
   */
  key(code: string, repeat = false): boolean {
    if (this.capturing) {
      if (!repeat) this.capture(code);
      return true;
    }
    const r = this.row;
    if (!this.checking && r.kind === "key" && (code === "Delete" || code === "Backspace")) {
      clearKey(r.action, this.col, r.player);
      savePrefs();
      this.host.sound(S_CLICK);
      return true;
    }
    return false;
  }

  /** Enter / A on the focused row. */
  activate(): void {
    const sound = this.host.sound;
    switch (this.row.kind) {
      case "style":
        this.changeStyle(1);
        break;
      case "key":
        sound(S_CLICK);
        this.capturing = true;
        break;
      case "reset":
        sound(S_CLICK);
        resetKeys(this.row.player);
        savePrefs();
        break;
      case "pad":
        sound(S_CLICK);
        this.checking = true;
        this.bHeldSince = 0;
        break;
      case "done":
        sound(S_CLICK);
        this.host.close();
        break;
    }
  }

  /**
   * A tap or click on row `i`, on one of its key slots or music styles if `part` says so. A tap
   * while a key is awaited or the gamepad is checked only cancels that, as a click does in the C.
   */
  tap(i: number, part: { slot?: number; style?: string } = {}): void {
    if (this.cancelWait()) return;
    this.cur = i;
    const r = this.row;
    if (part.style !== undefined && r.kind === "style") {
      this.host.setStyle(part.style);
      this.host.sound(S_CURSOR);
    } else if (part.slot !== undefined && r.kind === "key") {
      this.col = part.slot;
      this.activate();
    } else if (r.kind !== "volume" && r.kind !== "key") this.activate();
  }

  /** A tap or drag on row `i`'s volume bar, `cells` cells along it (volumeCellsAt). */
  setVolumeCells(i: number, cells: number): void {
    if (this.cancelWait()) return;
    this.cur = i;
    const r = this.row;
    if (r.kind !== "volume") return;
    const v = volumeFromBarCells(cells);
    if (r.which === "music") volume.tyrMusicVolume = v;
    else volume.fxVolume = v;
    set_volume(volume.tyrMusicVolume, volume.fxVolume);
    this.host.sound(S_CURSOR);
  }

  /** Stop waiting for a key and end the gamepad check, silently; true if either was on. */
  cancelWait(): boolean {
    const was = this.capturing || this.checking;
    this.capturing = this.checking = false;
    return was;
  }

  /** The gamepad check, every frame: holding B for PAD_CHECK_HOLD_MS ends it. True when it ended. */
  padHold(bPressed: boolean, now: number): boolean {
    if (!this.checking) return false;
    if (!bPressed) this.bHeldSince = 0;
    else if (!this.bHeldSince) this.bHeldSince = now;
    else if (now - this.bHeldSince > PAD_CHECK_HOLD_MS) {
      this.checking = false;
      this.bHeldSince = 0;
      this.host.sound(S_SPRING);
      return true;
    }
    return false;
  }

  /** The help line: the game's own help text for the row where it has one. */
  helpText(): string {
    if (this.checking) return "Press buttons and move the sticks to check them. Hold B (or press Esc) to finish.";
    if (this.capturing) return g.miscText[32] || "Press the key to use for this function.";
    switch (this.row.kind) {
      case "volume": return g.mainMenuHelp[15 - 1] ?? "";
      case "style": return "Change the music with the left/right arrow keys.";
      case "key":
        return (
          `${g.mainMenuHelp[20 - 1] ?? ""} Left/right picks the first or second key; Delete clears it.` +
          (this.row.player === 1 ? " In a two-player game, player 2's keys win over player 1's." : "")
        );
      case "reset": return g.mainMenuHelp[25 - 1] ?? "";
      case "pad": return "See which gamepad buttons the game reads, and what they do.";
      case "done": return g.mainMenuHelp[12 - 1] ?? "";
    }
  }

  private changeVolume(which: "music" | "sound", dir: number): void {
    this.host.sound(S_CURSOR);
    JE_changeVolume(which === "music" ? dir * VOLUME_STEP : 0, which === "sound" ? dir * VOLUME_STEP : 0, this.host.sound);
  }

  private changeStyle(dir: number): void {
    const styles = this.host.styles;
    const i = styles.indexOf(this.host.style() ?? "original");
    this.host.setStyle(styles[(i + dir + styles.length) % styles.length]);
    this.host.sound(S_CURSOR);
  }

  /** The awaited key (game_menu.c L2683-2741): Escape cancels, reserved keys clink. */
  private capture(code: string): void {
    const r = this.row;
    this.capturing = false;
    if (code === "Escape") this.host.sound(S_SPRING);
    else if (r.kind === "key" && bindKey(r.action, this.col, code, r.player)) {
      this.host.sound(S_CLICK);
      savePrefs();
    } else this.host.sound(S_CLINK);
  }
}

// --- The settings screen ---

/**
 * The settings screen. `focus` puts the cursor on its sound, keyboard or gamepad part (the item
 * screen's Options rows); "joystick" starts the gamepad check. Changes apply and are kept at once.
 * Shown over the screen that opened it, which waits underneath.
 */
export function showOptions(host: OptionsHost, focus: OptionsFocus = "sound"): Promise<void> {
  return new Promise((resolve) => {
    const styles = host.music.styles ?? [];
    const sound = (n: number) => host.sfx.playSampleNum(n);
    let raf = 0;
    const finish = () => {
      if (!screen.open) return;
      cancelAnimationFrame(raf);
      screen.close();
      resolve();
    };
    const menu = new SettingsMenu(optionsRows(styles), focus, {
      sound,
      styles,
      style: () => host.music.style,
      setStyle: (s) => host.music.setStyle?.(s),
      close: finish,
    });
    const rows = menu.rows;

    const screen = showScreen({
      id: "options",
      over: true,
      layout: "center",
      label: "Options",
      // Raw keys first, so the key being bound never becomes an intent (or reaches the game).
      onKey: (e) => {
        const used = menu.key(e.code, e.repeat);
        if (used) paint();
        return used;
      },
      onIntent: (intent, device) => {
        menu.intent(intent, device);
        paint();
        return true;
      },
    });

    // The rows, in sections: Sound, Keyboard (the C's KEY CONFIG), player 2's keyboard, Gamepad, then Done.
    const keyMenu = g.menuInt[6] ?? [];
    const sectionOf = (r: OptionsRow) =>
      r.kind === "volume" || r.kind === "style" ? 0 : r.kind === "key" || r.kind === "reset" ? 1 + r.player : r.kind === "pad" ? 3 : 4;
    const keyboard = keyMenu[0] ? styleName(keyMenu[0].toLowerCase()) : "Keyboard";
    const sectionTitles = ["Sound", keyboard, `${keyboard} · ${g.miscText[49]?.trim() || "Player 2"}`, (g.menuInt[13] ?? [])[0] || "Gamepad", ""];
    const list = h("ul", { class: "ui-menu opt-list", attrs: { role: "listbox", "aria-label": "Settings" } });
    const rowEls: HTMLLIElement[] = [];
    let section = -1;
    rows.forEach((r, i) => {
      const s = sectionOf(r);
      if (s !== section) {
        section = s;
        if (sectionTitles[s]) list.append(h("li", { class: "ui-label opt-section", attrs: { role: "presentation" }, text: sectionTitles[s] }));
      }
      const li = h("li", { class: `ui-menu__item opt-row opt-row--${r.kind}`, attrs: { role: "option", "data-i": String(i) } }, h("span", { class: "ui-menu__label opt-row__label", text: r.label }));
      if (r.kind === "volume") li.insertAdjacentHTML("beforeend", volumeSliderHtml(0, r.which, r.label));
      if (r.kind === "style") {
        li.append(h("span", { class: "opt-styles" }, ...styles.map((st) => h("button", { class: "opt-chip", text: styleName(st), attrs: { type: "button", tabindex: "-1", "data-style": st } }))));
      }
      if (r.kind === "key") {
        li.append(
          h("span", { class: "opt-keys" }, ...Array.from({ length: BINDING_SLOTS }, (_, slot) => h("button", { class: "opt-key", attrs: { type: "button", tabindex: "-1", "data-slot": String(slot) } }))),
        );
      }
      rowEls.push(li);
      list.append(li);
    });
    const padEl = h("div", { class: "opt-padcheck", attrs: { hidden: "", role: "status" } });
    const help = h("p", { class: "opt-help", attrs: { "aria-live": "polite" } });
    const hints = h("div", { class: "opt-hints" });
    // The help and hints stay in view at the panel's foot while the rows scroll.
    const foot = h("div", { class: "opt-foot" }, help, hints);

    screen.panel.append(backButton(() => (menu.intent("back", "touch"), paint())));
    screen.add(title((g.menuInt[3] ?? [])[0] || "Options", "Settings"), list, padEl, foot);

    /** The key hints for what the focused row (or the wait, or the check) takes. */
    const hintsFor = (): KeyHint[] => {
      if (menu.checking) return [{ key: "Esc", pad: "Hold B", touch: "Tap", label: "Finish" }];
      if (menu.capturing) return [{ key: "Any key", label: "Bind" }, { key: "Esc", pad: "B", touch: "Tap", label: "Cancel" }];
      const kind = menu.row.kind;
      const side: Partial<Record<OptionsRow["kind"], KeyHint>> = {
        volume: { key: "←→", pad: "✛", touch: "Drag", label: "Volume" },
        style: { key: "←→", pad: "✛", label: "Music" },
        key: { key: "←→", pad: "✛", label: "Key slot" },
      };
      return [
        { key: "↑↓", pad: "✛", label: "Move" },
        ...(side[kind] ? [side[kind]] : []),
        ...(kind === "volume" ? [] : [{ key: "Enter", pad: "A", touch: "Tap", label: kind === "key" ? "Change key" : "Select" }]),
        ...(kind === "key" ? [{ key: "Del", label: "Clear" }] : []),
        { key: "Esc", pad: "B", label: "Back" },
      ];
    };
    let hintsId = "";

    /** Draw the state: focus, values, the awaited key, the check, the help and hints. */
    const paint = () => {
      rows.forEach((r, i) => {
        const li = rowEls[i];
        const focused = i === menu.cur;
        li.classList.toggle("is-focused", focused);
        li.setAttribute("aria-selected", String(focused));
        if (r.kind === "volume") setVolumeSlider(li.querySelector<HTMLElement>(".opt-vol")!, r.which === "music" ? volume.tyrMusicVolume : volume.fxVolume);
        if (r.kind === "style") li.querySelectorAll<HTMLElement>("[data-style]").forEach((b) => b.classList.toggle("is-on", b.dataset.style === host.music.style));
        if (r.kind === "key") {
          li.querySelectorAll<HTMLElement>("[data-slot]").forEach((b, slot) => {
            const code = playerKeys(r.player)[r.action][slot];
            const sel = focused && slot === menu.col;
            const wait = sel && menu.capturing;
            b.textContent = wait ? "…" : keyName(code);
            b.classList.toggle("is-focused", sel);
            b.classList.toggle("is-waiting", wait);
            b.classList.toggle("is-none", !code);
          });
        }
      });
      list.hidden = menu.checking; // the check takes the list's place
      padEl.hidden = !menu.checking;
      help.innerHTML = highlight(menu.helpText());
      const id = `${menu.checking} ${menu.capturing} ${menu.row.kind}`;
      if (id !== hintsId) {
        hintsId = id;
        hints.replaceChildren(keyHints(hintsFor()));
      }
      if (!menu.checking) reveal(rowEls[menu.cur]);
    };

    // Taps and clicks: a row focuses (and does what Enter would, except on volume and key rows);
    // a key slot waits for its key; a music style plays it. Volume bars take a tap or a drag.
    list.addEventListener("click", (e) => {
      const t = e.target as HTMLElement;
      const rowEl = t.closest<HTMLElement>("[data-i]");
      if (!rowEl || t.closest(".opt-vol")) return;
      const slot = t.closest<HTMLElement>("[data-slot]")?.dataset.slot;
      menu.tap(Number(rowEl.dataset.i), { slot: slot === undefined ? undefined : Number(slot), style: t.closest<HTMLElement>("[data-style]")?.dataset.style });
      paint();
    });
    let drag: { pointer: number; i: number; bar: HTMLElement; cells: number } | null = null;
    list.addEventListener("pointerdown", (e) => {
      const bar = (e.target as HTMLElement).closest<HTMLElement>(".opt-vol");
      const rowEl = bar?.closest<HTMLElement>("[data-i]");
      if (!bar || !rowEl || drag) return;
      e.preventDefault();
      const i = Number(rowEl.dataset.i);
      if (menu.cancelWait()) return paint();
      drag = { pointer: e.pointerId, i, bar, cells: volumeBarCells(e, bar) };
      bar.setPointerCapture?.(e.pointerId);
      menu.setVolumeCells(i, drag.cells);
      paint();
    });
    list.addEventListener("pointermove", (e) => {
      if (!drag || e.pointerId !== drag.pointer) return;
      const cells = volumeBarCells(e, drag.bar);
      if (cells === drag.cells) return;
      drag.cells = cells;
      menu.setVolumeCells(drag.i, cells);
      paint();
    });
    const endDrag = (e: PointerEvent) => {
      if (drag && e.pointerId === drag.pointer) drag = null;
    };
    list.addEventListener("pointerup", endDrag);
    list.addEventListener("pointercancel", endDrag);
    padEl.addEventListener("click", () => {
      menu.cancelWait();
      paint();
    });

    // The gamepad check: every button and both sticks, live, with what the game does with them.
    const drawPad = (now: number) => {
      const pad = (navigator.getGamepads?.() ?? []).find((p): p is Gamepad => !!p);
      if (!pad) {
        padEl.innerHTML = `<p class="opt-pad__none">No gamepad found. Connect one and press a button.</p>`;
        return;
      }
      const standard = pad.mapping === "standard";
      const chips = pad.buttons
        .map((btn, i) => {
          const [name, use] = standard ? (PAD_BUTTONS[i] ?? [`${i}`, ""]) : [`${i}`, ""];
          const fill = Math.round((btn.value || (btn.pressed ? 1 : 0)) * 100);
          return `<span class="opt-pad__chip${btn.pressed ? " is-on" : ""}" style="--fill:${fill}%"><b>${esc(name)}</b>${use ? `<small>${esc(use)}</small>` : ""}</span>`;
        })
        .join("");
      const stick = (x = 0, y = 0, label: string) =>
        `<span class="opt-pad__stick"><i style="left:${50 + x * 40}%;top:${50 + y * 40}%"></i><small>${label}</small></span>`;
      padEl.innerHTML = `
        <p class="opt-pad__id">${esc(pad.id)}${standard ? "" : " · non-standard layout: buttons by number, the game expects the standard one"}</p>
        <div class="opt-pad__sticks">${stick(pad.axes[0], pad.axes[1], "Left stick · Move")}${stick(pad.axes[2], pad.axes[3], "Right stick")}</div>
        <div class="opt-pad__chips">${chips}</div>`;
      // Hold B (button 1) to leave the check.
      if (menu.padHold(!!pad.buttons[1]?.pressed, now)) paint();
    };
    const frame = (now: number) => {
      if (!screen.open) return;
      if (menu.checking) drawPad(now);
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    paint();
  });
}

// --- JE_loadScreen ---

/**
 * JE_loadScreen (mainint.c L619-901): the saved games, one-player and (left/right, [two-player])
 * two-player. Resolves with the slot the player picks (the caller loads it: JE_operation), or null
 * for "Exit to Main Menu" / Escape. An empty slot clinks.
 */
export function showLoadScreen(host: Pick<OptionsHost, "sfx">): Promise<number | null> {
  const menuItemsCount = 12;
  // [two-player] Left/right page between the one-player saves (slots 1-11) and the two-player
  // ones (12-22), as the C's playersIndex does (mainint.c L626-899).
  let playersIndex = 0;
  let slots: SaveSlotView[] = saveSlotViews(1, menuItemsCount - 1);
  const sound = (n: number) => host.sfx.playSampleNum(n);
  const lastLevel = g.miscTextB[3 - 1] || "Last Level";
  const episode = g.miscTextB[2 - 1] || "Episode";

  return new Promise((resolve) => {
    const finish = (slot: number | null) => {
      if (!screen.open) return;
      screen.close();
      resolve(slot);
    };
    const back = () => {
      sound(S_SPRING);
      finish(null);
    };
    const action = (selectedIndex: number) => {
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
    const page = (index: number) => {
      if (index === playersIndex || index < 0 || index > 1) return;
      sound(S_CURSOR);
      playersIndex = index;
      slots = saveSlotViews(playersIndex * 11 + 1, menuItemsCount - 1);
      list.setItems(items());
      paintPage();
    };
    const screen = showScreen({
      id: "load",
      over: true,
      layout: "center",
      label: "Load game",
      onBack: back,
      onIntent: (intent) => {
        if (intent !== "left" && intent !== "right") return false;
        page(playersIndex + (intent === "left" ? -1 : 1));
        return true;
      },
    });
    const items = () => [
      ...slots.map((s) => ({
        label: s.name,
        detail: `${lastLevel} ${s.empty ? "-----" : s.levelName}`,
        badge: s.empty ? undefined : `${episode} ${s.episode}`,
        class: s.empty ? "is-empty" : "",
      })),
      { label: g.miscText[33] || "Exit to Main Menu", class: "load-exit" },
    ];
    const list = new MenuList({
      label: "Saved games",
      class: "load-list",
      items: items(),
      onFocus: () => sound(S_CURSOR),
      onSelect: action,
    });
    list.el.addEventListener("contextmenu", (e) => {
      e.preventDefault(); // the C's right click: back
      back();
    });
    screen.panel.append(backButton(back));
    // [two-player] the page's title, and the C's paging arrows (left: one player, right: two)
    const heading = title(g.miscText[38] || "One Player Saved Games", "Load game");
    const arrow = (dir: -1 | 1) =>
      button({ label: dir < 0 ? "◀" : "▶", variant: "ghost", class: "load-page", onPress: () => page(playersIndex + dir) });
    const prev = arrow(-1);
    const next = arrow(1);
    const paintPage = () => {
      heading.querySelector("span:last-child")!.textContent = g.miscText[38 + playersIndex] || ["One Player Saved Games", "Two Player Saved Games"][playersIndex];
      prev.hidden = playersIndex === 0;
      next.hidden = playersIndex === 1;
    };
    paintPage();
    screen.add(
      h("div", { class: "load-pages" }, prev, heading, next),
      list,
      h("p", { class: "opt-help", text: g.mainMenuHelp[21 - 1] ?? "" }),
      keyHints([
        { key: "↑↓", pad: "✛", label: "Move" },
        { key: "←→", pad: "✛", label: "One / two players" },
        { key: "Enter", pad: "A", touch: "Tap", label: "Load" },
        { key: "Esc", pad: "B", label: "Back" },
      ]),
    );
  });
}

// --- JE_operation's save dialog ---

/**
 * The save-name dialog of JE_operation (mainint.c L2729-2843): "Save name:" with the slot's name to
 * edit (at most 14 characters the font has), under the last level's name. Resolves with the name
 * on Enter, A or OK, or null on Escape, B or CANCEL; JE_itemScreen_operation then saves (or not).
 * Shown over the item screen, which stays in view.
 */
export function promptSaveName(host: Pick<OptionsHost, "sfx">, initial: string): Promise<string | null> {
  const sound = (n: number) => host.sfx.playSampleNum(n);
  return new Promise((resolve) => {
    const input = h("input", { class: "save-name__input", attrs: { type: "text", maxlength: "14", spellcheck: "false", autocomplete: "off", "aria-label": "Save name" } });
    input.value = initial;
    let last = initial;
    const finish = (name: string | null) => {
      if (!screen.open) return;
      screen.close();
      resolve(name);
    };
    const screen = showScreen({
      id: "save-name",
      over: "show",
      scrim: true,
      layout: "narrow",
      label: "Save game",
      // The framework leaves keys typed into the field alone, except Enter and Escape (intents
      // below). Typing with the field unfocused puts the focus back in it.
      onKey: (e) => {
        if (e.target !== input) input.focus();
        return false;
      },
      onIntent: (intent) => {
        if (intent === "accept") finish(input.value);
        else if (intent === "back") finish(null);
        return true;
      },
    });
    // Keep the game's key handlers (which take Space, letters and Backspace) out of the typing.
    input.addEventListener("keydown", (e) => e.stopPropagation());
    input.addEventListener("input", () => {
      const v = [...input.value].filter(saveNameChar).join("").slice(0, 14);
      if (v !== input.value) input.value = v;
      if (v.length > last.length) sound(S_CURSOR);
      else if (v.length < last.length) sound(S_CLICK);
      last = v;
    });
    // A tap outside the field (on OK, or beside it) leaves the focus, and a phone's keyboard, there.
    screen.root.addEventListener("mousedown", (e) => {
      if (e.target !== input) e.preventDefault();
    });
    const lastLevel = (g.miscText[1 - 1] || "Last Level Completed").replace(/~/g, "");
    screen.add(
      title(g.levelName.trim() || "-----", lastLevel),
      h("label", { class: "save-name__field" }, h("span", { html: highlight(g.miscText[2 - 1] || "~Save name: ~") }), input),
      h(
        "div",
        { class: "ui-actions" },
        button({ label: g.miscText[9] || "OK", variant: "primary", hint: { key: "Enter", pad: "A" }, onPress: () => finish(input.value) }),
        button({ label: g.miscText[10] || "CANCEL", hint: { key: "Esc", pad: "B" }, onPress: () => finish(null) }),
      ),
    );
    input.focus();
    input.select();
  });
}
