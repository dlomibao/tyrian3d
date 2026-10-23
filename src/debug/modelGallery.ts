// Model review bench: `?debug=models` on the dev server shows the Blender models that replace
// sprites (src/render/spriteModels/) in the game's own renderer, each beside its original sprite,
// cycling through the animation frames it covers. Loaded by dynamic import, so it's not in the main
// bundle.
//
//   &page=P          page P (0-based) of 12 models
//   &model=a,b       only these models (names as in spriteModels/, e.g. newshf-1)
//   &flash=1         flash every model with the enemy hit filter every other second
//   &palette=N       palette N (default 5, the in-level palette)

import { loadDevFiles } from "../assets/files";
import { startLoop } from "../core/loop";
import { CLASSIC_TICK_MS } from "../core/timing";
import { beginDrawList, blit_sprite2, blit_sprite2_filter, blit_sprite2x2, drawGroup, drawList, drawState, Pass, type Sprite2Sheet } from "../sim/draw";
import { buildResources } from "../sim/resources";
import type { Resources } from "../sim/state";
import { SPRITE_MODELS, type SpriteModelEntry } from "../render/spriteModels";
import type { View } from "../render/view";

const PER_PAGE = 12;
const COLS = 4;
/** The original's playfield: x 24..288, y 0..184 on the 320x200 screen. */
const LEFT = 24;
const CELL_W = 66;
const CELL_H = 61;

export async function runModelGallery(view: View): Promise<void> {
  const params = new URLSearchParams(location.search);
  const overlay = document.createElement("div");
  Object.assign(overlay.style, {
    position: "fixed", left: "8px", top: "8px", font: "12px/1.4 ui-monospace, monospace", color: "#cfe3ff",
    background: "rgba(0,0,0,0.55)", padding: "4px 8px", borderRadius: "4px", pointerEvents: "none", whiteSpace: "pre",
  });
  document.body.append(overlay);
  const files = await loadDevFiles();
  if (!files) {
    overlay.textContent = "?debug=models needs the dev server with TYRIAN_DATA pointing at the Tyrian 2.1 data.";
    return;
  }
  const res = buildResources(files);
  view.setPalettes(res.palettes);

  const only = params.get("model")?.split(",");
  const all = [...SPRITE_MODELS].sort((a, b) => a.model.localeCompare(b.model));
  const chosen = only ? all.filter((e) => only.some((n) => e.model.endsWith(`/${n}`) || e.model === n)) : all;
  const page = Number(params.get("page") ?? 0);
  const shown = chosen.slice(page * PER_PAGE, (page + 1) * PER_PAGE);
  const flash = params.get("flash") === "1";
  const palette = Number(params.get("palette") ?? 5);
  overlay.textContent =
    `models ${page * PER_PAGE + 1}-${page * PER_PAGE + shown.length} of ${chosen.length} (sprite left, model right)\n` +
    shown.map((e, i) => `${i + 1}. ${e.model}`).join("\n");

  let tick = 0;
  startLoop(CLASSIC_TICK_MS, {
    update: () => {
      beginDrawList();
      drawState.pass = Pass.SkyEnemies;
      const filter = flash && Math.floor(tick / 35) % 2 === 1 ? 0x70 : 0;
      shown.forEach((entry, i) => drawEntry(res, entry, i, tick, filter));
      drawList.palette = palette;
      tick++;
      view.setDrawList(drawList);
    },
    render: (alpha) => view.render(null, alpha),
  });
  Object.assign(window, { tyrianModels: { view, shown } });
}

function sheetById(res: Resources, id: string): Sprite2Sheet | null {
  const m = /^newsh(.)\.shp$/.exec(id);
  if (m) return res.loadCompShapes(m[1]);
  const sheets = [res.spriteSheet8, res.spriteSheet9, res.spriteSheet10, res.spriteSheet11, res.spriteSheet12];
  return sheets.find((s) => s.id === id) ?? null;
}

/** Blit one object the way blit_enemy does: 1 tile, or the 2x2 block index, +1, +19, +20. */
function blitObject(sheet: Sprite2Sheet, size: 1 | 2, index: number, x: number, y: number, grouped: boolean, key: number, filter: number) {
  const tiles = size === 1 ? [[0, 0, 0]] : [[0, 0, 0], [1, 12, 0], [19, 0, 14], [20, 12, 14]];
  tiles.forEach(([offset, ox, oy], part) => {
    if (grouped) {
      drawGroup.index = index;
      drawGroup.size = size;
      drawGroup.dx = size * 6 - ox;
      drawGroup.dy = size * 7 - oy;
      drawGroup.first = part === 0;
    }
    drawState.key = key + part;
    if (filter) blit_sprite2_filter(x + ox, y + oy, sheet, index + offset, filter);
    else blit_sprite2(x + ox, y + oy, sheet, index + offset);
  });
  drawGroup.index = -1;
  drawState.key = -1;
}

function drawEntry(res: Resources, entry: SpriteModelEntry, slot: number, tick: number, filter: number) {
  const cx = LEFT + (slot % COLS) * CELL_W;
  const cy = 4 + Math.floor(slot / COLS) * CELL_H;
  const frames = entry.sprites.flatMap((s) => s.frames.map((f) => ({ ref: s, frame: f })));
  const { ref, frame } = frames[Math.floor(tick / 8) % frames.length];
  const sheet = sheetById(res, ref.sheet);
  if (!sheet) return;
  if (ref.bank) {
    // A player ship (blit_sprite2x2, as JE_playerMovement draws it): the renderer replaces every
    // banking frame, so show the model banking.
    const bank = Math.round(Math.sin(tick / 20) * ref.bank.max);
    drawState.key = 100 + slot * 8;
    blit_sprite2x2(cx + 21, cy + 10, sheet, frame + bank * ref.bank.step);
    drawState.key = -1;
    return;
  }
  const y = cy + 10 + Math.round(Math.sin(tick / 25 + slot) * 3);
  blitObject(sheet, ref.size, frame, cx + 4, y, false, 100 + slot * 8, filter);
  blitObject(sheet, ref.size, frame, cx + 36, y, true, 104 + slot * 8, filter);
}
