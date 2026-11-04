// Turns the simulation's per-tick draw lists (src/sim/draw.ts) into a 3D scene.
//
// - Sprites become extruded meshes (spriteMesh.ts), one InstancedMesh per distinct sprite and
//   material variant, so a full screen is a few dozen draw calls.
// - Background 1 (the ground) is one instanced quad per tile, textured from a palette-index
//   atlas. Backgrounds 2 and 3 are extruded like sprites (DECISIONS.md D8), except background 2
//   drawn blended (draw_background_2_blend: TYRIAN's ice clouds), which is flat translucent quads
//   from the same atlas (D45).
// - Every draw sits at its pass's height (passHeights.ts, D5) but is projected along the camera
//   ray back onto its original screen position and scaled to its original size (D6), so the
//   layout on screen is exactly the original's at any height.
// - Positions are interpolated between the last two ticks at display rate (interpolation.ts, D2).
// - Selected sprites are replaced by hand-made models (D4): the player ship with its banking
//   frames (MODEL_OVERRIDES), and whole enemies, all of whose tiles become one model
//   (setSpriteModels, D15), and sprites drawn on their own, like sidekicks (D49). preloadLevel
//   loads a level's models before it starts. Each object (an enemy, a ship, a sidekick) is drawn
//   one way for its life (D54): as its model if that had loaded when it appeared; held back (drawn
//   as nothing) for up to HOLD_MS while it loads; else as its extruded sprite, even after the model
//   arrives. So a sprite never pops into its model. Which way a sprite is drawn is decided by
//   sprite2Route.ts.
//   Materials named pal_<index> take their colour from the live palette.
//
// - Remastered backgrounds (setBackgroundStyle("remaster"), D34): the ground is upscaled 4x
//   (remaster/groundAtlas.ts) and structure tiles become Blender models found by tile pattern
//   (remaster/tileModels.ts). Tiles without a model, and models still loading, stay as above.
//   With HD terrain (setTerrainStyle("hd"), D57), tiles with a painting in public/art/terrain/ are
//   flat quads from its atlases instead (remaster/terrainMaterial.ts); the rest stay as above.
//
// - Remastered flat sprite art (setSpriteArt, D42): sprites with a painting in
//   public/art/sprites/ (shots and pickups) are flat textured quads (spriteArtLayer.ts) instead of
//   extruded sprites or models. Sprites without one, and atlases still loading, stay as above.
//
// Integrator API: add `root` to the scene, call setPalettes() once, setDrawList() every logic
// tick, and update(alpha, camera) every display frame before rendering.

import * as THREE from "three";
import type { Palette } from "../data/palette";
import { PX_PER_UNIT, screenWorldX, screenWorldZ } from "../game/playfield";
import { ENEMY_KEY_BASE, Pass, type Draw, type DrawList, type Sprite2Sheet, type SpriteDraw, type SpriteEffect, type TileDraw } from "../sim/draw";
import { DrawInterpolator } from "./interpolation";
import { FxMode, groundTileMaterial, paletteMaterial } from "./paletteMaterial";
import { PaletteTexture } from "./paletteTexture";
import { passHeight } from "./passHeights";
import { SpriteMeshCache } from "./spriteMesh";
import { colourFrame, rigModel, showFrame, type FrameRig } from "./modelFrames";
import { castsShadow, isModelHelper, setModelBlended } from "./modelPrep";
import { adoptRockMaterials, cloneRockMaterial, isRockMaterial, rockFades, setRockLook } from "./rockMaterial";
import type { SpriteModels } from "./spriteModels";
import { DamageFrames, type DamageState } from "./damage/damageFrames";
import { damageModeFromSearch } from "./damage/damageMode";
import { ShipCondition } from "./damage/shipDamage";
import { Route, Sprite2Router } from "./sprite2Route";
import { bankShift } from "./bankShift";
import type { LevelDamage, LevelSprite, LevelTile } from "../sim/levelSprites";
import { TileAtlas } from "./tileAtlas";
import { RemasteredFx, SpriteLook } from "./vfx/remasteredFx";
import { vfxModeFromSearch, type VfxMode } from "./vfx/vfxMode";
import { RemasterGroundAtlas } from "./remaster/groundAtlas";
import { remasterGroundMaterial } from "./remaster/groundMaterial";
import { paletteLuma } from "./remaster/mmpx";
import { TILE_MODELS, TileModelIndex } from "./remaster/tileModels";
import { StructureInstances } from "./remaster/structureInstances";
import { OpaqueCover, paintOutWreck } from "./remaster/opaqueCover";
import { modelHeightFromUrl } from "./modelHeight";
import { placeFlatQuad, SPRITE2X2_PARTS, spriteArtModeFromSearch, type FlatQuad, type ReadyFrame, type SpriteArt, type SpriteArtMode, type SpriteArtSheet } from "./spriteArt";
import { SpriteArtLayer } from "./spriteArtLayer";
import { BG_KEY_LAYER } from "../sim/backgrnd";
import { MAP_SIZES, TILE_HEIGHT, TILE_WIDTH } from "../data/levels";
import { terrainStyle as currentTerrainStyle, type TerrainStyle } from "../core/terrainStyle";
import { parseTileId, type TerrainTileset } from "./remaster/terrainArt";
import { TerrainArtSet } from "./remaster/terrainLoader";
import { terrainDepthMaterial, terrainMaterial, type TerrainKind } from "./remaster/terrainMaterial";

/** How backgrounds are drawn: the original tiles extruded (D8) or remastered (D34). */
export type BackgroundStyle = "original" | "remaster";

/**
 * The ground structures' tiles (layer 0 models that keep their tiles: TYRIAN's wrecks, trees and
 * boulders), as tile ids. Enemies that stand on them may hide them as their sprites did (D86).
 */
const WRECK_TILES = new Set(
  TILE_MODELS.filter((e) => e.layer === 0 && e.keepTiles !== false).flatMap((e) => e.tiles.flat().filter((n) => n >= 0).map((n) => `${e.shapes}:${n}`)),
);

/**
 * A wreck that fills its cells (TYRIAN's tyrbld-wreck crater: scorched dirt in the dirt colours, so
 * paintOutWreck would leave its outline) draws, in the pixel looks, as the plain ground tile the map
 * puts round it while an enemy covers it (the rock outcrop, D86).
 */
const COVERED_STAND_IN = new Map([340, 341, 342, 350, 351, 352].map((n) => [`shapesz.dat:${n}`, "shapesz.dat:100"]));
const STAND_IN_IDS = new Set(COVERED_STAND_IN.values());

/** How fast a ship's model eases toward its banking frame's roll (per second; the roll: spriteModels.ts bankRoll, D93). */
const ROLL_RATE = 12;
/** Opacity standing in for the C's value-averaging blend. */
const BLEND_ALPHA = 0.55;
/** Passes drawn with a partly emissive material: energy shots, explosions, sparks. */
const GLOW_PASSES = new Set<Pass>([Pass.PlayerShots, Pass.EnemyShots, Pass.Explosions, Pass.Effects]);
const GLOW = 0.65;
/** Shots and fireballs under the remastered effects (D35): fully emissive, no outline. */
const HOT_GLOW = 1.0;
/** Translucent ones (the C's blended explosions) glow harder, so they read as fire over anything. */
const HOT_BLEND_GLOW = 1.6;
/** Passes the remastered effects see (src/render/vfx/remasteredFx.ts). */
const VFX_PASSES = new Set<Pass>([Pass.PlayerShots, Pass.EnemyShots, Pass.Explosions]);
/** Pools unused for this many frames are freed. */
const POOL_TTL_FRAMES = 1800;

const enum Variant {
  Lit = 0,
  LitBlend,
  Glow,
  GlowBlend,
  Unlit,
  Ground,
  Hot,
  HotBlend,
  RemasterGround,
  /** Blended background-2 tiles (draw_background_2_blend) as flat translucent sheets. */
  GroundBlend,
  RemasterGroundBlend,
}

