import type { Object3D } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MODEL_OVERRIDES, type DrawListRenderer } from "./drawListRenderer";

const loader = new GLTFLoader();

/** Load a model exported by assets/blender/<name>.py from public/models/. */
export async function loadModel(name: string): Promise<Object3D> {
  const gltf = await loader.loadAsync(`${import.meta.env.BASE_URL}models/${name}.glb`);
  return gltf.scene;
}

/**
 * Load every model in MODEL_OVERRIDES and register it with the draw-list renderer. Models that
 * fail to load are skipped (their sprites stay extruded). Pass already-loaded models by name to
 * avoid fetching them twice.
 */
export async function loadModelOverrides(draws: DrawListRenderer, loaded: Record<string, Object3D> = {}): Promise<void> {
  await Promise.all(
    MODEL_OVERRIDES.map(async (override) => {
      try {
        const model = loaded[override.model] ?? (await loadModel(override.model));
        draws.addModelOverride(override, model);
      } catch (err) {
        console.error(`model ${override.model} failed to load; its sprite stays extruded`, err);
      }
    }),
  );
}
