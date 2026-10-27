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
// is in the original). Pixels beyond the edge are clamped or wrapped, as the caller chooses; the
// reference clamps. The reference's src(x + 2, y - 1) etc. are the same reads as p[i - pw + 2].

/** How pixels outside the image are read. */
export type EdgeMode = "clamp" | "wrap";

/** Pixels MMPX reads beyond the one it's on. */
const REACH = 3;

/**
 * Double `pixels` (w x h palette indices). `luma[i]` orders indices by brightness. With `window`
 * (x, y, width, height in source pixels) only that part is computed, reading the image around it;
 * the result is then 2 * width x 2 * height.
 */
export function mmpx2x(
  pixels: Uint8Array,
  w: number,
  h: number,
  luma: ArrayLike<number>,
  edge: EdgeMode = "clamp",
  window: { x: number; y: number; w: number; h: number } = { x: 0, y: 0, w, h },
): Uint8Array {
  // Copy the image with REACH pixels around it (clamped or wrapped), so reads need no checks.
  const pw = w + 2 * REACH;
  const ph = h + 2 * REACH;
  const p = new Uint8Array(pw * ph);
  for (let y = 0; y < ph; y++) {
    let sy = y - REACH;
    sy = edge === "wrap" ? ((sy % h) + h) % h : sy < 0 ? 0 : sy >= h ? h - 1 : sy;
    for (let x = 0; x < pw; x++) {
      let sx = x - REACH;
      sx = edge === "wrap" ? ((sx % w) + w) % w : sx < 0 ? 0 : sx >= w ? w - 1 : sx;
      p[y * pw + x] = pixels[sy * w + sx];
    }
  }
  const ow = window.w * 2;
  const out = new Uint8Array(ow * window.h * 2);

  for (let wy = 0; wy < window.h; wy++) {
    const y = window.y + wy;
    for (let wx = 0; wx < window.w; wx++) {
      const x = window.x + wx;
      const i = (y + REACH) * pw + x + REACH; // the pixel in the padded copy
      //    P
      //   ABC
      // QDEFR
      //   GHI
      //    S
      const A = p[i - pw - 1], B = p[i - pw], C = p[i - pw + 1];
      const D = p[i - 1], E = p[i], F = p[i + 1];
      const G = p[i + pw - 1], H = p[i + pw], I = p[i + pw + 1];

      let J = E, K = E, L = E, M = E;

      if (A !== E || B !== E || C !== E || D !== E || F !== E || G !== E || H !== E || I !== E) {
        const P = p[i - 2 * pw], S = p[i + 2 * pw];
        const Q = p[i - 2], R = p[i + 2];
        const Bl = luma[B], Dl = luma[D], El = luma[E], Fl = luma[F], Hl = luma[H];

        // 1:1 slopes: round corners and fill diagonals, but keep sharp right angles.
        if (D === B && D !== H && D !== F && (El >= Dl || E === A) && any3(E, A, C, G) && (El < Dl || A !== D || E !== P || E !== Q)) J = D;
        if (B === F && B !== D && B !== H && (El >= Bl || E === C) && any3(E, A, C, I) && (El < Bl || C !== B || E !== P || E !== R)) K = B;
        if (H === D && H !== F && H !== B && (El >= Hl || E === G) && any3(E, A, G, I) && (El < Hl || G !== H || E !== S || E !== Q)) L = H;
        if (F === H && F !== B && F !== D && (El >= Fl || E === I) && any3(E, C, G, I) && (El < Fl || I !== H || E !== R || E !== S)) M = F;

        // Disconnected line intersections.
        if (E !== F && all4(E, C, I, D, Q) && all2(F, B, H) && F !== p[i + 3]) K = M = F;
        if (E !== D && all4(E, A, G, F, R) && all2(D, B, H) && D !== p[i - 3]) J = L = D;
        if (E !== H && all4(E, G, I, B, P) && all2(H, D, F) && H !== p[i + 3 * pw]) L = M = H;
        if (E !== B && all4(E, A, C, H, S) && all2(B, D, F) && B !== p[i - 3 * pw]) J = K = B;

        // Tips of bright triangles on dark backgrounds.
        if (Bl < El && all4(E, G, H, I, S) && none4(E, A, D, C, F)) J = K = B;
        if (Hl < El && all4(E, A, B, C, P) && none4(E, D, G, I, F)) L = M = H;
        if (Fl < El && all4(E, A, D, G, Q) && none4(E, B, C, I, H)) K = M = F;
        if (Dl < El && all4(E, C, F, I, R) && none4(E, B, A, G, H)) J = L = D;

        // 2:1 and 1:2 slopes of one colour. These extend colours the rules above chose.
        if (H !== B) {
          if (H !== A && H !== E && H !== C) {
            if (all3(H, G, F, R) && none2(H, D, p[i - pw + 2])) L = M;
            if (all3(H, I, D, Q) && none2(H, F, p[i - pw - 2])) M = L;
          }
          if (B !== I && B !== G && B !== E) {
            if (all3(B, A, F, R) && none2(B, D, p[i + pw + 2])) J = K;
            if (all3(B, C, D, Q) && none2(B, F, p[i + pw - 2])) K = J;
          }
        }
        if (F !== D) {
          if (D !== I && D !== E && D !== C) {
            if (all3(D, A, H, S) && none2(D, B, p[i + 2 * pw + 1])) J = L;
            if (all3(D, G, B, P) && none2(D, H, p[i - 2 * pw + 1])) L = J;
          }
          if (F !== E && F !== A && F !== G) {
            if (all3(F, C, H, S) && none2(F, B, p[i + 2 * pw - 1])) K = M;
            if (all3(F, I, B, P) && none2(F, H, p[i - 2 * pw - 1])) M = K;
          }
        }
      }

      const o = wy * 2 * ow + wx * 2;
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
