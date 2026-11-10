// The debug console (D109): a screen of the interface framework with a scrollback and an input line,
// over the paused game or the menu it was opened from. Loaded on demand (src/app/consoleBridge.ts),
// so it stays out of the main bundle. Up/Down step through the history, Tab completes, Enter runs,
// Esc or ` closes; on touch screens buttons do the same, and the field takes the on-screen keyboard
// (the window shrinks to the part above it, so the line stays in view).

import "./console.css";
import { backButton, h, showScreen, ui, type Screen } from "../../ui";
import { consoleStore, saveConsoleStore, type ConsoleBridge } from "../../app/consoleBridge";
import { createCommands, runLine, setCompletionBridge, type ConsoleCtx, type LineKind } from "./commands";
import { completeLine, History } from "./parse";
import { perfOverlayOn, setPerfOverlay } from "./perf";
import { g } from "../../sim/state";

const commands = createCommands();
const history = new History(Array.isArray(consoleStore().history) ? consoleStore().history!.filter((l) => typeof l === "string") : []);
/** The scrollback, kept between openings. */
const log: { kind: LineKind | "info"; text: string }[] = [];
const LOG_MAX = 600;

function perf(bridge: ConsoleBridge): ConsoleCtx["perf"] {
  return {
    get: perfOverlayOn,
    set: (on) => {
      setPerfOverlay(bridge, on);
      saveConsoleStore({ perf: on });
    },
  };
}

/** The perf overlay, if it was left on in this browser (consoleBridge.installDebugConsole). */
export function restorePerfOverlay(bridge: ConsoleBridge): void {
  setPerfOverlay(bridge, true);
}

/** One line run without the screen (devtools, scripted checks): its output as text. */
export function runConsoleLine(bridge: ConsoleBridge, line: string): string[] {
  const ctx: ConsoleCtx = {
    bridge,
    close: () => bridge.closeConsole?.(),
    clear: () => (log.length = 0),
    overLeaveScreen: () => !bridge.leave?.screen.open || ui.current === bridge.leave.screen,
    perf: perf(bridge),
  };
  const out = runLine(commands, line, ctx);
  bridge.refresh?.();
  return out.map((l) => (l.kind === "err" ? `error: ${l.text}` : l.text));
}

const PLACE_TEXT = { title: "title", shop: "shop", level: "in a level", menu: "menu" } as const;

function where(bridge: ConsoleBridge): string {
  if (bridge.place === "level" || bridge.place === "shop") {
    const name = g.levelName?.trim();
    return `${PLACE_TEXT[bridge.place]} · episode ${g.episodeNum}${bridge.place === "level" && name ? ` · ${name} (section ${g.mainLevel})` : ""}`;
  }
  return PLACE_TEXT[bridge.place];
}

