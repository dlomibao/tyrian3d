// Destruct in 3D: draws a DestructGame (src/destruct/sim.ts) after each tick, the way
// src/render/ draws the main game's draw list. It reads the game's state and its per-tick
// `draws` (what the C blits onto VGAScreen) and never changes them.
//
// - Terrain: destructTempScreen's dirt (palette 16-25) as a slab DEPTH px deep. Its front face is
//   one plane textured from the screen (rebuilt only when the pixels change), its top, bottom and
//   side walls are geometry built from the dirt's outline, so craters, rings and holes are real
//   holes through the slab.
// - Fire: the explosion pixels (241-255, which fade a step a tick as in the C) glow on a plane in
//   front of the slab, with a few pooled point lights at the live explosions lighting the terrain.
// - Units and walls: their sprites from newsh~.shp, extruded into rounded solids like the main
//   game's (src/render/spriteMesh.ts) and coloured from the palette.
// - Shots, trails and crosshairs: small glowing beads in the palette colours JE_pixCool and
//   DE_RunTickDrawCrosshairs use.
//
// Units and shots are interpolated between ticks, so motion is smooth at any refresh rate.

import * as THREE from "three";
import { OutlineEffect } from "three/addons/effects/OutlineEffect.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { decodeSprite2, type Palette, vga6To8 } from "../data";
import { paletteMaterial } from "../render/paletteMaterial";
import { PaletteTexture } from "../render/paletteTexture";
import { extrudeSprite, toGeometry, type ExtrudeOptions } from "../render/spriteMesh";
import { type DestructGame, SCREEN_H, SCREEN_W, WALL_SPRITE } from "./sim";

/** The slab's depth, in pixels. */
const DEPTH = 26;
/** The first row the game uses (rows 0-11 are its HUD). */
const TOP_ROW = 12;
const FIELD_H = SCREEN_H - TOP_ROW;
const CAMERA_FOV = 30;
/** The camera looks down at the field by this much. */
const CAMERA_PITCH = THREE.MathUtils.degToRad(9);
const FRAME_MARGIN = 1.04;
const BACKGROUND = 0x020308;
const OUTLINE = { defaultThickness: 0.0035, defaultColor: [0.05, 0.03, 0.0] };
const NO_OUTLINE = { outlineParameters: { visible: false } };
const UNIT_EXTRUDE: ExtrudeOptions = { maxHeight: 6, edgeHeight: 2, radius: 4, bottom: 6 };
const WALL_EXTRUDE: ExtrudeOptions = { maxHeight: 9, edgeHeight: 7, radius: 2, bottom: 9 };
const MAX_BEADS = 512;
const EXPLOSION_LIGHTS = 4;

/** Screen pixel to world: x right, y up, centred on the field. */
const wx = (px: number) => px - SCREEN_W / 2;
const wy = (py: number) => (TOP_ROW + SCREEN_H) / 2 - py;

const isDirt = (c: number) => c >= 16 && c <= 25;

export class DestructRenderer {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(CAMERA_FOV, 1, 1, 4000);
  private readonly outline: OutlineEffect;
  private readonly palette = new PaletteTexture();
  private readonly rgb = new Uint8Array(256 * 3);
  private readonly root = new THREE.Group();

  // Terrain
  private readonly frontPixels = new Uint8Array(SCREEN_W * FIELD_H * 4);
  private readonly frontTexture: THREE.DataTexture;
  private readonly glowPixels = new Uint8Array(SCREEN_W * FIELD_H * 4);
  private readonly glowTexture: THREE.DataTexture;
  private readonly walls: THREE.Mesh;
  private readonly lastScreen = new Uint8Array(SCREEN_W * SCREEN_H);
  private terrainDirty = true;
  private glowDirty = true;
  private readonly lights: THREE.PointLight[] = [];

  // Sprites
  private readonly spriteMaterial: THREE.Material;
  private readonly geometries = new Map<string, THREE.BufferGeometry | null>();
  private readonly spriteMeshes: THREE.Mesh[] = [];
  private readonly spriteGroup = new THREE.Group();

  // Beads: shots, trails and crosshairs
  private readonly beads: THREE.InstancedMesh;
  private readonly glowDots: THREE.Points;

