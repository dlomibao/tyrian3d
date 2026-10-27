// Post-processing for OpenTyrian's screen filters (DECISIONS.md D31): the smoothies (lava, water,
// iced blur, blur), JE_starShowVGA's flipped screen and headlight, and JE_barBright's Zinglon beam.
// The sim records them per tick in drawList.screen (src/sim/smoothies.ts).
//
// The C rewrites the palette indices of the pixels drawn so far, so each filter only touches the
// draw passes before it. The hue half of that happens in the palette materials (screenHue.ts), on
// the real indices. The value half (the lava's wave and smear, the water's ripple, the blurs) is
// done here: the scene is drawn to a render target, and a mask pass draws it again with every
// object's pass height (D5) as its colour, so a filter changes a pixel only when the object on top
// there is from one of its passes. Positions are worked out in game_screen pixels: every draw sits
// on the camera ray through its original screen position (D6), so a pixel's game position is where
// its ray meets the ground, and the C's per-row and per-pixel offsets apply exactly. A colour's
// value is its brightness; a new value scales the lit colour, keeping its hue and lighting. Filters
// that mix with the previous frame do so per display frame with the weight that gives the C's
// per-tick blend. Nothing here runs while drawList.screen is null.

import * as THREE from "three";
import { CLASSIC_TICK_MS } from "../core/timing";
import { PLAYFIELD_H, PLAYFIELD_SCREEN_X, PLAYFIELD_SCREEN_Y, PLAYFIELD_W, PX_PER_UNIT } from "../game/playfield";
import { Pass, type DrawList } from "../sim/draw";
import type { ScreenFilters, ScreenFilterStage } from "../sim/smoothies";
import { PASS_HEIGHT } from "./passHeights";
import type { PaletteTexture } from "./paletteTexture";
import type { ScreenHue, ScreenHueStage } from "./screenHue";

/** Classic ticks per second (DECISIONS.md D2): the C runs each filter once a tick. */
const TICK_HZ = 1000 / CLASSIC_TICK_MS;
/** At most 6 filters a frame (iced, lava, water, iced, blur; lava runs once). */
const MAX_STAGES = 6;
const MAX_BARS = 4;

const KIND = { lava: 1, water: 2, iced: 3, blur: 4 } as const;

/** Height between a pass and the next: a filter covers every object below it (D5). */
export function passCeiling(pass: Pass): number {
  const h = PASS_HEIGHT[pass];
  const above = Object.values(PASS_HEIGHT).filter((v) => v > h);
  return above.length ? (h + Math.min(...above)) / 2 : h + 1;
}

/**
 * The weight of the previous frame for a filter that reads it, per display frame of `dt` seconds:
 * the C mixes half of the previous tick's screen in, so after one tick's worth of frames the old
 * picture has faded by half.
 */
export function previousFrameWeight(dt: number): number {
  return Math.pow(0.5, Math.max(0, dt) * TICK_HZ);
}

/** The shader's per-stage uniforms for one frame. */
export function stageUniforms(stages: readonly ScreenFilterStage[], dt: number, historyValid: boolean) {
  const kind = new Array<number>(MAX_STAGES).fill(0);
  const ceiling = new Array<number>(MAX_STAGES).fill(-1);
  const prev = new Array<number>(MAX_STAGES).fill(-1);
  stages.slice(0, MAX_STAGES).forEach((s, i) => {
    kind[i] = KIND[s.kind];
    ceiling[i] = passCeiling(s.pass);
    // -1: works in place on this frame's pixels; otherwise the previous frame's weight.
    prev[i] = s.temporal ? (historyValid ? previousFrameWeight(dt) : 0) : -1;
  });
  return { kind, ceiling, prev, count: Math.min(stages.length, MAX_STAGES) };
}

/** The hue changes of a frame's filters, for the palette materials (screenHue.ts). */
export function hueStages(stages: readonly ScreenFilterStage[]): ScreenHueStage[] {
  const out: ScreenHueStage[] = [];
  for (const s of stages) {
    if (s.kind === "lava") out.push({ ceiling: passCeiling(s.pass), hue: 0x7, water: false });
    else if (s.kind === "iced") out.push({ ceiling: passCeiling(s.pass), hue: 0x8, water: false });
    else if (s.kind === "water") out.push({ ceiling: passCeiling(s.pass), hue: (s.hue >> 4) & 0x0f, water: true });
  }
  return out;
}

