"""Sinking stone block (newshp.shp, assembly of 4 pieces: newshp-153/155 over newshp-191/193),
built from engineering cross-sections.

The sprite (48 x 56 px, three steps) is a raised platform of smooth light-grey ashlar on rubbly
ground, with three stones (A big upper middle, B narrow east, C low middle) that sink into the deck
step by step. The dark ribbed band south of it (rows 42-51) and the dark band along its east face
are the platform's drop shadow over the ground masonry: lighting, not geometry or paint (art rule 2,
E2 QA M2), so they are plain ground here and the game's sun shadow makes the shade.

Cross-sections (sprite px; x = col - 24, y = 28 - row, z up; 12 px = 1 Blender unit):
- Plinth: two masonry courses on the rounded-rect plan of columns 4-42, rows 0-41 (corner radius 2
  north, 3 south). Lower course 0 .. 1.0 at the full plan with a 0.18 chamfered water table; upper
  course (the bedding / mortar slab) 1.0 .. 3.56 set back 0.15, with facing blocks on its runs.
- Deck: one course of smooth slabs to 3.84 (= 0.32 units). Each stone fills its sprite pixel
  rectangle exactly; the 1 px joints between them are mortar at 3.56, a shallow seam (0.28 px), and
  each slab has a small rounded arris (0.26) that catches the light (the sprite's lit north / west,
  dark south / east stone edges). No ink in the seams.
- Sockets: the three sinking stones ride in pits through the bedding course (0.15 clearance); B, on
  the east edge, is held by a steel cheek plate. Stone tops per step 3.84 / 3.10 / 2.15 px.
- Ground (newshp-237's baked-in ground): dark ground plate, rubble down the west strip and along the
  bottom, low ground stones south of the platform, dark gravel and rubble on the east.

Colour: each part takes its sprite region's trimmed-median palette index (blueprint.json
spriteMedians): stone 9, joints 7, west rubble 6, east rubble 3, south ground and bottom rubble 5;
the sinking stones 9 / 8 / 6 (A), 9 / 7 / 3 (B), 9 / 7 / 5 (C) per step. Stone is matte. No concept
projection. Outline shell (D51) per step from a sealed copy of the platform (one closed solid, D90 /
D118), so the ink is on the platform's silhouette only, not in the seams or round the ground stones.
Underside: the closed ground plate only.

Texture: AO/roughness bake only (usp_talon.bake_maps, "bake": "model", D50/D65). The whole block is
built and baked once per step, then cut into the four pieces with common.split_assembly; every piece
has three models: <piece>, <piece>-f2, <piece>-f3.

Run: blender -b --factory-startup -P assets/blender/enemies/assembly-newshp-191.py [-- --no-bake] [--out all.glb]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (bake_maps)

NAME = "assembly-newshp-191"
ROOT = common.repo_root(__file__)
WT = ROOT
PIECES = ["newshp-153", "newshp-155", "newshp-191", "newshp-193"]
CX0, CY0 = 68, 24  # screen px of the assembly centre (pixel edge 24, 28): the Blender origin
U = 1 / 12

# --- dimensions (px) ---------------------------------------------------------------------------
PLAN = (4, 0, 43, 42)            # platform pixel edges: columns 4-42, rows 0-41
R_N, R_S = 2.0, 3.0              # plan corner radii north / south
TOP = 3.84                       # deck top (0.32 units)
BED = 3.56                       # mortar joints: shallow seams 0.28 px below the deck (E2 QA M2)
FLOOR = 2.0                      # pit floor level reference (bottom of the sinkers' travel)
LOWER = 1.0                      # lower plinth course top
SETBACK = 0.15                   # upper course set back from the plan
CH = 0.26                        # stone arris: a small rounded chamfer (the sprite's lit / dark edge)
CLEAR = 0.15                     # sinker clearance in its pit
SINK_TOP = [3.84, 3.10, 2.15]    # sinking stones' tops per step
SINK_PAL = {"A": [9, 8, 6], "B": [9, 7, 3], "C": [9, 7, 5]}

# Deck stones: inclusive pixel rects (c0, r0, c1, r1), and which one sinks.
STONES = [
    (4, 0, 25, 5), (27, 0, 42, 9), (4, 7, 10, 19), (12, 7, 25, 19, "A"), (27, 11, 36, 14),
    (38, 11, 42, 18, "B"), (27, 16, 36, 25), (38, 20, 42, 25), (4, 21, 14, 29), (16, 21, 18, 41),
    (20, 21, 25, 25), (20, 27, 32, 34, "C"), (34, 27, 42, 41), (20, 36, 32, 41), (4, 31, 14, 41),
]


def X(c):
    return c - 24


def Y(r):
    return 28 - r


# --- 2D helpers (px, CCW seen from above) -------------------------------------------------------

def rr(c0, r0, c1, r1, rad=None, seg=5):
    """Rounded rectangle over pixel edges, radii per corner {nw, ne, se, sw}, CCW."""
    rad = rad or {}
    x0, x1, yt, yb = X(c0), X(c1), Y(r0), Y(r1)
    pts = []
    for name, cx, cy, a0 in (("sw", x0, yb, 180), ("se", x1, yb, 270), ("ne", x1, yt, 0), ("nw", x0, yt, 90)):
        r = rad.get(name, 0)
        if not r:
            pts.append((cx, cy))
            continue
        ox = cx - math.copysign(r, math.cos(math.radians(a0 + 45)))
        oy = cy - math.copysign(r, math.sin(math.radians(a0 + 45)))
        for k in range(seg):
            a = math.radians(a0 + 90 * k / (seg - 1))
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def inset(o, d):
    """Every edge of the CCW polygon moved d inward (mitred)."""
    n = len(o)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = o[i], o[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0)
        lines.append(((x0 - (y1 - y0) / ln * d, y0 + (x1 - x0) / ln * d), (x1 - x0, y1 - y0)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def box2(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def dedupe(o, eps=1e-4):
    out = []
    for p in o:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps:
            out.append(p)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= eps:
        out.pop()
    return out


# --- mesh builder -------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.sharp_faces = []

    def ring(self, pts2, z):
        return [self.bm.verts.new((x, y, z)) for x, y in pts2]

    def ring3(self, pts3):
        return [self.bm.verts.new(p) for p in pts3]

    def bridge(self, a, b, mat):
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat

    def cap(self, r, mat, up=True):
        self.bm.faces.new(r if up else list(reversed(r))).material_index = mat

    def loft(self, rings, mats, cap0=True, cap1=True, capmat=None):
        """rings: each (pts2, z) or a list of 3D points; mats: one per band (or one for all)."""
        vr = []
        for r in rings:
            if isinstance(r, tuple) and len(r) == 2 and isinstance(r[1], (int, float)):
                vr.append(self.ring(r[0], r[1]))
            else:
                vr.append(self.ring3(r))
        if isinstance(mats, int):
            mats = [mats] * (len(vr) - 1)
        for k in range(len(vr) - 1):
            self.bridge(vr[k], vr[k + 1], mats[k])
        if cap0:
            self.cap(vr[0], capmat if capmat is not None else mats[0], up=False)
        if cap1:
            self.cap(vr[-1], capmat if capmat is not None else mats[-1], up=True)
        return vr

    def block(self, o, z0, z1, mat, ch=0.0, chb=0.0, top=None, bottom=True):
        """Prism over CCW outline o, top edge chamfered ch, bottom edge chamfered chb."""
        rings = []
        if chb:
            rings.append((inset(o, chb), z0))
            rings.append((o, z0 + chb))
        else:
            rings.append((o, z0))
        if ch:
            rings.append((o, z1 - ch))
            rings.append((inset(o, ch), z1))
        else:
            rings.append((o, z1))
        rs = self.loft(rings, mat, cap0=bottom, cap1=False)
        self.cap(rs[-1], top if top is not None else mat, up=True)
        return rs

    def dressed(self, o, z0, top, mat):
        """A smooth dressed slab: straight walls, a small rounded arris (two-step chamfer) and a
        flat face. The seam to its neighbour is only TOP - BED deep, so it reads as a faint line."""
        o = dedupe(o)
        rings = [(o, z0), (o, top - CH), (inset(o, CH * 0.45), top - CH * 0.22), (inset(o, CH), top)]
        self.loft(rings, mat)

    def wedge(self, x0, x1, ya, yb, za, zb, z0, mat):
        """Slab between y = ya (high, za) and y = yb (low, zb) over x0..x1, standing on z0."""
        lo = [(x0, yb, z0), (x1, yb, z0), (x1, ya, z0), (x0, ya, z0)]
        hi = [(x0, yb, zb), (x1, yb, zb), (x1, ya, za), (x0, ya, za)]
        self.loft([lo, hi], mat)

    def holed_slab(self, outer, holes, z0, z1, top, wall, hole_wall):
        """A slab from z0 to z1 over `outer` with vertical pits `holes` (CCW lists), no bottom face
        (it stands on the course below)."""
        bm = self.bm
        ob, ot = self.ring(outer, z0), self.ring(outer, z1)
        self.bridge(ob, ot, wall)
        loops = [ot]
        for h in holes:
            hb, ht = self.ring(h, z0), self.ring(h, z1)
            self.bridge(list(reversed(hb)), list(reversed(ht)), hole_wall)
            loops.append(ht)
        edges = []
        for loop in loops:
            for i in range(len(loop)):
                a, b2 = loop[i], loop[(i + 1) % len(loop)]
                edges.append(bm.edges.get((a, b2)) or bm.edges.new((a, b2)))
        res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=True, edges=edges)
        for f in res["geom"]:
            if isinstance(f, bmesh.types.BMFace):
                f.material_index = top
                f.normal_update()
                if f.normal.z < 0:
                    f.normal_flip()


# --- materials ----------------------------------------------------------------------------------

def merged_sprite():
    data = common.load_sprite(ROOT, "newshp-191")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


KINDS = {"stone": dict(metallic=0.0, roughness=0.82), "steel": dict(metallic=0.55, roughness=0.42),
         "rubble": dict(metallic=0.0, roughness=0.9), "mortar": dict(metallic=0.0, roughness=0.95)}


class Mats:
    def __init__(self, sprite, step):
        self.sprite, self.step = sprite, step
        self.list, self.slot = [], {}

    def __call__(self, index, kind="stone"):
        key = (index, kind)
        if key not in self.slot:
            mat = common.palette_material(self.sprite, index, f"nshp191_{self.step}_{kind}", **KINDS[kind])
            self.list.append(mat)
            self.slot[key] = len(self.list) - 1
        return self.slot[key]


# --- the model ----------------------------------------------------------------------------------

def plan_outline():
    return rr(*PLAN, {"nw": R_N, "ne": R_N, "se": R_S, "sw": R_S}, seg=7)


def stone_outline(c0, r0, c1, r1):
    """A stone's pixel footprint; corners that are platform corners follow the plan's rounding."""
    pc0, pr0, pc1, pr1 = PLAN
    rad = {"nw": R_N if (c0 == pc0 and r0 == pr0) else 0, "ne": R_N if (c1 + 1 == pc1 and r0 == pr0) else 0,
           "sw": R_S if (c0 == pc0 and r1 + 1 == pr1) else 0, "se": R_S if (c1 + 1 == pc1 and r1 + 1 == pr1) else 0}
    return rr(c0, r0, c1 + 1, r1 + 1, rad, seg=7)


def rand(seed):
    x = math.sin(seed * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


def rubble_stone(M, mat, c0, r0, c1, r1, h, seed, z0=0.24):
    """A rough-dressed rubble stone in its pixel cell: an irregular octagonal plan (jittered
    rounded rectangle), straight walls, a chamfer and a tilted, cambered top (lit faces, rock)."""
    cx, cy = (X(c0) + X(c1)) / 2, (Y(r0) + Y(r1)) / 2
    hx, hy = (X(c1) - X(c0)) / 2 - 0.14, (Y(r0) - Y(r1)) / 2 - 0.14
    n = 10
    o = []
    for k in range(n):
        t = 2 * math.pi * (k + 0.5 * rand(seed + k * 3.1)) / n
        cs, sn = math.cos(t), math.sin(t)
        e = 7.0  # superellipse: squarish, corners knocked off
        rr_ = (abs(cs) ** e + abs(sn) ** e) ** (-1 / e)
        f = 0.9 + 0.1 * rand(seed + k * 1.7)
        o.append((cx + hx * cs * rr_ * f, cy + hy * sn * rr_ * f))
    tx, ty = (rand(seed) - 0.5) * 0.3, (rand(seed + 7) - 0.5) * 0.3
    zt = z0 + h * (0.85 + 0.3 * rand(seed + 11))
    ch = min(0.34, hx * 0.45, hy * 0.45)

    def tilt(pts, z):
        return [(x, y, z + tx * (x - cx) + ty * (y - cy)) for x, y in pts]

    rings = M.loft([[(x, y, z0) for x, y in o], tilt(o, zt - ch), tilt(inset(o, ch * 0.55), zt - ch * 0.3),
                    tilt(inset(o, ch), zt)], mat, cap1=False)
    top = M.bm.verts.new((cx + (rand(seed + 5) - 0.5) * hx * 0.5, cy, zt + 0.08))
    r = rings[-1]
    for i in range(len(r)):
        M.bm.faces.new((r[i], r[(i + 1) % len(r)], top)).material_index = mat


def facing(M, mat):
    """Facing blocks on the upper plinth course's straight runs: real vertical joints (masonry
    coursing) for the tilted camera and the side views. Proud of the set-back course by 0.1."""
    pc0, pr0, pc1, pr1 = PLAN
    t, gap, z0, z1 = 0.1, 0.12, LOWER, BED - 0.06
    sb = SETBACK

    def run(a0, a1, length, make):
        nb = max(1, round((a1 - a0) / length))
        step_ = (a1 - a0) / nb
        for k in range(nb):
            make(a0 + k * step_ + gap / 2, a0 + (k + 1) * step_ - gap / 2)

    # south (front) and north: blocks ~5.5 px; west and east ~6 px, staggered by half a block
    yS, yN, xW, xE = Y(pr1) + sb, Y(pr0) - sb, X(pc0) + sb, X(pc1) - sb
    run(X(pc0) + R_S, X(pc1) - R_S, 5.5, lambda a, b: M.block(box2(a, yS - t, b, yS), z0, z1, mat, ch=0.06, bottom=False))
    run(X(pc0) + R_N, X(pc1) - R_N, 5.5, lambda a, b: M.block(box2(a, yN, b, yN + t), z0, z1, mat, ch=0.06, bottom=False))
    run(Y(pr1) + R_S, Y(pr0) - R_N, 6.0, lambda a, b: M.block(box2(xW - t, a, xW, b), z0, z1, mat, ch=0.06, bottom=False))
    run(Y(pr1) + R_S + 3, Y(pr0) - R_N, 6.0, lambda a, b: M.block(box2(xE, a, xE + t, b), z0, z1, mat, ch=0.06, bottom=False))


def build(sprite, step, coll):
    m = Mats(sprite, step)
    M = Mesh()
    G = 0.24  # ground plate top

    # ---- ground plate (closed underside: the plate's flat bottom) --------------------------------
    M.block(box2(X(0), Y(56), X(48), Y(0)), 0.0, G, m(5, "rubble"))

    # ---- west rubble strip (columns 0-3), the lit ledge stone, rubble along the bottom ----------
    # the gravel bed the west rubble lies in
    M.block(box2(X(0), Y(52), X(4), Y(0)), G - 0.01, G + 0.03, m(6, "rubble"), bottom=False)
    LR = [(0, 0, 3, 3, 0.84), (0, 5, 4, 8, 0.84), (0, 10, 3, 13, 0.96), (0, 19, 4, 23, 0.72), (0, 24, 3, 27, 0.96)]
    for i, (c0, r0, c1, r1, h) in enumerate(LR):
        for dr in (0, 28):
            if r0 + dr >= 42 and r0 + dr < 46:
                continue
            rubble_stone(M, m(6, "rubble"), c0, r0 + dr, min(c1, 4), min(r1 + dr, 52), h, i * 3 + dr)
    rubble_stone(M, m(8, "rubble"), 0, 42, 4, 45, 1.08, 99)
    for k in range(0, 48, 4):
        rubble_stone(M, m(5, "rubble"), k, 52, k + 4, 56, 0.6 + 0.2 * rand(k), 200 + k)

    # ---- east: the dark rubble beside the platform ---------------------------------------------
    # The sprite's dark band along the east face (cols 43-45) is the platform's drop shadow (art
    # rule 2): plain dark gravel here, the sun's shadow of the platform darkens it in game.
    M.block(box2(X(43), Y(52), X(48), Y(0)), G - 0.01, G + 0.03, m(3, "rubble"), bottom=False)
    RR = [(45.5, 0, 48, 3, 0.72), (46, 5, 48, 8, 0.6), (46, 14, 48, 18, 0.6), (46, 19, 48, 23, 0.6), (46, 24, 48, 27, 0.84)]
    for i, (c0, r0, c1, r1, h) in enumerate(RR):
        for dr in (0, 28):
            rubble_stone(M, m(3, "rubble"), c0, r0 + dr, c1, min(r1 + dr, 52), h, 50 + i * 3 + dr)

    # ---- south of the platform (rows 42-51): plain ground ----------------------------------------
    # The sprite's dark ribbed band here is the platform's drop shadow over the ground masonry (art
    # rule 2: shading is lighting, not geometry or paint). Only low ground stones on a gravel bed;
    # the sun's shadow of the platform makes the shade in game.
    M.block(box2(X(4), Y(52), X(43), Y(42)), G - 0.01, G + 0.03, m(5, "rubble"), bottom=False)
    for r0, off in ((42, 0), (45, 2), (48, 0)):
        for k in range(4 + off, 43 - 2, 4):
            rubble_stone(M, m(5, "rubble"), k, r0, min(k + 4, 43), r0 + 3, 0.42 + 0.2 * rand(k + r0), 300 + k + r0)

    # ---- the platform: two plinth courses -------------------------------------------------------
    plan = plan_outline()
    M.block(plan, G - 0.02, LOWER, m(6, "stone"), ch=0.18)
    upper = inset(plan, SETBACK)
    facing(M, m(6, "stone"))

    # ---- sockets of the sinking stones, the bedding / mortar course with the pits through it ---
    zt = SINK_TOP[step]
    sinkers, holes = [], []
    for s in STONES:
        if len(s) < 5:
            continue
        c0, r0, c1, r1, k = s
        x0, x1, yb, yt = X(c0), X(c1 + 1), Y(r1 + 1), Y(r0)
        if c1 + 1 == PLAN[2]:  # B: on the east edge, a steel cheek plate closes the socket
            x1 -= 0.45
        sinkers.append((k, (x0, yb, x1, yt), s))
        holes.append(box2(x0 - CLEAR, yb - CLEAR, x1 + CLEAR, yt + CLEAR))
    M.holed_slab(upper, holes, LOWER - 0.02, BED, m(7, "mortar"), m(6, "stone"), m(4, "steel"))
    # Pit floors (the plinth's lower course closes them under the slab at LOWER): steel base plates.
    for h in holes:
        M.block(h, LOWER - 0.02, FLOOR - 0.6, m(4, "steel"), bottom=False)

    # ---- the fixed ashlar ----------------------------------------------------------------------
    for s in STONES:
        if len(s) == 5:
            continue
        M.dressed(stone_outline(*s[:4]), BED - 0.12, TOP, m(9, "stone"))

    # ---- the sinking stones, guide plates and B's cheek plate ----------------------------------
    for k, (x0, yb, x1, yt), s in sinkers:
        pal = SINK_PAL[k][step]
        o = box2(x0, yb, x1, yt)
        M.dressed(o, max(FLOOR - 0.6, zt - (TOP - FLOOR)), zt, m(pal, "stone"))
        if k == "B":
            # cheek plate: steel, flush with the platform's east face, bolted (two bolt heads)
            xa, xb = x1 + CLEAR + 0.02, X(PLAN[2]) - SETBACK * 0.0
            M.block(box2(xa, yb - 1.0, xb, yt + 1.0), LOWER, TOP - 0.3, m(6, "steel"), ch=0.08)
            for yy in (yb + 0.9, yt - 0.9):
                ring = [(0.22 * math.cos(2 * math.pi * i / 8), 0.22 * math.sin(2 * math.pi * i / 8)) for i in range(8)]
                # bolt head on the outer face: a short octagonal boss pointing +X
                pts = [(xb, yy + v, 1.9 + u) for u, v in ring]
                tip = [(xb + 0.12, yy + v * 0.8, 1.9 + u * 0.8) for u, v in ring]
                M.loft([list(reversed(pts)), list(reversed(tip))], m(4, "steel"))

    # Sealed copy for the outline shell (D90/D118): the platform as one closed solid on the ground,
    # no joints, pits or ground stones, so the ink stays on the platform's silhouette only.
    S = Mesh()
    S.block(plan, G, TOP, 0, ch=CH)
    sbm = S.bm
    bmesh.ops.recalc_face_normals(sbm, faces=sbm.faces)
    bmesh.ops.scale(sbm, vec=(U, U, U), verts=sbm.verts)
    sme = bpy.data.meshes.new(f"{NAME}_sealed_s{step}")
    sbm.to_mesh(sme)
    sbm.free()
    sealed = bpy.data.objects.new(f"{NAME}_sealed_s{step}", sme)
    coll.objects.link(sealed)

    bm = M.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.scale(bm, vec=(U, U, U), verts=bm.verts)
    me = bpy.data.meshes.new(f"{NAME}_A_s{step}")
    bm.to_mesh(me)
    bm.free()
    for mt in m.list:
        me.materials.append(mt)
    obj = bpy.data.objects.new(f"{NAME}_A_s{step}", me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(32))
    return obj, sealed


def split_open(obj, layout, coll):
    """Cut the outline shell into the pieces without filling the cuts (no ink along the seams)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(o)
        out[name] = o
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    bake = "--no-bake" not in argv
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    shown = []
    for step in range(3):
        obj, sealed = build(sprite, step, coll)
        obj.name = obj.data.name = f"{NAME}_{step}"
        print(f"step {step}: {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
        shell = common.outline_shell(sealed, coll, voxel=0.014, faces=4000, smooth=6, inside=0.01)
        shell.hide_render = True
        bpy.data.objects.remove(sealed, do_unlink=True)
        if bake:  # AO/roughness only (D50/D65), on the merged object before it is cut
            T.TINT = (1.0, 1.0, 1.0)
            T.TEXTURED = tuple(range(len(obj.data.materials)))
            import tempfile
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"nshp191_bake{step}_"), size=1024, samples=64)
        pieces = common.split_assembly(obj, layout, coll)
        shells = split_open(shell, layout, coll)
        suffix = "" if step == 0 else f"-f{step + 1}"
        for name, cx, cy in layout:
            data = common.load_sprite(ROOT, name)
            sprites = [{**sp, "frames": [sp["frames"][step]]} for sp in data["sprites"]]
            model = f"{name}{suffix}"
            p, sh = pieces[name], shells[name]
            p.name = model
            p.data.set_sharp_from_angle(angle=math.radians(32.0))
            sh.name = f"{model}_outline"
            sh.data.shade_smooth()
            sh["tyrian_outline"] = True
            sh.data.materials.clear()
            sh.data.materials.append(outline_mat)
            objs = [p] + ([sh] if len(sh.data.polygons) else [])
            common.export_sprite_model(ROOT, objs, f"enemies/{model}", sprites,
                                       image_format="WEBP" if bake else "AUTO")
            for o in objs:
                o.location = (cx / 12 + step * 5.0, -cy / 12, 0)
            shown += objs
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.objects.remove(shell, do_unlink=True)
    if "--out" in argv:
        common.export_glb(shown, Path(argv[argv.index("--out") + 1]), image_format="WEBP" if bake else "AUTO")


if __name__ == "__main__":
    main()
