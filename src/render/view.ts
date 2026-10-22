import * as THREE from "three";
import { OutlineEffect } from "three/addons/effects/OutlineEffect.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import type { Settings } from "../core/settings";
import type { Palette } from "../data/palette";
import { PLAYFIELD_WORLD_D, PLAYFIELD_WORLD_W, PX_PER_UNIT, worldX, worldZ } from "../game/playfield";
import type { World } from "../game/world";
import type { DrawList } from "../sim/draw";
import { DrawListRenderer } from "./drawListRenderer";

/** Camera tilt from straight down, in radians. */
const CAMERA_TILT = THREE.MathUtils.degToRad(32);
const CAMERA_FOV = 40;
/** Extra room around the playfield when fitting the camera. */
const FRAME_MARGIN = 1.08;
/** Draw-list mode frames the original's playfield exactly; this only keeps outlines off the edge. */
const DRAW_LIST_FRAME_MARGIN = 1.01;
const MAX_BANK = THREE.MathUtils.degToRad(35);
const GROUND_TILE_PX = 64;
/** Dark outline around models, echoing the sprites' black edges. Thickness is relative to screen
 * size, so it looks the same at any resolution. */
const OUTLINE = { defaultThickness: 0.0045, defaultColor: [0.07, 0.035, 0.0] };
const NO_OUTLINE = { outlineParameters: { visible: false } };
const BACKGROUND = 0x05070d;

/**
 * Draws the game. Resolution-independent: sized to the canvas, not to Tyrian's 320x200.
 *
 * Two modes. Once it has a draw list from the ported sim (setDrawList), it draws draw lists through
 * `draws` and frames exactly the original's 264x184 playfield. Until then it draws the placeholder
 * World: a grid ground and the player ship.
 */
export class View {
  readonly renderer: THREE.WebGLRenderer;
  /** The draw-list renderer: sprites, background tiles, effects. */
  readonly draws = new DrawListRenderer();
  private readonly outline: OutlineEffect;
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

  constructor(
    container: HTMLElement,
    private readonly settings: Settings,
  ) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    // Neutral keeps the palette's hues and brightness closer to the original than ACES does.
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    container.appendChild(this.renderer.domElement);
    this.outline = new OutlineEffect(this.renderer, OUTLINE);

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

    this.resize();
    window.addEventListener("resize", () => this.resize());
  }

  /** Replace the placeholder-scene ship with a loaded model. */
  setShipModel(model: THREE.Object3D): void {
    this.ship.remove(this.shipModel);
    model.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) o.castShadow = true;
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
  }

  /** Draw a frame. alpha interpolates between the last two logic ticks (0 = previous, 1 = latest). */
  render(world: World | null, alpha: number): void {
    const drawLists = this.draws.active;
    if (drawLists !== this.framedForDrawLists) {
      this.framedForDrawLists = drawLists;
      this.resize();
    }
    this.fallback.visible = !drawLists;
    if (drawLists) this.draws.update(alpha, this.camera);
    else if (world) this.updateFallback(world, alpha);
    this.outline.render(this.scene, this.camera);
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

  private resize(): void {
    const w = window.innerWidth;
    const h = window.innerHeight;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, this.settings.maxPixelRatio));
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;

    // Fit the whole playfield at any aspect ratio.
    const margin = this.framedForDrawLists ? DRAW_LIST_FRAME_MARGIN : FRAME_MARGIN;
    const halfFov = THREE.MathUtils.degToRad(CAMERA_FOV / 2);
    const halfH = Math.max(
      (PLAYFIELD_WORLD_D / 2) * Math.cos(CAMERA_TILT),
      PLAYFIELD_WORLD_W / 2 / this.camera.aspect,
    );
    const distance = (halfH * margin) / Math.tan(halfFov) + (PLAYFIELD_WORLD_D / 2) * Math.sin(CAMERA_TILT);
    this.camera.position.set(0, distance * Math.cos(CAMERA_TILT), distance * Math.sin(CAMERA_TILT));
    this.camera.lookAt(0, 0, 0);
    this.camera.updateProjectionMatrix();

    // Mask everything outside the playfield's outline on screen. Draws are projected along camera
    // rays onto their original screen positions (DECISIONS.md D6), so the area inside shows exactly
    // what the original's 264x184 window showed, at every height.
    const x = PLAYFIELD_WORLD_W / 2;
    const z = PLAYFIELD_WORLD_D / 2;
    this.camera.updateMatrixWorld();
    const hole = new THREE.Path(
      [[-x, -z], [-x, z], [x, z], [x, -z]].map(([cx, cz]) => {
        const p = new THREE.Vector3(cx, 0, cz).project(this.camera);
        return new THREE.Vector2(p.x, p.y);
      }),
    );
    const outer = new THREE.Shape([new THREE.Vector2(-2, -2), new THREE.Vector2(2, -2), new THREE.Vector2(2, 2), new THREE.Vector2(-2, 2)]);
    outer.holes.push(hole);
    this.mask.geometry.dispose();
    this.mask.geometry = new THREE.ShapeGeometry(outer);
  }
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

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
