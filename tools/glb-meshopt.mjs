// Compress the geometry of .glb files in place with EXT_meshopt_compression (DECISIONS.md D206).
//
//   node tools/glb-meshopt.mjs [--dry] [--min-kb N] file.glb ...
//
// The vertex and index buffers are encoded with meshoptimizer's codec, as Blender's own exporter
// can (export_meshopt_compression_enable): POSITION (and its morph target deltas) through the
// exponential filter at 16 bits of mantissa per vector (a vertex is kept within 2^-15 of its
// largest coordinate: 0.004 game pixels 10 units from a model's origin), NORMAL and TANGENT at 12 bits (as
// Blender's exporter does for both: within 0.03 degrees), everything else (UVs, colours, indices)
// losslessly. The decoded attributes are float32 as
// before, so no code that reads a model's geometry changes. The images, materials, nodes and extras
// are left byte for byte. A file already compressed, or one that would not shrink, is left alone.
//
// three.js decodes it with the MeshoptDecoder (models.ts); Blender 5.2's importer reads it too.

import { readFileSync, writeFileSync } from "node:fs";
import { MeshoptEncoder } from "meshoptimizer";

const EXT = "EXT_meshopt_compression";
/** Mantissa bits kept per vector by the exponential filter (Blender's exporter: 12 for both). */
const EXP_BITS = { POSITION: 16, NORMAL: 12, TANGENT: 12 };
const COMPONENTS = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
const BYTES = { 5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4 };

/** Parse a .glb into its JSON and binary chunk. */
export function readGlb(bytes) {
  if (bytes.readUInt32LE(0) !== 0x46546c67) throw new Error("not a glb");
  const jsonLen = bytes.readUInt32LE(12);
  const json = JSON.parse(bytes.subarray(20, 20 + jsonLen).toString("utf8"));
  const binStart = 20 + jsonLen;
  const bin = binStart < bytes.length ? bytes.subarray(binStart + 8, binStart + 8 + bytes.readUInt32LE(binStart)) : Buffer.alloc(0);
  return { json, bin };
}

/** Write a .glb from its JSON and binary chunk (each padded to 4 bytes). */
export function writeGlb(json, bin) {
  let text = Buffer.from(JSON.stringify(json), "utf8");
  if (text.length % 4) text = Buffer.concat([text, Buffer.alloc(4 - (text.length % 4), 0x20)]);
  let body = bin;
  if (body.length % 4) body = Buffer.concat([body, Buffer.alloc(4 - (body.length % 4))]);
  const header = Buffer.alloc(12);
  header.writeUInt32LE(0x46546c67, 0);
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(12 + 8 + text.length + (body.length ? 8 + body.length : 0), 8);
  const chunk = (len, type) => {
    const c = Buffer.alloc(8);
    c.writeUInt32LE(len, 0);
    c.writeUInt32LE(type, 4);
    return c;
  };
  return Buffer.concat([header, chunk(text.length, 0x4e4f534a), text, ...(body.length ? [chunk(body.length, 0x004e4942), body] : [])]);
}

/**
 * How each bufferView would be encoded: { mode, filter, count, stride, name } for views that hold
 * exactly one tightly packed accessor of a triangle mesh's attributes or indices; others are absent.
 */
function plan(json) {
  const uses = new Map(); // bufferView -> accessors using it
  (json.accessors ?? []).forEach((a, i) => {
    if (a.bufferView === undefined) return;
    if (!uses.has(a.bufferView)) uses.set(a.bufferView, []);
    uses.get(a.bufferView).push(i);
  });
  const roles = new Map(); // accessor -> { kind, name, triangles }
  for (const mesh of json.meshes ?? []) {
    for (const p of mesh.primitives) {
      for (const [name, a] of Object.entries(p.attributes)) roles.set(a, { kind: "attr", name });
      for (const t of p.targets ?? []) for (const [name, a] of Object.entries(t)) roles.set(a, { kind: "attr", name });
      if (p.indices !== undefined) roles.set(p.indices, { kind: "index", triangles: (p.mode ?? 4) === 4 });
    }
  }
  const out = new Map();
  for (const [view, accessors] of uses) {
    if (accessors.length !== 1) continue;
    const a = json.accessors[accessors[0]];
    const v = json.bufferViews[view];
    const role = roles.get(accessors[0]);
    if (!role || a.sparse || (a.byteOffset ?? 0) !== 0 || v.extensions?.[EXT]) continue;
    const size = COMPONENTS[a.type] * BYTES[a.componentType];
    if ((v.byteStride ?? size) !== size || v.byteLength !== size * a.count) continue;
    if (role.kind === "index") {
      if (size !== 2 && size !== 4) continue;
      out.set(view, { mode: role.triangles && a.count % 3 === 0 ? "TRIANGLES" : "INDICES", filter: "NONE", count: a.count, stride: size, name: "indices" });
    } else {
      if (size % 4 !== 0 || size > 256) continue;
      const exp = role.name in EXP_BITS && a.componentType === 5126 && !a.normalized;
      out.set(view, { mode: "ATTRIBUTES", filter: exp ? "EXPONENTIAL" : "NONE", count: a.count, stride: size, name: role.name });
    }
  }
  return out;
}

