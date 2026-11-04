import * as THREE from "three";
import { OutlineEffect } from "./outlineEffect.js"; // three's, with the damage cut (D87)
import { INK_OUTLINE } from "./outlineColor";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import type { Settings } from "../core/settings";
import type { Palette } from "../data/palette";
import { PLAYFIELD_WORLD_D, PLAYFIELD_WORLD_W, PX_PER_UNIT, screenWorldX, screenWorldZ, worldX, worldZ } from "../game/playfield";
import type { World } from "../game/world";
import type { DrawList } from "../sim/draw";
import { DrawListRenderer } from "./drawListRenderer";
import { isModelHelper } from "./modelPrep";
import { ResolutionScaler } from "./resolutionScaler";
import { ScreenFilterPass } from "./screenFilters";
import { VFX_LAYER } from "./vfx/vfxMode";

/**
 * Camera tilt from straight down, in radians: Camera: Steep, the look before D61, and the tilt a
 * View starts with (the item screen's weapon preview keeps it).
 */
export const CAMERA_TILT = THREE.MathUtils.degToRad(32);
/**
 * Camera: Tilted, the game's default since D61: enough lean to show the models' sides, little enough
 * that the playfield nearly fills the HUD frame's opening (DECISIONS.md D61 has the 12-18° comparison).
 */
export const CAMERA_TILT_GENTLE = THREE.MathUtils.degToRad(15);
/**
 * Camera: Overhead (D61). Not exactly 0: lookAt straight down along the camera's up vector is
 * degenerate; a ten-millionth of a radian changes nothing on screen.
 */
export const CAMERA_TILT_OVERHEAD = 1e-7;
const CAMERA_FOV = 40;
/** Extra room around the playfield when fitting the camera. */
const FRAME_MARGIN = 1.08;
/** Draw-list mode frames the original's playfield exactly; this only keeps outlines off the edge. */
const DRAW_LIST_FRAME_MARGIN = 1.01;
const MAX_BANK = THREE.MathUtils.degToRad(35);
const GROUND_TILE_PX = 64;
/** Dark outline around models, echoing the sprites' black edges. Thickness is relative to screen
 * size, so it looks the same at any resolution. */
const OUTLINE = { defaultThickness: 0.0045, defaultColor: INK_OUTLINE };
const NO_OUTLINE = { outlineParameters: { visible: false } };
const BACKGROUND = 0x05070d;

/** Options for a view other than the game's full-window one (the item screen's weapon preview). */
export interface ViewOptions {
  /**
   * The part of the draw list's screen (game_screen pixels, D6) to frame and leave unmasked.
   * Defaults to the playfield, 264x184 at (24, 0).
   */
  frame?: { x: number; y: number; w: number; h: number };
  /** Size the canvas to its container (and follow it with a ResizeObserver) instead of the window. */
  fitContainer?: boolean;
}

/** A rectangle in CSS pixels, from the canvas's top left. */
export interface ScreenRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Draws the game. Resolution-independent: sized to the canvas, not to Tyrian's 320x200.
 *
 * Two modes. Once it has a draw list from the ported sim (setDrawList), it draws draw lists through
 * `draws` and frames exactly the original's 264x184 playfield. Until then it draws the placeholder
 * World: a grid ground and the player ship.
 */
