// A real level, played by the test bot, for looking at weapons and effects. Open the dev server
// with `?debug=play`. Loaded by dynamic import, so it's not in the main bundle.
//
//   ?debug=play                    episode 1's first level, Pulse-Cannon, the bot firing and sweeping
//   &episode=E&main=N              the episode and episode-script level (mainLevel) to play
//   &front=ID&power=P&rear=ID      weapon ports (item numbers, as in the item screen's lists)
//   &left=ID&right=ID              sidekicks (options)
//   &cycle=S                       change the front weapon every S seconds (through a few favourites)
//   &seed=N                        the random seed, so two runs play the same (default 1)
//   &skip=T                        fast-forward T ticks before showing anything
//   &freezeAt=T                    stop the game (and the effects' clock) at tick T, for screenshots
//   &vfx=original|remastered       the shot and explosion look (D35)
//   &stress=N                      add N extra copies of the tick's shots (bullet-hell load test)
//
// Keys: V switches the effects look, N the next front weapon, P (or Space) pauses.
// The bot is the one the episode tests use: invulnerable, always firing, sweeping left and right.

import { startLoop } from "../core/loop";
import { CLASSIC_TICK_MS } from "../core/timing";
import { loadDevFiles } from "../assets/files";
import { drawList, Pass, type Draw } from "../sim/draw";
import { startLevel, tick } from "../sim/game";
import { loadHelpText } from "../sim/helptext";
import { clearSimInput, simInput } from "../sim/input";
import { mt_srand } from "../sim/mtrand";
import { newOnePlayerGame } from "../sim/newgame";
import { buildResources, requireFile } from "../sim/resources";
import { g } from "../sim/state";
import { loadLevel } from "../sim/tyrian2";
import { JE_drawOptions } from "../sim/varz";
import type { View } from "../render/view";

/** Front weapons the cycle goes through: Pulse, Multi, Laser, Zica, Vulcan, Lightning, Starburst, Sonic, Protron, Missiles, Mega Pulse, Hyper Pulse. */
const FAVOURITES = [1, 2, 4, 5, 7, 8, 9, 11, 12, 17, 19, 27];

