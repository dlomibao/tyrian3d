// Where the ink outline is drawn in a frame (DECISIONS.md D146).
//
// OutlineEffect (outlineEffect.js) draws the outlines as a second pass over the finished frame,
// depth-tested only. The blended layers (the clouds' and ice's sheets, the flat sprite art and its
// explosions, the effects' particles and glows, a translucent ship) write no depth, so that pass
// painted every outline under them on top of them: a dome under TYRIAN's ice showed only its
// ink. The outlines belong to the opaque scene, so they are drawn inside the main pass instead,
// after everything that writes depth and before the first blended layer: three.js draws its
// translucent list in renderOrder order, and a hook object at OUTLINE_ORDER in that list runs the
// outline pass when it is reached. What is drawn later blends over the ink exactly as it blends
// over the model, so a covered model's outline fades or hides with it.

import * as THREE from "three";

/**
 * The outline pass's place among the translucent draws (their renderOrder): after the ones that
 * write depth (cutout terrain at -2, D132; an enemy's fading rock, FADE_ROCK_ORDER), before every
 * blended one (blend sheets at -1 or 1, the flat sprite art from -1, particles and glows at 1-2, a
 * translucent model at 3).
 */
export const OUTLINE_ORDER = -1.5;

/**
 * renderOrder of the meshes of an enemy's island rock that fades into the ground (D84): it is
 * translucent but writes depth, so it is drawn before the outlines (which it hides where it covers
 * them, as an opaque mesh does) and before the blend sheets (which cover it, as they cover the
 * model it belongs to).
 */
export const FADE_ROCK_ORDER = -1.75;

/**
 * An empty, never-drawn mesh in the translucent list at OUTLINE_ORDER that runs the outline pass
 * once when three.js reaches it in a draw armed by `draw`. Other draws of the scene (the screen
 * filters' mask, an effects-only redraw) pass it without effect.
 */
export class OutlineHook extends THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial> {
  private pending: (() => void) | null = null;

  constructor() {
    // No position attribute: three.js skips the draw call (an unbounded draw range). No normals:
    // OutlineEffect leaves it alone.
    super(
      new THREE.BufferGeometry(),
      new THREE.MeshBasicMaterial({
        name: "outline_hook",
        transparent: true,
        colorWrite: false,
        depthTest: false,
        depthWrite: false,
        userData: { outlineParameters: { visible: false } },
      }),
    );
    this.name = "outline-hook";
    this.renderOrder = OUTLINE_ORDER;
    this.frustumCulled = false;
    this.castShadow = false;
    this.receiveShadow = false;
    this.onBeforeRender = () => this.fire();
  }

  /**
   * Run `drawScene` (one render of the scene holding this hook) with `drawOutline` armed: it runs
   * when the render reaches the hook, or after the render if it never did (the hook culled or
   * hidden), so the outlines are never lost.
   */
  draw(drawScene: () => void, drawOutline: () => void): void {
    this.pending = drawOutline;
    try {
      drawScene();
      this.fire();
    } finally {
      this.pending = null;
    }
  }

  private fire(): void {
    const f = this.pending;
    this.pending = null;
    f?.();
  }
}
