import type { Object3D } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { prepareModel } from "./modelPrep";

const loader = new GLTFLoader();

/** Load a model exported by a script in assets/blender/ from public/models/<name>.glb. */
export async function loadModel(name: string): Promise<Object3D> {
  const gltf = await loader.loadAsync(`${import.meta.env.BASE_URL}models/${name}.glb`);
  return prepareModel(gltf.scene);
}