/** Show the console over whatever is up (nothing, during a level); resolves once it closes. */
export function showConsole(bridge: ConsoleBridge): Promise<void> {
  if (bridge.closeConsole) return Promise.resolve();
  setCompletionBridge(bridge);
  return new Promise((resolve) => {
    const under: Screen | null = ui.current;
    let closed = false;
    const close = () => {
      if (closed) return;
      closed = true;
      bridge.closeConsole = null;
      vv?.removeEventListener("resize", fit);
      vv?.removeEventListener("scroll", fit);
      screen.close();
      bridge.refresh?.();
      resolve();
    };
    bridge.closeConsole = close;

    const screen = showScreen({
      id: "console",
      over: under?.opts.id === "shop" ? "show" : true, // the shop stays in view, so its credits and loadout show the cheats
      backdrop: under ? undefined : "none",
      scrim: false,
      layout: "wide",
      label: "Debug console",
      onKey: (e) => {
        if (e.code === "Enter" || e.code === "NumpadEnter") {
          submit();
          return true;
        }
        if (e.code === "Escape") {
          close();
          return true;
        }
        // Typing with the field unfocused puts the focus back in it.
        if (e.target !== input && e.key.length === 1 && !e.ctrlKey && !e.metaKey) input.focus();
        return false;
      },
      onIntent: (intent) => {
        if (intent === "back") close();
        else if (intent === "accept") submit();
        return true;
      },
      onBack: close,
    });

    const logEl = h("div", { class: "con-log ui-well", attrs: { role: "log", "aria-live": "polite", "aria-label": "Console output" } });
    const input = h("input", {
      class: "con-input",
      attrs: {
        type: "text",
        spellcheck: "false",
        autocomplete: "off",
        autocapitalize: "none",
        autocorrect: "off",
        enterkeyhint: "go",
        "aria-label": "Command",
        placeholder: "help",
      },
    });
    const touchButton = (label: string, aria: string, act: () => void) => {
      const b = h("button", { class: "con-btn", text: label, attrs: { type: "button", "aria-label": aria } });
      // pointerdown, kept from the field: a tap mustn't take the focus (the on-screen keyboard would close).
      b.addEventListener("pointerdown", (e) => e.preventDefault());
      b.addEventListener("click", () => {
        act();
        input.focus();
      });
      return b;
    };
    const keys = h(
      "div",
      { class: "con-keys" },
      touchButton("Tab", "Complete", complete),
      touchButton("↑", "Previous command", () => setInput(history.up(input.value))),
      touchButton("↓", "Next command", () => setInput(history.down(input.value))),
    );
    const run = touchButton("Run", "Run", submit);
    run.classList.add("con-btn--run");
    const line = h("div", { class: "con-line" }, h("span", { class: "con-prompt", text: ">", attrs: { "aria-hidden": "true" } }), input, keys, run);
    const head = h("header", { class: "con-head" }, h("h2", { class: "ui-title con-title", text: "Debug console" }), h("span", { class: "con-where", text: where(bridge) }));
    screen.panel.append(backButton(close, "Close"));
    screen.add(head, logEl, line);

    const lineEl = (l: (typeof log)[number]) => {
      const tab = l.kind === "out" ? l.text.indexOf("\t") : -1;
      if (tab >= 0) return h("div", { class: "con-l con-l--out con-l--row" }, h("span", { text: l.text.slice(0, tab) }), h("span", { text: l.text.slice(tab + 1) }));
      return h("div", { class: `con-l con-l--${l.kind}`, text: l.kind === "cmd" ? `> ${l.text}` : l.text });
    };
    const print = (kind: LineKind | "info", text: string) => {
      log.push({ kind, text });
      logEl.append(lineEl(log.at(-1)!));
      while (log.length > LOG_MAX) {
        log.shift();
        logEl.firstElementChild?.remove();
      }
      logEl.scrollTop = logEl.scrollHeight;
    };
    logEl.append(...log.map(lineEl));
    print("info", `Tyrian 3D debug console (${where(bridge)}). \`help\` lists the commands.`);

    const ctx: ConsoleCtx = {
      bridge,
      close,
      clear: () => {
        log.length = 0;
        logEl.replaceChildren();
      },
      overLeaveScreen: () => !bridge.leave?.screen.open || under === bridge.leave.screen,
      perf: perf(bridge),
    };

    function setInput(v: string): void {
      input.value = v;
      input.setSelectionRange(v.length, v.length);
    }
    function submit(): void {
      const text = input.value;
      setInput("");
      if (!text.trim()) return;
      history.push(text);
      saveConsoleStore({ history: history.lines.slice(-100) });
      print("cmd", text);
      for (const l of runLine(commands, text, ctx)) print(l.kind, l.text);
      if (!closed) bridge.refresh?.();
    }
    function complete(): void {
      const c = completeLine(commands, input.value);
      setInput(c.line);
      if (c.options.length) print("info", c.options.join("  "));
    }

    input.addEventListener("keydown", (e) => {
      if (e.code === "Backquote" && !e.repeat) {
        e.preventDefault();
        close();
      } else if (e.code === "ArrowUp") {
        e.preventDefault();
        setInput(history.up(input.value));
      } else if (e.code === "ArrowDown") {
        e.preventDefault();
        setInput(history.down(input.value));
      } else if (e.code === "Tab") {
        e.preventDefault();
        complete();
      } else if (e.code === "Enter" || e.code === "NumpadEnter" || e.code === "Escape") {
        return; // the framework's: submit() and close() above
      }
      e.stopPropagation(); // the game's keys (Controls, cheat chords) never see the typing
    });

    // The on-screen keyboard: fit the screen to the part of the window above it (visualViewport).
    const vv = window.visualViewport;
    const fit = () => {
      if (!vv) return;
      screen.root.style.top = `${vv.offsetTop}px`;
      screen.root.style.height = `${vv.height}px`;
      screen.root.style.bottom = "auto";
      logEl.scrollTop = logEl.scrollHeight;
    };
    vv?.addEventListener("resize", fit);
    vv?.addEventListener("scroll", fit);
    fit();
    requestAnimationFrame(() => input.focus({ preventScroll: true }));
  });
}
