// Turns the simulation's per-tick draw lists (src/sim/draw.ts) into a 3D scene.
//
// - Sprites become extruded meshes (spriteMesh.ts), one InstancedMesh per distinct sprite and
//   material variant, so a full screen is a few dozen draw calls.
// - Background 1 (the ground) is one instanced quad per tile, textured from a palette-index
//   atlas. Backgrounds 2 and 3 are extruded like sprites (DECISIONS.md D8).
// - Every draw sits at its pass's height (passHeights.ts, D5) but is projected along the camera
//   ray back onto its original screen position and scaled to its original size (D6), so the
//   layout on screen is exactly the original's at any height.
// - Positions are interpolated between the last two ticks at display rate (interpolation.ts, D2).
// - Selected sprites are replaced by hand-made models (D4): the player ship with its banking
//   frames (MODEL_OVERRIDES), and whole enemies, all of whose tiles become one model
//   (setSpriteModels, D15). Models load on first use; until then the sprite stays extruded.
//   Materials named pal_<index> take their colour from the live palette.
//
// - Remastered backgrounds (setBackgroundStyle("remaster"), D34): the ground is upscaled 4x
//   (remaster/groundAtlas.ts) and structure tiles become Blender models found by tile pattern
//   (remaster/tileModels.ts). Tiles without a model, and models still loading, stay as above.
//
// Integrator API: add `root` to the scene, call setPalettes() once, setDrawList() every logic
// tick, and update(alpha, camera) every display frame before rendering.

import * as THREE from "three";
import type { Palette } from "../data/palette";
import { PX_PER_UNIT, screenWorldX, screenWorldZ } from "../game/playfield";
import { Pass, type Draw, type DrawList, type SpriteDraw, type SpriteEffect, type TileDraw } from "../sim/draw";
import { DrawInterpolator } from "./interpolation";
import { FxMode, groundTileMaterial, paletteMaterial } from "./paletteMaterial";
import { PaletteTexture } from "./paletteTexture";
import { passHeight } from "./passHeights";
import { SpriteMeshCache } from "./spriteMesh";
import { colourFrame, rigModel, showFrame, type FrameRig } from "./modelFrames";
import { spriteModelKey, type ModelOverride, type SpriteModels } from "./spriteModels";
import { TileAtlas } from "./tileAtlas";
import { RemasterGroundAtlas } from "./remaster/groundAtlas";
import { remasterGroundMaterial } from "./remaster/groundMaterial";
import { paletteLuma } from "./remaster/mmpx";
import { TileModelIndex } from "./remaster/tileModels";

/** How backgrounds are drawn: the original tiles extruded (D8) or remastered (D34). */
export type BackgroundStyle = "original" | "remaster";

/** Roll at full bank, and how fast the model eases toward its frame's roll (per second). */
const MAX_ROLL = THREE.MathUtils.degToRad(35);
const ROLL_RATE = 12;
/** Opacity standing in for the C's value-averaging blend. */
const BLEND_ALPHA = 0.55;
/** Passes drawn with a partly emissive material: energy shots, explosions, sparks. */
const GLOW_PASSES = new Set<Pass>([Pass.PlayerShots, Pass.EnemyShots, Pass.Explosions, Pass.Effects]);
const GLOW = 0.65;
/** Pools unused for this many frames are freed. */
const POOL_TTL_FRAMES = 1800;

const enum Variant {
  Lit = 0,
  LitBlend,
  Glow,
  GlowBlend,
  Unlit,
  Ground,
  RemasterGround,
}

/** One InstancedMesh and its per-instance data, reused every frame. */
class Pool {
  mesh!: THREE.InstancedMesh;
  /** Per-instance extra data: instFx (4 floats) or instTile (2 floats). */
  extra!: THREE.InstancedBufferAttribute;
  count = 0;
  lastUsed = 0;

