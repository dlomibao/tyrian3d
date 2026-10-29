import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { screenWorldX, screenWorldZ } from "../../src/game/playfield";
import { DrawListRenderer } from "../../src/render/drawListRenderer";
import { passHeight } from "../../src/render/passHeights";
import {
  parseSpriteArtManifest,
  placeFlatQuad,
  SpriteArt,
  spriteArtImageUrl,
  spriteArtModeFromSearch,
  type FlatQuad,
} from "../../src/render/spriteArt";
import { loadSpriteArt, type SpriteArtLoadIo } from "../../src/render/spriteArtLayer";
import { Pass, type DrawList, type Sprite2Sheet, type SpriteDraw } from "../../src/sim/draw";
import type { Palette } from "../../src/data/palette";

const quiet = () => {};

// The renderer reads ?height= and friends from the page's URL.
vi.stubGlobal("location", { search: "" });

/** A synthetic atlas: sheet "test.shp" with sprites 1 and 2 (12x14 boxes at scale 8) side by side. */
const MANIFEST = {
  scale: 8,
  sheets: {
    "test.shp": {
      image: "test.shp-1.webp",
      frames: { "1": { x: 0, y: 0, w: 96, h: 112 }, "2": { x: 96, y: 0, w: 96, h: 8 } },
    },
  },
};

/**
 * A Sprite2 sheet of `n` sprites (OpenTyrian's RLE): each one opaque pixel of colour 5 in a 12-wide
 * row, except sprite 2, which is empty when `emptySecond`.
 */
function sheet(id: string, n: number, emptySecond = false): Sprite2Sheet {
  const sprites = Array.from({ length: n }, (_, i) => (emptySecond && i === 1 ? [0x0f] : [0x10, 5, 0x0f]));
  // A u16 offset table, then each sprite's RLE after the previous one's.
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
    kind: "sprite2", sheet: sh, index, x: 100, y: 50, size: 1, pass: Pass.PlayerShots, key: 7, effect: "none", filter: 0, value: 0,
    groupIndex: -1, groupSize: 1, groupDx: 0, groupDy: 0, groupFirst: false, ...over,
  };
}

function readyArt(): SpriteArt<THREE.Texture> {
  const art = new SpriteArt<THREE.Texture>(parseSpriteArtManifest(MANIFEST)!);
  art.sheet("test.shp")!.setTexture(new THREE.Texture(), 256, 128);
  return art;
}

const palette: Palette = new Uint8Array(768) as unknown as Palette;

function render(r: DrawListRenderer, items: SpriteDraw[]) {
  const list: DrawList = { items, palette: 0, filter: -99, brightness: 0, screen: null };
  r.setDrawList(list);
  r.setDrawList(list);
  const camera = new THREE.PerspectiveCamera();
  camera.position.set(0, 30, 10);
  r.update(1, camera);
  return r.stats();
}

describe("sprite art manifest", () => {
  test("parses sheets and frames by the draw list's sheet id and sprite index", () => {
    const m = parseSpriteArtManifest(MANIFEST)!;
    expect(m.scale).toBe(8);
    expect(m.sheets.get("test.shp")!.frames.get(2)).toEqual({ x: 96, y: 0, w: 96, h: 8 });
  });

  test("not a manifest: null, so everything draws as before", () => {
    for (const bad of [null, 3, "x", {}, { scale: 0, sheets: {} }, { scale: 8 }, { sheets: {} }]) expect(parseSpriteArtManifest(bad, quiet)).toBeNull();
  });

  test("malformed sheets and frames are dropped, the rest kept", () => {
    const warnings: string[] = [];
    const m = parseSpriteArtManifest({
      scale: 8,
      sheets: {
        a: { frames: { "1": { x: 0, y: 0, w: 8, h: 8 } } },
        b: { image: "b.webp", frames: { "1": { x: 0, y: 0, w: 8, h: 8 }, x: { x: 0, y: 0, w: 8, h: 8 }, "2": { x: 0, y: 0, w: 0, h: 8 }, "3": { x: -1, y: 0, w: 8, h: 8 } } },
      },
    }, (w) => warnings.push(w))!;
    expect([...m.sheets.keys()]).toEqual(["b"]);
    expect([...m.sheets.get("b")!.frames.keys()]).toEqual([1]);
    expect(warnings).toHaveLength(4);
  });

  test("image URLs are escaped (sheet ids have '#')", () => {
    expect(spriteArtImageUrl("/art/sprites/", "tyrian.shp#7.webp")).toBe("/art/sprites/tyrian.shp%237.webp");
  });

  test("frames are there only once the atlas has loaded, with UVs and the original size", () => {
    const art = new SpriteArt<string>(parseSpriteArtManifest(MANIFEST)!);
    const s = art.sheet("test.shp")!;
    expect(s.listed(1)).toBe(true);
    expect(art.frame("test.shp", 1)).toBeUndefined();
    s.setTexture("tex", 256, 128);
    expect(art.frame("test.shp", 1)).toEqual({ u0: 0, v0: 0, u1: 96 / 256, v1: 112 / 128, w: 12, h: 14 });
    expect(art.frame("test.shp", 2)).toMatchObject({ u0: 96 / 256, u1: 192 / 256, w: 12, h: 1 });
    expect(art.frame("test.shp", 3)).toBeUndefined();
    expect(art.frame("other.shp", 1)).toBeUndefined();
    // A frame outside the image is dropped.
    s.setTexture("tex", 128, 128);
    expect(art.frame("test.shp", 2)).toBeUndefined();
  });

  test("?sprites= picks the mode; without it the renderer follows the effects look", () => {
    expect(spriteArtModeFromSearch("?sprites=original")).toBe("original");
    expect(spriteArtModeFromSearch("?vfx=original&sprites=remastered")).toBe("remastered");
    expect(spriteArtModeFromSearch("?sprites=x")).toBeUndefined();
    expect(spriteArtModeFromSearch("")).toBeUndefined();
    const r = new DrawListRenderer();
    r.setSpriteArtMode(undefined);
    r.setVfxMode("remastered");
    expect(r.spriteArtMode).toBe("remastered");
    r.setVfxMode("original");
    expect(r.spriteArtMode).toBe("original");
    r.setSpriteArtMode("remastered");
    expect(r.spriteArtMode).toBe("remastered");
  });
});

