// Glows that follow draws: a shot's halo and trail, an explosion's fireball light, a smoke puff.
//
// Unlike particles these are rebuilt every display frame from the draw list, so they sit exactly
// on the (interpolated) draw they belong to. Each is one instance of a camera-facing capsule from
// a tail point to a head point: with the two points equal it's a round glow, and with the tail
// behind a moving shot it's the shot's halo drawn out into a fading trail. One instanced draw call
// per layer; the buffers grow (doubling) when a frame needs more, and are otherwise reused.

import * as THREE from "three";

export const enum GlowShape {
  /** A soft glow, brightest at the head, fading toward the tail. */
  Glow = 0,
  /** A ragged smoke puff (alpha-blended layers). */
  Puff = 1,
}

const VERTEX = /* glsl */ `
attribute vec3 aHead;
attribute vec3 aTail;
attribute vec4 aParams; // radius, tail brightness (0..1), shape, seed
attribute vec4 aColor;
varying vec2 vLocal;    // along the capsule (from the tail) and across it, in radii
varying float vLen;     // capsule length in radii
varying vec4 vColor;
varying vec2 vParams;   // tail brightness, shape
varying float vSeed;

void main() {
  vec4 h = modelViewMatrix * vec4(aHead, 1.0);
  vec4 t = modelViewMatrix * vec4(aTail, 1.0);
  float r = aParams.x;
  vec2 d = h.xy - t.xy;
  float len = length(d);
  vec2 dir = len > 1e-5 ? d / len : vec2(0.0, 1.0);
  vec2 nrm = vec2(-dir.y, dir.x);
  // position.x: 0 at the tail end (minus a radius), 1 at the head end (plus a radius).
  float s = mix(-r, len + r, position.x);
  vec4 mv = mix(t, h, len > 1e-5 ? clamp(s / len, 0.0, 1.0) : 1.0);
  mv.xy = t.xy + dir * s + nrm * position.y * r;
  gl_Position = projectionMatrix * mv;
  vLocal = vec2(s, position.y * r) / r;
  vLen = len / r;
  vColor = aColor;
  vParams = aParams.yz;
  vSeed = aParams.w;
}
`;

const FRAGMENT = /* glsl */ `
varying vec2 vLocal;
varying float vLen;
varying vec4 vColor;
varying vec2 vParams;
varying float vSeed;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}

void main() {
  float along = clamp(vLocal.x, 0.0, vLen);
  vec2 q = vec2(vLocal.x - along, vLocal.y);
  float d = length(q);
  float a;
  vec3 rgb = vColor.rgb;
  if (vParams.y < 0.5) {
    if (d > 1.0) discard;
    float k = 1.0 - d;
    // Brightest at the head, falling to the tail brightness at the tail.
    float f = vLen > 1e-3 ? mix(vParams.x, 1.0, along / vLen) : 1.0;
    a = k * k * f;
    rgb *= 1.0 + 1.5 * k * k * k * f;
  } else {
    float n = noise(q * 2.2 + vSeed * 31.0) + 0.5 * noise(q * 4.5 - vSeed * 13.0);
    float e = d + (n - 0.75) * 0.5;
    if (e > 1.0) discard;
    a = smoothstep(1.0, 0.3, e);
    rgb *= 0.7 + 0.4 * n;
  }
  gl_FragColor = vec4(rgb, a * vColor.a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

export class GlowLayer {
  readonly mesh: THREE.Mesh;
  private readonly geometry = new THREE.InstancedBufferGeometry();
  private head!: THREE.InstancedBufferAttribute;
  private tail!: THREE.InstancedBufferAttribute;
  private params!: THREE.InstancedBufferAttribute;
  private color!: THREE.InstancedBufferAttribute;
  private attrs: THREE.InstancedBufferAttribute[] = [];
  private capacity = 0;
  count = 0;

  constructor(blending: THREE.Blending, capacity = 256) {
    // A quad: x from the tail end (0) to the head end (1), y across (-1..1).
    this.geometry.setAttribute("position", new THREE.Float32BufferAttribute([0, -1, 0, 1, -1, 0, 1, 1, 0, 0, 1, 0], 3));
    this.geometry.setIndex([0, 1, 2, 0, 2, 3]);
    this.allocate(capacity);
    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX,
      fragmentShader: FRAGMENT,
      transparent: true,
      depthWrite: false,
      blending,
      userData: { outlineParameters: { visible: false } },
    });
    this.mesh = new THREE.Mesh(this.geometry, material);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = blending === THREE.AdditiveBlending ? 2 : 1;
    this.mesh.name = blending === THREE.AdditiveBlending ? "vfx-glows" : "vfx-puffs";
  }

  private allocate(capacity: number): void {
    // three.js keys GPU buffers by attribute: release the old ones before replacing them.
    if (this.capacity > 0) this.geometry.dispose();
    const make = (name: string, itemSize: number, old?: THREE.InstancedBufferAttribute) => {
      const attr = new THREE.InstancedBufferAttribute(new Float32Array(capacity * itemSize), itemSize);
      attr.setUsage(THREE.DynamicDrawUsage);
      if (old) attr.array.set(old.array as Float32Array);
      this.geometry.setAttribute(name, attr);
      return attr;
    };
    this.head = make("aHead", 3, this.head);
    this.tail = make("aTail", 3, this.tail);
    this.params = make("aParams", 4, this.params);
    this.color = make("aColor", 4, this.color);
    this.attrs = [this.head, this.tail, this.params, this.color];
    this.capacity = capacity;
  }

  /**
   * Add a glow from tail to head (world positions), `radius` world units wide, with linear RGB and
   * alpha (or intensity, on additive layers). `tailFade` is the brightness at the tail (0..1).
   */
  add(hx: number, hy: number, hz: number, tx: number, ty: number, tz: number, radius: number,
    r: number, g: number, b: number, a: number, tailFade = 0, shape: GlowShape = GlowShape.Glow, seed = 0): void {
    if (this.count >= this.capacity) this.allocate(this.capacity * 2);
    const i = this.count++;
    const h = this.head.array as Float32Array;
    const t = this.tail.array as Float32Array;
    const p = this.params.array as Float32Array;
    const c = this.color.array as Float32Array;
    h[i * 3] = hx;
    h[i * 3 + 1] = hy;
    h[i * 3 + 2] = hz;
    t[i * 3] = tx;
    t[i * 3 + 1] = ty;
    t[i * 3 + 2] = tz;
    p[i * 4] = radius;
    p[i * 4 + 1] = tailFade;
    p[i * 4 + 2] = shape;
    p[i * 4 + 3] = seed;
    c[i * 4] = r;
    c[i * 4 + 1] = g;
    c[i * 4 + 2] = b;
    c[i * 4 + 3] = a;
  }

  /** Upload this frame's glows and start the next frame empty. */
  commit(): void {
    const n = this.count;
    this.geometry.instanceCount = n;
    this.mesh.visible = n > 0;
    if (n > 0) {
      for (const attr of this.attrs) {
        attr.clearUpdateRanges();
        attr.addUpdateRange(0, n * attr.itemSize);
        attr.needsUpdate = true;
      }
    }
    this.count = 0;
  }

  dispose(): void {
    this.geometry.dispose();
    (this.mesh.material as THREE.Material).dispose();
  }
}
