"""Brown seed pod (newshh.shp frame 131): a 3D version of its sprite.

Seen in episode 2 (level 2.4). A gold beetle-like carapace, pointed at the bottom: a rounded
head cap in front, a pale rounded keel running from the cap to the tip (lit on its left, shaded on
its right), two shallow dark L-slots either side of the keel where it meets the cap, two tan ears
at the shoulders and two rounded lobes on the flanks. One frame.

The shell and cap are one smooth height field lofted down the sprite: a ring per row (closer
together round the cap join), each as wide as the sprite's row (outline pixels included). The
heights follow a smoothed outline, so the stepped pixel edge doesn't crease the dome, and fall
gently to 1-2 px at the edge instead of standing as side walls. Each top face takes the palette
shade of the sprite pixel under it, blended with the pixels above and below, bucketed into a few
shades.

Run: blender --background --python assets/blender/enemies/newshh-131.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b018 as lib  # noqa: E402

NAME = "newshh-131"

# Palette shades used, darkest first, and which shade each sprite index is painted with.
SHADES = [16, 18, 20, 22, 24, 26, 29]
BUCKET = {16: 16, 17: 18, 18: 18, 19: 20, 20: 20, 21: 22, 22: 22, 23: 24,
          24: 24, 25: 24, 26: 26, 27: 26, 28: 26, 29: 29, 30: 29, 31: 29}
EAR = 23  # the ears' tan

# Heights in sprite px.
RIM = 0.6  # the shell's edge
BELLY = 1.2  # below z = 0 at the middle
SHELL = 8.6  # the dome at the centreline, behind the head (keel not included)
KEEL = 2.5  # how far the keel stands proud of the dome at its top
HEAD = 10.8  # top of the head cap
FLANK = 0.85  # cross-section exponent: under 1 rounds the shell, 1 is a parabola (no side walls)
CX = 12.5  # the sprite is symmetric about column 12's centre


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def band(a, b, soft, x):
    """1 between a and b, easing to 0 over `soft` outside them."""
    return smoothstep(a - soft, a, x) * (1 - smoothstep(b, b + soft, x))


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = [common.palette_material(sprite, i, NAME, metallic=0.12, roughness=0.5) for i in SHADES + [EAR]]
    mat_of = {idx: k for k, idx in enumerate(SHADES + [EAR])}
    pixels = sprite["frames"][0]["pixels"]
    H, W = len(pixels), len(pixels[0])

    # Each row's half width (px) about the centre, outline pixels included; rows 4-8 leave out the
    # ears (columns 2-4 and 20-22).
    hw_row = {}
    for r in range(H):
        cols = [c for c, v in enumerate(pixels[r]) if v != -1 and not (4 <= r <= 8 and not 5 <= c <= 19)]
        if cols:
            hw_row[r] = (max(cols) + 1 - min(cols)) / 2 + 0.15
    last = max(hw_row)

    def interp(table, v):
        # Linear between row centres.
        x = v - 0.5
        r0 = math.floor(x)
        f = x - r0
        a = table[min(max(r0, 0), last)]
        b = table[min(max(r0 + 1, 0), last)]
        return a + (b - a) * f if 0 <= x else a

    # The outline the heights follow: the rows' widths averaged over a few rows, so the stepped
    # pixel outline doesn't crease the shell (the rings themselves still follow the pixel outline).
    weights = (1, 2, 3, 2, 1)
    hw_smooth = {}
    for r in range(last + 1):
        acc = tot = 0.0
        for k, wgt in zip(range(-2, 3), weights):
            if r + k in hw_row:
                acc += wgt * hw_row[r + k]
                tot += wgt
        hw_smooth[r] = max(acc / tot, hw_row[r] - 0.6)

    def hw(v):
        return interp(hw_row, v)

    def hws(v):
        return interp(hw_smooth, v)

    def head_top(v, du):
        if v <= 3.0:
            h = HEAD * max(0.0, 1 - ((v - 3.0) / 3.0) ** 2) ** 0.8  # a rounded brow, not a wall
        else:
            h = HEAD - 1.0 * (v - 3.0) / 1.3
        h = max(h, RIM)
        t = min(1.0, abs(du) / hws(v))
        return RIM + (h - RIM) * (1 - t * t) ** 0.75

    def keel(v):
        # How far the keel stands proud, and its width (sigma, px): full height from row 6,
        # tapering in both down the body and fading out at the tip.
        k = KEEL * (0.55 + 0.45 * smoothstep(4.4, 6.5, v)) * (1 - 0.45 * smoothstep(12.0, 23.0, v))
        k *= 1 - smoothstep(23.0, 26.0, v)
        sig = 1.6 - 0.6 * smoothstep(12.0, 24.0, v)
        return k, sig

    def body_top(v, du):
        t = min(1.0, abs(du) / hws(v))
        # The dome: level behind the head, falling in a smooth arch to the tip.
        e = max(0.0, v - 11.0) / 15.2
        s = RIM + (SHELL - RIM) * max(0.0, 1 - e * e) ** 0.55
        z = RIM + (s - RIM) * (1 - t * t) ** FLANK
        # The keel: a rounded pale ridge running from the cap to the tip.
        k, sig = keel(v)
        z += k * math.exp(-(du / sig) ** 2)
        # The shoulder lobes (rows 9-15, columns 2-7 and 17-22): rounded pads on the flanks.
        for side in (-1, 1):
            r2 = ((du - side * 7.6) / 3.4) ** 2 + ((v - 12.8) / 4.4) ** 2
            if r2 < 1:
                z += 3.3 * (1 - r2) ** 1.6
        # Two shallow L-slots either side of the keel at the cap join: across row 4 (columns 7-10
        # and 14-17) and down beside the keel (columns 10 and 14, rows 4-7).
        a = abs(du)
        cut = max(band(1.6, 5.4, 0.5, a) * band(4.3, 4.9, 0.45, v),
                  band(1.6, 2.6, 0.45, a) * band(4.3, 7.2, 0.5, v))
        z -= 1.5 * cut
        return z

    def top(v, du):
        if v < 4.3:
            return head_top(v, du)
        if v < 4.45:
            return max(head_top(v, du), body_top(v, du))
        return body_top(v, du)

    def ramp(r, c):
        # The sprite's shade (16-31) at a pixel, or None for outline and empty pixels.
        if not (0 <= r < H and 0 <= c < W):
            return None
        idx = pixels[r][c]
        return idx if idx >= 16 else None

    def shade(u, v):
        # The pixel's shade, blended with the pixels above and below it so single-pixel speckle
        # evens out along the sprite's lengthwise bands (the keel, its shadow, the flanks) without
        # blurring across them; outline pixels take the darkest shade.
        r, c = int(math.floor(v)), int(math.floor(u))
        centre = ramp(r, c)
        if centre is None:
            return mat_of[16]
        acc, tot = 2.0 * centre, 2.0
        for dr, dc, wgt in ((-1, 0, 1), (1, 0, 1)):
            n = ramp(r + dr, c + dc)
            if n is not None:
                acc += wgt * n
                tot += wgt
        return mat_of[BUCKET[min(31, max(16, round(acc / tot)))]]

    # Rings: v down the sprite (px from its top edge).
    vs = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.3, 4.45, 4.8, 5.2, 5.6, 6.0, 6.5, 7.0, 7.6]
    vs += [8.25 + 0.75 * k for k in range(20)]  # 8.25 .. 22.5
    vs += [23.0, 23.5, 24.0, 24.5, 25.0, 25.5]
    tip_v = 26.0
    N = 14  # top points per side
    ts = [-(k / N) ** 1.3 for k in range(N, 0, -1)] + [0.0] + [(k / N) ** 1.3 for k in range(1, N + 1)]
    bottom_ts = [0.6, 0.0, -0.6]

    def to3(u, v, z):
        return ((u - 12) / 12, (14 - v) / 12, z / 12)

    bm = bmesh.new()
    rings = []
    for v in vs:
        w = hw(v)
        ring = [to3(CX + t * w, v, top(v, t * w)) for t in ts]
        ring += [to3(CX + t * w, v, -BELLY * math.sqrt(1 - t * t)) for t in bottom_ts]
        rings.append([bm.verts.new(p) for p in ring])
    tip = bm.verts.new(to3(CX, tip_v, 0.0))
    n = len(rings[0])
    ntop = len(ts) - 1  # top faces per band
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        vc = (vs[i] + vs[i + 1]) / 2
        wc = hw(vc)
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            f.material_index = shade(CX + (ts[k] + ts[j]) / 2 * wc, vc) if k < ntop else mat_of[20]
            f.smooth = True
    for k in range(n):
        j = (k + 1) % n
        f = bm.faces.new((rings[-1][k], rings[-1][j], tip))
        f.material_index = shade(CX, 25.5) if k < ntop else mat_of[20]
        f.smooth = True
    f = bm.faces.new(list(reversed(rings[0])))
    f.material_index = mat_of[20]
    f.smooth = True

    # The ears (rows 4-8, columns 2-5 and 19-22): tan blocks slanting out and back from the
    # shoulders, about 3 px wide and 3 px tall, rounded at the ends.
    v0, f0 = len(bm.verts), len(bm.faces)
    lib.tube(bm, [to3(5.4, 4.0, 1.6), to3(4.7, 4.9, 1.8), to3(3.6, 6.6, 1.8), to3(3.7, 8.0, 1.7),
                  to3(4.1, 8.7, 1.5)],
             [0.8 / 12, 1.25 / 12, 1.55 / 12, 1.2 / 12, 0.7 / 12], sides=8, flat=1.0, mat=mat_of[EAR])
    # Only their tops are tan; their sides are as dark as the sprite's outline round them.
    bm.faces.ensure_lookup_table()
    for f in bm.faces[f0:]:
        if f.calc_center_median().z < 2.75 / 12:
            f.material_index = mat_of[16]
    lib.mirror_new(bm, v0, f0, axis_x=0.0 + (CX - 12) / 12)

    obj = lib.to_object(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"], 0)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