  constructor(
    private readonly base: THREE.BufferGeometry,
    private readonly material: THREE.Material,
    private readonly extraName: "instFx" | "instTile",
    private readonly parent: THREE.Object3D,
    private readonly shadows: { cast: boolean; receive: boolean },
    capacity = 16,
  ) {
    this.allocate(capacity);
  }

  private allocate(capacity: number): void {
    const old = this.mesh;
    const g = new THREE.BufferGeometry();
    for (const name of Object.keys(this.base.attributes)) g.setAttribute(name, this.base.attributes[name]);
    g.setIndex(this.base.index);
    const itemSize = this.extraName === "instFx" ? 4 : 2;
    const extra = new THREE.InstancedBufferAttribute(new Float32Array(capacity * itemSize), itemSize);
    extra.setUsage(THREE.DynamicDrawUsage);
    g.setAttribute(this.extraName, extra);
    const mesh = new THREE.InstancedMesh(g, this.material, capacity);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    mesh.frustumCulled = false;
    mesh.castShadow = this.shadows.cast;
    mesh.receiveShadow = this.shadows.receive;
    mesh.count = 0;
    if (old) {
      mesh.instanceMatrix.array.set(old.instanceMatrix.array);
      extra.array.set(this.extra.array);
      this.parent.remove(old);
      old.dispose();
      old.geometry.dispose();
    }
    this.mesh = mesh;
    this.extra = extra;
    this.parent.add(mesh);
  }

  /** Start a slot and return its index; the caller fills the matrix and extra data. */
  next(frame: number): number {
    if (this.count >= this.mesh.instanceMatrix.count) this.allocate(this.mesh.instanceMatrix.count * 2);
    this.lastUsed = frame;
    return this.count++;
  }

  commit(): void {
    const n = this.count;
    this.mesh.count = n;
    this.mesh.visible = n > 0;
    if (n === 0) return;
    const m = this.mesh.instanceMatrix;
    m.clearUpdateRanges();
    m.addUpdateRange(0, n * 16);
    m.needsUpdate = true;
    this.extra.clearUpdateRanges();
    this.extra.addUpdateRange(0, n * this.extra.itemSize);
    this.extra.needsUpdate = true;
    this.count = 0;
  }

  dispose(): void {
    this.parent.remove(this.mesh);
    this.mesh.dispose();
    this.mesh.geometry.dispose();
  }
}

interface ModelClone {
  object: THREE.Object3D;
  roll: number;
  materials: THREE.Material[];
  /** Its pal_ materials and frame-tagged parts (modelFrames.ts). */
  rig: FrameRig;
  blended: boolean;
  /** The palette version, hit-flash hue and sprite frame its parts and colours were last set for. */
  paletteVersion: number;
  hue: number;
  frame: number;
}

/** Clones of one model, reused every frame. `source` is null until the model has loaded. */
interface ModelPool {
  name: string;
  source: THREE.Object3D | null;
  clones: ModelClone[];
  used: number;
}

/** Loads a model by path in public/models/ (without .glb). */
export type ModelLoader = (name: string) => Promise<THREE.Object3D>;

export interface DrawListStats {
  items: number;
  instances: number;
  pools: number;
  visiblePools: number;
  meshes: number;
  atlasTiles: number;
  remasterTiles: number;
}

export class DrawListRenderer {
  /** Add this to the scene. */
  readonly root = new THREE.Group();
  readonly palette = new PaletteTexture();
  readonly cache = new SpriteMeshCache();
  readonly atlas = new TileAtlas();
  readonly remasterAtlas = new RemasterGroundAtlas();

