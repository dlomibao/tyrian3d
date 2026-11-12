// The player ship's shadow as the C draws it (DECISIONS.md D170, D9's fallback): its `darken` draws
// (blit_sprite2x2_darken in JE_playerMovement, shadowYDist below the ship and shifted with background
// 2's parallax, drawn only while background 2 is on) become soft dark decals.
//
// blit_sprite2_darken halves the shade of what is under the sprite's opaque pixels:
// (index & 0xf0) | ((index & 0x0f) / 2). A decal is the sprite's silhouette, upscaled smoothly, drawn
// black at DARKEN opacity: what is under it keeps half its brightness. It lies flat at DECAL_HEIGHT on
// the camera ray through its screen rectangle (D6), so it covers exactly the screen area the C's
// shadow covered under every camera. It darkens what is below that height (the ground, structures,
// ground and sky enemies) and not the ship above it; in the C's draw order (renderOrder) it comes
// after the blend sheets and the flat art of the passes before the player's, and before the enemy
// shots and explosions.
//
// While a player's shadow is drawn this way its ship model casts no shadow-map shadow (no double).

import * as THREE from "three";
import { composeSprite2x2 } from "./spriteMesh";
import { decodeSprite2, type DecodedSprite } from "../data/sprites";
import { Pass, type Sprite2Sheet } from "../sim/draw";
import { placeFlatQuad, type FlatQuad } from "./spriteArt";
import { PASS_HEIGHT } from "./passHeights";
import { SPRITE_ART_ORDER } from "./spriteArtLayer";

/** What is under a shadow keeps this much of its brightness: the C halves the shade. */
export const DARKEN = 0.5;
/**
 * The decals' height: above the background-3 islands and the sky enemies, below the top enemies and
 * a fully banked ship's low wing tip (~2.5), so nothing of the ship is darkened.
 */
export const DECAL_HEIGHT = (PASS_HEIGHT[Pass.Background3] + PASS_HEIGHT[Pass.TopEnemies]) / 2;
/** Between the player shots' flat art and the enemy shots' (spriteArtLayer: -1 + pass / 100). */
export const DECAL_ORDER = SPRITE_ART_ORDER + Pass.Player / 100 - 0.0005;
/** Mask texels per original pixel, and the transparent border around the sprite, in pixels. */
const SCALE = 4;
const PAD = 1;

/** The player (0 or 1) a shadow draw belongs to: its key is playerKey(n, 2..5) (mainint.ts); else -1. */
export function shadowPlayerOfKey(key: number): number {
  const k = key - 10000; // PLAYER_KEY_BASE (mainint.ts), as playerOfKey reads it
  if (k < 0 || k >= 200) return -1;
  const part = k % 100;
  return part >= 2 && part <= 5 ? Math.floor(k / 100) : -1;
}

/**
 * A sprite's silhouette as a soft alpha mask, SCALE texels per pixel with a PAD-pixel border: the
 * opaque/transparent mask read bilinearly between pixel centres and pushed through a smoothstep, so
 * the staircase comes out rounded with an edge about a pixel wide. Row 0 is the sprite's top.
 */
export function shadowMask(sprite: DecodedSprite): { width: number; height: number; data: Uint8Array } {
  const sw = sprite.width, sh = sprite.height;
  const opaque = (x: number, y: number) => (x >= 0 && y >= 0 && x < sw && y < sh && sprite.pixels[y * sw + x] >= 0 ? 1 : 0);
  const width = (sw + 2 * PAD) * SCALE, height = (sh + 2 * PAD) * SCALE;
  const data = new Uint8Array(width * height * 4);
  for (let ty = 0; ty < height; ty++) {
    // The texel's centre in sprite pixels, measured from pixel centres.
    const py = (ty + 0.5) / SCALE - PAD - 0.5;
    const y0 = Math.floor(py), fy = py - y0;
    for (let tx = 0; tx < width; tx++) {
      const px = (tx + 0.5) / SCALE - PAD - 0.5;
      const x0 = Math.floor(px), fx = px - x0;
      const v =
        (opaque(x0, y0) * (1 - fx) + opaque(x0 + 1, y0) * fx) * (1 - fy) + (opaque(x0, y0 + 1) * (1 - fx) + opaque(x0 + 1, y0 + 1) * fx) * fy;
      const t = Math.min(1, Math.max(0, (v - 0.15) / 0.7));
      const a = Math.round(t * t * (3 - 2 * t) * 255);
      data.set([a, a, a, a], (ty * width + tx) * 4);
    }
  }
  return { width, height, data };
}

