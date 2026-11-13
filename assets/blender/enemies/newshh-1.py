"""Eye block (newshh.shp frames 1, 3, 39), design A: an eye-turret set in a block of GYGES's
organic wall.

What it is: a square block of the scaly blue-grey wall (it drifts with the scenery at +2 px/tick,
rows of four 72 px apart), filling its whole 24x28 tile. A fleshy tan ring of lumpy lips sits on a
low boss in the middle; inside the lips a grey stone lip, a dark socket and an eyeball whose iris
is dark on frame 39, dim green on frame 1 and wide open, bright green with a white-hot pupil on
frame 3 (ani 7: 39 -> 1 -> 3).

Build: everything in sprite px (x = column, y = row down the sprite, z = px up), converted at the
end (X = (x - 12) / 12, Y = (14 - y) / 12, Z = z / 12).
  * block: a core box inset 0.6 px, its four sides clad in vertical scale ribs (the wall), its top
    in columns of overlapping scale plates (2 px columns, shingled: each plate's lower end lifted,
    a chamfered ridge so it has a lit and a shaded facet). Each facet takes a shade of the
    sprite's own stone ramp (96..111), ranked by how it faces the art light (upper left) and the
    sprite's brightness under it, matched to the sprite's distribution of stone shades (D175).
  * boss: a low stone mound under the ring (its lit and shadowed flank is the sprite's grey and
    dark border round the ring).
  * ring: a lofted lumpy torus traced from the sprite's tan pixels (polar fit of inner/outer
    radius), nine lobes; tan ramp shading the same way, compressed.
  * stone lip, socket (dark, glow spill on frame 3), eyeball and irises (frame parts).
Underside: the core box's flat bottom, closed.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshh-1.py
(or Blender --background --python newshh-1.py -- [--sheet sheet.png] [--measure dir])
Exports public/models/enemies/newshh-1.glb and src/render/spriteModels/newshh-1.json.
"""

import math
import os
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WT / "assets" / "blender")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshh-1"
HERE = Path(__file__).resolve().parent

W, H = 24, 28
Z_BOT, Z_TOP = -1.5, 2.2          # the block's base and top (px)
INSET = 0.6                       # core inset; the ribs/plates reach the tile edge
C = (13.0, 12.9)                  # ring / socket centre (column, row)
ART_LIGHT = Vector((-1.0, 1.0, 1.4)).normalized()   # Blender coords: upper left, from above

STONE = list(range(96, 112))
TAN = list(range(160, 176)) + [28, 29]


def X(x):
    return (x - W / 2) / 12


def Y(y):
    return (H / 2 - y) / 12


def Z(z):
    return z / 12


def P(x, y, z):
    return (X(x), Y(y), Z(z))


# --- sprite --------------------------------------------------------------------------------------

def load():
    sprite = common.load_sprite(WT, NAME)
    frames = {f["index"]: f["pixels"] for f in sprite["frames"]}
    colors = {int(k): v for k, v in sprite["colors"].items()}
    return sprite, frames, colors


