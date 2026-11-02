// Enemies never pop from sprite to model when a model loads late (DECISIONS.md D54): each object is
// drawn one way for its life, and preloadLevel loads a level's models earliest-needed first.
// The loader here is a delayed fetch the test settles by hand.
import * as THREE from "three";
import { afterEach, describe, expect, test, vi } from "vitest";
import { DrawListRenderer, HOLD_MS } from "../../src/render/drawListRenderer";
import { spriteModels, type SpriteModelEntry } from "../../src/render/spriteModels";
import { ENEMY_KEY_BASE, Pass, type DrawList, type Sprite2Sheet, type SpriteDraw } from "../../src/sim/draw";
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

const SHEET = sheet("newsh9.shp", 60);
const ENEMY: SpriteModelEntry = { model: "enemies/test", sprites: [{ sheet: SHEET.id, size: 2, frames: [3] }] };
const OTHER: SpriteModelEntry = { model: "enemies/other", sprites: [{ sheet: SHEET.id, size: 2, frames: [5] }] };

/** An enemy's four quarters (blit_enemy), serial `serial`, frame `frame`. */
function enemy(serial: number, frame = 3, x = 100): SpriteDraw[] {
  return [0, 1, 19, 20].map((di, part) => ({
    kind: "sprite2", sheet: SHEET, index: frame + di, x: x + (di % 19) * 12, y: 50 + (di >= 19 ? 14 : 0), size: 1, pass: Pass.SkyEnemies,
    key: ENEMY_KEY_BASE + serial * 4 + part, effect: "none", filter: 0, value: 0,
    groupIndex: frame, groupSize: 2, groupDx: 12 - (di % 19) * 12, groupDy: 14 - (di >= 19 ? 14 : 0), groupFirst: part === 0,
  }));
}

/** A loader whose loads the test settles: resolve(name) or reject(name). */
function delayedLoader() {
  const pending = new Map<string, { resolve: (o: THREE.Object3D) => void; reject: (e: Error) => void }>();
  const order: string[] = [];
  let inFlight = 0;
  let maxInFlight = 0;
  const loader = (name: string) => {
    order.push(name);
    inFlight++;
    maxInFlight = Math.max(maxInFlight, inFlight);
    return new Promise<THREE.Object3D>((resolve, reject) => pending.set(name, { resolve, reject })).finally(() => inFlight--);
  };
  const model = () => {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial()));
    return g;
  };
  return {
    loader,
    order,
    maxInFlight: () => maxInFlight,
    async resolve(name: string) {
      pending.get(name)!.resolve(model());
      await flush();
    },
    async reject(name: string) {
      pending.get(name)!.reject(new Error("offline"));
      await flush();
    },
  };
}

const flush = async () => {
  for (let i = 0; i < 10; i++) await Promise.resolve();
};

const palette: Palette = new Uint8Array(768) as unknown as Palette;
let clock = 1000;
const now = vi.spyOn(performance, "now").mockImplementation(() => clock);
afterEach(() => void (clock = 1000));
void now;

function make(entries: SpriteModelEntry[], loader: (name: string) => Promise<THREE.Object3D>) {
  const r = new DrawListRenderer();
  r.setVfxMode("original");
  r.setPalettes([palette]);
  r.setSpriteModels(spriteModels(entries), loader);
  return r;
}

/** Draw one frame of `items` (as one tick), `ms` after the last; what's on screen. */
function frame(r: DrawListRenderer, items: SpriteDraw[], ms = 16) {
  clock += ms;
  const list: DrawList = { items, palette: 0, filter: -99, brightness: 0, screen: null };
  r.setDrawList(list);
  const camera = new THREE.PerspectiveCamera();
  camera.position.set(0, 30, 10);
  r.update(1, camera);
  const models = r.root.children.filter((o) => o.visible && o.children.some((c) => (c as THREE.Mesh).isMesh && !(c as THREE.InstancedMesh).isInstancedMesh));
  return { sprites: r.stats().instances, models: models.length };
}

