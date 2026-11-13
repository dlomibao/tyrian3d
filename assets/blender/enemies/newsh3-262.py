"""Rock pieces at the edges of the sandy rock arch (episode 4: 4.4 SURFACE, 4.10 DESERTRUN), design A.

One merged item, three models built from one rock (the arch itself is assembly-newsh3-198, not
built here; this only meets it):

- newsh3-262, the rock shoulder (24x28, top layer): the crown's right end turning down into the
  right leg. At arch (96, 14), right of the crown piece 241 and over the top of the leg piece 281.
- newsh3-282, the rock spur (24x28, ground layer, armour 255): the right leg's outer flank. At arch
  (108, 28), its left half under 281.
- newsh3-180, the rock tip (12x14 sprite, top layer): a knob of the arch's outer edge in the empty
  corner between the crown's 162 and the left leg's 198, at arch (12, 13) (a size-1 sprite is drawn
  6 px right and 7 px down of where a size-2 one would be: the stacking table's -18, +6 from 162).

262 and 282 are one surface: a height field in arch coordinates, sampled over each piece's own
outline. Across the band the rock rises from a low toe along the arch's outer edge (the sprite's
dark rim) in a rounded shoulder to a broad top (the leg's even mid-brown, about 14 px high where it
meets 279 and 281, which stand 13-15 px there). The crown's end (262's upper half) is held to a
7 px shelf so it meets 241's right cut (which batch 1 brought down to 6.5-7 px), its pale crest a
low lit swell on that shelf; the crack under it (the sprite's dark diagonal) is a V groove, and the
leg rises from it. The sprite's light streak (23s) from 262's middle down into 282 is a low fold
where the leg's top turns into its flank. Down 282 the leg comes to the ground at the sheet's bottom
(as 281 does, onto the terrain's leg tiles), and where 282 lies under 281 it is held 1.2 px lower so
281's own surface shows there.

Cut edges (where the rock carries on in a neighbour) are walls, except where a neighbour on a lower
pass follows to the south (262's bottom over 281, 282's bottom over the terrain): there the
underside rises to meet the top in a knife edge whose slope is flatter than the game camera's, so
no south-facing cut face draws over the neighbour. 180 is a closed chip: a wedge whose top rises to
the tile's lower-right corner (the sprite's pale 25/26 face, lit from the upper left), with its dark
rim along the free edge.

Colour: the D175 facet ramp (lib_newshd_rock.facet_ramp), as the arch: flat facets about 4.5 px
across, each one shade of the sprite's own brown ramp, ranked by how squarely it faces the art's
light and by the sprite's brightness under it (a 3x3 median of the sprite, so the per-pixel dither
doesn't make camouflage blobs). Matte sandstone (metallic 0, roughness 0.88). Underside and the
hidden cut walls in a dark brown. Outline shell (D51) per model from a sealed copy (D189
islands="outer"), its faces taken off the cut edges so no ink crosses the joins.

    blender -b --factory-startup -P newsh3-262.py -- [--all] [--out review.glb] [--game dir]

--out: all three models in one glb, laid out in arch coordinates relative to 262 (review only). --game dir: each
model also on its own for a review swap. A normal build builds and exports only newsh3-262 to the game
(public/models/enemies + spriteModels); newsh3-180.py and newsh3-282.py run this builder and build and
export only their own model (--all exports all three from this script).
"""

import math
import os
import random
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, geometry


def _find_repo():
    for p in Path(__file__).resolve().parents:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    env = os.environ.get("TYRIAN_REPO")
    if env:
        return Path(env)
    raise RuntimeError("repo root not found")


ROOT = _find_repo()
sys.path[:0] = [str(ROOT / "assets" / "blender"), str(ROOT / "assets" / "blender" / "enemies"),
                str(ROOT / "tools")]
import common  # noqa: E402
import lib_newshd_rock as R  # noqa: E402
import sprite_mask as SM  # noqa: E402

