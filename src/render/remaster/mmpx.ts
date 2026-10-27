// MMPX pixel-art magnification on palette indices (DECISIONS.md D34).
//
// Port of runMMPX2X from the MMPX reference code (Morgan McGuire and Mara Gagiu, "MMPX
// Style-Preserving Pixel Art Magnification", JCGT 2021; js-demo.html in the paper's supplement,
// MIT licence, see CREDITS.md). MMPX doubles an image while reconstructing curves, diagonals and
// sharp corners, and it never invents a colour: every output pixel is one of the input pixels. That
// is what lets the remastered ground keep palette indices, so level palettes, fades and
// JE_filterScreen still apply to it (D7). Applied twice it gives 4x.
//
// Changes from the reference: pixels are palette indices instead of RGBA, the luminance used to
// break ties comes from a 256-entry table (the palette's), and there is no alpha case (ground
// tiles are opaque; for transparent layers index 0 is given the lowest luminance, as transparent
// is in the original). The source is read through `src(x, y)` with the edge handling chosen by
// the caller (clamp, or wrap for tiles that repeat).

/** How pixels outside the image are read. */
export type EdgeMode = "clamp" | "wrap";

/** Double `pixels` (w x h palette indices). `luma[i]` orders indices by brightness. */
export function mmpx2x(pixels: Uint8Array, w: number, h: number, luma: ArrayLike<number>, edge: EdgeMode = "clamp"): Uint8Array {
  const out = new Uint8Array(w * h * 4);
  const src =
    edge === "wrap"
      ? (x: number, y: number) => pixels[(((x % w) + w) % w) + (((y % h) + h) % h) * w]
      : (x: number, y: number) => pixels[Math.max(0, Math.min(x, w - 1)) + Math.max(0, Math.min(y, h - 1)) * w];
  const ow = w * 2;

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      //    P
      //   ABC
      // QDEFR
      //   GHI
      //    S
      const A = src(x - 1, y - 1), B = src(x, y - 1), C = src(x + 1, y - 1);
      const D = src(x - 1, y), E = src(x, y), F = src(x + 1, y);
      const G = src(x - 1, y + 1), H = src(x, y + 1), I = src(x + 1, y + 1);

      let J = E, K = E, L = E, M = E;

      if (A !== E || B !== E || C !== E || D !== E || F !== E || G !== E || H !== E || I !== E) {
        const P = src(x, y - 2), S = src(x, y + 2);
        const Q = src(x - 2, y), R = src(x + 2, y);
        const Bl = luma[B], Dl = luma[D], El = luma[E], Fl = luma[F], Hl = luma[H];

        // 1:1 slopes: round corners and fill diagonals, but keep sharp right angles.
        if (D === B && D !== H && D !== F && (El >= Dl || E === A) && any3(E, A, C, G) && (El < Dl || A !== D || E !== P || E !== Q)) J = D;
        if (B === F && B !== D && B !== H && (El >= Bl || E === C) && any3(E, A, C, I) && (El < Bl || C !== B || E !== P || E !== R)) K = B;
        if (H === D && H !== F && H !== B && (El >= Hl || E === G) && any3(E, A, G, I) && (El < Hl || G !== H || E !== S || E !== Q)) L = H;
        if (F === H && F !== B && F !== D && (El >= Fl || E === I) && any3(E, C, G, I) && (El < Fl || I !== H || E !== R || E !== S)) M = F;

        // Disconnected line intersections.
        if (E !== F && all4(E, C, I, D, Q) && all2(F, B, H) && F !== src(x + 3, y)) K = M = F;
        if (E !== D && all4(E, A, G, F, R) && all2(D, B, H) && D !== src(x - 3, y)) J = L = D;
        if (E !== H && all4(E, G, I, B, P) && all2(H, D, F) && H !== src(x, y + 3)) L = M = H;
        if (E !== B && all4(E, A, C, H, S) && all2(B, D, F) && B !== src(x, y - 3)) J = K = B;

        // Tips of bright triangles on dark backgrounds.
        if (Bl < El && all4(E, G, H, I, S) && none4(E, A, D, C, F)) J = K = B;
        if (Hl < El && all4(E, A, B, C, P) && none4(E, D, G, I, F)) L = M = H;
        if (Fl < El && all4(E, A, D, G, Q) && none4(E, B, C, I, H)) K = M = F;
        if (Dl < El && all4(E, C, F, I, R) && none4(E, B, A, G, H)) J = L = D;

        // 2:1 and 1:2 slopes of one colour. These extend colours the rules above chose.
        if (H !== B) {
          if (H !== A && H !== E && H !== C) {
            if (all3(H, G, F, R) && none2(H, D, src(x + 2, y - 1))) L = M;
            if (all3(H, I, D, Q) && none2(H, F, src(x - 2, y - 1))) M = L;
          }
          if (B !== I && B !== G && B !== E) {
            if (all3(B, A, F, R) && none2(B, D, src(x + 2, y + 1))) J = K;
            if (all3(B, C, D, Q) && none2(B, F, src(x - 2, y + 1))) K = J;
          }
        }
        if (F !== D) {
          if (D !== I && D !== E && D !== C) {
            if (all3(D, A, H, S) && none2(D, B, src(x + 1, y + 2))) J = L;
            if (all3(D, G, B, P) && none2(D, H, src(x + 1, y - 2))) L = J;
          }
          if (F !== E && F !== A && F !== G) {
            if (all3(F, C, H, S) && none2(F, B, src(x - 1, y + 2))) K = M;
            if (all3(F, I, B, P) && none2(F, H, src(x - 1, y - 2))) M = K;
          }
        }
      }

      const o = y * 2 * ow + x * 2;
      out[o] = J;
      out[o + 1] = K;
      out[o + ow] = L;
      out[o + ow + 1] = M;
    }
  }
  return out;
}

