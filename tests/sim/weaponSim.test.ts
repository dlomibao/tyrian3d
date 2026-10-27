// The item screen's weapon simulator (src/sim/weaponSim.ts, a port of game_menu.c's
// JE_initWeaponView and JE_weaponSimUpdate): what it draws, and that the game after the item
// screen is exactly what it is without it.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { beforeEach, describe, expect, test } from "vitest";
import { starfield_restore, starfield_save } from "../../src/sim/backgrnd";
import { drawList, Pass, type DrawList, type SpriteDraw } from "../../src/sim/draw";
import {
  itemScreenEntries,
  JE_itemScreen_done,
  JE_itemScreen_init,
  JE_itemScreen_key,
  JE_itemScreen_update,
  MENU_UPGRADE_SUB,
  MENU_UPGRADES,
  menu,
  type ItemScreenKey,
} from "../../src/sim/game_menu";
import { loadHelpText } from "../../src/sim/helptext";
import { JE_initPlayerData } from "../../src/sim/mainint";
import { mt_restore, mt_save, mt_srand } from "../../src/sim/mtrand";
import { buildResources } from "../../src/sim/resources";
import { playerShotKey } from "../../src/sim/shots";
import { DIFFICULTY_NORMAL, g, newPlayerItems, type PlayerItems } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { weaponSim_active, weaponSim_frame, weaponSim_reset, weaponSim_sync, weaponSimPower } from "../../src/sim/weaponSim";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const HAVE = hasData("tyrian.hdt", "tyrian.shp", "levels1.dat", "tyrian1.lvl", "palette.dat", "newsh1.shp");

/** A fresh one-player game, as shop.test.ts sets one up. */
function freshGame(cash: number): void {
  mt_srand(1);
  if (!g.res || g.episodeNum !== 1) g.res = buildResources(files, 1);
  g.episodeNum = 1;
  loadHelpText(readData("tyrian.hdt"));
  g.player[0].items = newPlayerItems(); // JE_initPlayerData copies the old powers into last_items
  JE_initPlayerData();
  g.playDemo = false;
  g.jumpSection = false;
  g.onePlayerAction = false;
  g.twoPlayerMode = false;
  g.superTyrian = false;
  g.constantPlay = false;
  g.difficultyLevel = DIFFICULTY_NORMAL;
  g.initialDifficulty = DIFFICULTY_NORMAL;
  g.gameLoaded = true;
  g.player[0].cash = cash;
  g.upgradeCost = g.downgradeCost = 0;
  g.cubeMax = 0;
  g.mapPNum = 0;
  weaponSim_reset();
}

/** Everything the sim could leave behind: `g` (but its loaded data), mt_rand, the stars, shot keys and the draw list. */
function snapshot() {
  const { res: _res, lvl: _lvl, ...rest } = g;
  return structuredClone({ g: rest, rng: mt_save(), stars: starfield_save(), keys: [...playerShotKey], drawList: { ...drawList } });
}

function restore(s: ReturnType<typeof snapshot>): void {
  const c = structuredClone(s);
  Object.assign(g, c.g);
  mt_restore(c.rng);
  starfield_restore(c.stars);
  playerShotKey.splice(0, playerShotKey.length, ...c.keys);
  Object.assign(drawList, c.drawList);
}

/** Item screen input as shop.ts gives it: the key, the loop top, then the simulator's bookkeeping. */
function press(withPreview: boolean, frames: number, ...keys: ItemScreenKey[]): void {
  for (const k of keys) {
    JE_itemScreen_key(k);
    if (JE_itemScreen_done()) return;
    JE_itemScreen_update();
    itemScreenEntries();
    if (withPreview && weaponSim_sync()) for (let i = 0; i < frames; i++) weaponSim_frame();
  }
}

const shots = (list: DrawList) => list.items.filter((d): d is SpriteDraw => d.kind === "sprite2" && d.pass === Pass.PlayerShots);