const QUAD_VERTEX = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

/** Shared GLSL: game_screen pixels <-> screen UVs, and colours' values. */
const COMMON = /* glsl */ `
uniform mat4 viewProj;
uniform mat4 invViewProj;
const float PX = ${PX_PER_UNIT.toFixed(1)};
const vec2 ORIGIN = vec2(${(PLAYFIELD_SCREEN_X + PLAYFIELD_W / 2).toFixed(1)}, ${(PLAYFIELD_SCREEN_Y + PLAYFIELD_H / 2).toFixed(1)});

// Where the camera ray through this screen point meets the ground, in game_screen pixels.
vec2 gameAt(vec2 uv) {
  vec4 n = invViewProj * vec4(uv * 2.0 - 1.0, -1.0, 1.0);
  vec4 f = invViewProj * vec4(uv * 2.0 - 1.0, 1.0, 1.0);
  n /= n.w;
  f /= f.w;
  vec3 d = f.xyz - n.xyz;
  vec3 p = n.xyz + d * (-n.y / d.y);
  return p.xz * PX + ORIGIN;
}

vec2 uvAt(vec2 game) {
  vec2 w = (game - ORIGIN) / PX;
  vec4 c = viewProj * vec4(w.x, 0.0, w.y, 1.0);
  return c.xy / c.w * 0.5 + 0.5;
}

// A colour's value, 0..15, as the 16 shades of a palette hue run (sRGB brightness).
float valueOf(vec3 c) {
  float m = max(max(c.r, c.g), c.b);
  return clamp(pow(max(m, 0.0), 1.0 / 2.2) * 15.0, 0.0, 15.0);
}

// The colour with its value changed, its hue kept.
vec3 withValue(vec3 c, float v) {
  float v0 = valueOf(c);
  if (v0 < 0.25) return vec3(pow(clamp(v, 0.0, 15.0) / 15.0, 2.2));
  return c * pow(clamp(v, 0.0, 15.0) / v0, 2.2);
}
`;

