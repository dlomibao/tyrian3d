// A pooled GPU particle system: sparks, flashes, embers, smoke and debris.
//
// Each particle is one instance of a camera-facing quad. Everything about its flight is fixed when
// it's spawned (origin, velocity, gravity, lifetime, start and end size and colour) and the vertex
// shader works out where it is from the age alone, so the CPU touches a particle once, when it's
// born, and never per frame. Slots are a ring buffer: spawning writes the next slot (overwriting
// the oldest particle when it's full) and uploads only the slots written this frame. Dead
// particles stay in the buffer and the shader collapses them, so the draw count never changes and
// nothing is allocated after construction.

import * as THREE from "three";

/** The look of a particle, chosen per particle in the fragment shader. */
export const enum ParticleShape {
  /** A soft round glow. */
  Glow = 0,
  /** A streak stretched along its screen-space velocity. */
  Spark = 1,
  /** A soft, ragged puff. */
  Smoke = 2,
  /** A small tumbling chunk. */
  Debris = 3,
}

/**
 * A particle to spawn. Fill the fields of `ParticleSystem.spec` and call `spawn()`; the spec is
 * reused, so spawning allocates nothing. Positions and sizes are world units, times seconds.
 */
export interface ParticleSpec {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  /** Downward acceleration (world units/s²); the particle stops where it reaches the ground (y = 0). */
  gravity: number;
  /** Seconds from now until it appears (staggered smoke). */
  delay: number;
  life: number;
  /** Half-width at birth and at death (eased out between). */
  size0: number;
  size1: number;
  /** Sparks: extra length per unit of screen speed. */
  stretch: number;
  shape: ParticleShape;
  /** Linear RGB and alpha at birth and at death. */
  r0: number;
  g0: number;
  b0: number;
  a0: number;
  r1: number;
  g1: number;
  b1: number;
  a1: number;
}

const VERTEX = /* glsl */ `
attribute vec3 aOrigin;
attribute vec3 aVel;
attribute vec4 aTime;   // birth, life, gravity, time until it lands
attribute vec4 aSize;   // size0, size1, stretch, shape
attribute vec4 aCol0;
attribute vec4 aCol1;
uniform float uTime;
varying vec2 vUv;
varying vec4 vColor;
varying float vShape;
varying float vSeed;
varying float vT;

void main() {
  float age = uTime - aTime.x;
  float life = aTime.y;
  if (age < 0.0 || age >= life) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0); // outside the clip volume: nothing drawn
    return;
  }
  float t = age / life;
  float ta = min(age, aTime.w);
  vec3 p = aOrigin + aVel * ta;
  p.y -= 0.5 * aTime.z * ta * ta;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  float size = mix(aSize.x, aSize.y, 1.0 - (1.0 - t) * (1.0 - t));
  vec2 corner = position.xy;
  vSeed = fract(sin(dot(aOrigin.xz + aVel.xz, vec2(12.9898, 78.233))) * 43758.5453);
  vec2 offset = corner * size;
  if (aSize.w > 0.5 && aSize.w < 1.5) {
    // Spark: long along its screen-space velocity, thin across it.
    vec3 v = age < aTime.w ? aVel - vec3(0.0, aTime.z * ta, 0.0) : vec3(0.0);
    vec2 dir = (modelViewMatrix * vec4(v, 0.0)).xy;
    float len = length(dir);
    if (len > 1e-4) {
      dir /= len;
      offset = dir * corner.x * (size + len * aSize.z) + vec2(-dir.y, dir.x) * corner.y * size * 0.35;
    }
  } else if (aSize.w > 2.5) {
    // Debris tumbles.
    float a = vSeed * 6.2832 + age * (6.0 + 8.0 * vSeed);
    float c = cos(a), s = sin(a);
    offset = mat2(c, s, -s, c) * (corner * size * vec2(1.0, 0.6));
  }
  mv.xy += offset;
  gl_Position = projectionMatrix * mv;
  vUv = corner;
  vColor = mix(aCol0, aCol1, t);
  vShape = aSize.w;
  vT = t;
}
`;