REF = ROOT / "reference" / "models"

# Each piece's top-left pixel in the arch's coordinates (assembly-newsh3-198: 162 at (24, 0)).
PIECES = {"newsh3-262": (96, 14), "newsh3-282": (108, 28), "newsh3-180": (12, 13)}
# Cut edges (the rock carries on in a neighbour): (side, from, to) along that side in piece px.
CUTS = {"newsh3-262": [("left", 0, 28), ("bottom", 0, 24), ("right", 18, 28)],
        "newsh3-282": [("top", 0, 24), ("left", 0, 28), ("bottom", 0, 24)],
        "newsh3-180": [("right", 9, 14)]}
# Cut edges finished as knife edges (a lower-pass neighbour follows to the south).
KNIFE = {"newsh3-262": "bottom", "newsh3-282": "bottom"}
KNIFE_SLOPE = 0.62  # underside rise per px towards the knife edge (32 deg; the game camera is ~51)

# --- the shape, in px (12 px = 1 unit) -------------------------------------------------------------
EDGE = 0.5       # top at the arch's outer edge
TOP = 14.5       # the leg's broad top
SHOULDER = 12.0  # px in from the outer edge to that top (a rounded rise, steep at the edge)
CROWN = 7.0      # the crown's end: 241's right cut stands 6.5-7 px
BOTTOM = 1.0     # underside depth inside
UNDER_281 = 1.2  # 282 held this far under 281 where it lies beneath it
# 241's right edge (rows 0-13 of 262) and 279's (rows 14-27), as built by batch 1: 262 keeps at or
# under them at its left cut, so no west-facing step shows to the camera.
LEFT_EDGE = [1, 1, 2, 4, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 8, 9, 11, 12, 13, 14, 14, 15, 15, 15, 14, 13]

# Feature lines in arch px (262 at +96, +14).
CREST = [(97.0, 16.8), (98.8, 18.6), (100.6, 20.2), (102.0, 22.2), (103.2, 24.2), (104.2, 26.6), (104.9, 29.0)]
CRACK = [(95.5, 28.4), (97.5, 28.9), (100.4, 29.5), (102.5, 30.4), (103.8, 31.4), (105.5, 32.5)]
STREAK = [(105.5, 32.4), (107.5, 33.0), (109.5, 33.6), (110.5, 35.0), (111.5, 36.6), (112.5, 39.0),
          (113.3, 41.5), (114.0, 43.0), (115.4, 44.5), (116.5, 47.0)]
CRACKS_282 = [[(117.6, 37.0), (118.2, 40.8), (117.8, 44.2), (118.6, 48.0), (119.8, 49.6), (121.4, 52.0), (121.6, 54.0)],
              [(120.2, 49.6), (123.2, 51.6), (123.6, 55.6)], [(121.0, 34.2), (122.6, 37.6)]]

RAMP = {"angle": 24.0, "size": 4.5, "sprite": 0.8, "strength": 1.0, "bias": 0.0}
FINISH = dict(metallic=0.0, roughness=0.88)
MID = {"newsh3-262": 22, "newsh3-282": 22, "newsh3-180": 25}
UNDER = {"newsh3-262": 19, "newsh3-282": 19, "newsh3-180": 18}


def clamp01(x):
    return max(0.0, min(1.0, x))