  private readonly interp = new DrawInterpolator();
  private list: DrawList | null = null;
  private items: readonly Draw[] = [];
  private palettes: readonly Palette[] = [];
  private readonly materials: THREE.Material[];
  private readonly pools: Map<THREE.BufferGeometry, Pool>[] = [];
  private readonly allPools: Pool[] = [];
  private readonly groundGeometry = groundQuad();
  private readonly unitQuad = unitQuad();
  private readonly overridesBySheet = new Map<string, { override: ModelOverride; pool: ModelPool }[]>();
  private readonly modelPools = new Map<string, ModelPool>();
  private spriteModels = new Map<string, string>();
  private loader: ModelLoader | null = null;
  private frame = 0;
  private lastTime = performance.now();
  private instances = 0;
  private background: BackgroundStyle = "original";
  private tileModels = new TileModelIndex([]);
  /** Structures already placed this frame, by layer and pattern anchor. */
  private readonly placedStructures = new Set<string>();

  constructor() {
    this.root.name = "draw-list";
    const p = this.palette;
    this.materials = [];
    this.materials[Variant.Lit] = paletteMaterial(p, { lit: true, transparent: false, outline: true });
    this.materials[Variant.LitBlend] = paletteMaterial(p, { lit: true, transparent: true, outline: true });
    this.materials[Variant.Glow] = paletteMaterial(p, { lit: true, transparent: false, outline: true, glow: GLOW });
    this.materials[Variant.GlowBlend] = paletteMaterial(p, { lit: true, transparent: true, outline: false, glow: GLOW });
    this.materials[Variant.Unlit] = paletteMaterial(p, { lit: false, transparent: false, outline: false });
    this.materials[Variant.Ground] = groundTileMaterial(p, this.atlas);
    this.materials[Variant.RemasterGround] = remasterGroundMaterial(p, this.remasterAtlas);
    for (let v = 0; v <= Variant.RemasterGround; v++) this.pools.push(new Map());
  }

  /** The 23 palettes from palette.dat (resources.palettes); draw lists select one by index. */
  setPalettes(palettes: readonly Palette[]): void {
    this.palettes = palettes;
    if (this.list) this.applyPalette(this.list);
  }

  /**
   * Hand over one tick's draws. The list's `items` array must not be mutated afterwards (the
   * sim's beginDrawList starts a new array each tick, so this holds).
   */
  setDrawList(list: DrawList): void {
    this.list = list;
    this.items = list.items;
    this.interp.push(list.items);
    this.applyPalette(list);
    if (this.background === "remaster") {
      const palette = this.palettes[list.palette] ?? this.palettes[0];
      if (palette) this.remasterAtlas.setLuma(paletteLuma(palette));
      this.remasterAtlas.prepare(list.items);
      this.tileModels.prepare(list.items);
    }
  }

  /**
   * Draw backgrounds as the original's tiles (extruded, D8) or remastered (D34): the ground
   * upscaled, and structure tiles as models from `tileModels` (loaded with the sprite models'
   * loader on first sight; until then, and for tiles without a model, the tiles draw as before).
   */
  setBackgroundStyle(style: BackgroundStyle, tileModels: TileModelIndex = new TileModelIndex()): void {
    this.background = style;
    this.tileModels = style === "remaster" ? tileModels : new TileModelIndex([]);
    if (style === "remaster" && this.list) {
      this.remasterAtlas.prepare(this.list.items);
      this.tileModels.prepare(this.list.items);
    }
  }

  get backgroundStyle(): BackgroundStyle {
    return this.background;
  }

  /** Forget interpolation history (level start, teleports). */
  resetInterpolation(): void {
    this.interp.reset();
  }

  get active(): boolean {
    return this.list !== null;
  }

  /**
   * Draw sprites as models (spriteModels.ts): player ships with their banking frames, and grouped
   * sprites (whole enemies). Models are fetched with `loader` the first time they're seen; until
   * then their sprites stay extruded. Models are centred on their origin, forward -Z.
   */
  setSpriteModels(models: SpriteModels, loader: ModelLoader): void {
    this.loader = loader;
    this.spriteModels = models.grouped;
    this.overridesBySheet.clear();
    for (const override of models.banked) {
      let list = this.overridesBySheet.get(override.sheetId);
      if (!list) this.overridesBySheet.set(override.sheetId, (list = []));
      list.push({ override, pool: this.modelPool(override.model) });
    }
  }

