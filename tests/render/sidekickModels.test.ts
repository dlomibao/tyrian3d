// Sprites drawn on their own (the player's sidekicks) as models (spriteModels.ts `ungrouped`,
// DECISIONS.md D49): with no entry, or the model still loading, they draw exactly as before.
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { screenWorldX } from "../../src/game/playfield";
import { DrawListRenderer } from "../../src/render/drawListRenderer";
import { spriteModelKey, spriteModels, type SpriteModelEntry } from "../../src/render/spriteModels";
import { Pass, type DrawList, type Sprite2Sheet, type SpriteDraw } from "../../src/sim/draw";
import type { Palette } from "../../src/data/palette";

vi.stubGlobal("location", { search: "" });

/** A Sprite2 sheet of `n` sprites, each one opaque pixel of colour 5 (OpenTyrian's RLE). */
function sheet(id: string, n: number): Sprite2Sheet {
  const sprites = Array.from({ length: n }, () => [0x10, 5, 0x0f]);
  const bytes: number[] = [];
  let p = n * 2;
  for (const data of sprites) {
    bytes.push(p & 0xff, p >> 8);
    p += data.length;
  }
  return { id, data: Uint8Array.from([...bytes, ...sprites.flat()]) };
}

function draw(sh: Sprite2Sheet, index: number, over: Partial<SpriteDraw> = {}): SpriteDraw {
  return {
    kind: "sprite2", sheet: sh, index, x: 100, y: 50, size: 1, pass: Pass.Player, key: 7, effect: "none", filter: 0, value: 0,
    groupIndex: -1, groupSize: 1, groupDx: 0, groupDy: 0, groupFirst: false, ...over,
  };
}

const palette: Palette = new Uint8Array(768) as unknown as Palette;
const SHEET = "tyrian.shp#8";
const ENTRY: SpriteModelEntry = { model: "sidekicks/test", sprites: [{ sheet: SHEET, size: 1, frames: [3], ungrouped: true }] };

function make(entries: SpriteModelEntry[], loaded: boolean) {
  const r = new DrawListRenderer();
  r.setVfxMode("original");
  r.setPalettes([palette]);
  const model = new THREE.Group();
  model.add(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial()));
  r.setSpriteModels(spriteModels(entries), () => (loaded ? Promise.resolve(model) : new Promise(() => {})));
  return r;
}

async function render(r: DrawListRenderer, items: SpriteDraw[]) {
  const list: DrawList = { items, palette: 0, filter: -99, brightness: 0, screen: null };
  r.setDrawList(list);
  r.setDrawList(list);
  const camera = new THREE.PerspectiveCamera();
  camera.position.set(0, 30, 10);
  r.update(1, camera); // asks for the model
  await Promise.resolve();
  await Promise.resolve();
  r.update(1, camera);
  const models = r.root.children.filter((o) => o.visible && o.children.some((c) => (c as THREE.Mesh).isMesh && !(c as THREE.InstancedMesh).isInstancedMesh));
  return { ...r.stats(), models };
}

describe("spriteModels(): ungrouped entries", () => {
  test("are indexed apart from enemies' grouped frames, and still claim their frames", () => {
    const m = spriteModels([ENTRY]);
    expect(m.ungrouped.get(spriteModelKey(SHEET, 1, 3))).toBe("sidekicks/test");
    expect(m.grouped.size).toBe(0);
    expect(() => spriteModels([ENTRY, { model: "enemy", sprites: [{ sheet: SHEET, size: 1, frames: [3] }] }])).toThrow(/both replace/);
  });
});

describe("renderer: a sidekick's sprite as its model", () => {
  test("no entry: drawn as a sprite, as before", async () => {
    const sh = sheet(SHEET, 4);
    const s = await render(make([], true), [draw(sh, 3)]);
    expect(s).toMatchObject({ instances: 1, visiblePools: 1 });
    expect(s.models).toHaveLength(0);
  });

  test("model still loading: drawn as a sprite", async () => {
    const sh = sheet(SHEET, 4);
    const s = await render(make([ENTRY], false), [draw(sh, 3)]);
    expect(s).toMatchObject({ instances: 1, visiblePools: 1 });
  });

  test("loaded: the model replaces the draw, centred on the sprite; other frames and grouped draws stay sprites", async () => {
    const sh = sheet(SHEET, 4);
    const s = await render(make([ENTRY], true), [draw(sh, 3), draw(sh, 2), draw(sh, 3, { groupIndex: 3, groupFirst: true })]);
    expect(s.models).toHaveLength(1);
    expect(s.instances).toBe(2); // frame 2, and the grouped draw of 3 (no grouped model)
    // Centred on the 12x14 sprite at (100, 50): x 106 (raised toward the camera, so not exactly).
    expect(Math.abs(s.models[0].position.x - screenWorldX(106))).toBeLessThan(Math.abs(screenWorldX(100) - screenWorldX(106)));
  });

  test("a 2x2 draw needs a size-2 entry", async () => {
    const sh = sheet("tyrian.shp#9", 30);
    const big: SpriteModelEntry = { model: "sidekicks/big", sprites: [{ sheet: "tyrian.shp#9", size: 2, frames: [3], ungrouped: true }] };
    expect((await render(make([big], true), [draw(sh, 3, { size: 2 })])).models).toHaveLength(1);
    expect((await render(make([big], true), [draw(sh, 3)])).models).toHaveLength(0);
  });
});