  // Interpolation: positions at the previous and latest tick.
  private prevUnits = new Map<number, { x: number; y: number }>();
  private curUnits = new Map<number, { x: number; y: number }>();
  private prevShots = new Map<number, { x: number; y: number }>();
  private curShots = new Map<number, { x: number; y: number }>();
  private snapshot: Snapshot = { units: [], walls: [], beads: [], explosions: [] };
  private shake = 0;
  private time = 0;
  private last = performance.now();

  constructor(
    private readonly renderer: THREE.WebGLRenderer,
    palette: Palette,
    private readonly sheet: Uint8Array,
  ) {
    this.palette.set(palette, -99, 0);
    for (let i = 0; i < 768; i++) this.rgb[i] = vga6To8(palette[i]);
    this.outline = new OutlineEffect(renderer, OUTLINE);

    this.scene.background = new THREE.Color(BACKGROUND);
    const pmrem = new THREE.PMREMGenerator(renderer);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    this.scene.environmentIntensity = 0.45;
    pmrem.dispose();
    this.scene.add(new THREE.HemisphereLight(0x9fb8ff, 0x2a1c10, 1.1));
    const sun = new THREE.DirectionalLight(0xfff0dc, 2.4);
    sun.position.set(-140, 220, 260);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.bias = -0.0005;
    sun.shadow.normalBias = 0.4;
    Object.assign(sun.shadow.camera, { left: -200, right: 200, top: 140, bottom: -140, near: 10, far: 900 });
    this.scene.add(sun);
    for (let i = 0; i < EXPLOSION_LIGHTS; i++) {
      const light = new THREE.PointLight(0xff9a3a, 0, 90, 1.6);
      this.lights.push(light);
      this.scene.add(light);
    }

    this.scene.add(this.root, starfield());

    // Terrain front: the screen's dirt, lit; and the fire in front of it.
    this.frontTexture = dataTexture(this.frontPixels);
    const front = new THREE.Mesh(
      new THREE.PlaneGeometry(SCREEN_W, FIELD_H),
      new THREE.MeshStandardMaterial({ map: this.frontTexture, alphaTest: 0.5, roughness: 0.95, metalness: 0, envMapIntensity: 0.25, userData: NO_OUTLINE }),
    );
    front.position.set(0, (wy(TOP_ROW) + wy(SCREEN_H)) / 2, DEPTH / 2);
    front.receiveShadow = true;
    front.castShadow = true;
    this.root.add(front);

    this.glowTexture = dataTexture(this.glowPixels);
    this.glowTexture.magFilter = THREE.LinearFilter;
    const glow = new THREE.Mesh(
      new THREE.PlaneGeometry(SCREEN_W, FIELD_H),
      new THREE.MeshBasicMaterial({ map: this.glowTexture, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, userData: NO_OUTLINE }),
    );
    glow.position.copy(front.position).setZ(DEPTH / 2 + 1.5);
    glow.renderOrder = 2;
    this.root.add(glow);
    // A second, wider glow behind gives the fire some volume through the craters.
    const haze = glow.clone();
    haze.position.z = 0;
    haze.scale.set(1, 1, 1);
    haze.material = (glow.material as THREE.MeshBasicMaterial).clone();
    (haze.material as THREE.MeshBasicMaterial).opacity = 0.6;
    this.root.add(haze);

    this.walls = new THREE.Mesh(
      new THREE.BufferGeometry(),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0, envMapIntensity: 0.25, userData: NO_OUTLINE }),
    );
    this.walls.castShadow = true;
    this.walls.receiveShadow = true;
    this.root.add(this.walls);

    this.spriteMaterial = paletteMaterial(this.palette, { lit: true, transparent: false, outline: true, glow: 0.12 });
    this.root.add(this.spriteGroup);

    this.beads = new THREE.InstancedMesh(
      new THREE.SphereGeometry(0.75, 10, 8),
      new THREE.MeshBasicMaterial({ toneMapped: false, userData: NO_OUTLINE }),
      MAX_BEADS,
    );
    this.beads.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(MAX_BEADS * 3), 3);
    this.beads.frustumCulled = false;
    this.beads.count = 0;
    this.root.add(this.beads);

    const dotGeometry = new THREE.BufferGeometry();
    dotGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(MAX_BEADS * 3), 3));
    dotGeometry.setAttribute("color", new THREE.BufferAttribute(new Float32Array(MAX_BEADS * 3), 3));
    this.glowDots = new THREE.Points(
      dotGeometry,
      new THREE.PointsMaterial({ size: 9, vertexColors: true, map: dotTexture(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }),
    );
    this.glowDots.frustumCulled = false;
    this.root.add(this.glowDots);
  }

  /** Take the game's state after a tick. */
  tick(game: DestructGame): void {
    // The terrain changes only when its pixels do.
    const screen = game.tempScreen;
    for (let i = TOP_ROW * SCREEN_W; i < screen.length; i++) {
      const a = screen[i];
      const b = this.lastScreen[i];
      if (a === b) continue;
      if (isDirt(a) !== isDirt(b) || (isDirt(a) && a !== b)) this.terrainDirty = true;
      if (a >= 241 || b >= 241) this.glowDirty = true;
    }
    this.lastScreen.set(screen);

    [this.prevUnits, this.curUnits] = [this.curUnits, this.prevUnits];
    [this.prevShots, this.curShots] = [this.curShots, this.prevShots];
    this.curUnits.clear();
    this.curShots.clear();

    const units: Snapshot["units"] = [];
    for (const d of game.draws.units) {
      const key = d.player * 64 + d.index;
      this.curUnits.set(key, { x: d.x, y: d.y });
      units.push({ key, sprite: d.sprite, x: d.x, y: d.y });
    }
    game.shotRec.forEach((s, i) => {
      if (!s.isAvailable) this.curShots.set(i, { x: s.x, y: s.y });
    });

    const beads: Snapshot["beads"] = [];
    for (const p of game.draws.pixels) beads.push({ x: p.x, y: p.y, c: p.c, size: p.trail ? 0.65 : 1, shot: p.trail ? -1 : p.shot });
    for (const c of game.draws.crosshairs) crosshairBeads(c.x, c.y, beads);

    const explosions: Snapshot["explosions"] = [];
    for (const e of game.exploRec) if (!e.isAvailable) explosions.push({ x: e.x, y: e.y, size: e.explomax, width: e.explowidth });
    const newBig = explosions.some((e) => e.width === 3 && e.size >= 30);
    if (newBig) this.shake = Math.min(1, this.shake + 0.6);

    this.snapshot = { units, walls: game.draws.walls.slice(), beads, explosions };
  }

  /** Draw a frame; alpha interpolates between the last two ticks (0 = previous, 1 = latest). */
  render(alpha: number): void {
    const now = performance.now();
    const dt = Math.min(0.1, (now - this.last) / 1000);
    this.last = now;
    this.time += dt;

    if (this.terrainDirty) this.rebuildTerrain();
    if (this.glowDirty) this.updateGlow();

    const lerp = (a: number, b: number) => a + (b - a) * alpha;
    const snap = this.snapshot;

    // Units and walls.
    let m = 0;
    for (const u of snap.units) {
      const prev = this.prevUnits.get(u.key);
      const x = prev && Math.abs(prev.x - u.x) < 8 ? lerp(prev.x, u.x) : u.x;
      const y = prev && Math.abs(prev.y - u.y) < 8 ? lerp(prev.y, u.y) : u.y;
      m = this.placeSprite(m, u.sprite, x, y, 0, UNIT_EXTRUDE, 1.15);
    }
    for (const w of snap.walls) m = this.placeSprite(m, WALL_SPRITE, w.x, w.y, -0.5, WALL_EXTRUDE, 1);
    for (let i = m; i < this.spriteMeshes.length; i++) this.spriteMeshes[i].visible = false;

    // Beads.
    const matrix = new THREE.Matrix4();
    const color = new THREE.Color();
    const dots = this.glowDots.geometry.getAttribute("position") as THREE.BufferAttribute;
    const dotColors = this.glowDots.geometry.getAttribute("color") as THREE.BufferAttribute;
    let b = 0;
    for (const bead of snap.beads) {
      if (b >= MAX_BEADS) break;
      let x = bead.x;
      let y = bead.y;
      if (bead.shot >= 0) {
        const prev = this.prevShots.get(bead.shot);
        const cur = this.curShots.get(bead.shot);
        if (prev && cur && Math.abs(prev.x - cur.x) < 16 && Math.abs(prev.y - cur.y) < 16) {
          x += lerp(prev.x, cur.x) - cur.x;
          y += lerp(prev.y, cur.y) - cur.y;
        }
      }
      const z = bead.size < 0.5 ? DEPTH / 2 + 2 : 2;
      matrix.makeScale(bead.size, bead.size, bead.size).setPosition(wx(x + 0.5), wy(y + 0.5), z);
      this.beads.setMatrixAt(b, matrix);
      this.paletteColor(bead.c, color);
      this.beads.setColorAt(b, color);
      dots.setXYZ(b, wx(x + 0.5), wy(y + 0.5), z);
      const k = bead.size >= 1 ? 0.9 : bead.size < 0.5 ? 0.25 : 0.45;
      dotColors.setXYZ(b, color.r * k, color.g * k, color.b * k);
      b++;
    }
    this.beads.count = b;
    this.beads.instanceMatrix.needsUpdate = true;
    if (this.beads.instanceColor) this.beads.instanceColor.needsUpdate = true;
    this.glowDots.geometry.setDrawRange(0, b);
    dots.needsUpdate = true;
    dotColors.needsUpdate = true;

    // Explosion lights: the biggest live explosions.
    const lit = [...snap.explosions].sort((a, z) => z.size - a.size).slice(0, EXPLOSION_LIGHTS);
    this.lights.forEach((light, i) => {
      const e = lit[i];
      if (!e) {
        light.intensity = 0;
        return;
      }
      const life = 1 - e.width / Math.max(1, e.size);
      light.position.set(wx(e.x), wy(e.y), DEPTH / 2 + 10);
      light.distance = 30 + e.size * 2.5;
      light.intensity = 900 * (0.3 + life) * (e.size / 30);
    });

    this.frame(dt);
    this.outline.render(this.scene, this.camera);
  }

  dispose(): void {
    this.scene.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (mesh.geometry) mesh.geometry.dispose();
    });
    for (const g of this.geometries.values()) g?.dispose();
    this.frontTexture.dispose();
    this.glowTexture.dispose();
    this.palette.texture.dispose();
    this.scene.environment?.dispose();
  }

  /** Fit the field to the renderer's size, with a small shake after big explosions. */
  private frame(dt: number): void {
    const size = this.renderer.getSize(new THREE.Vector2());
    const aspect = size.x / Math.max(1, size.y);
    this.camera.aspect = aspect;
    const tan = Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV / 2));
    const halfW = (SCREEN_W / 2) * FRAME_MARGIN;
    const halfH = (FIELD_H / 2) * FRAME_MARGIN;
    const distance = Math.max(halfH / tan, halfW / (tan * aspect)) + DEPTH / 2;
    const centreY = (wy(TOP_ROW) + wy(SCREEN_H)) / 2;
    this.shake = Math.max(0, this.shake - dt * 2.5);
    const s = this.shake * this.shake * 2;
    const t = this.time;
    this.camera.position.set(Math.sin(t * 53) * s, centreY + Math.sin(CAMERA_PITCH) * distance + Math.sin(t * 61) * s, Math.cos(CAMERA_PITCH) * distance);
    this.camera.lookAt(0, centreY, 0);
    this.camera.updateProjectionMatrix();
  }

  private paletteColor(index: number, target: THREE.Color): THREE.Color {
    const o = (index & 0xff) * 3;
    return target.setRGB(this.rgb[o] / 255, this.rgb[o + 1] / 255, this.rgb[o + 2] / 255, THREE.SRGBColorSpace);
  }

  /** Show sprite `index` with its top-left at screen (x, y), centred `z` px into the slab. */
  private placeSprite(slot: number, index: number, x: number, y: number, zBias: number, opts: ExtrudeOptions, depthScale: number): number {
    const key = `${index}:${opts === WALL_EXTRUDE ? "w" : "u"}`;
    let geometry = this.geometries.get(key);
    if (geometry === undefined) {
      const data = extrudeSprite(decodeSprite2(this.sheet, index), opts);
      geometry = data ? toGeometry(data) : null;
      if (geometry) {
        const count = geometry.getAttribute("position").count;
        const fx = new Float32Array(count * 4);
        for (let i = 0; i < count; i++) fx[i * 4 + 3] = 1;
        geometry.setAttribute("instFx", new THREE.BufferAttribute(fx, 4));
        // Sprite space (x right, z down the sprite, y out of it) to world (x right, y up, z out).
        geometry.rotateX(Math.PI / 2);
        geometry.translate(0, 0, -(opts.maxHeight - opts.bottom) / 2);
      }
      this.geometries.set(key, geometry);
    }
    if (!geometry) return slot;
    let mesh = this.spriteMeshes[slot];
    if (!mesh) {
      mesh = new THREE.Mesh(geometry, this.spriteMaterial);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.spriteMeshes.push(mesh);
      this.spriteGroup.add(mesh);
    }
    mesh.geometry = geometry;
    mesh.visible = true;
    mesh.position.set(wx(x), wy(y), zBias);
    mesh.scale.set(1, 1, depthScale);
    return slot + 1;
  }

  /** The front texture and the slab's walls, from the dirt in the screen. */
  private rebuildTerrain(): void {
    this.terrainDirty = false;
    const screen = this.lastScreen;
    const front = this.frontPixels;
    // How deep under the surface each pixel is, for darker earth further down.
    const depthBelow = new Uint16Array(SCREEN_W);
    for (let y = TOP_ROW; y < SCREEN_H; y++) {
      // Texture rows go bottom-up.
      const row = (SCREEN_H - 1 - y) * SCREEN_W;
      for (let x = 0; x < SCREEN_W; x++) {
        const c = screen[y * SCREEN_W + x];
        const o = (row + x) * 4;
        if (!isDirt(c)) {
          depthBelow[x] = 0;
          front[o + 3] = 0;
          continue;
        }
        depthBelow[x]++;
        const shade = 1.08 - Math.min(0.42, depthBelow[x] * 0.006) + (hash(x, y) - 0.5) * 0.1;
        const p = c * 3;
        front[o] = clamp255(this.rgb[p] * shade);
        front[o + 1] = clamp255(this.rgb[p + 1] * shade);
        front[o + 2] = clamp255(this.rgb[p + 2] * shade);
        front[o + 3] = 255;
      }
    }
    this.frontTexture.needsUpdate = true;
    this.walls.geometry.dispose();
    this.walls.geometry = slabWalls(screen, this.rgb);
  }

  private updateGlow(): void {
    this.glowDirty = false;
    const screen = this.lastScreen;
    const glow = this.glowPixels;
    for (let y = TOP_ROW; y < SCREEN_H; y++) {
      const row = (SCREEN_H - 1 - y) * SCREEN_W;
      for (let x = 0; x < SCREEN_W; x++) {
        const c = screen[y * SCREEN_W + x];
        const o = (row + x) * 4;
        if (c < 241) {
          glow[o + 3] = 0;
          glow[o] = glow[o + 1] = glow[o + 2] = 0;
          continue;
        }
        const p = c * 3;
        glow[o] = this.rgb[p];
        glow[o + 1] = this.rgb[p + 1];
        glow[o + 2] = this.rgb[p + 2];
        glow[o + 3] = 255;
      }
    }
    this.glowTexture.needsUpdate = true;
  }
}

