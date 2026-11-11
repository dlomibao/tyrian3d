// The ink outline is drawn inside the main pass, before the blended layers (src/render/outlineHook.ts,
// DECISIONS.md D146): the hook's place in three.js's translucent draw order, and when it runs.
import * as THREE from "three";
import { WebGLRenderList } from "three/src/renderers/webgl/WebGLRenderLists.js";
import { describe, expect, test } from "vitest";
import { blendSheetOrder, CUTOUT_ORDER } from "../../src/render/drawListRenderer";
import { BLENDED_MODEL_ORDER, setModelBlended } from "../../src/render/modelPrep";
import { FADE_ROCK_ORDER, OUTLINE_ORDER, OutlineHook } from "../../src/render/outlineHook";
import { SPRITE_ART_ORDER } from "../../src/render/spriteArtLayer";
import { Pass } from "../../src/sim/draw";

/** A translucent mesh at `order`, as three.js would list it. */
function translucent(name: string, order: number, depthWrite = false): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial({ transparent: true, depthWrite }));
  m.name = name;
  m.renderOrder = order;
  return m;
}

/** The names of `objects` in the order three.js draws its translucent list, at camera depths `z`. */
function drawOrder(objects: THREE.Mesh[], z: (i: number) => number): string[] {
  const list = new WebGLRenderList({} as never);
  list.init();
  // three r186's push takes the camera too (for a reversed depth buffer); its types don't say so yet.
  const push = list.push as (...args: unknown[]) => void;
  const camera = new THREE.PerspectiveCamera();
  objects.forEach((o, i) => push(o, o.geometry, o.material, 0, z(i), null, camera));
  list.finish();
  list.sort(null as never, null as never, false);
  return list.transparent.map((item) => item.object.name);
}

describe("outline hook (D146)", () => {
  const hook = new OutlineHook();
  const depthWriting = [translucent("cutout cloud", CUTOUT_ORDER, true), translucent("fading rock", FADE_ROCK_ORDER, true)];
  const blended = [
    translucent("ice sheet", blendSheetOrder(Pass.Background2Mid)),
    translucent("top sheet", blendSheetOrder(Pass.Background2Top)),
    translucent("shot art", SPRITE_ART_ORDER + Pass.PlayerShots / 100),
    translucent("explosion stencil", SPRITE_ART_ORDER + Pass.Explosions / 100 - 0.001),
    translucent("explosion art", SPRITE_ART_ORDER + Pass.Explosions / 100),
    translucent("blended sprite", 0),
    translucent("scorch", 0),
    translucent("puffs", 1),
    translucent("glows", 2),
    translucent("translucent ship prepass", BLENDED_MODEL_ORDER - 0.001, true),
    translucent("translucent ship", BLENDED_MODEL_ORDER),
  ];

  test("comes after everything translucent that writes depth and before every blended layer, at any depth", () => {
    const all = [...blended, hook, ...depthWriting];
    for (const z of [(i: number) => i, (i: number) => -i, (i: number) => (i * 7919) % 13]) {
      const order = drawOrder(all, z);
      const at = order.indexOf("outline-hook");
      expect(order.slice(0, at).sort()).toEqual(depthWriting.map((o) => o.name).sort());
      expect(order.slice(at + 1).sort()).toEqual(blended.map((o) => o.name).sort());
    }
    expect(OUTLINE_ORDER).toBeGreaterThan(Math.max(CUTOUT_ORDER, FADE_ROCK_ORDER));
  });

  test("runs the outline once, when the draw reaches it", () => {
    const calls: string[] = [];
    hook.draw(
      () => {
        calls.push("opaque");
        hook.onBeforeRender(null as never, null as never, null as never, null as never, null as never, null as never);
        calls.push("blended");
      },
      () => calls.push("outline"),
    );
    expect(calls).toEqual(["opaque", "outline", "blended"]);
  });

  test("runs the outline after the draw if the draw never reached it; other draws never run it", () => {
    const calls: string[] = [];
    hook.draw(() => calls.push("scene"), () => calls.push("outline"));
    expect(calls).toEqual(["scene", "outline"]);
    hook.onBeforeRender(null as never, null as never, null as never, null as never, null as never, null as never);
    expect(calls).toEqual(["scene", "outline"]);
  });

  test("an enemy's fading rock keeps its order when its model turns opaque again", () => {
    const root = new THREE.Group();
    const rock = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
    const hull = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
    rock.renderOrder = rock.userData.renderOrder = FADE_ROCK_ORDER;
    root.add(rock, hull);
    setModelBlended(root, true);
    expect(rock.renderOrder).toBe(BLENDED_MODEL_ORDER);
    setModelBlended(root, false);
    expect(rock.renderOrder).toBe(FADE_ROCK_ORDER);
    expect(hull.renderOrder).toBe(0);
  });
});
