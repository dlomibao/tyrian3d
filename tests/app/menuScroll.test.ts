// Every menu screen must scroll when its content doesn't fit a short phone (D97). The bug was
// structural (a screen's one grid track was `auto`, so a pane's `max-height: 100%` and the shop's
// `height: 100%` never resolved and `overflow: hidden` cut the pane off), so this pins the structure:
// the screen has a definite track, its pane scrolls, nothing turns that scroll off, and every screen
// the app opens is on the list below (a new screen has to say how it scrolls).
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(__dirname, "..", "..", "src");
const walk = (dir: string): string[] =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
const files = walk(ROOT);
const css = files.filter((f) => f.endsWith(".css")).map((f) => ({ f, text: readFileSync(f, "utf8") }));
const ts = files.filter((f) => f.endsWith(".ts") && !f.includes("/sim/"));

/** Rules of a stylesheet as [selector, body] (no nesting in these files; at-rules are unwrapped). */
function rules(text: string): [string, string][] {
  const out: [string, string][] = [];
  const re = /([^{}]+)\{([^{}]*)\}/g;
  for (let m = re.exec(text.replace(/\/\*[\s\S]*?\*\//g, "")); m; m = re.exec(text.replace(/\/\*[\s\S]*?\*\//g, ""))) {
    if (m.index < 0) break;
    out.push([m[1].trim().replace(/\s+/g, " "), m[2]]);
    if (out.length > 5000) break;
  }
  return out;
}
const allRules = css.flatMap(({ f, text }) => {
  const clean = text.replace(/\/\*[\s\S]*?\*\//g, "");
  const found: [string, string, string][] = [];
  const re = /([^{}]+)\{([^{}]*)\}/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(clean))) found.push([f, m[1].trim().replace(/\s+/g, " "), m[2]]);
  return found;
});
void rules;
const body = (selector: string) =>
  allRules
    .filter(([, sel]) => sel.split(",").some((s) => s.trim() === selector))
    .map(([, , b]) => b)
    .join("\n");

/** How each screen scrolls. "panel": the framework's .ui-panel (overflow-y: auto) is its scroller;
 *  "fits": a fixed-size screen with its own paging or no long content (still must not trap focus). */
const SCREENS: Record<string, "panel" | "fits"> = {
  shop: "panel", // the item screen and its submenus, Data Cubes reader, 2-player shop (the panel scrolls)
  options: "panel", // key config, joystick, gamepad check are rows of this panel
  load: "panel",
  "save-name": "panel",
  highscores: "panel",
  "highscore-entry": "panel",
  gameplay: "panel",
  data: "panel",
  message: "panel",
  status: "panel",
  pause: "panel",
  "title-code": "panel",
  "super-arcade": "panel",
  "super-tyrian": "panel",
  title: "panel", // its own grid (D64): the logo, the steps' panel, the foot
  cinema: "fits", // story and episode-end text: a stage; the text pane scrolls (.cinema-text is a .ui-panel)
  "destruct-modes": "panel",
};

describe("menu screens scroll on a short window", () => {
  it("a screen has one definite track, so panes can size against the window", () => {
    expect(body(".ui-screen")).toMatch(/grid-template:\s*minmax\(0,\s*1fr\)\s*\/\s*minmax\(0,\s*1fr\)/);
    expect(body(".ui-screen")).toMatch(/touch-action:\s*pan-y/);
  });

  it("the framework pane scrolls on its own, without bouncing the page", () => {
    const panel = body(".ui-panel");
    expect(panel).toMatch(/max-height:\s*100%/);
    expect(panel).toMatch(/overflow-y:\s*auto/);
    expect(panel).toMatch(/overscroll-behavior:\s*contain/);
    expect(body(".ui-scroll")).toMatch(/overflow-y:\s*auto/);
  });

  it("every screen the app opens is accounted for", () => {
    const ids = new Set<string>();
    for (const f of ts) {
      const src = readFileSync(f, "utf8");
      for (const m of src.matchAll(/showScreen\(\{[^}]*?\bid:\s*"([a-z0-9-]+)"/g)) ids.add(m[1]);
    }
    expect(ids.size).toBeGreaterThan(10);
    for (const id of ids) expect(SCREENS, `screen "${id}" needs an entry in SCREENS (and a phone check)`).toHaveProperty(id);
  });

  it("no screen's CSS turns its pane's scrolling off or lets it outgrow the window", () => {
    for (const id of Object.keys(SCREENS)) {
      for (const [f, sel, b] of allRules) {
        // The title (D64) has no slab: its menu floats, and the screen itself scrolls.
        if (id === "title") continue;
        const targetsPanel = sel.split(",").some((s) => new RegExp(`\\.ui-screen--${id}\\s*>\\s*\\.ui-panel$`).test(s.trim()));
        if (!targetsPanel) continue;
        expect(b, `${f}: ${sel}`).not.toMatch(/overflow(-y)?:\s*(hidden|visible|clip)/);
        expect(b, `${f}: ${sel}`).not.toMatch(/max-height:\s*none/);
        expect(b, `${f}: ${sel}`).not.toMatch(/\b100vh\b/); // a phone's browser bars make vh taller than the window
      }
    }
  });

  it("the title scrolls as a whole when its menu doesn't fit", () => {
    expect(body(".ui-screen--title")).toMatch(/overflow-y:\s*auto/);
    expect(body(".ui-screen--title")).toMatch(/minmax\(min-content,\s*1fr\)/);
  });

  it("phone panes that fill the window do so with percentages, not vh", () => {
    for (const { f, text } of css) {
      if (!/ui-screen--(shop|options|load|highscores)/.test(text)) continue;
      expect(text.replace(/\/\*[\s\S]*?\*\//g, ""), f).not.toMatch(/height:\s*100vh/);
    }
  });
});
