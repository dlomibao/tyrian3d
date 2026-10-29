// The 3D scene behind the menus: the player's ship over a dark planet, in a slowly turning
// starfield. It draws with the game View's renderer (one canvas, one WebGL context) and only while
// a screen asks for it: during a level no screen is up, so it doesn't run at all.
//
// The ship is the game's own model (public/models, the colours its Blender script baked from the
// palette) with the View's lighting and outline; the planet and stars are generated here. Without
// WebGL a CSS stand-in (components.css .ui-backdrop-fallback) takes its place.
//
// Moods (BackdropMood, src/ui/screen.ts): "title" flies the ship over the planet's limb, "hangar"
// (the item screen) turns the player's current ship slowly, close up, and "space" (messages) pulls
// back to the planet. The camera eases between them.

import * as THREE from "three";
import { OutlineEffect } from "three/addons/effects/OutlineEffect.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { loadModel } from "../render/models";
import { spriteModelKey, spriteModels, type SpriteModels } from "../render/spriteModels";
import type { BackdropControl, BackdropMood } from "./screen";

/** The player ships' sprite sheet (spriteSheet9 = tyrian.shp sheet 8, whose shipGraphic indexes). */
const SHIP_SHEET = "tyrian.shp#8";
const DEFAULT_SHIP = "usp_talon";
/** The ship's length in scene units once its model is normalised. */
const SHIP_LENGTH = 2.4;
/** View's outline (src/render/view.ts), so the ship looks the same as in play. */
const OUTLINE = { defaultThickness: 0.0045, defaultColor: [0.07, 0.035, 0.0] };
const NO_OUTLINE = { outlineParameters: { visible: false } };
const PLANET_RADIUS = 400;
/** Vertical field of view on landscape screens. */
const FOV = 40;
const BACKGROUND = 0x03050a;

/**
 * The model that draws a player ship (its banked sprite at `shipGraphic` in the ship sheet, or a
 * grouped one there), or null. Pure, for tests.
 */
export function shipModelForGraphic(models: SpriteModels, shipGraphic: number): string | null {
  const banked = models.banked.find((b) => b.sheetId === SHIP_SHEET && b.baseIndex === shipGraphic);
  if (banked) return banked.model;
  return models.grouped.get(spriteModelKey(SHIP_SHEET, 2, shipGraphic)) ?? null;
}

interface Pose {
  /** Camera position and target. */
  cam: THREE.Vector3;
  look: THREE.Vector3;
  /**
   * Where the camera's target lands on screen, in normalised device coordinates (x right, y up),
   * so the ship can sit beside or above a panel. x applies on landscape screens; portrait uses
   * `frameXPortrait`.
   */
  frameX: number;
  frameXPortrait: number;
  frameY: number;
  /** On portrait screens, raise the ship by this much so it clears the panels below it. */
  liftPortrait: number;
  /** Ship heading (radians about Y; 0 points up the screen, -Z) and how fast it turns. */
  heading: number;
  spin: number;
  /** Ship scale. */
  scale: number;
}

/** Exported for tuning from the console in dev (window.tyrian.backdrop). */
export const POSES: Record<Exclude<BackdropMood, "none">, Pose> = {
  title: { cam: new THREE.Vector3(-2.2, 2.8, 7.8), look: new THREE.Vector3(0, 0, 0), frameX: 0.5, frameXPortrait: 0.15, frameY: 0.3, liftPortrait: 3.2, heading: -0.35, spin: 0, scale: 1 },
  hangar: { cam: new THREE.Vector3(0, 4.6, 4.4), look: new THREE.Vector3(0, 0, 0), frameX: -0.62, frameXPortrait: 0, frameY: 0.1, liftPortrait: 0, heading: 0, spin: 0.3, scale: 1 },
  space: { cam: new THREE.Vector3(-3.2, 2, 9.5), look: new THREE.Vector3(0, 0, 0), frameX: 0.55, frameXPortrait: 0, frameY: -0.45, liftPortrait: 0, heading: -0.35, spin: 0, scale: 1 },
};