def smoothstep(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def smin(a, b, k):
    """A smooth minimum (no crease where the two surfaces meet)."""
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k / 4


def bump(t):
    return 0.5 + 0.5 * math.cos(math.pi * t) if t < 1 else 0.0


def seg_dist(p, segs):
    best = 1e9
    for a, b in segs:
        ab = b - a
        t = clamp01((p - a).dot(ab) / (ab.length_squared or 1.0))
        best = min(best, (a + ab * t - p).length)
    return best


def poly_segs(line):
    return [(Vector(a), Vector(b)) for a, b in zip(line, line[1:])]


def trace_mask(mask):
    """The boundary of a bool mask as a loop of pixel corners (col, row); the largest loop."""
    h, w = len(mask), len(mask[0])
    inside = lambda c, r: 0 <= r < h and 0 <= c < w and mask[r][c]  # noqa: E731
    edges = {}
    for r in range(h):
        for c in range(w):
            if not inside(c, r):
                continue
            if not inside(c, r - 1):
                edges[(c + 1, r)] = (c, r)
            if not inside(c, r + 1):
                edges[(c, r + 1)] = (c + 1, r + 1)
            if not inside(c - 1, r):
                edges[(c, r)] = (c, r + 1)
            if not inside(c + 1, r):
                edges[(c + 1, r + 1)] = (c + 1, r)
    loops, seen = [], set()
    for s in list(edges):
        if s in seen:
            continue
        loop, p = [], s
        while p not in seen and p in edges:
            seen.add(p)
            loop.append(p)
            p = edges[p]
        loops.append(loop)
    return max(loops, key=len)


class Piece:
    def __init__(self, name):
        self.name = name
        self.sprite = common.load_sprite(ROOT, name)
        f = self.sprite["frames"][0]
        self.w, self.h = f["width"], f["height"]
        self.pix = f["pixels"]
        self.ox, self.oy = PIECES[name]
        idx, colors = SM.load(name, ref=REF)
        m = SM.masks(idx, colors)
        self.cuts = CUTS[name]
        # the model covers the inner mask (D74), the thin parts' free border and, along a cut edge,
        # every opaque pixel (the rock carries on there; no notch in the cut)
        self.mask = [[m["inner"][r][c] or m["free"][r][c] or (m["outer"][r][c] and self.on_cut_px(c, r))
                      for c in range(self.w)] for r in range(self.h)]

    def on_cut_px(self, c, r):
        for side, a, b in self.cuts:
            if side == "left" and c == 0 and a <= r < b:
                return True
            if side == "right" and c == self.w - 1 and a <= r < b:
                return True
            if side == "top" and r == 0 and a <= c < b:
                return True
            if side == "bottom" and r == self.h - 1 and a <= c < b:
                return True
        return False

    def cut_of(self, p, q):
        """The cut side a boundary segment (piece px corners) lies on, or None (free outline)."""
        for side, a, b in self.cuts:
            if side == "left" and p.x == 0 and q.x == 0 and a <= min(p.y, q.y) and max(p.y, q.y) <= b:
                return side
            if side == "right" and p.x == self.w and q.x == self.w and a <= min(p.y, q.y) and max(p.y, q.y) <= b:
                return side
            if side == "top" and p.y == 0 and q.y == 0 and a <= min(p.x, q.x) and max(p.x, q.x) <= b:
                return side
            if side == "bottom" and p.y == self.h and q.y == self.h and a <= min(p.x, q.x) and max(p.x, q.x) <= b:
                return side
        return None

    def outline(self, rounds=3):
        """The smoothed outline (piece px) and, per segment, its cut side or None."""
        loop = trace_mask(self.mask)
        pts = [Vector((float(c), float(r))) for c, r in loop]
        on_border = [p.x in (0, self.w) or p.y in (0, self.h) for p in pts]
        n = len(pts)
        keep = [i for i in range(n) if on_border[i] or abs((pts[i] - pts[i - 1]).cross(pts[(i + 1) % n] - pts[i])) > 1e-6]
        pts = [pts[i] for i in keep]
        pinned = [on_border[i] for i in keep]
        for _ in range(rounds):
            n = len(pts)
            pts = [p if pinned[i] else (pts[i - 1] + 2 * p + pts[(i + 1) % n]) / 4 for i, p in enumerate(pts)]
        n = len(pts)
        cut = [self.cut_of(pts[i], pts[(i + 1) % n]) if pinned[i] and pinned[(i + 1) % n] else None
               for i in range(n)]
        return pts, cut

    def X(self, u):  # piece px -> Blender (origin at the piece's centre)
        return (u - self.w / 2) / 12

    def Y(self, v):
        return (self.h / 2 - v) / 12


# --- the height field ------------------------------------------------------------------------------

class Field:
    """The rock of 262 and 282 in arch px: distance to the arch's outer edge (both pieces' free
    outline segments) through a rounded shoulder, plus the crown shelf, crack, streak and leg fall."""

    def __init__(self, pieces):
        self.free = []
        for pc in pieces:
            pts, cut = pc.outline()
            n = len(pts)
            for i in range(n):
                if cut[i] is None:
                    a = pts[i] + Vector((pc.ox, pc.oy))
                    b = pts[(i + 1) % n] + Vector((pc.ox, pc.oy))
                    self.free.append((a, b))
        self.crest = poly_segs(CREST)
        self.crack = poly_segs(CRACK)
        self.streak = poly_segs(STREAK)
        self.cracks282 = [s for line in CRACKS_282 for s in poly_segs(line)]

    def base(self, P):
        d = seg_dist(P, self.free)
        t = clamp01(d / SHOULDER)
        return EDGE + (TOP - EDGE) * (1 - (1 - t) ** 2), d

    def z262(self, u, v):
        P = Vector((u + 96, v + 14))
        z, d = self.base(P)
        k_edge = smoothstep(d / 2.5)  # relief fades out at the outer edge
        # the crown's end: a 7 px shelf meeting 241, the leg rising from the crack below it
        cap = CROWN + (TOP - CROWN) * smoothstep((v - 13.0) / 10.0)
        z = smin(z, cap, 1.6)
        # the pale crest: a low lit swell on the shelf, broad to the lower left, short to the upper right
        dc = seg_dist(P, self.crest)
        z += 1.3 * bump(dc / 3.2) * k_edge
        # the crack under the crown: a V groove
        z -= 1.3 * max(0.0, 1 - seg_dist(P, self.crack) / 1.1) * k_edge
        # the streak: a low fold where the leg's top turns into its flank
        z += 0.7 * bump(seg_dist(P, self.streak) / 1.8) * k_edge
        # keep at or under 241 / 279 along the left cut
        r = min(27, max(0, int(v)))
        lim = LEFT_EDGE[r] - 0.8  # 0.8 under: no sliver of the west cut wall shows past 241's edge
        if z > lim:
            z -= (z - lim) * (1 - smoothstep(u / 5.0))
        return max(EDGE * 0.6, z)

    def z282(self, u, v):
        P = Vector((u + 108, v + 28))
        z, d = self.base(P)
        k_edge = smoothstep(d / 2.5)
        z += 0.7 * bump(seg_dist(P, self.streak) / 1.8) * k_edge
        z -= 0.7 * max(0.0, 1 - seg_dist(P, self.cracks282) / 0.9) * smoothstep(d / 1.5)
        # under 281 (its right cut is 282's column 12): held lower, so 281's surface shows there
        z -= UNDER_281 * (1 - smoothstep((u - 8.0) / 4.0))
        # the leg comes down to the ground at the sheet's bottom, as 281 does
        f = 1 - smoothstep((P.y - 45.0) / 10.5)
        z = 0.25 + (z - 0.25) * f
        return max(0.2, z)


TOE_162 = 0.35  # 162's left column (the arch's outer toe) where the tip joins it


def z180(pc, u, v, d, d_cut):
    """The tip: a small faceted knob on the arch's outer toe, rising from its free rim (the dark
    17/18 ring) to a peak by the pale 25/26 pixels, steep down to the notch under it (the 1 px gap
    above 198 the sprites leave) and down to 162's toe at its right cut."""
    rise = clamp01(((u - 8.5) / 3.0 + (v - 9.5) / 4.0) / 2)
    z = 0.04 + 2.3 * smoothstep(d / 1.3) * (0.4 + 0.6 * rise)
    return z + (TOE_162 - z) * (1 - smoothstep(d_cut / 1.1))


# --- the mesh --------------------------------------------------------------------------------------

def build_piece(pc, field, coll, seed):
    rng = random.Random(seed)
    pts, cut = pc.outline(rounds=1 if pc.name == "newsh3-180" else 3)
    n = len(pts)
    ring = [(pts[i], pts[(i + 1) % n]) for i in range(n)]
    free = [ring[i] for i in range(n) if cut[i] is None]
    cut_segs = [ring[i] for i in range(n) if cut[i] is not None] or [(Vector((-99, -99)), Vector((-99, -98)))]
    knife = KNIFE.get(pc.name)
    on_tile = lambda q: q.x in (0, pc.w) or q.y in (0, pc.h)  # noqa: E731
    edge_tile = [s for s in ring if on_tile(s[0]) and on_tile(s[1])]
    edge_free = [s for s in ring if not (on_tile(s[0]) and on_tile(s[1]))]

    def inside(p):
        hit = False
        for a, b in ring:
            if (a.y > p.y) != (b.y > p.y):
                x = a.x + (p.y - a.y) * (b.x - a.x) / (b.y - a.y)
                if x > p.x:
                    hit = not hit
        return hit

    small = pc.name == "newsh3-180"
    step = 0.7 if small else 1.3
    coords = [Vector(p) for p in pts]
    extra = []
    # rows of points along the free outline (the shoulder's facets), then the feature lines
    for off in ((0.5, 1.1) if small else (0.7, 1.6, 2.8, 4.4)):
        for a, b in free:
            k = max(1, round((b - a).length / max(step, off * 0.8)))
            nrm = Vector((-(b - a).y, (b - a).x)).normalized()
            for j in range(k):
                q = a.lerp(b, (j + 0.5) / k)
                for s in (1, -1):
                    c = q + nrm * s * off
                    if inside(c) and abs(seg_dist(c, free) - off) < 0.25:
                        extra.append(c)
    if not small:
        for line in (CREST, CRACK, STREAK) + tuple(CRACKS_282):
            for a, b in poly_segs(line):
                a, b = a - Vector((pc.ox, pc.oy)), b - Vector((pc.ox, pc.oy))
                k = max(1, round((b - a).length / 1.0))
                for j in range(k + 1):
                    extra.append(a.lerp(b, j / k))
    kept = []
    for p in extra:
        if inside(p) and seg_dist(p, ring) > 0.35 and all((p - q).length > step * 0.6 for q in kept):
            kept.append(p)
    coords += kept
    gy = step / 2
    while gy < pc.h:
        gx = step / 2 + (step / 2 if int(gy / step) % 2 else 0)
        while gx < pc.w:
            p = Vector((gx + rng.uniform(-0.22, 0.22) * step, gy + rng.uniform(-0.22, 0.22) * step))
            if inside(p) and seg_dist(p, ring) > step * 0.45 and all((p - q).length > step * 0.6 for q in kept):
                coords.append(p)
            gx += step
        gy += step * 0.87
    vco, _, faces, orig, _, _ = geometry.delaunay_2d_cdt(coords, [], [list(range(n))], 3, 1e-5, True)
    out_of = {}
    for o, ins in enumerate(orig):
        for i in ins:
            out_of[i] = o
    on_knife = set()
    if knife:
        for i in range(n):
            if cut[i] == knife:
                on_knife.add(out_of[i])
                on_knife.add(out_of[(i + 1) % n])

    bm = bmesh.new()
    tops, bots = [], []
    for o, p in enumerate(vco):
        p = Vector(p)
        d = seg_dist(p, free) if free else 99.0
        if pc.name == "newsh3-262":
            zt = field.z262(p.x, p.y) if d > 1e-4 else EDGE
            zt = EDGE + (zt - EDGE) * smoothstep(d / 0.8) if d < 0.8 else zt
        elif pc.name == "newsh3-282":
            zt = field.z282(p.x, p.y)
            zt = 0.2 + (zt - 0.2) * smoothstep(d / 0.8) if d < 0.8 else zt
        else:
            zt = z180(pc, p.x, p.y, seg_dist(p, free), seg_dist(p, cut_segs))
        zb = -(0.3 + (BOTTOM - 0.3) * smoothstep(d / 3.0))
        if small:
            zb = -(0.02 + 0.3 * smoothstep(min(seg_dist(p, edge_free), seg_dist(p, edge_tile)) / 1.0))
        if knife:
            dist_k = pc.h - p.y if knife == "bottom" else p.y
            zb = max(zb, zt - KNIFE_SLOPE * dist_k)
        x, y = pc.X(p.x), pc.Y(p.y)
        tv = bm.verts.new((x, y, zt / 12))
        tops.append(tv)
        bots.append(tv if o in on_knife else bm.verts.new((x, y, zb / 12)))
    for f in faces:
        bm.faces.new([tops[i] for i in f]).material_index = 0
        fb = bm.faces.new([bots[i] for i in reversed(f)])
        # the underside is dark, except where it rises to a knife edge (seen from a low angle it is
        # the rock's broken face there: rock, shaded by the ramp)
        fb.material_index = 0 if knife and max(bots[i].co.z for i in f) * 12 > -0.5 else 1
    for i in range(n):
        a, b = out_of[i], out_of[(i + 1) % n]
        if a == b:
            continue
        quad = [tops[b], tops[a], bots[a], bots[b]]
        uniq = []
        for v in quad:
            if v not in uniq:
                uniq.append(v)
        if len(uniq) < 3:
            continue
        f = bm.faces.new(uniq)
        # rock (the ramp shades them): the free rim, the chip's sides and the cut walls (hidden
        # under the neighbour's top; a sliver that shows is rock, not a dark line)
        f.material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mats = [common.palette_material(pc.sprite, MID[pc.name], pc.name, **FINISH),
            common.palette_material(pc.sprite, UNDER[pc.name], f"{pc.name}-under", **FINISH)]
    obj = common.mesh_object(pc.name, bm, mats, coll, smooth=False)
    return obj


def median_sprite(pc):
    """facet_ramp's sprite: a 3x3 median over the rock's pixels (the dither goes, the broad lit
    planes, the dark cracks and the highlights stay), as the arch does."""
    raw = pc.pix
    h, w = pc.h, pc.w
    out = [row[:] for row in raw]
    for r in range(h):
        for c in range(w):
            if raw[r][c] < 0:
                continue
            vals = sorted(raw[rr][cc] for rr in range(max(0, r - 1), min(h, r + 2))
                          for cc in range(max(0, c - 1), min(w, c + 2)) if raw[rr][cc] >= 0)
            out[r][c] = vals[len(vals) // 2]
    s = dict(pc.sprite)
    s["frames"] = [dict(pc.sprite["frames"][0], pixels=out)]
    return s


def trim_caps(shell, planes, reach=2.5 / 12, facing=0.35, all_faces=False):
    """Take the outline shell's faces off the cut edges (faces near a cut plane facing out through
    it, or every face that near with all_faces): the hull drew them as ink across the join."""
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.normal_update()
    gone = []
    for f in bm.faces:
        c = f.calc_center_median()
        for axis, at, sign, keep in planes:
            k = 0 if axis == "x" else 1
            if abs(c[k] - at) < reach and (f.normal[k] * sign > facing or all_faces) and keep(c.x, c.y):
                gone.append(f)
                break
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    bm.to_mesh(shell.data)
    bm.free()
    print(f"trim_caps {shell.name}: {len(gone)} faces off the cut edges")


def cut_planes(pc):
    out = []
    for side, a, b in pc.cuts:
        if side == "left":
            out.append(("x", pc.X(0), -1, lambda x, y, a=a, b=b: pc.Y(b) - 0.05 < y < pc.Y(a) + 0.05))
        elif side == "right":
            out.append(("x", pc.X(pc.w), 1, lambda x, y, a=a, b=b: pc.Y(b) - 0.05 < y < pc.Y(a) + 0.05))
        elif side == "top":
            out.append(("y", pc.Y(0), 1, lambda x, y, a=a, b=b: pc.X(a) - 0.05 < x < pc.X(b) + 0.05))
        elif side == "bottom":
            out.append(("y", pc.Y(pc.h), -1, lambda x, y, a=a, b=b: pc.X(a) - 0.05 < x < pc.X(b) + 0.05))
    return out


def finish(pc, obj, coll):
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    small = pc.name == "newsh3-180"
    shell = common.outline_shell(sealed, coll, voxel=0.02 if small else 0.03, faces=600 if small else 3000,
                                 smooth=4 if small else 8, inside=0.004, islands="outer")
    bpy.data.objects.remove(sealed)
    shell.name = shell.data.name = f"{pc.name}_outline"
    planes = cut_planes(pc)
    if planes:
        trim_caps(shell, planes)
        knife = KNIFE.get(pc.name)
        kp = [p for p, (side, _, _) in zip(planes, pc.cuts) if side == knife]
        if kp:
            trim_caps(shell, kp, reach=1.6 / 12, all_faces=True)
        # 262's west cut meets 241: the hull's up-facing faces there drew a dark ink seam along the
        # join in the game camera; take every shell face off that strip (241 carries on the rock)
        if pc.name == "newsh3-262":
            lp = [p for p, (side, _, _) in zip(planes, pc.cuts) if side == "left"]
            trim_caps(shell, lp, reach=1.6 / 12, all_faces=True)
    R.facet_ramp(median_sprite(pc), R.Grid(pc.sprite, pc.name), obj,
                 {"mid": MID[pc.name], "ramp": RAMP, **FINISH}, mid=MID[pc.name], slot=0)
    return shell


def build(only=None):
    coll = common.reset_collection("newsh3-262_A")
    pieces = {n: Piece(n) for n in PIECES}
    field = Field([pieces["newsh3-262"], pieces["newsh3-282"]])
    models = {}
    for k, (name, pc) in enumerate(pieces.items()):
        if only is not None and name not in only:
            continue  # a wrapper builds only the model it exports
        obj = build_piece(pc, field, coll, seed=262 + k)
        shell = finish(pc, obj, coll)
        models[name] = (pc, [obj, shell])
        zs = [v.co.z * 12 for v in obj.data.vertices]
        print(f"{name}: {len(obj.data.polygons)} faces, z {min(zs):.2f}..{max(zs):.2f} px, "
              f"shell {len(shell.data.polygons)} faces")
    return models


def main(only=None):
    """Export the models in `only` (a normal build: each member script exports just its own). --all, --out
    and --game build all three."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--all" in argv or "--out" in argv or "--game" in argv:
        only = None
    models = build(only)
    if "--game" in argv:  # review copies, each model on its own as the game loads it
        gdir = Path(argv[argv.index("--game") + 1])
        for name, (pc, objs) in models.items():
            common.export_glb(objs, gdir / f"{name}.glb")
    if "--out" in argv:  # review: all three in one glb in arch coordinates, relative to 262's centre
        allobjs = []
        for name, (pc, objs) in models.items():
            dx = (pc.ox + pc.w / 2 - (96 + 12)) / 12
            dy = -(pc.oy + pc.h / 2 - (14 + 14)) / 12
            for o in objs:
                o.location = (dx, dy, 0)
                allobjs.append(o)
        common.export_glb(allobjs, Path(argv[argv.index("--out") + 1]))
        for name, (pc, objs) in models.items():
            for o in objs:
                o.location = (0, 0, 0)
        return
    for name, (pc, objs) in models.items():
        if only is None or name in only:
            common.export_sprite_model(ROOT, objs, f"enemies/{name}", pc.sprite["sprites"])
            print("exported", name)


if __name__ == "__main__":
    main(only={"newsh3-262"})