  /** Build this frame's instances. alpha interpolates from the previous tick (0) to the current (1). */
  update(alpha: number, camera: THREE.Camera): void {
    const now = performance.now();
    const dt = Math.min(0.1, (now - this.lastTime) / 1000);
    this.lastTime = now;
    this.frame++;
    const frame = this.frame;
    const items = this.items;
    const { prevX, prevY } = this.interp;
    const cam = camera.position;
    let instances = 0;
    for (const mp of this.modelPools.values()) mp.used = 0;
    this.placedStructures.clear();

    for (let i = 0; i < items.length; i++) {
      const d = items[i];
      switch (d.kind) {
        case "sprite2": {
          if (d.effect === "darken") continue; // Real shadows replace the C's shadow sprites (D9).
          const x = prevX[i] + (d.x - prevX[i]) * alpha;
          const y = prevY[i] + (d.y - prevY[i]) * alpha;
          if (d.groupIndex >= 0 && this.spriteModels.size > 0 && this.drawGroupModel(d, x, y, cam)) continue;
          if (this.overridesBySheet.size > 0 && this.drawOverride(d, x, y, cam, dt)) continue;
          const geometry = this.cache.sprite2Geometry(d.sheet, d.index, d.size);
          if (!geometry) continue;
          this.addSprite(geometry, d.pass, d.effect, d.filter, d.value, x, y, cam, frame);
          instances++;
          break;
        }
        case "sprite": {
          if (d.effect === "darken") continue;
          const geometry = this.cache.tableGeometry(d.table, d.index);
          if (!geometry) continue;
          const x = prevX[i] + (d.x - prevX[i]) * alpha;
          const y = prevY[i] + (d.y - prevY[i]) * alpha;
          this.addSprite(geometry, d.pass, d.effect, d.filter, d.value, x, y, cam, frame);
          instances++;
          break;
        }
        case "tile": {
          const x = prevX[i] + (d.x - prevX[i]) * alpha;
          const y = prevY[i] + (d.y - prevY[i]) * alpha;
          if (this.background === "remaster" && this.drawRemasterTile(d, x, y, cam, frame)) {
            instances++;
            break;
          }
          if (d.layer === 0) {
            const pool = this.pool(this.groundGeometry, Variant.Ground, frame);
            const s = pool.next(frame);
            this.atlas.place(d.tileId, d.tile, pool.extra.array as Float32Array, s * 2);
            writeMatrix(pool.mesh.instanceMatrix.array as Float32Array, s, x, y, passHeight(d.pass), 1, 1, cam);
          } else {
            const geometry = this.cache.tileGeometry(d.tileId, d.tile);
            if (!geometry) continue;
            this.addSprite(geometry, d.pass, d.effect, 0, 0, x, y, cam, frame);
          }
          instances++;
          break;
        }
        case "pixel":
          this.addSolid(d.color, d.x, d.y, 1, 1, d.pass, cam, frame);
          instances++;
          break;
        case "rect":
          this.addSolid(d.color, d.x1, d.y1, d.x2 - d.x1 + 1, d.y2 - d.y1 + 1, d.pass, cam, frame);
          instances++;
          break;
      }
    }

    for (let p = 0; p < this.allPools.length; p++) this.allPools[p].commit();
    for (const mp of this.modelPools.values()) {
      for (let c = mp.used; c < mp.clones.length; c++) mp.clones[c].object.visible = false;
    }
    this.atlas.flush();
    this.remasterAtlas.flush();
    this.instances = instances;
    if (frame % 300 === 0) this.evictPools(frame);
  }

  stats(): DrawListStats {
    return {
      items: this.items.length,
      instances: this.instances,
      pools: this.allPools.length,
      visiblePools: this.allPools.filter((p) => p.mesh.visible).length,
      meshes: this.cache.size,
      atlasTiles: this.atlas.size,
      remasterTiles: this.remasterAtlas.size,
    };
  }