export async function runPlayHarness(view: View): Promise<void> {
  const params = new URLSearchParams(location.search);
  const num = (key: string, fallback: number) => (params.has(key) && Number.isFinite(Number(params.get(key))) ? Number(params.get(key)) : fallback);
  const overlay = makeOverlay();
  const files = await loadDevFiles();
  if (!files) {
    overlay.textContent = "?debug=play needs the dev server with TYRIAN_DATA pointing at the Tyrian 2.1 data.";
    return;
  }
  const episode = num("episode", 1);
  mt_srand(num("seed", 1));
  g.res = buildResources(files, episode);
  loadHelpText(requireFile(files, "tyrian.hdt"));
  view.setPalettes(g.res.palettes);
  newOnePlayerGame(episode);
  loadLevel(files, episode, num("main", g.mainLevel));

  const p = g.player[0];
  let favourite = Math.max(0, FAVOURITES.indexOf(num("front", 1)));
  p.items.weapon[0] = { id: num("front", 1), power: num("power", 5) };
  p.items.weapon[1] = { id: num("rear", 0), power: num("power", 5) };
  p.items.sidekick[0] = num("left", 0);
  p.items.sidekick[1] = num("right", 0);
  startLevel();
  JE_drawOptions();
  clearSimInput();

  let t = 0;
  let paused = false;
  const stress = num("stress", 0);
  const freezeAt = num("freezeAt", -1);
  const cycleTicks = num("cycle", 0) * (1000 / CLASSIC_TICK_MS);
  const step = (show: boolean) => {
    // tests/sim/bot.ts: invulnerable, always firing, sweeping.
    p.invulnerable_ticks = 2;
    p.armor = Math.max(p.armor, 10);
    simInput.fire = true;
    simInput.left = Math.floor(t / 50) % 2 === 0;
    simInput.right = !simInput.left;
    if (cycleTicks > 0 && t > 0 && t % Math.round(cycleTicks) === 0) nextWeapon();
    const r = tick();
    t++;
    if (r.levelOver || r.gameOver) {
      loadLevel(files, episode, g.nextLevel > 0 && r.completed ? g.nextLevel : g.mainLevel);
      startLevel();
      view.draws.resetInterpolation();
    }
    if (stress > 0) addStressShots(drawList.items, stress, t);
    if (show) view.setDrawList(drawList);
  };
  const nextWeapon = () => {
    favourite = (favourite + 1) % FAVOURITES.length;
    p.items.weapon[0].id = FAVOURITES[favourite];
  };
  for (let i = num("skip", 0); i > 0; i--) step(i <= 2);

  window.addEventListener("keydown", (e) => {
    if (e.code === "KeyV") view.draws.setVfxMode(view.draws.vfxMode === "remastered" ? "original" : "remastered");
    else if (e.code === "KeyN") nextWeapon();
    else if (e.code === "KeyP" || e.code === "Space") paused = !paused;
    else return;
    e.preventDefault();
  });

  const frameTimes: number[] = [];
  let frames = 0;
  let lastReport = performance.now();
  view.renderer.info.autoReset = false;
  startLoop(CLASSIC_TICK_MS, {
    update: () => {
      if (paused || t === freezeAt) return;
      step(true);
    },
    render: (alpha) => {
      const frozen = paused || t === freezeAt;
      view.draws.vfxTimeScale = frozen ? 0 : 1;
      const t0 = performance.now();
      view.renderer.info.reset();
      view.render(null, frozen ? 1 : alpha);
      frameTimes.push(performance.now() - t0);
      frames++;
      const now = performance.now();
      if (now - lastReport > 500) {
        const s = view.draws.stats();
        const fx = view.draws.vfxStats();
        const avg = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
        const max = Math.max(...frameTimes);
        const info = view.renderer.info.render;
        const shots = g.shotAvail.filter((s) => s !== 0).length;
        const name = g.res.items.weaponPorts[p.items.weapon[0].id]?.name.trim();
        overlay.textContent =
          `${view.draws.vfxMode} (V) · ${name} (N) · tick ${t}${frozen ? " (paused)" : ""} · ` +
          `${((frames * 1000) / (now - lastReport)).toFixed(0)} fps · cpu ${avg.toFixed(2)} ms (max ${max.toFixed(1)}) · ` +
          `${s.items} draws · ${shots} shots · ${fx.particles} particles · ${info.calls} calls`;
        frameTimes.length = 0;
        frames = 0;
        lastReport = now;
      }
    },
  });
  Object.assign(window, { tyrianHarness: { view, g, step, nextWeapon, pause: (v = true) => (paused = v) } });
}

function makeOverlay(): HTMLDivElement {
  const div = document.createElement("div");
  Object.assign(div.style, {
    position: "fixed",
    left: "8px",
    top: "8px",
    font: "12px/1.4 ui-monospace, monospace",
    color: "#cfe3ff",
    background: "rgba(0,0,0,0.55)",
    padding: "4px 8px",
    borderRadius: "4px",
    pointerEvents: "none",
    maxWidth: "calc(100vw - 32px)",
    zIndex: "10",
  });
  div.textContent = "loading Tyrian data…";
  document.body.appendChild(div);
  return div;
}

/**
 * Append `n` copies of this tick's shots (player and enemy), spread over the screen and drifting,
 * with keys of their own so they interpolate and trail like real shots. Presentation only.
 */
function addStressShots(items: Draw[], n: number, t: number): void {
  const templates = items.filter((d) => d.kind === "sprite2" && (d.pass === Pass.PlayerShots || d.pass === Pass.EnemyShots) && d.effect !== "darken");
  if (templates.length === 0) return;
  for (let i = 0; i < n; i++) {
    const d = templates[i % templates.length];
    if (d.kind !== "sprite2") continue;
    const speed = 2 + (i % 7);
    const up = i % 2 === 0;
    const y = ((i * 53 + t * speed) % 200) - 10;
    items.push({ ...d, key: 900000 + i, x: 24 + ((i * 37 + Math.floor(i / 7) * 11) % 250), y: up ? 190 - y : y, pass: up ? Pass.PlayerShots : Pass.EnemyShots });
  }
}