export class View {
  readonly renderer: THREE.WebGLRenderer;
  /** Game pixels per CSS pixel across the middle of the play area (updated on resize). */
  gamePixelsPerScreenPixel = 1;
  /** The draw-list renderer: sprites, background tiles, effects. */
  readonly draws = new DrawListRenderer();
  private readonly outline: OutlineEffect;
  /** The smoothies, headlight and flip (D31), when a draw list asks for them. */
  private readonly screenFilters: ScreenFilterPass;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(CAMERA_FOV, 1, 0.1, 500);
  /**
   * A screen-space mask over everything outside the playfield's projection (see resize), drawn
   * last. A mask rather than clipping planes, because OutlineEffect's outline material ignores
   * clipping planes.
   */
  private readonly maskScene = new THREE.Scene();
  private readonly maskCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 2);
  private readonly mask = new THREE.Mesh(
    new THREE.BufferGeometry(),
    new THREE.MeshBasicMaterial({ color: BACKGROUND, toneMapped: false, depthTest: false, depthWrite: false }),
  );
  /** The placeholder scene, shown until the first draw list. */
  private readonly fallback = new THREE.Group();
  private readonly ground: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshStandardMaterial>;
  private readonly groundTexture: THREE.CanvasTexture;
  private readonly ship = new THREE.Group();
  private shipModel: THREE.Object3D;
  private roll = 0;
  private lastRender = performance.now();
  private framedForDrawLists = false;
  /** The framed area in world units (x0..x1, z0..z1); the playfield unless ViewOptions.frame. */
  private readonly frameRect: FrameRect;
  /** The camera's lean from straight down (CAMERA_TILT, or CAMERA_TILT_OVERHEAD). */
  private tilt = CAMERA_TILT;
  /** Where on the canvas the playfield goes (the HUD frame's opening, D61); null: all of it. */
  private viewport: ScreenRect | null = null;
  /** The framed area's four ground corners on screen, CSS pixels: far left, far right, near right, near left. */
  private corners: { x: number; y: number }[] = [];
  /** Dynamic resolution (D91): fewer pixels while the GPU can't hold 60 fps. */
  readonly scaler = new ResolutionScaler();
  /** The main thread's time in the last render(), for the scaler. */
  private lastRenderMs = 0;

  constructor(
    private readonly container: HTMLElement,
    private readonly settings: Settings,
    private readonly options: ViewOptions = {},
  ) {
    const f = options.frame;
    this.frameRect = f
      ? { x0: screenWorldX(f.x), x1: screenWorldX(f.x + f.w), z0: screenWorldZ(f.y), z1: screenWorldZ(f.y + f.h) }
      : PLAYFIELD_RECT;
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    // Shader error checks query every new program's logs, a stall per program on its first use; a
    // shader that fails to build is a development bug, so production skips them (D91).
    this.renderer.debug.checkShaderErrors = import.meta.env.DEV;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    // Neutral keeps the palette's hues and brightness closer to the original than ACES does.
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    container.appendChild(this.renderer.domElement);
    this.outline = new OutlineEffect(this.renderer, OUTLINE);
    this.screenFilters = new ScreenFilterPass(this.renderer, this.draws.palette);
    this.camera.layers.enable(VFX_LAYER); // [vfx] the remastered effects' particles (D35)

    // Image-based lighting so metal hulls pick up highlights like the sprites' shading.
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    this.scene.environmentIntensity = 0.7;
    pmrem.dispose();

    this.scene.background = new THREE.Color(BACKGROUND);
    this.maskScene.add(this.mask);

    this.scene.add(new THREE.HemisphereLight(0x9fb8ff, 0x20160c, 1.2));
    const sun = new THREE.DirectionalLight(0xffffff, 2.5);
    // Shadows should land a little below and right of their casters on screen, like the original's
    // ship shadow (JE_playerMovement). Draws are lifted along camera rays (DECISIONS.md D6), which by
    // itself pushes a shadow toward the bottom of the screen, so the sun shines from the left and
    // from the camera's side to cancel most of that.
    sun.position.set(-6, 20, 8.4);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.bias = -0.0004;
    sun.shadow.normalBias = 0.02;
    const s = sun.shadow.camera;
    s.left = -PLAYFIELD_WORLD_W;
    s.right = PLAYFIELD_WORLD_W;
    s.top = PLAYFIELD_WORLD_D;
    s.bottom = -PLAYFIELD_WORLD_D;
    this.scene.add(sun);

    this.scene.add(this.draws.root);
    this.scene.add(this.fallback);

    this.groundTexture = makeGridTexture();
    const groundSize = PLAYFIELD_WORLD_W * 4;
    const tiles = (groundSize * PX_PER_UNIT) / GROUND_TILE_PX;
    this.groundTexture.repeat.set(tiles, tiles);
    this.ground = new THREE.Mesh(
      new THREE.PlaneGeometry(groundSize, groundSize),
      new THREE.MeshStandardMaterial({ map: this.groundTexture, roughness: 0.9, envMapIntensity: 0.15, userData: NO_OUTLINE }),
    );
    this.ground.rotation.x = -Math.PI / 2;
    this.ground.position.y = -2;
    this.ground.receiveShadow = true;
    this.fallback.add(this.ground);

    this.fallback.add(playfieldOutline());

    this.shipModel = placeholderShip();
    this.ship.add(this.shipModel);
    this.fallback.add(this.ship);

    if (options.fitContainer) this.scaler.enabled = false; // the item screen's preview: tiny, never late
    this.resize();
    if (options.fitContainer) new ResizeObserver(() => this.resize()).observe(container);
    else window.addEventListener("resize", () => this.resize());
  }

  /** Replace the placeholder-scene ship with a loaded model. */
  setShipModel(model: THREE.Object3D): void {
    this.ship.remove(this.shipModel);
    model.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) o.castShadow = !isModelHelper(o);
    });
    this.shipModel = model;
    this.ship.add(model);
  }

  /** The palettes draw lists select from (resources.palettes). */
  setPalettes(palettes: readonly Palette[]): void {
    this.draws.setPalettes(palettes);
  }

  /** Hand over one logic tick's draws. From the first call on, the view draws only draw lists. */
  setDrawList(list: DrawList): void {
    this.draws.setDrawList(list);
    this.screenFilters.setDrawList(list);
  }

  /**
   * Compile every shader and upload every texture the level can use, before it starts (D91): its
   * loaded models (opaque and translucent), the draw list's material variants, the HD terrain's
   * and the sprite art's. Drawn the first time mid-level instead, each new variant stalled a frame
   * 20-35 ms (130-730 ms over a level's first two frames) and each new model's textures 20-45 ms.
   * The main and outline passes compile in parallel (compileAsync); one draw of a single pixel per
   * state then makes the shadow pass's programs and uploads the textures. Models that load later are
   * warmed a little each frame (warmLate).
   */
  async warmUp(): Promise<void> {
    const warm = this.draws.beginWarmUp(this.camera.position);
    try {
      for (const state of warm.states) {
        state();
        this.scene.updateMatrixWorld();
        await Promise.all([this.renderer.compileAsync(this.scene, this.camera), this.outline.compileAsync(this.scene, this.camera, this.scene)]);
        for (const t of texturesOf(this.scene)) this.renderer.initTexture(t);
        this.renderPixel();
      }
      await this.renderer.compileAsync(this.maskScene, this.maskCamera);
    } finally {
      warm.end();
    }
  }

  /** Textures of models loaded since the warm-up, uploaded one a frame (warmLate). */
  private readonly lateTextures: THREE.Texture[] = [];

  /**
   * Models and structures that loaded after the level's warm-up (they load in the background, D54):
   * compile their materials in parallel, and upload their textures one a frame, before they're due.
   */
  private warmLate(): void {
    const late = this.draws.takeLateWarm();
    if (late.length > 0) {
      // One compile for all of them (each call walks the scene for its lights).
      const root = new ObjectList(late);
      void this.renderer.compileAsync(root, this.camera, this.scene);
      void this.outline.compileAsync(root, this.camera, this.scene);
      for (const t of texturesOf(root)) if (!this.uploaded(t)) this.lateTextures.push(t);
    }
    const t = this.lateTextures.shift();
    if (t && !this.uploaded(t)) this.renderer.initTexture(t);
  }

  private uploaded(t: THREE.Texture): boolean {
    return (this.renderer.properties.get(t) as { __version?: number }).__version === t.version;
  }

  /** Draw the scene into one pixel of the canvas: as a frame does, but for its side effects (warmUp). */
  private renderPixel(): void {
    const r = this.renderer;
    r.setScissorTest(true);
    r.setScissor(0, 0, 1, 1);
    try {
      this.outline.render(this.scene, this.camera);
    } finally {
      r.setScissorTest(false);
    }
  }

  /** Draw a frame. alpha interpolates between the last two logic ticks (0 = previous, 1 = latest). */
  render(world: World | null, alpha: number): void {
    const start = performance.now();
    if (this.scaler.frame(start, this.lastRenderMs)) this.resize();
    try {
      this.renderFrame(world, alpha);
    } finally {
      this.lastRenderMs = performance.now() - start;
    }
  }

  /** Dynamic resolution on (Options → Resolution: Auto, the default) or off (Full) (D91). */
  setDynamicResolution(on: boolean): void {
    if (this.options.fitContainer) return;
    this.scaler.enabled = on;
    if (!on) this.resetResolution();
  }

  /**
   * Back to full resolution (D91), e.g. when a level ends: the menus' backdrop draws with this
   * renderer at whatever resolution the last level left.
   */
  resetResolution(): void {
    if (this.scaler.reset()) this.resize();
  }

  private renderFrame(world: World | null, alpha: number): void {
    const drawLists = this.draws.active;
    this.warmLate();
    if (drawLists !== this.framedForDrawLists) {
      this.framedForDrawLists = drawLists;
      this.resize();
    }
    this.fallback.visible = !drawLists;
    if (drawLists) this.draws.update(alpha, this.camera);
    else if (world) this.updateFallback(world, alpha);
    if (drawLists && this.screenFilters.active) {
      this.screenFilters.render(this.scene, this.camera, this.draws.root, () => this.outline.render(this.scene, this.camera), alpha);
    } else {
      this.outline.render(this.scene, this.camera);
    }
    if (drawLists && this.settings.clip) {
      const autoClear = this.renderer.autoClear;
      this.renderer.autoClear = false;
      this.renderer.render(this.maskScene, this.maskCamera);
      this.renderer.autoClear = autoClear;
    }
  }

  private updateFallback(world: World, alpha: number): void {
    const now = performance.now();
    const dt = Math.min(0.1, (now - this.lastRender) / 1000);
    this.lastRender = now;

    const p = world.player;
    this.ship.position.set(
      worldX(lerp(p.prevX, p.x, alpha)),
      0,
      worldZ(lerp(p.prevY, p.y, alpha)),
    );
    // Banking is cosmetic, so it eases per display frame rather than per logic tick.
    this.roll += (-p.bank * MAX_BANK - this.roll) * Math.min(1, dt * 10);
    this.ship.rotation.z = this.roll;

    // Scroll the ground toward the camera (+Z), in texture repeats.
    const scrollPx = lerp(world.prevScrollY, world.scrollY, alpha);
    this.groundTexture.offset.y = scrollPx / GROUND_TILE_PX;
  }

  /** Lean the camera (Options → Camera, D61); refits at once. */
  setTilt(tilt: number): void {
    if (tilt === this.tilt) return;
    this.tilt = tilt;
    this.resize();
  }

  /**
   * Fit the playfield into `rect` of the canvas (CSS pixels) rather than all of it: the HUD
   * frame's opening (D61). The canvas still covers the window; the camera's projection is shifted
   * off-axis so the playfield lands in the rectangle. null goes back to the whole canvas.
   */
  setViewport(rect: ScreenRect | null): void {
    const v = this.viewport;
    if (v === rect || (v && rect && v.x === rect.x && v.y === rect.y && v.w === rect.w && v.h === rect.h)) return;
    this.viewport = rect ? { ...rect } : null;
    this.resize();
  }

  /** The framed area's ground corners on screen (CSS pixels): far left, far right, near right, near left. */
  playfieldCorners(): readonly { x: number; y: number }[] {
    return this.corners;
  }

  private resize(): void {
    const w = this.options.fitContainer ? this.container.clientWidth : window.innerWidth;
    const h = this.options.fitContainer ? this.container.clientHeight : window.innerHeight;
    if (w <= 0 || h <= 0) return; // a hidden container: wait for the ResizeObserver
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, this.settings.maxPixelRatio) * this.scaler.scale);
    this.renderer.setSize(w, h);

    // Fit the playfield's on-screen outline to the window (or the viewport), centred, at any aspect
    // ratio (fitCamera). Inside the HUD frame the outline meets the opening's edges exactly.
    // (Draws are projected along camera rays onto their original screen positions (DECISIONS.md D6),
    // so everything drawn stays inside this outline whatever its height.)
    const vp = this.viewport && this.viewport.w > 0 && this.viewport.h > 0 ? this.viewport : null;
    const margin = vp ? 1 : this.framedForDrawLists ? DRAW_LIST_FRAME_MARGIN : FRAME_MARGIN;
    const { x0, x1, z0, z1 } = this.frameRect;
    this.camera.clearViewOffset();
    this.camera.aspect = vp ? vp.w / vp.h : w / h;
    fitCamera(this.camera, this.frameRect, this.tilt, margin);
    // The viewport: the same picture, drawn off-axis into its part of the canvas.
    if (vp) this.camera.setViewOffset(vp.w, vp.h, -vp.x, -vp.y, w, h);
    this.camera.updateProjectionMatrix();

    // Mask everything outside the playfield's outline on screen. Draws are projected along camera
    // rays onto their original screen positions (DECISIONS.md D6), so the area inside shows exactly
    // what the original's 264x184 window showed, at every height.
    this.camera.updateMatrixWorld();
    const ndc = [[x0, z0], [x1, z0], [x1, z1], [x0, z1]].map(([hx, hz]) => {
      const p = new THREE.Vector3(hx, 0, hz).project(this.camera);
      return new THREE.Vector2(p.x, p.y);
    });
    this.corners = ndc.map((p) => ({ x: ((p.x + 1) / 2) * w, y: ((1 - p.y) / 2) * h }));
    const hole = new THREE.Path(ndc);
    const outer = new THREE.Shape([new THREE.Vector2(-2, -2), new THREE.Vector2(2, -2), new THREE.Vector2(2, 2), new THREE.Vector2(-2, 2)]);
    outer.holes.push(hole);
    this.mask.geometry.dispose();
    this.mask.geometry = new THREE.ShapeGeometry(outer);

    // Game pixels per CSS pixel across the middle of the play area, for relative mouse/touch steering.
    const left = new THREE.Vector3(x0, 0, (z0 + z1) / 2).project(this.camera);
    const right = new THREE.Vector3(x1, 0, (z0 + z1) / 2).project(this.camera);
    const widthCss = ((right.x - left.x) / 2) * w;
    this.gamePixelsPerScreenPixel = widthCss > 0 ? ((x1 - x0) * PX_PER_UNIT) / widthCss : 1;
  }
}

