// Model viewer: `?viewer` (or `?viewer=<model name>`) shows each Blender model that replaces sprites
// (src/render/spriteModels/) beside the sprite it replaces. Multi-piece objects (bosses and big
// structures, src/viewer/assemblies.json) are listed too, each shown whole: every piece's sprite and
// model in place. The model can be rotated freely
// (drag), zoomed (wheel or pinch) and panned (right drag or two fingers). "Top" looks straight down
// at the sprite's scale, where the sprite can be laid over the model to compare outlines. Colours
// come from a game palette by index, as in game (pal_<index> materials, DECISIONS.md D15).
//
// Keys: up/down or j/k pick the model, left/right the frame, t top, g game angle, f free, o overlay.
// Loaded by dynamic import, so it stays out of the game's bundle.

import "./viewer.css";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OutlineEffect } from "three/addons/effects/OutlineEffect.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { filesFromZip, loadDevFiles, type FileMap } from "../assets/files";
import { loadStoredZip } from "../assets/store";
import { vga6To8, type Palette } from "../data/palette";
import { PaletteTexture } from "../render/paletteTexture";
import { SPRITE_MODELS, spriteModelKey, spriteModels, type SpriteModelEntry } from "../render/spriteModels";
import { buildResources } from "../sim/resources";
import type { Resources } from "../sim/state";
import assemblyLayouts from "./assemblies.json";
import { assemblyFrame, composeFrame, entryFrames, type AssemblyLayout, type SpriteFrame } from "./spriteFrames";

/** The in-level palette (JE_main sets pcxpal[3 - 1]). */
const LEVEL_PALETTE = 5;
/** The enemy hit flash's hue (blit_sprite2_filter), for the Flash toggle. */
const FLASH_HUE = 0x70;
/** The game's model outline (src/render/view.ts OUTLINE). */
const OUTLINE = { defaultThickness: 0.0045, defaultColor: [0.07, 0.035, 0.0] };
const PALETTE_MATERIAL = /^pal_(\d+)/;
/** Sprite pixels per Blender unit (assets/blender/README.md). */
const PX_PER_UNIT = 12;

type CameraMode = "free" | "top" | "game";

interface Item {
  name: string;
  kind: "ship" | "enemy" | "assembly";
  frames: SpriteFrame[];
  /** The sheets its sprites come from. */
  sheets: string[];
  /** A single model's entry, or an assembly's layout. */
  entry?: SpriteModelEntry;
  layout?: AssemblyLayout;
}

interface Loaded {
  root: THREE.Object3D;
  /** pal_ materials and their palette index. */
  paletteMaterials: { material: THREE.MeshStandardMaterial; index: number; emissive: boolean }[];
  materials: THREE.Material[];
  triangles: number;
  bytes: number;
  /** Assembly pieces with no model. */
  missing: number;
  size: THREE.Vector3;
  minY: number;
}

const naturalOrder = (a: string, b: string) => a.localeCompare(b, undefined, { numeric: true });

const KIND_ORDER = { ship: 0, assembly: 1, enemy: 2 };

function catalogue(): Item[] {
  const items: Item[] = SPRITE_MODELS.map((entry) => ({
    entry,
    name: entry.model.split("/").pop()!,
    kind: entry.model.startsWith("enemies/") ? "enemy" : "ship",
    frames: entryFrames(entry),
    sheets: [...new Set(entry.sprites.map((s) => s.sheet))],
  }));
  for (const layout of assemblyLayouts as AssemblyLayout[]) {
    items.push({ name: layout.name, kind: "assembly", layout, frames: [assemblyFrame(layout)], sheets: [...new Set(layout.pieces.map((p) => p.sheet))] });
  }
  return items.sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind] || naturalOrder(a.name, b.name));
}

