// The shop icons' model renders (DECISIONS.md D226): `?debug=shopicons` draws each shop picture that
// the game draws as a 3D model (a player ship: blit_sprite2x2 of its shipGraphic, as the item screen's
// simulator draws it) alone on a transparent canvas, through the game's own renderer: the model, its
// palette materials in the item screen's palette, the game's lights and ink outline, the Overhead
// camera (the sprite's view, so the outline lines up), framed as in a level with the ship at the
// aim point. tools/shop_icons.py `models` captures it (tools/cdpshot.mjs) and cuts each render back
// onto its original silhouette.
//
//   &keys=a,b        shop pictures as "<sheet id>:<first sprite>" (D210's manifest keys; # as %23).
//                    Default: every player ship model's level frame.
//   &px=N            canvas pixels per game pixel (default 12)
//   &margin=N        game pixels kept round the 24x28 picture in each crop (default 6)
//   &palette=N       palette (default 0, the item screen's: JE_loadPic 1)
//
// window.tyrianShopIcons.ready resolves to { px, margin, cell: [w, h], icons: { key: { x, y, bareY, model } },
// missing: [keys with no model], png: data URL of every crop side by side, in `icons` order }. The
// second row (bareY) is the same render without the ink outline, for the model's own fit (D74's rule).

import type * as THREE from "three";
import { loadDevFiles } from "../assets/files";
import { loadSettings } from "../core/settings";
import { beginDrawList, blit_sprite2x2, drawList, drawState, Pass, type Sprite2Sheet } from "../sim/draw";
import { buildResources } from "../sim/resources";
import type { Resources } from "../sim/state";
import { loadModel } from "../render/models";
import { spriteModels } from "../render/spriteModels";
import { Sprite2Router } from "../render/sprite2Route";
import { CAMERA_TILT_OVERHEAD, View } from "../render/view";

/** The original's playfield on the 320x200 screen: x 24..288, y 0..184 (the view frames it). */
const FIELD = { x: 24, y: 0, w: 264, h: 184 };
/** The picture: JE_drawItem's 24x28 block. */
const ICON_W = 24;
const ICON_H = 28;

export interface ShopIconRenders {
  px: number;
  margin: number;
  cell: [number, number];
  icons: Record<string, { x: number; y: number; bareY: number; model: string }>;
  missing: string[];
  png: string;
}

function sheetById(res: Resources, id: string): Sprite2Sheet | null {
  const m = /^newsh(.)\.shp$/.exec(id);
  if (m) return res.loadCompShapes(m[1]);
  return [res.spriteSheet8, res.spriteSheet9, res.spriteSheet10, res.spriteSheet11, res.spriteSheet12].find((s) => s.id === id) ?? null;
}