/** The glb with its geometry compressed, or null if there is nothing to gain. */
export function compressGlb(bytes) {
  const { json, bin } = readGlb(bytes);
  if (json.extensionsUsed?.includes(EXT) || (json.buffers ?? []).length !== 1) return null;
  const views = plan(json);
  if (views.size === 0) return null;
  const parts = [];
  let offset = 0;
  const push = (data) => {
    const start = offset;
    parts.push(data);
    offset += data.length;
    const pad = (4 - (offset % 4)) % 4;
    if (pad) {
      parts.push(Buffer.alloc(pad));
      offset += pad;
    }
    return start;
  };
  let fallback = 0;
  json.bufferViews.forEach((v, i) => {
    const src = bin.subarray(v.byteOffset ?? 0, (v.byteOffset ?? 0) + v.byteLength);
    const p = views.get(i);
    if (!p) {
      v.byteOffset = push(src);
      return;
    }
    let data = new Uint8Array(src.buffer, src.byteOffset, src.byteLength);
    if (p.filter === "EXPONENTIAL") {
      const f = new Float32Array(data.slice().buffer);
      data = MeshoptEncoder.encodeFilterExp(f, p.count, p.stride, EXP_BITS[p.name], "SharedVector");
    }
    const encoded = Buffer.from(MeshoptEncoder.encodeGltfBuffer(data, p.count, p.stride, p.mode));
    const ext = { buffer: 0, byteOffset: push(encoded), byteLength: encoded.length, byteStride: p.stride, count: p.count, mode: p.mode };
    if (p.filter !== "NONE") ext.filter = p.filter;
    // The view itself points at the uncompressed data's place in a fallback buffer with no data.
    v.buffer = 1;
    v.byteOffset = fallback;
    fallback += v.byteLength;
    fallback += (4 - (fallback % 4)) % 4;
    v.extensions = { ...(v.extensions ?? {}), [EXT]: ext };
  });
  const body = Buffer.concat(parts);
  json.buffers = [{ byteLength: body.length }, { byteLength: fallback, extensions: { [EXT]: { fallback: true } } }];
  json.extensionsUsed = [...new Set([...(json.extensionsUsed ?? []), EXT])];
  json.extensionsRequired = [...new Set([...(json.extensionsRequired ?? []), EXT])];
  const out = writeGlb(json, body);
  return out.length < bytes.length ? out : null;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const dry = args.includes("--dry");
  const minAt = args.indexOf("--min-kb");
  const minKb = minAt >= 0 ? Number(args[minAt + 1]) : 0;
  const files = args.filter((a, i) => a.endsWith(".glb") && args[i - 1] !== "--min-kb");
  await MeshoptEncoder.ready;
  let before = 0;
  let after = 0;
  for (const file of files) {
    const bytes = readFileSync(file);
    if (bytes.length < minKb * 1024) continue;
    const out = compressGlb(bytes);
    before += bytes.length;
    after += out ? out.length : bytes.length;
    console.log(`${file}: ${(bytes.length / 1024).toFixed(0)} KB -> ${out ? `${(out.length / 1024).toFixed(0)} KB` : "unchanged"}`);
    if (out && !dry) writeFileSync(file, out);
  }
  console.log(`total ${(before / 1048576).toFixed(1)} MB -> ${(after / 1048576).toFixed(1)} MB`);
}