const FRAGMENT = /* glsl */ `
varying vec2 vUv;
varying vec4 vColor;
varying float vShape;
varying float vSeed;
varying float vT;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}

void main() {
  float r = length(vUv);
  float a;
  vec3 rgb = vColor.rgb;
  if (vShape < 0.5) {
    if (r > 1.0) discard;
    a = (1.0 - r) * (1.0 - r);
    rgb *= 1.0 + 2.0 * a; // white-hot centre
  } else if (vShape < 1.5) {
    float across = 1.0 - abs(vUv.y);
    float along = 1.0 - abs(vUv.x);
    a = across * across * along;
    rgb *= 1.0 + across;
  } else if (vShape < 2.5) {
    float n = noise(vUv * 2.3 + vSeed * 17.0 + vT * 1.5) + 0.5 * noise(vUv * 4.7 - vSeed * 9.0);
    float edge = r + (n - 0.75) * 0.55;
    if (edge > 1.0) discard;
    a = smoothstep(1.0, 0.35, edge) * smoothstep(0.0, 0.12, vT);
    rgb *= 0.75 + 0.35 * n;
  } else {
    float m = max(abs(vUv.x), abs(vUv.y));
    a = smoothstep(1.0, 0.75, m);
    rgb *= 0.8 + 0.4 * (vUv.x * 0.5 + 0.5);
  }
  gl_FragColor = vec4(rgb, a * vColor.a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

const ATTRS = [
  ["aOrigin", 3],
  ["aVel", 3],
  ["aTime", 4],
  ["aSize", 4],
  ["aCol0", 4],
  ["aCol1", 4],
] as const;

export class ParticleSystem {
  readonly mesh: THREE.Mesh;
  /** Fill in and call spawn(). */
  readonly spec: ParticleSpec = {
    x: 0, y: 0, z: 0, vx: 0, vy: 0, vz: 0, gravity: 0, delay: 0, life: 1, size0: 1, size1: 1, stretch: 0,
    shape: ParticleShape.Glow, r0: 1, g0: 1, b0: 1, a0: 1, r1: 1, g1: 1, b1: 1, a1: 0,
  };
  private readonly attrs: THREE.InstancedBufferAttribute[] = [];
  private readonly origin: Float32Array;
  private readonly vel: Float32Array;
  private readonly time: Float32Array;
  private readonly size: Float32Array;
  private readonly col0: Float32Array;
  private readonly col1: Float32Array;
  private readonly material: THREE.ShaderMaterial;
  private cursor = 0;
  /** Slots written since the last upload: [start, start + count) around the ring. */
  private dirtyStart = 0;
  private dirtyCount = 0;
  private now = 0;
  /** Particles spawned in total, for stats and tests. */
  spawned = 0;

  constructor(readonly capacity: number, blending: THREE.Blending) {
    const geometry = new THREE.InstancedBufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3));
    geometry.setIndex([0, 1, 2, 0, 2, 3]);
    for (const [name, itemSize] of ATTRS) {
      const attr = new THREE.InstancedBufferAttribute(new Float32Array(capacity * itemSize), itemSize);
      attr.setUsage(THREE.DynamicDrawUsage);
      geometry.setAttribute(name, attr);
      this.attrs.push(attr);
    }
    // Every slot starts dead: born at -inf.
    const time = this.attrs[2].array as Float32Array;
    for (let i = 0; i < capacity; i++) time[i * 4] = -1e9;
    geometry.instanceCount = capacity;
    [this.origin, this.vel, this.time, this.size, this.col0, this.col1] = this.attrs.map((a) => a.array as Float32Array);

    this.material = new THREE.ShaderMaterial({
      vertexShader: VERTEX,
      fragmentShader: FRAGMENT,
      uniforms: { uTime: { value: 0 } },
      transparent: true,
      depthWrite: false,
      blending,
      userData: { outlineParameters: { visible: false } },
    });
    this.mesh = new THREE.Mesh(geometry, this.material);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = blending === THREE.AdditiveBlending ? 2 : 1;
    this.mesh.name = blending === THREE.AdditiveBlending ? "vfx-particles-additive" : "vfx-particles";
  }

  /** The clock the particles age by, in seconds. */
  get clock(): number {
    return this.now;
  }

  /** Advance the clock (display frames, so a paused game doesn't burn through its particles). */
  advance(dt: number): void {
    this.now += dt;
    this.material.uniforms.uTime.value = this.now;
  }

  /** Spawn a particle from `spec`. */
  spawn(): void {
    const s = this.spec;
    const i = this.cursor;
    this.cursor = (i + 1) % this.capacity;
    if (this.dirtyCount === 0) this.dirtyStart = i;
    if (this.dirtyCount < this.capacity) this.dirtyCount++;
    this.spawned++;

    let o = i * 3;
    this.origin[o] = s.x;
    this.origin[o + 1] = s.y;
    this.origin[o + 2] = s.z;
    this.vel[o] = s.vx;
    this.vel[o + 1] = s.vy;
    this.vel[o + 2] = s.vz;
    o = i * 4;
    this.time[o] = this.now + s.delay;
    this.time[o + 1] = s.life;
    this.time[o + 2] = s.gravity;
    this.time[o + 3] = landingTime(s.y, s.vy, s.gravity);
    this.size[o] = s.size0;
    this.size[o + 1] = s.size1;
    this.size[o + 2] = s.stretch;
    this.size[o + 3] = s.shape;
    this.col0[o] = s.r0;
    this.col0[o + 1] = s.g0;
    this.col0[o + 2] = s.b0;
    this.col0[o + 3] = s.a0;
    this.col1[o] = s.r1;
    this.col1[o + 1] = s.g1;
    this.col1[o + 2] = s.b1;
    this.col1[o + 3] = s.a1;
  }

  /** Upload the slots spawned since the last call. Call once per frame, before rendering. */
  flush(): void {
    const n = this.dirtyCount;
    if (n === 0) return;
    const start = this.dirtyStart;
    const first = Math.min(n, this.capacity - start);
    for (const attr of this.attrs) {
      const k = attr.itemSize;
      attr.clearUpdateRanges();
      attr.addUpdateRange(start * k, first * k);
      if (first < n) attr.addUpdateRange(0, (n - first) * k);
      attr.needsUpdate = true;
    }
    this.dirtyCount = 0;
  }

  /** Particles alive now (a scan of the ring; for stats and tests, not for every frame). */
  alive(): number {
    let n = 0;
    for (let i = 0; i < this.capacity; i++) {
      const age = this.now - this.time[i * 4];
      if (age >= 0 && age < this.time[i * 4 + 1]) n++;
    }
    return n;
  }

  /** Kill every particle (level change, switching effects off). */
  clear(): void {
    for (let i = 0; i < this.capacity; i++) this.time[i * 4] = -1e9;
    this.dirtyStart = 0;
    this.dirtyCount = this.capacity;
  }

  dispose(): void {
    this.mesh.geometry.dispose();
    this.material.dispose();
  }
}

/** Seconds until something at height y moving up at vy under `gravity` reaches y = 0 (Infinity if never). */
export function landingTime(y: number, vy: number, gravity: number): number {
  if (gravity <= 0) return vy < 0 ? Math.max(0, -y / vy) : 1e9;
  // y + vy t - g t² / 2 = 0
  const disc = vy * vy + 2 * gravity * y;
  return disc < 0 ? 1e9 : (vy + Math.sqrt(disc)) / gravity;
}