export async function runShopIconsHarness(mainView: View): Promise<void> {
  const params = new URLSearchParams(location.search);
  const num = (k: string, d: number) => (params.has(k) && Number.isFinite(Number(params.get(k))) ? Number(params.get(k)) : d);
  const px = num("px", 12);
  const margin = num("margin", 6);
  const palette = num("palette", 0);
  mainView.renderer.domElement.style.display = "none";
  const status = document.createElement("pre");
  Object.assign(status.style, { position: "fixed", left: "8px", top: "8px", margin: "0", color: "#cfe3ff", font: "12px ui-monospace, monospace", zIndex: "2" });
  document.body.append(status);

  const ready = (async (): Promise<ShopIconRenders> => {
    const files = await loadDevFiles();
    if (!files) throw new Error("?debug=shopicons needs the dev server with TYRIAN_DATA pointing at the Tyrian 2.1 data");
    const res = buildResources(files);
    const models = spriteModels();
    const router = new Sprite2Router(models);
    const keys = params.get("keys")?.split(",").filter(Boolean) ?? models.banked.map((o) => `${o.sheetId}:${o.baseIndex}`);

    // Which pictures the game draws as models: the shop picture is blit_sprite2x2(sheet, index) on
    // its own, as the simulator draws the ship (weaponSim.ts JE_drawItem1), so the model is the one
    // the renderer gives that draw.
    const todo: { key: string; sheet: Sprite2Sheet; index: number; model: string }[] = [];
    const missing: string[] = [];
    for (const key of keys) {
      const at = key.lastIndexOf(":");
      const sheet = sheetById(res, key.slice(0, at));
      const index = Number(key.slice(at + 1));
      const model = sheet && Number.isInteger(index) ? router.modelFor(sheet.id, 2, index, false) : undefined;
      if (sheet && model !== undefined) todo.push({ key, sheet, index, model });
      else missing.push(key);
    }

    // The view: transparent, the playfield framed as in a level (the same perspective), straight down.
    const host = document.createElement("div");
    Object.assign(host.style, { position: "absolute", left: "0", top: "0", width: `${FIELD.w * px}px`, height: `${FIELD.h * px}px` });
    document.body.append(host);
    const view = new View(host, { ...loadSettings(), clip: false, maxPixelRatio: 1 }, { fitContainer: true, transparent: true });
    view.setTilt(CAMERA_TILT_OVERHEAD);
    view.setPalettes(res.palettes);
    view.draws.setSpriteModels(models, loadModel);
    status.textContent = `loading ${todo.length} models`;
    await view.draws.preloadLevel({ sprites: todo.map((t) => ({ sheet: t.sheet.id, size: 2 as const, index: t.index, grouped: false, time: 0 })) });

    const cw = (ICON_W + 2 * margin) * px;
    const ch = (ICON_H + 2 * margin) * px;
    const out = document.createElement("canvas");
    out.width = Math.max(1, todo.length) * cw;
    out.height = 2 * ch;
    const ctx = out.getContext("2d");
    if (!ctx) throw new Error("no 2D canvas");
    const canvas = view.renderer.domElement;
    const icons: ShopIconRenders["icons"] = {};
    // The picture's top left on the screen: centred on the playfield, where the camera aims.
    const sx = FIELD.x + (FIELD.w - ICON_W) / 2;
    const sy = FIELD.y + (FIELD.h - ICON_H) / 2;
    /** The outline shells' outline on or off (modelPrep.ts: the shell carries the model's ink). */
    const ink = (visible: boolean) =>
      view.draws.root.traverse((o) => {
        const m = (o as THREE.Mesh).material;
        for (const mat of Array.isArray(m) ? m : m ? [m] : []) {
          if (mat.userData.outlineShell) mat.userData.outlineParameters = { ...mat.userData.outlineParameters, visible };
        }
      });
    todo.forEach((t, i) => {
      status.textContent = `rendering ${t.key} (${t.model})`;
      view.draws.resetInterpolation();
      for (const [row, withInk] of [[0, true], [1, false]] as const) {
        for (let n = 0; n < 3; n++) {
          beginDrawList();
          drawState.pass = Pass.Player;
          drawState.key = 1;
          blit_sprite2x2(sx, sy, t.sheet, t.index);
          drawState.key = -1;
          drawList.palette = palette;
          view.setDrawList(drawList);
          ink(withInk);
          view.render(null, 1);
        }
        // Game pixels to canvas pixels: the playfield's ground corners on screen (overhead: a rectangle).
        const [c0, c1, , c3] = view.playfieldCorners();
        const k = canvas.width / host.clientWidth;
        const gx = (x: number) => (c0.x + ((x - FIELD.x) / FIELD.w) * (c1.x - c0.x)) * k;
        const gy = (y: number) => (c0.y + ((y - FIELD.y) / FIELD.h) * (c3.y - c0.y)) * k;
        const x0 = gx(sx - margin);
        const y0 = gy(sy - margin);
        // Read back in the same task as the render (the drawing buffer isn't preserved).
        ctx.drawImage(canvas, x0, y0, gx(sx + ICON_W + margin) - x0, gy(sy + ICON_H + margin) - y0, i * cw, row * ch, cw, ch);
      }
      ink(true);
      icons[t.key] = { x: i * cw, y: 0, bareY: ch, model: t.model };
    });
    host.remove();
    view.renderer.dispose();
    status.textContent = `done: ${todo.length} rendered, ${missing.length} without a model`;
    return { px, margin, cell: [cw, ch], icons, missing, png: out.toDataURL("image/png") };
  })();
  ready.catch((err) => {
    status.textContent = String(err);
    console.error(err);
  });
  Object.assign(window, { tyrianShopIcons: { ready } });
}