const FILTER_FRAGMENT = /* glsl */ `
precision highp float;
precision highp int;
${COMMON}
uniform sampler2D sceneMap;
uniform sampler2D prevMap;
uniform sampler2D maskMap;
uniform int stageCount;
uniform int stageKind[${MAX_STAGES}];
uniform float stageCeiling[${MAX_STAGES}];
uniform float stagePrev[${MAX_STAGES}];
varying vec2 vUv;

float heightAt(vec2 uv) { return texture2D(maskMap, uv).r; }

// This frame's pixel at a game position, if it's from the filter's passes; otherwise the fallback
// (the C's buffer only holds what was drawn before the filter). Alpha < 1 marks the water's pixels.
vec4 below(vec2 game, float ceiling, vec4 fallback) {
  vec2 uv = uvAt(game);
  return heightAt(uv) < ceiling ? texture2D(sceneMap, uv) : fallback;
}

vec3 previous(vec2 game) { return texture2D(prevMap, uvAt(game)).rgb; }

bool isWater(vec4 c) { return c.a < 0.75; }

// The 8-pixel chunk's diw (the C counts it down from the bottom-right).
int diwAt(vec2 g) { return 320 * int(floor(g.y)) + (int(floor(g.x)) & ~7) + 8; }
// lava_filter's wave, -1..7 px.
float lavaWave(vec2 g) { return float(abs(((diwAt(g) >> 9) & 15) - 8) - 1); }
// water_filter's wave, -1..3 px.
float waterWave(vec2 g) { return float(abs(((diwAt(g) >> 10) & 7) - 4) - 1); }

void main() {
  vec4 c = texture2D(sceneMap, vUv);
  float h = heightAt(vUv);
  vec2 g = gameAt(vUv);
  for (int i = 0; i < ${MAX_STAGES}; i++) {
    if (i >= stageCount) break;
    float ceiling = stageCeiling[i];
    if (h >= ceiling) continue;
    float a = stagePrev[i];
    int kind = stageKind[i];
    if (kind == 1) {
      // lava_filter: value = (2 * src[x + wave] + dst below + dst above) / 4 (hue 0x70 is the
      // materials' job).
      vec2 p = g + vec2(lavaWave(g), 0.0);
      vec4 s = below(p, ceiling, c);
      float vs = valueOf(s.rgb);
      float v;
      if (a >= 0.0) {
        v = mix(vs, 0.5 * (valueOf(previous(p + vec2(0.0, 1.0))) + valueOf(previous(p - vec2(0.0, 1.0)))), a);
      } else {
        v = 0.5 * vs + 0.25 * (valueOf(below(p + vec2(0.0, 1.0), ceiling, s).rgb) + valueOf(below(p - vec2(0.0, 1.0), ceiling, s).rgb));
      }
      c.rgb = withValue(s.rgb, v);
    } else if (kind == 2) {
      // water_filter, bottom row up: dst = hue | (src value + dst[below, x + wave] value) / 2 for the
      // pixels it recoloured. The rows below are this frame's results, so the value is a running
      // half-and-half down the column, as far as the water goes.
      if (isWater(c)) {
        float acc = 0.5 * valueOf(c.rgb);
        float w = 0.5;
        vec2 p = g;
        for (int k = 0; k < 6; k++) {
          p += vec2(waterWave(p), 1.0);
          vec4 s = below(p, ceiling, vec4(c.rgb, 1.0));
          float vk = valueOf(s.rgb);
          if (!isWater(s) || k == 5) {
            acc += w * vk;
            break;
          }
          acc += w * 0.5 * vk;
          w *= 0.5;
        }
        c.rgb = withValue(c.rgb, acc);
      }
    } else if (kind == 3 || kind == 4) {
      // iced_blur_filter and blur_filter: value = (src + dst) / 2, this pixel's hue (ice blue for
      // the iced one, from the materials). In place they change nothing more.
      if (a >= 0.0) c.rgb = withValue(c.rgb, mix(valueOf(c.rgb), valueOf(previous(g)), a));
    }
  }
  gl_FragColor = vec4(c.rgb, 1.0);
}
`;