describe("loading", () => {
  const io = (manifest: unknown, failTexture = false): SpriteArtLoadIo => ({
    fetchJson: async () => manifest,
    loadTexture: async () => {
      if (failTexture) throw new Error("404");
      return { texture: new THREE.Texture(), width: 256, height: 128 };
    },
  });

  test("no manifest: null", async () => {
    expect(await loadSpriteArt("/", io(undefined))).toBeNull();
    const warn = console.warn;
    console.warn = quiet;
    try {
      expect(await loadSpriteArt("/", { ...io(undefined), fetchJson: () => Promise.reject(new Error("offline")) })).toBeNull();
    } finally {
      console.warn = warn;
    }
  });

  test("atlases load into their sheets, premultiplied and unflipped", async () => {
    const art = (await loadSpriteArt("/", io(MANIFEST)))!;
    await art.loaded;
    const s = art.sheet("test.shp")!;
    expect(s.texture!.premultiplyAlpha).toBe(true);
    expect(s.texture!.flipY).toBe(false);
    expect(art.frame("test.shp", 1)).toBeDefined();
  });

  test("an atlas that fails leaves its sprites original", async () => {
    const warn = console.warn;
    console.warn = quiet;
    try {
      const art = (await loadSpriteArt("/", io(MANIFEST, true)))!;
      await art.loaded;
      expect(art.frame("test.shp", 1)).toBeUndefined();
    } finally {
      console.warn = warn;
    }
  });
});

describe("flat quad placement", () => {
  test("on the ground it is the sprite's screen rectangle", () => {
    const q = placeFlatQuad(100, 50, 12, 14, 0, { x: 0, y: 30, z: 10 }, {} as FlatQuad);
    expect(q.x).toBeCloseTo(screenWorldX(100));
    expect(q.z).toBeCloseTo(screenWorldZ(50));
    expect(q.w).toBeCloseTo(1);
    expect(q.d).toBeCloseTo(14 / 12);
  });

  test("raised, its corners project along the camera rays onto the original rectangle", () => {
    const cam = { x: 1.5, y: 30, z: 12 };
    const h = passHeight(Pass.EnemyShots);
    const q = placeFlatQuad(100, 50, 12, 14, h, cam, {} as FlatQuad);
    expect(q.y).toBe(h);
    // A point at height h, pushed along the ray from the camera down to the ground.
    const ground = (x: number, z: number) => {
      const t = cam.y / (cam.y - h);
      return [cam.x + (x - cam.x) * t, cam.z + (z - cam.z) * t];
    };
    const [x0, z0] = ground(q.x, q.z);
    const [x1, z1] = ground(q.x + q.w, q.z + q.d);
    expect(x0).toBeCloseTo(screenWorldX(100));
    expect(z0).toBeCloseTo(screenWorldZ(50));
    expect(x1).toBeCloseTo(screenWorldX(112));
    expect(z1).toBeCloseTo(screenWorldZ(64));
  });
});