export class Backdrop implements BackdropControl {
  private mood: BackdropMood = "none";
  private raf = 0;
  private last = 0;
  private time = 0;
  private readonly fallback: HTMLDivElement | null = null;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 2000);
  private readonly outline: OutlineEffect | null = null;
  private readonly ship = new THREE.Group();
  private readonly shipPivot = new THREE.Group();
  /** Engine glows: one per engine the model names (extras `tyrian_engines`), else one at the tail. */
  private glows: THREE.Sprite[] = [];
  private readonly planet = new THREE.Group();
  private readonly stars = new THREE.Group();
  private readonly pose: Pose = { ...POSES.title, cam: POSES.title.cam.clone(), look: POSES.title.look.clone() };
  private frameX = POSES.title.frameX;
  private lift = 0;
  private target: Pose = POSES.title;
  private spinAngle = 0;
  private shipName = "";
  private models: SpriteModels | null = null;
  private readonly size = new THREE.Vector2();

  /** @param renderer the View's renderer, or null without WebGL (then a CSS stand-in shows). */
  constructor(private readonly renderer: THREE.WebGLRenderer | null) {
    if (!renderer) {
      this.fallback = document.createElement("div");
      this.fallback.className = "ui-backdrop-fallback";
      this.fallback.hidden = true;
      document.body.prepend(this.fallback);
      return;
    }
    this.outline = new OutlineEffect(renderer, OUTLINE);
    this.scene.background = new THREE.Color(BACKGROUND);

    // View's lighting (src/render/view.ts): image-based light for metal highlights, a sky/ground
    // hemisphere and a sun, here from the upper left so the planet shows a lit limb and a night side.
    const pmrem = new THREE.PMREMGenerator(renderer);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    this.scene.environmentIntensity = 0.7;
    pmrem.dispose();
    this.scene.add(new THREE.HemisphereLight(0x9fb8ff, 0x20160c, 1.1));
    const sun = new THREE.DirectionalLight(0xfff1dc, 2.6);
    sun.position.set(-30, 26, 8);
    this.scene.add(sun);
    const rim = new THREE.DirectionalLight(0x5cd6ff, 0.9);
    rim.position.set(20, 4, -30);
    this.scene.add(rim);

    this.stars.add(starLayer(2400, 1.1, 0.75), starLayer(260, 2.2, 1));
    this.stars.add(nebula(0x2a8fb8, new THREE.Vector3(-380, 160, -480), 560), nebula(0x8a5a14, new THREE.Vector3(420, 220, -520), 380));
    this.scene.add(this.stars);

    this.planet.add(planetMesh(), atmosphere());
    this.planet.position.set(0, -PLANET_RADIUS - 34, -300);
    // Tip the poles away from the camera (their texture pinches); it spins about its own axis.
    this.planet.rotation.set(-1.25, 0, 0.3, "XZY");
    this.scene.add(this.planet);

    this.ship.add(this.shipPivot);
    this.scene.add(this.ship);
    this.setShip(DEFAULT_SHIP);
  }

  setMood(mood: BackdropMood): void {
    if (mood === this.mood) return;
    const wasRunning = this.mood !== "none";
    this.mood = mood;
    if (mood !== "none") this.target = POSES[mood];
    if (this.fallback) {
      this.fallback.hidden = mood === "none";
      return;
    }
    if (mood === "none") cancelAnimationFrame(this.raf);
    else if (!wasRunning) {
      this.last = performance.now();
      this.raf = requestAnimationFrame(this.frame);
    }
  }

  /** Show a ship model (path in public/models without .glb). Keeps the current one if it fails. */
  setShip(name: string): void {
    if (!this.renderer || name === this.shipName) return;
    this.shipName = name;
    loadModel(name)
      .then((model) => {
        if (this.shipName !== name) return;
        // Normalise the size and centre it, so every ship sits the same in the frame.
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const centre = box.getCenter(new THREE.Vector3());
        const s = SHIP_LENGTH / Math.max(size.x, size.z, 1e-3);
        model.scale.setScalar(s);
        model.position.copy(centre).multiplyScalar(-s);
        this.shipPivot.clear();
        this.shipPivot.add(model);
        this.glows = engineGlows(model, this.shipPivot, (size.z * s) / 2 + 0.1).map((g) => {
          const sprite = engineGlow(g.color, g.size, g.opacity);
          sprite.position.copy(g.position);
          return sprite;
        });
        this.shipPivot.add(...this.glows);
      })
      .catch((err) => console.warn(`backdrop: ship model ${name} failed to load`, err));
  }

  /** Show the ship drawn by sprite `shipGraphic` (items.ships[id].shipGraphic). */
  setShipGraphic(shipGraphic: number): void {
    this.models ??= spriteModels();
    const name = shipModelForGraphic(this.models, shipGraphic);
    if (name) this.setShip(name);
  }

  private readonly frame = (now: number) => {
    if (this.mood === "none" || !this.renderer || !this.outline) return;
    const dt = Math.min(0.1, (now - this.last) / 1000);
    this.last = now;
    this.time += dt;
    const t = this.time;

    // Ease toward the mood's pose.
    const k = 1 - Math.exp(-dt * 1.6);
    const p = this.pose;
    p.cam.lerp(this.target.cam, k);
    p.look.lerp(this.target.look, k);
    p.heading += (this.target.heading - p.heading) * k;
    p.scale += (this.target.scale - p.scale) * k;
    p.spin += (this.target.spin - p.spin) * k;
    p.frameY += (this.target.frameY - p.frameY) * k;
    this.spinAngle += p.spin * dt;
    if (this.target.spin === 0) this.spinAngle -= this.spinAngle * k; // unwind once it stops turning

    this.renderer.getSize(this.size);
    const { x: w, y: h } = this.size;
    const aspect = w / Math.max(1, h);
    // Landscape screens use frameX, portrait ones frameXPortrait and liftPortrait, blending between.
    const land = Math.min(1, Math.max(0, (aspect - 0.9) / 0.6));
    this.lift += ((1 - land) * this.target.liftPortrait - this.lift) * k;

    // A slow drift: the ship bobs and banks, the planet turns, the stars wheel past.
    this.ship.position.set(Math.sin(t * 0.23) * 0.25, this.lift + Math.sin(t * 0.7) * 0.12, Math.sin(t * 0.17) * 0.2);
    this.ship.rotation.set(Math.sin(t * 0.5) * 0.04, p.heading + this.spinAngle + Math.sin(t * 0.21) * 0.06, Math.sin(t * 0.4 + 1) * 0.14);
    this.ship.scale.setScalar(p.scale);
    const flicker = Math.sin(t * 31) * 0.06 + Math.sin(t * 17) * 0.05;
    for (const g of this.glows) g.material.opacity = g.userData.opacity + flicker;
    this.planet.rotation.y = t * 0.012;
    this.stars.rotation.x = t * 0.006;

    // Frame the target off centre (beside or above the panels): shift the view window.
    const fx = this.target.frameXPortrait + (this.target.frameX - this.target.frameXPortrait) * land;
    this.frameX += (fx - this.frameX) * k;
    this.camera.aspect = aspect;
    // Portrait screens (phones) keep a landscape square's width in view rather than zooming in.
    this.camera.fov = aspect < 1 ? THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(FOV / 2)) / aspect)) : FOV;
    this.camera.setViewOffset(w, h, (-this.frameX * w) / 2, (p.frameY * h) / 2, w, h);
    this.camera.position.copy(p.cam);
    this.camera.lookAt(p.look);

    this.outline.render(this.scene, this.camera);
    this.raf = requestAnimationFrame(this.frame);
  };
}