interface Snapshot {
  units: { key: number; sprite: number; x: number; y: number }[];
  walls: { x: number; y: number }[];
  /** shot: the shot this is the head of (for interpolation), or -1. */
  beads: { x: number; y: number; c: number; size: number; shot: number }[];
  explosions: { x: number; y: number; size: number; width: number }[];
}

/** DE_RunTickDrawCrosshairs' five pixels (clipped away from the HUD as in the C), as small beads. */
function crosshairBeads(x: number, y: number, out: Snapshot["beads"]): void {
  if (y <= 9) return;
  if (y > 11) {
    if (y > 13) out.push({ x, y: y - 2, c: 3, size: 0.45, shot: -1 });
    out.push({ x: x + 3, y, c: 3, size: 0.45, shot: -1 }, { x, y, c: 14, size: 0.45, shot: -1 }, { x: x - 3, y, c: 3, size: 0.45, shot: -1 });
  }
  out.push({ x, y: y + 2, c: 3, size: 0.45, shot: -1 });
}

/** The slab's top, bottom and side faces: every edge between dirt and air, DEPTH deep. */
function slabWalls(screen: Uint8Array, rgb: Uint8Array): THREE.BufferGeometry {
  const pos: number[] = [];
  const nrm: number[] = [];
  const col: number[] = [];
  const z0 = -DEPTH / 2;
  const z1 = DEPTH / 2;
  const solid = (x: number, y: number) => x >= 0 && x < SCREEN_W && y >= TOP_ROW && y < SCREEN_H && isDirt(screen[y * SCREEN_W + x]);
  const quad = (a: number[], b: number[], c: number[], d: number[], n: number[], k: number, colour: number) => {
    for (const v of [a, b, c, a, c, d]) {
      pos.push(v[0], v[1], v[2]);
      nrm.push(n[0], n[1], n[2]);
      const p = colour * 3;
      col.push(srgbToLinear((rgb[p] / 255) * k), srgbToLinear((rgb[p + 1] / 255) * k), srgbToLinear((rgb[p + 2] / 255) * k));
    }
  };

  // Top and bottom faces: runs along each row.
  for (let y = TOP_ROW; y < SCREEN_H; y++) {
    for (const up of [true, false]) {
      let x = 0;
      while (x < SCREEN_W) {
        const exposed = (xx: number) => solid(xx, y) && !solid(xx, up ? y - 1 : y + 1);
        if (!exposed(x)) {
          x++;
          continue;
        }
        const c = screen[y * SCREEN_W + x];
        const start = x;
        while (x < SCREEN_W && exposed(x) && screen[y * SCREEN_W + x] === c) x++;
        const X0 = wx(start);
        const X1 = wx(x);
        if (up) {
          const Y = wy(y);
          quad([X0, Y, z1], [X1, Y, z1], [X1, Y, z0], [X0, Y, z0], [0, 1, 0], 1.12, c);
        } else {
          const Y = wy(y + 1);
          quad([X0, Y, z0], [X1, Y, z0], [X1, Y, z1], [X0, Y, z1], [0, -1, 0], 0.6, c);
        }
      }
    }
  }
  // Left and right faces: runs down each column.
  for (let x = 0; x < SCREEN_W; x++) {
    for (const left of [true, false]) {
      let y = TOP_ROW;
      while (y < SCREEN_H) {
        const exposed = (yy: number) => solid(x, yy) && !solid(left ? x - 1 : x + 1, yy);
        if (!exposed(y)) {
          y++;
          continue;
        }
        const c = screen[y * SCREEN_W + x];
        const start = y;
        while (y < SCREEN_H && exposed(y)) y++;
        const Y0 = wy(start);
        const Y1 = wy(y);
        if (left) {
          const X = wx(x);
          quad([X, Y0, z0], [X, Y1, z0], [X, Y1, z1], [X, Y0, z1], [-1, 0, 0], 0.85, c);
        } else {
          const X = wx(x + 1);
          quad([X, Y0, z1], [X, Y1, z1], [X, Y1, z0], [X, Y0, z0], [1, 0, 0], 0.85, c);
        }
      }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  return g;
}

function dataTexture(pixels: Uint8Array): THREE.DataTexture {
  const t = new THREE.DataTexture(pixels, SCREEN_W, FIELD_H, THREE.RGBAFormat, THREE.UnsignedByteType);
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = THREE.NearestFilter;
  t.minFilter = THREE.LinearFilter;
  t.generateMipmaps = false;
  t.needsUpdate = true;
  return t;
}

const clamp255 = (v: number) => (v < 0 ? 0 : v > 255 ? 255 : Math.round(v));
const srgbToLinear = (v: number) => {
  const c = Math.min(1, v);
  return c < 0.04045 ? c * 0.0773993808 : Math.pow(c * 0.9478672986 + 0.0521327014, 2.4);
};

/** A stable per-pixel noise in [0, 1). */
function hash(x: number, y: number): number {
  let h = Math.imul(x * 374761393 + y * 668265263, 1274126177);
  h ^= h >>> 13;
  h = Math.imul(h, 1103515245);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

let dot: THREE.Texture | null = null;
function dotTexture(): THREE.Texture {
  if (dot) return dot;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 32;
  const g = canvas.getContext("2d")!;
  const grad = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.35, "rgba(255,255,255,0.5)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 32, 32);
  dot = new THREE.CanvasTexture(canvas);
  return dot;
}

/** Faint stars far behind the field (the C's sky is black). */
function starfield(): THREE.Points {
  let s = 12345;
  const rnd = () => ((s = (Math.imul(s, 1103515245) + 12345) >>> 0) / 4294967296);
  const count = 900;
  const pos = new Float32Array(count * 3);
  const col = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    pos.set([(rnd() - 0.5) * 1800, (rnd() - 0.35) * 1000, -400 - rnd() * 300], i * 3);
    const k = 0.25 + rnd() * 0.6;
    col.set([k * 0.9, k * 0.95, k], i * 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  return new THREE.Points(g, new THREE.PointsMaterial({ size: 2.2, sizeAttenuation: false, vertexColors: true, map: dotTexture(), transparent: true, depthWrite: false, userData: NO_OUTLINE }));
}
