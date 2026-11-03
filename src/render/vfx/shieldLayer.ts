// The shield's hit flash (DECISIONS.md D67): the nine light-blue arcs JE_playerDamage draws round
// a ship whose shield took a hit, as one energy bubble round the ship model.
//
// Each bubble is an instance of a squashed sphere, additive, brightest at its rim (a fresnel term,
// so from above it reads as the original's ring), with a faint hexagonal cell pattern and a wave
// running from its middle out to the rim over the hit's three ticks. Like the glows (glowLayer.ts)
// they're rebuilt every display frame from the draw list, one instanced draw call, reused buffers.

import * as THREE from "three";

const VERTEX = /* glsl */ `
attribute vec3 aCentre;
attribute vec3 aScale;  // radii along x (across the screen), y (up) and z (down the screen)
attribute vec4 aColor;  // linear RGB, intensity
attribute vec2 aParams; // progress through the hit (0..1), seed
varying vec3 vWorld;
varying vec3 vNormal;
varying vec3 vLocal;
varying vec4 vColor;
varying vec2 vParams;

void main() {
  vec4 w = modelMatrix * vec4(aCentre + position * aScale, 1.0);
  vWorld = w.xyz;
  vNormal = normalize(mat3(modelMatrix) * (position / aScale));
  vLocal = position;
  vColor = aColor;
  vParams = aParams;
  gl_Position = projectionMatrix * viewMatrix * w;
}
`;

const FRAGMENT = /* glsl */ `
varying vec3 vWorld;
varying vec3 vNormal;
varying vec3 vLocal;
varying vec4 vColor;
varying vec2 vParams;

// Distance to the nearest edge of a hexagonal cell (0 on an edge, 0.5 in the middle).
float hexEdge(vec2 p) {
  const vec2 s = vec2(1.0, 1.7320508);
  vec4 c = floor(vec4(p, p - vec2(0.5, 1.0)) / s.xyxy) + 0.5;
  vec4 h = vec4(p - c.xy * s, p - (c.zw + 0.5) * s);
  vec2 q = dot(h.xy, h.xy) < dot(h.zw, h.zw) ? h.xy : h.zw;
  q = abs(q);
  return 0.5 - max(dot(q, s * 0.5), q.x);
}

void main() {
  vec3 n = normalize(vNormal);
  vec3 v = normalize(cameraPosition - vWorld);
  float facing = clamp(dot(n, v), 0.0, 1.0);
  float edge = 1.0 - facing;
  float t = vParams.x;
  float rim = edge * edge;
  rim *= rim;
  // The wave: from the middle (facing the camera) out to the rim as the hit goes on.
  float d = (edge - mix(0.15, 0.85, t)) / 0.12;
  float wave = exp(-d * d);
  // Cells seen from above, so they sit flat on the top of the bubble.
  float e = hexEdge(vLocal.xz * 4.0 + vParams.y * 7.0);
  float lines = 1.0 - smoothstep(0.0, 0.015 + 1.5 * fwidth(e), e);
  float a = 0.9 * rim + wave * (0.06 + 0.35 * lines) + lines * 0.18 * rim + 0.015;
  // The rim burns toward white.
  vec3 rgb = mix(vColor.rgb, vec3(1.0), clamp(0.25 * rim, 0.0, 0.25));
  gl_FragColor = vec4(rgb, a * vColor.a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

export class ShieldLayer {
  readonly mesh: THREE.Mesh;
  private readonly geometry = new THREE.InstancedBufferGeometry();
  private centre!: THREE.InstancedBufferAttribute;
  private scale!: THREE.InstancedBufferAttribute;
  private color!: THREE.InstancedBufferAttribute;
  private params!: THREE.InstancedBufferAttribute;
  private attrs: THREE.InstancedBufferAttribute[] = [];
  private capacity = 0;
  count = 0;

  constructor(capacity = 4) {
    const sphere = new THREE.SphereGeometry(1, 40, 20);
    this.geometry.setIndex(sphere.getIndex());
    this.geometry.setAttribute("position", sphere.getAttribute("position"));
    sphere.dispose();
    this.allocate(capacity);
    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX,
      fragmentShader: FRAGMENT,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      userData: { outlineParameters: { visible: false } },
    });
    this.mesh = new THREE.Mesh(this.geometry, material);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 2;
    this.mesh.name = "vfx-shield";
    this.mesh.visible = false;
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
    this.centre = make("aCentre", 3, this.centre);
    this.scale = make("aScale", 3, this.scale);
    this.color = make("aColor", 4, this.color);
    this.params = make("aParams", 2, this.params);
    this.attrs = [this.centre, this.scale, this.color, this.params];
    this.capacity = capacity;
  }

  /**
   * Add a bubble centred on (x, y, z) with radii (rx, ry, rz) (world units), linear RGB and
   * intensity, `t` of the way (0..1) through its hit.
   */
  add(x: number, y: number, z: number, rx: number, ry: number, rz: number, r: number, g: number, b: number, a: number, t: number, seed: number): void {
    if (this.count >= this.capacity) this.allocate(this.capacity * 2);
    const i = this.count++;
    const c = this.centre.array as Float32Array;
    const s = this.scale.array as Float32Array;
    const col = this.color.array as Float32Array;
    const p = this.params.array as Float32Array;
    c[i * 3] = x;
    c[i * 3 + 1] = y;
    c[i * 3 + 2] = z;
    s[i * 3] = rx;
    s[i * 3 + 1] = ry;
    s[i * 3 + 2] = rz;
    col[i * 4] = r;
    col[i * 4 + 1] = g;
    col[i * 4 + 2] = b;
    col[i * 4 + 3] = a;
    p[i * 2] = t;
    p[i * 2 + 1] = seed;
  }

  /** Upload this frame's bubbles and start the next frame empty. */
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