// --- generated pieces ---

/** A seeded random source, so the planet and stars are the same every visit. */
function random(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let x = Math.imul(s ^ (s >>> 15), 1 | s);
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

function starLayer(count: number, size: number, opacity: number): THREE.Points {
  const rnd = random(count);
  const pos = new Float32Array(count * 3);
  const col = new Float32Array(count * 3);
  const tints = [new THREE.Color(0xffffff), new THREE.Color(0xcfe8ff), new THREE.Color(0xffe2b0), new THREE.Color(0x9fdcff)];
  const c = new THREE.Color();
  for (let i = 0; i < count; i++) {
    // Uniform on a shell well outside the scene.
    const u = rnd() * 2 - 1;
    const a = rnd() * Math.PI * 2;
    const r = 500 + rnd() * 300;
    const q = Math.sqrt(1 - u * u);
    pos.set([Math.cos(a) * q * r, u * r, Math.sin(a) * q * r], i * 3);
    c.copy(tints[Math.floor(rnd() * tints.length)]).multiplyScalar(0.35 + rnd() * 0.65);
    col.set([c.r, c.g, c.b], i * 3);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const material = new THREE.PointsMaterial({ size: size * dpr, sizeAttenuation: false, vertexColors: true, transparent: true, opacity, depthWrite: false, map: dotTexture(), alphaTest: 0.01 });
  return new THREE.Points(geometry, material);
}

let dot: THREE.Texture | null = null;

function dotTexture(): THREE.Texture {
  if (dot) return dot;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 32;
  const g = canvas.getContext("2d")!;
  const grad = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.4, "rgba(255,255,255,0.8)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 32, 32);
  dot = new THREE.CanvasTexture(canvas);
  return dot;
}

/** A faint coloured haze far behind the scene. */
function nebula(color: number, at: THREE.Vector3, size: number): THREE.Sprite {
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTexture(), color, transparent: true, opacity: 0.09, depthWrite: false, blending: THREE.AdditiveBlending }));
  sprite.position.copy(at);
  sprite.scale.setScalar(size);
  return sprite;
}