/** A ground rectangle in world units. */
export interface FrameRect {
  x0: number;
  x1: number;
  z0: number;
  z1: number;
}

/** The game's playfield, 264x184 game pixels, in world units. */
export const PLAYFIELD_RECT: FrameRect = { x0: -PLAYFIELD_WORLD_W / 2, x1: PLAYFIELD_WORLD_W / 2, z0: -PLAYFIELD_WORLD_D / 2, z1: PLAYFIELD_WORLD_D / 2 };

/**
 * Aim `camera` (its fov and aspect set) at `rect` from `tilt` radians off straight down, so the
 * rectangle's on-screen outline fills the view, centred, with `margin` (1 = touching the edges in
 * its tighter dimension). The tilted perspective makes the near edge wider than the far one, so
 * it's solved numerically: project the four ground corners, then rescale the distance and re-aim
 * until they fill the frame. Leaves the projection matrix up to date (and any view offset cleared
 * by the caller).
 */
export function fitCamera(camera: THREE.PerspectiveCamera, rect: FrameRect, tilt: number, margin: number): void {
  const halfFov = THREE.MathUtils.degToRad(camera.fov / 2);
  const { x0, x1, z0, z1 } = rect;
  const cx = (x0 + x1) / 2;
  let distance = Math.max(z1 - z0, (x1 - x0) / camera.aspect) / (2 * Math.tan(halfFov));
  let aimZ = (z0 + z1) / 2;
  const corners = [x0, x1].flatMap((x) => [z0, z1].map((z) => new THREE.Vector3(x, 0, z)));
  const p = new THREE.Vector3();
  camera.updateProjectionMatrix();
  for (let i = 0; i < 40; i++) {
    camera.position.set(cx, distance * Math.cos(tilt), aimZ + distance * Math.sin(tilt));
    camera.lookAt(cx, 0, aimZ);
    camera.updateMatrixWorld();
    const b = projectedBounds(camera, corners, p);
    const extent = Math.max(b.maxX - b.minX, b.maxY - b.minY) / 2;
    const centreY = (b.minY + b.maxY) / 2;
    if (Math.abs(extent * margin - 1) < 1e-4 && Math.abs(centreY) < 1e-4) break;
    distance *= extent * margin;
    // Positive centreY means the outline sits high on screen: aim further up the field (-Z).
    aimZ -= centreY * distance * Math.tan(halfFov);
  }
}