describe.skipIf(!HAVE)("weapon simulator", () => {
  beforeEach(() => freshGame(10000));

  test("the Front Gun submenu shows the ship firing the selected gun", () => {
    loadLevel(files, 1, 2, () => {
      JE_itemScreen_init();
      JE_itemScreen_update();
      expect(weaponSim_sync()).toBe(false);
      press(true, 0, "down", "down", "enter", "down", "enter"); // Upgrade Ship, Front Gun
      expect(menu.curMenu).toBe(MENU_UPGRADE_SUB);
      expect(menu.curSel[MENU_UPGRADES]).toBe(3);
      expect(weaponSim_active()).toBe(true);
      expect(weaponSimPower()).toBe(500); // JE_initWeaponView

      const { items } = g.res;
      const p = g.player[0];
      const port = items.weaponPorts[p.items.weapon[0].id];
      const weapon = items.weapons[port.op[0][p.items.weapon[0].power - 1]];

      // shotRepeat starts at 1: the first frame only counts down, the second fires.
      let list = weaponSim_frame();
      expect(shots(list)).toHaveLength(0);
      expect(list.palette).toBe(0);
      expect(list.items[0]).toMatchObject({ kind: "rect", x1: 8, y1: 8, x2: 143, y2: 182, color: 0, pass: Pass.Background1 });
      expect(list.items.some((d) => d.kind === "pixel" && d.pass === Pass.Starfield)).toBe(true);
      // JE_drawItem(1, ship, x - 5, y - 7): the ship's picture at (67, 103), drawn last.
      expect(list.items.at(-1)).toMatchObject({ kind: "sprite2", size: 2, x: 67, y: 103, index: items.ships[p.items.ship].shipGraphic, pass: Pass.Player });
      expect(weaponSimPower()).toBe(500 + items.powerSys[p.items.generator].power);

      list = weaponSim_frame();
      const fired = shots(list);
      expect(fired.length).toBeGreaterThan(0);
      // player_shot_create puts the shot at (x + bx, y + by); simulate_player_shots moves it by
      // its speed and draws it one pixel right.
      const first = fired[0];
      const accel = -weapon.acceleration;
      expect(first.x).toBe(72 + weapon.bx[0] + weapon.sx[0] + weapon.accelerationX + 1);
      expect(first.y).toBe(110 + weapon.by[0] - weapon.sy[0] + accel);
      expect(first.key).toBeGreaterThanOrEqual(0);

      // The shot climbs on the next frames with the same key, so the renderer can interpolate it.
      list = weaponSim_frame();
      const again = shots(list).find((d) => d.key === first.key);
      expect(again).toBeDefined();
      expect(again!.y).toBeLessThan(first.y);

      // The game's own globals are untouched while the preview runs.
      expect(g.player[0].x).not.toBe(72);
      press(true, 0, "esc", "esc", "down", "down", "enter", "enter");
    });
  });

  test("the generator and sidekick submenus run it too, the ship and shield ones don't (as the C)", () => {
    loadLevel(files, 1, 2, () => {
      JE_itemScreen_init();
      JE_itemScreen_update();
      weaponSim_sync();
      press(true, 0, "down", "down", "enter");
      const runs: boolean[] = [];
      for (let sel = 2; sel <= 8; sel++) {
        press(true, 0, "enter");
        runs.push(weaponSim_active());
        press(true, 0, "esc", "down");
      }
      expect(runs).toEqual([false, true, true, false, true, true, true]);
      press(true, 0, "esc", "down", "down", "enter", "enter");
    });
  });

  test("a sidekick fires from its own place", () => {
    const { items } = g.res;
    const sidekick = items.options.findIndex((o, i) => i > 0 && o.wPort > 0 && o.tr !== 2);
    expect(sidekick).toBeGreaterThan(0);
    g.player[0].items.sidekick[0] = sidekick;
    g.player[0].items.weapon[0].id = 0; // no front gun, so every shot is the sidekick's
    g.player[0].last_items = structuredClone(g.player[0].items) as PlayerItems;
    loadLevel(files, 1, 2, () => {
      JE_itemScreen_init();
      JE_itemScreen_update();
      weaponSim_sync();
      press(true, 0, "down", "down", "enter", "down", "down", "down", "down", "down", "enter"); // Left Sidekick
      expect(menu.curSel[MENU_UPGRADES]).toBe(7);
      const all: SpriteDraw[] = [];
      for (let i = 0; i < 40; i++) all.push(...shots(weaponSim_frame()));
      expect(all.length).toBeGreaterThan(0);
      // Sidekick shots start from (72 - 15, 120) rather than the ship's (72, 110).
      const firstX = all[0].x - 1;
      const weapon = items.weapons[items.options[sidekick].wpNum];
      expect(firstX - (weapon.sx[0] + weapon.accelerationX)).toBe(57 + weapon.bx[0]);
      press(true, 0, "esc", "esc", "down", "down", "enter", "enter");
    });
  });

  test("the game after the item screen is exactly the same with the preview running", () => {
    // The scripted sessions of the C cross-check (shop.test.ts): buying, trading in, firing modes.
    const script = readFileSync(join(__dirname, "fixtures", "shop-trace.script"), "utf8");
    const fields: Record<string, (it: PlayerItems, v: number) => void> = {
      front: (it, v) => (it.weapon[0].id = v),
      fpow: (it, v) => (it.weapon[0].power = v),
      rear: (it, v) => (it.weapon[1].id = v),
    };
    let sessions = 0;
    let previewFrames = 0;
    for (const line of script.split("\n")) {
      if (!line || line.startsWith("#")) continue;
      const [section, cash, ...rest] = line.split(" ");
      const starts: unknown[] = [];
      freshGame(Number(cash));
      const start = snapshot();
      let atExit: unknown;
      const run = (withPreview: boolean) => {
        restore(start);
        weaponSim_reset();
        const keys: ItemScreenKey[] = [];
        for (const tok of rest) {
          const eq = tok.indexOf("=");
          if (eq < 0) keys.push(tok as ItemScreenKey);
          else for (const it of [g.player[0].items, g.player[0].last_items]) fields[tok.slice(0, eq)](it, Number(tok.slice(eq + 1)));
        }
        starts.push(snapshot());
        loadLevel(files, 1, Number(section), () => {
          JE_itemScreen_init();
          JE_itemScreen_update();
          itemScreenEntries();
          if (withPreview) weaponSim_sync();
          for (const k of keys) {
            if (JE_itemScreen_done()) break;
            press(withPreview, 37, k);
            if (withPreview && weaponSim_active()) previewFrames += 37;
          }
          atExit = snapshot(); // as JE_itemScreen returns
        });
        return [atExit, snapshot()];
      };
      const without = run(false);
      const withIt = run(true);
      expect(starts[1]).toEqual(starts[0]);
      expect(withIt).toEqual(without);
      sessions++;
    }
    expect(sessions).toBeGreaterThan(3);
    expect(previewFrames).toBeGreaterThan(500);
  });
});