/** Variants drawn as atlas quads (per-instance atlas offset) rather than meshes. */
const TILE_VARIANTS = new Set<Variant>([Variant.Ground, Variant.RemasterGround, Variant.GroundBlend, Variant.RemasterGroundBlend]);

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
    /** The shadow pass's material (HD terrain cutouts: only their opaque part casts). */
    private readonly depthMaterial?: THREE.Material,
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
    if (this.depthMaterial) mesh.customDepthMaterial = this.depthMaterial;
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
  /** A player ship's sideways shift toward its banking frame's sprite, game pixels (bankShift.ts). */
  shift: number;
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
  /** The load failed: the model's sprites are drawn extruded. */
  failed: boolean;
  /** Settles when the load has finished, loaded or failed. */
  settled: Promise<void>;
  clones: ModelClone[];
  used: number;
}

/** What a level can show (preloadLevel): the sprites it can draw and its background tiles. */
export interface LevelModelInfo {
  /** Every sprite the level can draw (sim/levelSprites.ts): enemies' frames, ships, sidekicks. */
  sprites: readonly LevelSprite[];
  /** The level's shapes?.dat (the tileId prefix), for its structure models; undefined: none. */
  tileShapes?: string;
  /** The tiles on its maps (sim/levelSprites.ts levelTiles), for which structure models it needs. */
  tiles?: readonly LevelTile[];
  /**
   * Its three maps as tile numbers (-1: none), row-major MAP_SIZES[layer].width wide, for the HD
   * terrain's neighbour variants (D57).
   */
  maps?: readonly [ArrayLike<number>, ArrayLike<number>, ArrayLike<number>];
  /** Its enemies' damaged frames (levelDamageFrames), drawn with their intact models (D87). */
  damage?: readonly LevelDamage[];
}

/** A model a level can show, and roughly when it's first needed (LevelSprite.time). */
export interface LevelModel {
  name: string;
  time: number;
  structure: boolean;
}

/** How preloadLevel went. */
export interface PreloadResult {
  /** Loads waited for (models due by `waitUntil`, and the sprite art), and how many had finished. */
  total: number;
  done: number;
  /** Every model of the level, waited for or not, which go on loading in the background. */
  models: number;
  /** It gave up waiting after `timeoutMs`; the rest go on loading. */
  timedOut: boolean;
}

/** Model loads preloadLevel keeps going at once, earliest needed first (on-demand loads skip the queue). */
const PRELOAD_CONCURRENCY = 6;

/**
 * How one object (an enemy, a ship, a sidekick: the draws sharing an object key) is drawn while
 * its model is shown or due (D54). Decided when the object first needs a model and kept for its
 * life, so it never pops from sprite to model.
 */
const enum ObjectLook {
  /** Its model was still loading when it appeared: drawn as nothing for up to HOLD_MS. */
  Holding,
  Model,
  /** Its model wasn't there in time (or failed): the extruded sprite for its whole life. */
  Sprite,
}

interface ObjectState {
  look: ObjectLook;
  /** When it first appeared (performance.now()), for Holding. */
  since: number;
  /** The last frame (DrawListRenderer.frame) it was drawn on, for forgetting it. */
  seen: number;
}

/**
 * How long an object whose model is still loading is held back (drawn as nothing) before it's
 * locked to its sprite for its life (D54). Short enough that an enemy flying in is barely late.
 */
export const HOLD_MS = 250;

/**
 * The object a draw belongs to, for ObjectState: an enemy (its four quarters share one), or the
 * draw's own key (a player ship, a trail, a sidekick). Null without a key.
 */
function objectKey(d: SpriteDraw): number | null {
  if (d.key < 0) return null;
  return d.key >= ENEMY_KEY_BASE ? -1 - Math.floor((d.key - ENEMY_KEY_BASE) / 4) : d.key;
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
  /** Structure model copies drawn (remastered backgrounds). */
  structures: number;
  /** Flat sprite art quads drawn, and their draw calls (D42). */
  flatSprites: number;
  flatCalls: number;
  /** HD terrain tiles drawn (D57). */
  hdTiles: number;
}

export class DrawListRenderer {
  /** Add this to the scene. */
  readonly root = new THREE.Group();
  readonly palette = new PaletteTexture();
  /** Each player ship's wear by its armour (D90), by player index; reset where no armour is drawn. */
  private readonly ships: ShipCondition[] = [];
  /** The ships' wear is following armour (a level's draw lists); false: the next one snaps to it. */
  private shipsLive = false;
  /** Damaged frames drawn with the intact models (D87); null with `?damage=off` (as sprites). */
  private readonly damage: DamageFrames | null = damageModeFromSearch() === "off" ? null : new DamageFrames(this.palette);
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
  private readonly modelPools = new Map<string, ModelPool>();
  /** Which way each Sprite2 draw goes: flat, a model, or extruded (sprite2Route.ts, D54). */
  private router = new Sprite2Router();
  /** The sheet of the draw being routed, for emptyTile. */
  private routeSheet: Sprite2Sheet | null = null;
  private readonly emptyTile = (index: number): boolean => this.cache.sprite2Geometry(this.routeSheet!, index, 1) === null;
  /** The sprite art (manifest and atlases) while it loads, so preloadLevel can wait for it. */
  private artLoading: Promise<unknown> = Promise.resolve();
  /** Per object key (objectKey): whether it's drawn as its model or its sprite (D54). */
  private readonly objects = new Map<number, ObjectState>();
  /** Per structure in view (anchor|model): whether it's drawn as its model or its tiles (D54). */
  private readonly structureLooks = new Map<string, { model: boolean; seen: number }>();
  /** `?height=N`: the models stretched along their up axis (modelHeight.ts). */
  private readonly modelHeight = modelHeightFromUrl();
  private loader: ModelLoader | null = null;
  private frame = 0;
  private lastTime = performance.now();
  private instances = 0;
  /** The remastered shot and explosion effects, or null for the original look (D35). */
  private fx: RemasteredFx | null = null;
  private vfx: VfxMode = "original";
  /** Speed of the effects' clock (0 freezes particles and flashes, for debug screenshots). */
  vfxTimeScale = 1;
  private background: BackgroundStyle = "original";
  private tileModels = new TileModelIndex([]);
  /** Structures already placed this frame, by layer and pattern anchor. */
  private readonly placedStructures = new Set<string>();
  /** This frame's ground structures, placed once the enemies are known (D86), and what the enemy models cover. */
  private readonly groundStructures: {
    model: string; x: number; y: number; z: number; scale: number;
    neighbours: ((row: number, col: number) => number[]) | undefined;
    left: number; top: number; w: number; h: number;
  }[] = [];
  private readonly cover = new OpaqueCover();
  /** This frame's ground cells of wreck tiles, drawn once the frame knows whether enemies cover them (D86). */
  private readonly groundCells: { d: TileDraw; x: number; y: number; remaster: boolean }[] = [];
  /** Wreck tiles with their wreck painted out to dirt (D86), by tile id. */
  private readonly coveredTiles = new Map<string, Uint8Array>();
  /** The plain ground tiles that stand in for covered wreck tiles (COVERED_STAND_IN), as last drawn. */
  private readonly standInTiles = new Map<string, Uint8Array>();
  private readonly structures = new StructureInstances();
  /** Structure models asked for (loading or loaded). */
  private readonly structureLoads = new Map<string, Promise<void>>();
  private readonly preloadedShapes = new Set<string>();
  /** Remastered flat sprite art (D42): the atlases, if any, and the layer that draws them. */
  private spriteArt: SpriteArt<THREE.Texture> | null = null;
  private readonly artLayer: SpriteArtLayer;
  /** `?sprites=` (or setSpriteArtMode); undefined follows the effects look. */
  private artMode: SpriteArtMode | undefined = spriteArtModeFromSearch();
  /** Each sheet's art, by the sheet object (null: none), so the per-draw lookup builds no strings. */
  private artSheets = new WeakMap<object, SpriteArtSheet<THREE.Texture> | null>();
  private readonly quad: FlatQuad = { x: 0, y: 0, z: 0, w: 0, d: 0 };
  /** HD terrain (D57): the look, the tilesets' art, its pools by material, and its materials. */
  private terrain: TerrainStyle = currentTerrainStyle();
  readonly terrainArt = new TerrainArtSet();
  private readonly hdPools = new Map<THREE.Material, Pool>();
  private readonly hdMaterials = new Map<string, { material: THREE.Material; depth?: THREE.Material }>();
  private readonly terrainLevel = { levelFilter: { value: -99 }, levelBrightness: { value: 0 } };
  /** tileId → [tileset, tile number] (null: not a tileset tile). */
  private readonly tileIds = new Map<string, [string, number] | null>();
  /** The current level's maps for the HD terrain's variants, and its tileset. */
  private levelMaps: { tileset: string; maps: NonNullable<LevelModelInfo["maps"]> } | null = null;
  private hdTiles = 0;
  /** The level's warm-up has run (D91): models that load from now on are warmed as they arrive. */
  private warmed = false;
  /** Models (by pool) and structures loaded since the warm-up, not yet handed to takeLateWarm. */
  private readonly lateModels: ModelPool[] = [];
  private readonly lateStructures: string[] = [];