  private applyPalette(list: DrawList): void {
    const palette = this.palettes[list.palette] ?? this.palettes[0];
    if (palette) this.palette.set(palette, list.filter, list.brightness);
  }

  private pool(geometry: THREE.BufferGeometry, variant: Variant, frame: number): Pool {
    const map = this.pools[variant];
    let pool = map.get(geometry);
    if (!pool) {
      const opaque = variant === Variant.Lit || variant === Variant.Glow;
      pool = new Pool(
        geometry,
        this.materials[variant],
        variant === Variant.Ground || variant === Variant.RemasterGround ? "instTile" : "instFx",
        this.root,
        { cast: opaque, receive: variant !== Variant.Unlit },
      );
      pool.lastUsed = frame;
      map.set(geometry, pool);
      this.allPools.push(pool);
    }
    return pool;
  }

  private addSprite(
    geometry: THREE.BufferGeometry,
    pass: Pass,
    effect: SpriteEffect,
    filter: number,
    value: number,
    x: number,
    y: number,
    cam: THREE.Vector3,
    frame: number,
  ): void {
    const blend = effect === "blend";
    const glow = GLOW_PASSES.has(pass);
    const variant = glow ? (blend ? Variant.GlowBlend : Variant.Glow) : blend ? Variant.LitBlend : Variant.Lit;
    const pool = this.pool(geometry, variant, frame);
    const s = pool.next(frame);
    writeMatrix(pool.mesh.instanceMatrix.array as Float32Array, s, x, y, passHeight(pass), 1, 1, cam);
    const fx = pool.extra.array as Float32Array;
    const o = s * 4;
    if (effect === "filter") {
      fx[o] = FxMode.Filter;
      fx[o + 1] = (filter >> 4) & 0x0f;
      fx[o + 2] = 0;
    } else if (effect === "hv") {
      fx[o] = FxMode.HueValue;
      fx[o + 1] = filter & 0x0f;
      fx[o + 2] = value;
    } else {
      fx[o] = FxMode.None;
      fx[o + 1] = 0;
      fx[o + 2] = 0;
    }
    fx[o + 3] = blend ? BLEND_ALPHA : 1;
  }

  private addSolid(color: number, x: number, y: number, w: number, h: number, pass: Pass, cam: THREE.Vector3, frame: number): void {
    const pool = this.pool(this.unitQuad, Variant.Unlit, frame);
    const s = pool.next(frame);
    writeMatrix(pool.mesh.instanceMatrix.array as Float32Array, s, x, y, passHeight(pass), w, h, cam);
    const fx = pool.extra.array as Float32Array;
    fx[s * 4] = FxMode.Solid;
    fx[s * 4 + 1] = color & 0xff;
    fx[s * 4 + 2] = 0;
    fx[s * 4 + 3] = 1;
  }

  /**
   * Draw a background tile remastered (D34): a structure tile as its model (once per structure per
   * frame, at the pattern's centre), and a ground tile from the upscaled atlas (also under a ground
   * structure). Returns false to draw the tile the original way.
   */
  private drawRemasterTile(d: TileDraw, x: number, y: number, cam: THREE.Vector3, frame: number): boolean {
    let modelled = false;
    if (this.tileModels.has(d)) {
      const match = this.tileModels.match(d);
      const pool = match ? this.modelPool(match.entry.model) : null;
      if (match && pool?.source) {
        const id = `${match.anchorKey}|${match.entry.model}`;
        if (!this.placedStructures.has(id)) {
          this.placedStructures.add(id);
          this.placeModel(pool, x + match.dx, y + match.dy, { pass: d.pass, effect: d.effect, filter: 0 }, cam);
        }
        if (!(match.entry.keepTiles ?? d.layer === 0)) return true;
        modelled = true;
      }
    }
    if (d.layer !== 0) return modelled;
    const pool = this.pool(this.groundGeometry, Variant.RemasterGround, frame);
    const s = pool.next(frame);
    if (!this.remasterAtlas.place(d.key, pool.extra.array as Float32Array, s * 2)) {
      pool.count--; // No slot yet (no palette): give the instance back.
      return false;
    }
    writeMatrix(pool.mesh.instanceMatrix.array as Float32Array, s, x, y, passHeight(d.pass), 1, 1, cam);
    return true;
  }

