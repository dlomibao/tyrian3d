"""The grey twin-walker gate (newsh5 85 + 87) and the red canister chain link (newsh5 168).

What it is (sprite read, 48x28 gate): two hunched grey walkers face the player, each a heavy
armoured head (helmet plate over a sloping face with two red eyes and a lit chin bar) crouched on
two short legs, the outer one ending in a dark-brown foot with rust talons. A low shoulder yoke
carries each walker to a round grey gate post; the two posts are joined at the top by a cross bar
with a red hinge pin on the centre column. From each post a pink claw arm hangs forward and down,
turns into a thin grey rod with a ball knuckle, and the two rods meet in a rust U strap at the
front: a cradle round the open middle, where the grey bomb (newsh5-77) sits. Mirror symmetric
about the gate's centre column (pixel 24; x = 24.5 px in edge coordinates).

The canister link (24x28): a glossy red drum lying along a blue-grey pole that runs the whole
height of the block, so stacked links make one long pole (the pole and its coupling sleeves are
cut exactly at the block's edges, and so is the outline shell). Seam grooves at rows 10 and 18,
a strap clamp and a slim side tank on the right, mounting saddles on top over the pole, a latch at
the upper left and an orange lamp.

Exports public/models/enemies/newsh5-85.glb and newsh5-87.glb (+ spriteModels JSON); newsh5-168.py
loads this builder and exports only newsh5-168. Review copies only behind the flags: --out FILE (the
pieces placed as in the layout), --game DIR (each piece's glb).

    blender --background --python assembly-newsh5-85.py [-- --out FILE] [--game DIR]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve()


def find_repo():
    for p in HERE.parents:
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("repo root not found")


ROOT = find_repo()
sys.path[:0] = [str(ROOT / "assets" / "blender"), str(ROOT / "assets" / "blender" / "enemies")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import lib_b051 as lib  # noqa: E402  (read-only: tube3d, ellipsoid, mirror)

NAME = "assembly-newsh5-85"
PIECES = ["newsh5-85", "newsh5-87"]
POLE = "newsh5-168"
AX = 24.5  # mirror line of the gate in px (edge coordinates: pixel c spans [c, c + 1])
PX = 1 / 12

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(flag, default=None):
    return ARGV[ARGV.index(flag) + 1] if flag in ARGV else default


# --- small geometry kit (all in sprite px: x right, y down the sprite, z up) -----------------------

def pch(keys):
    xs, ys = zip(*keys)
    f = T.pchip(list(xs), list(ys))
    lo, hi = xs[0], xs[-1]
    return lambda t: f(min(hi, max(lo, t)))


def frange(a, b, step):
    n = max(1, int(math.ceil((b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def rrect(xl, xr, zb, zt, rt, rb=0.25, nc=4):
    """A rounded-rectangle section in x-z: flat bottom at zb, top corners of radius rt."""
    hw, h = (xr - xl) / 2, zt - zb
    rt = max(0.15, min(rt, hw * 0.98, h * 0.9))
    rb = max(0.12, min(rb, hw * 0.98, h - rt))
    pts = []
    for cx, cz, r, a0 in ((xl + rb, zb + rb, rb, 180), (xr - rb, zb + rb, rb, 270),
                          (xr - rt, zt - rt, rt, 0), (xl + rt, zt - rt, rt, 90)):
        for k in range(nc + 1):
            a = math.radians(a0 + 90 * k / nc)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def skin(bm, rings, mats, cap0=True, cap1=True, smooth=True):
    """Faces between consecutive rings of 3D points (equal counts); mats per band or one int."""
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    start = len(bm.faces)
    out = []
    for i, (r0, r1) in enumerate(zip(vs, vs[1:])):
        m = mats if isinstance(mats, int) else mats[min(i, len(mats) - 1)]
        n = len(r0)
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = m
            f.smooth = smooth
            out.append(f)
    m0 = mats if isinstance(mats, int) else mats[0]
    m1 = mats if isinstance(mats, int) else mats[-1]
    if cap0:
        f = bm.faces.new(list(reversed(vs[0])))
        f.material_index, f.smooth = m0, False
    if cap1:
        f = bm.faces.new(vs[-1])
        f.material_index, f.smooth = m1, False
    return out


def loft_y(bm, ys, secf, mats, **kw):
    return skin(bm, [[(x, y, z) for x, z in secf(y)] for y in ys], mats, **kw)


def _fix_new(bm, before, mat, smooth=True):
    """lib's helpers paint faces by index from a start, which breaks after bmesh deletes reorder
    the sequence: paint the faces that are new since `before` instead."""
    for f in bm.faces:
        if f not in before:
            f.material_index = mat
            f.smooth = smooth


def tube(bm, pts, radii, mat, sides=10, smooth=True, caps=True):
    before = set(bm.faces)
    lib.tube3d(bm, pts, radii, sides=sides, mat=mat, smooth=smooth, caps=caps)
    _fix_new(bm, before, mat, smooth)


def sweep_rect(bm, pts, w, h, mat, rc=0.35, nc=2, caps=True):
    """A strap: rounded-rect section (w across, h tall) carried along a 3D polyline (mostly flat)."""
    sec = rrect(-w / 2, w / 2, -h / 2, h / 2, rc, rc, nc)
    P = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(P):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(Vector((0, 0, 1))).normalized()
        rings.append([tuple(p + side * u + Vector((0, 0, v))) for u, v in sec])
    skin(bm, rings, mat, cap0=caps, cap1=caps)


def ellipsoid(bm, c, r, mat, seg=12, rings=6):
    before = set(bm.faces)
    lib.ellipsoid(bm, c, r, segments=seg, rings=rings, mat=mat)
    _fix_new(bm, before, mat)


def chbox(bm, x0, x1, y0, y1, z0, z1, ch, mat, smooth=False):
    pts = T.cbox(x0, x1, y0, y1, z0, z1, ch)
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    for f in {f for v in verts if v.is_valid for f in v.link_faces}:
        f.material_index = mat
        f.smooth = smooth


def hull(bm, pts, mat):
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    for f in {f for v in verts if v.is_valid for f in v.link_faces}:
        f.material_index = mat
        f.smooth = False


def surface_z(bm, x, y):
    """Height of the mesh under (x, y) so far (a ray straight down), or None."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    hit = tree.ray_cast(Vector((x, y, 60)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] is not None else None