  constructor() {
    this.root.name = "draw-list";
    setRockLook(this.terrain === "hd");
    this.root.add(this.structures.group);
    const p = this.palette;
    this.materials = [];
    this.materials[Variant.Lit] = paletteMaterial(p, { lit: true, transparent: false, outline: true });
    // No outline on translucent draws: OutlineEffect draws the shell opaque (per-instance alpha is in
    // the shader, not material.opacity), which hides whatever the sprite should let through.
    this.materials[Variant.LitBlend] = paletteMaterial(p, { lit: true, transparent: true, outline: false });
    this.materials[Variant.Glow] = paletteMaterial(p, { lit: true, transparent: false, outline: true, glow: GLOW });
    this.materials[Variant.GlowBlend] = paletteMaterial(p, { lit: true, transparent: true, outline: false, glow: GLOW });
    this.materials[Variant.Unlit] = paletteMaterial(p, { lit: false, transparent: false, outline: false });
    this.materials[Variant.Ground] = groundTileMaterial(p, this.atlas);
    this.materials[Variant.Hot] = paletteMaterial(p, { lit: true, transparent: false, outline: false, glow: HOT_GLOW });
    this.materials[Variant.HotBlend] = paletteMaterial(p, { lit: true, transparent: true, outline: false, glow: HOT_BLEND_GLOW });
    this.materials[Variant.RemasterGround] = remasterGroundMaterial(p, this.remasterAtlas); // [bg-remaster]
    this.materials[Variant.GroundBlend] = groundTileMaterial(p, this.atlas, BLEND_ALPHA);
    this.materials[Variant.RemasterGroundBlend] = remasterGroundMaterial(p, this.remasterAtlas, undefined, BLEND_ALPHA);
    for (let v = 0; v <= Variant.RemasterGroundBlend; v++) this.pools.push(new Map());
    this.artLayer = new SpriteArtLayer(p);
    this.root.add(this.artLayer.root);
    this.setVfxMode(vfxModeFromSearch());
  }

  /** The shot and explosion look: the original sprites, or the remastered effects (D35). */
  get vfxMode(): VfxMode {
    return this.vfx;
  }

  setVfxMode(mode: VfxMode): void {
    if (mode === this.vfx) return;
    this.vfx = mode;
    this.fx?.dispose();
    this.fx = mode === "remastered" ? new RemasteredFx(this.cache, this.palette) : null;
    if (this.fx) this.root.add(this.fx.root);
  }

  /**
   * The remastered flat sprite art (D42), from loadSpriteArt (spriteArtLayer.ts), or null. Sprites
   * it has a painting for draw flat while the sprite look is "remastered".
   */
  setSpriteArt(art: SpriteArt<THREE.Texture> | null): void {
    this.spriteArt = art;
    this.artSheets = new WeakMap();
  }

  /**
   * The sprite art while it loads (loadSpriteArt's promise): preloadLevel waits for it and its
   * atlases, so shots and pickups are flat from the level's first tick rather than turning flat
   * when the art arrives.
   */
  setSpriteArtLoading(loading: Promise<SpriteArt<THREE.Texture> | null>): void {
    this.artLoading = loading.then((art) => art?.loaded).catch(() => undefined);
  }

  /**
   * How shots and pickups are drawn: "original" sprites, or the "remastered" flat art where it
   * exists. Undefined (the default without `?sprites=`) follows the effects look (setVfxMode).
   */
  setSpriteArtMode(mode: SpriteArtMode | undefined): void {
    this.artMode = mode;
  }

  /** The sprite look in effect. */
  get spriteArtMode(): SpriteArtMode {
    return this.artMode ?? (this.vfx === "remastered" ? "remastered" : "original");
  }

  /** Particles alive in the remastered effects (0 in the original look). */
  vfxStats(): { particles: number; spawned: number } {
    return this.fx ? this.fx.stats() : { particles: 0, spawned: 0 };
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
    this.fx?.tick(list.items, this.interp.prevX, this.interp.prevY);
    this.applyPalette(list);
    if (this.background === "remaster") {
      const palette = this.palettes[list.palette] ?? this.palettes[0];
      if (palette) this.remasterAtlas.setLuma(paletteLuma(palette));
      this.remasterAtlas.prepare(list.items, this.needsGroundAtlas);
      this.tileModels.prepare(list.items);
    }
  }

  /**
   * Whether a tile draw may need the upscaled ground atlas: not when the HD terrain has a painting of
   * it (drawHdTile's lookup), which is what draws it then. Upscaling every visible cell each tick
   * regardless was the draw list's biggest garbage source and ~25 ms of a level's first tick (D91).
   */
  private readonly needsGroundAtlas = (d: TileDraw): boolean => {
    if (this.terrain !== "hd") return true;
    let id = this.tileIds.get(d.tileId);
    if (id === undefined) this.tileIds.set(d.tileId, (id = parseTileId(d.tileId)));
    if (!id) return true;
    const tileset = this.terrainArt.get(id[0]);
    return !tileset || !tileset.tile(d.layer, id[1], d.key - d.layer * BG_KEY_LAYER);
  };

  /**
   * Draw backgrounds as the original's tiles (extruded, D8) or remastered (D34): the ground
   * upscaled, and structure tiles as models from `tileModels` (loaded with the sprite models'
   * loader on first sight; until then, and for tiles without a model, the tiles draw as before).
   */
  setBackgroundStyle(style: BackgroundStyle, tileModels: TileModelIndex = new TileModelIndex()): void {
    this.background = style;
    this.tileModels = style === "remaster" ? tileModels : new TileModelIndex([]);
    if (style === "remaster" && this.list) {
      this.remasterAtlas.prepare(this.list.items, this.needsGroundAtlas);
      this.tileModels.prepare(this.list.items);
    }
  }

  get backgroundStyle(): BackgroundStyle {
    return this.background;
  }

  /**
   * The terrain look within the remastered backgrounds (D57): "hd" draws tiles from the HD terrain
   * art where a tileset has it (loaded when its level starts, or its first tile is seen), the rest
   * as before; "original" draws them all as before. Switches at once.
   */
  setTerrainStyle(style: TerrainStyle): void {
    this.terrain = style;
    // The upscaled ground of every cell from this tick on (only the unpainted ones were prepared).
    if (this.background === "remaster" && this.list) this.remasterAtlas.prepare(this.list.items, this.needsGroundAtlas);
    setRockLook(style === "hd"); // the island rock: smooth, or the original's pixels (D84)
  }

  get terrainStyle(): TerrainStyle {
    return this.terrain;
  }

  /** Forget interpolation history (level start, teleports). */
  resetInterpolation(): void {
    this.interp.reset();
    this.fx?.reset();
  }

  get active(): boolean {
    return this.list !== null;
  }

  /**
   * Draw sprites as models (spriteModels.ts): player ships with their banking frames, grouped
   * sprites (whole enemies), and sprites drawn on their own (sidekicks). Models are fetched with
   * `loader` by preloadLevel, or the first time they're seen (see objectLook for what's drawn
   * meanwhile). Models are centred on their origin, forward -Z.
   */
  setSpriteModels(models: SpriteModels, loader: ModelLoader): void {
    // The island rock's HD materials (D84) take their colours from this renderer's palette.
    this.loader = (name) => loader(name).then((model) => adoptRockMaterials(model, this.palette));
    this.router = new Sprite2Router(models);
    if (this.damage !== null) this.router.setDamage([]);
    for (const o of models.banked) this.modelPool(o.model);
  }