const PRESENT_FRAGMENT = /* glsl */ `
precision highp float;
${COMMON}
uniform sampler2D sourceMap;
uniform int showCode;
uniform vec2 player;
uniform int barCount;
uniform vec4 bars[${MAX_BARS}];
varying vec2 vUv;

// showHeadlight (backgrnd.c L855-988): a cone of light up from the ship, the rest at a quarter.
float headlight(vec2 g, float v) {
  float col = g.x - 24.0;
  float row = g.y;
  float lx = (player.x - 17.0) - (player.y + 12.0) + 1.0 + row;
  float rx = (player.x - 17.0) + (player.y + 12.0) - row;
  float dark = v / 4.0;
  if (lx > rx + 1.0) return dark;
  if (col < lx - 5.0) return dark;
  if (col < lx) return (v + 3.0 * (6.0 - (lx - col))) / 4.0;
  if (col < rx) return v;
  if (col < rx + 5.0) return (v + 3.0 * (rx + 5.0 - col)) / 4.0;
  return dark;
}

void main() {
  vec2 g = gameAt(vUv);
  vec2 src = g;
  vec2 uv = vUv;
  // showFlipped: the 184 rows upside down.
  if (showCode == 1) {
    src = vec2(g.x, 184.0 - g.y);
    uv = uvAt(src);
  }
  vec3 c = texture2D(sourceMap, uv).rgb;

  // JE_barBright: +2 value per rectangle.
  float add = 0.0;
  for (int i = 0; i < ${MAX_BARS}; i++) {
    if (i >= barCount) break;
    vec4 b = bars[i];
    if (src.x >= b.x && src.x < b.z + 1.0 && src.y >= b.y && src.y < b.w + 1.0) add += 2.0;
  }
  if (add > 0.0) c = withValue(c, valueOf(c) + add);

  if (showCode == 2) c = withValue(c, headlight(g, valueOf(c)));

  gl_FragColor = vec4(c, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

const MASK_VERTEX = /* glsl */ `
uniform float objectHeight;
varying float vHeight;
void main() {
  mat4 m = modelMatrix;
  #ifdef USE_INSTANCING
    m = m * instanceMatrix;
  #endif
  vHeight = objectHeight > -1000.0 ? objectHeight : m[3][1];
  gl_Position = projectionMatrix * viewMatrix * m * vec4(position, 1.0);
}
`;

const MASK_FRAGMENT = /* glsl */ `
varying float vHeight;
void main() {
  gl_FragColor = vec4(vHeight, 0.0, 0.0, 1.0);
}
`;

const renderTarget = (samples: number) =>
  new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType,
    minFilter: THREE.LinearFilter,
    magFilter: THREE.LinearFilter,
    depthBuffer: true,
    samples,
  });

/**
 * Draws the scene through the screen filters when a draw list asks for any. `render` replaces the
 * plain scene render for those frames.
 */
export class ScreenFilterPass {
  private state: ScreenFilters | null = null;
  private prevPlayer = { x: 0, y: 0 };
  private readonly screenHue: ScreenHue;

  private readonly sceneTarget: THREE.WebGLRenderTarget;
  private readonly maskTarget = renderTarget(0);
  private history = [renderTarget(0), renderTarget(0)];
  private historyValid = false;
  private lastTime = performance.now();

  private readonly quadScene = new THREE.Scene();
  private readonly quadCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private readonly quad: THREE.Mesh;
  private readonly filterMaterial: THREE.ShaderMaterial;
  private readonly presentMaterial: THREE.ShaderMaterial;
  private readonly maskMaterial: THREE.ShaderMaterial;
  private readonly size = new THREE.Vector2();
  private readonly viewProj = new THREE.Matrix4();
  private readonly invViewProj = new THREE.Matrix4();

  constructor(
    private readonly renderer: THREE.WebGLRenderer,
    palette: PaletteTexture,
  ) {
    this.sceneTarget = renderTarget(Math.min(4, renderer.capabilities.maxSamples));
    this.screenHue = palette.screenHue;

    const common = {
      viewProj: { value: this.viewProj },
      invViewProj: { value: this.invViewProj },
    };
    this.filterMaterial = new THREE.ShaderMaterial({
      vertexShader: QUAD_VERTEX,
      fragmentShader: FILTER_FRAGMENT,
      uniforms: {
        ...common,
        sceneMap: { value: null },
        prevMap: { value: null },
        maskMap: { value: null },
        stageCount: { value: 0 },
        stageKind: { value: new Array(MAX_STAGES).fill(0) },
        stageCeiling: { value: new Array(MAX_STAGES).fill(0) },
        stagePrev: { value: new Array(MAX_STAGES).fill(0) },
      },
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    });
    this.presentMaterial = new THREE.ShaderMaterial({
      vertexShader: QUAD_VERTEX,
      fragmentShader: PRESENT_FRAGMENT,
      uniforms: {
        ...common,
        sourceMap: { value: null },
        showCode: { value: 0 },
        player: { value: new THREE.Vector2() },
        barCount: { value: 0 },
        bars: { value: Array.from({ length: MAX_BARS }, () => new THREE.Vector4()) },
      },
      depthTest: false,
      depthWrite: false,
    });
    this.maskMaterial = new THREE.ShaderMaterial({
      vertexShader: MASK_VERTEX,
      fragmentShader: MASK_FRAGMENT,
      uniforms: { objectHeight: { value: -2000 } },
      side: THREE.DoubleSide,
    });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.filterMaterial);
    this.quad.frustumCulled = false;
    this.quadScene.add(this.quad);
  }

  /** Take one tick's screen state (call with every draw list). */
  setDrawList(list: DrawList): void {
    if (this.state) this.prevPlayer = { x: this.state.playerX, y: this.state.playerY };
    else if (list.screen) this.prevPlayer = { x: list.screen.playerX, y: list.screen.playerY };
    if (!list.screen || list.screen.stages.length === 0) this.historyValid = false;
    this.state = list.screen;
    this.screenHue.set(list.screen ? hueStages(list.screen.stages) : []);
  }

  /** Whether the next frame needs the filters. */
  get active(): boolean {
    return this.state !== null;
  }

  /**
   * Draw a frame through the filters: `drawScene` renders the scene (with its outlines) into the
   * current render target. `root` holds the draw list's objects, for the mask.
   */
  render(scene: THREE.Scene, camera: THREE.Camera, root: THREE.Object3D, drawScene: () => void, alpha: number): void {
    const state = this.state;
    if (!state) {
      drawScene();
      return;
    }
    const r = this.renderer;
    const now = performance.now();
    const dt = Math.min(0.25, (now - this.lastTime) / 1000);
    this.lastTime = now;

    r.getDrawingBufferSize(this.size);
    const { x: w, y: h } = this.size;
    if (this.sceneTarget.width !== w || this.sceneTarget.height !== h) {
      for (const t of [this.sceneTarget, this.maskTarget, ...this.history]) t.setSize(w, h);
      this.historyValid = false;
    }
    camera.updateMatrixWorld();
    this.viewProj.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    this.invViewProj.copy(this.viewProj).invert();

    const previousTarget = r.getRenderTarget();
    r.setRenderTarget(this.sceneTarget);
    drawScene();

    let source: THREE.Texture = this.sceneTarget.texture;
    if (state.stages.length > 0) {
      this.renderMask(scene, camera, root);
      const u = this.filterMaterial.uniforms;
      const stages = stageUniforms(state.stages, dt, this.historyValid);
      u.sceneMap.value = this.sceneTarget.texture;
      u.prevMap.value = this.history[1].texture;
      u.maskMap.value = this.maskTarget.texture;
      u.stageCount.value = stages.count;
      u.stageKind.value = stages.kind;
      u.stageCeiling.value = stages.ceiling;
      u.stagePrev.value = stages.prev;
      this.quad.material = this.filterMaterial;
      r.setRenderTarget(this.history[0]);
      r.render(this.quadScene, this.quadCamera);
      source = this.history[0].texture;
      this.history.reverse(); // this frame's result is the next frame's previous one
      this.historyValid = true;
    }

    const p = this.presentMaterial.uniforms;
    p.sourceMap.value = source;
    p.showCode.value = state.showCode;
    (p.player.value as THREE.Vector2).set(
      this.prevPlayer.x + (state.playerX - this.prevPlayer.x) * alpha,
      this.prevPlayer.y + (state.playerY - this.prevPlayer.y) * alpha,
    );
    const bars = p.bars.value as THREE.Vector4[];
    const count = Math.min(MAX_BARS, state.bars.length / 4);
    for (let i = 0; i < count; i++) bars[i].fromArray(state.bars, i * 4);
    p.barCount.value = count;
    this.quad.material = this.presentMaterial;
    r.setRenderTarget(previousTarget);
    r.render(this.quadScene, this.quadCamera);
  }

  /** Draw every object's pass height (D5) into the mask target. */
  private renderMask(scene: THREE.Scene, camera: THREE.Camera, root: THREE.Object3D): void {
    const r = this.renderer;
    const background = scene.background;
    const override = scene.overrideMaterial;
    const shadows = r.shadowMap.autoUpdate;
    const clearColor = r.getClearColor(new THREE.Color());
    const clearAlpha = r.getClearAlpha();
    const material = this.maskMaterial;
    // Models are groups under root at their pass height; instanced sprites carry it per instance.
    material.onBeforeRender = (_r, _s, _c, _g, object) => {
      let height = -2000;
      if (!(object as THREE.InstancedMesh).isInstancedMesh) {
        let o: THREE.Object3D = object;
        while (o.parent && o.parent !== root) o = o.parent;
        height = o.parent === root ? o.position.y : 0;
      }
      if (material.uniforms.objectHeight.value !== height) {
        material.uniforms.objectHeight.value = height;
        material.uniformsNeedUpdate = true;
      }
    };
    scene.background = null;
    scene.overrideMaterial = material;
    r.shadowMap.autoUpdate = false;
    r.setClearColor(0x000000, 0);
    r.setRenderTarget(this.maskTarget);
    r.render(scene, camera);
    r.setClearColor(clearColor, clearAlpha);
    r.shadowMap.autoUpdate = shadows;
    scene.overrideMaterial = override;
    scene.background = background;
  }
}