interface Decal {
  material: THREE.MeshBasicMaterial;
  /** The sprite's size in original pixels. */
  w: number;
  h: number;
}

export class ShadowDecals {
  readonly root = new THREE.Group();
  private readonly geometry = unitQuad();
  private readonly decals = new Map<string, Decal | null>();
  private readonly meshes: THREE.Mesh[] = [];
  private used = 0;
  /** Bit n: player n's shadow was drawn as a decal this frame. */
  private players = 0;
  private readonly quad: FlatQuad = { x: 0, y: 0, z: 0, w: 0, d: 0 };

  constructor() {
    this.root.name = "shadowDecals";
  }

  /** Start a frame: no decals yet. */
  begin(): void {
    for (let i = 0; i < this.used; i++) this.meshes[i].visible = false;
    this.used = 0;
    this.players = 0;
  }

  /** Whether player `n`'s shadow is a decal this frame (its model then casts none). */
  hasPlayer(n: number): boolean {
    return (this.players & (1 << n)) !== 0;
  }

  /** A darken draw of `size` (1 or 2) sprites at screen (x, y), interpolated. */
  add(sheet: Sprite2Sheet, index: number, size: 1 | 2, key: number, x: number, y: number, cam: THREE.Vector3): void {
    const id = `${sheet.id}#${index}x${size}`;
    let decal = this.decals.get(id);
    if (decal === undefined) this.decals.set(id, (decal = makeDecal(size === 2 ? composeSprite2x2(sheet.data, index) : decodeSprite2(sheet.data, index))));
    this.place(decal, key, x, y, cam);
  }

  /** Show one decal in the middle of the playfield, for the level's shader warm-up (D91); begin() hides it. */
  warm(cam: THREE.Vector3): void {
    let decal = this.decals.get("warm");
    if (decal === undefined) this.decals.set("warm", (decal = makeDecal({ width: 1, height: 1, pixels: Int16Array.of(0) })));
    this.place(decal, -1, 24 + 132, 92, cam);
  }

  private place(decal: Decal | null, key: number, x: number, y: number, cam: THREE.Vector3): void {
    if (!decal) return;
    const player = shadowPlayerOfKey(key);
    if (player >= 0) this.players |= 1 << player;
    if (this.used === this.meshes.length) {
      const mesh = new THREE.Mesh(this.geometry, decal.material);
      mesh.castShadow = mesh.receiveShadow = false;
      mesh.renderOrder = DECAL_ORDER;
      mesh.frustumCulled = false;
      mesh.matrixAutoUpdate = true;
      this.meshes.push(mesh);
      this.root.add(mesh);
    }
    const mesh = this.meshes[this.used++];
    mesh.material = decal.material;
    const q = placeFlatQuad(x - PAD, y - PAD, decal.w + 2 * PAD, decal.h + 2 * PAD, DECAL_HEIGHT, cam, this.quad);
    mesh.position.set(q.x, q.y, q.z);
    mesh.scale.set(q.w, 1, q.d);
    mesh.visible = true;
  }
}

/** A sprite's decal: its mask texture and material; null for an empty sprite. */
function makeDecal(sprite: DecodedSprite): Decal | null {
  if (sprite.height === 0 || !sprite.pixels.some((p) => p >= 0)) return null;
  const mask = shadowMask(sprite);
  const texture = new THREE.DataTexture(mask.data, mask.width, mask.height, THREE.RGBAFormat, THREE.UnsignedByteType);
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.colorSpace = THREE.NoColorSpace;
  texture.needsUpdate = true;
  const material = new THREE.MeshBasicMaterial({
    color: 0x000000,
    alphaMap: texture,
    transparent: true,
    opacity: DARKEN,
    depthWrite: false,
    side: THREE.DoubleSide,
    userData: { outlineParameters: { visible: false } },
  });
  return { material, w: sprite.width, h: sprite.height };
}

/** A unit square in the ground plane, facing up: x 0..1 right, z 0..1 down the screen; uv (x, z). */
function unitQuad(): THREE.BufferGeometry {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1], 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute([0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 1], 2));
  g.setIndex([0, 2, 1, 0, 3, 2]);
  return g;
}
