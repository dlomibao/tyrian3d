// D247: a shot's hit spark (explosion type 0, newsh6.shp 146-152) is drawn again in the remastered
// effects, as its painted flat art; the original effects look keeps the C's sprite. A blended one over
// an enemy's flat art (the asteroids, D244) reads the painting under it, not the ground.
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { DrawListRenderer } from "../../src/render/drawListRenderer";
import { EXPLOSION_DATA, EXPLOSION_SHEET_ID, isHitSpark } from "../../src/render/vfx/explosionFrames";
import { parseSpriteArtManifest, SpriteArt } from "../../src/render/spriteArt";
import { Pass, type DrawList, type Sprite2Sheet, type SpriteDraw } from "../../src/sim/draw";
import type { Palette } from "../../src/data/palette";
import { coversTerrain } from "../../src/render/underShade";
import manifest from "../../public/art/sprites/manifest.json";

vi.stubGlobal("location", { search: "" });

const HIT_FRAMES = [146, 147, 148, 149, 150, 151, 152];

/** An explosion sheet whose sprite `index` is a 3-pixel row in the hit spark's red (0x75), the rest empty. */
function explosionSheet(index: number): Sprite2Sheet {
  const table = index * 2;
  const data = new Uint8Array(table + 6);
  for (let i = 0; i < index; i++) {
    data[i * 2] = table & 0xff;
    data[i * 2 + 1] = table >> 8;
  }
  data.set([0x30, 0x75, 0x77, 0x75, 0x00, 0x0f], table);
  return { id: EXPLOSION_SHEET_ID, data };
}

function hit(sheet: Sprite2Sheet, index: number): SpriteDraw {
  return {
    kind: "sprite2", sheet, index, x: 100, y: 80, size: 1, pass: Pass.Explosions, key: 30001, effect: "none", filter: 0, value: 0,
    groupIndex: -1, groupSize: 1, groupDx: 0, groupDy: 0, groupFirst: false,
  };
}

/** Flat art quads drawn for one hit spark frame in the given effects look. */
function flatQuads(vfx: "original" | "remastered", index = 146): number {
  const art = new SpriteArt<THREE.Texture>(parseSpriteArtManifest({ scale: 8, sheets: { [EXPLOSION_SHEET_ID]: { image: "x.webp", frames: { [index]: { x: 0, y: 0, w: 96, h: 8 } } } } })!);
  art.sheet(EXPLOSION_SHEET_ID)!.setTexture(new THREE.Texture(), 128, 16);
  const r = new DrawListRenderer();
  r.setVfxMode(vfx);
  r.setSpriteArtMode("remastered");
  r.setPalettes([new Uint8Array(768) as unknown as Palette]);
  r.setSpriteArt(art);
  const list: DrawList = { items: [hit(explosionSheet(index), index)], palette: 0, filter: -99, brightness: 0, screen: null };
  r.setDrawList(list);
  r.setDrawList(list);
  const camera = new THREE.PerspectiveCamera();
  camera.position.set(0, 30, 10);
  r.update(1, camera);
  return r.stats().flatSprites;
}

describe("hit sparks (D247)", () => {
  test("are explosion type 0's seven frames on the explosion sheet", () => {
    const [sprite, ttl] = EXPLOSION_DATA[0];
    expect(Array.from({ length: ttl }, (_, f) => sprite + 2 + f)).toEqual(HIT_FRAMES);
    for (const i of HIT_FRAMES) expect(isHitSpark(EXPLOSION_SHEET_ID, i)).toBe(true);
    for (const i of [145, 153, 122]) expect(isHitSpark(EXPLOSION_SHEET_ID, i)).toBe(false);
    expect(isHitSpark("newsh5.shp", 146)).toBe(false);
  });

  test("every frame has painted flat art", () => {
    const frames = (manifest as { sheets: Record<string, { frames: Record<string, unknown> }> }).sheets[EXPLOSION_SHEET_ID].frames;
    for (const i of HIT_FRAMES) expect(frames[String(i)], `newsh6.shp ${i}`).toBeDefined();
  });

  test("the remastered effects draw the spark as its flat art; the original effects keep the sprite", () => {
    expect(flatQuads("remastered")).toBe(1);
    expect(flatQuads("original")).toBe(0);
  });

  test("an enemy's flat art hides the terrain's shade from the blends over it; shots, the ship and explosions don't", () => {
    const batch = (pass?: number) => Object.assign(new THREE.Object3D(), { userData: pass === undefined ? {} : { artPass: pass } });
    for (const p of [Pass.GroundEnemies, Pass.SkyEnemies, Pass.TopEnemies, Pass.SkyEnemiesOver]) expect(coversTerrain(batch(p))).toBe(true);
    for (const p of [Pass.PlayerShots, Pass.EnemyShots, Pass.Player, Pass.Explosions, Pass.Effects]) expect(coversTerrain(batch(p))).toBe(false);
    expect(coversTerrain(batch())).toBe(false);
  });
});
