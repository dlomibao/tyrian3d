// The effects' look as it was when the outline pass drew them a second time (DECISIONS.md D206).
//
// OutlineEffect's render of the scene (outlineEffect.js, inside the main render, D146) drew every
// object it has no outline material for with that object's own material: each glow, particle,
// shield and flat sprite was drawn twice a frame, and D169 tuned the glows as they looked so. They
// are now left out of that render (userData.outlineSkip) and drawn once, with the output a second
// identical draw would have added:
// - additive (src * alpha + dst): twice the alpha. Past 1 the rest goes into the colour; where that
//   clamps, two draws had already reached white.
// - alpha blending: alpha a(2 - a), the same colour. Two draws give c a(2 - a) + dst (1 - a)^2.
// Both are exact on the canvas while nothing is drawn between the two copies; the first copy used to
// land at the outline pass's place in the frame, under the blend sheets and flat art, so only where an
// effect overlaps those does today's frame differ, by a part of the effect's own soft edge.

import * as THREE from "three";

/**
 * 1 while the effects draw as if twice (the main render), 0 for one plain draw. The screen filters
 * draw the effects over the filtered frame in a render of their own (ScreenFilterPass.renderOver),
 * which never had the outline pass's copy: they set it to 0 there, so the smoothie levels keep their
 * look too.
 */
export const VFX_DRAWN_TWICE = { value: 1 };

/** The GLSL that turns one draw's output into two draws' (`drawnTwice(gl_FragColor)`, after tone mapping and colour space). */
export function drawnTwicePars(blending: THREE.Blending, uniform = "uDrawnTwice"): string {
  const body =
    blending === THREE.AdditiveBlending
      ? `float a2 = c.a * (1.0 + ${uniform});
  float a = min(a2, 1.0);
  return vec4(c.rgb * (a2 / max(a, 1e-6)), a);`
      : `return vec4(c.rgb, c.a + ${uniform} * c.a * (1.0 - c.a));`;
  return /* glsl */ `
uniform float ${uniform};
vec4 drawnTwice(vec4 c) {
  ${body}
}
`;
}