/** The game data, if it's available without asking: the dev server's, or the cached zip. */
async function quietFiles(): Promise<FileMap | null> {
  const dev = await loadDevFiles();
  if (dev) return dev;
  const stored = await loadStoredZip();
  if (!stored) return null;
  try {
    return await filesFromZip(stored);
  } catch {
    return null;
  }
}

export async function runModelViewer(): Promise<void> {
  const items = catalogue();
  const params = new URLSearchParams(location.search);
  document.title = "Tyrian 3D: model viewer";
  document.body.classList.add("mv-page");
  document.body.innerHTML = `
    <div class="mv">
      <aside class="mv-list">
        <header>
          <h1>Models</h1>
          <input type="search" placeholder="Filter: newshf, ship, assembly…" aria-label="Filter models" />
          <p class="mv-count"></p>
        </header>
        <ul role="listbox" aria-label="Models"></ul>
      </aside>
      <main class="mv-main">
        <header class="mv-head">
          <div>
            <h2 class="mv-name"></h2>
            <p class="mv-meta"></p>
          </div>
          <div class="mv-nav">
            <button data-step="-1" title="Previous model (up or k)">‹ Prev</button>
            <button data-step="1" title="Next model (down or j)">Next ›</button>
          </div>
        </header>
        <div class="mv-panes">
          <section class="mv-pane mv-sprite-pane">
            <h3>Sprite</h3>
            <div class="mv-stage"><canvas class="mv-sprite"></canvas><p class="mv-nodata" hidden></p></div>
            <div class="mv-frames"></div>
            <label class="mv-check"><input type="checkbox" class="mv-play" /> Animate frames</label>
          </section>
          <section class="mv-pane mv-model-pane">
            <h3>Model</h3>
            <div class="mv-stage mv-gl"><canvas class="mv-model"></canvas><canvas class="mv-overlay"></canvas><p class="mv-loading" hidden>Loading…</p></div>
            <div class="mv-tools">
              <div class="mv-seg" role="group" aria-label="Camera">
                <button data-cam="free" title="Rotate freely (f)">Free</button>
                <button data-cam="top" title="Straight down at the sprite's scale (t)">Top</button>
                <button data-cam="game" title="The game camera's angle (g)">Game angle</button>
              </div>
              <label class="mv-check"><input type="checkbox" class="mv-overlay-on" /> Sprite over model (Top)</label>
              <label class="mv-range">opacity <input type="range" class="mv-overlay-alpha" min="0" max="1" step="0.05" value="0.5" /></label>
              <label class="mv-check"><input type="checkbox" class="mv-spin" /> Spin</label>
              <label class="mv-check"><input type="checkbox" class="mv-outline" checked /> Outline</label>
              <label class="mv-check"><input type="checkbox" class="mv-wire" /> Wireframe</label>
              <label class="mv-check"><input type="checkbox" class="mv-grid" checked /> Grid</label>
              <label class="mv-check"><input type="checkbox" class="mv-flash" /> Hit flash</label>
              <label class="mv-range">palette <select class="mv-palette"></select></label>
            </div>
          </section>
        </div>
      </main>
    </div>`;

  const $ = <T extends Element>(sel: string) => document.querySelector<T>(sel)!;
  const listEl = $<HTMLUListElement>(".mv-list ul");
  const filterEl = $<HTMLInputElement>(".mv-list input");
  const countEl = $<HTMLParagraphElement>(".mv-count");
  const nameEl = $<HTMLHeadingElement>(".mv-name");
  const metaEl = $<HTMLParagraphElement>(".mv-meta");
  const spriteCanvas = $<HTMLCanvasElement>(".mv-sprite");
  const noDataEl = $<HTMLParagraphElement>(".mv-nodata");
  const framesEl = $<HTMLDivElement>(".mv-frames");
  const playEl = $<HTMLInputElement>(".mv-play");
  const glStage = $<HTMLDivElement>(".mv-gl");
  const glCanvas = $<HTMLCanvasElement>(".mv-model");
  const overlayCanvas = $<HTMLCanvasElement>(".mv-overlay");
  const loadingEl = $<HTMLParagraphElement>(".mv-loading");
  const overlayOnEl = $<HTMLInputElement>(".mv-overlay-on");
  const overlayAlphaEl = $<HTMLInputElement>(".mv-overlay-alpha");
  const spinEl = $<HTMLInputElement>(".mv-spin");
  const outlineEl = $<HTMLInputElement>(".mv-outline");
  const wireEl = $<HTMLInputElement>(".mv-wire");
  const gridEl = $<HTMLInputElement>(".mv-grid");
  const flashEl = $<HTMLInputElement>(".mv-flash");
  const paletteEl = $<HTMLSelectElement>(".mv-palette");

  // --- Game data (sprites and palettes). The model side works without it. ---
  let res: Resources | null = null;
  const sheetCache = new Map<string, Uint8Array | null>();
  const sheetData = (id: string): Uint8Array | null => {
    if (!res) return null;
    if (!sheetCache.has(id)) {
      const m = /^newsh(.)\.shp$/.exec(id);
      let data: Uint8Array | null = null;
      try {
        if (m) data = res.loadCompShapes(m[1]).data;
        else {
          const sheets = [res.spriteSheet8, res.spriteSheet9, res.spriteSheet10, res.spriteSheet11, res.spriteSheet12];
          data = sheets.find((s) => s.id === id)?.data ?? null;
        }
      } catch {
        data = null;
      }
      sheetCache.set(id, data);
    }
    return sheetCache.get(id)!;
  };
  const paletteTexture = new PaletteTexture();
  let palettes: readonly Palette[] = [];

  // --- State ---
  let shown = items;
  let current = Math.max(0, items.findIndex((i) => i.name === params.get("viewer")));
  let frame = 0;
  let mode: CameraMode = "free";

  // --- Three.js ---
  const renderer = new THREE.WebGLRenderer({ canvas: glCanvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.toneMapping = THREE.NeutralToneMapping;
  const outline = new OutlineEffect(renderer, OUTLINE);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x15151b);
  scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
  scene.add(new THREE.HemisphereLight(0x9fb8ff, 0x20160c, 1.2));
  const sun = new THREE.DirectionalLight(0xffffff, 2.5);
  sun.position.set(-4, 8, 3);
  scene.add(sun);
  const grid = new THREE.GridHelper(8, 8, 0x4a4a5a, 0x2c2c38); // 1 cell = 1 unit = 12 sprite px
  scene.add(grid);

  const persp = new THREE.PerspectiveCamera(35, 1, 0.01, 200);
  const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 200);
  const perspControls = new OrbitControls(persp, glCanvas);
  const orthoControls = new OrbitControls(ortho, glCanvas);
  for (const c of [perspControls, orthoControls]) {
    c.enableDamping = true;
    c.autoRotateSpeed = 3;
  }
  const camera = () => (mode === "top" ? ortho : persp);
  const controls = () => (mode === "top" ? orthoControls : perspControls);

  const loader = new GLTFLoader();
  const glbs = new Map<string, Promise<{ scene: THREE.Object3D; bytes: number }>>();
  const built = new Map<string, Promise<Loaded>>();
  const pieceModels = spriteModels().grouped;
  let model: Loaded | null = null;

  /** A .glb from public/models/, fetched once. */
  function glb(path: string): Promise<{ scene: THREE.Object3D; bytes: number }> {
    let p = glbs.get(path);
    if (!p) {
      p = (async () => {
        const response = await fetch(`${import.meta.env.BASE_URL}models/${path}.glb`);
        if (!response.ok) throw new Error(`${path}.glb: HTTP ${response.status}`);
        const buffer = await response.arrayBuffer();
        return { scene: (await loader.parseAsync(buffer, "")).scene, bytes: buffer.byteLength };
      })();
      glbs.set(path, p);
    }
    return p;
  }

  /** The item's model: a single .glb, or an assembly's pieces each placed at its offset. */
  async function build(item: Item): Promise<Loaded> {
    let root: THREE.Object3D;
    let bytes = 0;
    let missing = 0;
    if (item.layout) {
      root = new THREE.Group();
      const paths = item.layout.pieces.map((p) => pieceModels.get(spriteModelKey(p.sheet, p.size, p.index)));
      const loaded = await Promise.all(paths.map((path) => (path ? glb(path) : null)));
      const counted = new Set<string>();
      item.layout.pieces.forEach((p, i) => {
        const piece = loaded[i];
        if (!piece) return void missing++;
        if (!counted.has(paths[i]!)) {
          counted.add(paths[i]!);
          bytes += piece.bytes;
        }
        // A piece's model is centred on the piece; sprite x right = +X, sprite y down = +Z.
        const clone = piece.scene.clone(true);
        clone.position.set(p.x / PX_PER_UNIT, 0, p.y / PX_PER_UNIT);
        root.add(clone);
      });
    } else {
      const one = await glb(item.entry!.model);
      root = one.scene;
      bytes = one.bytes;
    }
    const paletteMaterials: Loaded["paletteMaterials"] = [];
    const materials = new Set<THREE.Material>();
    let triangles = 0;
    root.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      const geo = mesh.geometry;
      triangles += (geo.index ? geo.index.count : geo.attributes.position.count) / 3;
      for (const m of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
        if (materials.has(m)) continue;
        materials.add(m);
        const match = PALETTE_MATERIAL.exec(m.name);
        const std = m as THREE.MeshStandardMaterial;
        if (match && std.isMeshStandardMaterial) paletteMaterials.push({ material: std, index: Number(match[1]) & 0xff, emissive: std.emissive.getHex() !== 0 });
      }
    });
    const box = new THREE.Box3().setFromObject(root);
    return { root, paletteMaterials, materials: [...materials], triangles, bytes, missing, size: box.getSize(new THREE.Vector3()), minY: box.min.y };
  }

  // --- Palette ---
  for (let i = 0; i < 23; i++) paletteEl.add(new Option(i === LEVEL_PALETTE ? `${i} (in level)` : String(i), String(i)));
  paletteEl.value = String(LEVEL_PALETTE);
  const hue = () => (flashEl.checked ? FLASH_HUE : -1);
  /** blit_sprite2_filter draws (filter & 0xf0) | (index & 0x0f). */
  const shade = (index: number) => (hue() < 0 ? index : hue() | (index & 0x0f));
  const rgb = (index: number): [number, number, number] => {
    const p = palettes[Number(paletteEl.value)];
    if (!p) return [128, 128, 128];
    const j = shade(index) * 3;
    return [vga6To8(p[j]), vga6To8(p[j + 1]), vga6To8(p[j + 2])];
  };
  function colourModel(): void {
    if (!model || !palettes.length) return;
    paletteTexture.set(palettes[Number(paletteEl.value)], -99, 0);
    for (const pm of model.paletteMaterials) {
      paletteTexture.color(shade(pm.index), pm.material.color);
      if (pm.emissive) pm.material.emissive.copy(pm.material.color);
    }
  }

  // --- Sprite side ---
  const pictureOf = (f: SpriteFrame): Int16Array | null => (res ? composeFrame(sheetData, f) : null);
  /** Paint a frame into a canvas at `scale` canvas px per sprite px. */
  function paintFrame(canvas: HTMLCanvasElement, f: SpriteFrame, scale: number): boolean {
    const pic = pictureOf(f);
    canvas.width = f.width * scale;
    canvas.height = f.height * scale;
    const ctx = canvas.getContext("2d")!;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!pic) return false;
    const img = ctx.createImageData(f.width, f.height);
    for (let i = 0; i < pic.length; i++) {
      if (pic[i] < 0) continue;
      const [r, g, b] = rgb(pic[i]);
      img.data.set([r, g, b, 255], i * 4);
    }
    const small = document.createElement("canvas");
    small.width = f.width;
    small.height = f.height;
    small.getContext("2d")!.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(small, 0, 0, canvas.width, canvas.height);
    return true;
  }
  /** Sprite display scale: whole screen px per sprite px, fitting the pane. Also the Top view's scale. */
  function spriteScale(f: SpriteFrame): number {
    const stage = spriteCanvas.parentElement!;
    const fit = Math.min(stage.clientWidth / f.width, stage.clientHeight / f.height);
    return Math.max(1, Math.floor(Math.min(fit, 16)));
  }
  function drawSprite(): void {
    const item = shown[current];
    if (!item) return;
    const f = item.frames[frame];
    const scale = spriteScale(f);
    const ok = paintFrame(spriteCanvas, f, scale);
    spriteCanvas.style.width = `${f.width * scale}px`;
    spriteCanvas.style.height = `${f.height * scale}px`;
    noDataEl.hidden = ok;
    framesEl.querySelectorAll("button").forEach((b, i) => b.classList.toggle("on", i === frame));
  }
  function buildFrameStrip(): void {
    const item = shown[current];
    framesEl.innerHTML = "";
    item.frames.forEach((f, i) => {
      const b = document.createElement("button");
      b.title = `${[...new Set(f.parts.map((p) => p.sheet))].join(", ")} ${f.label}`;
      const c = document.createElement("canvas");
      paintFrame(c, f, 2);
      b.append(c, Object.assign(document.createElement("span"), { textContent: f.label }));
      b.onclick = () => setFrame(i);
      framesEl.append(b);
    });
  }
  function setFrame(i: number): void {
    const n = shown[current]?.frames.length ?? 1;
    frame = ((i % n) + n) % n;
    drawSprite();
  }

  // --- Model side ---
  function size(): { w: number; h: number } {
    return { w: glStage.clientWidth, h: glStage.clientHeight };
  }
  function frameCamera(): void {
    if (!model) return;
    const { w, h } = size();
    // Fill most of the view with the model's bounding sphere.
    const radius = model.size.length() / 2;
    const vHalf = THREE.MathUtils.degToRad(persp.fov / 2);
    const hHalf = Math.atan(Math.tan(vHalf) * persp.aspect);
    const dist = radius / Math.sin(Math.min(vHalf, hHalf));
    if (mode === "game") {
      // From the bottom of the screen, tilted like the game camera.
      persp.position.set(0, dist * 0.8, dist * 0.6);
    } else if (mode === "free") {
      persp.position.set(dist * 0.55, dist * 0.6, dist * 0.6);
    }
    persp.up.set(0, 1, 0);
    perspControls.target.set(0, 0, 0);
    persp.lookAt(0, 0, 0);
    // Top: straight down, sprite up (-Z) at the top, 1 unit = 12 sprite px at the sprite's scale.
    const item = shown[current];
    const scale = item ? spriteScale(item.frames[frame]) : 8;
    const halfW = w / 2 / (PX_PER_UNIT * scale), halfH = h / 2 / (PX_PER_UNIT * scale);
    Object.assign(ortho, { left: -halfW, right: halfW, top: halfH, bottom: -halfH, zoom: 1 });
    ortho.position.set(0, 50, 0);
    ortho.up.set(0, 0, -1);
    ortho.lookAt(0, 0, 0);
    ortho.updateProjectionMatrix();
    orthoControls.target.set(0, 0, 0);
    perspControls.update();
    orthoControls.update();
  }
  function setMode(m: CameraMode): void {
    mode = m;
    perspControls.enabled = m !== "top";
    orthoControls.enabled = m === "top";
    document.querySelectorAll<HTMLButtonElement>("[data-cam]").forEach((b) => b.classList.toggle("on", b.dataset.cam === m));
    frameCamera();
  }
  function applyToggles(): void {
    if (model) for (const m of model.materials) (m as THREE.MeshStandardMaterial).wireframe = wireEl.checked;
    grid.visible = gridEl.checked;
    perspControls.autoRotate = orthoControls.autoRotate = spinEl.checked;
  }

  function drawOverlay(): void {
    const { w, h } = size();
    const dpr = Math.min(devicePixelRatio, 2);
    if (overlayCanvas.width !== Math.round(w * dpr) || overlayCanvas.height !== Math.round(h * dpr)) {
      overlayCanvas.width = Math.round(w * dpr);
      overlayCanvas.height = Math.round(h * dpr);
    }
    const ctx = overlayCanvas.getContext("2d")!;
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    const item = shown[current];
    if (mode !== "top" || !overlayOnEl.checked || !item || !res) return;
    const f = item.frames[frame];
    // The sprite's block, centred on the model's origin, sprite up = -Z; projected through the
    // Top camera so it follows zoom and pan.
    const corner = (x: number, z: number) => {
      const v = new THREE.Vector3(x, 0, z).project(ortho);
      return [((v.x + 1) / 2) * overlayCanvas.width, ((1 - v.y) / 2) * overlayCanvas.height];
    };
    const [x0, y0] = corner(-f.width / 2 / PX_PER_UNIT, -f.height / 2 / PX_PER_UNIT);
    const [x1, y1] = corner(f.width / 2 / PX_PER_UNIT, f.height / 2 / PX_PER_UNIT);
    ctx.globalAlpha = Number(overlayAlphaEl.value);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(spriteCanvas, x0, y0, x1 - x0, y1 - y0);
  }

  /** The model on screen, to reset the frame only when it changes. */
  let showing = "";
  async function show(i: number): Promise<void> {
    if (!shown.length) return;
    current = (i + shown.length) % shown.length;
    const item = shown[current];
    if (showing !== item.name) {
      // A player ship starts on its level frame, anything else on its first.
      frame = Math.max(0, item.frames.findIndex((f) => f.label === "level"));
      showing = item.name;
    }
    history.replaceState(null, "", `?viewer=${encodeURIComponent(item.name)}`);
    listEl.querySelectorAll("li").forEach((li) => {
      const on = li.dataset.name === item.name;
      li.classList.toggle("on", on);
      li.setAttribute("aria-selected", String(on));
      if (on) li.scrollIntoView({ block: "nearest" });
    });
    nameEl.textContent = item.name;
    const what = item.layout
      ? `Assembly of ${item.layout.pieces.length} pieces (each its own enemy and model)`
      : `${item.kind === "ship" ? "Player ship" : "Enemy"} · ${item.frames.length} frame${item.frames.length === 1 ? "" : "s"}`;
    metaEl.textContent = `${what} · ${item.sheets.join(", ")}`;
    buildFrameStrip();
    drawSprite();

    loadingEl.hidden = false;
    let p = built.get(item.name);
    if (!p) built.set(item.name, (p = build(item)));
    try {
      const loaded = await p;
      if (shown[current] !== item) return; // moved on meanwhile
      if (model) scene.remove(model.root);
      model = loaded;
      scene.add(model.root);
      grid.position.y = model.minY;
      metaEl.textContent += ` · ${Math.round(model.triangles)} triangles · ${(model.bytes / 1024).toFixed(0)} KB`;
      if (model.missing) metaEl.textContent += ` · ${model.missing} piece${model.missing === 1 ? "" : "s"} without a model`;
      colourModel();
      applyToggles();
      frameCamera();
    } catch (err) {
      metaEl.textContent += ` · failed to load: ${String(err)}`;
    } finally {
      loadingEl.hidden = true;
    }
  }

  // --- List ---
  function renderList(): void {
    const q = filterEl.value.trim().toLowerCase();
    const keep = shown[current];
    shown = q ? items.filter((i) => `${i.name} ${i.kind} ${i.sheets.join(" ")}`.toLowerCase().includes(q)) : items;
    countEl.textContent = `${shown.length} of ${items.length}`;
    listEl.innerHTML = "";
    const frag = document.createDocumentFragment();
    for (const item of shown) {
      const li = document.createElement("li");
      li.dataset.name = item.name;
      li.setAttribute("role", "option");
      li.textContent = item.name;
      if (item.kind !== "enemy") li.classList.add(item.kind);
      li.onclick = () => void show(shown.indexOf(item));
      frag.append(li);
    }
    listEl.append(frag);
    const again = keep ? shown.indexOf(keep) : -1;
    if (shown.length) void show(again >= 0 ? again : 0);
  }
  filterEl.oninput = renderList;

  // --- Controls ---
  document.querySelectorAll<HTMLButtonElement>("[data-step]").forEach((b) => (b.onclick = () => void show(current + Number(b.dataset.step))));
  document.querySelectorAll<HTMLButtonElement>("[data-cam]").forEach((b) => (b.onclick = () => setMode(b.dataset.cam as CameraMode)));
  for (const el of [spinEl, wireEl, gridEl]) el.onchange = applyToggles;
  flashEl.onchange = paletteEl.onchange = () => {
    colourModel();
    buildFrameStrip();
    drawSprite();
  };
  overlayOnEl.onchange = () => {
    if (overlayOnEl.checked && mode !== "top") setMode("top");
  };
  addEventListener("keydown", (e) => {
    if (e.target instanceof HTMLInputElement && e.target.type === "search" && !["ArrowUp", "ArrowDown"].includes(e.key)) return;
    if (e.target instanceof HTMLSelectElement) return;
    const k = e.key;
    if (k === "ArrowDown" || k === "j") void show(current + 1);
    else if (k === "ArrowUp" || k === "k") void show(current - 1);
    else if (k === "ArrowRight") setFrame(frame + 1);
    else if (k === "ArrowLeft") setFrame(frame - 1);
    else if (k === "t") setMode("top");
    else if (k === "g") setMode("game");
    else if (k === "f") setMode("free");
    else if (k === "o") {
      overlayOnEl.checked = !overlayOnEl.checked;
      overlayOnEl.onchange?.(new Event("change"));
    } else return;
    e.preventDefault();
  });

  // --- Loop ---
  let lastW = 0, lastH = 0, tick = 0;
  renderer.setAnimationLoop(() => {
    const { w, h } = size();
    if (w !== lastW || h !== lastH) {
      lastW = w;
      lastH = h;
      renderer.setSize(w, h, false);
      persp.aspect = w / Math.max(1, h);
      persp.updateProjectionMatrix();
      drawSprite();
      frameCamera();
    }
    if (playEl.checked && ++tick % 8 === 0) setFrame(frame + 1); // about the game's animation speed
    controls().update();
    if (outlineEl.checked) outline.render(scene, camera());
    else renderer.render(scene, camera());
    drawOverlay();
  });

  noDataEl.textContent = "Loading the game data…";
  setMode("free");
  renderList();

  // The sprites need the game data; ask for it only if it isn't already here.
  const files = await quietFiles();
  if (files) {
    useFiles(files);
  } else {
    noDataEl.innerHTML = `Sprites need the Tyrian 2.1 data. <button type="button">Choose tyrian21.zip</button>`;
    noDataEl.hidden = false;
    noDataEl.querySelector("button")!.onclick = async () => {
      const { askForData } = await import("../app/screens");
      useFiles(await askForData());
    };
  }

  function useFiles(f: FileMap): void {
    res = buildResources(f);
    palettes = res.palettes;
    sheetCache.clear();
    colourModel();
    buildFrameStrip();
    drawSprite();
  }
  Object.assign(window, { tyrianViewer: { renderer, scene, items } });
}