describe("an enemy whose model is still loading (D54)", () => {
  test("model loaded before it appears: drawn as the model from its first frame", async () => {
    const l = delayedLoader();
    const r = make([ENEMY], l.loader);
    const p = r.preloadLevel({ sprites: [{ sheet: SHEET.id, size: 2, index: 3, grouped: true, time: 0 }] });
    await l.resolve("enemies/test");
    expect(await p).toMatchObject({ total: 2, done: 2, models: 1, timedOut: false });
    expect(frame(r, enemy(1))).toEqual({ sprites: 0, models: 1 });
  });

  test("model arrives within HOLD_MS: held back (nothing drawn), then the model; never the sprite", async () => {
    const l = delayedLoader();
    const r = make([ENEMY], l.loader);
    const seen: { sprites: number; models: number }[] = [];
    for (let i = 0; i < 5; i++) seen.push(frame(r, enemy(1), 30));
    await l.resolve("enemies/test");
    for (let i = 0; i < 5; i++) seen.push(frame(r, enemy(1), 30));
    expect(seen.every((s) => s.sprites === 0)).toBe(true);
    expect(seen.slice(0, 5).every((s) => s.models === 0)).toBe(true);
    expect(seen.slice(5).every((s) => s.models === 1)).toBe(true);
  });

  test("model later than HOLD_MS: the sprite for the enemy's whole life, even once the model is in; the next enemy gets the model", async () => {
    const l = delayedLoader();
    const r = make([ENEMY], l.loader);
    expect(frame(r, enemy(1))).toEqual({ sprites: 0, models: 0 });
    expect(frame(r, enemy(1), HOLD_MS + 1)).toEqual({ sprites: 4, models: 0 });
    await l.resolve("enemies/test");
    for (let i = 0; i < 10; i++) expect(frame(r, enemy(1))).toEqual({ sprites: 4, models: 0 });
    // A new enemy (another serial) alongside: its model, while the first stays a sprite.
    expect(frame(r, [...enemy(1), ...enemy(2, 3, 160)])).toEqual({ sprites: 4, models: 1 });
  });

  test("a model that fails to load: the sprite, at once", async () => {
    const l = delayedLoader();
    const r = make([ENEMY], l.loader);
    frame(r, enemy(1));
    await l.reject("enemies/test");
    expect(frame(r, enemy(1))).toEqual({ sprites: 4, models: 0 });
  });

  test("an enemy shown as a model whose next frame's model is still loading is held back that frame, not drawn as a sprite", async () => {
    const l = delayedLoader();
    const r = make([ENEMY, OTHER], l.loader);
    frame(r, enemy(1));
    await l.resolve("enemies/test");
    expect(frame(r, enemy(1))).toEqual({ sprites: 0, models: 1 });
    expect(frame(r, enemy(1, 5))).toEqual({ sprites: 0, models: 0 });
    await l.resolve("enemies/other");
    expect(frame(r, enemy(1, 5))).toEqual({ sprites: 0, models: 1 });
  });
});

describe("preloadLevel", () => {
  const sprite = (index: number, time: number) => ({ sheet: SHEET.id, size: 2 as const, index, grouped: true, time });
  const entries = Array.from({ length: 10 }, (_, i): SpriteModelEntry => ({ model: `m${i}`, sprites: [{ sheet: SHEET.id, size: 2, frames: [1 + i * 2] }] }));

  test("loads earliest needed first, a few at a time, and waits only for what's due by waitUntil", async () => {
    const l = delayedLoader();
    const r = make(entries, l.loader);
    // Times in reverse of index: m9 first. Frames without a model (index 40) are skipped.
    const sprites = [...entries.map((_, i) => sprite(1 + i * 2, (9 - i) * 100)), sprite(40, 0)];
    let resolved = false;
    const p = r.preloadLevel({ sprites }, { waitUntil: 250 }).then((res) => ((resolved = true), res));
    await flush();
    expect(l.order).toEqual(["m9", "m8", "m7", "m6", "m5", "m4"]);
    for (const m of ["m9", "m8"]) await l.resolve(m);
    expect(resolved).toBe(false);
    await l.resolve("m7");
    const res = await p;
    expect(res).toMatchObject({ total: 4, done: 4, models: 10, timedOut: false });
    // The rest go on loading in the background, in order.
    for (const m of ["m6", "m5", "m4", "m3", "m2", "m1"]) await l.resolve(m);
    expect(l.order).toEqual(["m9", "m8", "m7", "m6", "m5", "m4", "m3", "m2", "m1", "m0"]);
    expect(l.maxInFlight()).toBeLessThanOrEqual(6);
  });

  test("gives up after timeoutMs, saying so", async () => {
    vi.useFakeTimers();
    try {
      const l = delayedLoader();
      const r = make(entries.slice(0, 1), l.loader);
      const p = r.preloadLevel({ sprites: [sprite(1, 0)] }, { timeoutMs: 5000 });
      await vi.advanceTimersByTimeAsync(5001);
      expect(await p).toMatchObject({ total: 2, done: 1, timedOut: true });
    } finally {
      vi.useRealTimers();
    }
  });
});