def lum(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# --- small mesh helpers (copied, not shared) -----------------------------------------------------

class Mesh:
    """A bmesh with face tags: (region, flat) per face."""

    def __init__(self):
        self.bm = bmesh.new()
        self.tag = {}  # face -> region name

    def faces(self, rings, region, cap0=True, cap1=True, closed=True):
        bm = self.bm
        vs = [[bm.verts.new(p) if not isinstance(p, bmesh.types.BMVert) else p for p in r] for r in rings]
        out = []
        for r0, r1 in zip(vs, vs[1:]):
            n = max(len(r0), len(r1))
            for i in range(n if closed else n - 1):
                j = (i + 1) % n
                if len(r0) == 1:
                    f = (r0[0], r1[j], r1[i])
                elif len(r1) == 1:
                    f = (r0[i], r0[j], r1[0])
                else:
                    f = (r0[i], r0[j], r1[j], r1[i])
                out.append(bm.faces.new(f))
        if cap0 and len(vs[0]) > 2:
            out.append(bm.faces.new(list(reversed(vs[0]))))
        if cap1 and len(vs[-1]) > 2:
            out.append(bm.faces.new(vs[-1]))
        for f in out:
            self.tag[f] = region
        return out

    def hull(self, pts, region):
        bm = self.bm
        verts = [bm.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        live = [v for v in verts if v.is_valid]
        faces = list({f for v in live for f in v.link_faces})
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                                 edges=list({e for f in faces for e in f.edges}))
        live = [v for v in verts if v.is_valid]
        faces = list({f for v in live for f in v.link_faces})
        centre = sum((Vector(p) for p in pts), Vector()) / len(pts)
        for f in faces:
            f.normal_update()
            if f.normal.dot(f.calc_center_median() - centre) < 0:
                f.normal_flip()
            self.tag[f] = region
        return faces


def plate_points(x0, x1, y0, y1, zb, zt0, zt1, ch, ridge):
    """A shingled scale plate (sprite px): base rect at zb, a top whose height runs zt0 (row y0)
    to zt1 (row y1), chamfered sides and a ridge `ridge` px left of centre (its left facet faces
    the light)."""
    xm = (x0 + x1) / 2 - ridge
    pts = []
    for y, zt in ((y0, zt0), (y1, zt1)):
        yi = y + (ch if y == y0 else -ch)
        pts += [(x0, y, zb), (x1, y, zb), (x0, y, zt - 2 * ch), (x1, y, zt - 2 * ch),
                (x0 + ch, yi, zt - ch * 0.6), (x1 - ch, yi, zt - ch * 0.6), (xm, yi, zt)]
    return [P(*p) for p in pts]


# --- the ring trace ------------------------------------------------------------------------------

def ring_profile(pix, n=48):
    """Inner and outer radius (px) of the tan ring per angle (sprite coords: angle from +x toward
    +row), smoothed: rays marched from C through frame 1's tan mask (first and last tan sample)."""
    def tan(x, y):
        c, r = int(math.floor(x)), int(math.floor(y))
        return 0 <= r < H and 0 <= c < W and pix[r][c] in TAN
    ro, ri = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        hits = [d / 10 for d in range(0, 130) if tan(C[0] + d / 10 * math.cos(a), C[1] + d / 10 * math.sin(a))]
        ro.append((hits[-1] + 0.45) if hits else 8.0)   # to the pixel edge
        ri.append((hits[0] - 0.45) if hits else 4.5)

    def smooth(v, k=2):
        return [sum(v[(i + j) % n] for j in range(-k, k + 1)) / (2 * k + 1) for i in range(n)]
    return smooth(ro), smooth(smooth(ri))


def lump_angles(pix, colors):
    """Angles (sprite coords) of the ring's lumps: the lit maxima of frame 1's tan brightness
    (a 1 px blur, 4 px window), gaps filled so lumps sit about 36 deg apart."""
    def tl(r, c):
        return lum(colors[pix[r][c]]) if 0 <= r < H and 0 <= c < W and pix[r][c] in TAN else None
    F = {}
    for r in range(H):
        for c in range(W):
            if tl(r, c) is None:
                continue
            sw = sv = 0.0
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    v = tl(r + dr, c + dc)
                    if v is not None:
                        w = math.exp(-(dr * dr + dc * dc) / 2)
                        sw += w
                        sv += w * v
            F[(r, c)] = sv / sw
    peaks = []
    for (r, c), v in F.items():
        if all(F.get((r + dr, c + dc), -1) <= v for dr in range(-2, 2) for dc in range(-2, 2)):
            peaks.append(math.atan2(r + 0.5 - C[1], c + 0.5 - C[0]))
    peaks.sort()
    merged = []
    for a in peaks:   # one lump per 34 deg
        if merged and a - merged[-1][-1] < math.radians(34):
            merged[-1].append(a)
        else:
            merged.append([a])
    if len(merged) > 1 and merged[0][0] + 2 * math.pi - merged[-1][-1] < math.radians(34):
        merged[0] = [x - 2 * math.pi for x in merged.pop()] + merged[0]
    peaks = [sum(g) / len(g) for g in merged]
    print("LUMP PEAKS", [round(math.degrees(a)) for a in peaks])
    out = []
    for k, a in enumerate(peaks):
        b = peaks[(k + 1) % len(peaks)] + (2 * math.pi if k == len(peaks) - 1 else 0)
        out.append(a)
        gap = b - a
        extra = max(round(gap / math.radians(45)) - 1, 0)
        for j in range(1, extra + 1):
            out.append(a + gap * j / (extra + 1))
    print("LUMPS", len(out))
    return sorted(x % (2 * math.pi) for x in out)



def interp(vals, a):
    n = len(vals)
    t = (a % (2 * math.pi)) / (2 * math.pi) * n
    i = int(t)
    f = t - i
    return vals[i % n] * (1 - f) + vals[(i + 1) % n] * f


# --- build ---------------------------------------------------------------------------------------

def build(sprite, frames, colors):
    pix = frames[1]
    M = Mesh()
    rng = random.Random(11)
    ro, ri = ring_profile(pix)

    def keep_out(x, y, pad):
        d = math.hypot(x - C[0], y - C[1])
        a = math.atan2(y - C[1], x - C[0])
        return d < interp(ro, a) + pad

    # --- the block: one closed chunk of the organic wall ---------------------------------------
    # Top: an irregular triangulated height field (jittered points, Delaunay) whose relief is the
    # wall's veins: the sprite's own stone brightness (blurred: its streaks run mostly down the
    # tile with a lean) plus wavy vein ridges along the same lean, so each face's shade (facet
    # ramp, below) follows the sprite's streaks. It rises into a low mound under the lips and rolls
    # off over the tile edge. Sides: two bands of jittered rock facets down to a flat base, so the
    # block reads as a chunk cut from the wall, not a plinth.
    from mathutils.geometry import delaunay_2d_cdt
    stone_l = [[lum(colors[v]) if v in STONE else None for v in line] for line in pix]
    vals = [v for line in stone_l for v in line if v is not None]
    mean = sum(vals) / len(vals)
    sd = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
    lmap = [[0.0] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            sw = sv = 0.0
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    rr_, cc_ = r + dr, c + dc
                    if 0 <= rr_ < H and 0 <= cc_ < W and stone_l[rr_][cc_] is not None:
                        # anisotropic: blur more along the streaks (down the tile) than across
                        w = math.exp(-(dc * dc) / 0.9 - (dr * dr) / 2.4)
                        sw += w
                        sv += w * stone_l[rr_][cc_]
            lmap[r][c] = max(min(((sv / sw) - mean) / sd, 2.0), -2.0) if sw else 0.0

    def lum_at(x, y):
        x, y = min(max(x - 0.5, 0.0), W - 1.001), min(max(y - 0.5, 0.0), H - 1.001)
        c, r = int(x), int(y)
        fx, fy = x - c, y - r
        c1, r1 = min(c + 1, W - 1), min(r + 1, H - 1)
        return (lmap[r][c] * (1 - fx) * (1 - fy) + lmap[r][c1] * fx * (1 - fy)
                + lmap[r1][c] * (1 - fx) * fy + lmap[r1][c1] * fx * fy)

    mound = T.pchip([-1.6, 0.0, 0.9, 1.8, 2.8, 3.6], [0.2, 0.75, 0.75, 0.4, 0.08, 0.0])
    HOLE = 1.2   # the field's inner edge, this far inside the lips' outer radius (hidden under them)

    def rel(x, y):
        a = math.atan2(y - C[1], x - C[0])
        return math.hypot(x - C[0], y - C[1]) - interp(ro, a)

    def vein_at(x, y):
        """Wavy worm-like ridges about 2.8 px apart, running down the tile with a lean (domain
        warped so they wander and break, like the wall's veins): 1 on a ridge, 0 in a crevice."""
        w1 = 0.9 * math.sin(0.42 * y + 0.9 * math.sin(0.35 * x + 0.2 * y))
        w2 = 0.45 * math.sin(1.05 * y + 0.7 * x + 1.7)
        lean = x - 0.3 * y + w1 + w2
        brk = 0.5 + 0.5 * math.sin(0.8 * y - 0.5 * x + 2.0 * math.sin(0.6 * x))   # ridge breaks
        return (1 - abs(math.sin(math.pi * lean / 2.8))) ** 1.6 * (0.55 + 0.45 * brk)
    M.vein = vein_at

    def field_z(x, y):
        e = min(x, W - x, y, H - y)
        roll = 1.5 * (1 - min(e / 2.2, 1.0)) ** 2           # rounded shoulder over the tile edge
        vein = vein_at(x, y)
        d = rel(x, y)
        m = mound(min(max(d, -1.0), 3.6))
        keep_relief = min(max((d - 0.6) / 1.6, 0.0), 1.0)   # the mound is smooth flesh-stone
        return Z_TOP + 0.35 + m + keep_relief * (0.3 * lum_at(x, y) + 0.9 * vein - 0.35) - roll

    STEP = 1.0
    border = []
    for k in range(int(W / STEP)):
        border.append((k * STEP, 0.0))
    for k in range(int(H / STEP)):
        border.append((float(W), k * STEP))
    for k in range(int(W / STEP)):
        border.append((W - k * STEP, float(H)))
    for k in range(int(H / STEP)):
        border.append((0.0, H - k * STEP))
    hole = []
    nh = 48
    for k in range(nh):
        a = 2 * math.pi * k / nh
        rr_ = ro[k] - HOLE
        hole.append((C[0] + rr_ * math.cos(a), C[1] + rr_ * math.sin(a)))
    inner = []
    gy = 0.55
    row_k = 0
    while gy < H - 0.4:
        gx = 0.55 + (0.5 if row_k % 2 else 0.0)
        while gx < W - 0.4:
            x = gx + rng.uniform(-0.3, 0.3)
            y = gy + rng.uniform(-0.3, 0.3)
            if 0.45 < x < W - 0.45 and 0.45 < y < H - 0.45 and rel(x, y) > -HOLE + 0.55:
                inner.append((x, y))
            gx += STEP
        gy += STEP * 0.9
        row_k += 1
    pts2 = border + hole + inner
    nb, nhole = len(border), len(hole)
    edges = [(i, (i + 1) % nb) for i in range(nb)] + [(nb + i, nb + (i + 1) % nhole) for i in range(nhole)]
    vout, _, fout, vorig, _, _ = delaunay_2d_cdt([Vector(p) for p in pts2], edges, [], 0, 1e-5)
    bm = M.bm
    fv = []
    o2n = {}
    for i, p in enumerate(vout):
        v = bm.verts.new(P(p.x, p.y, field_z(p.x, p.y)))
        fv.append(v)
        for o in vorig[i]:
            o2n[o] = i
    for tri in fout:
        cx_ = sum(vout[i].x for i in tri) / len(tri)
        cy_ = sum(vout[i].y for i in tri) / len(tri)
        if not (0 < cx_ < W and 0 < cy_ < H) or rel(cx_, cy_) < -HOLE:
            continue
        try:
            f = bm.faces.new([fv[i] for i in tri])
        except ValueError:
            continue
        M.tag[f] = "stone"
    # grey border round the lips (the sprite's 1-10 ring): faces over those pixels
    for f, reg in list(M.tag.items()):
        if reg != "stone":
            continue
        c = f.calc_center_median()
        col, rw = int(c.x * 12 + W / 2), int(H / 2 - c.y * 12)
        d = rel(c.x * 12 + W / 2, H / 2 - c.y * 12)
        grey = 0 <= rw < H and 0 <= col < W and 1 <= pix[rw][col] <= 10
        if d < 0.9 or (grey and d < 2.4):
            M.tag[f] = "boss"

    # sides: the border loop, a jittered middle band and a base loop, as triangle facets
    top_loop = [fv[o2n[i]] for i in range(nb)]

    def inset_pt(x, y, d):
        nx = (1 if x <= 0.01 else -1 if x >= W - 0.01 else 0)
        ny = (1 if y <= 0.01 else -1 if y >= H - 0.01 else 0)
        return x + nx * d, y + ny * d

    mid_loop, bot_loop = [], []
    for i, (x, y) in enumerate(border):
        zt = top_loop[i].co.z * 12
        zm = Z_BOT + (zt - Z_BOT) * rng.uniform(0.38, 0.62)
        mx, my = inset_pt(x, y, rng.uniform(0.05, 0.45))
        mid_loop.append(bm.verts.new(P(mx, my, zm)))
        bx, by = inset_pt(x, y, rng.uniform(0.1, 0.35))
        bot_loop.append(bm.verts.new(P(bx, by, Z_BOT)))
    for a_, b_ in ((top_loop, mid_loop), (mid_loop, bot_loop)):
        for i in range(nb):
            j = (i + 1) % nb
            for tri in (((a_[i], a_[j], b_[j]), (a_[i], b_[j], b_[i])) if (i + len(M.tag)) % 2
                        else ((a_[i], a_[j], b_[i]), (a_[j], b_[j], b_[i]))):
                M.tag[bm.faces.new(tri)] = "side"
    M.tag[bm.faces.new(list(reversed(bot_loop)))] = "under"

    n = 48
    # the lips: one continuous fleshy lip lofted round the ring (inner/outer radius per angle from
    # the sprite), its top rising into about eight lobes that blend at dark creases
    lumps = lump_angles(pix, colors)

    def lobe(a):
        a = a % (2 * math.pi)
        for k, c0 in enumerate(lumps):
            c1 = lumps[(k + 1) % len(lumps)] + (2 * math.pi if k == len(lumps) - 1 else 0)
            aa = a if a >= c0 else a + 2 * math.pi
            if c0 <= aa < c1:
                ph = (aa - c0) / (c1 - c0)
                # broad lobes, a narrow soft crease half way between lobe centres
                return 1 - math.exp(-((ph - 0.5) / 0.13) ** 2)
        return 1.0

    def lobe_ph(a):
        a = a % (2 * math.pi)
        for k, c0 in enumerate(lumps):
            c1 = lumps[(k + 1) % len(lumps)] + (2 * math.pi if k == len(lumps) - 1 else 0)
            aa = a if a >= c0 else a + 2 * math.pi
            if c0 <= aa < c1:
                return (aa - c0) / (c1 - c0)
        return 0.0

    NL = 96
    ts = [0.0, 0.08, 0.2, 0.35, 0.5, 0.65, 0.8, 0.92, 1.0]
    hz = T.pchip([0.0, 0.25, 0.5, 0.75, 1.0], [0.0, 0.8, 1.0, 0.82, 0.0])
    zbase = Z_TOP + 1.3
    ring_rows = []
    for t in ts:
        row_pts = []
        for k in range(NL):
            a = 2 * math.pi * k / NL
            L_ = lobe(a)
            rin, rout = interp(ri, a), interp(ro, a)
            pinch = 0.45 * (1 - L_)
            r = rin + 0.1 + pinch * 0.5 + t * (rout - rin - 0.2 - pinch)
            h = 1.9 + 1.0 * L_ * (0.75 + 0.25 * math.cos(2 * math.pi * min(max(lobe_ph(a), 0.0), 1.0)) ** 2)
            z = zbase + h * hz(t) - (0.8 if t in (0.0, 1.0) else 0.0)
            row_pts.append(P(C[0] + r * math.cos(a), C[1] + r * math.sin(a), z))
        ring_rows.append(row_pts)
    ring_faces = M.faces(ring_rows, "ring", cap0=False, cap1=False)
    M.crease = set()
    for f in ring_faces:
        c = f.calc_center_median()
        a = math.atan2(-(c.y * 12 - (H / 2 - C[1])), c.x * 12 + W / 2 - C[0])
        if lobe(a) < 0.1:
            M.crease.add(f)

    # stone lip inside the lips (thin) and the socket wall down to the socket floor
    lip = []
    for s, dz in ((0.6, 0.2), (0.0, 0.75), (-0.5, 0.7), (-0.9, 0.1), (-1.0, -0.9)):
        lip.append([P(C[0] + (ri[k] + s) * math.cos(2 * math.pi * k / n),
                      C[1] + (ri[k] + s) * math.sin(2 * math.pi * k / n), zbase + dz) for k in range(n)])
    M.faces(lip, "lip", cap0=False, cap1=False)
    sock = [lip[-1]]
    for s in (0.8, 0.5):
        sock.append([P(C[0] + (ri[k] - 1.0) * s * math.cos(2 * math.pi * k / n),
                       C[1] + (ri[k] - 1.0) * s * math.sin(2 * math.pi * k / n),
                       zbase - 0.9 - (1 - s) * 3.0) for k in range(n)])
    M.faces(sock, "socket", cap0=False, cap1=True)
    return M, ro, ri


def shade(M, region, ramp_px, colors, pix, mid_px=None, strength=1.0, a_sprite=0.6, bias=0.0, extra=None, a_extra=0.0):
    """Facet ramp (D175 recipe, copied): give each face of `region` a palette index of the sprite's
    own ramp: faces ranked by light facing and the sprite's brightness under them, the ranks
    matched to the sprite's distribution of those shades (pixels `ramp_px`, a list of indices)."""
    faces = [f for f, r in M.tag.items() if r == region and f.is_valid]
    if not faces:
        return {}
    counts = {}
    for i in ramp_px:
        counts[i] = counts.get(i, 0) + 1
    shades = sorted(counts.items(), key=lambda kv: lum(colors[kv[0]]))
    total = sum(counts.values())
    cdf, acc = [], 0
    for i, c in shades:
        acc += c
        cdf.append((acc / total, i))
    light, bright, seen = [], [], []
    for f in faces:
        f.normal_update()
        nrm = f.normal
        light.append(nrm.dot(ART_LIGHT))
        c = f.calc_center_median()
        col = int(c.x * 12 + W / 2)
        row = int(H / 2 - c.y * 12)
        b = None
        if nrm.z > 0.3 and 0 <= row < H and 0 <= col < W and pix[row][col] in counts:
            b = lum(colors[pix[row][col]])
        bright.append(b)
        seen.append(f.calc_area() * max(nrm.z, 0.05))

    def ranks(v):
        order = sorted(range(len(v)), key=lambda k: v[k])
        out = [0.0] * len(v)
        for r, k in enumerate(order):
            out[k] = r / max(len(v) - 1, 1)
        return out
    lr = ranks(light)
    have = [k for k, b in enumerate(bright) if b is not None]
    br = dict(zip(have, ranks([bright[k] for k in have])))
    key = [(1 - a_sprite) * lr[k] + a_sprite * br[k] if k in br else lr[k] * 0.8 for k in range(len(faces))]
    if extra is not None:   # a per-face value (e.g. how high on a vein ridge), ranked and mixed in
        er = ranks([extra(f) for f in faces])
        key = [(1 - a_extra) * key[k] + a_extra * er[k] for k in range(len(faces))]
    order = sorted(range(len(faces)), key=lambda k: key[k])
    tot = sum(seen)
    acc = 0.0
    pick = {}
    for k in order:
        q = (acc + seen[k] / 2) / tot
        acc += seen[k]
        q = min(max(0.5 + strength * (q - 0.5) - bias, 0.0), 1.0)
        pick[faces[k]] = next(i for c, i in cdf if c >= q - 1e-9)
    return pick


def mesh_obj(name, bm, mats, coll, smooth_regions=(), tags=None):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    if tags is not None:
        for f, reg in tags.items():
            if f.is_valid:
                f.smooth = reg in smooth_regions
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def sphere(bm, centre, radii, segs=24, rings=12, cap=None):
    """A UV ellipsoid; with `cap` (cos of the polar angle) only the cap above it."""
    cx, cy, cz = centre
    out_rings = []
    lim = math.acos(cap) if cap is not None else math.pi
    for i in range(1, rings + 1):
        th = lim * i / rings
        out_rings.append([bm.verts.new((cx + radii[0] * math.sin(th) * math.cos(2 * math.pi * k / segs),
                                        cy + radii[1] * math.sin(th) * math.sin(2 * math.pi * k / segs),
                                        cz + radii[2] * math.cos(th))) for k in range(segs)])
    top = bm.verts.new((cx, cy, cz + radii[2]))
    faces = []
    for k in range(segs):
        faces.append(bm.faces.new((top, out_rings[0][k], out_rings[0][(k + 1) % segs])))
    for a, b in zip(out_rings, out_rings[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            faces.append(bm.faces.new((a[k], b[k], b[j], a[j])))
    if cap is None:
        bot = out_rings[-1]
        # close the last ring to a point
        pt = bm.verts.new((cx, cy, cz - radii[2]))
        for f in faces[-segs:]:
            pass
        faces += [bm.faces.new((bot[k], pt, bot[(k + 1) % segs])) for k in range(segs)]
    else:
        faces.append(bm.faces.new(list(reversed(out_rings[-1]))))
    for f in faces:
        f.smooth = True
    return faces


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite, frames, colors = load()
    pix = frames[1]
    coll = common.reset_collection(NAME)
    M, ro, ri = build(sprite, frames, colors)

    # stone pixels: the stone ramp over the whole tile (frame 1); tan pixels for the lips
    stone_px = [v for line in pix for v in line if v in STONE]
    tan_px = [v for line in pix for v in line if v in TAN]
    picks = {}
    def vein_of(f):
        c = f.calc_center_median()
        return M.vein(c.x * 12 + W / 2, H / 2 - c.y * 12)
    # the wall's veins: crevices take the ramp's dark end, ridge tops its light end, nudged by
    # the sprite's own brightness so its bright streaks stay where it has them
    picks.update(shade(M, "stone", stone_px, colors, pix, strength=1.0, a_sprite=0.6, bias=0.15,
                       extra=vein_of, a_extra=0.55))
    hist = {}
    for f, i in picks.items():
        hist[i] = hist.get(i, 0) + 1
    print("STONE PICKS", sorted(hist.items()))
    picks.update(shade(M, "side", [v for v in stone_px if 97 <= v <= 103], colors, pix, strength=0.9))
    picks.update(shade(M, "boss", [v for line in pix for v in line if 1 <= v <= 10], colors, pix,
                       strength=0.9, a_sprite=0.5))
    for f, reg in M.tag.items():
        if reg == "ring":
            # the lip's median tan; its pale lobe tops are lighting, the creases a darker tan
            picks[f] = 167 if f in M.crease else 170
    # the stone rim inside the lips: the sprite's dark inner border (stone 96-104 and greys 1-4
    # between the tan and the socket)
    inner_px = [pix[r][c] for r in range(H) for c in range(W)
                if math.hypot(c + 0.5 - C[0], r + 0.5 - C[1]) < interp(ri, math.atan2(r + 0.5 - C[1], c + 0.5 - C[0])) + 0.8
                and (96 <= pix[r][c] <= 104 or 1 <= pix[r][c] <= 4)]
    picks.update(shade(M, "lip", inner_px, colors, pix, strength=0.9, a_sprite=0.0))

    mats, slot = [], {}

    def mat_for(idx, kind):
        key = (idx, kind)
        if key not in slot:
            slot[key] = len(mats)
            if kind == "stone":
                # wall rock: matte, so the game's light doesn't sheen it paler than the wall round it
                m = common.palette_material(sprite, idx, NAME, metallic=0.02, roughness=0.9)
            elif kind == "tan":
                m = common.palette_material(sprite, idx, NAME + "-flesh", metallic=0.05, roughness=0.6)
            elif kind == "socket":
                m = common.palette_material(sprite, idx, NAME + "-socket", metallic=0.3, roughness=0.5,
                                            frames={3: 35})
            else:
                m = common.palette_material(sprite, idx, NAME, metallic=0.1, roughness=0.7)
            mats.append(m)
        return slot[key]

    for f, reg in M.tag.items():
        if not f.is_valid:
            continue
        if reg in picks or f in picks:
            pass
        if f in picks:
            f.material_index = mat_for(picks[f], "tan" if reg in ("ring", "lump") else "stone")
        elif reg == "under":
            f.material_index = mat_for(98, "stone")
        elif reg == "socket":
            f.material_index = mat_for(32, "socket")
        else:
            f.material_index = mat_for(100, "stone")
    # D74: the sprite's right column (and its corners) is dark ink-like shading the game's own
    # outline replaces: pull the block's right side in to column 23 (only the last 2.5 px of the
    # block are squeezed, so the ring stays where the sprite has it).
    xa = X(W - 2.5)
    for v in M.bm.verts:
        if v.co.x > xa:
            v.co.x = xa + (v.co.x - xa) * (1.5 / 2.5)
    body = mesh_obj(NAME, M.bm, mats, coll, smooth_regions=("ring", "stone", "boss", "lip", "socket"), tags=M.tag)
    body.data.set_sharp_from_angle(angle=math.radians(70))

    # the eye
    ex_, ey_ = C[0] - 0.1, C[1] + 0.1
    zbase = Z_TOP + 1.3
    eye_r = 3.6
    ec = (X(ex_), Y(ey_), Z(zbase - 1.6))
    bm = bmesh.new()
    sphere(bm, ec, (eye_r / 12, eye_r / 12 * 1.05, eye_r / 12 * 0.8), segs=20, rings=8)
    ball_mat = common.palette_material(sprite, 32, NAME + "-ball", metallic=0.5, roughness=0.25, frames={3: 34})
    ball = mesh_obj(NAME + "-ball", bm, [ball_mat], coll)

    def iris(name, r, idx, frames_on, frame_pal=None, emis=1.0, lift=0.04, zr=None, shift=(0.0, 0.0)):
        """A cap of the eyeball's surface; `shift` (sprite px, x right / y down) slides it over
        the ball (each vertex moved, then put back on the ellipsoid)."""
        bm = bmesh.new()
        rz = eye_r * 0.8 + lift
        rx, ry = (eye_r + lift) / 12, (eye_r * 1.05 + lift) / 12
        cap = math.cos(math.asin(min(r / (eye_r + lift), 0.99)))
        sphere(bm, ec, (rx, ry, rz / 12), segs=20, rings=4, cap=cap)
        if shift != (0.0, 0.0):
            for v in bm.verts:
                v.co.x += shift[0] / 12
                v.co.y -= shift[1] / 12
                q = 1 - ((v.co.x - ec[0]) / rx) ** 2 - ((v.co.y - ec[1]) / ry) ** 2
                v.co.z = ec[2] + rz / 12 * math.sqrt(max(q, 0.0))
        m = common.palette_material(sprite, idx, NAME + "-" + name, metallic=1.0, roughness=0.6,
                                    emission_strength=emis, frames=frame_pal)
        obj = mesh_obj(NAME + "-" + name, bm, [m], coll)
        return common.frame_part(obj, frames_on)

    dim = iris("iris", 1.9, 196, [1, 39], frame_pal={39: 33}, emis=1.0)
    # frame 3: the open iris spreads a little below the ball's centre (sprite rows 11-15) and its
    # white-hot 2x2 core sits up and left of the iris centre (sprite columns 12-13, rows 12-13)
    wide = iris("iris-open", 3.0, 200, [3], emis=1.0, lift=0.05, shift=(-0.1, 0.4))
    pupil = iris("pupil", 1.05, 15, [3], emis=1.0, lift=0.1, shift=(-0.25, -0.3))

    parts = [body, ball, dim, wide, pupil]
    # outline shell from a sealed copy of the visible solid (D90/D118)
    src = body.copy()
    src.data = body.data.copy()
    coll.objects.link(src)
    shell = common.outline_shell(src, coll, voxel=0.02, faces=1400, inside=0.01)
    bpy.data.objects.remove(src, do_unlink=True)
    parts.append(shell)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts if o is not shell)
    print(f"TRIS {tris}  shell {sum(len(p.vertices) - 2 for p in shell.data.polygons)}")
    common.export_sprite_model(WT, parts, f"enemies/{NAME}", sprite["sprites"])

    if "--measure" in argv:
        measure(parts, shell, Path(argv[argv.index("--measure") + 1]), sprite, frames, colors)
    if "--sheet" in argv:
        render_sheet(parts, shell, Path(argv[argv.index("--sheet") + 1]), sprite)


# --- measuring -----------------------------------------------------------------------------------

def visible(parts, frame):
    return [o for o in parts if not o.get("tyrian_outline") and
            ("tyrian_frames" not in o or frame in list(o["tyrian_frames"]))]


def measure(parts, shell, out, sprite, frames, colors):
    """Top-view hits at 4x4 samples per sprite pixel: coverage (IoU vs the sprite's opaque mask)
    and, per region, the median palette index seen from above vs the sprite's."""
    import json
    from mathutils.bvhtree import BVHTree
    out.mkdir(parents=True, exist_ok=True)
    deps = bpy.context.evaluated_depsgraph_get()
    report = {}
    for fi, pix in frames.items():
        objs = visible(parts, fi)
        trees = []
        for o in objs:
            bm = bmesh.new()
            bm.from_object(o, deps)
            bm.transform(o.matrix_world)
            bm.faces.ensure_lookup_table()
            idx = []
            for f in bm.faces:
                m = o.data.materials[f.material_index]
                p = int(m.name.split("_")[1])
                fp = m.get("tyrian_frame_pal")
                if fp and str(fi) in fp:
                    p = int(fp[str(fi)])
                idx.append(p)
            trees.append((BVHTree.FromBMesh(bm), idx))
        cover = [[0] * W for _ in range(H)]
        seen = [[None] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                hits = []
                for sy in range(4):
                    for sx in range(4):
                        x, y = c + (sx + 0.5) / 4, r + (sy + 0.5) / 4
                        best = None
                        for tree, idx in trees:
                            loc, nrm, fidx, d = tree.ray_cast(Vector((X(x), Y(y), 5.0)), Vector((0, 0, -1)))
                            if loc is not None and (best is None or d < best[0]):
                                best = (d, idx[fidx])
                        if best:
                            hits.append(best[1])
                cover[r][c] = len(hits) / 16
                if hits:
                    hits.sort(key=lambda i: lum(colors.get(i, (0, 0, 0))))
                    seen[r][c] = hits[len(hits) // 2]
        model = sum(1 for r in range(H) for c in range(W) if cover[r][c] >= 0.5)
        spr = sum(1 for r in range(H) for c in range(W) if pix[r][c] >= 0)
        inter = sum(1 for r in range(H) for c in range(W) if cover[r][c] >= 0.5 and pix[r][c] >= 0)
        iou = inter / (model + spr - inter)
        # regions by the sprite's colour family
        def fam(v):
            if v in STONE:
                return "stone"
            if v in TAN:
                return "ring"
            if 192 <= v <= 207 or v == 15:
                return "eye"
            if 32 <= v <= 37:
                return "socket"
            return "grey"
        regs = {}
        for r in range(H):
            for c in range(W):
                if pix[r][c] < 0 or seen[r][c] is None:
                    continue
                regs.setdefault(fam(pix[r][c]), ([], []))
                regs[fam(pix[r][c])][0].append(pix[r][c])
                regs[fam(pix[r][c])][1].append(seen[r][c])

        def med(v):
            v = sorted(v, key=lambda i: lum(colors.get(i, (0, 0, 0))))
            n = len(v)
            core = v[n // 8: n - n // 8] or v
            return core[len(core) // 2]
        rr = {}
        for k, (a, b) in regs.items():
            ma, mb = med(a), med(b)
            rr[k] = {"sprite": ma, "model": mb, "n": len(a),
                     "dlum": round(lum(colors.get(mb, (0, 0, 0))) - lum(colors.get(ma, (0, 0, 0))), 1)}
        report[fi] = {"iou": round(iou, 4), "regions": rr, "cover": cover}
    (out / "measure.json").write_text(json.dumps(report, indent=1))
    print("MEASURE", json.dumps({k: {"iou": v["iou"], "regions": v["regions"]} for k, v in report.items()}))


# --- review renders ------------------------------------------------------------------------------

def render_sheet(parts, shell, out, sprite):
    """Eevee renders, palette colours lit from the upper left: top (ortho), game camera (32 deg
    tilt from the bottom of the screen), side, front, rear, 3/4 high, underside; one row per frame
    for the top and game views."""
    import tempfile
    scene = bpy.context.scene
    for o in list(scene.objects):
        if o not in parts and o.type in ("MESH", "LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = scene.render.resolution_y = 360
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bgn = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs[0].default_value = (0.05, 0.05, 0.06, 1)
    bgn.inputs[1].default_value = 1.0
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 3.2
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (-ART_LIGHT).to_track_quat("-Z", "Y").to_euler()
    shell.hide_render = True
    # a ground plane, dark (the block sits in the wall's scenery)
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, Z(Z_BOT)))
    ground = bpy.context.active_object
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs[0].default_value = (0.02, 0.03, 0.03, 1)
    ground.data.materials.append(gm)

    def cam(name, loc, look, ortho=None, lens=60):
        d = bpy.data.cameras.new(name)
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return o

    def set_frame(fi):
        for o in parts:
            if o is shell:
                continue
            o.hide_render = "tyrian_frames" in o and fi not in list(o["tyrian_frames"])
            for m in o.data.materials:
                rgb = m.get("tyrian_frame_rgb", {}).get(str(fi))
                base = m.get("_base")
                if base is None:
                    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                    m["_base"] = list(bsdf.inputs["Base Color"].default_value)
                    base = m["_base"]
                bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                col = (*rgb, 1.0) if rgb is not None else tuple(base)
                bsdf.inputs["Base Color"].default_value = col
                if bsdf.inputs["Emission Strength"].default_value > 0:
                    bsdf.inputs["Emission Color"].default_value = col

    tmp = Path(tempfile.mkdtemp())

    def shot(c, fi, tag):
        set_frame(fi)
        scene.camera = c
        p = tmp / f"{tag}_{fi}.png"
        scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        return p

    D = 7.0
    tilt = math.radians(32)
    views = {
        "top": cam("top", (0, 0, 8), (0, 0, 0), ortho=2.7),
        "game": cam("game", (0, -D * math.sin(tilt), D * math.cos(tilt)), (0, 0, 0), lens=42),
        "side": cam("side", (D, 0, 0.1), (0, 0, 0.1), lens=55),
        "front": cam("front", (0, -D, 0.1), (0, 0, 0.1), lens=55),
        "rear": cam("rear", (0, D, 0.1), (0, 0, 0.1), lens=55),
        "q34": cam("q34", (-D * 0.55, -D * 0.6, D * 0.55), (0, 0, 0), lens=55),
        "under": cam("under", (D * 0.4, -D * 0.5, -D * 0.6), (0, 0, 0), lens=55),
    }
    views["top"].rotation_euler = (0, 0, 0)
    files = {}
    for fi in (39, 1, 3):
        files[("top", fi)] = shot(views["top"], fi, "top")
        files[("game", fi)] = shot(views["game"], fi, "game")
    ground.hide_render = True
    for v in ("side", "front", "rear", "q34", "under"):
        files[(v, 3)] = shot(views[v], 3, v)
        files[(v + "-1", 1)] = shot(views[v], 1, v) if v == "q34" else None
    import json
    (out.parent / "sheet_files.json").write_text(json.dumps({f"{k[0]}:{k[1]}": str(v) for k, v in files.items() if v}))
    print("SHEETFILES", out.parent / "sheet_files.json")


main()