function projectedBounds(camera: THREE.Camera, corners: THREE.Vector3[], p = new THREE.Vector3()) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const c of corners) {
    p.copy(c).project(camera);
    minX = Math.min(minX, p.x);
    maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y);
    maxY = Math.max(maxY, p.y);
  }
  return { minX, maxX, minY, maxY };
}

/**
 * The playfield's on-screen width over its height with the game camera at `tilt`, once fitted (the
 * width is the near edge's). A view of exactly this aspect is filled by the playfield edge to edge,
 * which is how the HUD frame sizes its opening (D61). 264/184 straight down; wider when tilted.
 */
export function playfieldScreenAspect(tilt: number, rect: FrameRect = PLAYFIELD_RECT): number {
  const camera = new THREE.PerspectiveCamera(CAMERA_FOV, (rect.x1 - rect.x0) / (rect.z1 - rect.z0), 0.1, 500);
  const corners = [rect.x0, rect.x1].flatMap((x) => [rect.z0, rect.z1].map((z) => new THREE.Vector3(x, 0, z)));
  for (let i = 0; i < 8; i++) {
    fitCamera(camera, rect, tilt, 1);
    const b = projectedBounds(camera, corners);
    const next = (camera.aspect * (b.maxX - b.minX)) / (b.maxY - b.minY);
    if (Math.abs(next - camera.aspect) < 1e-6) break;
    camera.aspect = next;
  }
  return camera.aspect;
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/**
 * Objects that stay where they are in the scene, walked as one root by WebGLRenderer.compile and
 * OutlineEffect.compileAsync (which only traverse it); it has no lights of its own.
 */
class ObjectList extends THREE.Object3D {
  constructor(private readonly list: readonly THREE.Object3D[]) {
    super();
  }

  override traverse(callback: (object: THREE.Object3D) => void): void {
    for (const o of this.list) o.traverse(callback);
  }

  override traverseVisible(): void {}
}

/** Every texture the materials under `root` use (their texture properties and shader uniforms). */
function texturesOf(root: THREE.Object3D): Set<THREE.Texture> {
  const out = new Set<THREE.Texture>();
  const add = (v: unknown) => {
    if ((v as THREE.Texture | null)?.isTexture) out.add(v as THREE.Texture);
  };
  root.traverse((o) => {
    const m = (o as THREE.Mesh).material;
    if (!m) return;
    for (const mat of Array.isArray(m) ? m : [m]) {
      for (const v of Object.values(mat)) add(v);
      const uniforms = (mat as THREE.ShaderMaterial).uniforms;
      if (uniforms) for (const u of Object.values(uniforms)) add(u?.value);
    }
  });
  return out;
}

function makeGridTexture(): THREE.CanvasTexture {
  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const g = canvas.getContext("2d")!;
  g.fillStyle = "#1b2433";
  g.fillRect(0, 0, size, size);
  g.strokeStyle = "#3d5a80";
  g.lineWidth = 4;
  g.strokeRect(0, 0, size, size);
  g.strokeStyle = "#2a3a52";
  g.lineWidth = 2;
  g.beginPath();
  g.moveTo(size / 2, 0);
  g.lineTo(size / 2, size);
  g.moveTo(0, size / 2);
  g.lineTo(size, size / 2);
  g.stroke();
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

function playfieldOutline(): THREE.LineLoop {
  const x = PLAYFIELD_WORLD_W / 2;
  const z = PLAYFIELD_WORLD_D / 2;
  const geometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(-x, 0, -z),
    new THREE.Vector3(x, 0, -z),
    new THREE.Vector3(x, 0, z),
    new THREE.Vector3(-x, 0, z),
  ]);
  return new THREE.LineLoop(geometry, new THREE.LineBasicMaterial({ color: 0x7fa7e0, transparent: true, opacity: 0.8, userData: NO_OUTLINE }));
}

/** Stand-in ship until the Blender model loads: a cone pointing forward (-Z). */
function placeholderShip(): THREE.Object3D {
  const mesh = new THREE.Mesh(
    new THREE.ConeGeometry(0.8, 2, 8),
    new THREE.MeshStandardMaterial({ color: 0xc0c8d8, metalness: 0.4, roughness: 0.4 }),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.castShadow = true;
  return mesh;
}
