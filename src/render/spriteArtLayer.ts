// Draws remastered flat sprite art (spriteArt.ts, DECISIONS.md D42): each sprite with a painting is
// a flat quad in the playfield plane at its pass's height, textured from its sheet's atlas.
//
// One instanced draw per atlas and pass, rebuilt every display frame into reused buffers (like the
// glows, vfx/glowLayer.ts). Within a batch the instances keep the draw list's order; batches sort by
// pass (renderOrder), so later passes draw over earlier ones as in the C, and before the other
// transparent draws (see RENDER_ORDER).
//
// The atlases are uploaded premultiplied, so their soft edges filter and blend without fringes, and
// blended with depth testing but no depth writes. Palette effects are done on the art's brightness:
// the enemy hit flash (blit_sprite2_filter) and blit_sprite_hv recolour each texel with the palette
// entry of its hue at the shade its brightness gives; the "blend" effect is the renderer's opacity;
// JE_filterScreen's level hue and brightness and the smoothies' hues (D31) recolour or scale it the
// same way, from the live palette texture.

import * as THREE from "three";
import type { PaletteTexture } from "./paletteTexture";
import { SCREEN_HUE_PARS } from "./screenHue";
import { SpriteArt, parseSpriteArtManifest, spriteArtImageUrl, type FlatQuad, type ReadyFrame, type SpriteArtSheet } from "./spriteArt";

/** Where the manifest lives, under the site root. */
export const SPRITE_ART_DIR = "art/sprites/";

/**
 * Before the other transparent draws (the blended sprites at 0, puffs and particles at 1, glows at
 * 2): those are all in passes at or above what they overlap here (explosions over pickups, a shot's
 * halo over the shot), and as the art writes no depth, whatever draws later lands on top.
 */
const RENDER_ORDER = -1;

const VERTEX = /* glsl */ `
attribute vec3 aOrigin;   // world position of the quad's top-left corner
attribute vec2 aSize;     // world size along X and Z
attribute vec4 aUv;       // frame UV rectangle: u0 v0 u1 v1
attribute vec4 aFx;       // mode (0 none, 1 filter, 2 hue/value), hue, value, alpha
varying vec2 vUv;
varying vec4 vUvRect;
varying vec4 vFx;
varying float vHeight;

void main() {
  vec3 p = aOrigin + vec3(position.x * aSize.x, 0.0, position.z * aSize.y);
  vUv = mix(aUv.xy, aUv.zw, position.xz);
  vUvRect = aUv;
  vFx = aFx;
  vHeight = aOrigin.y;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}
`;