/** MMPX twice: 4x. The second pass wraps if the first did, so a repeating tile still repeats. */
export function mmpx4x(pixels: Uint8Array, w: number, h: number, luma: ArrayLike<number>, edge: EdgeMode = "clamp"): Uint8Array {
  return mmpx2x(mmpx2x(pixels, w, h, luma, edge), w * 2, h * 2, luma, edge);
}

/**
 * Luminance per palette index from 256 RGB triples (any scale), as the reference's luma(): the sum
 * of the channels, plus one so that black is brighter than "transparent" (index 0 on layers 1-2).
 */
export function paletteLuma(rgb: ArrayLike<number>, transparentZero = false): Float32Array {
  const luma = new Float32Array(256);
  for (let i = 0; i < 256; i++) luma[i] = rgb[i * 3] + rgb[i * 3 + 1] + rgb[i * 3 + 2] + 1;
  if (transparentZero) luma[0] = 0;
  return luma;
}

/**
 * Whether a tile repeats seamlessly with itself: its opposite edges continue each other. Wrapping
 * the upscaler's reads for such a tile (instead of clamping) keeps it seamless with its own copies,
 * which is how most of the ground is laid. Compares the edge rows and columns with a tolerance.
 */
export function tilesWithItself(pixels: Uint8Array, w: number, h: number): boolean {
  let same = 0;
  for (let x = 0; x < w; x++) if (pixels[x] === pixels[(h - 1) * w + x]) same++;
  for (let y = 0; y < h; y++) if (pixels[y * w] === pixels[y * w + w - 1]) same++;
  // Texture tiles aren't pixel-identical at their edges, they continue each other; a third of the
  // edge pixels matching their opposite is far above what unrelated edges share.
  return same >= (w + h) / 3;
}

const any3 = (b: number, a0: number, a1: number, a2: number) => b === a0 || b === a1 || b === a2;
const all2 = (b: number, a0: number, a1: number) => b === a0 && b === a1;
const all3 = (b: number, a0: number, a1: number, a2: number) => b === a0 && b === a1 && b === a2;
const all4 = (b: number, a0: number, a1: number, a2: number, a3: number) => b === a0 && b === a1 && b === a2 && b === a3;
const none2 = (b: number, a0: number, a1: number) => b !== a0 && b !== a1;
const none4 = (b: number, a0: number, a1: number, a2: number, a3: number) => b !== a0 && b !== a1 && b !== a2 && b !== a3;