def to_object(name, bm, mats, coll, origin_x, origin_y=14.0, smooth_angle=40):
    """px -> Blender (X = (x - origin_x) / 12, Y = (origin_y - y) / 12, Z = z / 12)."""
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    m = Matrix(((PX, 0, 0, -origin_x * PX), (0, -PX, 0, origin_y * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


# --- materials ---------------------------------------------------------------------------------------

def merged_sprite():
    data = {n: common.load_sprite(ROOT, n) for n in PIECES + [POLE]}
    s = dict(data[PIECES[0]])
    s["colors"] = {}
    for d in data.values():
        s["colors"].update(d["colors"])
    return s, data


def spec(mat, level):
    b = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b is not None and "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = level
    return mat


def gate_materials(sprite):
    tag = "nsh5_85A"
    P = lambda i, m, r, **kw: common.palette_material(sprite, i, tag, metallic=m, roughness=r, **kw)  # noqa: E731
    # Steel like the bomb it holds (newsh5-77: metallic, smooth), toned down on the darker greys
    # so they don't go to black mirrors in the game (D176).
    mats = {
        "head": P(5, 0.55, 0.36), "web": P(4, 0.5, 0.42), "post": P(7, 0.6, 0.32),
        "legO": P(5, 0.55, 0.38), "legI": P(6, 0.55, 0.36), "rod": P(8, 0.65, 0.3),
        "collar": P(104, 0.45, 0.4), "claw": P(72, 0.35, 0.36), "band": P(71, 0.35, 0.45),
        "talon": P(70, 0.3, 0.45), "foot": P(162, 0.15, 0.7), "dark": P(2, 0.3, 0.6),
        "eye": common.palette_material(sprite, 74, tag + "_eye", metallic=1.0, roughness=0.6,
                                       emission_strength=1.2),
    }
    for k in ("head", "post", "legO", "legI", "rod"):
        spec(mats[k], 0.7)
    order = list(mats)
    return [mats[k] for k in order], {k: i for i, k in enumerate(order)}


def pole_materials(sprite):
    tag = "nsh5_168A"
    P = lambda i, m, r, **kw: common.palette_material(sprite, i, tag, metallic=m, roughness=r, **kw)  # noqa: E731
    mats = {
        "red": spec(P(116, 0.3, 0.22), 0.85), "seam": P(113, 0.3, 0.4), "pole": spec(P(104, 0.55, 0.34), 0.7),
        "steel": P(106, 0.55, 0.32), "brk": P(102, 0.5, 0.38), "latch": P(103, 0.5, 0.36),
        "lamp": common.palette_material(sprite, 123, tag + "_lamp", metallic=1.0, roughness=0.6,
                                        emission_strength=1.0),
    }
    order = list(mats)
    return [mats[k] for k in order], {k: i for i, k in enumerate(order)}


# --- the gate ------------------------------------------------------------------------------------------

def build_gate(coll, mats, M):
    bm = bmesh.new()

    # ---- left half (mirrored about AX) ----
    # Head: a hunched armoured block, highest over rows 4-6, its face sloping to the chin at row 11.8.
    # Helmet narrower than the face below its lip (rows 4-6 start at column 4, rows 7-10 at 3).
    hxl = pch([(1.95, 9.2), (2.3, 8.3), (2.9, 6.7), (3.5, 5.0), (4.5, 4.25), (6.4, 4.05), (7.1, 3.15), (8.0, 3.0),
               (10.8, 3.0), (11.4, 3.55), (11.9, 4.3)])
    hxr = pch([(1.95, 11.4), (2.5, 12.2), (3.2, 13.2), (11.9, 13.4)])
    hzt = pch([(1.9, 4.6), (2.6, 7.0), (3.6, 8.7), (5.2, 9.3), (6.6, 8.9), (8.0, 7.7), (9.5, 6.1), (10.8, 4.8),
               (11.9, 3.6)])
    ys = frange(1.95, 11.9, 0.3)
    loft_y(bm, ys, lambda y: rrect(hxl(y), hxr(y), 0.0, hzt(y), 3.2, 0.3, 5), M["head"])
    # Helmet plate over the back and top (rows 2-6), its front lip a panel step at row 6.9.
    ys = frange(1.95, 6.9, 0.3)
    loft_y(bm, ys, lambda y: rrect(hxl(y) - 0.05, hxr(y) + 0.02, 3.0, hzt(y) + 0.55, 3.3, 0.3, 5), M["head"])
    # Keel strip down the helmet's crown (the lit column 9).
    pts = []
    for y in frange(2.3, 6.7, 0.55):
        z = surface_z(bm, 9.6, y)
        pts.append((9.6, y, z - 0.12))
    tube(bm, pts, [0.38] * len(pts), M["head"], sides=8)
    # Chin bar across the face's lower edge (the bright row 10), on stub brackets.
    zc = surface_z(bm, 8.0, 10.35)
    sweep_rect(bm, [(3.4, 10.4, zc - 0.25), (8.0, 10.45, zc - 0.05), (12.9, 10.4, zc - 0.25)], 1.1, 1.0, M["head"],
               rc=0.4)
    # Eyes: dark sockets with glowing red lenses on the sloping face (row 8, columns 7 and 10).
    for ex in (7.5, 10.5):
        z = surface_z(bm, ex, 8.5)
        ellipsoid(bm, (ex, 8.5, z - 0.15), (1.05, 0.95, 0.55), M["dark"], seg=12, rings=6)
        ellipsoid(bm, (ex, 8.55, z + 0.1), (0.72, 0.62, 0.42), M["eye"], seg=12, rings=6)

    # Shoulder yoke from the head to the post (columns 13-17), lower than both.
    wxr = pch([(3.8, 16.8), (7.4, 16.8), (8.4, 18.1), (12.0, 18.1)])
    wzt = pch([(3.8, 4.4), (4.6, 6.0), (7.2, 6.1), (9.5, 4.7), (12.0, 2.9)])
    ys = frange(3.8, 12.0, 0.4)
    loft_y(bm, ys, lambda y: rrect(12.6, wxr(y), 0.0, wzt(y), 1.3, 0.3, 3), M["web"])
    # A hydraulic ram on top of the yoke (sleeve and rod), head to post.
    tube(bm, [(12.4, 5.3, 6.55), (14.8, 5.3, 6.55)], [0.95, 0.95], M["web"], sides=10)
    tube(bm, [(14.6, 5.3, 6.55), (17.4, 5.3, 6.55)], [0.6, 0.6], M["rod"], sides=10)

    # Gate post (columns 16-22, rows 2-7): round, a flared foot, ringed shaft, blue-grey collar, domed cap.
    pcx, pcy, prx, pry = 19.65, 4.95, 3.35, 3.0
    prof = [(0.0, 1.0, "post"), (1.0, 1.0, "post"), (1.5, 0.9, "post"), (3.6, 0.9, "post"), (3.8, 0.84, "post"),
            (4.2, 0.84, "post"), (4.4, 0.9, "post"), (6.4, 0.9, "post"), (6.6, 0.84, "post"), (7.0, 0.84, "post"),
            (7.2, 0.9, "post"), (8.4, 0.9, "collar"), (8.7, 1.0, "collar"), (9.9, 1.0, "collar"),
            (10.2, 0.93, "post"), (11.0, 0.82, "post"), (11.6, 0.62, "post"), (11.95, 0.3, "post")]
    n = 24
    rings, bandm = [], []
    for z, s, mname in prof:
        ring = []
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            ca, sa = math.cos(a), math.sin(a)
            e = 2 / 3.2  # superellipse: the post's plan is a rounded square (rows 2-7, columns 17-22)
            ring.append((pcx + prx * s * math.copysign(abs(ca) ** e, ca), pcy + pry * s * math.copysign(abs(sa) ** e, sa), z))
        rings.append(ring)
        bandm.append(M[mname])
    skin(bm, rings, bandm[1:] + [bandm[-1]])

    # Claw arm hanging forward from the post (pink, columns 18-20, rows 8-13), a knuckle ring part way.
    chbox(bm, 16.6, 21.9, 5.6, 8.0, 0.0, 6.2, 0.6, M["web"])  # the claw's mount at the post's foot
    claw = [(19.45, 6.6, 7.6), (19.5, 8.4, 7.3), (19.6, 10.3, 6.4), (19.75, 12.2, 5.1), (20.1, 13.8, 4.0),
            (20.25, 14.7, 3.6)]
    tube(bm, claw, [1.55, 1.6, 1.55, 1.45, 1.05, 0.8], M["claw"], sides=12)
    tube(bm, [(19.5, 9.8, 6.75), (19.52, 10.5, 6.33)], [1.68, 1.68], M["collar"], sides=12)
    # Thin grey rod down to a ball knuckle (column 20, rows 14-19).
    rod = [(20.3, 14.2, 3.8), (20.5, 15.4, 3.35), (20.45, 17.2, 2.9), (20.0, 18.8, 2.4)]
    tube(bm, rod, [0.62, 0.62, 0.62, 0.66], M["rod"], sides=10)
    ellipsoid(bm, (19.35, 19.65, 2.1), (1.45, 1.35, 1.25), M["legI"], seg=14, rings=7)
    # Rust U strap: from the knuckle round the front to the centre column (rows 21-24).
    band = [(19.1, 19.9, 1.6), (19.1, 21.2, 1.35), (19.85, 22.55, 1.25), (21.2, 23.5, 1.2), (22.8, 24.1, 1.2),
            (AX, 24.2, 1.2)]
    sweep_rect(bm, band, 2.2, 1.5, M["band"], rc=0.45, caps=True)

    # Legs (rows 11-21): the outer leg (columns 5-9) and the inner one (columns 10-13), split by a
    # crease; each an armoured thigh, a knee pin and a shin running forward and down to the ground.
    oxl = pch([(11.4, 4.3), (12.4, 4.85), (16.6, 4.95)])
    ozt = pch([(11.4, 5.7), (14.0, 5.0), (16.6, 4.4)])
    loft_y(bm, frange(11.4, 16.7, 0.4), lambda y: rrect(oxl(y), 10.05, 0.0, ozt(y), 1.9, 0.25, 5), M["legO"])
    tube(bm, [(5.15, 16.45, 3.2), (9.95, 16.45, 3.2)], [1.4, 1.4], M["web"], sides=14)
    szt = pch([(16.1, 3.95), (18.0, 3.45), (19.6, 2.95), (20.1, 2.6)])
    loft_y(bm, frange(16.1, 20.1, 0.4), lambda y: rrect(5.3, 9.85, 0.0, szt(y), 1.4, 0.25, 4), M["legO"])
    ixr = pch([(10.8, 13.05), (15.8, 13.05)])
    izt = pch([(10.8, 6.1), (13.5, 5.35), (15.8, 4.7)])
    loft_y(bm, frange(10.8, 15.9, 0.4), lambda y: rrect(10.2, ixr(y), 0.0, izt(y), 1.5, 0.25, 4), M["legI"])
    tube(bm, [(10.25, 15.65, 3.55), (13.0, 15.65, 3.55)], [1.3, 1.3], M["web"], sides=14)
    jxr = pch([(15.4, 13.0), (16.4, 13.85), (19.4, 13.85), (20.3, 13.25), (21.0, 12.6)])
    jzt = pch([(15.4, 4.25), (18.0, 3.65), (20.2, 2.8), (21.0, 2.0)])
    loft_y(bm, frange(15.4, 21.0, 0.4), lambda y: rrect(10.3, jxr(y), 0.0, jzt(y), 1.3, 0.25, 4), M["legI"])
    # Ankle pin and the outer foot: a dark-brown pad with two rust talons hooking inward.
    tube(bm, [(6.0, 19.75, 1.6), (9.6, 19.75, 1.6)], [1.25, 1.25], M["web"], sides=12)
    poly = [(5.95, 19.9), (10.9, 19.9), (10.9, 21.85), (10.0, 22.7), (5.95, 22.7)]
    hull_pts = [(x, y, 0.0) for x, y in poly] + [(x, y, 1.35) for x, y in poly]
    cx_, cy_ = sum(x for x, _ in poly) / 5, sum(y for _, y in poly) / 5
    hull_pts += [(cx_ + (x - cx_) * 0.8, cy_ + (y - cy_) * 0.78, 1.95) for x, y in poly]
    hull(bm, hull_pts, M["foot"])
    tube(bm, [(8.7, 21.5, 1.15), (8.9, 23.0, 1.0), (9.4, 24.25, 0.8), (10.75, 24.95, 0.3)], [1.3, 1.3, 1.15, 0.3],
         M["talon"], sides=12)
    tube(bm, [(6.75, 21.6, 0.95), (7.1, 22.9, 0.75), (7.7, 23.65, 0.3)], [1.0, 0.85, 0.2], M["talon"], sides=10)
    # Inner foot: a grey hoof (rows 19-20, columns 10-12).
    chbox(bm, 10.3, 13.2, 19.2, 21.0, 0.0, 1.8, 0.5, M["legI"])

    lib.mirror(bm, AX)

    # ---- on the axis ----
    # Cross bar between the post collars (rows 3-4) and the red hinge pin on the centre column.
    tube(bm, [(21.2, 4.0, 9.3), (AX, 4.0, 9.3), (27.8, 4.0, 9.3)], [0.95, 0.95, 0.95], M["post"], sides=12)
    tube(bm, [(AX, 4.0, 7.9), (AX, 4.0, 10.9)], [1.05, 1.05], M["claw"], sides=12)
    tube(bm, [(AX, 4.0, 10.85), (AX, 4.0, 11.3)], [0.75, 0.55], M["post"], sides=12)

    return to_object(NAME, bm, mats, coll, origin_x=24.0)


# --- the canister link -----------------------------------------------------------------------------------

ZC = 8.0  # the pole's axis height (px)


def build_pole(coll, mats, M):
    bm = bmesh.new()
    px_, r = 11.5, 3.5
    # The pole: one straight tube through the whole block, coupling sleeves split at the block edges.
    tube(bm, [(px_, 0.0, ZC), (px_, 28.0, ZC)], [r, r], M["pole"], sides=24)
    for y0, y1 in ((0.0, 1.0), (27.0, 28.0)):
        tube(bm, [(px_, y0, ZC), (px_, y1, ZC)], [r + 0.3, r + 0.3], M["steel"], sides=24)
    # The drum, lying along the pole: domed ends, seam grooves at rows 10 and 18.
    dcx = 12.5
    prof = [(3.9, 3.9, "red"), (4.3, 4.6, "red"), (5.0, 5.7, "red"), (5.6, 6.2, "red"), (6.3, 6.45, "red"),
            (10.1, 6.5, "red"),
            (10.35, 6.05, "seam"), (10.75, 6.05, "seam"), (11.0, 6.5, "red"), (18.1, 6.5, "red"),
            (18.35, 6.05, "seam"), (18.75, 6.05, "seam"), (19.0, 6.5, "red"), (21.8, 6.45, "red"),
            (22.5, 5.95, "red"), (23.0, 5.5, "red"), (23.6, 4.7, "red"), (24.1, 3.9, "red")]
    n = 32
    rings, bm_ = [], []
    for y, rr, mname in prof:
        rings.append([(dcx + rr * math.cos(2 * math.pi * k / n), y, ZC + rr * math.sin(2 * math.pi * k / n))
                      for k in range(n)])
        bm_.append(M[mname])
    skin(bm, rings, [bm_[i] if bm_[i] == bm_[i + 1] else M["seam"] for i in range(len(bm_) - 1)])
    # End collars where the pole leaves the drum.
    for y0, y1 in ((3.3, 4.0), (24.0, 24.7)):
        tube(bm, [(px_, y0, ZC), (px_, y1, ZC)], [r + 0.55, r + 0.55], M["steel"], sides=24)

    # Ears on the end collars (rows 2-3 and 24-25, right of the pole).
    for y0, y1 in ((2.0, 4.05), (23.95, 25.9)):
        chbox(bm, 13.8, 16.55, y0, y1, ZC - 1.6, ZC + 2.0, 0.4, M["steel"])
    # Strap clamp round the right flank (rows 10-14) and the slim side tank below it (rows 15-22).
    arc = [math.radians(a) for a in frange(-40, 62, 6)]
    for i, (rin, rout) in enumerate([(6.2, 6.95)]):
        ringA = [(dcx + rout * math.cos(a), 10.15, ZC + rout * math.sin(a)) for a in arc] + \
                [(dcx + rin * math.cos(a), 10.15, ZC + rin * math.sin(a)) for a in reversed(arc)]
        ringB = [(x, 14.85, z) for x, _, z in ringA]
        skin(bm, [ringA, ringB], M["brk"])
    chbox(bm, 18.4, 19.85, 10.6, 14.4, 6.3, 9.8, 0.35, M["brk"])  # clamp bolt block
    tube(bm, [(17.4, 14.9, ZC + 2.4), (17.4, 15.6, ZC + 2.4), (17.4, 21.8, ZC + 2.4), (17.4, 22.9, ZC + 2.4)],
         [0.8, 1.55, 1.55, 0.7], M["red"], sides=16)
    # The grey rail along the drum's right shoulder (column 15, rows 11-21).
    zr = ZC + math.sqrt(6.5 ** 2 - (15.5 - dcx) ** 2)
    tube(bm, [(15.5, 11.0, zr - 0.15), (15.5, 21.6, zr - 0.15)], [0.55, 0.55], M["brk"], sides=8)
    # Mounting saddles over the pole on top (rows 5-7 and 19-23) and the latch at the upper left.
    for x0, x1, y0, y1 in ((9.9, 12.1, 4.7, 7.9), (9.8, 14.0, 19.0, 23.5)):
        chbox(bm, x0, x1, y0, y1, ZC + 4.0, ZC + 6.9, 0.45, M["steel"])
    chbox(bm, 6.55, 8.25, 6.9, 10.1, ZC + 1.8, ZC + 4.85, 0.35, M["latch"])
    # The orange lamp on the cap (row 6, columns 13-14) in a steel bezel.
    zl = ZC + math.sqrt(6.2 ** 2 - (13.9 - dcx) ** 2)
    tube(bm, [(13.9, 6.4, zl - 0.6), (13.9, 6.4, zl + 0.15)], [1.15, 1.15], M["steel"], sides=12)
    ellipsoid(bm, (13.9, 6.4, zl + 0.15), (0.95, 0.85, 0.6), M["lamp"], seg=12, rings=6)

    return to_object(POLE, bm, mats, coll, origin_x=12.0)


# --- outline shells, split, export ------------------------------------------------------------------------

def copy_obj(obj, name, coll):
    o = obj.copy()
    o.data = obj.data.copy()
    o.name = name
    coll.objects.link(o)
    return o


def cut_open(obj, x0=None, x1=None, y0=None, y1=None, fill=False):
    """Keep the part of obj inside the box (Blender units, local coords); cut faces left open unless fill."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    planes = []
    if x0 is not None:
        planes.append(((x0, 0, 0), (-1, 0, 0)))
    if x1 is not None:
        planes.append(((x1, 0, 0), (1, 0, 0)))
    if y0 is not None:
        planes.append(((0, y0, 0), (0, -1, 0)))
    if y1 is not None:
        planes.append(((0, y1, 0), (0, 1, 0)))
    for co, no in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        if fill:
            edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def build_and_export(which, out=None, game=None):
    """which: 'gate' (newsh5-85, newsh5-87) or 'pole' (newsh5-168). Exports only those models."""
    sprite, _ = merged_sprite()
    coll = common.reset_collection(NAME + ("" if which == "gate" else "_pole"))
    stats = {}
    export, gamep = [], {}
    if which == "gate":
        gmats, GM = gate_materials(sprite)
        gate = build_gate(coll, gmats, GM)
        # Outline shell from the sealed, uncut model (D51, D189 islands="outer").
        gshell = common.outline_shell(gate, coll, faces=7000, islands="outer")
        layout = [("newsh5-85", -12, 0), ("newsh5-87", 12, 0)]
        pieces = common.split_assembly(gate, layout, coll)
        for name, cx, cy in layout:
            p = pieces[name]
            p.name = name
            sh = copy_obj(gshell, f"{name}_outline", coll)
            x0 = cx * PX
            cut_open(sh, x0=x0 - 1.0, x1=x0 + 1.0)
            for v in sh.data.vertices:
                v.co.x -= x0
            sh["tyrian_outline"] = True
            if not sh.data.polygons:
                raise SystemExit(f"{name}_outline has no mesh")
            wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
            wn.keep_sharp = True
            p.location = (x0, 0, 0)
            sh.location = (x0, 0, 0)
            gamep[name] = [p, sh]
            stats[name] = {"tris": tri_count(p), "shell_tris": tri_count(sh)}
        bpy.data.objects.remove(gshell, do_unlink=True)
        bpy.data.objects.remove(gate, do_unlink=True)
    else:
        pmats, PM = pole_materials(sprite)
        pole = build_pole(coll, pmats, PM)
        pshell = common.outline_shell(pole, coll, faces=1200, islands="outer")
        # The link's shell stops exactly at the block's top and bottom edges, so stacked links show
        # one continuous outline along the pole with no ink ring at the joints.
        cut_open(pshell, y0=-14 * PX, y1=14 * PX)
        pole.name = POLE
        pshell.name = f"{POLE}_outline"
        pshell["tyrian_outline"] = True
        if not pshell.data.polygons:
            raise SystemExit("pole outline has no mesh")
        pole.location = (36 * PX, 0, 0)
        pshell.location = (36 * PX, 0, 0)
        gamep[POLE] = [pole, pshell]
        stats[POLE] = {"tris": tri_count(pole), "shell_tris": tri_count(pshell)}
    print("STATS", json.dumps(stats))

    for name, objs in gamep.items():
        locs = [o.location.copy() for o in objs]
        for o in objs:
            o.location = (0, 0, 0)
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, objs, f"enemies/{name}", data["sprites"])
        if game:
            common.export_glb(objs, Path(game) / f"{name}.glb")
        for o, l in zip(objs, locs):
            o.location = l
    if out:
        common.export_glb([o for v in gamep.values() for o in v], Path(out))


def main():
    build_and_export("gate", out=arg("--out"), game=arg("--game"))


if __name__ == "__main__":
    main()
