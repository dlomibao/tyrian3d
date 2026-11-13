"""Red rocket lying sideways (newsh8.shp, assembly of newsh8-125 + newsh8-127).

What it is: the same low-flying rocket as assembly-newsh8-191 (batch 1), turned a quarter turn:
it skims RIGHT across the screen over the ground, nose to the right. Seen from above (the 48x28
sprite, axis on row 11): the glowing exhaust at the left (columns 0-2), the dark red nozzle with a
glowing cooling band (columns 3-5), the grey engine module with a framed brown window (columns
6-17), a brown clamp collar with two swept brown fins and red tip pods (columns 13-23, rows 0-4 and
18-22), then the big red warhead body with two glowing vent slits (columns 29 and 31) tapering to
a blunt nose at column 47.

The build is batch 1's rebuilt assembly-newsh8-191 (e3-enemies-1, copied here, not imported), in
its own pixel frame (L = sprite row - 11 across the axis, R = sprite column + 4 along it, z up),
placed by to_units: X = (R - 28) / 12, Y = (2.5 - L) / 12.

Contract: the same two pieces (newsh8-125 centre (-12, 0) px, newsh8-127 (+12, 0)), one frame each
(125, 127), pal_<index> materials, D90/D118 outline shell from a sealed pre-cull copy, sunk under
the top surface (ink on the silhouette only), split open per piece.

Output: public/models/enemies/<piece>.glb and src/render/spriteModels/<piece>.json for each piece.

    blender -b --factory-startup -P assets/blender/enemies/assembly-newsh8-125.py -- [--bake] [--measure dir]
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "assets" / "blender" / "enemies"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "assembly-newsh8-125"
TAG = "n8r125A"
PIECES = ["newsh8-125", "newsh8-127"]
LAYOUT = [("newsh8-125", -12, 0), ("newsh8-127", 12, 0)]
PX = 1 / 12
DX = 0.0  # fine axial shift, px
ZC = 8.6  # body axis height, px
VR = 0.8  # body vertical radius / half width


def to_units(bm):
    """px (L, R, z) -> Blender units: X = (R - 28 + DX) / 12, Y = (2.5 - L) / 12, Z = z / 12."""
    m = Matrix(((0, PX, 0, (DX - 28) * PX), (-PX, 0, 0, 2.5 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)


# --- sprite data --------------------------------------------------------------------------------

def load_sprite():
    data = common.load_sprite(WT, PIECES[0])
    for p in PIECES[1:]:
        data["colors"].update(common.load_sprite(WT, p)["colors"])
    return data


def slit_sparks():
    """[(R, L, palette index)]: the bright pixels (>= 121) of the two slit columns of newsh8-127
    (its columns 5 and 7 = assembly columns 29 and 31 = R 33 and 35, rows 8-13)."""
    d = common.load_sprite(WT, "newsh8-127")
    f = d["frames"][0]
    out = []
    for c in (5, 7):
        for r, row in enumerate(f["pixels"]):
            v = int(row.split()[c]) if isinstance(row, str) else int(row[c])
            if v >= 121:
                out.append((24 + c + 4, r - 11, v))
    return out


# --- materials ----------------------------------------------------------------------------------

class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.index = {}

    def get(self, key, idx, metallic=0.55, roughness=0.4, glow=0.0, frames=None, spec=None):
        if key in self.index:
            return self.index[key]
        tag = f"{TAG}-{key}" if frames or key != str(idx) else TAG
        m = common.palette_material(self.sprite, idx, tag, metallic=metallic, roughness=roughness,
                                    emission_strength=glow, frames=frames)
        if spec is not None:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            bsdf.inputs["Specular IOR Level"].default_value = spec
        self.list.append(m)
        self.index[key] = len(self.list) - 1
        return self.index[key]


def make_mats(sprite):
    M = Mats(sprite)
    k = {}
    k["body"] = M.get("69", 69, metallic=0.45, roughness=0.36)
    k["tip"] = M.get("71", 71, metallic=0.55, roughness=0.34)
    k["nozzle"] = M.get("115", 115, metallic=0.65, roughness=0.42)
    k["housing"] = M.get("5", 5, metallic=0.7, roughness=0.32)
    k["rim"] = M.get("10", 10, metallic=0.75, roughness=0.26)
    k["frame"] = M.get("65", 65, metallic=0.4, roughness=0.45)
    k["pane"] = M.get("20", 20, metallic=0.1, roughness=0.14, spec=0.9)
    k["fin"] = M.get("19", 19, metallic=0.45, roughness=0.42)
    k["collar"] = M.get("22", 22, metallic=0.5, roughness=0.38)
    glow = dict(metallic=1.0, roughness=0.9, glow=1.3)
    k["plume"] = M.get("plume", 122, **glow)
    k["core"] = M.get("core", 126, **glow)
    k["band"] = M.get("band", 120, **glow)
    k["slit"] = M.get("120", 120, **glow)
    return M, k


# --- mesh builders (px) -------------------------------------------------------------------------

def ell(w, v, zc, n):
    """An ellipse section: n points (x, z), the first at the bottom, counter-clockwise from +R."""
    out = []
    for i in range(n):
        a = -math.pi / 2 + 2 * math.pi * (i + 0.5) / n
        out.append((w * math.cos(a), zc + v * math.sin(a)))
    return out


def sel(w, zt, zb, n, p=6.0):
    """A superellipse (rounded rectangle) section from zb to zt, half width w."""
    zc, h = (zt + zb) / 2, (zt - zb) / 2
    out = []
    for i in range(n):
        a = -math.pi / 2 + 2 * math.pi * (i + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        out.append((w * math.copysign(abs(c) ** (2 / p), c), zc + h * math.copysign(abs(s) ** (2 / p), s)))
    return out


def loft(bm, stations, matf, cap0=True, cap1=True, x0=0.0):
    """stations: [(R, [(x, z), ...] or None for a tip point (R, z))]; matf(i) -> material of the band
    between station i and i + 1 (i = -1 / len-1 for the caps)."""
    rings = []
    for R, sec in stations:
        if isinstance(sec, tuple):  # a tip: (x, z)
            rings.append([bm.verts.new((x0 + sec[0], R, sec[1]))])
        else:
            rings.append([bm.verts.new((x0 + x, R, z)) for x, z in sec])
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        n = max(len(a), len(b))
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1:
                f = (a[0], b[j], b[i])
            elif len(b) == 1:
                f = (a[i], a[j], b[0])
            else:
                f = (a[i], a[j], b[j], b[i])
            face = bm.faces.new(f)
            face.material_index = matf(k)
            face.smooth = True
    if cap0 and len(rings[0]) > 2:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = matf(-1)
    if cap1 and len(rings[-1]) > 2:
        f = bm.faces.new(rings[-1])
        f.material_index = matf(len(rings) - 1)


def hullbox(bm, pts, mat, smooth=False):
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs)
    dead = {v for v in res["geom_interior"] + res["geom_unused"] if isinstance(v, bmesh.types.BMVert)}
    dead |= {v for v in vs if not v.link_faces}
    if dead:
        bmesh.ops.delete(bm, geom=list(dead), context="VERTS")
    for g in res["geom"]:
        if isinstance(g, bmesh.types.BMFace):
            g.material_index = mat
            g.smooth = smooth
    # merge coplanar triangles into n-gons (cleaner shading, fewer faces)
    faces = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace) and g.is_valid]
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=list({v for f in faces for v in f.verts}),
                             edges=list({e for f in faces for e in f.edges}))


def chbox(bm, x0, x1, r0, r1, z0, z1, ch, mat, chz=None):
    hullbox(bm, T.cbox(x0, x1, r0, r1, z0, z1, ch, chz), mat)


def chamfer_slab(bm, outline, zmid, thick, inset, mat):
    """A convex plate (outline: [(x, R)] counter-clockwise seen from above, in px) with chamfered
    edges: top and bottom faces inset by `inset`; thick(x, R) is the plate thickness there."""
    n = len(outline)
    cx = sum(p[0] for p in outline) / n
    cy = sum(p[1] for p in outline) / n

    def ins(i):
        x, y = outline[i]
        px_, py = outline[i - 1]
        nx_, ny = outline[(i + 1) % n]
        # inward offset along the bisector of the two edge normals
        def nrm(ax, ay, bx, by):
            dx, dy = bx - ax, by - ay
            ln = math.hypot(dx, dy) or 1
            m = (-dy / ln, dx / ln)
            # point toward the centroid
            if (cx - ax) * m[0] + (cy - ay) * m[1] < 0:
                m = (-m[0], -m[1])
            return m
        n1 = nrm(px_, py, x, y)
        n2 = nrm(x, y, nx_, ny)
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        bl = math.hypot(bx, by) or 1
        cosh = max(0.3, (n1[0] * bx + n1[1] * by) / bl)
        d = inset / cosh
        return x + bx / bl * d, y + by / bl * d

    mid = [bm.verts.new((x, y, zmid)) for x, y in outline]
    top, bot = [], []
    for i in range(n):
        x, y = ins(i)
        t = thick(*outline[i]) / 2
        top.append(bm.verts.new((x, y, zmid + t)))
        bot.append(bm.verts.new((x, y, zmid - t)))
    for i in range(n):
        j = (i + 1) % n
        for a, b in ((top, mid), (mid, bot)):
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index = mat
    f = bm.faces.new(top)
    f.material_index = mat
    f = bm.faces.new(list(reversed(bot)))
    f.material_index = mat


# --- shape functions (px) -----------------------------------------------------------------------

# Warhead body half width by row (the inner mask: neck 6.5, bulge 8.5 rows 32-41, nose at 51).
BODY_R = [22.0, 23.5, 24.5, 27.0, 29.8, 30.6, 31.2, 31.8, 32.6, 37.0, 41.4, 42.8, 44.4, 46.0, 47.4,
          48.7, 49.7, 50.4, 50.85, 51.05]
BODY_W = [6.0, 6.45, 6.62, 6.65, 6.65, 6.9, 7.45, 8.25, 8.6, 8.7, 8.5, 7.75, 7.4, 6.6, 5.75, 4.95,
          4.1, 3.25, 2.2, 0.0]
_BW = T.pchip(BODY_R, BODY_W)
GROOVES = [42.3, 47.6]


def groove(R):
    g = 0.0
    for rg in GROOVES:
        x = (R - rg) / 0.26
        if abs(x) < 1:
            g += 0.28 * (1 - x * x) ** 2
    return g


def body_w(R):
    return max(0.0, _BW(R) - groove(R)) if R < 51.05 else 0.0


def body_top(R, L=0.0):
    w = body_w(R)
    if w <= abs(L):
        return ZC
    return ZC + VR * w * math.sqrt(1 - (L / w) ** 2)


HOUSING_TOP = ZC + 4.9
HOUSING_BOT = ZC - 4.6
HW = 5.55


# --- the rocket ---------------------------------------------------------------------------------

def build(bm, k):
    N = 32
    # Warhead body: neck, shoulder, bulge, nose.
    rs = sorted(set([22.0, 22.8, 23.6, 24.5, 25.8, 27.2, 28.6, 29.8, 30.3, 30.7, 31.0, 31.3, 31.6, 31.9,
                     32.3, 32.8, 33.5, 34.5, 35.5, 36.5, 38.0, 39.5, 40.8, 41.6, 43.4, 44.4, 45.2, 46.0,
                     46.8, 48.4, 49.0, 49.5, 50.0, 50.4, 50.7, 50.9]
                    + [g + d for g in GROOVES for d in (-0.3, -0.15, 0.0, 0.15, 0.3)]))
    st = [(R, ell(body_w(R), VR * body_w(R), ZC, N)) for R in rs] + [(51.05, (0.0, ZC))]
    loft(bm, st, lambda i: k["body"])

    # Collar: a clamp ring with chamfered edges.
    st = [(20.8, ell(6.25, VR * 6.25, ZC, N)), (21.15, ell(6.8, VR * 6.8, ZC, N)), (21.7, ell(6.85, VR * 6.85, ZC, N)),
          (21.85, ell(6.7, VR * 6.7, ZC, N)), (22.05, ell(6.85, VR * 6.85, ZC, N)),
          (23.85, ell(6.85, VR * 6.85, ZC, N)), (24.2, ell(6.3, VR * 6.3, ZC, N))]
    loft(bm, st, lambda i: k["collar"])

    # Engine module: a rounded-rectangle block, aft edge chamfered (the bright rim), groove at 18.25.
    def hsec(w, zt, zb):
        return sel(w, zt, zb, 40, p=7.0)
    hst = [(10.0, 4.55, HOUSING_TOP - 1.5, HOUSING_BOT + 1.1), (10.35, 5.05, HOUSING_TOP - 0.85, HOUSING_BOT + 0.6),
           (10.75, 5.45, HOUSING_TOP - 0.2, HOUSING_BOT + 0.15), (11.0, HW, HOUSING_TOP, HOUSING_BOT),
           (14.5, HW, HOUSING_TOP, HOUSING_BOT), (17.95, HW, HOUSING_TOP, HOUSING_BOT),
           (18.1, HW - 0.3, HOUSING_TOP - 0.3, HOUSING_BOT), (18.4, HW - 0.3, HOUSING_TOP - 0.3, HOUSING_BOT),
           (18.55, HW, HOUSING_TOP, HOUSING_BOT), (19.0, HW, HOUSING_TOP - 0.05, HOUSING_BOT),
           (20.0, HW, HOUSING_TOP - 0.5, HOUSING_BOT), (21.6, HW - 0.1, HOUSING_TOP - 1.0, HOUSING_BOT + 0.2)]
    loft(bm, [(R, hsec(w, zt, zb)) for R, w, zt, zb in hst],
         lambda i: k["rim"] if i < 3 else k["housing"])

    top = HOUSING_TOP
    # Window bezel (columns 9-13, rows 11-17) and the brown pane sunk in it (columns 10-12, rows 12-16).
    for x0, x1, r0, r1 in ((-2.5, 2.5, 11.05, 12.0), (-2.5, 2.5, 17.0, 17.95), (-2.5, -1.5, 11.05, 17.95),
                           (1.5, 2.5, 11.05, 17.95)):
        chbox(bm, x0, x1, r0, r1, top - 0.6, top + 0.5, 0.18, k["frame"])
    chbox(bm, -1.55, 1.55, 11.95, 17.05, top - 0.6, top + 0.15, 0.05, k["pane"])
    # Two low rails beside the window (columns 7 and 15).
    for s in (-1, 1):
        chbox(bm, s * 4.0 - 0.45, s * 4.0 + 0.45, 11.6, 17.6, top - 0.6, top + 0.3, 0.2, k["housing"])
    # Side strakes along the module's flanks (game camera and side view).
    for s in (-1, 1):
        chbox(bm, *sorted((s * (HW - 0.4), s * (HW + 0.25))), 11.6, 17.6, ZC + 1.2, ZC + 2.2, 0.2, k["rim"])
    # Grey strap over the collar (columns 9-13, rows 21-22), riding the housing's forward slope.
    hullbox(bm, T.cbox(-2.45, 2.45, 19.4, 23.1, top - 1.6, top - 0.15, 0.25)
            + T.cbox(-2.45, 2.45, 20.6, 23.1, ZC + 4.2, ZC + 5.75, 0.25), k["housing"])

    # Nozzle: bell with a lip, the glowing band at row 8, a root ring; then the plume.
    N2 = 28
    nst = [(6.75, 3.55), (6.85, 4.3), (7.05, 4.55), (7.55, 4.55), (7.72, 4.25), (7.78, 4.3), (8.8, 4.3),
           (8.86, 4.25), (9.0, 4.55), (9.85, 4.55), (10.05, 4.3), (10.6, 4.3)]
    mats_n = []
    for (r0, _), (r1, _) in zip(nst, nst[1:]):
        mid = (r0 + r1) / 2
        mats_n.append(k["band"] if 7.75 < mid < 8.83 else k["nozzle"])
    loft(bm, [(R, ell(w, w, ZC, N2)) for R, w in nst],
         lambda i: k["nozzle"] if i < 0 or i >= len(mats_n) else mats_n[i])
    pr = [6.95, 6.6, 6.2, 5.8, 5.5, 5.25, 5.1, 5.02]
    pf = T.pchip([4.98, 5.1, 5.4, 5.8, 6.3, 6.95], [0.0, 1.9, 2.6, 3.05, 3.5, 3.85])
    st = [(R, ell(pf(R), pf(R), ZC, N2)) for R in pr] + [(4.98, (0.0, ZC))]
    loft(bm, st, lambda i: k["plume"])
    # the white-hot core pokes out of the plume's middle
    pc = T.pchip([4.62, 4.75, 4.95, 5.3, 6.9], [0.0, 1.0, 1.5, 1.85, 1.9])
    st = [(R, ell(pc(R), pc(R), ZC, 20)) for R in (6.9, 5.8, 5.3, 5.0, 4.85, 4.72, 4.66)] + [(4.62, (0.0, ZC))]
    loft(bm, st, lambda i: k["core"])
    # Mounting lugs from the nozzle root to the module (columns 6 and 16, rows 8-9).
    for s in (-1, 1):
        chbox(bm, *sorted((s * 3.6, s * 5.55)), 7.9, 10.3, ZC - 1.0, ZC + 1.0, 0.3, k["body"])

    # Fins: swept chamfered plates (columns 1-5 / 17-21, rows 17-28) and red tip pods.
    zf = ZC + 0.3
    fin = [(4.4, 16.5), (6.15, 17.1), (10.0, 21.6), (10.0, 25.3), (7.3, 28.15), (4.4, 28.3)]

    def thick(x, R):
        return 1.5 - 0.11 * (x - 4.4)
    for s in (-1, 1):
        pts = [(s * x, R) for x, R in fin]
        if s < 0:
            pts = list(reversed(pts))
        chamfer_slab(bm, pts, zf, thick, 0.35, k["fin"])
        # tip pod: a slim capsule along R
        pf2 = T.pchip([21.7, 22.15, 22.9, 24.4, 25.0, 25.4], [0.0, 0.55, 0.74, 0.74, 0.5, 0.0])
        rs2 = [21.7, 21.85, 22.15, 22.5, 22.9, 23.6, 24.4, 24.75, 25.05, 25.25, 25.4]
        st = []
        for R in rs2:
            w = pf2(R)
            st.append((R, (0.0, zf) if w <= 0 else ell(w, w * 0.95, zf, 16)))
        loft(bm, st, lambda i: k["tip"], x0=s * 9.75)

    # Ventral fin (side view only): a thin swept blade under the module.
    vb = ZC - 7.2
    hullbox(bm, [(x, R, z) for x in (-0.45, 0.45) for R, z in ((13.2, HOUSING_BOT + 0.6), (21.0, HOUSING_BOT + 1.2),
                                                                (16.2, vb), (19.0, vb))], k["fin"])

    # Vent slits: flush glowing strips in the warhead's top (rows 33 and 35, columns 8-13).
    for R in (33.0, 35.0):
        conformal(bm, -3.5, 2.5, R + 0.08, R + 0.92, 0.05, -0.4, k["slit"])


def conformal(bm, l0, l1, r0, r1, off, depth, mat, nx=6, ny=2):
    """A strip on the body's top surface over [l0, l1] x [r0, r1] (px), `off` above it, with walls
    down to `depth` below it: a flush insert."""
    xs = [l0 + (l1 - l0) * i / nx for i in range(nx + 1)]
    ys = [r0 + (r1 - r0) * j / ny for j in range(ny + 1)]
    topv = [[bm.verts.new((x, y, body_top(y, x) + off)) for x in xs] for y in ys]
    botv = [[bm.verts.new((x, y, body_top(y, x) + depth)) for x in xs] for y in ys]
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((topv[j][i], topv[j][i + 1], topv[j + 1][i + 1], topv[j + 1][i]))
            f.material_index = mat
            f = bm.faces.new((botv[j][i], botv[j + 1][i], botv[j + 1][i + 1], botv[j][i + 1]))
            f.material_index = mat
    ring_t = [topv[0][i] for i in range(nx + 1)] + [topv[j][nx] for j in range(1, ny + 1)] \
        + [topv[ny][i] for i in range(nx - 1, -1, -1)] + [topv[j][0] for j in range(ny - 1, 0, -1)]
    ring_b = [botv[0][i] for i in range(nx + 1)] + [botv[j][nx] for j in range(1, ny + 1)] \
        + [botv[ny][i] for i in range(nx - 1, -1, -1)] + [botv[j][0] for j in range(ny - 1, 0, -1)]
    m = len(ring_t)
    for i in range(m):
        f = bm.faces.new((ring_t[i], ring_b[i], ring_b[(i + 1) % m], ring_t[(i + 1) % m]))
        f.material_index = mat


def build_sparks(bm, frame, sparks, slot_of):
    for R, L, idx in sparks[frame]:
        conformal(bm, L - 0.5, L + 0.5, R + 0.08, R + 0.92, 0.12, -0.1, slot_of[idx], nx=2, ny=1)


# --- object helpers -----------------------------------------------------------------------------

def to_object(name, bm, mats, coll, sharp=34):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    to_units(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(sharp))
    return obj


def cull_hidden(obj, grid=3, ndirs=40):
    """Delete faces no ray from outside can reach (copied from assembly-newshu-79.py)."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 1.5e-4
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    pts.append(vs[0].lerp(vs[1], u).lerp(vs[3].lerp(vs[2], u), v))
        else:
            for vco in vs[:12]:
                for t in (0.4, 0.9):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    return len(dead)


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (copied from newshv-10.py, D185): every
    shell vertex is dropped to `margin` under the lowest model top within `reach` (seen from above)."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    moved = 0
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for kk in range(12):
            a = 2 * math.pi * kk / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def split_open(obj, layout, coll, suffix):
    """split_assembly without filling the cuts (for the outline shell: no ink along the seam)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}{suffix}")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        o = bpy.data.objects.new(f"{name}{suffix}", me)
        coll.objects.link(o)
        for key in obj.keys():
            o[key] = obj[key]
        if len(me.polygons):
            me.shade_smooth()
        out[name] = o
    return out


# --- measuring ----------------------------------------------------------------------------------

def top_mask(objs, w_px, h_px, centre, out_png, k=4):
    """Flat white top view of `objs` on a w_px x h_px sprite grid (k image px per sprite px)."""
    scene = bpy.context.scene
    hidden = {}
    for o in scene.objects:
        hidden[o.name] = o.hide_render
        o.hide_render = o not in objs
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (1, 1, 1)
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = w_px * k, h_px * k
    scene.render.resolution_percentage = 100
    cd = bpy.data.cameras.new("topcam")
    cd.type = "ORTHO"
    cd.ortho_scale = max(w_px, h_px) / 12
    cam = bpy.data.objects.new("topcam", cd)
    scene.collection.objects.link(cam)
    cam.location = (centre[0], centre[1], 30)
    scene.camera = cam
    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in scene.objects:
        if o.name in hidden:
            o.hide_render = hidden[o.name]


def measure(whole, pieces, outdir):
    import sprite_mask as SM
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    res = {}
    top_mask([whole], 48, 28, (0, 0), outdir / "top_assembly.png")
    idx, colors = SM.load(NAME)
    m = SM.masks(idx, colors)
    top = SM.read_png_mask(str(outdir / "top_assembly.png"))
    r = SM.measure(m, top)
    res["assembly"] = r
    kk = len(top[0]) // 48
    lines = []
    for y in range(28):
        ln = ""
        for x in range(48):
            cov = sum(top[y * kk + j][x * kk + i] for j in range(kk) for i in range(kk)) / (kk * kk) >= 0.5
            inn, bd = m["inner"][y][x], m["border"][y][x]
            ln += ("#" if inn else "+") if cov else ("-" if inn else ("o" if bd else "."))
        lines.append(ln)
    (outdir / "diff.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    for name, cx, cy in LAYOUT:
        top_mask([pieces[name]], 24, 28, pieces[name].location[:2], outdir / f"top_{name}.png")
        data = json.loads((WT / "reference" / "models" / name / "sprite.json").read_text())
        frames = [SM._rows(f) for f in data["frames"]]
        for f in data["frames"]:
            idx, colors = SM.load(name, f["index"])
            m = SM.masks(idx, colors, SM.pulse_partners(idx, frames))
            res[f"{name}@{f['index']}"] = SM.measure(m, SM.read_png_mask(str(outdir / f"top_{name}.png")))
    (outdir / "measure.json").write_text(json.dumps(res, indent=1))
    for key, r in res.items():
        print(f"MEASURE {key}: rule grid {r['iou_rule_grid']} rule {r['iou_rule']} edge {r['edge_vs_inner_px']:+.2f}")
    return res


# --- main ---------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    bpy.context.view_layer.update()
    sprite = load_sprite()
    M, k = make_mats(sprite)

    bm = bmesh.new()
    build(bm, k)
    sparks = slit_sparks()
    idxs = sorted({i for *_, i in sparks})
    slot = {i: M.get(f"spark{i}", i, metallic=1.0, roughness=0.9, glow=1.3) for i in idxs}
    for R, L, i in sparks:
        conformal(bm, L - 0.5, L + 0.5, R + 0.08, R + 0.92, 0.12, -0.1, slot[i], nx=2, ny=1)
    whole = to_object(NAME, bm, M.list, coll)
    print("whole faces", len(whole.data.polygons), "tris", sum(len(p.vertices) - 2 for p in whole.data.polygons))

    bpy.context.view_layer.update()
    # Sealed pre-cull copy -> outline shell (D90/D118), sunk under the top (D185), split open.
    shell_whole = common.outline_shell(whole, coll, voxel=0.025, faces=2600, smooth=6, inside=0.004)
    sink_shell(shell_whole, whole, margin=0.02, reach=0.05)
    shells = split_open(shell_whole, LAYOUT, coll, "_outline")
    for o in shells.values():
        o["tyrian_outline"] = True

    pieces = common.split_assembly(whole, LAYOUT)
    frame_parts = {p: [] for p in PIECES}

    info = {}
    for name, cx, cy in LAYOUT:
        n = cull_hidden(pieces[name])
        me = pieces[name].data
        me.set_sharp_from_angle(angle=math.radians(34))
        info[name] = sum(len(p.vertices) - 2 for p in me.polygons)
        print(f"{name}: culled {n}, {info[name]} tris")
    for name, cx, cy in LAYOUT:
        pieces[name].location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()

    if "--measure" in argv:
        measure(whole, pieces, argv[argv.index("--measure") + 1])
    bpy.data.objects.remove(whole, do_unlink=True)
    bpy.data.objects.remove(shell_whole, do_unlink=True)

    if "--bake" in argv:
        for name, _, _ in LAYOUT:
            p = pieces[name]
            for i, m in enumerate(list(p.data.materials)):
                c = m.copy()
                c.name = m.name + f"_{name}"
                p.data.materials[i] = c
            T.bake_maps(p, tempfile.mkdtemp(prefix=f"{TAG}_{name}_"), size=1024, samples=48)
    fmt = "WEBP" if "--bake" in argv else "AUTO"

    # Export each piece (model + outline shell) to public/models and register it (spriteModels).
    for name, cx, cy in LAYOUT:
        objs = [pieces[name], shells[name]] + frame_parts[name]
        for o in objs:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, objs, f"enemies/{name}", data["sprites"], image_format=fmt)
        for o in objs:
            o.location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    info["shell_faces"] = {n: len(s.data.polygons) for n, s in shells.items()}
    print("built", info)


if __name__ == "__main__":
    main()