  /**
   * The models a level can show, earliest needed first: those of the sprites it can draw
   * (sim/levelSprites.ts: its enemies' frames, damaged frames and launched enemies, the players'
   * ships and sidekicks) and, in the remastered backgrounds, the structure models of its tiles.
   */
  levelModels(info: LevelModelInfo): LevelModel[] {
    const out = new Map<string, LevelModel>();
    for (const r of info.sprites) {
      const name = this.router.modelFor(r.sheet, r.size, r.index, r.grouped);
      if (name === undefined) continue;
      const had = out.get(name);
      if (!had || r.time < had.time) out.set(name, { name, time: r.time, structure: false });
    }
    if (this.background === "remaster" && info.tileShapes) {
      for (const [name, time] of this.tileModels.modelsOfTiles(info.tileShapes, info.tiles ?? [])) out.set(name, { name, time, structure: true });
    }
    return [...out.values()].sort((a, b) => a.time - b.time);
  }

  /**
   * Load what a level can show before it starts (D54), so nothing pops from sprite to model during
   * play. Loads go in order of when they're needed, PRELOAD_CONCURRENCY at a time; models already
   * loaded or loading are reused. Resolves once the models needed by `waitUntil` (curLoc units;
   * default all of them) and the sprite art have finished (loaded or failed), or after `timeoutMs`,
   * whichever is first; the rest go on loading. `progress(done, total)` counts what's waited for.
   */
  async preloadLevel(
    info: LevelModelInfo,
    { progress, timeoutMs = Infinity, waitUntil = Infinity }: { progress?: (done: number, total: number) => void; timeoutMs?: number; waitUntil?: number } = {},
  ): Promise<PreloadResult> {
    const models = this.levelModels(info);
    this.setLevelDamage(info.damage);
    // The structures' own first-sight loading (preloadStructures) would fetch the whole tileset.
    if (info.tileShapes) this.preloadedShapes.add(info.tileShapes);
    const settled = new Map<string, Promise<void>>();
    const load = (m: LevelModel): Promise<void> => {
      let p = settled.get(m.name);
      if (!p) settled.set(m.name, (p = m.structure ? this.structureSettled(m.name) : this.modelPool(m.name).settled));
      return p;
    };
    // Each waited-for model's promise settles when a worker has loaded it.
    const due = models.filter((m) => m.time <= waitUntil);
    const finished = new Map<string, { promise: Promise<void>; resolve: () => void }>();
    for (const m of due) {
      let resolve!: () => void;
      const promise = new Promise<void>((r) => (resolve = r));
      finished.set(m.name, { promise, resolve });
    }
    let next = 0;
    const worker = async () => {
      while (next < models.length) {
        const m = models[next++];
        await load(m);
        finished.get(m.name)?.resolve();
      }
    };
    for (let i = 0; i < PRELOAD_CONCURRENCY; i++) void worker();

    const waits = [...[...finished.values()].map((f) => f.promise), this.artLoading];
    // The HD terrain of its tileset (D57), so the ground doesn't change look once it's playing.
    const tileset = info.tileShapes ? parseTileId(`${info.tileShapes}:0`)?.[0] : undefined;
    this.levelMaps = tileset && info.maps ? { tileset, maps: info.maps } : null;
    if (tileset && this.background === "remaster") waits.push(this.requestTerrain(tileset).then(() => undefined));
    const result: PreloadResult = { total: waits.length, done: 0, models: models.length, timedOut: false };
    progress?.(0, waits.length);
    const all = Promise.all(
      waits.map((w) =>
        w.finally(() => {
          result.done++;
          progress?.(result.done, waits.length);
        }),
      ),
    );
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = Number.isFinite(timeoutMs)
      ? new Promise<void>((resolve) => (timer = setTimeout(() => ((result.timedOut = true), resolve()), timeoutMs)))
      : new Promise<void>(() => {});
    await Promise.race([all, timeout]);
    clearTimeout(timer);
    if (result.done === result.total) result.timedOut = false;
    return result;
  }

  /**
   * Follow each player's armour (DrawList.ships, D90). Without it (the menus' and the item screen's
   * draw lists) the ships are clean; the first draw list with it snaps to it (a level's start, a
   * capture part-way in), after which the look eases.
   */
  private updateShips(dt: number): void {
    const ships = this.list?.ships;
    if (!ships || ships.length === 0) {
      for (const c of this.ships) c.reset();
      this.shipsLive = false;
      return;
    }
    const step = this.shipsLive ? dt * (this.vfxTimeScale > 0 ? 1 : 0) : Infinity;
    ships.forEach((s, i) => (this.ships[i] ??= new ShipCondition()).update(s.armor, s.reference, step));
    this.shipsLive = true;
  }

  /**
   * The level's damaged frames (sim/levelSprites.ts levelDamageFrames), so they're drawn with the
   * intact models (D87). preloadLevel sets them; call it directly when a level starts without one.
   */
  setLevelDamage(damage: readonly LevelDamage[] | undefined): void {
    if (this.damage !== null && damage) this.router.setDamage(damage);
  }

