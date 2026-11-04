import type { Material, Mesh, Object3D, Texture } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { prepareModel } from "./modelPrep";
import { isRockSource } from "./rockMaterial";

const loader = new GLTFLoader();

/**
 * The largest side a model's texture is uploaded at (D91). A model fills a few hundred pixels of the
 * screen, so its baked maps (colour detail, normals, roughness) at 1024 still give each pixel a
 * texel or more; uploading a 2048 one stalled a frame ~50 ms (a 4096 one ~200 ms), and every model's
 * textures are uploaded during play when they load in the background.
 */
export const MAX_MODEL_TEXTURE = 1024;

/** Load a model exported by a script in assets/blender/ from public/models/<name>.glb. */
export async function loadModel(name: string): Promise<Object3D> {
  const gltf = await loader.loadAsync(`${import.meta.env.BASE_URL}models/${name}.glb`);
  await capTextures(gltf.scene);
  return prepareModel(gltf.scene);
}

/** The resize worker, started on first use; null where workers or ImageBitmap are missing. */
let worker: Worker | null | undefined;
const jobs = new Map<number, (bitmap: ImageBitmap | null) => void>();
let nextJob = 0;

function resizeWorker(): Worker | null {
  if (worker !== undefined) return worker;
  try {
    worker = new Worker(new URL("./textureResize.worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (e: MessageEvent<{ id: number; bitmap: ImageBitmap }>) => {
      jobs.get(e.data.id)?.(e.data.bitmap);
      jobs.delete(e.data.id);
    };
  } catch {
    worker = null;
  }
  return worker;
}

/**
 * `bitmap` scaled to width x height in the worker (it's transferred there: use the result instead),
 * or, if the worker couldn't, the same picture back; null without a worker (nothing transferred).
 */
function resized(bitmap: ImageBitmap, width: number, height: number): Promise<ImageBitmap | null> {
  const w = resizeWorker();
  if (!w) return Promise.resolve(null);
  const id = nextJob++;
  return new Promise((resolve) => {
    jobs.set(id, resolve);
    w.postMessage({ id, bitmap, width, height }, [bitmap]);
  });
}

/** Scale down (in a worker) every colour, normal and roughness texture larger than MAX_MODEL_TEXTURE. */
async function capTextures(root: Object3D): Promise<void> {
  if (typeof createImageBitmap !== "function" || typeof ImageBitmap === "undefined" || typeof Worker === "undefined") return;
  const textures = new Set<Texture>();
  // The island rock's textures hold palette data laid out per texel (D84): never resampled.
  const data = new Set<Texture>();
  root.traverse((o) => {
    const m = (o as Mesh).material as Material | Material[] | undefined;
    if (!m) return;
    for (const mat of Array.isArray(m) ? m : [m]) {
      for (const v of Object.values(mat)) if ((v as Texture | null)?.isTexture) (isRockSource(mat) ? data : textures).add(v as Texture);
    }
  });
  for (const t of data) textures.delete(t);
  const scaled = new Map<ImageBitmap, Promise<ImageBitmap | null>>();
  await Promise.all(
    [...textures].map(async (t) => {
      const image = t.image as unknown;
      if (!(image instanceof ImageBitmap)) return;
      const side = Math.max(image.width, image.height);
      if (side <= MAX_MODEL_TEXTURE) return;
      const k = MAX_MODEL_TEXTURE / side;
      let next = scaled.get(image);
      if (!next) scaled.set(image, (next = resized(image, Math.max(1, Math.round(image.width * k)), Math.max(1, Math.round(image.height * k)))));
      const bitmap = await next;
      if (!bitmap) return;
      t.image = bitmap;
      t.needsUpdate = true;
    }),
  );
}