function engineGlow(color: THREE.ColorRepresentation, size: number, opacity: number): THREE.Sprite {
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTexture(), color, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending }));
  sprite.scale.setScalar(size);
  sprite.userData.opacity = opacity;
  return sprite;
}

/** Where a glow goes behind an engine, its colour, size and base opacity. */
export interface EngineGlow {
  position: THREE.Vector3;
  color: string;
  size: number;
  opacity: number;
}

/**
 * The glows behind a ship's engines, in `pivot`'s space. A model can name its engines in the node
 * extras `tyrian_engines: { color, at: [[x, y, z], ...] }` (points in that node's space, e.g.
 * assets/blender/usp_talon.py's twin nozzles); otherwise one cyan glow sits `tail` behind the centre.
 * Pure (no sprites), for tests.
 */
export function engineGlows(model: THREE.Object3D, pivot: THREE.Object3D, tail: number): EngineGlow[] {
  let engines = null as { node: THREE.Object3D; color: string; at: number[][] } | null;
  model.traverse((o) => {
    const e = o.userData?.tyrian_engines;
    if (!engines && e && Array.isArray(e.at)) engines = { node: o, color: String(e.color ?? "#ff8a2a"), at: e.at };
  });
  if (!engines) return [{ position: new THREE.Vector3(0, 0, tail), color: "#8fe6ff", size: 0.4, opacity: 0.55 }];
  const { node, color, at } = engines;
  pivot.updateMatrixWorld(true);
  return at.map(([x, y, z]) => ({
    position: pivot.worldToLocal(node.localToWorld(new THREE.Vector3(x, y, z))),
    color,
    size: 0.26,
    opacity: 0.5,
  }));
}

/** Fractal value noise on a sphere's equirectangular map (wraps in x). */
function noiseField(w: number, h: number, seed: number, octaves: number): Float32Array {
  const rnd = random(seed);
  const grid = 64;
  const lattice = new Float32Array(grid * grid).map(() => rnd());
  const at = (x: number, y: number) => lattice[(((y % grid) + grid) % grid) * grid + (((x % grid) + grid) % grid)];
  const smooth = (t: number) => t * t * (3 - 2 * t);
  const out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      let v = 0;
      let amp = 0.5;
      let freq = 4;
      for (let o = 0; o < octaves; o++) {
        // Frequencies are whole numbers of cells across the width, so the map wraps seamlessly.
        const fx = (x / w) * freq;
        const fy = (y / h) * (freq / 2);
        const ix = Math.floor(fx);
        const iy = Math.floor(fy);
        const tx = smooth(fx - ix);
        const ty = smooth(fy - iy);
        const wrap = (i: number) => ((i % freq) + freq) % freq;
        const a = at(wrap(ix) + o * 7, iy + o * 13);
        const b = at(wrap(ix + 1) + o * 7, iy + o * 13);
        const c = at(wrap(ix) + o * 7, iy + 1 + o * 13);
        const d = at(wrap(ix + 1) + o * 7, iy + 1 + o * 13);
        v += amp * (a + (b - a) * tx + (c - a) * ty + (a - b - c + d) * tx * ty);
        amp *= 0.5;
        freq *= 2;
      }
      out[y * w + x] = v;
    }
  }
  return out;
}