  /** Build this frame's instances. alpha interpolates from the previous tick (0) to the current (1). */
  update(alpha: number, camera: THREE.Camera): void {
    const now = performance.now();
    const dt = Math.min(0.1, (now - this.lastTime) / 1000);
    this.lastTime = now;
    this.updateShips(dt);
    this.frame++;
    const frame = this.frame;
    const items = this.items;
    const { prevX, prevY } = this.interp;
    const cam = camera.position;
    let instances = 0;
    for (const mp of this.modelPools.values()) mp.used = 0;
    const fx = this.fx;
    fx?.begin(dt * this.vfxTimeScale, camera);
    this.placedStructures.clear();
    this.structures.begin();
    this.groundStructures.length = 0;
    this.groundCells.length = 0;
    this.cover.begin();
    const art = this.spriteArt !== null && this.spriteArtMode === "remastered";
    this.artLayer.begin();
    this.terrainLevel.levelFilter.value = this.palette.screenFilter;
    this.terrainLevel.levelBrightness.value = this.palette.screenBrightness;
    this.hdTiles = 0;

    for (let i = 0; i < items.length; i++) {
      const d = items[i];
      switch (d.kind) {
        case "sprite2": {
          if (d.effect === "darken") continue; // Real shadows replace the C's shadow sprites (D9).
          const x = prevX[i] + (d.x - prevX[i]) * alpha;
          const y = prevY[i] + (d.y - prevY[i]) * alpha;
          // With flat art for the sprite (for a grouped one, the object's first tile), it's drawn flat
          // instead of as a model (D42).
          const sheetArt = art ? this.artSheet(d.sheet) : null;
          this.routeSheet = d.sheet;
          const r = this.router.route(d, sheetArt, this.emptyTile);
          // A damaged frame drawn with the intact model (D87): its damage, for the shaders.
          const damaged = r.damaged && this.damage !== null ? this.damage.state(d, r.frame) : null;
          const flat = r.route === Route.Flat;
          if (r.route === Route.Group || r.route === Route.Override || r.route === Route.Ungrouped) {
            const pool = this.modelPool(r.model);
            const look = this.objectLook(d, pool, now, frame);
            if (look === ObjectLook.Model) {
              // Only ground enemies stand on the ground's structures and hide them (D86); a ship or
              // an aircraft model flying over a wreck doesn't erase it.
              if (d.pass === Pass.GroundEnemies && d.effect !== "blend") this.cover.add(d.sheet, d.index, d.size, x, y);
              const o = r.override;
              const shift = o ? (o.shifts?.[(d.index - o.baseIndex) / o.bankStep + o.maxBank] ?? bankShift(d.sheet.id, d.sheet.data, o.baseIndex, d.index)) : 0;
              this.drawModel(r.route, pool, r.roll, shift, d, x, y, cam, dt, r.frame, damaged);
              continue;
            }
            // Held back while its model loads, or locked to its sprite (D54).
            if (look === ObjectLook.Holding) continue;
          }
          const geometry = this.cache.sprite2Geometry(d.sheet, d.index, d.size);
          if (!geometry) continue;
          const look = fx && VFX_PASSES.has(d.pass) ? fx.sprite(d, geometry, x, y, d.x - prevX[i], d.y - prevY[i]) : SpriteLook.Default;
          if (look === SpriteLook.Hidden) continue;
          if (flat && this.addFlatSprite2(sheetArt!, d, x, y, cam)) {
            instances++;
            break;
          }
          this.addSprite(geometry, d.pass, d.effect, d.filter, d.value, x, y, cam, frame, look === SpriteLook.Hot);
          instances++;
          break;
        }
        case "sprite": {
          if (d.effect === "darken") continue;
          const geometry = this.cache.tableGeometry(d.table, d.index);
          if (!geometry) continue;
          const x = prevX[i] + (d.x - prevX[i]) * alpha;
          const y = prevY[i] + (d.y - prevY[i]) * alpha;
          const look = fx && VFX_PASSES.has(d.pass) ? fx.sprite(d, geometry, x, y, d.x - prevX[i], d.y - prevY[i]) : SpriteLook.Default;
          if (look === SpriteLook.Hidden) continue;
          const tableArt = art ? this.artSheet(d.table) : null;
          const f = tableArt?.frame(d.index);
          if (tableArt && f) this.addFlat(tableArt, f, 0, 0, d.pass, d.effect, d.filter, d.value, x, y, cam);
          else this.addSprite(geometry, d.pass, d.effect, d.filter, d.value, x, y, cam, frame, look === SpriteLook.Hot);
          instances++;
          break;
        }
        case "tile": {
          const x = prevX[i] + (d.x - prevX[i]) * alpha;
          const y = prevY[i] + (d.y - prevY[i]) * alpha;
          if (d.layer === 0 && STAND_IN_IDS.has(d.tileId)) this.standInTiles.set(d.tileId, d.tile);
          if (this.background === "remaster" && this.drawRemasterTile(d, x, y, cam, frame)) {
            instances++;
            break;
          }
          if (this.background !== "remaster" && d.layer === 0 && WRECK_TILES.has(d.tileId)) {
            this.groundCells.push({ d, x, y, remaster: false }); // D86, as in drawRemasterTile
            instances++;
          } else if (this.drawOriginalTile(d, x, y, cam, frame)) instances++;
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

    // A ground structure under opaque ground-enemy sprites (a wreck under its live bunker), as far as
    // the playfield shows it, is left out, as the sprites hid its tiles (D86).
    for (const s of this.groundStructures) {
      if (!this.cover.covered(s.left, s.top, s.w, s.h)) this.structures.place(s.model, s.x, s.y, s.z, s.scale, s.neighbours);
    }
    // A wreck's ground cell under opaque enemy sprites draws without the wreck: its covered HD
    // painting, else (the pixel looks) its plain-ground stand-in or the tile with its wreck pixels
    // painted out (D86). The HD look never falls back to pixels: a covered cell with no covered
    // painting (a tree or boulder under an enemy) keeps its HD tile, as the enemy model is drawn over
    // it anyway.
    for (const c of this.groundCells) {
      const covered = this.cover.covered(c.x, c.y, TILE_WIDTH, TILE_HEIGHT);
      if (c.remaster && this.drawRemasterGround(c.d, c.x, c.y, cam, frame, covered, true, covered)) continue;
      if (c.remaster && covered && this.drawRemasterGround(c.d, c.x, c.y, cam, frame, false, true, true)) continue;
      if (covered) {
        const standIn = COVERED_STAND_IN.get(c.d.tileId);
        const standInTile = standIn === undefined ? undefined : this.standInTiles.get(standIn);
        if (standInTile) {
          this.drawOriginalTile({ ...c.d, tileId: standIn!, tile: standInTile }, c.x, c.y, cam, frame);
          continue;
        }
        let tile = this.coveredTiles.get(c.d.tileId);
        if (!tile) this.coveredTiles.set(c.d.tileId, (tile = paintOutWreck(c.d.tile)));
        this.drawOriginalTile({ ...c.d, tileId: `${c.d.tileId}#covered`, tile }, c.x, c.y, cam, frame);
      } else if (!c.remaster || !this.drawRemasterGround(c.d, c.x, c.y, cam, frame, false)) this.drawOriginalTile(c.d, c.x, c.y, cam, frame);
    }

    for (let p = 0; p < this.allPools.length; p++) this.allPools[p].commit();
    this.artLayer.end();
    fx?.end();
    for (const mp of this.modelPools.values()) {
      for (let c = mp.used; c < mp.clones.length; c++) hideClone(mp.clones[c]);
    }
    this.structures.end(this.palette.version, this.paletteColor, (h) => this.palette.screenHue.modelHue(h)); // [filters] smoothie hue
    this.atlas.flush();
    this.remasterAtlas.flush();
    this.instances = instances;
    if (frame % 300 === 0) {
      this.evictPools(frame);
      this.forgetObjects(frame);
    }
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
      structures: this.structures.stats().instances,
      flatSprites: this.artLayer.instances,
      flatCalls: this.artLayer.drawCalls,
      hdTiles: this.hdTiles,
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
        TILE_VARIANTS.has(variant) ? "instTile" : "instFx",
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
    hot = false,
  ): void {
    const blend = effect === "blend";
    const glow = GLOW_PASSES.has(pass);
    const variant = hot
      ? blend ? Variant.HotBlend : Variant.Hot
      : glow ? (blend ? Variant.GlowBlend : Variant.Glow) : blend ? Variant.LitBlend : Variant.Lit;
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

  /** A sheet's flat art (D42), or null if it has none. */
  private artSheet(sheet: { readonly id: string }): SpriteArtSheet<THREE.Texture> | null {
    let a = this.artSheets.get(sheet);
    if (a === undefined) {
      a = this.spriteArt?.sheet(sheet.id) ?? null;
      this.artSheets.set(sheet, a);
    }
    return a;
  }

  /**
   * Draw a Sprite2 draw as flat art: one quad, or a blit_sprite2x2's four. Returns false (draw it
   * as before) if a non-empty tile has no frame.
   */
  private addFlatSprite2(art: SpriteArtSheet<THREE.Texture>, d: SpriteDraw, x: number, y: number, cam: THREE.Vector3): boolean {
    if (d.size === 1) {
      const f = art.frame(d.index);
      if (!f) return false;
      this.addFlat(art, f, 0, 0, d.pass, d.effect, d.filter, d.value, x, y, cam);
      return true;
    }
    for (const [di] of SPRITE2X2_PARTS) {
      if (!art.frame(d.index + di) && this.cache.sprite2Geometry(d.sheet, d.index + di, 1) !== null) return false;
    }
    for (const [di, dx, dy] of SPRITE2X2_PARTS) {
      const f = art.frame(d.index + di);
      if (f) this.addFlat(art, f, dx, dy, d.pass, d.effect, d.filter, d.value, x, y, cam);
    }
    return true;
  }

  /** One flat art quad at the draw's place (screen (x + dx, y + dy), its pass's height). */
  private addFlat(
    art: SpriteArtSheet<THREE.Texture>, f: ReadyFrame, dx: number, dy: number, pass: Pass,
    effect: SpriteEffect, filter: number, value: number, x: number, y: number, cam: THREE.Vector3,
  ): void {
    const q = placeFlatQuad(x + dx, y + dy, f.w, f.h, passHeight(pass), cam, this.quad);
    const alpha = effect === "blend" ? BLEND_ALPHA : 1;
    if (effect === "filter") this.artLayer.add(art, pass, q, f, FxMode.Filter, (filter >> 4) & 0x0f, 0, alpha);
    else if (effect === "hv") this.artLayer.add(art, pass, q, f, FxMode.HueValue, filter & 0x0f, value, alpha);
    else this.artLayer.add(art, pass, q, f, FxMode.None, 0, 0, alpha);
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
    // Structures are opaque models; a "blend" (translucent) tile is never one (only background 2 blends).
    if (this.tileModels.size > 0) this.preloadStructures(d.tileId);
    if (d.effect === "none" && this.tileModels.has(d)) {
      const match = this.tileModels.match(d);
      if (match && this.structureShown(`${match.anchorKey}|${match.entry.model}`, match.entry.model, frame)) {
        const id = `${match.anchorKey}|${match.entry.model}`;
        if (!this.placedStructures.has(id)) {
          this.placedStructures.add(id);
          // At the pass's height, on the camera ray through its screen point, scaled to keep its
          // screen size (D6), as placeModel does for enemies.
          const h = passHeight(d.pass);
          const k = h / cam.y;
          const gx = screenWorldX(x + match.dx);
          const gz = screenWorldZ(y + match.dy);
          const px = gx + (cam.x - gx) * k, pz = gz + (cam.z - gz) * k;
          const neighbours = this.mapNeighbours(d.layer, match.anchorKey);
          if (d.layer === 0) {
            const cols = match.entry.tiles[0].length, rows = match.entry.tiles.length;
            const cx = x + match.dx - (match.entry.offset?.[0] ?? 0), cy = y + match.dy - (match.entry.offset?.[1] ?? 0);
            this.groundStructures.push({ model: match.entry.model, x: px, y: h, z: pz, scale: 1 - k, neighbours, left: cx - cols * 12, top: cy - rows * 14, w: cols * 24, h: rows * 28 });
          } else this.structures.place(match.entry.model, px, h, pz, 1 - k, neighbours);
        }
        if (!(match.entry.keepTiles ?? d.layer === 0)) return true;
        modelled = true;
        // A wreck's ground cell draws once the frame knows whether an enemy covers it (D86).
        if (d.layer === 0 && WRECK_TILES.has(d.tileId)) {
          this.groundCells.push({ d, x, y, remaster: true });
          return true;
        }
      }
    }
    return this.drawRemasterGround(d, x, y, cam, frame, false, modelled);
  }

  /**
   * The rest of drawRemasterTile: the tile from the HD terrain art (only its covered painting if
   * `covered`, D86), else (unless `hdOnly`) the upscaled ground.
   */
  private drawRemasterGround(d: TileDraw, x: number, y: number, cam: THREE.Vector3, frame: number, covered: boolean, modelled = true, hdOnly = false): boolean {
    const blend = d.layer !== 0 && d.effect === "blend";
    // HD terrain where it's painted (D57): ground, cloud sheets, and islands without a model.
    if (!modelled || d.layer === 0) {
      if (this.drawHdTile(d, x, y, cam, frame, blend, covered)) return true;
    }
    if (hdOnly) return false;
    if (d.layer !== 0 && !blend) return modelled;
    // The ground, and blended background-2 tiles (TYRIAN's ice clouds) as translucent sheets, both
    // upscaled in context.
    const pool = this.pool(this.groundGeometry, blend ? Variant.RemasterGroundBlend : Variant.RemasterGround, frame);
    if (blend) pool.mesh.renderOrder = blendSheetOrder(d.pass);
    const s = pool.next(frame);
    if (!this.remasterAtlas.place(d.key, pool.extra.array as Float32Array, s * 2)) {
      pool.count--; // No slot yet (no palette): give the instance back.
      return false;
    }
    writeMatrix(pool.mesh.instanceMatrix.array as Float32Array, s, x, y, passHeight(d.pass), 1, 1, cam);
    return true;
  }

  /** Draw a tile the original way: the ground and blended background-2 tiles as flat sheets, the rest extruded. */
  private drawOriginalTile(d: TileDraw, x: number, y: number, cam: THREE.Vector3, frame: number): boolean {
    if (d.layer === 0 || d.effect === "blend") {
      // The ground, and blended background-2 tiles as flat translucent sheets (an extruded
      // tile seen through shows its sides and doubles up at the seams).
      const blend = d.effect === "blend";
      const pool = this.pool(this.groundGeometry, blend ? Variant.GroundBlend : Variant.Ground, frame);
      if (blend) pool.mesh.renderOrder = blendSheetOrder(d.pass);
      const s = pool.next(frame);
      this.atlas.place(d.tileId, d.tile, pool.extra.array as Float32Array, s * 2);
      writeMatrix(pool.mesh.instanceMatrix.array as Float32Array, s, x, y, passHeight(d.pass), 1, 1, cam);
    } else {
      const geometry = this.cache.tileGeometry(d.tileId, d.tile);
      if (!geometry) return false;
      this.addSprite(geometry, d.pass, d.effect, 0, 0, x, y, cam, frame);
    }
    return true;
  }

  /**
   * Draw a tile from the HD terrain art (D57) if the look is "hd" and its tileset has a painting of
   * it that has loaded. Returns false to draw it as before. The first tile of a tileset starts its
   * art loading (preloadLevel does so earlier, and waits).
   */
  private drawHdTile(d: TileDraw, x: number, y: number, cam: THREE.Vector3, frame: number, blend: boolean, covered = false): boolean {
    if (this.terrain !== "hd") return false;
    let id = this.tileIds.get(d.tileId);
    if (id === undefined) this.tileIds.set(d.tileId, (id = parseTileId(d.tileId)));
    if (!id) return false;
    const tileset = this.terrainArt.get(id[0]);
    if (tileset === undefined) {
      void this.requestTerrain(id[0]);
      return false;
    }
    const t = covered ? tileset?.coveredTile(d.layer, id[1]) : tileset?.tile(d.layer, id[1], d.key - d.layer * BG_KEY_LAYER);
    if (!t) return false;
    const kind: TerrainKind = d.layer === 0 ? "ground" : blend ? "blend" : "cutout";
    const pool = this.hdPool(t.texture, kind, tileset!.scale, frame);
    if (blend) pool.mesh.renderOrder = blendSheetOrder(d.pass);
    const s = pool.next(frame);
    const e = pool.extra.array as Float32Array;
    e[s * 2] = t.x;
    e[s * 2 + 1] = t.y;
    writeMatrix(pool.mesh.instanceMatrix.array as Float32Array, s, x, y, passHeight(d.pass), 1, 1, cam);
    this.hdTiles++;
    return true;
  }

  /**
   * Send the current level's HD terrain atlases to the GPU now (decode, upload, mipmaps: ~85 ms
   * for TYRIAN's), so the level's first frame doesn't pay for it (D57). Called after preloadLevel
   * when the look is "hd"; a later switch to HD uploads them on its first frame instead.
   */
  uploadTerrain(renderer: THREE.WebGLRenderer): void {
    if (this.terrain !== "hd" || this.background !== "remaster" || !this.levelMaps) return;
    const tileset = this.terrainArt.get(this.levelMaps.tileset);
    if (!tileset) return;
    for (const image of tileset.images.values()) if (image) renderer.initTexture(image.texture);
  }

  /**
   * Put what the level can draw in front of the camera for its warm-up (View.warmUp, D91): a clone of
   * every loaded model, a quad of every instanced material variant, every HD terrain material of the
   * level's tileset (each kind) and a batch per sprite art atlas. Each of `states` sets the clones one
   * way they can be drawn (opaque, translucent); `end` hides it all again. The clones stay in their
   * pools for play. From now on, models that load are handed to takeLateWarm.
   */
  beginWarmUp(cam: THREE.Vector3): { states: (() => void)[]; end: () => void } {
    this.warmed = true;
    this.lateModels.length = 0;
    this.lateStructures.length = 0;
    const frame = this.frame;
    // The middle of the playfield, at the ground enemies' height.
    const x = 24 + 264 / 2, y = 184 / 2, h = passHeight(Pass.GroundEnemies);
    const k = h / cam.y;
    const gx = screenWorldX(x), gz = screenWorldZ(y);
    const clones: ModelClone[] = [];
    for (const pool of this.modelPools.values()) {
      if (!pool.source) continue;
      if (pool.clones.length === 0) pool.clones.push(this.cloneModel(pool.source));
      const c = pool.clones[0];
      c.object.visible = true;
      c.object.matrixWorldAutoUpdate = true;
      c.object.position.set(gx + (cam.x - gx) * k, h, gz + (cam.z - gz) * k);
      c.object.scale.setScalar(1 - k);
      clones.push(c);
    }
    const pools: Pool[] = [];
    const quad = (pool: Pool) => {
      const s = pool.next(frame);
      writeMatrix(pool.mesh.instanceMatrix.array as Float32Array, s, x - 12, y - 14, h, 1, 1, cam);
      (pool.extra.array as Float32Array).fill(0, s * pool.extra.itemSize, (s + 1) * pool.extra.itemSize);
      pool.commit();
      pools.push(pool);
    };
    for (let v = 0; v <= Variant.RemasterGroundBlend; v++) quad(this.pool(TILE_VARIANTS.has(v) ? this.groundGeometry : this.unitQuad, v, frame));
    const tileset = this.levelMaps && this.background === "remaster" && this.terrain === "hd" ? this.terrainArt.get(this.levelMaps.tileset) : null;
    if (tileset) {
      for (const image of tileset.images.values()) {
        if (image) for (const kind of ["ground", "cutout", "blend"] as const) quad(this.hdPool(image.texture, kind, tileset.scale, frame));
      }
    }
    if (this.spriteArt) for (const sheet of this.spriteArt.sheets.values()) if (sheet.texture) this.artLayer.warm(sheet as SpriteArtSheet<THREE.Texture>);
    return {
      states: [() => clones.forEach((c) => this.setCloneBlended(c, false)), () => clones.forEach((c) => this.setCloneBlended(c, true))],
      end: () => {
        for (const c of clones) {
          this.setCloneBlended(c, false);
          hideClone(c);
        }
        for (const p of pools) {
          p.mesh.count = 0;
          p.mesh.visible = false;
        }
      },
    };
  }

  /**
   * What has loaded since the level's warm-up (D91), for View to compile and upload a little at a
   * time before it's drawn: a (hidden) clone of each new model, and each new structure's instanced
   * meshes.
   */
  takeLateWarm(): THREE.Object3D[] {
    const objects: THREE.Object3D[] = [];
    for (const pool of this.lateModels) {
      if (!pool.source) continue;
      if (pool.clones.length === 0) pool.clones.push(this.cloneModel(pool.source));
      hideClone(pool.clones[0]);
      objects.push(pool.clones[0].object);
    }
    this.lateModels.length = 0;
    for (const name of this.lateStructures) objects.push(...this.structures.meshes(name));
    this.lateStructures.length = 0;
    return objects;
  }

  /**
   * Send the flat sprite art's atlases (shots, pickups, explosions: D42) to the GPU now. Uploaded on
   * their first draw instead, mid-level, each cost a frame 18-30 ms (newsh6's 832x4096 at the first
   * explosion; decode, upload, mipmaps). The same atlases serve every level, so after the first
   * level's preload this does nothing (initTexture skips an uploaded texture).
   */
  uploadSpriteArt(renderer: THREE.WebGLRenderer): void {
    if (!this.spriteArt) return;
    for (const sheet of this.spriteArt.sheets.values()) if (sheet.texture) renderer.initTexture(sheet.texture);
  }

  /**
   * The tiles on the level's map left of, right of, above and below a cell of a structure whose
   * pattern's top-left cell is `anchorKey` (-1: none or off the map), so the island rock of each
   * cell can draw its edge band for each (D84).
   */
  private mapNeighbours(layer: 0 | 1 | 2, anchorKey: number): ((row: number, col: number) => number[]) | undefined {
    if (!this.levelMaps) return undefined;
    const map = this.levelMaps.maps[layer];
    const { width } = MAP_SIZES[layer];
    const anchor = anchorKey - layer * BG_KEY_LAYER;
    return (row, col) => {
      const i = anchor + row * width + col;
      const x = i % width;
      const at = (j: number, ok: boolean) => (ok && j >= 0 && j < map.length ? map[j] : -1);
      return [at(i - 1, x > 0), at(i + 1, x < width - 1), at(i - width, true), at(i + width, true)];
    };
  }

  /** Load a tileset's HD terrain art (once), and give it the level's maps for its variants. */
  private requestTerrain(name: string): Promise<TerrainTileset<THREE.Texture> | null> {
    return this.terrainArt.request(name).then((t) => {
      if (t) {
        const maps = this.levelMaps?.tileset === name ? this.levelMaps.maps : undefined;
        for (const layer of [0, 1, 2] as const) t.setMap(layer, maps ? { width: MAP_SIZES[layer].width, tiles: maps[layer] } : undefined);
      }
      return t;
    });
  }

  /** The pool of HD terrain quads for one atlas and kind. */
  private hdPool(texture: THREE.Texture, kind: TerrainKind, scale: number, frame: number): Pool {
    const key = `${texture.uuid}|${kind}`;
    let m = this.hdMaterials.get(key);
    if (!m) {
      m = {
        material: terrainMaterial(this.palette, texture, this.terrainLevel, { kind, scale, blend: BLEND_ALPHA }),
        depth: kind === "cutout" ? terrainDepthMaterial(texture, scale) : undefined,
      };
      this.hdMaterials.set(key, m);
    }
    let pool = this.hdPools.get(m.material);
    if (!pool) {
      pool = new Pool(this.groundGeometry, m.material, "instTile", this.root, { cast: kind === "cutout", receive: true }, 16, m.depth);
      pool.lastUsed = frame;
      this.hdPools.set(m.material, pool);
      this.allPools.push(pool);
    }
    return pool;
  }

  /**
   * Whether structure `id` (its anchor and model) is drawn as its model: decided when it first comes
   * into view, by whether the model has loaded, and kept while it stays in view (D54), so a
   * structure never pops from its tiles into its model. Starts the model's load if need be.
   */
  private structureShown(id: string, model: string, frame: number): boolean {
    let st = this.structureLooks.get(id);
    if (!st) this.structureLooks.set(id, (st = { model: this.structureLoaded(model), seen: frame }));
    st.seen = frame;
    return st.model;
  }

  /** Start loading every structure model of a tileset the first time one of its tiles is drawn. */
  private preloadStructures(tileId: string): void {
    const shapes = tileId.slice(0, tileId.indexOf(":"));
    if (this.preloadedShapes.has(shapes)) return;
    this.preloadedShapes.add(shapes);
    for (const model of this.tileModels.models(shapes)) this.structureLoaded(model);
  }

  /** Whether a structure model has loaded, starting its load the first time it's asked for. */
  private structureLoaded(name: string): boolean {
    if (this.structures.has(name)) return true;
    this.structureSettled(name);
    return false;
  }

  /**
   * Whether the object draw `d` belongs to is drawn as its model (whose pool is `pool`), held back,
   * or as its sprite (D54). The first time an object needs a model: the model if it has loaded;
   * held back for up to HOLD_MS if it's loading; else (or once the hold runs out) the sprite, for
   * the object's life. An object locked to its model whose next frame's model isn't there yet
   * (preloadLevel loads them all, so only if it wasn't asked for) is held back for that frame.
   * Draws without a key (never for enemies, ships or sidekicks) aren't remembered.
   */
  private objectLook(d: SpriteDraw, pool: ModelPool, now: number, frame: number): ObjectLook {
    const key = objectKey(d);
    let o = key === null ? undefined : this.objects.get(key);
    if (o === undefined) {
      const look = pool.source ? ObjectLook.Model : pool.failed ? ObjectLook.Sprite : ObjectLook.Holding;
      o = { look, since: now, seen: frame };
      if (key !== null) this.objects.set(key, o);
    }
    o.seen = frame;
    if (o.look === ObjectLook.Holding) {
      if (pool.source) o.look = ObjectLook.Model;
      else if (pool.failed || now - o.since > HOLD_MS) o.look = ObjectLook.Sprite;
    }
    if (o.look === ObjectLook.Model && !pool.source) return pool.failed ? ObjectLook.Sprite : ObjectLook.Holding;
    return o.look;
  }

  /** Forget objects not drawn for a while (their keys are never reused: enemy serials, players). */
  private forgetObjects(frame: number): void {
    for (const [key, o] of this.objects) if (frame - o.seen > 120) this.objects.delete(key);
    for (const [id, st] of this.structureLooks) if (frame - st.seen > 120) this.structureLooks.delete(id);
  }

  /** A structure model's load (started if it hasn't been), settling when loaded or failed. */
  private structureSettled(name: string): Promise<void> {
    let load = this.structureLoads.get(name);
    if (!load) {
      load = this.loader
        ? this.loader(name).then(
            (model) => {
              this.structures.add(name, model);
              if (this.warmed) this.lateStructures.push(name);
            },
            (err) => console.error(`structure model ${name} failed to load; its tiles stay as they were`, err),
          )
        : Promise.resolve();
      this.structureLoads.set(name, load);
    }
    return load;
  }

  /**
   * Draw a sprite as its loaded model (sprite2Route.ts): a player ship's frame (Override) at the
   * sprite's centre, rolled by its banking frame's roll and moved `shift` game pixels sideways to where
   * the frame's sprite sits (bankShift.ts, D62, or the entry's fitted shift, D93); a tile of a grouped object, an enemy (Group), whose model
   * goes at the object's centre on its first tile while the other tiles draw nothing; or a sprite
   * drawn on its own, a sidekick (Ungrouped), centred on the sprite and showing the frame drawn.
   */
  private drawModel(route: Route, pool: ModelPool, roll: number, shift: number, d: SpriteDraw, x: number, y: number, cam: THREE.Vector3, dt: number, frame: number, damaged: DamageState | null): void {
    let clone: ModelClone;
    if (route === Route.Override) {
      clone = this.placeModel(pool, x + (d.size * 12) / 2, y + (d.size * 14) / 2, d, cam);
      // Eased with the roll, so the two move together. Along X at the model's scale, which keeps it
      // on the camera ray through the shifted screen point (D6).
      clone.shift += (shift - clone.shift) * Math.min(1, dt * ROLL_RATE);
      clone.object.position.x += (clone.shift / PX_PER_UNIT) * clone.object.scale.x;
    } else if (route === Route.Ungrouped) {
      this.placeModel(pool, x + d.size * 6, y + d.size * 7, d, cam, d.index);
      return;
    } else {
      if (!d.groupFirst) return;
      clone = this.placeModel(pool, x + d.groupDx, y + d.groupDy, d, cam, frame);
      // [two-player] a grouped ship that banks (the dragonwing) rolls as the player ships do
      if (Number.isNaN(roll)) {
        this.damage?.apply(clone.object, clone.materials, damaged);
        return;
      }
    }
    // Banking eases per display frame, so the 5 sprite frames become a smooth roll.
    clone.roll += (-roll - clone.roll) * Math.min(1, dt * ROLL_RATE);
    clone.object.rotation.z = clone.roll;
    // A player ship's wear by its armour (D90), after the roll so the scorch rolls with the ship.
    const player = playerOfKey(d.key);
    if (player >= 0) this.damage?.applyShip(clone.object, clone.materials, this.ships[player] ?? null, route === Route.Group ? d.groupSize : d.size);
  }

  /** The pool for a model, starting its load the first time it's asked for. */
  private modelPool(name: string): ModelPool {
    let pool = this.modelPools.get(name);
    if (!pool) {
      const created: ModelPool = { name, source: null, failed: false, settled: Promise.resolve(), clones: [], used: 0 };
      this.modelPools.set(name, (pool = created));
      if (this.loader) {
        created.settled = this.loader(name).then(
          (model) => {
            created.source ??= model;
            if (this.warmed) this.lateModels.push(created);
          },
          (err) => {
            created.failed = true;
            console.error(`model ${name} failed to load; its sprites stay extruded`, err);
          },
        );
      } else created.failed = true;
    }
    return pool;
  }

  /**
   * Show the pool's next clone with its origin at screen point (cx, cy) on the draw's pass, at the
   * size the sprite had on screen (D6), translucent for the "blend" effect and with the enemy
   * hit-flash hue for "filter". `frame` is the sprite frame drawn, for models that animate (D17).
   */
  private placeModel(pool: ModelPool, cx: number, cy: number, d: SpriteDraw, cam: THREE.Vector3, frame = -1): ModelClone {
    if (pool.used === pool.clones.length) pool.clones.push(this.cloneModel(pool.source!));
    const clone = pool.clones[pool.used++];
    const { object } = clone;
    object.visible = true;
    object.matrixWorldAutoUpdate = true;
    const h = passHeight(d.pass);
    const k = h / cam.y;
    const gx = screenWorldX(cx);
    const gz = screenWorldZ(cy);
    object.position.set(gx + (cam.x - gx) * k, h, gz + (cam.z - gz) * k);
    object.scale.set(1 - k, (1 - k) * this.modelHeight, 1 - k);

    this.setCloneBlended(clone, d.effect === "blend");

    // blit_sprite2_filter draws (filter & 0xf0) | (index & 0x0f): the same shade in another hue.
    // [filters] A smoothie's hue covers that, as its filter runs after the draw (screenHue.ts).
    const screenHue = this.palette.screenHue.modelHue(h);
    const hue = screenHue >= 0 ? screenHue : d.effect === "filter" ? d.filter & 0xf0 : -1;
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

  /** Draw a clone translucent (the C's "blend": an invulnerable ship) or opaque. */
  private setCloneBlended(clone: ModelClone, blended: boolean): void {
    const { object } = clone;
    if (blended !== clone.blended) {
      clone.blended = blended;
      setModelBlended(object, blended);
      for (const m of clone.materials) {
        // The outline shell only toggles its outline; the depth prepass is shown by setModelBlended.
        if (m.userData.depthPrepass) continue;
        if (m.userData.outlineShell) {
          (m.userData.outlineParameters as { visible?: boolean }).visible = !blended;
          continue;
        }
        m.transparent = blended || rockFades(m);
        m.opacity = blended ? BLEND_ALPHA : 1;
        m.depthWrite = !blended;
        // A translucent two-sided material is drawn by three in two passes (back faces, then front),
        // flipping its side with needsUpdate each time: every program recomputed twice a frame (~2 ms
        // with the invulnerable Talon, D91). The depth prepass already hides the far faces, so one
        // pass draws the same.
        m.forceSinglePass = blended;
        // The outline shell would show through a translucent model as a dark husk.
        const outline = (m.userData.outlineParameters ??= {}) as { visible?: boolean; opaqueVisible?: boolean };
        if (blended) {
          outline.opaqueVisible = outline.visible ?? true;
          outline.visible = false;
        } else {
          outline.visible = outline.opaqueVisible ?? true;
        }
        m.needsUpdate = true;
      }
    }
  }

  private cloneModel(source: THREE.Object3D): ModelClone {
    const object = source.clone(true);
    const materials: THREE.Material[] = [];
    object.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = castsShadow(mesh);
      mesh.receiveShadow = !isModelHelper(mesh);
      // Own materials, so one clone can turn translucent (invulnerability) without the others.
      const clone = (m: THREE.Material) => (isRockMaterial(m) ? cloneRockMaterial(m) : m.clone());
      mesh.material = Array.isArray(mesh.material) ? mesh.material.map(clone) : clone(mesh.material);
      materials.push(...(Array.isArray(mesh.material) ? mesh.material : [mesh.material]));
    });
    // Patched for damage now rather than at its first damaged frame (D91): one shader program per
    // material kind for every clone, compiled by the level's warm-up.
    this.damage?.prepare(object, materials);
    // Only the root moves (placeModel); its parts' local matrices never change (D91).
    object.traverse((o) => {
      if (o === object) return;
      o.updateMatrix();
      o.matrixAutoUpdate = false;
    });
    this.root.add(object);
    return { object, roll: 0, shift: 0, materials, rig: rigModel(object), blended: false, paletteVersion: -1, hue: -1, frame: Number.NaN };
  }

  private readonly paletteColor = (index: number, target: THREE.Color) => this.palette.color(index, target);

  private evictPools(frame: number): void {
    for (const [material, pool] of this.hdPools) {
      if (frame - pool.lastUsed > POOL_TTL_FRAMES) {
        pool.dispose();
        this.hdPools.delete(material);
        this.allPools.splice(this.allPools.indexOf(pool), 1);
      }
    }
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
 * Hide a pooled model clone, and leave it out of three's per-frame matrix update until it's shown
 * again (D91): a level keeps a clone of every model it has loaded, and walking their hidden parts
 * was the largest JS cost of a frame (~0.7 ms in the boss fight).
 */
function hideClone(c: ModelClone): void {
  c.object.visible = false;
  c.object.matrixWorldAutoUpdate = false;
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
/**
 * Draw order among translucent objects for a blended background-2 sheet: before the others (shots,
 * explosions, a flashing ship are all above it) unless it's background2over 2, drawn over everything.
 * Instanced pools all sit at the origin, so three.js's depth sort can't order them.
 */
function blendSheetOrder(pass: Pass): number {
  return pass === Pass.Background2Top ? 1 : -1;
}

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

/**
 * The player index of a player ship's draw (sim/mainint.ts playerKey: PLAYER_KEY_BASE + 100 * p, part
 * 0 the ship or its left half, 1 its right half), or -1.
 */
export function playerOfKey(key: number): number {
  const k = key - 10000;
  if (k < 0 || k >= 200) return -1;
  const part = k % 100;
  return part === 0 || part === 1 ? Math.floor(k / 100) : -1;
}