const FRAGMENT = /* glsl */ `
uniform sampler2D map;
uniform sampler2D paletteMap;
uniform float levelFilter;     // JE_filterScreen's hue, or -99
uniform float levelBrightness; // and its brightness (0 or -99: none)
varying vec2 vUv;
varying vec4 vUvRect;
varying vec4 vFx;
varying float vHeight;
${SCREEN_HUE_PARS}

vec3 paletteColor(float index) {
  return texture2D(paletteMap, vec2((index + 0.5) / 256.0, 0.5)).rgb;
}

// JE_filterScreen's value rule: the sum if it's 0..15, 15 if it's 16..30, else 0.
float clampValue(float v) {
  return v < 0.0 ? 0.0 : (v > 15.0 ? (v >= 31.0 ? 0.0 : 15.0) : v);
}

void main() {
  // Stay inside this frame's texels, so neighbours in the atlas never bleed in.
  vec2 halfTexel = 0.5 / vec2(textureSize(map, 0));
  vec4 tex = texture2D(map, clamp(vUv, vUvRect.xy + halfTexel, vUvRect.zw - halfTexel));
  float a = tex.a * vFx.w;
  if (a < 0.004) discard;
  vec3 rgb = tex.rgb / max(tex.a, 1e-4);
  // The shade (0..15) a palette ramp would give this brightness.
  float lum = pow(max(dot(rgb, vec3(0.2126, 0.7152, 0.0722)), 0.0), 1.0 / 2.2);
  float shade = clamp(floor(lum * 15.0 + 0.5), 0.0, 15.0);
  float index = 16.0 + shade;
  bool recolour = false;
  if (vFx.x > 1.5) {
    index = vFx.y * 16.0 + clampValue(shade + vFx.z);
    recolour = true;
  } else if (vFx.x > 0.5) {
    index = vFx.y * 16.0 + shade;
    recolour = true;
  }
  float water = 0.0;
  float hued = screenHueIndex(index, vHeight, water);
  if (hued != index) recolour = true;
  if (recolour || levelFilter > -98.5) {
    // The palette texture already holds the level filter and brightness (paletteTexture.ts).
    rgb = paletteColor(hued);
  } else if (levelBrightness > -98.5 && levelBrightness != 0.0) {
    float s = lum * 15.0;
    float k = clampValue(floor(s + 0.5) + levelBrightness) / max(s, 0.5);
    rgb *= pow(k, 2.2);
  }
  gl_FragColor = vec4(rgb * a, a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

/** Instances of one atlas in one pass. */
class Batch {
  readonly mesh: THREE.Mesh;
  readonly geometry = new THREE.InstancedBufferGeometry();
  private origin!: THREE.InstancedBufferAttribute;
  private size!: THREE.InstancedBufferAttribute;
  private uv!: THREE.InstancedBufferAttribute;
  private fx!: THREE.InstancedBufferAttribute;
  private capacity = 0;
  count = 0;

  constructor(material: THREE.Material, renderOrder: number) {
    // A unit quad in the XZ plane, top-left at the origin, facing up.
    this.geometry.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1], 3));
    this.geometry.setIndex([0, 2, 1, 0, 3, 2]);
    this.allocate(64);
    this.mesh = new THREE.Mesh(this.geometry, material);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = renderOrder;
    this.mesh.name = "sprite-art";
  }

  private allocate(capacity: number): void {
    if (this.capacity > 0) this.geometry.dispose();
    const make = (name: string, itemSize: number, old?: THREE.InstancedBufferAttribute) => {
      const attr = new THREE.InstancedBufferAttribute(new Float32Array(capacity * itemSize), itemSize);
      attr.setUsage(THREE.DynamicDrawUsage);
      if (old) attr.array.set(old.array as Float32Array);
      this.geometry.setAttribute(name, attr);
      return attr;
    };
    this.origin = make("aOrigin", 3, this.origin);
    this.size = make("aSize", 2, this.size);
    this.uv = make("aUv", 4, this.uv);
    this.fx = make("aFx", 4, this.fx);
    this.capacity = capacity;
  }

  add(q: FlatQuad, f: ReadyFrame, mode: number, a: number, b: number, alpha: number): void {
    if (this.count >= this.capacity) this.allocate(this.capacity * 2);
    const i = this.count++;
    const o = this.origin.array as Float32Array;
    const s = this.size.array as Float32Array;
    const u = this.uv.array as Float32Array;
    const x = this.fx.array as Float32Array;
    o[i * 3] = q.x;
    o[i * 3 + 1] = q.y;
    o[i * 3 + 2] = q.z;
    s[i * 2] = q.w;
    s[i * 2 + 1] = q.d;
    u[i * 4] = f.u0;
    u[i * 4 + 1] = f.v0;
    u[i * 4 + 2] = f.u1;
    u[i * 4 + 3] = f.v1;
    x[i * 4] = mode;
    x[i * 4 + 1] = a;
    x[i * 4 + 2] = b;
    x[i * 4 + 3] = alpha;
  }

  commit(): void {
    const n = this.count;
    this.geometry.instanceCount = n;
    this.mesh.visible = n > 0;
    if (n > 0) {
      for (const attr of [this.origin, this.size, this.uv, this.fx]) {
        attr.clearUpdateRanges();
        attr.addUpdateRange(0, n * attr.itemSize);
        attr.needsUpdate = true;
      }
    }
    this.count = 0;
  }

  /** The instance data written this frame (before commit), for tests. */
  instance(i: number): { origin: number[]; size: number[]; uv: number[]; fx: number[] } {
    const get = (attr: THREE.InstancedBufferAttribute) => Array.from((attr.array as Float32Array).subarray(i * attr.itemSize, (i + 1) * attr.itemSize));
    return { origin: get(this.origin), size: get(this.size), uv: get(this.uv), fx: get(this.fx) };
  }

  dispose(): void {
    this.geometry.dispose();
  }
}

/** The flat sprite art's batches, one per atlas and pass. */
export class SpriteArtLayer {
  readonly root = new THREE.Group();
  private readonly materials = new Map<SpriteArtSheet<THREE.Texture>, THREE.ShaderMaterial>();
  private readonly batches = new Map<SpriteArtSheet<THREE.Texture>, Batch[]>();
  private readonly all: Batch[] = [];
  private readonly levelUniforms = { levelFilter: { value: -99 }, levelBrightness: { value: 0 } };
  /** Instances drawn last frame. */
  instances = 0;

  constructor(private readonly palette: PaletteTexture) {
    this.root.name = "sprite-art";
  }

  /** Start a display frame. */
  begin(): void {
    this.levelUniforms.levelFilter.value = this.palette.screenFilter;
    this.levelUniforms.levelBrightness.value = this.palette.screenBrightness;
  }

  /**
   * Add a quad of `sheet`'s frame `f` at `q` in pass `pass`, with the instance's palette effect
   * (mode 0 none, 1 the hit-flash filter with hue a, 2 hue a and value b) and opacity.
   */
  add(sheet: SpriteArtSheet<THREE.Texture>, pass: number, q: FlatQuad, f: ReadyFrame, mode: number, a: number, b: number, alpha: number): void {
    this.batch(sheet, pass).add(q, f, mode, a, b, alpha);
  }

  /** Upload this frame's instances. */
  end(): void {
    let n = 0;
    for (const b of this.all) {
      n += b.count;
      b.commit();
    }
    this.instances = n;
  }

  /** The batch for an atlas and pass, for tests. */
  peek(sheet: SpriteArtSheet<THREE.Texture>, pass: number): Batch | undefined {
    return this.batches.get(sheet)?.[pass];
  }

  get drawCalls(): number {
    return this.all.filter((b) => b.mesh.visible).length;
  }

  dispose(): void {
    for (const b of this.all) b.dispose();
    for (const m of this.materials.values()) m.dispose();
    this.root.removeFromParent();
  }

  private batch(sheet: SpriteArtSheet<THREE.Texture>, pass: number): Batch {
    let list = this.batches.get(sheet);
    if (!list) this.batches.set(sheet, (list = []));
    let b = list[pass];
    if (!b) {
      b = list[pass] = new Batch(this.material(sheet), RENDER_ORDER + pass / 100);
      this.all.push(b);
      this.root.add(b.mesh);
    }
    return b;
  }

  private material(sheet: SpriteArtSheet<THREE.Texture>): THREE.ShaderMaterial {
    let m = this.materials.get(sheet);
    if (!m) {
      m = new THREE.ShaderMaterial({
        vertexShader: VERTEX,
        fragmentShader: FRAGMENT,
        uniforms: {
          map: { value: sheet.texture },
          paletteMap: { value: this.palette.texture },
          ...this.levelUniforms,
          ...this.palette.screenHue.uniforms,
        },
        transparent: true,
        premultipliedAlpha: true,
        depthWrite: false,
        // Painted art shows its own colours, not compressed by the scene's tone mapping.
        toneMapped: false,
        side: THREE.DoubleSide,
        userData: { outlineParameters: { visible: false } },
      });
      this.materials.set(sheet, m);
    }
    return m;
  }
}

/** How the loader gets its inputs, so tests can run it without a network or WebGL. */
export interface SpriteArtLoadIo {
  fetchJson(url: string): Promise<unknown | undefined>;
  loadTexture(url: string): Promise<{ texture: THREE.Texture; width: number; height: number }>;
}

const browserIo = (): SpriteArtLoadIo => ({
  fetchJson: (url) => fetch(url).then((r) => (r.ok ? r.json() : undefined)),
  loadTexture: async (url) => {
    const texture = await new THREE.TextureLoader().loadAsync(url);
    const image = texture.image as { width: number; height: number };
    return { texture, width: image.width, height: image.height };
  },
});

/**
 * Load public/art/sprites/manifest.json and start loading its atlases. Resolves to null if there's
 * no manifest (an offline build, a failed request, a bad file): every sprite draws as before. Each
 * sheet's sprites draw as before until its atlas arrives, and for good if it fails to load.
 */
export async function loadSpriteArt(base: string = import.meta.env.BASE_URL, io: SpriteArtLoadIo = browserIo()): Promise<SpriteArt<THREE.Texture> | null> {
  const dir = `${base}${SPRITE_ART_DIR}`;
  let json: unknown;
  try {
    json = await io.fetchJson(`${dir}manifest.json`);
  } catch (err) {
    console.warn("sprite art manifest didn't load; using the original sprites", err);
    return null;
  }
  const manifest = json === undefined ? null : parseSpriteArtManifest(json);
  if (!manifest) return null;
  const art = new SpriteArt<THREE.Texture>(manifest);
  const loads = [...art.sheets.values()].map((sheet) =>
    io.loadTexture(spriteArtImageUrl(dir, sheet.image)).then(
      ({ texture, width, height }) => {
        texture.flipY = false;
        texture.premultiplyAlpha = true;
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.anisotropy = 4;
        texture.needsUpdate = true;
        sheet.setTexture(texture, width, height);
      },
      (err) => console.warn(`sprite art atlas ${sheet.image} didn't load; its sprites stay original`, err),
    ),
  );
  art.loaded = Promise.all(loads).then(() => undefined);
  return art;
}