/**
 * A dark rocky world in the steel and night-blue of Tyrian's palettes, with amber city lights along
 * its coasts. The lights are points, not texels, so they stay pin-sharp however close the camera is.
 */
function planetMesh(): THREE.Group {
  const w = 1024;
  const h = 512;
  const land = noiseField(w, h, 7, 6);
  const detail = noiseField(w, h, 11, 4);
  const surface = document.createElement("canvas");
  surface.width = w;
  surface.height = h;
  const img = surface.getContext("2d")!.createImageData(w, h);
  for (let i = 0; i < w * h; i++) {
    const v = land[i];
    const d = detail[i];
    const high = v > 0.52;
    // Seas near black-blue, highlands steel grey with darker ridges.
    const shade = high ? 0.55 + (v - 0.52) * 2 + (d - 0.5) * 0.3 : 0.25 + v * 0.35;
    img.data.set(high ? [Math.round(46 * shade), Math.round(56 * shade), Math.round(70 * shade), 255] : [Math.round(8 * shade), Math.round(16 * shade), Math.round(34 * shade), 255], i * 4);
  }
  surface.getContext("2d")!.putImageData(img, 0, 0);
  const map = new THREE.CanvasTexture(surface);
  map.colorSpace = THREE.SRGBColorSpace;
  map.anisotropy = 8;
  const material = new THREE.MeshStandardMaterial({ map, roughness: 0.92, metalness: 0, envMapIntensity: 0.15, userData: NO_OUTLINE });
  const group = new THREE.Group();
  group.add(new THREE.Mesh(new THREE.SphereGeometry(PLANET_RADIUS, 128, 96), material));

  // Cities: random spots on the sphere, kept where the land map is near the coast.
  const rnd = random(3);
  const pos: number[] = [];
  const col: number[] = [];
  for (let n = 0; n < 160000 && pos.length < 9000 * 3; n++) {
    const u = rnd();
    const z = rnd() * 2 - 1;
    const y = Math.floor(((1 - Math.acos(z) / Math.PI) * (h - 1)));
    const v = land[(h - 1 - y) * w + Math.floor(u * w)];
    if (Math.abs(v - 0.53) > 0.014 || rnd() > 0.6) continue;
    // SphereGeometry's mapping: u around from -X, v from the top (+Y).
    const phi = u * Math.PI * 2;
    const r = PLANET_RADIUS * 1.0015;
    const q = Math.sqrt(1 - z * z);
    pos.push(-Math.cos(phi) * q * r, z * r, Math.sin(phi) * q * r);
    const warm = 0.7 + rnd() * 0.3;
    col.push(1 * warm, (0.62 + rnd() * 0.2) * warm, 0.3 * warm);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  group.add(new THREE.Points(geometry, new THREE.PointsMaterial({ size: 1.6 * dpr, sizeAttenuation: false, vertexColors: true, transparent: true, map: dotTexture(), depthWrite: false })));
  return group;
}

/** A cyan rim of atmosphere: brightest where the surface turns away from the camera. */
function atmosphere(): THREE.Mesh {
  const material = new THREE.ShaderMaterial({
    uniforms: { color: { value: new THREE.Color(0x5cd6ff) } },
    vertexShader: /* glsl */ `
      varying vec3 vNormal;
      varying vec3 vView;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        vNormal = normalize(normalMatrix * normal);
        vView = normalize(-mv.xyz);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 color;
      varying vec3 vNormal;
      varying vec3 vView;
      void main() {
        float rim = 1.0 - max(dot(vNormal, vView), 0.0);
        gl_FragColor = vec4(color, pow(rim, 3.5) * 0.9);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    userData: NO_OUTLINE,
  });
  return new THREE.Mesh(new THREE.SphereGeometry(PLANET_RADIUS * 1.03, 96, 64), material);
}
