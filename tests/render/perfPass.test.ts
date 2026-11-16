// D206, the performance pass: the effects drawn once with two draws' output instead of a second time
// in the outline pass's render; the lights in the passes that draw a layer of their own (so three
// keeps every lit material's program); the under-shade pass drawn through a camera narrowed to the
// blended area; the models' geometry meshopt-compressed (tools/glb-meshopt.mjs).
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { MeshoptEncoder } from "meshoptimizer";
import { NdcRect } from "../../src/render/hueBlend";
import { PaletteTexture } from "../../src/render/paletteTexture";
import { UnderShadePass } from "../../src/render/underShade";
import { addLightsToLayer, restoreLights } from "../../src/render/passLights";
import { drawnTwicePars, VFX_DRAWN_TWICE } from "../../src/render/vfx/drawnTwice";
import { GlowLayer } from "../../src/render/vfx/glowLayer";
import { ParticleSystem } from "../../src/render/vfx/particles";
import { ShieldLayer } from "../../src/render/vfx/shieldLayer";
import { prepareModel } from "../../src/render/modelPrep";
// @ts-expect-error: a plain .mjs tool without types
import { compressGlb, readGlb, writeGlb } from "../../tools/glb-meshopt.mjs";

vi.stubGlobal("location", { search: "" });

/** The blend unit on one channel: one draw of (c, a) over dst, for `blending`. */
function blend(blending: THREE.Blending, dst: number, c: number, a: number): number {
  const s = Math.min(1, Math.max(0, c));
  const al = Math.min(1, Math.max(0, a));
  return Math.min(1, blending === THREE.AdditiveBlending ? dst + s * al : s * al + dst * (1 - al));
}

/** drawnTwice() (drawnTwicePars) evaluated in JS, as the GLSL computes it with the uniform at 1. */
function twice(blending: THREE.Blending, c: number, a: number): [number, number] {
  if (blending === THREE.AdditiveBlending) {
    const a2 = a * 2;
    const a1 = Math.min(a2, 1);
    return [c * (a2 / Math.max(a1, 1e-6)), a1];
  }
  return [c, a + a * (1 - a)];
}

describe("the effects, drawn once as if twice (D206)", () => {
  test("one draw with drawnTwice's output lands where two plain draws did, on the canvas", () => {
    for (const blending of [THREE.AdditiveBlending, THREE.NormalBlending]) {
      for (const dst of [0, 0.2, 0.7, 1])
        for (const c of [0, 0.3, 0.8, 1])
          for (const a of [0, 0.1, 0.45, 0.6, 1]) {
            const two = blend(blending, blend(blending, dst, c, a), c, a);
            const [c1, a1] = twice(blending, c, a);
            expect(blend(blending, dst, c1, a1), `${blending} dst ${dst} c ${c} a ${a}`).toBeCloseTo(two, 6);
          }
    }
    // The GLSL is the formula above.
    expect(drawnTwicePars(THREE.AdditiveBlending)).toContain("float a2 = c.a * (1.0 + uDrawnTwice);");
    expect(drawnTwicePars(THREE.NormalBlending)).toContain("c.a + uDrawnTwice * c.a * (1.0 - c.a)");
  });

  test("the glows, particles and shields leave the outline pass's render and share the switch", () => {
    const meshes = [
      new GlowLayer(THREE.AdditiveBlending, 4).mesh,
      new GlowLayer(THREE.NormalBlending, 4).mesh,
      new ParticleSystem(8, THREE.AdditiveBlending).mesh,
      new ParticleSystem(8, THREE.NormalBlending).mesh,
      new ShieldLayer().mesh,
    ];
    for (const m of meshes) {
      expect(m.userData.outlineSkip, m.name).toBe(true);
      const material = m.material as THREE.ShaderMaterial;
      expect(material.uniforms.uDrawnTwice, m.name).toBe(VFX_DRAWN_TWICE);
      expect(material.fragmentShader, m.name).toContain("gl_FragColor = drawnTwice(gl_FragColor);");
    }
    expect(VFX_DRAWN_TWICE.value).toBe(1);
  });

  test("a translucent model's depth prepass is left out of the outline pass's render", () => {
    const root = new THREE.Group();
    root.add(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial()));
    prepareModel(root);
    const prepass = root.children.find((o) => o.userData.depthPrepass)!;
    expect(prepass.userData.outlineSkip).toBe(true);
  });
});