  /** Draw a sprite as its override model (the player ship and its banking frames), if it has one. */
  private drawOverride(d: SpriteDraw, x: number, y: number, cam: THREE.Vector3, dt: number): boolean {
    const overrides = this.overridesBySheet.get(d.sheet.id);
    if (!overrides) return false;
    for (let p = 0; p < overrides.length; p++) {
      const { override: o, pool } = overrides[p];
      const offset = d.index - o.baseIndex;
      if (d.size !== o.size || offset % o.bankStep !== 0 || Math.abs(offset) > o.bankStep * o.maxBank) continue;
      if (!pool.source) return false;
      const bank = offset / o.bankStep / o.maxBank; // -1..1
      const clone = this.placeModel(pool, x + (d.size * 12) / 2, y + (d.size * 14) / 2, d, cam);
      // Banking eases per display frame, so the 5 sprite frames become a smooth roll.
      clone.roll += (-bank * MAX_ROLL - clone.roll) * Math.min(1, dt * ROLL_RATE);
      clone.object.rotation.z = clone.roll;
      return true;
    }
    return false;
  }

  /**
   * Draw a tile of a grouped object (an enemy) as part of the object's model, if it has one that
   * has loaded: the model goes at the object's centre on its first tile, and the other tiles draw
   * nothing. Returns false to draw the tile as a sprite.
   */
  private drawGroupModel(d: SpriteDraw, x: number, y: number, cam: THREE.Vector3): boolean {
    const name = this.spriteModels.get(spriteModelKey(d.sheet.id, d.groupSize, d.groupIndex));
    if (name === undefined) return false;
    const pool = this.modelPool(name);
    if (!pool.source) return false;
    if (d.groupFirst) this.placeModel(pool, x + d.groupDx, y + d.groupDy, d, cam, d.groupIndex);
    return true;
  }

  /** The pool for a model, starting its load the first time it's asked for. */
  private modelPool(name: string): ModelPool {
    let pool = this.modelPools.get(name);
    if (!pool) {
      const created: ModelPool = { name, source: null, clones: [], used: 0 };
      this.modelPools.set(name, (pool = created));
      this.loader?.(name).then(
        (model) => (created.source ??= model),
        (err) => console.error(`model ${name} failed to load; its sprites stay extruded`, err),
      );
    }
    return pool;
  }

  /**
   * Show the pool's next clone with its origin at screen point (cx, cy) on the draw's pass, at the
   * size the sprite had on screen (D6), translucent for the "blend" effect and with the enemy
   * hit-flash hue for "filter". `frame` is the sprite frame drawn, for models that animate (D17).
   */
  private placeModel(pool: ModelPool, cx: number, cy: number, d: Pick<SpriteDraw, "pass" | "effect" | "filter">, cam: THREE.Vector3, frame = -1): ModelClone {
    if (pool.used === pool.clones.length) pool.clones.push(this.cloneModel(pool.source!));
    const clone = pool.clones[pool.used++];
    const { object } = clone;
    object.visible = true;
    const h = passHeight(d.pass);
    const k = h / cam.y;
    const gx = screenWorldX(cx);
    const gz = screenWorldZ(cy);
    object.position.set(gx + (cam.x - gx) * k, h, gz + (cam.z - gz) * k);
    object.scale.setScalar(1 - k);

    const blended = d.effect === "blend";
    if (blended !== clone.blended) {
      clone.blended = blended;
      for (const m of clone.materials) {
        m.transparent = blended;
        m.opacity = blended ? BLEND_ALPHA : 1;
        m.depthWrite = !blended;
        m.needsUpdate = true;
      }
    }

    // blit_sprite2_filter draws (filter & 0xf0) | (index & 0x0f): the same shade in another hue.
    const hue = d.effect === "filter" ? d.filter & 0xf0 : -1;
    const { rig } = clone;
    const frameChanged = rig.animated && clone.frame !== frame;
    if (frameChanged) showFrame(rig, frame);
    if (rig.palette.length > 0 && (frameChanged || clone.paletteVersion !== this.palette.version || clone.hue !== hue)) {
      clone.paletteVersion = this.palette.version;
      clone.hue = hue;
      colourFrame(rig, frame, hue, this.paletteColor);
    }
    clone.frame = frame;
    return clone;
  }