describe("renderer", () => {
  const make = (art: SpriteArt<THREE.Texture> | null) => {
    const r = new DrawListRenderer();
    r.setVfxMode("original"); // no effects: just the sprites
    r.setSpriteArtMode("remastered");
    r.setPalettes([palette]);
    r.setSpriteArt(art);
    return r;
  };

  test("a sprite with art draws as a flat quad, one without as before", () => {
    const sh = sheet("test.shp", 3);
    const s = render(make(readyArt()), [draw(sh, 1), draw(sh, 3)]);
    expect(s.flatSprites).toBe(1);
    expect(s.flatCalls).toBe(1);
    expect(s.instances).toBe(2);
    expect(s.visiblePools).toBe(1); // sprite 3, extruded
  });

  test("the quad is at the sprite's rectangle and carries its frame and effect", () => {
    const sh = sheet("test.shp", 3);
    const art = readyArt();
    const r = make(art);
    const list: DrawList = { items: [draw(sh, 1, { effect: "filter", filter: 0x37 })], palette: 0, filter: -99, brightness: 0, screen: null };
    r.setDrawList(list);
    r.setDrawList(list);
    const camera = new THREE.PerspectiveCamera();
    camera.position.set(0, 30, 10);
    // Look at the instance before end() commits it: peek through the layer after a frame.
    r.update(1, camera);
    const layer = (r as unknown as { artLayer: { peek(s: unknown, p: number): { instance(i: number): { origin: number[]; size: number[]; uv: number[]; fx: number[] } } } }).artLayer;
    const inst = layer.peek(art.sheet("test.shp"), Pass.PlayerShots)!.instance(0);
    const q = placeFlatQuad(100, 50, 12, 14, passHeight(Pass.PlayerShots), camera.position, {} as FlatQuad);
    expect(inst.origin[0]).toBeCloseTo(q.x);
    expect(inst.origin[1]).toBeCloseTo(q.y);
    expect(inst.origin[2]).toBeCloseTo(q.z);
    expect(inst.size[0]).toBeCloseTo(q.w);
    expect(inst.size[1]).toBeCloseTo(q.d);
    expect(inst.uv).toEqual([0, 0, 96 / 256, 112 / 128].map((v) => Math.fround(v)));
    expect(inst.fx).toEqual([1, 3, 0, 1]); // the hit-flash filter, hue 3, opaque
  });

  test("no art, art still loading, or the original look: drawn as before", () => {
    const sh = sheet("test.shp", 3);
    expect(render(make(null), [draw(sh, 1)])).toMatchObject({ flatSprites: 0, visiblePools: 1 });
    const loading = new SpriteArt<THREE.Texture>(parseSpriteArtManifest(MANIFEST)!);
    expect(render(make(loading), [draw(sh, 1)])).toMatchObject({ flatSprites: 0, visiblePools: 1 });
    const r = make(readyArt());
    r.setSpriteArtMode("original");
    expect(render(r, [draw(sh, 1)])).toMatchObject({ flatSprites: 0, visiblePools: 1 });
  });

  test("a 2x2 draw is its four tiles' quads; it stays extruded if a non-empty tile has no art", () => {
    // Sprites 1, 2, 20, 21 make the 2x2 block at 1; give all of them frames.
    const frames: Record<string, { x: number; y: number; w: number; h: number }> = {};
    for (const i of [1, 2, 20, 21]) frames[i] = { x: 0, y: 0, w: 96, h: 8 };
    const art = new SpriteArt<THREE.Texture>(parseSpriteArtManifest({ scale: 8, sheets: { "big.shp": { image: "big.webp", frames } } })!);
    art.sheet("big.shp")!.setTexture(new THREE.Texture(), 256, 128);
    expect(render(make(art), [draw(sheet("big.shp", 21), 1, { size: 2 })])).toMatchObject({ flatSprites: 4, visiblePools: 0 });

    // Without sprite 2's frame: extruded, unless sprite 2 is empty.
    delete frames[2];
    const art2 = new SpriteArt<THREE.Texture>(parseSpriteArtManifest({ scale: 8, sheets: { "big.shp": { image: "big.webp", frames } } })!);
    art2.sheet("big.shp")!.setTexture(new THREE.Texture(), 256, 128);
    expect(render(make(art2), [draw(sheet("big.shp", 21), 1, { size: 2 })])).toMatchObject({ flatSprites: 0, visiblePools: 1 });
    expect(render(make(art2), [draw(sheet("big.shp", 21, true), 1, { size: 2 })])).toMatchObject({ flatSprites: 3, visiblePools: 0 });
  });

  test("many shots of one atlas are one draw per pass", () => {
    const sh = sheet("test.shp", 3);
    const items = Array.from({ length: 500 }, (_, i) => draw(sh, 1 + (i % 2), { pass: i % 3 ? Pass.PlayerShots : Pass.EnemyShots, x: i % 250, key: i }));
    expect(render(make(readyArt()), items)).toMatchObject({ flatSprites: 500, flatCalls: 2, visiblePools: 0 });
  });
});