describe("the lights in the passes with a layer of their own (D206)", () => {
  test("lights the camera sees join the layer, and go back as they were", () => {
    const camera = new THREE.Camera();
    const seen = new THREE.DirectionalLight();
    const hidden = new THREE.PointLight();
    hidden.layers.set(5);
    const lights = [seen, hidden];
    const masks = addLightsToLayer(lights, camera.layers, 29);
    expect(seen.layers.isEnabled(29)).toBe(true);
    expect(hidden.layers.isEnabled(29)).toBe(false);
    restoreLights(lights, masks);
    expect([seen.layers.mask, hidden.layers.mask]).toEqual([1, 1 << 5]);
  });

  test("the under-shade pass draws the lights too, through a camera narrowed to the blended area", () => {
    const scene = new THREE.Scene();
    const light = new THREE.DirectionalLight();
    scene.add(light, new THREE.Mesh(new THREE.PlaneGeometry(), new THREE.MeshStandardMaterial({ name: "pal_7" })));
    const camera = new THREE.PerspectiveCamera(40, 640 / 360, 0.1, 100);
    camera.position.set(1, 20, 3);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    const renders: { lights: number; camera: THREE.Camera; viewport: number[] }[] = [];
    let target: THREE.WebGLRenderTarget | null = null;
    const renderer = {
      autoClear: true,
      shadowMap: { autoUpdate: true },
      getRenderTarget: () => target,
      setRenderTarget: (t: THREE.WebGLRenderTarget | null) => (target = t),
      getDrawingBufferSize: (v: THREE.Vector2) => v.set(640, 360),
      getClearColor: (c: THREE.Color) => c,
      getClearAlpha: () => 1,
      setClearColor: () => {},
      render(s: THREE.Scene, c: THREE.Camera) {
        let lights = 0;
        s.traverseVisible((o) => void (o instanceof THREE.Light && o.layers.test(c.layers) && lights++));
        renders.push({ lights, camera: c, viewport: target!.viewport.toArray() });
      },
    } as unknown as THREE.WebGLRenderer;
    const pass = new UnderShadePass(new PaletteTexture());
    const area = new NdcRect();
    area.add(-0.5, -0.25);
    area.add(0.25, 0.5);
    pass.render(renderer, scene, camera, area);
    expect(renders).toHaveLength(1);
    expect(renders[0].lights).toBe(1);
    expect(light.layers.mask).toBe(1);
    // The scissored area is the viewport, and a world point lands on the same pixel through either camera.
    const [x, y, w, h] = renders[0].viewport;
    expect([x, y, w, h]).toEqual(pass.target.scissor.toArray());
    const narrowed = renders[0].camera;
    for (const p of [new THREE.Vector3(0, 0, 0), new THREE.Vector3(-2, 1, 1.5)]) {
      const full = p.clone().applyMatrix4(camera.matrixWorldInverse).applyMatrix4(camera.projectionMatrix);
      const crop = p.clone().applyMatrix4(narrowed.matrixWorldInverse).applyMatrix4(narrowed.projectionMatrix);
      expect(x + ((crop.x + 1) / 2) * w).toBeCloseTo(((full.x + 1) / 2) * 640, 6);
      expect(y + ((crop.y + 1) / 2) * h).toBeCloseTo(((full.y + 1) / 2) * 360, 6);
    }
  });
});

describe("the models' geometry, meshopt-compressed (tools/glb-meshopt.mjs, D206)", () => {
  /** A one-mesh glb: positions, normals, UVs and triangle indices, each in its own view. */
  function glb(n: number) {
    const pos = new Float32Array(n * 3).map((_, i) => Math.sin(i * 1.7) * 3.2);
    const nrm = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const v = new THREE.Vector3(Math.sin(i), Math.cos(i * 0.7), 0.3).normalize();
      nrm.set([v.x, v.y, v.z], i * 3);
    }
    const uv = new Float32Array(n * 2).map((_, i) => (i % 7) / 7);
    const idx = new Uint16Array(n * 3).map((_, i) => (i * 5) % n);
    const parts = [pos, nrm, uv, idx].map((a) => Buffer.from(a.buffer));
    let offset = 0;
    const views = parts.map((p) => {
      const v = { buffer: 0, byteOffset: offset, byteLength: p.length };
      offset += p.length;
      return v;
    });
    const json = {
      asset: { version: "2.0" },
      buffers: [{ byteLength: offset }],
      bufferViews: views,
      accessors: [
        { bufferView: 0, componentType: 5126, count: n, type: "VEC3", min: [-4, -4, -4], max: [4, 4, 4] },
        { bufferView: 1, componentType: 5126, count: n, type: "VEC3" },
        { bufferView: 2, componentType: 5126, count: n, type: "VEC2" },
        { bufferView: 3, componentType: 5123, count: n * 3, type: "SCALAR" },
      ],
      meshes: [{ primitives: [{ attributes: { POSITION: 0, NORMAL: 1, TEXCOORD_0: 2 }, indices: 3 }] }],
      nodes: [{ mesh: 0 }],
      scenes: [{ nodes: [0] }],
    };
    return { bytes: writeGlb(json, Buffer.concat(parts)), pos, nrm, uv, idx };
  }

  test("decodes to the same floats: positions within 2^-15 of the vector's largest coordinate, normals 2^-11, the rest exact", async () => {
    await MeshoptEncoder.ready;
    await MeshoptDecoder.ready;
    const src = glb(600);
    const out = compressGlb(src.bytes);
    expect(out).not.toBeNull();
    expect(out.length).toBeLessThan(src.bytes.length);
    const { json, bin } = readGlb(out);
    expect(json.extensionsRequired).toContain("EXT_meshopt_compression");
    const decode = (view: number, ctor: Float32ArrayConstructor | Uint16ArrayConstructor) => {
      const e = json.bufferViews[view].extensions.EXT_meshopt_compression;
      const target = new Uint8Array(e.count * e.byteStride);
      MeshoptDecoder.decodeGltfBuffer(target, e.count, e.byteStride, bin.subarray(e.byteOffset, e.byteOffset + e.byteLength), e.mode, e.filter ?? "NONE");
      return new ctor(target.buffer);
    };
    const pos = decode(0, Float32Array) as Float32Array;
    for (let i = 0; i < 600; i++) {
      const max = Math.max(...[0, 1, 2].map((k) => Math.abs(src.pos[i * 3 + k])));
      for (let k = 0; k < 3; k++) expect(Math.abs(pos[i * 3 + k] - src.pos[i * 3 + k])).toBeLessThanOrEqual(max / 32768 + 1e-7);
    }
    const nrm = decode(1, Float32Array) as Float32Array;
    for (let i = 0; i < nrm.length; i++) expect(Math.abs(nrm[i] - src.nrm[i])).toBeLessThan(1 / 2048 + 1e-7);
    expect(Array.from(decode(2, Float32Array))).toEqual(Array.from(src.uv));
    expect(Array.from(decode(3, Uint16Array))).toEqual(Array.from(src.idx));
    // Compressing again leaves it alone.
    expect(compressGlb(out)).toBeNull();
  });
});