  private cloneModel(source: THREE.Object3D): ModelClone {
    const object = source.clone(true);
    const materials: THREE.Material[] = [];
    object.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      // Own materials, so one clone can turn translucent (invulnerability) without the others.
      mesh.material = Array.isArray(mesh.material) ? mesh.material.map((m) => m.clone()) : mesh.material.clone();
      materials.push(...(Array.isArray(mesh.material) ? mesh.material : [mesh.material]));
    });
    this.root.add(object);
    return { object, roll: 0, materials, rig: rigModel(object), blended: false, paletteVersion: -1, hue: -1, frame: Number.NaN };
  }

  private readonly paletteColor = (index: number, target: THREE.Color) => this.palette.color(index, target);

  private evictPools(frame: number): void {
    for (let v = 0; v < this.pools.length; v++) {
      for (const [geometry, pool] of this.pools[v]) {
        if (frame - pool.lastUsed > POOL_TTL_FRAMES) {
          pool.dispose();
          this.pools[v].delete(geometry);
          this.allPools.splice(this.allPools.indexOf(pool), 1);
        }
      }
    }
  }
}

/**
 * Write instance `slot`'s matrix: the draw's top-left at screen (x, y), at `height` above the
 * ground, scaled by (w, h) px. The position is projected along the ray from the camera through
 * the draw's ground position, and the scale shrinks with height by the same factor, so the draw
 * covers exactly the screen area it covered in the original (DECISIONS.md D6).
 */
function writeMatrix(m: Float32Array, slot: number, x: number, y: number, height: number, w: number, h: number, cam: THREE.Vector3): void {
  const k = height / cam.y;
  const gx = screenWorldX(x);
  const gz = screenWorldZ(y);
  const s = (1 - k) / PX_PER_UNIT;
  const o = slot * 16;
  m[o] = s * w;
  m[o + 1] = 0;
  m[o + 2] = 0;
  m[o + 3] = 0;
  m[o + 4] = 0;
  m[o + 5] = s;
  m[o + 6] = 0;
  m[o + 7] = 0;
  m[o + 8] = 0;
  m[o + 9] = 0;
  m[o + 10] = s * h;
  m[o + 11] = 0;
  m[o + 12] = gx + (cam.x - gx) * k;
  m[o + 13] = height;
  m[o + 14] = gz + (cam.z - gz) * k;
  m[o + 15] = 1;
}

/** A 24x28 px ground tile quad (top-left at the origin), with tile-space UVs. */
function groundQuad(): THREE.BufferGeometry {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 24, 0, 0, 24, 0, 28, 0, 0, 28], 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute([0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], 3));
  g.setAttribute("tileUvIn", new THREE.Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 1], 2));
  g.setIndex([0, 2, 1, 0, 3, 2]);
  return g;
}

/** A 1x1 px horizontal quad (top-left at the origin) for pixels and rectangles. */
function unitQuad(): THREE.BufferGeometry {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1], 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute([0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], 3));
  g.setAttribute("palIndex", new THREE.Float32BufferAttribute([0, 0, 0, 0], 1));
  g.setIndex([0, 2, 1, 0, 3, 2]);
  return g;
}
